__FILENAME__ = bases
from .protocol import ANTReceiveException
from .libusb import ANTlibusb
import usb

class DynastreamANT(ANTlibusb):
    """Class that represents the Dynastream USB stick base, for
    garmin/suunto equipment. Only needs to set VID/PID.

    """
    VID = 0x0fcf
    PID = 0x1008
    NAME = "Dynastream"

class FitBitANT(ANTlibusb):
    """Class that represents the fitbit base. Due to the extra
    hardware to handle tracker connection and charging, has an extra
    initialization sequence.

    """

    VID = 0x10c4
    PID = 0x84c4
    NAME = "FitBit"

    def open(self, vid = None, pid = None):
        if not super(FitBitANT, self).open(vid, pid):
            return False
        self.init()
        return True
    
    def init(self):
        # Device setup
        # bmRequestType, bmRequest, wValue, wIndex, data
        self._connection.ctrl_transfer(0x40, 0x00, 0xFFFF, 0x0, [])
        self._connection.ctrl_transfer(0x40, 0x01, 0x2000, 0x0, [])
        # At this point, we get a 4096 buffer, then start all over
        # again? Apparently doesn't require an explicit receive
        self._connection.ctrl_transfer(0x40, 0x00, 0x0, 0x0, [])
        self._connection.ctrl_transfer(0x40, 0x00, 0xFFFF, 0x0, [])
        self._connection.ctrl_transfer(0x40, 0x01, 0x2000, 0x0, [])
        self._connection.ctrl_transfer(0x40, 0x01, 0x4A, 0x0, [])
        # Receive 1 byte, should be 0x2
        self._connection.ctrl_transfer(0xC0, 0xFF, 0x370B, 0x0, 1)
        self._connection.ctrl_transfer(0x40, 0x03, 0x800, 0x0, [])
        self._connection.ctrl_transfer(0x40, 0x13, 0x0, 0x0, \
                                       [0x08, 0x00, 0x00, 0x00,
                                        0x40, 0x00, 0x00, 0x00,
                                        0x00, 0x00, 0x00, 0x00,
                                        0x00, 0x00, 0x00, 0x00
                                        ])
        self._connection.ctrl_transfer(0x40, 0x12, 0x0C, 0x0, [])
        try:
            self._receive()
        except usb.USBError:
            pass

########NEW FILE########
__FILENAME__ = libusb
#!/usr/bin/env python
#################################################################
# pyusb access for ant devices
# By Kyle Machulis <kyle@nonpolynomial.com>
# http://www.nonpolynomial.com
#
# Licensed under the BSD License, as follows
#
# Copyright (c) 2011, Kyle Machulis/Nonpolynomial Labs
# All rights reserved.
#
# Redistribution and use in source and binary forms, 
# with or without modification, are permitted provided 
# that the following conditions are met:
#
#    * Redistributions of source code must retain the 
#      above copyright notice, this list of conditions 
#      and the following disclaimer.
#    * Redistributions in binary form must reproduce the 
#      above copyright notice, this list of conditions and 
#      the following disclaimer in the documentation and/or 
#      other materials provided with the distribution.
#    * Neither the name of the Nonpolynomial Labs nor the names 
#      of its contributors may be used to endorse or promote 
#      products derived from this software without specific 
#      prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND 
# CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, 
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF 
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE 
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR 
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, 
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT 
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; 
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN 
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR 
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, 
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#################################################################
#

from protocol import ANT
import usb

class ANTlibusb(ANT):
    ep = { 'in'  : 0x81, \
           'out' : 0x01
           }

    def __init__(self, chan=0x0, debug=False):
        super(ANTlibusb, self).__init__(chan, debug)
        self._connection = False
        self.timeout = 1000

    def open(self, vid = None, pid = None):
        if vid is None:
            vid = self.VID
        if pid is None:
            pid = self.PID
        self._connection = usb.core.find(idVendor = vid,
                                         idProduct = pid)
        if self._connection is None:
            return False

        # For some reason, we have to set config, THEN reset,
        # otherwise we segfault back in the ctypes (on linux, at
        # least). 
        self._connection.set_configuration()
        self._connection.reset()
        # The we have to set our configuration again
        self._connection.set_configuration()

        # Then we should get back a reset check, with 0x80
        # (SUSPEND_RESET) as our status
        #
        # I've commented this out because -- though it should just work
        # it does seem to be causing some odd problems for me and does
        # work with out it. Reed Wade - 31 Dec 2011
        ##self._check_reset_response(0x80)
        return True

    def close(self):
        if self._connection is not None:
            self._connection = None

    def _send(self, command):
        # libusb expects ordinals, it'll redo the conversion itself.
        c = command
        self._connection.write(self.ep['out'], map(ord, c), 0, 100)

    def _receive(self, size=4096):
        return self._connection.read(self.ep['in'], size, 0, self.timeout)

########NEW FILE########
__FILENAME__ = protocol
#!/usr/bin/env python
#################################################################
# ant message protocol
# By Kyle Machulis <kyle@nonpolynomial.com>
# http://www.nonpolynomial.com
#
# Licensed under the BSD License, as follows
#
# Copyright (c) 2011, Kyle Machulis/Nonpolynomial Labs
# All rights reserved.
#
# Redistribution and use in source and binary forms, 
# with or without modification, are permitted provided 
# that the following conditions are met:
#
#    * Redistributions of source code must retain the 
#      above copyright notice, this list of conditions 
#      and the following disclaimer.
#    * Redistributions in binary form must reproduce the 
#      above copyright notice, this list of conditions and 
#      the following disclaimer in the documentation and/or 
#      other materials provided with the distribution.
#    * Neither the name of the Nonpolynomial Labs nor the names 
#      of its contributors may be used to endorse or promote 
#      products derived from this software without specific 
#      prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND 
# CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, 
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF 
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE 
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR 
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, 
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT 
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; 
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN 
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR 
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, 
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#################################################################
#
# ANT code originally taken from
# http://code.google.com/p/mstump-learning-exercises/source/browse/trunk/python/ANT/ant_twisted.py
# Added to and untwistedized and fixed up by Kyle Machulis <kyle@nonpolynomial.com>
#

import operator, struct, array, time

class ANTReceiveException(Exception):
    pass

def hexList(data):
    return map(lambda s: chr(s).encode('HEX'), data)

def hexRepr(data):
    return repr(hexList(data))

def intListToByteList(data):
    return map(lambda i: struct.pack('!H', i)[1], array.array('B', data))

class ANTStatusException(Exception):
    pass

def log(f):
    def wrapper(self, *args, **kwargs):
        if self._debug:
            print "Start", f.__name__, args, kwargs
        try:
            res = f(self, *args, **kwargs)
        except:
            if self._debug:
                print "Fail", f.__name__
            raise
        if self._debug:
            print "End", f.__name__, res
        return res
    return wrapper

class ANT(object):

    def __init__(self, chan=0x00, debug=False):
        self._debug = debug
        self._chan = chan

        self._state = 0
        self._receiveBuffer = []

    def _event_to_string(self, event):
        try:
            return { 0:"RESPONSE_NO_ERROR",
                     1:"EVENT_RX_SEARCH_TIMEOUT",
                     2:"EVENT_RX_FAIL",
                     3:"EVENT_TX",
                     4:"EVENT_TRANSFER_RX_FAILED",
                     5:"EVENT_TRANSFER_TX_COMPLETED",
                     6:"EVENT_TRANSFER_TX_FAILED",
                     7:"EVENT_CHANNEL_CLOSED",
                     8:"EVENT_RX_FAIL_GO_TO_SEARCH",
                     9:"EVENT_CHANNEL_COLLISION",
                     10:"EVENT_TRANSFER_TX_START",
                     21:"CHANNEL_IN_WRONG_STATE",
                     22:"CHANNEL_NOT_OPENED",
                     24:"CHANNEL_ID_NOT_SET",
                     25:"CLOSE_ALL_CHANNELS",
                     31:"TRANSFER_IN_PROGRESS",
                     32:"TRANSFER_SEQUENCE_NUMBER_ERROR",
                     33:"TRANSFER_IN_ERROR",
                     40:"INVALID_MESSAGE",
                     41:"INVALID_NETWORK_NUMBER",
                     48:"INVALID_LIST_ID",
                     49:"INVALID_SCAN_TX_CHANNEL",
                     51:"INVALID_PARAMETER_PROVIDED",
                     53:"EVENT_QUE_OVERFLOW",
                     64:"NVM_FULL_ERROR",
                     65:"NVM_WRITE_ERROR",
                     66:"ASSIGN_CHANNEL_ID",
                     81:"SET_CHANNEL_ID",
                     0x4b:"OPEN_CHANNEL"}[event]
        except:
            return "%02x" % event

    def _check_reset_response(self, status):
        for tries in range(8):
            try:
                data = self._receive_message()
            except ANTReceiveException:
                continue
            if len(data) > 3 and data[2] == 0x6f and data[3] == status:
                return
        raise ANTStatusException("Failed to detect reset response")

    def _check_ok_response(self):
        # response packets will always be 7 bytes
        status = self._receive_message()

        if len(status) == 0:
            raise ANTStatusException("No message response received!")

        if status[2] == 0x40 and status[5] == 0x0:
            return

        raise ANTStatusException("Message status %d does not match 0x0 (NO_ERROR)" % (status[5]))

    @log
    def reset(self):
        self._send_message(0x4a, 0x00)
        # According to protocol docs, the system will take a maximum
        # of .5 seconds to restart
        #
        # sleep time was 0.6, changed to 1.0 which reduces fail rate; a retry might
        # be more sensible but wasn't sure if that might lead to possible duplicate 
        # acknowledgements in the receive queue. A setting of 2.0 caused the interface 
        # to not read fitbit devices. - Reed 31 Dec 2011
        #
        time.sleep(1.0)
        #
        # This is a requested reset, so we expect back 0x20
        # (COMMAND_RESET)
        self._check_reset_response(0x20)

    @log
    def set_channel_frequency(self, freq):
        self._send_message(0x45, self._chan, freq)
        self._check_ok_response()

    @log
    def set_transmit_power(self, power):
        self._send_message(0x47, 0x0, power)
        self._check_ok_response()

    @log
    def set_search_timeout(self, timeout):
        self._send_message(0x44, self._chan, timeout)
        self._check_ok_response()

    @log
    def send_network_key(self, network, key):
        self._send_message(0x46, network, key)
        self._check_ok_response()

    @log
    def set_channel_period(self, period):
        self._send_message(0x43, self._chan, period)
        self._check_ok_response()

    @log
    def set_channel_id(self, id):
        self._send_message(0x51, self._chan, id)
        self._check_ok_response()

    @log
    def open_channel(self):
        self._send_message(0x4b, self._chan)
        self._check_ok_response()

    @log
    def close_channel(self):
        self._send_message(0x4c, self._chan)
        self._check_ok_response()

    @log
    def assign_channel(self):
        self._send_message(0x42, self._chan, 0x00, 0x00)
        self._check_ok_response()

    @log
    def receive_acknowledged_reply(self, size = 13):
        for tries in range(30):
            status = self._receive_message(size)
            if len(status) > 4 and status[2] == 0x4F:
                return status[4:-1]
        raise ANTReceiveException("Failed to receive acknowledged reply")

    @log
    def _check_tx_response(self, maxtries = 16):
        for msgs in range(maxtries):
            status = self._receive_message()
            if len(status) > 5 and status[2] == 0x40:
                if status[5] == 0x0a: # TX Start
                    continue
                if status[5] == 0x05: # TX successful
                    return
                if status[5] == 0x06: # TX failed
                    raise ANTReceiveException("Transmission Failed")
        raise ANTReceiveException("No Transmission Ack Seen")

    @log
    def _send_burst_data(self, data, sleep = None):
        for tries in range(2):
            for l in range(0, len(data), 9):            
                self._send_message(0x50, data[l:l+9])
                # TODO: Should probably base this on channel timing
                if sleep != None:
                    time.sleep(sleep)
            try:
                self._check_tx_response()
            except ANTReceiveException:
                continue
            return
        raise ANTReceiveException("Failed to send burst data")

    @log
    def _check_burst_response(self):
        response = []
        for tries in range(128):
            status = self._receive_message()
            if len(status) > 5 and status[2] == 0x40 and status[5] == 0x4:
                raise ANTReceiveException("Burst receive failed by event!")
            elif len(status) > 4 and status[2] == 0x4f:
                response = response + status[4:-1]
                return response
            elif len(status) > 4 and status[2] == 0x50:
                response = response + status[4:-1]
                if status[3] & 0x80:
                    return response
        raise ANTReceiveException("Burst receive failed to detect end")

    @log
    def send_acknowledged_data(self, l):
        for tries in range(8):
            try:
                self._send_message(0x4f, self._chan, l)
                self._check_tx_response()
            except ANTReceiveException:
                continue
            return
        raise ANTReceiveException("Failed to send Acknowledged Data")

    def send_str(self, instring):
        if len(instring) > 8:
            raise "string is too big"

        return self._send_message(*[0x4e] + list(struct.unpack('%sB' % len(instring), instring)))

    def _send_message(self, *args):
        data = list()
        for l in list(args):
            if isinstance(l, list):
                data = data + l
            else:
                data.append(l)
        data.insert(0, len(data) - 1)
        data.insert(0, 0xa4)
        data.append(reduce(operator.xor, data))

        if self._debug:
            print "    sent: " + hexRepr(data)
        return self._send(map(chr, array.array('B', data)))

    def _find_sync(self, buf, start=0):
        i = 0;
        for v in buf:
            if i >= start and (v == 0xa4 or v == 0xa5):
                break
            i = i + 1
        if i != 0:
            if self._debug:
                print "Searching for SYNC, discarding: " + hexRepr(buf[0:i])
            del buf[0:i]
        return buf

    def _receive_message(self, size = 4096):
        timeouts = 0
        data = self._receiveBuffer
        l = 4 # Minimum packet size (SYNC, LEN, CMD, CKSM)
        while True:
            if len(data) < l:
                # data[] too small, try to read some more
                from usb.core import USBError
                try:
                    data += self._receive(size).tolist()
                    timeouts = 0
                except USBError:
                    timeouts = timeouts+1
                    if timeouts > 3:
                        # It looks like there isn't anything else coming.  Try
                        # to find a plausable packet..
                        data = self._find_sync(data)
                        while len(data) > 1 and len(data) < data[1]+4:
                            data = self._find_sync(data, 2)
                        if len(data) == 0:
                            # Failed to find anything..
                            self._receiveBuffer = []
                            return []
                continue
            data = self._find_sync(data)
            if len(data) < l: continue
            if data[1] < 0 or data[1] > 32:
                # Length doesn't look "reasonable"
                data = self._find_sync(data, 1)
                continue
            l = data[1] + 4
            if len(data) < l:
                continue
            p = data[0:l]
            if reduce(operator.xor, p) != 0:
                if self._debug:
                    print "Checksum error for proposed packet: " + hexRepr(p)
                data = self._find_sync(data, 1)
                continue
            self._receiveBuffer = data[l:]
            if self._debug:
                print "received: " + hexRepr(p)
            return p

    def _receive(self, size=4096):
        raise Exception("Need to define _receive function for ANT child class!")

    def _send(self):
        raise Exception("Need to define _send function for ANT child class!")


########NEW FILE########
__FILENAME__ = fitbit
#!/usr/bin/env python
#################################################################
# python fitbit object
# By Kyle Machulis <kyle@nonpolynomial.com>
# http://www.nonpolynomial.com
#
# Distributed as part of the libfitbit project
#
# Repo: http://www.github.com/qdot/libfitbit
#
# Licensed under the BSD License, as follows
#
# Copyright (c) 2011, Kyle Machulis/Nonpolynomial Labs
# All rights reserved.
#
# Redistribution and use in source and binary forms,
# with or without modification, are permitted provided
# that the following conditions are met:
#
#    * Redistributions of source code must retain the
#      above copyright notice, this list of conditions
#      and the following disclaimer.
#    * Redistributions in binary form must reproduce the
#      above copyright notice, this list of conditions and
#      the following disclaimer in the documentation and/or
#      other materials provided with the distribution.
#    * Neither the name of the Nonpolynomial Labs nor the names
#      of its contributors may be used to endorse or promote
#      products derived from this software without specific
#      prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND
# CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#################################################################
#
# ANT code originally taken from
# http://code.google.com/p/mstump-learning-exercises/source/browse/trunk/python/ANT/ant_twisted.py
# Added to and untwistedized and basically fixed up by Kyle Machulis <kyle@nonpolynomial.com>
#
# What's Done
#
# - Basic ANT protocol implementation
# - Basic FitBit protocol implementation
# - FitBit Base Initialization
# - FitBit Tracker Connection, Initialization, Info Retreival
# - Blind data retrieval (can get it, don't know what it is)
# - Talking to the fitbit website
# - Fix ANT Burst packet identifer
# - Add checksum checks for ANT receive
# - Fix packet status identifiers in ANT
#
# To Do (Big)
#
# - Dividing out into modules (ant classes may become their own library)
# - Figuring out more data formats and packets
# - Implementing data clearing

import itertools, sys, random, operator, datetime, time
from antprotocol.bases import FitBitANT, DynastreamANT
from antprotocol.protocol import ANTReceiveException

class FitBit(object):
    """Class to represent the fitbit tracker device, the portion of
    the fitbit worn by the user. Stores information about the tracker
    (serial number, firmware version, etc...).

    """

    def __init__(self, base = None):
        #: Iterator cycle of 0-8, for creating tracker packet serial numbers
        self.tracker_packet_count = itertools.cycle(range(0,8))

        # The tracker expects to start on 1, i.e. 0x39 This is set
        # after a reset (which is why we create the tracker in the
        # reset function). It won't talk if you try anything else.
        self.tracker_packet_count.next()

        #: used to track which internal databank we're on when
        self.current_bank_id = 0
        #: tracks current packet id for fitbit communication
        self.current_packet_id = None
        #: serial number of the tracker
        self.serial = None
        #: firmware version loaded on the tracker
        self.firmware_version = None
        #: Major version of BSL (?)
        self.bsl_major_version = None
        #: Minor version of BSL (?)
        self.bsl_minor_version = None
        #: Major version of App (?)
        self.app_major_version = None
        #: Minor version of App (?)
        self.app_minor_version = None
        #: True if tracker is in BSL Mode (?), False otherwise
        self.in_mode_bsl = None
        #: True if tracker is currently on charger, False otherwise
        self.on_charger = None

        self.base = base

    def gen_packet_id(self):
        """Generates the next packet id for information sent to the
        tracker.

        """

        self.current_packet_id = 0x38 + self.tracker_packet_count.next()
        return self.current_packet_id

    def parse_info_packet(self, data):
        """Parses the information gotten from the 0x24 retrieval command"""

        self.serial = data[0:5]
        self.firmware_version = data[5]
        self.bsl_major_version = data[6]
        self.bsl_minor_version = data[7]
        self.app_major_version = data[8]
        self.app_minor_version = data[9]
        self.in_mode_bsl = (False, True)[data[10]]
        self.on_charger = (False, True)[data[11]]

    def __str__(self):
        """Returns string representation of tracker information"""

        return "Tracker Serial: %s\n" \
               "Firmware Version: %d\n" \
               "BSL Version: %d.%d\n" \
               "APP Version: %d.%d\n" \
               "In Mode BSL? %s\n" \
               "On Charger? %s\n" % \
               ("".join(["%x" % (x) for x in self.serial]),
                self.firmware_version,
                self.bsl_major_version,
                self.bsl_minor_version,
                self.app_major_version,
                self.app_minor_version,
                self.in_mode_bsl,
                self.on_charger)

    def init_fitbit(self):
        self.init_device_channel([0xff, 0xff, 0x01, 0x01])

    def init_device_channel(self, channel):
        # ANT device initialization
        self.base.reset()
        self.base.send_network_key(0, [0,0,0,0,0,0,0,0])
        self.base.assign_channel()
        self.base.set_channel_period([0x0, 0x10])
        self.base.set_channel_frequency(0x2)
        self.base.set_transmit_power(0x3)
        self.base.set_search_timeout(0xFF)
        self.base.set_channel_id(channel)
        self.base.open_channel()

    def init_tracker_for_transfer(self):
        self.init_fitbit()
        self.wait_for_beacon()
        self.reset_tracker()

        # 0x78 0x02 is device id reset. This tells the device the new
        # channel id to hop to for dumpage
        cid = [random.randint(0,254), random.randint(0,254)]
        self.base.send_acknowledged_data([0x78, 0x02] + cid + [0x00, 0x00, 0x00, 0x00])
        self.base.close_channel()
        self.init_device_channel(cid + [0x01, 0x01])
        self.wait_for_beacon()
        self.ping_tracker()

    def reset_tracker(self):
        # 0x78 0x01 is apparently the device reset command
        self.base.send_acknowledged_data([0x78, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])

    def command_sleep(self):
        self.base.send_acknowledged_data([0x7f, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x3c])

    def wait_for_beacon(self):
        # FitBit device initialization
        print "Waiting for receive"
        for tries in range(75):
            try:
                d = self.base._receive_message()
                if d[2] == 0x4E:
                    return
            except Exception:
                pass
        raise ANTReceiveException("Failed to see tracker beacon")

    def _get_tracker_burst(self):
        d = self.base._check_burst_response()
        if d[1] != 0x81:
            raise Exception("Response received is not tracker burst! Got %s" % (d[0:2]))
        size = d[3] << 8 | d[2]
        if size == 0:
            return []
        return d[8:8+size]

    def run_opcode(self, opcode, payload = None):
        for tries in range(4):
            try:
                self.send_tracker_packet(opcode)
                data = self.base.receive_acknowledged_reply()
            except:
                continue
            if data[0] != self.current_packet_id:
                print "Tracker Packet IDs don't match! %02x %02x" % (data[0], self.current_packet_id)
                continue
            if data[1] == 0x42:
                return self.get_data_bank()
            if data[1] == 0x61:
                # Send payload data to device
                if payload is not None:
                    self.send_tracker_payload(payload)
                    data = self.base.receive_acknowledged_reply()
                    data.pop(0)
                    return data
                raise Exception("run_opcode: opcode %s, no payload" % (opcode))
            if data[1] == 0x41:
                data.pop(0)
                return data
        raise Exception("Failed to run opcode %s" % (opcode))

    def send_tracker_payload(self, payload):
        # The first packet will be the packet id, the length of the
        # payload, and ends with the payload CRC
        p = [0x00, self.gen_packet_id(), 0x80, len(payload), 0x00, 0x00, 0x00, 0x00, reduce(operator.xor, map(ord, payload))]
        prefix = itertools.cycle([0x20, 0x40, 0x60])
        for i in range(0, len(payload), 8):
            current_prefix = prefix.next()
            plist = []
            if i+8 >= len(payload):
                plist += [(current_prefix + 0x80) | self.base._chan]
            else:
                plist += [current_prefix | self.base._chan]
            plist += map(ord, payload[i:i+8])
            while len(plist) < 9:
                plist += [0x0]
            p += plist
        # TODO: Sending burst data with a guessed sleep value, should
        # probably be based on channel timing
        self.base._send_burst_data(p, .01)

    def get_tracker_info(self):
        data = self.run_opcode([0x24, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        self.parse_info_packet(data)
        return data

    def send_tracker_packet(self, packet):
        p = [self.gen_packet_id()] + packet
        self.base.send_acknowledged_data(p)

    def ping_tracker(self):
        self.base.send_acknowledged_data([0x78, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])

    def check_tracker_data_bank(self, index, cmd):
        self.send_tracker_packet([cmd, 0x00, 0x02, index, 0x00, 0x00, 0x00])
        return self._get_tracker_burst()

    def run_data_bank_opcode(self, index):
        return self.run_opcode([0x22, index, 0x00, 0x00, 0x00, 0x00, 0x00])

    def erase_data_bank(self, index, tstamp=None):
        if tstamp is None: tstamp = int(time.time())
        return self.run_opcode([0x25, index,
                                (tstamp & 0xff000000) >> 24,
                                (tstamp & 0x00ff0000) >> 16,
                                (tstamp & 0x0000ff00) >> 8,
                                (tstamp & 0x000000ff),
                                0x00])

    def get_data_bank(self):
        data = []
        cmd = 0x70  # Send 0x70 on first burst
        for parts in range(2000):
            bank = self.check_tracker_data_bank(self.current_bank_id, cmd)
            self.current_bank_id += 1
            cmd = 0x60  # Send 0x60 on subsequent bursts
            if len(bank) == 0:
                return data
            data = data + bank
        raise ANTReceiveException("Cannot complete data bank")

    def parse_bank2_data(self, data):
        for i in range(0, len(data), 13):
            print ["0x%.02x" % x for x in data[i:i+13]]
            # First 4 bytes are seconds from Jan 1, 1970
            print "Time: %s" % (datetime.datetime.fromtimestamp(data[i] | data[i + 1] << 8 | data[i + 2] << 16 | data[i + 3] << 24))

    def parse_bank0_data(self, data):
        # First 4 bytes are a time
        i = 0
        last_date_time = 0
        time_index = 0
        while i < len(data):
            # Date is in bigendian. No, really. And I think it's
            # because they're prefixing the 3 accelerometer reading
            # bytes with 0x80, so they can & against it.
            if not data[i] & 0x80:
                last_date_time = data[i+3] | data[i+2] << 8 | data[i+1] << 16 | data[i] << 24
                print "Time: %s" % (datetime.datetime.fromtimestamp(last_date_time))
                i = i + 4
                time_index = 0
            else:
                record_date = (datetime.datetime.fromtimestamp(last_date_time + 60 * time_index))
                # steps are easy. It's just the last byte
                steps = data[i+2]
                # active score: second byte, subtract 10 (because METs
                # start at 1 but 1 is subtracted per minute, see
                # asterisk note on fitbit website, divide by 10.
                active_score = (data[i+1] - 10) / 10.0
                # first byte: I don't know. It starts at 0x81. So we at least subtract that.
                not_sure = data[i] - 0x81
                print "%s: ???: %d Active Score: %f Steps: %d" % (record_date, not_sure, active_score, steps)
                i = i + 3
                time_index = time_index + 1

    def parse_bank1_data(self, data):
        for i in range(0, len(data), 14):
            print ["0x%.02x" % x for x in data[i:i+13]]
            # First 4 bytes are seconds from Jan 1, 1970
            daily_steps = data[i+7] << 8 | data[i+6]
            record_date = datetime.datetime.fromtimestamp(data[i] | data[i + 1] << 8 | data[i + 2] << 16 | data[i + 3] << 24)
            print "Time: %s Daily Steps: %d" % (record_date, daily_steps)

    def parse_bank6_data(self, data):
        i = 0
        tstamp = 0
        while i < len(data):
            if data[i] == 0x80:
                floors = data[i+1] / 10
                print "Time: %s: %d Floors" % (datetime.datetime.fromtimestamp(tstamp), floors)
                i += 2
                tstamp += 60
                continue
            d = data[i:i+4]
            tstamp = d[3] | d[2] << 8 | d[1] << 16 | d[0] << 24
            i += 4

def main():
    #base = DynastreamANT(True)
    base = FitBitANT(debug=True)
    if not base.open():
        print "No devices connected!"
        return 1

    device = FitBit(base)

    device.init_tracker_for_transfer()

    device.get_tracker_info()
    # print device.tracker

    device.parse_bank2_data(device.run_data_bank_opcode(0x02))
    print "---"
    device.parse_bank0_data(device.run_data_bank_opcode(0x00))
    device.run_data_bank_opcode(0x04)
    d = device.run_data_bank_opcode(0x02) # 13
    for i in range(0, len(d), 13):
        print ["%02x" % x for x in d[i:i+13]]
    d = device.run_data_bank_opcode(0x00) # 7
    print ["%02x" % x for x in d[0:7]]
    print ["%02x" % x for x in d[7:14]]
    j = 0
    for i in range(14, len(d), 3):
        print d[i:i+3]
        j += 1
    print "Records: %d" % (j)
    device.parse_bank1_data(device.run_data_bank_opcode(0x01))

    # for i in range(0, len(d), 14):
    #     print ["%02x" % x for x in d[i:i+14]]
    base.close()
    return 0

if __name__ == '__main__':
    sys.exit(main())

########NEW FILE########
__FILENAME__ = fitbit_client
#!/usr/bin/env python
#################################################################
# python fitbit web client for uploading data to fitbit site
# By Kyle Machulis <kyle@nonpolynomial.com>
# http://www.nonpolynomial.com
#
# Distributed as part of the libfitbit project
#
# Repo: http://www.github.com/openyou/libfitbit
#
# Licensed under the BSD License, as follows
#
# Copyright (c) 2011, Kyle Machulis/Nonpolynomial Labs
# All rights reserved.
#
# Redistribution and use in source and binary forms, 
# with or without modification, are permitted provided 
# that the following conditions are met:
#
#    * Redistributions of source code must retain the 
#      above copyright notice, this list of conditions 
#      and the following disclaimer.
#    * Redistributions in binary form must reproduce the 
#      above copyright notice, this list of conditions and 
#      the following disclaimer in the documentation and/or 
#      other materials provided with the distribution.
#    * Neither the name of the Nonpolynomial Labs nor the names 
#      of its contributors may be used to endorse or promote 
#      products derived from this software without specific 
#      prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND 
# CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, 
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF 
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE 
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR 
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, 
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT 
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; 
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN 
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR 
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, 
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#################################################################

import sys
import urllib
import urllib2
import urlparse
import base64
import xml.etree.ElementTree as et
from fitbit import FitBit
from antprotocol.bases import FitBitANT, DynastreamANT

class FitBitResponse(object):
    def __init__(self, response):
        self.current_opcode = {}
        self.opcodes = []
        self.root = et.fromstring(response.strip())
        self.host = None
        self.path = None
        self.response = None
        if self.root.find("response") is not None:
            self.host = self.root.find("response").attrib["host"]
            self.path = self.root.find("response").attrib["path"]
            if self.root.find("response").text:
                # Quick and dirty url encode split
                response = self.root.find("response").text
                self.response = dict(urlparse.parse_qsl(response))

        for opcode in self.root.findall("device/remoteOps/remoteOp"):
            op = {}
            op["opcode"] = [ord(x) for x in base64.b64decode(opcode.find("opCode").text)]
            op["payload"] = None
            if opcode.find("payloadData").text is not None:
                op["payload"] = [x for x in base64.b64decode(opcode.find("payloadData").text)]
            self.opcodes.append(op)
    
    def __repr__(self):
        return "<FitBitResponse object at 0x%x opcode=%s, response=%s>" % (id(self), str(self.opcodes), str(self.response))

class FitBitClient(object):
    CLIENT_UUID = "2ea32002-a079-48f4-8020-0badd22939e3"
    #FITBIT_HOST = "http://client.fitbit.com:80"
    FITBIT_HOST = "https://client.fitbit.com" # only used for initial request
    START_PATH = "/device/tracker/uploadData"
    DEBUG = True
    BASES = [FitBitANT, DynastreamANT]

    def __init__(self):
        self.info_dict = {}
        self.fitbit = None
        for base in [bc(debug=self.DEBUG) for bc in self.BASES]:
            for retries in (2,1,0):
                try:
                    if base.open():
                        print "Found %s base" % (base.NAME,)
                        self.fitbit = FitBit(base)
                        self.remote_info = None
                        break
                    else:
                        break
                except Exception, e:
                    print e
                    if retries:
                        print "retrying"
                        time.sleep(5)
            else:
                raise
            if self.fitbit:
                break
        if not self.fitbit:
            print "No devices connected!"
            exit(1)

    def form_base_info(self):
        self.info_dict.clear()
        self.info_dict["beaconType"] = "standard"
        self.info_dict["clientMode"] = "standard"
        self.info_dict["clientVersion"] = "1.0"
        self.info_dict["os"] = "libfitbit"
        self.info_dict["clientId"] = self.CLIENT_UUID
        if self.remote_info:
            self.info_dict = dict(self.info_dict, **self.remote_info)

    def run_upload_request(self):
        try:
            self.fitbit.init_tracker_for_transfer()

            url = self.FITBIT_HOST + self.START_PATH

            # Start the request Chain
            self.form_base_info()
            while url is not None:
                res = urllib2.urlopen(url, urllib.urlencode(self.info_dict)).read()
                print res
                r = FitBitResponse(res)
                self.remote_info = r.response
                self.form_base_info()
                op_index = 0
                for o in r.opcodes:
                    self.info_dict["opResponse[%d]" % op_index] = base64.b64encode(''.join([chr(x) for x in self.fitbit.run_opcode(o["opcode"], o["payload"])]))
                    self.info_dict["opStatus[%d]" % op_index] = "success"
                    op_index += 1
                urllib.urlencode(self.info_dict)
                print self.info_dict
                if r.host:
                    url = "http://%s%s" % (r.host, r.path)
                    print url
                else:
                    print "No URL returned. Quitting."
                    break
        except:
            self.fitbit.base.close()
            raise
        self.fitbit.command_sleep()
        self.fitbit.base.close()

def main():
    f = FitBitClient()
    f.run_upload_request()    
    return 0

if __name__ == '__main__':
    import time
    import traceback
    
    cycle_minutes = 15
    
    while True:
        try:
            main()
        except Exception, e:
            print "Failed with", e
            print
            print '-'*60
            traceback.print_exc(file=sys.stdout)
            print '-'*60
        else:
            print "normal finish"
            print "restarting..."
    
    #sys.exit(main())


########NEW FILE########
