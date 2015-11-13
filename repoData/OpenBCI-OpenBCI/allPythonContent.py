__FILENAME__ = hardware
"""
Hardware abstraction model.

Implemented with Traits for easy UI integration, but also accessible programmatically.
(programmatic access will require simulation of the event loop by calling the
data polling function periodically.)

To use serial port directly:
python.exe -m serial.tools.miniterm COM15 230400
"""

# Standard imports
import serial, time
import struct
import logging
import numpy as np

# Enthought imports
import traits.api as t
from pyface.timer.api import do_after

# Custom parameters.
COM_SEARCH_START = 13
COM_SEARCH_END = 15
BAUD = 115200  # * 2
STARTUP_TIMEOUT = 3  # seconds; initial timeout
RUN_TIMEOUT = 1  # seconds; timeout to use once running.
READ_INTERVAL_MS = 250

START_BYTE = bytes(0xA0)  # start of data packet
END_BYTE = bytes(0xC0)  # end of data packet

TIMESERIES_LENGTH = 4500
MIN_HISTORY_LENGTH = 4500
MAX_HISTORY_LENGTH = 65000

# Hardware/Calibration parameters. ###########
gain_fac = 24.0
full_scale_V = 4.5 / gain_fac
correction_factor = 2.0  # Need to revisit why we need this factor, but based on
                        # physical measurements, it is necessary
creare_volts_per_count = full_scale_V / (2.0 ** 24) * correction_factor
creare_volts_per_FS = creare_volts_per_count * 2 ** (24 - 1)  # per full scale: +/- 1.0
#############################

SAMPLE_RATE = 250.0  # Hz
CHANNELS = 8

i_sample = 0

class EEGSensor(t.HasTraits):
    preferences = t.Any()
    connected = t.Bool(False)
    serial_port = t.Instance(serial.Serial)

    com_port = t.Int()  # If None, we just search for it.
    def _com_port_default(self):
        """ Get default com port from preferences. """
        if self.preferences:
            return int(self.preferences.get('sensor.com_port', COM_SEARCH_START))
        return t.undefined
    def _com_port_changed(self, val):
        """ Save any COM port changes to preferences. """
        if self.preferences:
            return self.preferences.set('sensor.com_port', val)

    channels = t.Int(CHANNELS)
    timeseries = t.Array(dtype='float', value=np.zeros([1, CHANNELS + 1]))
    history = t.List()
    data_changed = t.Event()

    # Below, these separate properties and buttons for each channel are a bit
    #  verbose, but it seems to be the most clear way to implement this.
    channel_1_enabled = t.Bool(False)
    channel_2_enabled = t.Bool(False)
    channel_3_enabled = t.Bool(False)
    channel_4_enabled = t.Bool(False)
    channel_5_enabled = t.Bool(False)
    channel_6_enabled = t.Bool(False)
    channel_7_enabled = t.Bool(False)
    channel_8_enabled = t.Bool(False)

    channel_1_on = t.Button()
    channel_2_on = t.Button()
    channel_3_on = t.Button()
    channel_4_on = t.Button()
    channel_5_on = t.Button()
    channel_6_on = t.Button()
    channel_7_on = t.Button()
    channel_8_on = t.Button()

    channel_1_off = t.Button()
    channel_2_off = t.Button()
    channel_3_off = t.Button()
    channel_4_off = t.Button()
    channel_5_off = t.Button()
    channel_6_off = t.Button()
    channel_7_off = t.Button()
    channel_8_off = t.Button()

    # Properties
    history_length = t.Property(t.Int, depends_on="data_changed")
    def _get_history_length(self): return len(self.history)

    timeseries_length = t.Property(t.Int, depends_on="data_changed")
    def _get_timeseries_length(self): return self.timeseries.shape[0]



    @t.on_trait_change(','.join(['channel_%d_on' % i for i in range(1, 9)] +
                                ['channel_%d_off' % i for i in range(1, 9)]))
    def toggle_channels(self, name, new):
        if not self.connected:
            return
        deactivate_codes = ['1', '2', '3', '4', '5', '6', '7', '8']
        activate_codes = ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i']
        if name.endswith('_off'):
            cmd = deactivate_codes[int(name[-len('_off') - 1]) - 1]
        elif name.endswith('_on'):
            cmd = activate_codes[int(name[-len('_on') - 1]) - 1]
        else:
            raise ValueError()
        self.serial_port.write(cmd + '\n')
        # self.serial_port.write('b\n')
        time.sleep(.100)
        # self.serial_port.flushInput()
        # time.sleep(.50)


    def connect(self):
        if self.connected:
            self.disconnect()

        assert self.serial_port is None

        # If no com port is selected, search for it... this search code could
        #  be drastically sped up by analyzing a listing of actual COM ports.
        try:
            if self.com_port is None:
                for i in range(COM_SEARCH_START, COM_SEARCH_END + 1):
                    try:
                        port = 'COM%d' % i
                        self.serial_port = serial.Serial(port, BAUD, timeout=STARTUP_TIMEOUT)
                        if self.serial_port.read(1) == '':
                            self.serial_port.close()
                            self.serial_port = None
                            continue
                        else:
                            # Assume it's the right one...
                            self.serial_port.write('s\n')  # Reset.
                            self.serial_port.write('b\n')  # Start sending binary.
                            self.serial_port.read(5)  # Make sure we can read something
                            # Okay, we're convinced.
                            self.com_port = i
                            self.connected = True
                            self.serial_port.timeout = RUN_TIMEOUT
                            break
                    except serial.SerialException, e:
                        logging.warn("Couldn't open %s: %s" % (port, str(e)))
                else:
                    logging.warn("Couldn't find a functioning serial port." % (port, str(e)))

            else:  # A specific COM port is requested.
                port = 'COM%d' % self.com_port
                try:
                    self.serial_port = serial.Serial(port, BAUD, timeout=STARTUP_TIMEOUT)
                    if self.serial_port.read(1) == '':
                        self.serial_port.close()
                        self.serial_port = None
                        logging.warn('Could not read from serial port...')
                    else:
                        # Assume it's the right one...
                        self.connected = True
                        self.serial_port.timeout = RUN_TIMEOUT
                        self.serial_port.write('s\n')  # Reset.
                        self.serial_port.write('b\n')  # Start sending binary.
                        self.serial_port.read(5)  # Make sure we can read something
                        # Okay, we're convinced.

                except serial.SerialException, e:
                    self.disconnect()
                    logging.warn("Couldn't open %s: %s" % (port, str(e)))
        finally:
            if self.connected:
                self.read_input_continuously()
            else:
                self.disconnect()

    def disconnect(self):
        try:
            if self.serial_port is not None:
                self.serial_port.close()
        finally:
            self.serial_port = None
            self.connected = False

    def _read_mock_data(self, *args, **kwargs):
        """ Make synthetic noise in units of microvolts, for debugging
        purposes. """

        fs_Hz = 250  # Sample rate, Hz
        Nchan = 8  # How many channels of EEG
        Nsamples = 1  # How many samples do you want?
        foo_data = np.random.randn(Nchan)  # Gaussian noise with rms = 1.0
        data_uV = foo_data * np.sqrt(fs_Hz / 2.0)  # scale data to have RMS of 1.0 uV/sqrt(Hz)

        # The Arduino is outputting the ADS1299 as signed integers in 'counts'
        # so we need to convert microvolts to 'counts'

        # full scale at the ADS1299's internal ADC is [0 4.5] volts
        # ADS1299 set to have gain of x24 gain before ADC
        # ADS1299 issues 24-bit data from ADC, so there are 2^24 'counts'
        scale_V_per_count = 4.5 / 24 / (2 ** 24)
        data_counts = np.round((data_uV / 1e6) / scale_V_per_count)  # should be in counts [-2^23 to +2^23]
        return np.array(data_counts) / (2. ** (24 - 1))

    def _read_serial_binary(self, max_bytes_to_skip=3000):
        """
        Returns (and waits if necessary) for the next binary packet. The
        packet is returned as an array [sample_index, data1, data2, ... datan].
        
        RAISES
        ------
        RuntimeError : if it has to skip to many bytes.
        
        serial.SerialTimeoutException : if there isn't enough data to read.
        """
        global i_sample
        def read(n):
            val = self.serial_port.read(n)
            # print bytes(val),
            return val

        n_int_32 = self.channels + 1

        # Look for end of packet.
        for i in xrange(max_bytes_to_skip):
            val = read(1)
            if not val:
                if not self.serial_port.inWaiting():
                    logging.warn('Device appears to be stalled. Restarting...')
                    self.serial_port.write('b\n')  # restart if it's stopped...
                    time.sleep(.100)
                    continue
            # self.serial_port.write('b\n') , s , x
            # self.serial_port.inWaiting()
            if bytes(struct.unpack('B', val)[0]) == END_BYTE:
                # Look for the beginning of the packet, which should be next
                val = read(1)
                if bytes(struct.unpack('B', val)[0]) == START_BYTE:
                    if i > 0:
                        logging.warn("Had to skip %d bytes before finding stop/start bytes." % i)
                    # Read the number of bytes
                    val = read(1)
                    n_bytes = struct.unpack('B', val)[0]
                    if n_bytes == n_int_32 * 4:
                        # Read the rest of the packet.
                        val = read(4)
                        sample_index = struct.unpack('i', val)[0]
#                         if sample_index != 0:
#                             logging.warn("WARNING: sample_index should be zero, but sample_index == %d" % sample_index)
                        # NOTE: using i_sample, a surrogate sample count.
                        t_value = i_sample / float(SAMPLE_RATE)  # sample_index / float(SAMPLE_RATE)
                        i_sample += 1
                        val = read(4 * (n_int_32 - 1))
                        data = struct.unpack('i' * (n_int_32 - 1), val)
                        data = np.array(data) / (2. ** (24 - 1));  # make so full scale is +/- 1.0
                        # should set missing data to np.NAN here, maybe by testing for zeros..
                        # data[np.logical_not(self.channel_array)] = np.NAN  # set deactivated channels to NAN.
                        data[data == 0] = np.NAN
                        # print data
                        return np.concatenate([[t_value], data])  # A list [sample_index, data1, data2, ... datan]
                    elif n_bytes > 0:
                        print "Warning: Message length is the wrong size! %d should be %d" % (n_bytes, n_int_32 * 4)
                        # Clear the buffer of those bytes.
                        _ = read(n_bytes)
                    else:
                        raise ValueError("Warning: Message length is the wrong size! %d should be %d" % (n_bytes, n_int_32 * 4))
        raise RuntimeError("Maximum number of bytes skipped looking for binary packet (%d)" % max_bytes_to_skip)

    def read_input_buffer(self):
        """
        Reads all binary data in input buffer to arrays. If there is new data
        available, it updates the timeseries array and fires a data_changed event.
        
        Returns
        -------
        True :
            if the device is functioning properly and data readout should continue, 
        False :
            if data readout should stop.
        """

        if not self.connected:
            return False

        data_changed = False

        # Read all the data...
        while self.serial_port.inWaiting() > (self.channels + 1 * 4 + 3):

            # New data is raw, as returned from the microprocessor, but scaled -1 -> +1.
            # Here, we scale it -> uV.
            new_data = self._read_serial_binary()

            ########## Uncomment this next line for debugging purposes. #######
            # new_data[1:] = self._read_mock_data()  # overwrites real data with mock data.

            # Now, we scale from -1 -> +1, to uV:
            new_data[1:] = new_data[1:] * creare_volts_per_FS * 1.0e6  # now uV.
            self.history.append(new_data)
            data_changed = True

        if data_changed:
            # If the history gets too long, cull it:
            if len(self.history) > MAX_HISTORY_LENGTH:
                self.history = self.history[-MIN_HISTORY_LENGTH:]

            # Update the numpy timeseries array.
            self.timeseries = np.array(self.history[-TIMESERIES_LENGTH:])

            # Infer which channels are on/off... we don't keep track of this
            #  internally b/c it's safer to infer it from the Arduino output.
            [self.channel_1_enabled,
             self.channel_2_enabled,
             self.channel_3_enabled,
             self.channel_4_enabled,
             self.channel_5_enabled,
             self.channel_6_enabled,
             self.channel_7_enabled,
             self.channel_8_enabled] = np.logical_not(np.isnan(self.history[-1][1:])).tolist()
            self.data_changed = True  # fire data_changed event.

        return True

    def read_input_continuously(self):
        """ Polling function. This polls for any new data once every 
        READ_INTERVAL_MS milliseconds. If there's an error, it stops polling.
        """
        if self.read_input_buffer():
            do_after(READ_INTERVAL_MS, self.read_input_continuously)








########NEW FILE########
__FILENAME__ = mpl
""" Provides a TraitsUI/PyQT compatible Matplotlib Figure that uses a dark
style compatible with the 'qdarkstyle' package. """

# Standard imports
import matplotlib
matplotlib.use('Qt4Agg')
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas

# Enthought imports
from traitsui.qt4.editor import Editor
from traitsui.qt4.basic_editor_factory import BasicEditorFactory

# This code is inspired by the MPLTOOLS package, see
# https://github.com/tonysyu/mpltools for more info.
matplotlib.rcParams['lines.color'] = 'white'
matplotlib.rcParams['patch.edgecolor'] = 'white'

matplotlib.rcParams['text.color'] = 'white'

matplotlib.rcParams['axes.facecolor'] = 'black'
matplotlib.rcParams['axes.edgecolor'] = 'white'
matplotlib.rcParams['axes.labelcolor'] = 'white'
matplotlib.rcParams['axes.color_cycle'] = ['#8dd3c7', '#feffb3', '#bfbbd9', '#fa8174', '#81b1d2', '#fdb462', '#b3de69', '#bc82bd', '#ccebc4', '#ffed6f']

matplotlib.rcParams['xtick.color'] = 'white'
matplotlib.rcParams['ytick.color'] = 'white'

matplotlib.rcParams['grid.color'] = 'white'

matplotlib.rcParams['figure.facecolor'] = 'black'
matplotlib.rcParams['figure.edgecolor'] = 'black'

matplotlib.rcParams['savefig.facecolor'] = 'black'
matplotlib.rcParams['savefig.edgecolor'] = 'black'


# To match the qdarkstyle qss
matplotlib.rcParams['figure.facecolor'] = '#302F2F'
matplotlib.rcParams['axes.edgecolor'] = '#3A3939'
matplotlib.rcParams['text.color'] = 'silver'
matplotlib.rcParams['lines.linewidth'] = 2.0
matplotlib.rcParams['lines.solid_joinstyle'] = 'round'
matplotlib.rcParams['lines.solid_capstyle'] = 'round'
# matplotlib.rcParams['ytick.color'] = '#00ff00'
# matplotlib.rcParams['xtick.color'] = '#0ED5D5'
# matplotlib.rcParams['axes.labelcolor'] = '#0ED5D5'
matplotlib.rcParams['axes.facecolor'] = '#201F1F'
matplotlib.rcParams['grid.color'] = '#3A3939'
matplotlib.rcParams['grid.linestyle'] = '-'
matplotlib.rcParams['lines.markeredgewidth'] = 0.0


class _MPLFigureEditor(Editor):

    scrollable = True

    def init(self, parent):
        self.control = self._create_canvas(parent)
        self.set_tooltip()

    def update_editor(self):
        pass

    def _create_canvas(self, parent):
        """ Create the MPL canvas. """
        # matplotlib commands to create a canvas
        mpl_canvas = FigureCanvas(self.value)
        return mpl_canvas

class MPLFigureEditor(BasicEditorFactory):
    klass = _MPLFigureEditor

########NEW FILE########
__FILENAME__ = compile_qrc
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# QDarkStyle - A dark style sheet for Qt applications
#
# Copyright 2012, 2013 Colin Duquesnoy <colin.duquesnoy@gmail.com>
#
# This software is released under the LGPLv3 license.
# You should have received a copy of the GNU Lesser General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
"""
Utility scripts to compile the qrc file. The script will
attempt to compile the qrc file using the following tools:
    - rcc
    - pyside-rcc
    - pyrcc4

Delete the compiled files that you don't want to use 
manually after running this script.
"""
import os


def compile_all():
    """
    Compile style.qrc using rcc, pyside-rcc and pyrcc4
    """
    print("Compiling for Qt: style.qrc -> style.rcc")
    os.system("rcc style.qrc -o style.rcc")
    print("Compiling for PyQt4: style.qrc -> pyqt_style_rc.py")
    os.system("pyrcc4 style.qrc -o pyqt_style_rc.py")
    print("Compiling for PySide: style.qrc -> pyside_style_rc.py")
    os.system("pyside-rcc style.qrc -o pyside_style_rc.py")


if __name__ == "__main__":
    compile_all()

########NEW FILE########
__FILENAME__ = pyqt_style_rc
# -*- coding: utf-8 -*-

# Resource object code
#
# Created: Sun Mar 10 16:49:56 2013
#      by: The Resource Compiler for PyQt (Qt v4.8.2)
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore

qt_resource_data = "\
\x00\x00\x00\x96\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x09\x00\x00\x00\x06\x08\x04\x00\x00\x00\xbb\xce\x7c\x4e\
\x00\x00\x00\x02\x62\x4b\x47\x44\x00\xd3\xb5\x57\xa0\x5c\x00\x00\
\x00\x09\x70\x48\x59\x73\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\
\x9a\x9c\x18\x00\x00\x00\x07\x74\x49\x4d\x45\x07\xdc\x0b\x07\x0c\
\x0d\x1b\x75\xfe\x31\x99\x00\x00\x00\x27\x49\x44\x41\x54\x08\xd7\
\x65\x8c\xb1\x0d\x00\x00\x08\x83\xe0\xff\xa3\x75\x70\xb1\xca\xd4\
\x90\x50\x78\x08\x55\x21\x14\xb6\x54\x70\xe6\x48\x8d\x87\xcc\x0f\
\x0d\xe0\xf0\x08\x02\x34\xe2\x2b\xa7\x00\x00\x00\x00\x49\x45\x4e\
\x44\xae\x42\x60\x82\
\x00\x00\x02\x71\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x20\x00\x00\x00\x20\x08\x06\x00\x00\x00\x73\x7a\x7a\xf4\
\x00\x00\x00\x01\x73\x52\x47\x42\x00\xae\xce\x1c\xe9\x00\x00\x00\
\x06\x62\x4b\x47\x44\x00\xff\x00\xff\x00\xff\xa0\xbd\xa7\x93\x00\
\x00\x00\x09\x70\x48\x59\x73\x00\x00\x0e\xc4\x00\x00\x0e\xc4\x01\
\x95\x2b\x0e\x1b\x00\x00\x00\x07\x74\x49\x4d\x45\x07\xdc\x08\x17\
\x0b\x01\x28\x74\x6d\x24\x49\x00\x00\x01\xf1\x49\x44\x41\x54\x58\
\xc3\xcd\x57\x41\x4e\x02\x31\x14\xfd\xfd\xb5\x6e\x70\x21\x89\xb8\
\x11\x8d\x89\x5b\xef\x80\x3b\xb7\xde\x80\x36\x70\x2c\xa0\xbd\x86\
\x3b\xc2\x19\xd8\xb9\x21\x11\x13\x23\x0b\x4d\x94\x49\xb4\x69\xeb\
\xc6\xea\xa4\x61\x86\xb6\x40\xf0\xef\xc8\xd0\x79\x7d\xef\xbf\x79\
\xed\x07\xd8\x73\x91\xaa\x07\x4a\xa9\x57\x00\x00\xe7\xdc\x52\x08\
\xd1\xce\x79\xb9\x94\x72\x4e\x08\x69\x00\x00\x70\xce\x9b\x51\x1b\
\x18\x0c\x06\x53\xc6\xd8\xa5\x5f\x08\x00\x60\xad\x5d\x70\xce\x4f\
\x53\xc0\x95\x52\x2f\x88\xd8\xf2\xbf\x9d\x73\x4b\xad\xf5\xac\xdf\
\xef\x5f\x97\xff\x87\xe1\xc2\x10\x1c\x00\x00\x11\x5b\x52\xca\x79\
\x0a\xf3\x32\x38\x00\x00\x21\xa4\xc1\x18\xbb\xac\x54\x60\x15\xf3\
\xb0\xb4\xd6\xf3\x5e\xaf\x77\x5e\x07\x3e\x1c\x0e\x1f\x19\x63\x95\
\x2d\x0b\x95\xc0\x3a\xe6\x61\x51\x4a\x6b\x95\x90\x52\xce\x29\xa5\
\xad\x5a\xd3\x05\x4a\x10\x6f\x38\x44\x3c\x8e\x95\x78\x95\x27\xc2\
\x9e\x47\xbc\xe3\x8d\x73\xde\xc4\x1c\x77\x87\x9e\x58\xd5\xf3\xd8\
\x3a\xf0\x7d\x01\x80\xe3\x94\x85\x94\xd2\x33\xa5\xd4\x8b\xdf\x50\
\x2a\xf0\x0f\xe6\x9f\x09\x53\x25\xdc\xa4\xca\x2d\xfc\x6d\x01\xe7\
\xfc\xd4\x18\xf3\xb4\x6b\x70\x63\xcc\x53\xd9\x3f\x64\x5d\x80\xec\
\x8a\x79\x65\x10\xed\x4a\x89\x90\x79\xcc\x59\xb0\x35\x25\xea\xa2\
\xbc\xf2\x33\xdc\x96\x12\x55\xcc\xd7\x2a\xb0\x0d\x25\x62\x0e\x31\
\x84\x3d\x17\xa6\x9e\x6a\x9b\x24\x66\xea\x85\x64\x7f\x26\xdc\x94\
\x79\x8a\x12\xff\x2b\x88\xb6\xcd\x3c\x46\x89\xff\x71\x18\xe5\x32\
\xb7\xd6\x2e\xac\xb5\x8b\x4d\x94\x40\x7f\x4d\xca\x4d\xb8\xdc\xc4\
\xf4\x98\x98\x2b\x61\x79\x56\x10\x42\xb4\x73\x94\xf8\xdd\x00\xe7\
\xbc\xe9\x6f\x28\xb9\xd9\x9e\xa2\x84\x73\x6e\xe9\x07\x15\x2c\x5d\
\xb9\x67\xeb\x36\x11\x32\x0f\x4b\x08\xd1\x36\xc6\x3c\x03\x80\xad\
\x21\xf0\xa1\xb5\x9e\x55\xe6\x80\x94\xf2\x1d\x11\x1b\x84\x10\x52\
\x02\xfe\x72\xce\xdd\x0a\x21\xc6\x91\x83\xc9\x0d\x21\xe4\x1e\x11\
\x0f\x43\xe6\xdd\x6e\xf7\xa8\x36\x09\xa7\xd3\xe9\x95\xb5\x76\x59\
\x02\xff\x2c\x8a\xe2\x2e\x16\xfc\x47\x89\x71\x51\x14\x77\xd6\xda\
\xcf\x70\x20\x49\x1e\x4e\x27\x93\xc9\xc5\x68\x34\x7a\xcf\x31\x58\
\xa7\xd3\x39\x11\x42\x3c\xd4\x0d\xa7\x7b\xaf\x6f\x1a\x2b\x5a\x88\
\xa9\x6c\x88\x2e\x00\x00\x00\x00\x49\x45\x4e\x44\xae\x42\x60\x82\
\
\x00\x00\x00\x93\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x06\x00\x00\x00\x09\x08\x04\x00\x00\x00\xbb\x93\x95\x16\
\x00\x00\x00\x02\x62\x4b\x47\x44\x00\xd3\xb5\x57\xa0\x5c\x00\x00\
\x00\x09\x70\x48\x59\x73\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\
\x9a\x9c\x18\x00\x00\x00\x07\x74\x49\x4d\x45\x07\xdc\x0b\x07\x0c\
\x0c\x2b\x4a\x3c\x30\x74\x00\x00\x00\x24\x49\x44\x41\x54\x08\xd7\
\x63\x60\x40\x05\xff\xff\xc3\x58\x4c\xc8\x5c\x26\x64\x59\x26\x64\
\xc5\x70\x0e\x23\x23\x9c\xc3\xc8\x88\x61\x1a\x0a\x00\x00\x9e\x14\
\x0a\x05\x2b\xca\xe5\x75\x00\x00\x00\x00\x49\x45\x4e\x44\xae\x42\
\x60\x82\
\x00\x00\x00\xa0\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x06\x00\x00\x00\x09\x08\x04\x00\x00\x00\xbb\x93\x95\x16\
\x00\x00\x00\x01\x73\x52\x47\x42\x00\xae\xce\x1c\xe9\x00\x00\x00\
\x02\x62\x4b\x47\x44\x00\xff\x87\x8f\xcc\xbf\x00\x00\x00\x09\x70\
\x48\x59\x73\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\
\x00\x00\x00\x07\x74\x49\x4d\x45\x07\xdc\x08\x17\x14\x1f\x0d\xfc\
\x52\x2b\x9c\x00\x00\x00\x24\x49\x44\x41\x54\x08\xd7\x63\x60\x40\
\x05\x73\x3e\xc0\x58\x4c\xc8\x5c\x26\x64\x59\x26\x64\xc5\x70\x4e\
\x8a\x00\x9c\x93\x22\x80\x61\x1a\x0a\x00\x00\x29\x95\x08\xaf\x88\
\xac\xba\x34\x00\x00\x00\x00\x49\x45\x4e\x44\xae\x42\x60\x82\
\x00\x00\x00\xce\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x07\x00\x00\x00\x3f\x08\x06\x00\x00\x00\x2c\x7b\xd2\x13\
\x00\x00\x00\x01\x73\x52\x47\x42\x00\xae\xce\x1c\xe9\x00\x00\x00\
\x06\x62\x4b\x47\x44\x00\xff\x00\xff\x00\xff\xa0\xbd\xa7\x93\x00\
\x00\x00\x09\x70\x48\x59\x73\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\
\x00\x9a\x9c\x18\x00\x00\x00\x07\x74\x49\x4d\x45\x07\xdc\x08\x17\
\x09\x2f\x07\xd7\x3f\xc4\x52\x00\x00\x00\x4e\x49\x44\x41\x54\x38\
\xcb\x63\x60\x18\x36\x80\x19\xc6\xa8\x6f\x9f\xca\xe0\xe0\xe2\xcd\
\xf0\xea\xe5\x73\x86\x37\xaf\x5e\x30\x30\x30\x30\x30\x30\xe1\xd3\
\x39\x2a\x49\x48\x92\x05\x89\xfd\x1f\x89\xcd\x38\x1a\x42\xa3\x92\
\x83\x27\x69\x32\x8e\x86\x10\xa9\x92\xf0\x20\xd3\xd4\x31\x84\x0b\
\x5e\xbf\x72\x9e\x61\x14\x40\x01\x00\x13\x4d\x0c\x46\x89\x2a\x0a\
\x20\x00\x00\x00\x00\x49\x45\x4e\x44\xae\x42\x60\x82\
\x00\x00\x00\xb6\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x18\x00\x00\x00\x11\x08\x06\x00\x00\x00\xc7\x78\x6c\x30\
\x00\x00\x00\x01\x73\x52\x47\x42\x00\xae\xce\x1c\xe9\x00\x00\x00\
\x06\x62\x4b\x47\x44\x00\xff\x00\xff\x00\xff\xa0\xbd\xa7\x93\x00\
\x00\x00\x09\x70\x48\x59\x73\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\
\x00\x9a\x9c\x18\x00\x00\x00\x07\x74\x49\x4d\x45\x07\xdc\x08\x17\
\x0b\x2c\x0d\x1f\x43\xaa\xe1\x00\x00\x00\x36\x49\x44\x41\x54\x38\
\xcb\x63\x60\x20\x01\x2c\x5a\xb4\xe8\xff\xa2\x45\x8b\xfe\x93\xa2\
\x87\x89\x81\xc6\x60\xd4\x82\x11\x60\x01\x23\xa9\xc9\x74\xd0\xf9\
\x80\x85\x1c\x4d\x71\x71\x71\x8c\xa3\xa9\x68\xd4\x82\x61\x64\x01\
\x00\x31\xb5\x09\xec\x1f\x4b\xb4\x15\x00\x00\x00\x00\x49\x45\x4e\
\x44\xae\x42\x60\x82\
\x00\x00\x00\xa6\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x06\x00\x00\x00\x09\x08\x04\x00\x00\x00\xbb\x93\x95\x16\
\x00\x00\x00\x01\x73\x52\x47\x42\x00\xae\xce\x1c\xe9\x00\x00\x00\
\x02\x62\x4b\x47\x44\x00\xff\x87\x8f\xcc\xbf\x00\x00\x00\x09\x70\
\x48\x59\x73\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\
\x00\x00\x00\x07\x74\x49\x4d\x45\x07\xdc\x08\x17\x14\x1f\x20\xb9\
\x8d\x77\xe9\x00\x00\x00\x2a\x49\x44\x41\x54\x08\xd7\x63\x60\xc0\
\x06\xe6\x7c\x60\x60\x60\x42\x30\xa1\x1c\x08\x93\x81\x81\x09\xc1\
\x64\x60\x60\x62\x60\x48\x11\x40\xe2\x20\x73\x19\x90\x8d\x40\x02\
\x00\x23\xed\x08\xaf\x64\x9f\x0f\x15\x00\x00\x00\x00\x49\x45\x4e\
\x44\xae\x42\x60\x82\
\x00\x00\x00\xa6\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x09\x00\x00\x00\x06\x08\x04\x00\x00\x00\xbb\xce\x7c\x4e\
\x00\x00\x00\x01\x73\x52\x47\x42\x00\xae\xce\x1c\xe9\x00\x00\x00\
\x02\x62\x4b\x47\x44\x00\x9c\x53\x34\xfc\x5d\x00\x00\x00\x09\x70\
\x48\x59\x73\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\
\x00\x00\x00\x07\x74\x49\x4d\x45\x07\xdc\x08\x17\x0b\x1b\x0e\x16\
\x4d\x5b\x6f\x00\x00\x00\x2a\x49\x44\x41\x54\x08\xd7\x63\x60\xc0\
\x00\x8c\x0c\x0c\x73\x3e\x20\x0b\xa4\x08\x30\x32\x30\x20\x0b\xa6\
\x08\x30\x30\x30\x42\x98\x10\xc1\x14\x01\x14\x13\x50\xb5\xa3\x01\
\x00\xc6\xb9\x07\x90\x5d\x66\x1f\x83\x00\x00\x00\x00\x49\x45\x4e\
\x44\xae\x42\x60\x82\
\x00\x00\x00\xe1\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x0a\x00\x00\x00\x36\x08\x06\x00\x00\x00\xfe\x8a\x08\x6b\
\x00\x00\x00\x01\x73\x52\x47\x42\x00\xae\xce\x1c\xe9\x00\x00\x00\
\x06\x62\x4b\x47\x44\x00\xff\x00\xff\x00\xff\xa0\xbd\xa7\x93\x00\
\x00\x00\x09\x70\x48\x59\x73\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\
\x00\x9a\x9c\x18\x00\x00\x00\x07\x74\x49\x4d\x45\x07\xdc\x08\x17\
\x09\x33\x22\x7a\x4c\x4d\x48\x00\x00\x00\x61\x49\x44\x41\x54\x48\
\xc7\x63\xfc\xcf\x40\x1c\x60\x62\xa0\x99\x42\x63\x23\x23\x06\x63\
\x23\x23\x0c\x36\x1d\xac\x1e\x55\x38\xc8\x14\x32\xfe\x67\x60\x60\
\x68\x68\x9f\x8a\x33\x59\xae\x5a\x3a\x87\xe1\xda\x95\xf3\x8c\x34\
\xb2\x5a\x4b\xc7\x10\x6f\x8e\xb8\x76\xe5\x3c\x23\xe3\x7f\xa4\x84\
\xcb\xc0\xc0\xc0\x70\xf6\xdc\x39\x14\xf6\x68\x80\x8f\x06\xf8\x68\
\x80\x8f\x96\x66\x43\x27\x3d\x0e\x72\x37\x02\x00\x10\x30\x40\xb3\
\x35\xa0\x7c\x49\x00\x00\x00\x00\x49\x45\x4e\x44\xae\x42\x60\x82\
\
\x00\x00\x00\xa0\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x06\x00\x00\x00\x09\x08\x04\x00\x00\x00\xbb\x93\x95\x16\
\x00\x00\x00\x01\x73\x52\x47\x42\x00\xae\xce\x1c\xe9\x00\x00\x00\
\x02\x62\x4b\x47\x44\x00\xff\x87\x8f\xcc\xbf\x00\x00\x00\x09\x70\
\x48\x59\x73\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\
\x00\x00\x00\x07\x74\x49\x4d\x45\x07\xdc\x08\x17\x14\x1c\x1f\x24\
\xc6\x09\x17\x00\x00\x00\x24\x49\x44\x41\x54\x08\xd7\x63\x60\x40\
\x05\xff\xcf\xc3\x58\x4c\xc8\x5c\x26\x64\x59\x26\x64\xc5\x70\x0e\
\xa3\x21\x9c\xc3\x68\x88\x61\x1a\x0a\x00\x00\x6d\x84\x09\x75\x37\
\x9e\xd9\x23\x00\x00\x00\x00\x49\x45\x4e\x44\xae\x42\x60\x82\
\x00\x00\x00\xa6\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x09\x00\x00\x00\x06\x08\x04\x00\x00\x00\xbb\xce\x7c\x4e\
\x00\x00\x00\x01\x73\x52\x47\x42\x00\xae\xce\x1c\xe9\x00\x00\x00\
\x02\x62\x4b\x47\x44\x00\xff\x87\x8f\xcc\xbf\x00\x00\x00\x09\x70\
\x48\x59\x73\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\
\x00\x00\x00\x07\x74\x49\x4d\x45\x07\xdc\x08\x17\x08\x15\x3b\xdc\
\x3b\x0c\x9b\x00\x00\x00\x2a\x49\x44\x41\x54\x08\xd7\x63\x60\xc0\
\x00\x8c\x0c\x0c\x73\x3e\x20\x0b\xa4\x08\x30\x32\x30\x20\x0b\xa6\
\x08\x30\x30\x30\x42\x98\x10\xc1\x14\x01\x14\x13\x50\xb5\xa3\x01\
\x00\xc6\xb9\x07\x90\x5d\x66\x1f\x83\x00\x00\x00\x00\x49\x45\x4e\
\x44\xae\x42\x60\x82\
\x00\x00\x00\xe4\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x36\x00\x00\x00\x0a\x08\x06\x00\x00\x00\xff\xfd\xad\x0b\
\x00\x00\x00\x01\x73\x52\x47\x42\x00\xae\xce\x1c\xe9\x00\x00\x00\
\x06\x62\x4b\x47\x44\x00\x7f\x00\x87\x00\x95\xe6\xde\xa6\xaf\x00\
\x00\x00\x09\x70\x48\x59\x73\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\
\x00\x9a\x9c\x18\x00\x00\x00\x07\x74\x49\x4d\x45\x07\xdc\x08\x17\
\x09\x2a\x2b\x98\x90\x5c\xf4\x00\x00\x00\x64\x49\x44\x41\x54\x48\
\xc7\x63\xfc\xcf\x30\x3c\x01\x0b\xa5\x06\x34\xb4\x4f\x85\x87\xcd\
\xaa\xa5\x73\x18\xae\x5d\x39\xcf\x48\x2b\x35\x14\x79\xcc\xd8\xc8\
\x88\x24\x03\x7c\x89\xd0\x4f\x2d\x35\x84\xc0\xd9\x73\xe7\xe0\x6c\
\x26\x86\x91\x92\x14\x91\x7d\x4d\x54\x52\x0c\x4d\x26\xa8\x9f\x5a\
\x6a\x46\x93\xe2\x68\x52\x1c\x82\x49\x91\x91\xd2\x7a\x4c\x4b\xc7\
\x10\xc5\x08\x6c\xc5\x34\xb5\xd4\xd0\xd5\x63\x83\x15\x00\x00\x7a\
\x30\x4a\x09\x71\xea\x2d\x6e\x00\x00\x00\x00\x49\x45\x4e\x44\xae\
\x42\x60\x82\
\x00\x00\x00\xc3\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x40\x00\x00\x00\x40\x08\x06\x00\x00\x00\xaa\x69\x71\xde\
\x00\x00\x00\x06\x62\x4b\x47\x44\x00\xff\x00\xff\x00\xff\xa0\xbd\
\xa7\x93\x00\x00\x00\x09\x70\x48\x59\x73\x00\x00\x0b\x13\x00\x00\
\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x07\x74\x49\x4d\x45\x07\
\xdc\x0b\x07\x09\x2e\x37\xff\x44\xe8\xf0\x00\x00\x00\x1d\x69\x54\
\x58\x74\x43\x6f\x6d\x6d\x65\x6e\x74\x00\x00\x00\x00\x00\x43\x72\
\x65\x61\x74\x65\x64\x20\x77\x69\x74\x68\x20\x47\x49\x4d\x50\x64\
\x2e\x65\x07\x00\x00\x00\x27\x49\x44\x41\x54\x78\xda\xed\xc1\x01\
\x0d\x00\x00\x00\xc2\xa0\xf7\x4f\x6d\x0e\x37\xa0\x00\x00\x00\x00\
\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x80\x77\x03\x40\x40\
\x00\x01\xaf\x7a\x0e\xe8\x00\x00\x00\x00\x49\x45\x4e\x44\xae\x42\
\x60\x82\
\x00\x00\x00\xa5\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x09\x00\x00\x00\x06\x08\x04\x00\x00\x00\xbb\xce\x7c\x4e\
\x00\x00\x00\x01\x73\x52\x47\x42\x00\xae\xce\x1c\xe9\x00\x00\x00\
\x02\x62\x4b\x47\x44\x00\x9c\x53\x34\xfc\x5d\x00\x00\x00\x09\x70\
\x48\x59\x73\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\
\x00\x00\x00\x07\x74\x49\x4d\x45\x07\xdc\x08\x17\x0b\x02\x04\x6d\
\x98\x1b\x69\x00\x00\x00\x29\x49\x44\x41\x54\x08\xd7\x63\x60\xc0\
\x00\x8c\x0c\x0c\xff\xcf\xa3\x08\x18\x32\x32\x30\x20\x0b\x32\x1a\
\x32\x30\x30\x42\x98\x10\x41\x46\x43\x14\x13\x50\xb5\xa3\x01\x00\
\xd6\x10\x07\xd2\x2f\x48\xdf\x4a\x00\x00\x00\x00\x49\x45\x4e\x44\
\xae\x42\x60\x82\
\x00\x00\x00\xa0\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x06\x00\x00\x00\x09\x08\x04\x00\x00\x00\xbb\x93\x95\x16\
\x00\x00\x00\x01\x73\x52\x47\x42\x00\xae\xce\x1c\xe9\x00\x00\x00\
\x02\x62\x4b\x47\x44\x00\x9c\x53\x34\xfc\x5d\x00\x00\x00\x09\x70\
\x48\x59\x73\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\
\x00\x00\x00\x07\x74\x49\x4d\x45\x07\xdc\x08\x17\x0b\x1b\x29\xb3\
\x47\xee\x04\x00\x00\x00\x24\x49\x44\x41\x54\x08\xd7\x63\x60\x40\
\x05\x73\x3e\xc0\x58\x4c\xc8\x5c\x26\x64\x59\x26\x64\xc5\x70\x4e\
\x8a\x00\x9c\x93\x22\x80\x61\x1a\x0a\x00\x00\x29\x95\x08\xaf\x88\
\xac\xba\x34\x00\x00\x00\x00\x49\x45\x4e\x44\xae\x42\x60\x82\
\x00\x00\x01\xc8\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x20\x00\x00\x00\x20\x08\x06\x00\x00\x00\x73\x7a\x7a\xf4\
\x00\x00\x00\x01\x73\x52\x47\x42\x00\xae\xce\x1c\xe9\x00\x00\x00\
\x06\x62\x4b\x47\x44\x00\xff\x00\xff\x00\xff\xa0\xbd\xa7\x93\x00\
\x00\x00\x09\x70\x48\x59\x73\x00\x00\x0e\xc4\x00\x00\x0e\xc4\x01\
\x95\x2b\x0e\x1b\x00\x00\x00\x07\x74\x49\x4d\x45\x07\xdc\x08\x17\
\x0b\x03\x24\x4f\xed\x0a\xe0\x00\x00\x01\x48\x49\x44\x41\x54\x58\
\xc3\xed\x57\x41\x8e\x83\x30\x0c\xb4\x21\xd0\x3e\x10\x3f\x8e\x23\
\xe7\x20\xbe\xb3\x3f\xd9\x55\x03\x9b\xd9\x4b\x2a\x45\x10\x96\x24\
\x04\xf5\x82\xcf\x2e\x63\x4f\xc6\x63\x97\xe8\xc3\xc1\x57\x7c\x54\
\x6b\x6d\x98\xb9\x3a\xca\x03\xb0\xa8\x0b\x9b\xab\x23\x72\x7e\xab\
\x2b\x90\x45\xa4\x05\xb0\xc4\xe4\x56\x57\xb5\x2f\x22\x0d\x80\xf9\
\x28\x6f\xf3\x04\xe3\x38\x2e\x39\x80\x00\xac\x88\xb4\xa9\xbf\x53\
\x9e\x70\x7e\x98\xb9\xcd\x64\x65\x03\xae\xb5\x9e\x99\x59\x45\x3f\
\xc1\x19\x70\x00\x26\x30\x05\x2a\x9a\x01\x47\x7b\x16\x78\xd7\x75\
\x75\x42\xe7\x76\x8d\x73\x46\x84\xa9\x9d\x5b\x00\x66\x3d\x1d\xca\
\x5a\x4b\xd3\x34\xad\x05\x35\xa7\x0a\xea\xa8\x73\x9f\x29\x57\x68\
\x43\x44\x54\x0d\xc3\xf0\x05\x60\x23\xea\x0c\xe7\x53\xb1\x4c\x39\
\x9f\x30\x44\x64\xd9\xd3\x40\xed\x31\x60\x44\xe4\x51\xba\xf3\xe2\
\x46\x94\xda\x79\x94\x11\x15\x8a\xe0\x74\x38\xbf\x78\x14\x63\x60\
\xc7\xf3\x93\xa6\xe3\x34\x03\x22\xd2\x78\xaa\x4e\xf5\x85\x32\xcb\
\xe8\xad\xea\x1c\x47\x2c\xa6\x81\xd0\xd4\xc4\x1c\x25\x97\xad\xe3\
\xd8\xb8\x0b\xb8\x0b\xb8\x0b\xa8\x4a\xff\x61\xe9\xfb\xbe\x71\x26\
\xf4\x1d\x58\xf3\x71\x46\xc4\xcc\x2a\xf7\x3a\x76\xeb\x9d\x00\x44\
\x19\x91\x7a\x9f\xd4\xcc\x5c\xaf\x18\xa8\xcf\x50\xcb\xcc\xa1\x23\
\x07\xbb\x54\xc7\x9e\xd1\xb9\x01\xe0\x25\x22\xcf\x7f\xdf\xda\xbf\
\xd5\xca\x62\xc3\x84\xc0\x83\x62\xd3\x5a\xbf\x4a\x17\xb0\x07\x4e\
\x44\xf4\x07\xae\xf5\xd5\xa6\x1d\xd1\x22\x08\x00\x00\x00\x00\x49\
\x45\x4e\x44\xae\x42\x60\x82\
\x00\x00\x00\x9e\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x09\x00\x00\x00\x06\x08\x04\x00\x00\x00\xbb\xce\x7c\x4e\
\x00\x00\x00\x01\x73\x52\x47\x42\x00\xae\xce\x1c\xe9\x00\x00\x00\
\x02\x62\x4b\x47\x44\x00\xff\x87\x8f\xcc\xbf\x00\x00\x00\x09\x70\
\x48\x59\x73\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\
\x00\x00\x00\x07\x74\x49\x4d\x45\x07\xdc\x08\x17\x08\x15\x0f\xfd\
\x8f\xf8\x2e\x00\x00\x00\x22\x49\x44\x41\x54\x08\xd7\x63\x60\xc0\
\x0d\xfe\x9f\x87\xb1\x18\x91\x05\x18\x0d\xe1\x42\x48\x2a\x0c\x19\
\x18\x18\x91\x05\x10\x2a\xd1\x00\x00\xca\xb5\x07\xd2\x76\xbb\xb2\
\xc5\x00\x00\x00\x00\x49\x45\x4e\x44\xae\x42\x60\x82\
\x00\x00\x00\xbb\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x3f\x00\x00\x00\x07\x08\x06\x00\x00\x00\xbf\x76\x95\x1f\
\x00\x00\x00\x01\x73\x52\x47\x42\x00\xae\xce\x1c\xe9\x00\x00\x00\
\x06\x62\x4b\x47\x44\x00\xff\x00\xff\x00\xff\xa0\xbd\xa7\x93\x00\
\x00\x00\x09\x70\x48\x59\x73\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\
\x00\x9a\x9c\x18\x00\x00\x00\x07\x74\x49\x4d\x45\x07\xdc\x08\x17\
\x09\x35\x2b\x55\xca\x52\x6a\x00\x00\x00\x3b\x49\x44\x41\x54\x38\
\xcb\x63\x60\x18\x05\x23\x13\x30\x12\xa3\xa8\xbe\x7d\x2a\x25\x76\
\xfc\xa7\x97\x3b\xd1\xc1\xaa\xa5\x73\x18\xae\x5f\x39\x8f\x53\x9e\
\x69\x34\xe6\x09\x00\x4d\x1d\xc3\x21\x19\xf3\x0c\x0c\x0c\x78\x63\
\x7e\x14\x8c\x54\x00\x00\x69\x64\x0b\x05\xfd\x6b\x58\xca\x00\x00\
\x00\x00\x49\x45\x4e\x44\xae\x42\x60\x82\
\x00\x00\x00\x9f\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x09\x00\x00\x00\x06\x08\x04\x00\x00\x00\xbb\xce\x7c\x4e\
\x00\x00\x00\x01\x73\x52\x47\x42\x00\xae\xce\x1c\xe9\x00\x00\x00\
\x02\x62\x4b\x47\x44\x00\xff\x87\x8f\xcc\xbf\x00\x00\x00\x09\x70\
\x48\x59\x73\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\
\x00\x00\x00\x07\x74\x49\x4d\x45\x07\xdc\x08\x17\x08\x14\x1f\xf9\
\x23\xd9\x0b\x00\x00\x00\x23\x49\x44\x41\x54\x08\xd7\x63\x60\xc0\
\x0d\xe6\x7c\x80\xb1\x18\x91\x05\x52\x04\xe0\x42\x08\x15\x29\x02\
\x0c\x0c\x8c\xc8\x02\x08\x95\x68\x00\x00\xac\xac\x07\x90\x4e\x65\
\x34\xac\x00\x00\x00\x00\x49\x45\x4e\x44\xae\x42\x60\x82\
\x00\x00\x00\xef\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x51\x00\x00\x00\x3a\x08\x06\x00\x00\x00\xc8\xbc\xb5\xaf\
\x00\x00\x00\x01\x73\x52\x47\x42\x00\xae\xce\x1c\xe9\x00\x00\x00\
\x06\x62\x4b\x47\x44\x00\xff\x00\xff\x00\xff\xa0\xbd\xa7\x93\x00\
\x00\x00\x09\x70\x48\x59\x73\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\
\x00\x9a\x9c\x18\x00\x00\x00\x07\x74\x49\x4d\x45\x07\xdc\x08\x17\
\x0b\x2a\x32\xff\x7f\x20\x5a\x00\x00\x00\x6f\x49\x44\x41\x54\x78\
\xda\xed\xd0\xb1\x0d\x00\x30\x08\x03\x41\xc8\xa0\x0c\xc7\xa2\x49\
\xcf\x04\x28\xba\x2f\x5d\x59\x97\xb1\xb4\xee\xbe\x73\xab\xaa\xdc\
\xf8\xf5\x84\x20\x42\x84\x28\x88\x10\x21\x42\x14\x44\x88\x10\x21\
\x0a\x22\x44\x88\x10\x05\x11\x22\x44\x88\x82\x08\x11\x22\x44\x41\
\x84\x08\x51\x10\x21\x42\x84\x28\x88\x10\x21\x42\x14\x44\x88\x10\
\x21\x0a\x22\x44\x88\x10\x05\x11\x22\x44\x88\x82\x08\x11\x22\x44\
\x41\x84\x08\x51\x10\x21\x42\xfc\xaa\x07\x12\x55\x04\x74\x56\x9e\
\x9e\x54\x00\x00\x00\x00\x49\x45\x4e\x44\xae\x42\x60\x82\
\x00\x00\x00\xa6\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x06\x00\x00\x00\x09\x08\x04\x00\x00\x00\xbb\x93\x95\x16\
\x00\x00\x00\x01\x73\x52\x47\x42\x00\xae\xce\x1c\xe9\x00\x00\x00\
\x02\x62\x4b\x47\x44\x00\xff\x87\x8f\xcc\xbf\x00\x00\x00\x09\x70\
\x48\x59\x73\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\
\x00\x00\x00\x07\x74\x49\x4d\x45\x07\xdc\x08\x17\x14\x1d\x00\xb0\
\xd5\x35\xa3\x00\x00\x00\x2a\x49\x44\x41\x54\x08\xd7\x63\x60\xc0\
\x06\xfe\x9f\x67\x60\x60\x42\x30\xa1\x1c\x08\x93\x81\x81\x09\xc1\
\x64\x60\x60\x62\x60\x60\x34\x44\xe2\x20\x73\x19\x90\x8d\x40\x02\
\x00\x64\x40\x09\x75\x86\xb3\xad\x9c\x00\x00\x00\x00\x49\x45\x4e\
\x44\xae\x42\x60\x82\
\x00\x00\x00\xe0\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x51\x00\x00\x00\x3a\x08\x06\x00\x00\x00\xc8\xbc\xb5\xaf\
\x00\x00\x00\x01\x73\x52\x47\x42\x00\xae\xce\x1c\xe9\x00\x00\x00\
\x06\x62\x4b\x47\x44\x00\xff\x00\xff\x00\xff\xa0\xbd\xa7\x93\x00\
\x00\x00\x09\x70\x48\x59\x73\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\
\x00\x9a\x9c\x18\x00\x00\x00\x07\x74\x49\x4d\x45\x07\xdc\x08\x17\
\x0b\x29\x1c\x08\x84\x7e\x56\x00\x00\x00\x60\x49\x44\x41\x54\x78\
\xda\xed\xd9\xb1\x0d\x00\x20\x08\x00\x41\x71\x50\x86\x63\x51\xed\
\x8d\x85\x25\x89\x77\xa5\x15\xf9\x48\x45\x8c\xa6\xaa\x6a\x9d\x6f\
\x99\x19\x1d\x67\x9d\x03\x11\x45\x14\x11\x11\x45\x14\x51\x44\x44\
\x14\x51\x44\x11\x11\x51\x44\x11\x45\x44\x44\x11\x45\x14\x11\x11\
\x45\x14\xf1\x5b\xd1\x75\xb0\xdb\xdd\xd9\x4f\xb4\xce\x88\x28\x22\
\x00\x00\x00\x00\x00\x00\x00\x00\x00\xcf\x36\xce\x69\x07\x1e\xe9\
\x39\x55\x40\x00\x00\x00\x00\x49\x45\x4e\x44\xae\x42\x60\x82\
\x00\x00\x00\x81\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x10\x00\x00\x00\x10\x01\x03\x00\x00\x00\x25\x3d\x6d\x22\
\x00\x00\x00\x06\x50\x4c\x54\x45\x00\x00\x00\xae\xae\xae\x77\x6b\
\xd6\x2d\x00\x00\x00\x01\x74\x52\x4e\x53\x00\x40\xe6\xd8\x66\x00\
\x00\x00\x29\x49\x44\x41\x54\x78\x5e\x05\xc0\xb1\x0d\x00\x20\x08\
\x04\xc0\xc3\x58\xd8\xfe\x0a\xcc\xc2\x70\x8c\x6d\x28\x0e\x97\x47\
\x68\x86\x55\x71\xda\x1d\x6f\x25\xba\xcd\xd8\xfd\x35\x0a\x04\x1b\
\xd6\xd9\x1a\x92\x00\x00\x00\x00\x49\x45\x4e\x44\xae\x42\x60\x82\
\
\x00\x00\x01\x57\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x09\x00\x00\x00\x09\x08\x06\x00\x00\x00\xe0\x91\x06\x10\
\x00\x00\x00\x09\x70\x48\x59\x73\x00\x00\x0e\xc4\x00\x00\x0e\xc4\
\x01\x95\x2b\x0e\x1b\x00\x00\x00\x20\x63\x48\x52\x4d\x00\x00\x7a\
\x25\x00\x00\x80\x83\x00\x00\xf9\xff\x00\x00\x80\xe9\x00\x00\x75\
\x30\x00\x00\xea\x60\x00\x00\x3a\x98\x00\x00\x17\x6f\x92\x5f\xc5\
\x46\x00\x00\x00\xdd\x49\x44\x41\x54\x78\xda\x5c\x8e\xb1\x4e\x84\
\x40\x18\x84\x67\xef\x4c\x2c\xc8\xd9\x2c\x0d\x58\x50\x1b\x0b\xc3\
\xfa\x24\x77\xbd\x0d\x85\x4f\x40\x0b\xbb\xcb\x3b\xd0\x68\x41\x72\
\xc5\xd2\x28\x4f\x02\xcf\xb1\x97\x40\x61\xd4\xc2\xc4\x62\x2c\xbc\
\x4d\xd0\x49\xfe\xbf\xf8\x32\xff\x3f\x23\x48\xc2\x5a\x3b\x00\x80\
\xd6\xfa\x80\xb3\xac\xb5\x03\x49\x18\x63\x0e\x5b\x21\xc4\x90\xe7\
\xf9\x3e\x49\x92\x9b\xbe\xef\xef\xca\xb2\x7c\xf5\xde\xbf\x04\xe6\
\x9c\xbb\xbd\x20\xf9\x19\xae\x95\x52\xfb\x2c\xcb\xbe\xa5\x94\x01\
\x81\xe4\x9b\x38\xbf\x3c\x2a\xa5\x1e\xf0\x4f\xe3\x38\x3e\x37\x4d\
\xf3\x28\x48\x02\x00\xba\xae\x7b\x97\x52\xee\x82\x61\x59\x96\x8f\
\xa2\x28\xae\x00\x60\x03\x00\xc6\x98\xe3\xda\x00\x00\x71\x1c\xef\
\xb4\xd6\x4f\x00\xb0\x05\xf0\x27\x6a\x9e\x67\x44\x51\x04\x00\x48\
\xd3\xf4\xde\x39\x77\xbd\x21\xf9\xb5\xea\x70\x6a\xdb\xf6\x72\x9a\
\xa6\xd3\xaa\xf8\xef\xaa\xeb\xda\x57\x55\xe5\x49\x22\xcc\x9a\xfd\
\x0c\x00\x24\xab\x6e\xfa\x96\x21\xfc\xb8\x00\x00\x00\x00\x49\x45\
\x4e\x44\xae\x42\x60\x82\
"

qt_resource_name = "\
\x00\x09\
\x09\x5f\x97\x13\
\x00\x71\
\x00\x73\x00\x73\x00\x5f\x00\x69\x00\x63\x00\x6f\x00\x6e\x00\x73\
\x00\x02\
\x00\x00\x07\x83\
\x00\x72\
\x00\x63\
\x00\x12\
\x07\x8f\x9d\x27\
\x00\x62\
\x00\x72\x00\x61\x00\x6e\x00\x63\x00\x68\x00\x5f\x00\x6f\x00\x70\x00\x65\x00\x6e\x00\x2d\x00\x6f\x00\x6e\x00\x2e\x00\x70\x00\x6e\
\x00\x67\
\x00\x09\
\x06\x98\x83\x27\
\x00\x63\
\x00\x6c\x00\x6f\x00\x73\x00\x65\x00\x2e\x00\x70\x00\x6e\x00\x67\
\x00\x14\
\x06\x5e\x2c\x07\
\x00\x62\
\x00\x72\x00\x61\x00\x6e\x00\x63\x00\x68\x00\x5f\x00\x63\x00\x6c\x00\x6f\x00\x73\x00\x65\x00\x64\x00\x2d\x00\x6f\x00\x6e\x00\x2e\
\x00\x70\x00\x6e\x00\x67\
\x00\x18\
\x03\x8e\xde\x67\
\x00\x72\
\x00\x69\x00\x67\x00\x68\x00\x74\x00\x5f\x00\x61\x00\x72\x00\x72\x00\x6f\x00\x77\x00\x5f\x00\x64\x00\x69\x00\x73\x00\x61\x00\x62\
\x00\x6c\x00\x65\x00\x64\x00\x2e\x00\x70\x00\x6e\x00\x67\
\x00\x11\
\x08\x8c\x6a\xa7\
\x00\x48\
\x00\x73\x00\x65\x00\x70\x00\x61\x00\x72\x00\x74\x00\x6f\x00\x6f\x00\x6c\x00\x62\x00\x61\x00\x72\x00\x2e\x00\x70\x00\x6e\x00\x67\
\
\x00\x1a\
\x01\x21\xeb\x47\
\x00\x73\
\x00\x74\x00\x79\x00\x6c\x00\x65\x00\x73\x00\x68\x00\x65\x00\x65\x00\x74\x00\x2d\x00\x62\x00\x72\x00\x61\x00\x6e\x00\x63\x00\x68\
\x00\x2d\x00\x6d\x00\x6f\x00\x72\x00\x65\x00\x2e\x00\x70\x00\x6e\x00\x67\
\x00\x17\
\x0c\x65\xce\x07\
\x00\x6c\
\x00\x65\x00\x66\x00\x74\x00\x5f\x00\x61\x00\x72\x00\x72\x00\x6f\x00\x77\x00\x5f\x00\x64\x00\x69\x00\x73\x00\x61\x00\x62\x00\x6c\
\x00\x65\x00\x64\x00\x2e\x00\x70\x00\x6e\x00\x67\
\x00\x0f\
\x06\x53\x25\xa7\
\x00\x62\
\x00\x72\x00\x61\x00\x6e\x00\x63\x00\x68\x00\x5f\x00\x6f\x00\x70\x00\x65\x00\x6e\x00\x2e\x00\x70\x00\x6e\x00\x67\
\x00\x10\
\x01\x00\xca\xa7\
\x00\x48\
\x00\x6d\x00\x6f\x00\x76\x00\x65\x00\x74\x00\x6f\x00\x6f\x00\x6c\x00\x62\x00\x61\x00\x72\x00\x2e\x00\x70\x00\x6e\x00\x67\
\x00\x0f\
\x02\x9f\x05\x87\
\x00\x72\
\x00\x69\x00\x67\x00\x68\x00\x74\x00\x5f\x00\x61\x00\x72\x00\x72\x00\x6f\x00\x77\x00\x2e\x00\x70\x00\x6e\x00\x67\
\x00\x17\
\x0c\xab\x51\x07\
\x00\x64\
\x00\x6f\x00\x77\x00\x6e\x00\x5f\x00\x61\x00\x72\x00\x72\x00\x6f\x00\x77\x00\x5f\x00\x64\x00\x69\x00\x73\x00\x61\x00\x62\x00\x6c\
\x00\x65\x00\x64\x00\x2e\x00\x70\x00\x6e\x00\x67\
\x00\x10\
\x01\x07\x4a\xa7\
\x00\x56\
\x00\x6d\x00\x6f\x00\x76\x00\x65\x00\x74\x00\x6f\x00\x6f\x00\x6c\x00\x62\x00\x61\x00\x72\x00\x2e\x00\x70\x00\x6e\x00\x67\
\x00\x0f\
\x0c\xe2\x68\x67\
\x00\x74\
\x00\x72\x00\x61\x00\x6e\x00\x73\x00\x70\x00\x61\x00\x72\x00\x65\x00\x6e\x00\x74\x00\x2e\x00\x70\x00\x6e\x00\x67\
\x00\x0e\
\x04\xa2\xfc\xa7\
\x00\x64\
\x00\x6f\x00\x77\x00\x6e\x00\x5f\x00\x61\x00\x72\x00\x72\x00\x6f\x00\x77\x00\x2e\x00\x70\x00\x6e\x00\x67\
\x00\x11\
\x0b\xda\x30\xa7\
\x00\x62\
\x00\x72\x00\x61\x00\x6e\x00\x63\x00\x68\x00\x5f\x00\x63\x00\x6c\x00\x6f\x00\x73\x00\x65\x00\x64\x00\x2e\x00\x70\x00\x6e\x00\x67\
\
\x00\x0a\
\x05\x95\xde\x27\
\x00\x75\
\x00\x6e\x00\x64\x00\x6f\x00\x63\x00\x6b\x00\x2e\x00\x70\x00\x6e\x00\x67\
\x00\x0c\
\x06\xe6\xe6\x67\
\x00\x75\
\x00\x70\x00\x5f\x00\x61\x00\x72\x00\x72\x00\x6f\x00\x77\x00\x2e\x00\x70\x00\x6e\x00\x67\
\x00\x11\
\x08\xc4\x6a\xa7\
\x00\x56\
\x00\x73\x00\x65\x00\x70\x00\x61\x00\x72\x00\x74\x00\x6f\x00\x6f\x00\x6c\x00\x62\x00\x61\x00\x72\x00\x2e\x00\x70\x00\x6e\x00\x67\
\
\x00\x15\
\x0f\xf3\xc0\x07\
\x00\x75\
\x00\x70\x00\x5f\x00\x61\x00\x72\x00\x72\x00\x6f\x00\x77\x00\x5f\x00\x64\x00\x69\x00\x73\x00\x61\x00\x62\x00\x6c\x00\x65\x00\x64\
\x00\x2e\x00\x70\x00\x6e\x00\x67\
\x00\x14\
\x0b\xc5\xd7\xc7\
\x00\x73\
\x00\x74\x00\x79\x00\x6c\x00\x65\x00\x73\x00\x68\x00\x65\x00\x65\x00\x74\x00\x2d\x00\x76\x00\x6c\x00\x69\x00\x6e\x00\x65\x00\x2e\
\x00\x70\x00\x6e\x00\x67\
\x00\x0e\
\x0e\xde\xfa\xc7\
\x00\x6c\
\x00\x65\x00\x66\x00\x74\x00\x5f\x00\x61\x00\x72\x00\x72\x00\x6f\x00\x77\x00\x2e\x00\x70\x00\x6e\x00\x67\
\x00\x19\
\x08\x3e\xcc\x07\
\x00\x73\
\x00\x74\x00\x79\x00\x6c\x00\x65\x00\x73\x00\x68\x00\x65\x00\x65\x00\x74\x00\x2d\x00\x62\x00\x72\x00\x61\x00\x6e\x00\x63\x00\x68\
\x00\x2d\x00\x65\x00\x6e\x00\x64\x00\x2e\x00\x70\x00\x6e\x00\x67\
\x00\x0c\
\x06\x41\x40\x87\
\x00\x73\
\x00\x69\x00\x7a\x00\x65\x00\x67\x00\x72\x00\x69\x00\x70\x00\x2e\x00\x70\x00\x6e\x00\x67\
\x00\x0c\
\x04\x56\x23\x67\
\x00\x63\
\x00\x68\x00\x65\x00\x63\x00\x6b\x00\x62\x00\x6f\x00\x78\x00\x2e\x00\x70\x00\x6e\x00\x67\
"

qt_resource_struct = "\
\x00\x00\x00\x00\x00\x02\x00\x00\x00\x01\x00\x00\x00\x01\
\x00\x00\x00\x00\x00\x02\x00\x00\x00\x01\x00\x00\x00\x02\
\x00\x00\x00\x18\x00\x02\x00\x00\x00\x18\x00\x00\x00\x03\
\x00\x00\x01\x82\x00\x00\x00\x00\x00\x01\x00\x00\x07\x2a\
\x00\x00\x02\x00\x00\x00\x00\x00\x00\x01\x00\x00\x09\x5d\
\x00\x00\x00\xf0\x00\x00\x00\x00\x00\x01\x00\x00\x05\x1c\
\x00\x00\x01\xa8\x00\x00\x00\x00\x00\x01\x00\x00\x08\x0f\
\x00\x00\x00\x92\x00\x00\x00\x00\x00\x01\x00\x00\x03\xa6\
\x00\x00\x03\xca\x00\x00\x00\x00\x00\x01\x00\x00\x13\x2f\
\x00\x00\x02\x4a\x00\x00\x00\x00\x00\x01\x00\x00\x0b\x0c\
\x00\x00\x02\x94\x00\x00\x00\x00\x00\x01\x00\x00\x0c\x59\
\x00\x00\x03\xac\x00\x00\x00\x00\x00\x01\x00\x00\x12\xaa\
\x00\x00\x01\x5e\x00\x00\x00\x00\x00\x01\x00\x00\x06\x80\
\x00\x00\x00\x64\x00\x00\x00\x00\x00\x01\x00\x00\x03\x0f\
\x00\x00\x00\x4c\x00\x00\x00\x00\x00\x01\x00\x00\x00\x9a\
\x00\x00\x02\xae\x00\x00\x00\x00\x00\x01\x00\x00\x0e\x25\
\x00\x00\x00\x22\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\
\x00\x00\x03\x74\x00\x00\x00\x00\x00\x01\x00\x00\x11\xc6\
\x00\x00\x00\xc8\x00\x00\x00\x00\x00\x01\x00\x00\x04\x4a\
\x00\x00\x02\xcc\x00\x00\x00\x00\x00\x01\x00\x00\x0e\xc7\
\x00\x00\x03\x24\x00\x00\x00\x00\x00\x01\x00\x00\x10\x29\
\x00\x00\x02\x6c\x00\x00\x00\x00\x00\x01\x00\x00\x0b\xb5\
\x00\x00\x01\x2a\x00\x00\x00\x00\x00\x01\x00\x00\x05\xd6\
\x00\x00\x01\xcc\x00\x00\x00\x00\x00\x01\x00\x00\x08\xb3\
\x00\x00\x02\x26\x00\x00\x00\x00\x00\x01\x00\x00\x0a\x45\
\x00\x00\x03\x52\x00\x00\x00\x00\x00\x01\x00\x00\x11\x1c\
\x00\x00\x02\xf4\x00\x00\x00\x00\x00\x01\x00\x00\x0f\x86\
"

def qInitResources():
    QtCore.qRegisterResourceData(0x01, qt_resource_struct, qt_resource_name, qt_resource_data)

def qCleanupResources():
    QtCore.qUnregisterResourceData(0x01, qt_resource_struct, qt_resource_name, qt_resource_data)

qInitResources()

########NEW FILE########
__FILENAME__ = pyside_style_rc
# -*- coding: utf-8 -*-

# Resource object code
#
# Created: Sun Mar 10 16:49:56 2013
#      by: The Resource Compiler for PySide (Qt v4.8.0)
#
# WARNING! All changes made in this file will be lost!

from PySide import QtCore

qt_resource_data = "\x00\x00\x00\x96\x89PNG\x0d\x0a\x1a\x0a\x00\x00\x00\x0dIHDR\x00\x00\x00\x09\x00\x00\x00\x06\x08\x04\x00\x00\x00\xbb\xce|N\x00\x00\x00\x02bKGD\x00\xd3\xb5W\xa0\x5c\x00\x00\x00\x09pHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x07tIME\x07\xdc\x0b\x07\x0c\x0d\x1bu\xfe1\x99\x00\x00\x00'IDAT\x08\xd7e\x8c\xb1\x0d\x00\x00\x08\x83\xe0\xff\xa3up\xb1\xca\xd4\x90Px\x08U!\x14\xb6Tp\xe6H\x8d\x87\xcc\x0f\x0d\xe0\xf0\x08\x024\xe2+\xa7\x00\x00\x00\x00IEND\xaeB`\x82\x00\x00\x02q\x89PNG\x0d\x0a\x1a\x0a\x00\x00\x00\x0dIHDR\x00\x00\x00 \x00\x00\x00 \x08\x06\x00\x00\x00szz\xf4\x00\x00\x00\x01sRGB\x00\xae\xce\x1c\xe9\x00\x00\x00\x06bKGD\x00\xff\x00\xff\x00\xff\xa0\xbd\xa7\x93\x00\x00\x00\x09pHYs\x00\x00\x0e\xc4\x00\x00\x0e\xc4\x01\x95+\x0e\x1b\x00\x00\x00\x07tIME\x07\xdc\x08\x17\x0b\x01(tm$I\x00\x00\x01\xf1IDATX\xc3\xcdWAN\x021\x14\xfd\xfd\xb5np!\x89\xb8\x11\x8d\x89[\xef\x80;\xb7\xde\x806p,\xa0\xbd\x86;\xc2\x19\xd8\xb9!\x11\x13#\x0bM\x94I\xb4i\xeb\xc6\xea\xa4a\x86\xb6@\xf0\xef\xc8\xd0y}\xef\xbfy\xed\x07\xd8s\x91\xaa\x07J\xa9W\x00\x00\xe7\xdcR\x08\xd1\xcey\xb9\x94rN\x08i\x00\x00p\xce\x9bQ\x1b\x18\x0c\x06S\xc6\xd8\xa5_\x08\x00`\xad]p\xceOS\xc0\x95R/\x88\xd8\xf2\xbf\x9dsK\xad\xf5\xac\xdf\xef_\x97\xff\x87\xe1\xc2\x10\x1c\x00\x00\x11[R\xcay\x0a\xf328\x00\x00!\xa4\xc1\x18\xbb\xacT`\x15\xf3\xb0\xb4\xd6\xf3^\xafw^\x07>\x1c\x0e\x1f\x19c\x95-\x0b\x95\xc0:\xe6aQJk\x95\x90R\xce)\xa5\xadZ\xd3\x05J\x10o8D<\x8e\x95x\x95'\xc2\x9eG\xbc\xe3\x8ds\xde\xc4\x1cw\x87\x9eX\xd5\xf3\xd8:\xf0}\x01\x80\xe3\x94\x85\x94\xd23\xa5\xd4\x8b\xdfP*\xf0\x0f\xe6\x9f\x09S%\xdc\xa4\xca-\xfcm\x01\xe7\xfc\xd4\x18\xf3\xb4kpc\xccS\xd9?d]\x80\xec\x8aye\x10\xedJ\x89\x90y\xccY\xb05%\xea\xa2\xbc\xf23\xdc\x96\x12U\xcc\xd7*\xb0\x0d%b\x0e1\x84=\x17\xa6\x9ej\x9b$f\xea\x85d\x7f&\xdc\x94y\x8a\x12\xff+\x88\xb6\xcd<F\x89\xffq\x18\xe52\xb7\xd6.\xac\xb5\x8bM\x94@\x7fM\xcaM\xb8\xdc\xc4\xf4\x98\x98+ayV\x10B\xb4s\x94\xf8\xdd\x00\xe7\xbc\xe9o(\xb9\xd9\x9e\xa2\x84sn\xe9\x07\x15,]\xb9g\xeb6\x112\x0fK\x08\xd16\xc6<\x03\x80\xad!\xf0\xa1\xb5\x9eU\xe6\x80\x94\xf2\x1d\x11\x1b\x84\x10R\x02\xfer\xce\xdd\x0a!\xc6\x91\x83\xc9\x0d!\xe4\x1e\x11\x0fC\xe6\xddn\xf7\xa86\x09\xa7\xd3\xe9\x95\xb5vY\x02\xff,\x8a\xe2.\x16\xfcG\x89qQ\x14w\xd6\xda\xcfp I\x1eN'\x93\xc9\xc5h4z\xcf1X\xa7\xd39\x11B<\xd4\x0d\xa7{\xafo\x1a+Z\x88\xa9l\x88.\x00\x00\x00\x00IEND\xaeB`\x82\x00\x00\x00\x93\x89PNG\x0d\x0a\x1a\x0a\x00\x00\x00\x0dIHDR\x00\x00\x00\x06\x00\x00\x00\x09\x08\x04\x00\x00\x00\xbb\x93\x95\x16\x00\x00\x00\x02bKGD\x00\xd3\xb5W\xa0\x5c\x00\x00\x00\x09pHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x07tIME\x07\xdc\x0b\x07\x0c\x0c+J<0t\x00\x00\x00$IDAT\x08\xd7c`@\x05\xff\xff\xc3XL\xc8\x5c&dY&d\xc5p\x0e##\x9c\xc3\xc8\x88a\x1a\x0a\x00\x00\x9e\x14\x0a\x05+\xca\xe5u\x00\x00\x00\x00IEND\xaeB`\x82\x00\x00\x00\xa0\x89PNG\x0d\x0a\x1a\x0a\x00\x00\x00\x0dIHDR\x00\x00\x00\x06\x00\x00\x00\x09\x08\x04\x00\x00\x00\xbb\x93\x95\x16\x00\x00\x00\x01sRGB\x00\xae\xce\x1c\xe9\x00\x00\x00\x02bKGD\x00\xff\x87\x8f\xcc\xbf\x00\x00\x00\x09pHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x07tIME\x07\xdc\x08\x17\x14\x1f\x0d\xfcR+\x9c\x00\x00\x00$IDAT\x08\xd7c`@\x05s>\xc0XL\xc8\x5c&dY&d\xc5pN\x8a\x00\x9c\x93\x22\x80a\x1a\x0a\x00\x00)\x95\x08\xaf\x88\xac\xba4\x00\x00\x00\x00IEND\xaeB`\x82\x00\x00\x00\xce\x89PNG\x0d\x0a\x1a\x0a\x00\x00\x00\x0dIHDR\x00\x00\x00\x07\x00\x00\x00?\x08\x06\x00\x00\x00,{\xd2\x13\x00\x00\x00\x01sRGB\x00\xae\xce\x1c\xe9\x00\x00\x00\x06bKGD\x00\xff\x00\xff\x00\xff\xa0\xbd\xa7\x93\x00\x00\x00\x09pHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x07tIME\x07\xdc\x08\x17\x09/\x07\xd7?\xc4R\x00\x00\x00NIDAT8\xcbc`\x186\x80\x19\xc6\xa8o\x9f\xca\xe0\xe0\xe2\xcd\xf0\xea\xe5s\x867\xaf^000000\xe1\xd39*IH\x92\x05\x89\xfd\x1f\x89\xcd8\x1aB\xa3\x92\x83'i2\x8e\x86\x10\xa9\x92\xf0 \xd3\xd41\x84\x0b^\xbfr\x9ea\x14@\x01\x00\x13M\x0cF\x89*\x0a \x00\x00\x00\x00IEND\xaeB`\x82\x00\x00\x00\xb6\x89PNG\x0d\x0a\x1a\x0a\x00\x00\x00\x0dIHDR\x00\x00\x00\x18\x00\x00\x00\x11\x08\x06\x00\x00\x00\xc7xl0\x00\x00\x00\x01sRGB\x00\xae\xce\x1c\xe9\x00\x00\x00\x06bKGD\x00\xff\x00\xff\x00\xff\xa0\xbd\xa7\x93\x00\x00\x00\x09pHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x07tIME\x07\xdc\x08\x17\x0b,\x0d\x1fC\xaa\xe1\x00\x00\x006IDAT8\xcbc` \x01,Z\xb4\xe8\xff\xa2E\x8b\xfe\x93\xa2\x87\x89\x81\xc6`\xd4\x82\x11`\x01#\xa9\xc9t\xd0\xf9\x80\x85\x1cMqqq\x8c\xa3\xa9h\xd4\x82ad\x01\x001\xb5\x09\xec\x1fK\xb4\x15\x00\x00\x00\x00IEND\xaeB`\x82\x00\x00\x00\xa6\x89PNG\x0d\x0a\x1a\x0a\x00\x00\x00\x0dIHDR\x00\x00\x00\x06\x00\x00\x00\x09\x08\x04\x00\x00\x00\xbb\x93\x95\x16\x00\x00\x00\x01sRGB\x00\xae\xce\x1c\xe9\x00\x00\x00\x02bKGD\x00\xff\x87\x8f\xcc\xbf\x00\x00\x00\x09pHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x07tIME\x07\xdc\x08\x17\x14\x1f \xb9\x8dw\xe9\x00\x00\x00*IDAT\x08\xd7c`\xc0\x06\xe6|```B0\xa1\x1c\x08\x93\x81\x81\x09\xc1d``b`H\x11@\xe2 s\x19\x90\x8d@\x02\x00#\xed\x08\xafd\x9f\x0f\x15\x00\x00\x00\x00IEND\xaeB`\x82\x00\x00\x00\xa6\x89PNG\x0d\x0a\x1a\x0a\x00\x00\x00\x0dIHDR\x00\x00\x00\x09\x00\x00\x00\x06\x08\x04\x00\x00\x00\xbb\xce|N\x00\x00\x00\x01sRGB\x00\xae\xce\x1c\xe9\x00\x00\x00\x02bKGD\x00\x9cS4\xfc]\x00\x00\x00\x09pHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x07tIME\x07\xdc\x08\x17\x0b\x1b\x0e\x16M[o\x00\x00\x00*IDAT\x08\xd7c`\xc0\x00\x8c\x0c\x0cs> \x0b\xa4\x08020 \x0b\xa6\x08000B\x98\x10\xc1\x14\x01\x14\x13P\xb5\xa3\x01\x00\xc6\xb9\x07\x90]f\x1f\x83\x00\x00\x00\x00IEND\xaeB`\x82\x00\x00\x00\xe1\x89PNG\x0d\x0a\x1a\x0a\x00\x00\x00\x0dIHDR\x00\x00\x00\x0a\x00\x00\x006\x08\x06\x00\x00\x00\xfe\x8a\x08k\x00\x00\x00\x01sRGB\x00\xae\xce\x1c\xe9\x00\x00\x00\x06bKGD\x00\xff\x00\xff\x00\xff\xa0\xbd\xa7\x93\x00\x00\x00\x09pHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x07tIME\x07\xdc\x08\x17\x093\x22zLMH\x00\x00\x00aIDATH\xc7c\xfc\xcf@\x1c`b\xa0\x99Bc##\x06c##\x0c6\x1d\xac\x1eU8\xc8\x142\xfeg``hh\x9f\x8a3Y\xaeZ:\x87\xe1\xda\x95\xf3\x8c4\xb2ZK\xc7\x10o\x8e\xb8v\xe5<#\xe3\x7f\xa4\x84\xcb\xc0\xc0\xc0p\xf6\xdc9\x14\xf6h\x80\x8f\x06\xf8h\x80\x8f\x96fC'=\x0er7\x02\x00\x100@\xb35\xa0|I\x00\x00\x00\x00IEND\xaeB`\x82\x00\x00\x00\xa0\x89PNG\x0d\x0a\x1a\x0a\x00\x00\x00\x0dIHDR\x00\x00\x00\x06\x00\x00\x00\x09\x08\x04\x00\x00\x00\xbb\x93\x95\x16\x00\x00\x00\x01sRGB\x00\xae\xce\x1c\xe9\x00\x00\x00\x02bKGD\x00\xff\x87\x8f\xcc\xbf\x00\x00\x00\x09pHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x07tIME\x07\xdc\x08\x17\x14\x1c\x1f$\xc6\x09\x17\x00\x00\x00$IDAT\x08\xd7c`@\x05\xff\xcf\xc3XL\xc8\x5c&dY&d\xc5p\x0e\xa3!\x9c\xc3h\x88a\x1a\x0a\x00\x00m\x84\x09u7\x9e\xd9#\x00\x00\x00\x00IEND\xaeB`\x82\x00\x00\x00\xa6\x89PNG\x0d\x0a\x1a\x0a\x00\x00\x00\x0dIHDR\x00\x00\x00\x09\x00\x00\x00\x06\x08\x04\x00\x00\x00\xbb\xce|N\x00\x00\x00\x01sRGB\x00\xae\xce\x1c\xe9\x00\x00\x00\x02bKGD\x00\xff\x87\x8f\xcc\xbf\x00\x00\x00\x09pHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x07tIME\x07\xdc\x08\x17\x08\x15;\xdc;\x0c\x9b\x00\x00\x00*IDAT\x08\xd7c`\xc0\x00\x8c\x0c\x0cs> \x0b\xa4\x08020 \x0b\xa6\x08000B\x98\x10\xc1\x14\x01\x14\x13P\xb5\xa3\x01\x00\xc6\xb9\x07\x90]f\x1f\x83\x00\x00\x00\x00IEND\xaeB`\x82\x00\x00\x00\xe4\x89PNG\x0d\x0a\x1a\x0a\x00\x00\x00\x0dIHDR\x00\x00\x006\x00\x00\x00\x0a\x08\x06\x00\x00\x00\xff\xfd\xad\x0b\x00\x00\x00\x01sRGB\x00\xae\xce\x1c\xe9\x00\x00\x00\x06bKGD\x00\x7f\x00\x87\x00\x95\xe6\xde\xa6\xaf\x00\x00\x00\x09pHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x07tIME\x07\xdc\x08\x17\x09*+\x98\x90\x5c\xf4\x00\x00\x00dIDATH\xc7c\xfc\xcf0<\x01\x0b\xa5\x064\xb4O\x85\x87\xcd\xaa\xa5s\x18\xae]9\xcfH+5\x14y\xcc\xd8\xc8\x88$\x03|\x89\xd0O-5\x84\xc0\xd9s\xe7\xe0l&\x86\x91\x92\x14\x91}MTR\x0cM&\xa8\x9fZjF\x93\xe2hR\x1c\x82I\x91\x91\xd2zLK\xc7\x10\xc5\x08l\xc54\xb5\xd4\xd0\xd5c\x83\x15\x00\x00z0J\x09q\xea-n\x00\x00\x00\x00IEND\xaeB`\x82\x00\x00\x00\xc3\x89PNG\x0d\x0a\x1a\x0a\x00\x00\x00\x0dIHDR\x00\x00\x00@\x00\x00\x00@\x08\x06\x00\x00\x00\xaaiq\xde\x00\x00\x00\x06bKGD\x00\xff\x00\xff\x00\xff\xa0\xbd\xa7\x93\x00\x00\x00\x09pHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x07tIME\x07\xdc\x0b\x07\x09.7\xffD\xe8\xf0\x00\x00\x00\x1diTXtComment\x00\x00\x00\x00\x00Created with GIMPd.e\x07\x00\x00\x00'IDATx\xda\xed\xc1\x01\x0d\x00\x00\x00\xc2\xa0\xf7Om\x0e7\xa0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x80w\x03@@\x00\x01\xafz\x0e\xe8\x00\x00\x00\x00IEND\xaeB`\x82\x00\x00\x00\xa5\x89PNG\x0d\x0a\x1a\x0a\x00\x00\x00\x0dIHDR\x00\x00\x00\x09\x00\x00\x00\x06\x08\x04\x00\x00\x00\xbb\xce|N\x00\x00\x00\x01sRGB\x00\xae\xce\x1c\xe9\x00\x00\x00\x02bKGD\x00\x9cS4\xfc]\x00\x00\x00\x09pHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x07tIME\x07\xdc\x08\x17\x0b\x02\x04m\x98\x1bi\x00\x00\x00)IDAT\x08\xd7c`\xc0\x00\x8c\x0c\x0c\xff\xcf\xa3\x08\x18220 \x0b2\x1a200B\x98\x10AFC\x14\x13P\xb5\xa3\x01\x00\xd6\x10\x07\xd2/H\xdfJ\x00\x00\x00\x00IEND\xaeB`\x82\x00\x00\x00\xa0\x89PNG\x0d\x0a\x1a\x0a\x00\x00\x00\x0dIHDR\x00\x00\x00\x06\x00\x00\x00\x09\x08\x04\x00\x00\x00\xbb\x93\x95\x16\x00\x00\x00\x01sRGB\x00\xae\xce\x1c\xe9\x00\x00\x00\x02bKGD\x00\x9cS4\xfc]\x00\x00\x00\x09pHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x07tIME\x07\xdc\x08\x17\x0b\x1b)\xb3G\xee\x04\x00\x00\x00$IDAT\x08\xd7c`@\x05s>\xc0XL\xc8\x5c&dY&d\xc5pN\x8a\x00\x9c\x93\x22\x80a\x1a\x0a\x00\x00)\x95\x08\xaf\x88\xac\xba4\x00\x00\x00\x00IEND\xaeB`\x82\x00\x00\x01\xc8\x89PNG\x0d\x0a\x1a\x0a\x00\x00\x00\x0dIHDR\x00\x00\x00 \x00\x00\x00 \x08\x06\x00\x00\x00szz\xf4\x00\x00\x00\x01sRGB\x00\xae\xce\x1c\xe9\x00\x00\x00\x06bKGD\x00\xff\x00\xff\x00\xff\xa0\xbd\xa7\x93\x00\x00\x00\x09pHYs\x00\x00\x0e\xc4\x00\x00\x0e\xc4\x01\x95+\x0e\x1b\x00\x00\x00\x07tIME\x07\xdc\x08\x17\x0b\x03$O\xed\x0a\xe0\x00\x00\x01HIDATX\xc3\xedWA\x8e\x830\x0c\xb4!\xd0>\x10?\x8e#\xe7 \xbe\xb3?\xd9U\x03\x9b\xd9K*E\x10\x96$\x04\xf5\x82\xcf.cO\xc6c\x97\xe8\xc3\xc1W|Tkm\x98\xb9:\xca\x03\xb0\xa8\x0b\x9b\xab#r~\xab+\x90E\xa4\x05\xb0\xc4\xe4VW\xb5/\x22\x0d\x80\xf9(o\xf3\x04\xe38.9\x80\x00\xac\x88\xb4\xa9\xbfS\x9ep~\x98\xb9\xcdde\x03\xae\xb5\x9e\x99YE?\xc1\x19p\x00&0\x05*\x9a\x01G{\x16x\xd7uuB\xe7v\x8dsF\x84\xa9\x9d[\x00f=\x1d\xcaZK\xd34\xad\x055\xa7\x0a\xea\xa8s\x9f)WhCDT\x0d\xc3\xf0\x05`#\xea\x0c\xe7S\xb1L9\x9f0Dd\xd9\xd3@\xed1`D\xe4Q\xba\xf3\xe2F\x94\xday\x94\x11\x15\x8a\xe0t8\xbfx\x14c`\xc7\xf3\x93\xa6\xe34\x03\x22\xd2x\xaaN\xf5\x852\xcb\xe8\xad\xea\x1cG,\xa6\x81\xd0\xd4\xc4\x1c%\x97\xad\xe3\xd8\xb8\x0b\xb8\x0b\xb8\x0b\xa8J\xffa\xe9\xfb\xbeq&\xf4\x1dX\xf3qF\xc4\xcc*\xf7:v\xeb\x9d\x00D\x19\x91z\x9f\xd4\xcc\x5c\xaf\x18\xa8\xcfP\xcb\xcc\xa1#\x07\xbbT\xc7\x9e\xd1\xb9\x01\xe0%\x22\xcf\x7f\xdf\xda\xbf\xd5\xcab\xc3\x84\xc0\x83b\xd3Z\xbfJ\x17\xb0\x07ND\xf4\x07\xae\xf5\xd5\xa6\x1d\xd1\x22\x08\x00\x00\x00\x00IEND\xaeB`\x82\x00\x00\x00\x9e\x89PNG\x0d\x0a\x1a\x0a\x00\x00\x00\x0dIHDR\x00\x00\x00\x09\x00\x00\x00\x06\x08\x04\x00\x00\x00\xbb\xce|N\x00\x00\x00\x01sRGB\x00\xae\xce\x1c\xe9\x00\x00\x00\x02bKGD\x00\xff\x87\x8f\xcc\xbf\x00\x00\x00\x09pHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x07tIME\x07\xdc\x08\x17\x08\x15\x0f\xfd\x8f\xf8.\x00\x00\x00\x22IDAT\x08\xd7c`\xc0\x0d\xfe\x9f\x87\xb1\x18\x91\x05\x18\x0d\xe1BH*\x0c\x19\x18\x18\x91\x05\x10*\xd1\x00\x00\xca\xb5\x07\xd2v\xbb\xb2\xc5\x00\x00\x00\x00IEND\xaeB`\x82\x00\x00\x00\xbb\x89PNG\x0d\x0a\x1a\x0a\x00\x00\x00\x0dIHDR\x00\x00\x00?\x00\x00\x00\x07\x08\x06\x00\x00\x00\xbfv\x95\x1f\x00\x00\x00\x01sRGB\x00\xae\xce\x1c\xe9\x00\x00\x00\x06bKGD\x00\xff\x00\xff\x00\xff\xa0\xbd\xa7\x93\x00\x00\x00\x09pHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x07tIME\x07\xdc\x08\x17\x095+U\xcaRj\x00\x00\x00;IDAT8\xcbc`\x18\x05#\x130\x12\xa3\xa8\xbe}*%v\xfc\xa7\x97;\xd1\xc1\xaa\xa5s\x18\xae_9\x8fS\x9ei4\xe6\x09\x00M\x1d\xc3!\x19\xf3\x0c\x0c\x0cxc~\x14\x8cT\x00\x00id\x0b\x05\xfdkX\xca\x00\x00\x00\x00IEND\xaeB`\x82\x00\x00\x00\x9f\x89PNG\x0d\x0a\x1a\x0a\x00\x00\x00\x0dIHDR\x00\x00\x00\x09\x00\x00\x00\x06\x08\x04\x00\x00\x00\xbb\xce|N\x00\x00\x00\x01sRGB\x00\xae\xce\x1c\xe9\x00\x00\x00\x02bKGD\x00\xff\x87\x8f\xcc\xbf\x00\x00\x00\x09pHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x07tIME\x07\xdc\x08\x17\x08\x14\x1f\xf9#\xd9\x0b\x00\x00\x00#IDAT\x08\xd7c`\xc0\x0d\xe6|\x80\xb1\x18\x91\x05R\x04\xe0B\x08\x15)\x02\x0c\x0c\x8c\xc8\x02\x08\x95h\x00\x00\xac\xac\x07\x90Ne4\xac\x00\x00\x00\x00IEND\xaeB`\x82\x00\x00\x00\xef\x89PNG\x0d\x0a\x1a\x0a\x00\x00\x00\x0dIHDR\x00\x00\x00Q\x00\x00\x00:\x08\x06\x00\x00\x00\xc8\xbc\xb5\xaf\x00\x00\x00\x01sRGB\x00\xae\xce\x1c\xe9\x00\x00\x00\x06bKGD\x00\xff\x00\xff\x00\xff\xa0\xbd\xa7\x93\x00\x00\x00\x09pHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x07tIME\x07\xdc\x08\x17\x0b*2\xff\x7f Z\x00\x00\x00oIDATx\xda\xed\xd0\xb1\x0d\x000\x08\x03A\xc8\xa0\x0c\xc7\xa2I\xcf\x04(\xba/]Y\x97\xb1\xb4\xee\xbes\xab\xaa\xdc\xf8\xf5\x84 B\x84(\x88\x10!B\x14D\x88\x10!\x0a\x22D\x88\x10\x05\x11\x22D\x88\x82\x08\x11\x22DA\x84\x08Q\x10!B\x84(\x88\x10!B\x14D\x88\x10!\x0a\x22D\x88\x10\x05\x11\x22D\x88\x82\x08\x11\x22DA\x84\x08Q\x10!B\xfc\xaa\x07\x12U\x04tV\x9e\x9eT\x00\x00\x00\x00IEND\xaeB`\x82\x00\x00\x00\xa6\x89PNG\x0d\x0a\x1a\x0a\x00\x00\x00\x0dIHDR\x00\x00\x00\x06\x00\x00\x00\x09\x08\x04\x00\x00\x00\xbb\x93\x95\x16\x00\x00\x00\x01sRGB\x00\xae\xce\x1c\xe9\x00\x00\x00\x02bKGD\x00\xff\x87\x8f\xcc\xbf\x00\x00\x00\x09pHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x07tIME\x07\xdc\x08\x17\x14\x1d\x00\xb0\xd55\xa3\x00\x00\x00*IDAT\x08\xd7c`\xc0\x06\xfe\x9fg``B0\xa1\x1c\x08\x93\x81\x81\x09\xc1d``b``4D\xe2 s\x19\x90\x8d@\x02\x00d@\x09u\x86\xb3\xad\x9c\x00\x00\x00\x00IEND\xaeB`\x82\x00\x00\x00\xe0\x89PNG\x0d\x0a\x1a\x0a\x00\x00\x00\x0dIHDR\x00\x00\x00Q\x00\x00\x00:\x08\x06\x00\x00\x00\xc8\xbc\xb5\xaf\x00\x00\x00\x01sRGB\x00\xae\xce\x1c\xe9\x00\x00\x00\x06bKGD\x00\xff\x00\xff\x00\xff\xa0\xbd\xa7\x93\x00\x00\x00\x09pHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x07tIME\x07\xdc\x08\x17\x0b)\x1c\x08\x84~V\x00\x00\x00`IDATx\xda\xed\xd9\xb1\x0d\x00 \x08\x00AqP\x86cQ\xed\x8d\x85%\x89w\xa5\x15\xf9HE\x8c\xa6\xaaj\x9do\x99\x19\x1dg\x9d\x03\x11E\x14\x11\x11E\x14QDD\x14QD\x11\x11QD\x11EDD\x11E\x14\x11\x11E\x14\xf1[\xd1u\xb0\xdb\xdd\xd9O\xb4\xce\x88(\x22\x00\x00\x00\x00\x00\x00\x00\x00\x00\xcf6\xcei\x07\x1e\xe99U@\x00\x00\x00\x00IEND\xaeB`\x82\x00\x00\x00\x81\x89PNG\x0d\x0a\x1a\x0a\x00\x00\x00\x0dIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x01\x03\x00\x00\x00%=m\x22\x00\x00\x00\x06PLTE\x00\x00\x00\xae\xae\xaewk\xd6-\x00\x00\x00\x01tRNS\x00@\xe6\xd8f\x00\x00\x00)IDATx^\x05\xc0\xb1\x0d\x00 \x08\x04\xc0\xc3X\xd8\xfe\x0a\xcc\xc2p\x8cm(\x0e\x97Gh\x86Uq\xda\x1do%\xba\xcd\xd8\xfd5\x0a\x04\x1b\xd6\xd9\x1a\x92\x00\x00\x00\x00IEND\xaeB`\x82\x00\x00\x01W\x89PNG\x0d\x0a\x1a\x0a\x00\x00\x00\x0dIHDR\x00\x00\x00\x09\x00\x00\x00\x09\x08\x06\x00\x00\x00\xe0\x91\x06\x10\x00\x00\x00\x09pHYs\x00\x00\x0e\xc4\x00\x00\x0e\xc4\x01\x95+\x0e\x1b\x00\x00\x00 cHRM\x00\x00z%\x00\x00\x80\x83\x00\x00\xf9\xff\x00\x00\x80\xe9\x00\x00u0\x00\x00\xea`\x00\x00:\x98\x00\x00\x17o\x92_\xc5F\x00\x00\x00\xddIDATx\xda\x5c\x8e\xb1N\x84@\x18\x84g\xefL,\xc8\xd9,\x0dXP\x1b\x0b\xc3\xfa$w\xbd\x0d\x85O@\x0b\xbb\xcb;\xd0hAr\xc5\xd2(O\x02\xcf\xb1\x97@a\xd4\xc2\xc4b,\xbcM\xd0I\xfe\xbf\xf82\xff?#H\xc2Z;\x00\x80\xd6\xfa\x80\xb3\xac\xb5\x03I\x18c\x0e[!\xc4\x90\xe7\xf9>I\x92\x9b\xbe\xef\xef\xca\xb2|\xf5\xde\xbf\x04\xe6\x9c\xbb\xbd \xf9\x19\xae\x95R\xfb,\xcb\xbe\xa5\x94\x01\x81\xe4\x9b8\xbf<*\xa5\x1e\xf0O\xe38>7M\xf3(H\x02\x00\xba\xae{\x97R\xee\x82aY\x96\x8f\xa2(\xae\x00`\x03\x00\xc6\x98\xe3\xda\x00\x00q\x1c\xef\xb4\xd6O\x00\xb0\x05\xf0'j\x9egDQ\x04\x00H\xd3\xf4\xde9w\xbd!\xf9\xb5\xeapj\xdb\xf6r\x9a\xa6\xd3\xaa\xf8\xef\xaa\xeb\xdaWU\xe5I\x22\xcc\x9a\xfd\x0c\x00$\xabn\xfa\x96!\xfc\xb8\x00\x00\x00\x00IEND\xaeB`\x82"
qt_resource_name = "\x00\x09\x09_\x97\x13\x00q\x00s\x00s\x00_\x00i\x00c\x00o\x00n\x00s\x00\x02\x00\x00\x07\x83\x00r\x00c\x00\x12\x07\x8f\x9d'\x00b\x00r\x00a\x00n\x00c\x00h\x00_\x00o\x00p\x00e\x00n\x00-\x00o\x00n\x00.\x00p\x00n\x00g\x00\x09\x06\x98\x83'\x00c\x00l\x00o\x00s\x00e\x00.\x00p\x00n\x00g\x00\x14\x06^,\x07\x00b\x00r\x00a\x00n\x00c\x00h\x00_\x00c\x00l\x00o\x00s\x00e\x00d\x00-\x00o\x00n\x00.\x00p\x00n\x00g\x00\x18\x03\x8e\xdeg\x00r\x00i\x00g\x00h\x00t\x00_\x00a\x00r\x00r\x00o\x00w\x00_\x00d\x00i\x00s\x00a\x00b\x00l\x00e\x00d\x00.\x00p\x00n\x00g\x00\x11\x08\x8cj\xa7\x00H\x00s\x00e\x00p\x00a\x00r\x00t\x00o\x00o\x00l\x00b\x00a\x00r\x00.\x00p\x00n\x00g\x00\x1a\x01!\xebG\x00s\x00t\x00y\x00l\x00e\x00s\x00h\x00e\x00e\x00t\x00-\x00b\x00r\x00a\x00n\x00c\x00h\x00-\x00m\x00o\x00r\x00e\x00.\x00p\x00n\x00g\x00\x17\x0ce\xce\x07\x00l\x00e\x00f\x00t\x00_\x00a\x00r\x00r\x00o\x00w\x00_\x00d\x00i\x00s\x00a\x00b\x00l\x00e\x00d\x00.\x00p\x00n\x00g\x00\x0f\x06S%\xa7\x00b\x00r\x00a\x00n\x00c\x00h\x00_\x00o\x00p\x00e\x00n\x00.\x00p\x00n\x00g\x00\x10\x01\x00\xca\xa7\x00H\x00m\x00o\x00v\x00e\x00t\x00o\x00o\x00l\x00b\x00a\x00r\x00.\x00p\x00n\x00g\x00\x0f\x02\x9f\x05\x87\x00r\x00i\x00g\x00h\x00t\x00_\x00a\x00r\x00r\x00o\x00w\x00.\x00p\x00n\x00g\x00\x17\x0c\xabQ\x07\x00d\x00o\x00w\x00n\x00_\x00a\x00r\x00r\x00o\x00w\x00_\x00d\x00i\x00s\x00a\x00b\x00l\x00e\x00d\x00.\x00p\x00n\x00g\x00\x10\x01\x07J\xa7\x00V\x00m\x00o\x00v\x00e\x00t\x00o\x00o\x00l\x00b\x00a\x00r\x00.\x00p\x00n\x00g\x00\x0f\x0c\xe2hg\x00t\x00r\x00a\x00n\x00s\x00p\x00a\x00r\x00e\x00n\x00t\x00.\x00p\x00n\x00g\x00\x0e\x04\xa2\xfc\xa7\x00d\x00o\x00w\x00n\x00_\x00a\x00r\x00r\x00o\x00w\x00.\x00p\x00n\x00g\x00\x11\x0b\xda0\xa7\x00b\x00r\x00a\x00n\x00c\x00h\x00_\x00c\x00l\x00o\x00s\x00e\x00d\x00.\x00p\x00n\x00g\x00\x0a\x05\x95\xde'\x00u\x00n\x00d\x00o\x00c\x00k\x00.\x00p\x00n\x00g\x00\x0c\x06\xe6\xe6g\x00u\x00p\x00_\x00a\x00r\x00r\x00o\x00w\x00.\x00p\x00n\x00g\x00\x11\x08\xc4j\xa7\x00V\x00s\x00e\x00p\x00a\x00r\x00t\x00o\x00o\x00l\x00b\x00a\x00r\x00.\x00p\x00n\x00g\x00\x15\x0f\xf3\xc0\x07\x00u\x00p\x00_\x00a\x00r\x00r\x00o\x00w\x00_\x00d\x00i\x00s\x00a\x00b\x00l\x00e\x00d\x00.\x00p\x00n\x00g\x00\x14\x0b\xc5\xd7\xc7\x00s\x00t\x00y\x00l\x00e\x00s\x00h\x00e\x00e\x00t\x00-\x00v\x00l\x00i\x00n\x00e\x00.\x00p\x00n\x00g\x00\x0e\x0e\xde\xfa\xc7\x00l\x00e\x00f\x00t\x00_\x00a\x00r\x00r\x00o\x00w\x00.\x00p\x00n\x00g\x00\x19\x08>\xcc\x07\x00s\x00t\x00y\x00l\x00e\x00s\x00h\x00e\x00e\x00t\x00-\x00b\x00r\x00a\x00n\x00c\x00h\x00-\x00e\x00n\x00d\x00.\x00p\x00n\x00g\x00\x0c\x06A@\x87\x00s\x00i\x00z\x00e\x00g\x00r\x00i\x00p\x00.\x00p\x00n\x00g\x00\x0c\x04V#g\x00c\x00h\x00e\x00c\x00k\x00b\x00o\x00x\x00.\x00p\x00n\x00g"
qt_resource_struct = "\x00\x00\x00\x00\x00\x02\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x00\x02\x00\x00\x00\x01\x00\x00\x00\x02\x00\x00\x00\x18\x00\x02\x00\x00\x00\x18\x00\x00\x00\x03\x00\x00\x01\x82\x00\x00\x00\x00\x00\x01\x00\x00\x07*\x00\x00\x02\x00\x00\x00\x00\x00\x00\x01\x00\x00\x09]\x00\x00\x00\xf0\x00\x00\x00\x00\x00\x01\x00\x00\x05\x1c\x00\x00\x01\xa8\x00\x00\x00\x00\x00\x01\x00\x00\x08\x0f\x00\x00\x00\x92\x00\x00\x00\x00\x00\x01\x00\x00\x03\xa6\x00\x00\x03\xca\x00\x00\x00\x00\x00\x01\x00\x00\x13/\x00\x00\x02J\x00\x00\x00\x00\x00\x01\x00\x00\x0b\x0c\x00\x00\x02\x94\x00\x00\x00\x00\x00\x01\x00\x00\x0cY\x00\x00\x03\xac\x00\x00\x00\x00\x00\x01\x00\x00\x12\xaa\x00\x00\x01^\x00\x00\x00\x00\x00\x01\x00\x00\x06\x80\x00\x00\x00d\x00\x00\x00\x00\x00\x01\x00\x00\x03\x0f\x00\x00\x00L\x00\x00\x00\x00\x00\x01\x00\x00\x00\x9a\x00\x00\x02\xae\x00\x00\x00\x00\x00\x01\x00\x00\x0e%\x00\x00\x00\x22\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x03t\x00\x00\x00\x00\x00\x01\x00\x00\x11\xc6\x00\x00\x00\xc8\x00\x00\x00\x00\x00\x01\x00\x00\x04J\x00\x00\x02\xcc\x00\x00\x00\x00\x00\x01\x00\x00\x0e\xc7\x00\x00\x03$\x00\x00\x00\x00\x00\x01\x00\x00\x10)\x00\x00\x02l\x00\x00\x00\x00\x00\x01\x00\x00\x0b\xb5\x00\x00\x01*\x00\x00\x00\x00\x00\x01\x00\x00\x05\xd6\x00\x00\x01\xcc\x00\x00\x00\x00\x00\x01\x00\x00\x08\xb3\x00\x00\x02&\x00\x00\x00\x00\x00\x01\x00\x00\x0aE\x00\x00\x03R\x00\x00\x00\x00\x00\x01\x00\x00\x11\x1c\x00\x00\x02\xf4\x00\x00\x00\x00\x00\x01\x00\x00\x0f\x86"
def qInitResources():
    QtCore.qRegisterResourceData(0x01, qt_resource_struct, qt_resource_name, qt_resource_data)

def qCleanupResources():
    QtCore.qUnregisterResourceData(0x01, qt_resource_struct, qt_resource_name, qt_resource_data)

qInitResources()

########NEW FILE########
__FILENAME__ = run
# Make sure we use PySide (fixes OS X issue)
import os
os.environ['QT_API'] = 'pyside'

# Set up Traits toolkit.
from traits.etsconfig.etsconfig import ETSConfig
ETSConfig.toolkit = 'qt4'
ETSConfig.company = 'EEGSensor'

# Standard imports
import logging, os, datetime
import numpy as np

# Enthought imports
import traits.api as t
import traitsui.api as tui
from traitsui.api import (View, Label, Item, VGroup, HGroup,
                          spring, Heading)
from traitsui.qt4.extra.qt_view import QtView
from pyface.api import ImageResource
from pyface.timer.api import do_later
from apptools.preferences.api import Preferences

# Internal imports
from hardware import EEGSensor, SAMPLE_RATE, MAX_HISTORY_LENGTH
from matplotlib.figure import Figure
from mpl import MPLFigureEditor

# We package QDarkStyle for convenience. The most current version is
#  at https://pypi.python.org/pypi/QDarkStyle
#  or https://github.com/ColinDuquesnoy/QDarkStyleSheet
# This packages is simply for aesthetics.
import qdarkstyle

preferences = Preferences(filename=os.path.join(ETSConfig.get_application_home(True), 'preferences.ini'))

# Custom parameters.
X_WIDTH_S = 6.0
PLOT_STEP = 1

class SensorOperationController(tui.Controller):
    """ UI for controlling the hardware. """

    model = t.Instance(EEGSensor)
    connect = t.Button()
    disconnect = t.Button()

    def _connect_changed(self):
        self.model.connect()

    def _disconnect_changed(self):
        self.model.disconnect()

    traits_view = View(
                   HGroup(
                       spring,
                       VGroup(
                          HGroup(spring, Heading('EEG Sensor Controls'), spring),
                          VGroup(Item('com_port', style='simple', enabled_when="not object.connected"),
                                 Item('object.connected', style='readonly'),
                                 # Item('history_length', style='readonly'),
                                 # Item('timeseries_length', style='readonly'),
                                 show_labels=True
                                 ),
                          HGroup(# spring,
                              Item('controller.connect', enabled_when='not object.connected'),
                              Item('controller.disconnect', enabled_when='object.connected'),
                              spring,
                              show_labels=False),
                          Label('Last %d points saved to disk on exit.' % MAX_HISTORY_LENGTH),
                          ),
                       spring,
                       tui.VGrid(
                                Heading('Activate Ch:'),
                                Item('channel_1_on', label='1', enabled_when='not channel_1_enabled'),
                                Item('channel_2_on', label='2', enabled_when='not channel_2_enabled'),
                                Item('channel_3_on', label='3', enabled_when='not channel_3_enabled'),
                                Item('channel_4_on', label='4', enabled_when='not channel_4_enabled'),
                                Item('channel_5_on', label='5', enabled_when='not channel_5_enabled'),
                                Item('channel_6_on', label='6', enabled_when='not channel_6_enabled'),
                                Item('channel_7_on', label='7', enabled_when='not channel_7_enabled'),
                                Item('channel_8_on', label='8', enabled_when='not channel_8_enabled'),

                                Heading('Deactivate Ch:'),
                                Item('channel_1_off', label='1', enabled_when='channel_1_enabled'),
                                Item('channel_2_off', label='2', enabled_when='channel_2_enabled'),
                                Item('channel_3_off', label='3', enabled_when='channel_3_enabled'),
                                Item('channel_4_off', label='4', enabled_when='channel_4_enabled'),
                                Item('channel_5_off', label='5', enabled_when='channel_5_enabled'),
                                Item('channel_6_off', label='6', enabled_when='channel_6_enabled'),
                                Item('channel_7_off', label='7', enabled_when='channel_7_enabled'),
                                Item('channel_8_off', label='8', enabled_when='channel_8_enabled'),
                                show_labels=False,
                                show_border=True,
                                columns=9,
                                enabled_when='object.connected'
                            ),
                        spring,
                      ),
                   )

from scipy.signal import lfilter
class TimeDomainFilter(t.HasTraits):
    """ FIR filter """
    b = t.Array()
    a = t.Array()
    type = t.Enum(['BandPass'])

    def apply(self, signal):
        if self.type == 'BandPass':
            return lfilter(self.b, self.a, signal)
        else:
            raise NotImplementedError('Filter type %s not implemented' % self.type)

class SensorTimeseriesController(tui.ModelView):
    """ UI for a "ganged" timeseries plot. """
    model = t.Instance(EEGSensor)
    figure = t.Instance(Figure, ())
    lines = t.List(t.Any)
    axes = t.Any
    axes_r = t.Any
    filters = t.List(t.Instance(TimeDomainFilter))

    y_lim_uv = t.Float(100)

    view = View(Item('figure', editor=MPLFigureEditor(),
                            show_label=False,
                            springy=True,
                     full_size=True,),
                    width=400,
                    height=700,

                    resizable=True)

    def __init__(self, model=None, **metadata):
        """ Set up and initialize the plot. """
        tui.ModelView.__init__(self, model=model, **metadata)
        axes = self.figure.add_subplot(111)
        self.lines = []
        y_ticks = []
        y_labels = []
        y_labels2 = []
        for i in range(self.model.timeseries.shape[1] - 1):
            line, = axes.plot(self.model.timeseries[::PLOT_STEP, 0],
                              self.model.timeseries[::PLOT_STEP, i + 1] / self.y_lim_uv + i,
                              color='mistyrose',
                              alpha=.75,
                              linewidth=0.5)
            self.lines.append(line)
            y_ticks.append(i)
            y_labels.append('Ch %d' % (i + 1))
            y_labels2.append('Mean: 0.0\nRMS: 0.0')
        axes.set_title('EEG Timeseries')
        # axes.set_ylabel('Amplitude')
        axes.set_xlabel('Time [s]')
        axes.set_xlim(0, X_WIDTH_S, auto=False)
        axes.set_ylim(-1, self.model.timeseries.shape[1] - 1, auto=False)
        axes.set_yticks(y_ticks)
        axes.set_yticklabels(y_labels)
        self.axes = axes

        # Right axes
#         self.axes_r = self.figure.add_subplot(1, 1, 1, sharex=axes, frameon=False)
#         self.axes_r.yaxis.tick_right()
#         self.axes_r.yaxis.set_label_position("right")
#         self.axes_r.set_yticks(y_ticks)
#         self.axes_r.tick_params(axis='y', which='both', length=0)
#         self.axes_r.set_yticklabels(y_labels2, {'size':8})
#         self.axes_r.set_ylim(-1, self.model.timeseries.shape[1] - 1, auto=False)

        # l/b/r/t
        do_later(self.figure.tight_layout)  # optimize padding and layout after everything's set up.


    @t.on_trait_change('model.data_changed')
    def update_plot(self):
        """ Update the plot with new data """
        if self.model.timeseries.shape[0] < 2:
            return
        y_labels2 = []
        for i, line in enumerate(self.lines):
            y = self.model.timeseries[:, i + 1]
            nan_mask = np.isnan(y)
            y[nan_mask] = 0  # otherwise, a single NAN causes the filtering to fail.
            y = y - y.mean()
            for filter in self.filters:
                # Note that we re-apply the time-domain filter for every single update.
                y = filter.apply(y)

            y[nan_mask] = np.NAN  # put the NAN's back so they're not plotted.
            line.set_data(self.model.timeseries[::PLOT_STEP, 0] ,  # x
                          y[::PLOT_STEP] / self.y_lim_uv + i  # y
                          )
            y_labels2.append('Mean: %0.3f\nRMS: %0.3f' %
                             (y.mean(), np.sqrt(np.mean(np.square(y))))
                             )

#         self.axes_r.set_yticklabels(y_labels2, {'size':6})
        self.axes.set_xlim(max(np.max(self.model.timeseries[:, 0]), X_WIDTH_S) - X_WIDTH_S,
                      max(np.max(self.model.timeseries[:, 0]), X_WIDTH_S))
        self.figure.canvas.draw()


class SensorFFTController(tui.ModelView):
    """ UI for spectral plot. """

    model = t.Instance(EEGSensor)
    figure = t.Instance(Figure, ())
    lines = t.List(t.Any)
    axes = t.Any

    n_fft = t.Int(256)
    overlap = t.Float(0.75)

    view = View(Item('figure', editor=MPLFigureEditor(),
                            show_label=False,
                            springy=True,
                            full_size=True,),
                    width=350,
                    height=450,
                    resizable=True)

    def __init__(self, model=None, **metadata):
        """ Setup and initialize the plot. """
        tui.ModelView.__init__(self, model=model, **metadata)
        axes = self.figure.add_subplot(111)
        self.lines = []
        for i in range(self.model.timeseries.shape[1] - 1):
            line, = axes.plot([0], [1],
                              color='mistyrose',
                              alpha=.5)
            self.lines.append(line)

        axes.set_title('Frequency Content')
        axes.set_ylabel(r'Signal Strength ($\mu$V/sqrt(Hz))')
        axes.set_xlabel('Frequency (Hz)')
        axes.set_xticks([i * 10 for i in range(10)])  # multiples of 10
        axes.set_xlim(0, 65,  # SAMPLE_RATE / 2,
                      auto=False)

#         axes.set_ylim(-1, self.model.timeseries.shape[1] - 1, auto=False)
#         axes.set_yticks(y_ticks)
#         axes.set_yticklabels(y_labels)
        axes.set_yscale('log')
        self.axes = axes
        # l/b/r/t
        do_later(self.figure.tight_layout)  # optimize padding and layout after everything's set up.

    def _windowed_fft(self, data, fs):
        """ Applies a Hanning window, calculates FFT, and returns one-sided
        FFT as well as corresponding frequency vector.
        """
        N = len(data)
        window = np.hanning(N)
        win_pow = np.mean(window ** 2)
        windowed_data = np.fft.fft(data * window) / np.sqrt(win_pow)
        # freqs = np.linspace(0, 1, N, endpoint=True) * fs
        pD = np.abs(windowed_data * np.conjugate(windowed_data) / N ** 2)
        freqs = np.fft.fftfreq(N, 1 / float(fs))
        f = freqs[:N / 2 ]
        pD = pD[:N / 2 ]
        pD[1:] = pD[1:] * 2
        return pD, f

    @t.on_trait_change('model.data_changed')
    def update_plot(self):
        """ Update the plot with new data """
        n_data_pts = self.model.timeseries.shape[0]
        if n_data_pts < self.n_fft:
            return

        if n_data_pts >= 2 * self.n_fft:
            n_offset = 2 * self.n_fft
        else:
            n_offset = self.n_fft

        data_to_process = self.model.timeseries[-n_offset:]

        hz_per_bin = float(SAMPLE_RATE) / self.n_fft

        min_psds = []
        max_psds = []
        for i, line in enumerate(self.lines):
            y = data_to_process[:, i + 1]
            nan_mask = np.isnan(y)
            y[nan_mask] = 0  # otherwise, a single NAN causes the filtering to fail.
            y = y - y.mean()
            psd, f = self._windowed_fft(y, SAMPLE_RATE)
            psd_per_bin = psd / hz_per_bin
            line.set_data(f,  # x
                          np.sqrt(psd_per_bin)  # y
                          )
            min_psds.append(psd_per_bin.min())
            max_psds.append(psd_per_bin.max())
        self.axes.set_ylim(.1,
                           100)  # np.min(min_psds) * .75 + 1e-10, np.max(max_psds) * 1.33)
        self.figure.canvas.draw()




class AppHandler(tui.Handler):
    def close(self, info, isok):
        app = info.object  # convenience
        app.sensor.disconnect()
        file_name = os.path.join(ETSConfig.get_application_home(True),
                                 'sensor_output %s.csv' % str(datetime.datetime.now()).replace(':', '-'))
        # make sure directory exists.
        if not os.path.exists(ETSConfig.get_application_home(False)):
            os.makedirs(ETSConfig.get_application_home(False))
        arr = np.array(app.sensor.history)

        if not arr.size:
            return isok

        np.savetxt(file_name,
                   arr)
        msg = 'Output (size %s) saved to %s.' % (str(arr.shape), file_name)
        logging.info(msg)
        from pyface.api import information
        information(info.ui.control, msg, title='Array saved to disk.')
        return isok

#     def position(self, info):
#         """ Maximize the window... """
#         ret = tui.Handler.position(self, info)
#         info.ui.control.showMaximized()
#         return ret

class EEGSensorApp(t.HasTraits):

    sensor = t.Instance(EEGSensor)
    filters = t.List(t.Instance(TimeDomainFilter))

    sensor_operation_controller = t.Instance(SensorOperationController)
    def _sensor_operation_controller_default(self):
        return SensorOperationController(model=self.sensor)

    sensor_timeseries_controller = t.Instance(SensorTimeseriesController)
    def _sensor_timeseries_controller_default(self):
        return SensorTimeseriesController(model=self.sensor,
                                          filters=self.filters)

    sensor_fft_controller = t.Instance(SensorFFTController)
    def _sensor_fft_controller_default(self):
        return SensorFFTController(model=self.sensor)


    traits_view = QtView(
                     HGroup(
                         VGroup(
                            Item('sensor_timeseries_controller', style='custom'),
                            show_border=True,
                            show_labels=False
                          ),
                         VGroup(
                            Item('sensor_fft_controller', style='custom'),
                            Item('sensor_operation_controller', style='custom'),
                            show_border=True,
                            show_labels=False
                          ),
                        ),

                    title="EEG Sensor Console",
                    icon=ImageResource('application'),
                    # style_sheet_path='dark_style_sheet.qss',
                    style_sheet=qdarkstyle.load_stylesheet(pyside=True),
                    resizable=True,
                    handler=AppHandler(),
                    )


if __name__ == "__main__":
    try:
        logging.info('---------- STARTING ---------')
        from scipy.io import loadmat
        mat = loadmat('bp_filter_coeff.mat')
        filters = [TimeDomainFilter(b=mat['bp_filter_coeff']['b'][0, 0].squeeze(),
                                    a=mat['bp_filter_coeff']['a'][0, 0].squeeze()),
                   TimeDomainFilter(b=mat['bp_filter_coeff']['b_notch'][0, 0].squeeze(),
                                    a=mat['bp_filter_coeff']['a_notch'][0, 0].squeeze()), ]
        app = EEGSensorApp(sensor=EEGSensor(preferences=preferences),
                           filters=filters)
        app.configure_traits(id='eeg_main_app')
    finally:
        preferences.flush()
        logging.shutdown()


########NEW FILE########
__FILENAME__ = rfc2217
#! python
#
# Python Serial Port Extension for Win32, Linux, BSD, Jython
# see __init__.py
#
# This module implements a RFC2217 compatible client. RF2217 descibes a
# protocol to access serial ports over TCP/IP and allows setting the baud rate,
# modem control lines etc.
#
# (C) 2001-2013 Chris Liechti <cliechti@gmx.net>
# this is distributed under a free software license, see license.txt

# TODO:
# - setting control line -> answer is not checked (had problems with one of the
#   severs). consider implementing a compatibility mode flag to make check
#   conditional
# - write timeout not implemented at all

##############################################################################
# observations and issues with servers
#=============================================================================
# sredird V2.2.1
# - http://www.ibiblio.org/pub/Linux/system/serial/   sredird-2.2.2.tar.gz
# - does not acknowledge SET_CONTROL (RTS/DTR) correctly, always responding
#   [105 1] instead of the actual value.
# - SET_BAUDRATE answer contains 4 extra null bytes -> probably for larger
#   numbers than 2**32?
# - To get the signature [COM_PORT_OPTION 0] has to be sent.
# - run a server: while true; do nc -l -p 7000 -c "sredird debug /dev/ttyUSB0 /var/lock/sredir"; done
#=============================================================================
# telnetcpcd (untested)
# - http://ftp.wayne.edu/kermit/sredird/telnetcpcd-1.09.tar.gz
# - To get the signature [COM_PORT_OPTION] w/o data has to be sent.
#=============================================================================
# ser2net
# - does not negotiate BINARY or COM_PORT_OPTION for his side but at least
#   acknowledges that the client activates these options
# - The configuration may be that the server prints a banner. As this client
#   implementation does a flushInput on connect, this banner is hidden from
#   the user application.
# - NOTIFY_MODEMSTATE: the poll interval of the server seems to be one
#   second.
# - To get the signature [COM_PORT_OPTION 0] has to be sent.
# - run a server: run ser2net daemon, in /etc/ser2net.conf:
#     2000:telnet:0:/dev/ttyS0:9600 remctl banner
##############################################################################

# How to identify ports? pySerial might want to support other protocols in the
# future, so lets use an URL scheme.
# for RFC2217 compliant servers we will use this:
#    rfc2217://<host>:<port>[/option[/option...]]
#
# options:
# - "debug" print diagnostic messages
# - "ign_set_control": do not look at the answers to SET_CONTROL
# - "poll_modem": issue NOTIFY_MODEMSTATE requests when CTS/DTR/RI/CD is read.
#   Without this option it expects that the server sends notifications
#   automatically on change (which most servers do and is according to the
#   RFC).
# the order of the options is not relevant

from serial.serialutil import *
import time
import struct
import socket
import threading
import Queue
import logging

# port string is expected to be something like this:
# rfc2217://host:port
# host may be an IP or including domain, whatever.
# port is 0...65535

# map log level names to constants. used in fromURL()
LOGGER_LEVELS = {
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    }


# telnet protocol characters
IAC  = to_bytes([255]) # Interpret As Command
DONT = to_bytes([254])
DO   = to_bytes([253])
WONT = to_bytes([252])
WILL = to_bytes([251])
IAC_DOUBLED = to_bytes([IAC, IAC])

SE  = to_bytes([240])  # Subnegotiation End
NOP = to_bytes([241])  # No Operation
DM  = to_bytes([242])  # Data Mark
BRK = to_bytes([243])  # Break
IP  = to_bytes([244])  # Interrupt process
AO  = to_bytes([245])  # Abort output
AYT = to_bytes([246])  # Are You There
EC  = to_bytes([247])  # Erase Character
EL  = to_bytes([248])  # Erase Line
GA  = to_bytes([249])  # Go Ahead
SB =  to_bytes([250])  # Subnegotiation Begin

# selected telnet options
BINARY = to_bytes([0]) # 8-bit data path
ECHO = to_bytes([1])   # echo
SGA = to_bytes([3])    # suppress go ahead

# RFC2217
COM_PORT_OPTION = to_bytes([44])

# Client to Access Server
SET_BAUDRATE = to_bytes([1])
SET_DATASIZE = to_bytes([2])
SET_PARITY = to_bytes([3])
SET_STOPSIZE = to_bytes([4])
SET_CONTROL = to_bytes([5])
NOTIFY_LINESTATE = to_bytes([6])
NOTIFY_MODEMSTATE = to_bytes([7])
FLOWCONTROL_SUSPEND = to_bytes([8])
FLOWCONTROL_RESUME = to_bytes([9])
SET_LINESTATE_MASK = to_bytes([10])
SET_MODEMSTATE_MASK = to_bytes([11])
PURGE_DATA = to_bytes([12])

SERVER_SET_BAUDRATE = to_bytes([101])
SERVER_SET_DATASIZE = to_bytes([102])
SERVER_SET_PARITY = to_bytes([103])
SERVER_SET_STOPSIZE = to_bytes([104])
SERVER_SET_CONTROL = to_bytes([105])
SERVER_NOTIFY_LINESTATE = to_bytes([106])
SERVER_NOTIFY_MODEMSTATE = to_bytes([107])
SERVER_FLOWCONTROL_SUSPEND = to_bytes([108])
SERVER_FLOWCONTROL_RESUME = to_bytes([109])
SERVER_SET_LINESTATE_MASK = to_bytes([110])
SERVER_SET_MODEMSTATE_MASK = to_bytes([111])
SERVER_PURGE_DATA = to_bytes([112])

RFC2217_ANSWER_MAP = {
    SET_BAUDRATE: SERVER_SET_BAUDRATE,
    SET_DATASIZE: SERVER_SET_DATASIZE,
    SET_PARITY: SERVER_SET_PARITY,
    SET_STOPSIZE: SERVER_SET_STOPSIZE,
    SET_CONTROL: SERVER_SET_CONTROL,
    NOTIFY_LINESTATE: SERVER_NOTIFY_LINESTATE,
    NOTIFY_MODEMSTATE: SERVER_NOTIFY_MODEMSTATE,
    FLOWCONTROL_SUSPEND: SERVER_FLOWCONTROL_SUSPEND,
    FLOWCONTROL_RESUME: SERVER_FLOWCONTROL_RESUME,
    SET_LINESTATE_MASK: SERVER_SET_LINESTATE_MASK,
    SET_MODEMSTATE_MASK: SERVER_SET_MODEMSTATE_MASK,
    PURGE_DATA: SERVER_PURGE_DATA,
}

SET_CONTROL_REQ_FLOW_SETTING = to_bytes([0])        # Request Com Port Flow Control Setting (outbound/both)
SET_CONTROL_USE_NO_FLOW_CONTROL = to_bytes([1])     # Use No Flow Control (outbound/both)
SET_CONTROL_USE_SW_FLOW_CONTROL = to_bytes([2])     # Use XON/XOFF Flow Control (outbound/both)
SET_CONTROL_USE_HW_FLOW_CONTROL = to_bytes([3])     # Use HARDWARE Flow Control (outbound/both)
SET_CONTROL_REQ_BREAK_STATE = to_bytes([4])         # Request BREAK State
SET_CONTROL_BREAK_ON = to_bytes([5])                # Set BREAK State ON
SET_CONTROL_BREAK_OFF = to_bytes([6])               # Set BREAK State OFF
SET_CONTROL_REQ_DTR = to_bytes([7])                 # Request DTR Signal State
SET_CONTROL_DTR_ON = to_bytes([8])                  # Set DTR Signal State ON
SET_CONTROL_DTR_OFF = to_bytes([9])                 # Set DTR Signal State OFF
SET_CONTROL_REQ_RTS = to_bytes([10])                # Request RTS Signal State
SET_CONTROL_RTS_ON = to_bytes([11])                 # Set RTS Signal State ON
SET_CONTROL_RTS_OFF = to_bytes([12])                # Set RTS Signal State OFF
SET_CONTROL_REQ_FLOW_SETTING_IN = to_bytes([13])    # Request Com Port Flow Control Setting (inbound)
SET_CONTROL_USE_NO_FLOW_CONTROL_IN = to_bytes([14]) # Use No Flow Control (inbound)
SET_CONTROL_USE_SW_FLOW_CONTOL_IN = to_bytes([15])  # Use XON/XOFF Flow Control (inbound)
SET_CONTROL_USE_HW_FLOW_CONTOL_IN = to_bytes([16])  # Use HARDWARE Flow Control (inbound)
SET_CONTROL_USE_DCD_FLOW_CONTROL = to_bytes([17])   # Use DCD Flow Control (outbound/both)
SET_CONTROL_USE_DTR_FLOW_CONTROL = to_bytes([18])   # Use DTR Flow Control (inbound)
SET_CONTROL_USE_DSR_FLOW_CONTROL = to_bytes([19])   # Use DSR Flow Control (outbound/both)

LINESTATE_MASK_TIMEOUT = 128                # Time-out Error
LINESTATE_MASK_SHIFTREG_EMPTY = 64          # Transfer Shift Register Empty
LINESTATE_MASK_TRANSREG_EMPTY = 32          # Transfer Holding Register Empty
LINESTATE_MASK_BREAK_DETECT = 16            # Break-detect Error
LINESTATE_MASK_FRAMING_ERROR = 8            # Framing Error
LINESTATE_MASK_PARTIY_ERROR = 4             # Parity Error
LINESTATE_MASK_OVERRUN_ERROR = 2            # Overrun Error
LINESTATE_MASK_DATA_READY = 1               # Data Ready

MODEMSTATE_MASK_CD = 128                    # Receive Line Signal Detect (also known as Carrier Detect)
MODEMSTATE_MASK_RI = 64                     # Ring Indicator
MODEMSTATE_MASK_DSR = 32                    # Data-Set-Ready Signal State
MODEMSTATE_MASK_CTS = 16                    # Clear-To-Send Signal State
MODEMSTATE_MASK_CD_CHANGE = 8               # Delta Receive Line Signal Detect
MODEMSTATE_MASK_RI_CHANGE = 4               # Trailing-edge Ring Detector
MODEMSTATE_MASK_DSR_CHANGE = 2              # Delta Data-Set-Ready
MODEMSTATE_MASK_CTS_CHANGE = 1              # Delta Clear-To-Send

PURGE_RECEIVE_BUFFER = to_bytes([1])        # Purge access server receive data buffer
PURGE_TRANSMIT_BUFFER = to_bytes([2])       # Purge access server transmit data buffer
PURGE_BOTH_BUFFERS = to_bytes([3])          # Purge both the access server receive data buffer and the access server transmit data buffer


RFC2217_PARITY_MAP = {
    PARITY_NONE: 1,
    PARITY_ODD: 2,
    PARITY_EVEN: 3,
    PARITY_MARK: 4,
    PARITY_SPACE: 5,
}
RFC2217_REVERSE_PARITY_MAP = dict((v,k) for k,v in RFC2217_PARITY_MAP.items())

RFC2217_STOPBIT_MAP = {
    STOPBITS_ONE: 1,
    STOPBITS_ONE_POINT_FIVE: 3,
    STOPBITS_TWO: 2,
}
RFC2217_REVERSE_STOPBIT_MAP = dict((v,k) for k,v in RFC2217_STOPBIT_MAP.items())

# Telnet filter states
M_NORMAL = 0
M_IAC_SEEN = 1
M_NEGOTIATE = 2

# TelnetOption and TelnetSubnegotiation states
REQUESTED = 'REQUESTED'
ACTIVE = 'ACTIVE'
INACTIVE = 'INACTIVE'
REALLY_INACTIVE = 'REALLY_INACTIVE'

class TelnetOption(object):
    """Manage a single telnet option, keeps track of DO/DONT WILL/WONT."""

    def __init__(self, connection, name, option, send_yes, send_no, ack_yes, ack_no, initial_state, activation_callback=None):
        """\
        Initialize option.
        :param connection: connection used to transmit answers
        :param name: a readable name for debug outputs
        :param send_yes: what to send when option is to be enabled.
        :param send_no: what to send when option is to be disabled.
        :param ack_yes: what to expect when remote agrees on option.
        :param ack_no: what to expect when remote disagrees on option.
        :param initial_state: options initialized with REQUESTED are tried to
            be enabled on startup. use INACTIVE for all others.
        """
        self.connection = connection
        self.name = name
        self.option = option
        self.send_yes = send_yes
        self.send_no = send_no
        self.ack_yes = ack_yes
        self.ack_no = ack_no
        self.state = initial_state
        self.active = False
        self.activation_callback = activation_callback

    def __repr__(self):
        """String for debug outputs"""
        return "%s:%s(%s)" % (self.name, self.active, self.state)

    def process_incoming(self, command):
        """A DO/DONT/WILL/WONT was received for this option, update state and
        answer when needed."""
        if command == self.ack_yes:
            if self.state is REQUESTED:
                self.state = ACTIVE
                self.active = True
                if self.activation_callback is not None:
                    self.activation_callback()
            elif self.state is ACTIVE:
                pass
            elif self.state is INACTIVE:
                self.state = ACTIVE
                self.connection.telnetSendOption(self.send_yes, self.option)
                self.active = True
                if self.activation_callback is not None:
                    self.activation_callback()
            elif self.state is REALLY_INACTIVE:
                self.connection.telnetSendOption(self.send_no, self.option)
            else:
                raise ValueError('option in illegal state %r' % self)
        elif command == self.ack_no:
            if self.state is REQUESTED:
                self.state = INACTIVE
                self.active = False
            elif self.state is ACTIVE:
                self.state = INACTIVE
                self.connection.telnetSendOption(self.send_no, self.option)
                self.active = False
            elif self.state is INACTIVE:
                pass
            elif self.state is REALLY_INACTIVE:
                pass
            else:
                raise ValueError('option in illegal state %r' % self)


class TelnetSubnegotiation(object):
    """\
    A object to handle subnegotiation of options. In this case actually
    sub-sub options for RFC 2217. It is used to track com port options.
    """

    def __init__(self, connection, name, option, ack_option=None):
        if ack_option is None: ack_option = option
        self.connection = connection
        self.name = name
        self.option = option
        self.value = None
        self.ack_option = ack_option
        self.state = INACTIVE

    def __repr__(self):
        """String for debug outputs."""
        return "%s:%s" % (self.name, self.state)

    def set(self, value):
        """\
        request a change of the value. a request is sent to the server. if
        the client needs to know if the change is performed he has to check the
        state of this object.
        """
        self.value = value
        self.state = REQUESTED
        self.connection.rfc2217SendSubnegotiation(self.option, self.value)
        if self.connection.logger:
            self.connection.logger.debug("SB Requesting %s -> %r" % (self.name, self.value))

    def isReady(self):
        """\
        check if answer from server has been received. when server rejects
        the change, raise a ValueError.
        """
        if self.state == REALLY_INACTIVE:
            raise ValueError("remote rejected value for option %r" % (self.name))
        return self.state == ACTIVE
    # add property to have a similar interface as TelnetOption
    active = property(isReady)

    def wait(self, timeout=3):
        """\
        wait until the subnegotiation has been acknowledged or timeout. It
        can also throw a value error when the answer from the server does not
        match the value sent.
        """
        timeout_time = time.time() + timeout
        while time.time() < timeout_time:
            time.sleep(0.05)    # prevent 100% CPU load
            if self.isReady():
                break
        else:
            raise SerialException("timeout while waiting for option %r" % (self.name))

    def checkAnswer(self, suboption):
        """\
        check an incoming subnegotiation block. the parameter already has
        cut off the header like sub option number and com port option value.
        """
        if self.value == suboption[:len(self.value)]:
            self.state = ACTIVE
        else:
            # error propagation done in isReady
            self.state = REALLY_INACTIVE
        if self.connection.logger:
            self.connection.logger.debug("SB Answer %s -> %r -> %s" % (self.name, suboption, self.state))


class RFC2217Serial(SerialBase):
    """Serial port implementation for RFC 2217 remote serial ports."""

    BAUDRATES = (50, 75, 110, 134, 150, 200, 300, 600, 1200, 1800, 2400, 4800,
                 9600, 19200, 38400, 57600, 115200)

    def open(self):
        """\
        Open port with current settings. This may throw a SerialException
        if the port cannot be opened.
        """
        self.logger = None
        self._ignore_set_control_answer = False
        self._poll_modem_state = False
        self._network_timeout = 3
        if self._port is None:
            raise SerialException("Port must be configured before it can be used.")
        if self._isOpen:
            raise SerialException("Port is already open.")
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.connect(self.fromURL(self.portstr))
            self._socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except Exception, msg:
            self._socket = None
            raise SerialException("Could not open port %s: %s" % (self.portstr, msg))

        self._socket.settimeout(5) # XXX good value?

        # use a thread save queue as buffer. it also simplifies implementing
        # the read timeout
        self._read_buffer = Queue.Queue()
        # to ensure that user writes does not interfere with internal
        # telnet/rfc2217 options establish a lock
        self._write_lock = threading.Lock()
        # name the following separately so that, below, a check can be easily done
        mandadory_options = [
            TelnetOption(self, 'we-BINARY', BINARY, WILL, WONT, DO, DONT, INACTIVE),
            TelnetOption(self, 'we-RFC2217', COM_PORT_OPTION, WILL, WONT, DO, DONT, REQUESTED),
        ]
        # all supported telnet options
        self._telnet_options = [
            TelnetOption(self, 'ECHO', ECHO, DO, DONT, WILL, WONT, REQUESTED),
            TelnetOption(self, 'we-SGA', SGA, WILL, WONT, DO, DONT, REQUESTED),
            TelnetOption(self, 'they-SGA', SGA, DO, DONT, WILL, WONT, REQUESTED),
            TelnetOption(self, 'they-BINARY', BINARY, DO, DONT, WILL, WONT, INACTIVE),
            TelnetOption(self, 'they-RFC2217', COM_PORT_OPTION, DO, DONT, WILL, WONT, REQUESTED),
        ] + mandadory_options
        # RFC 2217 specific states
        # COM port settings
        self._rfc2217_port_settings = {
            'baudrate': TelnetSubnegotiation(self, 'baudrate', SET_BAUDRATE, SERVER_SET_BAUDRATE),
            'datasize': TelnetSubnegotiation(self, 'datasize', SET_DATASIZE, SERVER_SET_DATASIZE),
            'parity':   TelnetSubnegotiation(self, 'parity',   SET_PARITY,   SERVER_SET_PARITY),
            'stopsize': TelnetSubnegotiation(self, 'stopsize', SET_STOPSIZE, SERVER_SET_STOPSIZE),
            }
        # There are more subnegotiation objects, combine all in one dictionary
        # for easy access
        self._rfc2217_options = {
            'purge':    TelnetSubnegotiation(self, 'purge',    PURGE_DATA,   SERVER_PURGE_DATA),
            'control':  TelnetSubnegotiation(self, 'control',  SET_CONTROL,  SERVER_SET_CONTROL),
            }
        self._rfc2217_options.update(self._rfc2217_port_settings)
        # cache for line and modem states that the server sends to us
        self._linestate = 0
        self._modemstate = None
        self._modemstate_expires = 0
        # RFC 2217 flow control between server and client
        self._remote_suspend_flow = False

        self._thread = threading.Thread(target=self._telnetReadLoop)
        self._thread.setDaemon(True)
        self._thread.setName('pySerial RFC 2217 reader thread for %s' % (self._port,))
        self._thread.start()

        # negotiate Telnet/RFC 2217 -> send initial requests
        for option in self._telnet_options:
            if option.state is REQUESTED:
                self.telnetSendOption(option.send_yes, option.option)
        # now wait until important options are negotiated
        timeout_time = time.time() + self._network_timeout
        while time.time() < timeout_time:
            time.sleep(0.05)    # prevent 100% CPU load
            if sum(o.active for o in mandadory_options) == len(mandadory_options):
                break
        else:
            raise SerialException("Remote does not seem to support RFC2217 or BINARY mode %r" % mandadory_options)
        if self.logger:
            self.logger.info("Negotiated options: %s" % self._telnet_options)

        # fine, go on, set RFC 2271 specific things
        self._reconfigurePort()
        # all things set up get, now a clean start
        self._isOpen = True
        if not self._rtscts:
            self.setRTS(True)
            self.setDTR(True)
        self.flushInput()
        self.flushOutput()

    def _reconfigurePort(self):
        """Set communication parameters on opened port."""
        if self._socket is None:
            raise SerialException("Can only operate on open ports")

        # if self._timeout != 0 and self._interCharTimeout is not None:
            # XXX

        if self._writeTimeout is not None:
            raise NotImplementedError('writeTimeout is currently not supported')
            # XXX

        # Setup the connection
        # to get good performance, all parameter changes are sent first...
        if not isinstance(self._baudrate, (int, long)) or not 0 < self._baudrate < 2**32:
            raise ValueError("invalid baudrate: %r" % (self._baudrate))
        self._rfc2217_port_settings['baudrate'].set(struct.pack('!I', self._baudrate))
        self._rfc2217_port_settings['datasize'].set(struct.pack('!B', self._bytesize))
        self._rfc2217_port_settings['parity'].set(struct.pack('!B', RFC2217_PARITY_MAP[self._parity]))
        self._rfc2217_port_settings['stopsize'].set(struct.pack('!B', RFC2217_STOPBIT_MAP[self._stopbits]))

        # and now wait until parameters are active
        items = self._rfc2217_port_settings.values()
        if self.logger:
            self.logger.debug("Negotiating settings: %s" % (items,))
        timeout_time = time.time() + self._network_timeout
        while time.time() < timeout_time:
            time.sleep(0.05)    # prevent 100% CPU load
            if sum(o.active for o in items) == len(items):
                break
        else:
            raise SerialException("Remote does not accept parameter change (RFC2217): %r" % items)
        if self.logger:
            self.logger.info("Negotiated settings: %s" % (items,))

        if self._rtscts and self._xonxoff:
            raise ValueError('xonxoff and rtscts together are not supported')
        elif self._rtscts:
            self.rfc2217SetControl(SET_CONTROL_USE_HW_FLOW_CONTROL)
        elif self._xonxoff:
            self.rfc2217SetControl(SET_CONTROL_USE_SW_FLOW_CONTROL)
        else:
            self.rfc2217SetControl(SET_CONTROL_USE_NO_FLOW_CONTROL)

    def close(self):
        """Close port"""
        if self._isOpen:
            if self._socket:
                try:
                    self._socket.shutdown(socket.SHUT_RDWR)
                    self._socket.close()
                except:
                    # ignore errors.
                    pass
                self._socket = None
            if self._thread:
                self._thread.join()
            self._isOpen = False
            # in case of quick reconnects, give the server some time
            time.sleep(0.3)

    def makeDeviceName(self, port):
        raise SerialException("there is no sensible way to turn numbers into URLs")

    def fromURL(self, url):
        """extract host and port from an URL string"""
        if url.lower().startswith("rfc2217://"): url = url[10:]
        try:
            # is there a "path" (our options)?
            if '/' in url:
                # cut away options
                url, options = url.split('/', 1)
                # process options now, directly altering self
                for option in options.split('/'):
                    if '=' in option:
                        option, value = option.split('=', 1)
                    else:
                        value = None
                    if option == 'logging':
                        logging.basicConfig()   # XXX is that good to call it here?
                        self.logger = logging.getLogger('pySerial.rfc2217')
                        self.logger.setLevel(LOGGER_LEVELS[value])
                        self.logger.debug('enabled logging')
                    elif option == 'ign_set_control':
                        self._ignore_set_control_answer = True
                    elif option == 'poll_modem':
                        self._poll_modem_state = True
                    elif option == 'timeout':
                        self._network_timeout = float(value)
                    else:
                        raise ValueError('unknown option: %r' % (option,))
            # get host and port
            host, port = url.split(':', 1) # may raise ValueError because of unpacking
            port = int(port)               # and this if it's not a number
            if not 0 <= port < 65536: raise ValueError("port not in range 0...65535")
        except ValueError, e:
            raise SerialException('expected a string in the form "[rfc2217://]<host>:<port>[/option[/option...]]": %s' % e)
        return (host, port)

    #  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -

    def inWaiting(self):
        """Return the number of characters currently in the input buffer."""
        if not self._isOpen: raise portNotOpenError
        return self._read_buffer.qsize()

    def read(self, size=1):
        """\
        Read size bytes from the serial port. If a timeout is set it may
        return less characters as requested. With no timeout it will block
        until the requested number of bytes is read.
        """
        if not self._isOpen: raise portNotOpenError
        data = bytearray()
        try:
            while len(data) < size:
                if self._thread is None:
                    raise SerialException('connection failed (reader thread died)')
                data.append(self._read_buffer.get(True, self._timeout))
        except Queue.Empty: # -> timeout
            pass
        return bytes(data)

    def write(self, data):
        """\
        Output the given string over the serial port. Can block if the
        connection is blocked. May raise SerialException if the connection is
        closed.
        """
        if not self._isOpen: raise portNotOpenError
        self._write_lock.acquire()
        try:
            try:
                self._socket.sendall(to_bytes(data).replace(IAC, IAC_DOUBLED))
            except socket.error, e:
                raise SerialException("connection failed (socket error): %s" % e) # XXX what exception if socket connection fails
        finally:
            self._write_lock.release()
        return len(data)

    def flushInput(self):
        """Clear input buffer, discarding all that is in the buffer."""
        if not self._isOpen: raise portNotOpenError
        self.rfc2217SendPurge(PURGE_RECEIVE_BUFFER)
        # empty read buffer
        while self._read_buffer.qsize():
            self._read_buffer.get(False)

    def flushOutput(self):
        """\
        Clear output buffer, aborting the current output and
        discarding all that is in the buffer.
        """
        if not self._isOpen: raise portNotOpenError
        self.rfc2217SendPurge(PURGE_TRANSMIT_BUFFER)

    def sendBreak(self, duration=0.25):
        """Send break condition. Timed, returns to idle state after given
        duration."""
        if not self._isOpen: raise portNotOpenError
        self.setBreak(True)
        time.sleep(duration)
        self.setBreak(False)

    def setBreak(self, level=True):
        """\
        Set break: Controls TXD. When active, to transmitting is
        possible.
        """
        if not self._isOpen: raise portNotOpenError
        if self.logger:
            self.logger.info('set BREAK to %s' % ('inactive', 'active')[bool(level)])
        if level:
            self.rfc2217SetControl(SET_CONTROL_BREAK_ON)
        else:
            self.rfc2217SetControl(SET_CONTROL_BREAK_OFF)

    def setRTS(self, level=True):
        """Set terminal status line: Request To Send."""
        if not self._isOpen: raise portNotOpenError
        if self.logger:
            self.logger.info('set RTS to %s' % ('inactive', 'active')[bool(level)])
        if level:
            self.rfc2217SetControl(SET_CONTROL_RTS_ON)
        else:
            self.rfc2217SetControl(SET_CONTROL_RTS_OFF)

    def setDTR(self, level=True):
        """Set terminal status line: Data Terminal Ready."""
        if not self._isOpen: raise portNotOpenError
        if self.logger:
            self.logger.info('set DTR to %s' % ('inactive', 'active')[bool(level)])
        if level:
            self.rfc2217SetControl(SET_CONTROL_DTR_ON)
        else:
            self.rfc2217SetControl(SET_CONTROL_DTR_OFF)

    def getCTS(self):
        """Read terminal status line: Clear To Send."""
        if not self._isOpen: raise portNotOpenError
        return bool(self.getModemState() & MODEMSTATE_MASK_CTS)

    def getDSR(self):
        """Read terminal status line: Data Set Ready."""
        if not self._isOpen: raise portNotOpenError
        return bool(self.getModemState() & MODEMSTATE_MASK_DSR)

    def getRI(self):
        """Read terminal status line: Ring Indicator."""
        if not self._isOpen: raise portNotOpenError
        return bool(self.getModemState() & MODEMSTATE_MASK_RI)

    def getCD(self):
        """Read terminal status line: Carrier Detect."""
        if not self._isOpen: raise portNotOpenError
        return bool(self.getModemState() & MODEMSTATE_MASK_CD)

    # - - - platform specific - - -
    # None so far

    # - - - RFC2217 specific - - -

    def _telnetReadLoop(self):
        """read loop for the socket."""
        mode = M_NORMAL
        suboption = None
        try:
            while self._socket is not None:
                try:
                    data = self._socket.recv(1024)
                except socket.timeout:
                    # just need to get out of recv form time to time to check if
                    # still alive
                    continue
                except socket.error, e:
                    # connection fails -> terminate loop
                    if self.logger:
                        self.logger.debug("socket error in reader thread: %s" % (e,))
                    break
                if not data: break # lost connection
                for byte in data:
                    if mode == M_NORMAL:
                        # interpret as command or as data
                        if byte == IAC:
                            mode = M_IAC_SEEN
                        else:
                            # store data in read buffer or sub option buffer
                            # depending on state
                            if suboption is not None:
                                suboption.append(byte)
                            else:
                                self._read_buffer.put(byte)
                    elif mode == M_IAC_SEEN:
                        if byte == IAC:
                            # interpret as command doubled -> insert character
                            # itself
                            if suboption is not None:
                                suboption.append(IAC)
                            else:
                                self._read_buffer.put(IAC)
                            mode = M_NORMAL
                        elif byte == SB:
                            # sub option start
                            suboption = bytearray()
                            mode = M_NORMAL
                        elif byte == SE:
                            # sub option end -> process it now
                            self._telnetProcessSubnegotiation(bytes(suboption))
                            suboption = None
                            mode = M_NORMAL
                        elif byte in (DO, DONT, WILL, WONT):
                            # negotiation
                            telnet_command = byte
                            mode = M_NEGOTIATE
                        else:
                            # other telnet commands
                            self._telnetProcessCommand(byte)
                            mode = M_NORMAL
                    elif mode == M_NEGOTIATE: # DO, DONT, WILL, WONT was received, option now following
                        self._telnetNegotiateOption(telnet_command, byte)
                        mode = M_NORMAL
        finally:
            self._thread = None
            if self.logger:
                self.logger.debug("read thread terminated")

    # - incoming telnet commands and options

    def _telnetProcessCommand(self, command):
        """Process commands other than DO, DONT, WILL, WONT."""
        # Currently none. RFC2217 only uses negotiation and subnegotiation.
        if self.logger:
            self.logger.warning("ignoring Telnet command: %r" % (command,))

    def _telnetNegotiateOption(self, command, option):
        """Process incoming DO, DONT, WILL, WONT."""
        # check our registered telnet options and forward command to them
        # they know themselves if they have to answer or not
        known = False
        for item in self._telnet_options:
            # can have more than one match! as some options are duplicated for
            # 'us' and 'them'
            if item.option == option:
                item.process_incoming(command)
                known = True
        if not known:
            # handle unknown options
            # only answer to positive requests and deny them
            if command == WILL or command == DO:
                self.telnetSendOption((command == WILL and DONT or WONT), option)
                if self.logger:
                    self.logger.warning("rejected Telnet option: %r" % (option,))


    def _telnetProcessSubnegotiation(self, suboption):
        """Process subnegotiation, the data between IAC SB and IAC SE."""
        if suboption[0:1] == COM_PORT_OPTION:
            if suboption[1:2] == SERVER_NOTIFY_LINESTATE and len(suboption) >= 3:
                self._linestate = ord(suboption[2:3]) # ensure it is a number
                if self.logger:
                    self.logger.info("NOTIFY_LINESTATE: %s" % self._linestate)
            elif suboption[1:2] == SERVER_NOTIFY_MODEMSTATE and len(suboption) >= 3:
                self._modemstate = ord(suboption[2:3]) # ensure it is a number
                if self.logger:
                    self.logger.info("NOTIFY_MODEMSTATE: %s" % self._modemstate)
                # update time when we think that a poll would make sense
                self._modemstate_expires = time.time() + 0.3
            elif suboption[1:2] == FLOWCONTROL_SUSPEND:
                self._remote_suspend_flow = True
            elif suboption[1:2] == FLOWCONTROL_RESUME:
                self._remote_suspend_flow = False
            else:
                for item in self._rfc2217_options.values():
                    if item.ack_option == suboption[1:2]:
                        #~ print "processing COM_PORT_OPTION: %r" % list(suboption[1:])
                        item.checkAnswer(bytes(suboption[2:]))
                        break
                else:
                    if self.logger:
                        self.logger.warning("ignoring COM_PORT_OPTION: %r" % (suboption,))
        else:
            if self.logger:
                self.logger.warning("ignoring subnegotiation: %r" % (suboption,))

    # - outgoing telnet commands and options

    def _internal_raw_write(self, data):
        """internal socket write with no data escaping. used to send telnet stuff."""
        self._write_lock.acquire()
        try:
            self._socket.sendall(data)
        finally:
            self._write_lock.release()

    def telnetSendOption(self, action, option):
        """Send DO, DONT, WILL, WONT."""
        self._internal_raw_write(to_bytes([IAC, action, option]))

    def rfc2217SendSubnegotiation(self, option, value=''):
        """Subnegotiation of RFC2217 parameters."""
        value = value.replace(IAC, IAC_DOUBLED)
        self._internal_raw_write(to_bytes([IAC, SB, COM_PORT_OPTION, option] + list(value) + [IAC, SE]))

    def rfc2217SendPurge(self, value):
        item = self._rfc2217_options['purge']
        item.set(value) # transmit desired purge type
        item.wait(self._network_timeout) # wait for acknowledge from the server

    def rfc2217SetControl(self, value):
        item = self._rfc2217_options['control']
        item.set(value) # transmit desired control type
        if self._ignore_set_control_answer:
            # answers are ignored when option is set. compatibility mode for
            # servers that answer, but not the expected one... (or no answer
            # at all) i.e. sredird
            time.sleep(0.1)  # this helps getting the unit tests passed
        else:
            item.wait(self._network_timeout)  # wait for acknowledge from the server

    def rfc2217FlowServerReady(self):
        """\
        check if server is ready to receive data. block for some time when
        not.
        """
        #~ if self._remote_suspend_flow:
            #~ wait---

    def getModemState(self):
        """\
        get last modem state (cached value. if value is "old", request a new
        one. this cache helps that we don't issue to many requests when e.g. all
        status lines, one after the other is queried by te user (getCTS, getDSR
        etc.)
        """
        # active modem state polling enabled? is the value fresh enough?
        if self._poll_modem_state and self._modemstate_expires < time.time():
            if self.logger:
                self.logger.debug('polling modem state')
            # when it is older, request an update
            self.rfc2217SendSubnegotiation(NOTIFY_MODEMSTATE)
            timeout_time = time.time() + self._network_timeout
            while time.time() < timeout_time:
                time.sleep(0.05)    # prevent 100% CPU load
                # when expiration time is updated, it means that there is a new
                # value
                if self._modemstate_expires > time.time():
                    if self.logger:
                        self.logger.warning('poll for modem state failed')
                    break
            # even when there is a timeout, do not generate an error just
            # return the last known value. this way we can support buggy
            # servers that do not respond to polls, but send automatic
            # updates.
        if self._modemstate is not None:
            if self.logger:
                self.logger.debug('using cached modem state')
            return self._modemstate
        else:
            # never received a notification from the server
            raise SerialException("remote sends no NOTIFY_MODEMSTATE")


# assemble Serial class with the platform specific implementation and the base
# for file-like behavior. for Python 2.6 and newer, that provide the new I/O
# library, derive from io.RawIOBase
try:
    import io
except ImportError:
    # classic version with our own file-like emulation
    class Serial(RFC2217Serial, FileLike):
        pass
else:
    # io library present
    class Serial(RFC2217Serial, io.RawIOBase):
        pass


#############################################################################
# The following is code that helps implementing an RFC 2217 server.

class PortManager(object):
    """\
    This class manages the state of Telnet and RFC 2217. It needs a serial
    instance and a connection to work with. Connection is expected to implement
    a (thread safe) write function, that writes the string to the network.
    """

    def __init__(self, serial_port, connection, logger=None):
        self.serial = serial_port
        self.connection = connection
        self.logger = logger
        self._client_is_rfc2217 = False

        # filter state machine
        self.mode = M_NORMAL
        self.suboption = None
        self.telnet_command = None

        # states for modem/line control events
        self.modemstate_mask = 255
        self.last_modemstate = None
        self.linstate_mask = 0

        # all supported telnet options
        self._telnet_options = [
            TelnetOption(self, 'ECHO', ECHO, WILL, WONT, DO, DONT, REQUESTED),
            TelnetOption(self, 'we-SGA', SGA, WILL, WONT, DO, DONT, REQUESTED),
            TelnetOption(self, 'they-SGA', SGA, DO, DONT, WILL, WONT, INACTIVE),
            TelnetOption(self, 'we-BINARY', BINARY, WILL, WONT, DO, DONT, INACTIVE),
            TelnetOption(self, 'they-BINARY', BINARY, DO, DONT, WILL, WONT, REQUESTED),
            TelnetOption(self, 'we-RFC2217', COM_PORT_OPTION, WILL, WONT, DO, DONT, REQUESTED, self._client_ok),
            TelnetOption(self, 'they-RFC2217', COM_PORT_OPTION, DO, DONT, WILL, WONT, INACTIVE, self._client_ok),
            ]

        # negotiate Telnet/RFC2217 -> send initial requests
        if self.logger:
            self.logger.debug("requesting initial Telnet/RFC 2217 options")
        for option in self._telnet_options:
            if option.state is REQUESTED:
                self.telnetSendOption(option.send_yes, option.option)
        # issue 1st modem state notification

    def _client_ok(self):
        """\
        callback of telnet option. it gets called when option is activated.
        this one here is used to detect when the client agrees on RFC 2217. a
        flag is set so that other functions like check_modem_lines know if the
        client is ok.
        """
        # The callback is used for we and they so if one party agrees, we're
        # already happy. it seems not all servers do the negotiation correctly
        # and i guess there are incorrect clients too.. so be happy if client
        # answers one or the other positively.
        self._client_is_rfc2217 = True
        if self.logger:
            self.logger.info("client accepts RFC 2217")
        # this is to ensure that the client gets a notification, even if there
        # was no change
        self.check_modem_lines(force_notification=True)

    # - outgoing telnet commands and options

    def telnetSendOption(self, action, option):
        """Send DO, DONT, WILL, WONT."""
        self.connection.write(to_bytes([IAC, action, option]))

    def rfc2217SendSubnegotiation(self, option, value=''):
        """Subnegotiation of RFC 2217 parameters."""
        value = value.replace(IAC, IAC_DOUBLED)
        self.connection.write(to_bytes([IAC, SB, COM_PORT_OPTION, option] + list(value) + [IAC, SE]))

    # - check modem lines, needs to be called periodically from user to
    # establish polling

    def check_modem_lines(self, force_notification=False):
        modemstate = (
            (self.serial.getCTS() and MODEMSTATE_MASK_CTS) |
            (self.serial.getDSR() and MODEMSTATE_MASK_DSR) |
            (self.serial.getRI() and MODEMSTATE_MASK_RI) |
            (self.serial.getCD() and MODEMSTATE_MASK_CD)
        )
        # check what has changed
        deltas = modemstate ^ (self.last_modemstate or 0) # when last is None -> 0
        if deltas & MODEMSTATE_MASK_CTS:
            modemstate |= MODEMSTATE_MASK_CTS_CHANGE
        if deltas & MODEMSTATE_MASK_DSR:
            modemstate |= MODEMSTATE_MASK_DSR_CHANGE
        if deltas & MODEMSTATE_MASK_RI:
            modemstate |= MODEMSTATE_MASK_RI_CHANGE
        if deltas & MODEMSTATE_MASK_CD:
            modemstate |= MODEMSTATE_MASK_CD_CHANGE
        # if new state is different and the mask allows this change, send
        # notification. suppress notifications when client is not rfc2217
        if modemstate != self.last_modemstate or force_notification:
            if (self._client_is_rfc2217 and (modemstate & self.modemstate_mask)) or force_notification:
                self.rfc2217SendSubnegotiation(
                    SERVER_NOTIFY_MODEMSTATE,
                    to_bytes([modemstate & self.modemstate_mask])
                    )
                if self.logger:
                    self.logger.info("NOTIFY_MODEMSTATE: %s" % (modemstate,))
            # save last state, but forget about deltas.
            # otherwise it would also notify about changing deltas which is
            # probably not very useful
            self.last_modemstate = modemstate & 0xf0

    # - outgoing data escaping

    def escape(self, data):
        """\
        this generator function is for the user. all outgoing data has to be
        properly escaped, so that no IAC character in the data stream messes up
        the Telnet state machine in the server.

        socket.sendall(escape(data))
        """
        for byte in data:
            if byte == IAC:
                yield IAC
                yield IAC
            else:
                yield byte

    # - incoming data filter

    def filter(self, data):
        """\
        handle a bunch of incoming bytes. this is a generator. it will yield
        all characters not of interest for Telnet/RFC 2217.

        The idea is that the reader thread pushes data from the socket through
        this filter:

        for byte in filter(socket.recv(1024)):
            # do things like CR/LF conversion/whatever
            # and write data to the serial port
            serial.write(byte)

        (socket error handling code left as exercise for the reader)
        """
        for byte in data:
            if self.mode == M_NORMAL:
                # interpret as command or as data
                if byte == IAC:
                    self.mode = M_IAC_SEEN
                else:
                    # store data in sub option buffer or pass it to our
                    # consumer depending on state
                    if self.suboption is not None:
                        self.suboption.append(byte)
                    else:
                        yield byte
            elif self.mode == M_IAC_SEEN:
                if byte == IAC:
                    # interpret as command doubled -> insert character
                    # itself
                    if self.suboption is not None:
                        self.suboption.append(byte)
                    else:
                        yield byte
                    self.mode = M_NORMAL
                elif byte == SB:
                    # sub option start
                    self.suboption = bytearray()
                    self.mode = M_NORMAL
                elif byte == SE:
                    # sub option end -> process it now
                    self._telnetProcessSubnegotiation(bytes(self.suboption))
                    self.suboption = None
                    self.mode = M_NORMAL
                elif byte in (DO, DONT, WILL, WONT):
                    # negotiation
                    self.telnet_command = byte
                    self.mode = M_NEGOTIATE
                else:
                    # other telnet commands
                    self._telnetProcessCommand(byte)
                    self.mode = M_NORMAL
            elif self.mode == M_NEGOTIATE: # DO, DONT, WILL, WONT was received, option now following
                self._telnetNegotiateOption(self.telnet_command, byte)
                self.mode = M_NORMAL

    # - incoming telnet commands and options

    def _telnetProcessCommand(self, command):
        """Process commands other than DO, DONT, WILL, WONT."""
        # Currently none. RFC2217 only uses negotiation and subnegotiation.
        if self.logger:
            self.logger.warning("ignoring Telnet command: %r" % (command,))

    def _telnetNegotiateOption(self, command, option):
        """Process incoming DO, DONT, WILL, WONT."""
        # check our registered telnet options and forward command to them
        # they know themselves if they have to answer or not
        known = False
        for item in self._telnet_options:
            # can have more than one match! as some options are duplicated for
            # 'us' and 'them'
            if item.option == option:
                item.process_incoming(command)
                known = True
        if not known:
            # handle unknown options
            # only answer to positive requests and deny them
            if command == WILL or command == DO:
                self.telnetSendOption((command == WILL and DONT or WONT), option)
                if self.logger:
                    self.logger.warning("rejected Telnet option: %r" % (option,))


    def _telnetProcessSubnegotiation(self, suboption):
        """Process subnegotiation, the data between IAC SB and IAC SE."""
        if suboption[0:1] == COM_PORT_OPTION:
            if self.logger:
                self.logger.debug('received COM_PORT_OPTION: %r' % (suboption,))
            if suboption[1:2] == SET_BAUDRATE:
                backup = self.serial.baudrate
                try:
                    (baudrate,) = struct.unpack("!I", suboption[2:6])
                    if baudrate != 0:
                        self.serial.baudrate = baudrate
                except ValueError, e:
                    if self.logger:
                        self.logger.error("failed to set baud rate: %s" % (e,))
                    self.serial.baudrate = backup
                else:
                    if self.logger:
                        self.logger.info("%s baud rate: %s" % (baudrate and 'set' or 'get', self.serial.baudrate))
                self.rfc2217SendSubnegotiation(SERVER_SET_BAUDRATE, struct.pack("!I", self.serial.baudrate))
            elif suboption[1:2] == SET_DATASIZE:
                backup = self.serial.bytesize
                try:
                    (datasize,) = struct.unpack("!B", suboption[2:3])
                    if datasize != 0:
                        self.serial.bytesize = datasize
                except ValueError, e:
                    if self.logger:
                        self.logger.error("failed to set data size: %s" % (e,))
                    self.serial.bytesize = backup
                else:
                    if self.logger:
                        self.logger.info("%s data size: %s" % (datasize and 'set' or 'get', self.serial.bytesize))
                self.rfc2217SendSubnegotiation(SERVER_SET_DATASIZE, struct.pack("!B", self.serial.bytesize))
            elif suboption[1:2] == SET_PARITY:
                backup = self.serial.parity
                try:
                    parity = struct.unpack("!B", suboption[2:3])[0]
                    if parity != 0:
                            self.serial.parity = RFC2217_REVERSE_PARITY_MAP[parity]
                except ValueError, e:
                    if self.logger:
                        self.logger.error("failed to set parity: %s" % (e,))
                    self.serial.parity = backup
                else:
                    if self.logger:
                        self.logger.info("%s parity: %s" % (parity and 'set' or 'get', self.serial.parity))
                self.rfc2217SendSubnegotiation(
                    SERVER_SET_PARITY,
                    struct.pack("!B", RFC2217_PARITY_MAP[self.serial.parity])
                    )
            elif suboption[1:2] == SET_STOPSIZE:
                backup = self.serial.stopbits
                try:
                    stopbits = struct.unpack("!B", suboption[2:3])[0]
                    if stopbits != 0:
                        self.serial.stopbits = RFC2217_REVERSE_STOPBIT_MAP[stopbits]
                except ValueError, e:
                    if self.logger:
                        self.logger.error("failed to set stop bits: %s" % (e,))
                    self.serial.stopbits = backup
                else:
                    if self.logger:
                        self.logger.info("%s stop bits: %s" % (stopbits and 'set' or 'get', self.serial.stopbits))
                self.rfc2217SendSubnegotiation(
                    SERVER_SET_STOPSIZE,
                    struct.pack("!B", RFC2217_STOPBIT_MAP[self.serial.stopbits])
                    )
            elif suboption[1:2] == SET_CONTROL:
                if suboption[2:3] == SET_CONTROL_REQ_FLOW_SETTING:
                    if self.serial.xonxoff:
                        self.rfc2217SendSubnegotiation(SERVER_SET_CONTROL, SET_CONTROL_USE_SW_FLOW_CONTROL)
                    elif self.serial.rtscts:
                        self.rfc2217SendSubnegotiation(SERVER_SET_CONTROL, SET_CONTROL_USE_HW_FLOW_CONTROL)
                    else:
                        self.rfc2217SendSubnegotiation(SERVER_SET_CONTROL, SET_CONTROL_USE_NO_FLOW_CONTROL)
                elif suboption[2:3] == SET_CONTROL_USE_NO_FLOW_CONTROL:
                    self.serial.xonxoff = False
                    self.serial.rtscts = False
                    if self.logger:
                        self.logger.info("changed flow control to None")
                    self.rfc2217SendSubnegotiation(SERVER_SET_CONTROL, SET_CONTROL_USE_NO_FLOW_CONTROL)
                elif suboption[2:3] == SET_CONTROL_USE_SW_FLOW_CONTROL:
                    self.serial.xonxoff = True
                    if self.logger:
                        self.logger.info("changed flow control to XON/XOFF")
                    self.rfc2217SendSubnegotiation(SERVER_SET_CONTROL, SET_CONTROL_USE_SW_FLOW_CONTROL)
                elif suboption[2:3] == SET_CONTROL_USE_HW_FLOW_CONTROL:
                    self.serial.rtscts = True
                    if self.logger:
                        self.logger.info("changed flow control to RTS/CTS")
                    self.rfc2217SendSubnegotiation(SERVER_SET_CONTROL, SET_CONTROL_USE_HW_FLOW_CONTROL)
                elif suboption[2:3] == SET_CONTROL_REQ_BREAK_STATE:
                    if self.logger:
                        self.logger.warning("requested break state - not implemented")
                    pass # XXX needs cached value
                elif suboption[2:3] == SET_CONTROL_BREAK_ON:
                    self.serial.setBreak(True)
                    if self.logger:
                        self.logger.info("changed BREAK to active")
                    self.rfc2217SendSubnegotiation(SERVER_SET_CONTROL, SET_CONTROL_BREAK_ON)
                elif suboption[2:3] == SET_CONTROL_BREAK_OFF:
                    self.serial.setBreak(False)
                    if self.logger:
                        self.logger.info("changed BREAK to inactive")
                    self.rfc2217SendSubnegotiation(SERVER_SET_CONTROL, SET_CONTROL_BREAK_OFF)
                elif suboption[2:3] == SET_CONTROL_REQ_DTR:
                    if self.logger:
                        self.logger.warning("requested DTR state - not implemented")
                    pass # XXX needs cached value
                elif suboption[2:3] == SET_CONTROL_DTR_ON:
                    self.serial.setDTR(True)
                    if self.logger:
                        self.logger.info("changed DTR to active")
                    self.rfc2217SendSubnegotiation(SERVER_SET_CONTROL, SET_CONTROL_DTR_ON)
                elif suboption[2:3] == SET_CONTROL_DTR_OFF:
                    self.serial.setDTR(False)
                    if self.logger:
                        self.logger.info("changed DTR to inactive")
                    self.rfc2217SendSubnegotiation(SERVER_SET_CONTROL, SET_CONTROL_DTR_OFF)
                elif suboption[2:3] == SET_CONTROL_REQ_RTS:
                    if self.logger:
                        self.logger.warning("requested RTS state - not implemented")
                    pass # XXX needs cached value
                    #~ self.rfc2217SendSubnegotiation(SERVER_SET_CONTROL, SET_CONTROL_RTS_ON)
                elif suboption[2:3] == SET_CONTROL_RTS_ON:
                    self.serial.setRTS(True)
                    if self.logger:
                        self.logger.info("changed RTS to active")
                    self.rfc2217SendSubnegotiation(SERVER_SET_CONTROL, SET_CONTROL_RTS_ON)
                elif suboption[2:3] == SET_CONTROL_RTS_OFF:
                    self.serial.setRTS(False)
                    if self.logger:
                        self.logger.info("changed RTS to inactive")
                    self.rfc2217SendSubnegotiation(SERVER_SET_CONTROL, SET_CONTROL_RTS_OFF)
                #~ elif suboption[2:3] == SET_CONTROL_REQ_FLOW_SETTING_IN:
                #~ elif suboption[2:3] == SET_CONTROL_USE_NO_FLOW_CONTROL_IN:
                #~ elif suboption[2:3] == SET_CONTROL_USE_SW_FLOW_CONTOL_IN:
                #~ elif suboption[2:3] == SET_CONTROL_USE_HW_FLOW_CONTOL_IN:
                #~ elif suboption[2:3] == SET_CONTROL_USE_DCD_FLOW_CONTROL:
                #~ elif suboption[2:3] == SET_CONTROL_USE_DTR_FLOW_CONTROL:
                #~ elif suboption[2:3] == SET_CONTROL_USE_DSR_FLOW_CONTROL:
            elif suboption[1:2] == NOTIFY_LINESTATE:
                # client polls for current state
                self.rfc2217SendSubnegotiation(
                    SERVER_NOTIFY_LINESTATE,
                    to_bytes([0])   # sorry, nothing like that implemented
                    )
            elif suboption[1:2] == NOTIFY_MODEMSTATE:
                if self.logger:
                    self.logger.info("request for modem state")
                # client polls for current state
                self.check_modem_lines(force_notification=True)
            elif suboption[1:2] == FLOWCONTROL_SUSPEND:
                if self.logger:
                    self.logger.info("suspend")
                self._remote_suspend_flow = True
            elif suboption[1:2] == FLOWCONTROL_RESUME:
                if self.logger:
                    self.logger.info("resume")
                self._remote_suspend_flow = False
            elif suboption[1:2] == SET_LINESTATE_MASK:
                self.linstate_mask = ord(suboption[2:3]) # ensure it is a number
                if self.logger:
                    self.logger.info("line state mask: 0x%02x" % (self.linstate_mask,))
            elif suboption[1:2] == SET_MODEMSTATE_MASK:
                self.modemstate_mask = ord(suboption[2:3]) # ensure it is a number
                if self.logger:
                    self.logger.info("modem state mask: 0x%02x" % (self.modemstate_mask,))
            elif suboption[1:2] == PURGE_DATA:
                if suboption[2:3] == PURGE_RECEIVE_BUFFER:
                    self.serial.flushInput()
                    if self.logger:
                        self.logger.info("purge in")
                    self.rfc2217SendSubnegotiation(SERVER_PURGE_DATA, PURGE_RECEIVE_BUFFER)
                elif suboption[2:3] == PURGE_TRANSMIT_BUFFER:
                    self.serial.flushOutput()
                    if self.logger:
                        self.logger.info("purge out")
                    self.rfc2217SendSubnegotiation(SERVER_PURGE_DATA, PURGE_TRANSMIT_BUFFER)
                elif suboption[2:3] == PURGE_BOTH_BUFFERS:
                    self.serial.flushInput()
                    self.serial.flushOutput()
                    if self.logger:
                        self.logger.info("purge both")
                    self.rfc2217SendSubnegotiation(SERVER_PURGE_DATA, PURGE_BOTH_BUFFERS)
                else:
                    if self.logger:
                        self.logger.error("undefined PURGE_DATA: %r" % list(suboption[2:]))
            else:
                if self.logger:
                    self.logger.error("undefined COM_PORT_OPTION: %r" % list(suboption[1:]))
        else:
            if self.logger:
                self.logger.warning("unknown subnegotiation: %r" % (suboption,))


# simple client test
if __name__ == '__main__':
    import sys
    s = Serial('rfc2217://localhost:7000', 115200)
    sys.stdout.write('%s\n' % s)

    #~ s.baudrate = 1898

    sys.stdout.write("write...\n")
    s.write("hello\n")
    s.flush()
    sys.stdout.write("read: %s\n" % s.read(5))

    #~ s.baudrate = 19200
    #~ s.databits = 7
    s.close()

########NEW FILE########
__FILENAME__ = serialcli
#! python
# Python Serial Port Extension for Win32, Linux, BSD, Jython and .NET/Mono
# serial driver for .NET/Mono (IronPython), .NET >= 2
# see __init__.py
#
# (C) 2008 Chris Liechti <cliechti@gmx.net>
# this is distributed under a free software license, see license.txt

import clr
import System
import System.IO.Ports
from serial.serialutil import *


def device(portnum):
    """Turn a port number into a device name"""
    return System.IO.Ports.SerialPort.GetPortNames()[portnum]


# must invoke function with byte array, make a helper to convert strings
# to byte arrays
sab = System.Array[System.Byte]
def as_byte_array(string):
    return sab([ord(x) for x in string])  # XXX will require adaption when run with a 3.x compatible IronPython

class IronSerial(SerialBase):
    """Serial port implementation for .NET/Mono."""

    BAUDRATES = (50, 75, 110, 134, 150, 200, 300, 600, 1200, 1800, 2400, 4800,
                9600, 19200, 38400, 57600, 115200)

    def open(self):
        """Open port with current settings. This may throw a SerialException
           if the port cannot be opened."""
        if self._port is None:
            raise SerialException("Port must be configured before it can be used.")
        if self._isOpen:
            raise SerialException("Port is already open.")
        try:
            self._port_handle = System.IO.Ports.SerialPort(self.portstr)
        except Exception, msg:
            self._port_handle = None
            raise SerialException("could not open port %s: %s" % (self.portstr, msg))

        self._reconfigurePort()
        self._port_handle.Open()
        self._isOpen = True
        if not self._rtscts:
            self.setRTS(True)
            self.setDTR(True)
        self.flushInput()
        self.flushOutput()

    def _reconfigurePort(self):
        """Set communication parameters on opened port."""
        if not self._port_handle:
            raise SerialException("Can only operate on a valid port handle")

        #~ self._port_handle.ReceivedBytesThreshold = 1

        if self._timeout is None:
            self._port_handle.ReadTimeout = System.IO.Ports.SerialPort.InfiniteTimeout
        else:
            self._port_handle.ReadTimeout = int(self._timeout*1000)

        # if self._timeout != 0 and self._interCharTimeout is not None:
            # timeouts = (int(self._interCharTimeout * 1000),) + timeouts[1:]

        if self._writeTimeout is None:
            self._port_handle.WriteTimeout = System.IO.Ports.SerialPort.InfiniteTimeout
        else:
            self._port_handle.WriteTimeout = int(self._writeTimeout*1000)


        # Setup the connection info.
        try:
            self._port_handle.BaudRate = self._baudrate
        except IOError, e:
            # catch errors from illegal baudrate settings
            raise ValueError(str(e))

        if self._bytesize == FIVEBITS:
            self._port_handle.DataBits     = 5
        elif self._bytesize == SIXBITS:
            self._port_handle.DataBits     = 6
        elif self._bytesize == SEVENBITS:
            self._port_handle.DataBits     = 7
        elif self._bytesize == EIGHTBITS:
            self._port_handle.DataBits     = 8
        else:
            raise ValueError("Unsupported number of data bits: %r" % self._bytesize)

        if self._parity == PARITY_NONE:
            self._port_handle.Parity       = getattr(System.IO.Ports.Parity, 'None') # reserved keyword in Py3k
        elif self._parity == PARITY_EVEN:
            self._port_handle.Parity       = System.IO.Ports.Parity.Even
        elif self._parity == PARITY_ODD:
            self._port_handle.Parity       = System.IO.Ports.Parity.Odd
        elif self._parity == PARITY_MARK:
            self._port_handle.Parity       = System.IO.Ports.Parity.Mark
        elif self._parity == PARITY_SPACE:
            self._port_handle.Parity       = System.IO.Ports.Parity.Space
        else:
            raise ValueError("Unsupported parity mode: %r" % self._parity)

        if self._stopbits == STOPBITS_ONE:
            self._port_handle.StopBits     = System.IO.Ports.StopBits.One
        elif self._stopbits == STOPBITS_ONE_POINT_FIVE:
            self._port_handle.StopBits     = System.IO.Ports.StopBits.OnePointFive
        elif self._stopbits == STOPBITS_TWO:
            self._port_handle.StopBits     = System.IO.Ports.StopBits.Two
        else:
            raise ValueError("Unsupported number of stop bits: %r" % self._stopbits)

        if self._rtscts and self._xonxoff:
            self._port_handle.Handshake  = System.IO.Ports.Handshake.RequestToSendXOnXOff
        elif self._rtscts:
            self._port_handle.Handshake  = System.IO.Ports.Handshake.RequestToSend
        elif self._xonxoff:
            self._port_handle.Handshake  = System.IO.Ports.Handshake.XOnXOff
        else:
            self._port_handle.Handshake  = getattr(System.IO.Ports.Handshake, 'None')   # reserved keyword in Py3k

    #~ def __del__(self):
        #~ self.close()

    def close(self):
        """Close port"""
        if self._isOpen:
            if self._port_handle:
                try:
                    self._port_handle.Close()
                except System.IO.Ports.InvalidOperationException:
                    # ignore errors. can happen for unplugged USB serial devices
                    pass
                self._port_handle = None
            self._isOpen = False

    def makeDeviceName(self, port):
        try:
            return device(port)
        except TypeError, e:
            raise SerialException(str(e))

    #  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -

    def inWaiting(self):
        """Return the number of characters currently in the input buffer."""
        if not self._port_handle: raise portNotOpenError
        return self._port_handle.BytesToRead

    def read(self, size=1):
        """Read size bytes from the serial port. If a timeout is set it may
           return less characters as requested. With no timeout it will block
           until the requested number of bytes is read."""
        if not self._port_handle: raise portNotOpenError
        # must use single byte reads as this is the only way to read
        # without applying encodings
        data = bytearray()
        while size:
            try:
                data.append(self._port_handle.ReadByte())
            except System.TimeoutException, e:
                break
            else:
                size -= 1
        return bytes(data)

    def write(self, data):
        """Output the given string over the serial port."""
        if not self._port_handle: raise portNotOpenError
        if not isinstance(data, (bytes, bytearray)):
            raise TypeError('expected %s or bytearray, got %s' % (bytes, type(data)))
        try:
            # must call overloaded method with byte array argument
            # as this is the only one not applying encodings
            self._port_handle.Write(as_byte_array(data), 0, len(data))
        except System.TimeoutException, e:
            raise writeTimeoutError
        return len(data)

    def flushInput(self):
        """Clear input buffer, discarding all that is in the buffer."""
        if not self._port_handle: raise portNotOpenError
        self._port_handle.DiscardInBuffer()

    def flushOutput(self):
        """Clear output buffer, aborting the current output and
        discarding all that is in the buffer."""
        if not self._port_handle: raise portNotOpenError
        self._port_handle.DiscardOutBuffer()

    def sendBreak(self, duration=0.25):
        """Send break condition. Timed, returns to idle state after given duration."""
        if not self._port_handle: raise portNotOpenError
        import time
        self._port_handle.BreakState = True
        time.sleep(duration)
        self._port_handle.BreakState = False

    def setBreak(self, level=True):
        """Set break: Controls TXD. When active, to transmitting is possible."""
        if not self._port_handle: raise portNotOpenError
        self._port_handle.BreakState = bool(level)

    def setRTS(self, level=True):
        """Set terminal status line: Request To Send"""
        if not self._port_handle: raise portNotOpenError
        self._port_handle.RtsEnable = bool(level)

    def setDTR(self, level=True):
        """Set terminal status line: Data Terminal Ready"""
        if not self._port_handle: raise portNotOpenError
        self._port_handle.DtrEnable = bool(level)

    def getCTS(self):
        """Read terminal status line: Clear To Send"""
        if not self._port_handle: raise portNotOpenError
        return self._port_handle.CtsHolding

    def getDSR(self):
        """Read terminal status line: Data Set Ready"""
        if not self._port_handle: raise portNotOpenError
        return self._port_handle.DsrHolding

    def getRI(self):
        """Read terminal status line: Ring Indicator"""
        if not self._port_handle: raise portNotOpenError
        #~ return self._port_handle.XXX
        return False #XXX an error would be better

    def getCD(self):
        """Read terminal status line: Carrier Detect"""
        if not self._port_handle: raise portNotOpenError
        return self._port_handle.CDHolding

    # - - platform specific - - - -
    # none


# assemble Serial class with the platform specific implementation and the base
# for file-like behavior. for Python 2.6 and newer, that provide the new I/O
# library, derive from io.RawIOBase
try:
    import io
except ImportError:
    # classic version with our own file-like emulation
    class Serial(IronSerial, FileLike):
        pass
else:
    # io library present
    class Serial(IronSerial, io.RawIOBase):
        pass


# Nur Testfunktion!!
if __name__ == '__main__':
    import sys

    s = Serial(0)
    sys.stdio.write('%s\n' % s)

    s = Serial()
    sys.stdio.write('%s\n' % s)


    s.baudrate = 19200
    s.databits = 7
    s.close()
    s.port = 0
    s.open()
    sys.stdio.write('%s\n' % s)


########NEW FILE########
__FILENAME__ = serialjava
#!jython
#
# Python Serial Port Extension for Win32, Linux, BSD, Jython
# module for serial IO for Jython and JavaComm
# see __init__.py
#
# (C) 2002-2008 Chris Liechti <cliechti@gmx.net>
# this is distributed under a free software license, see license.txt

from serial.serialutil import *

def my_import(name):
    mod = __import__(name)
    components = name.split('.')
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod


def detect_java_comm(names):
    """try given list of modules and return that imports"""
    for name in names:
        try:
            mod = my_import(name)
            mod.SerialPort
            return mod
        except (ImportError, AttributeError):
            pass
    raise ImportError("No Java Communications API implementation found")


# Java Communications API implementations
# http://mho.republika.pl/java/comm/

comm = detect_java_comm([
    'javax.comm', # Sun/IBM
    'gnu.io',     # RXTX
])


def device(portnumber):
    """Turn a port number into a device name"""
    enum = comm.CommPortIdentifier.getPortIdentifiers()
    ports = []
    while enum.hasMoreElements():
        el = enum.nextElement()
        if el.getPortType() == comm.CommPortIdentifier.PORT_SERIAL:
            ports.append(el)
    return ports[portnumber].getName()


class JavaSerial(SerialBase):
    """Serial port class, implemented with Java Communications API and
       thus usable with jython and the appropriate java extension."""

    def open(self):
        """Open port with current settings. This may throw a SerialException
           if the port cannot be opened."""
        if self._port is None:
            raise SerialException("Port must be configured before it can be used.")
        if self._isOpen:
            raise SerialException("Port is already open.")
        if type(self._port) == type(''):      # strings are taken directly
            portId = comm.CommPortIdentifier.getPortIdentifier(self._port)
        else:
            portId = comm.CommPortIdentifier.getPortIdentifier(device(self._port))     # numbers are transformed to a comport id obj
        try:
            self.sPort = portId.open("python serial module", 10)
        except Exception, msg:
            self.sPort = None
            raise SerialException("Could not open port: %s" % msg)
        self._reconfigurePort()
        self._instream = self.sPort.getInputStream()
        self._outstream = self.sPort.getOutputStream()
        self._isOpen = True

    def _reconfigurePort(self):
        """Set communication parameters on opened port."""
        if not self.sPort:
            raise SerialException("Can only operate on a valid port handle")

        self.sPort.enableReceiveTimeout(30)
        if self._bytesize == FIVEBITS:
            jdatabits = comm.SerialPort.DATABITS_5
        elif self._bytesize == SIXBITS:
            jdatabits = comm.SerialPort.DATABITS_6
        elif self._bytesize == SEVENBITS:
            jdatabits = comm.SerialPort.DATABITS_7
        elif self._bytesize == EIGHTBITS:
            jdatabits = comm.SerialPort.DATABITS_8
        else:
            raise ValueError("unsupported bytesize: %r" % self._bytesize)

        if self._stopbits == STOPBITS_ONE:
            jstopbits = comm.SerialPort.STOPBITS_1
        elif stopbits == STOPBITS_ONE_POINT_FIVE:
            self._jstopbits = comm.SerialPort.STOPBITS_1_5
        elif self._stopbits == STOPBITS_TWO:
            jstopbits = comm.SerialPort.STOPBITS_2
        else:
            raise ValueError("unsupported number of stopbits: %r" % self._stopbits)

        if self._parity == PARITY_NONE:
            jparity = comm.SerialPort.PARITY_NONE
        elif self._parity == PARITY_EVEN:
            jparity = comm.SerialPort.PARITY_EVEN
        elif self._parity == PARITY_ODD:
            jparity = comm.SerialPort.PARITY_ODD
        elif self._parity == PARITY_MARK:
            jparity = comm.SerialPort.PARITY_MARK
        elif self._parity == PARITY_SPACE:
            jparity = comm.SerialPort.PARITY_SPACE
        else:
            raise ValueError("unsupported parity type: %r" % self._parity)

        jflowin = jflowout = 0
        if self._rtscts:
            jflowin  |=  comm.SerialPort.FLOWCONTROL_RTSCTS_IN
            jflowout |=  comm.SerialPort.FLOWCONTROL_RTSCTS_OUT
        if self._xonxoff:
            jflowin  |=  comm.SerialPort.FLOWCONTROL_XONXOFF_IN
            jflowout |=  comm.SerialPort.FLOWCONTROL_XONXOFF_OUT

        self.sPort.setSerialPortParams(self._baudrate, jdatabits, jstopbits, jparity)
        self.sPort.setFlowControlMode(jflowin | jflowout)

        if self._timeout >= 0:
            self.sPort.enableReceiveTimeout(self._timeout*1000)
        else:
            self.sPort.disableReceiveTimeout()

    def close(self):
        """Close port"""
        if self._isOpen:
            if self.sPort:
                self._instream.close()
                self._outstream.close()
                self.sPort.close()
                self.sPort = None
            self._isOpen = False

    def makeDeviceName(self, port):
        return device(port)

    #  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -

    def inWaiting(self):
        """Return the number of characters currently in the input buffer."""
        if not self.sPort: raise portNotOpenError
        return self._instream.available()

    def read(self, size=1):
        """Read size bytes from the serial port. If a timeout is set it may
           return less characters as requested. With no timeout it will block
           until the requested number of bytes is read."""
        if not self.sPort: raise portNotOpenError
        read = bytearray()
        if size > 0:
            while len(read) < size:
                x = self._instream.read()
                if x == -1:
                    if self.timeout >= 0:
                        break
                else:
                    read.append(x)
        return bytes(read)

    def write(self, data):
        """Output the given string over the serial port."""
        if not self.sPort: raise portNotOpenError
        if not isinstance(data, (bytes, bytearray)):
            raise TypeError('expected %s or bytearray, got %s' % (bytes, type(data)))
        self._outstream.write(data)
        return len(data)

    def flushInput(self):
        """Clear input buffer, discarding all that is in the buffer."""
        if not self.sPort: raise portNotOpenError
        self._instream.skip(self._instream.available())

    def flushOutput(self):
        """Clear output buffer, aborting the current output and
        discarding all that is in the buffer."""
        if not self.sPort: raise portNotOpenError
        self._outstream.flush()

    def sendBreak(self, duration=0.25):
        """Send break condition. Timed, returns to idle state after given duration."""
        if not self.sPort: raise portNotOpenError
        self.sPort.sendBreak(duration*1000.0)

    def setBreak(self, level=1):
        """Set break: Controls TXD. When active, to transmitting is possible."""
        if self.fd is None: raise portNotOpenError
        raise SerialException("The setBreak function is not implemented in java.")

    def setRTS(self, level=1):
        """Set terminal status line: Request To Send"""
        if not self.sPort: raise portNotOpenError
        self.sPort.setRTS(level)

    def setDTR(self, level=1):
        """Set terminal status line: Data Terminal Ready"""
        if not self.sPort: raise portNotOpenError
        self.sPort.setDTR(level)

    def getCTS(self):
        """Read terminal status line: Clear To Send"""
        if not self.sPort: raise portNotOpenError
        self.sPort.isCTS()

    def getDSR(self):
        """Read terminal status line: Data Set Ready"""
        if not self.sPort: raise portNotOpenError
        self.sPort.isDSR()

    def getRI(self):
        """Read terminal status line: Ring Indicator"""
        if not self.sPort: raise portNotOpenError
        self.sPort.isRI()

    def getCD(self):
        """Read terminal status line: Carrier Detect"""
        if not self.sPort: raise portNotOpenError
        self.sPort.isCD()


# assemble Serial class with the platform specific implementation and the base
# for file-like behavior. for Python 2.6 and newer, that provide the new I/O
# library, derive from io.RawIOBase
try:
    import io
except ImportError:
    # classic version with our own file-like emulation
    class Serial(JavaSerial, FileLike):
        pass
else:
    # io library present
    class Serial(JavaSerial, io.RawIOBase):
        pass


if __name__ == '__main__':
    s = Serial(0,
         baudrate=19200,        # baudrate
         bytesize=EIGHTBITS,    # number of databits
         parity=PARITY_EVEN,    # enable parity checking
         stopbits=STOPBITS_ONE, # number of stopbits
         timeout=3,             # set a timeout value, None for waiting forever
         xonxoff=0,             # enable software flow control
         rtscts=0,              # enable RTS/CTS flow control
    )
    s.setRTS(1)
    s.setDTR(1)
    s.flushInput()
    s.flushOutput()
    s.write('hello')
    sys.stdio.write('%r\n' % s.read(5))
    sys.stdio.write('%s\n' % s.inWaiting())
    del s



########NEW FILE########
__FILENAME__ = serialposix
#!/usr/bin/env python
#
# Python Serial Port Extension for Win32, Linux, BSD, Jython
# module for serial IO for POSIX compatible systems, like Linux
# see __init__.py
#
# (C) 2001-2010 Chris Liechti <cliechti@gmx.net>
# this is distributed under a free software license, see license.txt
#
# parts based on code from Grant B. Edwards  <grante@visi.com>:
#  ftp://ftp.visi.com/users/grante/python/PosixSerial.py
#
# references: http://www.easysw.com/~mike/serial/serial.html

import sys, os, fcntl, termios, struct, select, errno, time
from serial.serialutil import *

# Do check the Python version as some constants have moved.
if (sys.hexversion < 0x020100f0):
    import TERMIOS
else:
    TERMIOS = termios

if (sys.hexversion < 0x020200f0):
    import FCNTL
else:
    FCNTL = fcntl

# try to detect the OS so that a device can be selected...
# this code block should supply a device() and set_special_baudrate() function
# for the platform
plat = sys.platform.lower()

if   plat[:5] == 'linux':    # Linux (confirmed)

    def device(port):
        return '/dev/ttyS%d' % port

    TCGETS2 = 0x802C542A
    TCSETS2 = 0x402C542B
    BOTHER = 0o010000

    def set_special_baudrate(port, baudrate):
        # right size is 44 on x86_64, allow for some growth
        import array
        buf = array.array('i', [0] * 64)

        try:
            # get serial_struct
            FCNTL.ioctl(port.fd, TCGETS2, buf)
            # set custom speed
            buf[2] &= ~TERMIOS.CBAUD
            buf[2] |= BOTHER
            buf[9] = buf[10] = baudrate

            # set serial_struct
            res = FCNTL.ioctl(port.fd, TCSETS2, buf)
        except IOError, e:
            raise ValueError('Failed to set custom baud rate (%s): %s' % (baudrate, e))

    baudrate_constants = {
        0:       0000000,  # hang up
        50:      0000001,
        75:      0000002,
        110:     0000003,
        134:     0000004,
        150:     0000005,
        200:     0000006,
        300:     0000007,
        600:     0000010,
        1200:    0000011,
        1800:    0000012,
        2400:    0000013,
        4800:    0000014,
        9600:    0000015,
        19200:   0000016,
        38400:   0000017,
        57600:   0010001,
        115200:  0010002,
        230400:  0010003,
        460800:  0010004,
        500000:  0010005,
        576000:  0010006,
        921600:  0010007,
        1000000: 0010010,
        1152000: 0010011,
        1500000: 0010012,
        2000000: 0010013,
        2500000: 0010014,
        3000000: 0010015,
        3500000: 0010016,
        4000000: 0010017
    }

elif plat == 'cygwin':       # cygwin/win32 (confirmed)

    def device(port):
        return '/dev/com%d' % (port + 1)

    def set_special_baudrate(port, baudrate):
        raise ValueError("sorry don't know how to handle non standard baud rate on this platform")

    baudrate_constants = {
        128000: 0x01003,
        256000: 0x01005,
        500000: 0x01007,
        576000: 0x01008,
        921600: 0x01009,
        1000000: 0x0100a,
        1152000: 0x0100b,
        1500000: 0x0100c,
        2000000: 0x0100d,
        2500000: 0x0100e,
        3000000: 0x0100f
    }

elif plat[:7] == 'openbsd':    # OpenBSD

    def device(port):
        return '/dev/cua%02d' % port

    def set_special_baudrate(port, baudrate):
        raise ValueError("sorry don't know how to handle non standard baud rate on this platform")

    baudrate_constants = {}

elif plat[:3] == 'bsd' or  \
    plat[:7] == 'freebsd':

    def device(port):
        return '/dev/cuad%d' % port

    def set_special_baudrate(port, baudrate):
        raise ValueError("sorry don't know how to handle non standard baud rate on this platform")

    baudrate_constants = {}

elif plat[:6] == 'darwin':   # OS X

    version = os.uname()[2].split('.')
    # Tiger or above can support arbitrary serial speeds
    if int(version[0]) >= 8:
        def set_special_baudrate(port, baudrate):
            # use IOKit-specific call to set up high speeds
            import array, fcntl
            buf = array.array('i', [baudrate])
            IOSSIOSPEED = 0x80045402 #_IOW('T', 2, speed_t)
            fcntl.ioctl(port.fd, IOSSIOSPEED, buf, 1)
    else: # version < 8
        def set_special_baudrate(port, baudrate):
            raise ValueError("baud rate not supported")

    def device(port):
        return '/dev/cuad%d' % port

    baudrate_constants = {}


elif plat[:6] == 'netbsd':   # NetBSD 1.6 testing by Erk

    def device(port):
        return '/dev/dty%02d' % port

    def set_special_baudrate(port, baudrate):
        raise ValueError("sorry don't know how to handle non standard baud rate on this platform")

    baudrate_constants = {}

elif plat[:4] == 'irix':     # IRIX (partially tested)

    def device(port):
        return '/dev/ttyf%d' % (port+1) #XXX different device names depending on flow control

    def set_special_baudrate(port, baudrate):
        raise ValueError("sorry don't know how to handle non standard baud rate on this platform")

    baudrate_constants = {}

elif plat[:2] == 'hp':       # HP-UX (not tested)

    def device(port):
        return '/dev/tty%dp0' % (port+1)

    def set_special_baudrate(port, baudrate):
        raise ValueError("sorry don't know how to handle non standard baud rate on this platform")

    baudrate_constants = {}

elif plat[:5] == 'sunos':    # Solaris/SunOS (confirmed)

    def device(port):
        return '/dev/tty%c' % (ord('a')+port)

    def set_special_baudrate(port, baudrate):
        raise ValueError("sorry don't know how to handle non standard baud rate on this platform")

    baudrate_constants = {}

elif plat[:3] == 'aix':      # AIX

    def device(port):
        return '/dev/tty%d' % (port)

    def set_special_baudrate(port, baudrate):
        raise ValueError("sorry don't know how to handle non standard baud rate on this platform")

    baudrate_constants = {}

else:
    # platform detection has failed...
    sys.stderr.write("""\
don't know how to number ttys on this system.
! Use an explicit path (eg /dev/ttyS1) or send this information to
! the author of this module:

sys.platform = %r
os.name = %r
serialposix.py version = %s

also add the device name of the serial port and where the
counting starts for the first serial port.
e.g. 'first serial port: /dev/ttyS0'
and with a bit luck you can get this module running...
""" % (sys.platform, os.name, VERSION))
    # no exception, just continue with a brave attempt to build a device name
    # even if the device name is not correct for the platform it has chances
    # to work using a string with the real device name as port parameter.
    def device(portum):
        return '/dev/ttyS%d' % portnum
    def set_special_baudrate(port, baudrate):
        raise SerialException("sorry don't know how to handle non standard baud rate on this platform")
    baudrate_constants = {}
    #~ raise Exception, "this module does not run on this platform, sorry."

# whats up with "aix", "beos", ....
# they should work, just need to know the device names.


# load some constants for later use.
# try to use values from TERMIOS, use defaults from linux otherwise
TIOCMGET  = hasattr(TERMIOS, 'TIOCMGET') and TERMIOS.TIOCMGET or 0x5415
TIOCMBIS  = hasattr(TERMIOS, 'TIOCMBIS') and TERMIOS.TIOCMBIS or 0x5416
TIOCMBIC  = hasattr(TERMIOS, 'TIOCMBIC') and TERMIOS.TIOCMBIC or 0x5417
TIOCMSET  = hasattr(TERMIOS, 'TIOCMSET') and TERMIOS.TIOCMSET or 0x5418

#TIOCM_LE = hasattr(TERMIOS, 'TIOCM_LE') and TERMIOS.TIOCM_LE or 0x001
TIOCM_DTR = hasattr(TERMIOS, 'TIOCM_DTR') and TERMIOS.TIOCM_DTR or 0x002
TIOCM_RTS = hasattr(TERMIOS, 'TIOCM_RTS') and TERMIOS.TIOCM_RTS or 0x004
#TIOCM_ST = hasattr(TERMIOS, 'TIOCM_ST') and TERMIOS.TIOCM_ST or 0x008
#TIOCM_SR = hasattr(TERMIOS, 'TIOCM_SR') and TERMIOS.TIOCM_SR or 0x010

TIOCM_CTS = hasattr(TERMIOS, 'TIOCM_CTS') and TERMIOS.TIOCM_CTS or 0x020
TIOCM_CAR = hasattr(TERMIOS, 'TIOCM_CAR') and TERMIOS.TIOCM_CAR or 0x040
TIOCM_RNG = hasattr(TERMIOS, 'TIOCM_RNG') and TERMIOS.TIOCM_RNG or 0x080
TIOCM_DSR = hasattr(TERMIOS, 'TIOCM_DSR') and TERMIOS.TIOCM_DSR or 0x100
TIOCM_CD  = hasattr(TERMIOS, 'TIOCM_CD') and TERMIOS.TIOCM_CD or TIOCM_CAR
TIOCM_RI  = hasattr(TERMIOS, 'TIOCM_RI') and TERMIOS.TIOCM_RI or TIOCM_RNG
#TIOCM_OUT1 = hasattr(TERMIOS, 'TIOCM_OUT1') and TERMIOS.TIOCM_OUT1 or 0x2000
#TIOCM_OUT2 = hasattr(TERMIOS, 'TIOCM_OUT2') and TERMIOS.TIOCM_OUT2 or 0x4000
if hasattr(TERMIOS, 'TIOCINQ'):
    TIOCINQ = TERMIOS.TIOCINQ
else:
    TIOCINQ = hasattr(TERMIOS, 'FIONREAD') and TERMIOS.FIONREAD or 0x541B
TIOCOUTQ   = hasattr(TERMIOS, 'TIOCOUTQ') and TERMIOS.TIOCOUTQ or 0x5411

TIOCM_zero_str = struct.pack('I', 0)
TIOCM_RTS_str = struct.pack('I', TIOCM_RTS)
TIOCM_DTR_str = struct.pack('I', TIOCM_DTR)

TIOCSBRK  = hasattr(TERMIOS, 'TIOCSBRK') and TERMIOS.TIOCSBRK or 0x5427
TIOCCBRK  = hasattr(TERMIOS, 'TIOCCBRK') and TERMIOS.TIOCCBRK or 0x5428


class PosixSerial(SerialBase):
    """Serial port class POSIX implementation. Serial port configuration is 
    done with termios and fcntl. Runs on Linux and many other Un*x like
    systems."""

    def open(self):
        """Open port with current settings. This may throw a SerialException
           if the port cannot be opened."""
        if self._port is None:
            raise SerialException("Port must be configured before it can be used.")
        if self._isOpen:
            raise SerialException("Port is already open.")
        self.fd = None
        # open
        try:
            self.fd = os.open(self.portstr, os.O_RDWR|os.O_NOCTTY|os.O_NONBLOCK)
        except IOError, msg:
            self.fd = None
            raise SerialException(msg.errno, "could not open port %s: %s" % (self._port, msg))
        #~ fcntl.fcntl(self.fd, FCNTL.F_SETFL, 0)  # set blocking

        try:
            self._reconfigurePort()
        except:
            try:
                os.close(self.fd)
            except:
                # ignore any exception when closing the port
                # also to keep original exception that happened when setting up
                pass
            self.fd = None
            raise
        else:
            self._isOpen = True
        self.flushInput()


    def _reconfigurePort(self):
        """Set communication parameters on opened port."""
        if self.fd is None:
            raise SerialException("Can only operate on a valid file descriptor")
        custom_baud = None

        vmin = vtime = 0                # timeout is done via select
        if self._interCharTimeout is not None:
            vmin = 1
            vtime = int(self._interCharTimeout * 10)
        try:
            orig_attr = termios.tcgetattr(self.fd)
            iflag, oflag, cflag, lflag, ispeed, ospeed, cc = orig_attr
        except termios.error, msg:      # if a port is nonexistent but has a /dev file, it'll fail here
            raise SerialException("Could not configure port: %s" % msg)
        # set up raw mode / no echo / binary
        cflag |=  (TERMIOS.CLOCAL|TERMIOS.CREAD)
        lflag &= ~(TERMIOS.ICANON|TERMIOS.ECHO|TERMIOS.ECHOE|TERMIOS.ECHOK|TERMIOS.ECHONL|
                     TERMIOS.ISIG|TERMIOS.IEXTEN) #|TERMIOS.ECHOPRT
        for flag in ('ECHOCTL', 'ECHOKE'): # netbsd workaround for Erk
            if hasattr(TERMIOS, flag):
                lflag &= ~getattr(TERMIOS, flag)

        oflag &= ~(TERMIOS.OPOST)
        iflag &= ~(TERMIOS.INLCR|TERMIOS.IGNCR|TERMIOS.ICRNL|TERMIOS.IGNBRK)
        if hasattr(TERMIOS, 'IUCLC'):
            iflag &= ~TERMIOS.IUCLC
        if hasattr(TERMIOS, 'PARMRK'):
            iflag &= ~TERMIOS.PARMRK

        # setup baud rate
        try:
            ispeed = ospeed = getattr(TERMIOS, 'B%s' % (self._baudrate))
        except AttributeError:
            try:
                ispeed = ospeed = baudrate_constants[self._baudrate]
            except KeyError:
                #~ raise ValueError('Invalid baud rate: %r' % self._baudrate)
                # may need custom baud rate, it isn't in our list.
                ispeed = ospeed = getattr(TERMIOS, 'B38400')
                try:
                    custom_baud = int(self._baudrate) # store for later
                except ValueError:
                    raise ValueError('Invalid baud rate: %r' % self._baudrate)
                else:
                    if custom_baud < 0:
                        raise ValueError('Invalid baud rate: %r' % self._baudrate)

        # setup char len
        cflag &= ~TERMIOS.CSIZE
        if self._bytesize == 8:
            cflag |= TERMIOS.CS8
        elif self._bytesize == 7:
            cflag |= TERMIOS.CS7
        elif self._bytesize == 6:
            cflag |= TERMIOS.CS6
        elif self._bytesize == 5:
            cflag |= TERMIOS.CS5
        else:
            raise ValueError('Invalid char len: %r' % self._bytesize)
        # setup stopbits
        if self._stopbits == STOPBITS_ONE:
            cflag &= ~(TERMIOS.CSTOPB)
        elif self._stopbits == STOPBITS_ONE_POINT_FIVE:
            cflag |=  (TERMIOS.CSTOPB)  # XXX same as TWO.. there is no POSIX support for 1.5
        elif self._stopbits == STOPBITS_TWO:
            cflag |=  (TERMIOS.CSTOPB)
        else:
            raise ValueError('Invalid stop bit specification: %r' % self._stopbits)
        # setup parity
        iflag &= ~(TERMIOS.INPCK|TERMIOS.ISTRIP)
        if self._parity == PARITY_NONE:
            cflag &= ~(TERMIOS.PARENB|TERMIOS.PARODD)
        elif self._parity == PARITY_EVEN:
            cflag &= ~(TERMIOS.PARODD)
            cflag |=  (TERMIOS.PARENB)
        elif self._parity == PARITY_ODD:
            cflag |=  (TERMIOS.PARENB|TERMIOS.PARODD)
        else:
            raise ValueError('Invalid parity: %r' % self._parity)
        # setup flow control
        # xonxoff
        if hasattr(TERMIOS, 'IXANY'):
            if self._xonxoff:
                iflag |=  (TERMIOS.IXON|TERMIOS.IXOFF) #|TERMIOS.IXANY)
            else:
                iflag &= ~(TERMIOS.IXON|TERMIOS.IXOFF|TERMIOS.IXANY)
        else:
            if self._xonxoff:
                iflag |=  (TERMIOS.IXON|TERMIOS.IXOFF)
            else:
                iflag &= ~(TERMIOS.IXON|TERMIOS.IXOFF)
        # rtscts
        if hasattr(TERMIOS, 'CRTSCTS'):
            if self._rtscts:
                cflag |=  (TERMIOS.CRTSCTS)
            else:
                cflag &= ~(TERMIOS.CRTSCTS)
        elif hasattr(TERMIOS, 'CNEW_RTSCTS'):   # try it with alternate constant name
            if self._rtscts:
                cflag |=  (TERMIOS.CNEW_RTSCTS)
            else:
                cflag &= ~(TERMIOS.CNEW_RTSCTS)
        # XXX should there be a warning if setting up rtscts (and xonxoff etc) fails??

        # buffer
        # vmin "minimal number of characters to be read. = for non blocking"
        if vmin < 0 or vmin > 255:
            raise ValueError('Invalid vmin: %r ' % vmin)
        cc[TERMIOS.VMIN] = vmin
        # vtime
        if vtime < 0 or vtime > 255:
            raise ValueError('Invalid vtime: %r' % vtime)
        cc[TERMIOS.VTIME] = vtime
        # activate settings
        if [iflag, oflag, cflag, lflag, ispeed, ospeed, cc] != orig_attr:
            termios.tcsetattr(self.fd, TERMIOS.TCSANOW, [iflag, oflag, cflag, lflag, ispeed, ospeed, cc])

        # apply custom baud rate, if any
        if custom_baud is not None:
            set_special_baudrate(self, custom_baud)

    def close(self):
        """Close port"""
        if self._isOpen:
            if self.fd is not None:
                os.close(self.fd)
                self.fd = None
            self._isOpen = False

    def makeDeviceName(self, port):
        return device(port)

    #  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -

    def inWaiting(self):
        """Return the number of characters currently in the input buffer."""
        #~ s = fcntl.ioctl(self.fd, TERMIOS.FIONREAD, TIOCM_zero_str)
        s = fcntl.ioctl(self.fd, TIOCINQ, TIOCM_zero_str)
        return struct.unpack('I',s)[0]

    # select based implementation, proved to work on many systems
    def read(self, size=1):
        """Read size bytes from the serial port. If a timeout is set it may
           return less characters as requested. With no timeout it will block
           until the requested number of bytes is read."""
        if not self._isOpen: raise portNotOpenError
        read = bytearray()
        while len(read) < size:
            try:
                ready,_,_ = select.select([self.fd],[],[], self._timeout)
                # If select was used with a timeout, and the timeout occurs, it
                # returns with empty lists -> thus abort read operation.
                # For timeout == 0 (non-blocking operation) also abort when there
                # is nothing to read.
                if not ready:
                    break   # timeout
                buf = os.read(self.fd, size-len(read))
                # read should always return some data as select reported it was
                # ready to read when we get to this point.
                if not buf:
                    # Disconnected devices, at least on Linux, show the
                    # behavior that they are always ready to read immediately
                    # but reading returns nothing.
                    raise SerialException('device reports readiness to read but returned no data (device disconnected or multiple access on port?)')
                read.extend(buf)
            except select.error, e:
                # ignore EAGAIN errors. all other errors are shown
                # see also http://www.python.org/dev/peps/pep-3151/#select
                if e[0] != errno.EAGAIN:
                    raise SerialException('read failed: %s' % (e,))
            except OSError, e:
                # ignore EAGAIN errors. all other errors are shown
                if e.errno != errno.EAGAIN:
                    raise SerialException('read failed: %s' % (e,))
        return bytes(read)

    def write(self, data):
        """Output the given string over the serial port."""
        if not self._isOpen: raise portNotOpenError
        d = to_bytes(data)
        tx_len = len(d)
        if self._writeTimeout is not None and self._writeTimeout > 0:
            timeout = time.time() + self._writeTimeout
        else:
            timeout = None
        while tx_len > 0:
            try:
                n = os.write(self.fd, d)
                if timeout:
                    # when timeout is set, use select to wait for being ready
                    # with the time left as timeout
                    timeleft = timeout - time.time()
                    if timeleft < 0:
                        raise writeTimeoutError
                    _, ready, _ = select.select([], [self.fd], [], timeleft)
                    if not ready:
                        raise writeTimeoutError
                else:
                    # wait for write operation
                    _, ready, _ = select.select([], [self.fd], [], None)
                    if not ready:
                        raise SerialException('write failed (select)')
                d = d[n:]
                tx_len -= n
            except OSError, v:
                if v.errno != errno.EAGAIN:
                    raise SerialException('write failed: %s' % (v,))
        return len(data)

    def flush(self):
        """Flush of file like objects. In this case, wait until all data
           is written."""
        self.drainOutput()

    def flushInput(self):
        """Clear input buffer, discarding all that is in the buffer."""
        if not self._isOpen: raise portNotOpenError
        termios.tcflush(self.fd, TERMIOS.TCIFLUSH)

    def flushOutput(self):
        """Clear output buffer, aborting the current output and
        discarding all that is in the buffer."""
        if not self._isOpen: raise portNotOpenError
        termios.tcflush(self.fd, TERMIOS.TCOFLUSH)

    def sendBreak(self, duration=0.25):
        """Send break condition. Timed, returns to idle state after given duration."""
        if not self._isOpen: raise portNotOpenError
        termios.tcsendbreak(self.fd, int(duration/0.25))

    def setBreak(self, level=1):
        """Set break: Controls TXD. When active, no transmitting is possible."""
        if self.fd is None: raise portNotOpenError
        if level:
            fcntl.ioctl(self.fd, TIOCSBRK)
        else:
            fcntl.ioctl(self.fd, TIOCCBRK)

    def setRTS(self, level=1):
        """Set terminal status line: Request To Send"""
        if not self._isOpen: raise portNotOpenError
        if level:
            fcntl.ioctl(self.fd, TIOCMBIS, TIOCM_RTS_str)
        else:
            fcntl.ioctl(self.fd, TIOCMBIC, TIOCM_RTS_str)

    def setDTR(self, level=1):
        """Set terminal status line: Data Terminal Ready"""
        if not self._isOpen: raise portNotOpenError
        if level:
            fcntl.ioctl(self.fd, TIOCMBIS, TIOCM_DTR_str)
        else:
            fcntl.ioctl(self.fd, TIOCMBIC, TIOCM_DTR_str)

    def getCTS(self):
        """Read terminal status line: Clear To Send"""
        if not self._isOpen: raise portNotOpenError
        s = fcntl.ioctl(self.fd, TIOCMGET, TIOCM_zero_str)
        return struct.unpack('I',s)[0] & TIOCM_CTS != 0

    def getDSR(self):
        """Read terminal status line: Data Set Ready"""
        if not self._isOpen: raise portNotOpenError
        s = fcntl.ioctl(self.fd, TIOCMGET, TIOCM_zero_str)
        return struct.unpack('I',s)[0] & TIOCM_DSR != 0

    def getRI(self):
        """Read terminal status line: Ring Indicator"""
        if not self._isOpen: raise portNotOpenError
        s = fcntl.ioctl(self.fd, TIOCMGET, TIOCM_zero_str)
        return struct.unpack('I',s)[0] & TIOCM_RI != 0

    def getCD(self):
        """Read terminal status line: Carrier Detect"""
        if not self._isOpen: raise portNotOpenError
        s = fcntl.ioctl(self.fd, TIOCMGET, TIOCM_zero_str)
        return struct.unpack('I',s)[0] & TIOCM_CD != 0

    # - - platform specific - - - -

    def outWaiting(self):
        """Return the number of characters currently in the output buffer."""
        #~ s = fcntl.ioctl(self.fd, TERMIOS.FIONREAD, TIOCM_zero_str)
        s = fcntl.ioctl(self.fd, TIOCOUTQ, TIOCM_zero_str)
        return struct.unpack('I',s)[0]

    def drainOutput(self):
        """internal - not portable!"""
        if not self._isOpen: raise portNotOpenError
        termios.tcdrain(self.fd)

    def nonblocking(self):
        """internal - not portable!"""
        if not self._isOpen: raise portNotOpenError
        fcntl.fcntl(self.fd, FCNTL.F_SETFL, os.O_NONBLOCK)

    def fileno(self):
        """\
        For easier use of the serial port instance with select.
        WARNING: this function is not portable to different platforms!
        """
        if not self._isOpen: raise portNotOpenError
        return self.fd

    def setXON(self, level=True):
        """\
        Manually control flow - when software flow control is enabled.
        This will send XON (true) and XOFF (false) to the other device.
        WARNING: this function is not portable to different platforms!
        """
        if not self.hComPort: raise portNotOpenError
        if enable:
            termios.tcflow(self.fd, TERMIOS.TCION)
        else:
            termios.tcflow(self.fd, TERMIOS.TCIOFF)

    def flowControlOut(self, enable):
        """\
        Manually control flow of outgoing data - when hardware or software flow
        control is enabled.
        WARNING: this function is not portable to different platforms!
        """
        if not self._isOpen: raise portNotOpenError
        if enable:
            termios.tcflow(self.fd, TERMIOS.TCOON)
        else:
            termios.tcflow(self.fd, TERMIOS.TCOOFF)


# assemble Serial class with the platform specifc implementation and the base
# for file-like behavior. for Python 2.6 and newer, that provide the new I/O
# library, derrive from io.RawIOBase
try:
    import io
except ImportError:
    # classic version with our own file-like emulation
    class Serial(PosixSerial, FileLike):
        pass
else:
    # io library present
    class Serial(PosixSerial, io.RawIOBase):
        pass

class PosixPollSerial(Serial):
    """poll based read implementation. not all systems support poll properly.
    however this one has better handling of errors, such as a device
    disconnecting while it's in use (e.g. USB-serial unplugged)"""

    def read(self, size=1):
        """Read size bytes from the serial port. If a timeout is set it may
           return less characters as requested. With no timeout it will block
           until the requested number of bytes is read."""
        if self.fd is None: raise portNotOpenError
        read = bytearray()
        poll = select.poll()
        poll.register(self.fd, select.POLLIN|select.POLLERR|select.POLLHUP|select.POLLNVAL)
        if size > 0:
            while len(read) < size:
                # print "\tread(): size",size, "have", len(read)    #debug
                # wait until device becomes ready to read (or something fails)
                for fd, event in poll.poll(self._timeout*1000):
                    if event & (select.POLLERR|select.POLLHUP|select.POLLNVAL):
                        raise SerialException('device reports error (poll)')
                    #  we don't care if it is select.POLLIN or timeout, that's
                    #  handled below
                buf = os.read(self.fd, size - len(read))
                read.extend(buf)
                if ((self._timeout is not None and self._timeout >= 0) or 
                    (self._interCharTimeout is not None and self._interCharTimeout > 0)) and not buf:
                    break   # early abort on timeout
        return bytes(read)


if __name__ == '__main__':
    s = Serial(0,
                 baudrate=19200,        # baud rate
                 bytesize=EIGHTBITS,    # number of data bits
                 parity=PARITY_EVEN,    # enable parity checking
                 stopbits=STOPBITS_ONE, # number of stop bits
                 timeout=3,             # set a timeout value, None for waiting forever
                 xonxoff=0,             # enable software flow control
                 rtscts=0,              # enable RTS/CTS flow control
               )
    s.setRTS(1)
    s.setDTR(1)
    s.flushInput()
    s.flushOutput()
    s.write('hello')
    sys.stdout.write('%r\n' % s.read(5))
    sys.stdout.write('%s\n' % s.inWaiting())
    del s


########NEW FILE########
__FILENAME__ = serialutil
#! python
# Python Serial Port Extension for Win32, Linux, BSD, Jython
# see __init__.py
#
# (C) 2001-2010 Chris Liechti <cliechti@gmx.net>
# this is distributed under a free software license, see license.txt

# compatibility for older Python < 2.6
try:
    bytes
    bytearray
except (NameError, AttributeError):
    # Python older than 2.6 do not have these types. Like for Python 2.6 they
    # should behave like str. For Python older than 3.0 we want to work with
    # strings anyway, only later versions have a true bytes type.
    bytes = str
    # bytearray is a mutable type that is easily turned into an instance of
    # bytes
    class bytearray(list):
        # for bytes(bytearray()) usage
        def __str__(self): return ''.join(self)
        def __repr__(self): return 'bytearray(%r)' % ''.join(self)
        # append automatically converts integers to characters
        def append(self, item):
            if isinstance(item, str):
                list.append(self, item)
            else:
                list.append(self, chr(item))
        # +=
        def __iadd__(self, other):
            for byte in other:
                self.append(byte)
            return self

        def __getslice__(self, i, j):
            return bytearray(list.__getslice__(self, i, j))

        def __getitem__(self, item):
            if isinstance(item, slice):
                return bytearray(list.__getitem__(self, item))
            else:
                return ord(list.__getitem__(self, item))

        def __eq__(self, other):
            if isinstance(other, basestring):
                other = bytearray(other)
            return list.__eq__(self, other)

# ``memoryview`` was introduced in Python 2.7 and ``bytes(some_memoryview)``
# isn't returning the contents (very unfortunate). Therefore we need special
# cases and test for it. Ensure that there is a ``memoryview`` object for older
# Python versions. This is easier than making every test dependent on its
# existence.
try:
    memoryview
except (NameError, AttributeError):
    # implementation does not matter as we do not realy use it.
    # it just must not inherit from something else we might care for.
    class memoryview:
        pass


# all Python versions prior 3.x convert ``str([17])`` to '[17]' instead of '\x11'
# so a simple ``bytes(sequence)`` doesn't work for all versions
def to_bytes(seq):
    """convert a sequence to a bytes type"""
    if isinstance(seq, bytes):
        return seq
    elif isinstance(seq, bytearray):
        return bytes(seq)
    elif isinstance(seq, memoryview):
        return seq.tobytes()
    else:
        b = bytearray()
        for item in seq:
            b.append(item)  # this one handles int and str for our emulation and ints for Python 3.x
        return bytes(b)

# create control bytes
XON  = to_bytes([17])
XOFF = to_bytes([19])

CR = to_bytes([13])
LF = to_bytes([10])


PARITY_NONE, PARITY_EVEN, PARITY_ODD, PARITY_MARK, PARITY_SPACE = 'N', 'E', 'O', 'M', 'S'
STOPBITS_ONE, STOPBITS_ONE_POINT_FIVE, STOPBITS_TWO = (1, 1.5, 2)
FIVEBITS, SIXBITS, SEVENBITS, EIGHTBITS = (5, 6, 7, 8)

PARITY_NAMES = {
    PARITY_NONE:  'None',
    PARITY_EVEN:  'Even',
    PARITY_ODD:   'Odd',
    PARITY_MARK:  'Mark',
    PARITY_SPACE: 'Space',
}


class SerialException(IOError):
    """Base class for serial port related exceptions."""


class SerialTimeoutException(SerialException):
    """Write timeouts give an exception"""


writeTimeoutError = SerialTimeoutException('Write timeout')
portNotOpenError = SerialException('Attempting to use a port that is not open')


class FileLike(object):
    """An abstract file like class.

    This class implements readline and readlines based on read and
    writelines based on write.
    This class is used to provide the above functions for to Serial
    port objects.

    Note that when the serial port was opened with _NO_ timeout that
    readline blocks until it sees a newline (or the specified size is
    reached) and that readlines would never return and therefore
    refuses to work (it raises an exception in this case)!
    """

    def __init__(self):
        self.closed = True

    def close(self):
        self.closed = True

    # so that ports are closed when objects are discarded
    def __del__(self):
        """Destructor.  Calls close()."""
        # The try/except block is in case this is called at program
        # exit time, when it's possible that globals have already been
        # deleted, and then the close() call might fail.  Since
        # there's nothing we can do about such failures and they annoy
        # the end users, we suppress the traceback.
        try:
            self.close()
        except:
            pass

    def writelines(self, sequence):
        for line in sequence:
            self.write(line)

    def flush(self):
        """flush of file like objects"""
        pass

    # iterator for e.g. "for line in Serial(0): ..." usage
    def next(self):
        line = self.readline()
        if not line: raise StopIteration
        return line

    def __iter__(self):
        return self

    def readline(self, size=None, eol=LF):
        """read a line which is terminated with end-of-line (eol) character
        ('\n' by default) or until timeout."""
        leneol = len(eol)
        line = bytearray()
        while True:
            c = self.read(1)
            if c:
                line += c
                if line[-leneol:] == eol:
                    break
                if size is not None and len(line) >= size:
                    break
            else:
                break
        return bytes(line)

    def readlines(self, sizehint=None, eol=LF):
        """read a list of lines, until timeout.
        sizehint is ignored."""
        if self.timeout is None:
            raise ValueError("Serial port MUST have enabled timeout for this function!")
        leneol = len(eol)
        lines = []
        while True:
            line = self.readline(eol=eol)
            if line:
                lines.append(line)
                if line[-leneol:] != eol:    # was the line received with a timeout?
                    break
            else:
                break
        return lines

    def xreadlines(self, sizehint=None):
        """Read lines, implemented as generator. It will raise StopIteration on
        timeout (empty read). sizehint is ignored."""
        while True:
            line = self.readline()
            if not line: break
            yield line

    # other functions of file-likes - not used by pySerial

    #~ readinto(b)

    def seek(self, pos, whence=0):
        raise IOError("file is not seekable")

    def tell(self):
        raise IOError("file is not seekable")

    def truncate(self, n=None):
        raise IOError("file is not seekable")

    def isatty(self):
        return False


class SerialBase(object):
    """Serial port base class. Provides __init__ function and properties to
       get/set port settings."""

    # default values, may be overridden in subclasses that do not support all values
    BAUDRATES = (50, 75, 110, 134, 150, 200, 300, 600, 1200, 1800, 2400, 4800,
                 9600, 19200, 38400, 57600, 115200, 230400, 460800, 500000,
                 576000, 921600, 1000000, 1152000, 1500000, 2000000, 2500000,
                 3000000, 3500000, 4000000)
    BYTESIZES = (FIVEBITS, SIXBITS, SEVENBITS, EIGHTBITS)
    PARITIES  = (PARITY_NONE, PARITY_EVEN, PARITY_ODD, PARITY_MARK, PARITY_SPACE)
    STOPBITS  = (STOPBITS_ONE, STOPBITS_ONE_POINT_FIVE, STOPBITS_TWO)

    def __init__(self,
                 port = None,           # number of device, numbering starts at
                                        # zero. if everything fails, the user
                                        # can specify a device string, note
                                        # that this isn't portable anymore
                                        # port will be opened if one is specified
                 baudrate=9600,         # baud rate
                 bytesize=EIGHTBITS,    # number of data bits
                 parity=PARITY_NONE,    # enable parity checking
                 stopbits=STOPBITS_ONE, # number of stop bits
                 timeout=None,          # set a timeout value, None to wait forever
                 xonxoff=False,         # enable software flow control
                 rtscts=False,          # enable RTS/CTS flow control
                 writeTimeout=None,     # set a timeout for writes
                 dsrdtr=False,          # None: use rtscts setting, dsrdtr override if True or False
                 interCharTimeout=None  # Inter-character timeout, None to disable
                 ):
        """Initialize comm port object. If a port is given, then the port will be
           opened immediately. Otherwise a Serial port object in closed state
           is returned."""

        self._isOpen   = False
        self._port     = None           # correct value is assigned below through properties
        self._baudrate = None           # correct value is assigned below through properties
        self._bytesize = None           # correct value is assigned below through properties
        self._parity   = None           # correct value is assigned below through properties
        self._stopbits = None           # correct value is assigned below through properties
        self._timeout  = None           # correct value is assigned below through properties
        self._writeTimeout = None       # correct value is assigned below through properties
        self._xonxoff  = None           # correct value is assigned below through properties
        self._rtscts   = None           # correct value is assigned below through properties
        self._dsrdtr   = None           # correct value is assigned below through properties
        self._interCharTimeout = None   # correct value is assigned below through properties

        # assign values using get/set methods using the properties feature
        self.port     = port
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.parity   = parity
        self.stopbits = stopbits
        self.timeout  = timeout
        self.writeTimeout = writeTimeout
        self.xonxoff  = xonxoff
        self.rtscts   = rtscts
        self.dsrdtr   = dsrdtr
        self.interCharTimeout = interCharTimeout

        if port is not None:
            self.open()

    def isOpen(self):
        """Check if the port is opened."""
        return self._isOpen

    #  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -

    # TODO: these are not really needed as the is the BAUDRATES etc. attribute...
    # maybe i remove them before the final release...

    def getSupportedBaudrates(self):
        return [(str(b), b) for b in self.BAUDRATES]

    def getSupportedByteSizes(self):
        return [(str(b), b) for b in self.BYTESIZES]

    def getSupportedStopbits(self):
        return [(str(b), b) for b in self.STOPBITS]

    def getSupportedParities(self):
        return [(PARITY_NAMES[b], b) for b in self.PARITIES]

    #  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -

    def setPort(self, port):
        """Change the port. The attribute portstr is set to a string that
           contains the name of the port."""

        was_open = self._isOpen
        if was_open: self.close()
        if port is not None:
            if isinstance(port, basestring):
                self.portstr = port
            else:
                self.portstr = self.makeDeviceName(port)
        else:
            self.portstr = None
        self._port = port
        self.name = self.portstr
        if was_open: self.open()

    def getPort(self):
        """Get the current port setting. The value that was passed on init or using
           setPort() is passed back. See also the attribute portstr which contains
           the name of the port as a string."""
        return self._port

    port = property(getPort, setPort, doc="Port setting")


    def setBaudrate(self, baudrate):
        """Change baud rate. It raises a ValueError if the port is open and the
        baud rate is not possible. If the port is closed, then the value is
        accepted and the exception is raised when the port is opened."""
        try:
            b = int(baudrate)
        except TypeError:
            raise ValueError("Not a valid baudrate: %r" % (baudrate,))
        else:
            if b <= 0:
                raise ValueError("Not a valid baudrate: %r" % (baudrate,))
            self._baudrate = b
            if self._isOpen:  self._reconfigurePort()

    def getBaudrate(self):
        """Get the current baud rate setting."""
        return self._baudrate

    baudrate = property(getBaudrate, setBaudrate, doc="Baud rate setting")


    def setByteSize(self, bytesize):
        """Change byte size."""
        if bytesize not in self.BYTESIZES: raise ValueError("Not a valid byte size: %r" % (bytesize,))
        self._bytesize = bytesize
        if self._isOpen: self._reconfigurePort()

    def getByteSize(self):
        """Get the current byte size setting."""
        return self._bytesize

    bytesize = property(getByteSize, setByteSize, doc="Byte size setting")


    def setParity(self, parity):
        """Change parity setting."""
        if parity not in self.PARITIES: raise ValueError("Not a valid parity: %r" % (parity,))
        self._parity = parity
        if self._isOpen: self._reconfigurePort()

    def getParity(self):
        """Get the current parity setting."""
        return self._parity

    parity = property(getParity, setParity, doc="Parity setting")


    def setStopbits(self, stopbits):
        """Change stop bits size."""
        if stopbits not in self.STOPBITS: raise ValueError("Not a valid stop bit size: %r" % (stopbits,))
        self._stopbits = stopbits
        if self._isOpen: self._reconfigurePort()

    def getStopbits(self):
        """Get the current stop bits setting."""
        return self._stopbits

    stopbits = property(getStopbits, setStopbits, doc="Stop bits setting")


    def setTimeout(self, timeout):
        """Change timeout setting."""
        if timeout is not None:
            try:
                timeout + 1     # test if it's a number, will throw a TypeError if not...
            except TypeError:
                raise ValueError("Not a valid timeout: %r" % (timeout,))
            if timeout < 0: raise ValueError("Not a valid timeout: %r" % (timeout,))
        self._timeout = timeout
        if self._isOpen: self._reconfigurePort()

    def getTimeout(self):
        """Get the current timeout setting."""
        return self._timeout

    timeout = property(getTimeout, setTimeout, doc="Timeout setting for read()")


    def setWriteTimeout(self, timeout):
        """Change timeout setting."""
        if timeout is not None:
            if timeout < 0: raise ValueError("Not a valid timeout: %r" % (timeout,))
            try:
                timeout + 1     #test if it's a number, will throw a TypeError if not...
            except TypeError:
                raise ValueError("Not a valid timeout: %r" % timeout)

        self._writeTimeout = timeout
        if self._isOpen: self._reconfigurePort()

    def getWriteTimeout(self):
        """Get the current timeout setting."""
        return self._writeTimeout

    writeTimeout = property(getWriteTimeout, setWriteTimeout, doc="Timeout setting for write()")


    def setXonXoff(self, xonxoff):
        """Change XON/XOFF setting."""
        self._xonxoff = xonxoff
        if self._isOpen: self._reconfigurePort()

    def getXonXoff(self):
        """Get the current XON/XOFF setting."""
        return self._xonxoff

    xonxoff = property(getXonXoff, setXonXoff, doc="XON/XOFF setting")

    def setRtsCts(self, rtscts):
        """Change RTS/CTS flow control setting."""
        self._rtscts = rtscts
        if self._isOpen: self._reconfigurePort()

    def getRtsCts(self):
        """Get the current RTS/CTS flow control setting."""
        return self._rtscts

    rtscts = property(getRtsCts, setRtsCts, doc="RTS/CTS flow control setting")

    def setDsrDtr(self, dsrdtr=None):
        """Change DsrDtr flow control setting."""
        if dsrdtr is None:
            # if not set, keep backwards compatibility and follow rtscts setting
            self._dsrdtr = self._rtscts
        else:
            # if defined independently, follow its value
            self._dsrdtr = dsrdtr
        if self._isOpen: self._reconfigurePort()

    def getDsrDtr(self):
        """Get the current DSR/DTR flow control setting."""
        return self._dsrdtr

    dsrdtr = property(getDsrDtr, setDsrDtr, "DSR/DTR flow control setting")

    def setInterCharTimeout(self, interCharTimeout):
        """Change inter-character timeout setting."""
        if interCharTimeout is not None:
            if interCharTimeout < 0: raise ValueError("Not a valid timeout: %r" % interCharTimeout)
            try:
                interCharTimeout + 1     # test if it's a number, will throw a TypeError if not...
            except TypeError:
                raise ValueError("Not a valid timeout: %r" % interCharTimeout)

        self._interCharTimeout = interCharTimeout
        if self._isOpen: self._reconfigurePort()

    def getInterCharTimeout(self):
        """Get the current inter-character timeout setting."""
        return self._interCharTimeout

    interCharTimeout = property(getInterCharTimeout, setInterCharTimeout, doc="Inter-character timeout setting for read()")

    #  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -

    _SETTINGS = ('baudrate', 'bytesize', 'parity', 'stopbits', 'xonxoff',
            'dsrdtr', 'rtscts', 'timeout', 'writeTimeout', 'interCharTimeout')

    def getSettingsDict(self):
        """Get current port settings as a dictionary. For use with
        applySettingsDict"""
        return dict([(key, getattr(self, '_'+key)) for key in self._SETTINGS])

    def applySettingsDict(self, d):
        """apply stored settings from a dictionary returned from
        getSettingsDict. it's allowed to delete keys from the dictionary. these
        values will simply left unchanged."""
        for key in self._SETTINGS:
            if d[key] != getattr(self, '_'+key):   # check against internal "_" value
                setattr(self, key, d[key])          # set non "_" value to use properties write function

    #  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -

    def __repr__(self):
        """String representation of the current port settings and its state."""
        return "%s<id=0x%x, open=%s>(port=%r, baudrate=%r, bytesize=%r, parity=%r, stopbits=%r, timeout=%r, xonxoff=%r, rtscts=%r, dsrdtr=%r)" % (
            self.__class__.__name__,
            id(self),
            self._isOpen,
            self.portstr,
            self.baudrate,
            self.bytesize,
            self.parity,
            self.stopbits,
            self.timeout,
            self.xonxoff,
            self.rtscts,
            self.dsrdtr,
        )


    #  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -
    # compatibility with io library

    def readable(self): return True
    def writable(self): return True
    def seekable(self): return False
    def readinto(self, b):
        data = self.read(len(b))
        n = len(data)
        try:
            b[:n] = data
        except TypeError, err:
            import array
            if not isinstance(b, array.array):
                raise err
            b[:n] = array.array('b', data)
        return n


if __name__ == '__main__':
    import sys
    s = SerialBase()
    sys.stdout.write('port name:  %s\n' % s.portstr)
    sys.stdout.write('baud rates: %s\n' % s.getSupportedBaudrates())
    sys.stdout.write('byte sizes: %s\n' % s.getSupportedByteSizes())
    sys.stdout.write('parities:   %s\n' % s.getSupportedParities())
    sys.stdout.write('stop bits:  %s\n' % s.getSupportedStopbits())
    sys.stdout.write('%s\n' % s)

########NEW FILE########
__FILENAME__ = serialwin32
#! python
# Python Serial Port Extension for Win32, Linux, BSD, Jython
# serial driver for win32
# see __init__.py
#
# (C) 2001-2011 Chris Liechti <cliechti@gmx.net>
# this is distributed under a free software license, see license.txt
#
# Initial patch to use ctypes by Giovanni Bajo <rasky@develer.com>

import ctypes
from serial import win32

from serial.serialutil import *


def device(portnum):
    """Turn a port number into a device name"""
    return 'COM%d' % (portnum+1) # numbers are transformed to a string


class Win32Serial(SerialBase):
    """Serial port implementation for Win32 based on ctypes."""

    BAUDRATES = (50, 75, 110, 134, 150, 200, 300, 600, 1200, 1800, 2400, 4800,
                 9600, 19200, 38400, 57600, 115200)

    def __init__(self, *args, **kwargs):
        self.hComPort = None
        self._overlappedRead = None
        self._overlappedWrite = None
        self._rtsToggle = False

        self._rtsState = win32.RTS_CONTROL_ENABLE
        self._dtrState = win32.DTR_CONTROL_ENABLE


        SerialBase.__init__(self, *args, **kwargs)

    def open(self):
        """Open port with current settings. This may throw a SerialException
           if the port cannot be opened."""
        if self._port is None:
            raise SerialException("Port must be configured before it can be used.")
        if self._isOpen:
            raise SerialException("Port is already open.")
        # the "\\.\COMx" format is required for devices other than COM1-COM8
        # not all versions of windows seem to support this properly
        # so that the first few ports are used with the DOS device name
        port = self.portstr
        try:
            if port.upper().startswith('COM') and int(port[3:]) > 8:
                port = '\\\\.\\' + port
        except ValueError:
            # for like COMnotanumber
            pass
        self.hComPort = win32.CreateFile(port,
               win32.GENERIC_READ | win32.GENERIC_WRITE,
               0, # exclusive access
               None, # no security
               win32.OPEN_EXISTING,
               win32.FILE_ATTRIBUTE_NORMAL | win32.FILE_FLAG_OVERLAPPED,
               0)
        if self.hComPort == win32.INVALID_HANDLE_VALUE:
            self.hComPort = None    # 'cause __del__ is called anyway
            raise SerialException("could not open port %r: %r" % (self.portstr, ctypes.WinError()))

        try:
            self._overlappedRead = win32.OVERLAPPED()
            self._overlappedRead.hEvent = win32.CreateEvent(None, 1, 0, None)
            self._overlappedWrite = win32.OVERLAPPED()
            #~ self._overlappedWrite.hEvent = win32.CreateEvent(None, 1, 0, None)
            self._overlappedWrite.hEvent = win32.CreateEvent(None, 0, 0, None)

            # Setup a 4k buffer
            win32.SetupComm(self.hComPort, 4096, 4096)

            # Save original timeout values:
            self._orgTimeouts = win32.COMMTIMEOUTS()
            win32.GetCommTimeouts(self.hComPort, ctypes.byref(self._orgTimeouts))

            self._reconfigurePort()

            # Clear buffers:
            # Remove anything that was there
            win32.PurgeComm(self.hComPort,
                    win32.PURGE_TXCLEAR | win32.PURGE_TXABORT |
                    win32.PURGE_RXCLEAR | win32.PURGE_RXABORT)
        except:
            try:
                self._close()
            except:
                # ignore any exception when closing the port
                # also to keep original exception that happened when setting up
                pass
            self.hComPort = None
            raise
        else:
            self._isOpen = True


    def _reconfigurePort(self):
        """Set communication parameters on opened port."""
        if not self.hComPort:
            raise SerialException("Can only operate on a valid port handle")

        # Set Windows timeout values
        # timeouts is a tuple with the following items:
        # (ReadIntervalTimeout,ReadTotalTimeoutMultiplier,
        #  ReadTotalTimeoutConstant,WriteTotalTimeoutMultiplier,
        #  WriteTotalTimeoutConstant)
        if self._timeout is None:
            timeouts = (0, 0, 0, 0, 0)
        elif self._timeout == 0:
            timeouts = (win32.MAXDWORD, 0, 0, 0, 0)
        else:
            timeouts = (0, 0, int(self._timeout*1000), 0, 0)
        if self._timeout != 0 and self._interCharTimeout is not None:
            timeouts = (int(self._interCharTimeout * 1000),) + timeouts[1:]

        if self._writeTimeout is None:
            pass
        elif self._writeTimeout == 0:
            timeouts = timeouts[:-2] + (0, win32.MAXDWORD)
        else:
            timeouts = timeouts[:-2] + (0, int(self._writeTimeout*1000))
        win32.SetCommTimeouts(self.hComPort, ctypes.byref(win32.COMMTIMEOUTS(*timeouts)))

        win32.SetCommMask(self.hComPort, win32.EV_ERR)

        # Setup the connection info.
        # Get state and modify it:
        comDCB = win32.DCB()
        win32.GetCommState(self.hComPort, ctypes.byref(comDCB))
        comDCB.BaudRate = self._baudrate

        if self._bytesize == FIVEBITS:
            comDCB.ByteSize     = 5
        elif self._bytesize == SIXBITS:
            comDCB.ByteSize     = 6
        elif self._bytesize == SEVENBITS:
            comDCB.ByteSize     = 7
        elif self._bytesize == EIGHTBITS:
            comDCB.ByteSize     = 8
        else:
            raise ValueError("Unsupported number of data bits: %r" % self._bytesize)

        if self._parity == PARITY_NONE:
            comDCB.Parity       = win32.NOPARITY
            comDCB.fParity      = 0 # Disable Parity Check
        elif self._parity == PARITY_EVEN:
            comDCB.Parity       = win32.EVENPARITY
            comDCB.fParity      = 1 # Enable Parity Check
        elif self._parity == PARITY_ODD:
            comDCB.Parity       = win32.ODDPARITY
            comDCB.fParity      = 1 # Enable Parity Check
        elif self._parity == PARITY_MARK:
            comDCB.Parity       = win32.MARKPARITY
            comDCB.fParity      = 1 # Enable Parity Check
        elif self._parity == PARITY_SPACE:
            comDCB.Parity       = win32.SPACEPARITY
            comDCB.fParity      = 1 # Enable Parity Check
        else:
            raise ValueError("Unsupported parity mode: %r" % self._parity)

        if self._stopbits == STOPBITS_ONE:
            comDCB.StopBits     = win32.ONESTOPBIT
        elif self._stopbits == STOPBITS_ONE_POINT_FIVE:
            comDCB.StopBits     = win32.ONE5STOPBITS
        elif self._stopbits == STOPBITS_TWO:
            comDCB.StopBits     = win32.TWOSTOPBITS
        else:
            raise ValueError("Unsupported number of stop bits: %r" % self._stopbits)

        comDCB.fBinary          = 1 # Enable Binary Transmission
        # Char. w/ Parity-Err are replaced with 0xff (if fErrorChar is set to TRUE)
        if self._rtscts:
            comDCB.fRtsControl  = win32.RTS_CONTROL_HANDSHAKE
        elif self._rtsToggle:
            comDCB.fRtsControl  = win32.RTS_CONTROL_TOGGLE
        else:
            comDCB.fRtsControl  = self._rtsState
        if self._dsrdtr:
            comDCB.fDtrControl  = win32.DTR_CONTROL_HANDSHAKE
        else:
            comDCB.fDtrControl  = self._dtrState

        if self._rtsToggle:
            comDCB.fOutxCtsFlow     = 0
        else:
            comDCB.fOutxCtsFlow     = self._rtscts
        comDCB.fOutxDsrFlow     = self._dsrdtr
        comDCB.fOutX            = self._xonxoff
        comDCB.fInX             = self._xonxoff
        comDCB.fNull            = 0
        comDCB.fErrorChar       = 0
        comDCB.fAbortOnError    = 0
        comDCB.XonChar          = XON
        comDCB.XoffChar         = XOFF

        if not win32.SetCommState(self.hComPort, ctypes.byref(comDCB)):
            raise ValueError("Cannot configure port, some setting was wrong. Original message: %r" % ctypes.WinError())

    #~ def __del__(self):
        #~ self.close()


    def _close(self):
        """internal close port helper"""
        if self.hComPort:
            # Restore original timeout values:
            win32.SetCommTimeouts(self.hComPort, self._orgTimeouts)
            # Close COM-Port:
            win32.CloseHandle(self.hComPort)
            if self._overlappedRead is not None:
                win32.CloseHandle(self._overlappedRead.hEvent)
                self._overlappedRead = None
            if self._overlappedWrite is not None:
                win32.CloseHandle(self._overlappedWrite.hEvent)
                self._overlappedWrite = None
            self.hComPort = None

    def close(self):
        """Close port"""
        if self._isOpen:
            self._close()
            self._isOpen = False

    def makeDeviceName(self, port):
        return device(port)

    #  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -

    def inWaiting(self):
        """Return the number of characters currently in the input buffer."""
        flags = win32.DWORD()
        comstat = win32.COMSTAT()
        if not win32.ClearCommError(self.hComPort, ctypes.byref(flags), ctypes.byref(comstat)):
            raise SerialException('call to ClearCommError failed')
        return comstat.cbInQue

    def read(self, size=1):
        """Read size bytes from the serial port. If a timeout is set it may
           return less characters as requested. With no timeout it will block
           until the requested number of bytes is read."""
        if not self.hComPort: raise portNotOpenError
        if size > 0:
            win32.ResetEvent(self._overlappedRead.hEvent)
            flags = win32.DWORD()
            comstat = win32.COMSTAT()
            if not win32.ClearCommError(self.hComPort, ctypes.byref(flags), ctypes.byref(comstat)):
                raise SerialException('call to ClearCommError failed')
            if self.timeout == 0:
                n = min(comstat.cbInQue, size)
                if n > 0:
                    buf = ctypes.create_string_buffer(n)
                    rc = win32.DWORD()
                    err = win32.ReadFile(self.hComPort, buf, n, ctypes.byref(rc), ctypes.byref(self._overlappedRead))
                    if not err and win32.GetLastError() != win32.ERROR_IO_PENDING:
                        raise SerialException("ReadFile failed (%r)" % ctypes.WinError())
                    err = win32.WaitForSingleObject(self._overlappedRead.hEvent, win32.INFINITE)
                    read = buf.raw[:rc.value]
                else:
                    read = bytes()
            else:
                buf = ctypes.create_string_buffer(size)
                rc = win32.DWORD()
                err = win32.ReadFile(self.hComPort, buf, size, ctypes.byref(rc), ctypes.byref(self._overlappedRead))
                if not err and win32.GetLastError() != win32.ERROR_IO_PENDING:
                    raise SerialException("ReadFile failed (%r)" % ctypes.WinError())
                err = win32.GetOverlappedResult(self.hComPort, ctypes.byref(self._overlappedRead), ctypes.byref(rc), True)
                read = buf.raw[:rc.value]
        else:
            read = bytes()
        return bytes(read)

    def write(self, data):
        """Output the given string over the serial port."""
        if not self.hComPort: raise portNotOpenError
        #~ if not isinstance(data, (bytes, bytearray)):
            #~ raise TypeError('expected %s or bytearray, got %s' % (bytes, type(data)))
        # convert data (needed in case of memoryview instance: Py 3.1 io lib), ctypes doesn't like memoryview
        data = to_bytes(data)
        if data:
            #~ win32event.ResetEvent(self._overlappedWrite.hEvent)
            n = win32.DWORD()
            err = win32.WriteFile(self.hComPort, data, len(data), ctypes.byref(n), self._overlappedWrite)
            if not err and win32.GetLastError() != win32.ERROR_IO_PENDING:
                raise SerialException("WriteFile failed (%r)" % ctypes.WinError())
            if self._writeTimeout != 0: # if blocking (None) or w/ write timeout (>0)
                # Wait for the write to complete.
                #~ win32.WaitForSingleObject(self._overlappedWrite.hEvent, win32.INFINITE)
                err = win32.GetOverlappedResult(self.hComPort, self._overlappedWrite, ctypes.byref(n), True)
                if n.value != len(data):
                    raise writeTimeoutError
            return n.value
        else:
            return 0

    def flush(self):
        """Flush of file like objects. In this case, wait until all data
           is written."""
        while self.outWaiting():
            time.sleep(0.05)
        # XXX could also use WaitCommEvent with mask EV_TXEMPTY, but it would
        # require overlapped IO and its also only possible to set a single mask
        # on the port---

    def flushInput(self):
        """Clear input buffer, discarding all that is in the buffer."""
        if not self.hComPort: raise portNotOpenError
        win32.PurgeComm(self.hComPort, win32.PURGE_RXCLEAR | win32.PURGE_RXABORT)

    def flushOutput(self):
        """Clear output buffer, aborting the current output and
        discarding all that is in the buffer."""
        if not self.hComPort: raise portNotOpenError
        win32.PurgeComm(self.hComPort, win32.PURGE_TXCLEAR | win32.PURGE_TXABORT)

    def sendBreak(self, duration=0.25):
        """Send break condition. Timed, returns to idle state after given duration."""
        if not self.hComPort: raise portNotOpenError
        import time
        win32.SetCommBreak(self.hComPort)
        time.sleep(duration)
        win32.ClearCommBreak(self.hComPort)

    def setBreak(self, level=1):
        """Set break: Controls TXD. When active, to transmitting is possible."""
        if not self.hComPort: raise portNotOpenError
        if level:
            win32.SetCommBreak(self.hComPort)
        else:
            win32.ClearCommBreak(self.hComPort)

    def setRTS(self, level=1):
        """Set terminal status line: Request To Send"""
        # remember level for reconfigure
        if level:
            self._rtsState = win32.RTS_CONTROL_ENABLE
        else:
            self._rtsState = win32.RTS_CONTROL_DISABLE
        # also apply now if port is open
        if self.hComPort:
            if level:
                win32.EscapeCommFunction(self.hComPort, win32.SETRTS)
            else:
                win32.EscapeCommFunction(self.hComPort, win32.CLRRTS)

    def setDTR(self, level=1):
        """Set terminal status line: Data Terminal Ready"""
        # remember level for reconfigure
        if level:
            self._dtrState = win32.DTR_CONTROL_ENABLE
        else:
            self._dtrState = win32.DTR_CONTROL_DISABLE
        # also apply now if port is open
        if self.hComPort:
            if level:
                win32.EscapeCommFunction(self.hComPort, win32.SETDTR)
            else:
                win32.EscapeCommFunction(self.hComPort, win32.CLRDTR)

    def _GetCommModemStatus(self):
        stat = win32.DWORD()
        win32.GetCommModemStatus(self.hComPort, ctypes.byref(stat))
        return stat.value

    def getCTS(self):
        """Read terminal status line: Clear To Send"""
        if not self.hComPort: raise portNotOpenError
        return win32.MS_CTS_ON & self._GetCommModemStatus() != 0

    def getDSR(self):
        """Read terminal status line: Data Set Ready"""
        if not self.hComPort: raise portNotOpenError
        return win32.MS_DSR_ON & self._GetCommModemStatus() != 0

    def getRI(self):
        """Read terminal status line: Ring Indicator"""
        if not self.hComPort: raise portNotOpenError
        return win32.MS_RING_ON & self._GetCommModemStatus() != 0

    def getCD(self):
        """Read terminal status line: Carrier Detect"""
        if not self.hComPort: raise portNotOpenError
        return win32.MS_RLSD_ON & self._GetCommModemStatus() != 0

    # - - platform specific - - - -

    def setBufferSize(self, rx_size=4096, tx_size=None):
        """\
        Recommend a buffer size to the driver (device driver can ignore this
        vlaue). Must be called before the port is opended.
        """
        if tx_size is None: tx_size = rx_size
        win32.SetupComm(self.hComPort, rx_size, tx_size)

    def setXON(self, level=True):
        """\
        Manually control flow - when software flow control is enabled.
        This will send XON (true) and XOFF (false) to the other device.
        WARNING: this function is not portable to different platforms!
        """
        if not self.hComPort: raise portNotOpenError
        if level:
            win32.EscapeCommFunction(self.hComPort, win32.SETXON)
        else:
            win32.EscapeCommFunction(self.hComPort, win32.SETXOFF)

    def outWaiting(self):
        """return how many characters the in the outgoing buffer"""
        flags = win32.DWORD()
        comstat = win32.COMSTAT()
        if not win32.ClearCommError(self.hComPort, ctypes.byref(flags), ctypes.byref(comstat)):
            raise SerialException('call to ClearCommError failed')
        return comstat.cbOutQue

    # functions useful for RS-485 adapters
    def setRtsToggle(self, rtsToggle):
        """Change RTS toggle control setting."""
        self._rtsToggle = rtsToggle
        if self._isOpen: self._reconfigurePort()

    def getRtsToggle(self):
        """Get the current RTS toggle control setting."""
        return self._rtsToggle

    rtsToggle = property(getRtsToggle, setRtsToggle, doc="RTS toggle control setting")


# assemble Serial class with the platform specific implementation and the base
# for file-like behavior. for Python 2.6 and newer, that provide the new I/O
# library, derive from io.RawIOBase
try:
    import io
except ImportError:
    # classic version with our own file-like emulation
    class Serial(Win32Serial, FileLike):
        pass
else:
    # io library present
    class Serial(Win32Serial, io.RawIOBase):
        pass


# Nur Testfunktion!!
if __name__ == '__main__':
    s = Serial(0)
    sys.stdout.write("%s\n" % s)

    s = Serial()
    sys.stdout.write("%s\n" % s)

    s.baudrate = 19200
    s.databits = 7
    s.close()
    s.port = 0
    s.open()
    sys.stdout.write("%s\n" % s)


########NEW FILE########
__FILENAME__ = sermsdos
# sermsdos.py
#
# History:
#
#   3rd September 2002                      Dave Haynes
#   1. First defined
#
# Although this code should run under the latest versions of
# Python, on DOS-based platforms such as Windows 95 and 98,
# it has been specifically written to be compatible with
# PyDOS, available at:
# http://www.python.org/ftp/python/wpy/dos.html
#
# PyDOS is a stripped-down version of Python 1.5.2 for
# DOS machines. Therefore, in making changes to this file,
# please respect Python 1.5.2 syntax. In addition, please
# limit the width of this file to 60 characters.
#
# Note also that the modules in PyDOS contain fewer members
# than other versions, so we are restricted to using the
# following:
#
# In module os:
# -------------
# environ, chdir, getcwd, getpid, umask, fdopen, close,
# dup, dup2, fstat, lseek, open, read, write, O_RDONLY,
# O_WRONLY, O_RDWR, O_APPEND, O_CREAT, O_EXCL, O_TRUNC,
# access, F_OK, R_OK, W_OK, X_OK, chmod, listdir, mkdir,
# remove, rename, renames, rmdir, stat, unlink, utime,
# execl, execle, execlp, execlpe, execvp, execvpe, _exit,
# system.
#
# In module os.path:
# ------------------
# curdir, pardir, sep, altsep, pathsep, defpath, linesep.
#

import os
import sys
import string
import serial.serialutil

BAUD_RATES = {
                110: "11",
                150: "15",
                300: "30",
                600: "60",
                1200: "12",
                2400: "24",
                4800: "48",
                9600: "96",
                19200: "19"}

(PARITY_NONE, PARITY_EVEN, PARITY_ODD, PARITY_MARK,
PARITY_SPACE) = (0, 1, 2, 3, 4)
(STOPBITS_ONE, STOPBITS_ONEANDAHALF,
STOPBITS_TWO) = (1, 1.5, 2)
FIVEBITS, SIXBITS, SEVENBITS, EIGHTBITS = (5, 6, 7, 8)
(RETURN_ERROR, RETURN_BUSY, RETURN_RETRY, RETURN_READY,
RETURN_NONE) = ('E', 'B', 'P', 'R', 'N')
portNotOpenError = ValueError('port not open')

def device(portnum):
    return 'COM%d' % (portnum+1)

class Serial(serialutil.FileLike):
    """
       port: number of device; numbering starts at
            zero. if everything fails, the user can
            specify a device string, note that this
            isn't portable any more
       baudrate: baud rate
       bytesize: number of databits
       parity: enable parity checking
       stopbits: number of stopbits
       timeout: set a timeout (None for waiting forever)
       xonxoff: enable software flow control
       rtscts: enable RTS/CTS flow control
       retry: DOS retry mode
    """
    def __init__(self,
                 port,
                 baudrate = 9600,
                 bytesize = EIGHTBITS,
                 parity = PARITY_NONE,
                 stopbits = STOPBITS_ONE,
                 timeout = None,
                 xonxoff = 0,
                 rtscts = 0,
                 retry = RETURN_RETRY
                 ):

        if type(port) == type(''):
        # strings are taken directly
            self.portstr = port
        else:
        # numbers are transformed to a string
            self.portstr = device(port+1)

        self.baud = BAUD_RATES[baudrate]
        self.bytesize = str(bytesize)

        if parity == PARITY_NONE:
            self.parity = 'N'
        elif parity == PARITY_EVEN:
            self.parity = 'E'
        elif parity == PARITY_ODD:
            self.parity = 'O'
        elif parity == PARITY_MARK:
            self.parity = 'M'
        elif parity == PARITY_SPACE:
            self.parity = 'S'

        self.stop = str(stopbits)
        self.retry = retry
        self.filename = "sermsdos.tmp"

        self._config(self.portstr, self.baud, self.parity,
        self.bytesize, self.stop, self.retry, self.filename)

    def __del__(self):
        self.close()

    def close(self):
        pass

    def _config(self, port, baud, parity, data, stop, retry,
        filename):
        comString = string.join(("MODE ", port, ":"
        , " BAUD= ", baud, " PARITY= ", parity
        , " DATA= ", data, " STOP= ", stop, " RETRY= ",
        retry, " > ", filename ), '')
        os.system(comString)

    def setBaudrate(self, baudrate):
        self._config(self.portstr, BAUD_RATES[baudrate],
        self.parity, self.bytesize, self.stop, self.retry,
        self.filename)

    def inWaiting(self):
        """returns the number of bytes waiting to be read"""
        raise NotImplementedError

    def read(self, num = 1):
        """Read num bytes from serial port"""
        handle = os.open(self.portstr,
        os.O_RDONLY | os.O_BINARY)
        rv = os.read(handle, num)
        os.close(handle)
        return rv

    def write(self, s):
        """Write string to serial port"""
        handle = os.open(self.portstr,
        os.O_WRONLY | os.O_BINARY)
        rv = os.write(handle, s)
        os.close(handle)
        return rv

    def flushInput(self):
        raise NotImplementedError

    def flushOutput(self):
        raise NotImplementedError

    def sendBreak(self):
        raise NotImplementedError

    def setRTS(self,level=1):
        """Set terminal status line"""
        raise NotImplementedError

    def setDTR(self,level=1):
        """Set terminal status line"""
        raise NotImplementedError

    def getCTS(self):
        """Eead terminal status line"""
        raise NotImplementedError

    def getDSR(self):
        """Eead terminal status line"""
        raise NotImplementedError

    def getRI(self):
        """Eead terminal status line"""
        raise NotImplementedError

    def getCD(self):
        """Eead terminal status line"""
        raise NotImplementedError

    def __repr__(self):
        return string.join(( "<Serial>: ", self.portstr
        , self.baud, self.parity, self.bytesize, self.stop,
        self.retry , self.filename), ' ')

if __name__ == '__main__':
    s = Serial(0)
    sys.stdio.write('%s %s\n' % (__name__, s))

########NEW FILE########
__FILENAME__ = list_ports
#!/usr/bin/env python

# portable serial port access with python
# this is a wrapper module for different platform implementations of the
# port enumeration feature
#
# (C) 2011-2013 Chris Liechti <cliechti@gmx.net>
# this is distributed under a free software license, see license.txt

"""\
This module will provide a function called comports that returns an
iterable (generator or list) that will enumerate available com ports. Note that
on some systems non-existent ports may be listed.

Additionally a grep function is supplied that can be used to search for ports
based on their descriptions or hardware ID.
"""

import sys, os, re

# chose an implementation, depending on os
#~ if sys.platform == 'cli':
#~ else:
import os
# chose an implementation, depending on os
if os.name == 'nt': #sys.platform == 'win32':
    from serial.tools.list_ports_windows import *
elif os.name == 'posix':
    from serial.tools.list_ports_posix import *
#~ elif os.name == 'java':
else:
    raise ImportError("Sorry: no implementation for your platform ('%s') available" % (os.name,))

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def grep(regexp):
    """\
    Search for ports using a regular expression. Port name, description and
    hardware ID are searched. The function returns an iterable that returns the
    same tuples as comport() would do.
    """
    r = re.compile(regexp, re.I)
    for port, desc, hwid in comports():
        if r.search(port) or r.search(desc) or r.search(hwid):
            yield port, desc, hwid


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def main():
    import optparse

    parser = optparse.OptionParser(
        usage = "%prog [options] [<regexp>]",
        description = "Miniterm - A simple terminal program for the serial port."
    )

    parser.add_option("--debug",
            help="print debug messages and tracebacks (development mode)",
            dest="debug",
            default=False,
            action='store_true')

    parser.add_option("-v", "--verbose",
            help="show more messages (can be given multiple times)",
            dest="verbose",
            default=1,
            action='count')

    parser.add_option("-q", "--quiet",
            help="suppress all messages",
            dest="verbose",
            action='store_const',
            const=0)

    (options, args) = parser.parse_args()


    hits = 0
    # get iteraror w/ or w/o filter
    if args:
        if len(args) > 1:
            parser.error('more than one regexp not supported')
        print "Filtered list with regexp: %r" % (args[0],)
        iterator = sorted(grep(args[0]))
    else:
        iterator = sorted(comports())
    # list them
    for port, desc, hwid in iterator:
        print("%-20s" % (port,))
        if options.verbose > 1:
            print("    desc: %s" % (desc,))
            print("    hwid: %s" % (hwid,))
        hits += 1
    if options.verbose:
        if hits:
            print("%d ports found" % (hits,))
        else:
            print("no ports found")

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# test
if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = list_ports_linux
#!/usr/bin/env python

# portable serial port access with python
#
# This is a module that gathers a list of serial ports including details on
# GNU/Linux systems
#
# (C) 2011-2013 Chris Liechti <cliechti@gmx.net>
# this is distributed under a free software license, see license.txt

import glob
import sys
import os
import re

try:
    import subprocess
except ImportError:
    def popen(argv):
        try:
            si, so =  os.popen4(' '.join(argv))
            return so.read().strip()
        except:
            raise IOError('lsusb failed')
else:
    def popen(argv):
        try:
            return subprocess.check_output(argv, stderr=subprocess.STDOUT).strip()
        except:
            raise IOError('lsusb failed')


# The comports function is expected to return an iterable that yields tuples of
# 3 strings: port name, human readable description and a hardware ID.
#
# as currently no method is known to get the second two strings easily, they
# are currently just identical to the port name.

# try to detect the OS so that a device can be selected...
plat = sys.platform.lower()

def read_line(filename):
    """help function to read a single line from a file. returns none"""
    try:
        f = open(filename)
        line = f.readline().strip()
        f.close()
        return line
    except IOError:
        return None

def re_group(regexp, text):
    """search for regexp in text, return 1st group on match"""
    if sys.version < '3':
        m = re.search(regexp, text)
    else:
        # text is bytes-like
        m = re.search(regexp, text.decode('ascii', 'replace'))
    if m: return m.group(1)


# try to extract descriptions from sysfs. this was done by experimenting,
# no guarantee that it works for all devices or in the future...

def usb_sysfs_hw_string(sysfs_path):
    """given a path to a usb device in sysfs, return a string describing it"""
    bus, dev = os.path.basename(os.path.realpath(sysfs_path)).split('-')
    snr = read_line(sysfs_path+'/serial')
    if snr:
        snr_txt = ' SNR=%s' % (snr,)
    else:
        snr_txt = ''
    return 'USB VID:PID=%s:%s%s' % (
            read_line(sysfs_path+'/idVendor'),
            read_line(sysfs_path+'/idProduct'),
            snr_txt
            )

def usb_lsusb_string(sysfs_path):
    base = os.path.basename(os.path.realpath(sysfs_path))
    bus = base.split('-')[0]
    try:
        dev = int(read_line(os.path.join(sysfs_path, 'devnum')))
        desc = popen(['lsusb', '-v', '-s', '%s:%s' % (bus, dev)])
        # descriptions from device
        iManufacturer = re_group('iManufacturer\s+\w+ (.+)', desc)
        iProduct = re_group('iProduct\s+\w+ (.+)', desc)
        iSerial = re_group('iSerial\s+\w+ (.+)', desc) or ''
        # descriptions from kernel
        idVendor = re_group('idVendor\s+0x\w+ (.+)', desc)
        idProduct = re_group('idProduct\s+0x\w+ (.+)', desc)
        # create descriptions. prefer text from device, fall back to the others
        return '%s %s %s' % (iManufacturer or idVendor, iProduct or idProduct, iSerial)
    except IOError:
        return base

def describe(device):
    """\
    Get a human readable description.
    For USB-Serial devices try to run lsusb to get a human readable description.
    For USB-CDC devices read the description from sysfs.
    """
    base = os.path.basename(device)
    # USB-Serial devices
    sys_dev_path = '/sys/class/tty/%s/device/driver/%s' % (base, base)
    if os.path.exists(sys_dev_path):
        sys_usb = os.path.dirname(os.path.dirname(os.path.realpath(sys_dev_path)))
        return usb_lsusb_string(sys_usb)
    # USB-CDC devices
    sys_dev_path = '/sys/class/tty/%s/device/interface' % (base,)
    if os.path.exists(sys_dev_path):
        return read_line(sys_dev_path)
    return base

def hwinfo(device):
    """Try to get a HW identification using sysfs"""
    base = os.path.basename(device)
    if os.path.exists('/sys/class/tty/%s/device' % (base,)):
        # PCI based devices
        sys_id_path = '/sys/class/tty/%s/device/id' % (base,)
        if os.path.exists(sys_id_path):
            return read_line(sys_id_path)
        # USB-Serial devices
        sys_dev_path = '/sys/class/tty/%s/device/driver/%s' % (base, base)
        if os.path.exists(sys_dev_path):
            sys_usb = os.path.dirname(os.path.dirname(os.path.realpath(sys_dev_path)))
            return usb_sysfs_hw_string(sys_usb)
        # USB-CDC devices
        if base.startswith('ttyACM'):
            sys_dev_path = '/sys/class/tty/%s/device' % (base,)
            if os.path.exists(sys_dev_path):
                return usb_sysfs_hw_string(sys_dev_path + '/..')
    return 'n/a'    # XXX directly remove these from the list?

def comports():
    devices = glob.glob('/dev/ttyS*') + glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*')
    return [(d, describe(d), hwinfo(d)) for d in devices]

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# test
if __name__ == '__main__':
    for port, desc, hwid in sorted(comports()):
        print "%s: %s [%s]" % (port, desc, hwid)

########NEW FILE########
__FILENAME__ = list_ports_osx
#!/usr/bin/env python

# portable serial port access with python
#
# This is a module that gathers a list of serial ports including details on OSX
#
# code originally from https://github.com/makerbot/pyserial/tree/master/serial/tools
# with contributions from cibomahto, dgs3, FarMcKon, tedbrandston
# and modifications by cliechti
#
# this is distributed under a free software license, see license.txt



# List all of the callout devices in OS/X by querying IOKit.

# See the following for a reference of how to do this:
# http://developer.apple.com/library/mac/#documentation/DeviceDrivers/Conceptual/WorkingWSerial/WWSerial_SerialDevs/SerialDevices.html#//apple_ref/doc/uid/TP30000384-CIHGEAFD

# More help from darwin_hid.py

# Also see the 'IORegistryExplorer' for an idea of what we are actually searching

import ctypes
from ctypes import util
import re

iokit = ctypes.cdll.LoadLibrary(ctypes.util.find_library('IOKit'))
cf = ctypes.cdll.LoadLibrary(ctypes.util.find_library('CoreFoundation'))

kIOMasterPortDefault = ctypes.c_void_p.in_dll(iokit, "kIOMasterPortDefault")
kCFAllocatorDefault = ctypes.c_void_p.in_dll(cf, "kCFAllocatorDefault")

kCFStringEncodingMacRoman = 0

iokit.IOServiceMatching.restype = ctypes.c_void_p

iokit.IOServiceGetMatchingServices.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
iokit.IOServiceGetMatchingServices.restype = ctypes.c_void_p

iokit.IORegistryEntryGetParentEntry.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]

iokit.IORegistryEntryCreateCFProperty.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32]
iokit.IORegistryEntryCreateCFProperty.restype = ctypes.c_void_p

iokit.IORegistryEntryGetPath.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
iokit.IORegistryEntryGetPath.restype = ctypes.c_void_p

iokit.IORegistryEntryGetName.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
iokit.IORegistryEntryGetName.restype = ctypes.c_void_p

iokit.IOObjectGetClass.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
iokit.IOObjectGetClass.restype = ctypes.c_void_p

iokit.IOObjectRelease.argtypes = [ctypes.c_void_p]


cf.CFStringCreateWithCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int32]
cf.CFStringCreateWithCString.restype = ctypes.c_void_p

cf.CFStringGetCStringPtr.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
cf.CFStringGetCStringPtr.restype = ctypes.c_char_p

cf.CFNumberGetValue.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p]
cf.CFNumberGetValue.restype = ctypes.c_void_p

def get_string_property(device_t, property):
    """ Search the given device for the specified string property

    @param device_t Device to search
    @param property String to search for.
    @return Python string containing the value, or None if not found.
    """
    key = cf.CFStringCreateWithCString(
        kCFAllocatorDefault,
        property.encode("mac_roman"),
        kCFStringEncodingMacRoman
    )

    CFContainer = iokit.IORegistryEntryCreateCFProperty(
        device_t,
        key,
        kCFAllocatorDefault,
        0
    );

    output = None

    if CFContainer:
        output = cf.CFStringGetCStringPtr(CFContainer, 0)

    return output

def get_int_property(device_t, property):
    """ Search the given device for the specified string property

    @param device_t Device to search
    @param property String to search for.
    @return Python string containing the value, or None if not found.
    """
    key = cf.CFStringCreateWithCString(
        kCFAllocatorDefault,
        property.encode("mac_roman"),
        kCFStringEncodingMacRoman
    )

    CFContainer = iokit.IORegistryEntryCreateCFProperty(
        device_t,
        key,
        kCFAllocatorDefault,
        0
    );

    number = ctypes.c_uint16()

    if CFContainer:
        output = cf.CFNumberGetValue(CFContainer, 2, ctypes.byref(number))

    return number.value

def IORegistryEntryGetName(device):
    pathname = ctypes.create_string_buffer(100) # TODO: Is this ok?
    iokit.IOObjectGetClass(
        device,
        ctypes.byref(pathname)
    )

    return pathname.value

def GetParentDeviceByType(device, parent_type):
    """ Find the first parent of a device that implements the parent_type
        @param IOService Service to inspect
        @return Pointer to the parent type, or None if it was not found.
    """
    # First, try to walk up the IOService tree to find a parent of this device that is a IOUSBDevice.
    while IORegistryEntryGetName(device) != parent_type:
        parent = ctypes.c_void_p()
        response = iokit.IORegistryEntryGetParentEntry(
            device,
            "IOService".encode("mac_roman"),
            ctypes.byref(parent)
        )

        # If we weren't able to find a parent for the device, we're done.
        if response != 0:
            return None

        device = parent

    return device

def GetIOServicesByType(service_type):
    """
    """
    serial_port_iterator = ctypes.c_void_p()

    response = iokit.IOServiceGetMatchingServices(
        kIOMasterPortDefault,
        iokit.IOServiceMatching(service_type),
        ctypes.byref(serial_port_iterator)
    )

    services = []
    while iokit.IOIteratorIsValid(serial_port_iterator):
        service = iokit.IOIteratorNext(serial_port_iterator)
        if not service:
            break
        services.append(service)

    iokit.IOObjectRelease(serial_port_iterator)

    return services

def comports():
    # Scan for all iokit serial ports
    services = GetIOServicesByType('IOSerialBSDClient')

    ports = []
    for service in services:
        info = []

        # First, add the callout device file.
        info.append(get_string_property(service, "IOCalloutDevice"))

        # If the serial port is implemented by a
        usb_device = GetParentDeviceByType(service, "IOUSBDevice")
        if usb_device != None:
            info.append(get_string_property(usb_device, "USB Product Name"))

            info.append(
                "USB VID:PID=%x:%x SNR=%s"%(
                get_int_property(usb_device, "idVendor"),
                get_int_property(usb_device, "idProduct"),
                get_string_property(usb_device, "USB Serial Number"))
            )
        else:
           info.append('n/a')
           info.append('n/a')

        ports.append(info)

    return ports

# test
if __name__ == '__main__':
    for port, desc, hwid in sorted(comports()):
        print "%s: %s [%s]" % (port, desc, hwid)


########NEW FILE########
__FILENAME__ = list_ports_posix
#!/usr/bin/env python

# portable serial port access with python

# This is a module that gathers a list of serial ports on POSIXy systems.
# For some specific implementations, see also list_ports_linux, list_ports_osx
#
# this is a wrapper module for different platform implementations of the
# port enumeration feature
#
# (C) 2011-2013 Chris Liechti <cliechti@gmx.net>
# this is distributed under a free software license, see license.txt

"""\
The ``comports`` function is expected to return an iterable that yields tuples
of 3 strings: port name, human readable description and a hardware ID.

As currently no method is known to get the second two strings easily, they are
currently just identical to the port name.
"""

import glob
import sys
import os

# try to detect the OS so that a device can be selected...
plat = sys.platform.lower()

if   plat[:5] == 'linux':    # Linux (confirmed)
    from serial.tools.list_ports_linux import comports

elif plat == 'cygwin':       # cygwin/win32
    def comports():
        devices = glob.glob('/dev/com*')
        return [(d, d, d) for d in devices]

elif plat[:7] == 'openbsd':    # OpenBSD
    def comports():
        devices = glob.glob('/dev/cua*')
        return [(d, d, d) for d in devices]

elif plat[:3] == 'bsd' or  \
        plat[:7] == 'freebsd':

    def comports():
        devices = glob.glob('/dev/cuad*')
        return [(d, d, d) for d in devices]

elif plat[:6] == 'darwin':   # OS X (confirmed)
    from serial.tools.list_ports_osx import comports

elif plat[:6] == 'netbsd':   # NetBSD
    def comports():
        """scan for available ports. return a list of device names."""
        devices = glob.glob('/dev/dty*')
        return [(d, d, d) for d in devices]

elif plat[:4] == 'irix':     # IRIX
    def comports():
        """scan for available ports. return a list of device names."""
        devices = glob.glob('/dev/ttyf*')
        return [(d, d, d) for d in devices]

elif plat[:2] == 'hp':       # HP-UX (not tested)
    def comports():
        """scan for available ports. return a list of device names."""
        devices = glob.glob('/dev/tty*p0')
        return [(d, d, d) for d in devices]

elif plat[:5] == 'sunos':    # Solaris/SunOS
    def comports():
        """scan for available ports. return a list of device names."""
        devices = glob.glob('/dev/tty*c')
        return [(d, d, d) for d in devices]

elif plat[:3] == 'aix':      # AIX
    def comports():
        """scan for available ports. return a list of device names."""
        devices = glob.glob('/dev/tty*')
        return [(d, d, d) for d in devices]

else:
    # platform detection has failed...
    sys.stderr.write("""\
don't know how to enumerate ttys on this system.
! I you know how the serial ports are named send this information to
! the author of this module:

sys.platform = %r
os.name = %r
pySerial version = %s

also add the naming scheme of the serial ports and with a bit luck you can get
this module running...
""" % (sys.platform, os.name, serial.VERSION))
    raise ImportError("Sorry: no implementation for your platform ('%s') available" % (os.name,))

# test
if __name__ == '__main__':
    for port, desc, hwid in sorted(comports()):
        print "%s: %s [%s]" % (port, desc, hwid)

########NEW FILE########
__FILENAME__ = list_ports_windows
import ctypes
import re

def ValidHandle(value, func, arguments):
    if value == 0:
        raise ctypes.WinError()
    return value

import serial
from serial.win32 import ULONG_PTR, is_64bit
from ctypes.wintypes import HANDLE
from ctypes.wintypes import BOOL
from ctypes.wintypes import HWND
from ctypes.wintypes import DWORD
from ctypes.wintypes import WORD
from ctypes.wintypes import LONG
from ctypes.wintypes import ULONG
from ctypes.wintypes import LPCSTR
from ctypes.wintypes import HKEY
from ctypes.wintypes import BYTE

NULL = 0
HDEVINFO = ctypes.c_void_p
PCTSTR = ctypes.c_char_p
PTSTR = ctypes.c_void_p
CHAR = ctypes.c_char
LPDWORD = PDWORD = ctypes.POINTER(DWORD)
#~ LPBYTE = PBYTE = ctypes.POINTER(BYTE)
LPBYTE = PBYTE = ctypes.c_void_p        # XXX avoids error about types

ACCESS_MASK = DWORD
REGSAM = ACCESS_MASK


def byte_buffer(length):
    """Get a buffer for a string"""
    return (BYTE*length)()

def string(buffer):
    s = []
    for c in buffer:
        if c == 0: break
        s.append(chr(c & 0xff)) # "& 0xff": hack to convert signed to unsigned
    return ''.join(s)


class GUID(ctypes.Structure):
    _fields_ = [
        ('Data1', DWORD),
        ('Data2', WORD),
        ('Data3', WORD),
        ('Data4', BYTE*8),
    ]
    def __str__(self):
        return "{%08x-%04x-%04x-%s-%s}" % (
            self.Data1,
            self.Data2,
            self.Data3,
            ''.join(["%02x" % d for d in self.Data4[:2]]),
            ''.join(["%02x" % d for d in self.Data4[2:]]),
        )

class SP_DEVINFO_DATA(ctypes.Structure):
    _fields_ = [
        ('cbSize', DWORD),
        ('ClassGuid', GUID),
        ('DevInst', DWORD),
        ('Reserved', ULONG_PTR),
    ]
    def __str__(self):
        return "ClassGuid:%s DevInst:%s" % (self.ClassGuid, self.DevInst)
PSP_DEVINFO_DATA = ctypes.POINTER(SP_DEVINFO_DATA)

PSP_DEVICE_INTERFACE_DETAIL_DATA = ctypes.c_void_p

setupapi = ctypes.windll.LoadLibrary("setupapi")
SetupDiDestroyDeviceInfoList = setupapi.SetupDiDestroyDeviceInfoList
SetupDiDestroyDeviceInfoList.argtypes = [HDEVINFO]
SetupDiDestroyDeviceInfoList.restype = BOOL

SetupDiClassGuidsFromName = setupapi.SetupDiClassGuidsFromNameA
SetupDiClassGuidsFromName.argtypes = [PCTSTR, ctypes.POINTER(GUID), DWORD, PDWORD]
SetupDiClassGuidsFromName.restype = BOOL

SetupDiEnumDeviceInfo = setupapi.SetupDiEnumDeviceInfo
SetupDiEnumDeviceInfo.argtypes = [HDEVINFO, DWORD, PSP_DEVINFO_DATA]
SetupDiEnumDeviceInfo.restype = BOOL

SetupDiGetClassDevs = setupapi.SetupDiGetClassDevsA
SetupDiGetClassDevs.argtypes = [ctypes.POINTER(GUID), PCTSTR, HWND, DWORD]
SetupDiGetClassDevs.restype = HDEVINFO
SetupDiGetClassDevs.errcheck = ValidHandle

SetupDiGetDeviceRegistryProperty = setupapi.SetupDiGetDeviceRegistryPropertyA
SetupDiGetDeviceRegistryProperty.argtypes = [HDEVINFO, PSP_DEVINFO_DATA, DWORD, PDWORD, PBYTE, DWORD, PDWORD]
SetupDiGetDeviceRegistryProperty.restype = BOOL

SetupDiGetDeviceInstanceId = setupapi.SetupDiGetDeviceInstanceIdA
SetupDiGetDeviceInstanceId.argtypes = [HDEVINFO, PSP_DEVINFO_DATA, PTSTR, DWORD, PDWORD]
SetupDiGetDeviceInstanceId.restype = BOOL

SetupDiOpenDevRegKey = setupapi.SetupDiOpenDevRegKey
SetupDiOpenDevRegKey.argtypes = [HDEVINFO, PSP_DEVINFO_DATA, DWORD, DWORD, DWORD, REGSAM]
SetupDiOpenDevRegKey.restype = HKEY

advapi32 = ctypes.windll.LoadLibrary("Advapi32")
RegCloseKey = advapi32.RegCloseKey
RegCloseKey.argtypes = [HKEY]
RegCloseKey.restype = LONG

RegQueryValueEx = advapi32.RegQueryValueExA
RegQueryValueEx.argtypes = [HKEY, LPCSTR, LPDWORD, LPDWORD, LPBYTE, LPDWORD]
RegQueryValueEx.restype = LONG


DIGCF_PRESENT = 2
DIGCF_DEVICEINTERFACE = 16
INVALID_HANDLE_VALUE = 0
ERROR_INSUFFICIENT_BUFFER = 122
SPDRP_HARDWAREID = 1
SPDRP_FRIENDLYNAME = 12
DICS_FLAG_GLOBAL = 1
DIREG_DEV = 0x00000001
KEY_READ = 0x20019

# workaround for compatibility between Python 2.x and 3.x
Ports = serial.to_bytes([80, 111, 114, 116, 115]) # "Ports"
PortName = serial.to_bytes([80, 111, 114, 116, 78, 97, 109, 101]) # "PortName"

def comports():
    GUIDs = (GUID*8)() # so far only seen one used, so hope 8 are enough...
    guids_size = DWORD()
    if not SetupDiClassGuidsFromName(
            Ports,
            GUIDs,
            ctypes.sizeof(GUIDs),
            ctypes.byref(guids_size)):
        raise ctypes.WinError()

    # repeat for all possible GUIDs
    for index in range(guids_size.value):
        g_hdi = SetupDiGetClassDevs(
                ctypes.byref(GUIDs[index]),
                None,
                NULL,
                DIGCF_PRESENT) # was DIGCF_PRESENT|DIGCF_DEVICEINTERFACE which misses CDC ports

        devinfo = SP_DEVINFO_DATA()
        devinfo.cbSize = ctypes.sizeof(devinfo)
        index = 0
        while SetupDiEnumDeviceInfo(g_hdi, index, ctypes.byref(devinfo)):
            index += 1

            # get the real com port name
            hkey = SetupDiOpenDevRegKey(
                    g_hdi,
                    ctypes.byref(devinfo),
                    DICS_FLAG_GLOBAL,
                    0,
                    DIREG_DEV,  # DIREG_DRV for SW info
                    KEY_READ)
            port_name_buffer = byte_buffer(250)
            port_name_length = ULONG(ctypes.sizeof(port_name_buffer))
            RegQueryValueEx(
                    hkey,
                    PortName,
                    None,
                    None,
                    ctypes.byref(port_name_buffer),
                    ctypes.byref(port_name_length))
            RegCloseKey(hkey)

            # unfortunately does this method also include parallel ports.
            # we could check for names starting with COM or just exclude LPT
            # and hope that other "unknown" names are serial ports...
            if string(port_name_buffer).startswith('LPT'):
                continue

            # hardware ID
            szHardwareID = byte_buffer(250)
            # try to get ID that includes serial number
            if not SetupDiGetDeviceInstanceId(
                    g_hdi,
                    ctypes.byref(devinfo),
                    ctypes.byref(szHardwareID),
                    ctypes.sizeof(szHardwareID) - 1,
                    None):
                # fall back to more generic hardware ID if that would fail
                if not SetupDiGetDeviceRegistryProperty(
                        g_hdi,
                        ctypes.byref(devinfo),
                        SPDRP_HARDWAREID,
                        None,
                        ctypes.byref(szHardwareID),
                        ctypes.sizeof(szHardwareID) - 1,
                        None):
                    # Ignore ERROR_INSUFFICIENT_BUFFER
                    if ctypes.GetLastError() != ERROR_INSUFFICIENT_BUFFER:
                        raise ctypes.WinError()
            # stringify
            szHardwareID_str = string(szHardwareID)

            # in case of USB, make a more readable string, similar to that form
            # that we also generate on other platforms
            if szHardwareID_str.startswith('USB'):
                m = re.search(r'VID_([0-9a-f]{4})&PID_([0-9a-f]{4})(\\(\w+))?', szHardwareID_str, re.I)
                if m:
                    if m.group(4):
                        szHardwareID_str = 'USB VID:PID=%s:%s SNR=%s' % (m.group(1), m.group(2), m.group(4))
                    else:
                        szHardwareID_str = 'USB VID:PID=%s:%s' % (m.group(1), m.group(2))

            # friendly name
            szFriendlyName = byte_buffer(250)
            if not SetupDiGetDeviceRegistryProperty(
                    g_hdi,
                    ctypes.byref(devinfo),
                    SPDRP_FRIENDLYNAME,
                    #~ SPDRP_DEVICEDESC,
                    None,
                    ctypes.byref(szFriendlyName),
                    ctypes.sizeof(szFriendlyName) - 1,
                    None):
                # Ignore ERROR_INSUFFICIENT_BUFFER
                #~ if ctypes.GetLastError() != ERROR_INSUFFICIENT_BUFFER:
                    #~ raise IOError("failed to get details for %s (%s)" % (devinfo, szHardwareID.value))
                # ignore errors and still include the port in the list, friendly name will be same as port name
                yield string(port_name_buffer), 'n/a', szHardwareID_str
            else:
                yield string(port_name_buffer), string(szFriendlyName), szHardwareID_str

        SetupDiDestroyDeviceInfoList(g_hdi)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# test
if __name__ == '__main__':
    import serial

    for port, desc, hwid in sorted(comports()):
        print "%s: %s [%s]" % (port, desc, hwid)

########NEW FILE########
__FILENAME__ = miniterm
#!/usr/bin/env python

# Very simple serial terminal
# (C)2002-2011 Chris Liechti <cliechti@gmx.net>

# Input characters are sent directly (only LF -> CR/LF/CRLF translation is
# done), received characters are displayed as is (or escaped trough pythons
# repr, useful for debug purposes)


import sys, os, serial, threading
try:
    from serial.tools.list_ports import comports
except ImportError:
    comports = None

EXITCHARCTER = serial.to_bytes([0x1d])   # GS/CTRL+]
MENUCHARACTER = serial.to_bytes([0x14])  # Menu: CTRL+T

DEFAULT_PORT = None
DEFAULT_BAUDRATE = 9600
DEFAULT_RTS = None
DEFAULT_DTR = None


def key_description(character):
    """generate a readable description for a key"""
    ascii_code = ord(character)
    if ascii_code < 32:
        return 'Ctrl+%c' % (ord('@') + ascii_code)
    else:
        return repr(character)


# help text, starts with blank line! it's a function so that the current values
# for the shortcut keys is used and not the value at program start
def get_help_text():
    return """
--- pySerial (%(version)s) - miniterm - help
---
--- %(exit)-8s Exit program
--- %(menu)-8s Menu escape key, followed by:
--- Menu keys:
---    %(itself)-7s Send the menu character itself to remote
---    %(exchar)-7s Send the exit character itself to remote
---    %(info)-7s Show info
---    %(upload)-7s Upload file (prompt will be shown)
--- Toggles:
---    %(rts)-7s RTS          %(echo)-7s local echo
---    %(dtr)-7s DTR          %(break)-7s BREAK
---    %(lfm)-7s line feed    %(repr)-7s Cycle repr mode
---
--- Port settings (%(menu)s followed by the following):
---    p          change port
---    7 8        set data bits
---    n e o s m  change parity (None, Even, Odd, Space, Mark)
---    1 2 3      set stop bits (1, 2, 1.5)
---    b          change baud rate
---    x X        disable/enable software flow control
---    r R        disable/enable hardware flow control
""" % {
    'version': getattr(serial, 'VERSION', 'unknown version'),
    'exit': key_description(EXITCHARCTER),
    'menu': key_description(MENUCHARACTER),
    'rts': key_description('\x12'),
    'repr': key_description('\x01'),
    'dtr': key_description('\x04'),
    'lfm': key_description('\x0c'),
    'break': key_description('\x02'),
    'echo': key_description('\x05'),
    'info': key_description('\x09'),
    'upload': key_description('\x15'),
    'itself': key_description(MENUCHARACTER),
    'exchar': key_description(EXITCHARCTER),
}

if sys.version_info >= (3, 0):
    def character(b):
        return b.decode('latin1')
else:
    def character(b):
        return b

LF = serial.to_bytes([10])
CR = serial.to_bytes([13])
CRLF = serial.to_bytes([13, 10])

X00 = serial.to_bytes([0])
X0E = serial.to_bytes([0x0e])

# first choose a platform dependant way to read single characters from the console
global console

if os.name == 'nt':
    import msvcrt
    class Console(object):
        def __init__(self):
            pass

        def setup(self):
            pass    # Do nothing for 'nt'

        def cleanup(self):
            pass    # Do nothing for 'nt'

        def getkey(self):
            while True:
                z = msvcrt.getch()
                if z == X00 or z == X0E:    # functions keys, ignore
                    msvcrt.getch()
                else:
                    if z == CR:
                        return LF
                    return z

    console = Console()

elif os.name == 'posix':
    import termios, sys, os
    class Console(object):
        def __init__(self):
            self.fd = sys.stdin.fileno()
            self.old = None

        def setup(self):
            self.old = termios.tcgetattr(self.fd)
            new = termios.tcgetattr(self.fd)
            new[3] = new[3] & ~termios.ICANON & ~termios.ECHO & ~termios.ISIG
            new[6][termios.VMIN] = 1
            new[6][termios.VTIME] = 0
            termios.tcsetattr(self.fd, termios.TCSANOW, new)

        def getkey(self):
            c = os.read(self.fd, 1)
            return c

        def cleanup(self):
            if self.old is not None:
                termios.tcsetattr(self.fd, termios.TCSAFLUSH, self.old)

    console = Console()

    def cleanup_console():
        console.cleanup()

    sys.exitfunc = cleanup_console      # terminal modes have to be restored on exit...

else:
    raise NotImplementedError("Sorry no implementation for your platform (%s) available." % sys.platform)


def dump_port_list():
    if comports:
        sys.stderr.write('\n--- Available ports:\n')
        for port, desc, hwid in sorted(comports()):
            #~ sys.stderr.write('--- %-20s %s [%s]\n' % (port, desc, hwid))
            sys.stderr.write('--- %-20s %s\n' % (port, desc))


CONVERT_CRLF = 2
CONVERT_CR   = 1
CONVERT_LF   = 0
NEWLINE_CONVERISON_MAP = (LF, CR, CRLF)
LF_MODES = ('LF', 'CR', 'CR/LF')

REPR_MODES = ('raw', 'some control', 'all control', 'hex')

class Miniterm(object):
    def __init__(self, port, baudrate, parity, rtscts, xonxoff, echo=False, convert_outgoing=CONVERT_CRLF, repr_mode=0):
        try:
            self.serial = serial.serial_for_url(port, baudrate, parity=parity, rtscts=rtscts, xonxoff=xonxoff, timeout=1)
        except AttributeError:
            # happens when the installed pyserial is older than 2.5. use the
            # Serial class directly then.
            self.serial = serial.Serial(port, baudrate, parity=parity, rtscts=rtscts, xonxoff=xonxoff, timeout=1)
        self.echo = echo
        self.repr_mode = repr_mode
        self.convert_outgoing = convert_outgoing
        self.newline = NEWLINE_CONVERISON_MAP[self.convert_outgoing]
        self.dtr_state = True
        self.rts_state = True
        self.break_state = False

    def _start_reader(self):
        """Start reader thread"""
        self._reader_alive = True
        # start serial->console thread
        self.receiver_thread = threading.Thread(target=self.reader)
        self.receiver_thread.setDaemon(True)
        self.receiver_thread.start()

    def _stop_reader(self):
        """Stop reader thread only, wait for clean exit of thread"""
        self._reader_alive = False
        self.receiver_thread.join()


    def start(self):
        self.alive = True
        self._start_reader()
        # enter console->serial loop
        self.transmitter_thread = threading.Thread(target=self.writer)
        self.transmitter_thread.setDaemon(True)
        self.transmitter_thread.start()

    def stop(self):
        self.alive = False

    def join(self, transmit_only=False):
        self.transmitter_thread.join()
        if not transmit_only:
            self.receiver_thread.join()

    def dump_port_settings(self):
        sys.stderr.write("\n--- Settings: %s  %s,%s,%s,%s\n" % (
                self.serial.portstr,
                self.serial.baudrate,
                self.serial.bytesize,
                self.serial.parity,
                self.serial.stopbits))
        sys.stderr.write('--- RTS: %-8s  DTR: %-8s  BREAK: %-8s\n' % (
                (self.rts_state and 'active' or 'inactive'),
                (self.dtr_state and 'active' or 'inactive'),
                (self.break_state and 'active' or 'inactive')))
        try:
            sys.stderr.write('--- CTS: %-8s  DSR: %-8s  RI: %-8s  CD: %-8s\n' % (
                    (self.serial.getCTS() and 'active' or 'inactive'),
                    (self.serial.getDSR() and 'active' or 'inactive'),
                    (self.serial.getRI() and 'active' or 'inactive'),
                    (self.serial.getCD() and 'active' or 'inactive')))
        except serial.SerialException:
            # on RFC 2217 ports it can happen to no modem state notification was
            # yet received. ignore this error.
            pass
        sys.stderr.write('--- software flow control: %s\n' % (self.serial.xonxoff and 'active' or 'inactive'))
        sys.stderr.write('--- hardware flow control: %s\n' % (self.serial.rtscts and 'active' or 'inactive'))
        sys.stderr.write('--- data escaping: %s  linefeed: %s\n' % (
                REPR_MODES[self.repr_mode],
                LF_MODES[self.convert_outgoing]))

    def reader(self):
        """loop and copy serial->console"""
        try:
            while self.alive and self._reader_alive:
                data = character(self.serial.read(1))

                if self.repr_mode == 0:
                    # direct output, just have to care about newline setting
                    if data == '\r' and self.convert_outgoing == CONVERT_CR:
                        sys.stdout.write('\n')
                    else:
                        sys.stdout.write(data)
                elif self.repr_mode == 1:
                    # escape non-printable, let pass newlines
                    if self.convert_outgoing == CONVERT_CRLF and data in '\r\n':
                        if data == '\n':
                            sys.stdout.write('\n')
                        elif data == '\r':
                            pass
                    elif data == '\n' and self.convert_outgoing == CONVERT_LF:
                        sys.stdout.write('\n')
                    elif data == '\r' and self.convert_outgoing == CONVERT_CR:
                        sys.stdout.write('\n')
                    else:
                        sys.stdout.write(repr(data)[1:-1])
                elif self.repr_mode == 2:
                    # escape all non-printable, including newline
                    sys.stdout.write(repr(data)[1:-1])
                elif self.repr_mode == 3:
                    # escape everything (hexdump)
                    for c in data:
                        sys.stdout.write("%s " % c.encode('hex'))
                sys.stdout.flush()
        except serial.SerialException, e:
            self.alive = False
            # would be nice if the console reader could be interruptted at this
            # point...
            raise


    def writer(self):
        """\
        Loop and copy console->serial until EXITCHARCTER character is
        found. When MENUCHARACTER is found, interpret the next key
        locally.
        """
        menu_active = False
        try:
            while self.alive:
                try:
                    b = console.getkey()
                except KeyboardInterrupt:
                    b = serial.to_bytes([3])
                c = character(b)
                if menu_active:
                    if c == MENUCHARACTER or c == EXITCHARCTER: # Menu character again/exit char -> send itself
                        self.serial.write(b)                    # send character
                        if self.echo:
                            sys.stdout.write(c)
                    elif c == '\x15':                       # CTRL+U -> upload file
                        sys.stderr.write('\n--- File to upload: ')
                        sys.stderr.flush()
                        console.cleanup()
                        filename = sys.stdin.readline().rstrip('\r\n')
                        if filename:
                            try:
                                file = open(filename, 'r')
                                sys.stderr.write('--- Sending file %s ---\n' % filename)
                                while True:
                                    line = file.readline().rstrip('\r\n')
                                    if not line:
                                        break
                                    self.serial.write(line)
                                    self.serial.write('\r\n')
                                    # Wait for output buffer to drain.
                                    self.serial.flush()
                                    sys.stderr.write('.')   # Progress indicator.
                                sys.stderr.write('\n--- File %s sent ---\n' % filename)
                            except IOError, e:
                                sys.stderr.write('--- ERROR opening file %s: %s ---\n' % (filename, e))
                        console.setup()
                    elif c in '\x08hH?':                    # CTRL+H, h, H, ? -> Show help
                        sys.stderr.write(get_help_text())
                    elif c == '\x12':                       # CTRL+R -> Toggle RTS
                        self.rts_state = not self.rts_state
                        self.serial.setRTS(self.rts_state)
                        sys.stderr.write('--- RTS %s ---\n' % (self.rts_state and 'active' or 'inactive'))
                    elif c == '\x04':                       # CTRL+D -> Toggle DTR
                        self.dtr_state = not self.dtr_state
                        self.serial.setDTR(self.dtr_state)
                        sys.stderr.write('--- DTR %s ---\n' % (self.dtr_state and 'active' or 'inactive'))
                    elif c == '\x02':                       # CTRL+B -> toggle BREAK condition
                        self.break_state = not self.break_state
                        self.serial.setBreak(self.break_state)
                        sys.stderr.write('--- BREAK %s ---\n' % (self.break_state and 'active' or 'inactive'))
                    elif c == '\x05':                       # CTRL+E -> toggle local echo
                        self.echo = not self.echo
                        sys.stderr.write('--- local echo %s ---\n' % (self.echo and 'active' or 'inactive'))
                    elif c == '\x09':                       # CTRL+I -> info
                        self.dump_port_settings()
                    elif c == '\x01':                       # CTRL+A -> cycle escape mode
                        self.repr_mode += 1
                        if self.repr_mode > 3:
                            self.repr_mode = 0
                        sys.stderr.write('--- escape data: %s ---\n' % (
                            REPR_MODES[self.repr_mode],
                        ))
                    elif c == '\x0c':                       # CTRL+L -> cycle linefeed mode
                        self.convert_outgoing += 1
                        if self.convert_outgoing > 2:
                            self.convert_outgoing = 0
                        self.newline = NEWLINE_CONVERISON_MAP[self.convert_outgoing]
                        sys.stderr.write('--- line feed %s ---\n' % (
                            LF_MODES[self.convert_outgoing],
                        ))
                    elif c in 'pP':                         # P -> change port
                        dump_port_list()
                        sys.stderr.write('--- Enter port name: ')
                        sys.stderr.flush()
                        console.cleanup()
                        try:
                            port = sys.stdin.readline().strip()
                        except KeyboardInterrupt:
                            port = None
                        console.setup()
                        if port and port != self.serial.port:
                            # reader thread needs to be shut down
                            self._stop_reader()
                            # save settings
                            settings = self.serial.getSettingsDict()
                            try:
                                try:
                                    new_serial = serial.serial_for_url(port, do_not_open=True)
                                except AttributeError:
                                    # happens when the installed pyserial is older than 2.5. use the
                                    # Serial class directly then.
                                    new_serial = serial.Serial()
                                    new_serial.port = port
                                # restore settings and open
                                new_serial.applySettingsDict(settings)
                                new_serial.open()
                                new_serial.setRTS(self.rts_state)
                                new_serial.setDTR(self.dtr_state)
                                new_serial.setBreak(self.break_state)
                            except Exception, e:
                                sys.stderr.write('--- ERROR opening new port: %s ---\n' % (e,))
                                new_serial.close()
                            else:
                                self.serial.close()
                                self.serial = new_serial
                                sys.stderr.write('--- Port changed to: %s ---\n' % (self.serial.port,))
                            # and restart the reader thread
                            self._start_reader()
                    elif c in 'bB':                         # B -> change baudrate
                        sys.stderr.write('\n--- Baudrate: ')
                        sys.stderr.flush()
                        console.cleanup()
                        backup = self.serial.baudrate
                        try:
                            self.serial.baudrate = int(sys.stdin.readline().strip())
                        except ValueError, e:
                            sys.stderr.write('--- ERROR setting baudrate: %s ---\n' % (e,))
                            self.serial.baudrate = backup
                        else:
                            self.dump_port_settings()
                        console.setup()
                    elif c == '8':                          # 8 -> change to 8 bits
                        self.serial.bytesize = serial.EIGHTBITS
                        self.dump_port_settings()
                    elif c == '7':                          # 7 -> change to 8 bits
                        self.serial.bytesize = serial.SEVENBITS
                        self.dump_port_settings()
                    elif c in 'eE':                         # E -> change to even parity
                        self.serial.parity = serial.PARITY_EVEN
                        self.dump_port_settings()
                    elif c in 'oO':                         # O -> change to odd parity
                        self.serial.parity = serial.PARITY_ODD
                        self.dump_port_settings()
                    elif c in 'mM':                         # M -> change to mark parity
                        self.serial.parity = serial.PARITY_MARK
                        self.dump_port_settings()
                    elif c in 'sS':                         # S -> change to space parity
                        self.serial.parity = serial.PARITY_SPACE
                        self.dump_port_settings()
                    elif c in 'nN':                         # N -> change to no parity
                        self.serial.parity = serial.PARITY_NONE
                        self.dump_port_settings()
                    elif c == '1':                          # 1 -> change to 1 stop bits
                        self.serial.stopbits = serial.STOPBITS_ONE
                        self.dump_port_settings()
                    elif c == '2':                          # 2 -> change to 2 stop bits
                        self.serial.stopbits = serial.STOPBITS_TWO
                        self.dump_port_settings()
                    elif c == '3':                          # 3 -> change to 1.5 stop bits
                        self.serial.stopbits = serial.STOPBITS_ONE_POINT_FIVE
                        self.dump_port_settings()
                    elif c in 'xX':                         # X -> change software flow control
                        self.serial.xonxoff = (c == 'X')
                        self.dump_port_settings()
                    elif c in 'rR':                         # R -> change hardware flow control
                        self.serial.rtscts = (c == 'R')
                        self.dump_port_settings()
                    else:
                        sys.stderr.write('--- unknown menu character %s --\n' % key_description(c))
                    menu_active = False
                elif c == MENUCHARACTER: # next char will be for menu
                    menu_active = True
                elif c == EXITCHARCTER: 
                    self.stop()
                    break                                   # exit app
                elif c == '\n':
                    self.serial.write(self.newline)         # send newline character(s)
                    if self.echo:
                        sys.stdout.write(c)                 # local echo is a real newline in any case
                        sys.stdout.flush()
                else:
                    self.serial.write(b)                    # send byte
                    if self.echo:
                        sys.stdout.write(c)
                        sys.stdout.flush()
        except:
            self.alive = False
            raise

def main():
    import optparse

    parser = optparse.OptionParser(
        usage = "%prog [options] [port [baudrate]]",
        description = "Miniterm - A simple terminal program for the serial port."
    )

    group = optparse.OptionGroup(parser, "Port settings")

    group.add_option("-p", "--port",
        dest = "port",
        help = "port, a number or a device name. (deprecated option, use parameter instead)",
        default = DEFAULT_PORT
    )

    group.add_option("-b", "--baud",
        dest = "baudrate",
        action = "store",
        type = 'int',
        help = "set baud rate, default %default",
        default = DEFAULT_BAUDRATE
    )

    group.add_option("--parity",
        dest = "parity",
        action = "store",
        help = "set parity, one of [N, E, O, S, M], default=N",
        default = 'N'
    )

    group.add_option("--rtscts",
        dest = "rtscts",
        action = "store_true",
        help = "enable RTS/CTS flow control (default off)",
        default = False
    )

    group.add_option("--xonxoff",
        dest = "xonxoff",
        action = "store_true",
        help = "enable software flow control (default off)",
        default = False
    )

    group.add_option("--rts",
        dest = "rts_state",
        action = "store",
        type = 'int',
        help = "set initial RTS line state (possible values: 0, 1)",
        default = DEFAULT_RTS
    )

    group.add_option("--dtr",
        dest = "dtr_state",
        action = "store",
        type = 'int',
        help = "set initial DTR line state (possible values: 0, 1)",
        default = DEFAULT_DTR
    )

    parser.add_option_group(group)

    group = optparse.OptionGroup(parser, "Data handling")

    group.add_option("-e", "--echo",
        dest = "echo",
        action = "store_true",
        help = "enable local echo (default off)",
        default = False
    )

    group.add_option("--cr",
        dest = "cr",
        action = "store_true",
        help = "do not send CR+LF, send CR only",
        default = False
    )

    group.add_option("--lf",
        dest = "lf",
        action = "store_true",
        help = "do not send CR+LF, send LF only",
        default = False
    )

    group.add_option("-D", "--debug",
        dest = "repr_mode",
        action = "count",
        help = """debug received data (escape non-printable chars)
--debug can be given multiple times:
0: just print what is received
1: escape non-printable characters, do newlines as unusual
2: escape non-printable characters, newlines too
3: hex dump everything""",
        default = 0
    )

    parser.add_option_group(group)


    group = optparse.OptionGroup(parser, "Hotkeys")

    group.add_option("--exit-char",
        dest = "exit_char",
        action = "store",
        type = 'int',
        help = "ASCII code of special character that is used to exit the application",
        default = 0x1d
    )

    group.add_option("--menu-char",
        dest = "menu_char",
        action = "store",
        type = 'int',
        help = "ASCII code of special character that is used to control miniterm (menu)",
        default = 0x14
    )

    parser.add_option_group(group)

    group = optparse.OptionGroup(parser, "Diagnostics")

    group.add_option("-q", "--quiet",
        dest = "quiet",
        action = "store_true",
        help = "suppress non-error messages",
        default = False
    )

    parser.add_option_group(group)


    (options, args) = parser.parse_args()

    options.parity = options.parity.upper()
    if options.parity not in 'NEOSM':
        parser.error("invalid parity")

    if options.cr and options.lf:
        parser.error("only one of --cr or --lf can be specified")

    if options.menu_char == options.exit_char:
        parser.error('--exit-char can not be the same as --menu-char')

    global EXITCHARCTER, MENUCHARACTER
    EXITCHARCTER = chr(options.exit_char)
    MENUCHARACTER = chr(options.menu_char)

    port = options.port
    baudrate = options.baudrate
    if args:
        if options.port is not None:
            parser.error("no arguments are allowed, options only when --port is given")
        port = args.pop(0)
        if args:
            try:
                baudrate = int(args[0])
            except ValueError:
                parser.error("baud rate must be a number, not %r" % args[0])
            args.pop(0)
        if args:
            parser.error("too many arguments")
    else:
        # noport given on command line -> ask user now
        if port is None:
            dump_port_list()
            port = raw_input('Enter port name:')

    convert_outgoing = CONVERT_CRLF
    if options.cr:
        convert_outgoing = CONVERT_CR
    elif options.lf:
        convert_outgoing = CONVERT_LF

    try:
        miniterm = Miniterm(
            port,
            baudrate,
            options.parity,
            rtscts=options.rtscts,
            xonxoff=options.xonxoff,
            echo=options.echo,
            convert_outgoing=convert_outgoing,
            repr_mode=options.repr_mode,
        )
    except serial.SerialException, e:
        sys.stderr.write("could not open port %r: %s\n" % (port, e))
        sys.exit(1)

    if not options.quiet:
        sys.stderr.write('--- Miniterm on %s: %d,%s,%s,%s ---\n' % (
            miniterm.serial.portstr,
            miniterm.serial.baudrate,
            miniterm.serial.bytesize,
            miniterm.serial.parity,
            miniterm.serial.stopbits,
        ))
        sys.stderr.write('--- Quit: %s  |  Menu: %s | Help: %s followed by %s ---\n' % (
            key_description(EXITCHARCTER),
            key_description(MENUCHARACTER),
            key_description(MENUCHARACTER),
            key_description('\x08'),
        ))

    if options.dtr_state is not None:
        if not options.quiet:
            sys.stderr.write('--- forcing DTR %s\n' % (options.dtr_state and 'active' or 'inactive'))
        miniterm.serial.setDTR(options.dtr_state)
        miniterm.dtr_state = options.dtr_state
    if options.rts_state is not None:
        if not options.quiet:
            sys.stderr.write('--- forcing RTS %s\n' % (options.rts_state and 'active' or 'inactive'))
        miniterm.serial.setRTS(options.rts_state)
        miniterm.rts_state = options.rts_state

    console.setup()
    miniterm.start()
    try:
        miniterm.join(True)
    except KeyboardInterrupt:
        pass
    if not options.quiet:
        sys.stderr.write("\n--- exit ---\n")
    miniterm.join()
    #~ console.cleanup()

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = protocol_hwgrep
#! python
#
# Python Serial Port Extension for Win32, Linux, BSD, Jython
# see __init__.py
#
# This module implements a special URL handler that uses the port listing to
# find ports by searching the string descriptions.
#
# (C) 2011 Chris Liechti <cliechti@gmx.net>
# this is distributed under a free software license, see license.txt
#
# URL format:    hwgrep://regexp

import serial
import serial.tools.list_ports

class Serial(serial.Serial):
    """Just inherit the native Serial port implementation and patch the open function."""

    def setPort(self, value):
        """translate port name before storing it"""
        if isinstance(value, basestring) and value.startswith('hwgrep://'):
            serial.Serial.setPort(self, self.fromURL(value))
        else:
            serial.Serial.setPort(self, value)

    def fromURL(self, url):
        """extract host and port from an URL string"""
        if url.lower().startswith("hwgrep://"): url = url[9:]
        # use a for loop to get the 1st element from the generator
        for port, desc, hwid in serial.tools.list_ports.grep(url):
            return port
        else:
            raise serial.SerialException('no ports found matching regexp %r' % (url,))

    # override property
    port = property(serial.Serial.getPort, setPort, doc="Port setting")

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
if __name__ == '__main__':
    #~ s = Serial('hwgrep://ttyS0')
    s = Serial(None)
    s.port = 'hwgrep://ttyS0'
    print s


########NEW FILE########
__FILENAME__ = protocol_loop
#! python
#
# Python Serial Port Extension for Win32, Linux, BSD, Jython
# see __init__.py
#
# This module implements a loop back connection receiving itself what it sent.
#
# The purpose of this module is.. well... You can run the unit tests with it.
# and it was so easy to implement ;-)
#
# (C) 2001-2011 Chris Liechti <cliechti@gmx.net>
# this is distributed under a free software license, see license.txt
#
# URL format:    loop://[option[/option...]]
# options:
# - "debug" print diagnostic messages

from serial.serialutil import *
import threading
import time
import logging

# map log level names to constants. used in fromURL()
LOGGER_LEVELS = {
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    }


class LoopbackSerial(SerialBase):
    """Serial port implementation that simulates a loop back connection in plain software."""

    BAUDRATES = (50, 75, 110, 134, 150, 200, 300, 600, 1200, 1800, 2400, 4800,
                 9600, 19200, 38400, 57600, 115200)

    def open(self):
        """Open port with current settings. This may throw a SerialException
           if the port cannot be opened."""
        if self._isOpen:
            raise SerialException("Port is already open.")
        self.logger = None
        self.buffer_lock = threading.Lock()
        self.loop_buffer = bytearray()
        self.cts = False
        self.dsr = False

        if self._port is None:
            raise SerialException("Port must be configured before it can be used.")
        # not that there is anything to open, but the function applies the
        # options found in the URL
        self.fromURL(self.port)

        # not that there anything to configure...
        self._reconfigurePort()
        # all things set up get, now a clean start
        self._isOpen = True
        if not self._rtscts:
            self.setRTS(True)
            self.setDTR(True)
        self.flushInput()
        self.flushOutput()

    def _reconfigurePort(self):
        """Set communication parameters on opened port. for the loop://
        protocol all settings are ignored!"""
        # not that's it of any real use, but it helps in the unit tests
        if not isinstance(self._baudrate, (int, long)) or not 0 < self._baudrate < 2**32:
            raise ValueError("invalid baudrate: %r" % (self._baudrate))
        if self.logger:
            self.logger.info('_reconfigurePort()')

    def close(self):
        """Close port"""
        if self._isOpen:
            self._isOpen = False
            # in case of quick reconnects, give the server some time
            time.sleep(0.3)

    def makeDeviceName(self, port):
        raise SerialException("there is no sensible way to turn numbers into URLs")

    def fromURL(self, url):
        """extract host and port from an URL string"""
        if url.lower().startswith("loop://"): url = url[7:]
        try:
            # process options now, directly altering self
            for option in url.split('/'):
                if '=' in option:
                    option, value = option.split('=', 1)
                else:
                    value = None
                if not option:
                    pass
                elif option == 'logging':
                    logging.basicConfig()   # XXX is that good to call it here?
                    self.logger = logging.getLogger('pySerial.loop')
                    self.logger.setLevel(LOGGER_LEVELS[value])
                    self.logger.debug('enabled logging')
                else:
                    raise ValueError('unknown option: %r' % (option,))
        except ValueError, e:
            raise SerialException('expected a string in the form "[loop://][option[/option...]]": %s' % e)

    #  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -

    def inWaiting(self):
        """Return the number of characters currently in the input buffer."""
        if not self._isOpen: raise portNotOpenError
        if self.logger:
            # attention the logged value can differ from return value in
            # threaded environments...
            self.logger.debug('inWaiting() -> %d' % (len(self.loop_buffer),))
        return len(self.loop_buffer)

    def read(self, size=1):
        """Read size bytes from the serial port. If a timeout is set it may
        return less characters as requested. With no timeout it will block
        until the requested number of bytes is read."""
        if not self._isOpen: raise portNotOpenError
        if self._timeout is not None:
            timeout = time.time() + self._timeout
        else:
            timeout = None
        data = bytearray()
        while size > 0:
            self.buffer_lock.acquire()
            try:
                block = to_bytes(self.loop_buffer[:size])
                del self.loop_buffer[:size]
            finally:
                self.buffer_lock.release()
            data += block
            size -= len(block)
            # check for timeout now, after data has been read.
            # useful for timeout = 0 (non blocking) read
            if timeout and time.time() > timeout:
                break
        return bytes(data)

    def write(self, data):
        """Output the given string over the serial port. Can block if the
        connection is blocked. May raise SerialException if the connection is
        closed."""
        if not self._isOpen: raise portNotOpenError
        # ensure we're working with bytes
        data = to_bytes(data)
        # calculate aprox time that would be used to send the data
        time_used_to_send = 10.0*len(data) / self._baudrate
        # when a write timeout is configured check if we would be successful
        # (not sending anything, not even the part that would have time)
        if self._writeTimeout is not None and time_used_to_send > self._writeTimeout:
            time.sleep(self._writeTimeout) # must wait so that unit test succeeds
            raise writeTimeoutError
        self.buffer_lock.acquire()
        try:
            self.loop_buffer += data
        finally:
            self.buffer_lock.release()
        return len(data)

    def flushInput(self):
        """Clear input buffer, discarding all that is in the buffer."""
        if not self._isOpen: raise portNotOpenError
        if self.logger:
            self.logger.info('flushInput()')
        self.buffer_lock.acquire()
        try:
            del self.loop_buffer[:]
        finally:
            self.buffer_lock.release()

    def flushOutput(self):
        """Clear output buffer, aborting the current output and
        discarding all that is in the buffer."""
        if not self._isOpen: raise portNotOpenError
        if self.logger:
            self.logger.info('flushOutput()')

    def sendBreak(self, duration=0.25):
        """Send break condition. Timed, returns to idle state after given
        duration."""
        if not self._isOpen: raise portNotOpenError

    def setBreak(self, level=True):
        """Set break: Controls TXD. When active, to transmitting is
        possible."""
        if not self._isOpen: raise portNotOpenError
        if self.logger:
            self.logger.info('setBreak(%r)' % (level,))

    def setRTS(self, level=True):
        """Set terminal status line: Request To Send"""
        if not self._isOpen: raise portNotOpenError
        if self.logger:
            self.logger.info('setRTS(%r) -> state of CTS' % (level,))
        self.cts = level

    def setDTR(self, level=True):
        """Set terminal status line: Data Terminal Ready"""
        if not self._isOpen: raise portNotOpenError
        if self.logger:
            self.logger.info('setDTR(%r) -> state of DSR' % (level,))
        self.dsr = level

    def getCTS(self):
        """Read terminal status line: Clear To Send"""
        if not self._isOpen: raise portNotOpenError
        if self.logger:
            self.logger.info('getCTS() -> state of RTS (%r)' % (self.cts,))
        return self.cts

    def getDSR(self):
        """Read terminal status line: Data Set Ready"""
        if not self._isOpen: raise portNotOpenError
        if self.logger:
            self.logger.info('getDSR() -> state of DTR (%r)' % (self.dsr,))
        return self.dsr

    def getRI(self):
        """Read terminal status line: Ring Indicator"""
        if not self._isOpen: raise portNotOpenError
        if self.logger:
            self.logger.info('returning dummy for getRI()')
        return False

    def getCD(self):
        """Read terminal status line: Carrier Detect"""
        if not self._isOpen: raise portNotOpenError
        if self.logger:
            self.logger.info('returning dummy for getCD()')
        return True

    # - - - platform specific - - -
    # None so far


# assemble Serial class with the platform specific implementation and the base
# for file-like behavior. for Python 2.6 and newer, that provide the new I/O
# library, derive from io.RawIOBase
try:
    import io
except ImportError:
    # classic version with our own file-like emulation
    class Serial(LoopbackSerial, FileLike):
        pass
else:
    # io library present
    class Serial(LoopbackSerial, io.RawIOBase):
        pass


# simple client test
if __name__ == '__main__':
    import sys
    s = Serial('loop://')
    sys.stdout.write('%s\n' % s)

    sys.stdout.write("write...\n")
    s.write("hello\n")
    s.flush()
    sys.stdout.write("read: %s\n" % s.read(5))

    s.close()

########NEW FILE########
__FILENAME__ = protocol_rfc2217
#! python
#
# Python Serial Port Extension for Win32, Linux, BSD, Jython
# see ../__init__.py
#
# This is a thin wrapper to load the rfc2271 implementation.
#
# (C) 2011 Chris Liechti <cliechti@gmx.net>
# this is distributed under a free software license, see license.txt

from serial.rfc2217 import Serial

########NEW FILE########
__FILENAME__ = protocol_socket
#! python
#
# Python Serial Port Extension for Win32, Linux, BSD, Jython
# see __init__.py
#
# This module implements a simple socket based client.
# It does not support changing any port parameters and will silently ignore any
# requests to do so.
#
# The purpose of this module is that applications using pySerial can connect to
# TCP/IP to serial port converters that do not support RFC 2217.
#
# (C) 2001-2011 Chris Liechti <cliechti@gmx.net>
# this is distributed under a free software license, see license.txt
#
# URL format:    socket://<host>:<port>[/option[/option...]]
# options:
# - "debug" print diagnostic messages

from serial.serialutil import *
import time
import socket
import logging

# map log level names to constants. used in fromURL()
LOGGER_LEVELS = {
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    }

POLL_TIMEOUT = 2

class SocketSerial(SerialBase):
    """Serial port implementation for plain sockets."""

    BAUDRATES = (50, 75, 110, 134, 150, 200, 300, 600, 1200, 1800, 2400, 4800,
                 9600, 19200, 38400, 57600, 115200)

    def open(self):
        """Open port with current settings. This may throw a SerialException
           if the port cannot be opened."""
        self.logger = None
        if self._port is None:
            raise SerialException("Port must be configured before it can be used.")
        if self._isOpen:
            raise SerialException("Port is already open.")
        try:
            # XXX in future replace with create_connection (py >=2.6)
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.connect(self.fromURL(self.portstr))
        except Exception, msg:
            self._socket = None
            raise SerialException("Could not open port %s: %s" % (self.portstr, msg))

        self._socket.settimeout(POLL_TIMEOUT) # used for write timeout support :/

        # not that there anything to configure...
        self._reconfigurePort()
        # all things set up get, now a clean start
        self._isOpen = True
        if not self._rtscts:
            self.setRTS(True)
            self.setDTR(True)
        self.flushInput()
        self.flushOutput()

    def _reconfigurePort(self):
        """Set communication parameters on opened port. for the socket://
        protocol all settings are ignored!"""
        if self._socket is None:
            raise SerialException("Can only operate on open ports")
        if self.logger:
            self.logger.info('ignored port configuration change')

    def close(self):
        """Close port"""
        if self._isOpen:
            if self._socket:
                try:
                    self._socket.shutdown(socket.SHUT_RDWR)
                    self._socket.close()
                except:
                    # ignore errors.
                    pass
                self._socket = None
            self._isOpen = False
            # in case of quick reconnects, give the server some time
            time.sleep(0.3)

    def makeDeviceName(self, port):
        raise SerialException("there is no sensible way to turn numbers into URLs")

    def fromURL(self, url):
        """extract host and port from an URL string"""
        if url.lower().startswith("socket://"): url = url[9:]
        try:
            # is there a "path" (our options)?
            if '/' in url:
                # cut away options
                url, options = url.split('/', 1)
                # process options now, directly altering self
                for option in options.split('/'):
                    if '=' in option:
                        option, value = option.split('=', 1)
                    else:
                        value = None
                    if option == 'logging':
                        logging.basicConfig()   # XXX is that good to call it here?
                        self.logger = logging.getLogger('pySerial.socket')
                        self.logger.setLevel(LOGGER_LEVELS[value])
                        self.logger.debug('enabled logging')
                    else:
                        raise ValueError('unknown option: %r' % (option,))
            # get host and port
            host, port = url.split(':', 1) # may raise ValueError because of unpacking
            port = int(port)               # and this if it's not a number
            if not 0 <= port < 65536: raise ValueError("port not in range 0...65535")
        except ValueError, e:
            raise SerialException('expected a string in the form "[rfc2217://]<host>:<port>[/option[/option...]]": %s' % e)
        return (host, port)

    #  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -

    def inWaiting(self):
        """Return the number of characters currently in the input buffer."""
        if not self._isOpen: raise portNotOpenError
        if self.logger:
            # set this one to debug as the function could be called often...
            self.logger.debug('WARNING: inWaiting returns dummy value')
        return 0 # hmmm, see comment in read()

    def read(self, size=1):
        """Read size bytes from the serial port. If a timeout is set it may
        return less characters as requested. With no timeout it will block
        until the requested number of bytes is read."""
        if not self._isOpen: raise portNotOpenError
        data = bytearray()
        if self._timeout is not None:
            timeout = time.time() + self._timeout
        else:
            timeout = None
        while len(data) < size and (timeout is None or time.time() < timeout):
            try:
                # an implementation with internal buffer would be better
                # performing...
                t = time.time()
                block = self._socket.recv(size - len(data))
                duration = time.time() - t
                if block:
                    data.extend(block)
                else:
                    # no data -> EOF (connection probably closed)
                    break
            except socket.timeout:
                # just need to get out of recv from time to time to check if
                # still alive
                continue
            except socket.error, e:
                # connection fails -> terminate loop
                raise SerialException('connection failed (%s)' % e)
        return bytes(data)

    def write(self, data):
        """Output the given string over the serial port. Can block if the
        connection is blocked. May raise SerialException if the connection is
        closed."""
        if not self._isOpen: raise portNotOpenError
        try:
            self._socket.sendall(to_bytes(data))
        except socket.error, e:
            # XXX what exception if socket connection fails
            raise SerialException("socket connection failed: %s" % e)
        return len(data)

    def flushInput(self):
        """Clear input buffer, discarding all that is in the buffer."""
        if not self._isOpen: raise portNotOpenError
        if self.logger:
            self.logger.info('ignored flushInput')

    def flushOutput(self):
        """Clear output buffer, aborting the current output and
        discarding all that is in the buffer."""
        if not self._isOpen: raise portNotOpenError
        if self.logger:
            self.logger.info('ignored flushOutput')

    def sendBreak(self, duration=0.25):
        """Send break condition. Timed, returns to idle state after given
        duration."""
        if not self._isOpen: raise portNotOpenError
        if self.logger:
            self.logger.info('ignored sendBreak(%r)' % (duration,))

    def setBreak(self, level=True):
        """Set break: Controls TXD. When active, to transmitting is
        possible."""
        if not self._isOpen: raise portNotOpenError
        if self.logger:
            self.logger.info('ignored setBreak(%r)' % (level,))

    def setRTS(self, level=True):
        """Set terminal status line: Request To Send"""
        if not self._isOpen: raise portNotOpenError
        if self.logger:
            self.logger.info('ignored setRTS(%r)' % (level,))

    def setDTR(self, level=True):
        """Set terminal status line: Data Terminal Ready"""
        if not self._isOpen: raise portNotOpenError
        if self.logger:
            self.logger.info('ignored setDTR(%r)' % (level,))

    def getCTS(self):
        """Read terminal status line: Clear To Send"""
        if not self._isOpen: raise portNotOpenError
        if self.logger:
            self.logger.info('returning dummy for getCTS()')
        return True

    def getDSR(self):
        """Read terminal status line: Data Set Ready"""
        if not self._isOpen: raise portNotOpenError
        if self.logger:
            self.logger.info('returning dummy for getDSR()')
        return True

    def getRI(self):
        """Read terminal status line: Ring Indicator"""
        if not self._isOpen: raise portNotOpenError
        if self.logger:
            self.logger.info('returning dummy for getRI()')
        return False

    def getCD(self):
        """Read terminal status line: Carrier Detect"""
        if not self._isOpen: raise portNotOpenError
        if self.logger:
            self.logger.info('returning dummy for getCD()')
        return True

    # - - - platform specific - - -
    # None so far


# assemble Serial class with the platform specific implementation and the base
# for file-like behavior. for Python 2.6 and newer, that provide the new I/O
# library, derive from io.RawIOBase
try:
    import io
except ImportError:
    # classic version with our own file-like emulation
    class Serial(SocketSerial, FileLike):
        pass
else:
    # io library present
    class Serial(SocketSerial, io.RawIOBase):
        pass


# simple client test
if __name__ == '__main__':
    import sys
    s = Serial('socket://localhost:7000')
    sys.stdout.write('%s\n' % s)

    sys.stdout.write("write...\n")
    s.write("hello\n")
    s.flush()
    sys.stdout.write("read: %s\n" % s.read(5))

    s.close()

########NEW FILE########
__FILENAME__ = win32
from ctypes import *
from ctypes.wintypes import HANDLE
from ctypes.wintypes import BOOL
from ctypes.wintypes import LPCWSTR
_stdcall_libraries = {}
_stdcall_libraries['kernel32'] = WinDLL('kernel32')
from ctypes.wintypes import DWORD
from ctypes.wintypes import WORD
from ctypes.wintypes import BYTE

INVALID_HANDLE_VALUE = HANDLE(-1).value

# some details of the windows API differ between 32 and 64 bit systems..
def is_64bit():
    """Returns true when running on a 64 bit system"""
    return sizeof(c_ulong) != sizeof(c_void_p)

# ULONG_PTR is a an ordinary number, not a pointer and contrary to the name it
# is either 32 or 64 bits, depending on the type of windows...
# so test if this a 32 bit windows...
if is_64bit():
    # assume 64 bits
    ULONG_PTR = c_int64
else:
    # 32 bits
    ULONG_PTR = c_ulong


class _SECURITY_ATTRIBUTES(Structure):
    pass
LPSECURITY_ATTRIBUTES = POINTER(_SECURITY_ATTRIBUTES)


try:
    CreateEventW = _stdcall_libraries['kernel32'].CreateEventW
except AttributeError:
    # Fallback to non wide char version for old OS...
    from ctypes.wintypes import LPCSTR
    CreateEventA = _stdcall_libraries['kernel32'].CreateEventA
    CreateEventA.restype = HANDLE
    CreateEventA.argtypes = [LPSECURITY_ATTRIBUTES, BOOL, BOOL, LPCSTR]
    CreateEvent=CreateEventA

    CreateFileA = _stdcall_libraries['kernel32'].CreateFileA
    CreateFileA.restype = HANDLE
    CreateFileA.argtypes = [LPCSTR, DWORD, DWORD, LPSECURITY_ATTRIBUTES, DWORD, DWORD, HANDLE]
    CreateFile = CreateFileA
else:
    CreateEventW.restype = HANDLE
    CreateEventW.argtypes = [LPSECURITY_ATTRIBUTES, BOOL, BOOL, LPCWSTR]
    CreateEvent = CreateEventW # alias

    CreateFileW = _stdcall_libraries['kernel32'].CreateFileW
    CreateFileW.restype = HANDLE
    CreateFileW.argtypes = [LPCWSTR, DWORD, DWORD, LPSECURITY_ATTRIBUTES, DWORD, DWORD, HANDLE]
    CreateFile = CreateFileW # alias

class _OVERLAPPED(Structure):
    pass
OVERLAPPED = _OVERLAPPED

class _COMSTAT(Structure):
    pass
COMSTAT = _COMSTAT

class _DCB(Structure):
    pass
DCB = _DCB

class _COMMTIMEOUTS(Structure):
    pass
COMMTIMEOUTS = _COMMTIMEOUTS

GetLastError = _stdcall_libraries['kernel32'].GetLastError
GetLastError.restype = DWORD
GetLastError.argtypes = []

LPOVERLAPPED = POINTER(_OVERLAPPED)
LPDWORD = POINTER(DWORD)

GetOverlappedResult = _stdcall_libraries['kernel32'].GetOverlappedResult
GetOverlappedResult.restype = BOOL
GetOverlappedResult.argtypes = [HANDLE, LPOVERLAPPED, LPDWORD, BOOL]

ResetEvent = _stdcall_libraries['kernel32'].ResetEvent
ResetEvent.restype = BOOL
ResetEvent.argtypes = [HANDLE]

LPCVOID = c_void_p

WriteFile = _stdcall_libraries['kernel32'].WriteFile
WriteFile.restype = BOOL
WriteFile.argtypes = [HANDLE, LPCVOID, DWORD, LPDWORD, LPOVERLAPPED]

LPVOID = c_void_p

ReadFile = _stdcall_libraries['kernel32'].ReadFile
ReadFile.restype = BOOL
ReadFile.argtypes = [HANDLE, LPVOID, DWORD, LPDWORD, LPOVERLAPPED]

CloseHandle = _stdcall_libraries['kernel32'].CloseHandle
CloseHandle.restype = BOOL
CloseHandle.argtypes = [HANDLE]

ClearCommBreak = _stdcall_libraries['kernel32'].ClearCommBreak
ClearCommBreak.restype = BOOL
ClearCommBreak.argtypes = [HANDLE]

LPCOMSTAT = POINTER(_COMSTAT)

ClearCommError = _stdcall_libraries['kernel32'].ClearCommError
ClearCommError.restype = BOOL
ClearCommError.argtypes = [HANDLE, LPDWORD, LPCOMSTAT]

SetupComm = _stdcall_libraries['kernel32'].SetupComm
SetupComm.restype = BOOL
SetupComm.argtypes = [HANDLE, DWORD, DWORD]

EscapeCommFunction = _stdcall_libraries['kernel32'].EscapeCommFunction
EscapeCommFunction.restype = BOOL
EscapeCommFunction.argtypes = [HANDLE, DWORD]

GetCommModemStatus = _stdcall_libraries['kernel32'].GetCommModemStatus
GetCommModemStatus.restype = BOOL
GetCommModemStatus.argtypes = [HANDLE, LPDWORD]

LPDCB = POINTER(_DCB)

GetCommState = _stdcall_libraries['kernel32'].GetCommState
GetCommState.restype = BOOL
GetCommState.argtypes = [HANDLE, LPDCB]

LPCOMMTIMEOUTS = POINTER(_COMMTIMEOUTS)

GetCommTimeouts = _stdcall_libraries['kernel32'].GetCommTimeouts
GetCommTimeouts.restype = BOOL
GetCommTimeouts.argtypes = [HANDLE, LPCOMMTIMEOUTS]

PurgeComm = _stdcall_libraries['kernel32'].PurgeComm
PurgeComm.restype = BOOL
PurgeComm.argtypes = [HANDLE, DWORD]

SetCommBreak = _stdcall_libraries['kernel32'].SetCommBreak
SetCommBreak.restype = BOOL
SetCommBreak.argtypes = [HANDLE]

SetCommMask = _stdcall_libraries['kernel32'].SetCommMask
SetCommMask.restype = BOOL
SetCommMask.argtypes = [HANDLE, DWORD]

SetCommState = _stdcall_libraries['kernel32'].SetCommState
SetCommState.restype = BOOL
SetCommState.argtypes = [HANDLE, LPDCB]

SetCommTimeouts = _stdcall_libraries['kernel32'].SetCommTimeouts
SetCommTimeouts.restype = BOOL
SetCommTimeouts.argtypes = [HANDLE, LPCOMMTIMEOUTS]

WaitForSingleObject = _stdcall_libraries['kernel32'].WaitForSingleObject
WaitForSingleObject.restype = DWORD
WaitForSingleObject.argtypes = [HANDLE, DWORD]

ONESTOPBIT = 0 # Variable c_int
TWOSTOPBITS = 2 # Variable c_int
ONE5STOPBITS = 1

NOPARITY = 0 # Variable c_int
ODDPARITY = 1 # Variable c_int
EVENPARITY = 2 # Variable c_int
MARKPARITY = 3
SPACEPARITY = 4

RTS_CONTROL_HANDSHAKE = 2 # Variable c_int
RTS_CONTROL_DISABLE = 0 # Variable c_int
RTS_CONTROL_ENABLE = 1 # Variable c_int
RTS_CONTROL_TOGGLE = 3 # Variable c_int
SETRTS = 3
CLRRTS = 4

DTR_CONTROL_HANDSHAKE = 2 # Variable c_int
DTR_CONTROL_DISABLE = 0 # Variable c_int
DTR_CONTROL_ENABLE = 1 # Variable c_int
SETDTR = 5
CLRDTR = 6

MS_DSR_ON = 32 # Variable c_ulong
EV_RING = 256 # Variable c_int
EV_PERR = 512 # Variable c_int
EV_ERR = 128 # Variable c_int
SETXOFF = 1 # Variable c_int
EV_RXCHAR = 1 # Variable c_int
GENERIC_WRITE = 1073741824 # Variable c_long
PURGE_TXCLEAR = 4 # Variable c_int
FILE_FLAG_OVERLAPPED = 1073741824 # Variable c_int
EV_DSR = 16 # Variable c_int
MAXDWORD = 4294967295L # Variable c_uint
EV_RLSD = 32 # Variable c_int
ERROR_IO_PENDING = 997 # Variable c_long
MS_CTS_ON = 16 # Variable c_ulong
EV_EVENT1 = 2048 # Variable c_int
EV_RX80FULL = 1024 # Variable c_int
PURGE_RXABORT = 2 # Variable c_int
FILE_ATTRIBUTE_NORMAL = 128 # Variable c_int
PURGE_TXABORT = 1 # Variable c_int
SETXON = 2 # Variable c_int
OPEN_EXISTING = 3 # Variable c_int
MS_RING_ON = 64 # Variable c_ulong
EV_TXEMPTY = 4 # Variable c_int
EV_RXFLAG = 2 # Variable c_int
MS_RLSD_ON = 128 # Variable c_ulong
GENERIC_READ = 2147483648L # Variable c_ulong
EV_EVENT2 = 4096 # Variable c_int
EV_CTS = 8 # Variable c_int
EV_BREAK = 64 # Variable c_int
PURGE_RXCLEAR = 8 # Variable c_int
INFINITE = 0xFFFFFFFFL


class N11_OVERLAPPED4DOLLAR_48E(Union):
    pass
class N11_OVERLAPPED4DOLLAR_484DOLLAR_49E(Structure):
    pass
N11_OVERLAPPED4DOLLAR_484DOLLAR_49E._fields_ = [
    ('Offset', DWORD),
    ('OffsetHigh', DWORD),
]

PVOID = c_void_p

N11_OVERLAPPED4DOLLAR_48E._anonymous_ = ['_0']
N11_OVERLAPPED4DOLLAR_48E._fields_ = [
    ('_0', N11_OVERLAPPED4DOLLAR_484DOLLAR_49E),
    ('Pointer', PVOID),
]
_OVERLAPPED._anonymous_ = ['_0']
_OVERLAPPED._fields_ = [
    ('Internal', ULONG_PTR),
    ('InternalHigh', ULONG_PTR),
    ('_0', N11_OVERLAPPED4DOLLAR_48E),
    ('hEvent', HANDLE),
]
_SECURITY_ATTRIBUTES._fields_ = [
    ('nLength', DWORD),
    ('lpSecurityDescriptor', LPVOID),
    ('bInheritHandle', BOOL),
]
_COMSTAT._fields_ = [
    ('fCtsHold', DWORD, 1),
    ('fDsrHold', DWORD, 1),
    ('fRlsdHold', DWORD, 1),
    ('fXoffHold', DWORD, 1),
    ('fXoffSent', DWORD, 1),
    ('fEof', DWORD, 1),
    ('fTxim', DWORD, 1),
    ('fReserved', DWORD, 25),
    ('cbInQue', DWORD),
    ('cbOutQue', DWORD),
]
_DCB._fields_ = [
    ('DCBlength', DWORD),
    ('BaudRate', DWORD),
    ('fBinary', DWORD, 1),
    ('fParity', DWORD, 1),
    ('fOutxCtsFlow', DWORD, 1),
    ('fOutxDsrFlow', DWORD, 1),
    ('fDtrControl', DWORD, 2),
    ('fDsrSensitivity', DWORD, 1),
    ('fTXContinueOnXoff', DWORD, 1),
    ('fOutX', DWORD, 1),
    ('fInX', DWORD, 1),
    ('fErrorChar', DWORD, 1),
    ('fNull', DWORD, 1),
    ('fRtsControl', DWORD, 2),
    ('fAbortOnError', DWORD, 1),
    ('fDummy2', DWORD, 17),
    ('wReserved', WORD),
    ('XonLim', WORD),
    ('XoffLim', WORD),
    ('ByteSize', BYTE),
    ('Parity', BYTE),
    ('StopBits', BYTE),
    ('XonChar', c_char),
    ('XoffChar', c_char),
    ('ErrorChar', c_char),
    ('EofChar', c_char),
    ('EvtChar', c_char),
    ('wReserved1', WORD),
]
_COMMTIMEOUTS._fields_ = [
    ('ReadIntervalTimeout', DWORD),
    ('ReadTotalTimeoutMultiplier', DWORD),
    ('ReadTotalTimeoutConstant', DWORD),
    ('WriteTotalTimeoutMultiplier', DWORD),
    ('WriteTotalTimeoutConstant', DWORD),
]
__all__ = ['GetLastError', 'MS_CTS_ON', 'FILE_ATTRIBUTE_NORMAL',
           'DTR_CONTROL_ENABLE', '_COMSTAT', 'MS_RLSD_ON',
           'GetOverlappedResult', 'SETXON', 'PURGE_TXABORT',
           'PurgeComm', 'N11_OVERLAPPED4DOLLAR_48E', 'EV_RING',
           'ONESTOPBIT', 'SETXOFF', 'PURGE_RXABORT', 'GetCommState',
           'RTS_CONTROL_ENABLE', '_DCB', 'CreateEvent',
           '_COMMTIMEOUTS', '_SECURITY_ATTRIBUTES', 'EV_DSR',
           'EV_PERR', 'EV_RXFLAG', 'OPEN_EXISTING', 'DCB',
           'FILE_FLAG_OVERLAPPED', 'EV_CTS', 'SetupComm',
           'LPOVERLAPPED', 'EV_TXEMPTY', 'ClearCommBreak',
           'LPSECURITY_ATTRIBUTES', 'SetCommBreak', 'SetCommTimeouts',
           'COMMTIMEOUTS', 'ODDPARITY', 'EV_RLSD',
           'GetCommModemStatus', 'EV_EVENT2', 'PURGE_TXCLEAR',
           'EV_BREAK', 'EVENPARITY', 'LPCVOID', 'COMSTAT', 'ReadFile',
           'PVOID', '_OVERLAPPED', 'WriteFile', 'GetCommTimeouts',
           'ResetEvent', 'EV_RXCHAR', 'LPCOMSTAT', 'ClearCommError',
           'ERROR_IO_PENDING', 'EscapeCommFunction', 'GENERIC_READ',
           'RTS_CONTROL_HANDSHAKE', 'OVERLAPPED',
           'DTR_CONTROL_HANDSHAKE', 'PURGE_RXCLEAR', 'GENERIC_WRITE',
           'LPDCB', 'CreateEventW', 'SetCommMask', 'EV_EVENT1',
           'SetCommState', 'LPVOID', 'CreateFileW', 'LPDWORD',
           'EV_RX80FULL', 'TWOSTOPBITS', 'LPCOMMTIMEOUTS', 'MAXDWORD',
           'MS_DSR_ON', 'MS_RING_ON',
           'N11_OVERLAPPED4DOLLAR_484DOLLAR_49E', 'EV_ERR',
           'ULONG_PTR', 'CreateFile', 'NOPARITY', 'CloseHandle']

########NEW FILE########
