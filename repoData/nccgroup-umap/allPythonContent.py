__FILENAME__ = networking
from threading import Thread
from socket import *
import sys

class netserver(Thread):
    def __init__( self, maxusb_app, port):
        Thread.__init__( self )

        self.maxusb_app = maxusb_app
    
        self.sock = socket( AF_INET, SOCK_STREAM )
        self.maxusb_app.netserver_to_endpoint_sd = self.sock

        self.maxusb_app.netserver_sd = self.sock
        try:
            self.sock.bind(( '', port ))
        except:
            print("Error: Could not bind to local port")
            return

        self.sock.listen(5)
   
    def run( self ):

        newsock = 0

        while (self.maxusb_app.server_running == True):
            try:
                if not newsock:
                    newsock, address = self.sock.accept()    

                self.maxusb_app.netserver_from_endpoint_sd = newsock

                reply = newsock.recv(16384)
                if len(reply) > 0:
                    print ("Socket reply: %s" % reply)
                    self.maxusb_app.reply_buffer = reply

            except:
                print ("Error: Socket Accept")
                sys.exit()

        self.maxusb_app.netserver_to_endpoint_sd.close()
        self.maxusb_app.netserver_from_endpoint_sd.close()



########NEW FILE########
__FILENAME__ = USBAudio
# USBAudio.py
#
# Contains class definitions to implement a USB Audio device.

from USB import *
from USBDevice import *
from USBConfiguration import *
from USBInterface import *
from USBCSInterface import *
from USBEndpoint import *
from USBCSEndpoint import *


class USBAudioClass(USBClass):
    name = "USB Audio class"

    def __init__(self, maxusb_app):

        self.maxusb_app = maxusb_app
        self.setup_request_handlers()


    def setup_request_handlers(self):
        self.request_handlers = {
            0x0a : self.handle_set_idle,
            0x83 : self.handle_get_max,
            0x82 : self.handle_get_min,
            0x84 : self.handle_get_res,
            0x81 : self.handle_get_cur,
            0x04 : self.handle_set_res,
            0x01 : self.handle_set_cur
        }

    def handle_get_max(self, req):
        response = b'\xf0\xff'
        self.maxusb_app.send_on_endpoint(0, response)
        self.supported()

    def handle_get_min(self, req):
        response = b'\xa0\xe0'
        self.maxusb_app.send_on_endpoint(0, response)
        self.supported()

    def handle_get_res(self, req):
        response = b'\x30\x00'
        self.maxusb_app.send_on_endpoint(0, response)
        self.supported()

    def handle_get_cur(self, req):
        response = b''
#        response = b'\x80\xfd'
        self.maxusb_app.send_on_endpoint(0, response)
        self.supported()

    def handle_set_res(self, req):
        response = b''
        self.maxusb_app.send_on_endpoint(0, response)
        self.supported()

    def handle_set_cur(self, req):
        response = b''
        self.maxusb_app.send_on_endpoint(0, response)
        self.supported()

    def handle_set_idle(self, req):
        self.maxusb_app.send_on_endpoint(0, b'')
        self.supported()

    def supported(self):
        if self.maxusb_app.mode == 1:
            print (" **SUPPORTED**",end="")
            if self.maxusb_app.fplog:
                self.maxusb_app.fplog.write (" **SUPPORTED**\n")
            self.maxusb_app.stop = True


class USBAudioInterface(USBInterface):
    name = "USB audio interface"

    hid_descriptor = b'\x09\x21\x10\x01\x00\x01\x22\x2b\x00'
    report_descriptor = b'\x05\x0C\x09\x01\xA1\x01\x15\x00\x25\x01\x09\xE9\x09\xEA\x75\x01\x95\x02\x81\x02\x09\xE2\x09\x00\x81\x06\x05\x0B\x09\x20\x95\x01\x81\x42\x05\x0C\x09\x00\x95\x03\x81\x02\x26\xFF\x00\x09\x00\x75\x08\x95\x03\x81\x02\x09\x00\x95\x04\x91\x02\xC0'


    def __init__(self, int_num, maxusb_app, usbclass, sub, proto, verbose=0):

        self.maxusb_app = maxusb_app
        self.int_num = int_num

        descriptors = { 
                USB.desc_type_hid    : self.hid_descriptor,
                USB.desc_type_report : self.report_descriptor
        }

        if self.maxusb_app.testcase[1] == "CSInterface1_wTotalLength":
            wTotalLength = self.maxusb_app.testcase[2]
        else:
            wTotalLength = 0x0047
        if self.maxusb_app.testcase[1] == "CSInterface1_bInCollection":
            bInCollection = self.maxusb_app.testcase[2]
        else:
            bInCollection = 0x02
        if self.maxusb_app.testcase[1] == "CSInterface1_baInterfaceNr1":
            baInterfaceNr1 = self.maxusb_app.testcase[2]
        else:
            baInterfaceNr1 = 0x01
        if self.maxusb_app.testcase[1] == "CSInterface1_baInterfaceNr2":
            baInterfaceNr2 = self.maxusb_app.testcase[2]
        else:
            baInterfaceNr2 = 0x02

        cs_config1 = [
            0x01,           # HEADER
            0x0001,         # bcdADC
            wTotalLength,   # wTotalLength
            bInCollection,  # bInCollection
            baInterfaceNr1, # baInterfaceNr1
            baInterfaceNr2  # baInterfaceNr2
        ]

        if self.maxusb_app.testcase[1] == "CSInterface2_bTerminalID":
            bTerminalID = self.maxusb_app.testcase[2]
        else:
            bTerminalID = 0x01
        if self.maxusb_app.testcase[1] == "CSInterface2_wTerminalType":
            wTerminalType = self.maxusb_app.testcase[2]
        else:
            wTerminalType = 0x0101
        if self.maxusb_app.testcase[1] == "CSInterface2_bAssocTerminal":
            bAssocTerminal = self.maxusb_app.testcase[2]
        else:
            bAssocTerminal = 0x0
        if self.maxusb_app.testcase[1] == "CSInterface2_bNrChannel":
            bNrChannel = self.maxusb_app.testcase[2]
        else:
            bNrChannel = 0x02
        if self.maxusb_app.testcase[1] == "CSInterface2_wChannelConfig":
            wChannelConfig = self.maxusb_app.testcase[2]
        else:
            wChannelConfig = 0x0002

        cs_config2 = [
            0x02,           # INPUT_TERMINAL
            bTerminalID,    # bTerminalID
            wTerminalType,  # wTerminalType
            bAssocTerminal, # bAssocTerminal    
            bNrChannel,     # bNrChannel
            wChannelConfig, # wChannelConfig
            0,          # iChannelNames
            0           # iTerminal
        ]

        cs_config3 = [
            0x02,       # INPUT_TERMINAL
            0x02,       # bTerminalID
            0x0201,     # wTerminalType
            0,          # bAssocTerminal
            0x01,       # bNrChannel
            0x0001,     # wChannelConfig
            0,          # iChannelNames
            0           # iTerminal
        ]

        if self.maxusb_app.testcase[1] == "CSInterface4_bSourceID":
            bSourceID = self.maxusb_app.testcase[2]
        else:
            bSourceID = 0x09

        cs_config4 = [
            0x03,       # OUTPUT_TERMINAL
            0x06,       # bTerminalID
            0x0301,     # wTerminalType
            0,          # bAssocTerminal
            bSourceID,  # bSourceID
            0           # iTerminal
        ]

        cs_config5 = [
            0x03,       # OUTPUT_TERMINAL
            0x07,       # bTerminalID
            0x0101,     # wTerminalType
            0,          # bAssocTerminal
            0x0a,       # bSourceID
            0           # iTerminal
        ]

        if self.maxusb_app.testcase[1] == "CSInterface6_bUnitID":
            bUnitID = self.maxusb_app.testcase[2]
        else:
            bUnitID = 0x09
        if self.maxusb_app.testcase[1] == "CSInterface6_bSourceID":
            bSourceID = self.maxusb_app.testcase[2]
        else:
            bSourceID = 0x01
        if self.maxusb_app.testcase[1] == "CSInterface6_bControlSize":
            bControlSize = self.maxusb_app.testcase[2]
        else:
            bControlSize = 0x01
        if self.maxusb_app.testcase[1] == "CSInterface6_bmaControls0":
            bmaControls0 = self.maxusb_app.testcase[2]
        else:
            bmaControls0 = 0x01
        if self.maxusb_app.testcase[1] == "CSInterface6_bmaControls1":
            bmaControls1 = self.maxusb_app.testcase[2]
        else:
            bmaControls1 = 0x02
        if self.maxusb_app.testcase[1] == "CSInterface6_bmaControls2":
            bmaControls2 = self.maxusb_app.testcase[2]
        else:
            bmaControls2 = 0x02

        cs_config6 = [
            0x06,           # FEATURE_UNIT
            bUnitID,        # bUnitID
            bSourceID,      # bSourceID
            bControlSize,   # bControlSize
            bmaControls0,   # bmaControls0
            bmaControls1,   # bmaControls1
            bmaControls2,   # bmaControls2
            0               # iFeature
        ]

        cs_config7 = [
            0x06,       # FEATURE_UNIT
            0x0a,       # bUnitID
            0x02,       # bSourceID
            0x01,       # bControlSize
            0x43,       # bmaControls0
            0x00,       # bmaControls1
            0x00,       # bmaControls2
            0           # iFeature
        ]

        cs_interfaces0 = [
            USBCSInterface (
                maxusb_app,
                cs_config1,
                1,
                1,
                0
            ),
            USBCSInterface (
                maxusb_app,
                cs_config2,
                1,
                1,
                0
            ),
            USBCSInterface (
                maxusb_app,
                cs_config3,
                1,
                1,
                0
            ),
            USBCSInterface (
                maxusb_app,
                cs_config4,
                1,
                1,
                0
            ),
            USBCSInterface (
                maxusb_app,
                cs_config5,
                1,
                1,
                0
            ),
            USBCSInterface (
                maxusb_app,
                cs_config6,
                1,
                1,
                0
            ),
            USBCSInterface (
                maxusb_app,
                cs_config7,
                1,
                1,
                0
            )

        ]

#        cs_config8 = [
#            0x01,       # AS_GENERAL
#            0x01,       # bTerminalLink
#            0x01,       # bDelay
#            0x0001      # wFormatTag
#        ]

#        cs_config9 = [
#            0x02,       # FORMAT_TYPE
#            0x01,       # bFormatType
#            0x02,       # bNrChannels
#            0x02,       # bSubframeSize
#            0x10,       # bBitResolution
#            0x02,       # SamFreqType
#            0x80bb00,    # tSamFreq1
#            0x44ac00    # tSamFreq2
#        ]

        cs_interfaces1 = []
        cs_interfaces2 = []
        cs_interfaces3 = []

#        ep_cs_config1 = [
#            0x01,       # EP_GENERAL
#            0x01,       # Endpoint number
#            0x01,       # bmAttributes
#            0x01,       # bLockDelayUnits
#            0x0001,     # wLockeDelay
#        ]

        endpoints0 = [
            USBEndpoint(
                maxusb_app,
                1,           # endpoint address
                USBEndpoint.direction_in,
                USBEndpoint.transfer_type_interrupt,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                0x0400,         # max packet size
                0x02,           # polling interval, see USB 2.0 spec Table 9-13
                self.handle_data_available    # handler function
            )
        ]

        if self.int_num == 3:
                endpoints = endpoints0
        else:
                endpoints = []

        if self.int_num == 0:
                cs_interfaces = cs_interfaces0
        if self.int_num == 1:
                cs_interfaces = cs_interfaces1
        if self.int_num == 2:
                cs_interfaces = cs_interfaces2
        if self.int_num == 3:
                cs_interfaces = cs_interfaces3




#        if self.int_num == 1:
#                endpoints = endpoints1


        # TODO: un-hardcode string index (last arg before "verbose")
        USBInterface.__init__(
                self,
                maxusb_app,
                self.int_num,          # interface number
                0,          # alternate setting
                usbclass,          # 3 interface class
                sub,          # 0 subclass
                proto,          # 0 protocol
                0,          # string index
                verbose,
                endpoints,
                descriptors,
                cs_interfaces
        )

        self.device_class = USBAudioClass(maxusb_app)
        self.device_class.set_interface(self)


    def handle_data_available(self, data):
        if self.verbose > 0:
            print(self.name, "handling", len(data), "bytes of audio data")
    



class USBAudioDevice(USBDevice):
    name = "USB audio device"

    def __init__(self, maxusb_app, vid, pid, rev, verbose=0):

        int_class = 1
        int_subclass = 1
        int_proto = 0
        interface0 = USBAudioInterface(0, maxusb_app, 0x01, 0x01, 0x00,verbose=verbose)
        interface1 = USBAudioInterface(1, maxusb_app, 0x01, 0x02, 0x00,verbose=verbose)
        interface2 = USBAudioInterface(2, maxusb_app, 0x01, 0x02, 0x00,verbose=verbose)
        interface3 = USBAudioInterface(3, maxusb_app, 0x03, 0x00, 0x00,verbose=verbose)

        if vid == 0x1111:
            vid = 0x041e
        if pid == 0x2222:
            pid = 0x0402
        if rev == 0x3333:
            rev = 0x0100

        config = USBConfiguration(
                maxusb_app,
                1,                                          # index
                "Emulated Audio",    # string desc
                [ interface0, interface1, interface2, interface3 ]                  # interfaces
        )

        USBDevice.__init__(
                self,
                maxusb_app,
                0,                      # 0 device class
		        0,                      # device subclass
                0,                      # protocol release number
                64,                     # max packet size for endpoint 0
		        vid,                 # vendor id
                pid,                 # product id
		        rev,                 # device revision
                "Creative Technology Ltd.",                # manufacturer string
                "Creative HS-720 Headset",   # product string
                "",             # serial number string
                [ config ],
                verbose=verbose
        )


########NEW FILE########
__FILENAME__ = USBCDC
# USBCDC.py
#
# Contains class definitions to implement a USB CDC device.

from USB import *
from USBDevice import *
from USBConfiguration import *
from USBInterface import *
from USBCSInterface import *
from USBEndpoint import *
from USBCSEndpoint import *


class USBCDCClass(USBClass):
    name = "USB CDC class"

    def __init__(self, maxusb_app):

        self.maxusb_app = maxusb_app
        self.setup_request_handlers()

    def setup_request_handlers(self):
        self.request_handlers = {
            0x22 : self.handle_set_control_line_state,
            0x20 : self.handle_set_line_coding
        }

    def handle_set_control_line_state(self, req):
        self.maxusb_app.send_on_endpoint(0, b'')
        if self.maxusb_app.mode == 1:
            print (" **SUPPORTED**",end="")
            if self.maxusb_app.fplog:
                self.maxusb_app.fplog.write (" **SUPPORTED**\n")
            self.maxusb_app.stop = True

    def handle_set_line_coding(self, req):
        self.maxusb_app.send_on_endpoint(0, b'')



class USBCDCInterface(USBInterface):
    name = "USB CDC interface"

    def __init__(self, int_num, maxusb_app, usbclass, sub, proto, verbose=0):

        self.maxusb_app = maxusb_app
        self.int_num = int_num

        descriptors = { }

        cs_config1 = [
            0x00,           # Header Functional Descriptor
            0x1001,         # bcdCDC
        ]

        bmCapabilities = 0x03
        bDataInterface = 0x01

        cs_config2 = [
            0x01,           # Call Management Functional Descriptor
            bmCapabilities,
            bDataInterface
        ]

        bmCapabilities = 0x06

        cs_config3 = [
            0x02,           # Abstract Control Management Functional Descriptor
            bmCapabilities
        ]

        bControlInterface = 0
        bSubordinateInterface0 = 1

        cs_config4 = [
            0x06,       # Union Functional Descriptor
            bControlInterface,
            bSubordinateInterface0
        ]

        cs_interfaces0 = [
            USBCSInterface (
                maxusb_app,
                cs_config1,
                2,
                2,
                1
            ),
            USBCSInterface (
                maxusb_app,
                cs_config2,
                2,
                2,
                1
            ),
            USBCSInterface (
                maxusb_app,
                cs_config3,
                2,
                2,
                1
            ),
            USBCSInterface (
                maxusb_app,
                cs_config4,
                2,
                2,
                1
            )

        ]


        cs_interfaces1 = []

        endpoints0 = [
            USBEndpoint(
                maxusb_app,
                0x83,           # endpoint address
                USBEndpoint.direction_in,
                USBEndpoint.transfer_type_interrupt,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                0x2000,         # max packet size
                0xff,           # polling interval, see USB 2.0 spec Table 9-13
                #self.handle_data_available    # handler function
                None
            )
        ]


        endpoints1 = [
            USBEndpoint(
                maxusb_app,
                0x81,           # endpoint address
                USBEndpoint.direction_in,
                USBEndpoint.transfer_type_bulk,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                0x2000,         # max packet size
                0x00,           # polling interval, see USB 2.0 spec Table 9-13
                #self.handle_data_available    # handler function
                None
            ),
            USBEndpoint(
                maxusb_app,
                0x02,           # endpoint address
                USBEndpoint.direction_out,
                USBEndpoint.transfer_type_bulk,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                0x2000,         # max packet size
                0x00,           # polling interval, see USB 2.0 spec Table 9-13
                self.handle_data_available    # handler function
            )
        ]

        if self.int_num == 0:
                endpoints = endpoints0
                cs_interfaces = cs_interfaces0

        elif self.int_num == 1:
                endpoints = endpoints1
                cs_interfaces = cs_interfaces1




        # TODO: un-hardcode string index (last arg before "verbose")
        USBInterface.__init__(
                self,
                maxusb_app,
                self.int_num,          # interface number
                0,          # alternate setting
                usbclass,          # 3 interface class
                sub,          # 0 subclass
                proto,          # 0 protocol
                0,          # string index
                verbose,
                endpoints,
                descriptors,
                cs_interfaces
        )

        self.device_class = USBCDCClass(maxusb_app)
        self.device_class.set_interface(self)


    def handle_data_available(self, data):
        if self.verbose > 0:
            print(self.name, "handling", len(data), "bytes of audio data")
    



class USBCDCDevice(USBDevice):
    name = "USB CDC device"

    def __init__(self, maxusb_app, vid, pid, rev, verbose=0):

        int_class = 2
        int_subclass = 0
        int_proto = 0
        interface0 = USBCDCInterface(0, maxusb_app, 0x02, 0x02, 0x01,verbose=verbose)
        interface1 = USBCDCInterface(1, maxusb_app, 0x0a, 0x00, 0x00,verbose=verbose)

        if vid == 0x1111:
            vid = 0x2548
        if pid == 0x2222:
            pid = 0x1001
        if rev == 0x3333:
            rev = 0x1000


        config = USBConfiguration(
                maxusb_app,
                1,                          # index
                "Emulated CDC",             # string desc
                [ interface0, interface1 ]  # interfaces
        )


        USBDevice.__init__(
                self,
                maxusb_app,
                2,                      # 0 device class
		        0,                      # device subclass
                0,                      # protocol release number
                64,                     # max packet size for endpoint 0
		        vid,                 # vendor id
                pid,                 # product id
		        rev,                 # device revision
                "Vendor",               # manufacturer string
                "Product",              # product string
                "Serial",               # serial number string
                [ config ],
                verbose=verbose
        )


########NEW FILE########
__FILENAME__ = USBCDC2
# USBCDC.py
#
# Contains class definitions to implement a USB CDC device.

from USB import *
from USBDevice import *
from USBConfiguration import *
from USBInterface import *
from USBCSInterface import *
from USBEndpoint import *
from USBCSEndpoint import *


class USBCDCClass(USBClass):
    name = "USB CDC class"

    def __init__(self, maxusb_app):

        self.maxusb_app = maxusb_app
        self.setup_request_handlers()

    def setup_request_handlers(self):
        self.request_handlers = {
            0x00 : self.handle_send_encapsulated_command,
            0x01 : self.handle_get_encapsulated_response,
            0x22 : self.handle_set_control_line_state,
            0x20 : self.handle_set_line_coding
        }

    def handle_set_control_line_state(self, req):
        self.maxusb_app.send_on_endpoint(0, b'')
        if self.maxusb_app.mode == 1:
            print (" **SUPPORTED**",end="")
            if self.maxusb_app.fplog:
                self.maxusb_app.fplog.write (" **SUPPORTED**\n")
            self.maxusb_app.stop = True

    def handle_set_line_coding(self, req):
        self.maxusb_app.send_on_endpoint(0, b'')

    def handle_send_encapsulated_command(self, req):
        self.maxusb_app.send_on_endpoint(0, b'')

    def handle_get_encapsulated_response(self, req):
        self.maxusb_app.send_on_endpoint(0, b'')





class USBCDCInterface(USBInterface):
    name = "USB CDC interface"

    def __init__(self, int_num, maxusb_app, usbclass, sub, proto, verbose=0):


        self.maxusb_app = maxusb_app
        self.int_num = int_num

        descriptors = { }

        cs_config1 = [
            0x00,           # Header Functional Descriptor
            0x1001,         # bcdCDC
        ]

        bmCapabilities = 0x00
        bDataInterface = 0x01

        cs_config2 = [
            0x01,           # Call Management Functional Descriptor
            bmCapabilities,
            bDataInterface
        ]

        bmCapabilities = 0x00

        cs_config3 = [
            0x02,           # Abstract Control Management Functional Descriptor
            bmCapabilities
        ]

        bControlInterface = 0
        bSubordinateInterface0 = 1

        cs_config4 = [
            0x06,       # Union Functional Descriptor
            bControlInterface,
            bSubordinateInterface0
        ]

        cs_interfaces0 = [
            USBCSInterface (
                maxusb_app,
                cs_config1,
                2,
                2,
                0xff
            ),
            USBCSInterface (
                maxusb_app,
                cs_config2,
                2,
                2,
                0xff
            ),
            USBCSInterface (
                maxusb_app,
                cs_config3,
                2,
                2,
                0xff
            ),
            USBCSInterface (
                maxusb_app,
                cs_config4,
                2,
                2,
                0xff
            )

        ]


        cs_interfaces1 = []




        cs_config5 = [
            0x00,           # Header Functional Descriptor
            0x1001,         # bcdCDC
        ]


        bControlInterface = 0
        bSubordinateInterface0 = 1

        cs_config6 = [
            0x06,       # Union Functional Descriptor
            bControlInterface,
            bSubordinateInterface0
        ]





#        iMACAddress = self.get_string_id("020406080a0c")
        iMACAddress = 0
        bmEthernetStatistics = 0x00000000
        wMaxSegmentSize = 0xea05
        wNumberMCFilters = 0x0000
        bNumberPowerFilters = 0x00

        cs_config7 = [
            0x0f,       # Ethernet Networking Functional Descriptor
            iMACAddress,
            bmEthernetStatistics,
            wMaxSegmentSize,
            wNumberMCFilters,
            bNumberPowerFilters            
        ]

        cs_interfaces2 = [
            USBCSInterface (
                maxusb_app,
                cs_config5,
                2,
                6,
                0
            ),
            USBCSInterface (
                maxusb_app,
                cs_config6,
                2,
                6,
                0
            ),
            USBCSInterface (
                maxusb_app,
                cs_config7,
                2,
                6,
                0
            )

        ]

        cs_interfaces3 = []






        endpoints0 = [
            USBEndpoint(
                maxusb_app,
                3,           # endpoint address
                USBEndpoint.direction_in,
                USBEndpoint.transfer_type_interrupt,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                0x0800,         # max packet size
                0x09,           # polling interval, see USB 2.0 spec Table 9-13
                self.handle_data_available    # handler function
            )
        ]


        endpoints1 = [
            USBEndpoint(
                maxusb_app,
                3,           # endpoint address
                USBEndpoint.direction_in,
                USBEndpoint.transfer_type_bulk,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                0x0002,         # max packet size
                0x00,           # polling interval, see USB 2.0 spec Table 9-13
                self.handle_data_available    # handler function
            ),
            USBEndpoint(
                maxusb_app,
                1,           # endpoint address
                USBEndpoint.direction_out,
                USBEndpoint.transfer_type_bulk,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                0x0002,         # max packet size
                0x00,           # polling interval, see USB 2.0 spec Table 9-13
                self.handle_data_available    # handler function
            )
        ]


        endpoints2 = [
            USBEndpoint(
                maxusb_app,
                3,           # 2 endpoint address
                USBEndpoint.direction_in,
                USBEndpoint.transfer_type_interrupt,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                0x1000,         # max packet size
                0x09,           # polling interval, see USB 2.0 spec Table 9-13
                self.handle_data_available    # handler function
            )
        ]


        endpoints3 = [
            USBEndpoint(
                maxusb_app,
                3,           # 1 endpoint address
                USBEndpoint.direction_in,
                USBEndpoint.transfer_type_bulk,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                0x0002,         # max packet size
                0x00,           # polling interval, see USB 2.0 spec Table 9-13
                self.handle_data_available    # handler function
            ),
            USBEndpoint(
                maxusb_app,
                1,           # endpoint address
                USBEndpoint.direction_out,
                USBEndpoint.transfer_type_bulk,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                0x0002,         # max packet size
                0x00,           # polling interval, see USB 2.0 spec Table 9-13
                self.handle_data_available    # handler function
            )
        ]




        if self.int_num == 0:
                endpoints = endpoints0
                cs_interfaces = cs_interfaces0

        elif self.int_num == 1:
                endpoints = endpoints1
                cs_interfaces = cs_interfaces1

        elif self.int_num == 2:
                endpoints = endpoints2
                cs_interfaces = cs_interfaces2

        elif self.int_num == 3:
                endpoints = endpoints3
                cs_interfaces = cs_interfaces3


        if self.int_num == 2:   #Ugly hack
            self.int_num = 0

        if self.int_num == 3:
            self.int_num = 1




        # TODO: un-hardcode string index (last arg before "verbose")
        USBInterface.__init__(
                self,
                maxusb_app,
                self.int_num,          # interface number
                0,          # alternate setting
                usbclass,          # 3 interface class
                sub,          # 0 subclass
                proto,          # 0 protocol
                0,          # string index
                verbose,
                endpoints,
                descriptors,
                cs_interfaces
        )

        self.device_class = USBCDCClass(maxusb_app)
        self.device_class.set_interface(self)


    def handle_data_available(self):
        #print(self.name, "handling", len(data), "bytes of data")
        return



class USBCDCDevice(USBDevice):
    name = "USB CDC device"

    def __init__(self, maxusb_app, vid, pid, rev, verbose=0):

        interface0 = USBCDCInterface(0, maxusb_app, 0x02, 0x02, 0xff,verbose=verbose)
        interface1 = USBCDCInterface(1, maxusb_app, 0x0a, 0x00, 0x00,verbose=verbose)
        interface2 = USBCDCInterface(2, maxusb_app, 0x02, 0x06, 0x00,verbose=verbose)
        interface3 = USBCDCInterface(3, maxusb_app, 0x0a, 0x00, 0x00,verbose=verbose)

        if vid == 0x1111:
            vid = 0x1390
        if pid == 0x2222:
            pid = 0x5454
        if rev == 0x3333:
            rev = 0x0327


        config = [
            USBConfiguration(
                maxusb_app,
                2,                          # index
                "CDC Ethernet Control Module (ECM)",             # string desc
                [ interface0, interface1 ]  # interfaces
            ),
            USBConfiguration(
                maxusb_app,
                1,                          # index
                "Emulated CDC - ACM",             # string desc
                [ interface2, interface3 ]  # interfaces
            )
        ]



        USBDevice.__init__(
                self,
                maxusb_app,
                2,                      # 0 device class
		        0,                      # device subclass
                0,                      # protocol release number
                64,                     # max packet size for endpoint 0
		        vid,                 # vendor id
                pid,                 # product id
		        rev,                 # device revision
                "TOMTOM B.V.",               # manufacturer string
                "TomTom",              # product string
                "TA6380K10346",               # serial number string
                config,
                verbose=verbose
        )


########NEW FILE########
__FILENAME__ = USBFtdi
# USBFtdi.py
#
# Contains class definitions to implement a USB FTDI chip.

from USB import *
from USBDevice import *
from USBConfiguration import *
from USBInterface import *
from USBEndpoint import *
from USBVendor import *

from util import *

class USBFtdiVendor(USBVendor):
    name = "USB FTDI vendor"

    def setup_request_handlers(self):
        self.request_handlers = {
             0 : self.handle_reset_request,
             1 : self.handle_modem_ctrl_request,
             2 : self.handle_set_flow_ctrl_request,
             3 : self.handle_set_baud_rate_request,
             4 : self.handle_set_data_request,
             5 : self.handle_get_status_request,
             6 : self.handle_set_event_char_request,
             7 : self.handle_set_error_char_request,
             9 : self.handle_set_latency_timer_request,
            10 : self.handle_get_latency_timer_request
        }

    def handle_reset_request(self, req):
        if self.verbose > 0:
            print(self.name, "received reset request")

        self.device.maxusb_app.send_on_endpoint(0, b'')

    def handle_modem_ctrl_request(self, req):
        if self.verbose > 0:
            print(self.name, "received modem_ctrl request")

        dtr = req.value & 0x0001
        rts = (req.value & 0x0002) >> 1
        dtren = (req.value & 0x0100) >> 8
        rtsen = (req.value & 0x0200) >> 9

        if dtren:
            print("DTR is enabled, value", dtr)
        if rtsen:
            print("RTS is enabled, value", rts)

        self.device.maxusb_app.send_on_endpoint(0, b'')

    def handle_set_flow_ctrl_request(self, req):
        if self.verbose > 0:
            print(self.name, "received set_flow_ctrl request")

        if req.value == 0x000:
            print("SET_FLOW_CTRL to no handshaking")
        if req.value & 0x0001:
            print("SET_FLOW_CTRL for RTS/CTS handshaking")
        if req.value & 0x0002:
            print("SET_FLOW_CTRL for DTR/DSR handshaking")
        if req.value & 0x0004:
            print("SET_FLOW_CTRL for XON/XOFF handshaking")

        self.device.maxusb_app.send_on_endpoint(0, b'')

    def handle_set_baud_rate_request(self, req):
        if self.verbose > 0:
            print(self.name, "received set_baud_rate request")

        dtr = req.value & 0x0001
        print("baud rate set to", dtr)

        self.device.maxusb_app.send_on_endpoint(0, b'')

    def handle_set_data_request(self, req):
        if self.verbose > 0:
            print(self.name, "received set_data request")

        self.device.maxusb_app.send_on_endpoint(0, b'')

    def handle_get_status_request(self, req):
        if self.verbose > 0:
            print(self.name, "received get_status request")

        self.device.maxusb_app.send_on_endpoint(0, b'')

    def handle_set_event_char_request(self, req):
        if self.verbose > 0:
            print(self.name, "received set_event_char request")

        self.device.maxusb_app.send_on_endpoint(0, b'')

    def handle_set_error_char_request(self, req):
        if self.verbose > 0:
            print(self.name, "received set_error_char request")

        self.device.maxusb_app.send_on_endpoint(0, b'')

    def handle_set_latency_timer_request(self, req):
        if self.verbose > 0:
            print(self.name, "received set_latency_timer request")

        self.device.maxusb_app.send_on_endpoint(0, b'')

    def handle_get_latency_timer_request(self, req):
        if self.verbose > 0:
            print(self.name, "received get_latency_timer request")

        # bullshit value
        self.device.maxusb_app.send_on_endpoint(0, b'\x01')


class USBFtdiInterface(USBInterface):
    name = "USB FTDI interface"

    def __init__(self, verbose=0):
        descriptors = { }

        endpoints = [
            USBEndpoint(
                1,          # endpoint number
                USBEndpoint.direction_out,
                USBEndpoint.transfer_type_bulk,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                16384,      # max packet size
                0,          # polling interval, see USB 2.0 spec Table 9-13
                self.handle_data_available      # handler function
            ),
            USBEndpoint(
                3,          # endpoint number
                USBEndpoint.direction_in,
                USBEndpoint.transfer_type_bulk,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                16384,      # max packet size
                0,          # polling interval, see USB 2.0 spec Table 9-13
                None        # handler function
            )
        ]

        # TODO: un-hardcode string index (last arg before "verbose")
        USBInterface.__init__(
                self,
                0,          # interface number
                0,          # alternate setting
                0xff,       # interface class: vendor-specific
                0xff,       # subclass: vendor-specific
                0xff,       # protocol: vendor-specific
                0,          # string index
                verbose,
                endpoints,
                descriptors
        )

    def handle_data_available(self, data):
        s = data[1:]
        if self.verbose > 0:
            print(self.name, "received string", s)

        s = s.replace(b'\r', b'\r\n')

        reply = b'\x01\x00' + s

        self.configuration.device.maxusb_app.send_on_endpoint(3, reply)


class USBFtdiDevice(USBDevice):
    name = "USB FTDI device"

    def __init__(self, maxusb_app, verbose=0):
        interface = USBFtdiInterface(verbose=verbose)

        config = USBConfiguration(
                1,                                          # index
                "FTDI config",                              # string desc
                [ interface ]                               # interfaces
        )

        USBDevice.__init__(
                self,
                maxusb_app,
                0,                      # device class
                0,                      # device subclass
                0,                      # protocol release number
                64,                     # max packet size for endpoint 0
                0x0403,                 # 0403 vendor id: FTDI
                0x6001,                 # 6001 product id: FT232 USB-Serial (UART) IC
                0x0001,                 # 0001 device revision
                "GoodFET",              # manufacturer string
                "FTDI Emulator",        # product string
                "S/N3420E",             # serial number string
                [ config ],
                verbose=verbose
        )

        self.device_vendor = USBFtdiVendor()
        self.device_vendor.set_device(self)


########NEW FILE########
__FILENAME__ = USBHub
# USBHub.py
#
# Contains class definitions to implement a USB hub.

from USB import *
from USBDevice import *
from USBConfiguration import *
from USBInterface import *
from USBEndpoint import *

class USBHubClass(USBClass):
    name = "USB hub class"

    def __init__(self, maxusb_app):

        self.maxusb_app = maxusb_app
        self.setup_request_handlers()

    def setup_request_handlers(self):
        self.request_handlers = {
            0x00 : self.handle_get_hub_status_request,
            0x03 : self.handle_set_port_feature_request

        }

    def handle_get_hub_status_request(self, req):
        if self.maxusb_app.mode == 1:
            print (" **SUPPORTED**",end="")
            if self.maxusb_app.fplog:
                self.maxusb_app.fplog.write (" **SUPPORTED**\n")
            self.maxusb_app.stop = True
        else:

            response = b'\x61\x61\x61\x61'
            self.maxusb_app.send_on_endpoint(0, response)
            self.maxusb_app.stop = True

        
    def handle_set_port_feature_request(self, req):
#        print ("DEBUG: Set port feature request")
        response = b''
        self.maxusb_app.send_on_endpoint(0, response)



class USBHubInterface(USBInterface):
    name = "USB hub interface"

    def __init__(self, maxusb_app, verbose=0):
        self.maxusb_app = maxusb_app


        if self.maxusb_app.testcase[1] == "hub_bLength":
            bLength = self.maxusb_app.testcase[2]
        else:
            bLength = 9
        if self.maxusb_app.testcase[1] == "hub_bDescriptorType":
            bDescriptorType = self.maxusb_app.testcase[2]
        else:
            bDescriptorType = 0x29
        if self.maxusb_app.testcase[1] == "hub_bNbrPorts":
            bNbrPorts = self.maxusb_app.testcase[2]
        else:
            bNbrPorts = 4
        if self.maxusb_app.testcase[1] == "hub_wHubCharacteristics":
            wHubCharacteristics = self.maxusb_app.testcase[2]
        else:
            wHubCharacteristics = 0xe000
        if self.maxusb_app.testcase[1] == "hub_bPwrOn2PwrGood":
            bPwrOn2PwrGood = self.maxusb_app.testcase[2]
        else:
            bPwrOn2PwrGood = 0x32
        if self.maxusb_app.testcase[1] == "hub_bHubContrCurrent":
            bHubContrCurrent = self.maxusb_app.testcase[2]
        else:
            bHubContrCurrent = 0x64
        if self.maxusb_app.testcase[1] == "hub_DeviceRemovable":
            DeviceRemovable = self.maxusb_app.testcase[2]
        else:
            DeviceRemovable = 0
        if self.maxusb_app.testcase[1] == "hub_PortPwrCtrlMask":
            PortPwrCtrlMask = self.maxusb_app.testcase[2]
        else:
            PortPwrCtrlMask = 0xff

        hub_descriptor = bytes([
                bLength,                        # length of descriptor in bytes
                bDescriptorType,                # descriptor type 0x29 == hub
                bNbrPorts,                      # number of physical ports
                wHubCharacteristics & 0xff ,    # hub characteristics
                (wHubCharacteristics >> 8) & 0xff,
                bPwrOn2PwrGood,                 # time from power on til power good
                bHubContrCurrent,               # max current required by hub controller
                DeviceRemovable,
                PortPwrCtrlMask
        ])



        descriptors = { 
                USB.desc_type_hub    : hub_descriptor
        }

        endpoint = USBEndpoint(
                maxusb_app,
                0x81,          # endpoint number
                USBEndpoint.direction_in,
                USBEndpoint.transfer_type_interrupt,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                16384,      # max packet size
                0x0c,         # polling interval, see USB 2.0 spec Table 9-13
                self.handle_buffer_available    # handler function
        )

        # TODO: un-hardcode string index (last arg before "verbose")
        USBInterface.__init__(
                self,
                maxusb_app,
                0,          # interface number
                0,          # alternate setting
                9,          # 3 interface class
                0,          # 0 subclass
                0,          # 0 protocol
                0,          # string index
                verbose,
                [ endpoint ],
                descriptors
        )

        self.device_class = USBHubClass(maxusb_app)
        self.device_class.set_interface(self)


    def handle_buffer_available(self):

#        print ("DEBUG: handle_buffer_available")
        return


class USBHubDevice(USBDevice):
    name = "USB hub device"

    def __init__(self, maxusb_app, vid, pid, rev, verbose=0):


        interface = USBHubInterface(maxusb_app, verbose=verbose)

        if vid == 0x1111:
            vid = 0x05e3
        if pid == 0x2222:
            pid = 0x0608
        if rev == 0x3333:
            rev = 0x7764


        config = USBConfiguration(
                maxusb_app,
                1,                                          # index
                "Emulated Hub",    # string desc
                [ interface ]                  # interfaces
        )

        USBDevice.__init__(
                self,
                maxusb_app,
                9,                      # 0 device class
		        0,                      # device subclass
                1,                      # protocol release number
                64,                     # max packet size for endpoint 0
		        vid,                    # vendor id
                pid,                    # product id
		        rev,                    # device revision
                "Genesys Logic, Inc",   # manufacturer string
                "USB2.0 Hub",           # product string
                "1234",                 # serial number string
                [ config ],
                verbose=verbose
        )



########NEW FILE########
__FILENAME__ = USBImage
# USBImage.py 
#
# Contains class definitions to implement a USB image device.

from mmap import mmap
import os

from USB import *
from USBDevice import *
from USBConfiguration import *
from USBInterface import *
from USBEndpoint import *
from USBClass import *

from util import *

class USBImageClass(USBClass):
    name = "USB image class"

    def setup_request_handlers(self):
        self.request_handlers = {
            0x66 : self.handle_device_reset_request,
        }

    def handle_device_reset_request(self, req):
        self.interface.configuration.device.maxusb_app.send_on_endpoint(0, b'')



class USBImageInterface(USBInterface):
    name = "USB image interface"

    def __init__(self, int_num, maxusb_app, thumb_image, partial_image, usbclass, sub, proto, verbose=0):
        self.thumb_image = thumb_image
        self.partial_image = partial_image
        self.maxusb_app = maxusb_app
        self.int_num = int_num
        descriptors = { }

        endpoints = [
            USBEndpoint(
                maxusb_app,
                1,          # endpoint address
                USBEndpoint.direction_out,
                USBEndpoint.transfer_type_bulk,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                0x4000,      # max packet size
                0x00,          # polling interval, see USB 2.0 spec Table 9-13
                self.handle_data_available    # handler function
            ),
            USBEndpoint(
                maxusb_app,
                0x82,          # endpoint address
                USBEndpoint.direction_in,
                USBEndpoint.transfer_type_bulk,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                0x4000,      # max packet size
                0,          # polling interval, see USB 2.0 spec Table 9-13
                self.handle_data_available    # handler function
                #None        # handler function
            ),
            USBEndpoint(
                maxusb_app,
                0x83,          # endpoint address
                USBEndpoint.direction_in,
                USBEndpoint.transfer_type_interrupt,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                0x0800,      # max packet size
                0x10,          # polling interval, see USB 2.0 spec Table 9-13
                #None        # handler function
                self.handle_data_available    # handler function

            )


        ]


        # TODO: un-hardcode string index (last arg before "verbose")
        USBInterface.__init__(
                self,
                maxusb_app,
                self.int_num,          # interface number
                0,          # alternate setting
                usbclass,          # interface class
                sub,          # subclass
                proto,       # protocol
                0,          # string index
                verbose,
                endpoints,
                descriptors
        )

        self.device_class = USBImageClass()
        self.device_class.set_interface(self)


    def create_send_ok (self, transaction_id):

        if self.verbose > 0:
            print(self.name, "sent Image:OK")


        container_type = b'\x00\x03' # Response block
        response_code = b'\x20\x01'  # "OK"
        container_length = b'\x00\x00\x00\x0c' # always this length

        response = change_byte_order(container_length) + \
                   change_byte_order(container_type) + \
                   change_byte_order(response_code) + \
                   change_byte_order(transaction_id)

        return response

    def handle_data_available(self, data):
        if self.verbose > 0:
            print(self.name, "handling", len(data), "bytes of Image class data")

        if self.maxusb_app.mode == 1:
            print (" **SUPPORTED**",end="")
            if self.maxusb_app.fplog:
                self.maxusb_app.fplog.write (" **SUPPORTED**\n")
            self.maxusb_app.stop = True

        container = ContainerRequestWrapper(data)
        opcode = container.operation_code[1] << 8 | container.operation_code[0] 
        container_type = container.container_type[1] << 8 | \
                        container.container_type[0] 
        
        #print ("DEBUG: container type:", container_type) 


        if self.maxusb_app.testcase[1] == "DeviceInfo_TransactionID":
            transaction_id = change_byte_order(self.maxusb_app.testcase[2])
        elif self.maxusb_app.testcase[1] == "StorageIDArray_TransactionID":
            transaction_id = change_byte_order(self.maxusb_app.testcase[2])
        elif self.maxusb_app.testcase[1] == "StorageInfo_TransactionID":
            transaction_id = change_byte_order(self.maxusb_app.testcase[2])
        elif self.maxusb_app.testcase[1] == "ObjectHandles_TransactionID":
            transaction_id = change_byte_order(self.maxusb_app.testcase[2])
        elif self.maxusb_app.testcase[1] == "ObjectInfo_TransactionID":
            transaction_id = change_byte_order(self.maxusb_app.testcase[2])
        elif self.maxusb_app.testcase[1] == "ThumbData_TransactionID":
            transaction_id = change_byte_order(self.maxusb_app.testcase[2])
        elif self.maxusb_app.testcase[1] == "PartialData_TransactionID":
            transaction_id = change_byte_order(self.maxusb_app.testcase[2])
        else:
            transaction_id = bytes ([container.transaction_id[3], \
                                     container.transaction_id[2], \
                                     container.transaction_id[1], \
                                     container.transaction_id[0]]) 

        status = 0              # default to success
        response = None         # with no response data
        response2 = None

        if self.maxusb_app.server_running == True:
            try:
                self.maxusb_app.netserver_from_endpoint_sd.send(data)
            except:
                print ("Error: No network client connected")
            while True:
                if len(self.maxusb_app.reply_buffer) > 0:
                    self.maxusb_app.send_on_endpoint(2, self.maxusb_app.reply_buffer)
                    self.maxusb_app.reply_buffer = ""
                    break



        elif opcode == 0x1002:      # OpenSession
            if self.verbose > 0:
                print(self.name, "got OpenSession")

            response = self.create_send_ok(transaction_id)




        elif opcode == 0x1016:      # SetDevicePropValue
            if self.verbose > 0:
                print(self.name, "got SetDevicePropValue")

            if container_type == 2: #Data block
                response = self.create_send_ok(transaction_id)



        elif opcode == 0x100a:      # GetThumb
            if self.verbose > 0:
                print(self.name, "got GetThumb")
            thumb_data = (self.thumb_image.read_data())

            if self.maxusb_app.testcase[1] == "ThumbData_ContainerType":
                container_type = change_byte_order(self.maxusb_app.testcase[2])
            else:
                container_type = b'\x00\x02' # Data block
            if self.maxusb_app.testcase[1] == "ThumbData_OperationCode":
                operation_code = change_byte_order(self.maxusb_app.testcase[2])
            else:
                operation_code = b'\x10\x0a' # GetThumb
                thumbnail_data_object = thumb_data

            response = change_byte_order(container_type) + \
                       change_byte_order(operation_code) + \
                       change_byte_order(transaction_id) 

            x = 0
            while x < len(thumbnail_data_object):
                response += bytes([thumbnail_data_object[x]])
                x+=1

            container_length = len(response) + 4


            if self.maxusb_app.testcase[1] == "ThumbData_ContainerLength":
                container_length_bytes = change_byte_order(self.maxusb_app.testcase[2])
            else:
                container_length_bytes = bytes([
                (container_length      ) & 0xff,
                (container_length >>  8) & 0xff,
                (container_length >> 16) & 0xff,
                (container_length >> 24) & 0xff])

            response = container_length_bytes + response
            response2 = self.create_send_ok(transaction_id)



        elif opcode == 0x101b:      # GetPartialObject
            if self.verbose > 0:
                print(self.name, "got GetPartialObject")


#            return
#            partial_data = (self.partial_image.read_data())

#            if self.maxusb_app.testcase[1] == "PartialObject_ContainerType":
#                container_type = change_byte_order(self.maxusb_app.testcase[2])
#            else:
#                container_type = b'\x00\x02' # Data block
#            if self.maxusb_app.testcase[1] == "PartialObject_OperationCode":
#                operation_code = change_byte_order(self.maxusb_app.testcase[2])
#            else:
#                operation_code = b'\x10\x1b' # GetPartialObject
#                data_object = partial_data
#
#            response = change_byte_order(container_type) + \
#                       change_byte_order(operation_code) + \
#                       change_byte_order(transaction_id)
#
#            x = 0
#            while x < len(data_object):
#                response += bytes([data_object[x]])
#                x+=1
#
#            container_length = len(response) + 4
#
#
#            if self.maxusb_app.testcase[1] == "PartialObject_ContainerLength":
#                container_length_bytes = change_byte_order(self.maxusb_app.testcase[2])
#            else:
#                container_length_bytes = bytes([
#                (container_length      ) & 0xff,
#                (container_length >>  8) & 0xff,
#                (container_length >> 16) & 0xff,
#                (container_length >> 24) & 0xff])

#            response = container_length_bytes + response
#            response2 = self.create_send_ok(transaction_id)






        elif opcode == 0x1001:      # GetDeviceInfo
            if self.verbose > 0:
                print(self.name, "got GetDeviceInfo")

            if self.maxusb_app.testcase[1] == "DeviceInfo_ContainerType":
                container_type = change_byte_order(self.maxusb_app.testcase[2])
            else:
                container_type = b'\x00\x02' # Data block
            
            if self.maxusb_app.testcase[1] == "DeviceInfo_OperationCode":
                operation_code = change_byte_order(self.maxusb_app.testcase[2])
            else:
                operation_code = b'\x10\x01' # GetDeviceInfo
            #transaction ID
            if self.maxusb_app.testcase[1] == "DeviceInfo_StandardVersion":
                standard_version = change_byte_order(self.maxusb_app.testcase[2])
            else:
                standard_version = b'\x00\x64' # version 1.0
            if self.maxusb_app.testcase[1] == "DeviceInfo_VendorExtensionID":
                vendor_extension_id = change_byte_order(self.maxusb_app.testcase[2])
            else:
                vendor_extension_id = b'\x00\x00\x00\x06' # Microsoft Corporation
            if self.maxusb_app.testcase[1] == "DeviceInfo_VendorExtensionVersion":
                vendor_extension_version = change_byte_order(self.maxusb_app.testcase[2])
            else:
                vendor_extension_version = b'\x00\x64' # version 1.0
            if self.maxusb_app.testcase[1] == "DeviceInfo_VendorExtensionDesc":
                vendor_extension_desc = change_byte_order(self.maxusb_app.testcase[2])
            else:
                vendor_extension_desc = b'\x00'
            if self.maxusb_app.testcase[1] == "DeviceInfo_FunctionalMode":
                functional_mode = change_byte_order(self.maxusb_app.testcase[2])
            else:
                functional_mode = b'\x00\x00' # standard mode
           
            if self.maxusb_app.testcase[1] == "DeviceInfo_OperationsSupportedArraySize":
                operations_supported_array_size = change_byte_order(self.maxusb_app.testcase[2])
            else:
                operations_supported_array_size = b'\x00\x00\x00\x10' # 16 operations supported
       
            if self.maxusb_app.testcase[1] == "DeviceInfo_OperationSupported":
                op1_supported = change_byte_order(self.maxusb_app.testcase[2])
            else:
                op1_supported = b'\x10\x01' # GetDeviceInfo
            op2_supported = b'\x10\x02' # OpenSession
            op3_supported = b'\x10\x03' # CloseSession
            op4_supported = b'\x10\x04' # GetStorageIDs
            op5_supported = b'\x10\x05' # GetStorageInfo
            op6_supported = b'\x10\x06' # GetNumObjects
            op7_supported = b'\x10\x07' # GetObjectHandles
            op8_supported = b'\x10\x08' # GetObjectInfo
            op9_supported = b'\x10\x09' # GetObject
            op10_supported = b'\x10\x0a' # GetThumb
            op11_supported = b'\x10\x0c' # SendObjectInfo
            op12_supported = b'\x10\x0d' # SendObject
            op13_supported = b'\x10\x14' # GetDevicePropDesc
            op14_supported = b'\x10\x15' # GetDevicePropValue
            op15_supported = b'\x10\x16' # SetDevicePropValue
            op16_supported = b'\x10\x1b' # GetPartialObject
 
            if self.maxusb_app.testcase[1] == "DeviceInfo_EventsSupportedArraySize":
                events_supported_array_size = change_byte_order(self.maxusb_app.testcase[2])
            else:
                events_supported_array_size = b'\x00\x00\x00\x04' # 4 events supported

            if self.maxusb_app.testcase[1] == "DeviceInfo_EventSupported":
                ev1_supported = change_byte_order(self.maxusb_app.testcase[2])
            else:
                ev1_supported = b'\x40\x04' # StoredAdded
            ev2_supported = b'\x40\x05' # StoreRemoved
            ev3_supported = b'\x40\x08' # DeviceInfoChanged
            ev4_supported = b'\x40\x09' # RequestObjectTransfer

            if self.maxusb_app.testcase[1] == "DeviceInfo_DevicePropertiesSupportedArraySize":
                device_properties_supported_array_size = change_byte_order(self.maxusb_app.testcase[2])
            else:
                device_properties_supported_array_size = b'\x00\x00\x00\x02' # 2 properties supported

            if self.maxusb_app.testcase[1] == "DeviceInfo_DevicePropertySupported":
                dp1_supported = change_byte_order(self.maxusb_app.testcase[2])
            else:
                dp1_supported = b'\xd4\x06' # Unknown property 
            dp2_supported = b'\xd4\x07' # Unknown property

            if self.maxusb_app.testcase[1] == "DeviceInfo_CaptureFormatsSupportedArraySize":
                capture_formats_supported_array_size = change_byte_order(self.maxusb_app.testcase[2])
            else:
                capture_formats_supported_array_size = b'\x00\x00\x00\x00' # 0 formats supported

            if self.maxusb_app.testcase[1] == "DeviceInfo_ImageFormatsSupportedArraySize":
                image_formats_supported_array_size = change_byte_order(self.maxusb_app.testcase[2])
            else:
                image_formats_supported_array_size = b'\x00\x00\x00\x06' # 6 formats supported

            if self.maxusb_app.testcase[1] == "DeviceInfo_ImageFormatSupported":
                if1_supported = change_byte_order(self.maxusb_app.testcase[2])
            else:
                if1_supported = b'\x30\x01' # Association (Folder)
            if2_supported = b'\x30\x02' # Script
            if3_supported = b'\x30\x06' # DPOF
            if4_supported = b'\x30\x0d' # Unknown image format
            if5_supported = b'\x38\x01' # EXIF/JPEG
            if6_supported = b'\x38\x0d' # TIFF

            manufacturer = b'P\x00a\x00n\x00a\x00s\x00o\x00n\x00i\x00c\x00\x00\x00'
            manufacturer_length = len(manufacturer) / 2
            model = b'D\x00M\x00C\x00-\x00F\x00S\x007\x00\x00\x00'
            model_length = len(model) /2
            device_version = b'1\x00.\x000\x00\x00\x00'
            device_version_length = len(device_version) /2
            serial_number = b'0\x000\x000\x000\x000\x000\x000\x000\x000\x000\x000\x000\x000\x000\x000\x000\x000\x000\x001\x00X\x000\x002\x000\x009\x000\x003\x000\x007\x005\x004\x00\x00\x00\x00\x00'
            serial_number_length = len(serial_number) /2

            device_version_length_bytes = int_to_bytestring(device_version_length)
            serial_number_length_bytes = int_to_bytestring(serial_number_length)

            if self.maxusb_app.testcase[1] == "DeviceInfo_Manufacturer":
                manufacturer = change_byte_order(self.maxusb_app.testcase[2])
                manufacturer_length_bytes = b''
            else:
                manufacturer_length_bytes = int_to_bytestring(manufacturer_length)

            if self.maxusb_app.testcase[1] == "DeviceInfo_Model":
                model = change_byte_order(self.maxusb_app.testcase[2])
                model_length_bytes = b''
            else:
                model_length_bytes = int_to_bytestring(model_length)

            if self.maxusb_app.testcase[1] == "DeviceInfo_DeviceVersion":
                device_version = change_byte_order(self.maxusb_app.testcase[2])
                device_version_length_bytes = b''
            else:
                device_version_length_bytes = int_to_bytestring(device_version_length)

            if self.maxusb_app.testcase[1] == "DeviceInfo_SerialNumber":
                serial_number = change_byte_order(self.maxusb_app.testcase[2])
                serial_number_length_bytes = b''
            else:
                serial_number_length_bytes = int_to_bytestring(serial_number_length)

            response = change_byte_order(container_type) + \
                       change_byte_order(operation_code) + \
                       change_byte_order(transaction_id) + \
                       change_byte_order(standard_version) + \
                       change_byte_order(vendor_extension_id) + \
                       change_byte_order(vendor_extension_version) + \
                       change_byte_order(vendor_extension_desc) + \
                       change_byte_order(functional_mode) + \
                       change_byte_order(operations_supported_array_size) + \
                       change_byte_order(op1_supported) + \
                       change_byte_order(op2_supported) + \
                       change_byte_order(op3_supported) + \
                       change_byte_order(op4_supported) + \
                       change_byte_order(op5_supported) + \
                       change_byte_order(op6_supported) + \
                       change_byte_order(op7_supported) + \
                       change_byte_order(op8_supported) + \
                       change_byte_order(op9_supported) + \
                       change_byte_order(op10_supported) + \
                       change_byte_order(op11_supported) + \
                       change_byte_order(op12_supported) + \
                       change_byte_order(op13_supported) + \
                       change_byte_order(op14_supported) + \
                       change_byte_order(op15_supported) + \
                       change_byte_order(op16_supported) + \
                       change_byte_order(events_supported_array_size) + \
                       change_byte_order(ev1_supported) + \
                       change_byte_order(ev2_supported) + \
                       change_byte_order(ev3_supported) + \
                       change_byte_order(ev4_supported) + \
                       change_byte_order(device_properties_supported_array_size) + \
                       change_byte_order(dp1_supported) + \
                       change_byte_order(dp2_supported) + \
                       change_byte_order(capture_formats_supported_array_size) + \
                       change_byte_order(image_formats_supported_array_size) + \
                       change_byte_order(if1_supported) + \
                       change_byte_order(if2_supported) + \
                       change_byte_order(if3_supported) + \
                       change_byte_order(if4_supported) + \
                       change_byte_order(if5_supported) + \
                       change_byte_order(if6_supported) + \
                       manufacturer_length_bytes + \
                       manufacturer + \
                       model_length_bytes + \
                       model + \
                       device_version_length_bytes + \
                       device_version + \
                       serial_number_length_bytes + \
                       serial_number

            

            if self.maxusb_app.testcase[1] == "DeviceInfo_ContainerLength":
                container_length_bytes = change_byte_order(self.maxusb_app.testcase[2])
            else:
                container_length = len(response) + 4
                container_length_bytes = bytes([
                (container_length      ) & 0xff,
                (container_length >>  8) & 0xff,
                (container_length >> 16) & 0xff,
                (container_length >> 24) & 0xff])

            response = container_length_bytes + response
            response2 = self.create_send_ok(transaction_id)


        elif opcode == 0x1003:      # CloseSession
            if self.verbose > 0:
                print(self.name, "got CloseSession")

            response = self.create_send_ok(transaction_id)


        elif opcode == 0x1004:      # GetSTorageIDs
            if self.verbose > 0:
                print(self.name, "got GetStorageIDs")


            if self.maxusb_app.testcase[1] == "StorageIDArray_ContainerType":
                container_type = change_byte_order(self.maxusb_app.testcase[2])
            else:
                container_type = b'\x00\x02' # Data block

            if self.maxusb_app.testcase[1] == "StorageIDArray_OperationCode":
                operation_code = change_byte_order(self.maxusb_app.testcase[2])
            else:
                operation_code = b'\x10\x04' # GetStorageID

            if self.maxusb_app.testcase[1] == "StorageIDArray_StorageIDsArraySize":
                storage_id_array_size = change_byte_order(self.maxusb_app.testcase[2])
            else:
                storage_id_array_size = b'\x00\x00\x00\x01' # 1 storage ID


            if self.maxusb_app.testcase[1] == "StorageIDArray_StorageID":
                storage_id = change_byte_order(self.maxusb_app.testcase[2])
            else:
                storage_id = b'\x00\x01\x00\x01' # Phys: 0x0001 Log: 0x0001

            response = change_byte_order(container_type) + \
                       change_byte_order(operation_code) + \
                       change_byte_order(transaction_id) + \
                       change_byte_order(storage_id_array_size) + \
                       change_byte_order(storage_id)

            container_length = len(response) + 4


            if self.maxusb_app.testcase[1] == "StorageIDArray_ContainerLength":
                container_length_bytes = change_byte_order(self.maxusb_app.testcase[2])
            else:
                container_length_bytes = bytes([
                (container_length      ) & 0xff,
                (container_length >>  8) & 0xff,
                (container_length >> 16) & 0xff,
                (container_length >> 24) & 0xff])

            response = container_length_bytes + response
            response2 = self.create_send_ok(transaction_id)




        elif opcode == 0x1007:      # GetObjectHandles
            if self.verbose > 0:
                print(self.name, "got GetObjectHandles")


            if self.maxusb_app.testcase[1] == "ObjectHandles_ContainerType":
                container_type = change_byte_order(self.maxusb_app.testcase[2])
            else:
                container_type = b'\x00\x02' # Data block

            if self.maxusb_app.testcase[1] == "ObjectHandles_OperationCode":
                operation_code = change_byte_order(self.maxusb_app.testcase[2])
            else:
                operation_code = b'\x10\x07' # GetObjectHandles

            if self.maxusb_app.testcase[1] == "ObjectHandles_ObjectHandleArraySize":
                object_handle_array_size = change_byte_order(self.maxusb_app.testcase[2])
            else:
                object_handle_array_size = b'\x00\x00\x00\x01' # 1 array size
            if self.maxusb_app.testcase[1] == "ObjectHandles_ObjectHandle":
                object_handle = change_byte_order(self.maxusb_app.testcase[2])
            else:
                object_handle = b'\x42\x19\x42\xca' # Object handle

            response = change_byte_order(container_type) + \
                       change_byte_order(operation_code) + \
                       change_byte_order(transaction_id) + \
                       change_byte_order(object_handle_array_size) + \
                       change_byte_order(object_handle) 

            container_length = len(response) + 4

            if self.maxusb_app.testcase[1] == "ObjectHandles_ContainerLength":
                container_length_bytes = change_byte_order(self.maxusb_app.testcase[2])
            else:
                container_length_bytes = bytes([
                (container_length      ) & 0xff,
                (container_length >>  8) & 0xff,
                (container_length >> 16) & 0xff,
                (container_length >> 24) & 0xff])

            response = container_length_bytes + response
            response2 = self.create_send_ok(transaction_id)


        elif opcode == 0x1008:      # GetObjectInfo
            if self.verbose > 0:
                print(self.name, "got GetObjectInfo")


            if self.maxusb_app.testcase[1] == "ObjectInfo_ContainerType":
                container_type = change_byte_order(self.maxusb_app.testcase[2])
            else:
                container_type = b'\x00\x02' # Data block
            if self.maxusb_app.testcase[1] == "ObjectInfo_OperationCode":
                operation_code = change_byte_order(self.maxusb_app.testcase[2])
            else:
                operation_code = b'\x10\x08' # GetObjectInfo
            if self.maxusb_app.testcase[1] == "ObjectInfo_StorageID":
                storage_id = change_byte_order(self.maxusb_app.testcase[2])
            else:
                storage_id = b'\x00\x01\x00\x01' # Phy: 0x0001 Log: 0x0001
            if self.maxusb_app.testcase[1] == "ObjectInfo_ObjectFormat":
                object_format = change_byte_order(self.maxusb_app.testcase[2])
            else:
                object_format = b'\x38\x01' # EXIF/JPEG
            if self.maxusb_app.testcase[1] == "ObjectInfo_ProtectionStatus":
                protection_status = change_byte_order(self.maxusb_app.testcase[2])
            else:
                protection_status = b'\x00\x00' # no protection
            if self.maxusb_app.testcase[1] == "ObjectInfo_ObjectCompressedSize":
                object_compressed_size = change_byte_order(self.maxusb_app.testcase[2])
            else:
                object_compressed_size = b'\x00\x31\xd6\x58' # 3266136
            if self.maxusb_app.testcase[1] == "ObjectInfo_ThumbFormat":
                thumb_format = change_byte_order(self.maxusb_app.testcase[2])
            else:
                thumb_format = b'\x38\x08' # JFIF
            if self.maxusb_app.testcase[1] == "ObjectInfo_ThumbCompressedSize":
                thumb_compressed_size = change_byte_order(self.maxusb_app.testcase[2])
            else:
                thumb_compressed_size = b'\x00\x00\x0d\xcd' # 3533
            if self.maxusb_app.testcase[1] == "ObjectInfo_ThumbPixelWidth":
                thumb_pixel_width = change_byte_order(self.maxusb_app.testcase[2])
            else:
                thumb_pixel_width = b'\x00\x00\x00\xa0' # 160
            if self.maxusb_app.testcase[1] == "ObjectInfo_ThumbPixelHeight":
                thumb_pixel_height = change_byte_order(self.maxusb_app.testcase[2])
            else:
                thumb_pixel_height = b'\x00\x00\x00\x78' # 120
            if self.maxusb_app.testcase[1] == "ObjectInfo_ImagePixelWidth":
                image_pixel_width = change_byte_order(self.maxusb_app.testcase[2])
            else:
                image_pixel_width = b'\x00\x00\x0e\x40' # 3648
            if self.maxusb_app.testcase[1] == "ObjectInfo_ImagePixelHeight":
                image_pixel_height = change_byte_order(self.maxusb_app.testcase[2])
            else:
                image_pixel_height = b'\x00\x00\x0a\xb0' # 2736
            if self.maxusb_app.testcase[1] == "ObjectInfo_ImagePixelDepth":
                image_pixel_depth = change_byte_order(self.maxusb_app.testcase[2])
            else:
                image_pixel_depth = b'\x00\x00\x00\x18' # 24
            if self.maxusb_app.testcase[1] == "ObjectInfo_ParentObject":
                parent_object = change_byte_order(self.maxusb_app.testcase[2])
            else:
                parent_object = b'\x00\x00\x00\x00' # Object handle = 0
            if self.maxusb_app.testcase[1] == "ObjectInfo_AssociationType":
                association_type = change_byte_order(self.maxusb_app.testcase[2])
            else:
                association_type = b'\x00\x00' # undefined
            if self.maxusb_app.testcase[1] == "ObjectInfo_AssociationDesc":
                association_desc = change_byte_order(self.maxusb_app.testcase[2])
            else:
                association_desc = b'\x00\x00\x00\x00' # undefined
            if self.maxusb_app.testcase[1] == "ObjectInfo_SequenceNumber":
                sequence_number = change_byte_order(self.maxusb_app.testcase[2])
            else:
                sequence_number = b'\x00\x00\x00\x00' # 0
            if self.maxusb_app.testcase[1] == "ObjectInfo_Filename":
                filename = change_byte_order(self.maxusb_app.testcase[2])
            else:
                filename = b'\x0D\x50\x00\x31\x00\x30\x00\x31\x00\x30\x00\x37\x00\x34\x00\x39\x00\x2E\x00\x4A\x00\x50\x00\x47\x00\x00\x00' # P1010749.JPG
            if self.maxusb_app.testcase[1] == "ObjectInfo_CaptureDate":
                capture_date = change_byte_order(self.maxusb_app.testcase[2])
            else:
                capture_date = b'\x10\x32\x00\x30\x00\x31\x00\x33\x00\x30\x00\x37\x00\x32\x00\x33\x00\x54\x00\x31\x00\x31\x00\x30\x00\x35\x00\x30\x00\x36\x00\x00\x00' # 20130723T110506
            if self.maxusb_app.testcase[1] == "ObjectInfo_ModificationDate":
                modification_date = change_byte_order(self.maxusb_app.testcase[2])
            else:
                modification_date = b'\x10\x32\x00\x30\x00\x31\x00\x33\x00\x30\x00\x37\x00\x32\x00\x33\x00\x54\x00\x31\x00\x31\x00\x30\x00\x35\x00\x30\x00\x36\x00\x00\x00' # 20130723T110506

            if self.maxusb_app.testcase[1] == "ObjectInfo_Keywords":
                keywords = change_byte_order(self.maxusb_app.testcase[2])
            else:
                keywords = b'\x00' # none

            response = change_byte_order(container_type) + \
                       change_byte_order(operation_code) + \
                       change_byte_order(transaction_id) + \
                       change_byte_order(storage_id) + \
                       change_byte_order(object_format) + \
                       change_byte_order(protection_status) + \
                       change_byte_order(object_compressed_size) + \
                       change_byte_order(thumb_format) + \
                       change_byte_order(thumb_compressed_size) + \
                       change_byte_order(thumb_pixel_width) + \
                       change_byte_order(thumb_pixel_height) + \
                       change_byte_order(image_pixel_width) + \
                       change_byte_order(image_pixel_height) + \
                       change_byte_order(image_pixel_depth) + \
                       change_byte_order(parent_object) + \
                       change_byte_order(association_type) + \
                       change_byte_order(association_desc) + \
                       change_byte_order(sequence_number) + \
                       filename + \
                       capture_date + \
                       modification_date + \
                       keywords 

            container_length = len(response) + 4

            if self.maxusb_app.testcase[1] == "ObjectInfo_ContainerLength":
                container_length_bytes = change_byte_order(self.maxusb_app.testcase[2])
            else:
                container_length_bytes = bytes([
                (container_length      ) & 0xff,
                (container_length >>  8) & 0xff,
                (container_length >> 16) & 0xff,
                (container_length >> 24) & 0xff])

            response = container_length_bytes + response
            response2 = self.create_send_ok(transaction_id)




        elif opcode == 0x1005:      # GetSTorageInfo
            if self.verbose > 0:
                print(self.name, "got GetStorageInfo")

            if self.maxusb_app.testcase[1] == "StorageInfo_ContainerType":
                container_type = change_byte_order(self.maxusb_app.testcase[2])
            else:
                container_type = b'\x00\x02' # Data block
            if self.maxusb_app.testcase[1] == "StorageInfo_OperationCode":
                operation_code = change_byte_order(self.maxusb_app.testcase[2])
            else:
                operation_code = b'\x10\x05' # GetStorageInfo

            if self.maxusb_app.testcase[1] == "StorageInfo_StorageType":
                storage_type = change_byte_order(self.maxusb_app.testcase[2])
            else:
                storage_type = b'\x00\x04' # Removable RAM
            if self.maxusb_app.testcase[1] == "StorageInfo_FilesystemType":
                filesystem_type = change_byte_order(self.maxusb_app.testcase[2])
            else:
                filesystem_type = b'\x00\x03' # DCF (Design rule for Camera File system)

            if self.maxusb_app.testcase[1] == "StorageInfo_AccessCapability":
                access_capability = change_byte_order(self.maxusb_app.testcase[2])
            else:
                access_capability = b'\x00\x00' # Read-write

            if self.maxusb_app.testcase[1] == "StorageInfo_MaxCapacity":
                max_capacity = change_byte_order(self.maxusb_app.testcase[2])
            else:
                max_capacity = b'\x00\x00\x00\x00\x78\x18\x00\x00' # 2014838784 bytes

            if self.maxusb_app.testcase[1] == "StorageInfo_FreeSpaceInBytes":
                free_space_in_bytes = change_byte_order(self.maxusb_app.testcase[2])
            else:
                free_space_in_bytes = b'\x00\x00\x00\x00\x77\xda\x80\x00' # 2010808320 bytes


            if self.maxusb_app.testcase[1] == "StorageInfo_FreeSpaceInImages":
                free_space_in_images = change_byte_order(self.maxusb_app.testcase[2])
            else:
                free_space_in_images = b'\x00\x00\x00\x00' # 0 bytes

            if self.maxusb_app.testcase[1] == "StorageInfo_StorageDescription":
                storage_description = change_byte_order(self.maxusb_app.testcase[2])
            else:
                storage_description = b'\x00'

            if self.maxusb_app.testcase[1] == "StorageInfo_VolumeLabel":
                volume_label = change_byte_order(self.maxusb_app.testcase[2])
            else:
                volume_label = b'\x00' 

            response = change_byte_order(container_type) + \
                       change_byte_order(operation_code) + \
                       change_byte_order(transaction_id) + \
                       change_byte_order(storage_type) + \
                       change_byte_order(filesystem_type) + \
                       change_byte_order(access_capability) + \
                       change_byte_order(max_capacity) + \
                       change_byte_order(free_space_in_bytes) + \
                       change_byte_order(free_space_in_images) + \
                       change_byte_order(storage_description) + \
                       change_byte_order(volume_label)

            container_length = len(response) + 4

            if self.maxusb_app.testcase[1] == "StorageInfo_ContainerLength":
                container_length_bytes = change_byte_order(self.maxusb_app.testcase[2])
            else:
                container_length_bytes = bytes([
                (container_length      ) & 0xff,
                (container_length >>  8) & 0xff,
                (container_length >> 16) & 0xff,
                (container_length >> 24) & 0xff])

            response = container_length_bytes + response
            response2 = self.create_send_ok(transaction_id)


        if response and self.maxusb_app.server_running == False:
            if self.verbose > 2:
                print(self.name, "responding with", len(response), "bytes:",
                        bytes_as_hex(response))

            self.configuration.device.maxusb_app.send_on_endpoint(2, response)


        if response2 and self.maxusb_app.server_running == False:
            if self.verbose > 2:
                print(self.name, "responding with", len(response2), "bytes:",
                        bytes_as_hex(response2))

            self.configuration.device.maxusb_app.send_on_endpoint(2, response2)






class ThumbImage:
    def __init__(self, filename):
        self.filename = filename

        self.file = open(self.filename, 'r+b')
        self.image = mmap(self.file.fileno(), 0)

    def close(self):
        self.image.flush()
        self.image.close()

    def read_data(self):
        return self.image



class ContainerRequestWrapper:
    def __init__(self, bytestring):
        self.container_length       = bytestring[0:4]
        self.container_type         = bytestring[4:6]
        self.operation_code         = bytestring[6:8]
        self.transaction_id         = bytestring[8:12]
        self.parameter1             = bytestring[12:16]



class USBImageDevice(USBDevice):
    name = "USB image device"

    def __init__(self, maxusb_app, vid, pid, rev, int_class, int_sub, int_proto, thumb_image_filename, verbose=0):
        self.thumb_image = ThumbImage("ncc_group_logo.jpg")
        self.partial_image = ThumbImage("ncc_group_logo.bin")

        interface1 = USBImageInterface(0, maxusb_app, self.thumb_image, self.partial_image, int_class, int_sub, int_proto, verbose=verbose)


        if vid == 0x1111:
            vid = 0x04da
        if pid == 0x2222:
            pid = 0x2374
        if rev == 0x3333:
            rev = 0x0010


        config = USBConfiguration(
                maxusb_app,
                1,                                          # index
                "Image",                       # string desc
                [ interface1 ]                               # interfaces
        )

        USBDevice.__init__(
                self,
                maxusb_app,
                0,                      # device class
                0,                      # device subclass
                0,                      # protocol release number
                64,                     # max packet size for endpoint 0
                vid,                    # vendor id
                pid,                    # product id
                rev,                    # device revision
                "Panasonic",            # manufacturer string
                "DMC-FS7",              # product string
                "0000000000000000001X0209030754",         # serial number string
                [ config ],
                verbose=verbose
        )

    def disconnect(self):
        self.disk_image.close()
        USBDevice.disconnect(self)


########NEW FILE########
__FILENAME__ = USBIphone
# USBIphone.py
#
# Contains class definitions to implement a USB iPhone device.

from USB import *
from USBDevice import *
from USBConfiguration import *
from USBInterface import *
from USBCSInterface import *
from USBEndpoint import *
from USBCSEndpoint import *
from USBVendor import *

class USBIphoneVendor(USBVendor):
    name = "USB iPhone vendor"

    def setup_request_handlers(self):
        self.request_handlers = {
             0x40 : self.handle_40_request,
             0x45 : self.handle_45_request

        }

    def handle_40_request(self, req):
        if self.verbose > 0:
            print(self.name, "received reset request")

        self.device.maxusb_app.send_on_endpoint(0, b'')

    def handle_45_request(self, req):
        if self.verbose > 0:
            print(self.name, "received reset request")

        self.device.maxusb_app.send_on_endpoint(0, b'\x03')




class USBIphoneClass(USBClass):
    name = "USB iPhone class"

    def __init__(self, maxusb_app):

        self.maxusb_app = maxusb_app
        self.setup_request_handlers()

    def setup_request_handlers(self):
        self.request_handlers = {
            0x22 : self.handle_set_control_line_state,
            0x20 : self.handle_set_line_coding
        }

    def handle_set_control_line_state(self, req):
        self.maxusb_app.send_on_endpoint(0, b'')
        if self.maxusb_app.mode == 1:
            print (" **SUPPORTED**",end="")
            if self.maxusb_app.fplog:
                self.maxusb_app.fplog.write (" **SUPPORTED**\n")
            self.maxusb_app.stop = True

    def handle_set_line_coding(self, req):
        self.maxusb_app.send_on_endpoint(0, b'')



class USBIphoneInterface(USBInterface):
    name = "USB iPhone interface"

    def __init__(self, int_num, maxusb_app, usbclass, sub, proto, verbose=0):

        self.maxusb_app = maxusb_app
        self.int_num = int_num

        descriptors = { }

        endpoints0 = [
            USBEndpoint(
                maxusb_app,
                0x02,           # endpoint address
                USBEndpoint.direction_out,
                USBEndpoint.transfer_type_bulk,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                0x0002,         # max packet size
                0x0a,           # polling interval, see USB 2.0 spec Table 9-13
                self.handle_data_available    # handler function
            ),
            USBEndpoint(
                maxusb_app,
                0x81,           # endpoint address
                USBEndpoint.direction_in,
                USBEndpoint.transfer_type_bulk,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                0x0002,         # max packet size
                0x0a,           # polling interval, see USB 2.0 spec Table 9-13
                self.handle_data_available    # handler function
            ),
            USBEndpoint(
                maxusb_app,
                0x83,           # endpoint address
                USBEndpoint.direction_in,
                USBEndpoint.transfer_type_interrupt,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                0x4000,         # max packet size
                0x0a,           # polling interval, see USB 2.0 spec Table 9-13
                self.handle_data_available    # handler function
            )

        ]


        endpoints1 = [
            USBEndpoint(
                maxusb_app,
                0x04,           # endpoint address
                USBEndpoint.direction_out,
                USBEndpoint.transfer_type_bulk,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                0x0002,         # max packet size
                0x00,           # polling interval, see USB 2.0 spec Table 9-13
                self.handle_data_available    # handler function
            ),
            USBEndpoint(
                maxusb_app,
                0x85,           # endpoint address
                USBEndpoint.direction_in,
                USBEndpoint.transfer_type_bulk,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                0x0002,         # max packet size
                0x00,           # polling interval, see USB 2.0 spec Table 9-13
                self.handle_data_available    # handler function
            )
        ]


        endpoints2 = []


        if self.int_num == 0:
                endpoints = endpoints0

        elif self.int_num == 1:
                endpoints = endpoints1

        elif self.int_num == 2:
                endpoints = endpoints2




        # TODO: un-hardcode string index (last arg before "verbose")
        USBInterface.__init__(
                self,
                maxusb_app,
                self.int_num,          # interface number
                0,          # alternate setting
                usbclass,          # 3 interface class
                sub,          # 0 subclass
                proto,          # 0 protocol
                0,          # string index
                verbose,
                endpoints,
                descriptors
        )

        self.device_class = USBIphoneClass(maxusb_app)
        self.device_class.set_interface(self)


    def handle_data_available(self, data):
        if self.verbose > 0:
            print(self.name, "handling", len(data), "bytes of audio data")
    



class USBIphoneDevice(USBDevice):
    name = "USB iPhone device"

    def __init__(self, maxusb_app, vid, pid, rev, verbose=0):

        int_class = 0
        int_subclass = 0
        int_proto = 0
        interface0 = USBIphoneInterface(0, maxusb_app, 0x06, 0x01, 0x01,verbose=verbose)
        interface1 = USBIphoneInterface(1, maxusb_app, 0xff, 0xfe, 0x02,verbose=verbose)
        interface2 = USBIphoneInterface(2, maxusb_app, 0xff, 0xfd, 0x01,verbose=verbose)


        config = [
            USBConfiguration(                
                maxusb_app,
                1,                          # index
                "iPhone",             # string desc
                [ interface0, interface1, interface2 ]  # interfaces
            ),
            USBConfiguration(
                maxusb_app,
                2,                          # index
                "iPhone",             # string desc
                [ interface0, interface1, interface2 ]  # interfaces
            ),
            USBConfiguration(
                maxusb_app,
                3,                          # index
                "iPhone",             # string desc
                [ interface0, interface1, interface2 ]  # interfaces
            ),
            USBConfiguration(
                maxusb_app,
                4,                          # index
                "iPhone",             # string desc
                [ interface0, interface1, interface2 ]  # interfaces
            )

        ]


        USBDevice.__init__(
                self,
                maxusb_app,
                0,                      # 0 device class
		        0,                      # device subclass
                0,                      # protocol release number
                64,                     # max packet size for endpoint 0
		        0x05ac,                 # vendor id
                0x1297,                 # product id
		        0x0310,                 # device revision
                "Apple",                # manufacturer string
                "iPhone",               # product string
                "a9f579a7e04281fbf77fe04d06b5cc083e6eb5a3",               # serial number string
                config,
                verbose=verbose
        )
        self.device_vendor = USBIphoneVendor()
        self.device_vendor.set_device(self)




########NEW FILE########
__FILENAME__ = USBKeyboard
# USBKeyboard.py
#
# Contains class definitions to implement a USB keyboard.

from USB import *
from USBDevice import *
from USBConfiguration import *
from USBInterface import *
from USBEndpoint import *

class USBKeyboardClass(USBClass):
    name = "USB Keyboard class"

    def __init__(self, maxusb_app):

        self.maxusb_app = maxusb_app
        self.setup_request_handlers()

    def setup_request_handlers(self):
        self.request_handlers = {
            0x01 : self.handle_get_report,
            0x09 : self.handle_set_report,
            0x0a : self.handle_set_idle
        }

    def handle_set_idle(self, req):
        response = b''
        self.maxusb_app.send_on_endpoint(0, response)

    def handle_get_report(self, req):
        response = b''
        self.maxusb_app.send_on_endpoint(0, response)

    def handle_set_report(self, req):
        response = b''
        self.maxusb_app.send_on_endpoint(0, response)


class USBKeyboardInterface(USBInterface):
    name = "USB keyboard interface"

    def __init__(self, maxusb_app, verbose=0):

        self.maxusb_app = maxusb_app


        if self.maxusb_app.testcase[1] == "Report_Usage_Page":
            usage_page_generic_desktop_controls = self.maxusb_app.testcase[2]
        else:
            usage_page_generic_desktop_controls = b'\x05\x01'
#            usage_page_generic_desktop_controls = b'\xb1\x01'


        if self.maxusb_app.testcase[1] == "Report_Usage_Keyboard":
            usage_keyboard = self.maxusb_app.testcase[2]
        else:
            usage_keyboard = b'\x09\x06'
        collection_application = b'\xA1\x01'
        if self.maxusb_app.testcase[1] == "Report_Usage_Page_Keyboard":
            usage_page_keyboard = self.maxusb_app.testcase[2]
        else:
            usage_page_keyboard = b'\x05\x07'
        if self.maxusb_app.testcase[1] == "Report_Usage_Minimum1":
            usage_minimum1 = self.maxusb_app.testcase[2]
        else:
            usage_minimum1 = b'\x19\xE0'
        if self.maxusb_app.testcase[1] == "Report_Usage_Maximum1":
            usage_maximum1 = self.maxusb_app.testcase[2]
        else:
            usage_maximum1 = b'\x29\xE7'
        if self.maxusb_app.testcase[1] == "Report_Logical_Minimum1":
            logical_minimum1 = self.maxusb_app.testcase[2]
        else:
            logical_minimum1 = b'\x15\x00'
        if self.maxusb_app.testcase[1] == "Report_Logical_Maximum1":
            logical_maximum1 = self.maxusb_app.testcase[2]
        else:
            logical_maximum1 = b'\x25\x01'
        if self.maxusb_app.testcase[1] == "Report_Report_Size1":
            report_size1 = self.maxusb_app.testcase[2]
        else:
            report_size1 = b'\x75\x01'
        if self.maxusb_app.testcase[1] == "Report_Report_Count1":
            report_count1 = self.maxusb_app.testcase[2]
        else:
            report_count1 = b'\x95\x08'
        if self.maxusb_app.testcase[1] == "Report_Input_Data_Variable_Absolute_Bitfield":
            input_data_variable_absolute_bitfield = self.maxusb_app.testcase[2]
        else:
            input_data_variable_absolute_bitfield = b'\x81\x02'
        if self.maxusb_app.testcase[1] == "Report_Report_Count2":
            report_count2 = self.maxusb_app.testcase[2]
        else:
            report_count2 = b'\x95\x01'
        if self.maxusb_app.testcase[1] == "Report_Report_Size2":
            report_size2 = self.maxusb_app.testcase[2]
        else:
            report_size2 = b'\x75\x08'
        if self.maxusb_app.testcase[1] == "Report_Input_Constant_Array_Absolute_Bitfield":
            input_constant_array_absolute_bitfield = self.maxusb_app.testcase[2]
        else:
            input_constant_array_absolute_bitfield = b'\x81\x01'
        if self.maxusb_app.testcase[1] == "Report_Usage_Minimum2":
            usage_minimum2 = self.maxusb_app.testcase[2]
        else:
            usage_minimum2 = b'\x19\x00'
        if self.maxusb_app.testcase[1] == "Report_Usage_Maximum2":
            usage_maximum2 = self.maxusb_app.testcase[2]
        else:
            usage_maximum2 = b'\x29\x65'
        if self.maxusb_app.testcase[1] == "Report_Logical_Minimum2":
            logical_minimum2 = self.maxusb_app.testcase[2]
        else:
            logical_minimum2 = b'\x15\x00'
        if self.maxusb_app.testcase[1] == "Report_Logical_Maximum2":
            logical_maximum2 = self.maxusb_app.testcase[2]
        else:
            logical_maximum2 = b'\x25\x65'
        if self.maxusb_app.testcase[1] == "Report_Report_Size3":
            report_size3 = self.maxusb_app.testcase[2]
        else:
            report_size3 = b'\x75\x08'
        if self.maxusb_app.testcase[1] == "Report_Report_Count3":
            report_count3 = self.maxusb_app.testcase[2]
        else:
            report_count3 = b'\x95\x01'
        if self.maxusb_app.testcase[1] == "Report_Input_Data_Array_Absolute_Bitfield":
            input_data_array_absolute_bitfield = self.maxusb_app.testcase[2]
        else:
            input_data_array_absolute_bitfield = b'\x81\x00'
        if self.maxusb_app.testcase[1] == "Report_End_Collection":
            end_collection = self.maxusb_app.testcase[2]
        else:
            end_collection = b'\xc0'

        self.report_descriptor = usage_page_generic_desktop_controls + \
                        usage_keyboard + \
                        collection_application + \
                        usage_page_keyboard + \
                        usage_minimum1 + \
                        usage_maximum1 + \
                        logical_minimum1 + \
                        logical_maximum1 + \
                        report_size1 + \
                        report_count1 + \
                        input_data_variable_absolute_bitfield + \
                        report_count2 + \
                        report_size2 + \
                        input_constant_array_absolute_bitfield + \
                        usage_minimum2 + \
                        usage_maximum2 + \
                        logical_minimum2 + \
                        logical_maximum2 + \
                        report_size3 + \
                        report_count3 + \
                        input_data_array_absolute_bitfield + \
                        end_collection


        if self.maxusb_app.testcase[1] == "HID_bDescriptorType":
            bDescriptorType = self.maxusb_app.testcase[2]
        else:
            bDescriptorType = b'\x21' # HID
        bcdHID = b'\x10\x01'
        if self.maxusb_app.testcase[1] == "HID_bCountryCode":
            bCountryCode = self.maxusb_app.testcase[2]
        else:
            bCountryCode = b'\x00'
        if self.maxusb_app.testcase[1] == "HID_bNumDescriptors":
            bNumDescriptors = self.maxusb_app.testcase[2]
        else:
            bNumDescriptors = b'\x01'

        if self.maxusb_app.testcase[1] == "HID_bDescriptorType2":
            bDescriptorType2 = self.maxusb_app.testcase[2]
        else:
            bDescriptorType2 = b'\x22' #REPORT
        if self.maxusb_app.testcase[1] == "HID_wDescriptorLength":
            wDescriptorLength = self.maxusb_app.testcase[2]
        else:
            desclen = len (self.report_descriptor)
            wDescriptorLength =  bytes([
                (desclen     ) & 0xff,
                (desclen >> 8) & 0xff])

        self.hid_descriptor = bDescriptorType + \
                     bcdHID + \
                     bCountryCode + \
                     bNumDescriptors + \
                     bDescriptorType2 + \
                     wDescriptorLength

        if self.maxusb_app.testcase[1] == "HID_bLength":
            bLength = self.maxusb_app.testcase[2]
        else:
            bLength = bytes([len(self.hid_descriptor) + 1])

        self.hid_descriptor = bLength + self.hid_descriptor


        descriptors = { 
                USB.desc_type_hid    : self.hid_descriptor,
                USB.desc_type_report : self.report_descriptor
        }

        endpoint = USBEndpoint(
                maxusb_app,
                3,          # endpoint number
                USBEndpoint.direction_in,
                USBEndpoint.transfer_type_interrupt,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                16384,      # max packet size
                10,         # polling interval, see USB 2.0 spec Table 9-13
                self.handle_buffer_available    # handler function
        )

        # TODO: un-hardcode string index (last arg before "verbose")
        USBInterface.__init__(
                self,
                maxusb_app,
                0,          # interface number
                0,          # alternate setting
                3,          # 3 interface class
                0,          # 0 subclass
                0,          # 0 protocol
                0,          # string index
                verbose,
                [ endpoint ],
                descriptors
        )

        self.device_class = USBKeyboardClass(maxusb_app)

        empty_preamble = [ 0x00 ] * 10
        text = [ 0x0f, 0x00, 0x16, 0x00, 0x28, 0x00 ]

        self.keys = [ chr(x) for x in empty_preamble + text ]


    def handle_buffer_available(self):
        if not self.keys:
            if self.maxusb_app.mode == 1:
                print (" **SUPPORTED**",end="")
                if self.maxusb_app.fplog:
                    self.maxusb_app.fplog.write (" **SUPPORTED**\n")
                self.maxusb_app.stop = True

            return

        letter = self.keys.pop(0)
        self.type_letter(letter)

    def type_letter(self, letter, modifiers=0):
        data = bytes([ 0, 0, ord(letter) ])

        if self.verbose > 4:
            print(self.name, "sending keypress 0x%02x" % ord(letter))

        self.configuration.device.maxusb_app.send_on_endpoint(3, data)


class USBKeyboardDevice(USBDevice):
    name = "USB keyboard device"

    def __init__(self, maxusb_app, vid, pid, rev, verbose=0):


        interface = USBKeyboardInterface(maxusb_app, verbose=verbose)

        if vid == 0x1111:
            vid = 0x413c
        if pid == 0x2222:
            pid = 0x2107
        if rev == 0x3333:
            rev = 0x0178

        config = USBConfiguration(
                maxusb_app,
                1,                                          # index
                "Emulated Keyboard",    # string desc
                [ interface ]                  # interfaces
        )

        USBDevice.__init__(
                self,
                maxusb_app,
                0,                      # 0 device class
		        0,                      # device subclass
                0,                      # protocol release number
                64,                     # max packet size for endpoint 0
		        vid,                    # vendor id
                pid,                    # product id
		        rev,                    # device revision
                "Dell",                 # manufacturer string
                "Dell USB Entry Keyboard",   # product string
                "00001",                # serial number string
                [ config ],
                verbose=verbose
        )


########NEW FILE########
__FILENAME__ = USBMassStorage
# USBMassStorage.py 
#
# Contains class definitions to implement a USB mass storage device.

from mmap import mmap
import os

from USB import *
from USBDevice import *
from USBConfiguration import *
from USBInterface import *
from USBEndpoint import *
from USBClass import *

from util import *

class USBMassStorageClass(USBClass):
    name = "USB mass storage class"

    def setup_request_handlers(self):
        self.request_handlers = {
            0xFF : self.handle_bulk_only_mass_storage_reset_request,
            0xFE : self.handle_get_max_lun_request
         
        }

    def handle_bulk_only_mass_storage_reset_request(self, req):
        self.interface.configuration.device.maxusb_app.send_on_endpoint(0, b'')

    def handle_get_max_lun_request(self, req):
        self.interface.configuration.device.maxusb_app.send_on_endpoint(0, b'\x00')


class USBMassStorageInterface(USBInterface):
    name = "USB mass storage interface"

    def __init__(self, maxusb_app, disk_image, usbclass, sub, proto, verbose=0):
        self.disk_image = disk_image
        self.maxusb_app = maxusb_app
        descriptors = { }

        endpoints = [
            USBEndpoint(
                maxusb_app,
                1,          # endpoint number
                USBEndpoint.direction_out,
                USBEndpoint.transfer_type_bulk,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                16384,      # max packet size
                0,          # polling interval, see USB 2.0 spec Table 9-13
                self.handle_data_available    # handler function
            ),
            USBEndpoint(
                maxusb_app,
                3,          # endpoint number
                USBEndpoint.direction_in,
                USBEndpoint.transfer_type_bulk,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                16384,      # max packet size
                0,          # polling interval, see USB 2.0 spec Table 9-13
                None        # handler function
            )
        ]

        # TODO: un-hardcode string index (last arg before "verbose")
        USBInterface.__init__(
                self,
                maxusb_app,
                0,          # interface number
                0,          # alternate setting
                usbclass,          # 8 interface class: Mass Storage
                sub,          # 6 subclass: SCSI transparent command set
                proto,       # 0x50 protocol: bulk-only (BBB) transport
                0,          # string index
                verbose,
                endpoints,
                descriptors
        )

        self.device_class = USBMassStorageClass()
        self.device_class.set_interface(self)

        self.is_write_in_progress = False
        self.write_cbw = None
        self.write_base_lba = 0
        self.write_length = 0
        self.write_data = b''

    def handle_data_available(self, data):

        if self.verbose > 0:
            print(self.name, "handling", len(data), "bytes of SCSI data")

        if self.maxusb_app.mode == 1:
            print (" **SUPPORTED**",end="")
            if self.maxusb_app.fplog:
                self.maxusb_app.fplog.write (" **SUPPORTED**\n")
            self.maxusb_app.stop = True

        cbw = CommandBlockWrapper(data)
        opcode = cbw.cb[0]
        status = 0              # default to success
        response = None         # with no response data

        if self.maxusb_app.server_running == True:
            try:
                self.maxusb_app.netserver_from_endpoint_sd.send(data)
            except:
                print ("Error: No network client connected")

            while True:
                if len(self.maxusb_app.reply_buffer) > 0:
                    self.maxusb_app.send_on_endpoint(3, self.maxusb_app.reply_buffer)
                    self.maxusb_app.reply_buffer = ""
                    break

        elif self.is_write_in_progress:
            if self.verbose > 0:
                print(self.name, "got", len(data), "bytes of SCSI write data")

            self.write_data += data

            if len(self.write_data) < self.write_length:
                # more yet to read, don't send the CSW
                return

            self.disk_image.put_sector_data(self.write_base_lba, self.write_data)
            cbw = self.write_cbw

            self.is_write_in_progress = False
            self.write_data = b''

        elif opcode == 0x00:      # Test Unit Ready: just return OK status
            if self.verbose > 0:
                print(self.name, "got SCSI Test Unit Ready")

        elif opcode == 0x03:    # Request Sense
            if self.verbose > 0:
                print(self.name, "got SCSI Request Sense, data",
                        bytes_as_hex(cbw.cb[1:]))

            response_code = b'\x70'
            valid = b'\x00'
            filemark = b'\x06'
            information = b'\x00\x00\x00\x00'
            command_info = b'\x00\x00\x00\x00'
            additional_sense_code = b'\x3a'
            additional_sens_code_qualifier = b'\x00'
            field_replacement_unti_code = b'\x00'
            sense_key_specific = b'\x00\x00\x00'

            part1 = response_code + \
                    valid + \
                    filemark + \
                    information

            part2 = command_info + \
                    additional_sense_code + \
                    additional_sens_code_qualifier + \
                    field_replacement_unti_code + \
                    sense_key_specific

            length = bytes([len(part2)])
            response = part1 + length + part2


        elif opcode == 0x12:    # Inquiry
            if self.verbose > 0:
                print(self.name, "got SCSI Inquiry, data",
                        bytes_as_hex(cbw.cb[1:]))

            if self.maxusb_app.testcase[1] == "inquiry_peripheral":
                peripheral = self.maxusb_app.testcase[2]
            else:
                peripheral = b'\x00'    # SBC
            if self.maxusb_app.testcase[1] == "inquiry_RMB":
                RMB = self.maxusb_app.testcase[2]
            else:
                RMB = b'\x80'           # Removable
            if self.maxusb_app.testcase[1] == "inquiry_version":
                version = self.maxusb_app.testcase[2]
            else:
                version = b'\x00'
            if self.maxusb_app.testcase[1] == "response_data_format":
                response_data_format = self.maxusb_app.testcase[2]
            else:
                response_data_format = b'\x01'
            if self.maxusb_app.testcase[1] == "config1":
                config1 = self.maxusb_app.testcase[2]
            else:
                config1 = b'\x00'
            if self.maxusb_app.testcase[1] == "config2":
                config2 = self.maxusb_app.testcase[2]
            else:
                config2 = b'\x00'
            if self.maxusb_app.testcase[1] == "config3":
                config3 = self.maxusb_app.testcase[2]
            else:
                config3 = b'\x00'
            if self.maxusb_app.testcase[1] == "vendor_id":
                vendor_id = self.maxusb_app.testcase[2]
            else:
                vendor_id = b'PNY     '
            if self.maxusb_app.testcase[1] == "product_id":
                product_id = self.maxusb_app.testcase[2]
            else:
                product_id = b'USB 2.0 FD      '
            if self.maxusb_app.testcase[1] == "product_revision_level":
                product_revision_level = self.maxusb_app.testcase[2]
            else:
                product_revision_level = b'8.02'

            part1 = peripheral + \
                    RMB + \
                    version + \
                    response_data_format

            part2 = config1 + \
                    config2 + \
                    config3 + \
                    vendor_id + \
                    product_id + \
                    product_revision_level

            length = bytes([len(part2)])
            response = part1 + length + part2


        elif opcode == 0x1a or opcode == 0x5a:    # Mode Sense (6 or 10)
            page = cbw.cb[2] & 0x3f

            if self.verbose > 0:
                print(self.name, "got SCSI Mode Sense, page code 0x%02x" % page)

            if page == 0x1c:

                if self.maxusb_app.testcase[1] == "mode_sense_medium_type":
                    medium_type = self.maxusb_app.testcase[2]
                else:
                    medium_type = b'\x00'
                if self.maxusb_app.testcase[1] == "mode_sense_device_specific_param":
                    device_specific_param = self.maxusb_app.testcase[2]
                else:
                    device_specific_param = b'\x00'
                if self.maxusb_app.testcase[1] == "mode_sense_block_descriptor_len":
                    block_descriptor_len = self.maxusb_app.testcase[2]
                else:
                    block_descriptor_len = b'\x00'
                mode_page_1c = b'\x1c\x06\x00\x05\x00\x00\x00\x00'
            
                body =  medium_type + \
                        device_specific_param + \
                        block_descriptor_len + \
                        mode_page_1c 

                if self.maxusb_app.testcase[1] == "mode_sense_length":
                    length = self.maxusb_app.testcase[2]
                else:
                    length = bytes([len(body)]) 
                response = length + body

            if page == 0x3f:
                if self.maxusb_app.testcase[1] == "mode_sense_length":
                    length = self.maxusb_app.testcase[2]
                else:
                    length = b'\x45'
                if self.maxusb_app.testcase[1] == "mode_sense_medium_type":
                    medium_type = self.maxusb_app.testcase[2]
                else:
                    medium_type = b'\x00'
                if self.maxusb_app.testcase[1] == "mode_sense_device_specific_param":
                    device_specific_param = self.maxusb_app.testcase[2]
                else:
                    device_specific_param = b'\x00'
                if self.maxusb_app.testcase[1] == "mode_sense_block_descriptor_len":
                    block_descriptor_len = self.maxusb_app.testcase[2]
                else:
                    block_descriptor_len = b'\x08'
                mode_page = b'\x00\x00\x00\x00'

                response =  length + \
                            medium_type + \
                            device_specific_param + \
                            block_descriptor_len + \
                            mode_page

            else:
                if self.maxusb_app.testcase[1] == "mode_sense_length":
                    length = self.maxusb_app.testcase[2]
                else:
                    length = b'\x07'
                if self.maxusb_app.testcase[1] == "mode_sense_medium_type":
                    medium_type = self.maxusb_app.testcase[2]
                else:
                    medium_type = b'\x00'
                if self.maxusb_app.testcase[1] == "mode_sense_device_specific_param":
                    device_specific_param = self.maxusb_app.testcase[2]
                else:
                    device_specific_param = b'\x00'
                if self.maxusb_app.testcase[1] == "mode_sense_block_descriptor_len":
                    block_descriptor_len = self.maxusb_app.testcase[2]
                else:
                    block_descriptor_len = b'\x00'
                mode_page = b'\x00\x00\x00\x00'

                response =  length + \
                            medium_type + \
                            device_specific_param + \
                            block_descriptor_len + \
                            mode_page


        elif opcode == 0x1e:    # Prevent/Allow Removal: feign success
            if self.verbose > 0:
                print(self.name, "got SCSI Prevent/Allow Removal")

        #elif opcode == 0x1a or opcode == 0x5a:      # Mode Sense (6 or 10)
            # TODO

        elif opcode == 0x23:    # Read Format Capacity
            if self.verbose > 0:
                print(self.name, "got SCSI Read Format Capacity")

            if self.maxusb_app.testcase[1] == "read_format_capacity_capacity_list_length":
                capacity_list_length = self.maxusb_app.testcase[2]
            else:
                capacity_list_length = b'\x00\x00\x00\x08'
            if self.maxusb_app.testcase[1] == "read_format_capacity_number_of_blocks":
                number_of_blocks = self.maxusb_app.testcase[2]
            else:
                number_of_blocks = b'\x00\x00\x10\x00'
            if self.maxusb_app.testcase[1] == "read_format_capacity_descriptor_type":
                descriptor_type = self.maxusb_app.testcase[2]
            else:
                descriptor_type = b'\x00'
            if self.maxusb_app.testcase[1] == "read_format_capacity_block_length":
                block_length = self.maxusb_app.testcase[2]
            else:
                block_length = b'\x00\x02\x00'

            response =  capacity_list_length + \
                        number_of_blocks + \
                        descriptor_type + \
                        block_length


        elif opcode == 0x25:    # Read Capacity
            if self.verbose > 0:
                print(self.name, "got SCSI Read Capacity, data",
                        bytes_as_hex(cbw.cb[1:]))

            lastlba = self.disk_image.get_sector_count()

            if self.maxusb_app.testcase[1] == "read_capacity_logical_block_address":
                logical_block_address = self.maxusb_app.testcase[2]
            else:
                logical_block_address = bytes([
                    (lastlba >> 24) & 0xff,
                    (lastlba >> 16) & 0xff,
                    (lastlba >>  8) & 0xff,
                    (lastlba      ) & 0xff,
                ])


            if self.maxusb_app.testcase[1] == "read_capacity_length":
                length = self.maxusb_app.testcase[2]
            else:
                length = b'\x00\x00\x02\x00'
            response =  logical_block_address + \
                        length

        elif opcode == 0x28:    # Read (10)

            if self.maxusb_app.mode == 4:
                self.maxusb_app.stop = True


            base_lba = cbw.cb[2] << 24 \
                     | cbw.cb[3] << 16 \
                     | cbw.cb[4] << 8 \
                     | cbw.cb[5]

            num_blocks = cbw.cb[7] << 8 \
                       | cbw.cb[8]

            if self.verbose > 0:
                print(self.name, "got SCSI Read (10), lba", base_lba, "+",
                        num_blocks, "block(s)")
                        

            # Note that here we send the data directly rather than putting
            # something in 'response' and letting the end of the switch send
            for block_num in range(num_blocks):
                data = self.disk_image.get_sector_data(base_lba + block_num)
                self.configuration.device.maxusb_app.send_on_endpoint(3, data)

        elif opcode == 0x2a:    # Write (10)
            if self.verbose > 0:
                print(self.name, "got SCSI Write (10), data",
                        bytes_as_hex(cbw.cb[1:]))

            base_lba = cbw.cb[1] << 24 \
                     | cbw.cb[2] << 16 \
                     | cbw.cb[3] <<  8 \
                     | cbw.cb[4]

            num_blocks = cbw.cb[7] << 8 \
                       | cbw.cb[8]

            if self.verbose > 0:
                print(self.name, "got SCSI Write (10), lba", base_lba, "+",
                        num_blocks, "block(s)")

            # save for later
            self.write_cbw = cbw
            self.write_base_lba = base_lba
            self.write_length = num_blocks * self.disk_image.block_size
            self.is_write_in_progress = True

            # because we need to snarf up the data from wire before we reply
            # with the CSW
            return

        elif opcode == 0x35:    # Synchronize Cache (10): blindly OK
            if self.verbose > 0:
                print(self.name, "got Synchronize Cache (10)")

        else:
            if self.verbose > 0:
                print(self.name, "received unsupported SCSI opcode 0x%x" % opcode)
            status = 0x02   # command failed
            if cbw.data_transfer_length > 0:
                response = bytes([0] * cbw.data_transfer_length)

        if response and self.maxusb_app.server_running == False:
            if self.verbose > 2:
                print(self.name, "responding with", len(response), "bytes:",
                        bytes_as_hex(response))

            self.configuration.device.maxusb_app.send_on_endpoint(3, response)


        csw = bytes([
            ord('U'), ord('S'), ord('B'), ord('S'),
            cbw.tag[0], cbw.tag[1], cbw.tag[2], cbw.tag[3],
            0x00, 0x00, 0x00, 0x00,
            status
        ])

        if self.verbose > 3:
            print(self.name, "responding with status =", status)

#        if self.maxusb_app.server_running == False:
        self.configuration.device.maxusb_app.send_on_endpoint(3, csw)


class DiskImage:
    def __init__(self, filename, block_size):
        self.filename = filename
        self.block_size = block_size

        statinfo = os.stat(self.filename)
        self.size = statinfo.st_size

        self.file = open(self.filename, 'r+b')
        self.image = mmap(self.file.fileno(), 0)

    def close(self):
        self.image.flush()
        self.image.close()

    def get_sector_count(self):
        return int(self.size / self.block_size) - 1

    def get_sector_data(self, address):
        block_start = address * self.block_size
        block_end   = (address + 1) * self.block_size   # slices are NON-inclusive

        return self.image[block_start:block_end]

    def put_sector_data(self, address, data):
        block_start = address * self.block_size
        block_end   = (address + 1) * self.block_size   # slices are NON-inclusive

        self.image[block_start:block_end] = data[:self.block_size]
        self.image.flush()


class CommandBlockWrapper:
    def __init__(self, bytestring):
        self.signature              = bytestring[0:4]
        self.tag                    = bytestring[4:8]
        self.data_transfer_length   = bytestring[8] \
                                    | bytestring[9] << 8 \
                                    | bytestring[10] << 16 \
                                    | bytestring[11] << 24
        self.flags                  = int(bytestring[12])
        self.lun                    = int(bytestring[13] & 0x0f)
        self.cb_length              = int(bytestring[14] & 0x1f)
        #self.cb                     = bytestring[15:15+self.cb_length]
        self.cb                     = bytestring[15:]

    def __str__(self):
        s  = "sig: " + bytes_as_hex(self.signature) + "\n"
        s += "tag: " + bytes_as_hex(self.tag) + "\n"
        s += "data transfer len: " + str(self.data_transfer_length) + "\n"
        s += "flags: " + str(self.flags) + "\n"
        s += "lun: " + str(self.lun) + "\n"
        s += "command block len: " + str(self.cb_length) + "\n"
        s += "command block: " + bytes_as_hex(self.cb) + "\n"

        return s


class USBMassStorageDevice(USBDevice):
    name = "USB mass storage device"

    def __init__(self, maxusb_app, vid, pid, rev, int_class, int_sub, int_proto, disk_image_filename, verbose=0):
        self.disk_image = DiskImage(disk_image_filename, 512)

        interface = USBMassStorageInterface(maxusb_app, self.disk_image, int_class, int_sub, int_proto, verbose=verbose)

        if vid == 0x1111:
            vid = 0x154b
        if pid == 0x2222:
            pid = 0x6545
        if rev == 0x3333:
            rev = 0x0200

        config = USBConfiguration(
                maxusb_app,
                1,                                          # index
                "MassStorage config",                       # string desc
                [ interface ]                               # interfaces
        )

        USBDevice.__init__(
                self,
                maxusb_app,
                0,                      # device class
                0,                      # device subclass
                0,                      # protocol release number
                64,                     # max packet size for endpoint 0
                vid,                    # vendor id
                pid,                    # product id
                rev,                    # device revision
                "PNY",                  # manufacturer string
                "USB 2.0 FD",           # product string
                "4731020ef1914da9",     # serial number string
                [ config ],
                verbose=verbose
        )

    def disconnect(self):
        self.disk_image.close()
        USBDevice.disconnect(self)


########NEW FILE########
__FILENAME__ = USBPrinter
# USBPrinter.py 
#
# Contains class definitions to implement a USB printer device.

from mmap import mmap
import os
import time

from USB import *
from USBDevice import *
from USBConfiguration import *
from USBInterface import *
from USBEndpoint import *
from USBClass import *

from util import *

class USBPrinterClass(USBClass):
    name = "USB printer class"

    def __init__(self, maxusb_app):
     
        self.maxusb_app = maxusb_app
        self.setup_request_handlers()

    def setup_request_handlers(self):
        self.request_handlers = {
            0x00 : self.handle_get_device_ID_request,
        }


    def handle_get_device_ID_request(self, req):

        if self.maxusb_app.mode == 1:
            print (" **SUPPORTED**",end="")
            if self.maxusb_app.fplog:
                self.maxusb_app.fplog.write (" **SUPPORTED**\n")
            self.maxusb_app.stop = True

        if self.maxusb_app.testcase[1] == "Device_ID_Key1":
            device_id_key1 = self.maxusb_app.testcase[2]
        else:
            device_id_key1 = b"MFG"
        if self.maxusb_app.testcase[1] == "Device_ID_Value1":
            device_id_value1 = self.maxusb_app.testcase[2]
        else:
            device_id_value1 = b"Hewlett-Packard"
        if self.maxusb_app.testcase[1] == "Device_ID_Key2":
            device_id_key2 = self.maxusb_app.testcase[2]
        else:
            device_id_key2 = b"CMD"
        if self.maxusb_app.testcase[1] == "Device_ID_Value2":
            device_id_value2 = self.maxusb_app.testcase[2]
        else:
            device_id_value2 = b"PJL,PML,PCLXL,POSTSCRIPT,PCL"
        if self.maxusb_app.testcase[1] == "Device_ID_Key3":
            device_id_key3 = self.maxusb_app.testcase[2]
        else:
            device_id_key3 = b"MDL"
        if self.maxusb_app.testcase[1] == "Device_ID_Value3":
            device_id_value3 = self.maxusb_app.testcase[2]
        else:
            device_id_value3 = b"HP Color LaserJet CP1515n"
        if self.maxusb_app.testcase[1] == "Device_ID_Key4":
            device_id_key4 = self.maxusb_app.testcase[2]
        else:
            device_id_key4 = b"CLS"
        if self.maxusb_app.testcase[1] == "Device_ID_Value4":
            device_id_value4 = self.maxusb_app.testcase[2]
        else:
            device_id_value4 = b"PRINTER"
        if self.maxusb_app.testcase[1] == "Device_ID_Key5":
            device_id_key5 = self.maxusb_app.testcase[2]
        else:
            device_id_key5 = b"DES"
        if self.maxusb_app.testcase[1] == "Device_ID_Value5":
            device_id_value5 = self.maxusb_app.testcase[2]
        else:
            device_id_value5 = b"Hewlett-Packard Color LaserJet CP1515n"
        if self.maxusb_app.testcase[1] == "Device_ID_Key6":
            device_id_key6 = self.maxusb_app.testcase[2]
        else:
            device_id_key6 = b"MEM"
        if self.maxusb_app.testcase[1] == "Device_ID_Value6":
            device_id_value6 = self.maxusb_app.testcase[2]
        else:
            device_id_value6 = b"MEM=55MB"
        if self.maxusb_app.testcase[1] == "Device_ID_Key7":
            device_id_key7 = self.maxusb_app.testcase[2]
        else:
            device_id_key7 = b"COMMENT"
        if self.maxusb_app.testcase[1] == "Device_ID_Value7":
            device_id_value7 = self.maxusb_app.testcase[2]
        else:
            device_id_value7 = b"RES=600x8"


        device_id_length = b"\x00\xAB" # 171 bytes
        device_id_elements  =  device_id_key1 + b":" + device_id_value1 + b";"
        device_id_elements  += device_id_key2 + b":" + device_id_value2 + b";"
        device_id_elements  += device_id_key3 + b":" + device_id_value3 + b";"
        device_id_elements  += device_id_key4 + b":" + device_id_value4 + b";"
        device_id_elements  += device_id_key5 + b":" + device_id_value5 + b";"
        device_id_elements  += device_id_key6 + b":" + device_id_value6 + b";"
        device_id_elements  += device_id_key7 + b":" + device_id_value7 + b";"

        length = len(device_id_elements) + 2
        device_id_length = bytes([
        (length >> 8) & 0xff,
        (length)      & 0xff])

        device_id_response = device_id_length + device_id_elements

        self.interface.configuration.device.maxusb_app.send_on_endpoint(0, device_id_response)


class USBPrinterInterface(USBInterface):
    name = "USB printer interface"

    def __init__(self, int_num, maxusb_app, usbclass, sub, proto, verbose=0):
        self.maxusb_app = maxusb_app
        self.int_num = int_num
        self.filename = time.strftime("%Y%m%d%H%M%S", time.localtime())
        self.filename += ".pcl"
        self.writing = False


        descriptors = { }

        endpoints0 = [
            USBEndpoint(
                maxusb_app,
                1,          # endpoint address
                USBEndpoint.direction_out,
                USBEndpoint.transfer_type_bulk,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                16384,      # max packet size
                0xff,          # polling interval, see USB 2.0 spec Table 9-13
                self.handle_data_available    # handler function
            ),
            USBEndpoint(
                maxusb_app,
                0x81,          # endpoint address
                USBEndpoint.direction_in,
                USBEndpoint.transfer_type_bulk,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                16384,      # max packet size
                0,          # polling interval, see USB 2.0 spec Table 9-13
                None        # handler function
            )
        ]

        endpoints1 = [
            USBEndpoint(
                maxusb_app,
                0x0b,          # endpoint address
                USBEndpoint.direction_out,
                USBEndpoint.transfer_type_bulk,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                16384,      # max packet size
                0xff,          # polling interval, see USB 2.0 spec Table 9-13
                self.handle_data_available    # handler function
            ),
            USBEndpoint(
                maxusb_app,
                0x8b,          # endpoint address
                USBEndpoint.direction_in,
                USBEndpoint.transfer_type_bulk,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                16384,      # max packet size
                0,          # polling interval, see USB 2.0 spec Table 9-13
                None        # handler function
            )
        ]


        if self.int_num == 0:
                endpoints = endpoints0

        if self.int_num == 1:
                endpoints = endpoints1


        # TODO: un-hardcode string index (last arg before "verbose")
        USBInterface.__init__(
                self,
                maxusb_app,
                self.int_num,          # interface number
                0,          # alternate setting
                usbclass,     # interface class
                sub,          # subclass
                proto,       # protocol
                0,          # string index
                verbose,
                endpoints,
                descriptors
        )

        self.device_class = USBPrinterClass(maxusb_app)
        self.device_class.set_interface(self)

        self.is_write_in_progress = False
        self.write_cbw = None
        self.write_base_lba = 0
        self.write_length = 0
        self.write_data = b''

    def handle_data_available(self,data):

        if self.writing == False:
            print ("Writing PCL file: %s" % self.filename)

        text_buffer=""

        with open(self.filename, "ab") as out_file:
            self.writing = True
            out_file.write(data)

        x=0
        while x < len(data):
            text_buffer += chr(data[x])
            x+=1


        if 'EOJ\n' in text_buffer:
            print ("File write complete")
            out_file.close()
            self.maxusb_app.stop = True    

class USBPrinterDevice(USBDevice):
    name = "USB printer device"

    def __init__(self, maxusb_app, vid, pid, rev, int_class, int_sub, int_proto, verbose=0):

        interface1 = USBPrinterInterface(0, maxusb_app, int_class, int_sub, int_proto, verbose=verbose)

        int_class = 0xff
        int_subclass = 1
        int_proto = 1

        interface2 = USBPrinterInterface(1, maxusb_app, int_class, int_sub, int_proto, verbose=verbose)

        if vid == 0x1111:
            vid = 0x03f0
        if pid == 0x2222:
            pid = 0x4417
        if rev == 0x3333:
            rev = 0x0100

        config = USBConfiguration(
                maxusb_app,
                1,                                          # index
                "Printer",                       # string desc
                [ interface1, interface2 ]                               # interfaces
        )

        USBDevice.__init__(
                self,
                maxusb_app,
                0,                      # device class
                0,                      # device subclass
                0,                      # protocol release number
                64,                     # max packet size for endpoint 0
                vid,                    # vendor id
                pid,                    # product id
                rev,                    # device revision
                "Hewlett-Packard",      # manufacturer string
                "HP Color LaserJet CP1515n",               # product string
                "00CNC2618971",         # serial number string
                [ config ],
                verbose=verbose
        )

    def disconnect(self):
        USBDevice.disconnect(self)


########NEW FILE########
__FILENAME__ = USBSmartcard
# USBSmartcard.py
#
# Contains class definitions to implement a USB Smartcard.

# This devbice doesn't work properly yet!!!!!

from USB import *
from USBDevice import *
from USBConfiguration import *
from USBInterface import *
from USBEndpoint import *

class USBSmartcardClass(USBClass):
    name = "USB Smartcard class"

    def __init__(self, maxusb_app):

        self.maxusb_app = maxusb_app
        self.setup_request_handlers()


    def setup_request_handlers(self):
        self.request_handlers = {
            0x02 : self.handle_get_clock_frequencies
        }

    def handle_get_clock_frequencies(self, req):
        response = b'\x67\x32\x00\x00\xCE\x64\x00\x00\x9D\xC9\x00\x00\x3A\x93\x01\x00\x74\x26\x03\x00\xE7\x4C\x06\x00\xCE\x99\x0C\x00\xD7\x5C\x02\x00\x11\xF0\x03\x00\x34\x43\x00\x00\x69\x86\x00\x00\xD1\x0C\x01\x00\xA2\x19\x02\x00\x45\x33\x04\x00\x8A\x66\x08\x00\x0B\xA0\x02\x00\x73\x30\x00\x00\xE6\x60\x00\x00\xCC\xC1\x00\x00\x99\x83\x01\x00\x32\x07\x03\x00\x63\x0E\x06\x00\xB3\x22\x01\x00\x7F\xE4\x01\x00\x06\x50\x01\x00\x36\x97\x00\x00\x04\xFC\x00\x00\x53\x28\x00\x00\xA5\x50\x00\x00\x4A\xA1\x00\x00\x95\x42\x01\x00\x29\x85\x02\x00\xF8\x78\x00\x00\x3E\x49\x00\x00\x7C\x92\x00\x00\xF8\x24\x01\x00\xF0\x49\x02\x00\xE0\x93\x04\x00\xC0\x27\x09\x00\x74\xB7\x01\x00\x6C\xDC\x02\x00\xD4\x30\x00\x00\xA8\x61\x00\x00\x50\xC3\x00\x00\xA0\x86\x01\x00\x40\x0D\x03\x00\x80\x1A\x06\x00\x48\xE8\x01\x00\xBA\xDB\x00\x00\x36\x6E\x01\x00\x24\xF4\x00\x00\xDD\x6D\x00\x00\x1B\xB7\x00\x00'

        self.maxusb_app.send_on_endpoint(0, response)



class USBSmartcardInterface(USBInterface):
    name = "USB Smartcard interface"

    def __init__(self, maxusb_app, verbose=0):


        self.maxusb_app = maxusb_app

        if self.maxusb_app.testcase[1] == "icc_bLength":
            bLength = self.maxusb_app.testcase[2]
        else:
            bLength = b'\x36'

        if self.maxusb_app.testcase[1] == "icc_bDescriptorType":
            bDescriptorType = self.maxusb_app.testcase[2]
        else:
            bDescriptorType = b'\x21'   # USB-ICC
        bcdCCID = b'\x10\x01'
        if self.maxusb_app.testcase[1] == "icc_bMaxSlotIndex":
            bMaxSlotIndex = self.maxusb_app.testcase[2]
        else:
            bMaxSlotIndex = b'\x00' # index of highest available slot
        if self.maxusb_app.testcase[1] == "icc_bVoltageSupport":
            bVoltageSupport = self.maxusb_app.testcase[2]
        else:
            bVoltageSupport = b'\x07'
        if self.maxusb_app.testcase[1] == "icc_dwProtocols":
            dwProtocols = self.maxusb_app.testcase[2]
        else:
            dwProtocols = b'\x03\x00\x00\x00'
        if self.maxusb_app.testcase[1] == "icc_dwDefaultClock":
            dwDefaultClock = self.maxusb_app.testcase[2]
        else:
            dwDefaultClock = b'\xA6\x0E\x00\x00'
        if self.maxusb_app.testcase[1] == "icc_dwMaximumClock":
            dwMaximumClock = self.maxusb_app.testcase[2]
        else:
            dwMaximumClock = b'\x4C\x1D\x00\x00'
        if self.maxusb_app.testcase[1] == "icc_bNumClockSupported":
            bNumClockSupported = self.maxusb_app.testcase[2]
        else:
            bNumClockSupported = b'\x00'
        if self.maxusb_app.testcase[1] == "icc_dwDataRate":
            dwDataRate = self.maxusb_app.testcase[2]
        else:
            dwDataRate = b'\x60\x27\x00\x00'
        if self.maxusb_app.testcase[1] == "icc_dwMaxDataRate":
            dwMaxDataRate = self.maxusb_app.testcase[2]
        else:
            dwMaxDataRate = b'\xB4\xC4\x04\x00'
        if self.maxusb_app.testcase[1] == "icc_bNumDataRatesSupported":
            bNumDataRatesSupported = self.maxusb_app.testcase[2]
        else:
            bNumDataRatesSupported = b'\x00'
        if self.maxusb_app.testcase[1] == "icc_dwMaxIFSD":
            dwMaxIFSD = self.maxusb_app.testcase[2]
        else:
            dwMaxIFSD = b'\xFE\x00\x00\x00'
        if self.maxusb_app.testcase[1] == "icc_dwSynchProtocols":
            dwSynchProtocols = self.maxusb_app.testcase[2]
        else:
            dwSynchProtocols =  b'\x00\x00\x00\x00'
        if self.maxusb_app.testcase[1] == "icc_dwMechanical":
            dwMechanical = self.maxusb_app.testcase[2]
        else:
            dwMechanical = b'\x00\x00\x00\x00'
        if self.maxusb_app.testcase[1] == "icc_dwFeatures":
            dwFeatures = self.maxusb_app.testcase[2]
        else:
            dwFeatures = b'\x30\x00\x01\x00'
        if self.maxusb_app.testcase[1] == "icc_dwMaxCCIDMessageLength":
            dwMaxCCIDMessageLength = self.maxusb_app.testcase[2]
        else:
            dwMaxCCIDMessageLength = b'\x0F\x01\x00\x00'
        if self.maxusb_app.testcase[1] == "icc_bClassGetResponse":
            bClassGetResponse = self.maxusb_app.testcase[2]
        else:
            bClassGetResponse = b'\x00'
        if self.maxusb_app.testcase[1] == "icc_bClassEnvelope":
            bClassEnvelope = self.maxusb_app.testcase[2]
        else:
            bClassEnvelope = b'\x00'
        if self.maxusb_app.testcase[1] == "icc_wLcdLayout":
            wLcdLayout = self.maxusb_app.testcase[2]
        else:
            wLcdLayout = b'\x00\x00'
        if self.maxusb_app.testcase[1] == "icc_bPinSupport":
            bPinSupport = self.maxusb_app.testcase[2]
        else:
            bPinSupport = b'\x00'
        if self.maxusb_app.testcase[1] == "icc_bMaxCCIDBusySlots":
            bMaxCCIDBusySlots = self.maxusb_app.testcase[2]
        else:
            bMaxCCIDBusySlots = b'\x01'

        self.icc_descriptor =    bLength + \
                            bDescriptorType + \
                            bcdCCID + \
                            bMaxSlotIndex + \
                            bVoltageSupport + \
                            dwProtocols + \
                            dwDefaultClock + \
                            dwMaximumClock + \
                            bNumClockSupported + \
                            dwDataRate + \
                            dwMaxDataRate + \
                            bNumDataRatesSupported + \
                            dwMaxIFSD + \
                            dwSynchProtocols + \
                            dwMechanical + \
                            dwFeatures + \
                            dwMaxCCIDMessageLength + \
                            bClassGetResponse + \
                            bClassEnvelope + \
                            wLcdLayout + \
                            bPinSupport + \
                            bMaxCCIDBusySlots

        descriptors = { 
                USB.desc_type_hid    : self.icc_descriptor  # 33 is the same descriptor type code as HID
        }


        endpoint = [
            USBEndpoint(
                maxusb_app,
                3,          # endpoint number
                USBEndpoint.direction_in,
                USBEndpoint.transfer_type_interrupt,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                16384,      # max packet size
                8,         # polling interval, see USB 2.0 spec Table 9-13
                self.handle_buffer_available    # handler function
            ),
            USBEndpoint(
                maxusb_app,
                1,          # endpoint number
                USBEndpoint.direction_out,
                USBEndpoint.transfer_type_bulk,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                16384,      # max packet size
                0,         # polling interval, see USB 2.0 spec Table 9-13
                self.handle_data_available    # handler function
            ),
            USBEndpoint(
                maxusb_app,
                2,          # endpoint number
                USBEndpoint.direction_in,
                USBEndpoint.transfer_type_bulk,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                16384,      # max packet size
                0,         # polling interval, see USB 2.0 spec Table 9-13
                None    # handler function
            )
        ]



        # TODO: un-hardcode string index (last arg before "verbose")
        USBInterface.__init__(
                self,
                maxusb_app,
                0,          # interface number
                0,          # alternate setting
                0x0b,       # 3 interface class
                0,          # 0 subclass
                0,          # 0 protocol
                0,          # string index
                verbose,
                endpoint,
                descriptors
        )

        self.device_class = USBSmartcardClass(maxusb_app)
        self.trigger = False
        self.initial_data = b'\x50\x03'


    def handle_data_available(self,data):


        if self.maxusb_app.mode == 1:
            print (" **SUPPORTED**",end="")
            if self.maxusb_app.fplog:
                self.maxusb_app.fplog.write (" **SUPPORTED**\n")
            self.maxusb_app.stop = True

#        print ("Received:",data)
        command = ord(data[:1])
#        print ("command=%02x" % command)
        bSeq = data[6:7]
#        print ("seq=",ord(bSeq))
        bReserved = ord(data[7:8])
#        print ("bReserved=",bReserved) 

        if self.maxusb_app.server_running == True:
            try:
                self.maxusb_app.netserver_from_endpoint_sd.send(data)
            except:
                print ("Error: No network client connected")

            while True:
                if len(self.maxusb_app.reply_buffer) > 0:
                    self.maxusb_app.send_on_endpoint(2, self.maxusb_app.reply_buffer)
                    self.maxusb_app.reply_buffer = ""
                    break


        elif command == 0x61: # PC_to_RDR_SetParameters

            if self.maxusb_app.testcase[1] == "SetParameters_bMessageType":
                bMessageType = self.maxusb_app.testcase[2]
            else:
                bMessageType = b'\x82'  # RDR_to_PC_Parameters
            if self.maxusb_app.testcase[1] == "SetParameters_dwLength":
                dwLength = self.maxusb_app.testcase[2]
            else:
                dwLength = b'\x05\x00\x00\x00' # Message-specific data length
            if self.maxusb_app.testcase[1] == "SetParameters_bSlot":
                bSlot = self.maxusb_app.testcase[2]
            else:
                bSlot = b'\x00' # fixed for legacy reasons
            if self.maxusb_app.testcase[1] == "SetParameters_bStatus":
                bStatus = self.maxusb_app.testcase[2]
            else:
                bStatus = b'\x00' # reserved
            if self.maxusb_app.testcase[1] == "SetParameters_bError":
                bError = self.maxusb_app.testcase[2]
            else:
                bError = b'\x80'
            if self.maxusb_app.testcase[1] == "SetParameters_bProtocolNum":
                bProtocolNum = self.maxusb_app.testcase[2]
            else:
                bProtocolNum = b'\x00'

            abProtocolDataStructure = b'\x11\x00\x00\x0a\x00'
            
            response =  bMessageType + \
                        dwLength + \
                        bSlot + \
                        bSeq + \
                        bStatus + \
                        bError + \
                        bProtocolNum + \
                        abProtocolDataStructure      

 
        elif command == 0x62: # PC_to_RDR_IccPowerOn

            if bReserved == 2:

                if self.maxusb_app.testcase[1] == "IccPowerOn_bMessageType":
                    bMessageType = self.maxusb_app.testcase[2]
                else:
                    bMessageType = b'\x80'  # RDR_to_PC_DataBlock
                if self.maxusb_app.testcase[1] == "IccPowerOn_dwLength":
                    dwLength = self.maxusb_app.testcase[2]
                else:
                    dwLength = b'\x12\x00\x00\x00' # Message-specific data length
                if self.maxusb_app.testcase[1] == "IccPowerOn_bSlot":
                    bSlot = self.maxusb_app.testcase[2]
                else:
                    bSlot = b'\x00' # fixed for legacy reasons
                if self.maxusb_app.testcase[1] == "IccPowerOn_bStatus":
                    bStatus = self.maxusb_app.testcase[2]
                else:
                    bStatus = b'\x00'
                if self.maxusb_app.testcase[1] == "IccPowerOn_bError":
                    bError = self.maxusb_app.testcase[2]
                else:
                    bError = b'\x80'
                if self.maxusb_app.testcase[1] == "IccPowerOn_bChainParameter":
                    bChainParameter = self.maxusb_app.testcase[2]
                else:
                    bChainParameter = b'\x00'
                abData = b'\x3b\x6e\x00\x00\x80\x31\x80\x66\xb0\x84\x12\x01\x6e\x01\x83\x00\x90\x00'
                response =  bMessageType + \
                            dwLength + \
                            bSlot + \
                            bSeq + \
                            bStatus + \
                            bError + \
                            bChainParameter + \
                            abData

            else:
                if self.maxusb_app.testcase[1] == "IccPowerOn_bMessageType":
                    bMessageType = self.maxusb_app.testcase[2]
                else:
                    bMessageType = b'\x80'  # RDR_to_PC_DataBlock
                if self.maxusb_app.testcase[1] == "IccPowerOn_dwLength":
                    dwLength = self.maxusb_app.testcase[2]
                else:
                    dwLength = b'\x00\x00\x00\x00' # Message-specific data length
                if self.maxusb_app.testcase[1] == "IccPowerOn_bSlot":
                    bSlot = self.maxusb_app.testcase[2]
                else:
                    bSlot = b'\x00' # fixed for legacy reasons
                if self.maxusb_app.testcase[1] == "IccPowerOn_bStatus":
                    bStatus = self.maxusb_app.testcase[2]
                else:
                    bStatus = b'\x40'
                if self.maxusb_app.testcase[1] == "IccPowerOn_bError":
                    bError = self.maxusb_app.testcase[2]
                else:
                    bError = b'\xfe'
                if self.maxusb_app.testcase[1] == "IccPowerOn_bChainParameter":
                    bChainParameter = self.maxusb_app.testcase[2]
                else:
                    bChainParameter = b'\x00'

                response =  bMessageType + \
                            dwLength + \
                            bSlot + \
                            bSeq + \
                            bStatus + \
                            bError + \
                            bChainParameter



        elif command == 0x63: # PC_to_RDR_IccPowerOff

            if self.maxusb_app.testcase[1] == "IccPowerOff_bMessageType":
                bMessageType = self.maxusb_app.testcase[2]
            else:
                bMessageType = b'\x81'  # PC_to_RDR_IccPowerOff
            if self.maxusb_app.testcase[1] == "IccPowerOff_dwLength":
                dwLength = self.maxusb_app.testcase[2]
            else:
                dwLength = b'\x00\x00\x00\x00' # Message-specific data length
            if self.maxusb_app.testcase[1] == "IccPowerOff_bSlot":
                bSlot = self.maxusb_app.testcase[2]
            else:
                bSlot = b'\x00' # fixed for legacy reasons
            if self.maxusb_app.testcase[1] == "IccPowerOff_abRFU":
                abRFU = self.maxusb_app.testcase[2]            
            else:
                abRFU = b'\x01' # reserved

            response =  bMessageType + \
                        dwLength + \
                        bSlot + \
                        bSeq + \
                        abRFU


        elif command == 0x65: # PC_to_RDR_GetSlotStatus


            bMessageType = b'\x81'  # RDR_to_PC_SlotStatus
            dwLength = b'\x00\x00\x00\x00' # Message-specific data length
            bSlot = b'\x00'
            bStatus = b'\x01'
            bError = b'\x00'
            bClockStatus = b'\x00' # reserved

            response =  bMessageType + \
                        dwLength + \
                        bSlot + \
                        bSeq + \
                        bStatus + \
                        bError + \
                        bClockStatus




                    

        elif command == 0x6b: # PC_to_RDR_Escape

           
            bMessageType = b'\x83'  # RDR_to_PC_Escape
            dwLength = b'\x00\x00\x00\x00' # Message-specific data length
            bSlot = b'\x00'
            bStatus = b'\x41'
            bError = b'\x0a'
            bRFU = b'\x00' # reserved

            response =  bMessageType + \
                        dwLength + \
                        bSlot + \
                        bSeq + \
                        bStatus + \
                        bError + \
                        bRFU


        elif command == 0x6f: # PC_to_RDR_XfrBlock message

            if self.maxusb_app.testcase[1] == "XfrBlock_bMessageType":
                bMessageType = self.maxusb_app.testcase[2]
            else:
                bMessageType = b'\x80'  # RDR_to_PC_DataBlock
            if self.maxusb_app.testcase[1] == "XfrBlock_dwLength":
                dwLength = self.maxusb_app.testcase[2]
            else:
                dwLength = b'\x02\x00\x00\x00' # Message-specific data length
            if self.maxusb_app.testcase[1] == "XfrBlock_bSlot":
                bSlot = self.maxusb_app.testcase[2]
            else:
                bSlot = b'\x00' # fixed for legacy reasons
            if self.maxusb_app.testcase[1] == "XfrBlock_bStatus":
                bStatus = self.maxusb_app.testcase[2]
            else:
                bStatus = b'\x00' # reserved
            if self.maxusb_app.testcase[1] == "XfrBlock_bError":
                bError = self.maxusb_app.testcase[2]
            else:
                bError = b'\x80'
            if self.maxusb_app.testcase[1] == "XfrBlock_bChainParameter":
                bChainParameter = self.maxusb_app.testcase[2]
            else:
                bChainParameter = b'\x00'
            abData = b'\x6a\x82' 

            response =  bMessageType + \
                        dwLength + \
                        bSlot + \
                        bSeq + \
                        bStatus + \
                        bError + \
                        bChainParameter + \
                        abData

        elif command == 0x73: # PC_to_RDR_SetDataRateAndClockFrequency

            if self.maxusb_app.testcase[1] == "SetDataRateAndClockFrequency_bMessageType":
                bMessageType = self.maxusb_app.testcase[2]
            else:
                bMessageType = b'\x84'  # RDR_to_PC_DataRateAndClockFrequency
            if self.maxusb_app.testcase[1] == "SetDataRateAndClockFrequency_dwLength":
                dwLength = self.maxusb_app.testcase[2]
            else:
                dwLength = b'\x08\x00\x00\x00' # Message-specific data length
            if self.maxusb_app.testcase[1] == "SetDataRateAndClockFrequency_bSlot":
                bSlot = self.maxusb_app.testcase[2]
            else:
                bSlot = b'\x00' # fixed for legacy reasons
            if self.maxusb_app.testcase[1] == "SetDataRateAndClockFrequency_bStatus":
                bStatus = self.maxusb_app.testcase[2]
            else:
                bStatus = b'\x00' # reserved
            if self.maxusb_app.testcase[1] == "SetDataRateAndClockFrequency_bError":
                bError = self.maxusb_app.testcase[2]
            else:
                bError = b'\x80'
            if self.maxusb_app.testcase[1] == "SetDataRateAndClockFrequency_bRFU":
                bRFU = self.maxusb_app.testcase[2]
            else:
                bRFU = b'\x80'
            if self.maxusb_app.testcase[1] == "SetDataRateAndClockFrequency_dwClockFrequency":
                dwClockFrequency = self.maxusb_app.testcase[2]
            else:
                dwClockFrequency = b'\xA6\x0E\x00\x00'

            if self.maxusb_app.testcase[1] == "SetDataRateAndClockFrequency_dwDataRate":
                dwDataRate = self.maxusb_app.testcase[2]
            else:
                dwDataRate = b'\x60\x27\x00\x00' 

            response =  bMessageType + \
                        dwLength + \
                        bSlot + \
                        bSeq + \
                        bStatus + \
                        bError + \
                        bRFU + \
                        dwClockFrequency + \
                        dwDataRate

        else:
            print ("Received Smartcard command not understood") 
            response = b''

        if self.maxusb_app.server_running == False:
            self.configuration.device.maxusb_app.send_on_endpoint(2, response)


    def handle_buffer_available(self):

        if self.trigger == False:
            self.configuration.device.maxusb_app.send_on_endpoint(3, self.initial_data)
            self.trigger = True



class USBSmartcardDevice(USBDevice):
    name = "USB Smartcard device"

    def __init__(self, maxusb_app, vid, pid, rev, verbose=0):



        interface = USBSmartcardInterface(maxusb_app, verbose=verbose)


        if vid == 0x1111:
            vid = 0x0bda
        if pid == 0x2222:
            pid = 0x0165
        if rev == 0x3333:
            rev = 0x6123

        config = USBConfiguration(
                maxusb_app,
                1,                                          # index
                "Emulated Smartcard",    # string desc
                [ interface ]                  # interfaces
        )

        USBDevice.__init__(
                self,
                maxusb_app,
                0,                      # 0 device class
		        0,                      # device subclass
                0,                      # protocol release number
                64,                     # max packet size for endpoint 0
		        vid,                    # vendor id
                pid,                    # product id
		        rev,                    # device revision
                "Generic",              # manufacturer string
                "Smart Card Reader Interface",   # product string
                "20070818000000000",    # serial number string
                [ config ],
                verbose=verbose
        )


########NEW FILE########
__FILENAME__ = USBVendorSpecific
# USBVendorSpecific.py
#

from USB import *
from USBDevice import *
from USBConfiguration import *
from USBInterface import *
from USBEndpoint import *
from USBVendor import *


class USBVendorVendor(USBVendor):
    name = "USB vendor"

    def setup_request_handlers(self):
        self.request_handlers = {
             0 : self.handle_reset_request
        }

    def handle_reset_request(self, req):
        if self.verbose > 0:
            print(self.name, "received reset request")

        self.device.maxusb_app.send_on_endpoint(0, b'')



class USBVendorClass(USBClass):
    name = "USB Vendor class"

    def __init__(self, maxusb_app):

        self.maxusb_app = maxusb_app
        self.setup_request_handlers()

    def setup_request_handlers(self):
        self.request_handlers = {
            0x01 : self.handle_get_report
        }

    def handle_get_report(self, req):
        response = b''
        self.maxusb_app.send_on_endpoint(0, response)




class USBVendorInterface(USBInterface):
    name = "USB Vendor interface"

    def __init__(self, maxusb_app, verbose=0):

        self.maxusb_app = maxusb_app

        descriptors = { }


        endpoint = [
            USBEndpoint(
                maxusb_app,
                3,          # endpoint number
                USBEndpoint.direction_in,
                USBEndpoint.transfer_type_interrupt,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                16384,      # max packet size
                8,         # polling interval, see USB 2.0 spec Table 9-13
                self.handle_buffer_available    # handler function
            ),
            USBEndpoint(
                maxusb_app,
                1,          # endpoint number
                USBEndpoint.direction_out,
                USBEndpoint.transfer_type_bulk,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                16384,      # max packet size
                0,         # polling interval, see USB 2.0 spec Table 9-13
                self.handle_data_available    # handler function
            ),
            USBEndpoint(
                maxusb_app,
                2,          # endpoint number
                USBEndpoint.direction_in,
                USBEndpoint.transfer_type_bulk,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                16384,      # max packet size
                0,         # polling interval, see USB 2.0 spec Table 9-13
                None    # handler function
            )
        ]



        # TODO: un-hardcode string index (last arg before "verbose")
        USBInterface.__init__(
                self,
                maxusb_app,
                0,          # interface number
                0,          # alternate setting
                0xff,       # 3 interface class
                0xff,          # 0 subclass
                0xff,          # 0 protocol
                0,          # string index
                verbose,
                endpoint,
                descriptors
        )

        self.device_class = USBVendorClass(maxusb_app)


    def handle_data_available(self,data):
        return        


    def handle_buffer_available(self):
        return



class USBVendorDevice(USBDevice):
    name = "USB Vendor device"

    def __init__(self, maxusb_app, vid, pid, rev, verbose=0):


        interface = USBVendorInterface(maxusb_app, verbose=verbose)

        config = USBConfiguration(
                maxusb_app,
                1,                                          # index
                "Vendor device",    # string desc
                [ interface ]                  # interfaces
        )

        USBDevice.__init__(
                self,
                maxusb_app,
                0xff,                   # 0 device class
		        0xff,                   # device subclass
                0xff,                   # protocol release number
                64,                     # max packet size for endpoint 0
		        vid,                    # vendor id
                pid,                    # product id
		        rev,                    # device revision
                "Vendor",              # manufacturer string
                "Product",   # product string
                "00000000",    # serial number string
                [ config ],
                verbose=verbose
        )

        self.device_vendor = USBVendorVendor()
        self.device_vendor.set_device(self)



########NEW FILE########
__FILENAME__ = device_class_data
supported_devices = [
[1,1,0],
[1,2,0],
[2,2,1],
[2,3,0xff],
[2,6,0],
[3,0,0],
[6,1,1],
[7,1,2],
[8,6,0x50],
[9,0,0],
[0x0a,0,0],
[0x0b,0,0]
]

device_class_list = [
["Audio", 1],
["CDC Control", 2],
["Human Interface Device", 3],
#5 physical
["Image", 6],
["Printer", 7],
["Mass Storage", 8],
["Hub", 9],
["CDC Data", 10],
["Smart Card", 11],
["Content Security", 13],
["Video", 14],
["Personal Healthcare", 15],
# Diagnostic devices
# Wireless controller
["Application specific", 254]
]

device_subclass_list = [
[1, "Sub-class undefined", 0],
[1, "Audio control", 1],
[1, "Audio streaming", 2],
[1, "Midi streaming", 3],
[2, "Direct Line Control Model", 1],
[2, "Abstract Control Model", 2],
[2, "Telephone Control Model", 3],
[2, "Multi-Channel Control Model", 4],
[2, "CAPI Control Model", 5],
[2, "Ethernet Networking Control Model", 6],
[2, "ATM Networking Control Model", 7],
[2, "Wireless Handset Control Model", 8],
[2, "Device Management", 9],
[2, "Mobile Direct Line Model", 10],
[2, "OBEX", 11],
[2, "Ethernet Emulation Model", 12],
[2, "Network Control Model", 13],
[3, "No subclass", 0],
[3, "Boot interface", 1],
[6, "Still image capture device", 1],
[7, "Default", 1],
[8, "De facto use", 0],
[8, "RPC", 1],
[8, "MMC-5 (ATAPI)", 2],
[8, "QIC-157 (obsolete)", 3],
[8, "UFI", 4],
[8, "SFF-8070i (obsolete)", 5],
[8, "SCSI", 6],
[8, "LSD FS", 7],
[8, "IEE 1667", 8],
[8, "Vendor specific", 255],
[9, "Default", 0],
[10, "Default", 0],
[11, "Default", 0],
[13, "Default", 0],
[14, "Undefined", 0],
[14, "Video Control", 1],
[14, "Video streaming", 2],
[14, "Video Interface Collection", 3],
[15, "Default", 0],
[254, "DFU: Upgrade code", 1],
[254, "IrDA Bridge", 2],
[254, "Test and Measurement", 3]
]


device_protocol_list = [
[1, "PR Protocol undefined", 0],
[2, "No class-specific protocol required", 0],
[2, "AT commands V.250", 1],
[2, "AT commands specified by PCCA-101", 2],
[2, "AT commands specified by PCCA-101 and Annex O", 3],
[2, "AT commands specified by GSM 07.07", 4],
[2, "AT commands specified by 3GPP 27.007", 5],
[2, "AT commands specified by TIA for CDMA", 6],
[2, "Ethernet Emulation Model", 7],
[2, "External protocol", 254],
[2, "Vendor specific", 255],
[3, "None", 0],
[3, "Keyboard", 1],
[3, "Mouse", 2],
[6, "Bulk-only protocol", 1],
[7, "Unidirectional interface", 1],
[7, "Bidirectional interface", 2],
[7, "1284.4 compatible bi-directional interface", 3],
[7, "Vendor specific", 255],
[8, "CBI with command completion interrupt", 0],
[8, "CBI without command completion interrupt", 1],
[8, "Obsolete", 2],
[8, "BBB", 80],
[8, "UAS", 98],
[8, "Vendor specific", 255],
[9, "Default", 0],
[10, "Default", 0],
[10, "Network Transfer Block", 1],
[10, "ISDN BRI physical interface protocol", 48],
[10, "HDLC", 49],
[10, "Transparent", 50],
[10, "Q.921 management protocol", 80],
[10, "Q.921 data link protocol", 81],
[10, "Q.921 TEI-multiplexor", 82],
[10, "V.42bis", 144],
[10, "Q.931/Euro-ISDN", 145],
[10, "V.120", 146],
[10, "CAPI2.0", 147],
[10, "Host based driver", 253],
[10, "Protocol unit functional descriptor", 254],
[10, "Vendor specific", 255],
[11, "Default", 0],
[13, "Default", 0],
[14, "Undefined", 0],
[14, "Protocol 15", 1],
[15, "Default", 0],
[254, "DFU: Runtime protocol", 1],
[254, "IrDA Bridge", 0],
[254, "Test and Measurement: default", 0],
[254, "Test and Measurement: USB488 interface", 1]

]


########NEW FILE########
__FILENAME__ = Facedancer
# Facedancer.py
#
# Contains class definitions for Facedancer, FacedancerCommand, FacedancerApp,
# and GoodFETMonitorApp.

from util import *

class Facedancer:
    def __init__(self, serialport, verbose=0):
        self.serialport = serialport
        self.verbose = verbose

        self.reset()
        self.monitor_app = GoodFETMonitorApp(self, verbose=self.verbose)
        self.monitor_app.announce_connected()

    def halt(self):
        self.serialport.setRTS(1)
        self.serialport.setDTR(1)

    def reset(self):
        if self.verbose > 1:
            print("Facedancer resetting...")

        self.halt()
        self.serialport.setDTR(0)

        c = self.readcmd()

        if self.verbose > 0:
            print("Facedancer reset")

    def read(self, n):
        """Read raw bytes."""

        b = self.serialport.read(n)

        if self.verbose > 3:
            print("Facedancer received", len(b), "bytes;",
                    self.serialport.inWaiting(), "bytes remaining")

        if self.verbose > 2:
            print("Facedancer Rx:", bytes_as_hex(b))

        return b

    def readcmd(self):
        """Read a single command."""

        b = self.read(4)

        app = b[0]
        verb = b[1]
        n = b[2] + (b[3] << 8)

        if n > 0:
            data = self.read(n)
        else:
            data = b''

        if len(data) != n:
            raise ValueError('Facedancer expected ' + str(n) \
                    + ' bytes but received only ' + str(len(data)))

        cmd = FacedancerCommand(app, verb, data)

        if self.verbose > 1:
            print("Facedancer Rx command:", cmd)

        return cmd

    def write(self, b):
        """Write raw bytes."""

        if self.verbose > 2:
            print("Facedancer Tx:", bytes_as_hex(b))

        self.serialport.write(b)

    def writecmd(self, c):
        """Write a single command."""
        self.write(c.as_bytestring())

        if self.verbose > 1:
            print("Facedancer Tx command:", c)


class FacedancerCommand:
    def __init__(self, app=None, verb=None, data=None):
        self.app = app
        self.verb = verb
        self.data = data

    def __str__(self):
        s = "app 0x%02x, verb 0x%02x, len %d" % (self.app, self.verb,
                len(self.data))

        if len(self.data) > 0:
            s += ", data " + bytes_as_hex(self.data)

        return s

    def long_string(self):
        s = "app: " + str(self.app) + "\n" \
          + "verb: " + str(self.verb) + "\n" \
          + "len: " + str(len(self.data))

        if len(self.data) > 0:
            try:
                s += "\n" + self.data.decode("utf-8")
            except UnicodeDecodeError:
                s += "\n" + bytes_as_hex(self.data)

        return s

    def as_bytestring(self):
        n = len(self.data)

        b = bytearray(n + 4)
        b[0] = self.app
        b[1] = self.verb
        b[2] = n & 0xff
        b[3] = n >> 8
        b[4:] = self.data

        return b


class FacedancerApp:
    app_name = "override this"
    app_num = 0x00

    def __init__(self, device, verbose=0):
        self.device = device
        self.verbose = verbose

        self.init_commands()

        if self.verbose > 0:
            print(self.app_name, "initialized")

    def init_commands(self):
        pass

    def enable(self):
        for i in range(3):
            self.device.writecmd(self.enable_app_cmd)
            self.device.readcmd()

        if self.verbose > 0:
            print(self.app_name, "enabled")


class GoodFETMonitorApp(FacedancerApp):
    app_name = "GoodFET monitor"
    app_num = 0x00

    def read_byte(self, addr):
        d = [ addr & 0xff, addr >> 8 ]
        cmd = FacedancerCommand(0, 2, d)

        self.device.writecmd(cmd)
        resp = self.device.readcmd()

        return resp.data[0]

    def get_infostring(self):
        return bytes([ self.read_byte(0xff0), self.read_byte(0xff1) ])

    def get_clocking(self):
        return bytes([ self.read_byte(0x57), self.read_byte(0x56) ])

    def print_info(self):
        infostring = self.get_infostring()
        clocking = self.get_clocking()

        print("MCU", bytes_as_hex(infostring, delim=""))
        print("clocked at", bytes_as_hex(clocking, delim=""))

    def list_apps(self):
        cmd = FacedancerCommand(self.app_num, 0x82, b'0x0')
        self.device.writecmd(cmd)

        resp = self.device.readcmd()
        print("build date:", resp.data.decode("utf-8"))

        print("firmware apps:")
        while True:
            resp = self.device.readcmd()
            if len(resp.data) == 0:
                break
            print(resp.data.decode("utf-8"))

    def echo(self, s):
        b = bytes(s, encoding="utf-8")

        cmd = FacedancerCommand(self.app_num, 0x81, b)
        self.device.writecmd(cmd)

        resp = self.device.readcmd()

        return resp.data == b

    def announce_connected(self):
        cmd = FacedancerCommand(self.app_num, 0xb1, b'')
        self.device.writecmd(cmd)
        resp = self.device.readcmd()


########NEW FILE########
__FILENAME__ = MAXUSBApp
# MAXUSBApp.py
#
# Contains class definition for MAXUSBApp.

from util import *
from Facedancer import *
from USB import *
from USBDevice import USBDeviceRequest
import sys

class MAXUSBApp(FacedancerApp):
    app_name = "MAXUSB"
    app_num = 0x40

    reg_ep0_fifo                    = 0x00
    reg_ep1_out_fifo                = 0x01
    reg_ep2_in_fifo                 = 0x02
    reg_ep3_in_fifo                 = 0x03
    reg_setup_data_fifo             = 0x04
    reg_ep0_byte_count              = 0x05
    reg_ep1_out_byte_count          = 0x06
    reg_ep2_in_byte_count           = 0x07
    reg_ep3_in_byte_count           = 0x08
    reg_ep_stalls                   = 0x09
    reg_clr_togs                    = 0x0a
    reg_endpoint_irq                = 0x0b
    reg_endpoint_interrupt_enable   = 0x0c
    reg_usb_irq                     = 0x0d
    reg_usb_interrupt_enable        = 0x0e
    reg_usb_control                 = 0x0f
    reg_cpu_control                 = 0x10
    reg_pin_control                 = 0x11
    reg_revision                    = 0x12
    reg_function_address            = 0x13
    reg_io_pins                     = 0x14

    # bitmask values for reg_endpoint_irq = 0x0b
    is_setup_data_avail             = 0x20     # SUDAVIRQ
    is_in3_buffer_avail             = 0x10     # IN3BAVIRQ
    is_in2_buffer_avail             = 0x08     # IN2BAVIRQ
    is_out1_data_avail              = 0x04     # OUT1DAVIRQ
    is_out0_data_avail              = 0x02     # OUT0DAVIRQ
    is_in0_buffer_avail             = 0x01     # IN0BAVIRQ

    # bitmask values for reg_usb_control = 0x0f
    usb_control_vbgate              = 0x40
    usb_control_connect             = 0x08

    # bitmask values for reg_pin_control = 0x11
    interrupt_level                 = 0x08
    full_duplex                     = 0x10

    def __init__(self, device, logfp, mode, testcase, verbose=0):
        FacedancerApp.__init__(self, device, verbose)

        self.connected_device = None

        self.mode = mode
        self.netserver_to_endpoint_sd = 0
        self.netserver_from_endpoint_sd = 0
        self.server_running = False
        self.reply_buffer = ""
        self.testcase = testcase

        self.fplog = 0

        if logfp != 0:
            self.fplog = logfp

        self.fingerprint = []

        self.stop = False
        self.retries = False 
        self.enable()

        if verbose > 0:
            rev = self.read_register(self.reg_revision)
            print(self.app_name, "revision", rev)

        # set duplex and negative INT level (from GoodFEDMAXUSB.py)
        self.write_register(self.reg_pin_control,
                self.full_duplex | self.interrupt_level)

    def init_commands(self):
        self.read_register_cmd  = FacedancerCommand(self.app_num, 0x00, b'')
        self.write_register_cmd = FacedancerCommand(self.app_num, 0x00, b'')
        self.enable_app_cmd     = FacedancerCommand(self.app_num, 0x10, b'')
        self.ack_cmd            = FacedancerCommand(self.app_num, 0x00, b'\x01')

    def read_register(self, reg_num, ack=False):
        if self.verbose > 1:
            print(self.app_name, "reading register 0x%02x" % reg_num)

        self.read_register_cmd.data = bytearray([ reg_num << 3, 0 ])
        if ack:
            self.write_register_cmd.data[0] |= 1

        self.device.writecmd(self.read_register_cmd)
    
        resp = self.device.readcmd()

        if self.verbose > 2:
            print(self.app_name, "read register 0x%02x has value 0x%02x" %
                    (reg_num, resp.data[1]))

        return resp.data[1]

    def write_register(self, reg_num, value, ack=False):
        if self.verbose > 2:
            print(self.app_name, "writing register 0x%02x with value 0x%02x" %
                    (reg_num, value))

        self.write_register_cmd.data = bytearray([ (reg_num << 3) | 2, value ])
        if ack:
            self.write_register_cmd.data[0] |= 1

        self.device.writecmd(self.write_register_cmd)
        self.device.readcmd()

    def get_version(self):
        return self.read_register(self.reg_revision)

    def ack_status_stage(self):
        if self.verbose > 5:
            print(self.app_name, "sending ack!")

        self.device.writecmd(self.ack_cmd)
        self.device.readcmd()

    def connect(self, usb_device):
        self.write_register(self.reg_usb_control, self.usb_control_vbgate |
                self.usb_control_connect)

        self.connected_device = usb_device

        if self.verbose > 0:
            print(self.app_name, "connected device", self.connected_device.name)

    def disconnect(self):
        self.write_register(self.reg_usb_control, self.usb_control_vbgate)

        if self.verbose > 0:
            print(self.app_name, "disconnected device", self.connected_device.name)
        self.connected_device = None


    def clear_irq_bit(self, reg, bit):
        self.write_register(reg, bit)

    def read_bytes(self, reg, n):
        if self.verbose > 2:
            print(self.app_name, "reading", n, "bytes from register", reg)

        data = bytes([ (reg << 3) ] + ([0] * n))
        cmd = FacedancerCommand(self.app_num, 0x00, data)

        self.device.writecmd(cmd)
        resp = self.device.readcmd()

        if self.verbose > 3:
            print(self.app_name, "read", len(resp.data) - 1, "bytes from register", reg)

        return resp.data[1:]

    def write_bytes(self, reg, data):
        data = bytes([ (reg << 3) | 3 ]) + data
        cmd = FacedancerCommand(self.app_num, 0x00, data)

        self.device.writecmd(cmd)
        self.device.readcmd() # null response

        if self.verbose > 3:
            print(self.app_name, "wrote", len(data) - 1, "bytes to register", reg)

    # HACK: but given the limitations of the MAX chips, it seems necessary
    def send_on_endpoint(self, ep_num, data):
        if ep_num == 0:
            fifo_reg = self.reg_ep0_fifo
            bc_reg = self.reg_ep0_byte_count
        elif ep_num == 2:
            fifo_reg = self.reg_ep2_in_fifo
            bc_reg = self.reg_ep2_in_byte_count
        elif ep_num == 3:
            fifo_reg = self.reg_ep3_in_fifo
            bc_reg = self.reg_ep3_in_byte_count
        else:
            raise ValueError('endpoint ' + str(ep_num) + ' not supported')

        # FIFO buffer is only 64 bytes, must loop
        while len(data) > 64:
            self.write_bytes(fifo_reg, data[:64])
            self.write_register(bc_reg, 64, ack=True)

            data = data[64:]

        self.write_bytes(fifo_reg, data)
        self.write_register(bc_reg, len(data), ack=True)

        if self.verbose > 1:
            print(self.app_name, "wrote", bytes_as_hex(data), "to endpoint",
                    ep_num)

    # HACK: but given the limitations of the MAX chips, it seems necessary
    def read_from_endpoint(self, ep_num):
        if ep_num != 1:
            return b''

        byte_count = self.read_register(self.reg_ep1_out_byte_count)
        if byte_count == 0:
            return b''

        data = self.read_bytes(self.reg_ep1_out_fifo, byte_count)

        if self.verbose > 1:
            print(self.app_name, "read", bytes_as_hex(data), "from endpoint",
                    ep_num)

        return data

    def stall_ep0(self):
        if self.verbose > 0:
            print(self.app_name, "stalling endpoint 0")

        self.write_register(self.reg_ep_stalls, 0x23)

    def service_irqs(self):
        count = 0
        tmp_irq = 0

        while self.stop == False:
            irq = self.read_register(self.reg_endpoint_irq)

            if irq == tmp_irq:
                count +=1
            else:
                count = 0

            if count == 10000 and self.mode == 2:     #This needs to be configurable
                self.stop = True
                if self.fplog:
                    self.fplog.write("\n")
                return

            if count == 2000 and (self.mode == 3 or self.mode == 1 or self.mode == 4):		#This needs to be configurable
                self.stop = True

                if len(self.fingerprint) == 0:
                    print ("\n*** No response from host - check if the host is still functioning correctly ***\n")
                    self.disconnect()
                    sys.exit()


                self.disconnect()

                if self.fplog:
                    self.fplog.write("\n")

                return

            if self.verbose > 3:
                print(self.app_name, "read endpoint irq: 0x%02x" % irq)

            if self.verbose > 2:
                if irq & ~ (self.is_in0_buffer_avail \
                        | self.is_in2_buffer_avail | self.is_in3_buffer_avail):
                    print(self.app_name, "notable irq: 0x%02x" % irq)

            if irq & self.is_setup_data_avail:
                self.clear_irq_bit(self.reg_endpoint_irq, self.is_setup_data_avail)

                b = self.read_bytes(self.reg_setup_data_fifo, 8)
                req = USBDeviceRequest(b)
                self.connected_device.handle_request(req)

            if irq & self.is_out1_data_avail:
                data = self.read_from_endpoint(1)
                if data:
                    self.connected_device.handle_data_available(1, data)
                self.clear_irq_bit(self.reg_endpoint_irq, self.is_out1_data_avail)

            if irq & self.is_in2_buffer_avail:
                try:
                    self.connected_device.handle_buffer_available(2)
                except:
                    pass

            if irq & self.is_in3_buffer_avail:
                try:
                    self.connected_device.handle_buffer_available(3)
                except:
                    pass
            tmp_irq = irq
        self.disconnect()

########NEW FILE########
__FILENAME__ = testcases
testcases_class_independent = [
["Device_bLength_null","dev_bLength",0],
["Device_bLength_lower","dev_bLength",1],
["Device_bLength_higher","dev_bLength",20],
["Device_bLength_max","dev_bLength",0xff],
["Device_bDescriptorType_null","dev_bDescriptorType",0],
["Device_bDescriptorType_invalid","dev_bDescriptorType",0xff],
["Device_bMaxPacketSize0_null","dev_bMaxPacketSize0",0],
["Device_bMaxPacketSize0_max","dev_bMaxPacketSize0",0xff],

["String_Manufacturer_overflow","string_Manufacturer","A" * 126],
["String_Product_overflow","string_Product","A" * 126],
["String_Serial_overflow","string_Serial","A" * 126],
["String_Manufacturer_formatstring","string_Manufacturer","%x%n%n"],
["String_Product_formatstring","string_Product","%x%n%n"],
["String_Serial_formatstring","string_Serial","%x%n%n"],

["Configuration_bLength_null","conf_bLength",0],
["Configuration_bLength_lower","conf_bLength",1],
["Configuration_bLength_higher","conf_bLength",10],
["Configuration_bLength_max","conf_bLength",10],
["Configuration_bDescriptorType_null","conf_bDescriptorType",0],
["Configuration_bDescriptorType_invalid","conf_bDescriptorType",0xff],
["Configuration_wTotalLength_null","conf_wTotalLength",0],
["Configuration_wTotalLength_lower","conf_wTotalLength",1],
["Configuration_wTotalLength_higher","conf_wTotalLength",0xfff0],
["Configuration_wTotalLength_max","conf_wTotalLength",0xffff],
["Configuration_bNumInterfaces_null","conf_bNumInterfaces",0],
["Configuration_bNumInterfaces_higher","conf_bNumInterfaces",0xf0],
["Configuration_bNumInterfaces_max","conf_bNumInterfaces",0xff],

["Interface_bLength_null","int_bLength",0],
["Interface_bLength_lower","int_bLength",1],
["Interface_bLength_higher","int_bLength",0xf0],
["Interface_bLength_max","int_bLength",0xff],
["Interface_bDescriptorType_null","int_bDescriptorType",0],
["Interface_bDescriptorType_invalid","int_bDescriptorType",0xff],
["Interface_bNumEndpoints_null","int_bNumEndpoints",0],
["Interface_bNumEndpoints_lower","int_bNumEndpoints",1],
["Interface_bNumEndpoints_higher","int_bNumEndpoints",0xf0],
["Interface_bNumEndpoints_max","int_bNumEndpoints",0xff],

["Endpoint_bLength_null","end_bLength",0],
["Endpoint_bLength_lower","end_bLength",1],
["Endpoint_bLength_higher","end_bLength",0xf0],
["Endpoint_bLength_max","end_bLength",0xff],
["Endpoint_bDescriptorType_null","end_bDescriptorType",0],
["Endpoint_bDescriptorType_invalid","end_bDescriptorType",0xff],
["Endpoint_bEndpointAddress_null","end_bEndpointAddress",0],
["Endpoint_bEndpointAddress_max","end_bEndpointAddress",0xff],
["Endpoint_wMaxPacketSize_null","end_wMaxPacketSize",0],
["Endpoint_wMaxPacketSize_max","end_wMaxPacketSize",0xff],
]

# PIMA 15740
testcases_image_class = [
["DeviceInfo_ContainerLength_null","DeviceInfo_ContainerLength",b'\x00\x00\x00\x00'],
["DeviceInfo_ContainerLength_lower","DeviceInfo_ContainerLength",b'\x00\x00\x00\x01'],
["DeviceInfo_ContainerLength_higher","DeviceInfo_ContainerLength",b'\x00\x00\xff\xff'],
["DeviceInfo_ContainerLength_max","DeviceInfo_ContainerLength",b'\xff\xff\xff\xff'],
["DeviceInfo_ContainerType_null","DeviceInfo_ContainerType",b'\x00\x00'],
["DeviceInfo_ContainerType_max","DeviceInfo_ContainerType",b'\xff\xff'],
["DeviceInfo_OperationCode_null","DeviceInfo_OperationCode",b'\x00\x00'],
["DeviceInfo_OperationCode_max","DeviceInfo_OperationCode",b'\xff\xff'],
["DeviceInfo_TransactionID_null","DeviceInfo_TransactionID",b'\x00\x00\x00\x00'],
["DeviceInfo_TransactionID_max","DeviceInfo_TransactionID",b'\xff\xff\xff\xff'],
["DeviceInfo_StandardVersion_null","DeviceInfo_StandardVersion",b'\x00\x00'],
["DeviceInfo_StandardVersion_max","DeviceInfo_StandardVersion",b'\xff\xff'],
["DeviceInfo_VendorExtensionID_null","DeviceInfo_VendorExtensionID",b'\x00\x00\x00\x00'],
["DeviceInfo_VendorExtensionID_null","DeviceInfo_VendorExtensionID",b'\xff\xff\xff\xff'],
["DeviceInfo_VendorExtensionVersion_null","DeviceInfo_VendorExtensionVersion",b'\x00\x00'],
["DeviceInfo_VendorExtensionVersion_null","DeviceInfo_VendorExtensionVersion",b'\xff\xff'],
["DeviceInfo_VendorExtensionDesc_max","DeviceInfo_VendorExtensionDesc",b'\xff'],
["DeviceInfo_VendorExtensionDesc_overflow1","DeviceInfo_VendorExtensionDesc",b'\xfe' + b'\x61\x00' * 254 + b'\x00\x00'],
["DeviceInfo_VendorExtensionDesc_overflow2","DeviceInfo_VendorExtensionDesc",b'\x00' + b'\x61\x00' * 254 + b'\x00\x00'],
["DeviceInfo_VendorExtensionDesc_overflow3","DeviceInfo_VendorExtensionDesc",b'\x20' + b'\x61\x00' * 254 + b'\x00\x00'],
["DeviceInfo_VendorExtensionDesc_overflow4","DeviceInfo_VendorExtensionDesc",b'\xff' + b'\x61\x00' * 254 + b'\x00\x00'],
["DeviceInfo_VendorExtensionDesc_formatstring","DeviceInfo_VendorExtensionDesc",b'\x06' + b'\x25\x00\x78\x00\x25\x00\x6e\x00\x25\x00\x6e\x00' + b'\x00\x00'],
["DeviceInfo_FunctionalMode_max","DeviceInfo_FunctionalMode",b'\xff\xff'],
["DeviceInfo_OperationsSupportedArraySize_null","DeviceInfo_OperationsSupportedArraySize",b'\x00\x00\x00\x00'],
["DeviceInfo_OperationsSupportedArraySize_lower","DeviceInfo_OperationsSupportedArraySize",b'\x00\x00\x00\x01'],
["DeviceInfo_OperationsSupportedArraySize_higher","DeviceInfo_OperationsSupportedArraySize",b'\x00\x00\xff\xff'],
["DeviceInfo_OperationsSupportedArraySize_max","DeviceInfo_OperationsSupportedArraySize",b'\xff\xff\xff\xff'],
["DeviceInfo_OperationSupported_null","DeviceInfo_OperationSupported",b'\x00\x00'],
["DeviceInfo_OperationSupported_max","DeviceInfo_OperationSupported",b'\xff\xff'],
["DeviceInfo_EventsSupportedArraySize_null","DeviceInfo_EventsSupportedArraySize",b'\x00\x00\x00\x00'],
["DeviceInfo_EventsSupportedArraySize_lower","DeviceInfo_EventsSupportedArraySize",b'\x00\x00\x00\x01'],
["DeviceInfo_EventsSupportedArraySize_higher","DeviceInfo_EventsSupportedArraySize",b'\x00\x00\xff\xff'],
["DeviceInfo_EventsSupportedArraySize_max","DeviceInfo_EventsSupportedArraySize",b'\xff\xff\xff\xff'],
["DeviceInfo_EventSupported_null","DeviceInfo_EventSupported",b'\x00\x00'],
["DeviceInfo_EventSupported_max","DeviceInfo_EventSupported",b'\xff\xff'],
["DeviceInfo_DevicePropertiesSupportedArraySize_null","DeviceInfo_DevicePropertiesSupportedArraySize",b'\x00\x00\x00\x00'],
["DeviceInfo_DevicePropertiesSupportedArraySize_lower","DeviceInfo_DevicePropertiesSupportedArraySize",b'\x00\x00\x00\x01'],
["DeviceInfo_DevicePropertiesSupportedArraySize_higher","DeviceInfo_DevicePropertiesSupportedArraySize",b'\x00\x00\xff\xff'],
["DeviceInfo_DevicePropertiesSupportedArraySize_max","DeviceInfo_DevicePropertiesSupportedArraySize",b'\xff\xff\xff\xff'],
["DeviceInfo_DevicePropertySupported_null","DeviceInfo_DevicePropertySupported",b'\x00\x00'],
["DeviceInfo_DevicePropertySupported_max","DeviceInfo_DevicePropertySupported",b'\xff\xff'],
["DeviceInfo_CaptureFormatsSupportedArraySize_null","DeviceInfo_CaptureFormatsSupportedArraySize",b'\x00\x00\x00\x00'],
["DeviceInfo_CaptureFormatsSupportedArraySize_lower","DeviceInfo_CaptureFormatsSupportedArraySize",b'\x00\x00\x00\x01'],
["DeviceInfo_CaptureFormatsSupportedArraySize_higher","DeviceInfo_CaptureFormatsSupportedArraySize",b'\x00\x00\xff\xff'],
["DeviceInfo_CaptureFormatsSupportedArraySize_max","DeviceInfo_CaptureFormatsSupportedArraySize",b'\xff\xff\xff\xff'],
["DeviceInfo_ImageFormatsSupportedArraySize_null","DeviceInfo_ImageFormatsSupportedArraySize",b'\x00\x00\x00\x00'],
["DeviceInfo_ImageFormatsSupportedArraySize_lower","DeviceInfo_ImageFormatsSupportedArraySize",b'\x00\x00\x00\x01'],
["DeviceInfo_ImageFormatsSupportedArraySize_higher","DeviceInfo_ImageFormatsSupportedArraySize",b'\x00\x00\xff\xff'],
["DeviceInfo_ImageFormatsSupportedArraySize_max","DeviceInfo_ImageFormatsSupportedArraySize",b'\xff\xff\xff\xff'],
["DeviceInfo_ImageFormatSupported_null","DeviceInfo_ImageFormatSupported",b'\x00\x00'],
["DeviceInfo_ImageFormatSupported_max","DeviceInfo_ImageFormatSupported",b'\xff\xff'],
["DeviceInfo_Manufacturer_max","DeviceInfo_Manufacturer",b'\xff'],
["DeviceInfo_Manufacturer_overflow1","DeviceInfo_Manufacturer",b'\xfe' + b'\x61\x00' * 254 + b'\x00\x00'],
["DeviceInfo_Manufacturer_overflow2","DeviceInfo_Manufacturer",b'\x00' + b'\x61\x00' * 254 + b'\x00\x00'],
["DeviceInfo_Manufacturer_overflow3","DeviceInfo_Manufacturer",b'\x20' + b'\x61\x00' * 254 + b'\x00\x00'],
["DeviceInfo_Manufacturer_overflow4","DeviceInfo_Manufacturer",b'\xff' + b'\x61\x00' * 254 + b'\x00\x00'],
["DeviceInfo_Manufacturer_formatstring","DeviceInfo_Manufacturer",b'\x06' + b'\x25\x00\x78\x00\x25\x00\x6e\x00\x25\x00\x6e\x00' + b'\x00\x00'],
["DeviceInfo_Model_max","DeviceInfo_Model",b'\xff'],
["DeviceInfo_Model_overflow1","DeviceInfo_Model",b'\xfe' + b'\x61\x00' * 254 + b'\x00\x00'],
["DeviceInfo_Model_overflow2","DeviceInfo_Model",b'\x00' + b'\x61\x00' * 254 + b'\x00\x00'],
["DeviceInfo_Model_overflow3","DeviceInfo_Model",b'\x20' + b'\x61\x00' * 254 + b'\x00\x00'],
["DeviceInfo_Model_overflow4","DeviceInfo_Model",b'\xff' + b'\x61\x00' * 254 + b'\x00\x00'],
["DeviceInfo_Model_formatstring","DeviceInfo_Model",b'\x06' + b'\x25\x00\x78\x00\x25\x00\x6e\x00\x25\x00\x6e\x00' + b'\x00\x00'],
["DeviceInfo_DeviceVersion_max","DeviceInfo_DeviceVersion",b'\xff'],
["DeviceInfo_DeviceVersion_overflow1","DeviceInfo_DeviceVersion",b'\xfe' + b'\x61\x00' * 254 + b'\x00\x00'],
["DeviceInfo_DeviceVersion_overflow2","DeviceInfo_DeviceVersion",b'\x00' + b'\x61\x00' * 254 + b'\x00\x00'],
["DeviceInfo_DeviceVersion_overflow3","DeviceInfo_DeviceVersion",b'\x20' + b'\x61\x00' * 254 + b'\x00\x00'],
["DeviceInfo_DeviceVersion_overflow4","DeviceInfo_DeviceVersion",b'\xff' + b'\x61\x00' * 254 + b'\x00\x00'],
["DeviceInfo_DeviceVersion_formatstring","DeviceInfo_DeviceVersion",b'\x06' + b'\x25\x00\x78\x00\x25\x00\x6e\x00\x25\x00\x6e\x00' + b'\x00\x00'],
["DeviceInfo_SerialNumber_max","DeviceInfo_SerialNumber",b'\xff'],
["DeviceInfo_SerialNumber_overflow1","DeviceInfo_SerialNumber",b'\xfe' + b'\x61\x00' * 254 + b'\x00\x00'],
["DeviceInfo_SerialNumber_overflow2","DeviceInfo_SerialNumber",b'\x00' + b'\x61\x00' * 254 + b'\x00\x00'],
["DeviceInfo_SerialNumber_overflow3","DeviceInfo_SerialNumber",b'\x20' + b'\x61\x00' * 254 + b'\x00\x00'],
["DeviceInfo_SerialNumber_overflow4","DeviceInfo_SerialNumber",b'\xff' + b'\x61\x00' * 254 + b'\x00\x00'],
["DeviceInfo_SerialNumber_formatstring","DeviceInfo_SerialNumber",b'\x06' + b'\x25\x00\x78\x00\x25\x00\x6e\x00\x25\x00\x6e\x00' + b'\x00\x00'],

["StorageIDArray_ContainerLength_null","StorageIDArray_ContainerLength",b'\x00\x00\x00\x00'],
["StorageIDArray_ContainerLength_lower","StorageIDArray_ContainerLength",b'\x00\x00\x00\x01'],
["StorageIDArray_ContainerLength_higher","StorageIDArray_ContainerLength",b'\x00\x00\xff\xff'],
["StorageIDArray_ContainerLength_max","StorageIDArray_ContainerLength",b'\xff\xff\xff\xff'],
["StorageIDArray_ContainerType_null","StorageIDArray_ContainerType",b'\x00\x00'],
["StorageIDArray_ContainerType_max","StorageIDArray_ContainerType",b'\xff\xff'],
["StorageIDArray_OperationCode_null","StorageIDArray_OperationCode",b'\x00\x00'],
["StorageIDArray_OperationCode_max","StorageIDArray_OperationCode",b'\xff\xff'],
["StorageIDArray_TransactionID_null","StorageIDArray_TransactionID",b'\x00\x00\x00\x00'],
["StorageIDArray_TransactionID_max","StorageIDArray_TransactionID",b'\xff\xff\xff\xff'],
["StorageIDArray_StorageIDsArraySize_null","StorageIDArray_StorageIDsArraySize",b'\x00\x00\x00\x00'],
["StorageIDArray_StorageIDsArraySize_lower","StorageIDArray_StorageIDsArraySize",b'\x00\x00\x00\x01'],
["StorageIDArray_StorageIDsArraySize_higher","StorageIDArray_StorageIDsArraySize",b'\x00\x00\xff\xff'],
["StorageIDArray_StorageIDsArraySize_max","StorageIDArray_StorageIDsArraySize",b'\xff\xff\xff\xff'],
["StorageIDArray_StorageID_null","StorageIDArray_StorageID",b'\x00\x00'],
["StorageIDArray_StorageID_max","StorageIDArray_StorageID",b'\xff\xff'],

["StorageInfo_ContainerLength_null","StorageInfo_ContainerLength",b'\x00\x00\x00\x00'],
["StorageInfo_ContainerLength_lower","StorageInfo_ContainerLength",b'\x00\x00\x00\x01'],
["StorageInfo_ContainerLength_higher","StorageInfo_ContainerLength",b'\x00\x00\xff\xff'],
["StorageInfo_ContainerLength_max","StorageInfo_ContainerLength",b'\xff\xff\xff\xff'],
["StorageInfo_ContainerType_null","StorageInfo_ContainerType",b'\x00\x00'],
["StorageInfo_ContainerType_max","StorageInfo_ContainerType",b'\xff\xff'],
["StorageInfo_OperationCode_null","StorageInfo_OperationCode",b'\x00\x00'],
["StorageInfo_OperationCode_max","StorageInfo_OperationCode",b'\xff\xff'],
["StorageInfo_TransactionID_null","StorageInfo_TransactionID",b'\x00\x00\x00\x00'],
["StorageInfo_TransactionID_max","StorageInfo_TransactionID",b'\xff\xff\xff\xff'],
["StorageInfo_StorageType_null","StorageInfo_StorageType",b'\x00\x00'],
["StorageInfo_StorageType_max","StorageInfo_StorageType",b'\xff\xff'],
["StorageInfo_FilesystemType_null","StorageInfo_FilesystemType",b'\x00\x00'],
["StorageInfo_FilesystemType_max","StorageInfo_FilesystemType",b'\xff\xff'],
["StorageInfo_AccessCapability_null","StorageInfo_AccessCapability",b'\x00\x00'],
["StorageInfo_AccessCapability_max","StorageInfo_AccessCapability",b'\xff\xff'],
["StorageInfo_MaxCapacity_null","StorageInfo_MaxCapacity",b'\x00\x00\x00\x00\x00\x00\x00\x00'],
["StorageInfo_MaxCapacity_max","StorageInfo_MaxCapacity",b'\xff\xff\xff\xff\xff\xff\xff\xff'],
["StorageInfo_FreeSpaceInBytes_null","StorageInfo_FreeSpaceInBytes",b'\x00\x00\x00\x00\x00\x00\x00\x00'],
["StorageInfo_FreeSpaceInBytes_max","StorageInfo_FreeSpaceInBytes",b'\xff\xff\xff\xff\xff\xff\xff\xff'],
["StorageInfo_FreeSpaceInImages_null","StorageInfo_FreeSpaceInImages",b'\x00\x00\x00\x00'],
["StorageInfo_FreeSpaceInImages_max","StorageInfo_FreeSpaceInImages",b'\xff\xff\xff\xff'],
["StorageInfo_StorageDescription_max","StorageInfo_StorageDescription",b'\xff'],
["StorageInfo_StorageDescription_overflow1","StorageInfo_StorageDescription",b'\xfe' + b'\x61\x00' * 254 + b'\x00\x00'],
["StorageInfo_StorageDescription_overflow2","StorageInfo_StorageDescription",b'\x00' + b'\x61\x00' * 254 + b'\x00\x00'],
["StorageInfo_StorageDescription_overflow3","StorageInfo_StorageDescription",b'\x20' + b'\x61\x00' * 254 + b'\x00\x00'],
["StorageInfo_StorageDescription_overflow4","StorageInfo_StorageDescription",b'\xff' + b'\x61\x00' * 254 + b'\x00\x00'],
["StorageInfo_StorageDescription_formatstring","StorageInfo_StorageDescription",b'\x06' + b'\x25\x00\x78\x00\x25\x00\x6e\x00\x25\x00\x6e\x00' + b'\x00\x00'],
["StorageInfo_VolumeLabel_max","StorageInfo_VolumeLabel",b'\xff'],
["StorageInfo_VolumeLabel_overflow1","StorageInfo_VolumeLabel",b'\xfe' + b'\x61\x00' * 254 + b'\x00\x00'],
["StorageInfo_VolumeLabel_overflow2","StorageInfo_VolumeLabel",b'\x00' + b'\x61\x00' * 254 + b'\x00\x00'],
["StorageInfo_VolumeLabel_overflow3","StorageInfo_VolumeLabel",b'\x20' + b'\x61\x00' * 254 + b'\x00\x00'],
["StorageInfo_VolumeLabel_overflow4","StorageInfo_VolumeLabel",b'\xff' + b'\x61\x00' * 254 + b'\x00\x00'],
["StorageInfo_VolumeLabel_formatstring","StorageInfo_VolumeLabel",b'\x06' + b'\x25\x00\x78\x00\x25\x00\x6e\x00\x25\x00\x6e\x00' + b'\x00\x00'],

["ObjectHandles_ContainerLength_null","ObjectHandles_ContainerLength",b'\x00\x00\x00\x00'],
["ObjectHandles_ContainerLength_lower","ObjectHandles_ContainerLength",b'\x00\x00\x00\x01'],
["ObjectHandles_ContainerLength_higher","ObjectHandles_ContainerLength",b'\x00\x00\xff\xff'],
["ObjectHandles_ContainerLength_max","ObjectHandles_ContainerLength",b'\xff\xff\xff\xff'],
["ObjectHandles_ContainerType_null","ObjectHandles_ContainerType",b'\x00\x00'],
["ObjectHandles_ContainerType_max","ObjectHandles_ContainerType",b'\xff\xff'],
["ObjectHandles_OperationCode_null","ObjectHandles_OperationCode",b'\x00\x00'],
["ObjectHandles_OperationCode_max","ObjectHandles_OperationCode",b'\xff\xff'],
["ObjectHandles_TransactionID_null","ObjectHandles_TransactionID",b'\x00\x00\x00\x00'],
["ObjectHandles_TransactionID_max","ObjectHandles_TransactionID",b'\xff\xff\xff\xff'],
["ObjectHandles_ObjectHandleArraySize_null","ObjectHandles_ObjectHandleArraySize",b'\x00\x00\x00\x00'],
["ObjectHandles_ObjectHandleArraySize_lower","ObjectHandles_ObjectHandleArraySize",b'\x00\x00\x00\x01'],
["ObjectHandles_ObjectHandleArraySize_higher","ObjectHandles_ObjectHandleArraySize",b'\x00\x00\xff\xff'],
["ObjectHandles_ObjectHandleArraySize_max","ObjectHandles_ObjectHandleArraySize",b'\xff\xff\xff\xff'],
["ObjectHandles_ObjectHandle_null","ObjectHandles_ObjectHandle",b'\x00\x00'],
["ObjectHandles_ObjectHandle_max","ObjectHandles_ObjectHandle",b'\xff\xff'],

["ObjectInfo_ContainerLength_null","ObjectInfo_ContainerLength",b'\x00\x00\x00\x00'],
["ObjectInfo_ContainerLength_lower","ObjectInfo_ContainerLength",b'\x00\x00\x00\x01'],
["ObjectInfo_ContainerLength_higher","ObjectInfo_ContainerLength",b'\x00\x00\xff\xff'],
["ObjectInfo_ContainerLength_max","ObjectInfo_ContainerLength",b'\xff\xff\xff\xff'],
["ObjectInfo_ContainerType_null","ObjectInfo_ContainerType",b'\x00\x00'],
["ObjectInfo_ContainerType_max","ObjectInfo_ContainerType",b'\xff\xff'],
["ObjectInfo_OperationCode_null","ObjectInfo_OperationCode",b'\x00\x00'],
["ObjectInfo_OperationCode_max","ObjectInfo_OperationCode",b'\xff\xff'],
["ObjectInfo_TransactionID_null","ObjectInfo_TransactionID",b'\x00\x00\x00\x00'],
["ObjectInfo_TransactionID_max","ObjectInfo_TransactionID",b'\xff\xff\xff\xff'],
["ObjectInfo_StorageID_null","ObjectInfo_StorageID",b'\x00\x00'],
["ObjectInfo_StorageID_max","ObjectInfo_StorageID",b'\xff\xff'],
["ObjectInfo_ObjectFormat_null","ObjectInfo_ObjectFormat",b'\x00\x00\x00\x00'],
["ObjectInfo_ObjectFormat_lower","ObjectInfo_ObjectFormat",b'\x00\x00\x00\x01'],
["ObjectInfo_ObjectFormat_higher","ObjectInfo_ObjectFormat",b'\x00\x00\xff\xff'],
["ObjectInfo_ObjectFormat_max","ObjectInfo_ObjectFormat",b'\xff\xff\xff\xff'],
["ObjectInfo_ProtectionStatus_null","ObjectInfo_ProtectionStatus",b'\x00\x00'],
["ObjectInfo_ProtectionStatus_max","ObjectInfo_ProtectionStatus",b'\xff\xff'],
["ObjectInfo_ObjectCompressedSize_null","ObjectInfo_ObjectCompressedSize",b'\x00\x00\x00\x00'],
["ObjectInfo_ObjectCompressedSize_lower","ObjectInfo_ObjectCompressedSize",b'\x00\x00\x00\x01'],
["ObjectInfo_ObjectCompressedSize_higher","ObjectInfo_ObjectCompressedSize",b'\x00\x00\xff\xff'],
["ObjectInfo_ObjectCompressedSize_max","ObjectInfo_ObjectCompressedSize",b'\xff\xff\xff\xff'],
["ObjectInfo_ThumbFormat_null","ObjectInfo_ThumbFormat",b'\x00\x00\x00\x00'],
["ObjectInfo_ThumbFormat_max","ObjectInfo_ThumbFormat",b'\xff\xff\xff\xff'],
["ObjectInfo_ThumbCompressedSize_null","ObjectInfo_ThumbCompressedSize",b'\x00\x00\x00\x00'],
["ObjectInfo_ThumbCompressedSize_lower","ObjectInfo_ThumbCompressedSize",b'\x00\x00\x00\x01'],
["ObjectInfo_ThumbCompressedSize_higher","ObjectInfo_ThumbCompressedSize",b'\x00\x00\xff\xff'],
["ObjectInfo_ThumbCompressedSize_max","ObjectInfo_ThumbCompressedSize",b'\xff\xff\xff\xff'],
["ObjectInfo_ThumbPixelWidth_null","ObjectInfo_ThumbPixelWidth",b'\x00\x00\x00\x00'],
["ObjectInfo_ThumbPixelWidth_lower","ObjectInfo_ThumbPixelWidth",b'\x00\x00\x00\x01'],
["ObjectInfo_ThumbPixelWidth_higher","ObjectInfo_ThumbPixelWidth",b'\x00\x00\xff\xff'],
["ObjectInfo_ThumbPixelWidth_max","ObjectInfo_ThumbPixelWidth",b'\xff\xff\xff\xff'],
["ObjectInfo_ThumbPixelHeight_null","ObjectInfo_ThumbPixelHeight",b'\x00\x00\x00\x00'],
["ObjectInfo_ThumbPixelHeight_lower","ObjectInfo_ThumbPixelHeight",b'\x00\x00\x00\x01'],
["ObjectInfo_ThumbPixelHeight_higher","ObjectInfo_ThumbPixelHeight",b'\x00\x00\xff\xff'],
["ObjectInfo_ThumbPixelHeight_max","ObjectInfo_ThumbPixelHeight",b'\xff\xff\xff\xff'],
["ObjectInfo_ImagePixelWidth_null","ObjectInfo_ImagePixelWidth",b'\x00\x00\x00\x00'],
["ObjectInfo_ImagePixelWidth_lower","ObjectInfo_ImagePixelWidth",b'\x00\x00\x00\x01'],
["ObjectInfo_ImagePixelWidth_higher","ObjectInfo_ImagePixelWidth",b'\x00\x00\xff\xff'],
["ObjectInfo_ImagePixelWidth_max","ObjectInfo_ImagePixelWidth",b'\xff\xff\xff\xff'],
["ObjectInfo_ImagePixelHeight_null","ObjectInfo_ImagePixelHeight",b'\x00\x00\x00\x00'],
["ObjectInfo_ImagePixelHeight_lower","ObjectInfo_ImagePixelHeight",b'\x00\x00\x00\x01'],
["ObjectInfo_ImagePixelHeight_higher","ObjectInfo_ImagePixelHeight",b'\x00\x00\xff\xff'],
["ObjectInfo_ImagePixelHeight_max","ObjectInfo_ImagePixelHeight",b'\xff\xff\xff\xff'],
["ObjectInfo_ImagePixelDepth_null","ObjectInfo_ImagePixelDepth",b'\x00\x00\x00\x00'],
["ObjectInfo_ImagePixelDepth_lower","ObjectInfo_ImagePixelDepth",b'\x00\x00\x00\x01'],
["ObjectInfo_ImagePixelDepth_higher","ObjectInfo_ImagePixelDepth",b'\x00\x00\xff\xff'],
["ObjectInfo_ImagePixelDepth_max","ObjectInfo_ImagePixelDepth",b'\xff\xff\xff\xff'],
["ObjectInfo_ParentObject_null","ObjectInfo_ParentObject",b'\x00\x00\x00\x00'],
["ObjectInfo_ParentObject_max","ObjectInfo_ParentObject",b'\xff\xff\xff\xff'],
["ObjectInfo_AssociationType_null","ObjectInfo_AssociationType",b'\x00\x00'],
["ObjectInfo_AssociationType_max","ObjectInfo_AssociationType",b'\xff\xff'],
["ObjectInfo_AssociationDesc_null","ObjectInfo_AssociationDesc",b'\x00\x00\x00\x00'],
["ObjectInfo_AssociationDesc_max","ObjectInfo_AssociationDesc",b'\xff\xff\xff\xff'],
["ObjectInfo_SequenceNumber_null","ObjectInfo_SequenceNumber",b'\x00\x00\x00\x00'],
["ObjectInfo_SequenceNumber_lower","ObjectInfo_SequenceNumber",b'\x00\x00\x00\x01'],
["ObjectInfo_SequenceNumber_higher","ObjectInfo_SequenceNumber",b'\x00\x00\xff\xff'],
["ObjectInfo_SequenceNumber_max","ObjectInfo_SequenceNumber",b'\xff\xff\xff\xff'],
["ObjectInfo_Filename_max","ObjectInfo_Filename",b'\xff'],
["ObjectInfo_Filename_overflow1","ObjectInfo_Filename",b'\xfe' + b'\x61\x00' * 254 + b'\x00\x00'],
["ObjectInfo_Filename_overflow2","ObjectInfo_Filename",b'\x00' + b'\x61\x00' * 254 + b'\x00\x00'],
["ObjectInfo_Filename_overflow3","ObjectInfo_Filename",b'\x20' + b'\x61\x00' * 254 + b'\x00\x00'],
["ObjectInfo_Filename_overflow4","ObjectInfo_Filename",b'\xff' + b'\x61\x00' * 254 + b'\x00\x00'],
["ObjectInfo_Filename_formatstring","ObjectInfo_Filename",b'\x06' + b'\x25\x00\x78\x00\x25\x00\x6e\x00\x25\x00\x6e\x00' + b'\x00\x00'],
["ObjectInfo_CaptureDate_max","ObjectInfo_CaptureDate",b'\xff'],
["ObjectInfo_CaptureDate_overflow1","ObjectInfo_CaptureDate",b'\xfe' + b'\x61\x00' * 254 + b'\x00\x00'],
["ObjectInfo_CaptureDate_overflow2","ObjectInfo_CaptureDate",b'\x00' + b'\x61\x00' * 254 + b'\x00\x00'],
["ObjectInfo_CaptureDate_overflow3","ObjectInfo_CaptureDate",b'\x20' + b'\x61\x00' * 254 + b'\x00\x00'],
["ObjectInfo_CaptureDate_overflow4","ObjectInfo_CaptureDate",b'\xff' + b'\x61\x00' * 254 + b'\x00\x00'],
["ObjectInfo_CaptureDate_formatstring","ObjectInfo_CaptureDate",b'\x06' + b'\x25\x00\x78\x00\x25\x00\x6e\x00\x25\x00\x6e\x00' + b'\x00\x00'],
["ObjectInfo_ModificationDate_max","ObjectInfo_ModificationDate",b'\xff'],
["ObjectInfo_ModificationDate_overflow1","ObjectInfo_ModificationDate",b'\xfe' + b'\x61\x00' * 254 + b'\x00\x00'],
["ObjectInfo_ModificationDate_overflow2","ObjectInfo_ModificationDate",b'\x00' + b'\x61\x00' * 254 + b'\x00\x00'],
["ObjectInfo_ModificationDate_overflow3","ObjectInfo_ModificationDate",b'\x20' + b'\x61\x00' * 254 + b'\x00\x00'],
["ObjectInfo_ModificationDate_overflow4","ObjectInfo_ModificationDate",b'\xff' + b'\x61\x00' * 254 + b'\x00\x00'],
["ObjectInfo_ModificationDate_formatstring","ObjectInfo_ModificationDate",b'\x06' + b'\x25\x00\x78\x00\x25\x00\x6e\x00\x25\x00\x6e\x00' + b'\x00\x00'],
["ObjectInfo_Keywords_max","ObjectInfo_Keywords",b'\xff'],
["ObjectInfo_Keywords_overflow1","ObjectInfo_Keywords",b'\xfe' + b'\x61\x00' * 254 + b'\x00\x00'],
["ObjectInfo_Keywords_overflow2","ObjectInfo_Keywords",b'\x00' + b'\x61\x00' * 254 + b'\x00\x00'],
["ObjectInfo_Keywords_overflow3","ObjectInfo_Keywords",b'\x20' + b'\x61\x00' * 254 + b'\x00\x00'],
["ObjectInfo_Keywords_overflow4","ObjectInfo_Keywords",b'\xff' + b'\x61\x00' * 254 + b'\x00\x00'],
["ObjectInfo_Keywords_formatstring","ObjectInfo_Keywords",b'\x06' + b'\x25\x00\x78\x00\x25\x00\x6e\x00\x25\x00\x6e\x00' + b'\x00\x00'],
]

testcases_printer_class = [
["DeviceID_Key1_null","Device_ID_Key1",b'\x00'],
["DeviceID_Key1_overflow1","Device_ID_Key1",b'\x61' * 300],
["DeviceID_Key1_overflow2","Device_ID_Key1",b'\x61' * 1200],
["DeviceID_Key1_overflow3","Device_ID_Key1",b'\x61' * 2400],
["DeviceID_Key1_overflow4","Device_ID_Key1",b'\x61' * 5000],
["DeviceID_Key1_formatstring","Device_ID_Key1",b'\x25\x78\x25\x6e\x25\x6e'],
["DeviceID_Key2_null","Device_ID_Key2",b'\x00'],
["DeviceID_Key2_overflow1","Device_ID_Key2",b'\x61' * 300],
["DeviceID_Key2_overflow2","Device_ID_Key2",b'\x61' * 1200],
["DeviceID_Key2_overflow3","Device_ID_Key2",b'\x61' * 2400],
["DeviceID_Key2_overflow4","Device_ID_Key2",b'\x61' * 5000],
["DeviceID_Key2_formatstring","Device_ID_Key2",b'\x25\x78\x25\x6e\x25\x6e'],
["DeviceID_Key3_null","Device_ID_Key3",b'\x00'],
["DeviceID_Key3_overflow1","Device_ID_Key3",b'\x61' * 300],
["DeviceID_Key3_overflow2","Device_ID_Key3",b'\x61' * 1200],
["DeviceID_Key3_overflow3","Device_ID_Key3",b'\x61' * 2400],
["DeviceID_Key3_overflow4","Device_ID_Key3",b'\x61' * 5000],
["DeviceID_Key3_formatstring","Device_ID_Key3",b'\x25\x78\x25\x6e\x25\x6e'],
["DeviceID_Key4_null","Device_ID_Key4",b'\x00'],
["DeviceID_Key4_overflow1","Device_ID_Key4",b'\x61' * 300],
["DeviceID_Key4_overflow2","Device_ID_Key4",b'\x61' * 1200],
["DeviceID_Key4_overflow3","Device_ID_Key4",b'\x61' * 2400],
["DeviceID_Key4_overflow4","Device_ID_Key4",b'\x61' * 5000],
["DeviceID_Key4_formatstring","Device_ID_Key4",b'\x25\x78\x25\x6e\x25\x6e'],
["DeviceID_Key5_null","Device_ID_Key5",b'\x00'],
["DeviceID_Key5_overflow1","Device_ID_Key5",b'\x61' * 300],
["DeviceID_Key5_overflow2","Device_ID_Key5",b'\x61' * 1200],
["DeviceID_Key5_overflow3","Device_ID_Key5",b'\x61' * 2400],
["DeviceID_Key5_overflow4","Device_ID_Key5",b'\x61' * 5000],
["DeviceID_Key5_formatstring","Device_ID_Key5",b'\x25\x78\x25\x6e\x25\x6e'],
["DeviceID_Key6_null","Device_ID_Key6",b'\x00'],
["DeviceID_Key6_overflow1","Device_ID_Key6",b'\x61' * 300],
["DeviceID_Key6_overflow2","Device_ID_Key6",b'\x61' * 1200],
["DeviceID_Key6_overflow3","Device_ID_Key6",b'\x61' * 2400],
["DeviceID_Key6_overflow4","Device_ID_Key6",b'\x61' * 5000],
["DeviceID_Key6_formatstring","Device_ID_Key6",b'\x25\x78\x25\x6e\x25\x6e'],
["DeviceID_Key7_null","Device_ID_Key7",b'\x00'],
["DeviceID_Key7_overflow1","Device_ID_Key7",b'\x61' * 300],
["DeviceID_Key7_overflow2","Device_ID_Key7",b'\x61' * 1200],
["DeviceID_Key7_overflow3","Device_ID_Key7",b'\x61' * 2400],
["DeviceID_Key7_overflow4","Device_ID_Key7",b'\x61' * 5000],
["DeviceID_Key7_formatstring","Device_ID_Key7",b'\x25\x78\x25\x6e\x25\x6e'],
["DeviceID_Value1_null","Device_ID_Value1",b'\x00'],
["DeviceID_Value1_overflow1","Device_ID_Value1",b'\x61' * 300],
["DeviceID_Value1_overflow2","Device_ID_Value1",b'\x61' * 1200],
["DeviceID_Value1_overflow3","Device_ID_Value1",b'\x61' * 2400],
["DeviceID_Value1_overflow4","Device_ID_Value1",b'\x61' * 5000],
["DeviceID_Value1_formatstring","Device_ID_Value1",b'\x25\x78\x25\x6e\x25\x6e'],
["DeviceID_Value2_null","Device_ID_Value2",b'\x00'],
["DeviceID_Value2_overflow1","Device_ID_Value2",b'\x61' * 300],
["DeviceID_Value2_overflow2","Device_ID_Value2",b'\x61' * 1200],
["DeviceID_Value2_overflow3","Device_ID_Value2",b'\x61' * 2400],
["DeviceID_Value2_overflow4","Device_ID_Value2",b'\x61' * 5000],
["DeviceID_Value2_formatstring","Device_ID_Value2",b'\x25\x78\x25\x6e\x25\x6e'],
["DeviceID_Value3_null","Device_ID_Value3",b'\x00'],
["DeviceID_Value3_overflow1","Device_ID_Value3",b'\x61' * 300],
["DeviceID_Value3_overflow2","Device_ID_Value3",b'\x61' * 1200],
["DeviceID_Value3_overflow3","Device_ID_Value3",b'\x61' * 2400],
["DeviceID_Value3_overflow4","Device_ID_Value3",b'\x61' * 5000],
["DeviceID_Value3_formatstring","Device_ID_Value3",b'\x25\x78\x25\x6e\x25\x6e'],
["DeviceID_Value4_null","Device_ID_Value4",b'\x00'],
["DeviceID_Value4_overflow1","Device_ID_Value4",b'\x61' * 300],
["DeviceID_Value4_overflow2","Device_ID_Value4",b'\x61' * 1200],
["DeviceID_Value4_overflow3","Device_ID_Value4",b'\x61' * 2400],
["DeviceID_Value4_overflow4","Device_ID_Value4",b'\x61' * 5000],
["DeviceID_Value4_formatstring","Device_ID_Value4",b'\x25\x78\x25\x6e\x25\x6e'],
["DeviceID_Value5_null","Device_ID_Value5",b'\x00'],
["DeviceID_Value5_overflow1","Device_ID_Value5",b'\x61' * 300],
["DeviceID_Value5_overflow2","Device_ID_Value5",b'\x61' * 1200],
["DeviceID_Value5_overflow3","Device_ID_Value5",b'\x61' * 2400],
["DeviceID_Value5_overflow4","Device_ID_Value5",b'\x61' * 5000],
["DeviceID_Value5_formatstring","Device_ID_Value5",b'\x25\x78\x25\x6e\x25\x6e'],
["DeviceID_Value6_null","Device_ID_Value6",b'\x00'],
["DeviceID_Value6_overflow1","Device_ID_Value6",b'\x61' * 300],
["DeviceID_Value6_overflow2","Device_ID_Value6",b'\x61' * 1200],
["DeviceID_Value6_overflow3","Device_ID_Value6",b'\x61' * 2400],
["DeviceID_Value6_overflow4","Device_ID_Value6",b'\x61' * 5000],
["DeviceID_Value6_formatstring","Device_ID_Value6",b'\x25\x78\x25\x6e\x25\x6e'],
["DeviceID_Value7_null","Device_ID_Value7",b'\x00'],
["DeviceID_Value7_overflow1","Device_ID_Value7",b'\x61' * 300],
["DeviceID_Value7_overflow2","Device_ID_Value7",b'\x61' * 1200],
["DeviceID_Value7_overflow3","Device_ID_Value7",b'\x61' * 2400],
["DeviceID_Value7_overflow4","Device_ID_Value7",b'\x61' * 5000],
["DeviceID_Value7_formatstring","Device_ID_Value7",b'\x25\x78\x25\x6e\x25\x6e']
]

testcases_audio_class = [
["CSInterface1_wTotalLength_null","CSInterface1_wTotalLength",0x0000],
["CSInterface1_wTotalLength_lower","CSInterface1_wTotalLength",0x0001],
["CSInterface1_wTotalLength_higher","CSInterface1_wTotalLength",0x0100],
["CSInterface1_wTotalLength_max","CSInterface1_wTotalLength",0xffff],
["CSInterface1_bInCollection_null","CSInterface1_bInCollection",0x00],
["CSInterface1_bInCollection_lower","CSInterface1_bInCollection",0x01],
["CSInterface1_bInCollection_higher","CSInterface1_bInCollection",0x10],
["CSInterface1_bInCollection_max","CSInterface1_bInCollection",0xff],
["CSInterface1_baInterfaceNr1_null","CSInterface1_baInterfaceNr1",0x00],
["CSInterface1_baInterfaceNr1_lower","CSInterface1_baInterfaceNr1",0x01],
["CSInterface1_baInterfaceNr1_higher","CSInterface1_baInterfaceNr1",0x10],
["CSInterface1_baInterfaceNr1_max","CSInterface1_baInterfaceNr1",0xff],
["CSInterface1_baInterfaceNr2_null","CSInterface1_baInterfaceNr2",0x00],
["CSInterface1_baInterfaceNr2_lower","CSInterface1_baInterfaceNr2",0x01],
["CSInterface1_baInterfaceNr2_higher","CSInterface1_baInterfaceNr2",0x10],
["CSInterface1_baInterfaceNr2_max","CSInterface1_baInterfaceNr2",0xff],
["CSInterface2_bTerminalID_null","CSInterface2_bTerminalID",0x00],
["CSInterface2_bTerminalID_max","CSInterface2_bTerminalID",0xff],
["CSInterface2_wTerminalType_null","CSInterface2_wTerminalType",0x0000],
["CSInterface2_wTerminalType_max","CSInterface2_wTerminalType",0xffff],
["CSInterface2_bAssocTerminal_null","CSInterface2_bAssocTerminal",0x00],
["CSInterface2_bAssocTerminal_max","CSInterface2_bAssocTerminal",0xff],
["CSInterface2_bNrChannel_null","CSInterface2_bNrChannel",0x00],
["CSInterface2_bNrChannel_max","CSInterface2_bNrChannel",0xff],
["CSInterface2_wChannelConfig_null","CSInterface2_wChannelConfig",0x0000],
["CSInterface2_wChannelConfig_max","CSInterface2_wChannelConfig",0xffff],
["CSInterface4_bSourceID_null","CSInterface4_bSourceID",0x00],
["CSInterface4_bSourceID_higher","CSInterface4_bSourceID",0x7f],
["CSInterface4_bSourceID_max","CSInterface4_bSourceID",0x00],
["CSInterface6_bUnitID_null","CSInterface6_bUnitID",0x00],
["CSInterface6_bUnitID_higher","CSInterface6_bUnitID",0x7f],
["CSInterface6_bUnitID_max","CSInterface6_bUnitID",0xff],
["CSInterface6_bSourceID_null","CSInterface4_bSourceID",0x00],
["CSInterface6_bSourceID_higher","CSInterface4_bSourceID",0x7f],
["CSInterface6_bSourceID_max","CSInterface4_bSourceID",0x00],
["CSInterface6_bControlSize_null","CSInterface4_bControlSize",0x00],
["CSInterface6_bControlSize_higher","CSInterface4_bControlSize",0x7f],
["CSInterface6_bControlSize_max","CSInterface4_bControlSize",0x00],
["CSInterface6_bmaControls0_null","CSInterface4_bmaControls0",0x00],
["CSInterface6_bmaControls0_higher","CSInterface4_bmaControls0",0x7f],
["CSInterface6_bmaControls0_max","CSInterface4_bmaControls0",0x00],
["CSInterface6_bmaControls1_null","CSInterface4_bmaControls1",0x00],
["CSInterface6_bmaControls1_higher","CSInterface4_bmaControls1",0x7f],
["CSInterface6_bmaControls1_max","CSInterface4_bmaControls1",0x00],
["CSInterface6_bmaControls2_null","CSInterface4_bmaControls2",0x00],
["CSInterface6_bmaControls2_higher","CSInterface4_bmaControls2",0x7f],
["CSInterface6_bmaControls2_max","CSInterface4_bmaControls2",0x00],
]


testcases_hid_class = [
["HID_bLength_null","HID_bLength",b'\x00'],
["HID_bLength_lower","HID_bLength",b'\x01'],
["HID_bLength_higher","HID_bLength",b'\x50'],
["HID_bLength_max","HID_bLength",b'\xff'],
["HID_bDescriptorType_null","HID_bDescriptorType",b'\x00'],
["HID_bDescriptorType_invalid","HID_bDescriptorType",b'\xff'],
["HID_bCountryCode_invalid","HID_bCountryCode",b'\xff'],
["HID_bNumDescriptors_null","HID_bNumDescriptors",b'\x00'],
["HID_bNumDescriptors_higher","HID_bNumDescriptors",b'\x10'],
["HID_bNumDescriptors_max","HID_bNumDescriptors",b'\xff'],
["HID_bDescriptorType2_null","HID_bDescriptorType2",b'\x00'],
["HID_bDescriptorType2_invalid","HID_bDescriptorType2",b'\xff'],
["HID_wDescriptorLength_null","HID_wDescriptorLength",b'\x00\x00'],
["HID_wDescriptorLength_lower","HID_wDescriptorLength",b'\x10\x00'],
["HID_wDescriptorLength_higher","HID_wDescriptorLength",b'\xff\x00'],
["HID_wDescriptorLength_max","HID_wDescriptorLength",b'\xff\xff'],
["Report_Usage_Page_Logic_error1","Report_Usage_Page",b'\xb1\x01'],
["Report_Usage_Page_Logic_error2","Report_Usage_Page",b'\x81\x01'],
["Report_Usage_Page_Logic_error3","Report_Usage_Page",b'\xff\x01'],
["Report_Usage_Keyboard_Logic_error1","Report_Usage_Keyboard",b'\xb1\x06'],
["Report_Usage_Keyboard_Logic_error2","Report_Usage_Keyboard",b'\x81\x06'],
["Report_Usage_Keyboard_Logic_error3","Report_Usage_Keyboard",b'\xff\x06'],
["Report_Usage_Page_Keyboard_Logic_error1","Report_Usage_Page_Keyboard",b'\xb1\x07'],
["Report_Usage_Page_Keyboard_Logic_error2","Report_Usage_Page_Keyboard",b'\x81\x07'],
["Report_Usage_Page_Keyboard_Logic_error3","Report_Usage_Page_Keyboard",b'\xff\x07'],
["Report_Usage_Minimum1_null","Report_Usage_Minimum1",b'\x19\x00'],
["Report_Usage_Minimum1_lower","Report_Usage_Minimum1",b'\x19\x01'],
["Report_Usage_Minimum1_higher","Report_Usage_Minimum1",b'\x19\xf0'],
["Report_Usage_Minimum1_max","Report_Usage_Minimum1",b'\x19\xff'],
["Report_Usage_Maximum1_null","Report_Usage_Maximum1",b'\x29\x00'],
["Report_Usage_Maximum1_lower","Report_Usage_Maximum1",b'\x29\x01'],
["Report_Usage_Maximum1_higher","Report_Usage_Maximum1",b'\x29\xf0'],
["Report_Usage_Maximum1_max","Report_Usage_Maximum1",b'\x29\xff'],
["Report_Logical_Minimum1_null","Report_Logical_Minimum1",b'\x15\x00'],
["Report_Logical_Minimum1_lower","Report_Logical_Minimum1",b'\x15\x01'],
["Report_Logical_Minimum1_higher","Report_Logical_Minimum1",b'\x15\xf0'],
["Report_Logical_Minimum1_max","Report_Logical_Minimum1",b'\x15\xff'],
["Report_Logical_Maximum1_null","Report_Logical_Maximum1",b'\x25\x00'],
["Report_Logical_Maximum1_lower","Report_Logical_Maximum1",b'\x25\x01'],
["Report_Logical_Maximum1_higher","Report_Logical_Maximum1",b'\x25\xf0'],
["Report_Logical_Maximum1_max","Report_Logical_Maximum1",b'\x25\xff'],
["Report_Report_Size1_null","Report_Report_Size1",b'\x75\x00'],
["Report_Report_Size1_lower","Report_Report_Size1",b'\x75\x01'],
["Report_Report_Size1_higher","Report_Report_Size1",b'\x75\xf0'],
["Report_Report_Size1_max","Report_Report_Size1",b'\x75\xff'],
["Report_Report_Count1_null","Report_Report_Count1",b'\x95\x00'],
["Report_Report_Count1_lower","Report_Report_Count1",b'\x95\x01'],
["Report_Report_Count1_higher","Report_Report_Count1",b'\x95\xf0'],
["Report_Report_Count1_max","Report_Report_Count1",b'\x95\xff'],
["Report_Input_Data_Variable_Absolute_Bitfield_null","Report_Input_Data_Variable_Absolute_Bitfield",b'\x81\x00'],
["Report_Input_Data_Variable_Absolute_Bitfield_max","Report_Input_Data_Variable_Absolute_Bitfield",b'\x81\xff'],
["Report_Input_Data_Variable_Absolute_Bitfield_invalid","Report_Input_Data_Variable_Absolute_Bitfield",b'\x05\x02'],
["Report_Report_Count2_null","Report_Report_Count2",b'\x95\x00'],
["Report_Report_Count2_lower","Report_Report_Count2",b'\x95\x01'],
["Report_Report_Count2_higher","Report_Report_Count2",b'\x95\xf0'],
["Report_Report_Count2_max","Report_Report_Count2",b'\x95\xff'],
["Report_Report_Size2_null","Report_Report_Size2",b'\x75\x00'],
["Report_Report_Size2_lower","Report_Report_Size2",b'\x75\x01'],
["Report_Report_Size2_higher","Report_Report_Size2",b'\x75\xf0'],
["Report_Report_Size2_max","Report_Report_Size2",b'\x75\xff'],
["Report_Input_Constant_Array_Absolute_Bitfield_null","Report_Input_Constant_Array_Absolute_Bitfield",b'\x81\x00'],
["Report_Input_Constant_Array_Absolute_Bitfield_max","Report_Input_Constant_Array_Absolute_Bitfield",b'\x81\xff'],
["Report_Input_Constant_Array_Absolute_Bitfield_invalid","Report_Input_Constant_Array_Absolute_Bitfield",b'\x05\x01'],
["Report_Usage_Minimum2_null","Report_Usage_Minimum2",b'\x19\x00'],
["Report_Usage_Minimum2_lower","Report_Usage_Minimum2",b'\x19\x01'],
["Report_Usage_Minimum2_higher","Report_Usage_Minimum2",b'\x19\xf0'],
["Report_Usage_Minimum2_max","Report_Usage_Minimum2",b'\x19\xff'],
["Report_Usage_Maximum2_null","Report_Usage_Maximum2",b'\x29\x00'],
["Report_Usage_Maximum2_lower","Report_Usage_Maximum2",b'\x29\x01'],
["Report_Usage_Maximum2_higher","Report_Usage_Maximum2",b'\x29\xf0'],
["Report_Usage_Maximum2_max","Report_Usage_Maximum2",b'\x29\xff'],
["Report_Logical_Minimum2_null","Report_Logical_Minimum2",b'\x15\x00'],
["Report_Logical_Minimum2_lower","Report_Logical_Minimum2",b'\x15\x01'],
["Report_Logical_Minimum2_higher","Report_Logical_Minimum2",b'\x15\xf0'],
["Report_Logical_Minimum2_max","Report_Logical_Minimum2",b'\x15\xff'],
["Report_Logical_Maximum2_null","Report_Logical_Maximum2",b'\x25\x00'],
["Report_Logical_Maximum2_lower","Report_Logical_Maximum2",b'\x25\x01'],
["Report_Logical_Maximum2_higher","Report_Logical_Maximum2",b'\x25\xf0'],
["Report_Logical_Maximum2_max","Report_Logical_Maximum2",b'\x25\xff'],
["Report_Report_Size3_null","Report_Report_Size3",b'\x75\x00'],
["Report_Report_Size3_lower","Report_Report_Size3",b'\x75\x01'],
["Report_Report_Size3_higher","Report_Report_Size3",b'\x75\xf0'],
["Report_Report_Size3_max","Report_Report_Size3",b'\x75\xff'],
["Report_Report_Count3_null","Report_Report_Count3",b'\x95\x00'],
["Report_Report_Count3_lower","Report_Report_Count3",b'\x95\x01'],
["Report_Report_Count3_higher","Report_Report_Count3",b'\x95\xf0'],
["Report_Report_Count3_max","Report_Report_Count3",b'\x95\xff'],
["Report_Input_Data_Array_Absolute_Bitfield_null","Report_Input_Data_Array_Absolute_Bitfield",b'\x81\x00'],
["Report_Input_Data_Array_Absolute_Bitfield_max","Report_Input_Data_Array_Absolute_Bitfield",b'\x81\xff'],
["Report_Input_Data_Array_Absolute_Bitfield_invalid","Report_Input_Data_Array_Absolute_Bitfield",b'\x05\x00'],
["Report_End_Collection_null","Report_End_Collection",b'\x00'],
["Report_End_Collection_max","Report_End_Collection",b'\xff']

]


testcases_smartcard_class = [
["icc_bLength_null","icc_bLength",b'\x00'],
["icc_bLength_lower","icc_bLength",b'\x01'],
["icc_bLength_higher","icc_bLength",b'\x50'],
["icc_bLength_max","icc_bLength",b'\xff'],
["icc_bDescriptorType_null","icc_bDescriptorType",b'\x00'],
["icc_bDescriptorType_invalid","icc_bDescriptorType",b'\xff'],
["icc_bMaxSlotIndex_higher","icc_bMaxSlotIndex",b'\x50'],
["icc_bMaxSlotIndex_max","icc_bMaxSlotIndex",b'\xff'],
["icc_bVoltageSupport_null","icc_bVoltageSupport",b'\x00'],
["icc_bVoltageSupport_lower","icc_bVoltageSupport",b'\x01'],
["icc_bVoltageSupport_higher","icc_bVoltageSupport",b'\x50'],
["icc_bVoltageSupport_max","icc_bVoltageSupport",b'\xff'],
["icc_dwProtocols_null","icc_dwProtocols",b'\x00\x00\x00\x00'],
["icc_dwProtocols_max","icc_dwProtocols",b'\xff\xff\xff\xff'],
["icc_dwDefaultClock_null","icc_dwDefaultClock",b'\x00\x00\x00\x00'],
["icc_dwDefaultClock_max","icc_dwDefaultClock",b'\xff\xff\xff\xff'],
["icc_dwMaximumClock_null","icc_dwMaximumClock",b'\x00\x00\x00\x00'],
["icc_dwMaximumClock_max","icc_dwMaximumClock",b'\xff\xff\xff\xff'],
["icc_bNumClockSupported_higher","icc_bNumClockSupported",b'\x50'],
["icc_bNumClockSupported_max","icc_bNumClockSupported",b'\xff'],
["icc_dwDataRate_null","icc_dwDataRate",b'\x00\x00\x00\x00'],
["icc_dwDataRate_max","icc_dwDataRate",b'\xff\xff\xff\xff'],
["icc_dwMaxDataRate_null","icc_dwMaxDataRate",b'\x00\x00\x00\x00'],
["icc_dwMaxDataRate_max","icc_dwMaxDataRate",b'\xff\xff\xff\xff'],
["icc_bNumDataRatesSupported_higher","icc_bNumDataRatesSupported",b'\x50'],
["icc_bNumDataRatesSupported_max","icc_bNumDataRatesSupported",b'\xff'],
["icc_dwMaxIFSD_null","icc_dwMaxIFSD",b'\x00\x00\x00\x00'],
["icc_dwMaxIFSD_max","icc_dwMaxIFSD",b'\xff\xff\xff\xff'],
["icc_dwSynchProtocols_null","icc_dwSynchProtocols",b'\x00\x00\x00\x00'],
["icc_dwSynchProtocols_max","icc_dwSynchProtocols",b'\xff\xff\xff\xff'],
["icc_dwMechanical_null","icc_dwMechanical",b'\x00\x00\x00\x00'],
["icc_dwMechanical_max","icc_dwMechanical",b'\xff\xff\xff\xff'],
["icc_dwFeatures_null","icc_dwFeatures",b'\x00\x00\x00\x00'],
["icc_dwFeatures_max","icc_dwFeatures",b'\xff\xff\xff\xff'],
["icc_dwMaxCCIDMessageLength_null","icc_dwMaxCCIDMessageLength",b'\x00\x00\x00\x00'],
["icc_dwMaxCCIDMessageLength_max","icc_dwMaxCCIDMessageLength",b'\xff\xff\xff\xff'],
["icc_bClassGetResponse_higher","icc_bClassGetResponse",b'\x50'],
["icc_bClassGetResponse_max","icc_bClassGetResponse",b'\xff'],
["icc_bClassEnvelope_higher","icc_bClassEnvelope",b'\x50'],
["icc_bClassEnvelope_max","icc_bClassEnvelope",b'\xff'],
["icc_wLcdLayout_higher","icc_wLcdLayout",b'\x50\x50'],
["icc_wLcdLayout_max","icc_wLcdLayout",b'\xff\xff'],
["icc_bPinSupport_higher","icc_bPinSupport",b'\x50'],
["icc_bPinSupport_max","icc_bPinSupport",b'\xff'],
["icc_bMaxCCIDBusySlots_null","icc_bMaxCCIDBusySlots",b'\x00'],
["icc_bMaxCCIDBusySlots_higher","icc_bMaxCCIDBusySlots",b'\x50'],
["icc_bMaxCCIDBusySlots_max","icc_bMaxCCIDBusySlots",b'\xff'],
["SetParameters_bMessageType_null","SetParameters_bMessageType",b'\x00'],
["SetParameters_bMessageType_max","SetParameters_bMessageType",b'\xff'],
["SetParameters_dwLength_null","SetParameters_dwLength",b'\x00\x00\x00\x00'],
["SetParameters_dwLength_lower","SetParameters_dwLength",b'\x01\x00\x00\x00'],
["SetParameters_dwLength_higher","SetParameters_dwLength",b'\x7f\x00\x00\x00'],
["SetParameters_dwLength_max","SetParameters_dwLength",b'\xff\xff\xff\xff'],
["SetParameters_bSlot_invalid","SetParameters_bSlot",b'\xff'],
["SetParameters_bStatus_invalid","SetParameters_bStatus",b'\xff'],
["SetParameters_bError_invalid","SetParameters_bError",b'\xff'],
["SetParameters_bProtocolNum_invalid","SetParameters_bProtocolNum",b'\xff'],
["IccPowerOn_bMessageType_null","IccPowerOn_bMessageType",b'\x00'],
["IccPowerOn_bMessageType_max","IccPowerOn_bMessageType",b'\xff'],
["IccPowerOn_dwLength_null","IccPowerOn_dwLength",b'\x00\x00\x00\x00'],
["IccPowerOn_dwLength_lower","IccPowerOn_dwLength",b'\x01\x00\x00\x00'],
["IccPowerOn_dwLength_higher","IccPowerOn_dwLength",b'\x7f\x00\x00\x00'],
["IccPowerOn_dwLength_max","IccPowerOn_dwLength",b'\xff\xff\xff\xff'],
["IccPowerOn_bSlot_invalid","IccPowerOn_bSlot",b'\xff'],
["IccPowerOn_bStatus_invalid","IccPowerOn_bStatus",b'\xff'],
["IccPowerOn_bError_invalid","IccPowerOn_bError",b'\xff'],
["IccPowerOn_bChainParameter_invalid","IccPowerOn_bChainParameter",b'\xff'],
["IccPowerOff_bMessageType_null","IccPowerOff_bMessageType",b'\x00'],
["IccPowerOff_bMessageType_max","IccPowerOff_bMessageType",b'\xff'],
["IccPowerOff_dwLength_null","IccPowerOff_dwLength",b'\x00\x00\x00\x00'],
["IccPowerOff_dwLength_lower","IccPowerOff_dwLength",b'\x01\x00\x00\x00'],
["IccPowerOff_dwLength_higher","IccPowerOff_dwLength",b'\x7f\x00\x00\x00'],
["IccPowerOff_dwLength_max","IccPowerOff_dwLength",b'\xff\xff\xff\xff'],
["IccPowerOff_bSlot_invalid","IccPowerOff_bSlot",b'\xff'],
["IccPowerOff_abRFU_invalid","IccPowerOff_abRFU",b'\xff'],
["XfrBlock_bMessageType_null","XfrBlock_bMessageType",b'\x00'],
["XfrBlock_bMessageType_max","XfrBlock_bMessageType",b'\xff'],
["XfrBlock_dwLength_null","XfrBlock_dwLength",b'\x00\x00\x00\x00'],
["XfrBlock_dwLength_lower","XfrBlock_dwLength",b'\x01\x00\x00\x00'],
["XfrBlock_dwLength_higher","XfrBlock_dwLength",b'\x7f\x00\x00\x00'],
["XfrBlock_dwLength_max","XfrBlock_dwLength",b'\xff\xff\xff\xff'],
["XfrBlock_bSlot_invalid","XfrBlock_bSlot",b'\xff'],
["XfrBlock_bStatus_invalid","XfrBlock_bStatus",b'\xff'],
["XfrBlock_bError_invalid","XfrBlock_bError",b'\xff'],
["XfrBlock_bChainParameter_invalid","XfrBlock_bChainParameter",b'\xff'],
["SetDataRateAndClockFrequency_bMessageType_null","SetDataRateAndClockFrequency_bMessageType",b'\x00'],
["SetDataRateAndClockFrequency_bMessageType_max","SetDataRateAndClockFrequency_bMessageType",b'\xff'],
["SetDataRateAndClockFrequency_dwLength_null","SetDataRateAndClockFrequency_dwLength",b'\x00\x00\x00\x00'],
["SetDataRateAndClockFrequency_dwLength_lower","SetDataRateAndClockFrequency_dwLength",b'\x01\x00\x00\x00'],
["SetDataRateAndClockFrequency_dwLength_higher","SetDataRateAndClockFrequency_dwLength",b'\x7f\x00\x00\x00'],
["SetDataRateAndClockFrequency_dwLength_max","SetDataRateAndClockFrequency_dwLength",b'\xff\xff\xff\xff'],
["SetDataRateAndClockFrequency_bSlot_invalid","SetDataRateAndClockFrequency_bSlot",b'\xff'],
["SetDataRateAndClockFrequency_bStatus_invalid","SetDataRateAndClockFrequency_bStatus",b'\xff'],
["SetDataRateAndClockFrequency_bError_invalid","SetDataRateAndClockFrequency_bError",b'\xff'],
["SetDataRateAndClockFrequency_bRFU_invalid","SetDataRateAndClockFrequency_bRFU",b'\xff'],
["SetDataRateAndClockFrequency_dwClockFrequency_null","SetDataRateAndClockFrequency_dwClockFrequency",b'\x00\x00\x00\x00'],
["SetDataRateAndClockFrequency_dwClockFrequency_lower","SetDataRateAndClockFrequency_dwClockFrequency",b'\x01\x00\x00\x00'],
["SetDataRateAndClockFrequency_dwClockFrequency_higher","SetDataRateAndClockFrequency_dwClockFrequency",b'\x7f\x00\x00\x00'],
["SetDataRateAndClockFrequency_dwClockFrequency_max","SetDataRateAndClockFrequency_dwClockFrequency",b'\xff\xff\xff\xff'],
["SetDataRateAndClockFrequency_dwDataRate_null","SetDataRateAndClockFrequency_dwDataRate",b'\x00\x00\x00\x00'],
["SetDataRateAndClockFrequency_dwDataRate_lower","SetDataRateAndClockFrequency_dwDataRate",b'\x01\x00\x00\x00'],
["SetDataRateAndClockFrequency_dwDataRate_higher","SetDataRateAndClockFrequency_dwDataRate",b'\x7f\x00\x00\x00'],
["SetDataRateAndClockFrequency_dwDataRate_max","SetDataRateAndClockFrequency_dwDataRate",b'\xff\xff\xff\xff']

]

testcases_mass_storage_class = [
["inquiry_peripheral_max","inquiry_peripheral",b'\xff'],
["inquiry_RMB_null","inquiry_RMB",b'\x00'],
["inquiry_RMB_max","inquiry_RMB",b'\xff'],
["inquiry_version_invalid","inquiry_version",b'\xff'],
["inquiry_response_data_format_invalid","inquiry_version",b'\xff'],
["inquiry_config1_invalid","inquiry_version",b'\xff'],
["inquiry_config2_invalid","inquiry_version",b'\xff'],
["inquiry_config3_invalid","inquiry_version",b'\xff'],
["inquiry_vendor_id_formatstring","inquiry_vendor_id",b'%x%x%n%n'],
["inquiry_vendor_id_overflow1","inquiry_vendor_id",b'a' * 20],
["inquiry_vendor_id_overflow2","inquiry_vendor_id",b'a' * 50],
["inquiry_vendor_id_overflow3","inquiry_vendor_id",b'a' * 100],
["inquiry_vendor_id_overflow4","inquiry_vendor_id",b'a' * 255],
["inquiry_product_id_formatstring","inquiry_product_id",b'%x%x%x%x%x%x%n%n'],
["inquiry_product_id_overflow1","inquiry_product_id",b'a' * 20],
["inquiry_product_id_overflow2","inquiry_product_id",b'a' * 50],
["inquiry_product_id_overflow3","inquiry_product_id",b'a' * 100],
["inquiry_product_id_overflow4","inquiry_product_id",b'a' * 255],
["inquiry_product_revision_level_formatstring","inquiry_product_revision_level",b'%x%n'],
["inquiry_product_revision_level_overflow1","inquiry_product_revision_level",b'a' * 20],
["inquiry_product_revision_level_overflow2","inquiry_product_revision_level",b'a' * 50],
["inquiry_product_revision_level_overflow3","inquiry_product_revision_level",b'a' * 100],
["inquiry_product_revision_level_overflow4","inquiry_product_revision_level",b'a' * 255],
["read_capacity_logical_block_address_null","read_capacity_logical_block_address",b'\x00\x00\x00\x00'],
["read_capacity_logical_block_address_lower","read_capacity_logical_block_address",b'\x00\x00\x00\x01'],
["read_capacity_logical_block_address_higher","read_capacity_logical_block_address",b'\x00\xff\x00\x00'],
["read_capacity_logical_block_address_max","read_capacity_logical_block_address",b'\xff\xff\xff\xff'],
["read_capacity_length_null","read_capacity_length",b'\x00\x00\x00\x00'],
["read_capacity_length_lower","read_capacity_length",b'\x01\x00\x00\x01'],
["read_capacity_length_higher","read_capacity_length",b'\x00\xff\x00\x00'],
["read_capacity_length_max","read_capacity_length",b'\xff\xff\xff\xff'],
["read_format_capacity_capacity_list_length_null","read_format_capacity_capacity_list_length",b'\x00\x00\x00\x00'],
["read_format_capacity_capacity_list_length_lower","read_format_capacity_capacity_list_length",b'\x01\x00\x00\x01'],
["read_format_capacity_capacity_list_length_higher","read_format_capacity_capacity_list_length",b'\x00\xff\x00\x00'],
["read_format_capacity_capacity_list_length_max","read_format_capacity_capacity_list_length",b'\xff\xff\xff\xff'],
["read_format_capacity_number_of_blocks_null","read_format_capacity_number_of_blocks",b'\x00\x00\x00\x00'],
["read_format_capacity_number_of_blocks_lower","read_format_capacity_number_of_blocks",b'\x00\x00\x00\x01'],
["read_format_capacity_number_of_blocks_higher","read_format_capacity_number_of_blocks",b'\x00\xff\x00\x00'],
["read_format_capacity_number_of_blocks_max","read_format_capacity_number_of_blocks",b'\xff\xff\xff\xff'],
["read_format_capacity_descriptor_type_invalid","read_format_capacity_descriptor_type",b'\xff'],
["read_format_capacity_block_length_null","read_format_capacity_block_length",b'\x00\x00\x00'],
["read_format_capacity_block_length_lower","read_format_capacity_block_length",b'\x00\x01\x00'],
["read_format_capacity_block_length_higher","read_format_capacity_block_length",b'\x00\xff\xff'],
["read_format_capacity_block_length_max","read_format_capacity_block_length",b'\xff\xff\xff'],
["mode_sense_length_null","mode_sense_length",b'\x00'],
["mode_sense_length_lower","mode_sense_length",b'\x01'],
["mode_sense_length_higher","mode_sense_length",b'\x7f'],
["mode_sense_length_max","mode_sense_length",b'\xff'],
["mode_sense_medium_type_higher","mode_sense_medium_type",b'\x7f'],
["mode_sense_medium_type_max","mode_sense_medium_type",b'\xff'],
["mode_sense_device_specific_param_higher","mode_sense_device_specific_param",b'\x7f'],
["mode_sense_device_specific_param_max","mode_sense_device_specific_param",b'\xff'],
["mode_sense_block_descriptor_len_higher","mode_sense_block_descriptor_len",b'\x7f'],
["mode_sense_block_descriptor_len_max","mode_sense_block_descriptor_len",b'\xff']
]


testcases_hub_class = [
["hub_bLength_null","hub_bLength",0x00],
["hub_bLength_lower","hub_bLength",0x01],
["hub_bLength_higher","hub_bLength",0x7f],
["hub_bLength_max","hub_bLength",0xff],
["hub_bDescriptorType_null","hub_bDescriptorType",0x00],
["hub_bDescriptorType_invalid","hub_bDescriptorType",0xff],
["hub_bNbrPorts_null","hub_bNbrPorts",0x00],
["hub_bNbrPorts_lower","hub_bNbrPorts",0x01],
["hub_bNbrPorts_higher","hub_bNbrPorts",0x7f],
["hub_bNbrPorts_max","hub_bNbrPorts",0xff],
["hub_wHubCharacteristics_null","hub_wHubCharacteristics",0x0000],
["hub_wHubCharacteristics_max","hub_wHubCharacteristics",0xffff],
["hub_bHubContrCurrent_null","hub_bHubContrCurrent",0x00],
["hub_bHubContrCurrent_lower","hub_bHubContrCurrent",0x01],
["hub_bHubContrCurrent_higher","hub_bHubContrCurrent",0x7f],
["hub_bHubContrCurrent_max","hub_bHubContrCurrent",0xff]
]




########NEW FILE########
__FILENAME__ = timeout
from functools import wraps
import errno
import os
import signal

class TimeoutError(Exception):
    pass

def timeout(seconds=10, error_message=os.strerror(errno.ETIME)):
    def decorator(func):
        def _handle_timeout(signum, frame):
            raise TimeoutError(error_message)

        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.alarm(seconds)
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return result

        return wraps(func)(wrapper)

    return decorator

########NEW FILE########
__FILENAME__ = umap
#!/usr/bin/env python3
#
# umap.py
#
from serial import Serial, PARITY_NONE
import time
from Facedancer import *
from MAXUSBApp import *
from devices.networking import *
from devices.USBMassStorage import *
from devices.USBHub import *
from devices.USBIphone import *
from devices.USBAudio import *
from devices.USBKeyboard import *
from devices.USBPrinter import *
from devices.USBImage import *
from devices.USBCDC import *
from devices.USBVendorSpecific import *
from devices.USBSmartcard import *
from optparse import OptionParser
from optparse import OptionGroup
from collections import namedtuple, defaultdict
import codecs
import urllib.request
from testcases import *
from device_class_data import *
import sys
import platform


current_version = "1.03"
current_platform = platform.system()

print ("\n---------------------------------------")
print (" _   _ _ __ ___   __ _ _ __")   
print ("| | | | '_ ` _ \ / _` | '_ \\")  
print ("| |_| | | | | | | (_| | |_) |") 
print (" \__,_|_| |_| |_|\__,_| .__/")  
print ("                      |_|  ")
print ("\nThe USB host assessment tool")
print ("Andy Davis, NCC Group 2013")
print ("Version:", current_version)
print ("\nBased on Facedancer by Travis Goodspeed\n")
print ("For help type: umap.py -h")
print ("---------------------------------------\n")


parser = OptionParser(usage="%prog ", version=current_version)
group = OptionGroup(parser, "Experimental Options")

parser.add_option("-P", dest="serial", help="Facedancer serial port **Mandatory option** (SERIAL=/dev/ttyX or just 1 for COM1)")
parser.add_option("-L", action="store_true", dest="listclasses", default=False, help="List device classes supported by umap")
parser.add_option("-i", action="store_true", dest="identify", default=False, help="identify all supported device classes on connected host")
parser.add_option("-c", dest="cls", help="identify if a specific class on the connected host is supported (CLS=class:subclass:proto)")
parser.add_option("-O", action="store_true", dest="osid", default=False, help="Operating system identification")
parser.add_option("-e", dest="device", help="emulate a specific device (DEVICE=class:subclass:proto)")
parser.add_option("-n", action="store_true", dest="netsocket", default=False, help="Start network server connected to the bulk endpoints (TCP port 2001)")
parser.add_option("-v", dest="vid", help="specify Vendor ID (hex format e.g. 1a2b)")
parser.add_option("-p", dest="pid", help="specify Product ID (hex format e.g. 1a2b)")
parser.add_option("-r", dest="rev", help="specify product Revision (hex format e.g. 1a2b)")
parser.add_option("-f", dest="fuzzc", help="fuzz a specific class (FUZZC=class:subclass:proto:E/C/A[:start fuzzcase])")
parser.add_option("-s", dest="fuzzs", help="send a single fuzz testcase (FUZZS=class:subclass:proto:E/C:Testcase)")
parser.add_option("-d", dest="dly", help="delay between enumeration attempts (seconds): Default=1")
parser.add_option("-l", dest="log", help="log to a file")
parser.add_option("-R", dest="ref", help="Reference the VID/PID database (REF=VID:PID)")
parser.add_option("-u", action="store_true", dest="updatedb", default=False, help="update the VID/PID database (Internet connectivity required)")

group.add_option("-A", dest="apple", help="emulate an Apple iPhone device (APPLE=VID:PID:REV)")
group.add_option("-b", dest="vendor", help="brute-force vendor driver support (VENDOR=VID:PID)")

parser.add_option_group(group)

(options, args) = parser.parse_args()

device_vid = 0x1111
device_pid = 0x2222
device_rev = 0x3333
network_socket = False

if not options.serial:
    print ("Error: Facedancer serial port not supplied\n")
    sys.exit()
else:
    tmp_serial = options.serial

    if current_platform == "Windows":
        try:
            serial0 = int(tmp_serial)-1
        except:
            print ("Error: Invalid serial port specification")
            sys.exit()

    else:
        serial0 = tmp_serial

def connectserial():

    try:
        sp = Serial(serial0, 115200, parity=PARITY_NONE, timeout=2)
        return sp
    except:
        print ("\nError: Check serial port is connected to Facedancer board\n")
        sys.exit(0)

sp = connectserial()

if options.log:
    logfilepath = options.log
    fplog = open(logfilepath, mode='a')
    fplog.write ("---------------------------------------\n")
    fplog.write ("umap - the USB host assessment tool\n")
    fplog.write ("Andy Davis, NCC Group 2013\n")
    write_string = "Version:" + current_version + "\n"
    fplog.write (write_string)
    fplog.write ("\nBased on Facedancer by Travis Goodspeed\n")
    fplog.write ("---------------------------------------\n")

if options.netsocket:
    network_socket = True

if options.updatedb:
    print ("Downloading latest VID/PID database...")
    try:
        urllib.request.urlretrieve("http://www.linux-usb.org/usb.ids", "usb.ids")
        print ("Finished")
    except:
        print ("Error: Unable to contact server")


if options.vid:
    try:
        device_vid = int(options.vid,16)
        if device_vid > 65535:
            print ("Error: Invalid VID")
        else:
            print_output = "VID = %04x" % device_vid
            print (print_output)
            if options.log:
                fplog.write (print_output + "\n")
    except:
        print ("Error: Invalid VID")

if options.pid:
    try:
        device_pid = int(options.pid,16)
        if device_pid > 65535:
            print ("Error: Invalid PID")
        else:
            print_output = "PID = %04x" % device_pid
            print (print_output)
            if options.log:
                fplog.write (print_output + "\n")
    except:
        print ("Error: Invalid PID")

if options.rev:
    try:
        device_rev = int(options.rev,16)
        if device_rev > 65535:
            print ("Error: Invalid REV")
        else:
            print_output = "REV = %04x" % device_rev
            print (print_output)
            if options.log:
                fplog.write (print_output + "\n")
    except:
        print ("Error: Invalid REV")

if options.ref:
    vidpid = options.ref.split(':')
    if len(vidpid) != 2:
        print ("Error: VID/PID invalid")
    else:
        lookup_vid = vidpid[0]
        lookup_pid = vidpid[1]

        print ("Looking up VID=",lookup_vid, "/ PID=", lookup_pid)

        Vendor = namedtuple("Vendor", ['name', 'devices'])
        vendors = dict()

        with codecs.open("usb.ids", "r", "latin-1") as f:
            for line in f:
                if not line.strip():
                    continue
                line = line.rstrip()
                if line.startswith("#"):
                    continue
                if line.startswith("# List of known device classes, subclasses and protocols"): 
                    break
                if not line.startswith("\t"):
                    current_vendor, name = line.split(None, 1)
                    vendors[current_vendor] = Vendor(name=name, devices=dict())
                if line.startswith("\t"):
                    device_id, desc = line.lstrip().split(None, 1)
                    vendors[current_vendor].devices[device_id] = desc
        try:       
            print(vendors[lookup_vid].name, end=" ") 
        except:
            print ("\nVID could not be located")
        try:
            print(vendors[lookup_vid].devices[lookup_pid])
        except:
            print ("\nPID could not be located\n")

if options.dly:
    enumeration_delay = options.dly

    try:
        print ("Enumeration delay set to:", int(enumeration_delay))
        if options.log:
            write_string = "Enumeration delay set to:" + int( enumeration_delay) + "\n"
            fplog.write (write_string)

    except ValueError:
        print("Error: Enumeration delay is not an integer")
    
else:
    enumeration_delay = 1     

def optionerror():
    print ("Error: Invalid option\n")
    return


def execute_fuzz_testcase (device_class, device_subclass, device_proto, current_testcase, serialnum):
    
#    sp = connectserial()
    mode = 3

    if device_class == 8:
        mode = 4    # Hack to get the Mass storage device to stop for each fuzz case

    fd = Facedancer(sp, verbose=0)
    logfp = 0
    if options.log:
        logfp = fplog
    u = MAXUSBApp(fd, logfp, mode, current_testcase, verbose=0)
    if device_class == 1:
        d = USBAudioDevice(u, device_vid, device_pid, device_rev, verbose=0)
    elif device_class == 2:
        d = USBCDCDevice(u, device_vid, device_pid, device_rev, verbose=0)
    elif device_class == 3:
        d = USBKeyboardDevice(u, device_vid, device_pid, device_rev, verbose=0)
    elif device_class == 6:
        d = USBImageDevice(u, device_vid, device_pid, device_rev, device_class, device_subclass, device_proto, "ncc_group_logo.jpg", verbose=0)
    elif device_class == 7:
        d = USBPrinterDevice(u, device_vid, device_pid, device_rev, device_class, device_subclass, device_proto, verbose=0)
    elif device_class == 8:
        try:
            d = USBMassStorageDevice(u, device_vid, device_pid, device_rev, device_class, device_subclass, device_proto, "stick.img", verbose=0)
        except:
            print ("Error: stick.img not found - please create a disk image using dd")

    elif device_class == 9:
        d = USBHubDevice(u, device_vid, device_pid, device_rev, verbose=0)
    elif device_class == 10:
        d = USBCDCDevice(u, device_vid, device_pid, device_rev, verbose=0)
    elif device_class == 11:
        d = USBSmartcardDevice(u, device_vid, device_pid, device_rev, verbose=0)
    elif device_class == 14:
        d = USBImageDevice(u, device_vid, device_pid, device_rev, 0xe, 1, 0, "ncc_group_logo.jpg", verbose=0)   #HACK

    try:
        d.connect()
    except:
        pass
    try:
        d.run()
    except KeyboardInterrupt:
        d.disconnect()
        if options.log:
            fplog.close()

    time.sleep(int(enumeration_delay))


def connect_as_image (vid, pid, rev, mode):
    if mode == 1:
        ver1 = 0
        ver2 = 0
    else:
        ver1 = 1
        ver2 = 4
#    sp = connectserial()
    fake_testcase = ["dummy","",0]
    fd = Facedancer(sp, verbose=ver1)
    logfp = 0
    if options.log:
        logfp = fplog
    u = MAXUSBApp(fd, logfp, mode, fake_testcase, verbose=ver1)

    if network_socket == True:
        netserver(u, 2001).start()
        u.server_running = True
        input("Network socket listening on TCP port 2001 - Press Enter to continue with device emulation...")

    d = USBImageDevice(u, vid, pid, rev, 6, 1, 1, "ncc_group_logo.jpg", verbose=ver2)
    d.connect()
    try:
        d.run()
    except KeyboardInterrupt:
        d.disconnect()
        if options.log:
            fplog.close()


def connect_as_cdc (vid, pid, rev, mode):
    if mode == 1:
        ver1 = 0
        ver2 = 0
    else:
        ver1 = 1
        ver2 = 4
#    sp = connectserial()
    fake_testcase = ["dummy","",0]
    fd = Facedancer(sp, verbose=ver1)
    logfp = 0
    if options.log:
        logfp = fplog
    u = MAXUSBApp(fd, logfp, mode, fake_testcase, verbose=ver1)
    d = USBCDCDevice(u, vid, pid, rev, verbose=ver2)
    d.connect()
    try:
        d.run()
    except KeyboardInterrupt:
        d.disconnect()
        if options.log:
            fplog.close()


def connect_as_iphone (vid, pid, rev, mode):
    if mode == 1:
        ver1 = 0
        ver2 = 0
    else:
        ver1 = 1
        ver2 = 4
#    sp = connectserial()
    fake_testcase = ["dummy","",0]
    fd = Facedancer(sp, verbose=ver1)
    logfp = 0
    if options.log:
        logfp = fplog
    u = MAXUSBApp(fd, logfp, mode, fake_testcase, verbose=ver1)
    d = USBIphoneDevice(u, vid, pid, rev, verbose=ver2)
    d.connect()
    try:
        d.run()
    except KeyboardInterrupt:
        d.disconnect()
        if options.log:
            fplog.close()


def connect_as_audio (vid, pid, rev, mode):
    if mode == 1:
        ver1 = 0
        ver2 = 0
    else:
        ver1 = 1
        ver2 = 4
#    sp = connectserial()
    fake_testcase = ["dummy","",0]
    fd = Facedancer(sp, verbose=ver1)
    logfp = 0
    if options.log:
        logfp = fplog
    u = MAXUSBApp(fd, logfp, mode, fake_testcase, verbose=ver1)
    d = USBAudioDevice(u, vid, pid, rev, verbose=ver2)
    d.connect()
    try:
        d.run()
    except KeyboardInterrupt:
        d.disconnect()
        if options.log:
            fplog.close()


def connect_as_printer (vid, pid, rev, mode):
    if mode == 1:
        ver1 = 0
        ver2 = 0
    else:
        ver1 = 1
        ver2 = 4
#    sp = connectserial()
    fake_testcase = ["dummy","",0]
    fd = Facedancer(sp, verbose=ver1)
    logfp = 0
    if options.log:
        logfp = fplog
    u = MAXUSBApp(fd, logfp, mode, fake_testcase, verbose=ver1)
    d = USBPrinterDevice(u, vid, pid, rev, 7, 1, 2, verbose=ver2)
    d.connect()
    try:
        d.run()
    except KeyboardInterrupt:
        d.disconnect()
        if options.log:
            fplog.close()


def connect_as_keyboard (vid, pid, rev, mode):
    print ("network socket=")
    print (network_socket)
    if mode == 1:
        ver1 = 0
        ver2 = 0
    else:
        ver1 = 1
        ver2 = 4
#    sp = connectserial()
    fake_testcase = ["dummy","",0]
    fd = Facedancer(sp, verbose=ver1)
    logfp = 0
    if options.log:
        logfp = fplog
    u = MAXUSBApp(fd, logfp, mode, fake_testcase, verbose=ver1)
    d = USBKeyboardDevice(u, vid, pid, rev, verbose=ver2)
    d.connect()
    try:
        d.run()
    except KeyboardInterrupt:
        d.disconnect()
        if options.log:
            fplog.close()


def connect_as_smartcard (vid, pid, rev, mode):

    if mode == 1:
        ver1 = 0
        ver2 = 0
    else:
        ver1 = 1
        ver2 = 4
#    sp = connectserial()
    fake_testcase = ["dummy","",0]
    fd = Facedancer(sp, verbose=ver1)
    logfp = 0
    if options.log:
        logfp = fplog
    u = MAXUSBApp(fd, logfp, mode, fake_testcase, verbose=ver1)

    if network_socket == True:
        netserver(u, 2001).start()
        u.server_running = True
        input("Network socket listening on TCP port 2001 - Press Enter to continue with device emulation...")

    d = USBSmartcardDevice(u, vid, pid, rev, verbose=ver2)
    d.connect()
    try:
        d.run()
    except KeyboardInterrupt:
        d.disconnect()
        if options.log:
            fplog.close()


def connect_as_vendor (vid, pid, rev, mode):
    if mode == 1:
        ver1 = 0
        ver2 = 0
    else:
        ver1 = 1
        ver2 = 4
#    sp = connectserial()
    fake_testcase = ["dummy","",0]
    fd = Facedancer(sp, verbose=ver1)
    logfp = 0
    if options.log:
        logfp = fplog
    u = MAXUSBApp(fd, logfp, mode, fake_testcase, verbose=ver1)
    d = USBVendorDevice(u, vid, pid, rev, verbose=ver2)
    d.connect()
    try:
        d.run()
    except KeyboardInterrupt:
        d.disconnect()
        if options.log:
            fplog.close()



def connect_as_hub (vid, pid, rev, mode):
    if mode == 1:
        ver1 = 0
        ver2 = 0
    else:
        ver1 = 1
        ver2 = 4
#    sp = connectserial()
    fake_testcase = ["dummy","",0]
    fd = Facedancer(sp, verbose=ver1)
    logfp = 0
    if options.log:
        logfp = fplog
    u = MAXUSBApp(fd, logfp, mode, fake_testcase, verbose=ver1)
    d = USBHubDevice(u, vid, pid, rev, verbose=ver2)
    d.connect()
    try:
        d.run()
    except KeyboardInterrupt:
        d.disconnect()
        if options.log:
            fplog.close()


def connect_as_mass_storage (vid, pid, rev, mode):
    if mode == 1:
        ver1 = 0
        ver2 = 0
    else:
        ver1 = 1
        ver2 = 4
#    sp = connectserial()
    fake_testcase = ["dummy","",0] 
    fd = Facedancer(sp, verbose=ver1)
    logfp = 0
    if options.log:
        logfp = fplog
    u = MAXUSBApp(fd, logfp, mode, fake_testcase, verbose=ver1)

    if network_socket == True:
        netserver(u, 2001).start()
        u.server_running = True
        input("Network socket listening on TCP port 2001 - Press Enter to continue with device emulation...")

    try:
        d = USBMassStorageDevice(u, vid, pid, rev, 8, 6, 80, "stick.img", verbose=ver2)
        d.connect()
        try:
            d.run()
        except KeyboardInterrupt:
            d.disconnect()
            if options.log:
                fplog.close()

    except:
        print ("Error: stick.img not found - please create a disk image using dd")




def identify_classes (single_device):

    if single_device:
        supported_devices_id = single_device
    else:
        supported_devices_id = supported_devices
        
    class_count = 0


    while class_count < len(supported_devices_id):
        list_classes([supported_devices_id[class_count]])

        logfp = 0
        if options.log:
            logfp = fplog
        mode = 1 # identity mode

        if supported_devices_id[class_count][0] == 1:
            connect_as_audio (device_vid, device_pid, device_rev, 1)
        elif supported_devices_id[class_count][0] == 2:
            connect_as_cdc (device_vid, device_pid, device_rev, 1)
        elif supported_devices_id[class_count][0] == 3:
            connect_as_keyboard (device_vid, device_pid, device_rev, 1)
        elif supported_devices_id[class_count][0] == 6:
            connect_as_image (device_vid, device_pid, device_rev, 1)
        elif supported_devices_id[class_count][0] == 7:
            connect_as_printer (device_vid, device_pid, device_rev, 1)
        elif supported_devices_id[class_count][0] == 8:
            connect_as_mass_storage (device_vid, device_pid, device_rev, 1)
        elif supported_devices_id[class_count][0] == 9:
            connect_as_hub (device_vid, device_pid, device_rev, 1)
        elif supported_devices_id[class_count][0] == 10:
            connect_as_cdc (device_vid, device_pid, device_rev, 1)
        elif supported_devices_id[class_count][0] == 11:
            connect_as_smartcard (device_vid, device_pid, device_rev, 1)

        sys.stdout.flush()

        print ("")
        time.sleep(int(enumeration_delay)) 
        class_count += 1



def list_classes (devices_list):
    x = 0
    while x < len(devices_list):
        print ("%02x:%02x:%02x - " % (devices_list[x][0], devices_list[x][1], devices_list[x][2]), end="")

        class_name = 0
        while class_name < len (device_class_list):
            if (devices_list[x][0] == device_class_list[class_name][1]):
                print (device_class_list[class_name][0],": ",end="")
            class_name += 1

        subclass_name = 0
        while subclass_name < len (device_subclass_list):
            if (devices_list[x][0] == device_subclass_list[subclass_name][0]) and (devices_list[x][1] == device_subclass_list[subclass_name][2]):
                print (device_subclass_list[subclass_name][1],": ",end="")
            subclass_name += 1

        protocol_name = 0
        while protocol_name < len (device_protocol_list):
            if (devices_list[x][0] == device_protocol_list[protocol_name][0]) and (devices_list[x][2] == device_protocol_list[protocol_name][2]):
                print (device_protocol_list[protocol_name][1])
            protocol_name += 1

        x+=1


if options.listclasses:
    print ("XX:YY:ZZ - XX = Class : YY = Subclass : ZZ = Protocol")
    list_classes(supported_devices)

if options.identify:
    devtmp = []
    identify_classes(devtmp)

if options.fuzzs:
    error = 0
    devsubproto = options.fuzzs.split(':')

    if len(devsubproto) != 5:
        print ("Error: Device class specification invalid - too many parameters\n")
        sys.exit()

    try:
        usbclass = int(devsubproto[0],16)
        usbsubclass = int(devsubproto[1],16)
        usbproto = int(devsubproto[2],16)
        fuzztype = devsubproto[3]
        fuzztestcase = int(devsubproto[4])
    except:
        print ("Error: Device class specification invalid\n")
        sys.exit()

    if fuzztype == "E" and error != 1:
        print ("Fuzzing:")
        devicetmp = [[usbclass,usbsubclass,usbproto]]
        identify_classes(devicetmp)
        timestamp = time.strftime("%Y/%m/%d %H:%M:%S", time.localtime())
        print (timestamp, end="")
        print (" Enumeration phase: %04d -" % fuzztestcase, testcases_class_independent[fuzztestcase][0])
        execute_fuzz_testcase (usbclass,usbsubclass,usbproto,testcases_class_independent[fuzztestcase],serial0)

    elif fuzztype == "C" and error != 1:
        print ("Fuzzing:")
        timestamp = time.strftime("%Y/%m/%d %H:%M:%S", time.localtime())
        print (timestamp, end="")

        devicetmp = [[usbclass,usbsubclass,usbproto]]
        identify_classes(devicetmp)
        print (" Class-specific data...")
        if usbclass == 1:   #Audio
            print (" Audio class: %04d -" % fuzztestcase, testcases_audio_class[fuzztestcase][0])
            execute_fuzz_testcase (usbclass,usbsubclass,usbproto,testcases_audio_class[fuzztestcase],serial0)
        elif usbclass == 3:   #HID
            print (" HID class: %04d -" % fuzztestcase, testcases_hid_class[fuzztestcase][0])
            execute_fuzz_testcase (usbclass,usbsubclass,usbproto,testcases_hid_class[fuzztestcase],serial0)
        elif usbclass == 6:   #Image
            print (" Image class: %04d -" % fuzztestcase, testcases_image_class[fuzztestcase][0])
            execute_fuzz_testcase (usbclass,usbsubclass,usbproto,testcases_image_class[fuzztestcase],serial0)
        elif usbclass == 7:    #Printer
            print (" Printer class: %04d -" % fuzztestcase, testcases_printer_class[fuzztestcase][0])
            execute_fuzz_testcase (usbclass,usbsubclass,usbproto,testcases_printer_class[fuzztestcase],serial0)
        elif usbclass == 8:    #Mass Storage
            print (" Mass Storage class: %04d -" % fuzztestcase, testcases_mass_storage_class[fuzztestcase][0])
            execute_fuzz_testcase (usbclass,usbsubclass,usbproto,testcases_mass_storage_class[fuzztestcase],serial0)
        elif usbclass == 9:    #Hub
            print (" Hub class: %04d -" % fuzztestcase, testcases_hub_class[fuzztestcase][0])
            execute_fuzz_testcase (usbclass,usbsubclass,usbproto,testcases_hub_class[fuzztestcase],serial0)
        elif usbclass == 11:    #Printer
            print (" Smartcard class: %04d -" % fuzztestcase, testcases_smartcard_class[fuzztestcase][0])
            execute_fuzz_testcase (usbclass,usbsubclass,usbproto,testcases_smartcard_class[fuzztestcase],serial0)
        else:
            print ("\n***Class fuzzing not yet implemented for this device***\n")
        
    else:
        optionerror()

if options.fuzzc:
    start_fuzzcase = 0
    devsubproto = options.fuzzc.split(':')
    if len(devsubproto) > 5:
        print ("Error: Device class specification invalid - too many parameters\n")
        sys.exit()

    try:
        usbclass = int(devsubproto[0],16)
        usbsubclass = int(devsubproto[1],16)
        usbproto = int(devsubproto[2],16)
        fuzztype = devsubproto[3]
        try:
            if devsubproto[4]:
                start_fuzzcase = int(devsubproto[4])
        except:
            pass
    except:
        print ("Error: Device class specification invalid\n")
        sys.exit()

    if fuzztype == "E" or fuzztype == "A": 

        print ("Fuzzing:")
        if options.log:
            fplog.write ("Fuzzing:\n")
        devicetmp = [[usbclass,usbsubclass,usbproto]]
        identify_classes(devicetmp)
        print ("Enumeration phase...")
        if options.log:
            fplog.write ("Enumeration phase...\n")

        current_serial_port = 0
        x = 0
        if start_fuzzcase:
            if start_fuzzcase < len (testcases_class_independent):
                x = start_fuzzcase
            else:
                print ("Error: Invalid fuzzcase - starting from zero")
                if options.log:
                    fplog.write ("Error: Invalid fuzzcase - starting from zero\n")
        else:
            x = 0
        while (x < len (testcases_class_independent)):
            timestamp = time.strftime("%Y/%m/%d %H:%M:%S", time.localtime())
            print (timestamp, end="")
            print_output = " Enumeration phase: %04d - %s" % (x, testcases_class_independent[x][0])
            print (print_output)

            if options.log:
                fplog.write (timestamp)
                fplog.write (print_output)
                
            execute_fuzz_testcase (usbclass,usbsubclass,usbproto,testcases_class_independent[x],serial0)
            x+=1

    if fuzztype == "C" or fuzztype == "A":

        print ("Fuzzing:")
        if options.log:
            fplog.write ("Fuzzing:\n")
        devicetmp = [[usbclass,usbsubclass,usbproto]]
        identify_classes(devicetmp)
        print ("Class-specific data...")
        if options.log:
            fplog.write ("Class-specific data...\n")
        if usbclass == 3:   #HID

            x = 0
            if start_fuzzcase:
                if start_fuzzcase < len (testcases_hid_class):
                    x = start_fuzzcase
                else:
                    print ("Error: Invalid fuzzcase - starting from zero")
                    if options.log:
                        fplog.write ("Error: Invalid fuzzcase - starting from zero\n")
            else:
                x = 0
            while (x < len (testcases_hid_class)):
                timestamp = time.strftime("%Y/%m/%d %H:%M:%S", time.localtime())
                print (timestamp, end="")
                print_output = " HID class: %04d - %s" % (x, testcases_hid_class[x][0])
                print (print_output)

                if options.log:
                    fplog.write (timestamp)
                    fplog.write (print_output)

                execute_fuzz_testcase (usbclass,usbsubclass,usbproto,testcases_hid_class[x],serial0)
                x+=1

        elif usbclass == 6:   #Image
            x = 0
            if start_fuzzcase:
                if start_fuzzcase < len (testcases_image_class):
                    x = start_fuzzcase
                else:
                    print ("Error: Invalid fuzzcase - starting from zero")
                    if options.log:
                        fplog.write ("Error: Invalid fuzzcase - starting from zero\n")
            else:
                x = 0
            while (x < len (testcases_image_class)):
                timestamp = time.strftime("%Y/%m/%d %H:%M:%S", time.localtime())
                print (timestamp, end="")
                print_output = " Image class: %04d - %s" % (x, testcases_image_class[x][0])
                print (print_output)

                if options.log:
                    fplog.write (timestamp)
                    fplog.write (print_output)

                execute_fuzz_testcase (usbclass,usbsubclass,usbproto,testcases_image_class[x],serial0)
                x+=1

        elif usbclass == 7:   #Printer
            x = 0
            if start_fuzzcase:
                if start_fuzzcase < len (testcases_printer_class):
                    x = start_fuzzcase
                else:
                    print ("Error: Invalid fuzzcase - starting from zero")
                    if options.log:
                        fplog.write ("Error: Invalid fuzzcase - starting from zero\n")
            else:
                x = 0
            while (x < len (testcases_printer_class)):
                timestamp = time.strftime("%Y/%m/%d %H:%M:%S", time.localtime())
                print (timestamp, end="")
                print_output = " Printer class: %04d - %s" % (x, testcases_printer_class[x][0])
                print (print_output)

                if options.log:
                    fplog.write (timestamp)
                    fplog.write (print_output)

                execute_fuzz_testcase (usbclass,usbsubclass,usbproto,testcases_printer_class[x],serial0)
                x+=1

        elif usbclass == 1:   #Audio
            x = 0
            if start_fuzzcase:
                if start_fuzzcase < len (testcases_audio_class):
                    x = start_fuzzcase
                else:
                    print ("Error: Invalid fuzzcase - starting from zero")
                    if options.log:
                        fplog.write ("Error: Invalid fuzzcase - starting from zero\n")
            else:
                x = 0
            while (x < len (testcases_audio_class)):
                timestamp = time.strftime("%Y/%m/%d %H:%M:%S", time.localtime())
                print (timestamp, end="")
                print_output = " Audio class: %04d - %s" % (x, testcases_audio_class[x][0])
                print (print_output)

                if options.log:
                    fplog.write (timestamp)
                    fplog.write (print_output)

                execute_fuzz_testcase (usbclass,usbsubclass,usbproto,testcases_audio_class[x],serial0)
                x+=1

        elif usbclass == 8:   #Mass Storage
            x = 0
            if start_fuzzcase:
                if start_fuzzcase < len (testcases_mass_storage_class):
                    x = start_fuzzcase
                else:
                    print ("Error: Invalid fuzzcase - starting from zero")
                    if options.log:
                        fplog.write ("Error: Invalid fuzzcase - starting from zero\n")
            else:
                x = 0
            while (x < len (testcases_mass_storage_class)):
                timestamp = time.strftime("%Y/%m/%d %H:%M:%S", time.localtime())
                print (timestamp, end="")
                print_output = " Mass Storage class: %04d - %s" % (x, testcases_mass_storage_class[x][0])
                print (print_output)

                if options.log:
                    fplog.write (timestamp)
                    fplog.write (print_output)

                execute_fuzz_testcase (usbclass,usbsubclass,usbproto,testcases_mass_storage_class[x],serial0)
                x+=1

        elif usbclass == 9:   #Hub
            x = 0
            if start_fuzzcase:
                if start_fuzzcase < len (testcases_hub_class):
                    x = start_fuzzcase
                else:
                    print ("Error: Invalid fuzzcase - starting from zero")
                    if options.log:
                        fplog.write ("Error: Invalid fuzzcase - starting from zero\n")
            else:
                x = 0
            while (x < len (testcases_hub_class)):
                timestamp = time.strftime("%Y/%m/%d %H:%M:%S", time.localtime())
                print (timestamp, end="")
                print_output = " Hub class: %04d - %s" % (x, testcases_hub_class[x][0])
                print (print_output)

                if options.log:
                    fplog.write (timestamp)
                    fplog.write (print_output)

                execute_fuzz_testcase (usbclass,usbsubclass,usbproto,testcases_hub_class[x],serial0)
                x+=1

        elif usbclass == 11:   #Smartcard
            x = 0
            if start_fuzzcase:
                if start_fuzzcase < len (testcases_smartcard_class):
                    x = start_fuzzcase
                else:
                    print ("Error: Invalid fuzzcase - starting from zero")
                    if options.log:
                        fplog.write ("Error: Invalid fuzzcase - starting from zero\n")
            else:
                x = 0
            while (x < len (testcases_smartcard_class)):
                timestamp = time.strftime("%Y/%m/%d %H:%M:%S", time.localtime())
                print (timestamp, end="")
                print_output = " Smartcard class: %04d - %s" % (x, testcases_smartcard_class[x][0])
                print (print_output)

                if options.log:
                    fplog.write (timestamp)
                    fplog.write (print_output)

                execute_fuzz_testcase (usbclass,usbsubclass,usbproto,testcases_smartcard_class[x],serial0)
                x+=1

        else:
            print ("\nError: Class fuzzing not yet implemented for this device\n")


    if fuzztype != "C" and fuzztype != "E" and fuzztype != "A":
        optionerror()

if options.vendor:
    vidpid = options.vendor.split(':')
    vid = int(vidpid[0],16)
    pid = int(vidpid[1],16)
    rev = device_rev

    print ("Emulating vendor-specific device:", vidpid[0], vidpid[1])
    connect_as_vendor (vid, pid, rev, 1)

if options.apple:
    vidpidrev = options.apple.split(':')
    vid = int(vidpidrev[0],16)
    pid = int(vidpidrev[1],16)
    rev = int(vidpidrev[2],16)
    print ("Emulating iPhone device:", vidpidrev[0], vidpidrev[1], vidpidrev[2])
    connect_as_iphone (vid, pid, rev, 3)

if options.cls:
    devsubproto = options.cls.split(':')
    if len(devsubproto) != 3:
        print ("Error: Device class specification invalid\n")
    else:
        try:
            dev = int(devsubproto[0],16)
            sub = int(devsubproto[1],16)
            proto = int(devsubproto[2],16)
            devicetmp = [[dev,sub,proto]]
            identify_classes(devicetmp)
        except:
            print ("Error: Device class specification invalid\n")

if options.device:
    devsubproto = options.device.split(':')
    if len(devsubproto) != 3:
        print ("Error: Device class specification invalid\n")
        sys.exit()

    try:
        dev = int(devsubproto[0],16)
        sub = int(devsubproto[1],16)
        proto = int(devsubproto[2],16)
        devicetmp = [[dev,sub,proto]]
    except:
        print ("Error: Device class specification invalid\n")
        sys.exit()


    print ("Emulating ",end="")

    list_classes(devicetmp)


    if dev == 1:
        connect_as_audio (device_vid, device_pid, device_rev, 3)
    elif dev == 2:
        connect_as_cdc (device_vid, device_pid, device_rev, 3)
    elif dev == 3:
        connect_as_keyboard (device_vid, device_pid, device_rev, 3)
    elif dev == 6:
        connect_as_image (device_vid, device_pid, device_rev, 2)   
    elif dev == 7:
        connect_as_printer (device_vid, device_pid, device_rev, 0)
    elif dev == 8:
        connect_as_mass_storage (device_vid, device_pid, device_rev, 3)
    elif dev == 9:
        connect_as_hub (device_vid, device_pid, device_rev, 3)
    elif dev == 10:
        connect_as_cdc (device_vid, device_pid, device_rev, 0)
    elif dev == 11:
        connect_as_smartcard (device_vid, device_pid, device_rev, 3)
    else:
        print ("Error: Device not supported\n")

if options.osid:

    print ("Fingerprinting the connected host - please wait...")

    try:
        print (vid)
    except:
        vid = 0x1111

    try:
        print (pid)
    except:
        pid = 0x2222

    try:
        print (rev)
    except:
        rev = 0x3333

#    sp = connectserial()
    fake_testcase = ["dummy","",0]
    fd = Facedancer(sp, verbose=0)
    logfp = 0
    if options.log:
        logfp = fplog
    u = MAXUSBApp(fd, logfp, 3, fake_testcase, verbose=0)
    d = USBPrinterDevice(u, vid, pid, rev, 7, 1, 2, verbose=0)
    d.connect()
    try:
        d.run()
    except KeyboardInterrupt:
        d.disconnect()
        if options.log:
            fplog.close()

    matching1 = [s for s in u.fingerprint if "GetDes:1:0" in s]
    matching2 = [s for s in u.fingerprint if "GetDes:2:0" in s]

    if len(matching1) == 2 and len(matching2) == 2 and len(u.fingerprint) == 5:
        print ("\nOS Matches: Sony Playstation 3\n")
        sys.exit()

    if any("SetFea" in s for s in u.fingerprint):
        print ("\nOS Matches: Apple iPad/iPhone\n")
        sys.exit()
    
    matching = [s for s in u.fingerprint if "SetInt" in s]
    if len(matching) == 2:
        print ("\nOS Matches: Ubuntu Linux\n")
        sys.exit()

    if any("GetDes:3:4" in s for s in u.fingerprint):
        print ("\nOS Matches: Chrome OS\n")
        sys.exit()

    matching = [s for s in u.fingerprint if "GetDes:3:3" in s]
    if len(matching) == 2:
        print ("\nOS Matches: Microsoft Windows 8\n")
        sys.exit()

    print ("\nUnknown OS - Fingerprint:")
    print (u.fingerprint) 


if options.log:
    fplog.close()



########NEW FILE########
__FILENAME__ = USB
# USB.py
#
# Contains definition of USB class, which is just a container for a bunch of
# constants/enums associated with the USB protocol.
#
# TODO: would be nice if this module could re-export the other USB* classes so
# one need import only USB to get all the functionality

class USB:
    state_detached                      = 0
    state_attached                      = 1
    state_powered                       = 2
    state_default                       = 3
    state_address                       = 4
    state_configured                    = 5
    state_suspended                     = 6

    request_direction_host_to_device    = 0
    request_direction_device_to_host    = 1

    request_type_standard               = 0
    request_type_class                  = 1
    request_type_vendor                 = 2

    request_recipient_device            = 0
    request_recipient_interface         = 1
    request_recipient_endpoint          = 2
    request_recipient_other             = 3

    feature_endpoint_halt               = 0
    feature_device_remote_wakeup        = 1
    feature_test_mode                   = 2

    desc_type_device                    = 1
    desc_type_configuration             = 2
    desc_type_string                    = 3
    desc_type_interface                 = 4
    desc_type_endpoint                  = 5
    desc_type_device_qualifier          = 6
    desc_type_other_speed_configuration = 7
    desc_type_interface_power           = 8
    desc_type_hid                       = 33
    desc_type_report                    = 34
    desc_type_cs_interface              = 36
    desc_type_cs_endpoint               = 37
    desc_type_hub                       = 41

    # while this holds for HID, it may not be a correct model for the USB
    # ecosystem at large
    if_class_to_desc_type = {
            3 : desc_type_hid,
            0x0b : desc_type_hid
    }

    def interface_class_to_descriptor_type(interface_class):
        return USB.if_class_to_desc_type.get(interface_class, None)


########NEW FILE########
__FILENAME__ = USBClass
# USBClass.py
#
# Contains class definition for USBClass, intended as a base class (in the OO
# sense) for implementing device classes (in the USB sense), eg, HID devices,
# mass storage devices.

class USBClass:
    name = "generic USB device class"

    # maps bRequest to handler function
    request_handlers = { }

    def __init__(self, verbose=0):
        self.interface = None
        self.verbose = verbose

        self.setup_request_handlers()

    def set_interface(self, interface):
        self.interface = interface

    def setup_request_handlers(self):
        """To be overridden for subclasses to modify self.class_request_handlers"""
        pass


########NEW FILE########
__FILENAME__ = USBConfiguration
# USBConfiguration.py
#
# Contains class definition for USBConfiguration.

class USBConfiguration:
    def __init__(self, maxusb_app, configuration_index, configuration_string, interfaces):
        self.maxusb_app = maxusb_app
        self.configuration_index        = configuration_index
        self.configuration_string       = configuration_string
        self.configuration_string_index = 0
        self.interfaces                 = interfaces

        self.attributes = 0xe0
        self.max_power = 0x32

        self.device = None

        for i in self.interfaces:
            i.set_configuration(self)

    def set_device(self, device):
        self.device = device

    def set_configuration_string_index(self, i):
        self.configuration_string_index = i

    def get_descriptor(self):
        interface_descriptors = bytearray()
        for i in self.interfaces:
            interface_descriptors += i.get_descriptor()

        if self.maxusb_app.testcase[1] == "conf_bLength":
            bLength = self.maxusb_app.testcase[2]
        else:
            bLength = 9

        if self.maxusb_app.testcase[1] == "conf_bDescriptorType":
            bDescriptorType = self.maxusb_app.testcase[2]
        else:
            bDescriptorType = 2

        if self.maxusb_app.testcase[1] == "conf_wTotalLength":
            wTotalLength = self.maxusb_app.testcase[2]
        else:
            wTotalLength = len(interface_descriptors) + 9

        if self.maxusb_app.testcase[1] == "conf_bNumInterfaces":
            bNumInterfaces = self.maxusb_app.testcase[2]
        else:
            bNumInterfaces = len(self.interfaces)



        d = bytes([
                bLength,          # length of descriptor in bytes
                bDescriptorType,          # descriptor type 2 == configuration
                wTotalLength & 0xff,
                (wTotalLength >> 8) & 0xff,
                bNumInterfaces,
                self.configuration_index,
                self.configuration_string_index,
                self.attributes,
                self.max_power
        ])

        return d + interface_descriptors


########NEW FILE########
__FILENAME__ = USBCSEndpoint
# USBCSEndpoint.py
#
# Contains class definition for USBCSEndpoint.

class USBCSEndpoint:

    def __init__(self, maxusb_app, cs_config):

        self.maxusb_app         = maxusb_app
        self.cs_config = cs_config
        self.number = self.cs_config[1]

        self.interface = None
        self.device_class = None

        self.request_handlers   = {
                1 : self.handle_clear_feature_request
        }

    def handle_clear_feature_request(self, req):
        if self.maxusb_app.mode != 2:
            #print("received CLEAR_FEATURE request for endpoint", self.number,
            #        "with value", req.value)
            self.interface.configuration.device.maxusb_app.send_on_endpoint(0, b'')

    def set_interface(self, interface):
        self.interface = interface

    # see Table 9-13 of USB 2.0 spec (pdf page 297)
    def get_descriptor(self):
        if self.cs_config[0] == 0x01:  # EP_GENERAL
            bLength = 7
            bDescriptorType = 37 # CS_ENDPOINT
            bDescriptorSubtype = 0x01 # EP_GENERAL
            bmAttributes = self.cs_config[2]
            bLockDelayUnits = self.cs_config[3]
            wLockDelay = self.cs_config[4]


        d = bytearray([
                bLength,          # length of descriptor in bytes
                bDescriptorType,          # descriptor type 5 == endpoint
                bDescriptorSubtype,
                bmAttributes,
                bLockDelayUnits,
                wLockDelay & 0xff,
                (wLockDelay >> 8) & 0xff,

        ])

        return d


########NEW FILE########
__FILENAME__ = USBCSInterface
# USBCSInterface.py
#
# Contains class definition for USBCSInterface.

from USB import *

class USBCSInterface:
    name = "USB class-specific interface"

    def __init__(self, maxusb_app, cs_config, usbclass, sub, proto, verbose=0, descriptors={}):

        self.maxusb_app = maxusb_app
        self.usbclass = usbclass
        self.sub = sub
        self.proto = proto
        self.cs_config = cs_config
        self.verbose = verbose
        self.descriptors = descriptors

        self.descriptors[USB.desc_type_cs_interface] = self.get_descriptor

        self.request_handlers = {
             6 : self.handle_get_descriptor_request,
            11 : self.handle_set_interface_request
        }


    # USB 2.0 specification, section 9.4.3 (p 281 of pdf)
    # HACK: blatant copypasta from USBDevice pains me deeply
    def handle_get_descriptor_request(self, req):
        dtype  = (req.value >> 8) & 0xff
        dindex = req.value & 0xff
        lang   = req.index
        n      = req.length

        response = None

        if self.verbose > 2:
            print(self.name, ("received GET_DESCRIPTOR req %d, index %d, " \
                    + "language 0x%04x, length %d") \
                    % (dtype, dindex, lang, n))

        # TODO: handle KeyError
        response = self.descriptors[dtype]
        if callable(response):
            response = response(dindex)

        if response:
            n = min(n, len(response))
            self.configuration.device.maxusb_app.send_on_endpoint(0, response[:n])

            if self.verbose > 5:
                print(self.name, "sent", n, "bytes in response")

    def handle_set_interface_request(self, req):
        if self.verbose > 0:
            print(self.name, "received SET_INTERFACE request")

        self.configuration.device.maxusb_app.stall_ep0()


    # Table 9-12 of USB 2.0 spec (pdf page 296)
    def get_descriptor(self):


        d = b''


        ######################### CDC class ####################################################################

        if  self.cs_config[0] == 0x00 and self.usbclass == 2:   
            bDescriptorType = 36 # CS_INTERFACE
            bDescriptorSubtype = 0x00 # Header Functional Descriptor
            bcdCDC = self.cs_config[1]

            d = bytearray([
                    bDescriptorType,
                    bDescriptorSubtype,
                    (bcdCDC >> 8) & 0xff,
                    bcdCDC & 0xff,
            ])
            config_length = bytes ([len(d)+1])
            d = config_length + d


        if  self.cs_config[0] == 0x01 and self.usbclass == 2:
            bDescriptorType = 36 # CS_INTERFACE
            bDescriptorSubtype = 0x01 # Call Management Functional Descriptor
            bmCapabilities = self.cs_config[1]
            bDataInterface = self.cs_config[2]

            d = bytearray([
                    bDescriptorType,
                    bDescriptorSubtype,
                    bmCapabilities,
                    bDataInterface
            ])
            config_length = bytes ([len(d)+1])
            d = config_length + d


        if  self.cs_config[0] == 0x02 and self.usbclass == 2:  
            bDescriptorType = 36 # CS_INTERFACE
            bDescriptorSubtype = 0x02 # Abstract Control Management Functional Descriptor
            bmCapabilities = self.cs_config[1]

            d = bytearray([
                    bDescriptorType,
                    bDescriptorSubtype,
                    bmCapabilities
            ])
            config_length = bytes ([len(d)+1])
            d = config_length + d


        if  self.cs_config[0] == 0x06 and self.usbclass == 2:
            bDescriptorType = 36 # CS_INTERFACE
            bDescriptorSubtype = 0x06 # Abstract Control Management Functional Descriptor
            bControlInterface = self.cs_config[1]
            bSubordinateInterface = self.cs_config[2]

            d = bytearray([
                    bDescriptorType,
                    bDescriptorSubtype,
                    bControlInterface,
                    bSubordinateInterface
            ])
            config_length = bytes ([len(d)+1])
            d = config_length + d


        if  self.cs_config[0] == 0x0f and self.usbclass == 2 and self.sub == 6:
            bDescriptorType = 36 # CS_INTERFACE
            bDescriptorSubtype = 0x0f # Ethernet Networking Functional Descriptor
            iMACAddress = self.cs_config[1]
            bmEthernetStatistics = self.cs_config[2]
            wMaxSegmentSize = self.cs_config[3]
            wNumberMCFilters = self.cs_config[4]
            bNumberPowerFilters = self.cs_config[5]

            d = bytearray([
                    bDescriptorType,
                    bDescriptorSubtype,
                    iMACAddress,
                    (bmEthernetStatistics >> 24) & 0xff,
                    (bmEthernetStatistics >> 16) & 0xff,
                    (bmEthernetStatistics >> 8) & 0xff,
                    bmEthernetStatistics & 0xff,
                    (wMaxSegmentSize >> 8) & 0xff,
                    wMaxSegmentSize & 0xff,
                    (wNumberMCFilters >> 8) & 0xff,
                    wNumberMCFilters & 0xff,
                    bNumberPowerFilters
            ])
            config_length = bytes ([len(d)+1])
            d = config_length + d


     ########################## Audio class #################################################################

        if  self.cs_config[0] == 0x01 and self.usbclass == 1 and self.sub == 1 and self.proto == 0:   # HEADER
            bDescriptorType = 36 # CS_INTERFACE
            bDescriptorSubtype = 0x01 #HEADER 
            bcdADC = self.cs_config[1]
            wTotalLength = self.cs_config[2]
            bInCollection = self.cs_config[3]
            baInterfaceNr1 = self.cs_config[4]
            baInterfaceNr2 = self.cs_config[5]  # HACK: hardcoded number of interface

            d = bytearray([
                    bDescriptorType,
                    bDescriptorSubtype,
                    (bcdADC >> 8) & 0xff,
                    bcdADC & 0xff,
                    wTotalLength & 0xff,
                    (wTotalLength >> 8) & 0xff,
                    bInCollection,
                    baInterfaceNr1,
                    baInterfaceNr2
            ])
            config_length = bytes ([len(d)+1])
            d = config_length + d


        elif  self.cs_config[0] == 0x02 and self.usbclass == 1 and self.sub == 1 and self.proto == 0:   # INPUT_TERMINAL
            bDescriptorType = 36 # CS_INTERFACE
            bDescriptorSubtype = 0x02 # INPUT_TERMINAL
            bTerminalID = self.cs_config[1] 
            wTerminalType = self.cs_config[2]
            bAssocTerminal = self.cs_config[3] # ID of associated output terminal
            bNrChannels = self.cs_config[4] # number of logical output channels
            wChannelConfig = self.cs_config[5] # spatial location of logical channels: Left front/Right front
            iChannelNames = self.cs_config[6] # Index of String descriptor describing name of logical channel
            iTerminal = self.cs_config[7] # Index of String descriptor describing input terminal 

            d = bytearray([
                    bDescriptorType,
                    bDescriptorSubtype,
                    bTerminalID,
                    wTerminalType & 0xff,
                    (wTerminalType >> 8) & 0xff,
                    bAssocTerminal,
                    bNrChannels,
                    wChannelConfig & 0xff,
                    (wChannelConfig >> 8) & 0xff,
                    iChannelNames,
                    iTerminal
            ])
            config_length = bytes ([len(d)+1])
            d = config_length + d


        elif  self.cs_config[0] == 0x03 and self.usbclass == 1 and self.sub == 1 and self.proto == 0:   # OUTPUT_TERMINAL
            bDescriptorType = 36 # CS_INTERFACE
            bDescriptorSubtype = 0x03 # OUTPUT_TERMINAL
            bTerminalID = self.cs_config[1]
            wTerminalType = self.cs_config[2]
            bAssocTerminal = self.cs_config[3] # ID of associated output terminal
            bSourceID = self.cs_config[4] # ID of the terminal to which this terminal is connected
            iTerminal = self.cs_config[5] # Index of String descriptor describing input terminal

            d = bytearray([
                    bDescriptorType,
                    bDescriptorSubtype,
                    bTerminalID,
                    wTerminalType & 0xff,
                    (wTerminalType >> 8) & 0xff,
                    bAssocTerminal,
                    bSourceID,
                    iTerminal
            ])
            config_length = bytes ([len(d)+1])
            d = config_length + d


        elif  self.cs_config[0] == 0x06 and self.usbclass == 1 and self.sub == 1 and self.proto == 0:   # FEATURE_UNIT
            bDescriptorType = 36 # CS_INTERFACE
            bDescriptorSubtype = 0x06 # FEATURE_UNIT
            bUnitID = self.cs_config[1]
            bsourceID = self.cs_config[2]
            bControlSize = self.cs_config[3]
            bmaControls0 = self.cs_config[4]
            bmaControls1 = self.cs_config[5]
            bmaControls2 = self.cs_config[6]
            iFeature = self.cs_config[7]

            d = bytearray([
                    bDescriptorType,
                    bDescriptorSubtype,
                    bUnitID,
                    bsourceID,
                    bControlSize,
                    bmaControls0,
                    bmaControls1,
                    bmaControls2,
                    iFeature
            ])
            config_length = bytes ([len(d)+1])
            d = config_length + d


        elif  self.cs_config[0] == 0x01 and self.usbclass == 1 and self.sub == 2 and self.proto == 0:   # AS_GENERAL
            bDescriptorType = 36 # CS_INTERFACE
            bDescriptorSubtype = 0x01 # AS_GENERAL
            bTerminalLink = self.cs_config[1]
            bDelay = self.cs_config[2]
            wFormatTag = self.cs_config[3]

            d = bytearray([
                    bDescriptorType,
                    bDescriptorSubtype,
                    bTerminalLink,
                    bDelay,
                    wFormatTag & 0xff,
                    (wFormatTag >> 8) & 0xff,
            ])
            config_length = bytes ([len(d)+1])
            d = config_length + d


        elif  self.cs_config[0] == 0x02 and self.usbclass == 1 and self.sub == 2 and self.proto == 0:   # FORMAT_TYPE
            bDescriptorType = 36 # CS_INTERFACE
            bDescriptorSubtype = 0x02 # FORMAT_TYPE
            bFormatType = self.cs_config[1]
            bNrChannels = self.cs_config[2]
            bSubFrameSize = self.cs_config[3]
            bBitResolution = self.cs_config[4]
            bSamFreqType = self.cs_config[5]
            tSamFreq1 = self.cs_config[6]
            tSamFreq2 = self.cs_config[7]

            d = bytearray([
                    bDescriptorType,
                    bDescriptorSubtype,
                    bFormatType,
                    bNrChannels,
                    bSubFrameSize,
                    bBitResolution,
                    bSamFreqType,
                    (tSamFreq1 >> 16) & 0xff,
                    (tSamFreq1 >> 8) & 0xff,
                    tSamFreq1 & 0xff,
                    (tSamFreq2 >> 16) & 0xff,
                    (tSamFreq2 >> 8) & 0xff,
                    tSamFreq2 & 0xff
            ])
            config_length = bytes ([len(d)+1])
            d = config_length + d

        ############################# end Audio class ##########################################

        return d


########NEW FILE########
__FILENAME__ = USBDevice
# USBDevice.py
#
# Contains class definitions for USBDevice and USBDeviceRequest.

from USB import *
from USBClass import *
import sys

class USBDevice:
    name = "generic device"

    def __init__(self, maxusb_app, device_class, device_subclass,
            protocol_rel_num, max_packet_size_ep0, vendor_id, product_id,
            device_rev, manufacturer_string, product_string,
            serial_number_string, configurations=[], descriptors={},
            verbose=0):
        self.maxusb_app = maxusb_app
        self.verbose = verbose

        self.supported_device_class_trigger = False
        self.supported_device_class_count = 0


        self.strings = [ ]

        self.usb_spec_version           = 0x0002
        self.device_class               = device_class
        self.device_subclass            = device_subclass
        self.protocol_rel_num           = protocol_rel_num
        self.max_packet_size_ep0        = max_packet_size_ep0
        self.vendor_id                  = vendor_id
        self.product_id                 = product_id
        self.device_rev                 = device_rev

        if self.maxusb_app.testcase[1] == "string_Manufacturer":
            self.manufacturer_string_id = self.get_string_id(self.maxusb_app.testcase[2])
        else:
            self.manufacturer_string_id = self.get_string_id(manufacturer_string)

        if self.maxusb_app.testcase[1] == "string_Product":
            self.product_string_id = self.get_string_id(self.maxusb_app.testcase[2])
        else:
            self.product_string_id = self.get_string_id(product_string)

        if self.maxusb_app.testcase[1] == "string_Serial":
            self.serial_number_string_id = self.get_string_id(self.maxusb_app.testcase[2])
        else:
            self.serial_number_string_id = self.get_string_id(serial_number_string)




        # maps from USB.desc_type_* to bytearray OR callable
        self.descriptors = descriptors
        self.descriptors[USB.desc_type_device] = self.get_descriptor
        self.descriptors[USB.desc_type_configuration] = self.handle_get_configuration_descriptor_request
        self.descriptors[USB.desc_type_string] = self.handle_get_string_descriptor_request
        self.descriptors[USB.desc_type_hub] = self.handle_get_hub_descriptor_request
        self.descriptors[USB.desc_type_device_qualifier] = self.handle_get_device_qualifier_descriptor_request




        self.config_num = -1
        self.configuration = None
        self.configurations = configurations

        for c in self.configurations:
            csi = self.get_string_id(c.configuration_string)
            c.set_configuration_string_index(csi)
            c.set_device(self)

        self.state = USB.state_detached
        self.ready = False

        self.address = 0

        self.setup_request_handlers()

    def get_string_id(self, s):
        try:
            i = self.strings.index(s)
        except ValueError:
            # string descriptors start at index 1
            self.strings.append(s)
            i = len(self.strings)

        return i

    def setup_request_handlers(self):
        # see table 9-4 of USB 2.0 spec, page 279
        self.request_handlers = {
             0 : self.handle_get_status_request,
             1 : self.handle_clear_feature_request,
             3 : self.handle_set_feature_request,
             5 : self.handle_set_address_request,
             6 : self.handle_get_descriptor_request,
             7 : self.handle_set_descriptor_request,
             8 : self.handle_get_configuration_request,
             9 : self.handle_set_configuration_request,
            10 : self.handle_get_interface_request,
            11 : self.handle_set_interface_request,
            12 : self.handle_synch_frame_request
        }

    def connect(self):
        self.maxusb_app.connect(self)

        # skipping USB.state_attached may not be strictly correct (9.1.1.{1,2})
        self.state = USB.state_powered

    def disconnect(self):
        self.maxusb_app.disconnect()
        self.maxusb_app.server_running = False

        if self.maxusb_app.netserver_to_endpoint_sd:
            self.maxusb_app.netserver_to_endpoint_sd.close()

        if self.maxusb_app.netserver_from_endpoint_sd:
            self.maxusb_app.netserver_from_endpoint_sd.close()



        self.state = USB.state_detached

    def run(self):
        self.maxusb_app.service_irqs()

    def ack_status_stage(self):
        self.maxusb_app.ack_status_stage()

    def get_descriptor(self, n):

        if self.maxusb_app.testcase[1] == "dev_bLength":
            bLength = self.maxusb_app.testcase[2]
        else:
            bLength = 18

        if self.maxusb_app.testcase[1] == "dev_bDescriptorType":
            bDescriptorType = self.maxusb_app.testcase[2]
        else:
            bDescriptorType = 1

        if self.maxusb_app.testcase[1] == "dev_bMaxPacketSize0":
            bMaxPacketSize0 = self.maxusb_app.testcase[2]
        else:
            bMaxPacketSize0 = self.max_packet_size_ep0

        d = bytearray([
            bLength,       
            bDescriptorType,       
            (self.usb_spec_version >> 8) & 0xff,
            self.usb_spec_version & 0xff,
            self.device_class,
            self.device_subclass,
            self.protocol_rel_num,
            bMaxPacketSize0,
            self.vendor_id & 0xff,
            (self.vendor_id >> 8) & 0xff,
            self.product_id & 0xff,
            (self.product_id >> 8) & 0xff,
            self.device_rev & 0xff,
            (self.device_rev >> 8) & 0xff,
            self.manufacturer_string_id,
            self.product_string_id,
            self.serial_number_string_id,
            len(self.configurations)
        ])

        return d

    # IRQ handlers
    #####################################################

    def handle_get_device_qualifier_descriptor_request(self, n):

        bLength = 10
        bDescriptorType = 6
        bNumConfigurations = len(self.configurations)
        bReserved = 0
        bMaxPacketSize0 = self.max_packet_size_ep0

        d = bytearray([
            bLength,
            bDescriptorType,
            (self.usb_spec_version >> 8) & 0xff,
            self.usb_spec_version & 0xff,
            self.device_class,
            self.device_subclass,
            self.protocol_rel_num,
            bMaxPacketSize0,
            bNumConfigurations,
            bReserved    
        ])

        return d




    def handle_request(self, req):
        if self.verbose > 3:
            print(self.name, "received request", req)

        # figure out the intended recipient
        recipient_type = req.get_recipient()
        recipient = None
        index = req.get_index()
        if recipient_type == USB.request_recipient_device:
            recipient = self
        elif recipient_type == USB.request_recipient_interface:
            if (index & 0xff) < len(self.configuration.interfaces):
                recipient = self.configuration.interfaces[(index & 0xff)]
        elif recipient_type == USB.request_recipient_endpoint:
            recipient = self.endpoints.get(index, None)
        elif recipient_type == USB.request_recipient_other:
            recipient = self.configuration.interfaces[0]    #HACK for Hub class



        if not recipient:
            if self.verbose > 0:
                print(self.name, "invalid recipient, stalling")
            self.maxusb_app.stall_ep0()
            return

        # and then the type
        req_type = req.get_type()
        handler_entity = None
        if req_type == USB.request_type_standard:
            handler_entity = recipient
        elif req_type == USB.request_type_class:
            handler_entity = recipient.device_class
        elif req_type == USB.request_type_vendor:
            handler_entity = recipient.device_vendor



        if not handler_entity:
            if self.verbose > 0:
                print(self.name, "invalid handler entity, stalling")
            self.maxusb_app.stall_ep0()
            return



        if handler_entity == 9:         #HACK: for hub class
            handler_entity = recipient
        
        handler = handler_entity.request_handlers.get(req.request, None)

#        print ("DEBUG: Recipient=", recipient)
#        print ("DEBUG: Handler entity=", handler_entity)
#        print ("DEBUG: Hander=", handler)

        if not handler:

            if self.maxusb_app.mode == 2 or self.maxusb_app.mode == 3:

                self.maxusb_app.stop = True
                return

            if self.maxusb_app.mode == 1:

                print ("**SUPPORTED???**")
                if self.maxusb_app.fplog:
                    self.maxusb_app.fplog.write ("**SUPPORTED???**\n")
                self.maxusb_app.stop = True
                return

            else:

                print(self.name, "invalid handler, stalling")
                self.maxusb_app.stall_ep0()

        handler(req)

    def handle_data_available(self, ep_num, data):
        if self.state == USB.state_configured and ep_num in self.endpoints:
            endpoint = self.endpoints[ep_num]
            if callable(endpoint.handler):
                endpoint.handler(data)

    def handle_buffer_available(self, ep_num):
        if self.state == USB.state_configured and ep_num in self.endpoints:
            endpoint = self.endpoints[ep_num]
            if callable(endpoint.handler):
                endpoint.handler()
    
    # standard request handlers
    #####################################################

    # USB 2.0 specification, section 9.4.5 (p 282 of pdf)
    def handle_get_status_request(self, req):

        trace = "Dev:GetSta"
        self.maxusb_app.fingerprint.append(trace)


        if self.verbose > 2:
            print(self.name, "received GET_STATUS request")

        # self-powered and remote-wakeup (USB 2.0 Spec section 9.4.5)
#        response = b'\x03\x00'
        response = b'\x01\x00'
        self.maxusb_app.send_on_endpoint(0, response)

    # USB 2.0 specification, section 9.4.1 (p 280 of pdf)
    def handle_clear_feature_request(self, req):

        trace = "Dev:CleFea:%d:%d" % (req.request_type, req.value)
        self.maxusb_app.fingerprint.append(trace)

        if self.verbose > 2:
            print(self.name, "received CLEAR_FEATURE request with type 0x%02x and value 0x%02x" \
                % (req.request_type, req.value))
        
        #self.maxusb_app.send_on_endpoint(0, b'')

    # USB 2.0 specification, section 9.4.9 (p 286 of pdf)
    def handle_set_feature_request(self, req):

        trace = "Dev:SetFea" 
        self.maxusb_app.fingerprint.append(trace)


        if self.verbose > 2:
            print(self.name, "received SET_FEATURE request")

        response = b''
        self.maxusb_app.send_on_endpoint(0, response)




    # USB 2.0 specification, section 9.4.6 (p 284 of pdf)
    def handle_set_address_request(self, req):
        self.address = req.value
        self.state = USB.state_address
        self.ack_status_stage()

        trace = "Dev:SetAdr:%d" % self.address
        self.maxusb_app.fingerprint.append(trace)

        if self.verbose > 2:
            print(self.name, "received SET_ADDRESS request for address",
                    self.address)

    # USB 2.0 specification, section 9.4.3 (p 281 of pdf)
    def handle_get_descriptor_request(self, req):
        dtype  = (req.value >> 8) & 0xff
        dindex = req.value & 0xff
        lang   = req.index
        n      = req.length

        response = None

        trace = "Dev:GetDes:%d:%d" % (dtype,dindex)
        self.maxusb_app.fingerprint.append(trace)

        if self.verbose > 2:
            print(self.name, ("received GET_DESCRIPTOR req %d, index %d, " \
                    + "language 0x%04x, length %d") \
                    % (dtype, dindex, lang, n))

        response = self.descriptors.get(dtype, None)
        #print ("desc:", self.descriptors)
        if callable(response):
            response = response(dindex)

        if response:
            n = min(n, len(response))
            self.maxusb_app.verbose += 1
            self.maxusb_app.send_on_endpoint(0, response[:n])
            self.maxusb_app.verbose -= 1

            if self.verbose > 5:
                print(self.name, "sent", n, "bytes in response")
        else:
            self.maxusb_app.stall_ep0()

    def handle_get_configuration_descriptor_request(self, num):
        return self.configurations[num].get_descriptor()

    def handle_get_string_descriptor_request(self, num):
        if num == 0:
            d = bytes([
                    4,      # length of descriptor in bytes
                    3,      # descriptor type 3 == string
                    9,      # language code 0, byte 0
                    4       # language code 0, byte 1
            ])
        else:
            # string descriptors start at 1

            try:
                s = self.strings[num-1].encode('utf-16')
            except:
                s = self.strings[0].encode('utf-16')

            # Linux doesn't like the leading 2-byte Byte Order Mark (BOM);
            # FreeBSD is okay without it
            s = s[2:]

            d = bytearray([
                    len(s) + 2,     # length of descriptor in bytes
                    3               # descriptor type 3 == string
            ])
            d += s

        return d

    def handle_get_hub_descriptor_request(self, num):
        if self.maxusb_app.testcase[1] == "hub_bLength":
            bLength = self.maxusb_app.testcase[2]
        else:
            bLength = 9
        if self.maxusb_app.testcase[1] == "hub_bDescriptorType":
            bDescriptorType = self.maxusb_app.testcase[2]
        else:
            bDescriptorType = 0x29
        if self.maxusb_app.testcase[1] == "hub_bNbrPorts":
            bNbrPorts = self.maxusb_app.testcase[2]
        else:
            bNbrPorts = 4
        if self.maxusb_app.testcase[1] == "hub_wHubCharacteristics":
            wHubCharacteristics = self.maxusb_app.testcase[2]
        else:
            wHubCharacteristics = 0xe000
        if self.maxusb_app.testcase[1] == "hub_bPwrOn2PwrGood":
            bPwrOn2PwrGood = self.maxusb_app.testcase[2]
        else:
            bPwrOn2PwrGood = 0x32
        if self.maxusb_app.testcase[1] == "hub_bHubContrCurrent":
            bHubContrCurrent = self.maxusb_app.testcase[2]
        else:
            bHubContrCurrent = 0x64
        if self.maxusb_app.testcase[1] == "hub_DeviceRemovable":
            DeviceRemovable = self.maxusb_app.testcase[2]
        else:
            DeviceRemovable = 0
        if self.maxusb_app.testcase[1] == "hub_PortPwrCtrlMask":
            PortPwrCtrlMask = self.maxusb_app.testcase[2]
        else:
            PortPwrCtrlMask = 0xff

        hub_descriptor = bytes([
                bLength,                        # length of descriptor in bytes
                bDescriptorType,                # descriptor type 0x29 == hub
                bNbrPorts,                      # number of physical ports
                wHubCharacteristics & 0xff ,    # hub characteristics
                (wHubCharacteristics >> 8) & 0xff,
                bPwrOn2PwrGood,                 # time from power on til power good
                bHubContrCurrent,               # max current required by hub controller
                DeviceRemovable,
                PortPwrCtrlMask
        ])

        return hub_descriptor

    # USB 2.0 specification, section 9.4.8 (p 285 of pdf)
    def handle_set_descriptor_request(self, req):

        trace = "Dev:SetDes" 
        self.maxusb_app.fingerprint.append(trace)

        if self.verbose > 0:
            print(self.name, "received SET_DESCRIPTOR request")

    # USB 2.0 specification, section 9.4.2 (p 281 of pdf)
    def handle_get_configuration_request(self, req):

        trace = "Dev:GetCon" 
        self.maxusb_app.fingerprint.append(trace)


        if self.verbose > 0:
            print(self.name, "received GET_CONFIGURATION request")
        self.maxusb_app.send_on_endpoint(0, b'\x01') #HACK - once configuration supported



    # USB 2.0 specification, section 9.4.7 (p 285 of pdf)
    def handle_set_configuration_request(self, req):

        trace = "Dev:SetCon"
        self.maxusb_app.fingerprint.append(trace)

        if self.verbose > 0:
            print(self.name, "received SET_CONFIGURATION request")
        self.supported_device_class_trigger = True

        # configs are one-based
        self.config_num = req.value - 1
        #print ("DEBUG: config_num=", self.config_num)
        self.configuration = self.configurations[self.config_num]
        self.state = USB.state_configured

        # collate endpoint numbers
        self.endpoints = { }
        for i in self.configuration.interfaces:
            for e in i.endpoints:
                self.endpoints[e.number] = e

        # HACK: blindly acknowledge request
        self.ack_status_stage()

    # USB 2.0 specification, section 9.4.4 (p 282 of pdf)
    def handle_get_interface_request(self, req):

        trace = "Dev:GetInt"
        self.maxusb_app.fingerprint.append(trace)


        if self.verbose > 0:
            print(self.name, "received GET_INTERFACE request")

        if req.index == 0:
            # HACK: currently only support one interface
            self.maxusb_app.send_on_endpoint(0, b'\x00')
        else:
            self.maxusb_app.stall_ep0()

    # USB 2.0 specification, section 9.4.10 (p 288 of pdf)
    def handle_set_interface_request(self, req):

        trace = "Dev:SetInt"
        self.maxusb_app.fingerprint.append(trace)


        if self.verbose > 1:
            print(self.name, "received SET_INTERFACE request")

        self.maxusb_app.send_on_endpoint(0, b'')

    # USB 2.0 specification, section 9.4.11 (p 288 of pdf)
    def handle_synch_frame_request(self, req):

        trace = "Dev:SynFra"
        self.maxusb_app.fingerprint.append(trace)

        if self.verbose > 0:
            print(self.name, "received SYNCH_FRAME request")


class USBDeviceRequest:
    def __init__(self, raw_bytes):
        """Expects raw 8-byte setup data request packet"""

        self.request_type   = raw_bytes[0]
        self.request        = raw_bytes[1]
        self.value          = (raw_bytes[3] << 8) | raw_bytes[2]
        self.index          = (raw_bytes[5] << 8) | raw_bytes[4]
        self.length         = (raw_bytes[7] << 8) | raw_bytes[6]

    def __str__(self):
        s = "dir=%d, type=%d, rec=%d, r=%d, v=%d, i=%d, l=%d" \
                % (self.get_direction(), self.get_type(), self.get_recipient(),
                   self.request, self.value, self.index, self.length)
        return s

    def raw(self):
        """returns request as bytes"""
        b = bytes([ self.request_type, self.request,
                    (self.value  >> 8) & 0xff, self.value  & 0xff,
                    (self.index  >> 8) & 0xff, self.index  & 0xff,
                    (self.length >> 8) & 0xff, self.length & 0xff
                  ])
        return b

    def get_direction(self):
        return (self.request_type >> 7) & 0x01

    def get_type(self):
        return (self.request_type >> 5) & 0x03

    def get_recipient(self):
        return self.request_type & 0x1f

    # meaning of bits in wIndex changes whether we're talking about an
    # interface or an endpoint (see USB 2.0 spec section 9.3.4)
    def get_index(self):
        rec = self.get_recipient()
        if rec == 1:                # interface
            return self.index
        elif rec == 2:              # endpoint
    #        print (self.index, self.index & 0xff)
            return self.index






########NEW FILE########
__FILENAME__ = USBEndpoint
# USBEndpoint.py
#
# Contains class definition for USBEndpoint.

class USBEndpoint:
    direction_out               = 0x00
    direction_in                = 0x01

    transfer_type_control       = 0x00
    transfer_type_isochronous   = 0x01
    transfer_type_bulk          = 0x02
    transfer_type_interrupt     = 0x03

    sync_type_none              = 0x00
    sync_type_async             = 0x01
    sync_type_adaptive          = 0x02
    sync_type_synchronous       = 0x03

    usage_type_data             = 0x00
    usage_type_feedback         = 0x01
    usage_type_implicit_feedback = 0x02

    def __init__(self, maxusb_app, number, direction, transfer_type, sync_type,
            usage_type, max_packet_size, interval, handler):

        self.maxusb_app         = maxusb_app
        self.number             = number
        self.direction          = direction
        self.transfer_type      = transfer_type
        self.sync_type          = sync_type
        self.usage_type         = usage_type
        self.max_packet_size    = max_packet_size
        self.interval           = interval
        self.handler            = handler

        self.interface          = None

        self.request_handlers   = {
                1 : self.handle_clear_feature_request
        }

    def handle_clear_feature_request(self, req):


        if self.maxusb_app.mode != 2:
            #print("received CLEAR_FEATURE request for endpoint", self.number,
            #        "with value", req.value)
            self.interface.configuration.device.maxusb_app.send_on_endpoint(0, b'')

    def set_interface(self, interface):


        self.interface = interface

    # see Table 9-13 of USB 2.0 spec (pdf page 297)
    def get_descriptor(self):
        address = (self.number & 0x0f) | (self.direction << 7) 
        attributes = (self.transfer_type & 0x03) \
                   | ((self.sync_type & 0x03) << 2) \
                   | ((self.usage_type & 0x03) << 4)

        if self.maxusb_app.testcase[1] == "end_bLength":
            bLength = self.maxusb_app.testcase[2]
        else:
            bLength = 7

        if self.maxusb_app.testcase[1] == "end_bDescriptorType":
            bDescriptorType = self.maxusb_app.testcase[2]
        else:
            bDescriptorType = 5

        if self.maxusb_app.testcase[1] == "end_bEndpointAddress":
            bEndpointAddress = self.maxusb_app.testcase[2]
        else:
            bEndpointAddress = address

        if self.maxusb_app.testcase[1] == "end_wMaxPacketSize":
            wMaxPacketSize = self.maxusb_app.testcase[2]
        else:
            wMaxPacketSize = self.max_packet_size

        d = bytearray([
                bLength,          # length of descriptor in bytes
                bDescriptorType,          # descriptor type 5 == endpoint
                bEndpointAddress,
                attributes,
                (wMaxPacketSize >> 8) & 0xff,
                wMaxPacketSize & 0xff,
                self.interval
        ])

        return d


########NEW FILE########
__FILENAME__ = USBInterface
# USBInterface.py
#
# Contains class definition for USBInterface.

from USB import *

class USBInterface:
    name = "generic USB interface"

    def __init__(self, maxusb_app, interface_number, interface_alternate, interface_class,
            interface_subclass, interface_protocol, interface_string_index,
            verbose=0, endpoints=[], descriptors={}, cs_interfaces=[]):

        self.maxusb_app = maxusb_app
        self.number = interface_number
        self.alternate = interface_alternate
        self.iclass = interface_class
        self.subclass = interface_subclass
        self.protocol = interface_protocol
        self.string_index = interface_string_index

        self.endpoints = endpoints
        self.descriptors = descriptors
        self.cs_interfaces = cs_interfaces

        self.verbose = verbose

        self.descriptors[USB.desc_type_interface] = self.get_descriptor

        self.request_handlers = {
             6 : self.handle_get_descriptor_request,
            11 : self.handle_set_interface_request
        }

        self.configuration = None

        for e in self.endpoints:
            e.set_interface(self)

        self.device_class = None
        self.device_vendor = None

    def set_configuration(self, config):
        self.configuration = config

    # USB 2.0 specification, section 9.4.3 (p 281 of pdf)
    # HACK: blatant copypasta from USBDevice pains me deeply
    def handle_get_descriptor_request(self, req):
        dtype  = (req.value >> 8) & 0xff
        dindex = req.value & 0xff
        lang   = req.index
        n      = req.length

        response = None


        trace = "Int:GetDes:%d:%d" % (dtype,dindex)
        self.maxusb_app.fingerprint.append(trace)


        if self.verbose > 2:
            print(self.name, ("received GET_DESCRIPTOR req %d, index %d, " \
                    + "language 0x%04x, length %d") \
                    % (dtype, dindex, lang, n))

        # TODO: handle KeyError
        response = self.descriptors[dtype]
        if callable(response):
            response = response(dindex)

        if response:
            n = min(n, len(response))
            self.configuration.device.maxusb_app.send_on_endpoint(0, response[:n])

            if self.verbose > 5:
                print(self.name, "sent", n, "bytes in response")

    def handle_set_interface_request(self, req):

        trace = "Int:SetInt" 
        self.maxusb_app.fingerprint.append(trace)


        if self.verbose > 0:
            print(self.name, "received SET_INTERFACE request")

        self.configuration.device.maxusb_app.stall_ep0()
        #self.configuration.device.maxusb_app.send_on_endpoint(0, b'')

    # Table 9-12 of USB 2.0 spec (pdf page 296)
    def get_descriptor(self):

        if self.maxusb_app.testcase[1] == "int_bLength":
            bLength = self.maxusb_app.testcase[2]
        else:
            bLength = 9

        if self.maxusb_app.testcase[1] == "int_bDescriptorType":
            bDescriptorType = self.maxusb_app.testcase[2]
        else:
            bDescriptorType = 4

        if self.maxusb_app.testcase[1] == "int_bNumEndpoints":
            bNumEndpoints = self.maxusb_app.testcase[2]
        else:
            bNumEndpoints = len(self.endpoints)

        d = bytearray([
                bLength,          # length of descriptor in bytes
                bDescriptorType,          # descriptor type 4 == interface
                self.number,
                self.alternate,
                bNumEndpoints,
                self.iclass,
                self.subclass,
                self.protocol,
                self.string_index
        ])

        if self.iclass:
            iclass_desc_num = USB.interface_class_to_descriptor_type(self.iclass)
            if iclass_desc_num:
                d += self.descriptors[iclass_desc_num]
    
        for e in self.cs_interfaces:
            d += e.get_descriptor()

        for e in self.endpoints:
            d += e.get_descriptor()

        return d


########NEW FILE########
__FILENAME__ = USBVendor
# USBVendor.py
#
# Contains class definition for USBVendor, intended as a base class (in the OO
# sense) for implementing device vendors.

class USBVendor:
    name = "generic USB device vendor"

    # maps bRequest to handler function
    request_handlers = { }

    def __init__(self, verbose=0):
        self.device = None
        self.verbose = verbose

        self.setup_request_handlers()

    def set_device(self, device):
        self.device = device

    def setup_request_handlers(self):
        """To be overridden for subclasses to modify self.request_handlers"""
        pass


########NEW FILE########
__FILENAME__ = util
# util.py
#
# Random helpful functions.

import struct

def bytes_as_hex(b, delim=" "):
    return delim.join(["%02x" % x for x in b])

def change_byte_order(data):
    return (bytes(reversed(data)))

def int_to_bytestring(i):
    return struct.pack('B',int(i))
       

########NEW FILE########
