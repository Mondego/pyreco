__FILENAME__ = devinfo
# Copyright (C) 2009-2013 Wander Lairson Costa
#
# The following terms apply to all files associated
# with the software unless explicitly disclaimed in individual files.
#
# The authors hereby grant permission to use, copy, modify, distribute,
# and license this software and its documentation for any purpose, provided
# that existing copyright notices are retained in all copies and that this
# notice is included verbatim in any distributions. No written agreement,
# license, or royalty fee is required for any of the authorized uses.
# Modifications to this software may be copyrighted by their authors
# and need not follow the licensing terms described here, provided that
# the new terms are clearly indicated on the first page of each file where
# they apply.
#
# IN NO EVENT SHALL THE AUTHORS OR DISTRIBUTORS BE LIABLE TO ANY PARTY
# FOR DIRECT, INDIRECT, SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES
# ARISING OUT OF THE USE OF THIS SOFTWARE, ITS DOCUMENTATION, OR ANY
# DERIVATIVES THEREOF, EVEN IF THE AUTHORS HAVE BEEN ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# THE AUTHORS AND DISTRIBUTORS SPECIFICALLY DISCLAIM ANY WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.  THIS SOFTWARE
# IS PROVIDED ON AN "AS IS" BASIS, AND THE AUTHORS AND DISTRIBUTORS HAVE
# NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES, ENHANCEMENTS, OR
# MODIFICATIONS.

import usb.util

ID_VENDOR = 0x04d8
ID_PRODUCT = 0xfa2e

# transfer interfaces
INTF_BULK = 0
INTF_INTR = 1
INTF_ISO = 2

# endpoints address
EP_BULK = 1
EP_INTR = 2
EP_ISO = 3

# test type
TEST_NONE = 0
TEST_PCREAD = 1
TEST_PCWRITE = 2
TEST_LOOP = 3

# Vendor requests
PICFW_SET_TEST = 0x0e
PICFW_SET_TEST = 0x0f
PICFW_SET_VENDOR_BUFFER = 0x10
PICFW_GET_VENDOR_BUFFER = 0x11

def set_test_type(t, dev = None):
    if dev is None:
        dev = usb.core.find(idVendor = ID_VENDOR, idProduct = ID_PRODUCT)

    bmRequestType = usb.util.build_request_type(
                        usb.util.CTRL_OUT,
                        usb.util.CTRL_TYPE_VENDOR,
                        usb.util.CTRL_RECIPIENT_INTERFACE
                    )

    dev.ctrl_transfer(
        bmRequestType = bmRequestType,
        bRequest = PICFW_SET_TEST,
        wValue = t,
        wIndex = 0
    )


########NEW FILE########
__FILENAME__ = testall
#!/usr/bin/env python
#
# Copyright (C) 2009-2013 Wander Lairson Costa 
# 
# The following terms apply to all files associated
# with the software unless explicitly disclaimed in individual files.
# 
# The authors hereby grant permission to use, copy, modify, distribute,
# and license this software and its documentation for any purpose, provided
# that existing copyright notices are retained in all copies and that this
# notice is included verbatim in any distributions. No written agreement,
# license, or royalty fee is required for any of the authorized uses.
# Modifications to this software may be copyrighted by their authors
# and need not follow the licensing terms described here, provided that
# the new terms are clearly indicated on the first page of each file where
# they apply.
# 
# IN NO EVENT SHALL THE AUTHORS OR DISTRIBUTORS BE LIABLE TO ANY PARTY
# FOR DIRECT, INDIRECT, SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES
# ARISING OUT OF THE USE OF THIS SOFTWARE, ITS DOCUMENTATION, OR ANY
# DERIVATIVES THEREOF, EVEN IF THE AUTHORS HAVE BEEN ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
# 
# THE AUTHORS AND DISTRIBUTORS SPECIFICALLY DISCLAIM ANY WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.  THIS SOFTWARE
# IS PROVIDED ON AN "AS IS" BASIS, AND THE AUTHORS AND DISTRIBUTORS HAVE
# NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES, ENHANCEMENTS, OR
# MODIFICATIONS.

import utils
import unittest
import glob
import os.path

if __name__ == '__main__':
    suite = unittest.TestSuite()

    for i in glob.glob('*.py'):
        m = __import__(os.path.splitext(i)[0])
        if hasattr(m, 'get_suite'):
            suite.addTest(m.get_suite())

    utils.run_tests(suite)

########NEW FILE########
__FILENAME__ = test_backend
# Copyright (C) 2009-2013 Wander Lairson Costa
#
# The following terms apply to all files associated
# with the software unless explicitly disclaimed in individual files.
#
# The authors hereby grant permission to use, copy, modify, distribute,
# and license this software and its documentation for any purpose, provided
# that existing copyright notices are retained in all copies and that this
# notice is included verbatim in any distributions. No written agreement,
# license, or royalty fee is required for any of the authorized uses.
# Modifications to this software may be copyrighted by their authors
# and need not follow the licensing terms described here, provided that
# the new terms are clearly indicated on the first page of each file where
# they apply.
#
# IN NO EVENT SHALL THE AUTHORS OR DISTRIBUTORS BE LIABLE TO ANY PARTY
# FOR DIRECT, INDIRECT, SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES
# ARISING OUT OF THE USE OF THIS SOFTWARE, ITS DOCUMENTATION, OR ANY
# DERIVATIVES THEREOF, EVEN IF THE AUTHORS HAVE BEEN ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# THE AUTHORS AND DISTRIBUTORS SPECIFICALLY DISCLAIM ANY WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.  THIS SOFTWARE
# IS PROVIDED ON AN "AS IS" BASIS, AND THE AUTHORS AND DISTRIBUTORS HAVE
# NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES, ENHANCEMENTS, OR
# MODIFICATIONS.

import utils
import unittest
import devinfo
import usb.util
import usb.backend.libusb0 as libusb0
import usb.backend.libusb1 as libusb1
import usb.backend.openusb as openusb

class BackendTest(unittest.TestCase):
    def __init__(self, backend):
        unittest.TestCase.__init__(self)
        self.backend = backend

    def runTest(self):
        try:
            self.test_enumerate_devices()
            self.test_get_device_descriptor()
            self.test_get_configuration_descriptor()
            self.test_get_interface_descriptor()
            self.test_get_endpoint_descriptor()
            self.test_open_device()
            self.test_set_configuration()
            self.test_claim_interface()
            self.test_set_interface_altsetting()
            self.test_clear_halt()
            self.test_bulk_write_read()
            self.test_intr_write_read()
            self.test_iso_write_read()
            self.test_ctrl_transfer()
        except:
            # do this to not influence other tests upon error
            intf = self.backend.get_interface_descriptor(self.dev, 0, 0, 0)
            self.backend.release_interface(self.handle, intf.bInterfaceNumber)
            self.backend.close_device(self.handle)
            raise
        self.test_release_interface()
        #self.test_reset_device()
        self.test_close_device()
        #utils.delay_after_reset()

    def test_enumerate_devices(self):
        for d in self.backend.enumerate_devices():
            desc = self.backend.get_device_descriptor(d)
            if desc.idVendor == devinfo.ID_VENDOR and desc.idProduct == devinfo.ID_PRODUCT:
                self.dev = d
                return
        self.fail('PyUSB test device not found')

    def test_get_device_descriptor(self):
        dsc = self.backend.get_device_descriptor(self.dev)
        self.assertEqual(dsc.bLength, 18)
        self.assertEqual(dsc.bDescriptorType, usb.util.DESC_TYPE_DEVICE)
        self.assertEqual(dsc.bcdUSB, 0x0200)
        self.assertEqual(dsc.idVendor, devinfo.ID_VENDOR)
        self.assertEqual(dsc.idProduct, devinfo.ID_PRODUCT)
        self.assertEqual(dsc.bcdDevice, 0x0001)
        self.assertEqual(dsc.iManufacturer, 0x01)
        self.assertEqual(dsc.iProduct, 0x02)
        self.assertEqual(dsc.iSerialNumber, 0x03)
        self.assertEqual(dsc.bNumConfigurations, 0x01)
        self.assertEqual(dsc.bMaxPacketSize0, 8)
        self.assertEqual(dsc.bDeviceClass, 0x00)
        self.assertEqual(dsc.bDeviceSubClass, 0x00)
        self.assertEqual(dsc.bDeviceProtocol, 0x00)

    def test_get_configuration_descriptor(self):
        cfg = self.backend.get_configuration_descriptor(self.dev, 0)
        self.assertEqual(cfg.bLength, 9)
        self.assertEqual(cfg.bDescriptorType, usb.util.DESC_TYPE_CONFIG)
        self.assertEqual(cfg.wTotalLength, 78)
        self.assertEqual(cfg.bNumInterfaces, 0x01)
        self.assertEqual(cfg.bConfigurationValue, 0x01)
        self.assertEqual(cfg.iConfiguration, 0x00)
        self.assertEqual(cfg.bmAttributes, 0xC0)
        self.assertEqual(cfg.bMaxPower, 50)

    def test_get_interface_descriptor(self):
        intf = self.backend.get_interface_descriptor(self.dev, 0, 0, 0)
        self.assertEqual(intf.bLength, 9)
        self.assertEqual(intf.bDescriptorType, usb.util.DESC_TYPE_INTERFACE)
        self.assertEqual(intf.bInterfaceNumber, 0)
        self.assertEqual(intf.bAlternateSetting, 0)
        self.assertEqual(intf.bNumEndpoints, 2)
        self.assertEqual(intf.bInterfaceClass, 0x00)
        self.assertEqual(intf.bInterfaceSubClass, 0x00)
        self.assertEqual(intf.bInterfaceProtocol, 0x00)
        self.assertEqual(intf.iInterface, 0x00)

    def test_get_endpoint_descriptor(self):
        ep = self.backend.get_endpoint_descriptor(self.dev, 0, 0, 0, 0)
        self.assertEqual(ep.bLength, 7)
        self.assertEqual(ep.bDescriptorType, usb.util.DESC_TYPE_ENDPOINT)
        self.assertEqual(ep.bEndpointAddress, 0x01)
        self.assertEqual(ep.bmAttributes, 0x02)
        self.assertEqual(ep.wMaxPacketSize, 16)
        self.assertEqual(ep.bInterval, 0)

    def test_open_device(self):
        self.handle = self.backend.open_device(self.dev)

    def test_close_device(self):
        self.backend.close_device(self.handle)

    def test_set_configuration(self):
        cfg = self.backend.get_configuration_descriptor(self.dev, 0)
        self.backend.set_configuration(self.handle, cfg.bConfigurationValue)

    def test_set_interface_altsetting(self):
        intf = self.backend.get_interface_descriptor(self.dev, 0, 0, 0)
        self.backend.set_interface_altsetting(self.handle,
                                              intf.bInterfaceNumber,
                                              intf.bAlternateSetting)

    def test_claim_interface(self):
        intf = self.backend.get_interface_descriptor(self.dev, 0, 0, 0)
        self.backend.claim_interface(self.handle, intf.bInterfaceNumber)

    def test_release_interface(self):
        intf = self.backend.get_interface_descriptor(self.dev, 0, 0, 0)
        self.backend.release_interface(self.handle, intf.bInterfaceNumber)

    def test_bulk_write_read(self):
        self.backend.set_interface_altsetting(
                self.handle,
                0,
                devinfo.INTF_BULK
            )

        self.__write_read(
                self.backend.bulk_write,
                self.backend.bulk_read,
                devinfo.EP_BULK
            )

    def test_intr_write_read(self):
        self.backend.set_interface_altsetting(
                self.handle,
                0,
                devinfo.INTF_INTR
            )

        self.__write_read(
                self.backend.intr_write,
                self.backend.intr_read,
                devinfo.EP_INTR
            )

    def test_iso_write_read(self):
        self.backend.set_interface_altsetting(
                self.handle,
                0,
                devinfo.INTF_ISO
            )

        self.__write_read(
                self.backend.iso_write,
                self.backend.iso_read,
                devinfo.EP_ISO
            )

    def test_clear_halt(self):
        self.backend.clear_halt(self.handle, 0x01)
        self.backend.clear_halt(self.handle, 0x81)

    def test_ctrl_transfer(self):
        for data in (utils.get_array_data1(), utils.get_array_data2()):
            length = len(data) * data.itemsize
            buff = usb.util.create_buffer(length)

            ret = self.backend.ctrl_transfer(self.handle,
                                             0x40,
                                             devinfo.PICFW_SET_VENDOR_BUFFER,
                                             0,
                                             0,
                                             data,
                                             1000)
            self.assertEqual(ret,
                             length,
                             'Failed to write data: ' + str(data) + ', ' + str(length) + ' != ' + str(ret))

            ret = self.backend.ctrl_transfer(self.handle,
                                             0xC0,
                                             devinfo.PICFW_GET_VENDOR_BUFFER,
                                             0,
                                             0,
                                             buff,
                                             1000)

            self.assertEqual(ret, length)

            self.assertEqual(buff,
                             data,
                             'Failed to read data: ' + str(data) + ' != ' + str(ret))

    def test_reset_device(self):
        self.backend.reset_device(self.handle)

    def __write_read(self, write_fn, read_fn, ep):
        intf = self.backend.get_interface_descriptor(self.dev, 0, 0, 0).bInterfaceNumber
        for data in (utils.get_array_data1(), utils.get_array_data2()):
            length = len(data) * data.itemsize

            try:
                ret = write_fn(self.handle, ep, intf, data, 1000)
            except NotImplementedError:
                return

            self.assertEqual(ret,
                             length,
                             'Failed to write data: ' + \
                                str(data) + \
                                ', in EP = ' + \
                                str(ep))

            buff = usb.util.create_buffer(length)

            try:
                ret = read_fn(self.handle, ep | usb.util.ENDPOINT_IN, intf, buff, 1000)
            except NotImplementedError:
                return

            self.assertEqual(ret, length, str(ret) + ' != ' + str(length))

            self.assertEqual(buff,
                             data,
                             'Failed to read data: ' + \
                                str(data) + \
                                ', in EP = ' + \
                                str(ep))

def get_suite():
    suite = unittest.TestSuite()
    for m in (libusb1, libusb0, openusb):
        b = m.get_backend()
        if b is not None and utils.find_my_device(b):
            utils.logger.info('Adding %s(%s) to test suite...', BackendTest.__name__, m.__name__)
            suite.addTest(BackendTest(b))
        else:
            utils.logger.warning('%s(%s) is not available', BackendTest.__name__, m.__name__)
    return suite

if __name__ == '__main__':
    utils.run_tests(get_suite())

########NEW FILE########
__FILENAME__ = test_control
# Copyright (C) 2009-2013 Wander Lairson Costa
#
# The following terms apply to all files associated
# with the software unless explicitly disclaimed in individual files.
#
# The authors hereby grant permission to use, copy, modify, distribute,
# and license this software and its documentation for any purpose, provided
# that existing copyright notices are retained in all copies and that this
# notice is included verbatim in any distributions. No written agreement,
# license, or royalty fee is required for any of the authorized uses.
# Modifications to this software may be copyrighted by their authors
# and need not follow the licensing terms described here, provided that
# the new terms are clearly indicated on the first page of each file where
# they apply.
#
# IN NO EVENT SHALL THE AUTHORS OR DISTRIBUTORS BE LIABLE TO ANY PARTY
# FOR DIRECT, INDIRECT, SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES
# ARISING OUT OF THE USE OF THIS SOFTWARE, ITS DOCUMENTATION, OR ANY
# DERIVATIVES THEREOF, EVEN IF THE AUTHORS HAVE BEEN ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# THE AUTHORS AND DISTRIBUTORS SPECIFICALLY DISCLAIM ANY WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.  THIS SOFTWARE
# IS PROVIDED ON AN "AS IS" BASIS, AND THE AUTHORS AND DISTRIBUTORS HAVE
# NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES, ENHANCEMENTS, OR
# MODIFICATIONS.

import utils
import unittest
import struct
import usb.util
import usb.core
import usb.control
import usb.backend.libusb0 as libusb0
import usb.backend.libusb1 as libusb1
import usb.backend.openusb as openusb
import sys

class ControlTest(unittest.TestCase):
    def __init__(self, dev):
        unittest.TestCase.__init__(self)
        self.dev = dev

    def runTest(self):
        try:
            self.dev.set_configuration()
            self.test_getset_configuration()
            self.test_get_status()
            self.test_getset_descriptor()
            self.test_getset_interface()
            # this test case is problematic in Windows, and nobody could
            # figure out why. Let's disable it for now.
            if sys.platform not in ('win32', 'cygwin'):
                self.test_clearset_feature()
            self.test_get_string()
        finally:
            usb.util.dispose_resources(self.dev)

    def test_get_status(self):
        self.assertEqual(usb.control.get_status(self.dev), 1)
        self.assertEqual(usb.control.get_status(self.dev, self.dev[0][0,0]), 0)
        self.assertEqual(usb.control.get_status(self.dev, self.dev[0][0,0][0]), 0)
        self.assertRaises(ValueError, usb.control.get_status, (self.dev, 0), 0)

    def test_clearset_feature(self):
        e = self.dev[0][0,0][0]
        self.dev.set_interface_altsetting(0, 0)
        self.assertEqual(usb.control.get_status(self.dev, e), 0)
        usb.control.set_feature(self.dev, usb.control.ENDPOINT_HALT, e)
        self.assertEqual(usb.control.get_status(self.dev, e), 1)
        usb.control.clear_feature(self.dev, usb.control.ENDPOINT_HALT, e)
        self.assertEqual(usb.control.get_status(self.dev, e), 0)

    def test_getset_descriptor(self):
        # TODO: test set_descriptor
        dev_fmt = 'BBHBBBBHHHBBBB'
        dev_descr = (self.dev.bLength,
                     self.dev.bDescriptorType,
                     self.dev.bcdUSB,
                     self.dev.bDeviceClass,
                     self.dev.bDeviceSubClass,
                     self.dev.bDeviceProtocol,
                     self.dev.bMaxPacketSize0,
                     self.dev.idVendor,
                     self.dev.idProduct,
                     self.dev.bcdDevice,
                     self.dev.iManufacturer,
                     self.dev.iProduct,
                     self.dev.iSerialNumber,
                     self.dev.bNumConfigurations)
        ret = usb.control.get_descriptor(
                    self.dev,
                    struct.calcsize(dev_fmt),
                    self.dev.bDescriptorType,
                    0
                )
        self.assertEqual(struct.unpack(dev_fmt, ret.tostring()), dev_descr)

    def test_getset_configuration(self):
        usb.control.set_configuration(self.dev, 1)
        self.assertEqual(usb.control.get_configuration(self.dev), 1)

    def test_getset_interface(self):
        i = self.dev[0][0,0]
        usb.control.set_interface(
            self.dev,
            i.bInterfaceNumber,
            i.bAlternateSetting
        )
        self.assertEqual(usb.control.get_interface(
                            self.dev,
                            i.bInterfaceNumber),
                            i.bAlternateSetting
                        )

    # Although get_string is implemented in the util module,
    # we test it here for convenience
    def test_get_string(self):
        manufacturer_str = 'Travis Robinson'.encode('utf-16-le').decode('utf-16-le')
        product_str = 'Benchmark Device'.encode('utf-16-le').decode('utf-16-le')
        self.assertEqual(usb.util.get_string(self.dev, self.dev.iManufacturer), manufacturer_str)
        self.assertEqual(usb.util.get_string(self.dev, self.dev.iProduct), product_str)

def get_suite():
    suite = unittest.TestSuite()
    for m in (libusb1, libusb0, openusb):
        b = m.get_backend()
        if b is None:
            continue
        dev = utils.find_my_device(b)
        if dev is None:
            utils.logger.warning('Test hardware not found for backend %s', m.__name__)
            continue
        suite.addTest(ControlTest(dev))
    return suite

if __name__ == '__main__':
    utils.run_tests(get_suite())

########NEW FILE########
__FILENAME__ = test_find
# Copyright (C) 2009-2013 Wander Lairson Costa 
# 
# The following terms apply to all files associated
# with the software unless explicitly disclaimed in individual files.
# 
# The authors hereby grant permission to use, copy, modify, distribute,
# and license this software and its documentation for any purpose, provided
# that existing copyright notices are retained in all copies and that this
# notice is included verbatim in any distributions. No written agreement,
# license, or royalty fee is required for any of the authorized uses.
# Modifications to this software may be copyrighted by their authors
# and need not follow the licensing terms described here, provided that
# the new terms are clearly indicated on the first page of each file where
# they apply.
# 
# IN NO EVENT SHALL THE AUTHORS OR DISTRIBUTORS BE LIABLE TO ANY PARTY
# FOR DIRECT, INDIRECT, SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES
# ARISING OUT OF THE USE OF THIS SOFTWARE, ITS DOCUMENTATION, OR ANY
# DERIVATIVES THEREOF, EVEN IF THE AUTHORS HAVE BEEN ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
# 
# THE AUTHORS AND DISTRIBUTORS SPECIFICALLY DISCLAIM ANY WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.  THIS SOFTWARE
# IS PROVIDED ON AN "AS IS" BASIS, AND THE AUTHORS AND DISTRIBUTORS HAVE
# NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES, ENHANCEMENTS, OR
# MODIFICATIONS.

import utils
import usb.backend
from usb.core import find
import usb.util
import unittest
import devinfo

class _DeviceDescriptor(object):
    def __init__(self, idVendor, idProduct):
        self.bLength = 18
        self.bDescriptorType = usb.util.DESC_TYPE_DEVICE
        self.bcdUSB = 0x0200
        self.idVendor = idVendor
        self.idProduct = idProduct
        self.bcdDevice = 0x0001
        self.iManufacturer = 0
        self.iProduct = 0
        self.iSerialNumber = 0
        self.bNumConfigurations = 0
        self.bMaxPacketSize0 = 64
        self.bDeviceClass = 0xff
        self.bDeviceSubClass = 0xff
        self.bDeviceProtocol = 0xff
        self.bus = 1
        self.address = 1
        self.port_number= None

# We are only interested in test usb.find() function, we don't need
# to implement all IBackend stuff
class _MyBackend(usb.backend.IBackend):
    def __init__(self):
        self.devices = [_DeviceDescriptor(devinfo.ID_VENDOR, p) for p in range(4)]
    def enumerate_devices(self):
        return range(len(self.devices))
    def get_device_descriptor(self, dev):
        return self.devices[dev]

class FindTest(unittest.TestCase):
    def test_find(self):
        b = _MyBackend()
        self.assertEqual(find(backend=b, idVendor=1), None)
        self.assertNotEqual(find(backend=b, idProduct=1), None)
        self.assertEqual(len(find(find_all=True, backend=b)), len(b.devices))
        self.assertEqual(len(find(find_all=True, backend=b, idProduct=1)), 1)
        self.assertEqual(len(find(find_all=True, backend=b, idVendor=1)), 0)

        self.assertEqual(
                len(
                    find(
                        find_all=True,
                        backend=b,
                        custom_match = lambda d: d.idProduct==1
                    ),
                ),
                1
            )

        self.assertEqual(
                len(
                    find(
                        find_all=True,
                        backend=b,
                        custom_match = lambda d: d.idVendor==devinfo.ID_VENDOR,
                        idProduct=1
                    ),
                ),
                1
            )

def get_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(FindTest))
    return suite

if __name__ == '__main__':
    utils.run_tests(get_suite())

########NEW FILE########
__FILENAME__ = test_integration
# Copyright (C) 2009-2013 Wander Lairson Costa
#
# The following terms apply to all files associated
# with the software unless explicitly disclaimed in individual files.
#
# The authors hereby grant permission to use, copy, modify, distribute,
# and license this software and its documentation for any purpose, provided
# that existing copyright notices are retained in all copies and that this
# notice is included verbatim in any distributions. No written agreement,
# license, or royalty fee is required for any of the authorized uses.
# Modifications to this software may be copyrighted by their authors
# and need not follow the licensing terms described here, provided that
# the new terms are clearly indicated on the first page of each file where
# they apply.
#
# IN NO EVENT SHALL THE AUTHORS OR DISTRIBUTORS BE LIABLE TO ANY PARTY
# FOR DIRECT, INDIRECT, SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES
# ARISING OUT OF THE USE OF THIS SOFTWARE, ITS DOCUMENTATION, OR ANY
# DERIVATIVES THEREOF, EVEN IF THE AUTHORS HAVE BEEN ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# THE AUTHORS AND DISTRIBUTORS SPECIFICALLY DISCLAIM ANY WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.  THIS SOFTWARE
# IS PROVIDED ON AN "AS IS" BASIS, AND THE AUTHORS AND DISTRIBUTORS HAVE
# NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES, ENHANCEMENTS, OR
# MODIFICATIONS.

# Integration tests

import utils
import unittest
import usb.core
import devinfo
import usb._interop
import usb.util
import usb.backend.libusb0 as libusb0
import usb.backend.libusb1 as libusb1
import usb.backend.openusb as openusb

data_list = (utils.get_array_data1(),
             utils.get_array_data2(),
             utils.get_list_data1(),
             utils.get_list_data2(),
             utils.get_str_data1(),
             utils.get_str_data1())

class DeviceTest(unittest.TestCase):
    def __init__(self, dev):
        unittest.TestCase.__init__(self)
        self.dev = dev

    def runTest(self):
        try:
            self.test_attributes()
            self.test_timeout()
            self.test_set_configuration()
            self.test_set_interface_altsetting()
            self.test_write_read()
            self.test_write_array()
            self.test_ctrl_transfer()
            self.test_clear_halt()
            #self.test_reset()
        finally:
            usb.util.dispose_resources(self.dev)

    def test_attributes(self):
        self.assertEqual(self.dev.bLength, 18)
        self.assertEqual(self.dev.bDescriptorType, usb.util.DESC_TYPE_DEVICE)
        self.assertEqual(self.dev.bcdUSB, 0x0200)
        self.assertEqual(self.dev.idVendor, devinfo.ID_VENDOR)
        self.assertEqual(self.dev.idProduct, devinfo.ID_PRODUCT)
        self.assertEqual(self.dev.bcdDevice, 0x0001)
        self.assertEqual(self.dev.iManufacturer, 0x01)
        self.assertEqual(self.dev.iProduct, 0x02)
        self.assertEqual(self.dev.iSerialNumber, 0x03)
        self.assertEqual(self.dev.bNumConfigurations, 0x01)
        self.assertEqual(self.dev.bMaxPacketSize0, 8)
        self.assertEqual(self.dev.bDeviceClass, 0x00)
        self.assertEqual(self.dev.bDeviceSubClass, 0x00)
        self.assertEqual(self.dev.bDeviceProtocol, 0x00)

    def test_timeout(self):
        def set_invalid_timeout():
            self.dev.default_timeout = -1
        tmo = self.dev.default_timeout
        self.dev.default_timeout = 1
        self.assertEqual(self.dev.default_timeout, 1)
        self.dev.default_timeout = tmo
        self.assertEqual(self.dev.default_timeout, tmo)
        self.assertRaises(ValueError, set_invalid_timeout)
        self.assertEqual(self.dev.default_timeout, tmo)

    def test_set_configuration(self):
        cfg = self.dev[0].bConfigurationValue
        self.dev.set_configuration(cfg)
        self.dev.set_configuration()
        self.assertEqual(cfg, self.dev.get_active_configuration().bConfigurationValue)

    def test_set_interface_altsetting(self):
        intf = self.dev.get_active_configuration()[(0,0)]
        self.dev.set_interface_altsetting(intf.bInterfaceNumber, intf.bAlternateSetting)
        self.dev.set_interface_altsetting()

    def test_reset(self):
        self.dev.reset()
        utils.delay_after_reset()

    def test_write_read(self):
        altsettings = (devinfo.INTF_BULK, devinfo.INTF_INTR, devinfo.INTF_ISO)
        eps = (devinfo.EP_BULK, devinfo.EP_INTR, devinfo.EP_ISO)

        for alt in altsettings:
            self.dev.set_interface_altsetting(0, alt)
            for data in data_list:
                adata = utils.to_array(data)
                length = utils.data_len(data)
                buff = usb.util.create_buffer(length)

                try:
                    ret = self.dev.write(eps[alt], data)
                except NotImplementedError:
                    continue

                self.assertEqual(ret, length)

                self.assertEqual(ret,
                                 length,
                                 'Failed to write data: ' + \
                                    str(data) + ', in interface = ' + \
                                    str(alt)
                                )

                try:
                    ret = self.dev.read(eps[alt] | usb.util.ENDPOINT_IN, length)
                except NotImplementedError:
                    continue

                self.assertTrue(utils.array_equals(ret, adata),
                                 str(ret) + ' != ' + \
                                    str(adata) + ', in interface = ' + \
                                    str(alt)
                                )

                try:
                    ret = self.dev.write(eps[alt], data)
                except NotImplementedError:
                    continue

                self.assertEqual(ret, length)

                self.assertEqual(ret,
                                 length,
                                 'Failed to write data: ' + \
                                    str(data) + ', in interface = ' + \
                                    str(alt)
                                )

                try:
                    ret = self.dev.read(eps[alt] | usb.util.ENDPOINT_IN, buff)
                except NotImplementedError:
                    continue

                self.assertEqual(ret, length)

                self.assertTrue(utils.array_equals(buff, adata),
                                 str(buff) + ' != ' + \
                                    str(adata) + ', in interface = ' + \
                                    str(alt)
                                )
    def test_write_array(self):
        a = usb._interop.as_array('test')
        self.dev.set_interface_altsetting(0, devinfo.INTF_BULK)

        self.assertEquals(self.dev.write(devinfo.EP_BULK, a), len(a))

        self.assertTrue(utils.array_equals(
            self.dev.read(devinfo.EP_BULK | usb.util.ENDPOINT_IN, len(a)),
            a))

    def test_ctrl_transfer(self):
        for data in data_list:
            length = utils.data_len(data)
            adata = utils.to_array(data)

            ret = self.dev.ctrl_transfer(
                    0x40,
                    devinfo.PICFW_SET_VENDOR_BUFFER,
                    0,
                    0,
                    data)

            self.assertEqual(ret,
                             length,
                             'Failed to write data: ' + str(data))

            ret = utils.to_array(self.dev.ctrl_transfer(
                        0xC0,
                        devinfo.PICFW_GET_VENDOR_BUFFER,
                        0,
                        0,
                        length))

            self.assertTrue(utils.array_equals(ret, adata),
                             str(ret) + ' != ' + str(adata))

            buff = usb.util.create_buffer(length)

            ret = self.dev.ctrl_transfer(
                    0x40,
                    devinfo.PICFW_SET_VENDOR_BUFFER,
                    0,
                    0,
                    data)

            self.assertEqual(ret,
                             length,
                             'Failed to write data: ' + str(data))

            ret = self.dev.ctrl_transfer(
                        0xC0,
                        devinfo.PICFW_GET_VENDOR_BUFFER,
                        0,
                        0,
                        buff)

            self.assertEqual(ret, length)

            self.assertTrue(utils.array_equals(buff, adata),
                             str(buff) + ' != ' + str(adata))

    def test_clear_halt(self):
        self.dev.set_interface_altsetting(0, 0)
        self.dev.clear_halt(0x01)
        self.dev.clear_halt(0x81)

class ConfigurationTest(unittest.TestCase):
    def __init__(self, dev):
        unittest.TestCase.__init__(self)
        self.cfg = dev[0]
    def runTest(self):
        try:
            self.test_attributes()
            self.test_set()
        finally:
            usb.util.dispose_resources(self.cfg.device)
    def test_attributes(self):
        self.assertEqual(self.cfg.bLength, 9)
        self.assertEqual(self.cfg.bDescriptorType, usb.util.DESC_TYPE_CONFIG)
        self.assertEqual(self.cfg.wTotalLength, 78)
        self.assertEqual(self.cfg.bNumInterfaces, 0x01)
        self.assertEqual(self.cfg.bConfigurationValue, 0x01)
        self.assertEqual(self.cfg.iConfiguration, 0x00)
        self.assertEqual(self.cfg.bmAttributes, 0xC0)
        self.assertEqual(self.cfg.bMaxPower, 50)
    def test_set(self):
        self.cfg.set()

class InterfaceTest(unittest.TestCase):
    def __init__(self, dev):
        unittest.TestCase.__init__(self)
        self.dev = dev
        self.intf = dev[0][(0,0)]
    def runTest(self):
        try:
            self.dev.set_configuration()
            self.test_attributes()
            self.test_set_altsetting()
        finally:
            usb.util.dispose_resources(self.intf.device)
    def test_attributes(self):
        self.assertEqual(self.intf.bLength, 9)
        self.assertEqual(self.intf.bDescriptorType, usb.util.DESC_TYPE_INTERFACE)
        self.assertEqual(self.intf.bInterfaceNumber, 0)
        self.assertEqual(self.intf.bAlternateSetting, 0)
        self.assertEqual(self.intf.bNumEndpoints, 2)
        self.assertEqual(self.intf.bInterfaceClass, 0x00)
        self.assertEqual(self.intf.bInterfaceSubClass, 0x00)
        self.assertEqual(self.intf.bInterfaceProtocol, 0x00)
        self.assertEqual(self.intf.iInterface, 0x00)
    def test_set_altsetting(self):
        self.intf.set_altsetting()

class EndpointTest(unittest.TestCase):
    def __init__(self, dev):
        unittest.TestCase.__init__(self)
        self.dev = dev
        intf = dev[0][(0,0)]
        self.ep_out = usb.util.find_descriptor(intf, bEndpointAddress=0x01)
        self.ep_in = usb.util.find_descriptor(intf, bEndpointAddress=0x81)
    def runTest(self):
        try:
            self.dev.set_configuration()
            self.test_attributes()
            self.test_write_read()
        finally:
            usb.util.dispose_resources(self.dev)
    def test_attributes(self):
        self.assertEqual(self.ep_out.bLength, 7)
        self.assertEqual(self.ep_out.bDescriptorType, usb.util.DESC_TYPE_ENDPOINT)
        self.assertEqual(self.ep_out.bEndpointAddress, 0x01)
        self.assertEqual(self.ep_out.bmAttributes, 0x02)
        self.assertEqual(self.ep_out.wMaxPacketSize, 16)
        self.assertEqual(self.ep_out.bInterval, 0)
    def test_write_read(self):
        self.dev.set_interface_altsetting(0, 0)
        for data in data_list:
            adata = utils.to_array(data)
            length = utils.data_len(data)
            buff = usb.util.create_buffer(length)

            ret = self.ep_out.write(data)
            self.assertEqual(ret, length, 'Failed to write data: ' + str(data))
            ret = self.ep_in.read(length)
            self.assertTrue(utils.array_equals(ret, adata), str(ret) + ' != ' + str(adata))

            ret = self.ep_out.write(data)
            self.assertEqual(ret, length, 'Failed to write data: ' + str(data))
            ret = self.ep_in.read(buff)
            self.assertEqual(ret, length)
            self.assertTrue(utils.array_equals(buff, adata), str(buff) + ' != ' + str(adata))

def get_suite():
    suite = unittest.TestSuite()
    test_cases = (DeviceTest, ConfigurationTest, InterfaceTest, EndpointTest)
    for m in (libusb1, libusb0, openusb):
        b = m.get_backend()
        if b is None:
            continue
        dev = utils.find_my_device(b)
        if dev is None:
            utils.logger.warning('Test hardware not found for backend %s', m.__name__)
            continue

        for ObjectTestCase in test_cases:
            utils.logger.info('Adding %s(%s) to test suite...', ObjectTestCase.__name__, m.__name__)
            suite.addTest(ObjectTestCase(dev))

    return suite

if __name__ == '__main__':
    utils.run_tests(get_suite())

########NEW FILE########
__FILENAME__ = test_util
# Copyright (C) 2009-2013 Wander Lairson Costa 
# 
# The following terms apply to all files associated
# with the software unless explicitly disclaimed in individual files.
# 
# The authors hereby grant permission to use, copy, modify, distribute,
# and license this software and its documentation for any purpose, provided
# that existing copyright notices are retained in all copies and that this
# notice is included verbatim in any distributions. No written agreement,
# license, or royalty fee is required for any of the authorized uses.
# Modifications to this software may be copyrighted by their authors
# and need not follow the licensing terms described here, provided that
# the new terms are clearly indicated on the first page of each file where
# they apply.
# 
# IN NO EVENT SHALL THE AUTHORS OR DISTRIBUTORS BE LIABLE TO ANY PARTY
# FOR DIRECT, INDIRECT, SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES
# ARISING OUT OF THE USE OF THIS SOFTWARE, ITS DOCUMENTATION, OR ANY
# DERIVATIVES THEREOF, EVEN IF THE AUTHORS HAVE BEEN ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
# 
# THE AUTHORS AND DISTRIBUTORS SPECIFICALLY DISCLAIM ANY WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.  THIS SOFTWARE
# IS PROVIDED ON AN "AS IS" BASIS, AND THE AUTHORS AND DISTRIBUTORS HAVE
# NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES, ENHANCEMENTS, OR
# MODIFICATIONS.

import utils
import unittest
from usb.util import *
from devinfo import *
import usb.backend

class _ConfigurationDescriptor(object):
    def __init__(self, bConfigurationValue):
        self.bLength = 9
        self.bDescriptorType = DESC_TYPE_CONFIG
        self.wTotalLength = 18
        self.bNumInterfaces = 0
        self.bConfigurationValue = bConfigurationValue
        self.iConfiguration = 0
        self.bmAttributes = 0xc0
        self.bMaxPower = 50

class _DeviceDescriptor(object):
    def __init__(self):
        self.configurations = (_ConfigurationDescriptor(1), _ConfigurationDescriptor(2))
        self.bLength = 18
        self.bDescriptorType = usb.util.DESC_TYPE_DEVICE
        self.bcdUSB = 0x0200
        self.idVendor = ID_VENDOR
        self.idProduct = ID_PRODUCT
        self.bcdDevice = 0x0001
        self.iManufacturer = 0
        self.iProduct = 0
        self.iSerialNumber = 0
        self.bNumConfigurations = len(self.configurations)
        self.bMaxPacketSize0 = 64
        self.bDeviceClass = 0xff
        self.bDeviceSubClass = 0xff
        self.bDeviceProtocol = 0xff

class FindDescriptorTest(unittest.TestCase):
    def runTest(self):
        d = usb.core.find(idVendor=ID_VENDOR)
        if d is None:
            return

        self.assertEqual(find_descriptor(d, bConfigurationValue=10), None)
        self.assertNotEqual(find_descriptor(d, bConfigurationValue=1), None)
        self.assertEqual(len(find_descriptor(d, find_all=True, bConfigurationValue=10)), 0)
        self.assertEqual(len(find_descriptor(d, find_all=True, bConfigurationValue=1)), 1)
        self.assertEqual(len(find_descriptor(d, find_all=True)), d.bNumConfigurations)
        self.assertEqual(find_descriptor(d, custom_match = lambda c: c.bConfigurationValue == 10), None)
        self.assertNotEqual(find_descriptor(d, custom_match = lambda c: c.bConfigurationValue == 1), None)
        self.assertEqual(len(find_descriptor(d, find_all=True, custom_match = lambda c: c.bConfigurationValue == 10)), 0)
        self.assertEqual(len(find_descriptor(d, find_all=True, custom_match = lambda c: c.bConfigurationValue == 1)), 1)
        self.assertEqual(find_descriptor(d, custom_match = lambda c: c.bConfigurationValue == 10, bLength=9), None)
        self.assertNotEqual(find_descriptor(d, custom_match = lambda c: c.bConfigurationValue == 1, bLength=9), None)

        cfg = find_descriptor(d)
        self.assertTrue(isinstance(cfg, usb.core.Configuration))
        intf = find_descriptor(cfg)
        self.assertTrue(isinstance(intf, usb.core.Interface))

class UtilTest(unittest.TestCase):
    def test_endpoint_address(self):
        self.assertEqual(endpoint_address(0x01), 0x01)
        self.assertEqual(endpoint_address(0x81), 0x01)
    def test_endpoint_direction(self):
        self.assertEqual(endpoint_direction(0x01), ENDPOINT_OUT)
        self.assertEqual(endpoint_direction(0x81), ENDPOINT_IN)
    def test_endpoint_type(self):
        self.assertEqual(endpoint_type(ENDPOINT_TYPE_CTRL), ENDPOINT_TYPE_CTRL)
        self.assertEqual(endpoint_type(ENDPOINT_TYPE_ISO), ENDPOINT_TYPE_ISO)
        self.assertEqual(endpoint_type(ENDPOINT_TYPE_INTR), ENDPOINT_TYPE_INTR)
        self.assertEqual(endpoint_type(ENDPOINT_TYPE_BULK), ENDPOINT_TYPE_BULK)
    def test_ctrl_direction(self):
        self.assertEqual(ctrl_direction(CTRL_OUT), CTRL_OUT)
        self.assertEqual(ctrl_direction(CTRL_IN), CTRL_IN)
    def test_build_request_type(self):
        self.assertEqual(build_request_type(CTRL_OUT, CTRL_TYPE_STANDARD, CTRL_RECIPIENT_DEVICE), 0x00)
        self.assertEqual(build_request_type(CTRL_OUT, CTRL_TYPE_STANDARD, CTRL_RECIPIENT_INTERFACE), 0x01)
        self.assertEqual(build_request_type(CTRL_OUT, CTRL_TYPE_STANDARD, CTRL_RECIPIENT_ENDPOINT), 0x02)
        self.assertEqual(build_request_type(CTRL_OUT, CTRL_TYPE_STANDARD, CTRL_RECIPIENT_OTHER), 0x03)
        self.assertEqual(build_request_type(CTRL_OUT, CTRL_TYPE_CLASS, CTRL_RECIPIENT_DEVICE), 0x20)
        self.assertEqual(build_request_type(CTRL_OUT, CTRL_TYPE_CLASS, CTRL_RECIPIENT_INTERFACE), 0x21)
        self.assertEqual(build_request_type(CTRL_OUT, CTRL_TYPE_CLASS, CTRL_RECIPIENT_ENDPOINT), 0x22)
        self.assertEqual(build_request_type(CTRL_OUT, CTRL_TYPE_CLASS, CTRL_RECIPIENT_OTHER), 0x23)
        self.assertEqual(build_request_type(CTRL_OUT, CTRL_TYPE_VENDOR, CTRL_RECIPIENT_DEVICE), 0x40)
        self.assertEqual(build_request_type(CTRL_OUT, CTRL_TYPE_VENDOR, CTRL_RECIPIENT_INTERFACE), 0x41)
        self.assertEqual(build_request_type(CTRL_OUT, CTRL_TYPE_VENDOR, CTRL_RECIPIENT_ENDPOINT), 0x42)
        self.assertEqual(build_request_type(CTRL_OUT, CTRL_TYPE_VENDOR, CTRL_RECIPIENT_OTHER), 0x43)
        self.assertEqual(build_request_type(CTRL_OUT, CTRL_TYPE_RESERVED, CTRL_RECIPIENT_DEVICE), 0x60)
        self.assertEqual(build_request_type(CTRL_OUT, CTRL_TYPE_RESERVED, CTRL_RECIPIENT_INTERFACE), 0x61)
        self.assertEqual(build_request_type(CTRL_OUT, CTRL_TYPE_RESERVED, CTRL_RECIPIENT_ENDPOINT), 0x62)
        self.assertEqual(build_request_type(CTRL_OUT, CTRL_TYPE_RESERVED, CTRL_RECIPIENT_OTHER), 0x63)
        self.assertEqual(build_request_type(CTRL_IN, CTRL_TYPE_STANDARD, CTRL_RECIPIENT_DEVICE), 0x80)
        self.assertEqual(build_request_type(CTRL_IN, CTRL_TYPE_STANDARD, CTRL_RECIPIENT_INTERFACE), 0x81)
        self.assertEqual(build_request_type(CTRL_IN, CTRL_TYPE_STANDARD, CTRL_RECIPIENT_ENDPOINT), 0x82)
        self.assertEqual(build_request_type(CTRL_IN, CTRL_TYPE_STANDARD, CTRL_RECIPIENT_OTHER), 0x83)
        self.assertEqual(build_request_type(CTRL_IN, CTRL_TYPE_CLASS, CTRL_RECIPIENT_DEVICE), 0xa0)
        self.assertEqual(build_request_type(CTRL_IN, CTRL_TYPE_CLASS, CTRL_RECIPIENT_INTERFACE), 0xa1)
        self.assertEqual(build_request_type(CTRL_IN, CTRL_TYPE_CLASS, CTRL_RECIPIENT_ENDPOINT), 0xa2)
        self.assertEqual(build_request_type(CTRL_IN, CTRL_TYPE_CLASS, CTRL_RECIPIENT_OTHER), 0xa3)
        self.assertEqual(build_request_type(CTRL_IN, CTRL_TYPE_VENDOR, CTRL_RECIPIENT_DEVICE), 0xc0)
        self.assertEqual(build_request_type(CTRL_IN, CTRL_TYPE_VENDOR, CTRL_RECIPIENT_INTERFACE), 0xc1)
        self.assertEqual(build_request_type(CTRL_IN, CTRL_TYPE_VENDOR, CTRL_RECIPIENT_ENDPOINT), 0xc2)
        self.assertEqual(build_request_type(CTRL_IN, CTRL_TYPE_VENDOR, CTRL_RECIPIENT_OTHER), 0xc3)
        self.assertEqual(build_request_type(CTRL_IN, CTRL_TYPE_RESERVED, CTRL_RECIPIENT_DEVICE), 0xe0)
        self.assertEqual(build_request_type(CTRL_IN, CTRL_TYPE_RESERVED, CTRL_RECIPIENT_INTERFACE), 0xe1)
        self.assertEqual(build_request_type(CTRL_IN, CTRL_TYPE_RESERVED, CTRL_RECIPIENT_ENDPOINT), 0xe2)
        self.assertEqual(build_request_type(CTRL_IN, CTRL_TYPE_RESERVED, CTRL_RECIPIENT_OTHER), 0xe3)

def get_suite():
    suite = unittest.TestSuite()
    suite.addTest(FindDescriptorTest())
    suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(UtilTest))
    return suite

if __name__ == '__main__':
    utils.run_tests(get_suite())

########NEW FILE########
__FILENAME__ = utils
# Copyright (C) 2009-2013 Wander Lairson Costa 
# 
# The following terms apply to all files associated
# with the software unless explicitly disclaimed in individual files.
# 
# The authors hereby grant permission to use, copy, modify, distribute,
# and license this software and its documentation for any purpose, provided
# that existing copyright notices are retained in all copies and that this
# notice is included verbatim in any distributions. No written agreement,
# license, or royalty fee is required for any of the authorized uses.
# Modifications to this software may be copyrighted by their authors
# and need not follow the licensing terms described here, provided that
# the new terms are clearly indicated on the first page of each file where
# they apply.
# 
# IN NO EVENT SHALL THE AUTHORS OR DISTRIBUTORS BE LIABLE TO ANY PARTY
# FOR DIRECT, INDIRECT, SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES
# ARISING OUT OF THE USE OF THIS SOFTWARE, ITS DOCUMENTATION, OR ANY
# DERIVATIVES THEREOF, EVEN IF THE AUTHORS HAVE BEEN ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
# 
# THE AUTHORS AND DISTRIBUTORS SPECIFICALLY DISCLAIM ANY WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.  THIS SOFTWARE
# IS PROVIDED ON AN "AS IS" BASIS, AND THE AUTHORS AND DISTRIBUTORS HAVE
# NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES, ENHANCEMENTS, OR
# MODIFICATIONS.

import sys
import os.path
import operator
from ctypes import c_ubyte, POINTER, cast

parent_dir = os.path.split(os.getcwd())[0]

# if we are at PyUSB source tree, add usb package to python path
if os.path.exists(os.path.join(parent_dir, 'usb')):
    sys.path.insert(0, parent_dir)

import usb.core
import logging
import devinfo
import time
import unittest
import usb._interop as _interop

logger = logging.getLogger('usb.test')

# data generation functions
def get_array_data1(length = 8):
    return _interop.as_array(range(length))

def get_array_data2(length = 8):
    data = list(range(length))
    data.reverse()
    return _interop.as_array(data)

def get_list_data1(length = 8):
    return list(range(length))

def get_list_data2(length = 8):
    data = list(range(length))
    data.reverse()
    return data

def get_str_data1(length = 8): 
    if sys.version_info[0] >= 3:
        # On Python 3, string char is 4 bytes long
        length = int(length / 4)
    return ''.join([chr(x) for x in range(length)])

def get_str_data2(length = 8):
    if sys.version_info[0] >= 3:
        length = int(length / 4)
    data = list(range(length))
    data.reverse()
    return ''.join([chr(x) for x in data])

def to_array(data):
    return _interop.as_array(data)

def delay_after_reset():
    time.sleep(3) # necessary to wait device reenumeration

# check if our test hardware is present
def find_my_device(backend = None):
    try:
        return usb.core.find(backend=backend,
                             idVendor=devinfo.ID_VENDOR,
                             idProduct=devinfo.ID_PRODUCT)
    except Exception:
        return None

def run_tests(suite):
    runner = unittest.TextTestRunner()
    runner.run(suite)

def data_len(data):
    a = _interop.as_array(data)
    return len(data) * a.itemsize

def array_equals(a1, a2):
    if a1.typecode != 'u' and a2.typecode != 'u':
        return a1 == a2
    else:
        # as python3 strings are unicode, loads of trouble,
        # because we read data from USB devices are byte arrays
        l1 = len(a1) * a1.itemsize
        l2 = len(a2) * a2.itemsize
        if l1 != l2:
            return False
        c_ubyte_p = POINTER(c_ubyte)
        p1 = cast(a1.buffer_info()[0], c_ubyte_p)
        p2 = cast(a2.buffer_info()[0], c_ubyte_p)
        # we do a item by item compare we unicode is involved
        return all(map(operator.eq, p1[:l1], p2[:l2]))

########NEW FILE########
__FILENAME__ = libusb0
# Copyright (C) 2009-2013 Wander Lairson Costa
#
# The following terms apply to all files associated
# with the software unless explicitly disclaimed in individual files.
#
# The authors hereby grant permission to use, copy, modify, distribute,
# and license this software and its documentation for any purpose, provided
# that existing copyright notices are retained in all copies and that this
# notice is included verbatim in any distributions. No written agreement,
# license, or royalty fee is required for any of the authorized uses.
# Modifications to this software may be copyrighted by their authors
# and need not follow the licensing terms described here, provided that
# the new terms are clearly indicated on the first page of each file where
# they apply.
#
# IN NO EVENT SHALL THE AUTHORS OR DISTRIBUTORS BE LIABLE TO ANY PARTY
# FOR DIRECT, INDIRECT, SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES
# ARISING OUT OF THE USE OF THIS SOFTWARE, ITS DOCUMENTATION, OR ANY
# DERIVATIVES THEREOF, EVEN IF THE AUTHORS HAVE BEEN ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# THE AUTHORS AND DISTRIBUTORS SPECIFICALLY DISCLAIM ANY WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.  THIS SOFTWARE
# IS PROVIDED ON AN "AS IS" BASIS, AND THE AUTHORS AND DISTRIBUTORS HAVE
# NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES, ENHANCEMENTS, OR
# MODIFICATIONS.

from ctypes import *
import os
import usb.backend
import usb.util
import sys
from usb.core import USBError
from usb._debug import methodtrace
import usb._interop as _interop
import logging
import usb.libloader

__author__ = 'Wander Lairson Costa'

__all__ = ['get_backend']

_logger = logging.getLogger('usb.backend.libusb0')

# usb.h

_PC_PATH_MAX = 4

if sys.platform.find('bsd') != -1 or sys.platform.find('mac') != -1 or \
        sys.platform.find('darwin') != -1:
    _PATH_MAX = 1024
elif sys.platform == 'win32' or sys.platform == 'cygwin':
    _PATH_MAX = 511
else:
    _PATH_MAX = os.pathconf('.', _PC_PATH_MAX)

# libusb-win32 makes all structures packed, while
# default libusb only does for some structures
# _PackPolicy defines the structure packing according
# to the platform.
class _PackPolicy(object):
    pass

if sys.platform == 'win32' or sys.platform == 'cygwin':
    _PackPolicy._pack_ = 1

# Data structures

class _usb_descriptor_header(Structure):
    _pack_ = 1
    _fields_ = [('blength', c_uint8),
                ('bDescriptorType', c_uint8)]

class _usb_string_descriptor(Structure):
    _pack_ = 1
    _fields_ = [('bLength', c_uint8),
                ('bDescriptorType', c_uint8),
                ('wData', c_uint16)]

class _usb_endpoint_descriptor(Structure, _PackPolicy):
    _fields_ = [('bLength', c_uint8),
                ('bDescriptorType', c_uint8),
                ('bEndpointAddress', c_uint8),
                ('bmAttributes', c_uint8),
                ('wMaxPacketSize', c_uint16),
                ('bInterval', c_uint8),
                ('bRefresh', c_uint8),
                ('bSynchAddress', c_uint8),
                ('extra', POINTER(c_uint8)),
                ('extralen', c_int)]

class _usb_interface_descriptor(Structure, _PackPolicy):
    _fields_ = [('bLength', c_uint8),
                ('bDescriptorType', c_uint8),
                ('bInterfaceNumber', c_uint8),
                ('bAlternateSetting', c_uint8),
                ('bNumEndpoints', c_uint8),
                ('bInterfaceClass', c_uint8),
                ('bInterfaceSubClass', c_uint8),
                ('bInterfaceProtocol', c_uint8),
                ('iInterface', c_uint8),
                ('endpoint', POINTER(_usb_endpoint_descriptor)),
                ('extra', POINTER(c_uint8)),
                ('extralen', c_int)]

class _usb_interface(Structure, _PackPolicy):
    _fields_ = [('altsetting', POINTER(_usb_interface_descriptor)),
                ('num_altsetting', c_int)]

class _usb_config_descriptor(Structure, _PackPolicy):
    _fields_ = [('bLength', c_uint8),
                ('bDescriptorType', c_uint8),
                ('wTotalLength', c_uint16),
                ('bNumInterfaces', c_uint8),
                ('bConfigurationValue', c_uint8),
                ('iConfiguration', c_uint8),
                ('bmAttributes', c_uint8),
                ('bMaxPower', c_uint8),
                ('interface', POINTER(_usb_interface)),
                ('extra', POINTER(c_uint8)),
                ('extralen', c_int)]

class _usb_device_descriptor(Structure, _PackPolicy):
    _pack_ = 1
    _fields_ = [('bLength', c_uint8),
                ('bDescriptorType', c_uint8),
                ('bcdUSB', c_uint16),
                ('bDeviceClass', c_uint8),
                ('bDeviceSubClass', c_uint8),
                ('bDeviceProtocol', c_uint8),
                ('bMaxPacketSize0', c_uint8),
                ('idVendor', c_uint16),
                ('idProduct', c_uint16),
                ('bcdDevice', c_uint16),
                ('iManufacturer', c_uint8),
                ('iProduct', c_uint8),
                ('iSerialNumber', c_uint8),
                ('bNumConfigurations', c_uint8)]

class _usb_device(Structure, _PackPolicy):
    pass

class _usb_bus(Structure, _PackPolicy):
    pass

_usb_device._fields_ = [('next', POINTER(_usb_device)),
                        ('prev', POINTER(_usb_device)),
                        ('filename', c_int8 * (_PATH_MAX + 1)),
                        ('bus', POINTER(_usb_bus)),
                        ('descriptor', _usb_device_descriptor),
                        ('config', POINTER(_usb_config_descriptor)),
                        ('dev', c_void_p),
                        ('devnum', c_uint8),
                        ('num_children', c_ubyte),
                        ('children', POINTER(POINTER(_usb_device)))]

_usb_bus._fields_ = [('next', POINTER(_usb_bus)),
                    ('prev', POINTER(_usb_bus)),
                    ('dirname', c_char * (_PATH_MAX + 1)),
                    ('devices', POINTER(_usb_device)),
                    ('location', c_uint32),
                    ('root_dev', POINTER(_usb_device))]

_usb_dev_handle = c_void_p

class _DeviceDescriptor:
    def __init__(self, dev):
        desc = dev.descriptor
        self.bLength = desc.bLength
        self.bDescriptorType = desc.bDescriptorType
        self.bcdUSB = desc.bcdUSB
        self.bDeviceClass = desc.bDeviceClass
        self.bDeviceSubClass = desc.bDeviceSubClass
        self.bDeviceProtocol = desc.bDeviceProtocol
        self.bMaxPacketSize0 = desc.bMaxPacketSize0
        self.idVendor = desc.idVendor
        self.idProduct = desc.idProduct
        self.bcdDevice = desc.bcdDevice
        self.iManufacturer = desc.iManufacturer
        self.iProduct = desc.iProduct
        self.iSerialNumber = desc.iSerialNumber
        self.bNumConfigurations = desc.bNumConfigurations
        self.address = dev.devnum
        self.bus = dev.bus[0].location

        self.port_number = None
_lib = None

def _load_library(find_library=None):
    return usb.libloader.load_locate_library(
                ('usb-0.1', 'usb', 'libusb0'),
                'cygusb0.dll', 'Libusb 0',
                find_library=find_library
    )

def _setup_prototypes(lib):
    # usb_dev_handle *usb_open(struct usb_device *dev);
    lib.usb_open.argtypes = [POINTER(_usb_device)]
    lib.usb_open.restype = _usb_dev_handle

    # int usb_close(usb_dev_handle *dev);
    lib.usb_close.argtypes = [_usb_dev_handle]

    # int usb_get_string(usb_dev_handle *dev,
    #                    int index,
    #                    int langid,
    #                    char *buf,
    #                    size_t buflen);
    lib.usb_get_string.argtypes = [
            _usb_dev_handle,
            c_int,
            c_int,
            c_char_p,
            c_size_t
        ]

    # int usb_get_string_simple(usb_dev_handle *dev,
    #                           int index,
    #                           char *buf,
    #                           size_t buflen);
    lib.usb_get_string_simple.argtypes = [
            _usb_dev_handle,
            c_int,
            c_char_p,
            c_size_t
        ]

    # int usb_get_descriptor_by_endpoint(usb_dev_handle *udev,
    #                                    int ep,
    #                                    unsigned char type,
    #                                    unsigned char index,
    #                                    void *buf,
    #                                    int size);
    lib.usb_get_descriptor_by_endpoint.argtypes = [
                                _usb_dev_handle,
                                c_int,
                                c_ubyte,
                                c_ubyte,
                                c_void_p,
                                c_int
                            ]

    # int usb_get_descriptor(usb_dev_handle *udev,
    #                        unsigned char type,
    #                        unsigned char index,
    #                        void *buf,
    #                        int size);
    lib.usb_get_descriptor.argtypes = [
                    _usb_dev_handle,
                    c_ubyte,
                    c_ubyte,
                    c_void_p,
                    c_int
                ]

    # int usb_bulk_write(usb_dev_handle *dev,
    #                    int ep,
    #                    const char *bytes,
    #                    int size,
    #                    int timeout);
    lib.usb_bulk_write.argtypes = [
            _usb_dev_handle,
            c_int,
            c_char_p,
            c_int,
            c_int
        ]

    # int usb_bulk_read(usb_dev_handle *dev,
    #                   int ep,
    #                   char *bytes,
    #                   int size,
    #                   int timeout);
    lib.usb_bulk_read.argtypes = [
            _usb_dev_handle,
            c_int,
            c_char_p,
            c_int,
            c_int
        ]

    # int usb_interrupt_write(usb_dev_handle *dev,
    #                         int ep,
    #                         const char *bytes,
    #                         int size,
    #                         int timeout);
    lib.usb_interrupt_write.argtypes = [
            _usb_dev_handle,
            c_int,
            c_char_p,
            c_int,
            c_int
        ]

    # int usb_interrupt_read(usb_dev_handle *dev,
    #                        int ep,
    #                        char *bytes,
    #                        int size,
    #                        int timeout);
    lib.usb_interrupt_read.argtypes = [
            _usb_dev_handle,
            c_int,
            c_char_p,
            c_int,
            c_int
        ]

    # int usb_control_msg(usb_dev_handle *dev,
    #                     int requesttype,
    #                     int request,
    #                     int value,
    #                     int index,
    #                     char *bytes,
    #                     int size,
    #                     int timeout);
    lib.usb_control_msg.argtypes = [
            _usb_dev_handle,
            c_int,
            c_int,
            c_int,
            c_int,
            c_char_p,
            c_int,
            c_int
        ]

    # int usb_set_configuration(usb_dev_handle *dev, int configuration);
    lib.usb_set_configuration.argtypes = [_usb_dev_handle, c_int]

    # int usb_claim_interface(usb_dev_handle *dev, int interface);
    lib.usb_claim_interface.argtypes = [_usb_dev_handle, c_int]

    # int usb_release_interface(usb_dev_handle *dev, int interface);
    lib.usb_release_interface.argtypes = [_usb_dev_handle, c_int]

    # int usb_set_altinterface(usb_dev_handle *dev, int alternate);
    lib.usb_set_altinterface.argtypes = [_usb_dev_handle, c_int]

    # int usb_resetep(usb_dev_handle *dev, unsigned int ep);
    lib.usb_resetep.argtypes = [_usb_dev_handle, c_int]

    # int usb_clear_halt(usb_dev_handle *dev, unsigned int ep);
    lib.usb_clear_halt.argtypes = [_usb_dev_handle, c_int]

    # int usb_reset(usb_dev_handle *dev);
    lib.usb_reset.argtypes = [_usb_dev_handle]

    # char *usb_strerror(void);
    lib.usb_strerror.argtypes = []
    lib.usb_strerror.restype = c_char_p

    # void usb_set_debug(int level);
    lib.usb_set_debug.argtypes = [c_int]

    # struct usb_device *usb_device(usb_dev_handle *dev);
    lib.usb_device.argtypes = [_usb_dev_handle]
    lib.usb_device.restype = POINTER(_usb_device)

    # struct usb_bus *usb_get_busses(void);
    lib.usb_get_busses.restype = POINTER(_usb_bus)

def _check(ret):
    if ret is None:
        errmsg = _lib.usb_strerror()
    else:
        if hasattr(ret, 'value'):
            ret = ret.value

        if ret < 0:
            errmsg = _lib.usb_strerror()
            # No error means that we need to get the error
            # message from the return code
            # Thanks to Nicholas Wheeler to point out the problem...
            # Also see issue #2860940
            if errmsg.lower() == 'no error':
                errmsg = os.strerror(-ret)
        else:
            return ret
    raise USBError(errmsg, ret)

# implementation of libusb 0.1.x backend
class _LibUSB(usb.backend.IBackend):
    @methodtrace(_logger)
    def enumerate_devices(self):
        _check(_lib.usb_find_busses())
        _check(_lib.usb_find_devices())
        bus = _lib.usb_get_busses()
        while bool(bus):
            dev = bus[0].devices
            while bool(dev):
                yield dev[0]
                dev = dev[0].next
            bus = bus[0].next

    @methodtrace(_logger)
    def get_device_descriptor(self, dev):
        return _DeviceDescriptor(dev)

    @methodtrace(_logger)
    def get_configuration_descriptor(self, dev, config):
        if config >= dev.descriptor.bNumConfigurations:
            raise IndexError('Invalid configuration index ' + str(config))
        return dev.config[config]

    @methodtrace(_logger)
    def get_interface_descriptor(self, dev, intf, alt, config):
        cfgdesc = self.get_configuration_descriptor(dev, config)
        if intf >= cfgdesc.bNumInterfaces:
            raise IndexError('Invalid interface index ' + str(interface))
        interface = cfgdesc.interface[intf]
        if alt >= interface.num_altsetting:
            raise IndexError('Invalid alternate setting index ' + str(alt))
        return interface.altsetting[alt]

    @methodtrace(_logger)
    def get_endpoint_descriptor(self, dev, ep, intf, alt, config):
        interface = self.get_interface_descriptor(dev, intf, alt, config)
        if ep >= interface.bNumEndpoints:
            raise IndexError('Invalid endpoint index ' + str(ep))
        return interface.endpoint[ep]

    @methodtrace(_logger)
    def open_device(self, dev):
        return _check(_lib.usb_open(dev))

    @methodtrace(_logger)
    def close_device(self, dev_handle):
        _check(_lib.usb_close(dev_handle))

    @methodtrace(_logger)
    def set_configuration(self, dev_handle, config_value):
        _check(_lib.usb_set_configuration(dev_handle, config_value))

    @methodtrace(_logger)
    def set_interface_altsetting(self, dev_handle, intf, altsetting):
        _check(_lib.usb_set_altinterface(dev_handle, altsetting))

    @methodtrace(_logger)
    def get_configuration(self, dev_handle):
        bmRequestType = usb.util.build_request_type(
                                usb.util.CTRL_IN,
                                usb.util.CTRL_TYPE_STANDARD,
                                usb.util.CTRL_RECIPIENT_DEVICE
                            )
        buff = usb.util.create_buffer(1)
        ret = self.ctrl_transfer(
                dev_handle,
                bmRequestType,
                0x08,
                0,
                0,
                buff,
                100)

        assert ret == 1
        return buff[0]


    @methodtrace(_logger)
    def claim_interface(self, dev_handle, intf):
        _check(_lib.usb_claim_interface(dev_handle, intf))

    @methodtrace(_logger)
    def release_interface(self, dev_handle, intf):
        _check(_lib.usb_release_interface(dev_handle, intf))

    @methodtrace(_logger)
    def bulk_write(self, dev_handle, ep, intf, data, timeout):
        return self.__write(_lib.usb_bulk_write,
                            dev_handle,
                            ep,
                            intf,
                            data, timeout)

    @methodtrace(_logger)
    def bulk_read(self, dev_handle, ep, intf, buff, timeout):
        return self.__read(_lib.usb_bulk_read,
                           dev_handle,
                           ep,
                           intf,
                           buff,
                           timeout)

    @methodtrace(_logger)
    def intr_write(self, dev_handle, ep, intf, data, timeout):
        return self.__write(_lib.usb_interrupt_write,
                            dev_handle,
                            ep,
                            intf,
                            data,
                            timeout)

    @methodtrace(_logger)
    def intr_read(self, dev_handle, ep, intf, buff, timeout):
        return self.__read(_lib.usb_interrupt_read,
                           dev_handle,
                           ep,
                           intf,
                           buff,
                           timeout)

    @methodtrace(_logger)
    def ctrl_transfer(self,
                      dev_handle,
                      bmRequestType,
                      bRequest,
                      wValue,
                      wIndex,
                      data,
                      timeout):
        address, length = data.buffer_info()
        length *= data.itemsize
        return _check(_lib.usb_control_msg(
                            dev_handle,
                            bmRequestType,
                            bRequest,
                            wValue,
                            wIndex,
                            cast(address, c_char_p),
                            length,
                            timeout
                        ))

    @methodtrace(_logger)
    def clear_halt(self, dev_handle, ep):
        _check(_lib.usb_clear_halt(dev_handle, ep))

    @methodtrace(_logger)
    def reset_device(self, dev_handle):
        _check(_lib.usb_reset(dev_handle))

    @methodtrace(_logger)
    def detach_kernel_driver(self, dev_handle, intf):
        _check(_lib.usb_detach_kernel_driver_np(dev_handle, intf))

    def __write(self, fn, dev_handle, ep, intf, data, timeout):
        address, length = data.buffer_info()
        length *= data.itemsize
        return int(_check(fn(
                        dev_handle,
                        ep,
                        cast(address, c_char_p),
                        length,
                        timeout
                    )))

    def __read(self, fn, dev_handle, ep, intf, buff, timeout):
        address, length = buff.buffer_info()
        length *= buff.itemsize
        ret = int(_check(fn(
                    dev_handle,
                    ep,
                    cast(address, c_char_p),
                    length,
                    timeout
                )))
        return ret

def get_backend(find_library=None):
    global _lib
    try:
        if _lib is None:
            _lib = _load_library(find_library)
            _setup_prototypes(_lib)
            _lib.usb_init()
        return _LibUSB()
    except usb.libloader.LibaryException:
        # exception already logged (if any)
        _logger.error('Error loading libusb 0.1 backend', exc_info=False)
        return None
    except Exception:
        _logger.error('Error loading libusb 0.1 backend', exc_info=True)
        return None

########NEW FILE########
__FILENAME__ = libusb1
# Copyright (C) 2009-2013 Wander Lairson Costa
#
# The following terms apply to all files associated
# with the software unless explicitly disclaimed in individual files.
#
# The authors hereby grant permission to use, copy, modify, distribute,
# and license this software and its documentation for any purpose, provided
# that existing copyright notices are retained in all copies and that this
# notice is included verbatim in any distributions. No written agreement,
# license, or royalty fee is required for any of the authorized uses.
# Modifications to this software may be copyrighted by their authors
# and need not follow the licensing terms described here, provided that
# the new terms are clearly indicated on the first page of each file where
# they apply.
#
# IN NO EVENT SHALL THE AUTHORS OR DISTRIBUTORS BE LIABLE TO ANY PARTY
# FOR DIRECT, INDIRECT, SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES
# ARISING OUT OF THE USE OF THIS SOFTWARE, ITS DOCUMENTATION, OR ANY
# DERIVATIVES THEREOF, EVEN IF THE AUTHORS HAVE BEEN ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# THE AUTHORS AND DISTRIBUTORS SPECIFICALLY DISCLAIM ANY WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.  THIS SOFTWARE
# IS PROVIDED ON AN "AS IS" BASIS, AND THE AUTHORS AND DISTRIBUTORS HAVE
# NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES, ENHANCEMENTS, OR
# MODIFICATIONS.

from ctypes import *
import usb.util
import sys
import logging
from usb._debug import methodtrace
import usb._interop as _interop
import errno
import math
from usb.core import USBError
import usb.libloader

__author__ = 'Wander Lairson Costa'

__all__ = [
            'get_backend',
            'LIBUSB_SUCESS',
            'LIBUSB_ERROR_IO',
            'LIBUSB_ERROR_INVALID_PARAM',
            'LIBUSB_ERROR_ACCESS',
            'LIBUSB_ERROR_NO_DEVICE',
            'LIBUSB_ERROR_NOT_FOUND',
            'LIBUSB_ERROR_BUSY',
            'LIBUSB_ERROR_TIMEOUT',
            'LIBUSB_ERROR_OVERFLOW',
            'LIBUSB_ERROR_PIPE',
            'LIBUSB_ERROR_INTERRUPTED',
            'LIBUSB_ERROR_NO_MEM',
            'LIBUSB_ERROR_NOT_SUPPORTED',
            'LIBUSB_ERROR_OTHER'
            'LIBUSB_TRANSFER_COMPLETED',
            'LIBUSB_TRANSFER_ERROR',
            'LIBUSB_TRANSFER_TIMED_OUT',
            'LIBUSB_TRANSFER_CANCELLED',
            'LIBUSB_TRANSFER_STALL',
            'LIBUSB_TRANSFER_NO_DEVICE',
            'LIBUSB_TRANSFER_OVERFLOW'
        ]

_logger = logging.getLogger('usb.backend.libusb1')

# libusb.h

# transfer_type codes
# Control endpoint
_LIBUSB_TRANSFER_TYPE_CONTROL = 0,
# Isochronous endpoint
_LIBUSB_TRANSFER_TYPE_ISOCHRONOUS = 1
# Bulk endpoint
_LIBUSB_TRANSFER_TYPE_BULK = 2
# Interrupt endpoint
_LIBUSB_TRANSFER_TYPE_INTERRUPT = 3

# return codes

LIBUSB_SUCCESS = 0
LIBUSB_ERROR_IO = -1
LIBUSB_ERROR_INVALID_PARAM = -2
LIBUSB_ERROR_ACCESS = -3
LIBUSB_ERROR_NO_DEVICE = -4
LIBUSB_ERROR_NOT_FOUND = -5
LIBUSB_ERROR_BUSY = -6
LIBUSB_ERROR_TIMEOUT = -7
LIBUSB_ERROR_OVERFLOW = -8
LIBUSB_ERROR_PIPE = -9
LIBUSB_ERROR_INTERRUPTED = -10
LIBUSB_ERROR_NO_MEM = -11
LIBUSB_ERROR_NOT_SUPPORTED = -12
LIBUSB_ERROR_OTHER = -99

# map return code to errno values
_libusb_errno = {
    0:None,
    LIBUSB_ERROR_IO:errno.__dict__.get('EIO', None),
    LIBUSB_ERROR_INVALID_PARAM:errno.__dict__.get('EINVAL', None),
    LIBUSB_ERROR_ACCESS:errno.__dict__.get('EACCES', None),
    LIBUSB_ERROR_NO_DEVICE:errno.__dict__.get('ENODEV', None),
    LIBUSB_ERROR_NOT_FOUND:errno.__dict__.get('ENOENT', None),
    LIBUSB_ERROR_BUSY:errno.__dict__.get('EBUSY', None),
    LIBUSB_ERROR_TIMEOUT:errno.__dict__.get('ETIMEDOUT', None),
    LIBUSB_ERROR_OVERFLOW:errno.__dict__.get('EOVERFLOW', None),
    LIBUSB_ERROR_PIPE:errno.__dict__.get('EPIPE', None),
    LIBUSB_ERROR_INTERRUPTED:errno.__dict__.get('EINTR', None),
    LIBUSB_ERROR_NO_MEM:errno.__dict__.get('ENOMEM', None),
    LIBUSB_ERROR_NOT_SUPPORTED:errno.__dict__.get('ENOSYS', None),
    LIBUSB_ERROR_OTHER:None
}

# Transfer status codes:
# Note that this does not indicate
# that the entire amount of requested data was transferred.
LIBUSB_TRANSFER_COMPLETED = 0
LIBUSB_TRANSFER_ERROR = 1
LIBUSB_TRANSFER_TIMED_OUT = 2
LIBUSB_TRANSFER_CANCELLED = 3
LIBUSB_TRANSFER_STALL = 4
LIBUSB_TRANSFER_NO_DEVICE = 5
LIBUSB_TRANSFER_OVERFLOW = 6

# map return codes to strings
_str_transfer_error = {
    LIBUSB_TRANSFER_COMPLETED:'Success (no error)',
    LIBUSB_TRANSFER_ERROR:'Transfer failed',
    LIBUSB_TRANSFER_TIMED_OUT:'Transfer timed out',
    LIBUSB_TRANSFER_CANCELLED:'Transfer was cancelled',
    LIBUSB_TRANSFER_STALL:'For bulk/interrupt endpoints: halt condition '\
                          'detected (endpoint stalled). For control '\
                          'endpoints: control request not supported.',
    LIBUSB_TRANSFER_NO_DEVICE:'Device was disconnected',
    LIBUSB_TRANSFER_OVERFLOW:'Device sent more data than requested'
}

# map transfer codes to errno codes
_transfer_errno = {
    LIBUSB_TRANSFER_COMPLETED:0,
    LIBUSB_TRANSFER_ERROR:errno.__dict__.get('EIO', None),
    LIBUSB_TRANSFER_TIMED_OUT:errno.__dict__.get('ETIMEDOUT', None),
    LIBUSB_TRANSFER_CANCELLED:errno.__dict__.get('EAGAIN', None),
    LIBUSB_TRANSFER_STALL:errno.__dict__.get('EIO', None),
    LIBUSB_TRANSFER_NO_DEVICE:errno.__dict__.get('ENODEV', None),
    LIBUSB_TRANSFER_OVERFLOW:errno.__dict__.get('EOVERFLOW', None)
}

# Data structures

class _libusb_endpoint_descriptor(Structure):
    _fields_ = [('bLength', c_uint8),
                ('bDescriptorType', c_uint8),
                ('bEndpointAddress', c_uint8),
                ('bmAttributes', c_uint8),
                ('wMaxPacketSize', c_uint16),
                ('bInterval', c_uint8),
                ('bRefresh', c_uint8),
                ('bSynchAddress', c_uint8),
                ('extra', POINTER(c_ubyte)),
                ('extra_length', c_int)]

class _libusb_interface_descriptor(Structure):
    _fields_ = [('bLength', c_uint8),
                ('bDescriptorType', c_uint8),
                ('bInterfaceNumber', c_uint8),
                ('bAlternateSetting', c_uint8),
                ('bNumEndpoints', c_uint8),
                ('bInterfaceClass', c_uint8),
                ('bInterfaceSubClass', c_uint8),
                ('bInterfaceProtocol', c_uint8),
                ('iInterface', c_uint8),
                ('endpoint', POINTER(_libusb_endpoint_descriptor)),
                ('extra', POINTER(c_ubyte)),
                ('extra_length', c_int)]

class _libusb_interface(Structure):
    _fields_ = [('altsetting', POINTER(_libusb_interface_descriptor)),
                ('num_altsetting', c_int)]

class _libusb_config_descriptor(Structure):
    _fields_ = [('bLength', c_uint8),
                ('bDescriptorType', c_uint8),
                ('wTotalLength', c_uint16),
                ('bNumInterfaces', c_uint8),
                ('bConfigurationValue', c_uint8),
                ('iConfiguration', c_uint8),
                ('bmAttributes', c_uint8),
                ('bMaxPower', c_uint8),
                ('interface', POINTER(_libusb_interface)),
                ('extra', POINTER(c_ubyte)),
                ('extra_length', c_int)]

class _libusb_device_descriptor(Structure):
    _fields_ = [('bLength', c_uint8),
                ('bDescriptorType', c_uint8),
                ('bcdUSB', c_uint16),
                ('bDeviceClass', c_uint8),
                ('bDeviceSubClass', c_uint8),
                ('bDeviceProtocol', c_uint8),
                ('bMaxPacketSize0', c_uint8),
                ('idVendor', c_uint16),
                ('idProduct', c_uint16),
                ('bcdDevice', c_uint16),
                ('iManufacturer', c_uint8),
                ('iProduct', c_uint8),
                ('iSerialNumber', c_uint8),
                ('bNumConfigurations', c_uint8)]


# Isochronous packet descriptor.
class _libusb_iso_packet_descriptor(Structure):
    _fields_ = [('length', c_uint),
                ('actual_length', c_uint),
                ('status', c_int)] # enum libusb_transfer_status

_libusb_device_handle = c_void_p

class _libusb_transfer(Structure):
    pass
_libusb_transfer_p = POINTER(_libusb_transfer)

_libusb_transfer_cb_fn_p = CFUNCTYPE(None, _libusb_transfer_p)

_libusb_transfer._fields_ = [('dev_handle', _libusb_device_handle),
                             ('flags', c_uint8),
                             ('endpoint', c_uint8),
                             ('type', c_uint8),
                             ('timeout', c_uint),
                             ('status', c_int), # enum libusb_transfer_status
                             ('length', c_int),
                             ('actual_length', c_int),
                             ('callback', _libusb_transfer_cb_fn_p),
                             ('user_data', py_object),
                             ('buffer', c_void_p),
                             ('num_iso_packets', c_int),
                             ('iso_packet_desc', _libusb_iso_packet_descriptor)
]

def _get_iso_packet_list(transfer):
    list_type = _libusb_iso_packet_descriptor * transfer.num_iso_packets
    return list_type.from_address(addressof(transfer.iso_packet_desc))

_lib = None

def _load_library(find_library=None):
    # Windows backend uses stdcall calling convention
    #
    # On FreeBSD 8/9, libusb 1.0 and libusb 0.1 are in the same shared
    # object libusb.so, so if we found libusb library name, we must assure
    # it is 1.0 version. We just try to get some symbol from 1.0 version
    return usb.libloader.load_locate_library(
                ('usb-1.0', 'libusb-1.0', 'usb'),
                'cygusb-1.0.dll', 'Libusb 1',
                win_cls=(WinDLL if sys.platform == 'win32' else None),
                find_library=find_library, check_symbols=('libusb_init',)
    )

def _setup_prototypes(lib):
    # void libusb_set_debug (libusb_context *ctx, int level)
    lib.libusb_set_debug.argtypes = [c_void_p, c_int]

    # int libusb_init (libusb_context **context)
    lib.libusb_init.argtypes = [POINTER(c_void_p)]

    # void libusb_exit (struct libusb_context *ctx)
    lib.libusb_exit.argtypes = [c_void_p]

    # ssize_t libusb_get_device_list (libusb_context *ctx,
    #                                 libusb_device ***list)
    lib.libusb_get_device_list.argtypes = [
            c_void_p,
            POINTER(POINTER(c_void_p))
        ]

    # void libusb_free_device_list (libusb_device **list,
    #                               int unref_devices)
    lib.libusb_free_device_list.argtypes = [
            POINTER(c_void_p),
            c_int
        ]

    # libusb_device *libusb_ref_device (libusb_device *dev)
    lib.libusb_ref_device.argtypes = [c_void_p]
    lib.libusb_ref_device.restype = c_void_p

    # void libusb_unref_device(libusb_device *dev)
    lib.libusb_unref_device.argtypes = [c_void_p]

    # int libusb_open(libusb_device *dev, libusb_device_handle **handle)
    lib.libusb_open.argtypes = [c_void_p, POINTER(_libusb_device_handle)]

    # void libusb_close(libusb_device_handle *dev_handle)
    lib.libusb_close.argtypes = [_libusb_device_handle]

    # int libusb_set_configuration(libusb_device_handle *dev,
    #                              int configuration)
    lib.libusb_set_configuration.argtypes = [_libusb_device_handle, c_int]

    # int libusb_get_configuration(libusb_device_handle *dev,
    #                              int *config)
    lib.libusb_get_configuration.argtypes = [_libusb_device_handle, POINTER(c_int)]

    # int libusb_claim_interface(libusb_device_handle *dev,
    #                               int interface_number)
    lib.libusb_claim_interface.argtypes = [_libusb_device_handle, c_int]

    # int libusb_release_interface(libusb_device_handle *dev,
    #                              int interface_number)
    lib.libusb_release_interface.argtypes = [_libusb_device_handle, c_int]

    # int libusb_set_interface_alt_setting(libusb_device_handle *dev,
    #                                      int interface_number,
    #                                      int alternate_setting)
    lib.libusb_set_interface_alt_setting.argtypes = [
            _libusb_device_handle,
            c_int,
            c_int
        ]

    # int libusb_reset_device (libusb_device_handle *dev)
    lib.libusb_reset_device.argtypes = [_libusb_device_handle]

    # int libusb_kernel_driver_active(libusb_device_handle *dev,
    #                                 int interface)
    lib.libusb_kernel_driver_active.argtypes = [
            _libusb_device_handle,
            c_int
        ]

    # int libusb_detach_kernel_driver(libusb_device_handle *dev,
    #                                 int interface)
    lib.libusb_detach_kernel_driver.argtypes = [
            _libusb_device_handle,
            c_int
        ]

    # int libusb_attach_kernel_driver(libusb_device_handle *dev,
    #                                 int interface)
    lib.libusb_attach_kernel_driver.argtypes = [
            _libusb_device_handle,
            c_int
        ]

    # int libusb_get_device_descriptor(
    #                   libusb_device *dev,
    #                   struct libusb_device_descriptor *desc
    #               )
    lib.libusb_get_device_descriptor.argtypes = [
            c_void_p,
            POINTER(_libusb_device_descriptor)
        ]

    # int libusb_get_config_descriptor(
    #           libusb_device *dev,
    #           uint8_t config_index,
    #           struct libusb_config_descriptor **config
    #       )
    lib.libusb_get_config_descriptor.argtypes = [
            c_void_p,
            c_uint8,
            POINTER(POINTER(_libusb_config_descriptor))
        ]

    # void  libusb_free_config_descriptor(
    #           struct libusb_config_descriptor *config
    #   )
    lib.libusb_free_config_descriptor.argtypes = [
            POINTER(_libusb_config_descriptor)
        ]

    # int libusb_get_string_descriptor_ascii(libusb_device_handle *dev,
    #                                         uint8_t desc_index,
    #                                         unsigned char *data,
    #                                         int length)
    lib.libusb_get_string_descriptor_ascii.argtypes = [
            _libusb_device_handle,
            c_uint8,
            POINTER(c_ubyte),
            c_int
        ]

    # int libusb_control_transfer(libusb_device_handle *dev_handle,
    #                             uint8_t bmRequestType,
    #                             uint8_t bRequest,
    #                             uint16_t wValue,
    #                             uint16_t wIndex,
    #                             unsigned char *data,
    #                             uint16_t wLength,
    #                             unsigned int timeout)
    lib.libusb_control_transfer.argtypes = [
            _libusb_device_handle,
            c_uint8,
            c_uint8,
            c_uint16,
            c_uint16,
            POINTER(c_ubyte),
            c_uint16,
            c_uint
        ]

    #int libusb_bulk_transfer(
    #           struct libusb_device_handle *dev_handle,
    #           unsigned char endpoint,
    #           unsigned char *data,
    #           int length,
    #           int *transferred,
    #           unsigned int timeout
    #       )
    lib.libusb_bulk_transfer.argtypes = [
                _libusb_device_handle,
                c_ubyte,
                POINTER(c_ubyte),
                c_int,
                POINTER(c_int),
                c_uint
            ]

    # int libusb_interrupt_transfer(
    #               libusb_device_handle *dev_handle,
    #               unsigned char endpoint,
    #               unsigned char *data,
    #               int length,
    #               int *actual_length,
    #               unsigned int timeout
    #           );
    lib.libusb_interrupt_transfer.argtypes = [
                    _libusb_device_handle,
                    c_ubyte,
                    POINTER(c_ubyte),
                    c_int,
                    POINTER(c_int),
                    c_uint
                ]

    # libusb_transfer* libusb_alloc_transfer(int iso_packets);
    lib.libusb_alloc_transfer.argtypes = [c_int]
    lib.libusb_alloc_transfer.restype = POINTER(_libusb_transfer)

    # void libusb_free_transfer(struct libusb_transfer *transfer)
    lib.libusb_free_transfer.argtypes = [POINTER(_libusb_transfer)]

    # int libusb_submit_transfer(struct libusb_transfer *transfer);
    lib.libusb_submit_transfer.argtypes = [POINTER(_libusb_transfer)]

    # const char *libusb_strerror(enum libusb_error errcode)
    lib.libusb_strerror.argtypes = [c_uint]
    lib.libusb_strerror.restype = c_char_p

    # int libusb_clear_halt(libusb_device_handle *dev, unsigned char endpoint)
    lib.libusb_clear_halt.argtypes = [_libusb_device_handle, c_ubyte]

    # void libusb_set_iso_packet_lengths(
    #               libusb_transfer* transfer,
    #               unsigned int length
    #           );
    def libusb_set_iso_packet_lengths(transfer_p, length):
        r"""This function is inline in the libusb.h file, so we must implement
            it.

        lib.libusb_set_iso_packet_lengths.argtypes = [
                        POINTER(_libusb_transfer),
                        c_int
                    ]
        """
        transfer = transfer_p.contents
        for iso_packet_desc in _get_iso_packet_list(transfer):
            iso_packet_desc.length = length
    lib.libusb_set_iso_packet_lengths = libusb_set_iso_packet_lengths

    #int libusb_get_max_iso_packet_size(libusb_device* dev,
    #                                   unsigned char endpoint);
    lib.libusb_get_max_iso_packet_size.argtypes = [c_void_p,
                                                   c_ubyte]

    # void libusb_fill_iso_transfer(
    #               struct libusb_transfer* transfer,
    #               libusb_device_handle*  dev_handle,
    #               unsigned char endpoint,
    #               unsigned char* buffer,
    #               int length,
    #               int num_iso_packets,
    #               libusb_transfer_cb_fn   callback,
    #               void * user_data,
    #               unsigned int timeout
    #           );
    def libusb_fill_iso_transfer(_libusb_transfer_p, dev_handle, endpoint, buffer, length,
                                 num_iso_packets, callback, user_data, timeout):
        r"""This function is inline in the libusb.h file, so we must implement
            it.

        lib.libusb_fill_iso_transfer.argtypes = [
                       _libusb_transfer,
                       _libusb_device_handle,
                       c_ubyte,
                       POINTER(c_ubyte),
                       c_int,
                       c_int,
                       _libusb_transfer_cb_fn_p,
                       c_void_p,
                       c_uint
                   ]
        """
        transfer = _libusb_transfer_p.contents
        transfer.dev_handle = dev_handle
        transfer.endpoint = endpoint
        transfer.type = _LIBUSB_TRANSFER_TYPE_ISOCHRONOUS
        transfer.timeout = timeout
        transfer.buffer = cast(buffer, c_void_p)
        transfer.length = length
        transfer.num_iso_packets = num_iso_packets
        transfer.user_data = user_data
        transfer.callback = callback
    lib.libusb_fill_iso_transfer = libusb_fill_iso_transfer

    # uint8_t libusb_get_bus_number(libusb_device *dev)
    lib.libusb_get_bus_number.argtypes = [c_void_p]
    lib.libusb_get_bus_number.restype = c_uint8

    # uint8_t libusb_get_device_address(libusb_device *dev)
    lib.libusb_get_device_address.argtypes = [c_void_p]
    lib.libusb_get_device_address.restype = c_uint8

    try:
        # uint8_t libusb_get_port_number(libusb_device *dev)
        lib.libusb_get_port_number.argtypes = [c_void_p]
        lib.libusb_get_port_number.restype = c_uint8
    except AttributeError:
        pass

    #int libusb_handle_events(libusb_context *ctx);
    lib.libusb_handle_events.argtypes = [c_void_p]

def _strerror(errcode):
    return _lib.libusb_strerror(errcode).decode('utf8')

# check a libusb function call
def _check(ret):
    if hasattr(ret, 'value'):
        ret = ret.value

    if ret < 0:
        if ret == LIBUSB_ERROR_NOT_SUPPORTED:
            raise NotImplementedError(_strerror(ret))
        else:
            raise USBError(_strerror(ret), ret, _libusb_errno[ret])

    return ret

# wrap a device
class _Device(object):
    def __init__(self, devid):
        self.devid = _lib.libusb_ref_device(devid)
    def __del__(self):
        _lib.libusb_unref_device(self.devid)

# wrap a descriptor and keep a reference to another object
# Thanks to Thomas Reitmayr.
class _WrapDescriptor(object):
    def __init__(self, desc, obj = None):
        self.obj = obj
        self.desc = desc
    def __getattr__(self, name):
        return getattr(self.desc, name)

# wrap a configuration descriptor
class _ConfigDescriptor(object):
    def __init__(self, desc):
        self.desc = desc
    def __del__(self):
        _lib.libusb_free_config_descriptor(self.desc)
    def __getattr__(self, name):
        return getattr(self.desc.contents, name)


# iterator for libusb devices
class _DevIterator(object):
    def __init__(self, ctx):
        self.dev_list = POINTER(c_void_p)()
        self.num_devs = _check(_lib.libusb_get_device_list(
                                    ctx,
                                    byref(self.dev_list))
                                )
    def __iter__(self):
        for i in range(self.num_devs):
            yield _Device(self.dev_list[i])
    def __del__(self):
        _lib.libusb_free_device_list(self.dev_list, 1)

class _DeviceHandle(object):
    def __init__(self, dev):
        self.handle = _libusb_device_handle()
        self.devid = dev.devid
        _check(_lib.libusb_open(self.devid, byref(self.handle)))

class _IsoTransferHandler(object):
    def __init__(self, dev_handle, ep, buff, timeout):
        address, length = buff.buffer_info()

        packet_length = _lib.libusb_get_max_iso_packet_size(dev_handle.devid, ep)
        packet_count = int(math.ceil(float(length) / packet_length))

        self.transfer = _lib.libusb_alloc_transfer(packet_count)

        _lib.libusb_fill_iso_transfer(self.transfer,
                                      dev_handle.handle,
                                      ep,
                                      cast(address, POINTER(c_ubyte)),
                                      length,
                                      packet_count,
                                      _libusb_transfer_cb_fn_p(self.__callback),
                                      None,
                                      timeout)

        self.__set_packets_length(length, packet_length)

    def __del__(self):
        _lib.libusb_free_transfer(self.transfer)

    def submit(self, ctx = None):
        self.__callback_done = 0
        _check(_lib.libusb_submit_transfer(self.transfer))

        while not self.__callback_done:
            _check(_lib.libusb_handle_events(ctx))

        return self.__compute_size_transf_data()

    def __compute_size_transf_data(self):
        return sum([t.actual_length for t in
                    _get_iso_packet_list(self.transfer.contents)])

    def __set_packets_length(self, n, packet_length):
        _lib.libusb_set_iso_packet_lengths(self.transfer, packet_length)
        r = n % packet_length
        if r:
            iso_packets = _get_iso_packet_list(self.transfer.contents)
            iso_packets[-1].length = r

    def __callback(self, transfer):
        if transfer.contents.status == LIBUSB_TRANSFER_COMPLETED:
            self.__callback_done = 1
        else:
            status = int(transfer.contents.status)
            raise usb.USBError(_str_transfer_error[status],
                               status,
                               _transfer_errno[status])

# implementation of libusb 1.0 backend
class _LibUSB(usb.backend.IBackend):
    @methodtrace(_logger)
    def __init__(self, lib):
        usb.backend.IBackend.__init__(self)
        self.lib = lib
        self.ctx = c_void_p()
        _check(self.lib.libusb_init(byref(self.ctx)))

    @methodtrace(_logger)
    def __del__(self):
        self.lib.libusb_exit(self.ctx)


    @methodtrace(_logger)
    def enumerate_devices(self):
        return _DevIterator(self.ctx)

    @methodtrace(_logger)
    def get_device_descriptor(self, dev):
        dev_desc = _libusb_device_descriptor()
        _check(self.lib.libusb_get_device_descriptor(dev.devid, byref(dev_desc)))
        dev_desc.bus = self.lib.libusb_get_bus_number(dev.devid)
        dev_desc.address = self.lib.libusb_get_device_address(dev.devid)

	#Only available i newer versions of libusb
        try:
            dev_desc.port_number = self.lib.libusb_get_port_number(dev.devid)
        except AttributeError:
            dev_desc.port_number = None

        return dev_desc

    @methodtrace(_logger)
    def get_configuration_descriptor(self, dev, config):
        cfg = POINTER(_libusb_config_descriptor)()
        _check(self.lib.libusb_get_config_descriptor(
                dev.devid,
                config, byref(cfg)))
        return _ConfigDescriptor(cfg)

    @methodtrace(_logger)
    def get_interface_descriptor(self, dev, intf, alt, config):
        cfg = self.get_configuration_descriptor(dev, config)
        if intf >= cfg.bNumInterfaces:
            raise IndexError('Invalid interface index ' + str(intf))
        i = cfg.interface[intf]
        if alt >= i.num_altsetting:
            raise IndexError('Invalid alternate setting index ' + str(alt))
        return _WrapDescriptor(i.altsetting[alt], cfg)

    @methodtrace(_logger)
    def get_endpoint_descriptor(self, dev, ep, intf, alt, config):
        i = self.get_interface_descriptor(dev, intf, alt, config)
        if ep > i.bNumEndpoints:
            raise IndexError('Invalid endpoint index ' + str(ep))
        return _WrapDescriptor(i.endpoint[ep], i)

    @methodtrace(_logger)
    def open_device(self, dev):
        return _DeviceHandle(dev)

    @methodtrace(_logger)
    def close_device(self, dev_handle):
        self.lib.libusb_close(dev_handle.handle)

    @methodtrace(_logger)
    def set_configuration(self, dev_handle, config_value):
        _check(self.lib.libusb_set_configuration(dev_handle.handle, config_value))

    @methodtrace(_logger)
    def get_configuration(self, dev_handle):
        config = c_int()
        _check(self.lib.libusb_get_configuration(dev_handle.handle, byref(config)))
        return config.value

    @methodtrace(_logger)
    def set_interface_altsetting(self, dev_handle, intf, altsetting):
        _check(self.lib.libusb_set_interface_alt_setting(
                                dev_handle.handle,
                                intf,
                                altsetting))

    @methodtrace(_logger)
    def claim_interface(self, dev_handle, intf):
        _check(self.lib.libusb_claim_interface(dev_handle.handle, intf))

    @methodtrace(_logger)
    def release_interface(self, dev_handle, intf):
        _check(self.lib.libusb_release_interface(dev_handle.handle, intf))

    @methodtrace(_logger)
    def bulk_write(self, dev_handle, ep, intf, data, timeout):
        return self.__write(self.lib.libusb_bulk_transfer,
                            dev_handle,
                            ep,
                            intf,
                            data,
                            timeout)

    @methodtrace(_logger)
    def bulk_read(self, dev_handle, ep, intf, buff, timeout):
        return self.__read(self.lib.libusb_bulk_transfer,
                           dev_handle,
                           ep,
                           intf,
                           buff,
                           timeout)

    @methodtrace(_logger)
    def intr_write(self, dev_handle, ep, intf, data, timeout):
        return self.__write(self.lib.libusb_interrupt_transfer,
                            dev_handle,
                            ep,
                            intf,
                            data,
                            timeout)

    @methodtrace(_logger)
    def intr_read(self, dev_handle, ep, intf, buff, timeout):
        return self.__read(self.lib.libusb_interrupt_transfer,
                           dev_handle,
                           ep,
                           intf,
                           buff,
                           timeout)

    @methodtrace(_logger)
    def iso_write(self, dev_handle, ep, intf, data, timeout):
        handler = _IsoTransferHandler(dev_handle, ep, data, timeout)
        return handler.submit(self.ctx)

    @methodtrace(_logger)
    def iso_read(self, dev_handle, ep, intf, buff, timeout):
        handler = _IsoTransferHandler(dev_handle, ep, buff, timeout)
        return handler.submit(self.ctx)

    @methodtrace(_logger)
    def ctrl_transfer(self,
                      dev_handle,
                      bmRequestType,
                      bRequest,
                      wValue,
                      wIndex,
                      data,
                      timeout):
        addr, length = data.buffer_info()
        length *= data.itemsize

        ret = _check(self.lib.libusb_control_transfer(
                                        dev_handle.handle,
                                        bmRequestType,
                                        bRequest,
                                        wValue,
                                        wIndex,
                                        cast(addr, POINTER(c_ubyte)),
                                        length,
                                        timeout))

        return ret

    @methodtrace(_logger)
    def clear_halt(self, dev_handle, ep):
        _check(self.lib.libusb_clear_halt(dev_handle.handle, ep))

    @methodtrace(_logger)
    def reset_device(self, dev_handle):
        _check(self.lib.libusb_reset_device(dev_handle.handle))

    @methodtrace(_logger)
    def is_kernel_driver_active(self, dev_handle, intf):
        return bool(_check(self.lib.libusb_kernel_driver_active(dev_handle.handle,
                        intf)))

    @methodtrace(_logger)
    def detach_kernel_driver(self, dev_handle, intf):
        _check(self.lib.libusb_detach_kernel_driver(dev_handle.handle, intf))

    @methodtrace(_logger)
    def attach_kernel_driver(self, dev_handle, intf):
        _check(self.lib.libusb_attach_kernel_driver(dev_handle.handle, intf))

    def __write(self, fn, dev_handle, ep, intf, data, timeout):
        address, length = data.buffer_info()
        length *= data.itemsize
        transferred = c_int()
        retval = fn(dev_handle.handle,
                  ep,
                  cast(address, POINTER(c_ubyte)),
                  length,
                  byref(transferred),
                  timeout)
        # do not assume LIBUSB_ERROR_TIMEOUT means no I/O.
        if not (transferred.value and retval == LIBUSB_ERROR_TIMEOUT):
            _check(retval)

        return transferred.value

    def __read(self, fn, dev_handle, ep, intf, buff, timeout):
        address, length = buff.buffer_info()
        length *= buff.itemsize
        transferred = c_int()
        retval = fn(dev_handle.handle,
                  ep,
                  cast(address, POINTER(c_ubyte)),
                  length,
                  byref(transferred),
                  timeout)
        # do not assume LIBUSB_ERROR_TIMEOUT means no I/O.
        if not (transferred.value and retval == LIBUSB_ERROR_TIMEOUT):
            _check(retval)
        return transferred.value

def get_backend(find_library=None):
    global _lib
    try:
        if _lib is None:
            _lib = _load_library(find_library=find_library)
            _setup_prototypes(_lib)
        return _LibUSB(_lib)
    except usb.libloader.LibaryException:
        # exception already logged (if any)
        _logger.error('Error loading libusb 1.0 backend', exc_info=False)
        return None
    except Exception:
        _logger.error('Error loading libusb 1.0 backend', exc_info=True)
        return None

########NEW FILE########
__FILENAME__ = openusb
# Copyright (C) 2009-2013 Wander Lairson Costa
#
# The following terms apply to all files associated
# with the software unless explicitly disclaimed in individual files.
#
# The authors hereby grant permission to use, copy, modify, distribute,
# and license this software and its documentation for any purpose, provided
# that existing copyright notices are retained in all copies and that this
# notice is included verbatim in any distributions. No written agreement,
# license, or royalty fee is required for any of the authorized uses.
# Modifications to this software may be copyrighted by their authors
# and need not follow the licensing terms described here, provided that
# the new terms are clearly indicated on the first page of each file where
# they apply.
#
# IN NO EVENT SHALL THE AUTHORS OR DISTRIBUTORS BE LIABLE TO ANY PARTY
# FOR DIRECT, INDIRECT, SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES
# ARISING OUT OF THE USE OF THIS SOFTWARE, ITS DOCUMENTATION, OR ANY
# DERIVATIVES THEREOF, EVEN IF THE AUTHORS HAVE BEEN ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# THE AUTHORS AND DISTRIBUTORS SPECIFICALLY DISCLAIM ANY WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.  THIS SOFTWARE
# IS PROVIDED ON AN "AS IS" BASIS, AND THE AUTHORS AND DISTRIBUTORS HAVE
# NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES, ENHANCEMENTS, OR
# MODIFICATIONS.

from ctypes import *
import ctypes.util
import usb.util
from usb._debug import methodtrace
import logging
import errno
import sys
import usb._interop as _interop
import usb.util as util
import usb.libloader
from usb.core import USBError

__author__ = 'Wander Lairson Costa'

__all__ = [
            'get_backend'
            'OPENUSB_SUCCESS'
            'OPENUSB_PLATFORM_FAILURE'
            'OPENUSB_NO_RESOURCES'
            'OPENUSB_NO_BANDWIDTH'
            'OPENUSB_NOT_SUPPORTED'
            'OPENUSB_HC_HARDWARE_ERROR'
            'OPENUSB_INVALID_PERM'
            'OPENUSB_BUSY'
            'OPENUSB_BADARG'
            'OPENUSB_NOACCESS'
            'OPENUSB_PARSE_ERROR'
            'OPENUSB_UNKNOWN_DEVICE'
            'OPENUSB_INVALID_HANDLE'
            'OPENUSB_SYS_FUNC_FAILURE'
            'OPENUSB_NULL_LIST'
            'OPENUSB_CB_CONTINUE'
            'OPENUSB_CB_TERMINATE'
            'OPENUSB_IO_STALL'
            'OPENUSB_IO_CRC_ERROR'
            'OPENUSB_IO_DEVICE_HUNG'
            'OPENUSB_IO_REQ_TOO_BIG'
            'OPENUSB_IO_BIT_STUFFING'
            'OPENUSB_IO_UNEXPECTED_PID'
            'OPENUSB_IO_DATA_OVERRUN'
            'OPENUSB_IO_DATA_UNDERRUN'
            'OPENUSB_IO_BUFFER_OVERRUN'
            'OPENUSB_IO_BUFFER_UNDERRUN'
            'OPENUSB_IO_PID_CHECK_FAILURE'
            'OPENUSB_IO_DATA_TOGGLE_MISMATCH'
            'OPENUSB_IO_TIMEOUT'
            'OPENUSB_IO_CANCELED'
        ]

_logger = logging.getLogger('usb.backend.openusb')

OPENUSB_SUCCESS = 0
OPENUSB_PLATFORM_FAILURE = -1
OPENUSB_NO_RESOURCES = -2
OPENUSB_NO_BANDWIDTH = -3
OPENUSB_NOT_SUPPORTED = -4
OPENUSB_HC_HARDWARE_ERROR = -5
OPENUSB_INVALID_PERM = -6
OPENUSB_BUSY = -7
OPENUSB_BADARG = -8
OPENUSB_NOACCESS = -9
OPENUSB_PARSE_ERROR = -10
OPENUSB_UNKNOWN_DEVICE = -11
OPENUSB_INVALID_HANDLE = -12
OPENUSB_SYS_FUNC_FAILURE = -13
OPENUSB_NULL_LIST = -14
OPENUSB_CB_CONTINUE = -20
OPENUSB_CB_TERMINATE = -21
OPENUSB_IO_STALL = -50
OPENUSB_IO_CRC_ERROR = -51
OPENUSB_IO_DEVICE_HUNG = -52
OPENUSB_IO_REQ_TOO_BIG = -53
OPENUSB_IO_BIT_STUFFING = -54
OPENUSB_IO_UNEXPECTED_PID = -55
OPENUSB_IO_DATA_OVERRUN = -56
OPENUSB_IO_DATA_UNDERRUN = -57
OPENUSB_IO_BUFFER_OVERRUN = -58
OPENUSB_IO_BUFFER_UNDERRUN = -59
OPENUSB_IO_PID_CHECK_FAILURE = -60
OPENUSB_IO_DATA_TOGGLE_MISMATCH = -61
OPENUSB_IO_TIMEOUT = -62
OPENUSB_IO_CANCELED = -63

_openusb_errno = {
    OPENUSB_SUCCESS:None,
    OPENUSB_PLATFORM_FAILURE:None,
    OPENUSB_NO_RESOURCES:errno.__dict__.get('ENOMEM', None),
    OPENUSB_NO_BANDWIDTH:None,
    OPENUSB_NOT_SUPPORTED:errno.__dict__.get('ENOSYS', None),
    OPENUSB_HC_HARDWARE_ERROR:errno.__dict__.get('EIO', None),
    OPENUSB_INVALID_PERM:errno.__dict__.get('EBADF', None),
    OPENUSB_BUSY:errno.__dict__.get('EBUSY', None),
    OPENUSB_BADARG:errno.__dict__.get('EINVAL', None),
    OPENUSB_NOACCESS:errno.__dict__.get('EACCES', None),
    OPENUSB_PARSE_ERROR:None,
    OPENUSB_UNKNOWN_DEVICE:errno.__dict__.get('ENODEV', None),
    OPENUSB_INVALID_HANDLE:errno.__dict__.get('EINVAL', None),
    OPENUSB_SYS_FUNC_FAILURE:None,
    OPENUSB_NULL_LIST:None,
    OPENUSB_CB_CONTINUE:None,
    OPENUSB_CB_TERMINATE:None,
    OPENUSB_IO_STALL:errno.__dict__.get('EIO', None),
    OPENUSB_IO_CRC_ERROR:errno.__dict__.get('EIO', None),
    OPENUSB_IO_DEVICE_HUNG:errno.__dict__.get('EIO', None),
    OPENUSB_IO_REQ_TOO_BIG:errno.__dict__.get('E2BIG', None),
    OPENUSB_IO_BIT_STUFFING:None,
    OPENUSB_IO_UNEXPECTED_PID:errno.__dict__.get('ESRCH', None),
    OPENUSB_IO_DATA_OVERRUN:errno.__dict__.get('EOVERFLOW', None),
    OPENUSB_IO_DATA_UNDERRUN:None,
    OPENUSB_IO_BUFFER_OVERRUN:errno.__dict__.get('EOVERFLOW', None),
    OPENUSB_IO_BUFFER_UNDERRUN:None,
    OPENUSB_IO_PID_CHECK_FAILURE:None,
    OPENUSB_IO_DATA_TOGGLE_MISMATCH:None,
    OPENUSB_IO_TIMEOUT:errno.__dict__.get('ETIMEDOUT', None),
    OPENUSB_IO_CANCELED:errno.__dict__.get('EINTR', None)
}

class _usb_endpoint_desc(Structure):
    _fields_ = [('bLength', c_uint8),
                ('bDescriptorType', c_uint8),
                ('bEndpointAddress', c_uint8),
                ('bmAttributes', c_uint8),
                ('wMaxPacketSize', c_uint16),
                ('bInterval', c_uint8),
                ('bRefresh', c_uint8),
                ('bSynchAddress', c_uint8)]

class _usb_interface_desc(Structure):
    _fields_ = [('bLength', c_uint8),
                ('bDescriptorType', c_uint8),
                ('bInterfaceNumber', c_uint8),
                ('bAlternateSetting', c_uint8),
                ('bNumEndpoints', c_uint8),
                ('bInterfaceClass', c_uint8),
                ('bInterfaceSubClass', c_uint8),
                ('bInterfaceProtocol', c_uint8),
                ('iInterface', c_uint8)]

class _usb_config_desc(Structure):
    _fields_ = [('bLength', c_uint8),
                ('bDescriptorType', c_uint8),
                ('wTotalLength', c_uint16),
                ('bNumInterfaces', c_uint8),
                ('bConfigurationValue', c_uint8),
                ('iConfiguration', c_uint8),
                ('bmAttributes', c_uint8),
                ('bMaxPower', c_uint8)]

class _usb_device_desc(Structure):
    _fields_ = [('bLength', c_uint8),
                ('bDescriptorType', c_uint8),
                ('bcdUSB', c_uint16),
                ('bDeviceClass', c_uint8),
                ('bDeviceSubClass', c_uint8),
                ('bDeviceProtocol', c_uint8),
                ('bMaxPacketSize0', c_uint8),
                ('idVendor', c_uint16),
                ('idProduct', c_uint16),
                ('bcdDevice', c_uint16),
                ('iManufacturer', c_uint8),
                ('iProduct', c_uint8),
                ('iSerialNumber', c_uint8),
                ('bNumConfigurations', c_uint8)]

class _openusb_request_result(Structure):
    _fields_ = [('status', c_int32),
                ('transferred_bytes', c_uint32)]

class _openusb_ctrl_request(Structure):
    def __init__(self):
        super(_openusb_ctrl_request, self).__init__()
        self.setup.bmRequestType = 0
        self.setup.bRequest = 0
        self.setup.wValue = 0
        self.setup.wIndex = 0
        self.payload = None
        self.length = 0
        self.timeout = 0
        self.flags = 0
        self.result.status = 0
        self.result.transferred_bytes = 0
        self.next = None

    class _openusb_ctrl_setup(Structure):
        _fields_ = [('bmRequestType', c_uint8),
                    ('bRequest', c_uint8),
                    ('wValue', c_uint16),
                    ('wIndex', c_uint16)]
    _fields_ = [('setup', _openusb_ctrl_setup),
                ('payload', POINTER(c_uint8)),
                ('length', c_uint32),
                ('timeout', c_uint32),
                ('flags', c_uint32),
                ('result', _openusb_request_result),
                ('next', c_void_p)]

class _openusb_intr_request(Structure):
    _fields_ = [('interval', c_uint16),
                ('payload', POINTER(c_uint8)),
                ('length', c_uint32),
                ('timeout', c_uint32),
                ('flags', c_uint32),
                ('result', _openusb_request_result),
                ('next', c_void_p)]

class _openusb_bulk_request(Structure):
    _fields_ = [('payload', POINTER(c_uint8)),
                ('length', c_uint32),
                ('timeout', c_uint32),
                ('flags', c_uint32),
                ('result', _openusb_request_result),
                ('next', c_void_p)]

class _openusb_isoc_pkts(Structure):
    class _openusb_isoc_packet(Structure):
        _fields_ = [('payload', POINTER(c_uint8)),
                    ('length', c_uint32)]
    _fields_ = [('num_packets', c_uint32),
                ('packets', POINTER(_openusb_isoc_packet))]

class _openusb_isoc_request(Structure):
    _fields_ = [('start_frame', c_uint32),
                ('flags', c_uint32),
                ('pkts', _openusb_isoc_pkts),
                ('isoc_results', POINTER(_openusb_request_result)),
                ('isoc_status', c_int32),
                ('next', c_void_p)]

_openusb_devid = c_uint64
_openusb_busid = c_uint64
_openusb_handle = c_uint64
_openusb_dev_handle = c_uint64

_lib = None
_ctx = None

def _load_library(find_library=None):
    # FIXME: cygwin name is "openusb"?
    #        (that's what the original _load_library() function
    #         would have searched for)
    return usb.libloader.load_locate_library(
        ('openusb',), 'openusb', "OpenUSB library", find_library=find_library
    )

def _setup_prototypes(lib):
    # int32_t openusb_init(uint32_t flags , openusb_handle_t *handle);
    lib.openusb_init.argtypes = [c_uint32, POINTER(_openusb_handle)]
    lib.openusb_init.restype = c_int32

    # void openusb_fini(openusb_handle_t handle );
    lib.openusb_fini.argtypes = [_openusb_handle]

    # uint32_t openusb_get_busid_list(openusb_handle_t handle,
    #                                 openusb_busid_t **busids,
    #                                 uint32_t *num_busids);
    lib.openusb_get_busid_list.argtypes = [
            _openusb_handle,
            POINTER(POINTER(_openusb_busid)),
            POINTER(c_uint32)
        ]

    # void openusb_free_busid_list(openusb_busid_t * busids);
    lib.openusb_free_busid_list.argtypes = [POINTER(_openusb_busid)]

    # uint32_t openusb_get_devids_by_bus(openusb_handle_t handle,
    #                                    openusb_busid_t busid,
    #                                    openusb_devid_t **devids,
    #                                    uint32_t *num_devids);
    lib.openusb_get_devids_by_bus.argtypes = [
                _openusb_handle,
                _openusb_busid,
                POINTER(POINTER(_openusb_devid)),
                POINTER(c_uint32)
            ]

    lib.openusb_get_devids_by_bus.restype = c_int32

    # void openusb_free_devid_list(openusb_devid_t * devids);
    lib.openusb_free_devid_list.argtypes = [POINTER(_openusb_devid)]

    # int32_t openusb_open_device(openusb_handle_t handle,
    #                             openusb_devid_t devid ,
    #                             uint32_t flags,
    #                             openusb_dev_handle_t *dev);
    lib.openusb_open_device.argtypes = [
                _openusb_handle,
                _openusb_devid,
                c_uint32,
                POINTER(_openusb_dev_handle)
            ]

    lib.openusb_open_device.restype = c_int32

    # int32_t openusb_close_device(openusb_dev_handle_t dev);
    lib.openusb_close_device.argtypes = [_openusb_dev_handle]
    lib.openusb_close_device.restype = c_int32

    # int32_t openusb_set_configuration(openusb_dev_handle_t dev,
    #                                   uint8_t cfg);
    lib.openusb_set_configuration.argtypes = [_openusb_dev_handle, c_uint8]
    lib.openusb_set_configuration.restype = c_int32

    # int32_t openusb_get_configuration(openusb_dev_handle_t dev,
    #                                   uint8_t *cfg);
    lib.openusb_get_configuration.argtypes = [_openusb_dev_handle, POINTER(c_uint8)]
    lib.openusb_get_configuration.restype = c_int32

    # int32_t openusb_claim_interface(openusb_dev_handle_t dev,
    #                                 uint8_t ifc,
    #                                 openusb_init_flag_t flags);
    lib.openusb_claim_interface.argtypes = [
            _openusb_dev_handle,
            c_uint8,
            c_int
        ]

    lib.openusb_claim_interface.restype = c_int32

    # int32_t openusb_release_interface(openusb_dev_handle_t dev,
    #                                   uint8_t ifc);
    lib.openusb_release_interface.argtypes = [
            _openusb_dev_handle,
            c_uint8
        ]

    lib.openusb_release_interface.restype = c_int32

    # int32_topenusb_set_altsetting(openusb_dev_handle_t dev,
    #                               uint8_t ifc,
    #                               uint8_t alt);
    lib.openusb_set_altsetting.argtypes = [
            _openusb_dev_handle,
            c_uint8,
            c_uint8
        ]
    lib.openusb_set_altsetting.restype = c_int32

    # int32_t openusb_reset(openusb_dev_handle_t dev);
    lib.openusb_reset.argtypes = [_openusb_dev_handle]
    lib.openusb_reset.restype = c_int32

    # int32_t openusb_parse_device_desc(openusb_handle_t handle,
    #                                   openusb_devid_t devid,
    #                                   uint8_t *buffer,
    #                                   uint16_t buflen,
    #                                   usb_device_desc_t *devdesc);
    lib.openusb_parse_device_desc.argtypes = [
            _openusb_handle,
            _openusb_devid,
            POINTER(c_uint8),
            c_uint16,
            POINTER(_usb_device_desc)
        ]

    lib.openusb_parse_device_desc.restype = c_int32

    # int32_t openusb_parse_config_desc(openusb_handle_t handle,
    #                                   openusb_devid_t devid,
    #                                   uint8_t *buffer,
    #                                   uint16_t buflen,
    #                                   uint8_t cfgidx,
    #                                   usb_config_desc_t *cfgdesc);
    lib.openusb_parse_config_desc.argtypes = [
                _openusb_handle,
                _openusb_devid,
                POINTER(c_uint8),
                c_uint16,
                c_uint8,
                POINTER(_usb_config_desc)
            ]
    lib.openusb_parse_config_desc.restype = c_int32

    # int32_t openusb_parse_interface_desc(openusb_handle_t handle,
    #                                      openusb_devid_t devid,
    #                                      uint8_t *buffer,
    #                                      uint16_t buflen,
    #                                      uint8_t cfgidx,
    #                                      uint8_t ifcidx,
    #                                      uint8_t alt,
    #                                      usb_interface_desc_t *ifcdesc);
    lib.openusb_parse_interface_desc.argtypes = [
                    _openusb_handle,
                    _openusb_devid,
                    POINTER(c_uint8),
                    c_uint16,
                    c_uint8,
                    c_uint8,
                    c_uint8,
                    POINTER(_usb_interface_desc)
                ]

    lib.openusb_parse_interface_desc.restype = c_int32

    # int32_t openusb_parse_endpoint_desc(openusb_handle_t handle,
    #                                     openusb_devid_t devid,
    #                                     uint8_t *buffer,
    #                                     uint16_t buflen,
    #                                     uint8_t cfgidx,
    #                                     uint8_t ifcidx,
    #                                     uint8_t alt,
    #                                     uint8_t eptidx,
    #                                     usb_endpoint_desc_t *eptdesc);
    lib.openusb_parse_endpoint_desc.argtypes = [
                    _openusb_handle,
                    _openusb_devid,
                    POINTER(c_uint8),
                    c_uint16,
                    c_uint8,
                    c_uint8,
                    c_uint8,
                    c_uint8,
                    POINTER(_usb_endpoint_desc)
                ]

    lib.openusb_parse_interface_desc.restype = c_int32

    # const char *openusb_strerror(int32_t error );
    lib.openusb_strerror.argtypes = [c_int32]
    lib.openusb_strerror.restype = c_char_p

    # int32_t openusb_ctrl_xfer(openusb_dev_handle_t dev,
    #                           uint8_t ifc,
    #                           uint8_t ept,
    #                           openusb_ctrl_request_t *ctrl);
    lib.openusb_ctrl_xfer.argtypes = [
            _openusb_dev_handle,
            c_uint8,
            c_uint8,
            POINTER(_openusb_ctrl_request)
        ]

    lib.openusb_ctrl_xfer.restype = c_int32

    # int32_t openusb_intr_xfer(openusb_dev_handle_t dev,
    #                           uint8_t ifc,
    #                           uint8_t ept,
    #                           openusb_intr_request_t *intr);
    lib.openusb_intr_xfer.argtypes = [
                _openusb_dev_handle,
                c_uint8,
                c_uint8,
                POINTER(_openusb_intr_request)
            ]

    lib.openusb_bulk_xfer.restype = c_int32

    # int32_t openusb_bulk_xfer(openusb_dev_handle_t dev,
    #                           uint8_t ifc,
    #                           uint8_t ept,
    #                           openusb_bulk_request_t *bulk);
    lib.openusb_bulk_xfer.argtypes = [
            _openusb_dev_handle,
            c_uint8,
            c_uint8,
            POINTER(_openusb_bulk_request)
        ]

    lib.openusb_bulk_xfer.restype = c_int32

    # int32_t openusb_isoc_xfer(openusb_dev_handle_t dev,
    #                           uint8_t ifc,
    #                           uint8_t ept,
    #                           openusb_isoc_request_t *isoc);
    lib.openusb_isoc_xfer.argtypes = [
            _openusb_dev_handle,
            c_uint8,
            c_uint8,
            POINTER(_openusb_isoc_request)
        ]

    lib.openusb_isoc_xfer.restype = c_int32

def _check(ret):
    if hasattr(ret, 'value'):
        ret = ret.value

    if ret != 0:
        raise USBError(_lib.openusb_strerror(ret), ret, _openusb_errno[ret])
    return ret

class _Context(object):
    def __init__(self):
        self.handle = _openusb_handle()
        _check(_lib.openusb_init(0, byref(self.handle)))
    def __del__(self):
        _lib.openusb_fini(self.handle)

class _BusIterator(object):
    def __init__(self):
        self.buslist = POINTER(_openusb_busid)()
        num_busids = c_uint32()
        _check(_lib.openusb_get_busid_list(_ctx.handle,
                                           byref(self.buslist),
                                           byref(num_busids)))
        self.num_busids = num_busids.value
    def __iter__(self):
        for i in range(self.num_busids):
            yield self.buslist[i]
    def __del__(self):
        _lib.openusb_free_busid_list(self.buslist)

class _DevIterator(object):
    def __init__(self, busid):
        self.devlist = POINTER(_openusb_devid)()
        num_devids = c_uint32()
        _check(_lib.openusb_get_devids_by_bus(_ctx.handle,
                                              busid,
                                              byref(self.devlist),
                                              byref(num_devids)))
        self.num_devids = num_devids.value
    def __iter__(self):
        for i in range(self.num_devids):
            yield self.devlist[i]
    def __del__(self):
        _lib.openusb_free_devid_list(self.devlist)

class _OpenUSB(usb.backend.IBackend):
    @methodtrace(_logger)
    def enumerate_devices(self):
        for bus in _BusIterator():
            for devid in _DevIterator(bus):
                yield devid

    @methodtrace(_logger)
    def get_device_descriptor(self, dev):
        desc = _usb_device_desc()
        _check(_lib.openusb_parse_device_desc(_ctx.handle,
                                              dev,
                                              None,
                                              0,
                                              byref(desc)))
        desc.bus = None
        desc.address = None
        desc.port_number = None
        return desc

    @methodtrace(_logger)
    def get_configuration_descriptor(self, dev, config):
        desc = _usb_config_desc()
        _check(_lib.openusb_parse_config_desc(_ctx.handle,
                                              dev,
                                              None,
                                              0,
                                              config,
                                              byref(desc)))
        return desc

    @methodtrace(_logger)
    def get_interface_descriptor(self, dev, intf, alt, config):
        desc = _usb_interface_desc()
        _check(_lib.openusb_parse_interface_desc(_ctx.handle,
                                                 dev,
                                                 None,
                                                 0,
                                                 config,
                                                 intf,
                                                 alt,
                                                 byref(desc)))
        return desc

    @methodtrace(_logger)
    def get_endpoint_descriptor(self, dev, ep, intf, alt, config):
        desc = _usb_endpoint_desc()
        _check(_lib.openusb_parse_endpoint_desc(_ctx.handle,
                                                dev,
                                                None,
                                                0,
                                                config,
                                                intf,
                                                alt,
                                                ep,
                                                byref(desc)))
        return desc

    @methodtrace(_logger)
    def open_device(self, dev):
        handle = _openusb_dev_handle()
        _check(_lib.openusb_open_device(_ctx.handle, dev, 0, byref(handle)))
        return handle

    @methodtrace(_logger)
    def close_device(self, dev_handle):
        _lib.openusb_close_device(dev_handle)

    @methodtrace(_logger)
    def set_configuration(self, dev_handle, config_value):
        _check(_lib.openusb_set_configuration(dev_handle, config_value))

    @methodtrace(_logger)
    def get_configuration(self, dev_handle):
        config = c_uint8()
        _check(_lib.openusb_get_configuration(dev_handle, byref(config)))
        return config.value

    @methodtrace(_logger)
    def set_interface_altsetting(self, dev_handle, intf, altsetting):
        _check(_lib.openusb_set_altsetting(dev_handle, intf, altsetting))

    @methodtrace(_logger)
    def claim_interface(self, dev_handle, intf):
        _check(_lib.openusb_claim_interface(dev_handle, intf, 0))

    @methodtrace(_logger)
    def release_interface(self, dev_handle, intf):
        _lib.openusb_release_interface(dev_handle, intf)

    @methodtrace(_logger)
    def bulk_write(self, dev_handle, ep, intf, data, timeout):
        request = _openusb_bulk_request()
        memset(byref(request), 0, sizeof(request))
        payload, request.length = data.buffer_info()
        request.payload = cast(payload, POINTER(c_uint8))
        request.timeout = timeout
        _check(_lib.openusb_bulk_xfer(dev_handle, intf, ep, byref(request)))
        return request.result.transferred_bytes

    @methodtrace(_logger)
    def bulk_read(self, dev_handle, ep, intf, buff, timeout):
        request = _openusb_bulk_request()
        memset(byref(request), 0, sizeof(request))
        payload, request.length = buff.buffer_info()
        request.payload = cast(payload, POINTER(c_uint8))
        request.timeout = timeout
        _check(_lib.openusb_bulk_xfer(dev_handle, intf, ep, byref(request)))
        return request.result.transferred_bytes

    @methodtrace(_logger)
    def intr_write(self, dev_handle, ep, intf, data, timeout):
        request = _openusb_intr_request()
        memset(byref(request), 0, sizeof(request))
        payload, request.length = data.buffer_info()
        request.payload = cast(payload, POINTER(c_uint8))
        request.timeout = timeout
        _check(_lib.openusb_intr_xfer(dev_handle, intf, ep, byref(request)))
        return request.result.transferred_bytes

    @methodtrace(_logger)
    def intr_read(self, dev_handle, ep, intf, buff, timeout):
        request = _openusb_intr_request()
        memset(byref(request), 0, sizeof(request))
        payload, request.length = buff.buffer_info()
        request.payload = cast(payload, POINTER(c_uint8))
        request.timeout = timeout
        _check(_lib.openusb_intr_xfer(dev_handle, intf, ep, byref(request)))
        return request.result.transferred_bytes

# TODO: implement isochronous
#    @methodtrace(_logger)
#    def iso_write(self, dev_handle, ep, intf, data, timeout):
#       pass

#    @methodtrace(_logger)
#    def iso_read(self, dev_handle, ep, intf, size, timeout):
#        pass

    @methodtrace(_logger)
    def ctrl_transfer(self,
                      dev_handle,
                      bmRequestType,
                      bRequest,
                      wValue,
                      wIndex,
                      data,
                      timeout):
        request = _openusb_ctrl_request()
        request.setup.bmRequestType = bmRequestType
        request.setup.bRequest = bRequest
        request.setup.wValue
        request.setup.wIndex
        request.timeout = timeout

        direction = usb.util.ctrl_direction(bmRequestType)

        payload, request.length = data.buffer_info()
        request.length *= data.itemsize
        request.payload = cast(payload, POINTER(c_uint8))

        _check(_lib.openusb_ctrl_xfer(dev_handle, 0, 0, byref(request)))

        return request.result.transferred_bytes

    @methodtrace(_logger)
    def reset_device(self, dev_handle):
        _check(_lib.openusb_reset(dev_handle))

    @methodtrace(_logger)
    def clear_halt(self, dev_handle, ep):
        bmRequestType = util.build_request_type(
                            util.CTRL_OUT,
                            util.CTRL_TYPE_STANDARD,
                            util.CTRL_RECIPIENT_ENDPOINT)
        self.ctrl_transfer(
            dev_handle,
            bmRequestType,
            0x03,
            0,
            ep,
            _interop.as_array(),
            1000)

def get_backend(find_library=None):
    try:
        global _lib, _ctx
        if _lib is None:
            _lib = _load_library(find_library)
            _setup_prototypes(_lib)
            _ctx = _Context()
        return _OpenUSB()
    except usb.libloader.LibaryException:
        # exception already logged (if any)
        _logger.error('Error loading OpenUSB backend', exc_info=False)
        return None
    except Exception:
        _logger.error('Error loading OpenUSB backend', exc_info=True)
        return None

########NEW FILE########
__FILENAME__ = control
# Copyright (C) 2009-2013 Wander Lairson Costa
#
# The following terms apply to all files associated
# with the software unless explicitly disclaimed in individual files.
#
# The authors hereby grant permission to use, copy, modify, distribute,
# and license this software and its documentation for any purpose, provided
# that existing copyright notices are retained in all copies and that this
# notice is included verbatim in any distributions. No written agreement,
# license, or royalty fee is required for any of the authorized uses.
# Modifications to this software may be copyrighted by their authors
# and need not follow the licensing terms described here, provided that
# the new terms are clearly indicated on the first page of each file where
# they apply.
#
# IN NO EVENT SHALL THE AUTHORS OR DISTRIBUTORS BE LIABLE TO ANY PARTY
# FOR DIRECT, INDIRECT, SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES
# ARISING OUT OF THE USE OF THIS SOFTWARE, ITS DOCUMENTATION, OR ANY
# DERIVATIVES THEREOF, EVEN IF THE AUTHORS HAVE BEEN ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# THE AUTHORS AND DISTRIBUTORS SPECIFICALLY DISCLAIM ANY WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.  THIS SOFTWARE
# IS PROVIDED ON AN "AS IS" BASIS, AND THE AUTHORS AND DISTRIBUTORS HAVE
# NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES, ENHANCEMENTS, OR
# MODIFICATIONS.

r"""usb.control - USB standard control requests

This module exports:

get_status - get recipeint status
clear_feature - clear a recipient feature
set_feature - set a recipient feature
get_descriptor - get a device descriptor
set_descriptor - set a device descriptor
get_configuration - get a device configuration
set_configuration - set a device configuration
get_interface - get a device interface
set_interface - set a device interface
"""

__author__ = 'Wander Lairson Costa'

__all__ = ['get_status',
           'clear_feature',
           'set_feature',
           'get_descriptor',
           'set_descriptor',
           'get_configuration',
           'set_configuration',
           'get_interface',
           'set_interface',
           'ENDPOINT_HALT',
           'FUNCTION_SUSPEND',
           'DEVICE_REMOTE_WAKEUP',
           'U1_ENABLE',
           'U2_ENABLE',
           'LTM_ENABLE']

import usb.util as util
import usb.core as core

def _parse_recipient(recipient, direction):
    if recipient is None:
        r = util.CTRL_RECIPIENT_DEVICE
        wIndex = 0
    elif isinstance(recipient, core.Interface):
        r = util.CTRL_RECIPIENT_INTERFACE
        wIndex = recipient.bInterfaceNumber
    elif isinstance(recipient, core.Endpoint):
        r = util.CTRL_RECIPIENT_ENDPOINT
        wIndex = recipient.bEndpointAddress
    else:
        raise ValueError('Invalid recipient.')
    bmRequestType = util.build_request_type(
                            direction,
                            util.CTRL_TYPE_STANDARD,
                            r
                        )
    return (bmRequestType, wIndex)

# standard feature selectors from USB 2.0/3.0
ENDPOINT_HALT = 0
FUNCTION_SUSPEND = 0
DEVICE_REMOTE_WAKEUP = 1
U1_ENABLE = 48
U2_ENABLE = 49
LTM_ENABLE = 50

def get_status(dev, recipient = None):
    r"""Return the status for the specified recipient.

    dev is the Device object to which the request will be
    sent to.

    The recipient can be None (on which the status will be queried
    on the device), an Interface or Endpoint descriptors.

    The status value is returned as an integer with the lower
    word being the two bytes status value.
    """
    bmRequestType, wIndex = _parse_recipient(recipient, util.CTRL_IN)
    ret = dev.ctrl_transfer(bmRequestType = bmRequestType,
                            bRequest = 0x00,
                            wIndex = wIndex,
                            data_or_wLength = 2)
    return ret[0] | (ret[1] << 8)

def clear_feature(dev, feature, recipient = None):
    r"""Clear/disable a specific feature.

    dev is the Device object to which the request will be
    sent to.

    feature is the feature you want to disable.

    The recipient can be None (on which the status will be queried
    on the device), an Interface or Endpoint descriptors.
    """
    if feature == ENDPOINT_HALT:
        dev.clear_halt(recipient)
    else:
        bmRequestType, wIndex = _parse_recipient(recipient, util.CTRL_OUT)
        dev.ctrl_transfer(bmRequestType = bmRequestType,
                          bRequest = 0x01,
                          wIndex = wIndex,
                          wValue = feature)

def set_feature(dev, feature, recipient = None):
    r"""Set/enable a specific feature.

    dev is the Device object to which the request will be
    sent to.

    feature is the feature you want to enable.

    The recipient can be None (on which the status will be queried
    on the device), an Interface or Endpoint descriptors.
    """
    bmRequestType, wIndex = _parse_recipient(recipient, util.CTRL_OUT)
    dev.ctrl_transfer(bmRequestType = bmRequestType,
                      bRequest = 0x03,
                      wIndex = wIndex,
                      wValue = feature)

def get_descriptor(dev, desc_size, desc_type, desc_index, wIndex = 0):
    r"""Return the specified descriptor.

    dev is the Device object to which the request will be
    sent to.

    desc_size is the descriptor size.

    desc_type and desc_index are the descriptor type and index,
    respectively. wIndex index is used for string descriptors
    and represents the Language ID. For other types of descriptors,
    it is zero.
    """
    wValue = desc_index | (desc_type << 8)
    bmRequestType = util.build_request_type(
                        util.CTRL_IN,
                        util.CTRL_TYPE_STANDARD,
                        util.CTRL_RECIPIENT_DEVICE
                    )
    return dev.ctrl_transfer(
            bmRequestType = bmRequestType,
            bRequest = 0x06,
            wValue = wValue,
            wIndex = wIndex,
            data_or_wLength = desc_size
        )

def set_descriptor(dev, desc, desc_type, desc_index, wIndex = None):
    r"""Update an existing descriptor or add a new one.

    dev is the Device object to which the request will be
    sent to.

    The desc parameter is the descriptor to be sent to the device.
    desc_type and desc_index are the descriptor type and index,
    respectively. wIndex index is used for string descriptors
    and represents the Language ID. For other types of descriptors,
    it is zero.
    """
    wValue = desc_index | (desc_type << 8)
    bmRequestType = util.build_request_type(
                        util.CTRL_OUT,
                        util.CTRL_TYPE_STANDARD,
                        util.CTRL_RECIPIENT_DEVICE
                    )
    dev.ctrl_transfer(
        bmRequestType = bmRequestType,
        bRequest = 0x07,
        wValue = wValue,
        wIndex = wIndex,
        data_or_wLength = desc
    )

def get_configuration(dev):
    r"""Get the current active configuration of the device.

    dev is the Device object to which the request will be
    sent to.

    This function differs from the Device.get_active_configuration
    method because the later may use cached data, while this
    function always does a device request.
    """
    bmRequestType = util.build_request_type(
                            util.CTRL_IN,
                            util.CTRL_TYPE_STANDARD,
                            util.CTRL_RECIPIENT_DEVICE
                        )
    return dev.ctrl_transfer(
                bmRequestType,
                bRequest = 0x08,
                data_or_wLength = 1
            )[0]

def set_configuration(dev, bConfigurationNumber):
    r"""Set the current device configuration.

    dev is the Device object to which the request will be
    sent to.
    """
    dev.set_configuration(bConfigurationNumber)

def get_interface(dev, bInterfaceNumber):
    r"""Get the current alternate setting of the interface.

    dev is the Device object to which the request will be
    sent to.
    """
    bmRequestType = util.build_request_type(
                            util.CTRL_IN,
                            util.CTRL_TYPE_STANDARD,
                            util.CTRL_RECIPIENT_INTERFACE
                        )
    return dev.ctrl_transfer(
                bmRequestType = bmRequestType,
                bRequest = 0x0a,
                wIndex = bInterfaceNumber,
                data_or_wLength = 1
            )[0]

def set_interface(dev, bInterfaceNumber, bAlternateSetting):
    r"""Set the alternate setting of the interface.

    dev is the Device object to which the request will be
    sent to.
    """
    dev.set_interface_altsetting(bInterfaceNumber, bAlternateSetting)


########NEW FILE########
__FILENAME__ = core
# Copyright (C) 2009-2013 Wander Lairson Costa
#
# The following terms apply to all files associated
# with the software unless explicitly disclaimed in individual files.
#
# The authors hereby grant permission to use, copy, modify, distribute,
# and license this software and its documentation for any purpose, provided
# that existing copyright notices are retained in all copies and that this
# notice is included verbatim in any distributions. No written agreement,
# license, or royalty fee is required for any of the authorized uses.
# Modifications to this software may be copyrighted by their authors
# and need not follow the licensing terms described here, provided that
# the new terms are clearly indicated on the first page of each file where
# they apply.
#
# IN NO EVENT SHALL THE AUTHORS OR DISTRIBUTORS BE LIABLE TO ANY PARTY
# FOR DIRECT, INDIRECT, SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES
# ARISING OUT OF THE USE OF THIS SOFTWARE, ITS DOCUMENTATION, OR ANY
# DERIVATIVES THEREOF, EVEN IF THE AUTHORS HAVE BEEN ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# THE AUTHORS AND DISTRIBUTORS SPECIFICALLY DISCLAIM ANY WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.  THIS SOFTWARE
# IS PROVIDED ON AN "AS IS" BASIS, AND THE AUTHORS AND DISTRIBUTORS HAVE
# NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES, ENHANCEMENTS, OR
# MODIFICATIONS.

r"""usb.core - Core USB features.

This module exports:

Device - a class representing a USB device.
Configuration - a class representing a configuration descriptor.
Interface - a class representing an interface descriptor.
Endpoint - a class representing an endpoint descriptor.
find() - a function to find USB devices.
"""

__author__ = 'Wander Lairson Costa'

__all__ = ['Device', 'Configuration', 'Interface', 'Endpoint', 'find']

import usb.util as util
import copy
import operator
import usb._interop as _interop
import logging
import array

_logger = logging.getLogger('usb.core')

_DEFAULT_TIMEOUT = 1000

def _set_attr(input, output, fields):
    for f in fields:
       setattr(output, f, getattr(input, f))

class _ResourceManager(object):
    def __init__(self, dev, backend):
        self.backend = backend
        self._active_cfg_index = None
        self.dev = dev
        self.handle = None
        self._claimed_intf = _interop._set()
        self._ep_info = {}

    def managed_open(self):
        if self.handle is None:
            self.handle = self.backend.open_device(self.dev)
        return self.handle

    def managed_close(self):
        if self.handle is not None:
            self.backend.close_device(self.handle)
            self.handle = None

    def managed_set_configuration(self, device, config):
        if config is None:
            cfg = device[0]
        elif isinstance(config, Configuration):
            cfg = config
        elif config == 0: # unconfigured state
            class MockConfiguration(object):
                def __init__(self):
                    self.index = None
                    self.bConfigurationValue = 0
            cfg = MockConfiguration()
        else:
            cfg = util.find_descriptor(device, bConfigurationValue=config)

        self.managed_open()
        self.backend.set_configuration(self.handle, cfg.bConfigurationValue)

        # cache the index instead of the object to avoid cyclic references
        # of the device and Configuration (Device tracks the _ResourceManager,
        # which tracks the Configuration, which tracks the Device)
        self._active_cfg_index = cfg.index

        self._ep_info.clear()

    def managed_claim_interface(self, device, intf):
        self.managed_open()

        if isinstance(intf, Interface):
            i = intf.bInterfaceNumber
        else:
            i = intf

        if i not in self._claimed_intf:
            self.backend.claim_interface(self.handle, i)
            self._claimed_intf.add(i)

    def managed_release_interface(self, device, intf):
        if intf is None:
            cfg = self.get_active_configuration(device)
            i = cfg[(0,0)].bInterfaceNumber
        elif isinstance(intf, Interface):
            i = intf.bInterfaceNumber
        else:
            i = intf

        if i in self._claimed_intf:
            self.backend.release_interface(self.handle, i)
            self._claimed_intf.remove(i)

    def managed_set_interface(self, device, intf, alt):
        if isinstance(intf, Interface):
            i = intf
        else:
            cfg = self.get_active_configuration(device)
            if intf is None:
                intf = cfg[(0,0)].bInterfaceNumber
            if alt is not None:
                i = util.find_descriptor(cfg, bInterfaceNumber=intf, bAlternateSetting=alt)
            else:
                i = util.find_descriptor(cfg, bInterfaceNumber=intf)

        self.managed_claim_interface(device, i)

        if alt is None:
            alt = i.bAlternateSetting

        self.backend.set_interface_altsetting(self.handle, i.bInterfaceNumber, alt)

    def setup_request(self, device, endpoint):
        # we need the endpoint address, but the "endpoint" parameter
        # can be either the a Endpoint object or the endpoint address itself
        if isinstance(endpoint, Endpoint):
            endpoint_address = endpoint.bEndpointAddress
        else:
            endpoint_address = endpoint

        intf, ep = self.get_interface_and_endpoint(device, endpoint_address)
        self.managed_claim_interface(device, intf)
        return (intf, ep)

    # Find the interface and endpoint objects which endpoint address belongs to
    def get_interface_and_endpoint(self, device, endpoint_address):
        try:
            return self._ep_info[endpoint_address]
        except KeyError:
            for intf in self.get_active_configuration(device):
                ep = util.find_descriptor(intf, bEndpointAddress=endpoint_address)
                if ep is not None:
                    self._ep_info[endpoint_address] = (intf, ep)
                    return intf, ep

            raise ValueError('Invalid endpoint address ' + hex(endpoint_address))

    def get_active_configuration(self, device):
        if self._active_cfg_index is None:
            self.managed_open()
            cfg = util.find_descriptor(
                    device,
                    bConfigurationValue=self.backend.get_configuration(self.handle)
                )
            if cfg is None:
                raise USBError('Configuration not set')
            self._active_cfg_index = cfg.index
            return cfg
        return device[self._active_cfg_index]

    def release_all_interfaces(self, device):
        claimed = copy.copy(self._claimed_intf)
        for i in claimed:
            self.managed_release_interface(device, i)

    def dispose(self, device, close_handle = True):
        self.release_all_interfaces(device)
        if close_handle:
            self.managed_close()
        self._ep_info.clear()
        self._active_cfg_index = None

class USBError(IOError):
    r"""Exception class for USB errors.

    Backends must raise this exception when USB related errors occur.
    The backend specific error code is available through the
    'backend_error_code' member variable.
    """

    def __init__(self, strerror, error_code = None, errno = None):
        r"""Initialize the object.

        This initializes the USBError object. The strerror and errno are passed
        to the parent object. The error_code parameter is attributed to the
        backend_error_code member variable.
        """
        IOError.__init__(self, errno, strerror)
        self.backend_error_code = error_code

class Endpoint(object):
    r"""Represent an endpoint object.

    This class contains all fields of the Endpoint Descriptor
    according to the USB Specification. You may access them as class
    properties.  For example, to access the field bEndpointAddress
    of the endpoint descriptor:

    >>> import usb.core
    >>> dev = usb.core.find()
    >>> for cfg in dev:
    >>>     for i in cfg:
    >>>         for e in i:
    >>>             print e.bEndpointAddress
    """

    def __init__(self, device, endpoint, interface = 0,
                    alternate_setting = 0, configuration = 0):
        r"""Initialize the Endpoint object.

        The device parameter is the device object returned by the find()
        function. endpoint is the endpoint logical index (not the endpoint address).
        The configuration parameter is the logical index of the
        configuration (not the bConfigurationValue field). The interface
        parameter is the interface logical index (not the bInterfaceNumber field)
        and alternate_setting is the alternate setting logical index (not the
        bAlternateSetting value).  Not every interface has more than one alternate
        setting.  In this case, the alternate_setting parameter should be zero.
        By "logical index" we mean the relative order of the configurations returned by the
        peripheral as a result of GET_DESCRIPTOR request.
        """
        self.device = device
        self.index = endpoint

        backend = device._ctx.backend

        desc = backend.get_endpoint_descriptor(
                    device._ctx.dev,
                    endpoint,
                    interface,
                    alternate_setting,
                    configuration
                )

        _set_attr(
                desc,
                self,
                (
                    'bLength',
                    'bDescriptorType',
                    'bEndpointAddress',
                    'bmAttributes',
                    'wMaxPacketSize',
                    'bInterval',
                    'bRefresh',
                    'bSynchAddress'
                )
            )

    def write(self, data, timeout = None):
        r"""Write data to the endpoint.

        The parameter data contains the data to be sent to the endpoint and
        timeout is the time limit of the operation. The transfer type and
        endpoint address are automatically inferred.

        The method returns the number of bytes written.

        For details, see the Device.write() method.
        """
        return self.device.write(self, data, timeout)

    def read(self, size_or_buffer, timeout = None):
        r"""Read data from the endpoint.

        The parameter size_or_buffer is either the number of bytes to
        read or an array object where the data will be put in and timeout is the
        time limit of the operation. The transfer type and endpoint address
        are automatically inferred.

        The method returns either an array object or the number of bytes
        actually read.

        For details, see the Device.read() method.
        """
        return self.device.read(self, size_or_buffer, timeout)

    def clear_halt(self):
        r"""Clear the halt/status condition."""
        self.device.clear_halt(self.bEndpointAddress)

class Interface(object):
    r"""Represent an interface object.

    This class contains all fields of the Interface Descriptor
    according to the USB Specification. You may access them as class
    properties.  For example, to access the field bInterfaceNumber
    of the interface descriptor:

    >>> import usb.core
    >>> dev = usb.core.find()
    >>> for cfg in dev:
    >>>     for i in cfg:
    >>>         print i.bInterfaceNumber
    """

    def __init__(self, device, interface = 0,
            alternate_setting = 0, configuration = 0):
        r"""Initialize the interface object.

        The device parameter is the device object returned by the find()
        function. The configuration parameter is the logical index of the
        configuration (not the bConfigurationValue field). The interface
        parameter is the interface logical index (not the bInterfaceNumber field)
        and alternate_setting is the alternate setting logical index (not the
        bAlternateSetting value).  Not every interface has more than one alternate
        setting.  In this case, the alternate_setting parameter should be zero.
        By "logical index" we mean the relative order of the configurations returned by the
        peripheral as a result of GET_DESCRIPTOR request.
        """
        self.device = device
        self.alternate_index = alternate_setting
        self.index = interface
        self.configuration = configuration

        backend = device._ctx.backend

        desc = backend.get_interface_descriptor(
                    self.device._ctx.dev,
                    interface,
                    alternate_setting,
                    configuration
                )

        _set_attr(
                desc,
                self,
                (
                    'bLength',
                    'bDescriptorType',
                    'bInterfaceNumber',
                    'bAlternateSetting',
                    'bNumEndpoints',
                    'bInterfaceClass',
                    'bInterfaceSubClass',
                    'bInterfaceProtocol',
                    'iInterface',
                )
            )

    def set_altsetting(self):
        r"""Set the interface alternate setting."""
        self.device.set_interface_altsetting(
            self.bInterfaceNumber,
            self.bAlternateSetting
        )

    def __iter__(self):
        r"""Iterate over all endpoints of the interface."""
        for i in range(self.bNumEndpoints):
            yield Endpoint(
                    self.device,
                    i,
                    self.index,
                    self.alternate_index,
                    self.configuration
                )
    def __getitem__(self, index):
        r"""Return the Endpoint object in the given position."""
        return Endpoint(
                self.device,
                index,
                self.index,
                self.alternate_index,
                self.configuration
            )

class Configuration(object):
    r"""Represent a configuration object.

    This class contains all fields of the Configuration Descriptor
    according to the USB Specification. You may access them as class
    properties.  For example, to access the field bConfigurationValue
    of the configuration descriptor:

    >>> import usb.core
    >>> dev = usb.core.find()
    >>> for cfg in dev:
    >>>     print cfg.bConfigurationValue
    """

    def __init__(self, device, configuration = 0):
        r"""Initialize the configuration object.

        The device parameter is the device object returned by the find()
        function. The configuration parameter is the logical index of the
        configuration (not the bConfigurationValue field). By "logical index"
        we mean the relative order of the configurations returned by the
        peripheral as a result of GET_DESCRIPTOR request.
        """
        self.device = device
        self.index = configuration

        backend = device._ctx.backend

        desc = backend.get_configuration_descriptor(
                self.device._ctx.dev,
                configuration
            )

        _set_attr(
                desc,
                self,
                (
                    'bLength',
                    'bDescriptorType',
                    'wTotalLength',
                    'bNumInterfaces',
                    'bConfigurationValue',
                    'iConfiguration',
                    'bmAttributes',
                    'bMaxPower'
                )
            )

    def set(self):
        r"""Set this configuration as the active one."""
        self.device.set_configuration(self.bConfigurationValue)

    def __iter__(self):
        r"""Iterate over all interfaces of the configuration."""
        for i in range(self.bNumInterfaces):
            alt = 0
            try:
                while True:
                    yield Interface(self.device, i, alt, self.index)
                    alt += 1
            except (USBError, IndexError):
                pass
    def __getitem__(self, index):
        r"""Return the Interface object in the given position.

        index is a tuple of two values with interface index and
        alternate setting index, respectivally. Example:

        >>> interface = config[(0, 0)]
        """
        return Interface(self.device, index[0], index[1], self.index)


class Device(object):
    r"""Device object.

    This class contains all fields of the Device Descriptor according
    to the USB Specification. You may access them as class properties.
    For example, to access the field bDescriptorType of the device
    descriptor:

    >>> import usb.core
    >>> dev = usb.core.find()
    >>> dev.bDescriptorType

    Additionally, the class provides methods to communicate with
    the hardware. Typically, an application will first call the
    set_configuration() method to put the device in a known configured
    state, optionally call the set_interface_altsetting() to select the
    alternate setting (if there is more than one) of the interface used,
    and call the write() and read() method to send and receive data.

    When working in a new hardware, one first try would be like this:

    >>> import usb.core
    >>> dev = usb.core.find(idVendor=myVendorId, idProduct=myProductId)
    >>> dev.set_configuration()
    >>> dev.write(1, 'test')

    This sample finds the device of interest (myVendorId and myProductId should be
    replaced by the corresponding values of your device), then configures the device
    (by default, the configuration value is 1, which is a typical value for most
    devices) and then writes some data to the endpoint 0x01.

    Timeout values for the write, read and ctrl_transfer methods are specified in
    miliseconds. If the parameter is omitted, Device.default_timeout value will
    be used instead. This property can be set by the user at anytime.
    """

    def __init__(self, dev, backend):
        r"""Initialize the Device object.

        Library users should normally get a Device instance through
        the find function. The dev parameter is the identification
        of a device to the backend and its meaning is opaque outside
        of it. The backend parameter is a instance of a backend
        object.
        """
        self._ctx = _ResourceManager(dev, backend)
        self.__default_timeout = _DEFAULT_TIMEOUT
        self._serial_number, self._product, self._manufacturer = None, None, None

        desc = backend.get_device_descriptor(dev)

        _set_attr(
                desc,
                self,
                (
                    'bLength',
                    'bDescriptorType',
                    'bcdUSB',
                    'bDeviceClass',
                    'bDeviceSubClass',
                    'bDeviceProtocol',
                    'bMaxPacketSize0',
                    'idVendor',
                    'idProduct',
                    'bcdDevice',
                    'iManufacturer',
                    'iProduct',
                    'iSerialNumber',
                    'bNumConfigurations',
                    'address',
                    'bus',
                    'port_number'
                )
            )

        if desc.bus is not None:
            self.bus = int(desc.bus)
        else:
            self.bus = None

        if desc.address is not None:
            self.address = int(desc.address)
        else:
            self.address = None

        if desc.port_number is not None:
            self.port_number = int(desc.port_number)
        else:
            self.port_number = None

    @property
    def serial_number(self):
        """ Return the USB device's serial number string descriptor

        This property will cause some USB traffic the first time it is accessed
        and cache the resulting value for future use.
        """
        if self._serial_number is None:
            self._serial_number = util.get_string(self, self.iSerialNumber)
        return self._serial_number

    @property
    def product(self):
        """ Return the USB device's product string descriptor

        This property will cause some USB traffic the first time it is accessed
        and cache the resulting value for future use.
        """
        if self._product is None:
            self._product = util.get_string(self, self.iProduct)
        return self._product

    @property
    def manufacturer(self):
        """ Return the USB device's manufacturer string descriptor

        This property will cause some USB traffic the first time it is accessed
        and cache the resulting value for future use.
        """
        if self._manufacturer is None:
            self._manufacturer = util.get_string(self, self.iManufacturer)
        return self._manufacturer

    def set_configuration(self, configuration = None):
        r"""Set the active configuration.

        The configuration parameter is the bConfigurationValue field of the
        configuration you want to set as active. If you call this method
        without parameter, it will use the first configuration found.
        As a device hardly ever has more than one configuration, calling
        the method without parameter is enough to get the device ready.
        """
        self._ctx.managed_set_configuration(self, configuration)

    def get_active_configuration(self):
        r"""Return a Configuration object representing the current configuration set."""
        return self._ctx.get_active_configuration(self)

    def set_interface_altsetting(self, interface = None, alternate_setting = None):
        r"""Set the alternate setting for an interface.

        When you want to use an interface and it has more than one alternate setting,
        you should call this method to select the alternate setting you would like
        to use. If you call the method without one or the two parameters, it will
        be selected the first one found in the Device in the same way of set_configuration
        method.

        Commonly, an interface has only one alternate setting and this call is
        not necessary. For most of the devices, either it has more than one alternate
        setting or not, it is not harmful to make a call to this method with no arguments,
        as devices will silently ignore the request when there is only one alternate
        setting, though the USB Spec allows devices with no additional alternate setting
        return an error to the Host in response to a SET_INTERFACE request.

        If you are in doubt, you may want to call it with no arguments wrapped by
        a try/except clause:

        >>> try:
        >>>     dev.set_interface_altsetting()
        >>> except usb.core.USBError:
        >>>     pass
        """
        self._ctx.managed_set_interface(self, interface, alternate_setting)

    def clear_halt(self, ep):
        r""" Clear the halt/stall condition for the endpoint ep."""
        if isinstance(ep, Endpoint):
            ep = ep.bEndpointAddress
        self._ctx.managed_open()
        self._ctx.backend.clear_halt(self._ctx.handle, ep)

    def reset(self):
        r"""Reset the device."""
        self._ctx.managed_open()
        self._ctx.dispose(self, False)
        self._ctx.backend.reset_device(self._ctx.handle)
        self._ctx.dispose(self, True)

    def write(self, endpoint, data, timeout = None):
        r"""Write data to the endpoint.

        This method is used to send data to the device. The endpoint parameter
        corresponds to the bEndpointAddress member whose endpoint you want to
        communicate with.

        The data parameter should be a sequence like type convertible to
        array type (see array module).

        The timeout is specified in miliseconds.

        The method returns the number of bytes written.
        """
        backend = self._ctx.backend

        fn_map = {
                    util.ENDPOINT_TYPE_BULK:backend.bulk_write,
                    util.ENDPOINT_TYPE_INTR:backend.intr_write,
                    util.ENDPOINT_TYPE_ISO:backend.iso_write
                }

        intf, ep = self._ctx.setup_request(self, endpoint)
        fn = fn_map[util.endpoint_type(ep.bmAttributes)]

        return fn(
                self._ctx.handle,
                ep.bEndpointAddress,
                intf.bInterfaceNumber,
                _interop.as_array(data),
                self.__get_timeout(timeout)
            )

    def read(self, endpoint, size_or_buffer, timeout = None):
        r"""Read data from the endpoint.

        This method is used to receive data from the device. The endpoint parameter
        corresponds to the bEndpointAddress member whose endpoint you want to
        communicate with. The size_or_buffer parameter either tells how many bytes
        you want to read or supplies the buffer to receive the data (it *must* be
        an object of the type array).

        The timeout is specified in miliseconds.

        If the size_or_buffer parameter is the number of bytes to read, the method
        returns an array object with the data read. If the size_or_buffer parameter
        is an array object, it returns the number of bytes actually read.
        """
        backend = self._ctx.backend

        fn_map = {
                    util.ENDPOINT_TYPE_BULK:backend.bulk_read,
                    util.ENDPOINT_TYPE_INTR:backend.intr_read,
                    util.ENDPOINT_TYPE_ISO:backend.iso_read
                }

        intf, ep = self._ctx.setup_request(self, endpoint)
        fn = fn_map[util.endpoint_type(ep.bmAttributes)]

        if isinstance(size_or_buffer, array.array):
            buff = size_or_buffer
        else: # here we consider it is a integer
            buff = util.create_buffer(size_or_buffer)

        ret = fn(
                self._ctx.handle,
                ep.bEndpointAddress,
                intf.bInterfaceNumber,
                buff,
                self.__get_timeout(timeout))

        if isinstance(size_or_buffer, array.array):
            return ret
        elif ret != len(buff) * buff.itemsize:
            return buff[:ret]
        else:
            return buff


    def ctrl_transfer(self, bmRequestType, bRequest, wValue=0, wIndex=0,
            data_or_wLength = None, timeout = None):
        r"""Do a control transfer on the endpoint 0.

        This method is used to issue a control transfer over the
        endpoint 0(endpoint 0 is required to always be a control endpoint).

        The parameters bmRequestType, bRequest, wValue and wIndex are the
        same of the USB Standard Control Request format.

        Control requests may or may not have a data payload to write/read.
        In cases which it has, the direction bit of the bmRequestType
        field is used to infere the desired request direction. For
        host to device requests (OUT), data_or_wLength parameter is
        the data payload to send, and it must be a sequence type convertible
        to an array object. In this case, the return value is the number of data
        payload written. For device to host requests (IN), data_or_wLength
        is either the wLength parameter of the control request specifying the
        number of bytes to read in data payload, and the return value is
        an array object with data read, or an array object which the data
        will be read to, and the return value is the number of bytes read.
        """
        try:
            buff = util.create_buffer(data_or_wLength)
        except TypeError:
            buff = _interop.as_array(data_or_wLength)

        self._ctx.managed_open()

        # Thanks to Johannes Stezenbach to point me out that we need to
        # claim the recipient interface
        recipient = bmRequestType & 3
        if recipient == util.CTRL_RECIPIENT_INTERFACE:
            interface_number = wIndex & 0xff
            self._ctx.managed_claim_interface(self, interface_number)

        ret = self._ctx.backend.ctrl_transfer(
                                    self._ctx.handle,
                                    bmRequestType,
                                    bRequest,
                                    wValue,
                                    wIndex,
                                    buff,
                                    self.__get_timeout(timeout))

        if isinstance(data_or_wLength, array.array) \
                or util.ctrl_direction(bmRequestType) == util.CTRL_OUT:
            return ret
        elif ret != len(buff) * buff.itemsize:
            return buff[:ret]
        else:
            return buff

    def is_kernel_driver_active(self, interface):
        r"""Determine if there is kernel driver associated with the interface.

        If a kernel driver is active, and the object will be unable to perform I/O.

        The interface parameter is the device interface number to check.
        """
        self._ctx.managed_open()
        return self._ctx.backend.is_kernel_driver_active(
                self._ctx.handle,
                interface)

    def detach_kernel_driver(self, interface):
        r"""Detach a kernel driver.

        If successful, you will then be able to perform I/O.

        The interface parameter is the device interface number to detach the driver from.
        """
        self._ctx.managed_open()
        self._ctx.backend.detach_kernel_driver(
            self._ctx.handle,
            interface)

    def attach_kernel_driver(self, interface):
        r"""Re-attach an interface's kernel driver, which was previously
        detached using detach_kernel_driver().

        The interface parameter is the device interface number to attach the driver to.
        """
        self._ctx.managed_open()
        self._ctx.backend.attach_kernel_driver(
            self._ctx.handle,
            interface)

    def __iter__(self):
        r"""Iterate over all configurations of the device."""
        for i in range(self.bNumConfigurations):
            yield Configuration(self, i)

    def __getitem__(self, index):
        r"""Return the Configuration object in the given position."""
        return Configuration(self, index)

    def __del__(self):
        self._ctx.dispose(self)

    def __get_timeout(self, timeout):
        if timeout is not None:
            return timeout
        return self.__default_timeout

    def __set_def_tmo(self, tmo):
        if tmo < 0:
            raise ValueError('Timeout cannot be a negative value')
        self.__default_timeout = tmo

    def __get_def_tmo(self):
        return self.__default_timeout

    default_timeout = property(
                        __get_def_tmo,
                        __set_def_tmo,
                        doc = 'Default timeout for transfer I/O functions'
                    )

def find(find_all=False, backend = None, custom_match = None, **args):
    r"""Find an USB device and return it.

    find() is the function used to discover USB devices.
    You can pass as arguments any combination of the
    USB Device Descriptor fields to match a device. For example:

    find(idVendor=0x3f4, idProduct=0x2009)

    will return the Device object for the device with
    idVendor Device descriptor field equals to 0x3f4 and
    idProduct equals to 0x2009.

    If there is more than one device which matchs the criteria,
    the first one found will be returned. If a matching device cannot
    be found the function returns None. If you want to get all
    devices, you can set the parameter find_all to True, then find
    will return an list with all matched devices. If no matching device
    is found, it will return an empty list. Example:

    printers = find(find_all=True, bDeviceClass=7)

    This call will get all the USB printers connected to the system.
    (actually may be not, because some devices put their class
     information in the Interface Descriptor).

    You can also use a customized match criteria:

    dev = find(custom_match = lambda d: d.idProduct=0x3f4 and d.idvendor=0x2009)

    A more accurate printer finder using a customized match would be like
    so:

    def is_printer(dev):
        import usb.util
        if dev.bDeviceClass == 7:
            return True
        for cfg in dev:
            if usb.util.find_descriptor(cfg, bInterfaceClass=7) is not None:
                return True

    printers = find(find_all=True, custom_match = is_printer)

    Now even if the device class code is in the interface descriptor the
    printer will be found.

    You can combine a customized match with device descriptor fields. In this
    case, the fields must match and the custom_match must return True. In the our
    previous example, if we would like to get all printers belonging to the
    manufacturer 0x3f4, the code would be like so:

    printers = find(find_all=True, idVendor=0x3f4, custom_match=is_printer)

    If you want to use find as a 'list all devices' function, just call
    it with find_all = True:

    devices = find(find_all=True)

    Finally, you may pass a custom backend to the find function:

    find(backend = MyBackend())

    PyUSB has builtin backends for libusb 0.1, libusb 1.0 and OpenUSB.
    If you do not supply a backend explicitly, find() function will select
    one of the predefineds backends according to system availability.

    Backends are explained in the usb.backend module.
    """

    def device_iter(k, v):
        for dev in backend.enumerate_devices():
            d = Device(dev, backend)
            if  _interop._reduce(
                        lambda a, b: a and b,
                        map(
                            operator.eq,
                            v,
                            map(lambda i: getattr(d, i), k)
                        ),
                        True
                    ) and (custom_match is None or custom_match(d)):
                yield d

    if backend is None:
        import usb.backend.libusb1 as libusb1
        import usb.backend.libusb0 as libusb0
        import usb.backend.openusb as openusb

        for m in (libusb1, openusb, libusb0):
            backend = m.get_backend()
            if backend is not None:
                _logger.info('find(): using backend "%s"', m.__name__)
                break
        else:
            raise ValueError('No backend available')

    k, v = args.keys(), args.values()

    if find_all:
        return [d for d in device_iter(k, v)]
    else:
        try:
            return _interop._next(device_iter(k, v))
        except StopIteration:
            return None

########NEW FILE########
__FILENAME__ = legacy
# Copyright (C) 2009-2013 Wander Lairson Costa 
# 
# The following terms apply to all files associated
# with the software unless explicitly disclaimed in individual files.
# 
# The authors hereby grant permission to use, copy, modify, distribute,
# and license this software and its documentation for any purpose, provided
# that existing copyright notices are retained in all copies and that this
# notice is included verbatim in any distributions. No written agreement,
# license, or royalty fee is required for any of the authorized uses.
# Modifications to this software may be copyrighted by their authors
# and need not follow the licensing terms described here, provided that
# the new terms are clearly indicated on the first page of each file where
# they apply.
# 
# IN NO EVENT SHALL THE AUTHORS OR DISTRIBUTORS BE LIABLE TO ANY PARTY
# FOR DIRECT, INDIRECT, SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES
# ARISING OUT OF THE USE OF THIS SOFTWARE, ITS DOCUMENTATION, OR ANY
# DERIVATIVES THEREOF, EVEN IF THE AUTHORS HAVE BEEN ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
# 
# THE AUTHORS AND DISTRIBUTORS SPECIFICALLY DISCLAIM ANY WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.  THIS SOFTWARE
# IS PROVIDED ON AN "AS IS" BASIS, AND THE AUTHORS AND DISTRIBUTORS HAVE
# NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES, ENHANCEMENTS, OR
# MODIFICATIONS.

import usb.core as core
import usb.util as util
import usb._interop as _interop
import usb.control as control

__author__ = 'Wander Lairson Costa'

USBError = core.USBError

CLASS_AUDIO = 1
CLASS_COMM = 2
CLASS_DATA = 10
CLASS_HID = 3
CLASS_HUB = 9
CLASS_MASS_STORAGE = 8
CLASS_PER_INTERFACE = 0
CLASS_PRINTER = 7
CLASS_VENDOR_SPEC = 255
DT_CONFIG = 2
DT_CONFIG_SIZE = 9
DT_DEVICE = 1
DT_DEVICE_SIZE = 18
DT_ENDPOINT = 5
DT_ENDPOINT_AUDIO_SIZE = 9
DT_ENDPOINT_SIZE = 7
DT_HID = 33
DT_HUB = 41
DT_HUB_NONVAR_SIZE = 7
DT_INTERFACE = 4
DT_INTERFACE_SIZE = 9
DT_PHYSICAL = 35
DT_REPORT = 34
DT_STRING = 3
ENDPOINT_ADDRESS_MASK = 15
ENDPOINT_DIR_MASK = 128
ENDPOINT_IN = 128
ENDPOINT_OUT = 0
ENDPOINT_TYPE_BULK = 2
ENDPOINT_TYPE_CONTROL = 0
ENDPOINT_TYPE_INTERRUPT = 3
ENDPOINT_TYPE_ISOCHRONOUS = 1
ENDPOINT_TYPE_MASK = 3
ERROR_BEGIN = 500000
MAXALTSETTING = 128
MAXCONFIG = 8
MAXENDPOINTS = 32
MAXINTERFACES = 32
RECIP_DEVICE = 0
RECIP_ENDPOINT = 2
RECIP_INTERFACE = 1
RECIP_OTHER = 3
REQ_CLEAR_FEATURE = 1
REQ_GET_CONFIGURATION = 8
REQ_GET_DESCRIPTOR = 6
REQ_GET_INTERFACE = 10
REQ_GET_STATUS = 0
REQ_SET_ADDRESS = 5
REQ_SET_CONFIGURATION = 9
REQ_SET_DESCRIPTOR = 7
REQ_SET_FEATURE = 3
REQ_SET_INTERFACE = 11
REQ_SYNCH_FRAME = 12
TYPE_CLASS = 32
TYPE_RESERVED = 96
TYPE_STANDARD = 0
TYPE_VENDOR = 64

class Endpoint(object):
    r"""Endpoint descriptor object."""
    def __init__(self, ep):
        self.address = ep.bEndpointAddress
        self.interval = ep.bInterval
        self.maxPacketSize = ep.wMaxPacketSize
        self.type = util.endpoint_type(ep.bmAttributes)

class Interface(object):
    r"""Interface descriptor object."""
    def __init__(self, intf):
        self.alternateSetting = intf.bAlternateSetting
        self.interfaceNumber = intf.bInterfaceNumber
        self.iInterface = intf.iInterface
        self.interfaceClass = intf.bInterfaceClass
        self.interfaceSubClass = intf.bInterfaceSubClass
        self.interfaceProtocol = intf.bInterfaceProtocol
        self.endpoints = [Endpoint(e) for e in intf]

class Configuration(object):
    r"""Configuration descriptor object."""
    def __init__(self, cfg):
        self.iConfiguration = cfg.iConfiguration
        self.maxPower = cfg.bMaxPower << 2
        self.remoteWakeup = (cfg.bmAttributes >> 5) & 1
        self.selfPowered = (cfg.bmAttributes >> 6) & 1
        self.totalLength = cfg.wTotalLength
        self.value = cfg.bConfigurationValue
        self.interfaces = [
                            list(g) for k, g in _interop._groupby(
                                    _interop._sorted(
                                        [Interface(i) for i in cfg],
                                        key=lambda i: i.interfaceNumber
                                    ),
                                    lambda i: i.alternateSetting)
                        ]

class DeviceHandle(object):
    def __init__(self, dev):
        self.dev = dev
        self.__claimed_interface = -1

    def bulkWrite(self, endpoint, buffer, timeout = 100):
        r"""Perform a bulk write request to the endpoint specified.

            Arguments:
                endpoint: endpoint number.
                buffer: sequence data buffer to write.
                        This parameter can be any sequence type.
                timeout: operation timeout in miliseconds. (default: 100)
                         Returns the number of bytes written.
        """
        return self.dev.write(endpoint, buffer, self.__claimed_interface, timeout)

    def bulkRead(self, endpoint, size, timeout = 100):
        r"""Performs a bulk read request to the endpoint specified.

            Arguments:
                endpoint: endpoint number.
                size: number of bytes to read.
                timeout: operation timeout in miliseconds. (default: 100)
            Return a tuple with the data read.
        """
        return self.dev.read(endpoint, size, self.__claimed_interface, timeout)

    def interruptWrite(self, endpoint, buffer, timeout = 100):
        r"""Perform a interrupt write request to the endpoint specified.

            Arguments:
                endpoint: endpoint number.
                buffer: sequence data buffer to write.
                        This parameter can be any sequence type.
                timeout: operation timeout in miliseconds. (default: 100)
                         Returns the number of bytes written.
        """
        return self.dev.write(endpoint, buffer, self.__claimed_interface, timeout)

    def interruptRead(self, endpoint, size, timeout = 100):
        r"""Performs a interrupt read request to the endpoint specified.

            Arguments:
                endpoint: endpoint number.
                size: number of bytes to read.
                timeout: operation timeout in miliseconds. (default: 100)
            Return a tuple with the data read.
        """
        return self.dev.read(endpoint, size, self.__claimed_interface, timeout)

    def controlMsg(self, requestType, request, buffer, value = 0, index = 0, timeout = 100):
        r"""Perform a control request to the default control pipe on a device.

        Arguments:
            requestType: specifies the direction of data flow, the type
                         of request, and the recipient.
            request: specifies the request.
            buffer: if the transfer is a write transfer, buffer is a sequence 
                    with the transfer data, otherwise, buffer is the number of
                    bytes to read.
            value: specific information to pass to the device. (default: 0)
                   index: specific information to pass to the device. (default: 0)
            timeout: operation timeout in miliseconds. (default: 100)
        Return the number of bytes written.
        """
        return self.dev.ctrl_transfer(
                    requestType,
                    request,
                    wValue = value,
                    wIndex = index,
                    data_or_wLength = buffer,
                    timeout = timeout
                )

    def clearHalt(self, endpoint):
        r"""Clears any halt status on the specified endpoint.

        Arguments:
            endpoint: endpoint number.
        """
        cfg = self.dev.get_active_configuration()
        intf = util.find_descriptor(cfg, bInterfaceNumber = self.__claimed_interface)
        e = util.find_descriptor(intf, bEndpointAddress = endpoint)
        control.clear_feature(self.dev, control.ENDPOINT_HALT, e)

    def claimInterface(self, interface):
        r"""Claims the interface with the Operating System.

        Arguments:
            interface: interface number or an Interface object.
        """
        if isinstance(interface, Interface):
            if_num = interface.interfaceNumber
        else:
            if_num = interface

        util.claim_interface(self.dev, if_num)
        self.__claimed_interface = if_num

    def releaseInterface(self):
        r"""Release an interface previously claimed with claimInterface."""
        util.release_interface(self.dev, self.__claimed_interface)
        self.__claimed_interface = -1

    def reset(self):
        r"""Reset the specified device by sending a RESET
            down the port it is connected to."""
        self.dev.reset()

    def resetEndpoint(self, endpoint):
        r"""Reset all states for the specified endpoint.

        Arguments:
            endpoint: endpoint number.
        """
        self.clearHalt(endpoint)

    def setConfiguration(self, configuration):
        r"""Set the active configuration of a device.

        Arguments:
            configuration: a configuration value or a Configuration object.
        """
        self.dev.set_configuration(configuration)

    def setAltInterface(self, alternate):
        r"""Sets the active alternate setting of the current interface.

        Arguments:
            alternate: an alternate setting number or an Interface object.
        """
        self.dev.set_interface_altsetting(self.__claimed_interface, alternate)

    def getString(self, index, length, langid = None):
        r"""Retrieve the string descriptor specified by index
            and langid from a device.

        Arguments:
            index: index of descriptor in the device.
            length: number of bytes of the string (ignored)
            langid: Language ID. If it is omittedi, will be
                    used the first language.
        """
        return util.get_string(self.dev, index, langid).encode('ascii')

    def getDescriptor(self, desc_type, desc_index, length, endpoint = -1):
        r"""Retrieves a descriptor from the device identified by the type
        and index of the descriptor.

        Arguments:
            desc_type: descriptor type.
            desc_index: index of the descriptor.
            len: descriptor length.
            endpoint: ignored.
        """
        return control.get_descriptor(self.dev, length, desc_type, desc_index)

    def detachKernelDriver(self, interface):
        r"""Detach a kernel driver from the interface (if one is attached,
            we have permission and the operation is supported by the OS)

        Arguments:
            interface: interface number or an Interface object.
        """
        self.dev.detach_kernel_driver(interface)

class Device(object):
    r"""Device descriptor object"""
    def __init__(self, dev):
        self.deviceClass = dev.bDeviceClass
        self.deviceSubClass = dev.bDeviceSubClass
        self.deviceProtocol = dev.bDeviceProtocol
        self.deviceVersion = str((dev.bcdDevice >> 12) & 0xf) + \
                            str((dev.bcdDevice >> 8) & 0xf) + \
                            '.' + \
                            str((dev.bcdDevice >> 4) & 0xf) + \
                            str(dev.bcdDevice & 0xf)
        self.devnum = None
        self.filename = ''
        self.iManufacturer = dev.iManufacturer
        self.iProduct = dev.iProduct
        self.iSerialNumber = dev.iSerialNumber
        self.idProduct = dev.idProduct
        self.idVendor = dev.idVendor
        self.maxPacketSize = dev.bMaxPacketSize0
        self.usbVersion = str((dev.bcdUSB >> 12) & 0xf) + \
                         str((dev.bcdUSB >> 8) & 0xf) + \
                         '.' + \
                         str((dev.bcdUSB >> 4) & 0xf) + \
                         str(dev.bcdUSB & 0xf)
        self.configurations = [Configuration(c) for c in dev]
        self.dev = dev

    def open(self):
        r"""Open the device for use.

        Return a DeviceHandle object
        """
        return DeviceHandle(self.dev)

class Bus(object):
    r"""Bus object."""
    def __init__(self, devices):
        self.dirname = ''
        self.location = 0
        self.devices = [Device(d) for d in devices]

def busses():
    r"""Return a tuple with the usb busses."""
    return (Bus(g) for k, g in _interop._groupby(
            _interop._sorted(core.find(find_all=True), key=lambda d: d.bus),
            lambda d: d.bus))


########NEW FILE########
__FILENAME__ = libloader
# <header>
# -*- coding: utf-8 -*-

import ctypes
import ctypes.util
import logging
import sys

__all__ = [
            'LibaryException',
            'LibraryNotFoundException',
            'NoLibraryCandidatesException',
            'LibraryNotLoadedException',
            'LibraryMissingSymbolsException',
            'locate_library',
            'load_library',
            'load_locate_library'
]


_LOGGER = logging.getLogger('usb.libloader')


class LibaryException(OSError):
    pass

class LibraryNotFoundException(LibaryException):
    pass

class NoLibraryCandidatesException(LibraryNotFoundException):
    pass

class LibraryNotLoadedException(LibaryException):
    pass

class LibraryMissingSymbolsException(LibaryException):
    pass


def locate_library (candidates, find_library=ctypes.util.find_library):
    """Tries to locate a library listed in candidates using the given
    find_library() function (or ctypes.util.find_library).
    Returns the first library found, which can the library's name or the
    path to the library file, depending on find_library().
    Returns None if no library found.

    arguments:
    * candidates   -- iterable with library names
    * find_library -- function that takes one positional arg (candidate)
                      and returns a non-empty str if a library has been found.
                      Any "false" value (None,False,empty str) is interpreted
                      as "library not found".
                      Defaults to ctypes.util.find_library if not given or
                      None.
    """
    if find_library is None:
        find_library = ctypes.util.find_library

    use_dll_workaround = (
        sys.platform == 'win32' and find_library is ctypes.util.find_library
    )

    for candidate in candidates:
        # Workaround for CPython 3.3 issue#16283 / pyusb #14
        if use_dll_workaround:
            candidate += '.dll'

        libname = find_library(candidate)
        if libname:
            return libname
    # -- end for
    return None

def load_library(lib, name=None, lib_cls=None):
    """Loads a library. Catches and logs exceptions.

    Returns: the loaded library or None

    arguments:
    * lib        -- path to/name of the library to be loaded
    * name       -- the library's identifier (for logging)
                    Defaults to None.
    * lib_cls    -- library class. Defaults to None (-> ctypes.CDLL).
    """
    try:
        if lib_cls:
            return lib_cls(lib)
        else:
            return ctypes.CDLL(lib)
    except Exception:
        lib_msg = (
            (('%s (%s)' % (name, lib)) if name else lib)
            + ' could not be loaded'
        )
        if sys.platform == 'cygwin':
            lib_msg += ' in cygwin'
        _LOGGER.error(lib_msg, exc_info=True)
        return None

def load_locate_library(candidates, cygwin_lib, name,
                        win_cls=None, cygwin_cls=None, others_cls=None,
                        find_library=None, check_symbols=None):
    """Locates and loads a library.

    Returns: the loaded library

    arguments:
    * candidates    -- candidates list for locate_library()
    * cygwin_lib    -- name of the cygwin library
    * name          -- lib identifier (for logging). Defaults to None.
    * win_cls       -- class that is used to instantiate the library on
                       win32 platforms. Defaults to None (-> ctypes.CDLL).
    * other_cls     -- library class for cygwin platforms.
                       Defaults to None (-> ctypes.CDLL).
    * cygwin_cls    -- library class for all other platforms.
                       Defaults to None (-> ctypes.CDLL).
    * find_library  -- see locate_library(). Defaults to None.
    * check_symbols -- either None or a list of symbols that the loaded lib
                       must provide (hasattr(<>)) in order to be considered
                       valid. LibraryMissingSymbolsException is raised if
                       any symbol is missing.

    raises:
    * NoLibraryCandidatesException
    * LibraryNotFoundException
    * LibraryNotLoadedException
    * LibraryMissingSymbolsException
    """
    if sys.platform == 'cygwin':
        if cygwin_lib:
            loaded_lib = load_library(cygwin_lib, name, cygwin_cls)
        else:
            raise NoLibraryCandidatesException(name)
    elif candidates:
        lib = locate_library(candidates, find_library)
        if lib:
            if sys.platform == 'win32':
                loaded_lib = load_library(lib, name, win_cls)
            else:
                loaded_lib = load_library(lib, name, others_cls)
        else:
            _LOGGER.error('%r could not be found', (name or candidates))
            raise LibraryNotFoundException(name)
    else:
        raise NoLibraryCandidatesException(name)

    if loaded_lib is None:
        raise LibraryNotLoadedException(name)
    elif check_symbols:
        symbols_missing = [
                    s for s in check_symbols if not hasattr(loaded_lib, s)
        ]
        if symbols_missing:
            msg = ('%r, missing symbols: %r', lib, symbols_missing )
            _LOGGER.error(msg)
            raise LibraryMissingSymbolsException(lib)
        else:
            return loaded_lib
    else:
        return loaded_lib

########NEW FILE########
__FILENAME__ = util
# Copyright (C) 2009-2013 Wander Lairson Costa
#
# The following terms apply to all files associated
# with the software unless explicitly disclaimed in individual files.
#
# The authors hereby grant permission to use, copy, modify, distribute,
# and license this software and its documentation for any purpose, provided
# that existing copyright notices are retained in all copies and that this
# notice is included verbatim in any distributions. No written agreement,
# license, or royalty fee is required for any of the authorized uses.
# Modifications to this software may be copyrighted by their authors
# and need not follow the licensing terms described here, provided that
# the new terms are clearly indicated on the first page of each file where
# they apply.
#
# IN NO EVENT SHALL THE AUTHORS OR DISTRIBUTORS BE LIABLE TO ANY PARTY
# FOR DIRECT, INDIRECT, SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES
# ARISING OUT OF THE USE OF THIS SOFTWARE, ITS DOCUMENTATION, OR ANY
# DERIVATIVES THEREOF, EVEN IF THE AUTHORS HAVE BEEN ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# THE AUTHORS AND DISTRIBUTORS SPECIFICALLY DISCLAIM ANY WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.  THIS SOFTWARE
# IS PROVIDED ON AN "AS IS" BASIS, AND THE AUTHORS AND DISTRIBUTORS HAVE
# NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES, ENHANCEMENTS, OR
# MODIFICATIONS.

r"""usb.util - Utility functions.

This module exports:

endpoint_address - return the endpoint absolute address.
endpoint_direction - return the endpoint transfer direction.
endpoint_type - return the endpoint type
ctrl_direction - return the direction of a control transfer
build_request_type - build a bmRequestType field of a control transfer.
find_descriptor - find an inner descriptor.
claim_interface - explicitly claim an interface.
release_interface - explicitly release an interface.
dispose_resources - release internal resources allocated by the object.
get_string - retrieve a string descriptor from the device.
"""

__author__ = 'Wander Lairson Costa'

import operator
import array
import usb._interop as _interop

# descriptor type
DESC_TYPE_DEVICE = 0x01
DESC_TYPE_CONFIG = 0x02
DESC_TYPE_STRING = 0x03
DESC_TYPE_INTERFACE = 0x04
DESC_TYPE_ENDPOINT = 0x05

# endpoint direction
ENDPOINT_IN = 0x80
ENDPOINT_OUT = 0x00

# endpoint type
ENDPOINT_TYPE_CTRL = 0x00
ENDPOINT_TYPE_ISO = 0x01
ENDPOINT_TYPE_BULK = 0x02
ENDPOINT_TYPE_INTR = 0x03

# control request type
CTRL_TYPE_STANDARD = (0 << 5)
CTRL_TYPE_CLASS = (1 << 5)
CTRL_TYPE_VENDOR = (2 << 5)
CTRL_TYPE_RESERVED = (3 << 5)

# control request recipient
CTRL_RECIPIENT_DEVICE = 0
CTRL_RECIPIENT_INTERFACE = 1
CTRL_RECIPIENT_ENDPOINT = 2
CTRL_RECIPIENT_OTHER = 3

# control request direction
CTRL_OUT = 0x00
CTRL_IN = 0x80

_ENDPOINT_ADDR_MASK = 0x0f
_ENDPOINT_DIR_MASK = 0x80
_ENDPOINT_TRANSFER_TYPE_MASK = 0x03
_CTRL_DIR_MASK = 0x80

def endpoint_address(address):
    r"""Return the endpoint absolute address.

    The address parameter is the bEndpointAddress field
    of the endpoint descriptor.
    """
    return address & _ENDPOINT_ADDR_MASK

def endpoint_direction(address):
    r"""Return the endpoint direction.

    The address parameter is the bEndpointAddress field
    of the endpoint descriptor.
    The possible return values are ENDPOINT_OUT or ENDPOINT_IN.
    """
    return address & _ENDPOINT_DIR_MASK

def endpoint_type(bmAttributes):
    r"""Return the transfer type of the endpoint.

    The bmAttributes parameter is the bmAttributes field
    of the endpoint descriptor.
    The possible return values are: ENDPOINT_TYPE_CTRL,
    ENDPOINT_TYPE_ISO, ENDPOINT_TYPE_BULK or ENDPOINT_TYPE_INTR.
    """
    return bmAttributes & _ENDPOINT_TRANSFER_TYPE_MASK

def ctrl_direction(bmRequestType):
    r"""Return the direction of a control request.

    The bmRequestType parameter is the value of the
    bmRequestType field of a control transfer.
    The possible return values are CTRL_OUT or CTRL_IN.
    """
    return bmRequestType & _CTRL_DIR_MASK

def build_request_type(direction, type, recipient):
    r"""Build a bmRequestType field for control requests.

    These is a conventional function to build a bmRequestType
    for a control request.

    The direction parameter can be CTRL_OUT or CTRL_IN.
    The type parameter can be CTRL_TYPE_STANDARD, CTRL_TYPE_CLASS,
    CTRL_TYPE_VENDOR or CTRL_TYPE_RESERVED values.
    The recipient can be CTRL_RECIPIENT_DEVICE, CTRL_RECIPIENT_INTERFACE,
    CTRL_RECIPIENT_ENDPOINT or CTRL_RECIPIENT_OTHER.

    Return the bmRequestType value.
    """
    return recipient | type | direction

def create_buffer(length):
    r"""Create a buffer to be passed to a read function

    A read function may receive a out buffer so the data
    is read inplace and the object can be reused, avoiding
    the overhead of creating a new object at each new read
    call. This function creates a compatible sequence buffer
    of the given length.
    """
    return array.array('B', '\x00' * length)

def find_descriptor(desc, find_all=False, custom_match=None, **args):
    r"""Find an inner descriptor.

    find_descriptor works in the same way the core.find() function does,
    but it acts on general descriptor objects. For example, suppose you
    have a Device object called dev and want a Configuration of this
    object with its bConfigurationValue equals to 1, the code would
    be like so:

    >>> cfg = util.find_descriptor(dev, bConfigurationValue=1)

    You can use any field of the Descriptor as a match criteria, and you
    can supply a customized match just like core.find() does. The
    find_descriptor function also accepts the find_all parameter to get
    a list of descriptor instead of just one.
    """
    def desc_iter(k, v):
        for d in desc:
            if (custom_match is None or custom_match(d)) and \
                _interop._reduce(
                        lambda a, b: a and b,
                        map(
                            operator.eq,
                            v,
                            map(lambda i: getattr(d, i), k)
                        ),
                        True
                    ):
                yield d

    k, v = args.keys(), args.values()

    if find_all:
        return [d for d in desc_iter(k, v)]
    else:
        try:
            return _interop._next(desc_iter(k, v))
        except StopIteration:
            return None

def claim_interface(device, interface):
    r"""Explicitly claim an interface.

    PyUSB users normally do not have to worry about interface claiming,
    as the library takes care of it automatically. But there are situations
    where you need deterministic interface claiming. For these uncommon
    cases, you can use claim_interface.

    If the interface is already claimed, either through a previously call
    to claim_interface or internally by the device object, nothing happens.
    """
    device._ctx.managed_claim_interface(device, interface)

def release_interface(device, interface):
    r"""Explicitly release an interface.

    This function is used to release an interface previously claimed,
    either through a call to claim_interface or internally by the
    device object.

    Normally, you do not need to worry about claiming policies, as
    the device object takes care of it automatically.
    """
    device._ctx.managed_release_interface(device, interface)

def dispose_resources(device):
    r"""Release internal resources allocated by the object.

    Sometimes you need to provide deterministic resources
    freeing, for example to allow another application to
    talk to the device. As Python does not provide deterministic
    destruction, this function releases all internal resources
    allocated by the device, like device handle and interface
    policy.

    After calling this function, you can continue using the device
    object normally. If the resources will be necessary again, it
    will allocate them automatically.
    """
    device._ctx.dispose(device)

def get_string(dev, index, langid = None):
    r"""Retrieve a string descriptor from the device.

    dev is the Device object to which the request will be
    sent to.

    index is the string descriptor index and langid is the Language
    ID of the descriptor. If langid is omitted, the string descriptor
    of the first Language ID will be returned.

    The return value is the unicode string present in the descriptor.
    """
    from usb.control import get_descriptor
    if langid is None:
	# Asking for the zero'th index is special - it returns a string
	# descriptor that contains all the language IDs supported by the device.
	# Typically there aren't many - often only one. The language IDs are 16
	# bit numbers, and they start at the third byte in the descriptor. See
	# USB 2.0 specification section 9.6.7 for more information.
        #
        # Note from libusb 1.0 sources (descriptor.c)
        buf = get_descriptor(
                    dev,
                    254,
                    DESC_TYPE_STRING,
                    0
                )
        assert len(buf) >= 4
        langid = buf[2] | (buf[3] << 8)

    buf = get_descriptor(
                dev,
                255, # Maximum descriptor size
                DESC_TYPE_STRING,
                index,
                langid
            )
    return buf[2:buf[0]].tostring().decode('utf-16-le')

########NEW FILE########
__FILENAME__ = _debug
# Copyright (C) 2009-2013 Wander Lairson Costa 
# 
# The following terms apply to all files associated
# with the software unless explicitly disclaimed in individual files.
# 
# The authors hereby grant permission to use, copy, modify, distribute,
# and license this software and its documentation for any purpose, provided
# that existing copyright notices are retained in all copies and that this
# notice is included verbatim in any distributions. No written agreement,
# license, or royalty fee is required for any of the authorized uses.
# Modifications to this software may be copyrighted by their authors
# and need not follow the licensing terms described here, provided that
# the new terms are clearly indicated on the first page of each file where
# they apply.
# 
# IN NO EVENT SHALL THE AUTHORS OR DISTRIBUTORS BE LIABLE TO ANY PARTY
# FOR DIRECT, INDIRECT, SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES
# ARISING OUT OF THE USE OF THIS SOFTWARE, ITS DOCUMENTATION, OR ANY
# DERIVATIVES THEREOF, EVEN IF THE AUTHORS HAVE BEEN ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
# 
# THE AUTHORS AND DISTRIBUTORS SPECIFICALLY DISCLAIM ANY WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.  THIS SOFTWARE
# IS PROVIDED ON AN "AS IS" BASIS, AND THE AUTHORS AND DISTRIBUTORS HAVE
# NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES, ENHANCEMENTS, OR
# MODIFICATIONS.

__author__ = 'Wander Lairson Costa'

__all__ = ['methodtrace', 'functiontrace']

import logging
import usb._interop as _interop

_enable_tracing = False

def enable_tracing(enable):
    global _enable_tracing
    _enable_tracing = enable

def _trace_function_call(logger, fname, *args, **named_args):
    logger.debug(
                # TODO: check if 'f' is a method or a free function
                fname + '(' + \
                ', '.join((str(val) for val in args)) + \
                ', '.join((name + '=' + str(val) for name, val in named_args.items())) + ')'
            )

# decorator for methods calls tracing
def methodtrace(logger):
    def decorator_logging(f):
        if not _enable_tracing:
            return f
        def do_trace(*args, **named_args):
            # this if is just a optimization to avoid unecessary string formatting
            if logging.DEBUG >= logger.getEffectiveLevel():
                fn = type(args[0]).__name__ + '.' + f.__name__
                _trace_function_call(logger, fn, *args[1:], **named_args)
            return f(*args, **named_args)
        _interop._update_wrapper(do_trace, f)
        return do_trace
    return decorator_logging

# decorator for methods calls tracing
def functiontrace(logger):
    def decorator_logging(f):
        if not _enable_tracing:
            return f
        def do_trace(*args, **named_args):
            # this if is just a optimization to avoid unecessary string formatting
            if logging.DEBUG >= logger.getEffectiveLevel():
                _trace_function_call(logger, f.__name__, *args, **named_args)
            return f(*args, **named_args)
        _interop._update_wrapper(do_trace, f)
        return do_trace
    return decorator_logging

########NEW FILE########
__FILENAME__ = _interop
# Copyright (C) 2009-2013 Wander Lairson Costa
#
# The following terms apply to all files associated
# with the software unless explicitly disclaimed in individual files.
#
# The authors hereby grant permission to use, copy, modify, distribute,
# and license this software and its documentation for any purpose, provided
# that existing copyright notices are retained in all copies and that this
# notice is included verbatim in any distributions. No written agreement,
# license, or royalty fee is required for any of the authorized uses.
# Modifications to this software may be copyrighted by their authors
# and need not follow the licensing terms described here, provided that
# the new terms are clearly indicated on the first page of each file where
# they apply.
#
# IN NO EVENT SHALL THE AUTHORS OR DISTRIBUTORS BE LIABLE TO ANY PARTY
# FOR DIRECT, INDIRECT, SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES
# ARISING OUT OF THE USE OF THIS SOFTWARE, ITS DOCUMENTATION, OR ANY
# DERIVATIVES THEREOF, EVEN IF THE AUTHORS HAVE BEEN ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# THE AUTHORS AND DISTRIBUTORS SPECIFICALLY DISCLAIM ANY WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.  THIS SOFTWARE
# IS PROVIDED ON AN "AS IS" BASIS, AND THE AUTHORS AND DISTRIBUTORS HAVE
# NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES, ENHANCEMENTS, OR
# MODIFICATIONS.

# All the hacks necessary to assure compatibility across all
# supported versions come here.
# Please, note that there is one version check for each
# hack we need to do, this makes maintenance easier... ^^

import sys
import array

__all__ = ['_reduce', '_set', '_next', '_groupby', '_sorted', '_update_wrapper']

# we support Python >= 2.3
assert sys.hexversion >= 0x020300f0

# On Python 3, reduce became a functools module function
try:
    import functools
    _reduce = functools.reduce
except (ImportError, AttributeError):
    _reduce = reduce

# we only have the builtin set type since 2.5 version
try:
    _set = set
except NameError:
    import sets
    _set = sets.Set

# On Python >= 2.6, we have the builtin next() function
# On Python 2.5 and before, we have to call the iterator method next()
def _next(iter):
    try:
        return next(iter)
    except NameError:
        return iter.next()

# groupby is available only since 2.4 version
try:
    import itertools
    _groupby = itertools.groupby
except (ImportError, AttributeError):
    # stolen from Python docs
    class _groupby(object):
        # [k for k, g in groupby('AAAABBBCCDAABBB')] --> A B C D A B
        # [list(g) for k, g in groupby('AAAABBBCCD')] --> AAAA BBB CC D
        def __init__(self, iterable, key=None):
            if key is None:
                key = lambda x: x
            self.keyfunc = key
            self.it = iter(iterable)
            self.tgtkey = self.currkey = self.currvalue = object()
        def __iter__(self):
            return self
        def next(self):
            while self.currkey == self.tgtkey:
                self.currvalue = _next(self.it)    # Exit on StopIteration
                self.currkey = self.keyfunc(self.currvalue)
            self.tgtkey = self.currkey
            return (self.currkey, self._grouper(self.tgtkey))
        def _grouper(self, tgtkey):
            while self.currkey == tgtkey:
                yield self.currvalue
                self.currvalue = _next(self.it)    # Exit on StopIteration
                self.currkey = self.keyfunc(self.currvalue)

# builtin sorted function is only availale since 2.4 version
try:
    _sorted = sorted
except NameError:
    def _sorted(l, key=None, reverse=False):
        # sort function on Python 2.3 does not
        # support 'key' parameter
        class KeyToCmp(object):
            def __init__(self, K):
                self.key = K
            def __call__(self, x, y):
                kx = self.key(x)
                ky = self.key(y)
                if kx < ky:
                    return reverse and 1 or -1
                elif kx > ky:
                    return reverse and -1 or 1
                else:
                    return 0
        tmp = list(l)
        tmp.sort(KeyToCmp(key))
        return tmp

try:
    import functools
    _update_wrapper = functools.update_wrapper
except (ImportError, AttributeError):
    def _update_wrapper(wrapper, wrapped):
        wrapper.__name__ = wrapped.__name__
        wrapper.__module__ = wrapped.__module__
        wrapper.__doc__ = wrapped.__doc__
        wrapper.__dict__ = wrapped.__dict__

def as_array(data=None):
    if data is None:
        return array.array('B')

    if isinstance(data, array.array):
        return data

    try:
        return array.array('B', data)
    except TypeError:
        # When you pass a unicode string or a character sequence,
        # you get a TypeError if the first parameter does not match
        a = array.array('B')
        a.fromstring(data)
        return a


########NEW FILE########
