__FILENAME__ = example
#!/usr/bin/env python
import threading, logging, time

from kafka.client import KafkaClient
from kafka.consumer import SimpleConsumer
from kafka.producer import SimpleProducer

class Producer(threading.Thread):
    daemon = True

    def run(self):
        client = KafkaClient("localhost:9092")
        producer = SimpleProducer(client)

        while True:
            producer.send_messages('my-topic', "test")
            producer.send_messages('my-topic', "\xc2Hola, mundo!")

            time.sleep(1)


class Consumer(threading.Thread):
    daemon = True

    def run(self):
        client = KafkaClient("localhost:9092")
        consumer = SimpleConsumer(client, "test-group", "my-topic")

        for message in consumer:
            print(message)

def main():
    threads = [
        Producer(),
        Consumer()
    ]

    for t in threads:
        t.start()

    time.sleep(5)

if __name__ == "__main__":
    logging.basicConfig(
        format='%(asctime)s.%(msecs)s:%(name)s:%(thread)d:%(levelname)s:%(process)d:%(message)s',
        level=logging.DEBUG
        )
    main()

########NEW FILE########
__FILENAME__ = client
import copy
import logging
import collections

import kafka.common

from functools import partial
from itertools import count
from kafka.common import (TopicAndPartition,
                          ConnectionError, FailedPayloadsError,
                          PartitionUnavailableError,
                          LeaderUnavailableError, KafkaUnavailableError,
                          UnknownTopicOrPartitionError, NotLeaderForPartitionError)

from kafka.conn import collect_hosts, KafkaConnection, DEFAULT_SOCKET_TIMEOUT_SECONDS
from kafka.protocol import KafkaProtocol

log = logging.getLogger("kafka")


class KafkaClient(object):

    CLIENT_ID = "kafka-python"
    ID_GEN = count()

    # NOTE: The timeout given to the client should always be greater than the
    # one passed to SimpleConsumer.get_message(), otherwise you can get a
    # socket timeout.
    def __init__(self, hosts, client_id=CLIENT_ID,
                 timeout=DEFAULT_SOCKET_TIMEOUT_SECONDS):
        # We need one connection to bootstrap
        self.client_id = client_id
        self.timeout = timeout
        self.hosts = collect_hosts(hosts)

        # create connections only when we need them
        self.conns = {}
        self.brokers = {}            # broker_id -> BrokerMetadata
        self.topics_to_brokers = {}  # topic_id -> broker_id
        self.topic_partitions = {}   # topic_id -> [0, 1, 2, ...]
        self.load_metadata_for_topics()  # bootstrap with all metadata


    ##################
    #   Private API  #
    ##################

    def _get_conn(self, host, port):
        "Get or create a connection to a broker using host and port"
        host_key = (host, port)
        if host_key not in self.conns:
            self.conns[host_key] = KafkaConnection(
                host,
                port,
                timeout=self.timeout
            )

        return self.conns[host_key]

    def _get_leader_for_partition(self, topic, partition):
        """
        Returns the leader for a partition or None if the partition exists
        but has no leader.

        PartitionUnavailableError will be raised if the topic or partition
        is not part of the metadata.
        """

        key = TopicAndPartition(topic, partition)
        # reload metadata whether the partition is not available
        # or has no leader (broker is None)
        if self.topics_to_brokers.get(key) is None:
            self.load_metadata_for_topics(topic)

        if key not in self.topics_to_brokers:
            raise PartitionUnavailableError("%s not available" % str(key))

        return self.topics_to_brokers[key]

    def _next_id(self):
        """
        Generate a new correlation id
        """
        return KafkaClient.ID_GEN.next()

    def _send_broker_unaware_request(self, requestId, request):
        """
        Attempt to send a broker-agnostic request to one of the available
        brokers. Keep trying until you succeed.
        """
        for (host, port) in self.hosts:
            try:
                conn = self._get_conn(host, port)
                conn.send(requestId, request)
                response = conn.recv(requestId)
                return response
            except Exception as e:
                log.warning("Could not send request [%r] to server %s:%i, "
                            "trying next server: %s" % (request, host, port, e))

        raise KafkaUnavailableError("All servers failed to process request")

    def _send_broker_aware_request(self, payloads, encoder_fn, decoder_fn):
        """
        Group a list of request payloads by topic+partition and send them to
        the leader broker for that partition using the supplied encode/decode
        functions

        Params
        ======
        payloads: list of object-like entities with a topic and
                  partition attribute
        encode_fn: a method to encode the list of payloads to a request body,
                   must accept client_id, correlation_id, and payloads as
                   keyword arguments
        decode_fn: a method to decode a response body into response objects.
                   The response objects must be object-like and have topic
                   and partition attributes

        Return
        ======
        List of response objects in the same order as the supplied payloads
        """

        # Group the requests by topic+partition
        original_keys = []
        payloads_by_broker = collections.defaultdict(list)

        for payload in payloads:
            leader = self._get_leader_for_partition(payload.topic,
                                                    payload.partition)
            if leader is None:
                raise LeaderUnavailableError(
                    "Leader not available for topic %s partition %s" %
                    (payload.topic, payload.partition))

            payloads_by_broker[leader].append(payload)
            original_keys.append((payload.topic, payload.partition))

        # Accumulate the responses in a dictionary
        acc = {}

        # keep a list of payloads that were failed to be sent to brokers
        failed_payloads = []

        # For each broker, send the list of request payloads
        for broker, payloads in payloads_by_broker.items():
            conn = self._get_conn(broker.host, broker.port)
            requestId = self._next_id()
            request = encoder_fn(client_id=self.client_id,
                                 correlation_id=requestId, payloads=payloads)

            failed = False
            # Send the request, recv the response
            try:
                conn.send(requestId, request)
                if decoder_fn is None:
                    continue
                try:
                    response = conn.recv(requestId)
                except ConnectionError as e:
                    log.warning("Could not receive response to request [%s] "
                                "from server %s: %s", request, conn, e)
                    failed = True
            except ConnectionError as e:
                log.warning("Could not send request [%s] to server %s: %s",
                            request, conn, e)
                failed = True

            if failed:
                failed_payloads += payloads
                self.reset_all_metadata()
                continue

            for response in decoder_fn(response):
                acc[(response.topic, response.partition)] = response

        if failed_payloads:
            raise FailedPayloadsError(failed_payloads)

        # Order the accumulated responses by the original key order
        return (acc[k] for k in original_keys) if acc else ()

    def __repr__(self):
        return '<KafkaClient client_id=%s>' % (self.client_id)

    def _raise_on_response_error(self, resp):
        try:
            kafka.common.check_error(resp)
        except (UnknownTopicOrPartitionError, NotLeaderForPartitionError) as e:
            self.reset_topic_metadata(resp.topic)
            raise

    #################
    #   Public API  #
    #################
    def reset_topic_metadata(self, *topics):
        for topic in topics:
            try:
                partitions = self.topic_partitions[topic]
            except KeyError:
                continue

            for partition in partitions:
                self.topics_to_brokers.pop(TopicAndPartition(topic, partition), None)

            del self.topic_partitions[topic]

    def reset_all_metadata(self):
        self.topics_to_brokers.clear()
        self.topic_partitions.clear()

    def has_metadata_for_topic(self, topic):
        return topic in self.topic_partitions

    def close(self):
        for conn in self.conns.values():
            conn.close()

    def copy(self):
        """
        Create an inactive copy of the client object
        A reinit() has to be done on the copy before it can be used again
        """
        c = copy.deepcopy(self)
        for k, v in c.conns.items():
            c.conns[k] = v.copy()
        return c

    def reinit(self):
        for conn in self.conns.values():
            conn.reinit()

    def load_metadata_for_topics(self, *topics):
        """
        Discover brokers and metadata for a set of topics. This function is called
        lazily whenever metadata is unavailable.
        """
        request_id = self._next_id()
        request = KafkaProtocol.encode_metadata_request(self.client_id,
                                                        request_id, topics)

        response = self._send_broker_unaware_request(request_id, request)

        (brokers, topics) = KafkaProtocol.decode_metadata_response(response)

        log.debug("Broker metadata: %s", brokers)
        log.debug("Topic metadata: %s", topics)

        self.brokers = brokers

        for topic, partitions in topics.items():
            self.reset_topic_metadata(topic)

            if not partitions:
                log.warning('No partitions for %s', topic)
                continue

            self.topic_partitions[topic] = []
            for partition, meta in partitions.items():
                self.topic_partitions[topic].append(partition)
                topic_part = TopicAndPartition(topic, partition)
                if meta.leader == -1:
                    log.warning('No leader for topic %s partition %s', topic, partition)
                    self.topics_to_brokers[topic_part] = None
                else:
                    self.topics_to_brokers[topic_part] = brokers[meta.leader]

    def send_produce_request(self, payloads=[], acks=1, timeout=1000,
                             fail_on_error=True, callback=None):
        """
        Encode and send some ProduceRequests

        ProduceRequests will be grouped by (topic, partition) and then
        sent to a specific broker. Output is a list of responses in the
        same order as the list of payloads specified

        Params
        ======
        payloads: list of ProduceRequest
        fail_on_error: boolean, should we raise an Exception if we
                       encounter an API error?
        callback: function, instead of returning the ProduceResponse,
                  first pass it through this function

        Return
        ======
        list of ProduceResponse or callback(ProduceResponse), in the
        order of input payloads
        """

        encoder = partial(
            KafkaProtocol.encode_produce_request,
            acks=acks,
            timeout=timeout)

        if acks == 0:
            decoder = None
        else:
            decoder = KafkaProtocol.decode_produce_response

        resps = self._send_broker_aware_request(payloads, encoder, decoder)

        out = []
        for resp in resps:
            if fail_on_error is True:
                self._raise_on_response_error(resp)

            if callback is not None:
                out.append(callback(resp))
            else:
                out.append(resp)
        return out

    def send_fetch_request(self, payloads=[], fail_on_error=True,
                           callback=None, max_wait_time=100, min_bytes=4096):
        """
        Encode and send a FetchRequest

        Payloads are grouped by topic and partition so they can be pipelined
        to the same brokers.
        """

        encoder = partial(KafkaProtocol.encode_fetch_request,
                          max_wait_time=max_wait_time,
                          min_bytes=min_bytes)

        resps = self._send_broker_aware_request(
            payloads, encoder,
            KafkaProtocol.decode_fetch_response)

        out = []
        for resp in resps:
            if fail_on_error is True:
                self._raise_on_response_error(resp)

            if callback is not None:
                out.append(callback(resp))
            else:
                out.append(resp)
        return out

    def send_offset_request(self, payloads=[], fail_on_error=True,
                            callback=None):
        resps = self._send_broker_aware_request(
            payloads,
            KafkaProtocol.encode_offset_request,
            KafkaProtocol.decode_offset_response)

        out = []
        for resp in resps:
            if fail_on_error is True:
                self._raise_on_response_error(resp)
            if callback is not None:
                out.append(callback(resp))
            else:
                out.append(resp)
        return out

    def send_offset_commit_request(self, group, payloads=[],
                                   fail_on_error=True, callback=None):
        encoder = partial(KafkaProtocol.encode_offset_commit_request,
                          group=group)
        decoder = KafkaProtocol.decode_offset_commit_response
        resps = self._send_broker_aware_request(payloads, encoder, decoder)

        out = []
        for resp in resps:
            if fail_on_error is True:
                self._raise_on_response_error(resp)

            if callback is not None:
                out.append(callback(resp))
            else:
                out.append(resp)
        return out

    def send_offset_fetch_request(self, group, payloads=[],
                                  fail_on_error=True, callback=None):

        encoder = partial(KafkaProtocol.encode_offset_fetch_request,
                          group=group)
        decoder = KafkaProtocol.decode_offset_fetch_response
        resps = self._send_broker_aware_request(payloads, encoder, decoder)

        out = []
        for resp in resps:
            if fail_on_error is True:
                self._raise_on_response_error(resp)
            if callback is not None:
                out.append(callback(resp))
            else:
                out.append(resp)
        return out

########NEW FILE########
__FILENAME__ = codec
from cStringIO import StringIO
import gzip
import struct

_XERIAL_V1_HEADER = (-126, 'S', 'N', 'A', 'P', 'P', 'Y', 0, 1, 1)
_XERIAL_V1_FORMAT = 'bccccccBii'

try:
    import snappy
    _has_snappy = True
except ImportError:
    _has_snappy = False


def has_gzip():
    return True


def has_snappy():
    return _has_snappy


def gzip_encode(payload):
    buffer = StringIO()
    handle = gzip.GzipFile(fileobj=buffer, mode="w")
    handle.write(payload)
    handle.close()
    buffer.seek(0)
    result = buffer.read()
    buffer.close()
    return result


def gzip_decode(payload):
    buffer = StringIO(payload)
    handle = gzip.GzipFile(fileobj=buffer, mode='r')
    result = handle.read()
    handle.close()
    buffer.close()
    return result


def snappy_encode(payload, xerial_compatible=False, xerial_blocksize=32 * 1024):
    """Encodes the given data with snappy if xerial_compatible is set then the
       stream is encoded in a fashion compatible with the xerial snappy library

       The block size (xerial_blocksize) controls how frequent the blocking occurs
       32k is the default in the xerial library.

       The format winds up being
        +-------------+------------+--------------+------------+--------------+
        |   Header    | Block1 len | Block1 data  | Blockn len | Blockn data  |
        |-------------+------------+--------------+------------+--------------|
        |  16 bytes   |  BE int32  | snappy bytes |  BE int32  | snappy bytes |
        +-------------+------------+--------------+------------+--------------+

        It is important to not that the blocksize is the amount of uncompressed
        data presented to snappy at each block, whereas the blocklen is the
        number of bytes that will be present in the stream, that is the
        length will always be <= blocksize.
    """

    if not _has_snappy:
        raise NotImplementedError("Snappy codec is not available")

    if xerial_compatible:
        def _chunker():
            for i in xrange(0, len(payload), xerial_blocksize):
                yield payload[i:i+xerial_blocksize]

        out = StringIO()

        header = ''.join([struct.pack('!' + fmt, dat) for fmt, dat
            in zip(_XERIAL_V1_FORMAT, _XERIAL_V1_HEADER)])

        out.write(header)
        for chunk in _chunker():
            block = snappy.compress(chunk)
            block_size = len(block)
            out.write(struct.pack('!i', block_size))
            out.write(block)

        out.seek(0)
        return out.read()

    else:
        return snappy.compress(payload)


def _detect_xerial_stream(payload):
    """Detects if the data given might have been encoded with the blocking mode
        of the xerial snappy library.

        This mode writes a magic header of the format:
            +--------+--------------+------------+---------+--------+
            | Marker | Magic String | Null / Pad | Version | Compat |
            |--------+--------------+------------+---------+--------|
            |  byte  |   c-string   |    byte    |  int32  | int32  |
            |--------+--------------+------------+---------+--------|
            |  -126  |   'SNAPPY'   |     \0     |         |        |
            +--------+--------------+------------+---------+--------+

        The pad appears to be to ensure that SNAPPY is a valid cstring
        The version is the version of this format as written by xerial,
        in the wild this is currently 1 as such we only support v1.

        Compat is there to claim the miniumum supported version that
        can read a xerial block stream, presently in the wild this is
        1.
    """

    if len(payload) > 16:
        header = header = struct.unpack('!' + _XERIAL_V1_FORMAT, bytes(payload)[:16])
        return header == _XERIAL_V1_HEADER
    return False


def snappy_decode(payload):
    if not _has_snappy:
        raise NotImplementedError("Snappy codec is not available")

    if _detect_xerial_stream(payload):
        # TODO ? Should become a fileobj ?
        out = StringIO()
        byt = buffer(payload[16:])
        length = len(byt)
        cursor = 0

        while cursor < length:
            block_size = struct.unpack_from('!i', byt[cursor:])[0]
            # Skip the block size
            cursor += 4
            end = cursor + block_size
            out.write(snappy.decompress(byt[cursor:end]))
            cursor = end

        out.seek(0)
        return out.read()
    else:
        return snappy.decompress(payload)

########NEW FILE########
__FILENAME__ = common
from collections import namedtuple

###############
#   Structs   #
###############

# Request payloads
ProduceRequest = namedtuple("ProduceRequest",
                            ["topic", "partition", "messages"])

FetchRequest = namedtuple("FetchRequest",
                          ["topic", "partition", "offset", "max_bytes"])

OffsetRequest = namedtuple("OffsetRequest",
                           ["topic", "partition", "time", "max_offsets"])

OffsetCommitRequest = namedtuple("OffsetCommitRequest",
                                 ["topic", "partition", "offset", "metadata"])

OffsetFetchRequest = namedtuple("OffsetFetchRequest", ["topic", "partition"])

# Response payloads
ProduceResponse = namedtuple("ProduceResponse",
                             ["topic", "partition", "error", "offset"])

FetchResponse = namedtuple("FetchResponse", ["topic", "partition", "error",
                                             "highwaterMark", "messages"])

OffsetResponse = namedtuple("OffsetResponse",
                            ["topic", "partition", "error", "offsets"])

OffsetCommitResponse = namedtuple("OffsetCommitResponse",
                                  ["topic", "partition", "error"])

OffsetFetchResponse = namedtuple("OffsetFetchResponse",
                                 ["topic", "partition", "offset",
                                  "metadata", "error"])

BrokerMetadata = namedtuple("BrokerMetadata", ["nodeId", "host", "port"])

PartitionMetadata = namedtuple("PartitionMetadata",
                               ["topic", "partition", "leader",
                                "replicas", "isr"])

# Other useful structs
OffsetAndMessage = namedtuple("OffsetAndMessage", ["offset", "message"])
Message = namedtuple("Message", ["magic", "attributes", "key", "value"])
TopicAndPartition = namedtuple("TopicAndPartition", ["topic", "partition"])


#################
#   Exceptions  #
#################


class KafkaError(RuntimeError):
    pass


class BrokerResponseError(KafkaError):
    pass


class UnknownError(BrokerResponseError):
    errno = -1
    message = 'UNKNOWN'


class OffsetOutOfRangeError(BrokerResponseError):
    errno = 1
    message = 'OFFSET_OUT_OF_RANGE'


class InvalidMessageError(BrokerResponseError):
    errno = 2
    message = 'INVALID_MESSAGE'


class UnknownTopicOrPartitionError(BrokerResponseError):
    errno = 3
    message = 'UNKNOWN_TOPIC_OR_PARTITON'


class InvalidFetchRequestError(BrokerResponseError):
    errno = 4
    message = 'INVALID_FETCH_SIZE'


class LeaderNotAvailableError(BrokerResponseError):
    errno = 5
    message = 'LEADER_NOT_AVAILABLE'


class NotLeaderForPartitionError(BrokerResponseError):
    errno = 6
    message = 'NOT_LEADER_FOR_PARTITION'


class RequestTimedOutError(BrokerResponseError):
    errno = 7
    message = 'REQUEST_TIMED_OUT'


class BrokerNotAvailableError(BrokerResponseError):
    errno = 8
    message = 'BROKER_NOT_AVAILABLE'


class ReplicaNotAvailableError(BrokerResponseError):
    errno = 9
    message = 'REPLICA_NOT_AVAILABLE'


class MessageSizeTooLargeError(BrokerResponseError):
    errno = 10
    message = 'MESSAGE_SIZE_TOO_LARGE'


class StaleControllerEpochError(BrokerResponseError):
    errno = 11
    message = 'STALE_CONTROLLER_EPOCH'


class OffsetMetadataTooLargeError(BrokerResponseError):
    errno = 12
    message = 'OFFSET_METADATA_TOO_LARGE'


class StaleLeaderEpochCodeError(BrokerResponseError):
    errno = 13
    message = 'STALE_LEADER_EPOCH_CODE'


class KafkaUnavailableError(KafkaError):
    pass


class LeaderUnavailableError(KafkaError):
    pass


class PartitionUnavailableError(KafkaError):
    pass


class FailedPayloadsError(KafkaError):
    pass


class ConnectionError(KafkaError):
    pass


class BufferUnderflowError(KafkaError):
    pass


class ChecksumError(KafkaError):
    pass


class ConsumerFetchSizeTooSmall(KafkaError):
    pass


class ConsumerNoMoreData(KafkaError):
    pass


class ProtocolError(KafkaError):
    pass


class UnsupportedCodecError(KafkaError):
    pass


kafka_errors = {
    -1 : UnknownError,
    1  : OffsetOutOfRangeError,
    2  : InvalidMessageError,
    3  : UnknownTopicOrPartitionError,
    4  : InvalidFetchRequestError,
    5  : LeaderNotAvailableError,
    6  : NotLeaderForPartitionError,
    7  : RequestTimedOutError,
    8  : BrokerNotAvailableError,
    9  : ReplicaNotAvailableError,
    10 : MessageSizeTooLargeError,
    11 : StaleControllerEpochError,
    12 : OffsetMetadataTooLargeError,
    13 : StaleLeaderEpochCodeError,
}


def check_error(response):
    error = kafka_errors.get(response.error)
    if error:
        raise error(response)


########NEW FILE########
__FILENAME__ = conn
import copy
import logging
import socket
import struct
from random import shuffle
from threading import local

from kafka.common import ConnectionError

log = logging.getLogger("kafka")

DEFAULT_SOCKET_TIMEOUT_SECONDS = 120
DEFAULT_KAFKA_PORT = 9092


def collect_hosts(hosts, randomize=True):
    """
    Collects a comma-separated set of hosts (host:port) and optionally
    randomize the returned list.
    """

    if isinstance(hosts, basestring):
        hosts = hosts.strip().split(',')

    result = []
    for host_port in hosts:

        res = host_port.split(':')
        host = res[0]
        port = int(res[1]) if len(res) > 1 else DEFAULT_KAFKA_PORT
        result.append((host.strip(), port))

    if randomize:
        shuffle(result)

    return result


class KafkaConnection(local):
    """
    A socket connection to a single Kafka broker

    This class is _not_ thread safe. Each call to `send` must be followed
    by a call to `recv` in order to get the correct response. Eventually,
    we can do something in here to facilitate multiplexed requests/responses
    since the Kafka API includes a correlation id.

    host:    the host name or IP address of a kafka broker
    port:    the port number the kafka broker is listening on
    timeout: default 120. The socket timeout for sending and receiving data
             in seconds. None means no timeout, so a request can block forever.
    """
    def __init__(self, host, port, timeout=DEFAULT_SOCKET_TIMEOUT_SECONDS):
        super(KafkaConnection, self).__init__()
        self.host = host
        self.port = port
        self.timeout = timeout
        self._sock = None

        self.reinit()

    def __repr__(self):
        return "<KafkaConnection host=%s port=%d>" % (self.host, self.port)

    ###################
    #   Private API   #
    ###################

    def _raise_connection_error(self):
        self._dirty = True
        raise ConnectionError("Kafka @ {0}:{1} went away".format(self.host, self.port))

    def _read_bytes(self, num_bytes):
        bytes_left = num_bytes
        responses = []

        log.debug("About to read %d bytes from Kafka", num_bytes)
        if self._dirty:
            self.reinit()

        while bytes_left:
            try:
                data = self._sock.recv(min(bytes_left, 4096))
            except socket.error:
                log.exception('Unable to receive data from Kafka')
                self._raise_connection_error()

            if data == '':
                log.error("Not enough data to read this response")
                self._raise_connection_error()

            bytes_left -= len(data)
            log.debug("Read %d/%d bytes from Kafka", num_bytes - bytes_left, num_bytes)
            responses.append(data)

        return ''.join(responses)

    ##################
    #   Public API   #
    ##################

    # TODO multiplex socket communication to allow for multi-threaded clients

    def send(self, request_id, payload):
        "Send a request to Kafka"
        log.debug("About to send %d bytes to Kafka, request %d" % (len(payload), request_id))
        try:
            if self._dirty:
                self.reinit()
            sent = self._sock.sendall(payload)
            if sent is not None:
                self._raise_connection_error()
        except socket.error:
            log.exception('Unable to send payload to Kafka')
            self._raise_connection_error()

    def recv(self, request_id):
        """
        Get a response from Kafka
        """
        log.debug("Reading response %d from Kafka" % request_id)
        # Read the size off of the header
        resp = self._read_bytes(4)

        (size,) = struct.unpack('>i', resp)

        # Read the remainder of the response
        resp = self._read_bytes(size)
        return str(resp)

    def copy(self):
        """
        Create an inactive copy of the connection object
        A reinit() has to be done on the copy before it can be used again
        """
        c = copy.deepcopy(self)
        c._sock = None
        return c

    def close(self):
        """
        Close this connection
        """
        if self._sock:
            self._sock.close()

    def reinit(self):
        """
        Re-initialize the socket connection
        """
        self.close()
        self._sock = socket.create_connection((self.host, self.port), self.timeout)
        self._dirty = False

########NEW FILE########
__FILENAME__ = consumer
from __future__ import absolute_import

from itertools import izip_longest, repeat
import logging
import time
import numbers
from threading import Lock
from multiprocessing import Process, Queue as MPQueue, Event, Value
from Queue import Empty, Queue

import kafka
from kafka.common import (
    FetchRequest,
    OffsetRequest, OffsetCommitRequest,
    OffsetFetchRequest,
    ConsumerFetchSizeTooSmall, ConsumerNoMoreData
)

from kafka.util import ReentrantTimer

log = logging.getLogger("kafka")

AUTO_COMMIT_MSG_COUNT = 100
AUTO_COMMIT_INTERVAL = 5000

FETCH_DEFAULT_BLOCK_TIMEOUT = 1
FETCH_MAX_WAIT_TIME = 100
FETCH_MIN_BYTES = 4096
FETCH_BUFFER_SIZE_BYTES = 4096
MAX_FETCH_BUFFER_SIZE_BYTES = FETCH_BUFFER_SIZE_BYTES * 8

ITER_TIMEOUT_SECONDS = 60
NO_MESSAGES_WAIT_TIME_SECONDS = 0.1


class FetchContext(object):
    """
    Class for managing the state of a consumer during fetch
    """
    def __init__(self, consumer, block, timeout):
        self.consumer = consumer
        self.block = block

        if block:
            if not timeout:
                timeout = FETCH_DEFAULT_BLOCK_TIMEOUT
            self.timeout = timeout * 1000

    def __enter__(self):
        """Set fetch values based on blocking status"""
        self.orig_fetch_max_wait_time = self.consumer.fetch_max_wait_time
        self.orig_fetch_min_bytes = self.consumer.fetch_min_bytes
        if self.block:
            self.consumer.fetch_max_wait_time = self.timeout
            self.consumer.fetch_min_bytes = 1
        else:
            self.consumer.fetch_min_bytes = 0

    def __exit__(self, type, value, traceback):
        """Reset values"""
        self.consumer.fetch_max_wait_time = self.orig_fetch_max_wait_time
        self.consumer.fetch_min_bytes = self.orig_fetch_min_bytes


class Consumer(object):
    """
    Base class to be used by other consumers. Not to be used directly

    This base class provides logic for
    * initialization and fetching metadata of partitions
    * Auto-commit logic
    * APIs for fetching pending message count
    """
    def __init__(self, client, group, topic, partitions=None, auto_commit=True,
                 auto_commit_every_n=AUTO_COMMIT_MSG_COUNT,
                 auto_commit_every_t=AUTO_COMMIT_INTERVAL):

        self.client = client
        self.topic = topic
        self.group = group
        self.client.load_metadata_for_topics(topic)
        self.offsets = {}

        if not partitions:
            partitions = self.client.topic_partitions[topic]
        else:
            assert all(isinstance(x, numbers.Integral) for x in partitions)

        # Variables for handling offset commits
        self.commit_lock = Lock()
        self.commit_timer = None
        self.count_since_commit = 0
        self.auto_commit = auto_commit
        self.auto_commit_every_n = auto_commit_every_n
        self.auto_commit_every_t = auto_commit_every_t

        # Set up the auto-commit timer
        if auto_commit is True and auto_commit_every_t is not None:
            self.commit_timer = ReentrantTimer(auto_commit_every_t,
                                               self.commit)
            self.commit_timer.start()

        def get_or_init_offset_callback(resp):
            try:
                kafka.common.check_error(resp)
                return resp.offset
            except kafka.common.UnknownTopicOrPartitionError:
                return 0

        if auto_commit:
            for partition in partitions:
                req = OffsetFetchRequest(topic, partition)
                (offset,) = self.client.send_offset_fetch_request(group, [req],
                              callback=get_or_init_offset_callback,
                              fail_on_error=False)
                self.offsets[partition] = offset
        else:
            for partition in partitions:
                self.offsets[partition] = 0

    def commit(self, partitions=None):
        """
        Commit offsets for this consumer

        partitions: list of partitions to commit, default is to commit
                    all of them
        """

        # short circuit if nothing happened. This check is kept outside
        # to prevent un-necessarily acquiring a lock for checking the state
        if self.count_since_commit == 0:
            return

        with self.commit_lock:
            # Do this check again, just in case the state has changed
            # during the lock acquiring timeout
            if self.count_since_commit == 0:
                return

            reqs = []
            if not partitions:  # commit all partitions
                partitions = self.offsets.keys()

            for partition in partitions:
                offset = self.offsets[partition]
                log.debug("Commit offset %d in SimpleConsumer: "
                          "group=%s, topic=%s, partition=%s" %
                          (offset, self.group, self.topic, partition))

                reqs.append(OffsetCommitRequest(self.topic, partition,
                                                offset, None))

            resps = self.client.send_offset_commit_request(self.group, reqs)
            for resp in resps:
                kafka.common.check_error(resp)

            self.count_since_commit = 0

    def _auto_commit(self):
        """
        Check if we have to commit based on number of messages and commit
        """

        # Check if we are supposed to do an auto-commit
        if not self.auto_commit or self.auto_commit_every_n is None:
            return

        if self.count_since_commit >= self.auto_commit_every_n:
            self.commit()

    def stop(self):
        if self.commit_timer is not None:
            self.commit_timer.stop()
            self.commit()

    def pending(self, partitions=None):
        """
        Gets the pending message count

        partitions: list of partitions to check for, default is to check all
        """
        if not partitions:
            partitions = self.offsets.keys()

        total = 0
        reqs = []

        for partition in partitions:
            reqs.append(OffsetRequest(self.topic, partition, -1, 1))

        resps = self.client.send_offset_request(reqs)
        for resp in resps:
            partition = resp.partition
            pending = resp.offsets[0]
            offset = self.offsets[partition]
            total += pending - offset - (1 if offset > 0 else 0)

        return total


class SimpleConsumer(Consumer):
    """
    A simple consumer implementation that consumes all/specified partitions
    for a topic

    client: a connected KafkaClient
    group: a name for this consumer, used for offset storage and must be unique
    topic: the topic to consume
    partitions: An optional list of partitions to consume the data from

    auto_commit: default True. Whether or not to auto commit the offsets
    auto_commit_every_n: default 100. How many messages to consume
                         before a commit
    auto_commit_every_t: default 5000. How much time (in milliseconds) to
                         wait before commit
    fetch_size_bytes:    number of bytes to request in a FetchRequest
    buffer_size:         default 4K. Initial number of bytes to tell kafka we
                         have available. This will double as needed.
    max_buffer_size:     default 16K. Max number of bytes to tell kafka we have
                         available. None means no limit.
    iter_timeout:        default None. How much time (in seconds) to wait for a
                         message in the iterator before exiting. None means no
                         timeout, so it will wait forever.

    Auto commit details:
    If both auto_commit_every_n and auto_commit_every_t are set, they will
    reset one another when one is triggered. These triggers simply call the
    commit method on this class. A manual call to commit will also reset
    these triggers
    """
    def __init__(self, client, group, topic, auto_commit=True, partitions=None,
                 auto_commit_every_n=AUTO_COMMIT_MSG_COUNT,
                 auto_commit_every_t=AUTO_COMMIT_INTERVAL,
                 fetch_size_bytes=FETCH_MIN_BYTES,
                 buffer_size=FETCH_BUFFER_SIZE_BYTES,
                 max_buffer_size=MAX_FETCH_BUFFER_SIZE_BYTES,
                 iter_timeout=None):
        super(SimpleConsumer, self).__init__(
            client, group, topic,
            partitions=partitions,
            auto_commit=auto_commit,
            auto_commit_every_n=auto_commit_every_n,
            auto_commit_every_t=auto_commit_every_t)

        if max_buffer_size is not None and buffer_size > max_buffer_size:
            raise ValueError("buffer_size (%d) is greater than "
                             "max_buffer_size (%d)" %
                             (buffer_size, max_buffer_size))
        self.buffer_size = buffer_size
        self.max_buffer_size = max_buffer_size
        self.partition_info = False     # Do not return partition info in msgs
        self.fetch_max_wait_time = FETCH_MAX_WAIT_TIME
        self.fetch_min_bytes = fetch_size_bytes
        self.fetch_offsets = self.offsets.copy()
        self.iter_timeout = iter_timeout
        self.queue = Queue()

    def __repr__(self):
        return '<SimpleConsumer group=%s, topic=%s, partitions=%s>' % \
            (self.group, self.topic, str(self.offsets.keys()))

    def provide_partition_info(self):
        """
        Indicates that partition info must be returned by the consumer
        """
        self.partition_info = True

    def seek(self, offset, whence):
        """
        Alter the current offset in the consumer, similar to fseek

        offset: how much to modify the offset
        whence: where to modify it from
                0 is relative to the earliest available offset (head)
                1 is relative to the current offset
                2 is relative to the latest known offset (tail)
        """

        if whence == 1:  # relative to current position
            for partition, _offset in self.offsets.items():
                self.offsets[partition] = _offset + offset
        elif whence in (0, 2):  # relative to beginning or end
            # divide the request offset by number of partitions,
            # distribute the remained evenly
            (delta, rem) = divmod(offset, len(self.offsets))
            deltas = {}
            for partition, r in izip_longest(self.offsets.keys(),
                                             repeat(1, rem), fillvalue=0):
                deltas[partition] = delta + r

            reqs = []
            for partition in self.offsets.keys():
                if whence == 0:
                    reqs.append(OffsetRequest(self.topic, partition, -2, 1))
                elif whence == 2:
                    reqs.append(OffsetRequest(self.topic, partition, -1, 1))
                else:
                    pass

            resps = self.client.send_offset_request(reqs)
            for resp in resps:
                self.offsets[resp.partition] = \
                    resp.offsets[0] + deltas[resp.partition]
        else:
            raise ValueError("Unexpected value for `whence`, %d" % whence)

        # Reset queue and fetch offsets since they are invalid
        self.fetch_offsets = self.offsets.copy()
        if self.auto_commit:
            self.count_since_commit += 1
            self.commit()

        self.queue = Queue()

    def get_messages(self, count=1, block=True, timeout=0.1):
        """
        Fetch the specified number of messages

        count: Indicates the maximum number of messages to be fetched
        block: If True, the API will block till some messages are fetched.
        timeout: If block is True, the function will block for the specified
                 time (in seconds) until count messages is fetched. If None,
                 it will block forever.
        """
        messages = []
        if timeout is not None:
            max_time = time.time() + timeout

        new_offsets = {}
        while count > 0 and (timeout is None or timeout > 0):
            result = self._get_message(block, timeout, get_partition_info=True,
                                       update_offset=False)
            if result:
                partition, message = result
                if self.partition_info:
                    messages.append(result)
                else:
                    messages.append(message)
                new_offsets[partition] = message.offset + 1
                count -= 1
            else:
                # Ran out of messages for the last request.
                if not block:
                    # If we're not blocking, break.
                    break
                if timeout is not None:
                    # If we're blocking and have a timeout, reduce it to the
                    # appropriate value
                    timeout = max_time - time.time()

        # Update and commit offsets if necessary
        self.offsets.update(new_offsets)
        self.count_since_commit += len(messages)
        self._auto_commit()
        return messages

    def get_message(self, block=True, timeout=0.1, get_partition_info=None):
        return self._get_message(block, timeout, get_partition_info)

    def _get_message(self, block=True, timeout=0.1, get_partition_info=None,
                     update_offset=True):
        """
        If no messages can be fetched, returns None.
        If get_partition_info is None, it defaults to self.partition_info
        If get_partition_info is True, returns (partition, message)
        If get_partition_info is False, returns message
        """
        if self.queue.empty():
            # We're out of messages, go grab some more.
            with FetchContext(self, block, timeout):
                self._fetch()
        try:
            partition, message = self.queue.get_nowait()

            if update_offset:
                # Update partition offset
                self.offsets[partition] = message.offset + 1

                # Count, check and commit messages if necessary
                self.count_since_commit += 1
                self._auto_commit()

            if get_partition_info is None:
                get_partition_info = self.partition_info
            if get_partition_info:
                return partition, message
            else:
                return message
        except Empty:
            return None

    def __iter__(self):
        if self.iter_timeout is None:
            timeout = ITER_TIMEOUT_SECONDS
        else:
            timeout = self.iter_timeout

        while True:
            message = self.get_message(True, timeout)
            if message:
                yield message
            elif self.iter_timeout is None:
                # We did not receive any message yet but we don't have a
                # timeout, so give up the CPU for a while before trying again
                time.sleep(NO_MESSAGES_WAIT_TIME_SECONDS)
            else:
                # Timed out waiting for a message
                break

    def _fetch(self):
        # Create fetch request payloads for all the partitions
        requests = []
        partitions = self.fetch_offsets.keys()
        while partitions:
            for partition in partitions:
                requests.append(FetchRequest(self.topic, partition,
                                             self.fetch_offsets[partition],
                                             self.buffer_size))
            # Send request
            responses = self.client.send_fetch_request(
                requests,
                max_wait_time=int(self.fetch_max_wait_time),
                min_bytes=self.fetch_min_bytes)

            retry_partitions = set()
            for resp in responses:
                partition = resp.partition
                try:
                    for message in resp.messages:
                        # Put the message in our queue
                        self.queue.put((partition, message))
                        self.fetch_offsets[partition] = message.offset + 1
                except ConsumerFetchSizeTooSmall:
                    if (self.max_buffer_size is not None and
                            self.buffer_size == self.max_buffer_size):
                        log.error("Max fetch size %d too small",
                                  self.max_buffer_size)
                        raise
                    if self.max_buffer_size is None:
                        self.buffer_size *= 2
                    else:
                        self.buffer_size = max(self.buffer_size * 2,
                                               self.max_buffer_size)
                    log.warn("Fetch size too small, increase to %d (2x) "
                             "and retry", self.buffer_size)
                    retry_partitions.add(partition)
                except ConsumerNoMoreData as e:
                    log.debug("Iteration was ended by %r", e)
                except StopIteration:
                    # Stop iterating through this partition
                    log.debug("Done iterating over partition %s" % partition)
                partitions = retry_partitions

def _mp_consume(client, group, topic, chunk, queue, start, exit, pause, size):
    """
    A child process worker which consumes messages based on the
    notifications given by the controller process

    NOTE: Ideally, this should have been a method inside the Consumer
    class. However, multiprocessing module has issues in windows. The
    functionality breaks unless this function is kept outside of a class
    """

    # Make the child processes open separate socket connections
    client.reinit()

    # We will start consumers without auto-commit. Auto-commit will be
    # done by the master controller process.
    consumer = SimpleConsumer(client, group, topic,
                              partitions=chunk,
                              auto_commit=False,
                              auto_commit_every_n=None,
                              auto_commit_every_t=None)

    # Ensure that the consumer provides the partition information
    consumer.provide_partition_info()

    while True:
        # Wait till the controller indicates us to start consumption
        start.wait()

        # If we are asked to quit, do so
        if exit.is_set():
            break

        # Consume messages and add them to the queue. If the controller
        # indicates a specific number of messages, follow that advice
        count = 0

        message = consumer.get_message()
        if message:
            queue.put(message)
            count += 1

            # We have reached the required size. The controller might have
            # more than what he needs. Wait for a while.
            # Without this logic, it is possible that we run into a big
            # loop consuming all available messages before the controller
            # can reset the 'start' event
            if count == size.value:
                pause.wait()

        else:
            # In case we did not receive any message, give up the CPU for
            # a while before we try again
            time.sleep(NO_MESSAGES_WAIT_TIME_SECONDS)

    consumer.stop()


class MultiProcessConsumer(Consumer):
    """
    A consumer implementation that consumes partitions for a topic in
    parallel using multiple processes

    client: a connected KafkaClient
    group: a name for this consumer, used for offset storage and must be unique
    topic: the topic to consume

    auto_commit: default True. Whether or not to auto commit the offsets
    auto_commit_every_n: default 100. How many messages to consume
                         before a commit
    auto_commit_every_t: default 5000. How much time (in milliseconds) to
                         wait before commit
    num_procs: Number of processes to start for consuming messages.
               The available partitions will be divided among these processes
    partitions_per_proc: Number of partitions to be allocated per process
               (overrides num_procs)

    Auto commit details:
    If both auto_commit_every_n and auto_commit_every_t are set, they will
    reset one another when one is triggered. These triggers simply call the
    commit method on this class. A manual call to commit will also reset
    these triggers
    """
    def __init__(self, client, group, topic, auto_commit=True,
                 auto_commit_every_n=AUTO_COMMIT_MSG_COUNT,
                 auto_commit_every_t=AUTO_COMMIT_INTERVAL,
                 num_procs=1, partitions_per_proc=0):

        # Initiate the base consumer class
        super(MultiProcessConsumer, self).__init__(
            client, group, topic,
            partitions=None,
            auto_commit=auto_commit,
            auto_commit_every_n=auto_commit_every_n,
            auto_commit_every_t=auto_commit_every_t)

        # Variables for managing and controlling the data flow from
        # consumer child process to master
        self.queue = MPQueue(1024)  # Child consumers dump messages into this
        self.start = Event()        # Indicates the consumers to start fetch
        self.exit = Event()         # Requests the consumers to shutdown
        self.pause = Event()        # Requests the consumers to pause fetch
        self.size = Value('i', 0)   # Indicator of number of messages to fetch

        partitions = self.offsets.keys()

        # If unspecified, start one consumer per partition
        # The logic below ensures that
        # * we do not cross the num_procs limit
        # * we have an even distribution of partitions among processes
        if not partitions_per_proc:
            partitions_per_proc = round(len(partitions) * 1.0 / num_procs)
            if partitions_per_proc < num_procs * 0.5:
                partitions_per_proc += 1

        # The final set of chunks
        chunker = lambda *x: [] + list(x)
        chunks = map(chunker, *[iter(partitions)] * int(partitions_per_proc))

        self.procs = []
        for chunk in chunks:
            chunk = filter(lambda x: x is not None, chunk)
            args = (client.copy(),
                    group, topic, chunk,
                    self.queue, self.start, self.exit,
                    self.pause, self.size)

            proc = Process(target=_mp_consume, args=args)
            proc.daemon = True
            proc.start()
            self.procs.append(proc)

    def __repr__(self):
        return '<MultiProcessConsumer group=%s, topic=%s, consumers=%d>' % \
            (self.group, self.topic, len(self.procs))

    def stop(self):
        # Set exit and start off all waiting consumers
        self.exit.set()
        self.pause.set()
        self.start.set()

        for proc in self.procs:
            proc.join()
            proc.terminate()

        super(MultiProcessConsumer, self).stop()

    def __iter__(self):
        """
        Iterator to consume the messages available on this consumer
        """
        # Trigger the consumer procs to start off.
        # We will iterate till there are no more messages available
        self.size.value = 0
        self.pause.set()

        while True:
            self.start.set()
            try:
                # We will block for a small while so that the consumers get
                # a chance to run and put some messages in the queue
                # TODO: This is a hack and will make the consumer block for
                # at least one second. Need to find a better way of doing this
                partition, message = self.queue.get(block=True, timeout=1)
            except Empty:
                break

            # Count, check and commit messages if necessary
            self.offsets[partition] = message.offset + 1
            self.start.clear()
            self.count_since_commit += 1
            self._auto_commit()
            yield message

        self.start.clear()

    def get_messages(self, count=1, block=True, timeout=10):
        """
        Fetch the specified number of messages

        count: Indicates the maximum number of messages to be fetched
        block: If True, the API will block till some messages are fetched.
        timeout: If block is True, the function will block for the specified
                 time (in seconds) until count messages is fetched. If None,
                 it will block forever.
        """
        messages = []

        # Give a size hint to the consumers. Each consumer process will fetch
        # a maximum of "count" messages. This will fetch more messages than
        # necessary, but these will not be committed to kafka. Also, the extra
        # messages can be provided in subsequent runs
        self.size.value = count
        self.pause.clear()

        if timeout is not None:
            max_time = time.time() + timeout

        new_offsets = {}
        while count > 0 and (timeout is None or timeout > 0):
            # Trigger consumption only if the queue is empty
            # By doing this, we will ensure that consumers do not
            # go into overdrive and keep consuming thousands of
            # messages when the user might need only a few
            if self.queue.empty():
                self.start.set()

            try:
                partition, message = self.queue.get(block, timeout)
            except Empty:
                break

            messages.append(message)
            new_offsets[partition] = message.offset + 1
            count -= 1
            if timeout is not None:
                timeout = max_time - time.time()

        self.size.value = 0
        self.start.clear()
        self.pause.set()

        # Update and commit offsets if necessary
        self.offsets.update(new_offsets)
        self.count_since_commit += len(messages)
        self._auto_commit()

        return messages

########NEW FILE########
__FILENAME__ = partitioner
from itertools import cycle


class Partitioner(object):
    """
    Base class for a partitioner
    """
    def __init__(self, partitions):
        """
        Initialize the partitioner

        partitions - A list of available partitions (during startup)
        """
        self.partitions = partitions

    def partition(self, key, partitions):
        """
        Takes a string key and num_partitions as argument and returns
        a partition to be used for the message

        partitions - The list of partitions is passed in every call. This
                     may look like an overhead, but it will be useful
                     (in future) when we handle cases like rebalancing
        """
        raise NotImplementedError('partition function has to be implemented')


class RoundRobinPartitioner(Partitioner):
    """
    Implements a round robin partitioner which sends data to partitions
    in a round robin fashion
    """
    def __init__(self, partitions):
        super(RoundRobinPartitioner, self).__init__(partitions)
        self.iterpart = cycle(partitions)

    def _set_partitions(self, partitions):
        self.partitions = partitions
        self.iterpart = cycle(partitions)

    def partition(self, key, partitions):
        # Refresh the partition list if necessary
        if self.partitions != partitions:
            self._set_partitions(partitions)

        return self.iterpart.next()


class HashedPartitioner(Partitioner):
    """
    Implements a partitioner which selects the target partition based on
    the hash of the key
    """
    def partition(self, key, partitions):
        size = len(partitions)
        idx = hash(key) % size

        return partitions[idx]

########NEW FILE########
__FILENAME__ = producer
from __future__ import absolute_import

import logging
import time
import random

from Queue import Empty
from collections import defaultdict
from itertools import cycle
from multiprocessing import Queue, Process

from kafka.common import (
    ProduceRequest, TopicAndPartition, UnsupportedCodecError
)
from kafka.partitioner import HashedPartitioner
from kafka.protocol import CODEC_NONE, ALL_CODECS, create_message_set

log = logging.getLogger("kafka")

BATCH_SEND_DEFAULT_INTERVAL = 20
BATCH_SEND_MSG_COUNT = 20

STOP_ASYNC_PRODUCER = -1


def _send_upstream(queue, client, codec, batch_time, batch_size,
                   req_acks, ack_timeout):
    """
    Listen on the queue for a specified number of messages or till
    a specified timeout and send them upstream to the brokers in one
    request

    NOTE: Ideally, this should have been a method inside the Producer
    class. However, multiprocessing module has issues in windows. The
    functionality breaks unless this function is kept outside of a class
    """
    stop = False
    client.reinit()

    while not stop:
        timeout = batch_time
        count = batch_size
        send_at = time.time() + timeout
        msgset = defaultdict(list)

        # Keep fetching till we gather enough messages or a
        # timeout is reached
        while count > 0 and timeout >= 0:
            try:
                topic_partition, msg = queue.get(timeout=timeout)

            except Empty:
                break

            # Check if the controller has requested us to stop
            if topic_partition == STOP_ASYNC_PRODUCER:
                stop = True
                break

            # Adjust the timeout to match the remaining period
            count -= 1
            timeout = send_at - time.time()
            msgset[topic_partition].append(msg)

        # Send collected requests upstream
        reqs = []
        for topic_partition, msg in msgset.items():
            messages = create_message_set(msg, codec)
            req = ProduceRequest(topic_partition.topic,
                                 topic_partition.partition,
                                 messages)
            reqs.append(req)

        try:
            client.send_produce_request(reqs,
                                        acks=req_acks,
                                        timeout=ack_timeout)
        except Exception:
            log.exception("Unable to send message")


class Producer(object):
    """
    Base class to be used by producers

    Params:
    client - The Kafka client instance to use
    async - If set to true, the messages are sent asynchronously via another
            thread (process). We will not wait for a response to these
    req_acks - A value indicating the acknowledgements that the server must
               receive before responding to the request
    ack_timeout - Value (in milliseconds) indicating a timeout for waiting
                  for an acknowledgement
    batch_send - If True, messages are send in batches
    batch_send_every_n - If set, messages are send in batches of this size
    batch_send_every_t - If set, messages are send after this timeout
    """

    ACK_NOT_REQUIRED = 0            # No ack is required
    ACK_AFTER_LOCAL_WRITE = 1       # Send response after it is written to log
    ACK_AFTER_CLUSTER_COMMIT = -1   # Send response after data is committed

    DEFAULT_ACK_TIMEOUT = 1000

    def __init__(self, client, async=False,
                 req_acks=ACK_AFTER_LOCAL_WRITE,
                 ack_timeout=DEFAULT_ACK_TIMEOUT,
                 codec=None,
                 batch_send=False,
                 batch_send_every_n=BATCH_SEND_MSG_COUNT,
                 batch_send_every_t=BATCH_SEND_DEFAULT_INTERVAL):

        if batch_send:
            async = True
            assert batch_send_every_n > 0
            assert batch_send_every_t > 0
        else:
            batch_send_every_n = 1
            batch_send_every_t = 3600

        self.client = client
        self.async = async
        self.req_acks = req_acks
        self.ack_timeout = ack_timeout

        if codec is None:
            codec = CODEC_NONE
        elif codec not in ALL_CODECS:
            raise UnsupportedCodecError("Codec 0x%02x unsupported" % codec)

        self.codec = codec

        if self.async:
            self.queue = Queue()  # Messages are sent through this queue
            self.proc = Process(target=_send_upstream,
                                args=(self.queue,
                                      self.client.copy(),
                                      self.codec,
                                      batch_send_every_t,
                                      batch_send_every_n,
                                      self.req_acks,
                                      self.ack_timeout))

            # Process will die if main thread exits
            self.proc.daemon = True
            self.proc.start()

    def send_messages(self, topic, partition, *msg):
        """
        Helper method to send produce requests
        """
        if self.async:
            for m in msg:
                self.queue.put((TopicAndPartition(topic, partition), m))
            resp = []
        else:
            messages = create_message_set(msg, self.codec)
            req = ProduceRequest(topic, partition, messages)
            try:
                resp = self.client.send_produce_request([req], acks=self.req_acks,
                                                        timeout=self.ack_timeout)
            except Exception:
                log.exception("Unable to send messages")
                raise
        return resp

    def stop(self, timeout=1):
        """
        Stop the producer. Optionally wait for the specified timeout before
        forcefully cleaning up.
        """
        if self.async:
            self.queue.put((STOP_ASYNC_PRODUCER, None))
            self.proc.join(timeout)

            if self.proc.is_alive():
                self.proc.terminate()


class SimpleProducer(Producer):
    """
    A simple, round-robin producer. Each message goes to exactly one partition

    Params:
    client - The Kafka client instance to use
    async - If True, the messages are sent asynchronously via another
            thread (process). We will not wait for a response to these
    req_acks - A value indicating the acknowledgements that the server must
               receive before responding to the request
    ack_timeout - Value (in milliseconds) indicating a timeout for waiting
                  for an acknowledgement
    batch_send - If True, messages are send in batches
    batch_send_every_n - If set, messages are send in batches of this size
    batch_send_every_t - If set, messages are send after this timeout
    random_start - If true, randomize the initial partition which the
                   the first message block will be published to, otherwise
                   if false, the first message block will always publish 
                   to partition 0 before cycling through each partition
    """
    def __init__(self, client, async=False,
                 req_acks=Producer.ACK_AFTER_LOCAL_WRITE,
                 ack_timeout=Producer.DEFAULT_ACK_TIMEOUT,
                 codec=None,
                 batch_send=False,
                 batch_send_every_n=BATCH_SEND_MSG_COUNT,
                 batch_send_every_t=BATCH_SEND_DEFAULT_INTERVAL,
                 random_start=False):
        self.partition_cycles = {}
        self.random_start = random_start
        super(SimpleProducer, self).__init__(client, async, req_acks,
                                             ack_timeout, codec, batch_send,
                                             batch_send_every_n,
                                             batch_send_every_t)

    def _next_partition(self, topic):
        if topic not in self.partition_cycles:
            if topic not in self.client.topic_partitions:
                self.client.load_metadata_for_topics(topic)
            self.partition_cycles[topic] = cycle(self.client.topic_partitions[topic])

            # Randomize the initial partition that is returned
            if self.random_start:
                num_partitions = len(self.client.topic_partitions[topic])
                for _ in xrange(random.randint(0, num_partitions-1)):
                    self.partition_cycles[topic].next()

        return self.partition_cycles[topic].next()

    def send_messages(self, topic, *msg):
        partition = self._next_partition(topic)
        return super(SimpleProducer, self).send_messages(topic, partition, *msg)

    def __repr__(self):
        return '<SimpleProducer batch=%s>' % self.async


class KeyedProducer(Producer):
    """
    A producer which distributes messages to partitions based on the key

    Args:
    client - The kafka client instance
    partitioner - A partitioner class that will be used to get the partition
        to send the message to. Must be derived from Partitioner
    async - If True, the messages are sent asynchronously via another
            thread (process). We will not wait for a response to these
    ack_timeout - Value (in milliseconds) indicating a timeout for waiting
                  for an acknowledgement
    batch_send - If True, messages are send in batches
    batch_send_every_n - If set, messages are send in batches of this size
    batch_send_every_t - If set, messages are send after this timeout
    """
    def __init__(self, client, partitioner=None, async=False,
                 req_acks=Producer.ACK_AFTER_LOCAL_WRITE,
                 ack_timeout=Producer.DEFAULT_ACK_TIMEOUT,
                 codec=None,
                 batch_send=False,
                 batch_send_every_n=BATCH_SEND_MSG_COUNT,
                 batch_send_every_t=BATCH_SEND_DEFAULT_INTERVAL):
        if not partitioner:
            partitioner = HashedPartitioner
        self.partitioner_class = partitioner
        self.partitioners = {}

        super(KeyedProducer, self).__init__(client, async, req_acks,
                                            ack_timeout, codec, batch_send,
                                            batch_send_every_n,
                                            batch_send_every_t)

    def _next_partition(self, topic, key):
        if topic not in self.partitioners:
            if topic not in self.client.topic_partitions:
                self.client.load_metadata_for_topics(topic)
            self.partitioners[topic] = \
                self.partitioner_class(self.client.topic_partitions[topic])
        partitioner = self.partitioners[topic]
        return partitioner.partition(key, self.client.topic_partitions[topic])

    def send(self, topic, key, msg):
        partition = self._next_partition(topic, key)
        return self.send_messages(topic, partition, msg)

    def __repr__(self):
        return '<KeyedProducer batch=%s>' % self.async

########NEW FILE########
__FILENAME__ = protocol
import logging
import struct
import zlib

from kafka.codec import (
    gzip_encode, gzip_decode, snappy_encode, snappy_decode
)
from kafka.common import (
    BrokerMetadata, PartitionMetadata, Message, OffsetAndMessage,
    ProduceResponse, FetchResponse, OffsetResponse,
    OffsetCommitResponse, OffsetFetchResponse, ProtocolError,
    BufferUnderflowError, ChecksumError, ConsumerFetchSizeTooSmall,
    UnsupportedCodecError
)
from kafka.util import (
    read_short_string, read_int_string, relative_unpack,
    write_short_string, write_int_string, group_by_topic_and_partition
)

log = logging.getLogger("kafka")

ATTRIBUTE_CODEC_MASK = 0x03
CODEC_NONE = 0x00
CODEC_GZIP = 0x01
CODEC_SNAPPY = 0x02
ALL_CODECS = (CODEC_NONE, CODEC_GZIP, CODEC_SNAPPY)


class KafkaProtocol(object):
    """
    Class to encapsulate all of the protocol encoding/decoding.
    This class does not have any state associated with it, it is purely
    for organization.
    """
    PRODUCE_KEY = 0
    FETCH_KEY = 1
    OFFSET_KEY = 2
    METADATA_KEY = 3
    OFFSET_COMMIT_KEY = 8
    OFFSET_FETCH_KEY = 9

    ###################
    #   Private API   #
    ###################

    @classmethod
    def _encode_message_header(cls, client_id, correlation_id, request_key):
        """
        Encode the common request envelope
        """
        return struct.pack('>hhih%ds' % len(client_id),
                           request_key,          # ApiKey
                           0,                    # ApiVersion
                           correlation_id,       # CorrelationId
                           len(client_id),       # ClientId size
                           client_id)            # ClientId

    @classmethod
    def _encode_message_set(cls, messages):
        """
        Encode a MessageSet. Unlike other arrays in the protocol,
        MessageSets are not length-prefixed

        Format
        ======
        MessageSet => [Offset MessageSize Message]
          Offset => int64
          MessageSize => int32
        """
        message_set = ""
        for message in messages:
            encoded_message = KafkaProtocol._encode_message(message)
            message_set += struct.pack('>qi%ds' % len(encoded_message), 0, len(encoded_message), encoded_message)
        return message_set

    @classmethod
    def _encode_message(cls, message):
        """
        Encode a single message.

        The magic number of a message is a format version number.
        The only supported magic number right now is zero

        Format
        ======
        Message => Crc MagicByte Attributes Key Value
          Crc => int32
          MagicByte => int8
          Attributes => int8
          Key => bytes
          Value => bytes
        """
        if message.magic == 0:
            msg = struct.pack('>BB', message.magic, message.attributes)
            msg += write_int_string(message.key)
            msg += write_int_string(message.value)
            crc = zlib.crc32(msg)
            msg = struct.pack('>i%ds' % len(msg), crc, msg)
        else:
            raise ProtocolError("Unexpected magic number: %d" % message.magic)
        return msg

    @classmethod
    def _decode_message_set_iter(cls, data):
        """
        Iteratively decode a MessageSet

        Reads repeated elements of (offset, message), calling decode_message
        to decode a single message. Since compressed messages contain futher
        MessageSets, these two methods have been decoupled so that they may
        recurse easily.
        """
        cur = 0
        read_message = False
        while cur < len(data):
            try:
                ((offset, ), cur) = relative_unpack('>q', data, cur)
                (msg, cur) = read_int_string(data, cur)
                for (offset, message) in KafkaProtocol._decode_message(msg, offset):
                    read_message = True
                    yield OffsetAndMessage(offset, message)
            except BufferUnderflowError:
                # NOTE: Not sure this is correct error handling:
                # Is it possible to get a BUE if the message set is somewhere
                # in the middle of the fetch response? If so, we probably have
                # an issue that's not fetch size too small.
                # Aren't we ignoring errors if we fail to unpack data by
                # raising StopIteration()?
                # If _decode_message() raises a ChecksumError, couldn't that
                # also be due to the fetch size being too small?
                if read_message is False:
                    # If we get a partial read of a message, but haven't
                    # yielded anything there's a problem
                    raise ConsumerFetchSizeTooSmall()
                else:
                    raise StopIteration()

    @classmethod
    def _decode_message(cls, data, offset):
        """
        Decode a single Message

        The only caller of this method is decode_message_set_iter.
        They are decoupled to support nested messages (compressed MessageSets).
        The offset is actually read from decode_message_set_iter (it is part
        of the MessageSet payload).
        """
        ((crc, magic, att), cur) = relative_unpack('>iBB', data, 0)
        if crc != zlib.crc32(data[4:]):
            raise ChecksumError("Message checksum failed")

        (key, cur) = read_int_string(data, cur)
        (value, cur) = read_int_string(data, cur)

        codec = att & ATTRIBUTE_CODEC_MASK

        if codec == CODEC_NONE:
            yield (offset, Message(magic, att, key, value))

        elif codec == CODEC_GZIP:
            gz = gzip_decode(value)
            for (offset, msg) in KafkaProtocol._decode_message_set_iter(gz):
                yield (offset, msg)

        elif codec == CODEC_SNAPPY:
            snp = snappy_decode(value)
            for (offset, msg) in KafkaProtocol._decode_message_set_iter(snp):
                yield (offset, msg)

    ##################
    #   Public API   #
    ##################

    @classmethod
    def encode_produce_request(cls, client_id, correlation_id,
                               payloads=None, acks=1, timeout=1000):
        """
        Encode some ProduceRequest structs

        Params
        ======
        client_id: string
        correlation_id: int
        payloads: list of ProduceRequest
        acks: How "acky" you want the request to be
            0: immediate response
            1: written to disk by the leader
            2+: waits for this many number of replicas to sync
            -1: waits for all replicas to be in sync
        timeout: Maximum time the server will wait for acks from replicas.
                 This is _not_ a socket timeout
        """
        payloads = [] if payloads is None else payloads
        grouped_payloads = group_by_topic_and_partition(payloads)

        message = cls._encode_message_header(client_id, correlation_id,
                                             KafkaProtocol.PRODUCE_KEY)

        message += struct.pack('>hii', acks, timeout, len(grouped_payloads))

        for topic, topic_payloads in grouped_payloads.items():
            message += struct.pack('>h%dsi' % len(topic),
                                   len(topic), topic, len(topic_payloads))

            for partition, payload in topic_payloads.items():
                msg_set = KafkaProtocol._encode_message_set(payload.messages)
                message += struct.pack('>ii%ds' % len(msg_set), partition,
                                       len(msg_set), msg_set)

        return struct.pack('>i%ds' % len(message), len(message), message)

    @classmethod
    def decode_produce_response(cls, data):
        """
        Decode bytes to a ProduceResponse

        Params
        ======
        data: bytes to decode
        """
        ((correlation_id, num_topics), cur) = relative_unpack('>ii', data, 0)

        for i in range(num_topics):
            ((strlen,), cur) = relative_unpack('>h', data, cur)
            topic = data[cur:cur + strlen]
            cur += strlen
            ((num_partitions,), cur) = relative_unpack('>i', data, cur)
            for i in range(num_partitions):
                ((partition, error, offset), cur) = relative_unpack('>ihq',
                                                                    data, cur)

                yield ProduceResponse(topic, partition, error, offset)

    @classmethod
    def encode_fetch_request(cls, client_id, correlation_id, payloads=None,
                             max_wait_time=100, min_bytes=4096):
        """
        Encodes some FetchRequest structs

        Params
        ======
        client_id: string
        correlation_id: int
        payloads: list of FetchRequest
        max_wait_time: int, how long to block waiting on min_bytes of data
        min_bytes: int, the minimum number of bytes to accumulate before
                   returning the response
        """

        payloads = [] if payloads is None else payloads
        grouped_payloads = group_by_topic_and_partition(payloads)

        message = cls._encode_message_header(client_id, correlation_id,
                                             KafkaProtocol.FETCH_KEY)

        # -1 is the replica id
        message += struct.pack('>iiii', -1, max_wait_time, min_bytes,
                               len(grouped_payloads))

        for topic, topic_payloads in grouped_payloads.items():
            message += write_short_string(topic)
            message += struct.pack('>i', len(topic_payloads))
            for partition, payload in topic_payloads.items():
                message += struct.pack('>iqi', partition, payload.offset,
                                       payload.max_bytes)

        return struct.pack('>i%ds' % len(message), len(message), message)

    @classmethod
    def decode_fetch_response(cls, data):
        """
        Decode bytes to a FetchResponse

        Params
        ======
        data: bytes to decode
        """
        ((correlation_id, num_topics), cur) = relative_unpack('>ii', data, 0)

        for i in range(num_topics):
            (topic, cur) = read_short_string(data, cur)
            ((num_partitions,), cur) = relative_unpack('>i', data, cur)

            for i in range(num_partitions):
                ((partition, error, highwater_mark_offset), cur) = \
                    relative_unpack('>ihq', data, cur)

                (message_set, cur) = read_int_string(data, cur)

                yield FetchResponse(
                    topic, partition, error,
                    highwater_mark_offset,
                    KafkaProtocol._decode_message_set_iter(message_set))

    @classmethod
    def encode_offset_request(cls, client_id, correlation_id, payloads=None):
        payloads = [] if payloads is None else payloads
        grouped_payloads = group_by_topic_and_partition(payloads)

        message = cls._encode_message_header(client_id, correlation_id,
                                             KafkaProtocol.OFFSET_KEY)

        # -1 is the replica id
        message += struct.pack('>ii', -1, len(grouped_payloads))

        for topic, topic_payloads in grouped_payloads.items():
            message += write_short_string(topic)
            message += struct.pack('>i', len(topic_payloads))

            for partition, payload in topic_payloads.items():
                message += struct.pack('>iqi', partition, payload.time,
                                       payload.max_offsets)

        return struct.pack('>i%ds' % len(message), len(message), message)

    @classmethod
    def decode_offset_response(cls, data):
        """
        Decode bytes to an OffsetResponse

        Params
        ======
        data: bytes to decode
        """
        ((correlation_id, num_topics), cur) = relative_unpack('>ii', data, 0)

        for i in range(num_topics):
            (topic, cur) = read_short_string(data, cur)
            ((num_partitions,), cur) = relative_unpack('>i', data, cur)

            for i in range(num_partitions):
                ((partition, error, num_offsets,), cur) = \
                    relative_unpack('>ihi', data, cur)

                offsets = []
                for j in range(num_offsets):
                    ((offset,), cur) = relative_unpack('>q', data, cur)
                    offsets.append(offset)

                yield OffsetResponse(topic, partition, error, tuple(offsets))

    @classmethod
    def encode_metadata_request(cls, client_id, correlation_id, topics=None):
        """
        Encode a MetadataRequest

        Params
        ======
        client_id: string
        correlation_id: int
        topics: list of strings
        """
        topics = [] if topics is None else topics
        message = cls._encode_message_header(client_id, correlation_id,
                                             KafkaProtocol.METADATA_KEY)

        message += struct.pack('>i', len(topics))

        for topic in topics:
            message += struct.pack('>h%ds' % len(topic), len(topic), topic)

        return write_int_string(message)

    @classmethod
    def decode_metadata_response(cls, data):
        """
        Decode bytes to a MetadataResponse

        Params
        ======
        data: bytes to decode
        """
        ((correlation_id, numbrokers), cur) = relative_unpack('>ii', data, 0)

        # Broker info
        brokers = {}
        for i in range(numbrokers):
            ((nodeId, ), cur) = relative_unpack('>i', data, cur)
            (host, cur) = read_short_string(data, cur)
            ((port,), cur) = relative_unpack('>i', data, cur)
            brokers[nodeId] = BrokerMetadata(nodeId, host, port)

        # Topic info
        ((num_topics,), cur) = relative_unpack('>i', data, cur)
        topic_metadata = {}

        for i in range(num_topics):
            # NOTE: topic_error is discarded. Should probably be returned with
            # the topic metadata.
            ((topic_error,), cur) = relative_unpack('>h', data, cur)
            (topic_name, cur) = read_short_string(data, cur)
            ((num_partitions,), cur) = relative_unpack('>i', data, cur)
            partition_metadata = {}

            for j in range(num_partitions):
                # NOTE: partition_error_code is discarded. Should probably be
                # returned with the partition metadata.
                ((partition_error_code, partition, leader, numReplicas), cur) = \
                    relative_unpack('>hiii', data, cur)

                (replicas, cur) = relative_unpack(
                    '>%di' % numReplicas, data, cur)

                ((num_isr,), cur) = relative_unpack('>i', data, cur)
                (isr, cur) = relative_unpack('>%di' % num_isr, data, cur)

                partition_metadata[partition] = \
                    PartitionMetadata(
                        topic_name, partition, leader, replicas, isr)

            topic_metadata[topic_name] = partition_metadata

        return brokers, topic_metadata

    @classmethod
    def encode_offset_commit_request(cls, client_id, correlation_id,
                                     group, payloads):
        """
        Encode some OffsetCommitRequest structs

        Params
        ======
        client_id: string
        correlation_id: int
        group: string, the consumer group you are committing offsets for
        payloads: list of OffsetCommitRequest
        """
        grouped_payloads = group_by_topic_and_partition(payloads)

        message = cls._encode_message_header(client_id, correlation_id,
                                             KafkaProtocol.OFFSET_COMMIT_KEY)
        message += write_short_string(group)
        message += struct.pack('>i', len(grouped_payloads))

        for topic, topic_payloads in grouped_payloads.items():
            message += write_short_string(topic)
            message += struct.pack('>i', len(topic_payloads))

            for partition, payload in topic_payloads.items():
                message += struct.pack('>iq', partition, payload.offset)
                message += write_short_string(payload.metadata)

        return struct.pack('>i%ds' % len(message), len(message), message)

    @classmethod
    def decode_offset_commit_response(cls, data):
        """
        Decode bytes to an OffsetCommitResponse

        Params
        ======
        data: bytes to decode
        """
        ((correlation_id,), cur) = relative_unpack('>i', data, 0)
        ((num_topics,), cur) = relative_unpack('>i', data, cur)

        for i in xrange(num_topics):
            (topic, cur) = read_short_string(data, cur)
            ((num_partitions,), cur) = relative_unpack('>i', data, cur)

            for i in xrange(num_partitions):
                ((partition, error), cur) = relative_unpack('>ih', data, cur)
                yield OffsetCommitResponse(topic, partition, error)

    @classmethod
    def encode_offset_fetch_request(cls, client_id, correlation_id,
                                    group, payloads):
        """
        Encode some OffsetFetchRequest structs

        Params
        ======
        client_id: string
        correlation_id: int
        group: string, the consumer group you are fetching offsets for
        payloads: list of OffsetFetchRequest
        """
        grouped_payloads = group_by_topic_and_partition(payloads)
        message = cls._encode_message_header(client_id, correlation_id,
                                             KafkaProtocol.OFFSET_FETCH_KEY)

        message += write_short_string(group)
        message += struct.pack('>i', len(grouped_payloads))

        for topic, topic_payloads in grouped_payloads.items():
            message += write_short_string(topic)
            message += struct.pack('>i', len(topic_payloads))

            for partition, payload in topic_payloads.items():
                message += struct.pack('>i', partition)

        return struct.pack('>i%ds' % len(message), len(message), message)

    @classmethod
    def decode_offset_fetch_response(cls, data):
        """
        Decode bytes to an OffsetFetchResponse

        Params
        ======
        data: bytes to decode
        """

        ((correlation_id,), cur) = relative_unpack('>i', data, 0)
        ((num_topics,), cur) = relative_unpack('>i', data, cur)

        for i in range(num_topics):
            (topic, cur) = read_short_string(data, cur)
            ((num_partitions,), cur) = relative_unpack('>i', data, cur)

            for i in range(num_partitions):
                ((partition, offset), cur) = relative_unpack('>iq', data, cur)
                (metadata, cur) = read_short_string(data, cur)
                ((error,), cur) = relative_unpack('>h', data, cur)

                yield OffsetFetchResponse(topic, partition, offset,
                                          metadata, error)


def create_message(payload, key=None):
    """
    Construct a Message

    Params
    ======
    payload: bytes, the payload to send to Kafka
    key: bytes, a key used for partition routing (optional)
    """
    return Message(0, 0, key, payload)


def create_gzip_message(payloads, key=None):
    """
    Construct a Gzipped Message containing multiple Messages

    The given payloads will be encoded, compressed, and sent as a single atomic
    message to Kafka.

    Params
    ======
    payloads: list(bytes), a list of payload to send be sent to Kafka
    key: bytes, a key used for partition routing (optional)
    """
    message_set = KafkaProtocol._encode_message_set(
        [create_message(payload) for payload in payloads])

    gzipped = gzip_encode(message_set)
    codec = ATTRIBUTE_CODEC_MASK & CODEC_GZIP

    return Message(0, 0x00 | codec, key, gzipped)


def create_snappy_message(payloads, key=None):
    """
    Construct a Snappy Message containing multiple Messages

    The given payloads will be encoded, compressed, and sent as a single atomic
    message to Kafka.

    Params
    ======
    payloads: list(bytes), a list of payload to send be sent to Kafka
    key: bytes, a key used for partition routing (optional)
    """
    message_set = KafkaProtocol._encode_message_set(
        [create_message(payload) for payload in payloads])

    snapped = snappy_encode(message_set)
    codec = ATTRIBUTE_CODEC_MASK & CODEC_SNAPPY

    return Message(0, 0x00 | codec, key, snapped)


def create_message_set(messages, codec=CODEC_NONE):
    """Create a message set using the given codec.

    If codec is CODEC_NONE, return a list of raw Kafka messages. Otherwise,
    return a list containing a single codec-encoded message.
    """
    if codec == CODEC_NONE:
        return [create_message(m) for m in messages]
    elif codec == CODEC_GZIP:
        return [create_gzip_message(messages)]
    elif codec == CODEC_SNAPPY:
        return [create_snappy_message(messages)]
    else:
        raise UnsupportedCodecError("Codec 0x%02x unsupported" % codec)

########NEW FILE########
__FILENAME__ = queue
from __future__ import absolute_import

from copy import copy
import logging
from multiprocessing import Process, Queue, Event
from Queue import Empty
import time

from kafka.client import KafkaClient, FetchRequest, ProduceRequest

log = logging.getLogger("kafka")

raise NotImplementedError("Still need to refactor this class")


class KafkaConsumerProcess(Process):
    def __init__(self, client, topic, partition, out_queue, barrier,
                 consumer_fetch_size=1024, consumer_sleep=200):
        self.client = copy(client)
        self.topic = topic
        self.partition = partition
        self.out_queue = out_queue
        self.barrier = barrier
        self.consumer_fetch_size = consumer_fetch_size
        self.consumer_sleep = consumer_sleep / 1000.
        log.info("Initializing %s" % self)
        Process.__init__(self)

    def __str__(self):
        return "[KafkaConsumerProcess: topic=%s, \
            partition=%s, sleep=%s]" % \
            (self.topic, self.partition, self.consumer_sleep)

    def run(self):
        self.barrier.wait()
        log.info("Starting %s" % self)
        fetchRequest = FetchRequest(self.topic, self.partition,
                                    offset=0, size=self.consumer_fetch_size)

        while True:
            if self.barrier.is_set() is False:
                log.info("Shutdown %s" % self)
                self.client.close()
                break

            lastOffset = fetchRequest.offset
            (messages, fetchRequest) = self.client.get_message_set(fetchRequest)

            if fetchRequest.offset == lastOffset:
                log.debug("No more data for this partition, "
                          "sleeping a bit (200ms)")
                time.sleep(self.consumer_sleep)
                continue

            for message in messages:
                self.out_queue.put(message)


class KafkaProducerProcess(Process):
    def __init__(self, client, topic, in_queue, barrier,
                 producer_flush_buffer=500,
                 producer_flush_timeout=2000,
                 producer_timeout=100):

        self.client = copy(client)
        self.topic = topic
        self.in_queue = in_queue
        self.barrier = barrier
        self.producer_flush_buffer = producer_flush_buffer
        self.producer_flush_timeout = producer_flush_timeout / 1000.
        self.producer_timeout = producer_timeout / 1000.
        log.info("Initializing %s" % self)
        Process.__init__(self)

    def __str__(self):
        return "[KafkaProducerProcess: topic=%s, \
            flush_buffer=%s, flush_timeout=%s, timeout=%s]" % \
            (self.topic,
                self.producer_flush_buffer,
                self.producer_flush_timeout,
                self.producer_timeout)

    def run(self):
        self.barrier.wait()
        log.info("Starting %s" % self)
        messages = []
        last_produce = time.time()

        def flush(messages):
            self.client.send_message_set(ProduceRequest(self.topic, -1,
                                                        messages))
            del messages[:]

        while True:
            if self.barrier.is_set() is False:
                log.info("Shutdown %s, flushing messages" % self)
                flush(messages)
                self.client.close()
                break

            if len(messages) > self.producer_flush_buffer:
                log.debug("Message count threshold reached. Flushing messages")
                flush(messages)
                last_produce = time.time()

            elif (time.time() - last_produce) > self.producer_flush_timeout:
                log.debug("Producer timeout reached. Flushing messages")
                flush(messages)
                last_produce = time.time()

            try:
                msg = KafkaClient.create_message(
                    self.in_queue.get(True, self.producer_timeout))
                messages.append(msg)

            except Empty:
                continue


class KafkaQueue(object):
    def __init__(self, client, topic, partitions,
                 producer_config=None, consumer_config=None):
        """
        KafkaQueue a Queue-like object backed by a Kafka producer and some
        number of consumers

        Messages are eagerly loaded by the consumer in batches of size
        consumer_fetch_size.
        Messages are buffered in the producer thread until
        producer_flush_timeout or producer_flush_buffer is reached.

        Params
        ======
        client: KafkaClient object
        topic: str, the topic name
        partitions: list of ints, the partions to consume from
        producer_config: dict, see below
        consumer_config: dict, see below

        Consumer Config
        ===============
        consumer_fetch_size: int, number of bytes to fetch in one call
                             to Kafka. Default is 1024
        consumer_sleep: int, time in milliseconds a consumer should sleep
                        when it reaches the end of a partition. Default is 200

        Producer Config
        ===============
        producer_timeout: int, time in milliseconds a producer should
                          wait for messages to enqueue for producing.
                          Default is 100
        producer_flush_timeout: int, time in milliseconds a producer
                                should allow messages to accumulate before
                                sending to Kafka. Default is 2000
        producer_flush_buffer: int, number of messages a producer should
                               allow to accumulate. Default is 500

        """
        producer_config = {} if producer_config is None else producer_config
        consumer_config = {} if consumer_config is None else consumer_config

        self.in_queue = Queue()
        self.out_queue = Queue()
        self.consumers = []
        self.barrier = Event()

        # Initialize and start consumer threads
        for partition in partitions:
            consumer = KafkaConsumerProcess(client, topic, partition,
                                            self.in_queue, self.barrier,
                                            **consumer_config)
            consumer.start()
            self.consumers.append(consumer)

        # Initialize and start producer thread
        self.producer = KafkaProducerProcess(client, topic, self.out_queue,
                                             self.barrier, **producer_config)
        self.producer.start()

        # Trigger everything to start
        self.barrier.set()

    def get(self, block=True, timeout=None):
        """
        Consume a message from Kafka

        Params
        ======
        block: boolean, default True
        timeout: int, number of seconds to wait when blocking, default None

        Returns
        =======
        msg: str, the payload from Kafka
        """
        return self.in_queue.get(block, timeout).payload

    def put(self, msg, block=True, timeout=None):
        """
        Send a message to Kafka

        Params
        ======
        msg: std, the message to send
        block: boolean, default True
        timeout: int, number of seconds to wait when blocking, default None
        """
        self.out_queue.put(msg, block, timeout)

    def close(self):
        """
        Close the internal queues and Kafka consumers/producer
        """
        self.in_queue.close()
        self.out_queue.close()
        self.barrier.clear()
        self.producer.join()
        for consumer in self.consumers:
            consumer.join()

########NEW FILE########
__FILENAME__ = util
import collections
import struct
import sys
from threading import Thread, Event

from kafka.common import BufferUnderflowError


def write_int_string(s):
    if s is None:
        return struct.pack('>i', -1)
    else:
        return struct.pack('>i%ds' % len(s), len(s), s)


def write_short_string(s):
    if s is None:
        return struct.pack('>h', -1)
    elif len(s) > 32767 and sys.version < (2,7):
        # Python 2.6 issues a deprecation warning instead of a struct error
        raise struct.error(len(s))
    else:
        return struct.pack('>h%ds' % len(s), len(s), s)


def read_short_string(data, cur):
    if len(data) < cur + 2:
        raise BufferUnderflowError("Not enough data left")

    (strlen,) = struct.unpack('>h', data[cur:cur + 2])
    if strlen == -1:
        return None, cur + 2

    cur += 2
    if len(data) < cur + strlen:
        raise BufferUnderflowError("Not enough data left")

    out = data[cur:cur + strlen]
    return out, cur + strlen


def read_int_string(data, cur):
    if len(data) < cur + 4:
        raise BufferUnderflowError(
            "Not enough data left to read string len (%d < %d)" %
            (len(data), cur + 4))

    (strlen,) = struct.unpack('>i', data[cur:cur + 4])
    if strlen == -1:
        return None, cur + 4

    cur += 4
    if len(data) < cur + strlen:
        raise BufferUnderflowError("Not enough data left")

    out = data[cur:cur + strlen]
    return out, cur + strlen


def relative_unpack(fmt, data, cur):
    size = struct.calcsize(fmt)
    if len(data) < cur + size:
        raise BufferUnderflowError("Not enough data left")

    out = struct.unpack(fmt, data[cur:cur + size])
    return out, cur + size


def group_by_topic_and_partition(tuples):
    out = collections.defaultdict(dict)
    for t in tuples:
        out[t.topic][t.partition] = t
    return out


class ReentrantTimer(object):
    """
    A timer that can be restarted, unlike threading.Timer
    (although this uses threading.Timer)

    t: timer interval in milliseconds
    fn: a callable to invoke
    args: tuple of args to be passed to function
    kwargs: keyword arguments to be passed to function
    """
    def __init__(self, t, fn, *args, **kwargs):

        if t <= 0:
            raise ValueError('Invalid timeout value')

        if not callable(fn):
            raise ValueError('fn must be callable')

        self.thread = None
        self.t = t / 1000.0
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.active = None

    def _timer(self, active):
        while not active.wait(self.t):
            self.fn(*self.args, **self.kwargs)

    def start(self):
        if self.thread is not None:
            self.stop()

        self.active = Event()
        self.thread = Thread(target=self._timer, args=(self.active,))
        self.thread.daemon = True  # So the app exits when main thread exits
        self.thread.start()

    def stop(self):
        if self.thread is None:
            return

        self.active.set()
        self.thread.join(self.t + 1)
        self.timer = None

########NEW FILE########
__FILENAME__ = load_example
#!/usr/bin/env python
import threading, logging, time, collections

from kafka.client import KafkaClient
from kafka.consumer import SimpleConsumer
from kafka.producer import SimpleProducer

msg_size = 524288

class Producer(threading.Thread):
    daemon = True
    big_msg = "1" * msg_size

    def run(self):
        client = KafkaClient("localhost:9092")
        producer = SimpleProducer(client)
        self.sent = 0

        while True:
            producer.send_messages('my-topic', self.big_msg)
            self.sent += 1


class Consumer(threading.Thread):
    daemon = True

    def run(self):
        client = KafkaClient("localhost:9092")
        consumer = SimpleConsumer(client, "test-group", "my-topic",
            max_buffer_size = None,
        )
        self.valid = 0
        self.invalid = 0

        for message in consumer:
            if len(message.message.value) == msg_size:
                self.valid += 1
            else:
                self.invalid += 1

def main():
    threads = [
        Producer(),
        Consumer()
    ]

    for t in threads:
        t.start()

    time.sleep(10)
    print 'Messages sent: %d' % threads[0].sent
    print 'Messages recvd: %d' % threads[1].valid
    print 'Messages invalid: %d' % threads[1].invalid

if __name__ == "__main__":
    logging.basicConfig(
        format='%(asctime)s.%(msecs)s:%(name)s:%(thread)d:%(levelname)s:%(process)d:%(message)s',
        level=logging.DEBUG
        )
    main()

########NEW FILE########
__FILENAME__ = fixtures
import logging
import glob
import os
import shutil
import subprocess
import tempfile
import uuid

from urlparse import urlparse
from service import ExternalService, SpawnedService
from testutil import get_open_port

class Fixture(object):
    kafka_version = os.environ.get('KAFKA_VERSION', '0.8.0')
    scala_version = os.environ.get("SCALA_VERSION", '2.8.0')
    project_root = os.environ.get('PROJECT_ROOT', os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    kafka_root = os.environ.get("KAFKA_ROOT", os.path.join(project_root, 'servers', kafka_version, "kafka-src"))
    ivy_root = os.environ.get('IVY_ROOT', os.path.expanduser("~/.ivy2/cache"))

    @classmethod
    def test_resource(cls, filename):
        return os.path.join(cls.project_root, "servers", cls.kafka_version, "resources", filename)

    @classmethod
    def test_classpath(cls):
        # ./kafka-src/bin/kafka-run-class.sh is the authority.
        jars = ["."]

        # 0.8.0 build path, should contain the core jar and a deps jar
        jars.extend(glob.glob(cls.kafka_root + "/core/target/scala-%s/*.jar" % cls.scala_version))

        # 0.8.1 build path, should contain the core jar and several dep jars
        jars.extend(glob.glob(cls.kafka_root + "/core/build/libs/*.jar"))
        jars.extend(glob.glob(cls.kafka_root + "/core/build/dependant-libs-%s/*.jar" % cls.scala_version))

        jars = filter(os.path.exists, map(os.path.abspath, jars))
        return ":".join(jars)

    @classmethod
    def kafka_run_class_args(cls, *args):
        # ./kafka-src/bin/kafka-run-class.sh is the authority.
        result = ["java", "-Xmx512M", "-server"]
        result.append("-Dlog4j.configuration=file:%s" % cls.test_resource("log4j.properties"))
        result.append("-Dcom.sun.management.jmxremote")
        result.append("-Dcom.sun.management.jmxremote.authenticate=false")
        result.append("-Dcom.sun.management.jmxremote.ssl=false")
        result.append("-cp")
        result.append(cls.test_classpath())
        result.extend(args)
        return result

    @classmethod
    def render_template(cls, source_file, target_file, binding):
        with open(source_file, "r") as handle:
            template = handle.read()
        with open(target_file, "w") as handle:
            handle.write(template.format(**binding))


class ZookeeperFixture(Fixture):
    @classmethod
    def instance(cls):
        if "ZOOKEEPER_URI" in os.environ:
            parse = urlparse(os.environ["ZOOKEEPER_URI"])
            (host, port) = (parse.hostname, parse.port)
            fixture = ExternalService(host, port)
        else:
            (host, port) = ("127.0.0.1", get_open_port())
            fixture = cls(host, port)

        fixture.open()
        return fixture

    def __init__(self, host, port):
        self.host = host
        self.port = port

        self.tmp_dir = None
        self.child = None

    def out(self, message):
        logging.info("*** Zookeeper [%s:%d]: %s", self.host, self.port, message)

    def open(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.out("Running local instance...")
        logging.info("  host    = %s", self.host)
        logging.info("  port    = %s", self.port)
        logging.info("  tmp_dir = %s", self.tmp_dir)

        # Generate configs
        template = self.test_resource("zookeeper.properties")
        properties = os.path.join(self.tmp_dir, "zookeeper.properties")
        self.render_template(template, properties, vars(self))

        # Configure Zookeeper child process
        self.child = SpawnedService(self.kafka_run_class_args(
            "org.apache.zookeeper.server.quorum.QuorumPeerMain",
            properties
        ))

        # Party!
        self.out("Starting...")
        self.child.start()
        self.child.wait_for(r"Snapshotting")
        self.out("Done!")

    def close(self):
        self.out("Stopping...")
        self.child.stop()
        self.child = None
        self.out("Done!")
        shutil.rmtree(self.tmp_dir)


class KafkaFixture(Fixture):
    @classmethod
    def instance(cls, broker_id, zk_host, zk_port, zk_chroot=None, replicas=1, partitions=2):
        if zk_chroot is None:
            zk_chroot = "kafka-python_" + str(uuid.uuid4()).replace("-", "_")
        if "KAFKA_URI" in os.environ:
            parse = urlparse(os.environ["KAFKA_URI"])
            (host, port) = (parse.hostname, parse.port)
            fixture = ExternalService(host, port)
        else:
            (host, port) = ("127.0.0.1", get_open_port())
            fixture = KafkaFixture(host, port, broker_id, zk_host, zk_port, zk_chroot, replicas, partitions)
            fixture.open()
        return fixture

    def __init__(self, host, port, broker_id, zk_host, zk_port, zk_chroot, replicas=1, partitions=2):
        self.host = host
        self.port = port

        self.broker_id = broker_id

        self.zk_host = zk_host
        self.zk_port = zk_port
        self.zk_chroot = zk_chroot

        self.replicas   = replicas
        self.partitions = partitions

        self.tmp_dir = None
        self.child = None
        self.running = False

    def out(self, message):
        logging.info("*** Kafka [%s:%d]: %s", self.host, self.port, message)

    def open(self):
        if self.running:
            self.out("Instance already running")
            return

        self.tmp_dir = tempfile.mkdtemp()
        self.out("Running local instance...")
        logging.info("  host       = %s", self.host)
        logging.info("  port       = %s", self.port)
        logging.info("  broker_id  = %s", self.broker_id)
        logging.info("  zk_host    = %s", self.zk_host)
        logging.info("  zk_port    = %s", self.zk_port)
        logging.info("  zk_chroot  = %s", self.zk_chroot)
        logging.info("  replicas   = %s", self.replicas)
        logging.info("  partitions = %s", self.partitions)
        logging.info("  tmp_dir    = %s", self.tmp_dir)

        # Create directories
        os.mkdir(os.path.join(self.tmp_dir, "logs"))
        os.mkdir(os.path.join(self.tmp_dir, "data"))

        # Generate configs
        template = self.test_resource("kafka.properties")
        properties = os.path.join(self.tmp_dir, "kafka.properties")
        self.render_template(template, properties, vars(self))

        # Configure Kafka child process
        self.child = SpawnedService(self.kafka_run_class_args(
            "kafka.Kafka", properties
        ))

        # Party!
        self.out("Creating Zookeeper chroot node...")
        proc = subprocess.Popen(self.kafka_run_class_args(
                "org.apache.zookeeper.ZooKeeperMain",
                "-server", "%s:%d" % (self.zk_host, self.zk_port),
                "create", "/%s" % self.zk_chroot, "kafka-python"
            ),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)

        if proc.wait() != 0:
            self.out("Failed to create Zookeeper chroot node")
            self.out(proc.stdout)
            self.out(proc.stderr)
            raise RuntimeError("Failed to create Zookeeper chroot node")
        self.out("Done!")

        self.out("Starting...")
        self.child.start()
        self.child.wait_for(r"\[Kafka Server %d\], Started" % self.broker_id)
        self.out("Done!")
        self.running = True

    def close(self):
        if not self.running:
            self.out("Instance already stopped")
            return

        self.out("Stopping...")
        self.child.stop()
        self.child = None
        self.out("Done!")
        shutil.rmtree(self.tmp_dir)
        self.running = False

########NEW FILE########
__FILENAME__ = service
import logging
import re
import select
import subprocess
import sys
import threading
import time

__all__ = [
    'ExternalService',
    'SpawnedService',

]

class ExternalService(object):
    def __init__(self, host, port):
        print("Using already running service at %s:%d" % (host, port))
        self.host = host
        self.port = port

    def open(self):
        pass

    def close(self):
        pass


class SpawnedService(threading.Thread):
    def __init__(self, args=[]):
        threading.Thread.__init__(self)

        self.args = args
        self.captured_stdout = []
        self.captured_stderr = []

        self.should_die = threading.Event()

    def run(self):
        self.run_with_handles()

    def run_with_handles(self):
        self.child = subprocess.Popen(
            self.args,
            bufsize=1,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        alive = True

        while True:
            (rds, wds, xds) = select.select([self.child.stdout, self.child.stderr], [], [], 1)

            if self.child.stdout in rds:
                line = self.child.stdout.readline()
                self.captured_stdout.append(line)

            if self.child.stderr in rds:
                line = self.child.stderr.readline()
                self.captured_stderr.append(line)

            if self.should_die.is_set():
                self.child.terminate()
                alive = False

            poll_results = self.child.poll()
            if poll_results is not None:
                if not alive:
                    break
                else:
                    self.dump_logs()
                    raise RuntimeError("Subprocess has died. Aborting. (args=%s)" % ' '.join(str(x) for x in self.args))

    def dump_logs(self):
        logging.critical('stderr')
        for line in self.captured_stderr:
            logging.critical(line.rstrip())

        logging.critical('stdout')
        for line in self.captured_stdout:
            logging.critical(line.rstrip())

    def wait_for(self, pattern, timeout=10):
        t1 = time.time()
        while True:
            t2 = time.time()
            if t2 - t1 >= timeout:
                try:
                    self.child.kill()
                except:
                    logging.exception("Received exception when killing child process")
                self.dump_logs()

                raise RuntimeError("Waiting for %r timed out" % pattern)

            if re.search(pattern, '\n'.join(self.captured_stdout), re.IGNORECASE) is not None:
                return
            if re.search(pattern, '\n'.join(self.captured_stderr), re.IGNORECASE) is not None:
                return
            time.sleep(0.1)

    def start(self):
        threading.Thread.start(self)

    def stop(self):
        self.should_die.set()
        self.join()


########NEW FILE########
__FILENAME__ = testutil
import functools
import logging
import os
import random
import socket
import string
import time
import unittest2
import uuid

from kafka.common import OffsetRequest
from kafka import KafkaClient

__all__ = [
    'random_string',
    'ensure_topic_creation',
    'get_open_port',
    'kafka_versions',
    'KafkaIntegrationTestCase',
    'Timer',
]

def random_string(l):
    s = "".join(random.choice(string.letters) for i in xrange(l))
    return s

def kafka_versions(*versions):
    def kafka_versions(func):
        @functools.wraps(func)
        def wrapper(self):
            kafka_version = os.environ.get('KAFKA_VERSION')

            if not kafka_version:
                self.skipTest("no kafka version specified")
            elif 'all' not in versions and kafka_version not in versions:
                self.skipTest("unsupported kafka version")

            return func(self)
        return wrapper
    return kafka_versions

def ensure_topic_creation(client, topic_name, timeout = 30):
    start_time = time.time()

    client.load_metadata_for_topics(topic_name)
    while not client.has_metadata_for_topic(topic_name):
        if time.time() > start_time + timeout:
            raise Exception("Unable to create topic %s" % topic_name)
        client.load_metadata_for_topics(topic_name)
        time.sleep(1)

def get_open_port():
    sock = socket.socket()
    sock.bind(("", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port

class KafkaIntegrationTestCase(unittest2.TestCase):
    create_client = True
    topic = None

    def setUp(self):
        super(KafkaIntegrationTestCase, self).setUp()
        if not os.environ.get('KAFKA_VERSION'):
            return

        if not self.topic:
            self.topic = "%s-%s" % (self.id()[self.id().rindex(".") + 1:], random_string(10))

        if self.create_client:
            self.client = KafkaClient('%s:%d' % (self.server.host, self.server.port))

        ensure_topic_creation(self.client, self.topic)

        self._messages = {}

    def tearDown(self):
        super(KafkaIntegrationTestCase, self).tearDown()
        if not os.environ.get('KAFKA_VERSION'):
            return

        if self.create_client:
            self.client.close()

    def current_offset(self, topic, partition):
        offsets, = self.client.send_offset_request([ OffsetRequest(topic, partition, -1, 1) ])
        return offsets.offsets[0]

    def msgs(self, iterable):
        return [ self.msg(x) for x in iterable ]

    def msg(self, s):
        if s not in self._messages:
            self._messages[s] = '%s-%s-%s' % (s, self.id(), str(uuid.uuid4()))

        return self._messages[s]

class Timer(object):
    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, *args):
        self.end = time.time()
        self.interval = self.end - self.start

logging.basicConfig(level=logging.DEBUG)

########NEW FILE########
__FILENAME__ = test_client
import os
import random
import struct
import unittest2

from mock import MagicMock, patch

from kafka import KafkaClient
from kafka.common import (
    ProduceRequest, BrokerMetadata, PartitionMetadata,
    TopicAndPartition, KafkaUnavailableError,
    LeaderUnavailableError, PartitionUnavailableError
)
from kafka.protocol import (
    create_message, KafkaProtocol
)

class TestKafkaClient(unittest2.TestCase):
    def test_init_with_list(self):
        with patch.object(KafkaClient, 'load_metadata_for_topics'):
            client = KafkaClient(hosts=['kafka01:9092', 'kafka02:9092', 'kafka03:9092'])

        self.assertItemsEqual(
            [('kafka01', 9092), ('kafka02', 9092), ('kafka03', 9092)],
            client.hosts)

    def test_init_with_csv(self):
        with patch.object(KafkaClient, 'load_metadata_for_topics'):
            client = KafkaClient(hosts='kafka01:9092,kafka02:9092,kafka03:9092')

        self.assertItemsEqual(
            [('kafka01', 9092), ('kafka02', 9092), ('kafka03', 9092)],
            client.hosts)

    def test_init_with_unicode_csv(self):
        with patch.object(KafkaClient, 'load_metadata_for_topics'):
            client = KafkaClient(hosts=u'kafka01:9092,kafka02:9092,kafka03:9092')

        self.assertItemsEqual(
            [('kafka01', 9092), ('kafka02', 9092), ('kafka03', 9092)],
            client.hosts)

    def test_send_broker_unaware_request_fail(self):
        'Tests that call fails when all hosts are unavailable'

        mocked_conns = {
            ('kafka01', 9092): MagicMock(),
            ('kafka02', 9092): MagicMock()
        }

        # inject KafkaConnection side effects
        mocked_conns[('kafka01', 9092)].send.side_effect = RuntimeError("kafka01 went away (unittest)")
        mocked_conns[('kafka02', 9092)].send.side_effect = RuntimeError("Kafka02 went away (unittest)")

        def mock_get_conn(host, port):
            return mocked_conns[(host, port)]

        # patch to avoid making requests before we want it
        with patch.object(KafkaClient, 'load_metadata_for_topics'):
            with patch.object(KafkaClient, '_get_conn', side_effect=mock_get_conn):
                client = KafkaClient(hosts=['kafka01:9092', 'kafka02:9092'])

                with self.assertRaises(KafkaUnavailableError):
                    client._send_broker_unaware_request(1, 'fake request')

                for key, conn in mocked_conns.iteritems():
                    conn.send.assert_called_with(1, 'fake request')

    def test_send_broker_unaware_request(self):
        'Tests that call works when at least one of the host is available'

        mocked_conns = {
            ('kafka01', 9092): MagicMock(),
            ('kafka02', 9092): MagicMock(),
            ('kafka03', 9092): MagicMock()
        }
        # inject KafkaConnection side effects
        mocked_conns[('kafka01', 9092)].send.side_effect = RuntimeError("kafka01 went away (unittest)")
        mocked_conns[('kafka02', 9092)].recv.return_value = 'valid response'
        mocked_conns[('kafka03', 9092)].send.side_effect = RuntimeError("kafka03 went away (unittest)")

        def mock_get_conn(host, port):
            return mocked_conns[(host, port)]

        # patch to avoid making requests before we want it
        with patch.object(KafkaClient, 'load_metadata_for_topics'):
            with patch.object(KafkaClient, '_get_conn', side_effect=mock_get_conn):
                client = KafkaClient(hosts='kafka01:9092,kafka02:9092')

                resp = client._send_broker_unaware_request(1, 'fake request')

                self.assertEqual('valid response', resp)
                mocked_conns[('kafka02', 9092)].recv.assert_called_with(1)

    @patch('kafka.client.KafkaConnection')
    @patch('kafka.client.KafkaProtocol')
    def test_load_metadata(self, protocol, conn):
        "Load metadata for all topics"

        conn.recv.return_value = 'response'  # anything but None

        brokers = {}
        brokers[0] = BrokerMetadata(1, 'broker_1', 4567)
        brokers[1] = BrokerMetadata(2, 'broker_2', 5678)

        topics = {}
        topics['topic_1'] = {
            0: PartitionMetadata('topic_1', 0, 1, [1, 2], [1, 2])
        }
        topics['topic_noleader'] = {
            0: PartitionMetadata('topic_noleader', 0, -1, [], []),
            1: PartitionMetadata('topic_noleader', 1, -1, [], [])
        }
        topics['topic_no_partitions'] = {}
        topics['topic_3'] = {
            0: PartitionMetadata('topic_3', 0, 0, [0, 1], [0, 1]),
            1: PartitionMetadata('topic_3', 1, 1, [1, 0], [1, 0]),
            2: PartitionMetadata('topic_3', 2, 0, [0, 1], [0, 1])
        }
        protocol.decode_metadata_response.return_value = (brokers, topics)

        # client loads metadata at init
        client = KafkaClient(hosts=['broker_1:4567'])
        self.assertDictEqual({
            TopicAndPartition('topic_1', 0): brokers[1],
            TopicAndPartition('topic_noleader', 0): None,
            TopicAndPartition('topic_noleader', 1): None,
            TopicAndPartition('topic_3', 0): brokers[0],
            TopicAndPartition('topic_3', 1): brokers[1],
            TopicAndPartition('topic_3', 2): brokers[0]},
            client.topics_to_brokers)

    @patch('kafka.client.KafkaConnection')
    @patch('kafka.client.KafkaProtocol')
    def test_get_leader_for_partitions_reloads_metadata(self, protocol, conn):
        "Get leader for partitions reload metadata if it is not available"

        conn.recv.return_value = 'response'  # anything but None

        brokers = {}
        brokers[0] = BrokerMetadata(0, 'broker_1', 4567)
        brokers[1] = BrokerMetadata(1, 'broker_2', 5678)

        topics = {'topic_no_partitions': {}}
        protocol.decode_metadata_response.return_value = (brokers, topics)

        client = KafkaClient(hosts=['broker_1:4567'])

        # topic metadata is loaded but empty
        self.assertDictEqual({}, client.topics_to_brokers)

        topics['topic_no_partitions'] = {
            0: PartitionMetadata('topic_no_partitions', 0, 0, [0, 1], [0, 1])
        }
        protocol.decode_metadata_response.return_value = (brokers, topics)

        # calling _get_leader_for_partition (from any broker aware request)
        # will try loading metadata again for the same topic
        leader = client._get_leader_for_partition('topic_no_partitions', 0)

        self.assertEqual(brokers[0], leader)
        self.assertDictEqual({
            TopicAndPartition('topic_no_partitions', 0): brokers[0]},
            client.topics_to_brokers)

    @patch('kafka.client.KafkaConnection')
    @patch('kafka.client.KafkaProtocol')
    def test_get_leader_for_unassigned_partitions(self, protocol, conn):
        "Get leader raises if no partitions is defined for a topic"

        conn.recv.return_value = 'response'  # anything but None

        brokers = {}
        brokers[0] = BrokerMetadata(0, 'broker_1', 4567)
        brokers[1] = BrokerMetadata(1, 'broker_2', 5678)

        topics = {'topic_no_partitions': {}}
        protocol.decode_metadata_response.return_value = (brokers, topics)

        client = KafkaClient(hosts=['broker_1:4567'])

        self.assertDictEqual({}, client.topics_to_brokers)

        with self.assertRaises(PartitionUnavailableError):
            client._get_leader_for_partition('topic_no_partitions', 0)

    @patch('kafka.client.KafkaConnection')
    @patch('kafka.client.KafkaProtocol')
    def test_get_leader_returns_none_when_noleader(self, protocol, conn):
        "Getting leader for partitions returns None when the partiion has no leader"

        conn.recv.return_value = 'response'  # anything but None

        brokers = {}
        brokers[0] = BrokerMetadata(0, 'broker_1', 4567)
        brokers[1] = BrokerMetadata(1, 'broker_2', 5678)

        topics = {}
        topics['topic_noleader'] = {
            0: PartitionMetadata('topic_noleader', 0, -1, [], []),
            1: PartitionMetadata('topic_noleader', 1, -1, [], [])
        }
        protocol.decode_metadata_response.return_value = (brokers, topics)

        client = KafkaClient(hosts=['broker_1:4567'])
        self.assertDictEqual(
            {
                TopicAndPartition('topic_noleader', 0): None,
                TopicAndPartition('topic_noleader', 1): None
            },
            client.topics_to_brokers)
        self.assertIsNone(client._get_leader_for_partition('topic_noleader', 0))
        self.assertIsNone(client._get_leader_for_partition('topic_noleader', 1))

        topics['topic_noleader'] = {
            0: PartitionMetadata('topic_noleader', 0, 0, [0, 1], [0, 1]),
            1: PartitionMetadata('topic_noleader', 1, 1, [1, 0], [1, 0])
        }
        protocol.decode_metadata_response.return_value = (brokers, topics)
        self.assertEqual(brokers[0], client._get_leader_for_partition('topic_noleader', 0))
        self.assertEqual(brokers[1], client._get_leader_for_partition('topic_noleader', 1))

    @patch('kafka.client.KafkaConnection')
    @patch('kafka.client.KafkaProtocol')
    def test_send_produce_request_raises_when_noleader(self, protocol, conn):
        "Send producer request raises LeaderUnavailableError if leader is not available"

        conn.recv.return_value = 'response'  # anything but None

        brokers = {}
        brokers[0] = BrokerMetadata(0, 'broker_1', 4567)
        brokers[1] = BrokerMetadata(1, 'broker_2', 5678)

        topics = {}
        topics['topic_noleader'] = {
            0: PartitionMetadata('topic_noleader', 0, -1, [], []),
            1: PartitionMetadata('topic_noleader', 1, -1, [], [])
        }
        protocol.decode_metadata_response.return_value = (brokers, topics)

        client = KafkaClient(hosts=['broker_1:4567'])

        requests = [ProduceRequest(
            "topic_noleader", 0,
            [create_message("a"), create_message("b")])]

        with self.assertRaises(LeaderUnavailableError):
            client.send_produce_request(requests)


########NEW FILE########
__FILENAME__ = test_client_integration
import os
import random
import socket
import time
import unittest2

import kafka
from kafka.common import *
from fixtures import ZookeeperFixture, KafkaFixture
from testutil import *

class TestKafkaClientIntegration(KafkaIntegrationTestCase):
    @classmethod
    def setUpClass(cls):  # noqa
        if not os.environ.get('KAFKA_VERSION'):
            return

        cls.zk = ZookeeperFixture.instance()
        cls.server = KafkaFixture.instance(0, cls.zk.host, cls.zk.port)

    @classmethod
    def tearDownClass(cls):  # noqa
        if not os.environ.get('KAFKA_VERSION'):
            return

        cls.server.close()
        cls.zk.close()

    @unittest2.skip("This doesn't appear to work on Linux?")
    def test_timeout(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_port = get_open_port()
        server_socket.bind(('localhost', server_port))

        with Timer() as t:
            with self.assertRaises((socket.timeout, socket.error)):
                conn = kafka.conn.KafkaConnection("localhost", server_port, 1.0)
        self.assertGreaterEqual(t.interval, 1.0)

    @kafka_versions("all")
    def test_consume_none(self):
        fetch = FetchRequest(self.topic, 0, 0, 1024)

        fetch_resp, = self.client.send_fetch_request([fetch])
        self.assertEquals(fetch_resp.error, 0)
        self.assertEquals(fetch_resp.topic, self.topic)
        self.assertEquals(fetch_resp.partition, 0)

        messages = list(fetch_resp.messages)
        self.assertEquals(len(messages), 0)

    ####################
    #   Offset Tests   #
    ####################

    @kafka_versions("0.8.1")
    def test_commit_fetch_offsets(self):
        req = OffsetCommitRequest(self.topic, 0, 42, "metadata")
        (resp,) = self.client.send_offset_commit_request("group", [req])
        self.assertEquals(resp.error, 0)

        req = OffsetFetchRequest(self.topic, 0)
        (resp,) = self.client.send_offset_fetch_request("group", [req])
        self.assertEquals(resp.error, 0)
        self.assertEquals(resp.offset, 42)
        self.assertEquals(resp.metadata, "")  # Metadata isn't stored for now

########NEW FILE########
__FILENAME__ = test_codec
import struct
import unittest2

from kafka.codec import (
    has_snappy, gzip_encode, gzip_decode,
    snappy_encode, snappy_decode
)
from kafka.protocol import (
    create_gzip_message, create_message, create_snappy_message, KafkaProtocol
)
from testutil import *

class TestCodec(unittest2.TestCase):
    def test_gzip(self):
        for i in xrange(1000):
            s1 = random_string(100)
            s2 = gzip_decode(gzip_encode(s1))
            self.assertEquals(s1, s2)

    @unittest2.skipUnless(has_snappy(), "Snappy not available")
    def test_snappy(self):
        for i in xrange(1000):
            s1 = random_string(100)
            s2 = snappy_decode(snappy_encode(s1))
            self.assertEquals(s1, s2)

    @unittest2.skipUnless(has_snappy(), "Snappy not available")
    def test_snappy_detect_xerial(self):
        import kafka as kafka1
        _detect_xerial_stream = kafka1.codec._detect_xerial_stream

        header = b'\x82SNAPPY\x00\x00\x00\x00\x01\x00\x00\x00\x01Some extra bytes'
        false_header = b'\x01SNAPPY\x00\x00\x00\x01\x00\x00\x00\x01'
        random_snappy = snappy_encode('SNAPPY' * 50)
        short_data = b'\x01\x02\x03\x04'

        self.assertTrue(_detect_xerial_stream(header))
        self.assertFalse(_detect_xerial_stream(b''))
        self.assertFalse(_detect_xerial_stream(b'\x00'))
        self.assertFalse(_detect_xerial_stream(false_header))
        self.assertFalse(_detect_xerial_stream(random_snappy))
        self.assertFalse(_detect_xerial_stream(short_data))

    @unittest2.skipUnless(has_snappy(), "Snappy not available")
    def test_snappy_decode_xerial(self):
        header = b'\x82SNAPPY\x00\x00\x00\x00\x01\x00\x00\x00\x01'
        random_snappy = snappy_encode('SNAPPY' * 50)
        block_len = len(random_snappy)
        random_snappy2 = snappy_encode('XERIAL' * 50)
        block_len2 = len(random_snappy2)

        to_test = header \
            + struct.pack('!i', block_len) + random_snappy \
            + struct.pack('!i', block_len2) + random_snappy2 \

        self.assertEquals(snappy_decode(to_test), ('SNAPPY' * 50) + ('XERIAL' * 50))

    @unittest2.skipUnless(has_snappy(), "Snappy not available")
    def test_snappy_encode_xerial(self):
        to_ensure = b'\x82SNAPPY\x00\x00\x00\x00\x01\x00\x00\x00\x01' + \
            '\x00\x00\x00\x18' + \
            '\xac\x02\x14SNAPPY\xfe\x06\x00\xfe\x06\x00\xfe\x06\x00\xfe\x06\x00\x96\x06\x00' + \
            '\x00\x00\x00\x18' + \
            '\xac\x02\x14XERIAL\xfe\x06\x00\xfe\x06\x00\xfe\x06\x00\xfe\x06\x00\x96\x06\x00'

        to_test = ('SNAPPY' * 50) + ('XERIAL' * 50)

        compressed = snappy_encode(to_test, xerial_compatible=True, xerial_blocksize=300)
        self.assertEquals(compressed, to_ensure)


########NEW FILE########
__FILENAME__ = test_conn
import os
import random
import struct
import unittest2
import kafka.conn

class ConnTest(unittest2.TestCase):
    def test_collect_hosts__happy_path(self):
        hosts = "localhost:1234,localhost"
        results = kafka.conn.collect_hosts(hosts)

        self.assertEqual(set(results), set([
            ('localhost', 1234),
            ('localhost', 9092),
        ]))

    def test_collect_hosts__string_list(self):
        hosts = [
            'localhost:1234',
            'localhost',
        ]

        results = kafka.conn.collect_hosts(hosts)

        self.assertEqual(set(results), set([
            ('localhost', 1234),
            ('localhost', 9092),
        ]))

    def test_collect_hosts__with_spaces(self):
        hosts = "localhost:1234, localhost"
        results = kafka.conn.collect_hosts(hosts)

        self.assertEqual(set(results), set([
            ('localhost', 1234),
            ('localhost', 9092),
        ]))

    @unittest2.skip("Not Implemented")
    def test_send(self):
        pass

    @unittest2.skip("Not Implemented")
    def test_send__reconnects_on_dirty_conn(self):
        pass

    @unittest2.skip("Not Implemented")
    def test_send__failure_sets_dirty_connection(self):
        pass

    @unittest2.skip("Not Implemented")
    def test_recv(self):
        pass

    @unittest2.skip("Not Implemented")
    def test_recv__reconnects_on_dirty_conn(self):
        pass

    @unittest2.skip("Not Implemented")
    def test_recv__failure_sets_dirty_connection(self):
        pass

    @unittest2.skip("Not Implemented")
    def test_recv__doesnt_consume_extra_data_in_stream(self):
        pass

    @unittest2.skip("Not Implemented")
    def test_close__object_is_reusable(self):
        pass

########NEW FILE########
__FILENAME__ = test_consumer
import os
import random
import struct
import unittest2

from mock import MagicMock, patch

from kafka import KafkaClient
from kafka.consumer import SimpleConsumer
from kafka.common import (
    ProduceRequest, BrokerMetadata, PartitionMetadata,
    TopicAndPartition, KafkaUnavailableError,
    LeaderUnavailableError, PartitionUnavailableError
)
from kafka.protocol import (
    create_message, KafkaProtocol
)

class TestKafkaConsumer(unittest2.TestCase):
    def test_non_integer_partitions(self):
        with self.assertRaises(AssertionError):
            consumer = SimpleConsumer(MagicMock(), 'group', 'topic', partitions = [ '0' ])

########NEW FILE########
__FILENAME__ = test_consumer_integration
import os
from datetime import datetime

from kafka import *  # noqa
from kafka.common import *  # noqa
from kafka.consumer import MAX_FETCH_BUFFER_SIZE_BYTES
from fixtures import ZookeeperFixture, KafkaFixture
from testutil import *

class TestConsumerIntegration(KafkaIntegrationTestCase):
    @classmethod
    def setUpClass(cls):
        if not os.environ.get('KAFKA_VERSION'):
            return

        cls.zk = ZookeeperFixture.instance()
        cls.server1 = KafkaFixture.instance(0, cls.zk.host, cls.zk.port)
        cls.server2 = KafkaFixture.instance(1, cls.zk.host, cls.zk.port)

        cls.server = cls.server1 # Bootstrapping server

    @classmethod
    def tearDownClass(cls):
        if not os.environ.get('KAFKA_VERSION'):
            return

        cls.server1.close()
        cls.server2.close()
        cls.zk.close()

    def send_messages(self, partition, messages):
        messages = [ create_message(self.msg(str(msg))) for msg in messages ]
        produce = ProduceRequest(self.topic, partition, messages = messages)
        resp, = self.client.send_produce_request([produce])
        self.assertEquals(resp.error, 0)

        return [ x.value for x in messages ]

    def assert_message_count(self, messages, num_messages):
        # Make sure we got them all
        self.assertEquals(len(messages), num_messages)

        # Make sure there are no duplicates
        self.assertEquals(len(set(messages)), num_messages)

    @kafka_versions("all")
    def test_simple_consumer(self):
        self.send_messages(0, range(0, 100))
        self.send_messages(1, range(100, 200))

        # Start a consumer
        consumer = self.consumer()

        self.assert_message_count([ message for message in consumer ], 200)

        consumer.stop()

    @kafka_versions("all")
    def test_simple_consumer__seek(self):
        self.send_messages(0, range(0, 100))
        self.send_messages(1, range(100, 200))

        consumer = self.consumer()

        # Rewind 10 messages from the end
        consumer.seek(-10, 2)
        self.assert_message_count([ message for message in consumer ], 10)

        # Rewind 13 messages from the end
        consumer.seek(-13, 2)
        self.assert_message_count([ message for message in consumer ], 13)

        consumer.stop()

    @kafka_versions("all")
    def test_simple_consumer_blocking(self):
        consumer = self.consumer()

        # Ask for 5 messages, nothing in queue, block 5 seconds
        with Timer() as t:
            messages = consumer.get_messages(block=True, timeout=5)
            self.assert_message_count(messages, 0)
        self.assertGreaterEqual(t.interval, 5)

        self.send_messages(0, range(0, 10))

        # Ask for 5 messages, 10 in queue. Get 5 back, no blocking
        with Timer() as t:
            messages = consumer.get_messages(count=5, block=True, timeout=5)
            self.assert_message_count(messages, 5)
        self.assertLessEqual(t.interval, 1)

        # Ask for 10 messages, get 5 back, block 5 seconds
        with Timer() as t:
            messages = consumer.get_messages(count=10, block=True, timeout=5)
            self.assert_message_count(messages, 5)
        self.assertGreaterEqual(t.interval, 5)

        consumer.stop()

    @kafka_versions("all")
    def test_simple_consumer_pending(self):
        # Produce 10 messages to partitions 0 and 1
        self.send_messages(0, range(0, 10))
        self.send_messages(1, range(10, 20))

        consumer = self.consumer()

        self.assertEquals(consumer.pending(), 20)
        self.assertEquals(consumer.pending(partitions=[0]), 10)
        self.assertEquals(consumer.pending(partitions=[1]), 10)

        consumer.stop()

    @kafka_versions("all")
    def test_multi_process_consumer(self):
        # Produce 100 messages to partitions 0 and 1
        self.send_messages(0, range(0, 100))
        self.send_messages(1, range(100, 200))

        consumer = self.consumer(consumer = MultiProcessConsumer)

        self.assert_message_count([ message for message in consumer ], 200)

        consumer.stop()

    @kafka_versions("all")
    def test_multi_process_consumer_blocking(self):
        consumer = self.consumer(consumer = MultiProcessConsumer)

        # Ask for 5 messages, No messages in queue, block 5 seconds
        with Timer() as t:
            messages = consumer.get_messages(block=True, timeout=5)
            self.assert_message_count(messages, 0)

        self.assertGreaterEqual(t.interval, 5)

        # Send 10 messages
        self.send_messages(0, range(0, 10))

        # Ask for 5 messages, 10 messages in queue, block 0 seconds
        with Timer() as t:
            messages = consumer.get_messages(count=5, block=True, timeout=5)
            self.assert_message_count(messages, 5)
        self.assertLessEqual(t.interval, 1)

        # Ask for 10 messages, 5 in queue, block 5 seconds
        with Timer() as t:
            messages = consumer.get_messages(count=10, block=True, timeout=5)
            self.assert_message_count(messages, 5)
        self.assertGreaterEqual(t.interval, 5)

        consumer.stop()

    @kafka_versions("all")
    def test_multi_proc_pending(self):
        self.send_messages(0, range(0, 10))
        self.send_messages(1, range(10, 20))

        consumer = MultiProcessConsumer(self.client, "group1", self.topic, auto_commit=False)

        self.assertEquals(consumer.pending(), 20)
        self.assertEquals(consumer.pending(partitions=[0]), 10)
        self.assertEquals(consumer.pending(partitions=[1]), 10)

        consumer.stop()

    @kafka_versions("all")
    def test_large_messages(self):
        # Produce 10 "normal" size messages
        small_messages = self.send_messages(0, [ str(x) for x in range(10) ])

        # Produce 10 messages that are large (bigger than default fetch size)
        large_messages = self.send_messages(0, [ random_string(5000) for x in range(10) ])

        # Consumer should still get all of them
        consumer = self.consumer()

        expected_messages = set(small_messages + large_messages)
        actual_messages = set([ x.message.value for x in consumer ])
        self.assertEqual(expected_messages, actual_messages)

        consumer.stop()

    @kafka_versions("all")
    def test_huge_messages(self):
        huge_message, = self.send_messages(0, [
            create_message(random_string(MAX_FETCH_BUFFER_SIZE_BYTES + 10)),
        ])

        # Create a consumer with the default buffer size
        consumer = self.consumer()

        # This consumer failes to get the message
        with self.assertRaises(ConsumerFetchSizeTooSmall):
            consumer.get_message(False, 0.1)

        consumer.stop()

        # Create a consumer with no fetch size limit
        big_consumer = self.consumer(
            max_buffer_size = None,
            partitions = [0],
        )

        # Seek to the last message
        big_consumer.seek(-1, 2)

        # Consume giant message successfully
        message = big_consumer.get_message(block=False, timeout=10)
        self.assertIsNotNone(message)
        self.assertEquals(message.message.value, huge_message)

        big_consumer.stop()

    @kafka_versions("0.8.1")
    def test_offset_behavior__resuming_behavior(self):
        msgs1 = self.send_messages(0, range(0, 100))
        msgs2 = self.send_messages(1, range(100, 200))

        # Start a consumer
        consumer1 = self.consumer(
            auto_commit_every_t = None,
            auto_commit_every_n = 20,
        )

        # Grab the first 195 messages
        output_msgs1 = [ consumer1.get_message().message.value for _ in xrange(195) ]
        self.assert_message_count(output_msgs1, 195)

        # The total offset across both partitions should be at 180
        consumer2 = self.consumer(
            auto_commit_every_t = None,
            auto_commit_every_n = 20,
        )

        # 181-200
        self.assert_message_count([ message for message in consumer2 ], 20)

        consumer1.stop()
        consumer2.stop()

    def consumer(self, **kwargs):
        if os.environ['KAFKA_VERSION'] == "0.8.0":
            # Kafka 0.8.0 simply doesn't support offset requests, so hard code it being off
            kwargs['auto_commit'] = False
        else:
            kwargs.setdefault('auto_commit', True)

        consumer_class = kwargs.pop('consumer', SimpleConsumer)
        group = kwargs.pop('group', self.id())
        topic = kwargs.pop('topic', self.topic)

        if consumer_class == SimpleConsumer:
            kwargs.setdefault('iter_timeout', 0)

        return consumer_class(self.client, group, topic, **kwargs)

########NEW FILE########
__FILENAME__ = test_failover_integration
import os
import time

from kafka import *  # noqa
from kafka.common import *  # noqa
from fixtures import ZookeeperFixture, KafkaFixture
from testutil import *

class TestFailover(KafkaIntegrationTestCase):
    create_client = False

    @classmethod
    def setUpClass(cls):  # noqa
        if not os.environ.get('KAFKA_VERSION'):
            return

        zk_chroot = random_string(10)
        replicas = 2
        partitions = 2

        # mini zookeeper, 2 kafka brokers
        cls.zk = ZookeeperFixture.instance()
        kk_args = [cls.zk.host, cls.zk.port, zk_chroot, replicas, partitions]
        cls.brokers = [KafkaFixture.instance(i, *kk_args) for i in range(replicas)]

        hosts = ['%s:%d' % (b.host, b.port) for b in cls.brokers]
        cls.client = KafkaClient(hosts)

    @classmethod
    def tearDownClass(cls):
        if not os.environ.get('KAFKA_VERSION'):
            return

        cls.client.close()
        for broker in cls.brokers:
            broker.close()
        cls.zk.close()

    @kafka_versions("all")
    def test_switch_leader(self):
        key, topic, partition = random_string(5), self.topic, 0
        producer = SimpleProducer(self.client)

        for i in range(1, 4):

            # XXX unfortunately, the conns dict needs to be warmed for this to work
            # XXX unfortunately, for warming to work, we need at least as many partitions as brokers
            self._send_random_messages(producer, self.topic, 10)

            # kil leader for partition 0
            broker = self._kill_leader(topic, partition)

            # expect failure, reload meta data
            with self.assertRaises(FailedPayloadsError):
                producer.send_messages(self.topic, 'part 1')
                producer.send_messages(self.topic, 'part 2')
            time.sleep(1)

            # send to new leader
            self._send_random_messages(producer, self.topic, 10)

            broker.open()
            time.sleep(3)

            # count number of messages
            count = self._count_messages('test_switch_leader group %s' % i, topic)
            self.assertIn(count, range(20 * i, 22 * i + 1))

        producer.stop()

    @kafka_versions("all")
    def test_switch_leader_async(self):
        key, topic, partition = random_string(5), self.topic, 0
        producer = SimpleProducer(self.client, async=True)

        for i in range(1, 4):

            self._send_random_messages(producer, self.topic, 10)

            # kil leader for partition 0
            broker = self._kill_leader(topic, partition)

            # expect failure, reload meta data
            producer.send_messages(self.topic, 'part 1')
            producer.send_messages(self.topic, 'part 2')
            time.sleep(1)

            # send to new leader
            self._send_random_messages(producer, self.topic, 10)

            broker.open()
            time.sleep(3)

            # count number of messages
            count = self._count_messages('test_switch_leader_async group %s' % i, topic)
            self.assertIn(count, range(20 * i, 22 * i + 1))

        producer.stop()

    def _send_random_messages(self, producer, topic, n):
        for j in range(n):
            resp = producer.send_messages(topic, random_string(10))
            if len(resp) > 0:
                self.assertEquals(resp[0].error, 0)
        time.sleep(1)  # give it some time

    def _kill_leader(self, topic, partition):
        leader = self.client.topics_to_brokers[TopicAndPartition(topic, partition)]
        broker = self.brokers[leader.nodeId]
        broker.close()
        time.sleep(1)  # give it some time
        return broker

    def _count_messages(self, group, topic):
        hosts = '%s:%d' % (self.brokers[0].host, self.brokers[0].port)
        client = KafkaClient(hosts)
        consumer = SimpleConsumer(client, group, topic, auto_commit=False, iter_timeout=0)
        all_messages = []
        for message in consumer:
            all_messages.append(message)
        consumer.stop()
        client.close()
        return len(all_messages)

########NEW FILE########
__FILENAME__ = test_package
import unittest2

class TestPackage(unittest2.TestCase):
    def test_top_level_namespace(self):
        import kafka as kafka1
        self.assertEquals(kafka1.KafkaClient.__name__, "KafkaClient")
        self.assertEquals(kafka1.client.__name__, "kafka.client")
        self.assertEquals(kafka1.codec.__name__, "kafka.codec")

    def test_submodule_namespace(self):
        import kafka.client as client1
        self.assertEquals(client1.__name__, "kafka.client")
        self.assertEquals(client1.KafkaClient.__name__, "KafkaClient")

        from kafka import client as client2
        self.assertEquals(client2.__name__, "kafka.client")
        self.assertEquals(client2.KafkaClient.__name__, "KafkaClient")

        from kafka.client import KafkaClient as KafkaClient1
        self.assertEquals(KafkaClient1.__name__, "KafkaClient")

        from kafka.codec import gzip_encode as gzip_encode1
        self.assertEquals(gzip_encode1.__name__, "gzip_encode")

        from kafka import KafkaClient as KafkaClient2
        self.assertEquals(KafkaClient2.__name__, "KafkaClient")

        from kafka.codec import snappy_encode
        self.assertEquals(snappy_encode.__name__, "snappy_encode")

########NEW FILE########
__FILENAME__ = test_producer_integration
import os
import time
import uuid

from kafka import *  # noqa
from kafka.common import *  # noqa
from kafka.codec import has_gzip, has_snappy
from fixtures import ZookeeperFixture, KafkaFixture
from testutil import *

class TestKafkaProducerIntegration(KafkaIntegrationTestCase):
    topic = 'produce_topic'

    @classmethod
    def setUpClass(cls):  # noqa
        if not os.environ.get('KAFKA_VERSION'):
            return

        cls.zk = ZookeeperFixture.instance()
        cls.server = KafkaFixture.instance(0, cls.zk.host, cls.zk.port)

    @classmethod
    def tearDownClass(cls):  # noqa
        if not os.environ.get('KAFKA_VERSION'):
            return

        cls.server.close()
        cls.zk.close()

    @kafka_versions("all")
    def test_produce_many_simple(self):
        start_offset = self.current_offset(self.topic, 0)

        self.assert_produce_request(
            [ create_message("Test message %d" % i) for i in range(100) ],
            start_offset,
            100,
        )

        self.assert_produce_request(
            [ create_message("Test message %d" % i) for i in range(100) ],
            start_offset+100,
            100,
        )

    @kafka_versions("all")
    def test_produce_10k_simple(self):
        start_offset = self.current_offset(self.topic, 0)

        self.assert_produce_request(
            [ create_message("Test message %d" % i) for i in range(10000) ],
            start_offset,
            10000,
        )

    @kafka_versions("all")
    def test_produce_many_gzip(self):
        start_offset = self.current_offset(self.topic, 0)

        message1 = create_gzip_message(["Gzipped 1 %d" % i for i in range(100)])
        message2 = create_gzip_message(["Gzipped 2 %d" % i for i in range(100)])

        self.assert_produce_request(
            [ message1, message2 ],
            start_offset,
            200,
        )

    @kafka_versions("all")
    def test_produce_many_snappy(self):
        self.skipTest("All snappy integration tests fail with nosnappyjava")
        start_offset = self.current_offset(self.topic, 0)

        self.assert_produce_request([
                create_snappy_message(["Snappy 1 %d" % i for i in range(100)]),
                create_snappy_message(["Snappy 2 %d" % i for i in range(100)]),
            ],
            start_offset,
            200,
        )

    @kafka_versions("all")
    def test_produce_mixed(self):
        start_offset = self.current_offset(self.topic, 0)

        msg_count = 1+100
        messages = [
            create_message("Just a plain message"),
            create_gzip_message(["Gzipped %d" % i for i in range(100)]),
        ]

        # All snappy integration tests fail with nosnappyjava
        if False and has_snappy():
            msg_count += 100
            messages.append(create_snappy_message(["Snappy %d" % i for i in range(100)]))

        self.assert_produce_request(messages, start_offset, msg_count)

    @kafka_versions("all")
    def test_produce_100k_gzipped(self):
        start_offset = self.current_offset(self.topic, 0)

        self.assert_produce_request([
                create_gzip_message(["Gzipped batch 1, message %d" % i for i in range(50000)])
            ],
            start_offset,
            50000,
        )

        self.assert_produce_request([
                create_gzip_message(["Gzipped batch 1, message %d" % i for i in range(50000)])
            ],
            start_offset+50000,
            50000,
        )

    ############################
    #   SimpleProducer Tests   #
    ############################

    @kafka_versions("all")
    def test_simple_producer(self):
        start_offset0 = self.current_offset(self.topic, 0)
        start_offset1 = self.current_offset(self.topic, 1)
        producer = SimpleProducer(self.client)

        # Goes to first partition, randomly.
        resp = producer.send_messages(self.topic, self.msg("one"), self.msg("two"))
        self.assert_produce_response(resp, start_offset0)

        # Goes to the next partition, randomly.
        resp = producer.send_messages(self.topic, self.msg("three"))
        self.assert_produce_response(resp, start_offset1)

        self.assert_fetch_offset(0, start_offset0, [ self.msg("one"), self.msg("two") ])
        self.assert_fetch_offset(1, start_offset1, [ self.msg("three") ])

        # Goes back to the first partition because there's only two partitions
        resp = producer.send_messages(self.topic, self.msg("four"), self.msg("five"))
        self.assert_produce_response(resp, start_offset0+2)
        self.assert_fetch_offset(0, start_offset0, [ self.msg("one"), self.msg("two"), self.msg("four"), self.msg("five") ])

        producer.stop()

    @kafka_versions("all")
    def test_producer_random_order(self):
        producer = SimpleProducer(self.client, random_start = True)
        resp1 = producer.send_messages(self.topic, self.msg("one"), self.msg("two"))
        resp2 = producer.send_messages(self.topic, self.msg("three"))
        resp3 = producer.send_messages(self.topic, self.msg("four"), self.msg("five"))

        self.assertEqual(resp1[0].partition, resp3[0].partition)
        self.assertNotEqual(resp1[0].partition, resp2[0].partition)

    @kafka_versions("all")
    def test_producer_ordered_start(self):
        producer = SimpleProducer(self.client, random_start = False)
        resp1 = producer.send_messages(self.topic, self.msg("one"), self.msg("two"))
        resp2 = producer.send_messages(self.topic, self.msg("three"))
        resp3 = producer.send_messages(self.topic, self.msg("four"), self.msg("five"))

        self.assertEqual(resp1[0].partition, 0)
        self.assertEqual(resp2[0].partition, 1)
        self.assertEqual(resp3[0].partition, 0)

    @kafka_versions("all")
    def test_round_robin_partitioner(self):
        start_offset0 = self.current_offset(self.topic, 0)
        start_offset1 = self.current_offset(self.topic, 1)

        producer = KeyedProducer(self.client, partitioner=RoundRobinPartitioner)
        resp1 = producer.send(self.topic, "key1", self.msg("one"))
        resp2 = producer.send(self.topic, "key2", self.msg("two"))
        resp3 = producer.send(self.topic, "key3", self.msg("three"))
        resp4 = producer.send(self.topic, "key4", self.msg("four"))

        self.assert_produce_response(resp1, start_offset0+0)
        self.assert_produce_response(resp2, start_offset1+0)
        self.assert_produce_response(resp3, start_offset0+1)
        self.assert_produce_response(resp4, start_offset1+1)

        self.assert_fetch_offset(0, start_offset0, [ self.msg("one"), self.msg("three") ])
        self.assert_fetch_offset(1, start_offset1, [ self.msg("two"), self.msg("four")  ])

        producer.stop()

    @kafka_versions("all")
    def test_hashed_partitioner(self):
        start_offset0 = self.current_offset(self.topic, 0)
        start_offset1 = self.current_offset(self.topic, 1)

        producer = KeyedProducer(self.client, partitioner=HashedPartitioner)
        resp1 = producer.send(self.topic, 1, self.msg("one"))
        resp2 = producer.send(self.topic, 2, self.msg("two"))
        resp3 = producer.send(self.topic, 3, self.msg("three"))
        resp4 = producer.send(self.topic, 3, self.msg("four"))
        resp5 = producer.send(self.topic, 4, self.msg("five"))

        self.assert_produce_response(resp1, start_offset1+0)
        self.assert_produce_response(resp2, start_offset0+0)
        self.assert_produce_response(resp3, start_offset1+1)
        self.assert_produce_response(resp4, start_offset1+2)
        self.assert_produce_response(resp5, start_offset0+1)

        self.assert_fetch_offset(0, start_offset0, [ self.msg("two"), self.msg("five") ])
        self.assert_fetch_offset(1, start_offset1, [ self.msg("one"), self.msg("three"), self.msg("four") ])

        producer.stop()

    @kafka_versions("all")
    def test_acks_none(self):
        start_offset0 = self.current_offset(self.topic, 0)
        start_offset1 = self.current_offset(self.topic, 1)

        producer = SimpleProducer(self.client, req_acks=SimpleProducer.ACK_NOT_REQUIRED)
        resp = producer.send_messages(self.topic, self.msg("one"))
        self.assertEquals(len(resp), 0)

        self.assert_fetch_offset(0, start_offset0, [ self.msg("one") ])
        producer.stop()

    @kafka_versions("all")
    def test_acks_local_write(self):
        start_offset0 = self.current_offset(self.topic, 0)
        start_offset1 = self.current_offset(self.topic, 1)

        producer = SimpleProducer(self.client, req_acks=SimpleProducer.ACK_AFTER_LOCAL_WRITE)
        resp = producer.send_messages(self.topic, self.msg("one"))

        self.assert_produce_response(resp, start_offset0)
        self.assert_fetch_offset(0, start_offset0, [ self.msg("one") ])

        producer.stop()

    @kafka_versions("all")
    def test_acks_cluster_commit(self):
        start_offset0 = self.current_offset(self.topic, 0)
        start_offset1 = self.current_offset(self.topic, 1)

        producer = SimpleProducer(
            self.client,
            req_acks=SimpleProducer.ACK_AFTER_CLUSTER_COMMIT)

        resp = producer.send_messages(self.topic, self.msg("one"))
        self.assert_produce_response(resp, start_offset0)
        self.assert_fetch_offset(0, start_offset0, [ self.msg("one") ])

        producer.stop()

    @kafka_versions("all")
    def test_batched_simple_producer__triggers_by_message(self):
        start_offset0 = self.current_offset(self.topic, 0)
        start_offset1 = self.current_offset(self.topic, 1)

        producer = SimpleProducer(self.client,
                                  batch_send=True,
                                  batch_send_every_n=5,
                                  batch_send_every_t=20)

        # Send 5 messages and do a fetch
        resp = producer.send_messages(self.topic,
            self.msg("one"),
            self.msg("two"),
            self.msg("three"),
            self.msg("four"),
        )

        # Batch mode is async. No ack
        self.assertEquals(len(resp), 0)

        # It hasn't sent yet
        self.assert_fetch_offset(0, start_offset0, [])
        self.assert_fetch_offset(1, start_offset1, [])

        resp = producer.send_messages(self.topic,
            self.msg("five"),
            self.msg("six"),
            self.msg("seven"),
        )

        # Batch mode is async. No ack
        self.assertEquals(len(resp), 0)

        self.assert_fetch_offset(0, start_offset0, [
            self.msg("one"),
            self.msg("two"),
            self.msg("three"),
            self.msg("four"),
        ])

        self.assert_fetch_offset(1, start_offset1, [
            self.msg("five"),
        #    self.msg("six"),
        #    self.msg("seven"),
        ])

        producer.stop()

    @kafka_versions("all")
    def test_batched_simple_producer__triggers_by_time(self):
        start_offset0 = self.current_offset(self.topic, 0)
        start_offset1 = self.current_offset(self.topic, 1)

        producer = SimpleProducer(self.client,
                                  batch_send=True,
                                  batch_send_every_n=100,
                                  batch_send_every_t=5)

        # Send 5 messages and do a fetch
        resp = producer.send_messages(self.topic,
            self.msg("one"),
            self.msg("two"),
            self.msg("three"),
            self.msg("four"),
        )

        # Batch mode is async. No ack
        self.assertEquals(len(resp), 0)

        # It hasn't sent yet
        self.assert_fetch_offset(0, start_offset0, [])
        self.assert_fetch_offset(1, start_offset1, [])

        resp = producer.send_messages(self.topic,
            self.msg("five"),
            self.msg("six"),
            self.msg("seven"),
        )

        # Batch mode is async. No ack
        self.assertEquals(len(resp), 0)

        # Wait the timeout out
        time.sleep(5)

        self.assert_fetch_offset(0, start_offset0, [
            self.msg("one"),
            self.msg("two"),
            self.msg("three"),
            self.msg("four"),
        ])

        self.assert_fetch_offset(1, start_offset1, [
            self.msg("five"),
            self.msg("six"),
            self.msg("seven"),
        ])

        producer.stop()

    @kafka_versions("all")
    def test_async_simple_producer(self):
        start_offset0 = self.current_offset(self.topic, 0)
        start_offset1 = self.current_offset(self.topic, 1)

        producer = SimpleProducer(self.client, async=True)
        resp = producer.send_messages(self.topic, self.msg("one"))
        self.assertEquals(len(resp), 0)

        self.assert_fetch_offset(0, start_offset0, [ self.msg("one") ])

        producer.stop()

    @kafka_versions("all")
    def test_async_keyed_producer(self):
        start_offset0 = self.current_offset(self.topic, 0)
        start_offset1 = self.current_offset(self.topic, 1)

        producer = KeyedProducer(self.client, partitioner = RoundRobinPartitioner, async=True)

        resp = producer.send(self.topic, "key1", self.msg("one"))
        self.assertEquals(len(resp), 0)

        self.assert_fetch_offset(0, start_offset0, [ self.msg("one") ])

        producer.stop()

    def assert_produce_request(self, messages, initial_offset, message_ct):
        produce = ProduceRequest(self.topic, 0, messages=messages)

        # There should only be one response message from the server.
        # This will throw an exception if there's more than one.
        resp = self.client.send_produce_request([ produce ])
        self.assert_produce_response(resp, initial_offset)

        self.assertEqual(self.current_offset(self.topic, 0), initial_offset + message_ct)

    def assert_produce_response(self, resp, initial_offset):
        self.assertEqual(len(resp), 1)
        self.assertEqual(resp[0].error, 0)
        self.assertEqual(resp[0].offset, initial_offset)

    def assert_fetch_offset(self, partition, start_offset, expected_messages):
        # There should only be one response message from the server.
        # This will throw an exception if there's more than one.

        resp, = self.client.send_fetch_request([ FetchRequest(self.topic, partition, start_offset, 1024) ])

        self.assertEquals(resp.error, 0)
        self.assertEquals(resp.partition, partition)
        messages = [ x.message.value for x in resp.messages ]

        self.assertEqual(messages, expected_messages)
        self.assertEquals(resp.highwaterMark, start_offset+len(expected_messages))

########NEW FILE########
__FILENAME__ = test_protocol
import contextlib
from contextlib import contextmanager
import struct
import unittest2

import mock
from mock import sentinel

from kafka import KafkaClient
from kafka.common import (
    OffsetRequest, OffsetCommitRequest, OffsetFetchRequest,
    OffsetResponse, OffsetCommitResponse, OffsetFetchResponse,
    ProduceRequest, FetchRequest, Message, ChecksumError,
    ConsumerFetchSizeTooSmall, ProduceResponse, FetchResponse, OffsetAndMessage,
    BrokerMetadata, PartitionMetadata, TopicAndPartition, KafkaUnavailableError,
    ProtocolError, LeaderUnavailableError, PartitionUnavailableError,
    UnsupportedCodecError
)
from kafka.codec import (
    has_snappy, gzip_encode, gzip_decode,
    snappy_encode, snappy_decode
)
import kafka.protocol
from kafka.protocol import (
    ATTRIBUTE_CODEC_MASK, CODEC_NONE, CODEC_GZIP, CODEC_SNAPPY, KafkaProtocol,
    create_message, create_gzip_message, create_snappy_message,
    create_message_set
)

class TestProtocol(unittest2.TestCase):
    def test_create_message(self):
        payload = "test"
        key = "key"
        msg = create_message(payload, key)
        self.assertEqual(msg.magic, 0)
        self.assertEqual(msg.attributes, 0)
        self.assertEqual(msg.key, key)
        self.assertEqual(msg.value, payload)

    def test_create_gzip(self):
        payloads = ["v1", "v2"]
        msg = create_gzip_message(payloads)
        self.assertEqual(msg.magic, 0)
        self.assertEqual(msg.attributes, ATTRIBUTE_CODEC_MASK & CODEC_GZIP)
        self.assertEqual(msg.key, None)
        # Need to decode to check since gzipped payload is non-deterministic
        decoded = gzip_decode(msg.value)
        expect = "".join([
            struct.pack(">q", 0),          # MsgSet offset
            struct.pack(">i", 16),         # MsgSet size
            struct.pack(">i", 1285512130), # CRC
            struct.pack(">bb", 0, 0),      # Magic, flags
            struct.pack(">i", -1),         # -1 indicates a null key
            struct.pack(">i", 2),          # Msg length (bytes)
            "v1",                          # Message contents

            struct.pack(">q", 0),          # MsgSet offset
            struct.pack(">i", 16),         # MsgSet size
            struct.pack(">i", -711587208), # CRC
            struct.pack(">bb", 0, 0),      # Magic, flags
            struct.pack(">i", -1),         # -1 indicates a null key
            struct.pack(">i", 2),          # Msg length (bytes)
            "v2",                          # Message contents
        ])

        self.assertEqual(decoded, expect)

    @unittest2.skipUnless(has_snappy(), "Snappy not available")
    def test_create_snappy(self):
        payloads = ["v1", "v2"]
        msg = create_snappy_message(payloads)
        self.assertEqual(msg.magic, 0)
        self.assertEqual(msg.attributes, ATTRIBUTE_CODEC_MASK & CODEC_SNAPPY)
        self.assertEqual(msg.key, None)
        decoded = snappy_decode(msg.value)
        expect = "".join([
            struct.pack(">q", 0),          # MsgSet offset
            struct.pack(">i", 16),         # MsgSet size
            struct.pack(">i", 1285512130), # CRC
            struct.pack(">bb", 0, 0),      # Magic, flags
            struct.pack(">i", -1),         # -1 indicates a null key
            struct.pack(">i", 2),          # Msg length (bytes)
            "v1",                          # Message contents

            struct.pack(">q", 0),          # MsgSet offset
            struct.pack(">i", 16),         # MsgSet size
            struct.pack(">i", -711587208), # CRC
            struct.pack(">bb", 0, 0),      # Magic, flags
            struct.pack(">i", -1),         # -1 indicates a null key
            struct.pack(">i", 2),          # Msg length (bytes)
            "v2",                          # Message contents
        ])

        self.assertEqual(decoded, expect)

    def test_encode_message_header(self):
        expect = "".join([
            struct.pack(">h", 10),             # API Key
            struct.pack(">h", 0),              # API Version
            struct.pack(">i", 4),              # Correlation Id
            struct.pack(">h", len("client3")), # Length of clientId
            "client3",                         # ClientId
        ])

        encoded = KafkaProtocol._encode_message_header("client3", 4, 10)
        self.assertEqual(encoded, expect)

    def test_encode_message(self):
        message = create_message("test", "key")
        encoded = KafkaProtocol._encode_message(message)
        expect = "".join([
            struct.pack(">i", -1427009701), # CRC
            struct.pack(">bb", 0, 0),       # Magic, flags
            struct.pack(">i", 3),           # Length of key
            "key",                          # key
            struct.pack(">i", 4),           # Length of value
            "test",                         # value
        ])

        self.assertEqual(encoded, expect)

    def test_decode_message(self):
        encoded = "".join([
            struct.pack(">i", -1427009701), # CRC
            struct.pack(">bb", 0, 0),       # Magic, flags
            struct.pack(">i", 3),           # Length of key
            "key",                          # key
            struct.pack(">i", 4),           # Length of value
            "test",                         # value
        ])

        offset = 10
        (returned_offset, decoded_message) = list(KafkaProtocol._decode_message(encoded, offset))[0]

        self.assertEqual(returned_offset, offset)
        self.assertEqual(decoded_message, create_message("test", "key"))

    def test_encode_message_failure(self):
        with self.assertRaises(ProtocolError):
            KafkaProtocol._encode_message(Message(1, 0, "key", "test"))

    def test_encode_message_set(self):
        message_set = [
            create_message("v1", "k1"),
            create_message("v2", "k2")
        ]

        encoded = KafkaProtocol._encode_message_set(message_set)
        expect = "".join([
            struct.pack(">q", 0),          # MsgSet Offset
            struct.pack(">i", 18),         # Msg Size
            struct.pack(">i", 1474775406), # CRC
            struct.pack(">bb", 0, 0),      # Magic, flags
            struct.pack(">i", 2),          # Length of key
            "k1",                          # Key
            struct.pack(">i", 2),          # Length of value
            "v1",                          # Value

            struct.pack(">q", 0),          # MsgSet Offset
            struct.pack(">i", 18),         # Msg Size
            struct.pack(">i", -16383415),  # CRC
            struct.pack(">bb", 0, 0),      # Magic, flags
            struct.pack(">i", 2),          # Length of key
            "k2",                          # Key
            struct.pack(">i", 2),          # Length of value
            "v2",                          # Value
        ])

        self.assertEqual(encoded, expect)

    def test_decode_message_set(self):
        encoded = "".join([
            struct.pack(">q", 0),          # MsgSet Offset
            struct.pack(">i", 18),         # Msg Size
            struct.pack(">i", 1474775406), # CRC
            struct.pack(">bb", 0, 0),      # Magic, flags
            struct.pack(">i", 2),          # Length of key
            "k1",                          # Key
            struct.pack(">i", 2),          # Length of value
            "v1",                          # Value

            struct.pack(">q", 1),          # MsgSet Offset
            struct.pack(">i", 18),         # Msg Size
            struct.pack(">i", -16383415),  # CRC
            struct.pack(">bb", 0, 0),      # Magic, flags
            struct.pack(">i", 2),          # Length of key
            "k2",                          # Key
            struct.pack(">i", 2),          # Length of value
            "v2",                          # Value
        ])

        msgs = list(KafkaProtocol._decode_message_set_iter(encoded))
        self.assertEqual(len(msgs), 2)
        msg1, msg2 = msgs

        returned_offset1, decoded_message1 = msg1
        returned_offset2, decoded_message2 = msg2

        self.assertEqual(returned_offset1, 0)
        self.assertEqual(decoded_message1, create_message("v1", "k1"))

        self.assertEqual(returned_offset2, 1)
        self.assertEqual(decoded_message2, create_message("v2", "k2"))

    def test_decode_message_gzip(self):
        gzip_encoded = ('\xc0\x11\xb2\xf0\x00\x01\xff\xff\xff\xff\x00\x00\x000'
                        '\x1f\x8b\x08\x00\xa1\xc1\xc5R\x02\xffc`\x80\x03\x01'
                        '\x9f\xf9\xd1\x87\x18\x18\xfe\x03\x01\x90\xc7Tf\xc8'
                        '\x80$wu\x1aW\x05\x92\x9c\x11\x00z\xc0h\x888\x00\x00'
                        '\x00')
        offset = 11
        messages = list(KafkaProtocol._decode_message(gzip_encoded, offset))

        self.assertEqual(len(messages), 2)
        msg1, msg2 = messages

        returned_offset1, decoded_message1 = msg1
        self.assertEqual(returned_offset1, 0)
        self.assertEqual(decoded_message1, create_message("v1"))

        returned_offset2, decoded_message2 = msg2
        self.assertEqual(returned_offset2, 0)
        self.assertEqual(decoded_message2, create_message("v2"))

    @unittest2.skipUnless(has_snappy(), "Snappy not available")
    def test_decode_message_snappy(self):
        snappy_encoded = ('\xec\x80\xa1\x95\x00\x02\xff\xff\xff\xff\x00\x00'
                          '\x00,8\x00\x00\x19\x01@\x10L\x9f[\xc2\x00\x00\xff'
                          '\xff\xff\xff\x00\x00\x00\x02v1\x19\x1bD\x00\x10\xd5'
                          '\x96\nx\x00\x00\xff\xff\xff\xff\x00\x00\x00\x02v2')
        offset = 11
        messages = list(KafkaProtocol._decode_message(snappy_encoded, offset))
        self.assertEqual(len(messages), 2)

        msg1, msg2 = messages

        returned_offset1, decoded_message1 = msg1
        self.assertEqual(returned_offset1, 0)
        self.assertEqual(decoded_message1, create_message("v1"))

        returned_offset2, decoded_message2 = msg2
        self.assertEqual(returned_offset2, 0)
        self.assertEqual(decoded_message2, create_message("v2"))

    def test_decode_message_checksum_error(self):
        invalid_encoded_message = "This is not a valid encoded message"
        iter = KafkaProtocol._decode_message(invalid_encoded_message, 0)
        self.assertRaises(ChecksumError, list, iter)

    # NOTE: The error handling in _decode_message_set_iter() is questionable.
    # If it's modified, the next two tests might need to be fixed.
    def test_decode_message_set_fetch_size_too_small(self):
        with self.assertRaises(ConsumerFetchSizeTooSmall):
            list(KafkaProtocol._decode_message_set_iter('a'))

    def test_decode_message_set_stop_iteration(self):
        encoded = "".join([
            struct.pack(">q", 0),          # MsgSet Offset
            struct.pack(">i", 18),         # Msg Size
            struct.pack(">i", 1474775406), # CRC
            struct.pack(">bb", 0, 0),      # Magic, flags
            struct.pack(">i", 2),          # Length of key
            "k1",                          # Key
            struct.pack(">i", 2),          # Length of value
            "v1",                          # Value

            struct.pack(">q", 1),          # MsgSet Offset
            struct.pack(">i", 18),         # Msg Size
            struct.pack(">i", -16383415),  # CRC
            struct.pack(">bb", 0, 0),      # Magic, flags
            struct.pack(">i", 2),          # Length of key
            "k2",                          # Key
            struct.pack(">i", 2),          # Length of value
            "v2",                          # Value
            "@1$%(Y!",                     # Random padding
        ])

        msgs = list(KafkaProtocol._decode_message_set_iter(encoded))
        self.assertEqual(len(msgs), 2)
        msg1, msg2 = msgs

        returned_offset1, decoded_message1 = msg1
        returned_offset2, decoded_message2 = msg2

        self.assertEqual(returned_offset1, 0)
        self.assertEqual(decoded_message1, create_message("v1", "k1"))

        self.assertEqual(returned_offset2, 1)
        self.assertEqual(decoded_message2, create_message("v2", "k2"))

    def test_encode_produce_request(self):
        requests = [
            ProduceRequest("topic1", 0, [
                create_message("a"),
                create_message("b")
            ]),
            ProduceRequest("topic2", 1, [
                create_message("c")
            ])
        ]

        msg_a_binary = KafkaProtocol._encode_message(create_message("a"))
        msg_b_binary = KafkaProtocol._encode_message(create_message("b"))
        msg_c_binary = KafkaProtocol._encode_message(create_message("c"))

        header = "".join([
            struct.pack('>i', 0x94),                   # The length of the message overall
            struct.pack('>h', 0),                      # Msg Header, Message type = Produce
            struct.pack('>h', 0),                      # Msg Header, API version
            struct.pack('>i', 2),                      # Msg Header, Correlation ID
            struct.pack('>h7s', 7, "client1"),         # Msg Header, The client ID
            struct.pack('>h', 2),                      # Num acks required
            struct.pack('>i', 100),                    # Request Timeout
            struct.pack('>i', 2),                      # The number of requests
        ])

        total_len = len(msg_a_binary) + len(msg_b_binary)
        topic1 = "".join([
            struct.pack('>h6s', 6, 'topic1'),          # The topic1
            struct.pack('>i', 1),                      # One message set
            struct.pack('>i', 0),                      # Partition 0
            struct.pack('>i', total_len + 24),         # Size of the incoming message set
            struct.pack('>q', 0),                      # No offset specified
            struct.pack('>i', len(msg_a_binary)),      # Length of message
            msg_a_binary,                              # Actual message
            struct.pack('>q', 0),                      # No offset specified
            struct.pack('>i', len(msg_b_binary)),      # Length of message
            msg_b_binary,                              # Actual message
        ])

        topic2 = "".join([
            struct.pack('>h6s', 6, 'topic2'),          # The topic1
            struct.pack('>i', 1),                      # One message set
            struct.pack('>i', 1),                      # Partition 1
            struct.pack('>i', len(msg_c_binary) + 12), # Size of the incoming message set
            struct.pack('>q', 0),                      # No offset specified
            struct.pack('>i', len(msg_c_binary)),      # Length of message
            msg_c_binary,                              # Actual message
        ])

        expected1 = "".join([ header, topic1, topic2 ])
        expected2 = "".join([ header, topic2, topic1 ])

        encoded = KafkaProtocol.encode_produce_request("client1", 2, requests, 2, 100)
        self.assertIn(encoded, [ expected1, expected2 ])

    def test_decode_produce_response(self):
        t1 = "topic1"
        t2 = "topic2"
        encoded = struct.pack('>iih%dsiihqihqh%dsiihq' % (len(t1), len(t2)),
                              2, 2, len(t1), t1, 2, 0, 0, 10L, 1, 1, 20L,
                              len(t2), t2, 1, 0, 0, 30L)
        responses = list(KafkaProtocol.decode_produce_response(encoded))
        self.assertEqual(responses,
                         [ProduceResponse(t1, 0, 0, 10L),
                          ProduceResponse(t1, 1, 1, 20L),
                          ProduceResponse(t2, 0, 0, 30L)])

    def test_encode_fetch_request(self):
        requests = [
            FetchRequest("topic1", 0, 10, 1024),
            FetchRequest("topic2", 1, 20, 100),
        ]

        header = "".join([
            struct.pack('>i', 89),             # The length of the message overall
            struct.pack('>h', 1),              # Msg Header, Message type = Fetch
            struct.pack('>h', 0),              # Msg Header, API version
            struct.pack('>i', 3),              # Msg Header, Correlation ID
            struct.pack('>h7s', 7, "client1"), # Msg Header, The client ID
            struct.pack('>i', -1),             # Replica Id
            struct.pack('>i', 2),              # Max wait time
            struct.pack('>i', 100),            # Min bytes
            struct.pack('>i', 2),              # Num requests
        ])

        topic1 = "".join([
            struct.pack('>h6s', 6, 'topic1'), # Topic
            struct.pack('>i', 1),             # Num Payloads
            struct.pack('>i', 0),             # Partition 0
            struct.pack('>q', 10),            # Offset
            struct.pack('>i', 1024),          # Max Bytes
        ])

        topic2 = "".join([
            struct.pack('>h6s', 6, 'topic2'), # Topic
            struct.pack('>i', 1),             # Num Payloads
            struct.pack('>i', 1),             # Partition 0
            struct.pack('>q', 20),            # Offset
            struct.pack('>i', 100),           # Max Bytes
        ])

        expected1 = "".join([ header, topic1, topic2 ])
        expected2 = "".join([ header, topic2, topic1 ])

        encoded = KafkaProtocol.encode_fetch_request("client1", 3, requests, 2, 100)
        self.assertIn(encoded, [ expected1, expected2 ])

    def test_decode_fetch_response(self):
        t1 = "topic1"
        t2 = "topic2"
        msgs = map(create_message, ["message1", "hi", "boo", "foo", "so fun!"])
        ms1 = KafkaProtocol._encode_message_set([msgs[0], msgs[1]])
        ms2 = KafkaProtocol._encode_message_set([msgs[2]])
        ms3 = KafkaProtocol._encode_message_set([msgs[3], msgs[4]])

        encoded = struct.pack('>iih%dsiihqi%dsihqi%dsh%dsiihqi%ds' %
                              (len(t1), len(ms1), len(ms2), len(t2), len(ms3)),
                              4, 2, len(t1), t1, 2, 0, 0, 10, len(ms1), ms1, 1,
                              1, 20, len(ms2), ms2, len(t2), t2, 1, 0, 0, 30,
                              len(ms3), ms3)

        responses = list(KafkaProtocol.decode_fetch_response(encoded))
        def expand_messages(response):
            return FetchResponse(response.topic, response.partition,
                                 response.error, response.highwaterMark,
                                 list(response.messages))

        expanded_responses = map(expand_messages, responses)
        expect = [FetchResponse(t1, 0, 0, 10, [OffsetAndMessage(0, msgs[0]),
                                               OffsetAndMessage(0, msgs[1])]),
                  FetchResponse(t1, 1, 1, 20, [OffsetAndMessage(0, msgs[2])]),
                  FetchResponse(t2, 0, 0, 30, [OffsetAndMessage(0, msgs[3]),
                                               OffsetAndMessage(0, msgs[4])])]
        self.assertEqual(expanded_responses, expect)

    def test_encode_metadata_request_no_topics(self):
        expected = "".join([
            struct.pack(">i", 17),         # Total length of the request
            struct.pack('>h', 3),          # API key metadata fetch
            struct.pack('>h', 0),          # API version
            struct.pack('>i', 4),          # Correlation ID
            struct.pack('>h3s', 3, "cid"), # The client ID
            struct.pack('>i', 0),          # No topics, give all the data!
        ])

        encoded = KafkaProtocol.encode_metadata_request("cid", 4)

        self.assertEqual(encoded, expected)

    def test_encode_metadata_request_with_topics(self):
        expected = "".join([
            struct.pack(">i", 25),         # Total length of the request
            struct.pack('>h', 3),          # API key metadata fetch
            struct.pack('>h', 0),          # API version
            struct.pack('>i', 4),          # Correlation ID
            struct.pack('>h3s', 3, "cid"), # The client ID
            struct.pack('>i', 2),          # Number of topics in the request
            struct.pack('>h2s', 2, "t1"),  # Topic "t1"
            struct.pack('>h2s', 2, "t2"),  # Topic "t2"
        ])

        encoded = KafkaProtocol.encode_metadata_request("cid", 4, ["t1", "t2"])

        self.assertEqual(encoded, expected)

    def _create_encoded_metadata_response(self, broker_data, topic_data,
                                          topic_errors, partition_errors):
        encoded = struct.pack('>ii', 3, len(broker_data))
        for node_id, broker in broker_data.iteritems():
            encoded += struct.pack('>ih%dsi' % len(broker.host), node_id,
                                   len(broker.host), broker.host, broker.port)

        encoded += struct.pack('>i', len(topic_data))
        for topic, partitions in topic_data.iteritems():
            encoded += struct.pack('>hh%dsi' % len(topic), topic_errors[topic],
                                   len(topic), topic, len(partitions))
            for partition, metadata in partitions.iteritems():
                encoded += struct.pack('>hiii',
                                       partition_errors[(topic, partition)],
                                       partition, metadata.leader,
                                       len(metadata.replicas))
                if len(metadata.replicas) > 0:
                    encoded += struct.pack('>%di' % len(metadata.replicas),
                                           *metadata.replicas)

                encoded += struct.pack('>i', len(metadata.isr))
                if len(metadata.isr) > 0:
                    encoded += struct.pack('>%di' % len(metadata.isr),
                                           *metadata.isr)

        return encoded

    def test_decode_metadata_response(self):
        node_brokers = {
            0: BrokerMetadata(0, "brokers1.kafka.rdio.com", 1000),
            1: BrokerMetadata(1, "brokers1.kafka.rdio.com", 1001),
            3: BrokerMetadata(3, "brokers2.kafka.rdio.com", 1000)
        }

        topic_partitions = {
            "topic1": {
                0: PartitionMetadata("topic1", 0, 1, (0, 2), (2,)),
                1: PartitionMetadata("topic1", 1, 3, (0, 1), (0, 1))
            },
            "topic2": {
                0: PartitionMetadata("topic2", 0, 0, (), ())
            }
        }
        topic_errors = {"topic1": 0, "topic2": 1}
        partition_errors = {
            ("topic1", 0): 0,
            ("topic1", 1): 1,
            ("topic2", 0): 0
        }
        encoded = self._create_encoded_metadata_response(node_brokers,
                                                         topic_partitions,
                                                         topic_errors,
                                                         partition_errors)
        decoded = KafkaProtocol.decode_metadata_response(encoded)
        self.assertEqual(decoded, (node_brokers, topic_partitions))

    def test_encode_offset_request(self):
        expected = "".join([
            struct.pack(">i", 21),         # Total length of the request
            struct.pack('>h', 2),          # Message type = offset fetch
            struct.pack('>h', 0),          # API version
            struct.pack('>i', 4),          # Correlation ID
            struct.pack('>h3s', 3, "cid"), # The client ID
            struct.pack('>i', -1),         # Replica Id
            struct.pack('>i', 0),          # No topic/partitions
        ])

        encoded = KafkaProtocol.encode_offset_request("cid", 4)

        self.assertEqual(encoded, expected)

    def test_encode_offset_request__no_payload(self):
        expected = "".join([
            struct.pack(">i", 65),            # Total length of the request

            struct.pack('>h', 2),             # Message type = offset fetch
            struct.pack('>h', 0),             # API version
            struct.pack('>i', 4),             # Correlation ID
            struct.pack('>h3s', 3, "cid"),    # The client ID
            struct.pack('>i', -1),            # Replica Id
            struct.pack('>i', 1),             # Num topics
            struct.pack(">h6s", 6, "topic1"), # Topic for the request
            struct.pack(">i", 2),             # Two partitions

            struct.pack(">i", 3),             # Partition 3
            struct.pack(">q", -1),            # No time offset
            struct.pack(">i", 1),             # One offset requested

            struct.pack(">i", 4),             # Partition 3
            struct.pack(">q", -1),            # No time offset
            struct.pack(">i", 1),             # One offset requested
        ])

        encoded = KafkaProtocol.encode_offset_request("cid", 4, [
            OffsetRequest('topic1', 3, -1, 1),
            OffsetRequest('topic1', 4, -1, 1),
        ])

        self.assertEqual(encoded, expected)

    def test_decode_offset_response(self):
        encoded = "".join([
            struct.pack(">i", 42),            # Correlation ID
            struct.pack(">i", 1),             # One topics
            struct.pack(">h6s", 6, "topic1"), # First topic
            struct.pack(">i", 2),             # Two partitions

            struct.pack(">i", 2),             # Partition 2
            struct.pack(">h", 0),             # No error
            struct.pack(">i", 1),             # One offset
            struct.pack(">q", 4),             # Offset 4

            struct.pack(">i", 4),             # Partition 4
            struct.pack(">h", 0),             # No error
            struct.pack(">i", 1),             # One offset
            struct.pack(">q", 8),             # Offset 8
        ])

        results = KafkaProtocol.decode_offset_response(encoded)
        self.assertEqual(set(results), set([
            OffsetResponse(topic = 'topic1', partition = 2, error = 0, offsets=(4,)),
            OffsetResponse(topic = 'topic1', partition = 4, error = 0, offsets=(8,)),
        ]))

    def test_encode_offset_commit_request(self):
        header = "".join([
            struct.pack('>i', 99),               # Total message length

            struct.pack('>h', 8),                # Message type = offset commit
            struct.pack('>h', 0),                # API version
            struct.pack('>i', 42),               # Correlation ID
            struct.pack('>h9s', 9, "client_id"), # The client ID
            struct.pack('>h8s', 8, "group_id"),  # The group to commit for
            struct.pack('>i', 2),                # Num topics
        ])

        topic1 = "".join([
            struct.pack(">h6s", 6, "topic1"),    # Topic for the request
            struct.pack(">i", 2),                # Two partitions
            struct.pack(">i", 0),                # Partition 0
            struct.pack(">q", 123),              # Offset 123
            struct.pack(">h", -1),               # Null metadata
            struct.pack(">i", 1),                # Partition 1
            struct.pack(">q", 234),              # Offset 234
            struct.pack(">h", -1),               # Null metadata
        ])

        topic2 = "".join([
            struct.pack(">h6s", 6, "topic2"),    # Topic for the request
            struct.pack(">i", 1),                # One partition
            struct.pack(">i", 2),                # Partition 2
            struct.pack(">q", 345),              # Offset 345
            struct.pack(">h", -1),               # Null metadata
        ])

        expected1 = "".join([ header, topic1, topic2 ])
        expected2 = "".join([ header, topic2, topic1 ])

        encoded = KafkaProtocol.encode_offset_commit_request("client_id", 42, "group_id", [
            OffsetCommitRequest("topic1", 0, 123, None),
            OffsetCommitRequest("topic1", 1, 234, None),
            OffsetCommitRequest("topic2", 2, 345, None),
        ])

        self.assertIn(encoded, [ expected1, expected2 ])

    def test_decode_offset_commit_response(self):
        encoded = "".join([
            struct.pack(">i", 42),            # Correlation ID
            struct.pack(">i", 1),             # One topic
            struct.pack(">h6s", 6, "topic1"), # First topic
            struct.pack(">i", 2),             # Two partitions

            struct.pack(">i", 2),             # Partition 2
            struct.pack(">h", 0),             # No error

            struct.pack(">i", 4),             # Partition 4
            struct.pack(">h", 0),             # No error
        ])

        results = KafkaProtocol.decode_offset_commit_response(encoded)
        self.assertEqual(set(results), set([
            OffsetCommitResponse(topic = 'topic1', partition = 2, error = 0),
            OffsetCommitResponse(topic = 'topic1', partition = 4, error = 0),
        ]))

    def test_encode_offset_fetch_request(self):
        header = "".join([
            struct.pack('>i', 69),               # Total message length
            struct.pack('>h', 9),                # Message type = offset fetch
            struct.pack('>h', 0),                # API version
            struct.pack('>i', 42),               # Correlation ID
            struct.pack('>h9s', 9, "client_id"), # The client ID
            struct.pack('>h8s', 8, "group_id"),  # The group to commit for
            struct.pack('>i', 2),                # Num topics
        ])

        topic1 = "".join([
            struct.pack(">h6s", 6, "topic1"),    # Topic for the request
            struct.pack(">i", 2),                # Two partitions
            struct.pack(">i", 0),                # Partition 0
            struct.pack(">i", 1),                # Partition 1
        ])

        topic2 = "".join([
            struct.pack(">h6s", 6, "topic2"),    # Topic for the request
            struct.pack(">i", 1),                # One partitions
            struct.pack(">i", 2),                # Partition 2
        ])

        expected1 = "".join([ header, topic1, topic2 ])
        expected2 = "".join([ header, topic2, topic1 ])

        encoded = KafkaProtocol.encode_offset_fetch_request("client_id", 42, "group_id", [
            OffsetFetchRequest("topic1", 0),
            OffsetFetchRequest("topic1", 1),
            OffsetFetchRequest("topic2", 2),
        ])

        self.assertIn(encoded, [ expected1, expected2 ])

    def test_decode_offset_fetch_response(self):
        encoded = "".join([
            struct.pack(">i", 42),            # Correlation ID
            struct.pack(">i", 1),             # One topics
            struct.pack(">h6s", 6, "topic1"), # First topic
            struct.pack(">i", 2),             # Two partitions

            struct.pack(">i", 2),             # Partition 2
            struct.pack(">q", 4),             # Offset 4
            struct.pack(">h4s", 4, "meta"),   # Metadata
            struct.pack(">h", 0),             # No error

            struct.pack(">i", 4),             # Partition 4
            struct.pack(">q", 8),             # Offset 8
            struct.pack(">h4s", 4, "meta"),   # Metadata
            struct.pack(">h", 0),             # No error
        ])

        results = KafkaProtocol.decode_offset_fetch_response(encoded)
        self.assertEqual(set(results), set([
            OffsetFetchResponse(topic = 'topic1', partition = 2, offset = 4, error = 0, metadata = "meta"),
            OffsetFetchResponse(topic = 'topic1', partition = 4, offset = 8, error = 0, metadata = "meta"),
        ]))

    @contextmanager
    def mock_create_message_fns(self):
        patches = contextlib.nested(
            mock.patch.object(kafka.protocol, "create_message",
                              return_value=sentinel.message),
            mock.patch.object(kafka.protocol, "create_gzip_message",
                              return_value=sentinel.gzip_message),
            mock.patch.object(kafka.protocol, "create_snappy_message",
                              return_value=sentinel.snappy_message),
        )

        with patches:
            yield

    def test_create_message_set(self):
        messages = [1, 2, 3]

        # Default codec is CODEC_NONE. Expect list of regular messages.
        expect = [sentinel.message] * len(messages)
        with self.mock_create_message_fns():
            message_set = create_message_set(messages)
        self.assertEqual(message_set, expect)

        # CODEC_NONE: Expect list of regular messages.
        expect = [sentinel.message] * len(messages)
        with self.mock_create_message_fns():
            message_set = create_message_set(messages, CODEC_NONE)
        self.assertEqual(message_set, expect)

        # CODEC_GZIP: Expect list of one gzip-encoded message.
        expect = [sentinel.gzip_message]
        with self.mock_create_message_fns():
            message_set = create_message_set(messages, CODEC_GZIP)
        self.assertEqual(message_set, expect)

        # CODEC_SNAPPY: Expect list of one snappy-encoded message.
        expect = [sentinel.snappy_message]
        with self.mock_create_message_fns():
            message_set = create_message_set(messages, CODEC_SNAPPY)
        self.assertEqual(message_set, expect)

        # Unknown codec should raise UnsupportedCodecError.
        with self.assertRaises(UnsupportedCodecError):
            create_message_set(messages, -1)

########NEW FILE########
__FILENAME__ = test_util
import os
import random
import struct
import unittest2
import kafka.util
import kafka.common

class UtilTest(unittest2.TestCase):
    @unittest2.skip("Unwritten")
    def test_relative_unpack(self):
        pass

    def test_write_int_string(self):
        self.assertEqual(
            kafka.util.write_int_string('some string'),
            '\x00\x00\x00\x0bsome string'
        )

    def test_write_int_string__empty(self):
        self.assertEqual(
            kafka.util.write_int_string(''),
            '\x00\x00\x00\x00'
        )

    def test_write_int_string__null(self):
        self.assertEqual(
            kafka.util.write_int_string(None),
            '\xff\xff\xff\xff'
        )

    def test_read_int_string(self):
        self.assertEqual(kafka.util.read_int_string('\xff\xff\xff\xff', 0), (None, 4))
        self.assertEqual(kafka.util.read_int_string('\x00\x00\x00\x00', 0), ('', 4))
        self.assertEqual(kafka.util.read_int_string('\x00\x00\x00\x0bsome string', 0), ('some string', 15))

    def test_read_int_string__insufficient_data(self):
        with self.assertRaises(kafka.common.BufferUnderflowError):
            kafka.util.read_int_string('\x00\x00\x00\x021', 0)

    def test_write_short_string(self):
        self.assertEqual(
            kafka.util.write_short_string('some string'),
            '\x00\x0bsome string'
        )

    def test_write_short_string__empty(self):
        self.assertEqual(
            kafka.util.write_short_string(''),
            '\x00\x00'
        )

    def test_write_short_string__null(self):
        self.assertEqual(
            kafka.util.write_short_string(None),
            '\xff\xff'
        )

    def test_write_short_string__too_long(self):
        with self.assertRaises(struct.error):
            kafka.util.write_short_string(' ' * 33000)

    def test_read_short_string(self):
        self.assertEqual(kafka.util.read_short_string('\xff\xff', 0), (None, 2))
        self.assertEqual(kafka.util.read_short_string('\x00\x00', 0), ('', 2))
        self.assertEqual(kafka.util.read_short_string('\x00\x0bsome string', 0), ('some string', 13))

    def test_read_int_string__insufficient_data(self):
        with self.assertRaises(kafka.common.BufferUnderflowError):
            kafka.util.read_int_string('\x00\x021', 0)

    def test_relative_unpack(self):
        self.assertEqual(
            kafka.util.relative_unpack('>hh', '\x00\x01\x00\x00\x02', 0),
            ((1, 0), 4)
        )

    def test_relative_unpack(self):
        with self.assertRaises(kafka.common.BufferUnderflowError):
            kafka.util.relative_unpack('>hh', '\x00', 0)


    def test_group_by_topic_and_partition(self):
        t = kafka.common.TopicAndPartition

        l = [
            t("a", 1),
            t("a", 1),
            t("a", 2),
            t("a", 3),
            t("b", 3),
        ]

        self.assertEqual(kafka.util.group_by_topic_and_partition(l), {
            "a" : {
                1 : t("a", 1),
                2 : t("a", 2),
                3 : t("a", 3),
            },
            "b" : {
                3 : t("b", 3),
            }
        })

########NEW FILE########
