__FILENAME__ = ant
# Ant
#
# Copyright (c) 2012, Gustav Tiger <gustav@tiger.name>
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import array
import collections
import struct
import threading
import time
import Queue
import logging

import usb.core
import usb.util

from message import Message
from commons import format_list
from driver import find_driver

_logger = logging.getLogger("garmin.ant.base.ant")

class Ant():

    _RESET_WAIT = 1

    def __init__(self):

        self._driver = find_driver()

        self._message_queue_cond = threading.Condition()
        self._message_queue      = collections.deque()

        self._events = Queue.Queue()
    
        self._buffer = array.array('B', [])
        self._burst_data = array.array('B', [])
        self._last_data = array.array('B', [])

        self._running = True

        self._driver.open()

        self._worker_thread = threading.Thread(target=self._worker, name="ant.base")
        self._worker_thread.start()

        self.reset_system()

    def start(self):
        self._main()

    def stop(self):
        if self._running:
            _logger.debug("Stoping ant.base")
            self._running = False
            self._worker_thread.join()

    def _on_broadcast(self, message):
        self._events.put(('event', (message._data[0],
                Message.Code.EVENT_RX_BROADCAST, message._data[1:])))

    def _on_acknowledge(self, message):
        self._events.put(('event', (message._data[0],
                Message.Code.EVENT_RX_ACKNOWLEDGED, message._data[1:])))

    def _on_burst_data(self, message):

        sequence = message._data[0] >> 5
        channel  = message._data[0] & 0b00011111
        data     = message._data[1:]
        
        # First sequence
        if sequence == 0:
            self._burst_data = data
        # Other
        else:
            self._burst_data.extend(data)

        # Last sequence (indicated by bit 3)
        if sequence & 0b100 != 0:
            self._events.put(('event', (channel,
                    Message.Code.EVENT_RX_BURST_PACKET, self._burst_data)))

    def _worker(self):

        _logger.debug("Ant runner started")

        while self._running:
            try:
                message = self.read_message()
                
                if message == None:
                    break

                # TODO: flag and extended for broadcast, acknowledge, and burst

                # Only do callbacks for new data. Resent data only indicates
                # a new channel timeslot.
                if not (message._id == Message.ID.BROADCAST_DATA and 
                    message._data == self._last_data):
                   
                    # Notifications
                    if message._id in [Message.ID.STARTUP_MESSAGE, \
                            Message.ID.SERIAL_ERROR_MESSAGE]:
                        self._events.put(('response', (None, message._id, 
                                message._data)))
                    # Response (no channel)
                    elif message._id in [Message.ID.RESPONSE_VERSION, \
                            Message.ID.RESPONSE_CAPABILITIES, \
                            Message.ID.RESPONSE_SERIAL_NUMBER]:
                        self._events.put(('response', (None, message._id,
                                message._data)))
                    # Response (channel)
                    elif message._id in [Message.ID.RESPONSE_CHANNEL_STATUS, \
                            Message.ID.RESPONSE_CHANNEL_ID]:
                        self._events.put(('response', (message._data[0],
                                message._id, message._data[1:])))
                    # Response (other)
                    elif (message._id == Message.ID.RESPONSE_CHANNEL \
                          and message._data[1] != 0x01):
                        self._events.put(('response', (message._data[0], 
                                message._data[1], message._data[2:])))
                    # Channel event
                    elif message._id == Message.ID.BROADCAST_DATA:
                        self._on_broadcast(message)
                    elif message._id == Message.ID.ACKNOWLEDGE_DATA:
                        self._on_acknowledge(message)
                    elif message._id == Message.ID.BURST_TRANSFER_DATA:
                        self._on_burst_data(message)
                    elif message._id == Message.ID.RESPONSE_CHANNEL:
                        _logger.debug("Got channel event, %r", message)
                        self._events.put(('event', (message._data[0],
                                message._data[1], message._data[2:])))
                    else:
                        _logger.warning("Got unknown message, %r", message)
                else:
                    _logger.debug("No new data this period")

                # Send messages in queue, on indicated time slot
                if message._id == Message.ID.BROADCAST_DATA:
                    time.sleep(0.1)
                    _logger.debug("Got broadcast data, examine queue to see if we should send anything back")
                    if self._message_queue_cond.acquire(blocking=False):
                        while len(self._message_queue) > 0:
                            m = self._message_queue.popleft()
                            self.write_message(m)
                            _logger.debug(" - sent message from queue, %r", m)
                            
                            if(m._id != Message.ID.BURST_TRANSFER_DATA or \
                               m._data[0] & 0b10000000):# or m._data[0] == 0):
                                break
                        else:
                            _logger.debug(" - no messages in queue")
                        self._message_queue_cond.release()

                self._last_data = message._data

            except usb.USBError as e:
                _logger.warning("%s, %r", type(e), e.args)

        _logger.debug("Ant runner stopped")

    def _main(self):
        while self._running:
            try:
                (event_type, event) = self._events.get(True, 1.0)
                self._events.task_done()
                (channel, event, data) = event
                
                if event_type == 'response':
                    self.response_function(channel, event, data)
                elif event_type == 'event':
                    self.channel_event_function(channel, event, data)
                else:
                    _logger.warning("Unknown message typ '%s': %r", event_type, event)
            except Queue.Empty as e:
                pass

    def write_message_timeslot(self, message):
        with self._message_queue_cond:
            self._message_queue.append(message)

    def write_message(self, message):
        data = message.get()
        self._driver.write(data)
        _logger.debug("Write data: %s", format_list(data))


    def read_message(self):
        while self._running:
            # If we have a message in buffer already, return it
            if len(self._buffer) >= 5 and len(self._buffer) >= self._buffer[1] + 4:
                packet       = self._buffer[:self._buffer[1] + 4]
                self._buffer = self._buffer[self._buffer[1] + 4:]
                return Message.parse(packet)
            # Otherwise, read some data and call the function again
            else:
                data = self._driver.read()
                self._buffer.extend(data)
                _logger.debug("Read data: %s (now have %s in buffer)",
                              format_list(data), format_list(self._buffer))

    # Ant functions

    def unassign_channel(self, channel):
        pass

    def assign_channel(self, channel, channelType, networkNumber):
        message = Message(Message.ID.ASSIGN_CHANNEL, [channel, channelType, networkNumber])
        self.write_message(message)

    def open_channel(self, channel):
        message = Message(Message.ID.OPEN_CHANNEL, [channel])
        self.write_message(message)

    def set_channel_id(self, channel, deviceNum, deviceType, transmissionType):
        data = array.array('B', struct.pack("<BHBB", channel, deviceNum, deviceType, transmissionType))
        message = Message(Message.ID.SET_CHANNEL_ID, data)
        self.write_message(message)

    def set_channel_period(self, channel, messagePeriod):
        data = array.array('B', struct.pack("<BH", channel, messagePeriod))
        message = Message(Message.ID.SET_CHANNEL_PERIOD, data)
        self.write_message(message)

    def set_channel_search_timeout(self, channel, timeout):
        message = Message(Message.ID.SET_CHANNEL_SEARCH_TIMEOUT, [channel, timeout])
        self.write_message(message)

    def set_channel_rf_freq(self, channel, rfFreq):
        message = Message(Message.ID.SET_CHANNEL_RF_FREQ, [channel, rfFreq])
        self.write_message(message)

    def set_network_key(self, network, key):
        message = Message(Message.ID.SET_NETWORK_KEY, [network] + key)
        self.write_message(message)

    # This function is a bit of a mystery. It is mentioned in libgant,
    # http://sportwatcher.googlecode.com/svn/trunk/libgant/gant.h and is
    # also sent from the official ant deamon on windows.
    def set_search_waveform(self, channel, waveform):
        message = Message(Message.ID.SET_SEARCH_WAVEFORM, [channel] + waveform)
        self.write_message(message)

    def reset_system(self):
        message = Message(Message.ID.RESET_SYSTEM, [0x00])
        self.write_message(message)
        time.sleep(self._RESET_WAIT)

    def request_message(self, channel, messageId):
        message = Message(Message.ID.REQUEST_MESSAGE, [channel, messageId])
        self.write_message(message)

    def send_acknowledged_data(self, channel, data):
        assert len(data) == 8
        message = Message(Message.ID.ACKNOWLEDGE_DATA,
                          array.array('B', [channel]) + data)
        self.write_message_timeslot(message)

    def send_burst_transfer_packet(self, channel_seq, data, first):
        assert len(data) == 8
        message = Message(Message.ID.BURST_TRANSFER_DATA,
                          array.array('B', [channel_seq]) + data)
        self.write_message_timeslot(message)

    def send_burst_transfer(self, channel, data):
        assert len(data) % 8 == 0
        _logger.debug("Send burst transfer, chan %s, data %s", channel, data)
        packets = len(data) / 8
        for i in range(packets):
            sequence = ((i - 1) % 3) + 1
            if i == 0:
                sequence = 0
            elif i == packets - 1:
                sequence = sequence | 0b100
            channel_seq = channel | sequence << 5
            packet_data = data[i * 8:i * 8 + 8]
            _logger.debug("Send burst transfer, packet %d, seq %d, data %s", i, sequence, packet_data)
            self.send_burst_transfer_packet(channel_seq, packet_data, first=i==0)

    def response_function(self, channel, event, data):
        pass

    def channel_event_function(self, channel, event, data):
        pass

########NEW FILE########
__FILENAME__ = commons
# Ant
#
# Copyright (c) 2012, Gustav Tiger <gustav@tiger.name>
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

def format_list(l):
    return "[" + " ".join(map(lambda a: str.format("{0:02x}", a), l)) + "]"



########NEW FILE########
__FILENAME__ = driver
# Ant
#
# Copyright (c) 2012, Gustav Tiger <gustav@tiger.name>
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import logging

_logger = logging.getLogger("garmin.ant.base.driver")

class DriverException(Exception):
    pass

class DriverNotFound(DriverException):
    pass

class DriverTimeoutException(DriverException):
    pass

class Driver:
    
    @classmethod
    def find(cls):
        pass
    
    def open(self):
        pass
    
    def close(self):
        pass

    def read(self):
        pass
    
    def write(self, data):
        pass

drivers = []

try:
    import array
    import os
    import os.path

    import serial

    class SerialDriver(Driver):

        ID_VENDOR  = 0x0fcf
        ID_PRODUCT = 0x1004

        @classmethod
        def find(cls):
            return cls.get_url() != None
        
        @classmethod
        def get_url(cls):
            try:
                path = '/sys/bus/usb-serial/devices'
                for device in os.listdir(path):
                    try:
                        device_path = os.path.realpath(os.path.join(path, device))
                        device_path = os.path.join(device_path, "../../")
                        ven = int(open(os.path.join(device_path, 'idVendor')).read().strip(), 16)
                        pro = int(open(os.path.join(device_path, 'idProduct')).read().strip(), 16)
                        if ven == cls.ID_VENDOR or cls.ID_PRODUCT == pro:
                            return os.path.join("/dev", device)
                    except:
                        continue
                return None
            except OSError:
                return None
        
        def open(self):
            
            # TODO find correct port on our own, could be done with
            #      serial.tools.list_ports, but that seems to have some
            #      problems at the moment.
            
            try:
                self._serial = serial.serial_for_url(self.get_url(), 115200)
            except serial.SerialException as e:
                raise DriverException(e)
            
            print "Serial information:"
            print "name:            ", self._serial.name
            print "port:            ", self._serial.port
            print "baudrate:        ", self._serial.baudrate
            print "bytesize:        ", self._serial.bytesize
            print "parity:          ", self._serial.parity
            print "stopbits:        ", self._serial.stopbits
            print "timeout:         ", self._serial.timeout
            print "writeTimeout:    ", self._serial.writeTimeout
            print "xonxoff:         ", self._serial.xonxoff
            print "rtscts:          ", self._serial.rtscts
            print "dsrdtr:          ", self._serial.dsrdtr
            print "interCharTimeout:", self._serial.interCharTimeout

            self._serial.timeout = 0
        
        def read(self):
            data = self._serial.read(4096)
            #print "serial read", len(data), type(data), data
            return array.array('B', data)

        def write(self, data):
            try:
                #print "serial write", type(data), data
                self._serial.write(data)
            except serial.SerialTimeoutException as e:
                raise DriverTimeoutException(e)

        def close(self):
            self._serial.close()

    drivers.append(SerialDriver)
    
except ImportError:
    pass


try:
    import usb.core
    import usb.util

    class USBDriver(Driver):

        def __init__(self):
            pass

        @classmethod
        def find(cls):
            return usb.core.find(idVendor=cls.ID_VENDOR, idProduct=cls.ID_PRODUCT) != None

        def open(self):
            # Find USB device
            _logger.debug("USB Find device, vendor %#04x, product %#04x", self.ID_VENDOR, self.ID_PRODUCT)
            dev = usb.core.find(idVendor=self.ID_VENDOR, idProduct=self.ID_PRODUCT)

            # was it found?
            if dev is None:
                raise ValueError('Device not found')

            _logger.debug("USB Config values:")
            for cfg in dev:
                _logger.debug(" Config %s", cfg.bConfigurationValue)
                for intf in cfg:
                    _logger.debug("  Interface %s, Alt %s", str(intf.bInterfaceNumber), str(intf.bAlternateSetting))
                    for ep in intf:
                        _logger.debug("   Endpoint %s", str(ep.bEndpointAddress))

            # unmount a kernel driver (TODO: should probably reattach later)
            try:
                if dev.is_kernel_driver_active(0):
                    _logger.debug("A kernel driver active, detatching")
                    dev.detach_kernel_driver(0)
                else:
                    _logger.debug("No kernel driver active")
            except NotImplementedError as e:
                _logger.warning("Could not check if kernel driver was active, not implemented in usb backend")

            # set the active configuration. With no arguments, the first
            # configuration will be the active one
            dev.set_configuration()
            dev.reset()
            #dev.set_configuration()

            # get an endpoint instance
            cfg = dev.get_active_configuration()
            interface_number = cfg[(0,0)].bInterfaceNumber
            alternate_setting = usb.control.get_interface(dev, interface_number)
            intf = usb.util.find_descriptor(
                cfg, bInterfaceNumber = interface_number,
                bAlternateSetting = alternate_setting
            )

            self._out = usb.util.find_descriptor(
                intf,
                # match the first OUT endpoint
                custom_match = \
                lambda e: \
                    usb.util.endpoint_direction(e.bEndpointAddress) == \
                    usb.util.ENDPOINT_OUT
            )

            _logger.debug("UBS Endpoint out: %s, %s", self._out, self._out.bEndpointAddress)

            self._in = usb.util.find_descriptor(
                intf,
                # match the first OUT endpoint
                custom_match = \
                lambda e: \
                    usb.util.endpoint_direction(e.bEndpointAddress) == \
                    usb.util.ENDPOINT_IN
            )

            _logger.debug("UBS Endpoint in: %s, %s", self._in, self._in.bEndpointAddress)

            assert self._out is not None and self._in is not None
        
        def close(self):
            pass
        
        def read(self):
            return self._in.read(4096)
        
        def write(self, data):
            self._out.write(data)

    class USB2Driver(USBDriver):
        ID_VENDOR  = 0x0fcf
        ID_PRODUCT = 0x1008

    class USB3Driver(USBDriver):
        ID_VENDOR  = 0x0fcf
        ID_PRODUCT = 0x1009

    drivers.append(USB2Driver)
    drivers.append(USB3Driver)

except ImportError:
    pass

def find_driver():
    
    print "Driver available:", drivers
    
    for driver in reversed(drivers):
        if driver.find():
            print " - Using:", driver
            return driver()
    raise DriverNotFound


########NEW FILE########
__FILENAME__ = message
# Ant
#
# Copyright (c) 2012, Gustav Tiger <gustav@tiger.name>
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import array
import collections
import struct
import threading
import logging

from commons import format_list

_logger = logging.getLogger("garmin.ant.base.message")

class Message:

    class ID:
        INVALID                            = 0x00

        # Configuration messages
        UNASSIGN_CHANNEL                   = 0x41
        ASSIGN_CHANNEL                     = 0x42
        SET_CHANNEL_ID                     = 0x51
        SET_CHANNEL_PERIOD                 = 0x43
        SET_CHANNEL_SEARCH_TIMEOUT         = 0x44
        SET_CHANNEL_RF_FREQ                = 0x45
        SET_NETWORK_KEY                    = 0x46
        SET_TRANSMIT_POWER                 = 0x47
        SET_SEARCH_WAVEFORM                = 0x49 # XXX: Not in official docs
        ADD_CHANNEL_ID                     = 0x59
        CONFIG_LIST                        = 0x5A
        SET_CHANNEL_TX_POWER               = 0x60
        LOW_PRIORITY_CHANNEL_SEARCH_TIMOUT = 0x63
        SERIAL_NUMBER_SET_CHANNEL          = 0x65
        ENABLE_EXT_RX_MESGS                = 0x66
        ENABLE_LED                         = 0x68
        ENABLE_CRYSTAL                     = 0x6D
        LIB_CONFIG                         = 0x6E
        FREQUENCY_AGILITY                  = 0x70
        PROXIMITY_SEARCH                   = 0x71
        CHANNEL_SEARCH_PRIORITY            = 0x75
        #SET_USB_INFO                       = 0xff

        # Notifications
        STARTUP_MESSAGE                    = 0x6F
        SERIAL_ERROR_MESSAGE               = 0xAE

        # Control messags
        RESET_SYSTEM                       = 0x4A
        OPEN_CHANNEL                       = 0x4B
        CLOSE_CHANNEL                      = 0x4C
        OPEN_RX_SCAN_MODE                  = 0x5B
        REQUEST_MESSAGE                    = 0x4D
        SLEEP_MESSAGE                      = 0xC5

        # Data messages
        BROADCAST_DATA                     = 0x4E
        ACKNOWLEDGE_DATA                   = 0x4F
        BURST_TRANSFER_DATA                = 0x50

        # Responses (from channel)
        RESPONSE_CHANNEL                   = 0x40
        
        # Responses (from REQUEST_MESSAGE, 0x4d)
        RESPONSE_CHANNEL_STATUS            = 0x52
        RESPONSE_CHANNEL_ID                = 0x51
        RESPONSE_VERSION                   = 0x3E
        RESPONSE_CAPABILITIES              = 0x54
        RESPONSE_SERIAL_NUMBER             = 0x61

    class Code:
        RESPONSE_NO_ERROR                  = 0

        EVENT_RX_SEARCH_TIMEOUT            = 1
        EVENT_RX_FAIL                      = 2
        EVENT_TX                           = 3
        EVENT_TRANSFER_RX_FAILED           = 4
        EVENT_TRANSFER_TX_COMPLETED        = 5
        EVENT_TRANSFER_TX_FAILED           = 6
        EVENT_CHANNEL_CLOSED               = 7
        EVENT_RX_FAIL_GO_TO_SEARCH         = 8
        EVENT_CHANNEL_COLLISION            = 9
        EVENT_TRANSFER_TX_START            = 10

        CHANNEL_IN_WRONG_STATE             = 21
        CHANNEL_NOT_OPENED                 = 22
        CHANNEL_ID_NOT_SET                 = 24
        CLOSE_ALL_CHANNELS                 = 25

        TRANSFER_IN_PROGRESS               = 31
        TRANSFER_SEQUENCE_NUMBER_ERROR     = 32
        TRANSFER_IN_ERROR                  = 33

        MESSAGE_SIZE_EXCEEDS_LIMIT         = 39
        INVALID_MESSAGE                    = 40
        INVALID_NETWORK_NUMBER             = 41
        INVALID_LIST_ID                    = 48
        INVALID_SCAN_TX_CHANNEL            = 49
        INVALID_PARAMETER_PROVIDED         = 51
        EVENT_SERIAL_QUE_OVERFLOW          = 52
        EVENT_QUE_OVERFLOW                 = 53
        NVM_FULL_ERROR                     = 64
        NVM_WRITE_ERROR                    = 65
        USB_STRING_WRITE_FAIL              = 112
        MESG_SERIAL_ERROR_ID               = 174

        EVENT_RX_BROADCAST                 = 1000
        EVENT_RX_FLAG_BROADCAST            = 1001
        EVENT_RX_ACKNOWLEDGED              = 2000
        EVENT_RX_FLAG_ACKNOWLEDGED         = 2001
        EVENT_RX_BURST_PACKET              = 3000
        EVENT_RX_FLAG_BURST_PACKET         = 3001

        @staticmethod
        def lookup(event):
            for key, value in Message.Code.__dict__.items():
                if type(value) == int and value == event:
                    return key

    def __init__(self, mId, data):
        self._sync     = 0xa4
        self._length   = len(data)
        self._id       = mId
        self._data     = data
        self._checksum = (self._sync ^ self._length ^ self._id
                          ^ reduce(lambda x, y: x ^ y, data))

    def __repr__(self):
        return str.format(
                   "<ant.base.Message {0:02x}:{1} (s:{2:02x}, l:{3}, c:{4:02x})>",
                   self._id, format_list(self._data), self._sync,
                   self._length, self._checksum)

    def get(self):
        result = array.array('B', [self._sync, self._length, self._id])
        result.extend(self._data)
        result.append(self._checksum)
        return result

    '''
    Parse a message from an array
    '''
    @staticmethod
    def parse(buf):
        sync     = buf[0]
        length   = buf[1]
        mId      = buf[2]
        data     = buf[3:-1]
        checksum = buf[-1]

        assert sync     == 0xa4
        assert length   == len(data)
        assert checksum == reduce(lambda x, y: x ^ y, buf[:-1])

        return Message(mId, data)

########NEW FILE########
__FILENAME__ = channel
# Ant
#
# Copyright (c) 2012, Gustav Tiger <gustav@tiger.name>
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import collections
import threading
import logging

from ant.base.message import Message
from ant.easy.exception import TransferFailedException
from ant.easy.filter import wait_for_event, wait_for_response, wait_for_special

_logger = logging.getLogger("garmin.ant.easy.channel")

class Channel():
    
    class Type:
        BIDIRECTIONAL_RECEIVE         = 0x00
        BIDIRECTIONAL_TRANSMIT        = 0x10
        
        SHARED_BIDIRECTIONAL_RECEIVE  = 0x20
        SHARED_BIDIRECTIONAL_TRANSMIT = 0x30
        
        UNIDIRECTIONAL_RECEIVE_ONLY   = 0x40
        UNIDIRECTIONAL_TRANSMIT_ONLY  = 0x50
    
    def __init__(self, id, node, ant):
        self.id  = id
        self._node = node
        self._ant = ant

    def wait_for_event(self, ok_codes):
        return wait_for_event(ok_codes, self._node._events, self._node._event_cond)

    def wait_for_response(self, event_id):
        return wait_for_response(event_id, self._node._responses, self._node._responses_cond)

    def wait_for_special(self, event_id):
        return wait_for_special(event_id, self._node._responses, self._node._responses_cond)

    def _assign(self, channelType, networkNumber):
        self._ant.assign_channel(self.id, channelType, networkNumber)
        return self.wait_for_response(Message.ID.ASSIGN_CHANNEL)

    def _unassign(self):
        pass

    def open(self):
        self._ant.open_channel(self.id)
        return self.wait_for_response(Message.ID.OPEN_CHANNEL)

    def set_id(self, deviceNum, deviceType, transmissionType):
        self._ant.set_channel_id(self.id, deviceNum, deviceType, transmissionType)
        return self.wait_for_response(Message.ID.SET_CHANNEL_ID)
    
    def set_period(self, messagePeriod):
        self._ant.set_channel_period(self.id, messagePeriod)
        return self.wait_for_response(Message.ID.SET_CHANNEL_PERIOD)
    
    def set_search_timeout(self, timeout):
        self._ant.set_channel_search_timeout(self.id, timeout)
        return self.wait_for_response(Message.ID.SET_CHANNEL_SEARCH_TIMEOUT)
    
    def set_rf_freq(self, rfFreq):
        self._ant.set_channel_rf_freq(self.id, rfFreq)
        return self.wait_for_response(Message.ID.SET_CHANNEL_RF_FREQ)

    def set_search_waveform(self, waveform):
        self._ant.set_search_waveform(self.id, waveform)
        return self.wait_for_response(Message.ID.SET_SEARCH_WAVEFORM)

    def request_message(self, messageId):
        _logger.debug("requesting message %#02x", messageId)
        self._ant.request_message(self.id, messageId)
        _logger.debug("done requesting message %#02x", messageId)
        return self.wait_for_special(messageId)

    def send_acknowledged_data(self, data):
        try:
            _logger.debug("send acknowledged data %s", self.id)
            self._ant.send_acknowledged_data(self.id, data)
            self.wait_for_event([Message.Code.EVENT_TRANSFER_TX_COMPLETED])
            _logger.debug("done sending acknowledged data %s", self.id)
        except TransferFailedException:
            _logger.warning("failed to send acknowledged data %s, retrying", self.id)
            self.send_acknowledged_data(data)

    def send_burst_transfer_packet(self, channelSeq, data, first):
        _logger.debug("send burst transfer packet %s", data)
        self._ant.send_burst_transfer_packet(channelSeq, data, first)

    def send_burst_transfer(self, data):
        try:
            #self._last_call = (self.send_burst_transfer, [self.id, data])
            _logger.debug("send burst transfer %s", self.id)
            self._ant.send_burst_transfer(self.id, data)
            self.wait_for_event([Message.Code.EVENT_TRANSFER_TX_START])
            self.wait_for_event([Message.Code.EVENT_TRANSFER_TX_COMPLETED])
            _logger.debug("done sending burst transfer %s", self.id)
        except TransferFailedException:
            _logger.warning("failed to send burst transfer %s, retrying", self.id)
            self.send_burst_transfer(data)


########NEW FILE########
__FILENAME__ = exception
# Ant
#
# Copyright (c) 2012, Gustav Tiger <gustav@tiger.name>
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import logging

_logger = logging.getLogger("garmin.ant.easy.exception")

class AntException(Exception):
    pass

class TransferFailedException(AntException):
    pass

class ReceiveFailedException(AntException):
    pass

class ReceiveFailException(AntException):
    pass

########NEW FILE########
__FILENAME__ = filter
# Ant
#
# Copyright (c) 2012, Gustav Tiger <gustav@tiger.name>
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import logging

from ant.base.message import Message
from ant.easy.exception import AntException, TransferFailedException

_logger = logging.getLogger("garmin.ant.easy.filter")

def wait_for_message(match, process, queue, condition):
    """
    Wait for a specific message in the *queue* guarded by the *condition*
    matching the function *match* (which is a function that takes a
    message as a parameter and returns a boolean). The messages is
    processed by the *process* function before returning it.
    """
    _logger.debug("wait for message matching %r", match)
    condition.acquire()
    for _ in range(10):
        _logger.debug("looking for matching message in %r", queue)
        #_logger.debug("wait for response to %#02x, checking", mId)
        for message in queue:
            if match(message):
                _logger.debug(" - response found %r", message)
                queue.remove(message)
                condition.release()
                return process(message)
            elif (message[1] == 1 and 
                 message[2][0] == Message.Code.EVENT_TRANSFER_TX_FAILED):
                _logger.warning("Transfer send failed:")
                _logger.warning(message)
                queue.remove(message)
                condition.release()
                raise TransferFailedException()
        _logger.debug(" - could not find response matching %r", match)
        condition.wait(1.0)
    condition.release()
    raise AntException("Timed out while waiting for message")
    
def wait_for_event(ok_codes, queue, condition):
    def match((channel, event, data)):
        return data[0] in ok_codes
    def process((channel, event, data)):
        return (channel, event, data)
    return wait_for_message(match, process, queue, condition)

def wait_for_response(event_id, queue, condition):
    """
    Waits for a response to a specific message sent by the channel response
    message, 0x40. It's expected to return RESPONSE_NO_ERROR, 0x00.
    """
    def match((channel, event, data)):
        return event == event_id
    def process((channel, event, data)):
        if data[0] == Message.Code.RESPONSE_NO_ERROR:
            return (channel, event, data)
        else:
            raise Exception("Responded with error " + str(data[0])
                    + ":" + Message.Code.lookup(data[0]))
    return wait_for_message(match, process, queue, condition)

def wait_for_special(event_id, queue, condition):
    """
    Waits for special responses to messages such as Channel ID, ANT
    Version, etc. This does not throw any exceptions, besides timeouts.
    """
    def match((channel, event, data)):
        return event == event_id
    def process(event):
        return event
    return wait_for_message(match, process, queue, condition)

########NEW FILE########
__FILENAME__ = node
# Ant
#
# Copyright (c) 2012, Gustav Tiger <gustav@tiger.name>
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import collections
import threading
import logging
import Queue

from ant.base.ant import Ant
from ant.base.message import Message
from ant.easy.channel import Channel
from ant.easy.filter import wait_for_event, wait_for_response, wait_for_special

_logger = logging.getLogger("garmin.ant.easy.node")

class Node():
    
    def __init__(self):
        
        self._responses_cond = threading.Condition()
        self._responses      = collections.deque()
        self._event_cond     = threading.Condition()
        self._events         = collections.deque()
        
        self._datas = Queue.Queue()
        
        self.channels = {}
        
        self.ant = Ant()
        
        self._running = True
        
        self._worker_thread = threading.Thread(target=self._worker, name="ant.easy")
        self._worker_thread.start()

    def new_channel(self, ctype):
        channel = Channel(0, self, self.ant)
        self.channels[0] = channel
        channel._assign(ctype, 0x00)
        return channel

    def request_message(self, messageId):
        _logger.debug("requesting message %#02x", messageId)
        self.ant.request_message(0, messageId)
        _logger.debug("done requesting message %#02x", messageId)
        return self.wait_for_special(messageId)

    def set_network_key(self, network, key):
        self.ant.set_network_key(network, key)
        return self.wait_for_response(Message.ID.SET_NETWORK_KEY)

    def wait_for_event(self, ok_codes):
        return wait_for_event(ok_codes, self._events, self._event_cond)

    def wait_for_response(self, event_id):
        return wait_for_response(event_id, self._responses, self._responses_cond)

    def wait_for_special(self, event_id):
        return wait_for_special(event_id, self._responses, self._responses_cond)

    def _worker_response(self, channel, event, data):
        self._responses_cond.acquire()
        self._responses.append((channel, event, data))
        self._responses_cond.notify()
        self._responses_cond.release()

    def _worker_event(self, channel, event, data):
        if event == Message.Code.EVENT_RX_BURST_PACKET:
            self._datas.put(('burst', channel, data))
        elif event == Message.Code.EVENT_RX_BROADCAST:
            self._datas.put(('broadcast', channel, data))
        else:
            self._event_cond.acquire()
            self._events.append((channel, event, data))
            self._event_cond.notify()
            self._event_cond.release()

    def _worker(self):
        self.ant.response_function = self._worker_response
        self.ant.channel_event_function = self._worker_event
        
        # TODO: check capabilities
        self.ant.start()
        
    def _main(self):
        while self._running:
            try:
                (data_type, channel, data) = self._datas.get(True, 1.0)
                self._datas.task_done()
                
                if data_type == 'broadcast':
                    self.channels[channel].on_broadcast_data(data)
                elif data_type == 'burst':
                    self.channels[channel].on_burst_data(data)
                else:
                    _logger.warning("Unknown data type '%s': %r", data_type, data)
            except Queue.Empty as e:
                pass

    def start(self):
        self._main()

    def stop(self):
        if self._running:
            _logger.debug("Stoping ant.easy")
            self._running = False
            self.ant.stop()
            self._worker_thread.join()



########NEW FILE########
__FILENAME__ = test
#from ant.base import Message
from .. node import Node, Message
from .. channel import Channel

import logging
import struct
import sys

try:
    logger = logging.getLogger("garmin")
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(fmt='%(asctime)s  %(name)-15s  %(levelname)-8s  %(message)s'))
    logger.addHandler(handler)

    n = Node(0x0fcf, 0x1008)
    print "Request basic information..."
    m = n.request_message(Message.ID.RESPONSE_VERSION)
    print "  ANT version:  ", struct.unpack("<10sx", m[2])[0]
    m = n.request_message(Message.ID.RESPONSE_CAPABILITIES)
    print "  Capabilities: ", m[2]
    m = n.request_message(Message.ID.RESPONSE_SERIAL_NUMBER)
    print "  Serial number:", struct.unpack("<I", m[2])[0]

    print "Starting system..."

    NETWORK_KEY= [0xa8, 0xa4, 0x23, 0xb9, 0xf5, 0x5e, 0x63, 0xc1]

    n.reset_system()
    n.set_network_key(0x00, NETWORK_KEY)

    c = n.new_channel(Channel.Type.BIDIRECTIONAL_RECEIVE)

    c.set_period(4096)
    c.set_search_timeout(255)
    c.set_rf_freq(50)
    c.set_search_waveform([0x53, 0x00])
    c.set_id(0, 0x01, 0)
    
    print "Open channel..."
    c.open()
    c.request_message(Message.ID.RESPONSE_CHANNEL_STATUS)

    print "Searching..."

    n.start()

    print "Done"
except KeyboardInterrupt:
    print "Interrupted"
    n.stop()
    sys.exit(1)

########NEW FILE########
__FILENAME__ = beacon
# Ant
#
# Copyright (c) 2012, Gustav Tiger <gustav@tiger.name>
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import struct

class Beacon:
    
    class ClientDeviceState:
        LINK           = 0x00 # 0b0000
        AUTHENTICATION = 0x01 # 0b0001
        TRANSPORT      = 0x02 # 0b0010
        BUSY           = 0x03 # 0b0011

    BEACON_ID = 0x43

    def is_data_available(self):
        return bool(self._status_byte_1 & 0x20) # 0b00100000

    def is_upload_enabled(self):
        return bool(self._status_byte_1 & 0x10) # 0b00010000

    def is_pairing_enabled(self):
        return bool(self._status_byte_1 & 0x08) # 0b00001000

    def get_channel_period(self):
        return self._status_byte_1 & 0x07 # 0b00000111, TODO

    def get_client_device_state(self):
        return self._status_byte_2 & 0x0f # 0b00001111, TODO

    def get_serial(self):
        return struct.unpack("<I", self._descriptor)[0]

    def get_descriptor(self):
        return struct.unpack("<HH", self._descriptor)

    @staticmethod
    def parse(data):
        values = struct.unpack("<BBBB4x", data)
        
        assert values[0] == 0x43
        
        beacon = Beacon()
        beacon._status_byte_1 = values[1]
        beacon._status_byte_2 = values[2]
        beacon._authentication_type = values[3]
        beacon._descriptor = data[4:]
        return beacon


########NEW FILE########
__FILENAME__ = command
# Ant-FS
#
# Copyright (c) 2012, Gustav Tiger <gustav@tiger.name>
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import array
import collections
import copy
import logging
import struct

_logger = logging.getLogger("garmin.ant.fs.command")

class Command:
    
    class Type:
        
        # Commands
        LINK                  = 0x02
        DISCONNECT            = 0x03
        AUTHENTICATE          = 0x04
        PING                  = 0x05
        
        DOWNLOAD_REQUEST      = 0x09
        UPLOAD_REQUEST        = 0x0A
        ERASE_REQUEST         = 0x0B
        UPLOAD_DATA           = 0x0C
        
        # Responses
        AUTHENTICATE_RESPONSE = 0x84
        DOWNLOAD_RESPONSE     = 0x89
        UPLOAD_RESPONSE       = 0x8A
        ERASE_RESPONSE        = 0x8B
        UPLOAD_DATA_RESPONSE  = 0x8C
    
    _format = "<BB"
    _id     = None
    
    def __init__(self):
        self._arguments = collections.OrderedDict()
        self._add_argument('x',  0x44)
        self._add_argument('id', self._id)
    
    def _add_argument(self, name, value):
        self._arguments[name] = value
    
    def _get_argument(self, name):
        return self._arguments[name]
    
    def _get_arguments(self):
        return self._arguments.values()
    
    def get_id(self):
        return self._id

    def get(self):
        data = struct.pack(self._format, *self._get_arguments())
        lst  = array.array('B', data)
        _logger.debug("packing %r in %r,%s", data, lst, type(lst))
        return lst

    @classmethod
    def _parse_args(cls, data):
        return struct.unpack(cls._format, data)

    @classmethod
    def _parse(cls, data):
        args = cls._parse_args(data)
        assert args[0] == 0x44
        assert args[1] == cls._id
        return cls(*args[2:])

    def _debug(self):
        max_key_length, max_value_length = 0, 0
        for key, value in self._arguments.items():
            max_key_length = max(len(str(key)), max_key_length)
            max_value_length = max(len(str(value)), max_value_length)
        max_length = max_key_length + max_value_length + 3
        print "=" * max_length
        print self.__class__.__name__
        print "-" * max_length
        for key, value in self._arguments.items():
            print str(key) + ":", " " * (max_length - len(key)), str(value)
        print "=" * max_length

class LinkCommand(Command):
    
    _id     = Command.Type.LINK
    _format = Command._format + "BBI"
    
    def __init__(self, channel_frequency, channel_period, host_serial_number):
        Command.__init__(self)
        self._add_argument("channel_frequency", channel_frequency)
        self._add_argument("channel_period", channel_period)
        self._add_argument("host_serial_number", host_serial_number)

class DisconnectCommand(Command):
    
    class Type:
        RETURN_LINK             = 0
        RETURN_BROADCAST        = 1

    _id     = Command.Type.DISCONNECT
    _format = Command._format + "BBBxxx"

    def __init__(self, command_type, time_duration, application_specific_duration):
        Command.__init__(self)
        self._add_argument("command_type", command_type)
        self._add_argument("time_duration", time_duration)
        self._add_argument("application_specific_duration", application_specific_duration)

class AuthenticateBase(Command):
    
    _format = None

    def __init__(self, x_type, serial_number, data = []):
        Command.__init__(self)
        self._add_argument("type", x_type)
        self._add_argument("serial_number", serial_number)
        self._add_argument("data", data)

    def _pad(self, data):
        padded_data = copy.copy(data)
        missing = 8 - len(padded_data) % 8
        if missing < 8:
            padded_data.extend([0x00] * missing)
        return padded_data

    def get_serial(self):
        return self._get_argument("serial_number")

    def get_data_string(self):
        if self._get_argument("data") == []:
            return None
        else:
            return "".join(map(chr, self._get_argument("data")))

    def get_data_array(self):
        return self._get_argument("data")

    def get(self):
        lst = array.array('B', struct.pack("<BBBBI", self._get_arguments()[0],
                self._get_arguments()[1], self._get_arguments()[2],
                len(self._get_argument("data")), self._get_arguments()[3]))
        padded = self._pad(self._get_argument("data"))
        lst.extend(array.array('B', padded))
        return lst

    @classmethod
    def _parse_args(cls, data):
        header = struct.unpack("<BBBxI", data[0:8])
        data_length = data[3]
        return header + (data[8:8 + data_length],)

class AuthenticateCommand(AuthenticateBase):
    
    class Request:
        PASS_THROUGH     = 0
        SERIAL           = 1
        PAIRING          = 2
        PASSKEY_EXCHANGE = 3
    
    _id     = Command.Type.AUTHENTICATE

    def __init__(self, command_type, host_serial_number, data = []):
        AuthenticateBase.__init__(self, command_type, host_serial_number, data)

class AuthenticateResponse(AuthenticateBase):
    
    class Response:
        NOT_AVAILABLE = 0
        ACCEPT        = 1
        REJECT        = 2
    
    _id     = Command.Type.AUTHENTICATE_RESPONSE

    def __init__(self, response_type, client_serial_number, data = []):
        AuthenticateBase.__init__(self, response_type, client_serial_number, data)

class PingCommand(Command):
    
    _id     = Command.Type.PING


class DownloadRequest(Command):
    
    _id     = Command.Type.DOWNLOAD_REQUEST
    _format = Command._format + "HIx?HI"
    
    def __init__(self, data_index, data_offset, initial_request, crc_seed,
                 maximum_block_size = 0):
        Command.__init__(self)
        self._add_argument("data_index", data_index)
        self._add_argument("data_offset", data_offset)
        self._add_argument("initial_request", initial_request)
        self._add_argument("crc_seed", crc_seed)
        self._add_argument("maximum_block_size", maximum_block_size)

class DownloadResponse(Command):
    
    class Response:
        OK              = 0
        NOT_EXIST       = 1
        NOT_READABLE    = 2
        NOT_READY       = 3
        INVALID_REQUEST = 4
        INCORRECT_CRC   = 5
    
    _id     = Command.Type.DOWNLOAD_RESPONSE
    _format = None
    
    def __init__(self, response, remaining, offset, size, data, crc):
        Command.__init__(self)
        self._add_argument("response", response)
        self._add_argument("remaining", remaining)
        self._add_argument("offset", offset)
        self._add_argument("size", size)
        self._add_argument("data", data)
        self._add_argument("crc", crc)
    
    @classmethod
    def _parse_args(cls, data):
        return struct.unpack("<BBBxIII", data[0:16]) + \
            (data[16:-8],) + struct.unpack("<6xH", data[-8:])

class UploadRequest(Command):
    
    _id     = Command.Type.UPLOAD_REQUEST
    _format = Command._format + "HI4xI"
    
    def __init__(self, data_index, max_size, data_offset):
        Command.__init__(self)
        self._add_argument("data_index", data_index)
        self._add_argument("max_size", max_size)
        self._add_argument("data_offset", data_offset)


class UploadResponse(Command):
    
    class Response:
        OK               = 0
        NOT_EXIST        = 1
        NOT_WRITEABLE    = 2
        NOT_ENOUGH_SPACE = 3
        INVALID_REQUEST  = 4
        NOT_READY        = 5
    
    _id     = Command.Type.UPLOAD_RESPONSE
    _format = Command._format + "BxIII6xH"
    
    def __init__(self, response, last_data_offset, maximum_file_size,
                 maximum_block_size, crc):
        Command.__init__(self)
        self._add_argument("response", response)
        self._add_argument("last_data_offset", last_data_offset)
        self._add_argument("maximum_file_size", maximum_file_size)
        self._add_argument("maximum_block_size", maximum_block_size)
        self._add_argument("crc", crc)


class UploadDataCommand(Command):
    
    _id     = Command.Type.UPLOAD_DATA
    _format = None

    def __init__(self, crc_seed, data_offset, data, crc):
        Command.__init__(self)
        self._add_argument("crc_seed", crc_seed)
        self._add_argument("data_offset", data_offset)
        self._add_argument("data", data)
        self._add_argument("crc", crc)

    def get(self):
        header = struct.pack("<BBHI", *self._get_arguments()[:4])
        footer = struct.pack("<6xH", self._get_argument("crc"))
        data = array.array('B', header)
        data.extend(self._get_argument("data"))
        data.extend(array.array('B', footer))
        return data

    @classmethod
    def _parse_args(cls, data):
        return struct.unpack("<BBHI", data[0:8]) + \
            (data[8:-8],) + struct.unpack("<6xH", data[-8:])

class UploadDataResponse(Command):
    
    class Response:
        OK     = 0
        FAILED = 1
    
    _id     = Command.Type.UPLOAD_DATA_RESPONSE
    _format = Command._format + "B5x"
    
    def __init__(self, response):
        Command.__init__(self)
        self._add_argument("response", response)


class EraseRequestCommand(Command):
    
    _id     = Command.Type.ERASE_REQUEST
    _format = Command._format + "I"
    
    def __init__(self, data_file_index):
        Command.__init__(self)
        self._add_argument("data_file_index", data_file_index)

class EraseResponse(Command):
    
    class Response:
        ERASE_SUCCESSFUL = 0
        ERASE_FAILED     = 1
        NOT_READY        = 2
    
    _id     = Command.Type.ERASE_RESPONSE
    _format = Command._format + "B"
    
    def __init__(self, response):
        Command.__init__(self)
        self._add_argument("response", response)


_classes = {
    # Commands
    Command.Type.LINK:                  LinkCommand,
    Command.Type.DISCONNECT:            DisconnectCommand,
    Command.Type.AUTHENTICATE:          AuthenticateCommand,
    Command.Type.PING:                  PingCommand,
    
    Command.Type.DOWNLOAD_REQUEST:      DownloadRequest,
    Command.Type.UPLOAD_REQUEST:        UploadRequest,
    Command.Type.ERASE_REQUEST:         EraseRequestCommand,
    Command.Type.UPLOAD_DATA:           UploadDataCommand,
    
    # Responses
    Command.Type.AUTHENTICATE_RESPONSE: AuthenticateResponse,
    Command.Type.DOWNLOAD_RESPONSE:     DownloadResponse,
    Command.Type.UPLOAD_RESPONSE:       UploadResponse,
    Command.Type.ERASE_RESPONSE:        EraseResponse,
    Command.Type.UPLOAD_DATA_RESPONSE:  UploadDataResponse}

def parse(data):
    _logger.debug("parsing data %r", data)
    mark, command_type  = struct.unpack("<BB", data[0:2])
    assert mark == 0x44
    command_class = _classes[command_type]
    
    return command_class._parse(data)


########NEW FILE########
__FILENAME__ = commandpipe
# Ant-FS
#
# Copyright (c) 2012, Gustav Tiger <gustav@tiger.name>
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import array
import collections
import logging
import struct

_logger = logging.getLogger("garmin.ant.fs.commandpipe")

class CommandPipe:
    
    class Type:
        
        REQUEST                    = 0x01
        RESPONSE                   = 0x02
        TIME                       = 0x03
        CREATE_FILE                = 0x04
        DIRECTORY_FILTER           = 0x05
        SET_AUTHENTICATION_PASSKEY = 0x06
        SET_CLIENT_FRIENDLY_NAME   = 0x07
        FACTORY_RESET_COMMAND      = 0x08

    _format = "<BxxB"
    _id     = None

    def __init__(self):
        self._arguments = collections.OrderedDict()
        self._add_argument('command',  self._id)
        self._add_argument('sequence', 0)

    def _add_argument(self, name, value):
        self._arguments[name] = value
    
    def _get_argument(self, name):
        return self._arguments[name]
    
    def _get_arguments(self):
        return self._arguments.values()

    def get(self):
        data = struct.pack(self._format, *self._get_arguments())
        lst  = array.array('B', data)
        _logger.debug("packing %r in %r,%s", data, lst, type(lst))
        return lst

    @classmethod
    def _parse_args(cls, data):
        return struct.unpack(cls._format, data)

    @classmethod
    def _parse(cls, data):
        args = cls._parse_args(data)
        assert args[0] == cls._id
        return cls(*args[2:])

    def _debug(self):
        max_key_length, max_value_length = 0, 0
        for key, value in self._arguments.items():
            max_key_length = max(len(str(key)), max_key_length)
            max_value_length = max(len(str(value)), max_value_length)
        max_length = max_key_length + max_value_length + 3
        print "=" * max_length
        print self.__class__.__name__
        print "-" * max_length
        for key, value in self._arguments.items():
            print str(key) + ":", " " * (max_length - len(key)), str(value)
        print "=" * max_length

class Request(CommandPipe):
    
    _id     = CommandPipe.Type.REQUEST
    _format = CommandPipe._format + "Bxxx"

    def __init__(self, request_id):
        CommandPipe.__init__(self)

class Response(CommandPipe):
    
    class Response:
        OK            = 0
        FAILED        = 1
        REJECTED      = 2
        NOT_SUPPORTED = 3
    
    _id     = CommandPipe.Type.RESPONSE
    _format = CommandPipe._format + "BxBx"

    def get_request_id(self):
        return self._get_argument("request_id")

    def get_response(self):
        return self._get_argument("response")

    def __init__(self, request_id, response):
        CommandPipe.__init__(self)
        self._add_argument('request_id', request_id)
        self._add_argument('response', response)

class Time(CommandPipe):
    
    class Format:
        DIRECTORY = 0
        SYSTEM    = 1
        COUNTER   = 2
    
    _id     = CommandPipe.Type.TIME
    _format = CommandPipe._format + "IIBxxx"
    
    def __init__(self, current_time, system_time, time_format):
        CommandPipe.__init__(self)


class CreateFile(CommandPipe):
    
    _id     = CommandPipe.Type.CREATE_FILE
    _format = None

    def __init__(self, size, data_type, identifier, identifier_mask):
        CommandPipe.__init__(self)
        self._add_argument('size', size)
        self._add_argument('data_type', data_type)
        self._add_argument('identifier', identifier)
        self._add_argument('identifier_mask', identifier_mask)

    def get(self):
        data = array.array('B', struct.pack(CommandPipe._format + "IB",
                           *self._get_arguments()[:4]))
        data.extend(self._get_argument("identifier"))
        data.extend([0])
        data.extend(self._get_argument("identifier_mask"))
        return data

    @classmethod
    def _parse_args(cls, data):
        return struct.unpack(Command._format + "IB", data[0:9])\
                + (data[9:12],) + (data[13:16],)


class CreateFileResponse(Response):

    _format = Response._format + "BBBBHxx"

    def __init__(self, request_id, response, data_type, identifier, index):
        Response.__init__(self, request_id, response)
        self._add_argument('data_type', data_type)
        self._add_argument('identifier', identifier)
        self._add_argument('index', index)

    def get_data_type(self):
        return self._get_argument("data_type")

    def get_identifier(self):
        return self._get_argument("identifier")
    
    def get_index(self):
        return self._get_argument("index")

    @classmethod
    def _parse_args(cls, data):
        return Response._parse_args(data[:8]) + \
                (data[8], data[9:12], struct.unpack("<H", data[12:14])[0])

_classes = {
    CommandPipe.Type.REQUEST:                     Request,
    CommandPipe.Type.RESPONSE:                   Response,
    CommandPipe.Type.TIME:                       Time,
    CommandPipe.Type.CREATE_FILE:                CreateFile,
    CommandPipe.Type.DIRECTORY_FILTER:           None,
    CommandPipe.Type.SET_AUTHENTICATION_PASSKEY: None,
    CommandPipe.Type.SET_CLIENT_FRIENDLY_NAME:   None,
    CommandPipe.Type.FACTORY_RESET_COMMAND:      None}

_responses = {
    CommandPipe.Type.CREATE_FILE:                CreateFileResponse}

def parse(data):
    commandpipe_type = _classes[data[0]]
    if commandpipe_type == Response:
        if data[4] in _responses:
            commandpipe_type = _responses[data[4]]
    return commandpipe_type._parse(data)


########NEW FILE########
__FILENAME__ = commons
# Ant-FS
#
# Copyright (c) 2012, Gustav Tiger <gustav@tiger.name>
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

# http://reveng.sourceforge.net/crc-catalogue/16.htm#crc.cat.arc
def crc(data, seed=0x0000):
    rem = seed
    for byte in data:
        rem ^= byte 
        for _ in range(0, 8):
            if rem & 0x0001:
                rem = (rem >> 1)
                rem ^= 0xa001
            else:
                rem = rem >> 1

    return rem


########NEW FILE########
__FILENAME__ = file
# Ant-FS
#
# Copyright (c) 2012, Gustav Tiger <gustav@tiger.name>
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import datetime
import logging
import struct

_logger = logging.getLogger("garmin.ant.fs.file")

class Directory:
    def __init__(self, version, time_format, current_system_time,
            last_modified, files):
        self._version = version
        self._time_format = time_format
        self._current_system_time = current_system_time
        self._last_modified = last_modified
        self._files = files

    def get_version(self):
        return self._version

    def get_files(self):
        return self._files

    def print_list(self):
        print "Index\tType\tFIT Type\tFIT Number\tSize\tDate\tFIT Flags\tFlags"
        for f in self.get_files():
            print f.get_index(), "\t", f.get_type(), "\t",\
                  f.get_fit_sub_type(), "\t", f.get_fit_file_number(), "\t",\
                  f.get_size(), "\t", f.get_date(), "\t", f._typ_flags, "\t",\
                  f.get_flags_string()

    @staticmethod
    def parse(data):
        _logger.debug("Parse '%s' as directory", data)

        # Header
        version, structure_length, time_format, current_system_time, \
            last_modified = struct.unpack("<BBB5xII", data[:16])

        version_major = (version & 0xf0) >> 4
        version_minor = (version & 0x0f)
    
        files = []
        for offset in range(16 , len(data), 16):
            item_data = data[offset:offset + 16]
            _logger.debug(" - (%d - %d) %d, %s", offset, offset + 16, len(item_data), item_data)
            files.append(File.parse(item_data))
        return Directory((version_major, version_minor), time_format,
                current_system_time, last_modified, files)


class File:

    class Type:
        FIT     = 0x80

    class Identifier:
        DEVICE           = 1
        SETTING          = 2
        SPORT_SETTING    = 3
        ACTIVITY         = 4
        WORKOUT          = 5
        COURSE           = 6
        WEIGHT           = 9
        TOTALS           = 10
        GOALS            = 11
        BLOOD_PRESSURE   = 14
        ACTIVITY_SUMMARY = 20

    def  __init__(self, index, typ, ident, typ_flags, flags, size, date):
        self._index = index
        self._type = typ
        self._ident = ident
        self._typ_flags = typ_flags
        self._flags = flags
        self._size = size
        self._date = date

    def get_index(self):
        return self._index

    def get_type(self):
        return self._type

    def get_identifier(self):
        return self._ident

    def get_fit_sub_type(self):
        return self._ident[0]

    def get_fit_file_number(self):
        return struct.unpack("<xH", self._ident)[0]

    def get_size(self):
        return self._size

    def get_date(self):
        return self._date

    def get_flags_string(self):
        s  = "r" if self._flags & 0b00001000 == 0 else "-"
        s += "w" if self._flags & 0b00010000 == 0 else "-"
        s += "e" if self._flags & 0b00100000 == 0 else "-"
        s += "a" if self._flags & 0b01000000 == 0 else "-"
        s += "A" if self._flags & 0b10000000 == 0 else "-"
        return s

    @staticmethod
    def parse(data):
        _logger.debug("Parse '%s' (%d) as file %s", data, len(data), type(data))

        # i1, i2, i3 -> three byte integer, not supported by struct
        (index, data_type, data_flags, flags, file_size, file_date) \
                 = struct.unpack("<HB3xBBII", data)
        file_date  = datetime.datetime.fromtimestamp(file_date + 631065600)
        identifier = data[3:6]

        return File(index, data_type, identifier, data_flags, flags, file_size, file_date)



########NEW FILE########
__FILENAME__ = manager
# Ant-FS
#
# Copyright (c) 2012, Gustav Tiger <gustav@tiger.name>
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import array
import logging
import struct
import threading
import traceback
import Queue

from ant.easy.channel import Channel
from ant.easy.node import Node, Message

import ant.fs.command
from ant.fs.beacon import Beacon
from ant.fs.command import LinkCommand, DownloadRequest, DownloadResponse, \
        AuthenticateCommand, AuthenticateResponse, DisconnectCommand, \
        UploadRequest, UploadResponse, UploadDataCommand, UploadDataResponse
from ant.fs.commandpipe import CreateFile, CreateFileResponse, Response
from ant.fs.file import Directory, File
from ant.fs.commons import crc

_logger = logging.getLogger("garmin.ant.fs.manager")

class AntFSException(Exception):

    def __init__(self, error, errno=None):
        Exception.__init__(self, error, errno)
        self._error = error
        self._errno = errno

    def get_error(self):
        if self._errno != None:
            return str(self._errno) + ": " + self._error
        else:
            return self._error

class AntFSDownloadException(AntFSException):
    
    def __init__(self, error, errno=None):
        AntFSException.__init__(self, error, errno)

class AntFSUploadException(AntFSException):
    
    def __init__(self, error, errno=None):
        AntFSException.__init__(self, error, errno)

class AntFSAuthenticationException(AntFSException):
    
    def __init__(self, error, errno=None):
        AntFSException.__init__(self, error, errno)

class Application:
    
    _serial_number = 1337
    _frequency     = 19    # 0 to 124, x - 2400 (in MHz)
    
    def __init__(self):

        self._queue = Queue.Queue()
        self._beacons = Queue.Queue()

        self._node = Node()

        try:
            NETWORK_KEY= [0xa8, 0xa4, 0x23, 0xb9, 0xf5, 0x5e, 0x63, 0xc1]
            self._node.set_network_key(0x00, NETWORK_KEY)


            print "Request basic information..."

            m = self._node.request_message(Message.ID.RESPONSE_CAPABILITIES)
            print "  Capabilities: ", m[2]

            #m = self._node.request_message(Message.ID.RESPONSE_VERSION)
            #print "  ANT version:  ", struct.unpack("<10sx", m[2])[0]

            #m = self._node.request_message(Message.ID.RESPONSE_SERIAL_NUMBER)
            #print "  Serial number:", struct.unpack("<I", m[2])[0]

            print "Starting system..."

            #NETWORK_KEY= [0xa8, 0xa4, 0x23, 0xb9, 0xf5, 0x5e, 0x63, 0xc1]
            #self._node.set_network_key(0x00, NETWORK_KEY)

            print "Key done..."

            self._channel = self._node.new_channel(Channel.Type.BIDIRECTIONAL_RECEIVE)
            self._channel.on_broadcast_data = self._on_data
            self._channel.on_burst_data = self._on_data
            
            self.setup_channel(self._channel)
            
            self._worker_thread =threading.Thread(target=self._worker, name="ant.fs")
            self._worker_thread.start()
        except Exception as e:
            self.stop()
            raise e

    def _worker(self):
        self._node.start()

    def _main(self):
        try:
            _logger.debug("Link level")
            beacon = self._get_beacon()
            if self.on_link(beacon):
                for i in range(0, 5):
                    beacon = self._get_beacon()
                    if beacon.get_client_device_state() == Beacon.ClientDeviceState.AUTHENTICATION:
                        _logger.debug("Auth layer")
                        if self.on_authentication(beacon):
                            _logger.debug("Authenticated")
                            beacon = self._get_beacon()
                            self.on_transport(beacon)
                        self.disconnect()
                        break
        #except Exception as e:
        #    print e
        #    traceback.print_exc()
        #    for line in traceback.format_exc().splitlines():
        #        _logger.error("%r", line)
        finally:
            _logger.debug("Run 5")
            self.stop()


    def _on_beacon(self, data):
        b = Beacon.parse(data)
        self._beacons.put(b)

    def _on_command(self, data):
        c = ant.fs.command.parse(data)
        self._queue.put(c)

    def _on_data(self, data):
        #print "_on_data", data, len(data)
        if data[0] == 0x43:
            self._on_beacon(data[:8])
            if len(data[8:]) > 0:
                self._on_command(data[8:])
        elif data[0] == 0x44:
            self._on_command(data)
    
    def _get_beacon(self):
        b = self._beacons.get()
        self._beacons.task_done()
        return b
    
    def _get_command(self, timeout=3.0):
        _logger.debug("Get command, t%d, s%d", timeout, self._queue.qsize())
        c = self._queue.get(True, timeout)
        self._queue.task_done()
        return c
    
    def _send_command(self, c):
        data = c.get()
        if len(data) == 8:
            self._channel.send_acknowledged_data(data)
        else:
            self._channel.send_burst_transfer(data)
    
    # Application actions are defined from here
    # =======================================================================
    
    # These should be overloaded:
    
    def setup_channel(self, channel):
        pass
    
    def on_link(self, beacon):
        pass
    
    def on_authentication(self, beacon):
        pass
    
    def on_transport(self, beacon):
        pass
    
    # Shouldn't have to touch these:
    
    def start(self):
        self._main()

    def stop(self):
        self._node.stop()
    
    def erase(self, index):
        pass
    
    def _send_commandpipe(self, data):
        #print "send commandpipe", data
        self.upload(0xfffe, data)
    
    def _get_commandpipe(self):
        #print "get commandpipe"
        return ant.fs.commandpipe.parse(self.download(0xfffe))
    
    def create(self, typ, data, callback=None):
        #print "create", typ
        request = CreateFile(len(data), 0x80, [typ, 0x00, 0x00], [0x00, 0xff, 0xff])
        self._send_commandpipe(request.get())
        result = self._get_commandpipe()
        #result._debug()
        
        if result.get_response() != Response.Response.OK:
            raise AntFSCreateFileException("Could not create file",
                    result.get_response())
        
        #print "create result", result, result.get_index(), result.get_data_type(), result.get_identifier()
        #d = self.download_directory()
        
        self.upload(result.get_index(), data, callback)
        return result.get_index()
    
    def upload(self, index, data, callback=None):
        #print "upload", index, len(data)

        iteration = 0
        while True:
            
            # Request Upload
            
            # Continue using Last Data Offset (special MAX_ULONG value)
            request_offset = 0 if iteration == 0 else 0xffffffff
            self._send_command(UploadRequest(index, len(data), request_offset))
            
            upload_response = self._get_command()
            #upload_response._debug()
            
            if upload_response._get_argument("response") != UploadResponse.Response.OK:
                raise AntFSUploadException("Upload request failed",
                        upload_response._get_argument("response"))

            # Upload data
            offset      = upload_response._get_argument("last_data_offset")
            max_block   = upload_response._get_argument("maximum_block_size")
            #print " uploading", offset, "to", offset + max_block
            data_packet = data[offset:offset + max_block]
            crc_seed    = upload_response._get_argument("crc")
            crc_val     = crc(data_packet, upload_response._get_argument("crc"))
            
            # Pad with 0 to even 8 bytes
            missing_bytes = 8 - (len(data_packet) % 8)
            if missing_bytes != 8:
                data_packet.extend(array.array('B', [0] * missing_bytes))
                #print " adding", str(missing_bytes), "padding"

            #print " packet", len(data_packet)
            #print " crc   ", crc_val, "from seed", crc_seed

            self._send_command(UploadDataCommand(crc_seed, offset, data_packet, crc_val))
            upload_data_response = self._get_command()
            #upload_data_response._debug()
            if upload_data_response._get_argument("response") != UploadDataResponse.Response.OK:
                raise AntFSUploadException("Upload data failed",
                        upload_data_response._get_argument("response"))
            
            if callback != None and len(data) != 0:
                callback(float(offset) / float(len(data)))

            if offset + len(data_packet) >= len(data):
                #print " done"
                break

            #print " one more"
            iteration += 1

    
    def download(self, index, callback=None):
        offset  = 0
        initial = True
        crc     = 0
        data    = array.array('B')
        while True:
            _logger.debug("Download %d, o%d, c%d", index, offset, crc)
            self._send_command(DownloadRequest(index, offset, True, crc))
            _logger.debug("Wait for response...")
            try:
                response = self._get_command()
                if response._get_argument("response") == DownloadResponse.Response.OK:
                    remaining    = response._get_argument("remaining")
                    offset       = response._get_argument("offset")
                    total        = offset + remaining
                    data[offset:total] = response._get_argument("data")[:remaining]
                    #print "rem", remaining, "offset", offset, "total", total, "size", response._get_argument("size")
                    # TODO: check CRC
                    
                    if callback != None and response._get_argument("size") != 0:
                        callback(float(total) / float(response._get_argument("size")))
                    if total == response._get_argument("size"):
                        return data
                    crc = response._get_argument("crc")
                    offset = total
                else:
                    raise AntFSDownloadException("Download request failed: ",
                            response._get_argument("response"))
            except Queue.Empty:
                _logger.debug("Download %d timeout", index)
                #print "recover from download failure"
    
    def download_directory(self, callback=None):
        data = self.download(0, callback)
        return Directory.parse(data)

    def link(self):
        self._channel.request_message(Message.ID.RESPONSE_CHANNEL_ID)
        self._send_command(LinkCommand(self._frequency, 4, self._serial_number))
       
        # New period, search timeout
        self._channel.set_period(4096)
        self._channel.set_search_timeout(3)
        self._channel.set_rf_freq(self._frequency)

    def authentication_serial(self):
        self._send_command(AuthenticateCommand(
                AuthenticateCommand.Request.SERIAL,
                self._serial_number))
        response = self._get_command()
        return (response.get_serial(), response.get_data_string())

    def authentication_passkey(self, passkey):
        self._send_command(AuthenticateCommand(
                AuthenticateCommand.Request.PASSKEY_EXCHANGE,
                self._serial_number, passkey))

        response = self._get_command()
        if response._get_argument("type") == AuthenticateResponse.Response.ACCEPT:
            return response.get_data_array()
        else:
            raise AntFSAuthenticationException("Passkey authentication failed",
                    response._get_argument("type"))

    def authentication_pair(self, friendly_name):
        data = array.array('B', map(ord, list(friendly_name)))
        self._send_command(AuthenticateCommand(
                AuthenticateCommand.Request.PAIRING,
                self._serial_number, data))

        response = self._get_command(30)
        if response._get_argument("type") == AuthenticateResponse.Response.ACCEPT:
            return response.get_data_array()
        else:
            raise AntFSAuthenticationException("Pair authentication failed",
                    response._get_argument("type"))
        

    def disconnect(self):
        d = DisconnectCommand(DisconnectCommand.Type.RETURN_LINK, 0, 0)
        self._send_command(d)


########NEW FILE########
__FILENAME__ = beacon_test
# Ant-FS
#
# Copyright (c) 2012, Gustav Tiger <gustav@tiger.name>
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import array

from ant.fs.beacon import Beacon

def parse():
    data = array.array('B', [0x43, 0x04, 0x00, 0x03, 0x41, 0x05, 0x01, 0x00])
    beacon = Beacon.parse(data)
    print beacon

########NEW FILE########
__FILENAME__ = commandpipe_test
# Ant-FS
#
# Copyright (c) 2012, Gustav Tiger <gustav@tiger.name>
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import array

from ant.fs.commandpipe import parse, CreateFile

def main():

    # Test create file
    data    = [0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09]
    request = CreateFile(len(data), 0x80, [0x04, 0x00, 0x00], [0x00, 0xff, 0xff])
    print request
    print request.get()
    
    # Test create file response
    response_data = array.array('B', [2, 0, 0, 0, 4, 0, 0, 0, 128, 4, 123, 0, 103, 0, 0, 0])
    response = parse(response_data)
    assert response.get_request_id() == 0x04
    assert response.get_response()   == 0x00
    assert response.get_data_type()  == 0x80 #FIT
    assert response.get_identifier() == array.array('B', [4, 123, 0])
    assert response.get_index()      == 103


########NEW FILE########
__FILENAME__ = command_test
# Ant-FS
#
# Copyright (c) 2012, Gustav Tiger <gustav@tiger.name>
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import array

from ant.fs.command import parse, DownloadRequest, DownloadResponse,\
        AuthenticateCommand

def authenticate_command():

    command = AuthenticateCommand(
            AuthenticateCommand.Type.REQUEST_SERIAL, 123456789)
    assert command.get() == array.array('B',
            [0x44, 0x04, 0x01, 0x00, 0x15, 0xcd, 0x5b, 0x7])

    command = AuthenticateCommand(
            AuthenticateCommand.Type.REQUEST_PAIRING, 987654321,
            map(ord, 'hello'))
    assert command.get() == array.array('B',
            [0x44, 0x04, 0x02, 0x05, 0xb1, 0x68, 0xde, 0x3a,
             0x68, 0x65, 0x6c, 0x6c, 0x6f, 0x00, 0x00, 0x00])

def download_request():

    # Download request
    request = array.array('B', [0x44, 0x09, 0x5f, 0x00, 0x00, 0xba, 0x00,
        0x00, 0x00, 0x00, 0x9e, 0xc2, 0x00, 0x00, 0x00, 0x00])

    a = parse(request)
    assert isinstance(a, DownloadRequest)

def download_response():

    # Download response
    download_response = array.array('B', [68, 137, 0, 0, 241, 1, 0, 0, 0, 186, 0,
        0, 241, 187, 0, 0, 56, 4, 83, 78, 255, 255, 1, 12, 255, 255, 255,3, 72,
        129, 233, 42, 96, 64, 0, 0, 255, 255, 255, 255, 255, 255, 255, 255, 10,
        42, 0, 0, 73, 0, 0, 0, 255, 255, 255, 255, 255, 255, 255, 255, 2, 120,
        255, 99, 255, 2, 192, 129, 233, 42, 121, 0, 0, 0, 21, 3, 255, 71, 0, 0,
        19, 0, 33, 253, 4, 134, 2, 4, 134, 3, 4, 133, 4, 4, 133, 5, 4, 133, 6, 4,
        133, 7, 4, 134, 8, 4, 134, 9, 4, 134, 10, 4, 134, 27, 4, 133, 28, 4, 133,
        29, 4, 133, 30, 4, 133, 254, 2, 132, 11, 2, 132, 12, 2, 132, 13,2, 132,
        14, 2, 132, 19, 2, 132, 20, 2, 132, 21, 2, 132, 22, 2, 132, 0, 1, 0, 1,
        1, 0, 15, 1, 2, 16, 1, 2, 17, 1, 2, 18, 1, 2, 23, 1, 0, 24, 1, 0, 25, 1,
        0, 26, 1, 2, 7, 150, 130, 233, 42, 234, 120, 233, 42, 19, 218, 10, 41,
        131, 80, 137, 8, 208, 206, 10, 41, 220, 95, 137, 8, 22, 176, 32, 0,22,
        176, 32, 0, 88, 34, 9, 0, 255, 255, 255, 255, 172, 1, 11, 41, 164, 238,
        139, 8, 58, 63, 10, 41, 131, 80, 137, 8, 0, 0, 137, 2, 0, 0, 234, 10, 57,
        14, 255, 255, 255, 255, 184, 0, 227, 0, 9, 1, 164, 172, 255, 255, 255, 7,
        1, 255, 2, 150, 130, 233, 42, 1, 0, 0, 0, 8, 9, 1, 72, 0, 0, 18, 0, 34,
        253, 4, 134, 2, 4, 134, 3, 4, 133, 4, 4, 133, 7, 4, 134, 8, 4, 134, 9, 4,
        134, 10, 4, 134, 29, 4, 133, 30, 4, 133, 31, 4, 133, 32, 4, 133, 254, 2,
        132, 11, 2, 132, 13, 2, 132, 14, 2, 132, 15, 2, 132, 20, 2, 132, 21, 2,
        132, 22, 2, 132, 23, 2, 132, 25, 2, 132, 26, 2, 132, 0, 1, 0, 1, 1, 0, 5,
        1, 0, 6, 1, 0, 16, 1, 2, 17, 1, 2, 18, 1, 2, 19, 1, 2, 24, 1, 2, 27, 1, 2,
        28, 1, 0, 8, 150, 130, 233, 42, 234, 120, 233, 42, 19, 218, 10, 41, 131,
        80, 137, 8, 22, 176, 32, 0, 22, 176, 32, 0, 88, 34, 9, 0, 255, 255, 255,
        255, 172, 1, 11, 41, 164, 238, 139, 8, 58, 63, 10, 41, 131, 80, 137, 8, 0,
        0, 137, 2, 0, 0, 234, 10, 57, 14, 255, 255, 255, 255, 184, 0, 227, 0, 0,
        0, 1, 0, 9, 1, 1, 0, 164, 172, 255, 255, 46, 255, 0, 73, 0, 0, 34, 0, 7,
        253, 4, 134, 0, 4, 134, 1, 2, 132, 2, 1, 0, 3, 1, 0, 4, 1, 0, 6, 1, 2, 9,
        150, 130, 233, 42, 22, 176, 32, 0, 1, 0, 0, 26, 1, 255, 233, 66, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])

    a = parse(download_response)
    assert isinstance(a, DownloadResponse)


########NEW FILE########
__FILENAME__ = commons
# Ant-FS
#
# Copyright (c) 2012, Gustav Tiger <gustav@tiger.name>
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import array

# Most significant bit first (big-endian)
# x^16+x^12+x^5+1 = (1) 0001 0000 0010 0001 = 0x1021
def crc(data):
    rem = 0
    # A popular variant complements rem here
    for byte in data:
        rem ^= (byte << 8)  # n = 16 in this example
        for _ in range(0, 8):     # Assuming 8 bits per byte
            if rem & 0x8000:    # if leftmost (most significant) bit is set
                rem = (rem << 1)
                rem ^= 0x1021
            else:
                rem = rem << 1
            rem = rem & 0xffff # Trim remainder to 16 bits
    return "done", bin(rem)


print crc(array.array("B", "Wikipedia"))
    

########NEW FILE########
__FILENAME__ = file_test
# Ant-FS
#
# Copyright (c) 2012, Gustav Tiger <gustav@tiger.name>
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import array

from ant.fs.file import Directory

def parse_dir():
    
    data = array.array('B', [1, 16, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
            0, 1, 0, 1, 12, 0, 0, 0, 80, 0, 224, 25, 0, 0, 0, 0, 0, 2, 0,
            1, 13, 0, 0, 0, 48, 0, 0, 4, 0, 0, 0, 0, 0, 3, 0, 128, 1, 255,
            255, 0, 144, 92, 2, 0, 0, 0, 0, 0, 0, 4, 0, 128, 2, 255, 255,
            0, 208, 29, 2, 0, 0, 0, 0, 0, 0, 5, 0, 128, 3, 3, 0, 0, 208,
            172, 4, 0, 0, 0, 0, 0, 0, 6, 0, 128, 3, 1, 0, 0, 208, 172, 4,
            0, 0, 0, 0, 0, 0, 7, 0, 128, 4, 33, 0, 0, 176, 32, 9, 0, 0, 128,
            250, 213, 41, 8, 0, 128, 4, 34, 0, 0, 176, 160, 49, 0, 0, 130,
            250, 213, 41, 9, 0, 128, 4, 35, 0, 0, 176, 184, 23, 0, 0, 130,
            250, 213, 41, 10, 0, 128, 4, 36, 0, 0, 176, 233, 2, 0, 0, 130,
            250, 213, 41, 11, 0, 128, 4, 37, 0, 0, 176, 139, 3, 0, 0, 132,
            250, 213, 41, 12, 0, 128, 4, 38, 0, 0, 176, 233, 2, 0, 0, 132,
            250, 213, 41, 13, 0, 128, 4, 39, 0, 0, 176, 45, 4, 0, 0, 134, 250,
            213, 41, 14, 0, 128, 4, 40, 0, 0, 176, 49, 29, 0, 0, 134, 250, 213,
            41, 15, 0, 128, 4, 41, 0, 0, 176, 89, 26, 0, 0, 134, 250, 213, 41,
            16, 0, 128, 4, 42, 0, 0, 176, 173, 61, 0, 0, 136, 250, 213, 41, 17,
            0, 128, 4, 43, 0, 0, 176, 80, 67, 0, 0, 138, 250, 213, 41, 18, 0,
            128, 4, 44, 0, 0, 176, 107, 46, 0, 0, 138, 250, 213, 41, 19, 0,
            128, 4, 45, 0, 0, 176, 40, 26, 0, 0, 140, 250, 213, 41, 20, 0, 128,
            4, 46, 0, 0, 176, 217, 23, 0, 0, 140, 250, 213, 41, 21, 0, 128, 4,
            47, 0, 0, 176, 108, 3, 0, 0, 144, 250, 213, 41, 22, 0, 128, 4, 48,
            0, 0, 176, 166, 80, 0, 0, 144, 250, 213, 41, 23, 0, 128, 4, 49, 0,
            0, 176, 159, 62, 0, 0, 146, 250, 213, 41, 24, 0, 128, 4, 50, 0, 0,
            176, 253, 15, 0, 0, 148, 250, 213, 41, 25, 0, 128, 4, 51, 0, 0,
            176, 163, 24, 0, 0, 150, 250, 213, 41, 26, 0, 128, 4, 52, 0, 0,
            176, 56, 25, 0, 0, 150, 250, 213, 41, 27, 0, 128, 4, 53, 0, 0,
            176, 158, 22, 0, 0, 152, 250, 213, 41, 28, 0, 128, 4, 54, 0, 0,
            176, 114, 19, 0, 0, 154, 250, 213, 41, 29, 0, 128, 4, 55, 0, 0,
            176, 239, 23, 0, 0, 154, 250, 213, 41, 30, 0, 128, 4, 56, 0, 0,
            176, 155, 35, 0, 0, 156, 250, 213, 41, 31, 0, 128, 4, 57, 0, 0,
            176, 156, 19, 0, 0, 158, 250, 213, 41])
    
    d = Directory.parse(data)
    print d, d.get_version(), d._time_format, d._current_system_time, d._last_modified

########NEW FILE########
__FILENAME__ = test
#from ant.base import Message
from ant.easy.node import Node, Message
from ant.easy.channel import Channel
from ant.fs.manager import Application

import array
import logging
import struct
import sys
import threading
import traceback


class App(Application):
    
    def setup_channel(self, channel):
        print "on setup channel"
        channel.set_period(4096)
        channel.set_search_timeout(255)
        channel.set_rf_freq(50)
        channel.set_search_waveform([0x53, 0x00])
        channel.set_id(0, 0x01, 0)
        
        print "Open channel..."
        channel.open()
        channel.request_message(Message.ID.RESPONSE_CHANNEL_STATUS)

    def on_link(self, beacon):
        print "on link"
        self.link()
    
    def on_authentication(self, beacon):
        print "on authentication"
        serial  = self.authentication_serial()
        #passkey = self.authentication_pair("Friendly little name")
        passkey = array.array('B', [234, 85, 223, 166, 87, 48, 71, 153])
        self.authentication_passkey(passkey)
        #print "Link", serial, "-", info, "-", beacon

    def on_transport(self, beacon):
        print "on transport"
        d = self.download_directory()
        print d, d.get_version(), d._time_format, d._current_system_time, d._last_modified
        print d._files

def main():

    try:
        # Set up logging
        logger = logging.getLogger("garmin")
        logger.setLevel(logging.DEBUG)
        handler = logging.FileHandler("test.log", "w")
        #handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(fmt='%(threadName)-10s %(asctime)s  %(name)-15s  %(levelname)-8s  %(message)s'))
        logger.addHandler(handler)

        app = App()
        app.start()
    except (Exception, KeyboardInterrupt):
        traceback.print_exc()
        print "Interrupted"
        app.stop()
        sys.exit(1)


########NEW FILE########
__FILENAME__ = garmin
#!/usr/bin/python
#
# Ant
#
# Copyright (c) 2012, Gustav Tiger <gustav@tiger.name>
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

#from ant.base import Message
#from ant.easy.node import Node, Message
#from ant.easy.channel import Channel
from ant.fs.manager import Application, AntFSAuthenticationException
from ant.fs.file import File

import utilities
import scripting

import array
import logging
import datetime
import time
from optparse import OptionParser   
import os
import struct
import sys
import traceback

_logger = logging.getLogger("garmin")

_directories = {
    ".":          File.Identifier.DEVICE,
    "activities": File.Identifier.ACTIVITY,
    "courses":    File.Identifier.COURSE,
    #"profile":   File.Identifier.?
    #"goals?":    File.Identifier.GOALS,
    #"bloodprs":  File.Identifier.BLOOD_PRESSURE,
    #"summaries": File.Identifier.ACTIVITY_SUMMARY,
    "settings":   File.Identifier.SETTING,
    "sports":     File.Identifier.SPORT_SETTING,
    "totals":     File.Identifier.TOTALS,
    "weight":     File.Identifier.WEIGHT,
    "workouts":   File.Identifier.WORKOUT}

_filetypes = dict((v, k) for (k, v) in _directories.items())


class Device:
    
    class ProfileVersionException(Exception):
        pass
    
    _PROFILE_VERSION      = 1
    _PROFILE_VERSION_FILE = "profile_version"
    
    def __init__(self, basedir, serial, name):
        self._path   = os.path.join(basedir, str(serial))
        self._serial = serial
        self._name   = name
        
        # Check profile version, if not a new device
        if os.path.isdir(self._path):
            if self.get_profile_version() < self._PROFILE_VERSION:
                raise Device.ProfileVersionException("Profile version mismatch, too old")
            elif self.get_profile_version() > self._PROFILE_VERSION:
                raise Device.ProfileVersionException("Profile version mismatch, to new")

        # Create directories
        utilities.makedirs_if_not_exists(self._path)
        for directory in _directories:
            directory_path = os.path.join(self._path, directory)
            utilities.makedirs_if_not_exists(directory_path)

        # Write profile version (If none)
        path = os.path.join(self._path, self._PROFILE_VERSION_FILE)
        if not os.path.exists(path):
            with open(path, 'wb') as f:
                f.write(str(self._PROFILE_VERSION))

    def get_path(self):
        return self._path

    def get_serial(self):
        return self._serial

    def get_name(self):
        return self._name

    def get_profile_version(self):
        path = os.path.join(self._path, self._PROFILE_VERSION_FILE)
        try:
            with open(path, 'rb') as f:
                return int(f.read())
        except IOError as e:
            # TODO
            return 0

    def read_passkey(self):

        try:
            with open(os.path.join(self._path, "authfile"), 'rb') as f:
                d = array.array('B', f.read())
                _logger.debug("loaded authfile: %r", d)
                return d
        except:
            return None
            
    def write_passkey(self, passkey):

        with open(os.path.join(self._path, "authfile"), 'wb') as f:
            passkey.tofile(f)
            _logger.debug("wrote authfile: %r, %r", self._serial, passkey)




class Garmin(Application):

    PRODUCT_NAME = "garmin-extractor"

    def __init__(self, uploading):
        Application.__init__(self)
        
        _logger.debug("Creating directories")
        self.config_dir = utilities.XDG(self.PRODUCT_NAME).get_config_dir()
        self.script_dir = os.path.join(self.config_dir, "scripts")
        utilities.makedirs_if_not_exists(self.config_dir)
        utilities.makedirs_if_not_exists(self.script_dir)
        
        self.scriptr  = scripting.Runner(self.script_dir)
        
        self.device = None
        self._uploading = uploading

    def setup_channel(self, channel):
        channel.set_period(4096)
        channel.set_search_timeout(255)
        channel.set_rf_freq(50)
        channel.set_search_waveform([0x53, 0x00])
        channel.set_id(0, 0x01, 0)
        
        channel.open()
        #channel.request_message(Message.ID.RESPONSE_CHANNEL_STATUS)
        print "Searching..."

    def on_link(self, beacon):
        _logger.debug("on link, %r, %r", beacon.get_serial(),
                      beacon.get_descriptor())
        self.link()
        return True

    def on_authentication(self, beacon):
        _logger.debug("on authentication")
        serial, name = self.authentication_serial()
        self._device = Device(self.config_dir, serial, name)
        
        passkey = self._device.read_passkey()
        print "Authenticating with", name, "(" + str(serial) + ")"
        _logger.debug("serial %s, %r, %r", name, serial, passkey)
        
        if passkey != None:
            try:
                print " - Passkey:",
                self.authentication_passkey(passkey)
                print "OK"
                return True
            except AntFSAuthenticationException as e:
                print "FAILED"
                return False
        else:
            try:
                print " - Pairing:",
                passkey = self.authentication_pair(self.PRODUCT_NAME)
                self._device.write_passkey(passkey)
                print "OK"
                return True
            except AntFSAuthenticationException as e:
                print "FAILED"
                return False

    def on_transport(self, beacon):

        directory = self.download_directory()
        #directory.print_list()
        
        # Map local files to FIT file types
        local_files  = {}
        for folder, filetype in _directories.items():
            local_files[filetype] = []
            path = os.path.join(self._device.get_path(), folder)
            for filename in os.listdir(path):
                if os.path.splitext(filename)[1].lower() == ".fit":
                    local_files[filetype] += [filename]

        # Map remote files to FIT file types
        remote_files = {}
        for filetype in _filetypes:
            remote_files[filetype] = []
        for fil in directory.get_files():
            if fil.get_fit_sub_type() in remote_files:
                remote_files[fil.get_fit_sub_type()] += [fil]

        # Calculate remote and local file diff
        # TODO: rework when adding delete support
        downloading, uploading, download_total, upload_total = {}, {}, 0, 0
        for filetype in _filetypes:
            downloading[filetype] = filter(lambda fil: self.get_filename(fil)
                    not in local_files[filetype], remote_files[filetype])
            download_total += len(downloading[filetype])
            uploading[filetype] = filter(lambda name: name not in
                    map(self.get_filename, remote_files[filetype]),
                    local_files[filetype])
            upload_total += len(uploading[filetype])

        print "Downloading", download_total, "file(s)", \
              "and uploading", upload_total, "file(s)"

        # Download missing files:
        for files in downloading.values():
            for fileobject in files:
                self.download_file(fileobject)

        # Upload missing files:
        if upload_total > 0 and self._uploading:
            # Upload
            results = {}
            for typ, files in uploading.items():
                for filename in files:
                    #print "upload", typ, filename
                    index = self.upload_file(typ, filename)
                    #print "got index", index
                    results[index] = (filename, typ)
            # Rename
            directory = self.download_directory()
            #directory.print_list()
            for index, (filename, typ) in results.items():
                #print "rename for", index, filename, typ
                #print "candidates:", filter(lambda f: f.get_index() == index, directory.get_files())
                try:
                    file_object = filter(lambda f: f.get_index() == index,
                            directory.get_files())[0]
                    src = os.path.join(self._device.get_path(), _filetypes[typ], filename)
                    dst = self.get_filepath(file_object)
                    print " - Renamed", src, "to", dst
                    os.rename(src, dst)
                except Exception as e:
                    print " - Failed", index, filename, e

    def get_filename(self, fil):
        return str.format("{0}_{1}_{2}.fit",
                fil.get_date().strftime("%Y-%m-%d_%H-%M-%S"),
                fil.get_fit_sub_type(), fil.get_fit_file_number())

    def get_filepath(self, fil):
        path = os.path.join(self._device.get_path(),
                _filetypes[fil.get_fit_sub_type()])
        return os.path.join(path, self.get_filename(fil))


    def _get_progress_callback(self):
        def callback(new_progress):
            delta = time.time() - callback.start_time
            eta = datetime.timedelta(seconds=int(delta / new_progress - delta))
            s = "[{0:<30}] ETA: {1}".format("." * int(new_progress * 30), eta)
            sys.stdout.write(s)
            sys.stdout.flush()
            sys.stdout.write("\b" * len(s))
        callback.start_time = time.time()
        return callback

    def download_file(self, fil):

        sys.stdout.write("Downloading {0}: ".format(self.get_filename(fil)))
        sys.stdout.flush()
        data = self.download(fil.get_index(), self._get_progress_callback())
        with open(self.get_filepath(fil), "w") as fd:
            data.tofile(fd)
        sys.stdout.write("\n")
        sys.stdout.flush()
        
        self.scriptr.run_download(self.get_filepath(fil), fil.get_fit_sub_type())

    def upload_file(self, typ, filename):
        sys.stdout.write("Uploading {0}: ".format(filename))
        sys.stdout.flush()
        with open(os.path.join(self._device.get_path(), _filetypes[typ],
                filename), 'r') as fd:
            data = array.array('B', fd.read())
        index = self.create(typ, data, self._get_progress_callback())
        sys.stdout.write("\n")
        sys.stdout.flush()
        return index

def main():
    
    parser = OptionParser()
    parser.add_option("--upload", action="store_true", dest="upload", default=False, help="enable uploading")
    parser.add_option("--debug", action="store_true", dest="debug", default=False, help="enable debug")
    (options, args) = parser.parse_args()
    
    # Find out what time it is
    # used for logging filename.
    currentTime = time.strftime("%Y%m%d-%H%M%S")

    # Set up logging
    logger = logging.getLogger("garmin")
    logger.setLevel(logging.DEBUG)

    # If you add new module/logger name longer than the 15 characters just increase the value after %(name).
    # The longest module/logger name now is "garmin.ant.base" and "garmin.ant.easy".
    formatter = logging.Formatter(fmt='%(threadName)-10s %(asctime)s  %(name)-15s  %(levelname)-8s  %(message)s (%(filename)s:%(lineno)d)')

    handler = logging.FileHandler(currentTime + "-garmin.log", "w")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    if options.debug:
        logger.addHandler(logging.StreamHandler())

    try:
        g = Garmin(options.upload)
        try:
            g.start()
        except:
            g.stop()
            raise
    except Device.ProfileVersionException as e:
        print "\nError:", str(e), "\n\nThis means that", \
                Garmin.PRODUCT_NAME, "found that your data directory " \
                "stucture was too old or too new. The best option is " \
                "probably to let", Garmin.PRODUCT_NAME, "recreate your " \
                "folder by deleting your data folder, after backing it up, " \
                "and let all your files be redownloaded from your sports " \
                "watch."
    except (Exception, KeyboardInterrupt) as e:
        traceback.print_exc()
        for line in traceback.format_exc().splitlines():
            _logger.error("%r", line)
        print "Interrupted:", str(e)
        sys.exit(1)

if __name__ == "__main__":
    sys.exit(main())


########NEW FILE########
__FILENAME__ = scripting
# Utilities
#
# Copyright (c) 2012, Gustav Tiger <gustav@tiger.name>
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import errno
import os
import subprocess
import threading

class Runner:

    def __init__(self, directory):
        self.directory = directory
        
        # TODO: loop over scripts, check if they are runnable, warn
        #       then don't warn at runtime.


    def get_scripts(self):
        scripts = []
        for _, _, filenames in os.walk(self.directory):
            for filename in filenames:
                scripts.append(filename)
        return sorted(scripts)

    def _run_action(self, action, filename, fit_type):
        for script in self.get_scripts():
            try:
                subprocess.call([os.path.join(self.directory, script),
                                 action, filename, str(fit_type)])
            except OSError as e:
                print " - Could not run", script, "-",\
                      errno.errorcode[e.errno], os.strerror(e.errno)

    def run_action(self, action, filename, fit_type):
        t = threading.Thread(target=self._run_action, args=(action, filename, fit_type))
        t.start()

    def run_download(self, filename, fit_type):
        self.run_action("DOWNLOAD", filename, fit_type)

    def run_upload(self, filename, fit_type):
        self.run_action("UPLOAD", filename, fit_type)

    def run_delete(self, filename, fit_type):
        self.run_action("DELETE", filename, fit_type)


########NEW FILE########
__FILENAME__ = 40-convert_to_tcx
#!/usr/bin/python
#
# Script to run the FIT-to-TCX converter on every new FIT file that is being
# downloaded by Garmin-Extractor.
#
# Adjust the fittotcx path to point to where you have put the FIT-to-TCX files.
#
# Copyright (c) 2012, Gustav Tiger <gustav@tiger.name>
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import errno
import os
import subprocess
import sys

fittotcx = "/path/to/FIT-to-TCX/fittotcx.py"

def main(action, filename, fit_type):

    # Only new downloads which are activities
    if action != "DOWNLOAD" or fit_type != "4":
        return 0

    basedir  = os.path.split(os.path.dirname(filename))[0]
    basefile = os.path.basename(filename)

    # Create directory
    targetdir = os.path.join(basedir, "activities_tcx")
    try:
        os.mkdir(targetdir)
    except:
        pass

    targetfile = os.path.splitext(basefile)[0] + ".tcx"

    try:
        # Run FIT-to-TCX
        process = subprocess.Popen([fittotcx, filename], stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        (data, _) = process.communicate()
    except OSError as e:
        print "Could not run Convert to TCX -", fittotcx, \
              "-", errno.errorcode[e.errno], os.strerror(e.errno)
        return -1

    if process.returncode != 0:
        print "Convert to TCX exited with error code", process.returncode
        return -1

    # Write result
    f = file(os.path.join(targetdir, targetfile), 'w')
    f.write(data)
    f.close()
    return 0

if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))


########NEW FILE########
__FILENAME__ = 40-upload_to_garmin_connect
#!/usr/bin/python
#
# Code by Tony Bussieres <t.bussieres@gmail.com> inspired by 
# 40-convert_to_tcx.py by Gustav Tiger <gustav@tiger.name>
#
# This helper uses GcpUploader to send the fit files to Garmin Connect
# 
# To install GcpUploader:
#
# sudo pip install GcpUploader
#
# edit the file ~/.guploadrc and add the following
# [Credentials]
# username=yourgarminuser
# password=yourgarminpass
#
# Then change the gupload path  (See CHANGEME in the code)
#
# Don't forget to make this script executable :
#
# chmod +x /path/to/40-upload_to_garmin_connect.py


import errno
import os
import subprocess
import sys

# CHANGE ME:
gupload = "/path/to/bin/gupload.py"

def main(action, filename):

    if action != "DOWNLOAD":
        return 0

    try:
        process = subprocess.Popen([gupload, filename], stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        (data, _) = process.communicate()
    except OSError as e:
        print "Could not send to Garmin", gupload, \
              "-", errno.errorcode[e.errno], os.strerror(e.errno)
        return -1

    if process.returncode != 0:
        print "gupload.py exited with error code", process.returncode
        return -1
    print "Successfully uploaded %s to Garmin Connect" % (filename);
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))


########NEW FILE########
__FILENAME__ = utilities
# Utilities
#
# Copyright (c) 2012, Gustav Tiger <gustav@tiger.name>
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import errno
import os

def makedirs_if_not_exists(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno == errno.EEXIST:
            pass
        else: 
            raise


class XDGError(Exception):
    
    def __init__(self, message):
        self.message = message

class XDG:

    def __init__(self, application):
        self._application = application

    def get_data_dir(self):
        if "XDG_DATA_HOME" in os.environ:
            return os.path.join(os.environ["XDG_DATA_HOME"], self._application)
        elif "HOME" in os.environ:
            return os.path.join(os.environ["HOME"], ".local/share", self._application)
        else:
            raise XDGError("Neither XDG_DATA_HOME nor HOME found in the environment")
        
    def get_config_dir(self):
        if "XDG_CONFIG_HOME" in os.environ:
            return os.path.join(os.environ["XDG_CONFIG_HOME"], self._application)
        elif "HOME" in os.environ:
            return os.path.join(os.environ["HOME"], ".config", self._application)
        else:
            raise XDGError("Neither XDG_CONFIG_HOME nor HOME found in the environment")


########NEW FILE########
