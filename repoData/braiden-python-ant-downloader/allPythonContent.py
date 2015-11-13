__FILENAME__ = ant-downloader
#!/usr/bin/env python
from antd.main import downloader
downloader()

########NEW FILE########
__FILENAME__ = ant
# Copyright (c) 2012, Braiden Kindt.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
# 
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDER AND CONTRIBUTORS
# ''AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY
# WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.


import threading
import logging
import array
import errno
import time
import struct
import collections

_log = logging.getLogger("antd.ant")
_trace = logging.getLogger("antd.trace")

# first byte of an packet
SYNC = 0xA4
# direction of command
DIR_IN = "IN"
DIR_OUT = "OUT"
# channel response codes
RESPONSE_NO_ERROR = 0
CHANNEL_IN_WRONG_STATE = 21
CHANNEL_NOT_OPENED = 22
CHANNEL_ID_NOT_SET = 24
CLOSE_ALL_CHANNELS = 25
TRANSFER_IN_PROGRESS = 31
TRANSFER_SEQUENCE_NUMBER_ERROR = 32
TANNSFER_IN_ERROR = 33
MESSAGE_SIZE_EXCEEDS_LIMIT = 39
INVALID_MESSAGE = 40
INVALID_NETWORK_NUMBER = 41
INVALID_LIST_ID = 48
INVALID_SCAN_TX_CHANNEL = 49
INVALID_PARAMETER_PROVIDED = 51
NVM_FULL_ERROR = 64
NVM_WRITE_ERROR = 65
USB_STRING_WRITE_FAIL = 112
MESG_SERIAL_ERROR_ID = 174
# rf event codes
EVENT_RX_SEARCH_TIMEOUT = 1
EVENT_RX_FAIL = 2
EVENT_TX = 3
EVENT_TRANSFER_RX_FAILED = 4
EVENT_TRANSFER_TX_COMPLETED = 5
EVENT_TRANSFER_TX_FAILED = 6
EVENT_CHANNEL_CLOSED = 7
EVENT_RX_FAIL_GO_TO_SEARCH = 8
EVENT_CHANNEL_COLLISION = 9
EVENT_TRANSFER_TX_START = 10
EVENT_SERIAL_QUE_OVERFLOW = 52
EVENT_QUEUE_OVERFLOW = 53
# channel status
CHANNEL_STATUS_UNASSIGNED = 0
CHANNEL_STATUS_ASSIGNED = 1
CHANNEL_STATUS_SEARCHING = 2
CHANNEL_STATUS_TRACKING = 3

class AntError(Exception):
    """
    Default error, unless a more specific error
    instance is provided, usually indicates that
    the ANT hardware rejected command. Usually do
    to invalid state / API usage.
    """
class AntTimeoutError(AntError):
    """
    An expected reply was not received from hardware.
    For "recv_*()" and "read()" operations timeout is
    safely retryable. For other types of commands, do
    not assume timeout means command did not take effect.
    This is particularly true for Acknowledged writes.
    For such timeouts, restarting ANT session is usually
    only course of action.
    """
class AntTxFailedError(AntError):
    """
    An Acknowledged message of burst transfer failed
    to transmit successfully. Retry is typically safe
    but recovery for burst is application dependent.
    """
class AntChannelClosedError(AntError):
    """
    Raise while attempty to read / write to a closed
    channel, or if a channel transitions to closed
    while a read / write is running. (channel may
    be closed due to search timeout expiring.)
    """

def msg_to_string(msg):
    """
    Retruns a string representation of
    the provided array (for debug output)
    """
    return array.array("B", msg).tostring().encode("hex")

def is_timeout(ioerror):
    """
    True if ioerror can be categorized as a timeout.
    """
    try:
        # all IOerrors returned by pyusb contain
        # msg, errno, and should be unpackable.
        err, msg = ioerror
    except ValueError:
        # but, sometimes we can't unpack. I don't
        # know what is raising theses IOErrors
        # just assume its a timeout, so operation
        # is retried
        return True
    else:
        return (err == errno.ETIMEDOUT #libusb10
                or msg == "Connection timed out") #libusb01

def generate_checksum(msg):
    """
    Generate a checksum of the given msg.
    xor of all bytes.
    """
    return reduce(lambda x, y: x ^ y, msg)

def validate_checksum(msg):
    """
    Retrun true if message has valid checksum
    """
    return generate_checksum(msg) == 0

def tokenize_message(msg):
    """
    A generator returning on ant messages
    from the provided string of one or more
    conacatinated messages.
    """
    while msg:
        assert msg[0] & 0xFE == SYNC
        length = msg[1]
        yield msg[:4 + length]
        msg = msg[4 + length:]

def data_tostring(data):
    """
    Return a string repenting bytes of given
    data. used by send() methods to convert
    arugment to required string.
    """
    if isinstance(data, list):
        return array.array("B", data).tostring()
    elif isinstance(data, array.array):
        return data.tostring()
    else:
        return data

# retry policies define the strategy used to
# determin if a command should be retried based
# on provided error. They can be configured
# for each ANT message defined below. Retry
# on timeout should be considered dangerous.
# e.g. retrying a timedout acknowledged message
# will certainly fail.

def timeout_retry_policy(error):
    return default_retry_policy(error) or isinstance(error, AntTimeoutError)

def default_retry_policy(error):
    return isinstance(error, AntTxFailedError)

def always_retry_policy(error):
    return True

def never_retry_policy(error):
    return False

def wait_and_retry_policy(error):
    if default_retry_policy(error):
        time.sleep(1)
        return True
    else:
        return False

# matcher define the strategry to determine
# if an incoming message from ANT device sould
# udpate the status of a running command.

def same_channel_or_network_matcher(request, reply):
    return (
            (not hasattr(reply, "channel_number")
             or (hasattr(request, "channel_number") and (0x1f & request.channel_number) == (0x1f & reply.channel_number)))
        or 
            (not hasattr(reply, "network_number")
             or (hasattr(request, "network_number") and request.network_number == reply.network_number)))

def default_matcher(request, reply):
    return (same_channel_or_network_matcher(request, reply) 
            and isinstance(reply, ChannelEvent)
            and reply.msg_id == request.ID)

def reset_matcher(request, reply):
    return isinstance(reply, StartupMessage)

def close_channel_matcher(request, reply):
    return same_channel_or_network_matcher(request, reply) and (
            (isinstance(reply, ChannelEvent)
             and reply.msg_id == CloseChannel.ID
             and reply.msg_code != 0)
        or (isinstance(reply, ChannelEvent)
             and reply.msg_id == 1
             and reply.msg_code == EVENT_CHANNEL_CLOSED))

def request_message_matcher(request, reply):
    return default_matcher(request, reply) or reply.ID == request.msg_id

def recv_broadcast_matcher(request, reply):
    return (close_channel_matcher(request, reply)
        or isinstance(reply, RecvBroadcastData))

def send_data_matcher(request, reply):
    return (close_channel_matcher(request, reply)
        or (isinstance(reply, ChannelEvent)
            and reply.msg_id == 1
            and reply.msg_code in (EVENT_TX, EVENT_TRANSFER_TX_COMPLETED, EVENT_TRANSFER_TX_FAILED)))

# validators define stragegy for determining
# if a give reply from ANT should raise an
# error. 

def default_validator(request, reply):
    if isinstance(reply, ChannelEvent) and reply.msg_code in (EVENT_CHANNEL_CLOSED, CHANNEL_NOT_OPENED):
        return AntChannelClosedError("Channel closed. %s" % reply)
    elif isinstance(reply, ChannelEvent) and reply.msg_code != RESPONSE_NO_ERROR:
        return AntError("Failed to execute command message_code=%d. %s" % (reply.msg_code, reply))

def close_channel_validator(request, reply):
    if not (isinstance(reply, ChannelEvent) and reply.msg_id == 1 and reply.msg_code == EVENT_CHANNEL_CLOSED):
        return default_validator(request, reply)

def send_data_validator(request, reply):
    if isinstance(reply, ChannelEvent) and reply.msg_id == 1 and reply.msg_code == EVENT_TRANSFER_TX_FAILED:
        return AntTxFailedError("Send message was not acknowledged by peer. %s" % reply)
    elif not (isinstance(reply, ChannelEvent) and reply.msg_id == 1 and reply.msg_code in (EVENT_TX, EVENT_TRANSFER_TX_COMPLETED)):
        return default_validator(request, reply)

def message(direction, name, id, pack_format, arg_names, retry_policy=default_retry_policy, matcher=default_matcher, validator=default_validator):
    """
    Return a class supporting basic packing
    operations with the give metadata.
    """
    # pre-create the struct used to pack/unpack this message format
    if pack_format:
        byte_order_and_size = ""
        if pack_format[0] not in ("@", "=", "<", ">", "!"):
            # apply default by order and size
            byte_order_and_size = "<"
        msg_struct = struct.Struct(byte_order_and_size + pack_format)
    else:
        msg_struct = None

    # create named-tuple used to converting *arg, **kwds to this messages args
    msg_arg_tuple = collections.namedtuple(name, arg_names)

    # class representing the message definition pased to this method
    class Message(object):

        DIRECTION = direction
        NAME = name
        ID = id

        def __init__(self, *args, **kwds):
            tuple = msg_arg_tuple(*args, **kwds)
            self.__dict__.update(tuple._asdict())

        @property
        def args(self):
            return msg_arg_tuple(**dict((k, v) for k, v in self.__dict__.items() if k in arg_names))

        @classmethod
        def unpack_args(cls, packed_args):
            try: return Message(*msg_struct.unpack(packed_args))
            except AttributeError: return Message(*([None] * len(arg_names)))

        def pack_args(self):
            try: return msg_struct.pack(*self.args)
            except AttributeError: pass
        
        def pack_size(self):
            try: return msg_struct.size
            except AttributeError: return 0

        def is_retryable(self, err):
            return retry_policy(err)

        def is_reply(self, cmd):
            return matcher(self, cmd)

        def validate_reply(self, cmd):
            return validator(self, cmd)

        def __str__(self):
            return str(self.args)

    return Message

# ANT Message Protocol Definitions
UnassignChannel = message(DIR_OUT, "UNASSIGN_CHANNEL", 0x41, "B", ["channel_number"], retry_policy=timeout_retry_policy)
AssignChannel = message(DIR_OUT, "ASSIGN_CHANNEL", 0x42, "BBB", ["channel_number", "channel_type", "network_number"], retry_policy=timeout_retry_policy)
SetChannelId = message(DIR_OUT, "SET_CHANNEL_ID", 0x51, "BHBB", ["channel_number", "device_number", "device_type_id", "trans_type"], retry_policy=timeout_retry_policy)
SetChannelPeriod = message(DIR_OUT, "SET_CHANNEL_PERIOD", 0x43, "BH", ["channel_number", "messaging_period"], retry_policy=timeout_retry_policy) 
SetChannelSearchTimeout = message(DIR_OUT, "SET_CHANNEL_SEARCH_TIMEOUT", 0x44, "BB", ["channel_number", "search_timeout"], retry_policy=timeout_retry_policy)
SetChannelRfFreq = message(DIR_OUT, "SET_CHANNEL_RF_FREQ", 0x45, "BB", ["channel_number", "rf_freq"], retry_policy=timeout_retry_policy)
SetNetworkKey = message(DIR_OUT, "SET_NETWORK_KEY", 0x46, "B8s", ["network_number", "network_key"], retry_policy=timeout_retry_policy)
ResetSystem = message(DIR_OUT, "RESET_SYSTEM", 0x4a, "x", [], retry_policy=always_retry_policy, matcher=reset_matcher)
OpenChannel = message(DIR_OUT, "OPEN_CHANNEL", 0x4b, "B", ["channel_number"], retry_policy=timeout_retry_policy)
CloseChannel = message(DIR_OUT, "CLOSE_CHANNEL", 0x4c, "B", ["channel_number"], retry_policy=timeout_retry_policy, matcher=close_channel_matcher, validator=close_channel_validator)
RequestMessage = message(DIR_OUT, "REQUEST_MESSAGE", 0x4d, "BB", ["channel_number", "msg_id"], retry_policy=timeout_retry_policy, matcher=request_message_matcher)
SetSearchWaveform = message(DIR_OUT, "SET_SEARCH_WAVEFORM", 0x49, "BH", ["channel_number", "waveform"], retry_policy=timeout_retry_policy)
SendBroadcastData = message(DIR_OUT, "SEND_BROADCAST_DATA", 0x4e, "B8s", ["channel_number", "data"], matcher=send_data_matcher, validator=send_data_validator)
SendAcknowledgedData = message(DIR_OUT, "SEND_ACKNOWLEDGED_DATA", 0x4f, "B8s", ["channel_number", "data"], retry_policy=wait_and_retry_policy, matcher=send_data_matcher, validator=send_data_validator)
SendBurstTransferPacket = message(DIR_OUT, "SEND_BURST_TRANSFER_PACKET", 0x50, "B8s", ["channel_number", "data"], retry_policy=wait_and_retry_policy, matcher=send_data_matcher, validator=send_data_validator)
StartupMessage = message(DIR_IN, "STARTUP_MESSAGE", 0x6f, "B", ["startup_message"])
SerialError = message(DIR_IN, "SERIAL_ERROR", 0xae, None, ["error_number", "msg_contents"])
RecvBroadcastData = message(DIR_IN, "RECV_BROADCAST_DATA", 0x4e, "B8s", ["channel_number", "data"])
RecvAcknowledgedData = message(DIR_IN, "RECV_ACKNOWLEDGED_DATA", 0x4f, "B8s", ["channel_number", "data"])
RecvBurstTransferPacket = message(DIR_IN, "RECV_BURST_TRANSFER_PACKET", 0x50, "B8s", ["channel_number", "data"])
ChannelEvent = message(DIR_IN, "CHANNEL_EVENT", 0x40, "BBB", ["channel_number", "msg_id", "msg_code"])
ChannelStatus = message(DIR_IN, "CHANNEL_STATUS", 0x52, "BB", ["channel_number", "channel_status"])
ChannelId = message(DIR_IN, "CHANNEL_ID", 0x51, "BHBB", ["channel_number", "device_number", "device_type_id", "man_id"])
AntVersion = message(DIR_IN, "VERSION", 0x3e, "11s", ["ant_version"])
#Capabilities = message(DIR_IN, "CAPABILITIES", 0x54, "BBBBBx", ["max_channels", "max_networks", "standard_opts", "advanced_opts1", "advanced_opts2"])
SerialNumber = message(DIR_IN, "SERIAL_NUMBER", 0x61, "I", ["serial_number"])
# Synthetic Commands
UnimplementedCommand = message(None, "UNIMPLEMENTED_COMMAND", None, None, ["msg_id", "msg_contents"])

# hack, capabilites may be 4 (AP1) or 6 (AP2) bytes
class Capabilities(message(DIR_IN, "CAPABILITIES", 0x54, "BBBB", ["max_channels", "max_networks", "standard_opts", "advanced_opts1"])):

    @classmethod
    def unpack_args(cls, packed_args):
        return super(Capabilities, cls).unpack_args(packed_args[:4])


ALL_ANT_COMMANDS = [ UnassignChannel, AssignChannel, SetChannelId, SetChannelPeriod, SetChannelSearchTimeout,
                     SetChannelRfFreq, SetNetworkKey, ResetSystem, OpenChannel, CloseChannel, RequestMessage,
                     SetSearchWaveform, SendBroadcastData, SendAcknowledgedData, SendBurstTransferPacket,
                     StartupMessage, SerialError, RecvBroadcastData, RecvAcknowledgedData, RecvBurstTransferPacket,
                     ChannelEvent, ChannelStatus, ChannelId, AntVersion, Capabilities, SerialNumber ]

class ReadData(RequestMessage):
    """
    A phony command which is pushed to request data from client.
    This command will remain runnning as long as the channel is
    in a state where read is valid, and raise error if channel
    transitions to a state where read is impossible. Its kind-of
    an ugly hack so that channel status causes exceptions in read.
    """

    def __init__(self, channel_id, data_type):
        super(ReadData, self).__init__(channel_id, ChannelStatus.ID)
        self.data_type = data_type
    
    def is_retryable(self):
        return False

    def is_reply(self, cmd):
        return ((same_channel_or_network_matcher(self, cmd)
                    and isinstance(cmd, ChannelStatus)
                    and cmd.channel_status & 0x03 not in (CHANNEL_STATUS_SEARCHING, CHANNEL_STATUS_TRACKING))
                or close_channel_matcher(self, cmd))

    def validate_reply(self, cmd):
        return AntChannelClosedError("Channel closed. %s" % cmd)
    
    def __str__(self):
        return "ReadData(channel_number=%d)" % self.channel_number

class SendBurstData(SendBurstTransferPacket):

    data = None
    channel_number = None

    def __init__(self, channel_number, data):
        if len(data) <= 8: channel_number |= 0x80
        super(SendBurstData, self).__init__(channel_number, data)

    @property
    def done(self):
        return self._done

    @done.setter
    def done(self, value):
        self._done = value
        self.seq_num = 0
        self.index = 0
        self.incr_packet_index()

    def create_next_packet(self):
        """
        Return a command which can be exceuted
        to deliver the next packet of this burst.
        """
        is_last_packet = self.index + 8 >= len(self.data)
        data = self.data[self.index:self.index + 8]
        channel_number = self.channel_number | ((self.seq_num & 0x03) << 5) | (0x80 if is_last_packet else 0x00)
        return SendBurstTransferPacket(channel_number, data)
    
    def incr_packet_index(self):
        """
        Increment the pointer for data in next packet.
        create_next_packet() will update index until
        this method is called.
        """
        self.seq_num += 1
        if not self.seq_num & 0x03: self.seq_num += 1
        self.index += 8
        self.has_more_data = self.index < len(self.data)

    def __str__(self):
        return "SEND_BURST_COMMAND(channel_number=%d)" % self.channel_number


class Core(object):
    """
    Asynchronous ANT api.
    """
    
    def __init__(self, hardware, messages=ALL_ANT_COMMANDS):
        self.hardware = hardware
        self.input_msg_by_id = dict((m.ID, m) for m in messages if m.DIRECTION == DIR_IN)
        # per ant protocol doc, writing 15 zeros
        # should reset internal state of device.
        #self.hardware.write([0] * 15, 100)

    def close(self):
        self.hardware.close()

    def pack(self, command):
        """
        Return an array of bytes representing
        the data which needs to be written to
        hardware to execute the given command.
        """
        if command.ID is not None:
            if command.DIRECTION != DIR_OUT:
                _log.warning("Request to pack input message. %s", command)
            msg = [SYNC, command.pack_size(), command.ID]
            msg_args = command.pack_args()
            if msg_args is not None:
                msg.extend(array.array("B", msg_args))
                msg.append(generate_checksum(msg))
                return msg
    
    def unpack(self, msg):
        """
        Return the command represented by
        the given byte ANT array.
        """
        if not validate_checksum(msg):
            _log.error("Invalid checksum, mesage discarded. %s", msg_to_string(msg))
            return None
        sync, length, msg_id = msg[:3]
        try:
            command_class = self.input_msg_by_id[msg_id]
        except (KeyError):
            _log.warning("Attempt to unpack unkown message (0x%02x). %s", msg_id, msg_to_string(msg))
            return UnimplementedCommand(msg_id, msg)
        else:
            return command_class.unpack_args(array.array("B", msg[3:-1]).tostring())

    def send(self, command, timeout=100):
        """
        Execute the given command. Returns true
        if command was written to device. False
        if the device nack'd the write. When
        the method returns false, caller should
        retry.
        """
        msg = self.pack(command)
        if not msg: return True
        _trace.debug("SEND: %s", msg_to_string(msg))
        # ant protocol states \x00\x00 padding is optional.
        # libusb01 is quirky when using multiple threads?
        # adding the \00's seems to help with occasional issue
        # where read can block indefinitely until more data
        # is received.
        msg.extend([0] * 2)
        try:
            self.hardware.write(msg, timeout)
            return True
        except IOError as err:
            if is_timeout(err): return False
            else: raise

    def recv(self, timeout=1000):
        """
        A generator which return commands
        parsed from input stream of ant device.
        StopIteration raised when input stream empty.
        """
        while True:
            try:
                # tokenize message (possibly more than on per read)
                for msg in tokenize_message(self.hardware.read(timeout)):
                    _trace.debug("RECV: %s", msg_to_string(msg))
                    cmd = self.unpack(msg)
                    if cmd: yield cmd
            except IOError as err:
                # iteration terminates on timeout
                if is_timeout(err): raise StopIteration()
                else: raise


class Session(object):
    """
    Provides synchronous (blocking) API
    on top of basic (Core) ANT impl.
    """

    default_read_timeout = 5
    default_write_timeout = 5
    default_retry = 9

    channels = []
    networks = []
    _recv_buffer = []
    _burst_buffer = []

    def __init__(self, core):
        self.core = core
        self.running = False
        self.running_cmd = None
        try:
            self._start()
        except Exception as e:
            try: self.close()
            except Exception: _log.warning("Caught exception trying to cleanup resources.", exc_info=True)
            finally: raise e
    
    def _start(self):
        """
        Start the message consumer thread.
        """
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.loop)
            self.thread.daemon = True
            self.thread.start()
            self.reset_system()

    def close(self):
        """
        Stop the message consumer thread.
        """
        try:
            self.reset_system()
            self.running = False
            self.thread.join(1)
            self.core.close()
            assert not self.thread.is_alive()
        except AttributeError: pass

    def reset_system(self):
        """
        Reset the and device and initialize
        channel/network properties.
        """
        self._send(ResetSystem(), timeout=.5, retry=5)
        if not self.channels:
            _log.debug("Querying ANT capabilities")
            cap = self.get_capabilities() 
            #ver = self.get_ant_version()
            #sn = self.get_serial_number()
            _log.debug("Device Capabilities: %s", cap)
            #_log.debug("Device ANT Version: %s", ver)
            #_log.debug("Device SN#: %s", sn)
            self.channels = [Channel(self, n) for n in range(0, cap.max_channels)]
            self.networks = [Network(self, n) for n in range(0, cap.max_networks)]
        self._recv_buffer = [[]] * len(self.channels)
        self._burst_buffer = [[]] * len(self.channels)

    def get_capabilities(self):
        """
        Return the capabilities of this device. 9.5.7.4
        """
        return self._send(RequestMessage(0, Capabilities.ID))

    def get_ant_version(self):
        """
        Return the version on ANT firmware on device. 9.5.7.3
        """
        return self._send(RequestMessage(0, AntVersion.ID))

    def get_serial_number(self):
        """
        Return SN# of and device. 9.5.7.5
        """
        return self._send(RequestMessage(0, SerialNumber.ID))

    def _send(self, cmd, timeout=1, retry=0):
        """
        Execute the given command. An exception will
        be raised if reply is not received in timeout
        seconds. If retry is non-zero, commands returning
        EAGAIN will be retried. retry also appleis to
        RESET_SYSTEM commands. This method blocks until
        a response if received from hardware or timeout.
        Care should be taken to ensure timeout is sufficiently
        large. Care should be taken to ensure timeout is
        at least as large as a on message period.
        """
        _log.debug("Executing Command. %s", cmd)
        for t in range(0, retry + 1):
            # invalid to send command while another is running
            # (except for reset system)
            assert not self.running_cmd or isinstance(cmd, ResetSystem)
            # HACK, need to clean this up. not all devices support sending
            # a response message for ResetSystem, so don't bother waiting for it
            if not isinstance(cmd, ResetSystem):
                # set expiration and event on command. Once self.runnning_cmd
                # is set access to this command from this thread is invalid 
                # until event object is set.
                cmd.expiration = time.time() + timeout if timeout > 0 else None
                cmd.done = threading.Event()
                self.running_cmd = cmd
            else:
                # reset is done without waiting
                cmd.done = threading.Event()
                cmd.result = StartupMessage(0)
            # continue trying to commit command until session closed or command timeout 
            while self.running and not cmd.done.is_set() and not self.core.send(cmd):
                _log.warning("Device write timeout. Will keep trying.")
            if isinstance(cmd, ResetSystem):
                # sleep to give time for reset to execute
                time.sleep(1)
                cmd.done.set()
            # continue waiting for command completion until session closed
            while self.running and not cmd.done.is_set():
                if isinstance(cmd, SendBurstData) and cmd.has_more_data:
                    # if the command being executed is burst
                    # continue writing packets until data empty.
                    # usb will nack packed it case where we're
                    # overflowing the ant device. and packet will
                    # be tring next time.
                    packet = cmd.create_next_packet()
                    if self.core.send(packet): cmd.incr_packet_index()
                else:
                    cmd.done.wait(1)
            # cmd.done guarantees a result is available
            if cmd.done.is_set():
                try:
                    return cmd.result
                except AttributeError:
                    # must have failed, check if error is retryable
                    if t < retry and cmd.is_retryable(cmd.error):
                        _log.warning("Retryable error. %d try(s) remaining. %s", retry - t, cmd.error)
                    else:
                        # not retryable, or too many retries
                        raise cmd.error
            else:
                self.running_cmd = None
                raise AntError("Session closed.")

    def _handle_reply(self, cmd):
        """
        Handle the given command, updating
        the status of running command if
        applicable.
        """
        _log.debug("Processing reply. %s", cmd)
        if self.running_cmd and self.running_cmd.is_reply(cmd):
            err = self.running_cmd.validate_reply(cmd)
            if err:
                self._set_error(err)
            else:
                self._set_result(cmd)

    def _handle_timeout(self):
        """
        Update the status of running command
        if the message has expired.
        """
        # if a command is currently running, check for timeout condition
        if self.running_cmd and self.running_cmd.expiration and time.time() > self.running_cmd.expiration:
            self._set_error(AntTimeoutError("No reply to command. %s" %  self.running_cmd))

    def _handle_read(self, cmd=None):
        """
        Append incoming ack messages to read buffer.
        Append completed burst message to buffer.
        Full run command from buffer if data available.
        """
        # handle update the recv buffers
        try:
            # acknowledged data is immediately made avalible to client
            # (and buffered if no read is currently running)
            if isinstance(cmd, RecvAcknowledgedData):
                self._recv_buffer[cmd.channel_number].append(cmd)
            # burst data double-buffered. it is not made available to
            # client until the complete transfer is completed.
            elif isinstance(cmd, RecvBurstTransferPacket):
                channel_number = 0x1f & cmd.channel_number
                self._burst_buffer[channel_number].append(cmd)
                # burst complete, make the complete burst available for read.
                if cmd.channel_number & 0x80:
                    _log.debug("Burst transfer completed, marking %d packets available for read.", len(self._burst_buffer[channel_number]))
                    self._recv_buffer[channel_number].extend(self._burst_buffer[channel_number])
                    self._burst_buffer[channel_number] = []
            # a burst transfer failed, any data currently read is discarded.
            # we assume the sender will retransmit the entire payload.
            elif isinstance(cmd, ChannelEvent) and cmd.msg_id == 1 and cmd.msg_code == EVENT_TRANSFER_RX_FAILED:
                _log.warning("Burst transfer failed, discarding data. %s", cmd)
                self._burst_buffer[cmd.channel_number] = []
        except IndexError:
            _log.warning("Ignoring data, buffers not initialized. %s", cmd)

        # dispatcher data if running command is ReadData and something available
        if self.running_cmd and isinstance(self.running_cmd, ReadData):
            if isinstance(cmd, RecvBroadcastData) and self.running_cmd.data_type == RecvBroadcastData:
                # read broadcast is unbuffered, and blocks until a broadcast is received
                # if a broadcast is received and nobody is listening it is discarded.
                self._set_result(cmd)
            elif self._recv_buffer[self.running_cmd.channel_number]:
                if self.running_cmd.data_type == RecvAcknowledgedData:
                    # return the most recent acknowledged data packet if one exists
                    for ack_msg in [msg for msg in self._recv_buffer[self.running_cmd.channel_number] if isinstance(msg, RecvAcknowledgedData)]:
                        self._set_result(ack_msg)
                        self._recv_buffer[self.running_cmd.channel_number].remove(ack_msg)
                        break
                elif self.running_cmd.data_type in (RecvBurstTransferPacket, ReadData):
                    # select in a single entire burst transfer or ACK
                    data = []
                    for pkt in list(self._recv_buffer[self.running_cmd.channel_number]):
                        if isinstance(pkt, RecvBurstTransferPacket) or self.running_cmd.data_type == ReadData:
                            data.append(pkt)
                            self._recv_buffer[self.running_cmd.channel_number].remove(pkt)
                            if pkt.channel_number & 0x80 or isinstance(pkt, RecvAcknowledgedData): break
                    # append all text to data of first packet
                    if data:
                        result = data[0]
                        for pkt in data[1:]:
                            result.data += pkt.data
                        self._set_result(result)

    def _handle_log(self, msg):
        if isinstance(msg, ChannelEvent) and msg.msg_id == 1:
            if msg.msg_code == EVENT_RX_SEARCH_TIMEOUT:
                _log.warning("RF channel timed out searching for device. channel_number=%d", msg.channel_number)
            elif msg.msg_code == EVENT_RX_FAIL:
                _log.warning("Failed to receive RF beacon at expected period. channel_number=%d", msg.channel_number)
            elif msg.msg_code == EVENT_RX_FAIL_GO_TO_SEARCH:
                _log.warning("Channel dropped to search do to too many dropped messages. channel_number=%d", msg.channel_number)
            elif msg.msg_code == EVENT_CHANNEL_COLLISION:
                _log.warning("Channel collision, another RF device intefered with channel. channel_number=%d", msg.channel_number)
            elif msg.msg_code == EVENT_SERIAL_QUE_OVERFLOW:
                _log.error("USB Serial buffer overflow. PC reading too slow.")

    def _set_result(self, result):
        """
        Update the running command with given result,
        and set flag to indicate to caller that command
        is done.
        """
        if self.running_cmd:
            cmd = self.running_cmd
            self.running_cmd = None
            cmd.result = result
            cmd.done.set()

    def _set_error(self, err):
        """
        Update the running command with 
        given exception. The exception will
        be raised to thread which invoked 
        synchronous command.
        """
        if self.running_cmd:
            cmd = self.running_cmd
            self.running_cmd = None
            cmd.error = err
            cmd.done.set()

    def loop(self):
        """
        Message loop consuming data from the
        ANT device. Typically loop is started
        by thread created in Session.open()
        """
        try:
            while self.running:
                for cmd in self.core.recv():
                    if not self.running: break
                    self._handle_log(cmd)
                    self._handle_read(cmd)
                    self._handle_reply(cmd)
                    self._handle_timeout()
                else:
                    if not self.running: break
                    self._handle_read()
                    self._handle_timeout()
        except Exception:
            _log.error("Caught Exception handling message, session closing.", exc_info=True)
        finally:
            self.running_cmd = None
            self.running = False


class Channel(object):

    def __init__(self, session, channel_number):
        self._session = session;
        self.channel_number = channel_number

    def open(self):
        self._session._send(OpenChannel(self.channel_number))

    def close(self):
        self._session._send(CloseChannel(self.channel_number))

    def assign(self, channel_type, network_number):
        self._session._send(AssignChannel(self.channel_number, channel_type, network_number))

    def unassign(self):
        self._session._send(UnassignChannel(self.channel_number))

    def set_id(self, device_number=0, device_type_id=0, trans_type=0):
        self._session._send(SetChannelId(self.channel_number, device_number, device_type_id, trans_type))

    def set_period(self, messaging_period=8192):
        self._session._send(SetChannelPeriod(self.channel_number, messaging_period))

    def set_search_timeout(self, search_timeout=12):
        self._session._send(SetChannelSearchTimeout(self.channel_number, search_timeout))

    def set_rf_freq(self, rf_freq=66):
        self._session._send(SetChannelRfFreq(self.channel_number, rf_freq))

    def set_search_waveform(self, search_waveform=None):
        if search_waveform is not None:
            self._session._send(SetSearchWaveform(self.channel_number, search_waveform))

    def get_status(self):
        return self._session._send(RequestMessage(self.channel_number, ChannelStatus.ID))

    def get_id(self):
        return self._session._send(RequestMessage(self.channel_number, ChannelId.ID))

    def send_broadcast(self, data, timeout=None):
        if timeout is None: timeout = self._session.default_write_timeout
        data = data_tostring(data)
        assert len(data) <= 8
        self._session._send(SendBroadcastData(self.channel_number, data), timeout=timeout)

    def send_acknowledged(self, data, timeout=None, retry=None, direct=False):
        if timeout is None: timeout = self._session.default_write_timeout
        if retry is None: retry = self._session.default_retry
        data = data_tostring(data)
        assert len(data) <= 8
        cmd = SendAcknowledgedData(self.channel_number, data)
        if not direct:
            self._session._send(cmd, timeout=timeout, retry=retry)
        else:
            # force message tx regardless of command queue
            # state, and ignore result. usefully for best
            # attempt cleanup on exit.
            self._session.core.send(cmd)

    def send_burst(self, data, timeout=None, retry=None):
        if timeout is None: timeout = self._session.default_write_timeout
        if retry is None: retry = self._session.default_retry
        data = data_tostring(data)
        self._session._send(SendBurstData(self.channel_number, data), timeout=timeout, retry=retry)

    def recv_broadcast(self, timeout=None):
        if timeout is None: timeout = self._session.default_read_timeout
        return self._session._send(ReadData(self.channel_number, RecvBroadcastData), timeout=timeout).data

    def recv_acknowledged(self, timeout=None):
        if timeout is None: timeout = self._session.default_read_timeout
        return self._session._send(ReadData(self.channel_number, RecvAcknowledgedData), timeout=timeout).data

    def recv_burst(self, timeout=None):
        if timeout is None: timeout = self._session.default_read_timeout
        return self._session._send(ReadData(self.channel_number, RecvBurstTransferPacket), timeout=timeout).data 

    def write(self, data, timeout=None, retry=None):
        if timeout is None: timeout = self._session.default_write_timeout
        if retry is None: retry = self._session.default_retry
        data = data_tostring(data)
        if len(data) <= 8:
            self.send_acknowledged(data, timeout=timeout, retry=retry)
        else:
            self.send_burst(data, timeout=timeout, retry=retry)
    
    def read(self, timeout=None):
        if timeout is None: timeout = self._session.default_read_timeout
        return self._session._send(ReadData(self.channel_number, ReadData), timeout=timeout).data 
    
class Network(object):

    def __init__(self, session, network_number):
        self._session = session
        self.network_number = network_number

    def set_key(self, network_key="\x00" * 8):
        self._session._send(SetNetworkKey(self.network_number, network_key))


# vim: ts=4 sts=4 et

########NEW FILE########
__FILENAME__ = antfs
# Copyright (c) 2012, Braiden Kindt.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
# 
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDER AND CONTRIBUTORS
# ''AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY
# WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.


import random
import struct
import collections
import logging
import time
import os
import socket
import binascii
import ConfigParser

import antd.ant as ant

_log = logging.getLogger("antd.antfs")

ANTFS_HOST_ID = os.getpid() & 0xFFFFFFFF
ANTFS_HOST_NAME = socket.gethostname()[:8]


class Beacon(object):

    DATA_PAGE_ID = 0x43
    STATE_LINK, STATE_AUTH, STATE_TRANSPORT, STATE_BUSY = range(0,4)

    __struct = struct.Struct("<BBBBI")

    @classmethod
    def unpack(cls, msg):
        if msg and ord(msg[0]) == Beacon.DATA_PAGE_ID:
            result = cls()
            result.data_page_id, result.status_1, result.status_2, result.auth_type, result.descriptor = cls.__struct.unpack(msg[:8])
            result.period = 0x07 & result.status_1
            result.pairing_enabled = 0x80 & result.status_1
            result.upload_enabled = 0x10 & result.status_1
            result.data_available = 0x20 & result.status_1
            result.device_state = 0x0f & result.status_2
            result.data = msg[8:]
            return result

    def __str__(self):
        return self.__class__.__name__ + str(self.__dict__)


class Command(object):

    DATA_PAGE_ID = 0x44
    LINK, DISCONNECT, AUTH, PING, DIRECT = 0x02, 0x03, 0x04, 0x05, 0x0D

    __struct = struct.Struct("<BB6x")

    @classmethod
    def unpack(cls, msg):
        beacon = Beacon.unpack(msg) 
        if beacon and beacon.data and ord(beacon.data[0]) == Command.DATA_PAGE_ID:
            result = cls()
            result.beacon = beacon
            result.data_page_id, result.command_id = cls.__struct.unpack(beacon.data[:8])
            return result

    def __str__(self):
        return self.__class__.__name__ + str(self.__dict__)


class Disconnect(Command):
    
    COMMAND_ID = Command.DISCONNECT

    __struct = struct.Struct("<BB6x")

    def pack(self):
        return self.__struct.pack(self.DATA_PAGE_ID, self.COMMAND_ID)


class Ping(Command):
    
    COMMAND_ID = Command.PING

    __struct = struct.Struct("<BB6x")

    def pack(self):
        return self.__struct.pack(self.DATA_PAGE_ID, self.COMMAND_ID)


class Link(Command):

    COMMAND_ID = Command.LINK 

    __struct = struct.Struct("<BBBBI")

    def __init__(self, freq, period, host_id=ANTFS_HOST_ID):
        self.frequency = freq
        self.period = period
        self.host_id = host_id

    def pack(self):
        return self.__struct.pack(self.DATA_PAGE_ID, self.COMMAND_ID, self.frequency, self.period, self.host_id)
    

class Auth(Command):

    COMMAND_ID = Command.AUTH

    OP_PASS_THRU, OP_CLIENT_SN, OP_PAIR, OP_PASSKEY = range(0, 4)
    RESPONSE_NA, RESPONSE_ACCEPT, RESPONSE_REJECT = range(0, 3)

    __struct = struct.Struct("<BBBBI")

    def __init__(self, op_id=None, auth_string="", host_id=ANTFS_HOST_ID):
        self.op_id = op_id
        self.auth_string = auth_string
        self.host_id = host_id

    def pack(self):
        return self.__struct.pack(self.DATA_PAGE_ID, self.COMMAND_ID, self.op_id, len(self.auth_string), self.host_id) + self.auth_string
    
    @classmethod
    def unpack(cls, msg):
        auth = super(Auth, cls).unpack(msg)
        if auth and auth.command_id & 0x7F == Auth.COMMAND_ID:
            data_page_id, command_id, auth.response_type, auth_string_length, auth.client_id = cls.__struct.unpack(auth.beacon.data[:8])
            auth.auth_string = auth.beacon.data[8:8 + auth_string_length]
            return auth


class GarminSendDirect(Command):
    
    COMMAND_ID = Command.DIRECT

    __struct = struct.Struct("<BBHHH")

    def __init__(self, data="", fd=0xFFFF, offset=0x0000):
        self.fd = fd
        self.offset = offset
        self.data = data
        self.blocks = (len(data) - 1) // 8

    def pack(self):
        return self.__struct.pack(self.DATA_PAGE_ID, self.COMMAND_ID, self.fd, self.offset, self.blocks) + self.data
    
    @classmethod
    def unpack(cls, msg):
        direct = super(GarminSendDirect, cls).unpack(msg)
        if direct and direct.command_id & 0x7F == GarminSendDirect.COMMAND_ID:
            data_page_id, command_id, direct.fd, direct.offset, direct.blocks = cls.__struct.unpack(direct.beacon.data[:8])
            direct.data = direct.beacon.data[8:8 + 8 * direct.blocks]
            return direct


class KnownDeviceDb(object):

    def __init__(self, file = None):
        self.file = file
        self.key_by_device_id = dict()
        self.device_id_by_ant_device_number = dict()
        self.cfg = ConfigParser.SafeConfigParser()
        if file: self.cfg.read([file])
        for section in self.cfg.sections():
            device_id = int(section, 0)
            try: self.key_by_device_id[device_id] = binascii.unhexlify(self.cfg.get(section, "key"))
            except ConfigParser.NoOptionError: pass
            try: self.device_id_by_ant_device_number[int(self.cfg.get(section, "device_number"), 0)] = device_id
            except ConfigParser.NoOptionError: pass

    def get_key(self, device_id):
        return self.key_by_device_id.get(device_id, None)

    def add_key(self, device_id, key):
        self.add_to_cfg(device_id, "key", key.encode("hex"))

    def get_device_id(self, ant_device_number):
        return self.device_id_by_ant_device_number.get(ant_device_number, None)

    def add_device_id(self, ant_device_number, device_id):
        self.add_to_cfg(device_id, "device_number", hex(ant_device_number))

    def delete_device(self, device_id):
        section = "0x%08x" % device_id 
        try: self.cfg.remove_section(section)
        except ConfigParser.NoSectionError: pass
        else:
            if self.file:
                with open(self.file, "w") as file:
                    self.cfg.write(file)
        
    def add_to_cfg(self, device_id, key, value):
        section = "0x%08x" % device_id 
        try: self.cfg.add_section(section)
        except ConfigParser.DuplicateSectionError: pass
        self.cfg.set(section, key, value)
        if self.file:
            with open(self.file, "w") as file:
                self.cfg.write(file)


class Host(object):

    search_network_key = "\xa8\xa4\x23\xb9\xf5\x5e\x63\xc1"
    search_freq = 50
    search_period = 0x1000
    search_timeout = 255
    search_waveform = 0x0053

    transport_freqs = [3, 7, 15, 20, 25, 29, 34, 40, 45, 49, 54, 60, 65, 70, 75, 80]
    transport_period = 0b100
    transport_timeout = 2

    def __init__(self, ant_session, known_client_keys=None):
        self.ant_session = ant_session
        self.known_client_keys = known_client_keys if known_client_keys is not None else KnownDeviceDb()

    def close(self):
        self.channel.send_acknowledged(Disconnect().pack(), direct=True)
        self.ant_session.close()

    def disconnect(self):
        try:
            beacon = Beacon.unpack(self.channel.recv_broadcast(.5))
        except ant.AntTimeoutError:
            pass
        else:
            self.channel.send_acknowledged(Disconnect().pack(), direct=True)
            self.channel.close()

    def ping(self):
        self.channel.write(Ping().pack())

    def search(self, search_timeout=60, device_id=None, include_unpaired_devices=False, include_devices_with_no_data=False):
        """
        Search for devices. If device_id is None return the first device
        which has data available. Unless include_unpaired_devices = True
        only devices for which we know secret key will be returned.

        If device_id is non-None, we will continue to search for device who's
        ANT device_id matchers the requested value. If found the device
        is returned regardless of whether it has data or not.
        include_unpaired_devices is ignored when device_id is provided.
        """
        timeout = time.time() + search_timeout
        while time.time() < timeout:
            try:
                # if we didn't find a device, maybe another is in range?
                # restart search every time. Once a device is tracking
                # we don't get any more hits. So, just keep re-openning
                # channel until we find device we're looking for.
                # TODO could implement AP2 filters, but this logic maintains
                # support for older devices.
                self._open_antfs_search_channel()
                # wait to recv beacon from device
                beacon = Beacon.unpack(self.channel.recv_broadcast(timeout=timeout - time.time()))
            except ant.AntTimeoutError:
                # ignore timeout error
                pass
            else:
                tracking_device_number = self.channel.get_id().device_number
                tracking_device_id = self.known_client_keys.get_device_id(tracking_device_number)
                # check if event was a beacon
                if beacon:
                    _log.debug("Got ANT-FS Beacon. device_number=0x%04x %s", tracking_device_number, beacon)
                    # and if device is a state which will accept our link
                    if  beacon.device_state != Beacon.STATE_LINK:
                        _log.warning("Device busy, not ready for link. device_number=0x%04x state=%d.",
                                tracking_device_number, beacon.device_state)
                    # are we looking for a sepcific device
                    if device_id is not None:
                        if device_id == tracking_device_id:
                            # the device exactly matches the one we're looking for
                            self.beacon = beacon
                            self.device_id = tracking_device_id
                            return beacon
                        else:
                            # a specific device id was request, but is not the one
                            # currently linked, try again. FIXME should really implement
                            # AP2 filters
                            _log.debug("Found device, but device_id does not match. 0x%08x != 0x%08x", tracking_device_id or 0, device_id)
                            continue
                    elif not include_unpaired_devices and tracking_device_id is None:
                        # requested not to return unpared devices
                        # but the one linked is unkown.
                        # FIXME add device to AP2 filter and contiue search
                        _log.debug("Found device, but paring not enabled. device_number=0x%04x", tracking_device_number)
                        continue
                    elif not beacon.data_available and not include_devices_with_no_data:
                        _log.debug("Found device, but no new data for download. device_number=0x%04x", tracking_device_number)
                    else:
                        self.beacon = beacon
                        self.device_id = tracking_device_id # may be None
                        return beacon
        
    def link(self):
        """
        Atempt to create an ANTFS link with the device
        who's beacon was most recently returned by search().
        If this channel is not tracking, the operation will
        block until a device is found, and attempt a link.
        Operation will raise a timeout exception if device
        does not reply in time our if an attempt was made
        to link while channel was not tracking.
        """
        # make sure our message period matches the target
        _log.debug("Setting period to match device, hz=%d",  2 ** (self.beacon.period - 1))
        self._configure_antfs_period(self.beacon.period)
        # wait for channel to sync
        Beacon.unpack(self.channel.recv_broadcast(0))
        # send the link commmand
        link = Link(freq=random.choice(self.transport_freqs), period=self.transport_period)
        _log.debug("Linking with device. freq=24%02dmhz", link.frequency)
        self.channel.send_acknowledged(link.pack())
        # change this channels frequency to match link
        self._configure_antfs_transport_channel(link)
        # block indefinately for the antfs beacon on new freq.
        # (don't need a timeout since channel will auto close if device lost)
        self.beacon = Beacon.unpack(self.channel.recv_broadcast(0))
        # device should be broadcasting our id and ready to accept auth
        assert self.beacon.device_state == Beacon.STATE_AUTH
        return self.beacon

    def auth(self, pair=True, timeout=60):
        """
        Attempt to create an authenticated transport
        with the device we are currenly linked. Not
        valid unless device is in link status.
        If a client key is known, transport will be
        openned without user interaction. If key is unkown
        we will attempt to pair with device (which must
        be acknowledged by human on GPS device.)
        If paising is not enabled Auth is impossible.
        Error raised if auth is not successful.
        Timeout only applies user interaction during pairing process.
        """
        # get the S/N of client device
        auth_cmd = Auth(Auth.OP_CLIENT_SN)
        self.channel.write(auth_cmd.pack())
        while True:
            auth_reply = Auth.unpack(self.channel.read())
            if auth_reply: break
        _log.debug("Got client auth string. %s", auth_reply)
        # check if the auth key for this device is known
        client_id = auth_reply.client_id
        # property may not have been set yet if new device
        self.device_id = client_id  
        # look up key
        key = self.known_client_keys.get_key(client_id)
        if key:
            _log.debug("Device secret known.")
            auth_cmd = Auth(Auth.OP_PASSKEY, key)
            self.channel.write(auth_cmd.pack())
            while True:
                auth_reply = Auth.unpack(self.channel.read())
                if auth_reply: break
            if auth_reply.response_type == Auth.RESPONSE_ACCEPT:
                _log.debug("Device accepted key.")
            else:
                _log.warning("Device pairing failed. Removing key from db. Try re-pairing.")
                self.known_client_keys.delete_device(client_id)
        elif pair:
            _log.debug("Device unkown, requesting pairing.")
            auth_cmd = Auth(Auth.OP_PAIR, ANTFS_HOST_NAME)
            self.channel.write(auth_cmd.pack())
            while True:
                auth_reply = Auth.unpack(self.channel.read(timeout))
                if auth_reply: break
            if auth_reply.response_type == Auth.RESPONSE_ACCEPT:
                _log.debug("Device paired. key=%s", auth_reply.auth_string.encode("hex"))
                self.known_client_keys.add_key(client_id, auth_reply.auth_string)
                device_number = self.channel.get_id().device_number
                self.known_client_keys.add_device_id(device_number, client_id)
            else:
                _log.warning("Device pairing failed. Request rejected?")
        else:
            _log.warning("Device 0x08%x has data but pairing is disabled and key is unkown.", client_id)
        #confirm the ANT-FS channel is open
        self.beacon = Beacon.unpack(self.channel.recv_broadcast(0))
        assert self.beacon.device_state == Beacon.STATE_TRANSPORT
        return self.beacon

    def write(self, msg):
        direct_cmd = GarminSendDirect(msg)
        self.channel.write(direct_cmd.pack())

    def read(self):
        direct_reply = GarminSendDirect.unpack(self.channel.read())
        return direct_reply.data if direct_reply else None

    def _open_antfs_search_channel(self):
        self.ant_session.reset_system()
        self.channel = self.ant_session.channels[0]
        self.network = self.ant_session.networks[0]
        self._configure_antfs_search_channel()
        self.channel.open()

    def _configure_antfs_search_channel(self):
        self.network.set_key(self.search_network_key)
        self.channel.assign(channel_type=0x00, network_number=self.network.network_number)
        self.channel.set_id(device_number=0, device_type_id=0, trans_type=0)
        self.channel.set_period(self.search_period)
        self.channel.set_search_timeout(self.search_timeout)
        self.channel.set_rf_freq(self.search_freq)
        self.channel.set_search_waveform(self.search_waveform)

    def _configure_antfs_transport_channel(self, link):
        self.channel.set_rf_freq(link.frequency)
        self.channel.set_search_timeout(self.transport_timeout)
        self._configure_antfs_period(link.period)

    def _configure_antfs_period(self, period):
        period_hz = 2 ** (period - 1)
        channel_period = 0x8000 / period_hz
        self.channel.set_period(channel_period)
        

# vim: ts=4 sts=4 et

########NEW FILE########
__FILENAME__ = cfg
# Copyright (c) 2012, Braiden Kindt.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
# 
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDER AND CONTRIBUTORS
# ''AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY
# WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.


import ConfigParser
import dbm
import os
import binascii
import logging
import sys
import pkg_resources
import logging

_log = logging.getLogger("antd.cfg")
_cfg = ConfigParser.SafeConfigParser()

CONFIG_FILE_VERSION = 2
DEFAULT_CONFIG_LOCATION = os.path.expanduser("~/.antd/antd.cfg")

def write_default_config(target):
    dirname = os.path.dirname(target)
    if not os.path.exists(dirname): os.makedirs(dirname)
    with open(target, "w") as file:
        file.write(pkg_resources.resource_string(__name__, "antd.cfg"))
    
def read(file=None):
    if file is None:
        file = DEFAULT_CONFIG_LOCATION
        if not os.path.isfile(file):
            # copy the template configuration file to users .antd directory
            write_default_config(file)
    read = _cfg.read([file])
    if read:
        # config file read sucessfuelly, setup logger
        _log.setLevel(logging.WARNING)
        init_loggers()
        # check for version mismatch
        try: version = _cfg.getint("antd", "version")
        except (ConfigParser.NoOptionError, ConfigParser.NoSectionError): version = -1
        if version != CONFIG_FILE_VERSION:
            new_file = DEFAULT_CONFIG_LOCATION + ".%d" % CONFIG_FILE_VERSION
            write_default_config(new_file)
            _log.warning("Config file version does not match expected version (%d).", CONFIG_FILE_VERSION)
            _log.warning("If you have issues recommended you replace your configuration with %s", new_file)  
            _log.warning("Set [antd] version=%d in your current config file to disable this warning.", CONFIG_FILE_VERSION)
    return read

def init_loggers(force_level=None, out=sys.stdin):
    level = force_level if force_level is not None else logging.ERROR
    logging.basicConfig(
            level=level,
            out=out,
            format="[%(threadName)s]\t%(asctime)s\t%(levelname)s\t%(message)s")
    try:
        for logger, log_level in _cfg.items("antd.logging"):
            level = force_level if force_level is not None else logging.getLevelName(log_level)
            logging.getLogger(logger).setLevel(level) 
    except ConfigParser.NoSectionError:
        pass

def create_hardware():
    import antd.hw as hw
    try:
        id_vendor = int(_cfg.get("antd.hw", "id_vendor"), 0)
        id_product = int(_cfg.get("antd.hw", "id_product"), 0)
        bulk_endpoint = int(_cfg.get("antd.hw", "bulk_endpoint"), 0)
        return hw.UsbHardware(id_vendor, id_product, bulk_endpoint)
    except hw.NoUsbHardwareFound:
        _log.warning("Failed to find Garmin nRF24AP2 (newer) USB Stick.", exc_info=True)
        _log.warning("Looking for nRF24AP1 (older) Serial USB Stick.")
        tty = _cfg.get("antd.hw", "serial_device")
        return hw.SerialHardware(tty, 115200)

def create_ant_core():
    import antd.ant as ant
    return ant.Core(create_hardware())

def create_ant_session():
    import antd.ant as ant
    session = ant.Session(create_ant_core())
    session.default_read_timeout = int(_cfg.get("antd.ant", "default_read_timeout"), 0)
    session.default_write_timeout = int(_cfg.get("antd.ant", "default_write_timeout"), 0)
    session.default_retry = int(_cfg.get("antd.ant", "default_retry"), 0)
    return session

def create_antfs_host():
    import antd.antfs as antfs
    keys_file = _cfg.get("antd.antfs", "auth_pairing_keys")
    keys_file = os.path.expanduser(keys_file)
    keys_dir = os.path.dirname(keys_file)
    if not os.path.exists(keys_dir): os.makedirs(keys_dir)
    keys = antfs.KnownDeviceDb(keys_file)
    host = antfs.Host(create_ant_session(), keys)
    host.search_network_key = binascii.unhexlify(_cfg.get("antd.antfs", "search_network_key"))
    host.search_freq = int(_cfg.get("antd.antfs", "search_freq"), 0)
    host.search_period = int(_cfg.get("antd.antfs", "search_period"), 0)
    host.search_timeout = int(_cfg.get("antd.antfs", "search_timeout"), 0)
    host.search_waveform = int(_cfg.get("antd.antfs", "search_waveform"), 0)
    host.transport_freqs = [int(s, 0) for s in _cfg.get("antd.antfs", "transport_freq").split(",")]
    host.transport_period = int(_cfg.get("antd.antfs", "transport_period"), 0)
    host.transport_timeout = int(_cfg.get("antd.antfs", "transport_timeout"), 0)
    return host

def create_garmin_connect_plugin():
    try:
        if _cfg.getboolean("antd.connect", "enabled"):
            import antd.connect as connect
            client = connect.GarminConnect()
            client.username = _cfg.get("antd.connect", "username")
            client.password = _cfg.get("antd.connect", "password")
            client.cache = os.path.expanduser(_cfg.get("antd.connect", "cache")) 
            return client 
    except ConfigParser.NoSectionError: pass

def create_strava_plugin():
    try:
        if _cfg.getboolean("antd.strava", "enabled"):
            import antd.connect as connect
            client = connect.StravaConnect()
            client.smtp_server = _cfg.get("antd.strava", "smtp_server")
            client.smtp_port = _cfg.get("antd.strava", "smtp_port")
            client.smtp_username = _cfg.get("antd.strava", "smtp_username")
            client.smtp_password = _cfg.get("antd.strava", "smtp_password")
            return client
    except ConfigParser.NoSectionError: pass

def create_tcx_plugin():
    if _cfg.getboolean("antd.tcx", "enabled"):
        import antd.tcx as tcx
        tcx = tcx.TcxPlugin()
        tcx.tcx_output_dir = os.path.expanduser(_cfg.get("antd.tcx", "tcx_output_dir"))
        try:
            tcx.cache = os.path.expanduser(_cfg.get("antd.tcx", "cache")) 
        except ConfigParser.NoOptionError: pass
        return tcx

def create_notification_plugin():
    try:
        if _cfg.getboolean("antd.notification", "enabled"):
            import antd.notif as notif
            notif = notif.NotifPlugin()
            return notif
    except ConfigParser.NoSectionError: pass

def get_path(section, key, file="", tokens={}):
    path = os.path.expanduser(_cfg.get(section, key))
    path = path % tokens
    if not os.path.exists(path): os.makedirs(path)
    return os.path.sep.join([path, file]) if file else path

def get_delete_from_device():
    try:
        return _cfg.getboolean("antd", "delete_from_device")
    except ConfigParser.NoOptionError:
        return False

def get_retry():
    return int(_cfg.get("antd", "retry"), 0)

def get_raw_output_dir():
    return get_path("antd", "raw_output_dir")


# vim: ts=4 sts=4 et

########NEW FILE########
__FILENAME__ = connect
# Copyright (c) 2012, Braiden Kindt.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
# 
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDER AND CONTRIBUTORS
# ''AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY
# WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.


import logging
import os
import sys
import requests
import json
import glob
import time
import re

import antd.plugin as plugin

_log = logging.getLogger("antd.connect")

class GarminConnect(plugin.Plugin):

    username = None
    password = None

    logged_in = False
    login_invalid = False
    
    rsession = None
    
    def __init__(self):
        self._rate_lock = open("/tmp/gc_rate.lock", "w")
        return
    
    # Borrowed to support new Garmin login
    # https://github.com/cpfair/tapiriik
    def _rate_limit(self):
        import fcntl
        print("Waiting for lock")
        fcntl.flock(self._rate_lock,fcntl.LOCK_EX)
        try:
            print("Have lock")
            time.sleep(1) # I appear to been banned from Garmin Connect while determining this.
            print("Rate limited")
        finally:
            fcntl.flock(self._rate_lock,fcntl.LOCK_UN)

    # work around old versions of requests
    def get_response_text(self, response):
        return response.text if hasattr(response, "text") else response.content
    
    def data_available(self, device_sn, format, files):
        if format not in ("tcx"): return files
        result = []
        try:
            for file in files:
                self.login()
                self.upload(format, file)
                result.append(file)
            plugin.publish_data(device_sn, "notif_connect", files)
        except Exception:
            _log.warning("Failed to upload to Garmin Connect.", exc_info=True)
        finally:
            return result

    def login(self):
        if self.logged_in: return
        if self.login_invalid: raise InvalidLogin()
        
        # Use a session, removes the need to manage cookies ourselves
        self.rsession = requests.Session()
        
        _log.debug("Checking to see what style of login to use for Garmin Connect.")
        #Login code taken almost directly from https://github.com/cpfair/tapiriik/
        self._rate_limit()
        gcPreResp = self.rsession.get("http://connect.garmin.com/", allow_redirects=False)
        # New site gets this redirect, old one does not
        if gcPreResp.status_code == 200:
            _log.debug("Using old login style")
            params = {"login": "login", "login:loginUsernameField": self.username, "login:password": self.password, "login:signInButton": "Sign In", "javax.faces.ViewState": "j_id1"}
            auth_retries = 3 # Did I mention Garmin Connect is silly?
            for retries in range(auth_retries):
                self._rate_limit()
                resp = self.rsession.post("https://connect.garmin.com/signin", data=params, allow_redirects=False, cookies=gcPreResp.cookies)
                if resp.status_code >= 500 and resp.status_code < 600:
                    raise APIException("Remote API failure")
                if resp.status_code != 302:  # yep
                    if "errorMessage" in self.get_response_text(resp):
                        if retries < auth_retries - 1:
                            time.sleep(1)
                            continue
                        else:
                            login_invalid = True
                            raise APIException("Invalid login", block=True, user_exception=UserException(UserExceptionType.Authorization, intervention_required=True))
                    else:
                        raise APIException("Mystery login error %s" % self.get_response_text(resp))
                _log.debug("Old style login complete")
                break
        elif gcPreResp.status_code == 302:
            _log.debug("Using new style login")
            # JSIG CAS, cool I guess.
            # Not quite OAuth though, so I'll continue to collect raw credentials.
            # Commented stuff left in case this ever breaks because of missing parameters...
            data = {
                "username": self.username,
                "password": self.password,
                "_eventId": "submit",
                "embed": "true",
                # "displayNameRequired": "false"
            }
            params = {
                "service": "http://connect.garmin.com/post-auth/login",
                # "redirectAfterAccountLoginUrl": "http://connect.garmin.com/post-auth/login",
                # "redirectAfterAccountCreationUrl": "http://connect.garmin.com/post-auth/login",
                # "webhost": "olaxpw-connect00.garmin.com",
                "clientId": "GarminConnect",
                # "gauthHost": "https://sso.garmin.com/sso",
                # "rememberMeShown": "true",
                # "rememberMeChecked": "false",
                "consumeServiceTicket": "false",
                # "id": "gauth-widget",
                # "embedWidget": "false",
                # "cssUrl": "https://static.garmincdn.com/com.garmin.connect/ui/src-css/gauth-custom.css",
                # "source": "http://connect.garmin.com/en-US/signin",
                # "createAccountShown": "true",
                # "openCreateAccount": "false",
                # "usernameShown": "true",
                # "displayNameShown": "false",
                # "initialFocus": "true",
                # "locale": "en"
            }
            _log.debug("Fetching login variables")
            
            # I may never understand what motivates people to mangle a perfectly good protocol like HTTP in the ways they do...
            preResp = self.rsession.get("https://sso.garmin.com/sso/login", params=params)
            if preResp.status_code != 200:
                raise APIException("SSO prestart error %s %s" % (preResp.status_code, self.get_response_text(preResp)))
            data["lt"] = re.search("name=\"lt\"\s+value=\"([^\"]+)\"", self.get_response_text(preResp)).groups(1)[0]
            _log.debug("lt=%s"%data["lt"])

            _log.debug("Posting login credentials to Garmin Connect. username=%s", self.username)
            ssoResp = self.rsession.post("https://sso.garmin.com/sso/login", params=params, data=data, allow_redirects=False)
            if ssoResp.status_code != 200:
                login_invalid = True
                _log.error("Login failed")
                raise APIException("SSO error %s %s" % (ssoResp.status_code, self.get_response_text(ssoResp)))

            ticket_match = re.search("ticket=([^']+)'", self.get_response_text(ssoResp))
            if not ticket_match:
                login_invalid = True
                raise APIException("Invalid login", block=True, user_exception=UserException(UserExceptionType.Authorization, intervention_required=True))
            ticket = ticket_match.groups(1)[0]

            # ...AND WE'RE NOT DONE YET!

            _log.debug("Post login step 1")
            self._rate_limit()
            gcRedeemResp1 = self.rsession.get("http://connect.garmin.com/post-auth/login", params={"ticket": ticket}, allow_redirects=False)
            if gcRedeemResp1.status_code != 302:
                raise APIException("GC redeem 1 error %s %s" % (gcRedeemResp1.status_code, self.get_response_text(gcRedeemResp1)))

            _log.debug("Post login step 2")
            self._rate_limit()
            gcRedeemResp2 = self.rsession.get(gcRedeemResp1.headers["location"], allow_redirects=False)
            if gcRedeemResp2.status_code != 302:
                raise APIException("GC redeem 2 error %s %s" % (gcRedeemResp2.status_code, self.get_response_text(gcRedeemResp2)))

        else:
            raise APIException("Unknown GC prestart response %s %s" % (gcPreResp.status_code, self.get_response_text(gcPreResp)))

        
        self.logged_in = True
        
    
    def upload(self, format, file_name):
        #TODO: Restore streaming for upload
        with open(file_name) as file:
            files = {'file': file}
            _log.info("Uploading %s to Garmin Connect.", file_name) 
            r = self.rsession.post("http://connect.garmin.com/proxy/upload-service-1.1/json/upload/.%s" % format, files=files)
        
class StravaConnect(plugin.Plugin):

    server = None
    smtp_server = None
    smtp_port = None
    smtp_username = None
    smtp_password = None

    logged_in = False

    def __init__(self):
        from smtplib import SMTP
        self.server = SMTP()
        pass

    def data_available(self, device_sn, format, files):
        if format not in ("tcx"): return files
        result = []
        try:
            for file in files:
                self.login()
                self.upload(format, file)
                result.append(file)
            self.logout()
        except Exception:
            _log.warning("Failed to upload to Strava.", exc_info=True)
        finally:
            return result

    def logout(self):
        self.server.close()

    def login(self):
        if self.logged_in: return
        self.server.connect(self.smtp_server, self.smtp_port)
        self.server.ehlo()
        self.server.starttls()
        self.server.ehlo()
        self.server.login(self.smtp_username, self.smtp_password)
        self.logged_in = True
    
    def upload(self, format, file_name):
        from email.mime.base import MIMEBase
        from email.mime.multipart import MIMEMultipart
        import datetime
        from email import encoders
        outer = MIMEMultipart()
        outer['Subject'] = 'Garmin Data Upload from %s' % datetime.date.today()
        outer['To' ] = 'upload@strava.com'
        outer['From' ] = self.smtp_username
        outer.preamble = 'You will not see this in a MIME-aware mail reader.\n'
        with open(file_name, 'rb') as fp:
            msg = MIMEBase('application', 'octet-stream')
            msg.set_payload(fp.read())
        encoders.encode_base64(msg)
        msg.add_header('Content-Disposition', 'attachment', filename=file_name)
        outer.attach(msg)
        self.server.sendmail(self.smtp_username, 'upload@strava.com', outer.as_string())

class InvalidLogin(Exception): pass


# vim: ts=4 sts=4 et

########NEW FILE########
__FILENAME__ = garmin
# Copyright (c) 2012, Braiden Kindt.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
# 
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDER AND CONTRIBUTORS
# ''AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY
# WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""
Implementation of the Garmin Device Interface Specifications.
http://www8.garmin.com/support/commProtocol.html
Classes named like Annn, Dnnn coorelate with the documented
types in specification. Currently this class only implementes
the necessary protocols and datatypes  to dynamically discover
device capaibilties and save runs. The spec was last updated
in 2006, so some datatypes include undocumented/unkown fields.
"""

import logging
import struct
import time
import collections

import antd.ant as ant

_log = logging.getLogger("antd.garmin")

class P000(object):
    """
    Physical protocol, must be implemented by all devices.
    """
    PID_ACK = 6
    PID_NACK = 21

class L000(P000):
    """
    Data link protocl at least PID_PRODUCT_RQST
    is impelmented by all devices.
    """
    PID_PROTOCOL_ARRAY = 253
    PID_PRODUCT_RQST = 254
    PID_PRODUCT_DATA = 255
    PID_EXT_PRODUCT_DATA = 248

    def __init__(self):
        self.data_type_by_pid = {
            L000.PID_PRODUCT_DATA: ProductDataType,
            L000.PID_EXT_PRODUCT_DATA: ExtProductDataType,
            L000.PID_PROTOCOL_ARRAY: ProtocolArrayType,
        }

class L001(L000):
    """
    Link protocol defining how data is requested and
    returned from device. 
    """
    PID_COMMAND_DATA = 10                  
    PID_XFER_CMPLT = 12
    PID_DATE_TIME_DATA = 14
    PID_POSITION_DATA = 17
    PID_PRX_WPT_DATA = 19
    PID_RECORDS = 27
    PID_RTE_HDR = 29
    PID_RTE_WPT_DATA = 30
    PID_ALMANAC_DATA = 31
    PID_TRK_DATA = 34
    PID_WPT_DATA = 35
    PID_PVT_DATA = 51
    PID_RTE_LINK_DATA = 98
    PID_TRK_HDR = 99
    PID_FLIGHTBOOK_RECORD = 134
    PID_LAP = 149
    PID_WPT_CAT = 152
    PID_RUN = 990
    PID_WORKOUT = 991
    PID_WORKOUT_OCCURRENCE = 992
    PID_FITNESS_USER_PROFILE = 993
    PID_WORKOUT_LIMITS = 994
    PID_COURSE = 1061
    PID_COURSE_LAP = 1062
    PID_COURSE_POINT = 1063
    PID_COURSE_TRK_HDR = 1064
    PID_COURSE_TRK_DATA = 1065
    PID_COURSE_LIMITS = 1066      
    # undocumented, assuming this was added
    # due to inefficiency in packet per wpt
    # over ANT
    PID_TRK_DATA_ARRAY = 1510

    def __init__(self):
        self.data_type_by_pid = {
            L001.PID_XFER_CMPLT: CommandIdType,
            L001.PID_RECORDS: RecordsType,
        }

class A010(object):
    """
    Command protocol. Mainly used in comination with
    L001.PID_COMMAND_DATA to download data from device.
    """
    CMND_ABORT_TRANSFER = 0   
    CMND_TRANSFER_ALM = 1
    CMND_TRANSFER_POSN = 2
    CMND_TRANSFER_PRX = 3
    CMND_TRANSFER_RTE = 4
    CMND_TRANSFER_TIME = 5
    CMND_TRANSFER_TRK = 6
    CMND_TRANSFER_WPT = 7
    CMND_TURN_OFF_PWR = 8
    CMND_START_PVT_DATA = 49
    CMND_STOP_PVT_DATA = 50
    CMND_FLIGHTBOOK_TRANSFER = 92
    CMND_TRANSFER_LAPS = 117
    CMND_TRANSFER_WPT_CATS = 121
    CMND_TRANSFER_RUNS = 450
    CMND_TRANSFER_WORKOUTS = 451
    CMND_TRANSFER_WORKOUT_OCCURRENCES = 452
    CMND_TRANSFER_FITNESS_USER_PROFILE = 453
    CMND_TRANSFER_WORKOUT_LIMITS = 454
    CMND_TRANSFER_COURSES = 561
    CMND_TRANSFER_COURSE_LAPS = 562
    CMND_TRANSFER_COURSE_POINTS = 563
    CMND_TRANSFER_COURSE_TRACKS = 564
    CMND_TRANSFER_COURSE_LIMITS = 565

    def __init__(self):
        self.data_type_by_pid = {}


def dump_packet(file, packet):
    """
    Dump the given packet to file.
    Format is consistant with garmin physical packet format.
    uint16=packet_id, uint16t=data_length, char[]=data
    """
    pid, length, data = packet
    file.write(struct.pack("<HH", pid, length))
    if data: file.write(data.raw)

def dump(file, data):
    """
    Recursively dump the given packets (or packet)
    to given file.
    """
    for packet in data:
        try:
            dump(file, packet)
        except TypeError:
            dump_packet(file, packet)

def pack(pid, data_type=None):
    """
    Pack a garmin request pack, data_type
    if non-None is assumed to be uint16_t.
    packet padded to 8-bytes (FIXME, padding
    is done for ant transport. unportable
    and not even necessary?
    """
    return struct.pack("<HHHxx", pid, 0 if data_type is None else 2, data_type or 0)

def unpack(msg):
    """
    Unpack a garmin device communication packet.
    uint16_t=pid, uint16_t=length, data[]
    """
    pid, length = struct.unpack("<HH", msg[:4])
    data = msg[4:4 + length]
    return pid, length, data

def tokenize(msg):
    """
    A generator which returning unpacked
    packets from the given string of concatinated
    packet strings.
    """
    while True:
        pid, length, data = unpack(msg)
        if pid or length:
            yield pid, length, msg[4:length + 4] 
            msg = msg[length + 4:]
            if len(msg) < 4: break
        else:
            break

def chunk(l, n):
    """
    A generator returning n-sized lists
    of l's elements.
    """
    for i in xrange(0, len(l), n):
        yield l[i:i+n]

def get_proto_cls(protocol_array, values):
    """
    Given a garmin protocol_array, return
    the first value in values which is implemented
    by the device.
    """
    for val in values:
        if val.__name__ in protocol_array:
            return val

def data_types_by_protocol(protocol_array):
    """
    Return a dict mapping each protocol Annn
    to the data types returned by the device
    descrived by protocol array.
    """
    result = {}
    for proto in protocol_array:
        if "A" in proto:
            data_types = []
            result[proto] = data_types
        elif "D" in proto:
            data_types.append(proto)
    return result

def abbrev(str, max_len):
    """
    Return a string  of up to max length.
    adding elippis if string greater than max len.
    """
    if len(str) > max_len: return str[:max_len] + "..."
    else: return str

def extract_wpts(protocols, get_trks_pkts, index):
    """
    Given a collection of track points packets,
    return those which are members of given track index.
    Where PID_TRK_DATA_ARRAY is encountered, data is expanded
    such that result is equvalent to cas where each was its
    on packet of PID_TRK_DATA
    """
    i = iter(get_trks_pkts)
    # position iter at first wpt record of given index
    for pid, length, data in i:
        if pid == protocols.link_proto.PID_TRK_HDR and data.index == index:
            break
    # extract wpts
    for pkt in i:
        if pkt.pid == protocols.link_proto.PID_TRK_HDR:
            break
        elif pkt.pid == protocols.link_proto.PID_TRK_DATA:
            yield data
        elif pkt.pid == protocols.link_proto.PID_TRK_DATA_ARRAY:
            for wpt in pkt.data.wpts: yield wpt

def extract_runs(protocols, get_runs_pkts):
    """
    Given garmin packets which are result of A1000 (get_runs)
    Return an object tree runs->laps->points for easier processing.
    """
    runs, laps, trks = get_runs_pkts
    runs = [r.data for r in runs.by_pid[protocols.link_proto.PID_RUN]]
    laps = [l.data for l in laps.by_pid[protocols.link_proto.PID_LAP]]
    _log.debug("extract_runs: found %d run(s)", len(runs))
    for run_num, run in enumerate(runs):
        run.laps = [l for l in laps if run.first_lap_index <= l.index <= run.last_lap_index]
        run.time.time = run.laps[0].start_time.time
        run.wpts = list(extract_wpts(protocols, trks, run.track_index))
        _log.debug("extract_runs: run %d has: %d lap(s), %d wpt(s)", run_num + 1, len(run.laps), len(run.wpts))
        for lap in run.laps: lap.wpts = []
        lap_num = 0
        for wpt in run.wpts:
            try:
                while wpt.time.time >= run.laps[lap_num + 1].start_time.time:
                    _log.debug("extract_runs: run %d lap %d has: %d wpt(s)",
                            run_num + 1, lap_num + 1, len(run.laps[lap_num].wpts))
                    lap_num += 1
            except IndexError:
                pass
            run.laps[lap_num].wpts.append(wpt)
        all_wpt_in_laps = sum(len(lap.wpts) for lap in run.laps)
        if len(run.wpts) != all_wpt_in_laps:
            _log.warning("extract_runs: run %d waypoint mismatch: total(%d) != wpt_in_laps(%d)",
                    run_num + 1, len(run.wpts), all_wpt_in_laps)
    return runs


class Device(object):
    """
    Class represents a garmin gps device.
    Methods of this class will delegate to
    the specific protocols impelemnted by this
    device. They may raise DeviceNotSupportedError
    if the device does not implement a specific
    operation.
    """
    
    def __init__(self, stream):
        self.stream = stream
        self.init_device_api()

    def get_product_data(self):
        """
        Get product capabilities.
        """
        return self.execute(A000())[0]

    def get_runs(self):
        """
        Get new runs from device.
        """
        if self.run_proto:
            return self.execute(self.run_proto)
        else:
            raise DeviceNotSupportedError("Device does not support get_runs.")

    def delete_runs(self):
        """
        Delete runs from device.
        UNDOCUMENTED, implementation does not delegate to protocol array.
        This method won't raise error on unsupported hardware, and my silently fail.
        """
        return self.execute(DeleteRuns(self))

    def init_device_api(self):
        """
        Initialize the protocols used by this
        instance based on the protocol capabilities
        array which is return from A000.
        """
        product_data = self.get_product_data()
        try:
            self.device_id = product_data.by_pid[L000.PID_PRODUCT_DATA][0].data
            self.protocol_array = product_data.by_pid[L000.PID_PROTOCOL_ARRAY][0].data.protocol_array
            _log.debug("init_device_api: product_id=%d, software_version=%0.2f, description=%s",
                    self.device_id.product_id, self.device_id.software_version/100., self.device_id.description)
            _log.debug("init_device_api: protocol_array=%s", self.protocol_array)
        except (IndexError, TypeError):
            raise DeviceNotSupportedError("Product data not returned by device.")
        self.data_types_by_protocol = data_types_by_protocol(self.protocol_array)
        # the tuples in this section define an ordered collection
        # of protocols which are candidates to provide each specific
        # function. Each proto will be device based on the first one
        # whihc exists in this devices capabiltities.
        # This section needs to be updated whenever a new protocol 
        # needs to be supported.
        self.link_proto = self._find_core_protocol("link", (L000, L001))
        self.cmd_proto = self._find_core_protocol("command", (A010,))
        self.trk_proto = self._find_app_protocol("get_trks", (A301, A302))
        self.lap_proto = self._find_app_protocol("get_laps", (A906,))
        self.run_proto = self._find_app_protocol("get_runs", (A1000,))

    def _find_core_protocol(self, name, candidates):
        """
        Return the first procotol in candidates
        which is supported by this device.
        """
        proto = get_proto_cls(self.protocol_array, candidates)
        if proto:
            _log.debug("Using %s protocol %s.", name, proto.__name__)
        else:
            raise DeviceNotSupportedError("Device does not implement a known link protocol. capabilities=%s" 
                    % self.protocol_array)
        return proto()

    def _find_app_protocol(self, function_name, candidates):
        """
        Return the first protocol in candidates whihc
        is supported by this device. additionally, check
        that the datatypes which are returned by the give
        protocol are implented by this python module.
        If not a warning is logged. (but no excetpion is raised._
        This allows raw data dump to succeed, but trx generation to fail.
        """
        cls = get_proto_cls(self.protocol_array, candidates)
        data_types = self.data_types_by_protocol.get(cls.__name__, [])
        data_type_cls = [globals().get(nm, DataType) for nm in data_types]
        if not cls:
            _log.warning("Download may FAIL. Protocol unimplemented. %s:%s", function_name, candidates)
        else:
            _log.debug("Using %s%s for: %s", cls.__name__, data_types, function_name)
            if DataType in data_type_cls:
                _log.warning("Download may FAIL. DataType unimplemented. %s:%s%s", function_name, cls.__name__, data_types)
            try:
                return cls(self, *data_type_cls)
            except Exception:
                _log.warning("Download may Fail. Failed to ceate protocol %s.", function_name, exc_info=True)

    def execute(self, protocol):
        """
        Execute the give garmin Applection protcol.
        e.g. one of the Annn classes.
        """
        result = []
        for next in protocol.execute():
            if hasattr(next, "execute"):
                result.extend(self.execute(next))
            else:
                pid, data = next
                in_packets = []
                self.stream.write(pack(pid, data))
                while True:
                    pkt = self.stream.read()
                    if not pkt: break
                    for pid, length, data in tokenize(pkt):
                        in_packets.append((pid, length, protocol.decode_packet(pid, length, data)))
                        self.stream.write(pack(P000.PID_ACK, pid))
                in_packets.append((0, 0, None))
                result.append(protocol.decode_list(in_packets))

        return protocol.decode_result(result)


class MockHost(object):
    """
    A mock device which can be used
    when instantiating a Device.
    Rather than accessing hardware,
    commands are replayed though given
    string (which can be read from file.
    This class is dumb, so caller has
    to ensure pkts in the import string
    or file are properly ordered.
    """

    def __init__(self, data):
        self.reader = self._read(data)

    def write(self, *args, **kwds):
        pass

    def read(self):
        try:
            return self.reader.next()
        except StopIteration:
            return ""

    def _read(self, data):
        while data:
            (length,) = struct.unpack("<H", data[2:4])
            if length: pkt = data[0:length + 4]
            else: pkt = ""
            data = data[length + 4:]
            yield pkt


class Protocol(object):
    """
    A protocol defines the required comands
    which need to be sent to hardware to perform
    a specific function.
    """

    def __init__(self, protocols):
        self.link_proto = protocols.link_proto
        self.cmd_proto = protocols.cmd_proto
        self.data_type_by_pid = dict(
            protocols.link_proto.data_type_by_pid.items() +
            protocols.cmd_proto.data_type_by_pid.items()
        )

    def execute(self):
        """
        A generator or array which contains either a tuple
        representing a command which should be executed
        or a protocol (who's execute shoudl be deletaged to.
        """
        return []

    def decode_packet(self, pid, length, data):
        """
        Decode the given packet's data property.
        """
        if length:
            data_cls = self.data_type_by_pid.get(pid, DataType)
            return data_cls(data)

    def decode_list(self, pkts):
        return PacketList(pkts)

    def decode_result(self, list):
        return list

class DownloadProtocol(Protocol):
    """
    Protocol with download progess logging.
    Can be extended/ehnanced for GUI use.
    """

    pid_data = []

    def decode_packet(self, pid, length, data):
        data = super(DownloadProtocol, self).decode_packet(pid, length, data)
        try:
            if pid == self.link_proto.PID_RECORDS:
                self.on_start(pid, data)
            elif pid in self.pid_data:
                self.on_data(pid, data)
            elif pid == self.link_proto.PID_XFER_CMPLT:
                self.on_finish(pid, data)
        except Exception:
            # notification may fail if data packet could not be enriched by a known data type?
            # dont' allow this to stop the download, still want to write raw packets to file.
            _log.warning("Caught exception sending notification of download status, ignoring error", exc_info=True)
        finally:
            return data
            

    def on_start(self, pid, data):
        _log.info("%s: Starting download. %d record(s)", self.__class__.__name__, data.count)
        self.expected = data.count
        self.count = 0
        self.last_log = time.time()

    def on_data(self, pid, data):
        self.count += 1
        if self.last_log + 1 < time.time():
            _log.info("%s: Download in progress. %d/%d", self.__class__.__name__, self.count, self.expected)
            self.last_log = time.time()

    def on_finish(self, pid, data):
        _log.info("%s: Finished download. %d/%d", self.__class__.__name__, self.count, self.expected)
        if self.count != self.expected:
            _log.warning("%s: Record count mismatch, expected(%d) != actual(%d)", 
                    self.__class__.__name__, self.expected, self.count)
    

class A000(Protocol):
    """
    Device capabilities.
    """

    def __init__(self):
        self.data_type_by_pid = L000().data_type_by_pid

    def execute(self):
        _log.debug("A000: executing product request")
        yield (L000.PID_PRODUCT_RQST, None)


class DeleteRuns(Protocol):
    """
    Delete runs from delete.
    UNDOCUMENTED.
    """

    def execute(self):
        yield (self.link_proto.PID_COMMAND_DATA, 0x02a5)


class A1000(DownloadProtocol):
    """
    Get runs.
    """

    def __init__(self, protocols, run_type):
        super(A1000, self).__init__(protocols)
        if not protocols.lap_proto or not protocols.trk_proto:
            raise DeviceNotSupportedError("A1000 required device to supoprt lap and track protocols.")
        self.lap_proto = protocols.lap_proto
        self.trk_proto = protocols.trk_proto
        self.data_type_by_pid.update({
            self.link_proto.PID_RUN: run_type,
        })
        self.pid_data = [self.link_proto.PID_RUN]
        
    def execute(self):
        _log.debug("A1000: executing transfer runs")
        yield (self.link_proto.PID_COMMAND_DATA, self.cmd_proto.CMND_TRANSFER_RUNS)
        yield self.lap_proto
        yield self.trk_proto


class A301(DownloadProtocol):
    """
    Get tracks
    """

    def __init__(self, protocols, trk_hdr_type, trk_type):
        super(A301, self).__init__(protocols)
        self.data_type_by_pid.update({
            self.link_proto.PID_TRK_HDR: trk_hdr_type,
            self.link_proto.PID_TRK_DATA: trk_type,
            self.link_proto.PID_TRK_DATA_ARRAY: trk_type,
        })
        self.pid_data = [
            self.link_proto.PID_TRK_HDR,
            self.link_proto.PID_TRK_DATA,
            self.link_proto.PID_TRK_DATA_ARRAY,
        ]

    def execute(self):
        _log.debug("A301: executing transfer tracks")
        yield (self.link_proto.PID_COMMAND_DATA, self.cmd_proto.CMND_TRANSFER_TRK)

    def on_data(self, pid, data):
        """
        PID_TRK_DATA_ARRAY return multiple data objects per
        packet, override default products implementation to override.
        """
        if pid == self.link_proto.PID_TRK_DATA_ARRAY:
            self.count += data.num_valid_wpt - 1
        super(A301, self).on_data(pid, data)


class A302(A301):
    """
    Same as 301
    """


class A906(DownloadProtocol):
    """
    Get laps
    """

    def __init__(self, protocols, lap_type):
        super(A906, self).__init__(protocols)
        self.data_type_by_pid.update({
            self.link_proto.PID_LAP: lap_type
        })
        self.pid_data = [self.link_proto.PID_LAP]

    def execute(self):
        _log.debug("A906: executing transfer laps")
        yield (self.link_proto.PID_COMMAND_DATA, self.cmd_proto.CMND_TRANSFER_LAPS)


class PacketList(list):

    Packet = collections.namedtuple("Packet", ["pid", "length", "data"])

    def __init__(self, iterable):
        super(PacketList, self).__init__(self.Packet(*i) for i in iterable)
        self._update_packets_by_id()

    def _update_packets_by_id(self):
        d = collections.defaultdict(list)
        for pkt in self: d[pkt[0]].append(pkt)
        self.by_pid = d


class DataType(object):
    """
    DataType is base implementation for parser which
    interpruts the data payload of a garmin packet.
    Default implentation save message .raw property
    but provides no addition properties.
    """

    def __init__(self, raw_str):
        self.raw = raw_str
        self.unparsed = self.raw
        self.str_args = []

    def _unpack(self, format, arg_names):
        """
        Use the givem format to extract the give
        proeprty names from this instance unparsed text.
        """
        sz = struct.calcsize(format)
        data = self.unparsed[:sz]
        self.unparsed = self.unparsed[sz:]
        args = struct.unpack(format, data)
        assert len(args) == len(arg_names)
        for name, arg in zip(arg_names, args):
            setattr(self, name, arg)
        self.str_args.extend(arg_names)
        
    def _parse(self, type, arg_name=None):
        """
        Invoke a composite data type to parse
        from start of this instance's unparsed text.
        If arg_name is provided, reulst will be
        assigned as attribute of this instance.
        """
        data = type(self.unparsed)
        if arg_name:
            setattr(self, arg_name, data)
            self.str_args.append(arg_name)
        self.unparsed = data.unparsed
        data.unparsed = ""
        return data

    def __str__(self):
        parsed_args = [(k, getattr(self, k)) for k in self.str_args]
        if not self.unparsed:
            return "%s%s" % (self.__class__.__name__, parsed_args)
        else:
            return "%s%s, unparsed=%s" % (self.__class__.__name__, parsed_args,
                                          abbrev(self.unparsed.encode("hex"), 32))
        
    def __repr__(self):
        return self.__str__()


class TimeType(DataType):
    
    EPOCH = 631065600 # Dec 31, 1989 @ 12:00am UTC  

    def __init__(self, data):
       super(TimeType, self).__init__(data)
       self._unpack("<I", ["time"])

    @property
    def gmtime(self):
        return time.gmtime(self.EPOCH + self.time)

class PositionType(DataType):
    
    INVALID_SEMI_CIRCLE = 2**31 - 1

    def __init__(self, data):
        super(PositionType, self).__init__(data)
        self._unpack("<ii", ["lat", "lon"])
        self.valid = self.lat != self.INVALID_SEMI_CIRCLE and self.lon != self.INVALID_SEMI_CIRCLE
        if self.valid:
            self.deglat = self.lat * (180. / 2**31)
            self.deglon = self.lon * (180. / 2**31)
        else:
            self.deglat, self.deflon, lat, lon = [None] * 4


class CommandIdType(DataType):
    
    def __init__(self, data):
        super(CommandIdType, self).__init__(data)
        self._unpack("<H", ["command_id"])


class RecordsType(DataType):

    def __init__(self, data):
        super(RecordsType, self).__init__(data)
        self._unpack("<H", ["count"])


class ProductDataType(DataType):

    def __init__(self, data):
        super(ProductDataType, self).__init__(data)
        self._unpack("<Hh", ["product_id", "software_version"])
        self.description = [str for str in self.unparsed.split("\x00") if str]
        self.str_args.append("description")


class ExtProductDataType(DataType):
    
    def __init__(self, data):
        super(ExtProductDataType, self).__init__(data)
        self.description = [str for str in data.split("\x00") if str]
        self.str_args.append("description")


class ProtocolArrayType(DataType):
    
    def __init__(self, data):
        super(ProtocolArrayType, self).__init__(data)
        self.protocol_array = ["%s%03d" % (proto, ord(msb) << 8 | ord(lsb)) for proto, lsb, msb in chunk(data, 3)]
        self.str_args.append("protocol_array")


class WorkoutStepType(DataType):

    def __init__(self, data):
        super(WorkoutStepType, self).__init__(data)
        self._unpack("<16sffHBBBB2x", [
            "custom_name",
            "target_custom_zone_low",
            "target_cusomt_zone_hit",
            "duration_value",
            "intensity",
            "duration_type",
            "target_type",
            "target_value",
        ])
        self.custom_name = self.custom_name[:self.custom_name.index("\x00")]


class D1008(DataType):
    """
    Workout
    """
    
    def __init__(self, data):
        super(D1008, self).__init__(data)
        self._unpack("<I", ["num_valid_steps"])
        self.steps = [None] * self.num_valid_steps
        for step_num in xrange(0, self.num_valid_steps):
            self.steps[step_num] = self._parse(WorkoutStepType)
        self._unpack("<16sb", ["name", "sport_type"])
        self.name = self.name[:self.name.index("\x00")]


class D1009(DataType):
    """
    Run
    """

    def __init__(self, data):
        super(D1009, self).__init__(data)
        self._unpack("<HHHBBBx2x", [
            "track_index",
            "first_lap_index",
            "last_lap_index",
            "sport_type",
            "program_type",
            "multisport",
        ])
        self._parse(TimeType, "time")
        self._unpack("<f", ["distance"])
        self.workout = D1008(self.unparsed)
        self.unparsed = self.workout.unparsed
        self.workout.unparsed = ""
        self.str_args.append("workout")


class D1011(DataType):
    """
    Lap
    """

    def __init__(self, data):
        super(D1011, self).__init__(data)
        self._unpack("<H2x", ["index"])
        self._parse(TimeType, "start_time")
        self._unpack("<Iff", [
            "total_time",
            "total_dist",
            "max_speed",
        ])
        self._parse(PositionType, "begin")
        self._parse(PositionType, "end")
        self._unpack("HBBBBB", [
            "calories",
            "avg_heart_rate",
            "max_heart_rate",
            "intensity",
            "avg_cadence",
            "trigger_method",
        ])
        if self.avg_heart_rate == 0: self.avg_heart_rate = None
        if self.max_heart_rate == 0: self.max_heart_rate = None
        if self.avg_cadence == 0xFF: self.avg_cadence = None


class D1015(D1011):
    """
    Lap + extra mystery bytes
    """

    def __init__(self, data):
        super(D1015, self).__init__(data)
        self._unpack("BBBBB", [
            "undocumented_0",
            "undocumented_1",
            "undocumented_2",
            "undocumented_3",
            "undocumented_4",
        ])


class D311(DataType):
    """
    wpt header
    """
    
    def __init__(self, data):
        super(D311, self).__init__(data)
        self._unpack("<H", ["index"])


class D304(DataType):
    """
    way point
    """
    
    INVALID_FLOAT = struct.unpack("<f", "\x51\x59\x04\x69")[0]

    def __init__(self, data):
        super(D304, self).__init__(data)
        self._parse(PositionType, "posn")
        self._parse(TimeType, "time")
        self._unpack("<ffBBB", [
            "alt",
            "distance",
            "heart_rate",
            "cadence",
            "sensor",
        ])
        if self.alt == self.INVALID_FLOAT: self.alt = None
        if self.distance == self.INVALID_FLOAT: self.distance = None
        if self.cadence == 0xFF: self.cadence = None
        if self.heart_rate == 0: self.heart_rate = None


class D1018(DataType):
    """
    An array of waypoints
    undocumented.
    """
    
    def __init__(self, data):
        super(D1018, self).__init__(data)
        self._unpack("<I", ["num_valid_wpt"])
        self.wpts = [None] * self.num_valid_wpt
        self.str_args.append("wpts")
        for n in xrange(0, self.num_valid_wpt):
            self.wpts[n] = self._parse(D304)
            # word alignment
            self.unparsed = self.unparsed[1:]
        

class DeviceNotSupportedError(Exception):
    """
    Raised device capabilites lack capabilites
    to complete request.
    """


# vim: ts=4 sts=4 et

########NEW FILE########
__FILENAME__ = hw
# Copyright (c) 2012, Braiden Kindt.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
# 
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDER AND CONTRIBUTORS
# ''AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY
# WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.


import usb.core
import usb.util
import errno
import logging
import struct
import array

_log = logging.getLogger("antd.usb")

class UsbHardware(object):
    """
    Provides access to USB based ANT chips.
    Communication is sent of a USB endpoint.
    USB based hardware with a serial bridge
    (e.g. nRF24AP1 + FTDI) is not supported.
    """
    
    def __init__(self, id_vendor=0x0fcf, id_product=0x1008, ep=1):
        for dev in usb.core.find(idVendor=id_vendor, idProduct=id_product, find_all=True):
            try:
                dev.set_configuration()
                usb.util.claim_interface(dev, 0)
                self.dev = dev
                self.ep = ep
                break
            except IOError as (err, msg):
                if err == errno.EBUSY or "Device or resource busy" in msg: #libusb10 or libusb01
                    _log.info("Found device with vid(0x%04x) pid(0x%04x), but interface already claimed.", id_vendor, id_product)
                else:
                    raise
        else:
            raise NoUsbHardwareFound(errno.ENOENT, "No available device matching vid(0x%04x) pid(0x%04x)." % (id_vendor, id_product))

    def close(self):
        usb.util.release_interface(self.dev, 0)

    def write(self, data, timeout):
        transfered = self.dev.write(self.ep | usb.util.ENDPOINT_OUT, data, timeout=timeout)
        if transfered != len(data):
            raise IOError(errno.EOVERFLOW, "Write too large, len(data) > wMaxPacketSize not supported.")

    def read(self, timeout):
        return self.dev.read(self.ep | usb.util.ENDPOINT_IN, 16384, timeout=timeout)


class NoUsbHardwareFound(IOError): pass

class SerialHardware(object):

    def __init__(self, dev="/dev/ttyUSB0", baudrate=115200):
        import serial
        self.dev = serial.Serial(port=dev, baudrate=baudrate, timeout=1)

    def close(self):
        self.dev.close()

    def write(self, data, timeout):
        arr = array.array("B", data)
        self.dev.write(arr.tostring())

    def read(self, timeout):
        # attempt to read the start of packet
        header = self.dev.read(2)
        if header:
            sync, length = struct.unpack("2B", header)
            if sync not in (0xa4, 0xa5):
                raise IOError(-1, "ANT packet did not start with expected SYNC packet. Remove USB device and try again?")
            length += 2 # checksum & msg_id
            data = self.dev.read(length)
            if len(data) != length:
                raise IOError(-1, "ANT packet short?")
            return array.array("B", header + data)
        else:
            raise IOError(errno.ETIMEDOUT, "Timeout")

# vim: ts=4 sts=4 et

########NEW FILE########
__FILENAME__ = main
#!/usr/bin/python

# Copyright (c) 2012, Braiden Kindt.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
# 
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDER AND CONTRIBUTORS
# ''AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY
# WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

def downloader():
    import logging
    import sys
    import time
    import struct
    import argparse
    import os
    import dbm
    import shutil
    import lxml.etree as etree
    import antd
    
    # command line
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", "-c", nargs=1, metavar="f",
            help="use provided configuration, defaults to ~/.antd/antd.cfg")
    parser.add_argument("--daemon", "-d", action="store_const", const=True,
            help="run in continuous search mode downloading data from any available devices, WILL NOT PAIR WITH NEW DEVICES")
    parser.add_argument("--verbose", "-v", action="store_const", const=True,
            help="enable all debugging output, NOISY: see config file to selectively enable loggers")
    parser.add_argument("--force", "-f", action="store_const", const=True,
            help="force a connection with device even if it claims no data available. FOR DEBUG ONLY.")
    args = parser.parse_args()
    
    # load configuration
    cfg = args.config[0] if args.config else None
    if not antd.cfg.read(cfg):
        print "unable to read config file." 
        parser.print_usage()
        sys.exit(1)
    
    # enable debug if -v used
    if args.verbose: antd.cfg.init_loggers(logging.DEBUG)
    _log = logging.getLogger("antd")
    
    # register plugins, add uploaders and file converters here
    antd.plugin.register_plugins(
        antd.cfg.create_garmin_connect_plugin(),
        antd.cfg.create_strava_plugin(),
        antd.cfg.create_tcx_plugin(),
        antd.cfg.create_notification_plugin()
    )
    
    # create an ANTFS host from configuration
    host = antd.cfg.create_antfs_host()
    try:
        failed_count = 0
        while failed_count <= antd.cfg.get_retry():
            try:
                _log.info("Searching for ANT devices.")
                # in daemon mode we do not attempt to pair with unkown devices
                # (it requires gps watch to wake up and would drain battery of
                # any un-paired devices in range.)
                beacon = host.search(include_unpaired_devices=not args.daemon,
                                     include_devices_with_no_data=args.force or not args.daemon)
                if beacon and (beacon.data_available or args.force):
                    _log.info("Device has data. Linking.")
                    host.link()
                    _log.info("Pairing with device.")
                    client_id = host.auth(pair=not args.daemon)
                    raw_name = time.strftime("%Y%m%d-%H%M%S.raw")
                    raw_full_path = antd.cfg.get_path("antd", "raw_output_dir", raw_name, 
                                                      {"device_id": hex(host.device_id)})
                    with open(raw_full_path, "w") as file:
                        _log.info("Saving raw data to %s.", file.name)
                        # create a garmin device, and initialize its
                        # ant initialize its capabilities.
                        dev = antd.Device(host)
                        antd.garmin.dump(file, dev.get_product_data())
                        # download runs
                        runs = dev.get_runs()
                        antd.garmin.dump(file, runs)
                        if antd.cfg.get_delete_from_device(): dev.delete_runs()
                    _log.info("Closing session.")
                    host.disconnect()
                    _log.info("Excuting plugins.")
                    # dispatcher data to plugins
                    antd.plugin.publish_data(host.device_id, "raw", [raw_full_path])
                elif not args.daemon:
                    _log.info("Found device, but no data available for download.")
                if not args.daemon: break
                failed_count = 0
            except antd.AntError:
                _log.warning("Caught error while communicating with device, will retry.", exc_info=True) 
                failed_count += 1
    finally:
        try: host.close()
        except Exception: _log.warning("Failed to cleanup resources on exist.", exc_info=True)
    
    
# vim: ts=4 sts=4 et

########NEW FILE########
__FILENAME__ = notif
# Copyright (c) 2012, Ivan Kelly <ivan@ivankelly.net>
#               2013, Braiden Kindt <braiden@braiden.org>
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
# 
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDER AND CONTRIBUTORS
# ''AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY
# WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import os.path
import antd.plugin as plugin
import logging

_log = logging.getLogger("antd.notif")

import pynotify

class NotifPlugin(plugin.Plugin):
    _enabled = True

    def __init__(self):
        self._enabled = True
        if not pynotify.init("python-ant-downloader"):
            _log.error("Couldn't enabled pynotify, disabling")
            self._enabled = False

    def data_available(self, device_sn, format, files):
        if not self._enabled:
            return files
        
        try:
            filenames = map(os.path.basename, files)
            if format == "notif_connect":
                n = pynotify.Notification(
                    "Ant+ Downloader",
                    "Uploaded files [%s] to Garmin Connect" % ", ".join(filenames),
                    "notification-message-im")
                n.show()
#           elif format == "tcx":
#               n = pynotify.Notification(
#                   "Ant+ Downloader",
#                   "Files [%s] processed" % ", ".join(filenames), 
#                   "notification-message-im")
#               n.show()
        finally:
            return files

########NEW FILE########
__FILENAME__ = plugin
# Copyright (c) 2012, Braiden Kindt.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
# 
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDER AND CONTRIBUTORS
# ''AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY
# WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.


import logging
import dbm
import os

_log = logging.getLogger("antd.plugin")
_plugins = []

class Plugin(object):
    """
    A plugin receives notifications when new data
    is available, it can consume the data or transform it.
    TCX file generation, and garmin connect upload are
    both implementations of plugin. You can implement
    your own to produce new file formats or upload somewhere.
    """

    def data_available(self, device_sn, format, files):
        """
        Notification that data is available, this could
        be raw packet data from device, or higher level
        data generated by other plugins, e.g. TCX.
        Return: files which were sucessfullly processed.
        """
        pass


class PluginQueue(object):
    """
    File based queue representing unprocessed
    files which were not handled the a plugin.
    """

    def __init__(self, plugin):
        try: self.queue_file_name = plugin.cache
        except AttributeError: self.queue_file_name = None
        self.queue = []

    def load_queue(self):
        if self.queue_file_name and os.path.isfile(self.queue_file_name):
            with open(self.queue_file_name, "r") as file:
                lines = file.read().splitlines()
            self.queue = []
            for line in lines:
                device_sn, format, file = line.split(",")
                if os.path.isfile(file):
                    self.queue.append((int(device_sn), format, file))
                else:
                    _log.warning("File pending processing, but disappeared. %s", file)
    
    def save_queue(self):
        if self.queue_file_name and self.queue: 
            with open(self.queue_file_name, "w") as file:
                file.writelines("%d,%s,%s\n" % e for e in self.queue)
        elif self.queue_file_name and os.path.isfile(self.queue_file_name):
            os.unlink(self.queue_file_name)
    
    def add_to_queue(self, device_sn, format, files):
        for file in files:
            self.queue.append((device_sn, format, file))


def register_plugins(*plugins):
    _plugins.extend(p for p in plugins if p is not None)
    for plugin in plugins:
        try: plugin and recover_and_publish_data(plugin) 
        except Exception: _log.warning("Plugin failed. %s", plugin, exc_info=True)

def recover_and_publish_data(plugin):
    q = PluginQueue(plugin)
    q.load_queue()
    if q.queue:
        try:
            _log.debug("Attempting to reprocess failed files.")
            for device_sn, format, file in list(q.queue):
                if plugin.data_available(device_sn, format, [file]):
                    q.queue.remove((device_sn, format, file))
        except Exception:
            _log.warning("Plugin failed. %s", plugin, exc_info=True)
        finally:
            q.save_queue()
    
def publish_data(device_sn, format, files):
    for plugin in _plugins:
        try:
            processed = plugin.data_available(device_sn, format, files)
            not_processed = [f for f in files if f not in processed]
        except Exception: 
            processed = []
            not_processed = files
            _log.warning("Plugin failed. %s", plugin, exc_info=True)
        finally:
            q = PluginQueue(plugin)
            q.load_queue()
            q.add_to_queue(device_sn, format, not_processed)
            q.save_queue()


# vim: ts=4 sts=4 et

########NEW FILE########
__FILENAME__ = tcx
# Copyright (c) 2012, Braiden Kindt.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
# 
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDER AND CONTRIBUTORS
# ''AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY
# WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.


import logging
import time
import os
import glob
import shutil
import lxml.etree as etree
import lxml.builder as builder

import antd.plugin as plugin
import antd.garmin as garmin

_log = logging.getLogger("antd.tcx")

E = builder.ElementMaker(nsmap={
    None: "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2",
    "ext": "http://www.garmin.com/xmlschemas/ActivityExtension/v2",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
})

X = builder.ElementMaker(namespace="http://www.garmin.com/xmlschemas/ActivityExtension/v2")

class TcxPlugin(plugin.Plugin):
    
    tcx_output_dir = "."

    def data_available(self, device_sn, format, files):
        if "raw" != format: return files
        processed = []
        result = []
        try:
            for file in files:
                _log.info("TcxPlugin: processing %s.", file)
                try:
                    dir = self.tcx_output_dir % {"device_id": hex(device_sn)}
                    if not os.path.exists(dir): os.makedirs(dir)
                    files = export_tcx(device_sn, file, dir)
                    result.extend(files)
                    processed.append(file)
                except Exception:
                    _log.warning("Failed to process %s. Maybe a datatype is unimplemented?", file, exc_info=True)
            plugin.publish_data(device_sn, "tcx", result)
        finally:
            return processed


def format_time(gmtime):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", gmtime)

def format_intensity(intensity):
    if intensity == 1:
        return "Resting"
    else:
        return "Active"

def format_trigger_method(trigger_method):
    if trigger_method == 0: return "Manual"
    elif trigger_method == 1: return "Distance"
    elif trigger_method == 2: return "Location"
    elif trigger_method == 3: return "Time"
    elif trigger_method == 4: return "HeartRate"

def format_sport(sport):
    if sport == 0: return "Running"
    elif sport == 1: return "Biking"
    elif sport == 2: return "Other"

def format_sensor_state(sensor):
    if sensor: return "Present"
    else: return "Absent"

def create_wpt(wpt, sport_type):
    elements = [E.Time(format_time(wpt.time.gmtime))]
    if wpt.posn.valid:
        elements.extend([
            E.Position(
                E.LatitudeDegrees(str(wpt.posn.deglat)),
                E.LongitudeDegrees(str(wpt.posn.deglon)))])
    if wpt.alt is not None:
        elements.append(E.AltitudeMeters(str(wpt.alt)))
    if wpt.distance is not None:
        elements.append(E.DistanceMeters(str(wpt.distance)))
    if wpt.heart_rate:
        elements.append(E.HeartRateBpm(E.Value(str(wpt.heart_rate))))
    if wpt.cadence is not None and sport_type != 0:
        elements.append(E.Cadence(str(wpt.cadence)))
    #elements.append(E.SensorState(format_sensor_state(wpt.sensor)))
    if wpt.cadence is not None and sport_type == 0:
        elements.append(E.Extensions(X.TPX(X.RunCadence(str(wpt.cadence)))))
    #if len(elements) > 1:
    return E.Trackpoint(*elements)

def create_lap(lap, sport_type):
    elements = [
        E.TotalTimeSeconds("%0.2f" % (lap.total_time / 100.)),
        E.DistanceMeters(str(lap.total_dist)),
        E.MaximumSpeed(str(lap.max_speed)),
        E.Calories(str(lap.calories))]
    if lap.avg_heart_rate or lap.max_heart_rate:
        elements.extend([
            E.AverageHeartRateBpm(E.Value(str(lap.avg_heart_rate))),
            E.MaximumHeartRateBpm(E.Value(str(lap.max_heart_rate)))])
    elements.append(
        E.Intensity(format_intensity(lap.intensity)))
    if lap.avg_cadence is not None and sport_type != 0:
        elements.append(
            E.Cadence(str(lap.avg_cadence)))
    elements.append(E.TriggerMethod(format_trigger_method(lap.trigger_method)))
    wpts = [el for el in (create_wpt(w, sport_type) for w in lap.wpts) if el is not None]
    if wpts:
        elements.append(E.Track(*wpts))
    if lap.avg_cadence is not None and sport_type == 0:
        elements.append(E.Extensions(X.LX(X.AvgRunCadence(str(lap.avg_cadence)))))
    return E.Lap(
        {"StartTime": format_time(lap.start_time.gmtime)},
        *elements)

def create_creator(device):
    major = device.device_id.software_version / 100
    minor = device.device_id.software_version % 100
    return E.Creator({"{http://www.w3.org/2001/XMLSchema-instance}type": "Device_t"},
                     E.Name("".join(device.device_id.description)),
                     E.UnitId(str(device.stream.device_id)),
                     E.ProductID(str(device.device_id.product_id)),
                     E.Version(E.VersionMajor(str(major)),
                               E.VersionMinor(str(minor)),
                               E.BuildMajor("0"),
                               E.BuildMinor("0")))


def create_activity(device, run):
    laps = list(create_lap(l, run.sport_type) for l in run.laps)
    return E.Activity(
        {"Sport": format_sport(run.sport_type)},
        E.Id(format_time(run.time.gmtime)),
        *(laps + [create_creator(device)]))

def create_document(device, runs):
    doc = E.TrainingCenterDatabase(
        E.Activities(
            *list(create_activity(device, r) for r in runs)))
    return doc

def export_tcx(device_sn, raw_file_name, output_dir):
    """
    Given a garmin raw packet dump, tcx to specified output directory.
    """
    with open(raw_file_name) as file:
        result = []
        host = garmin.MockHost(file.read())
        host.device_id = device_sn
        device = garmin.Device(host)
        run_pkts = device.get_runs()
        runs = garmin.extract_runs(device, run_pkts)
        for run in runs:
            tcx_name = time.strftime("%Y%m%d-%H%M%S.tcx", run.time.gmtime)
            tcx_full_path = os.path.sep.join([output_dir, tcx_name])
            _log.info("tcx: writing %s -> %s.", os.path.basename(raw_file_name), tcx_full_path)
            with open(tcx_full_path, "w") as file:
                doc = create_document(device, [run])
                file.write(etree.tostring(doc, pretty_print=True, xml_declaration=True, encoding="UTF-8"))
            result.append(tcx_full_path)
        return result


# vim: ts=4 sts=4 et

########NEW FILE########
__FILENAME__ = raw2string
#!/usr/bin/env python

# Copyright (c) 2012, Braiden Kindt.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
# 
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDER AND CONTRIBUTORS
# ''AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY
# WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.


import sys
import logging
import lxml.etree as etree

import antd.garmin as garmin
import antd.tcx as tcx
import antd.cfg as cfg

cfg.init_loggers(logging.DEBUG, out=sys.stderr)

if len(sys.argv) != 2:
	print "usage: %s <file>" % sys.argv[0]
	sys.exit(1)

with open(sys.argv[1]) as file:
	host = garmin.MockHost(file.read())
	#device = garmin.Device(host)
	for idx, pkt in enumerate(host.reader):
		if pkt:
			pid, length, data = garmin.unpack(pkt)
			data = "\n".join([(d if not idx else (" " * 23) + d) for idx, d in enumerate(garmin.chunk(data.encode("hex"), 32))])
			print "%04d pid=%04x len=%04x %s" % (idx, pid, length, data)
		else:
			print "%04d EOF" % idx

########NEW FILE########
__FILENAME__ = raw2tcx
#!/usr/bin/env python

# Copyright (c) 2012, Braiden Kindt.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
# 
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDER AND CONTRIBUTORS
# ''AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY
# WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.


import sys
import logging
import lxml.etree as etree

import antd.garmin as garmin
import antd.tcx as tcx
import antd.cfg as cfg

cfg.init_loggers(logging.DEBUG, out=sys.stderr)

if len(sys.argv) != 2:
	print "usage: %s <file>" % sys.argv[0]
	sys.exit(1)

with open(sys.argv[1]) as file:
	host = garmin.MockHost(file.read())
	host.device_id = 0
	device = garmin.Device(host)
	runs = device.get_runs()
	doc = tcx.create_document(device, garmin.extract_runs(device, runs))
	print etree.tostring(doc, pretty_print=True, xml_declaration=True, encoding="UTF-8")

########NEW FILE########
__FILENAME__ = test_master
#!/usr/bin/python

import sys
import logging
import time

import antd.ant as ant
import antd.hw as hw

logging.basicConfig(
        level=logging.DEBUG,
        out=sys.stderr,
        format="[%(threadName)s]\t%(asctime)s\t%(levelname)s\t%(message)s")

_LOG = logging.getLogger()

dev = hw.UsbHardware()
core = ant.Core(dev)
session = ant.Session(core)
try:
    channel = session.channels[0]
    network = session.networks[0]
    network.set_key("\x00" * 8)
    channel.assign(channel_type=0x30, network_number=0)
    channel.set_id(device_number=0, device_type_id=0, trans_type=0)
    channel.set_period(0x4000)
    channel.set_search_timeout(20)
    channel.set_rf_freq(40)
    channel.open()
    channel.send_broadcast("testtest")
    while True:
        _LOG.info("READ %s", channel.read(timeout=10))
finally:
    try: session.close()
    except: _LOG.warning("Caught exception while resetting system.", exc_info=True)


# vim: ts=4 sts=4 et

########NEW FILE########
__FILENAME__ = test_notif
#!/usr/bin/python

import antd.plugin as plugin
import antd.notif as notif
import antd.cfg as cfg

cfg._cfg.add_section("antd.notification")
cfg._cfg.set("antd.notification", "enabled", "True")
cfg.init_loggers()

plugin.register_plugins(
    cfg.create_notification_plugin()
)

files = ['file1', 'file2', 'file3']

plugin.publish_data("0xdeadbeef", "notif_connect", files)

plugin.publish_data("0xdeadbeef", "notif_junk", files)
plugin.publish_data("0xdeadbeef", "complete_junk", files)


########NEW FILE########
__FILENAME__ = test_slave
#!/usr/bin/python

import sys
import logging

import antd.ant as ant
import antd.hw as hw

logging.basicConfig(
        level=logging.DEBUG,
        out=sys.stderr,
        format="[%(threadName)s]\t%(asctime)s\t%(levelname)s\t%(message)s")

_LOG = logging.getLogger()

dev = hw.UsbHardware()
core = ant.Core(dev)
session = ant.Session(core)
try:
    channel = session.channels[0]
    network = session.networks[0]
    network.set_key("\x00" * 8)
    channel.assign(channel_type=0x00, network_number=0)
    channel.set_id(device_number=0, device_type_id=0, trans_type=0)
    channel.set_period(0x4000)
    channel.set_search_timeout(4)
    channel.set_rf_freq(40)
    channel.open()
    _LOG.info("BROADCAST: %s", channel.recv_broadcast(timeout=0))
    channel.send_acknowledged("ack")
    channel.send_burst("burst")
    channel.send_burst("burst" * 10)
    channel.write("write")
finally:
    try: session.close()
    except: _LOG.warning("Caught exception while resetting system.", exc_info=True)


# vim: ts=4 sts=4 et

########NEW FILE########
__FILENAME__ = test_wait_for_broadcast
#!/usr/bin/python

import sys
import logging

import antd.ant as ant
import antd.hw as hw

logging.basicConfig(
        level=logging.DEBUG,
        out=sys.stderr,
        format="[%(threadName)s]\t%(asctime)s\t%(levelname)s\t%(message)s")

_LOG = logging.getLogger()

dev = hw.UsbHardware()
core = ant.Core(dev)
session = ant.Session(core)
try:
    channel = session.channels[0]
    network = session.networks[0]
    network.set_key("\xa8\xa4\x23\xb9\xf5\x5e\x63\xc1")
    channel.assign(channel_type=0x00, network_number=0)
    channel.set_id(device_number=0, device_type_id=0, trans_type=0)
    channel.set_period(0x1000)
    channel.set_search_timeout(20)
    channel.set_rf_freq(50)
    channel.set_search_waveform(0x0053)
    channel.open()
    print channel.recv_broadcast(timeout=0).encode("hex")
finally:
    try: session.close()
    except: _LOG.warning("Caught exception while resetting system.", exc_info=True)


# vim: ts=4 sts=4 et

########NEW FILE########
