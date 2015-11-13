__FILENAME__ = cli
#
# rtlsdr_scan
#
# http://eartoearoak.com/software/rtlsdr-scanner
#
# Copyright 2012 - 2014 Al Brown
#
# A frequency scanning GUI for the OsmoSDR rtl-sdr library at
# http://sdr.osmocom.org/trac/wiki/rtl-sdr
#
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import Queue
import os
import sys
from threading import Thread
import threading
from urlparse import urlparse

from constants import SAMPLE_RATE
from devices import DeviceRTL, get_devices_rtl
from events import Event, post_event, EventThread
from file import save_plot, export_plot, ScanInfo, File
from misc import nearest, calc_real_dwell, next_2_to_pow
from scan import ThreadScan, anaylse_data, update_spectrum
from settings import Settings


class Cli():
    def __init__(self, pool, args):
        start = args.start
        end = args.end
        gain = args.gain
        dwell = args.dwell
        nfft = args.fft
        lo = args.lo
        index = args.index
        remote = args.remote
        directory, filename = os.path.split(args.file)
        _null, ext = os.path.splitext(args.file)

        self.lock = threading.Lock()

        self.stepsTotal = 0
        self.steps = 0

        self.spectrum = {}
        self.settings = Settings(load=False)

        self.queue = Queue.Queue()

        error = None

        if end <= start:
            error = "Start should be lower than end"
        elif dwell <= 0:
            error = "Dwell should be positive"
        elif nfft <= 0:
            error = "FFT bins should be positive"
        elif ext != ".rfs" and File.get_type_index(ext) == -1:
            error = "File extension should be "
            error += File.get_type_pretty(File.Types.SAVE)
            error += File.get_type_pretty(File.Types.PLOT)
        else:
            device = DeviceRTL()
            if remote is None:
                self.settings.devicesRtl = get_devices_rtl()
                count = len(self.settings.devicesRtl)
                if index > count - 1:
                    error = "Device not found ({0} devices in total):\n".format(count)
                    for device in self.settings.devicesRtl:
                        error += "\t{0}: {1}\n".format(device.indexRtl,
                                                       device.name)
            else:
                device.isDevice = False
                url = urlparse('//' + remote)
                if url.hostname is not None:
                    device.server = url.hostname
                else:
                    error = "Invalid hostname"
                if url.port is not None:
                    device.port = url.port
                else:
                    device.port = 1234
                self.settings.devicesRtl.append(device)
                index = len(self.settings.devicesRtl) - 1

        if error is not None:
            print "Error: {0}".format(error)
            exit(1)

        if end - 1 < start:
            end = start + 1
        if remote is None:
            gain = nearest(gain, self.settings.devicesRtl[index].gains)

        self.settings.start = start
        self.settings.stop = end
        self.settings.dwell = calc_real_dwell(dwell)
        self.settings.nfft = nfft
        self.settings.devicesRtl[index].gain = gain
        self.settings.devicesRtl[index].lo = lo

        print "{0} - {1}MHz".format(start, end)
        print "{0}dB Gain".format(gain)
        print "{0}s Dwell".format(self.settings.dwell)
        print "{0} FFT points".format(nfft)
        print "{0}MHz LO".format(lo)
        if remote is not None:
            print remote
        else:
            print self.settings.devicesRtl[index].name

        self.__scan(self.settings, index, pool)

        fullName = os.path.join(directory, filename)
        if ext == ".rfs":
            scanInfo = ScanInfo()
            scanInfo.setFromSettings(self.settings)

            save_plot(fullName, scanInfo, self.spectrum, None)
        else:
            exportType = File.get_type_index(ext)
            export_plot(fullName, exportType, self.spectrum)

        print "Done"

    def __scan(self, settings, index, pool):
        samples = settings.dwell * SAMPLE_RATE
        samples = next_2_to_pow(int(samples))
        threadScan = ThreadScan(self.queue, None, settings, index, samples,
                                False)
        while threadScan.isAlive() or self.steps > 0:
            if not self.queue.empty():
                self.__process_event(self.queue, pool)
        print ""

    def __process_event(self, queue, pool):
        event = queue.get()
        status = event.data.get_status()
        freq = event.data.get_arg1()
        data = event.data.get_arg2()

        if status == Event.STARTING:
            print "Starting"
        elif status == Event.STEPS:
            self.stepsTotal = (freq + 1) * 2
            self.steps = self.stepsTotal
        elif status == Event.INFO:
            if data != -1:
                self.settings.devicesRtl[self.settings.indexRtl].tuner = data
        elif status == Event.DATA:
            cal = self.settings.devicesRtl[self.settings.indexRtl].calibration
            pool.apply_async(anaylse_data, (freq, data, cal,
                                            self.settings.nfft,
                                            self.settings.overlap,
                                            "Hamming"),
                             callback=self.__on_process_done)
            self.__progress()
        elif status == Event.ERROR:
            print "Error: {0}".format(data)
            exit(1)
        elif status == Event.PROCESSED:
            offset = self.settings.devicesRtl[self.settings.indexRtl].offset
            Thread(target=update_spectrum, name='Update',
                   args=(queue, self.lock, self.settings.start,
                         self.settings.stop, freq,
                         data, offset, self.spectrum, False,)).start()
        elif status == Event.UPDATED:
            self.__progress()

    def __on_process_done(self, data):
        timeStamp, freq, scan = data
        post_event(self.queue, EventThread(Event.PROCESSED, freq,
                                                 (timeStamp, scan)))

    def __progress(self):
        self.steps -= 1
        comp = (self.stepsTotal - self.steps) * 100 / self.stepsTotal
        sys.stdout.write("\r{0:.1f}%".format(comp))


if __name__ == '__main__':
    print 'Please run rtlsdr_scan.py'
    exit(1)

########NEW FILE########
__FILENAME__ = constants
#
# rtlsdr_scan
#
# http://eartoearoak.com/software/rtlsdr-scanner
#
# Copyright 2012 - 2014 Al Brown
#
# A frequency scanning GUI for the OsmoSDR rtl-sdr library at
# http://sdr.osmocom.org/trac/wiki/rtl-sdr
#
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import numpy


F_MIN = 0
F_MAX = 9999
GAIN = 0
SAMPLE_RATE = 2e6
BANDWIDTH = 500e3
TIMESTAMP_FILE = 'version-timestamp'

MODE = ["Single", 0,
        "Continuous", 1]

NFFT = [16,
        32,
        64,
        128,
        512,
        1024,
        2048,
        4096,
        8192,
        16384,
        32768]

DWELL = ["16 ms", 0.016,
         "32 ms", 0.032,
         "65 ms", 0.065,
         "131 ms", 0.131,
         "262 ms", 0.262,
         "524 ms", 0.524,
         "1 s", 1.048,
         "2 s", 2.097,
         "8 s", 8.388]

DISPLAY = ["Plot", 0,
           "Spectrogram", 1,
           "3D Spectrogram", 2]

TUNER = ["Unknown",
         "Elonics E4000",
         "Fitipower FC0012",
         "Fitipower FC0013",
         "FCI FC2580",
         "Rafael Micro R820T",
         "Rafael Micro R828D"]

WINFUNC = ["Bartlett", numpy.bartlett,
           "Blackman", numpy.blackman,
           "Hamming", numpy.hamming,
           "Hanning", numpy.hanning]


class Warn:
    SCAN, OPEN, EXIT, NEW = range(4)


class Cal:
    START, DONE, OK, CANCEL = range(4)


class Display:
    PLOT, SPECT, SURFACE = range(3)


class Mode:
    SINGLE, CONTIN = range(2)


class Plot:
    STR_FULL = 'Full'
    STR_PARTIAL = 'Partial'


class PlotFunc:
    NONE, AVG, MIN, MAX, VAR = range(5)


class Markers:
    MIN, MAX, AVG, GMEAN, \
    HP, HFS, HFE, \
    OP, OFS, OFE = range(10)


if __name__ == '__main__':
    print 'Please run rtlsdr_scan.py'
    exit(1)

########NEW FILE########
__FILENAME__ = devices
#
# rtlsdr_scan
#
# http://eartoearoak.com/software/rtlsdr-scanner
#
# Copyright 2012 -2014 Al Brown
#
# A frequency scanning GUI for the OsmoSDR rtl-sdr library at
# http://sdr.osmocom.org/trac/wiki/rtl-sdr
#
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
from ctypes import c_ubyte, string_at

import rtlsdr
import serial


class DeviceGPS():
    NMEA_SERIAL, GPSD, GPSD_OLD, NMEA_TCP = range(4)
    TYPE = ['NMEA (Serial)', 'GPSd', 'GPSd (Legacy)', 'NMEA (Server)']
    BAUDS = [50, 75, 110, 134, 150, 200, 300, 600, 1200, 1800, 2400, 4800,
             9600, 19200, 38400, 57600, 115200]
    BYTES = [serial.FIVEBITS, serial.SIXBITS, serial.SEVENBITS,
             serial.EIGHTBITS]
    PARITIES = [serial.PARITY_NONE, serial.PARITY_EVEN, serial.PARITY_ODD,
                serial.PARITY_MARK, serial.PARITY_SPACE]
    STOPS = [serial.STOPBITS_ONE, serial.STOPBITS_ONE_POINT_FIVE,
             serial.STOPBITS_TWO]

    def __init__(self):
        self.name = 'GPS'
        self.type = DeviceGPS.GPSD
        self.resource = 'localhost:2947'
        self.baud = 115200
        self.bytes = serial.EIGHTBITS
        self.parity = serial.PARITY_NONE
        self.stops = serial.STOPBITS_ONE
        self.soft = False

    def get_serial_desc(self):
        port = self.resource.split('/')
        return '{0} {1}-{2}{3}{4}'.format(port[0], self.baud, self.bytes,
                                           self.parity, self.stops)


class DeviceRTL():
    def __init__(self):
        self.isDevice = True
        self.indexRtl = None
        self.name = None
        self.serial = ''
        self.server = 'localhost'
        self.port = 1234
        self.gains = []
        self.gain = 0
        self.calibration = 0
        self.lo = 0
        self.offset = 250e3
        self.tuner = 0

    def set(self, device):
        self.gain = device.gain
        self.calibration = device.calibration
        self.lo = device.lo
        self.offset = device.offset
        self.tuner = device.tuner

    def get_gains_str(self):
        gainsStr = []
        for gain in self.gains:
            gainsStr.append(str(gain))

        return gainsStr

    def get_closest_gain_str(self, desired):
        gain = min(self.gains, key=lambda n: abs(n - desired))

        return str(gain)


def get_devices_rtl(currentDevices=[], statusBar=None):
    if statusBar is not None:
        statusBar.set_general("Refreshing device list...")

    devices = []
    count = rtlsdr.librtlsdr.rtlsdr_get_device_count()

    for dev in range(0, count):
        device = DeviceRTL()
        device.indexRtl = dev
        device.name = format_device_rtl_name(rtlsdr.librtlsdr.rtlsdr_get_device_name(dev))
        buffer1 = (c_ubyte * 256)()
        buffer2 = (c_ubyte * 256)()
        serial = (c_ubyte * 256)()
        rtlsdr.librtlsdr.rtlsdr_get_device_usb_strings(dev, buffer1, buffer2,
                                                       serial)
        device.serial = string_at(serial)
        try:
            sdr = rtlsdr.RtlSdr(dev)
        except IOError:
            continue
        device.gains = sdr.valid_gains_db
        device.calibration = 0.0
        device.lo = 0.0
        for conf in currentDevices:
            if conf.isDevice and device.name == conf.name and device.serial == conf.serial:
                device.set(conf)

        devices.append(device)

    for conf in currentDevices:
        if not conf.isDevice:
            devices.append(conf)

    if statusBar is not None:
        statusBar.set_general("")

    return devices


def format_device_rtl_name(name):
    remove = ["/", "\\"]
    for char in remove:
        name = name.replace(char, " ")

    return name


if __name__ == '__main__':
    print 'Please run rtlsdr_scan.py'
    exit(1)

########NEW FILE########
__FILENAME__ = dialogs
#
# rtlsdr_scan
#
# http://eartoearoak.com/software/rtlsdr-scanner
#
# Copyright 2012 - 2014 Al Brown
#
# A frequency scanning GUI for the OsmoSDR rtl-sdr library at
# http://sdr.osmocom.org/trac/wiki/rtl-sdr
#
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import Queue
import copy
import itertools
from urlparse import urlparse

from PIL import Image
from matplotlib import mlab, patheffects
import matplotlib
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.ticker import ScalarFormatter
import numpy
import rtlsdr
import serial.tools.list_ports
from wx import grid
import wx
from wx.lib import masked
from wx.lib.agw.cubecolourdialog import CubeColourDialog
from wx.lib.masked.numctrl import NumCtrl

from constants import F_MIN, F_MAX, Cal, SAMPLE_RATE, BANDWIDTH, WINFUNC, \
    TUNER
from devices import DeviceRTL, DeviceGPS
from events import Event
from file import open_plot, File
from location import ThreadLocation
from misc import close_modeless, format_time, ValidatorCoord, get_colours, \
    nearest, load_bitmap, get_version_timestamp, get_serial_ports
from rtltcp import RtlTcp
from windows import PanelGraphCompare, PanelColourBar, CellRenderer, PanelLine


class DialogCompare(wx.Dialog):
    def __init__(self, parent, settings, filename):

        self.settings = settings
        self.dirname = settings.dirScans
        self.filename = filename

        wx.Dialog.__init__(self, parent=parent, title="Compare plots",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER | wx.MAXIMIZE_BOX)

        self.graph = PanelGraphCompare(self, self.__on_cursor)
        self.graph.show_plot1(settings.compareOne)
        self.graph.show_plot2(settings.compareTwo)
        self.graph.show_plotdiff(settings.compareDiff)

        textPlot1 = wx.StaticText(self, label='Plot 1')
        linePlot1 = PanelLine(self, wx.BLUE)
        self.checkOne = wx.CheckBox(self, wx.ID_ANY)
        self.checkOne.SetValue(settings.compareOne)
        self.buttonPlot1 = wx.Button(self, wx.ID_ANY, 'Load...')
        self.textPlot1 = wx.StaticText(self, label="<None>")
        self.textLoc1 = wx.StaticText(self, label='\n')
        self.Bind(wx.EVT_BUTTON, self.__on_load_plot, self.buttonPlot1)

        textPlot2 = wx.StaticText(self, label='Plot 2')
        linePlot2 = PanelLine(self, wx.GREEN)
        self.checkTwo = wx.CheckBox(self, wx.ID_ANY)
        self.checkTwo.SetValue(settings.compareTwo)
        self.buttonPlot2 = wx.Button(self, wx.ID_ANY, 'Load...')
        self.textPlot2 = wx.StaticText(self, label="<None>")
        self.textLoc2 = wx.StaticText(self, label='\n')
        self.Bind(wx.EVT_BUTTON, self.__on_load_plot, self.buttonPlot2)

        textPlotDiff = wx.StaticText(self, label='Difference')
        linePlotDiff = PanelLine(self, wx.RED)
        self.checkDiff = wx.CheckBox(self, wx.ID_ANY)
        self.checkDiff.SetValue(settings.compareDiff)
        self.textLocDiff = wx.StaticText(self, label='\n')

        font = textPlot1.GetFont()
        fontSize = font.GetPointSize()
        font.SetPointSize(fontSize + 4)
        textPlot1.SetFont(font)
        textPlot2.SetFont(font)
        textPlotDiff.SetFont(font)

        fontStyle = font.GetStyle()
        fontWeight = font.GetWeight()
        font = wx.Font(fontSize, wx.FONTFAMILY_MODERN, fontStyle,
                       fontWeight)
        self.textLoc1.SetFont(font)
        self.textLoc2.SetFont(font)
        self.textLocDiff.SetFont(font)

        buttonClose = wx.Button(self, wx.ID_CLOSE, 'Close')

        self.Bind(wx.EVT_CHECKBOX, self.__on_check1, self.checkOne)
        self.Bind(wx.EVT_CHECKBOX, self.__on_check2, self.checkTwo)
        self.Bind(wx.EVT_CHECKBOX, self.__on_check_diff, self.checkDiff)
        self.Bind(wx.EVT_BUTTON, self.__on_close, buttonClose)

        grid = wx.GridBagSizer(5, 5)

        grid.Add(textPlot1, pos=(0, 0))
        grid.Add(linePlot1, pos=(0, 1), flag=wx.EXPAND)
        grid.Add(self.checkOne, pos=(0, 2), flag=wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.buttonPlot1, pos=(1, 0))
        grid.Add(self.textPlot1, pos=(2, 0))
        grid.Add(self.textLoc1, pos=(3, 0))

        grid.Add(wx.StaticLine(self), pos=(5, 0), span=(1, 3), flag=wx.EXPAND)
        grid.Add(textPlot2, pos=(6, 0))
        grid.Add(linePlot2, pos=(6, 1), flag=wx.EXPAND)
        grid.Add(self.checkTwo, pos=(6, 2), flag=wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.buttonPlot2, pos=(7, 0))
        grid.Add(self.textPlot2, pos=(8, 0))
        grid.Add(self.textLoc2, pos=(9, 0))

        grid.Add(wx.StaticLine(self), pos=(11, 0), span=(1, 3), flag=wx.EXPAND)
        grid.Add(textPlotDiff, pos=(12, 0))
        grid.Add(linePlotDiff, pos=(12, 1), flag=wx.EXPAND)
        grid.Add(self.checkDiff, pos=(12, 2), flag=wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.textLocDiff, pos=(13, 0))

        sizerV = wx.BoxSizer(wx.HORIZONTAL)
        sizerV.Add(self.graph, 1, wx.EXPAND)
        sizerV.Add(grid, 0, wx.ALL, border=5)

        sizerH = wx.BoxSizer(wx.VERTICAL)
        sizerH.Add(sizerV, 1, wx.EXPAND, border=5)
        sizerH.Add(buttonClose, 0, wx.ALL | wx.ALIGN_RIGHT, border=5)

        self.SetSizerAndFit(sizerH)

        close_modeless()

    def __on_cursor(self, locs):
        self.textLoc1.SetLabel(self.__format_loc(locs['x1'], locs['y1']))
        self.textLoc2.SetLabel(self.__format_loc(locs['x2'], locs['y2']))
        self.textLocDiff.SetLabel(self.__format_loc(locs['x3'], locs['y3']))

    def __on_load_plot(self, event):
        dlg = wx.FileDialog(self, "Open a scan", self.dirname, self.filename,
                            File.get_type_filters(File.Types.SAVE),
                             wx.OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            self.dirname = dlg.GetDirectory()
            self.filename = dlg.GetFilename()
            _scanInfo, spectrum, _location = open_plot(self.dirname,
                                                       self.filename)
            if event.EventObject == self.buttonPlot1:
                self.textPlot1.SetLabel(self.filename)
                self.graph.set_spectrum1(spectrum)
            else:
                self.textPlot2.SetLabel(self.filename)
                self.graph.set_spectrum2(spectrum)

        dlg.Destroy()

    def __on_check1(self, _event):
        checked = self.checkOne.GetValue()
        self.settings.compareOne = checked
        self.graph.show_plot1(checked)

    def __on_check2(self, _event):
        checked = self.checkTwo.GetValue()
        self.settings.compareTwo = checked
        self.graph.show_plot2(checked)

    def __on_check_diff(self, _event):
        checked = self.checkDiff.GetValue()
        self.settings.compareDiff = checked
        self.graph.show_plotdiff(checked)

    def __on_close(self, _event):
        close_modeless()
        self.Destroy()

    def __format_loc(self, x, y):
        if None in [x, y]:
            return ""

        return '{0:.6f} MHz\n{1: .2f}    dB/Hz'.format(x, y)


class DialogAutoCal(wx.Dialog):
    def __init__(self, parent, freq, callbackCal):
        self.callback = callbackCal
        self.cal = 0

        wx.Dialog.__init__(self, parent=parent, title="Auto Calibration",
                           style=wx.CAPTION)
        self.Bind(wx.EVT_CLOSE, self.__on_close)

        title = wx.StaticText(self, label="Calibrate to a known stable signal")
        font = title.GetFont()
        font.SetPointSize(font.GetPointSize() + 2)
        title.SetFont(font)
        text = wx.StaticText(self, label="Frequency (MHz)")
        self.textFreq = masked.NumCtrl(self, value=freq, fractionWidth=3,
                                        min=F_MIN, max=F_MAX)

        self.buttonCal = wx.Button(self, label="Calibrate")
        if len(parent.devicesRtl) == 0:
            self.buttonCal.Disable()
        self.buttonCal.Bind(wx.EVT_BUTTON, self.__on_cal)
        self.textResult = wx.StaticText(self)

        self.buttonOk = wx.Button(self, wx.ID_OK, 'OK')
        self.buttonOk.Disable()
        self.buttonCancel = wx.Button(self, wx.ID_CANCEL, 'Cancel')

        self.buttonOk.Bind(wx.EVT_BUTTON, self.__on_close)
        self.buttonCancel.Bind(wx.EVT_BUTTON, self.__on_close)

        buttons = wx.StdDialogButtonSizer()
        buttons.AddButton(self.buttonOk)
        buttons.AddButton(self.buttonCancel)
        buttons.Realize()

        sizer = wx.GridBagSizer(10, 10)
        sizer.Add(title, pos=(0, 0), span=(1, 2),
                  flag=wx.ALIGN_CENTRE | wx.ALL, border=10)
        sizer.Add(text, pos=(1, 0), flag=wx.ALL | wx.EXPAND, border=10)
        sizer.Add(self.textFreq, pos=(1, 1), flag=wx.ALL | wx.EXPAND,
                  border=5)
        sizer.Add(self.buttonCal, pos=(2, 0), span=(1, 2),
                  flag=wx.ALIGN_CENTRE | wx.ALL | wx.EXPAND, border=10)
        sizer.Add(self.textResult, pos=(3, 0), span=(1, 2),
                  flag=wx.ALL | wx.EXPAND, border=10)
        sizer.Add(buttons, pos=(4, 0), span=(1, 2),
                  flag=wx.ALL | wx.EXPAND, border=10)

        self.SetSizerAndFit(sizer)

    def __on_cal(self, _event):
        self.buttonCal.Disable()
        self.buttonOk.Disable()
        self.buttonCancel.Disable()
        self.textFreq.Disable()
        self.textResult.SetLabel("Calibrating...")
        self.callback(Cal.START)

    def __on_close(self, event):
        status = [Cal.CANCEL, Cal.OK][event.GetId() == wx.ID_OK]
        self.callback(status)
        self.EndModal(event.GetId())
        return

    def __enable_controls(self):
        self.buttonCal.Enable(True)
        self.buttonOk.Enable(True)
        self.buttonCancel.Enable(True)
        self.textFreq.Enable()

    def set_cal(self, cal):
        self.cal = cal
        self.__enable_controls()
        self.textResult.SetLabel("Correction (ppm): {0:.3f}".format(cal))

    def get_cal(self):
        return self.cal

    def reset_cal(self):
        self.set_cal(self.cal)

    def get_arg1(self):
        return self.textFreq.GetValue()


class DialogGeo(wx.Dialog):

    def __init__(self, parent, spectrum, location, settings):
        self.spectrum = spectrum
        self.location = location
        self.directory = settings.dirExport
        self.colourMap = settings.colourMap
        self.dpi = settings.exportDpi
        self.canvas = None
        self.extent = None
        self.xyz = None
        self.plotAxes = False
        self.plotHeat = True
        self.plotCont = True
        self.plotPoint = False
        self.plot = None
        self.colourMap = settings.colourMap

        wx.Dialog.__init__(self, parent=parent, title='Export Map')

        self.figure = matplotlib.figure.Figure(facecolor='white')
        self.figure.set_size_inches((6, 6))
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.axes = self.figure.add_subplot(111)

        self.checkAxes = wx.CheckBox(self, label='Axes')
        self.checkAxes.SetValue(self.plotAxes)
        self.Bind(wx.EVT_CHECKBOX, self.__on_axes, self.checkAxes)
        self.checkHeat = wx.CheckBox(self, label='Heat Map')
        self.checkHeat.SetValue(self.plotHeat)
        self.Bind(wx.EVT_CHECKBOX, self.__on_heat, self.checkHeat)
        self.checkCont = wx.CheckBox(self, label='Contour Lines')
        self.checkCont.SetValue(self.plotCont)
        self.Bind(wx.EVT_CHECKBOX, self.__on_cont, self.checkCont)
        self.checkPoint = wx.CheckBox(self, label='Locations')
        self.checkPoint.SetValue(self.plotPoint)
        self.Bind(wx.EVT_CHECKBOX, self.__on_point, self.checkPoint)

        colours = get_colours()
        self.choiceColour = wx.Choice(self, choices=colours)
        self.choiceColour.SetSelection(colours.index(self.colourMap))
        self.Bind(wx.EVT_CHOICE, self.__on_colour, self.choiceColour)
        self.colourBar = PanelColourBar(self, settings.colourMap)

        freqMin = min(spectrum[min(spectrum)]) * 1000
        freqMax = max(spectrum[min(spectrum)]) * 1000
        bw = freqMax - freqMin

        textCentre = wx.StaticText(self, label='Centre')
        self.spinCentre = wx.SpinCtrl(self)
        self.spinCentre.SetToolTip(wx.ToolTip('Centre frequency (kHz)'))
        self.spinCentre.SetRange(freqMin, freqMax)
        self.spinCentre.SetValue(freqMin + bw / 2)

        textBw = wx.StaticText(self, label='Bandwidth')
        self.spinBw = wx.SpinCtrl(self)
        self.spinBw.SetToolTip(wx.ToolTip('Bandwidth (kHz)'))
        self.spinBw.SetRange(1, bw)
        self.spinBw.SetValue(bw / 10)

        buttonUpdate = wx.Button(self, label='Update')
        self.Bind(wx.EVT_BUTTON, self.__on_update, buttonUpdate)

        sizerButtons = wx.StdDialogButtonSizer()
        buttonOk = wx.Button(self, wx.ID_OK)
        buttonCancel = wx.Button(self, wx.ID_CANCEL)
        sizerButtons.AddButton(buttonOk)
        sizerButtons.AddButton(buttonCancel)
        sizerButtons.Realize()
        self.Bind(wx.EVT_BUTTON, self.__on_ok, buttonOk)

        self.__setup_plot()

        sizerGrid = wx.GridBagSizer(5, 5)
        sizerGrid.Add(self.canvas, pos=(0, 0), span=(1, 5),
                  flag=wx.EXPAND | wx.ALL, border=5)
        sizerGrid.Add(self.choiceColour, pos=(1, 0), span=(1, 2),
                  flag=wx.ALIGN_LEFT | wx.ALL, border=5)
        sizerGrid.Add(self.colourBar, pos=(1, 2), span=(1, 1),
                  flag=wx.ALIGN_LEFT | wx.ALL, border=5)
        sizerGrid.Add(self.checkAxes, pos=(2, 0), span=(1, 1),
                  flag=wx.ALIGN_LEFT | wx.ALL, border=5)
        sizerGrid.Add(self.checkHeat, pos=(2, 1), span=(1, 1),
                  flag=wx.ALIGN_LEFT | wx.ALL, border=5)
        sizerGrid.Add(self.checkCont, pos=(2, 2), span=(1, 1),
                  flag=wx.ALIGN_LEFT | wx.ALL, border=5)
        sizerGrid.Add(self.checkPoint, pos=(2, 3), span=(1, 1),
                  flag=wx.ALIGN_LEFT | wx.ALL, border=5)
        sizerGrid.Add(textCentre, pos=(3, 0), span=(1, 1),
                  flag=wx.ALIGN_RIGHT | wx.ALL, border=5)
        sizerGrid.Add(self.spinCentre, pos=(3, 1), span=(1, 1),
                  flag=wx.ALIGN_LEFT | wx.ALL, border=5)
        sizerGrid.Add(textBw, pos=(3, 2), span=(1, 1),
                  flag=wx.ALIGN_RIGHT | wx.ALL, border=5)
        sizerGrid.Add(self.spinBw, pos=(3, 3), span=(1, 1),
                  flag=wx.ALIGN_LEFT | wx.ALL, border=5)
        sizerGrid.Add(buttonUpdate, pos=(3, 4), span=(1, 1),
                  flag=wx.ALIGN_LEFT | wx.ALL, border=5)
        sizerGrid.Add(sizerButtons, pos=(4, 4), span=(1, 1),
                  flag=wx.ALIGN_RIGHT | wx.ALL, border=5)

        self.SetSizerAndFit(sizerGrid)

        self.__draw_plot()

    def __setup_plot(self):
        self.axes.clear()

        if self.plotHeat:
            self.choiceColour.Show()
            self.colourBar.Show()
        else:
            self.choiceColour.Hide()
            self.colourBar.Hide()

        self.axes.set_title('Preview')
        self.axes.set_xlabel('Longitude ($^\circ$)')
        self.axes.set_ylabel('Latitude ($^\circ$)')
        self.axes.set_xlim(auto=True)
        self.axes.set_ylim(auto=True)
        formatter = ScalarFormatter(useOffset=False)
        self.axes.xaxis.set_major_formatter(formatter)
        self.axes.yaxis.set_major_formatter(formatter)

    def __draw_plot(self):
        self.plot = None
        x = []
        y = []
        z = []

        freqCentre = self.spinCentre.GetValue()
        freqBw = self.spinBw.GetValue()
        freqMin = (freqCentre - freqBw) / 1000.
        freqMax = (freqCentre + freqBw) / 1000.

        for timeStamp in self.spectrum:
            spectrum = self.spectrum[timeStamp]
            sweep = [yv for xv, yv in spectrum.items() if freqMin <= xv <= freqMax]
            peak = max(sweep)
            try:
                location = self.location[timeStamp]
            except KeyError:
                continue
            x.append(location[1])
            y.append(location[0])
            z.append(peak)

        if len(x) == 0:
            self.__draw_warning()
            return

        xi = numpy.linspace(min(x), max(x), 500)
        yi = numpy.linspace(min(y), max(y), 500)

        try:
            zi = mlab.griddata(x, y, z, xi, yi)
        except:
            self.__draw_warning()
            return

        self.extent = (min(x), max(x), min(y), max(y))
        self.xyz = (x, y, z)

        if self.plotHeat:
            self.plot = self.axes.pcolormesh(xi, yi, zi, cmap=self.colourMap)

        if self.plotCont:
            contours = self.axes.contour(xi, yi, zi, linewidths=0.5,
                                         colors='k')
            self.axes.clabel(contours, inline=1, fontsize='x-small',
                             gid='clabel')

        if self.plotPoint:
            self.axes.plot(x, y, 'wo')
            for posX, posY, posZ in zip(x, y, z):
                self.axes.annotate('{0:.2f}dB'.format(posZ), xy=(posX, posY),
                                   xytext=(-5, 5), ha='right',
                                   textcoords='offset points')

        if matplotlib.__version__ >= '1.3':
            effect = patheffects.withStroke(linewidth=2, foreground="w",
                                            alpha=0.75)
            for child in self.axes.get_children():
                child.set_path_effects([effect])

        if self.plotAxes:
            self.axes.set_axis_on()
        else:
            self.axes.set_axis_off()
        self.canvas.draw()

    def __draw_warning(self):
        self.axes.text(0.5, 0.5, 'Insufficient GPS data',
                       ha='center', va='center',
                       transform=self.axes.transAxes)

    def __on_update(self, _event):
        self.__setup_plot()
        self.__draw_plot()

    def __on_ok(self, _event):
        self.EndModal(wx.ID_OK)

    def __on_axes(self, _event):
        self.plotAxes = self.checkAxes.GetValue()
        if self.plotAxes:
            self.axes.set_axis_on()
        else:
            self.axes.set_axis_off()
        self.canvas.draw()

    def __on_heat(self, _event):
        self.plotHeat = self.checkHeat.GetValue()
        self.__on_update(None)

    def __on_cont(self, _event):
        self.plotCont = self.checkCont.GetValue()
        self.__on_update(None)

    def __on_point(self, _event):
        self.plotPoint = self.checkPoint.GetValue()
        self.__on_update(None)

    def __on_colour(self, _event):
        self.colourMap = self.choiceColour.GetStringSelection()
        self.colourBar.set_map(self.colourMap)
        if self.plot:
            self.plot.set_cmap(self.colourMap)
            self.canvas.draw()

    def get_filename(self):
        return self.filename

    def get_directory(self):
        return self.directory

    def get_extent(self):
        return self.extent

    def get_image(self):
        width = self.extent[1] - self.extent[0]
        height = self.extent[3] - self.extent[2]
        self.figure.set_size_inches((6, 6. * width / height))
        self.figure.set_dpi(self.dpi)
        self.axes.set_title('')
        self.figure.patch.set_alpha(0)
        self.axes.axesPatch.set_alpha(0)
        canvas = FigureCanvasAgg(self.figure)
        canvas.draw()

        renderer = canvas.get_renderer()
        if matplotlib.__version__ >= '1.2':
            buf = renderer.buffer_rgba()
        else:
            buf = renderer.buffer_rgba(0, 0)
        size = canvas.get_width_height()
        image = Image.frombuffer('RGBA', size, buf, 'raw', 'RGBA', 0, 1)

        return image

    def get_xyz(self):
        return self.xyz


class DialogOffset(wx.Dialog):
    def __init__(self, parent, device, offset, winFunc):
        self.device = device
        self.offset = offset * 1e3
        self.winFunc = winFunc
        self.band1 = None
        self.band2 = None

        wx.Dialog.__init__(self, parent=parent, title="Scan Offset")

        figure = matplotlib.figure.Figure(facecolor='white')
        self.axes = figure.add_subplot(111)
        self.canvas = FigureCanvas(self, -1, figure)

        textHelp = wx.StaticText(self,
            label="Remove the aerial and press refresh, "
            "adjust the offset so the shaded areas overlay the flattest parts "
            "of the plot.")

        textFreq = wx.StaticText(self, label="Test frequency (MHz)")
        self.spinFreq = wx.SpinCtrl(self)
        self.spinFreq.SetRange(F_MIN, F_MAX)
        self.spinFreq.SetValue(200)

        textGain = wx.StaticText(self, label="Test gain (dB)")
        self.spinGain = wx.SpinCtrl(self)
        self.spinGain.SetRange(-100, 200)
        self.spinGain.SetValue(200)

        refresh = wx.Button(self, wx.ID_ANY, 'Refresh')
        self.Bind(wx.EVT_BUTTON, self.__on_refresh, refresh)

        textOffset = wx.StaticText(self, label="Offset (kHz)")
        self.spinOffset = wx.SpinCtrl(self)
        self.spinOffset.SetRange(0, ((SAMPLE_RATE / 2) - BANDWIDTH) / 1e3)
        self.spinOffset.SetValue(offset)
        self.Bind(wx.EVT_SPINCTRL, self.__on_spin, self.spinOffset)

        sizerButtons = wx.StdDialogButtonSizer()
        buttonOk = wx.Button(self, wx.ID_OK)
        buttonCancel = wx.Button(self, wx.ID_CANCEL)
        sizerButtons.AddButton(buttonOk)
        sizerButtons.AddButton(buttonCancel)
        sizerButtons.Realize()
        self.Bind(wx.EVT_BUTTON, self.__on_ok, buttonOk)

        boxSizer1 = wx.BoxSizer(wx.HORIZONTAL)
        boxSizer1.Add(textFreq, border=5)
        boxSizer1.Add(self.spinFreq, border=5)
        boxSizer1.Add(textGain, border=5)
        boxSizer1.Add(self.spinGain, border=5)

        boxSizer2 = wx.BoxSizer(wx.HORIZONTAL)
        boxSizer2.Add(textOffset, border=5)
        boxSizer2.Add(self.spinOffset, border=5)

        gridSizer = wx.GridBagSizer(5, 5)
        gridSizer.Add(self.canvas, pos=(0, 0), span=(1, 2),
                  flag=wx.ALIGN_CENTRE | wx.ALL, border=5)
        gridSizer.Add(textHelp, pos=(1, 0), span=(1, 2),
                  flag=wx.ALIGN_CENTRE | wx.ALL, border=5)
        gridSizer.Add(boxSizer1, pos=(2, 0), span=(1, 2),
                  flag=wx.ALIGN_CENTRE | wx.ALL, border=5)
        gridSizer.Add(refresh, pos=(3, 0), span=(1, 2),
                  flag=wx.ALIGN_CENTRE | wx.ALL, border=5)
        gridSizer.Add(boxSizer2, pos=(4, 0), span=(1, 2),
                  flag=wx.ALIGN_CENTRE | wx.ALL, border=5)
        gridSizer.Add(sizerButtons, pos=(5, 1), span=(1, 1),
                  flag=wx.ALIGN_RIGHT | wx.ALL, border=5)

        self.SetSizerAndFit(gridSizer)
        self.__draw_limits()

        self.__setup_plot()

    def __setup_plot(self):
        self.axes.clear()
        self.band1 = None
        self.band2 = None
        self.axes.set_xlabel("Frequency (MHz)")
        self.axes.set_ylabel('Level ($\mathsf{dB/\sqrt{Hz}}$)')
        self.axes.set_yscale('log')
        self.axes.set_xlim(-1, 1)
        self.axes.set_ylim(auto=True)
        self.axes.grid(True)
        self.__draw_limits()

    def __plot(self, capture):
        self.__setup_plot()
        pos = WINFUNC[::2].index(self.winFunc)
        function = WINFUNC[1::2][pos]
        powers, freqs = matplotlib.mlab.psd(capture,
                         NFFT=1024,
                         Fs=SAMPLE_RATE / 1e6,
                         window=function(1024))

        plot = []
        for x, y in itertools.izip(freqs, powers):
            plot.append((x, y))
        plot.sort()
        x, y = numpy.transpose(plot)
        self.axes.plot(x, y, linewidth=0.4)
        self.canvas.draw()

    def __on_ok(self, _event):
        self.EndModal(wx.ID_OK)

    def __on_refresh(self, _event):
        dlg = wx.BusyInfo('Please wait...')

        try:
            if self.device.isDevice:
                sdr = rtlsdr.RtlSdr(self.device.indexRtl)
            else:
                sdr = RtlTcp(self.device.server, self.device.port)
            sdr.set_sample_rate(SAMPLE_RATE)
            sdr.set_center_freq(self.spinFreq.GetValue() * 1e6)
            sdr.set_gain(self.spinGain.GetValue())
            capture = sdr.read_samples(2 ** 21)
            sdr.close()
        except IOError as error:
            if self.device.isDevice:
                message = error.message
            else:
                message = error
            dlg.Destroy()
            dlg = wx.MessageDialog(self,
                                   'Capture failed:\n{0}'.format(message),
                                   'Error',
                                   wx.OK | wx.ICON_ERROR)
            dlg.ShowModal()
            dlg.Destroy()
            return

        self.__plot(capture)

        dlg.Destroy()

    def __on_spin(self, _event):
        self.offset = self.spinOffset.GetValue() * 1e3
        self.__draw_limits()

    def __draw_limits(self):
        limit1 = self.offset
        limit2 = limit1 + BANDWIDTH / 2
        limit1 /= 1e6
        limit2 /= 1e6
        if self.band1 is not None:
            self.band1.remove()
        if self.band2 is not None:
            self.band2.remove()
        self.band1 = self.axes.axvspan(limit1, limit2, color='g', alpha=0.25)
        self.band2 = self.axes.axvspan(-limit1, -limit2, color='g', alpha=0.25)
        self.canvas.draw()

    def get_offset(self):
        return self.offset / 1e3


class DialogProperties(wx.Dialog):
    def __init__(self, parent, scanInfo):
        wx.Dialog.__init__(self, parent, title="Scan Properties")

        self.scanInfo = scanInfo

        box = wx.BoxSizer(wx.VERTICAL)

        grid = wx.GridBagSizer(0, 0)

        boxScan = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Scan"),
                                     wx.HORIZONTAL)

        gridScan = wx.GridBagSizer(0, 0)

        textDesc = wx.StaticText(self, label="Description")
        gridScan.Add(textDesc, (0, 0), (1, 1), wx.ALL, 5)
        self.textCtrlDesc = wx.TextCtrl(self, value=scanInfo.desc,
                                        style=wx.TE_MULTILINE)
        gridScan.Add(self.textCtrlDesc, (0, 1), (2, 2), wx.ALL | wx.EXPAND, 5)

        textStart = wx.StaticText(self, label="Start")
        gridScan.Add(textStart, (2, 0), (1, 1), wx.ALL, 5)
        textCtrlStart = wx.TextCtrl(self, value="Unknown",
                                    style=wx.TE_READONLY)
        if scanInfo.start is not None:
            textCtrlStart.SetValue(str(scanInfo.start))
        gridScan.Add(textCtrlStart, (2, 1), (1, 1), wx.ALL, 5)
        textMHz1 = wx.StaticText(self, wx.ID_ANY, label="MHz")
        gridScan.Add(textMHz1, (2, 2), (1, 1), wx.ALL, 5)

        textStop = wx.StaticText(self, label="Stop")
        gridScan.Add(textStop, (3, 0), (1, 1), wx.ALL, 5)
        textCtrlStop = wx.TextCtrl(self, value="Unknown",
                                   style=wx.TE_READONLY)
        if scanInfo.stop is not None:
            textCtrlStop.SetValue(str(scanInfo.stop))
        gridScan.Add(textCtrlStop, (3, 1), (1, 1), wx.ALL, 5)
        textMHz2 = wx.StaticText(self, label="MHz")
        gridScan.Add(textMHz2, (3, 2), (1, 1), wx.ALL, 5)

        textDwell = wx.StaticText(self, label="Dwell")
        gridScan.Add(textDwell, (4, 0), (1, 1), wx.ALL, 5)
        textCtrlDwell = wx.TextCtrl(self, value="Unknown",
                                    style=wx.TE_READONLY)
        if scanInfo.dwell is not None:
            textCtrlDwell.SetValue(str(scanInfo.dwell))
        gridScan.Add(textCtrlDwell, (4, 1), (1, 1), wx.ALL, 5)
        textSeconds = wx.StaticText(self, label="seconds")
        gridScan.Add(textSeconds, (4, 2), (1, 1), wx.ALL, 5)

        textNfft = wx.StaticText(self, label="FFT Size")
        gridScan.Add(textNfft, (5, 0), (1, 1), wx.ALL, 5)
        textCtrlNfft = wx.TextCtrl(self, value="Unknown", style=wx.TE_READONLY)
        if scanInfo.nfft is not None:
            textCtrlNfft.SetValue(str(scanInfo.nfft))
        gridScan.Add(textCtrlNfft, (5, 1), (1, 1), wx.ALL, 5)

        textRbw = wx.StaticText(self, label="RBW")
        gridScan.Add(textRbw, (6, 0), (1, 1), wx.ALL, 5)
        rbw = ((SAMPLE_RATE / scanInfo.nfft) / 1000.0) * 2.0
        textCtrlStop = wx.TextCtrl(self, value="{0:.3f}".format(rbw),
                                   style=wx.TE_READONLY)
        gridScan.Add(textCtrlStop, (6, 1), (1, 1), wx.ALL, 5)
        textKHz = wx.StaticText(self, label="kHz")
        gridScan.Add(textKHz, (6, 2), (1, 1), wx.ALL, 5)

        textTime = wx.StaticText(self, label="First scan")
        gridScan.Add(textTime, (7, 0), (1, 1), wx.ALL, 5)
        textCtrlTime = wx.TextCtrl(self, value="Unknown", style=wx.TE_READONLY)
        if scanInfo.timeFirst is not None:
            textCtrlTime.SetValue(format_time(scanInfo.timeFirst, True))
        gridScan.Add(textCtrlTime, (7, 1), (1, 1), wx.ALL, 5)

        textTime = wx.StaticText(self, label="Last scan")
        gridScan.Add(textTime, (8, 0), (1, 1), wx.ALL, 5)
        textCtrlTime = wx.TextCtrl(self, value="Unknown", style=wx.TE_READONLY)
        if scanInfo.timeLast is not None:
            textCtrlTime.SetValue(format_time(scanInfo.timeLast, True))
        gridScan.Add(textCtrlTime, (8, 1), (1, 1), wx.ALL, 5)

        textLat = wx.StaticText(self, label="Latitude")
        gridScan.Add(textLat, (9, 0), (1, 1), wx.ALL, 5)
        self.textCtrlLat = wx.TextCtrl(self, value="Unknown")
        self.textCtrlLat.SetValidator(ValidatorCoord(True))
        if scanInfo.lat is not None:
            self.textCtrlLat.SetValue(str(scanInfo.lat))
        gridScan.Add(self.textCtrlLat, (9, 1), (1, 1), wx.ALL, 5)

        textLon = wx.StaticText(self, label="Longitude")
        gridScan.Add(textLon, (10, 0), (1, 1), wx.ALL, 5)
        self.textCtrlLon = wx.TextCtrl(self, value="Unknown")
        self.textCtrlLon.SetValidator(ValidatorCoord(False))
        if scanInfo.lon is not None:
            self.textCtrlLon.SetValue(str(scanInfo.lon))
        gridScan.Add(self.textCtrlLon, (10, 1), (1, 1), wx.ALL, 5)

        boxScan.Add(gridScan, 0, 0, 5)

        grid.Add(boxScan, (0, 0), (1, 1), wx.ALL | wx.EXPAND, 5)

        boxDevice = wx.StaticBoxSizer(wx.StaticBox(self, label="Device"),
                                      wx.VERTICAL)

        gridDevice = wx.GridBagSizer(0, 0)

        textName = wx.StaticText(self, label="Name")
        gridDevice.Add(textName, (0, 0), (1, 1), wx.ALL, 5)
        textCtrlName = wx.TextCtrl(self, value="Unknown", style=wx.TE_READONLY)
        if scanInfo.name is not None:
            textCtrlName.SetValue(scanInfo.name)
        gridDevice.Add(textCtrlName, (0, 1), (1, 2), wx.ALL | wx.EXPAND, 5)

        textTuner = wx.StaticText(self, label="Tuner")
        gridDevice.Add(textTuner, (1, 0), (1, 1), wx.ALL, 5)
        textCtrlTuner = wx.TextCtrl(self, value="Unknown",
                                    style=wx.TE_READONLY)
        if scanInfo.tuner != -1:
            textCtrlTuner.SetValue(TUNER[scanInfo.tuner])
        gridDevice.Add(textCtrlTuner, (1, 1), (1, 2), wx.ALL | wx.EXPAND, 5)

        testGain = wx.StaticText(self, label="Gain")
        gridDevice.Add(testGain, (2, 0), (1, 1), wx.ALL, 5)
        textCtrlGain = wx.TextCtrl(self, value="Unknown", style=wx.TE_READONLY)
        if scanInfo.gain is not None:
            textCtrlGain.SetValue(str(scanInfo.gain))
        gridDevice.Add(textCtrlGain, (2, 1), (1, 1), wx.ALL, 5)
        textDb = wx.StaticText(self, label="dB")
        gridDevice.Add(textDb, (2, 2), (1, 1), wx.ALL, 5)

        textLo = wx.StaticText(self, label="LO")
        gridDevice.Add(textLo, (3, 0), (1, 1), wx.ALL, 5)
        textCtrlLo = wx.TextCtrl(self, value="Unknown", style=wx.TE_READONLY)
        if scanInfo.lo is not None:
            textCtrlLo.SetValue(str(scanInfo.lo))
        gridDevice.Add(textCtrlLo, (3, 1), (1, 1), wx.ALL, 5)
        textMHz3 = wx.StaticText(self, label="MHz")
        gridDevice.Add(textMHz3, (3, 2), (1, 1), wx.ALL, 5)

        textCal = wx.StaticText(self, label="Calibration")
        gridDevice.Add(textCal, (4, 0), (1, 1), wx.ALL, 5)
        textCtrlCal = wx.TextCtrl(self, value="Unknown", style=wx.TE_READONLY)
        if scanInfo.calibration is not None:
            textCtrlCal.SetValue(str(scanInfo.calibration))
        gridDevice.Add(textCtrlCal, (4, 1), (1, 1), wx.ALL, 5)
        testPpm = wx.StaticText(self, label="ppm")
        gridDevice.Add(testPpm, (4, 2), (1, 1), wx.ALL, 5)

        boxDevice.Add(gridDevice, 1, wx.EXPAND, 5)

        grid.Add(boxDevice, (1, 0), (1, 1), wx.ALL | wx.EXPAND, 5)

        box.Add(grid, 1, wx.ALL | wx.EXPAND, 5)

        sizerButtons = wx.StdDialogButtonSizer()
        buttonOk = wx.Button(self, wx.ID_OK)
        buttonCancel = wx.Button(self, wx.ID_CANCEL)
        sizerButtons.AddButton(buttonOk)
        sizerButtons.AddButton(buttonCancel)
        sizerButtons.Realize()
        self.Bind(wx.EVT_BUTTON, self.__on_ok, buttonOk)
        box.Add(sizerButtons, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        self.SetSizerAndFit(box)

    def __on_ok(self, _event):
        self.scanInfo.desc = self.textCtrlDesc.GetValue()
        if self.Validate():
            lat = self.textCtrlLat.GetValue()
            if len(lat) == 0 or lat == "-" or lat.lower() == "unknown":
                self.scanInfo.lat = None
            else:
                self.scanInfo.lat = float(lat)

            lon = self.textCtrlLon.GetValue()
            if len(lon) == 0 or lon == "-" or lon.lower() == "unknown":
                self.scanInfo.lon = None
            else:
                self.scanInfo.lon = float(lon)

            self.EndModal(wx.ID_CLOSE)


class DialogPrefs(wx.Dialog):

    def __init__(self, parent, settings):
        self.settings = settings
        self.index = 0

        wx.Dialog.__init__(self, parent=parent, title="Preferences")

        self.colours = get_colours()
        self.winFunc = settings.winFunc
        self.background = settings.background

        self.checkSaved = wx.CheckBox(self, wx.ID_ANY,
                                      "Save warning")
        self.checkSaved.SetValue(settings.saveWarn)
        self.checkSaved.SetToolTip(wx.ToolTip('Prompt to save scan on exit'))
        self.checkAlert = wx.CheckBox(self, wx.ID_ANY,
                                      "Level alert (dB)")
        self.checkAlert.SetValue(settings.alert)
        self.checkAlert.SetToolTip(wx.ToolTip('Play alert when level exceeded'))
        self.Bind(wx.EVT_CHECKBOX, self.__on_alert, self.checkAlert)
        self.spinLevel = wx.SpinCtrl(self, wx.ID_ANY, min=-100, max=20)
        self.spinLevel.SetValue(settings.alertLevel)
        self.spinLevel.Enable(settings.alert)
        self.spinLevel.SetToolTip(wx.ToolTip('Alert threshold'))
        textBackground = wx.StaticText(self, label='Background colour')
        self.buttonBackground = wx.Button(self, wx.ID_ANY)
        self.buttonBackground.SetBackgroundColour(self.background)
        self.Bind(wx.EVT_BUTTON, self.__on_background, self.buttonBackground)
        textColour = wx.StaticText(self, label="Colour map")
        self.choiceColour = wx.Choice(self, choices=self.colours)
        self.choiceColour.SetSelection(self.colours.index(settings.colourMap))
        self.Bind(wx.EVT_CHOICE, self.__on_choice, self.choiceColour)
        self.colourBar = PanelColourBar(self, settings.colourMap)
        self.checkPoints = wx.CheckBox(self, wx.ID_ANY,
                                      "Limit points")
        self.checkPoints.SetValue(settings.pointsLimit)
        self.checkPoints.SetToolTip(wx.ToolTip('Limit the resolution of plots'))
        self.Bind(wx.EVT_CHECKBOX, self.__on_points, self.checkPoints)
        self.spinPoints = wx.SpinCtrl(self, wx.ID_ANY, min=1000, max=100000)
        self.spinPoints.Enable(settings.pointsLimit)
        self.spinPoints.SetValue(settings.pointsMax)
        self.spinPoints.SetToolTip(wx.ToolTip('Maximum number of points to plot'))
        textDpi = wx.StaticText(self, label='Export DPI')
        self.spinDpi = wx.SpinCtrl(self, wx.ID_ANY, min=72, max=6000)
        self.spinDpi.SetValue(settings.exportDpi)
        self.spinDpi.SetToolTip(wx.ToolTip('DPI of exported images'))
        self.checkGps = wx.CheckBox(self, wx.ID_ANY,
                                      "Use GPS")
        self.checkGps.SetValue(settings.gps)
        self.checkGps.SetToolTip(wx.ToolTip('Record GPS location'))

        self.radioAvg = wx.RadioButton(self, wx.ID_ANY, 'Average Scans',
                                       style=wx.RB_GROUP)
        self.radioAvg.SetToolTip(wx.ToolTip('Average level with each scan'))
        self.Bind(wx.EVT_RADIOBUTTON, self.__on_radio, self.radioAvg)
        self.radioRetain = wx.RadioButton(self, wx.ID_ANY,
                                          'Retain previous scans')
        self.radioRetain.SetToolTip(wx.ToolTip('Can be slow'))
        self.Bind(wx.EVT_RADIOBUTTON, self.__on_radio, self.radioRetain)
        self.radioRetain.SetValue(settings.retainScans)

        textMaxScans = wx.StaticText(self, label="Max scans")
        self.spinCtrlMaxScans = wx.SpinCtrl(self)
        self.spinCtrlMaxScans.SetRange(1, 500)
        self.spinCtrlMaxScans.SetValue(settings.retainMax)
        self.spinCtrlMaxScans.SetToolTip(wx.ToolTip('Maximum previous scans'
                                                    ' to display'))

        self.checkFade = wx.CheckBox(self, wx.ID_ANY,
                                      "Fade previous scans")
        self.checkFade.SetValue(settings.fadeScans)
        textWidth = wx.StaticText(self, label="Line width")
        self.ctrlWidth = NumCtrl(self, integerWidth=2, fractionWidth=1)
        self.ctrlWidth.SetValue(settings.lineWidth)

        self.__on_radio(None)

        sizerButtons = wx.StdDialogButtonSizer()
        buttonOk = wx.Button(self, wx.ID_OK)
        buttonCancel = wx.Button(self, wx.ID_CANCEL)
        sizerButtons.AddButton(buttonOk)
        sizerButtons.AddButton(buttonCancel)
        sizerButtons.Realize()
        self.Bind(wx.EVT_BUTTON, self.__on_ok, buttonOk)

        gengrid = wx.GridBagSizer(10, 10)
        gengrid.Add(self.checkSaved, pos=(0, 0))
        gengrid.Add(self.checkAlert, pos=(1, 0), flag=wx.ALIGN_CENTRE)
        gengrid.Add(self.spinLevel, pos=(1, 1))
        gengrid.Add(textBackground, pos=(2, 0), flag=wx.ALIGN_CENTRE)
        gengrid.Add(self.buttonBackground, pos=(2, 1))
        gengrid.Add(textColour, pos=(3, 0))
        gengrid.Add(self.choiceColour, pos=(3, 1))
        gengrid.Add(self.colourBar, pos=(3, 2))
        gengrid.Add(self.checkPoints, pos=(4, 0))
        gengrid.Add(self.spinPoints, pos=(4, 1))
        gengrid.Add(textDpi, pos=(5, 0))
        gengrid.Add(self.spinDpi, pos=(5, 1))
        gengrid.Add(self.checkGps, pos=(6, 0))
        genbox = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "General"))
        genbox.Add(gengrid, 0, wx.ALL | wx.ALIGN_CENTRE_VERTICAL, 10)

        congrid = wx.GridBagSizer(10, 10)
        congrid.Add(self.radioAvg, pos=(0, 0))
        congrid.Add(self.radioRetain, pos=(1, 0))
        congrid.Add(textMaxScans, pos=(2, 0),
                    flag=wx.ALIGN_CENTRE_VERTICAL)
        congrid.Add(self.spinCtrlMaxScans, pos=(2, 1))
        conbox = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY,
                                                "Continuous Scans"),
                                   wx.VERTICAL)
        conbox.Add(congrid, 0, wx.ALL | wx.EXPAND, 10)

        plotgrid = wx.GridBagSizer(10, 10)
        plotgrid.Add(self.checkFade, pos=(0, 0))
        plotgrid.Add(textWidth, pos=(1, 0))
        plotgrid.Add(self.ctrlWidth, pos=(1, 1))
        plotbox = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Plot View"),
                                     wx.HORIZONTAL)
        plotbox.Add(plotgrid, 0, wx.ALL | wx.EXPAND, 10)

        grid = wx.GridBagSizer(10, 10)
        grid.AddGrowableCol(0, 1)
        grid.AddGrowableCol(1, 0)
        grid.Add(genbox, pos=(0, 0), span=(1, 2), flag=wx.EXPAND)
        grid.Add(conbox, pos=(1, 0), span=(1, 2), flag=wx.EXPAND)
        grid.Add(plotbox, pos=(2, 0), span=(1, 2), flag=wx.EXPAND)
        grid.Add(sizerButtons, pos=(3, 1), flag=wx.EXPAND)

        box = wx.BoxSizer()
        box.Add(grid, flag=wx.ALL | wx.ALIGN_CENTRE, border=10)

        self.SetSizerAndFit(box)

    def __on_alert(self, _event):
        enabled = self.checkAlert.GetValue()
        self.spinLevel.Enable(enabled)

    def __on_points(self, _event):
        enabled = self.checkPoints.GetValue()
        self.spinPoints.Enable(enabled)

    def __on_background(self, _event):
        colour = wx.ColourData()
        colour.SetColour(self.background)

        dlg = CubeColourDialog(self, colour, 0)
        if dlg.ShowModal() == wx.ID_OK:
            newColour = dlg.GetColourData().GetColour()
            self.background = newColour.GetAsString(wx.C2S_HTML_SYNTAX)
            self.buttonBackground.SetBackgroundColour(self.background)
        dlg.Destroy()

    def __on_radio(self, _event):
        enabled = self.radioRetain.GetValue()
        self.checkFade.Enable(enabled)
        self.spinCtrlMaxScans.Enable(enabled)

    def __on_choice(self, _event):
        self.colourBar.set_map(self.choiceColour.GetStringSelection())
        self.choiceColour.SetFocus()

    def __on_ok(self, _event):
        self.settings.saveWarn = self.checkSaved.GetValue()
        self.settings.alert = self.checkAlert.GetValue()
        self.settings.alertLevel = self.spinLevel.GetValue()
        self.settings.gps = self.checkGps.GetValue()
        self.settings.pointsLimit = self.checkPoints.GetValue()
        self.settings.pointsMax = self.spinPoints.GetValue()
        self.settings.exportDpi = self.spinDpi.GetValue()
        self.settings.retainScans = self.radioRetain.GetValue()
        self.settings.fadeScans = self.checkFade.GetValue()
        self.settings.lineWidth = self.ctrlWidth.GetValue()
        self.settings.retainMax = self.spinCtrlMaxScans.GetValue()
        self.settings.colourMap = self.choiceColour.GetStringSelection()
        self.settings.background = self.background

        self.EndModal(wx.ID_OK)


class DialogAdvPrefs(wx.Dialog):
    def __init__(self, parent, settings):
        self.settings = settings

        wx.Dialog.__init__(self, parent=parent, title="Advanced Preferences")

        self.winFunc = settings.winFunc

        textOverlap = wx.StaticText(self, label='PSD Overlap (%)')
        self.slideOverlap = wx.Slider(self, wx.ID_ANY,
                                      settings.overlap * 100,
                                      0, 75,
                                      style=wx.SL_LABELS)
        self.slideOverlap.SetToolTip(wx.ToolTip('Power spectral density'
                                                    ' overlap'))
        textWindow = wx.StaticText(self, label='Window')
        self.buttonWindow = wx.Button(self, wx.ID_ANY, self.winFunc)
        self.Bind(wx.EVT_BUTTON, self.__on_window, self.buttonWindow)

        buttonOk = wx.Button(self, wx.ID_OK)
        buttonCancel = wx.Button(self, wx.ID_CANCEL)
        sizerButtons = wx.StdDialogButtonSizer()
        sizerButtons.AddButton(buttonOk)
        sizerButtons.AddButton(buttonCancel)
        sizerButtons.Realize()
        self.Bind(wx.EVT_BUTTON, self.__on_ok, buttonOk)

        advgrid = wx.GridBagSizer(10, 10)
        advgrid.Add(textOverlap, pos=(0, 0),
                    flag=wx.ALL | wx.ALIGN_CENTRE)
        advgrid.Add(self.slideOverlap, pos=(0, 1), flag=wx.EXPAND)
        advgrid.Add(textWindow, pos=(1, 0), flag=wx.EXPAND)
        advgrid.Add(self.buttonWindow, pos=(1, 1))
        advgrid.Add(sizerButtons, pos=(2, 1), flag=wx.EXPAND)

        advBox = wx.BoxSizer()
        advBox.Add(advgrid, flag=wx.ALL | wx.ALIGN_CENTRE, border=10)

        self.SetSizerAndFit(advBox)

    def __on_window(self, _event):
        dlg = DialogWinFunc(self, self.winFunc)
        if dlg.ShowModal() == wx.ID_OK:
            self.winFunc = dlg.get_win_func()
            self.buttonWindow.SetLabel(self.winFunc)
        dlg.Destroy()

    def __on_ok(self, _event):
        self.settings.overlap = self.slideOverlap.GetValue() / 100.0
        self.settings.winFunc = self.winFunc

        self.EndModal(wx.ID_OK)


class DialogDevicesRTL(wx.Dialog):
    COL_SEL, COL_DEV, COL_TUN, COL_SER, COL_IND, \
    COL_GAIN, COL_CAL, COL_LO, COL_OFF = range(9)

    def __init__(self, parent, devices, settings):
        self.devices = copy.copy(devices)
        self.settings = settings
        self.index = None

        wx.Dialog.__init__(self, parent=parent, title="Radio Devices")

        self.gridDev = grid.Grid(self)
        self.gridDev.CreateGrid(len(self.devices), 9)
        self.gridDev.SetRowLabelSize(0)
        self.gridDev.SetColLabelValue(self.COL_SEL, "Select")
        self.gridDev.SetColLabelValue(self.COL_DEV, "Device")
        self.gridDev.SetColLabelValue(self.COL_TUN, "Tuner")
        self.gridDev.SetColLabelValue(self.COL_SER, "Serial Number")
        self.gridDev.SetColLabelValue(self.COL_IND, "Index")
        self.gridDev.SetColLabelValue(self.COL_GAIN, "Gain\n(dB)")
        self.gridDev.SetColLabelValue(self.COL_CAL, "Calibration\n(ppm)")
        self.gridDev.SetColLabelValue(self.COL_LO, "LO\n(MHz)")
        self.gridDev.SetColLabelValue(self.COL_OFF, "Band Offset\n(kHz)")
        self.gridDev.SetColFormatFloat(self.COL_GAIN, -1, 1)
        self.gridDev.SetColFormatFloat(self.COL_CAL, -1, 3)
        self.gridDev.SetColFormatFloat(self.COL_LO, -1, 3)
        self.gridDev.SetColFormatFloat(self.COL_OFF, -1, 0)

        self.__set_dev_grid()
        self.Bind(grid.EVT_GRID_CELL_LEFT_CLICK, self.__on_click)

        serverSizer = wx.BoxSizer(wx.HORIZONTAL)
        buttonAdd = wx.Button(self, wx.ID_ADD)
        self.buttonDel = wx.Button(self, wx.ID_DELETE)
        self.Bind(wx.EVT_BUTTON, self.__on_add, buttonAdd)
        self.Bind(wx.EVT_BUTTON, self.__on_del, self.buttonDel)
        serverSizer.Add(buttonAdd, 0, wx.ALL)
        serverSizer.Add(self.buttonDel, 0, wx.ALL)
        self.__set_button_state()

        buttonOk = wx.Button(self, wx.ID_OK)
        buttonCancel = wx.Button(self, wx.ID_CANCEL)
        sizerButtons = wx.StdDialogButtonSizer()
        sizerButtons.AddButton(buttonOk)
        sizerButtons.AddButton(buttonCancel)
        sizerButtons.Realize()
        self.Bind(wx.EVT_BUTTON, self.__on_ok, buttonOk)

        self.devbox = wx.BoxSizer(wx.VERTICAL)
        self.devbox.Add(self.gridDev, 1, wx.ALL | wx.EXPAND, 10)
        self.devbox.Add(serverSizer, 0, wx.ALL | wx.EXPAND, 10)
        self.devbox.Add(sizerButtons, 0, wx.ALL | wx.EXPAND, 10)

        self.SetSizerAndFit(self.devbox)

    def __set_dev_grid(self):
        colourBackground = self.gridDev.GetLabelBackgroundColour()
        attributes = grid.GridCellAttr()
        attributes.SetBackgroundColour(colourBackground)
        self.gridDev.SetColAttr(self.COL_IND, attributes)

        self.gridDev.ClearGrid()

        i = 0
        for device in self.devices:
            self.gridDev.SetReadOnly(i, self.COL_SEL, True)
            self.gridDev.SetReadOnly(i, self.COL_DEV, device.isDevice)
            self.gridDev.SetReadOnly(i, self.COL_TUN, True)
            self.gridDev.SetReadOnly(i, self.COL_SER, True)
            self.gridDev.SetReadOnly(i, self.COL_IND, True)
            self.gridDev.SetCellRenderer(i, self.COL_SEL, CellRenderer())
            if device.isDevice:
                cell = grid.GridCellChoiceEditor(map(str, device.gains),
                                                 allowOthers=False)
                self.gridDev.SetCellEditor(i, self.COL_GAIN, cell)
            self.gridDev.SetCellEditor(i, self.COL_CAL,
                                       grid.GridCellFloatEditor(-1, 3))
            self.gridDev.SetCellEditor(i, self.COL_LO,
                                       grid.GridCellFloatEditor(-1, 3))
            if device.isDevice:
                self.gridDev.SetCellValue(i, self.COL_DEV, device.name)
                self.gridDev.SetCellValue(i, self.COL_SER, str(device.serial))
                self.gridDev.SetCellValue(i, self.COL_IND, str(i))
                self.gridDev.SetCellBackgroundColour(i, self.COL_DEV,
                                                     colourBackground)
                self.gridDev.SetCellValue(i, self.COL_GAIN,
                                          str(nearest(device.gain,
                                                      device.gains)))
            else:
                self.gridDev.SetCellValue(i, self.COL_DEV,
                                          '{0}:{1}'.format(device.server,
                                                           device.port))
                self.gridDev.SetCellValue(i, self.COL_SER, '')
                self.gridDev.SetCellValue(i, self.COL_IND, '')
                self.gridDev.SetCellValue(i, self.COL_GAIN, str(device.gain))
            self.gridDev.SetCellBackgroundColour(i, self.COL_SER,
                                                 colourBackground)

            self.gridDev.SetCellValue(i, self.COL_TUN, TUNER[device.tuner])
            self.gridDev.SetCellValue(i, self.COL_CAL, str(device.calibration))
            self.gridDev.SetCellValue(i, self.COL_LO, str(device.lo))
            self.gridDev.SetCellValue(i, self.COL_OFF, str(device.offset / 1e3))
            i += 1

        if self.settings.indexRtl >= len(self.devices):
            self.settings.indexRtl = len(self.devices) - 1
        self.__select_row(self.settings.indexRtl)
        self.index = self.settings.indexRtl

        self.gridDev.AutoSize()

    def __get_dev_grid(self):
        i = 0
        for device in self.devices:
            if not device.isDevice:
                server = self.gridDev.GetCellValue(i, self.COL_DEV)
                server = '//' + server
                url = urlparse(server)
                if url.hostname is not None:
                    device.server = url.hostname
                else:
                    device.server = 'localhost'
                if url.port is not None:
                    device.port = url.port
                else:
                    device.port = 1234
            device.gain = float(self.gridDev.GetCellValue(i, self.COL_GAIN))
            device.calibration = float(self.gridDev.GetCellValue(i, self.COL_CAL))
            device.lo = float(self.gridDev.GetCellValue(i, self.COL_LO))
            device.offset = float(self.gridDev.GetCellValue(i, self.COL_OFF)) * 1e3
            i += 1

    def __set_button_state(self):
        if len(self.devices) > 0:
            if self.devices[self.index].isDevice:
                self.buttonDel.Disable()
            else:
                self.buttonDel.Enable()

    def __warn_duplicates(self):
        servers = []
        for device in self.devices:
            if not device.isDevice:
                servers.append("{0}:{1}".format(device.server, device.port))

        dupes = set(servers)
        if len(dupes) != len(servers):
            message = "Duplicate server found:\n'{0}'".format(dupes.pop())
            dlg = wx.MessageDialog(self, message, "Warning",
                                   wx.OK | wx.ICON_WARNING)
            dlg.ShowModal()
            dlg.Destroy()
            return True

        return False

    def __on_click(self, event):
        col = event.GetCol()
        index = event.GetRow()
        if col == self.COL_SEL:
            self.index = event.GetRow()
            self.__select_row(index)
        elif col == self.COL_OFF:
            device = self.devices[index]
            dlg = DialogOffset(self, device,
                               float(self.gridDev.GetCellValue(index,
                                                               self.COL_OFF)),
                               self.settings.winFunc)
            if dlg.ShowModal() == wx.ID_OK:
                self.gridDev.SetCellValue(index, self.COL_OFF,
                                          str(dlg.get_offset()))
            dlg.Destroy()
        else:
            self.gridDev.ForceRefresh()
            event.Skip()

        self.__set_button_state()

    def __on_add(self, _event):
        device = DeviceRTL()
        device.isDevice = False
        self.devices.append(device)
        self.gridDev.AppendRows(1)
        self.__set_dev_grid()
        self.SetSizerAndFit(self.devbox)

    def __on_del(self, _event):
        del self.devices[self.index]
        self.gridDev.DeleteRows(self.index)
        self.__set_dev_grid()
        self.SetSizerAndFit(self.devbox)
        self.__set_button_state()

    def __on_ok(self, _event):
        self.__get_dev_grid()
        if self.__warn_duplicates():
            return
        self.EndModal(wx.ID_OK)

    def __select_row(self, index):
        self.gridDev.ClearSelection()
        for i in range(0, len(self.devices)):
            tick = "0"
            if i == index:
                tick = "1"
            self.gridDev.SetCellValue(i, self.COL_SEL, tick)

    def get_index(self):
        return self.index

    def get_devices(self):
        return self.devices


class DialogDevicesGPS(wx.Dialog):
    COL_SEL, COL_NAME, COL_TYPE, COL_HOST, COL_TEST = range(5)

    def __init__(self, parent, settings):
        self.settings = settings
        self.index = settings.indexGps
        self.devices = copy.copy(settings.devicesGps)
        self.comboType = None

        wx.Dialog.__init__(self, parent=parent, title="GPS Devices")

        self.gridDev = grid.Grid(self)
        self.gridDev.CreateGrid(len(self.devices), 5)
        self.gridDev.SetRowLabelSize(0)
        self.gridDev.SetColLabelValue(self.COL_SEL, "Select")
        self.gridDev.SetColLabelValue(self.COL_NAME, "Name")
        self.gridDev.SetColLabelValue(self.COL_HOST, "Host")
        self.gridDev.SetColLabelValue(self.COL_TYPE, "Type")
        self.gridDev.SetColLabelValue(self.COL_TEST, "Test")

        self.__set_dev_grid()

        sizerDevice = wx.BoxSizer(wx.HORIZONTAL)
        buttonAdd = wx.Button(self, wx.ID_ADD)
        self.buttonDel = wx.Button(self, wx.ID_DELETE)
        self.Bind(wx.EVT_BUTTON, self.__on_add, buttonAdd)
        self.Bind(wx.EVT_BUTTON, self.__on_del, self.buttonDel)
        sizerDevice.Add(buttonAdd, 0, wx.ALL)
        sizerDevice.Add(self.buttonDel, 0, wx.ALL)
        self.__set_button_state()

        buttonOk = wx.Button(self, wx.ID_OK)
        buttonCancel = wx.Button(self, wx.ID_CANCEL)
        sizerButtons = wx.StdDialogButtonSizer()
        sizerButtons.AddButton(buttonOk)
        sizerButtons.AddButton(buttonCancel)
        sizerButtons.Realize()
        self.Bind(wx.EVT_BUTTON, self.__on_ok, buttonOk)

        self.devbox = wx.BoxSizer(wx.VERTICAL)
        self.devbox.Add(self.gridDev, 1, wx.ALL | wx.EXPAND, 10)
        self.devbox.Add(sizerDevice, 0, wx.ALL | wx.EXPAND, 10)
        self.devbox.Add(sizerButtons, 0, wx.ALL | wx.EXPAND, 10)

        self.SetSizerAndFit(self.devbox)

    def __set_dev_grid(self):
        self.gridDev.Unbind(grid.EVT_GRID_EDITOR_CREATED)
        self.Unbind(grid.EVT_GRID_CELL_LEFT_CLICK)
        self.Unbind(grid.EVT_GRID_CELL_CHANGE)
        self.gridDev.ClearGrid()

        i = 0
        for device in self.devices:
            self.gridDev.SetReadOnly(i, self.COL_SEL, True)
            self.gridDev.SetCellRenderer(i, self.COL_SEL, CellRenderer())
            self.gridDev.SetCellValue(i, self.COL_NAME, device.name)
            cell = grid.GridCellChoiceEditor(sorted(DeviceGPS.TYPE),
                                             allowOthers=False)
            self.gridDev.SetCellValue(i, self.COL_TYPE,
                                      DeviceGPS.TYPE[device.type])
            self.gridDev.SetCellEditor(i, self.COL_TYPE, cell)

            if device.type == DeviceGPS.NMEA_SERIAL:
                self.gridDev.SetCellValue(i, self.COL_HOST,
                                          device.get_serial_desc())
                self.gridDev.SetReadOnly(i, self.COL_HOST, True)
            else:
                self.gridDev.SetCellValue(i, self.COL_HOST, device.resource)
                self.gridDev.SetReadOnly(i, self.COL_HOST, False)

            self.gridDev.SetCellValue(i, self.COL_TEST, '...')
            self.gridDev.SetCellAlignment(i, self.COL_TEST,
                                          wx.ALIGN_CENTRE, wx.ALIGN_CENTRE)
            i += 1

        if self.index >= len(self.devices):
            self.index = len(self.devices) - 1
        self.__select_row(self.index)
        self.index = self.index

        self.gridDev.AutoSize()

        self.gridDev.Bind(grid.EVT_GRID_EDITOR_CREATED, self.__on_create)
        self.Bind(grid.EVT_GRID_CELL_LEFT_CLICK, self.__on_click)
        self.Bind(grid.EVT_GRID_CELL_CHANGE, self.__on_change)

    def __set_button_state(self):
        if len(self.devices) > 0:
            self.buttonDel.Enable()
        else:
            self.buttonDel.Disable()
        if len(self.devices) == 1:
            self.__select_row(0)

    def __warn_duplicates(self):
        devices = []
        for device in self.devices:
            devices.append(device.name)

        dupes = set(devices)
        if len(dupes) != len(devices):
            message = "Duplicate name found:\n'{0}'".format(dupes.pop())
            dlg = wx.MessageDialog(self, message, "Warning",
                                   wx.OK | wx.ICON_WARNING)
            dlg.ShowModal()
            dlg.Destroy()
            return True

        return False

    def __on_create(self, event):
        col = event.GetCol()
        index = event.GetRow()
        device = self.devices[index]
        if col == self.COL_TYPE:
            self.comboType = event.GetControl()
            self.comboType.Bind(wx.EVT_COMBOBOX,
                                lambda event,
                                device=device: self.__on_type(event, device))
        event.Skip()

    def __on_click(self, event):
        col = event.GetCol()
        index = event.GetRow()
        device = self.devices[index]
        if col == self.COL_SEL:
            self.index = event.GetRow()
            self.__select_row(index)
        elif col == self.COL_HOST:
            if device.type == DeviceGPS.NMEA_SERIAL:
                dlg = DialogGPSSerial(self, device)
                dlg.ShowModal()
                dlg.Destroy()
                self.gridDev.SetCellValue(index, self.COL_HOST,
                                          device.get_serial_desc())
            else:
                event.Skip()

        elif col == self.COL_TEST:
            dlg = DialogGPSTest(self, device)
            dlg.ShowModal()
            dlg.Destroy()
        else:
            self.gridDev.ForceRefresh()
            event.Skip()

    def __on_change(self, event):
        col = event.GetCol()
        index = event.GetRow()
        device = self.devices[index]
        if col == self.COL_NAME:
            device.name = self.gridDev.GetCellValue(index, self.COL_NAME)
        elif col == self.COL_TYPE:
            device.type = DeviceGPS.TYPE.index(self.gridDev.GetCellValue(index,
                                                                         self.COL_TYPE))
            self.__set_dev_grid()
            event.Skip()
        elif col == self.COL_HOST:
            if device.type != DeviceGPS.NMEA_SERIAL:
                device.resource = self.gridDev.GetCellValue(index,
                                                            self.COL_HOST)

    def __on_type(self, event, device):
        device.type = DeviceGPS.TYPE.index(event.GetString())
        if device.type == DeviceGPS.NMEA_SERIAL:
            device.resource = get_serial_ports()[0]
        elif device.type == DeviceGPS.NMEA_TCP:
            device.resource = 'localhost:10110'
        else:
            device.resource = 'localhost:2947'

    def __on_add(self, _event):
        device = DeviceGPS()
        self.devices.append(device)
        self.gridDev.AppendRows(1)
        self.__set_dev_grid()
        self.SetSizerAndFit(self.devbox)
        self.__set_button_state()

    def __on_del(self, _event):
        del self.devices[self.index]
        self.gridDev.DeleteRows(self.index)
        self.__set_dev_grid()
        self.SetSizerAndFit(self.devbox)
        self.__set_button_state()

    def __on_ok(self, _event):
        if self.__warn_duplicates():
            return

        self.settings.devicesGps = self.devices
        if len(self.devices) == 0:
            self.index = -1
        self.settings.indexGps = self.index
        self.EndModal(wx.ID_OK)

    def __select_row(self, index):
        self.index = index
        self.gridDev.ClearSelection()
        for i in range(0, len(self.devices)):
            tick = "0"
            if i == index:
                tick = "1"
            self.gridDev.SetCellValue(i, self.COL_SEL, tick)


class DialogWinFunc(wx.Dialog):
    def __init__(self, parent, winFunc):
        self.winFunc = winFunc
        x = numpy.linspace(-numpy.pi, numpy.pi, 1000)
        self.data = numpy.sin(x) + 0j

        wx.Dialog.__init__(self, parent=parent, title="Window Function")

        self.figure = matplotlib.figure.Figure(facecolor='white',
                                               figsize=(5, 4))
        self.figure.suptitle('Window Function')
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.axesWin = self.figure.add_subplot(211)
        self.axesFft = self.figure.add_subplot(212)

        text = wx.StaticText(self, label='Function')

        self.choice = wx.Choice(self, choices=WINFUNC[::2])
        self.choice.SetSelection(WINFUNC[::2].index(winFunc))

        sizerButtons = wx.StdDialogButtonSizer()
        buttonOk = wx.Button(self, wx.ID_OK)
        buttonCancel = wx.Button(self, wx.ID_CANCEL)
        sizerButtons.AddButton(buttonOk)
        sizerButtons.AddButton(buttonCancel)
        sizerButtons.Realize()
        self.Bind(wx.EVT_BUTTON, self.__on_ok, buttonOk)

        sizerFunction = wx.BoxSizer(wx.HORIZONTAL)
        sizerFunction.Add(text, flag=wx.ALL, border=5)
        sizerFunction.Add(self.choice, flag=wx.ALL, border=5)

        sizerGrid = wx.GridBagSizer(5, 5)
        sizerGrid.Add(self.canvas, pos=(0, 0), span=(1, 2), border=5)
        sizerGrid.Add(sizerFunction, pos=(1, 0), span=(1, 2),
                      flag=wx.ALIGN_CENTRE | wx.ALL, border=5)
        sizerGrid.Add(sizerButtons, pos=(2, 1),
                  flag=wx.ALIGN_RIGHT | wx.ALL, border=5)

        self.Bind(wx.EVT_CHOICE, self.__on_choice, self.choice)
        self.Bind(wx.EVT_BUTTON, self.__on_ok, buttonOk)

        self.__plot()

        self.SetSizerAndFit(sizerGrid)

    def __plot(self):
        pos = WINFUNC[::2].index(self.winFunc)
        function = WINFUNC[1::2][pos](512)

        self.axesWin.clear()
        self.axesWin.plot(function, 'g')
        self.axesWin.set_xlabel('Time')
        self.axesWin.set_ylabel('Multiplier')
        self.axesWin.set_xlim(0, 512)
        self.axesWin.set_xticklabels([])
        self.axesFft.clear()
        self.axesFft.psd(self.data, NFFT=512, Fs=1000, window=function)
        self.axesFft.set_xlabel('Frequency')
        self.axesFft.set_ylabel('$\mathsf{dB/\sqrt{Hz}}$')
        self.axesFft.set_xlim(-256, 256)
        self.axesFft.set_xticklabels([])
        self.figure.tight_layout()

        self.canvas.draw()

    def __on_choice(self, _event):
        self.winFunc = WINFUNC[::2][self.choice.GetSelection()]
        self.plot()

    def __on_ok(self, _event):
        self.EndModal(wx.ID_OK)

    def get_win_func(self):
        return self.winFunc


class DialogGPSSerial(wx.Dialog):
    def __init__(self, parent, device):
        self.device = device
        self.ports = get_serial_ports()

        wx.Dialog.__init__(self, parent=parent, title='Serial port settings')

        textPort = wx.StaticText(self, label='Port')
        self.choicePort = wx.Choice(self, choices=self.ports)
        sel = 0
        if device.resource in self.ports:
            sel = self.ports.index(device.resource)
        self.choicePort.SetSelection(sel)

        textBaud = wx.StaticText(self, label='Baud rate')
        self.choiceBaud = wx.Choice(self,
                                    choices=[str(baud) for baud in DeviceGPS.BAUDS])
        self.choiceBaud.SetSelection(DeviceGPS.BAUDS.index(device.baud))
        textByte = wx.StaticText(self, label='Byte size')
        self.choiceBytes = wx.Choice(self,
                                     choices=[str(byte) for byte in DeviceGPS.BYTES])
        self.choiceBytes.SetSelection(DeviceGPS.BYTES.index(device.bytes))
        textParity = wx.StaticText(self, label='Parity')
        self.choiceParity = wx.Choice(self, choices=DeviceGPS.PARITIES)
        self.choiceParity.SetSelection(DeviceGPS.PARITIES.index(device.parity))
        textStop = wx.StaticText(self, label='Stop bits')
        self.choiceStops = wx.Choice(self,
                                     choices=[str(stop) for stop in DeviceGPS.STOPS])
        self.choiceStops.SetSelection(DeviceGPS.STOPS.index(device.stops))
        textSoft = wx.StaticText(self, label='Software flow control')
        self.checkSoft = wx.CheckBox(self)
        self.checkSoft.SetValue(device.soft)

        buttonOk = wx.Button(self, wx.ID_OK)
        buttonCancel = wx.Button(self, wx.ID_CANCEL)
        sizerButtons = wx.StdDialogButtonSizer()
        sizerButtons.AddButton(buttonOk)
        sizerButtons.AddButton(buttonCancel)
        sizerButtons.Realize()
        self.Bind(wx.EVT_BUTTON, self.__on_ok, buttonOk)

        grid = wx.GridBagSizer(10, 10)
        grid.Add(textPort, pos=(0, 0), flag=wx.ALL)
        grid.Add(self.choicePort, pos=(0, 1), flag=wx.ALL)
        grid.Add(textBaud, pos=(1, 0), flag=wx.ALL)
        grid.Add(self.choiceBaud, pos=(1, 1), flag=wx.ALL)
        grid.Add(textByte, pos=(2, 0), flag=wx.ALL)
        grid.Add(self.choiceBytes, pos=(2, 1), flag=wx.ALL)
        grid.Add(textParity, pos=(3, 0), flag=wx.ALL)
        grid.Add(self.choiceParity, pos=(3, 1), flag=wx.ALL)
        grid.Add(textStop, pos=(4, 0), flag=wx.ALL)
        grid.Add(self.choiceStops, pos=(4, 1), flag=wx.ALL)
        grid.Add(textSoft, pos=(5, 0), flag=wx.ALL)
        grid.Add(self.checkSoft, pos=(5, 1), flag=wx.ALL)

        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(grid, flag=wx.ALL, border=10)
        box.Add(sizerButtons, flag=wx.ALL | wx.ALIGN_RIGHT, border=10)

        self.SetSizerAndFit(box)

    def __on_ok(self, _event):
        self.device.resource = self.ports[self.choicePort.GetSelection()]
        self.device.baud = DeviceGPS.BAUDS[self.choiceBaud.GetSelection()]
        self.device.bytes = DeviceGPS.BYTES[self.choiceBytes.GetSelection()]
        self.device.parity = DeviceGPS.PARITIES[self.choiceParity.GetSelection()]
        self.device.stops = DeviceGPS.STOPS[self.choiceStops.GetSelection()]
        self.device.soft = self.checkSoft.GetValue()

        self.EndModal(wx.ID_OK)


class DialogGPSTest(wx.Dialog):
    def __init__(self, parent, device):
        self.device = device
        self.threadLocation = None
        self.raw = ''

        wx.Dialog.__init__(self, parent=parent, title='GPS Test')

        textLat = wx.StaticText(self, label='Longitude')
        self.textLat = wx.TextCtrl(self, style=wx.TE_READONLY)
        textLon = wx.StaticText(self, label='Latitude')
        self.textLon = wx.TextCtrl(self, style=wx.TE_READONLY)
        textAlt = wx.StaticText(self, label='Altitude')
        self.textAlt = wx.TextCtrl(self, style=wx.TE_READONLY)
        textRaw = wx.StaticText(self, label='Raw output')
        self.textRaw = wx.TextCtrl(self,
                                   style=wx.TE_MULTILINE | wx.TE_READONLY)

        self.buttonStart = wx.Button(self, label='Start')
        self.Bind(wx.EVT_BUTTON, self.__on_start, self.buttonStart)
        self.buttonStop = wx.Button(self, label='Stop')
        self.Bind(wx.EVT_BUTTON, self.__on_stop, self.buttonStop)
        self.buttonStop.Disable()

        buttonOk = wx.Button(self, wx.ID_OK)
        self.Bind(wx.EVT_BUTTON, self.__on_ok, buttonOk)

        grid = wx.GridBagSizer(10, 10)

        grid.Add(textLat, pos=(0, 1), flag=wx.ALL, border=5)
        grid.Add(self.textLat, pos=(0, 2), span=(1, 2), flag=wx.ALL, border=5)
        grid.Add(textLon, pos=(1, 1), flag=wx.ALL, border=5)
        grid.Add(self.textLon, pos=(1, 2), span=(1, 2), flag=wx.ALL, border=5)
        grid.Add(textAlt, pos=(2, 1), flag=wx.ALL, border=5)
        grid.Add(self.textAlt, pos=(2, 2), span=(1, 2), flag=wx.ALL, border=5)
        grid.Add(textRaw, pos=(3, 0), flag=wx.ALL, border=5)
        grid.Add(self.textRaw, pos=(4, 0), span=(5, 4),
                 flag=wx.ALL | wx.EXPAND, border=5)
        grid.Add(self.buttonStart, pos=(9, 1), flag=wx.ALL, border=5)
        grid.Add(self.buttonStop, pos=(9, 2), flag=wx.ALL, border=5)
        grid.Add(buttonOk, pos=(10, 3), flag=wx.ALL, border=5)

        self.SetSizerAndFit(grid)

        self.queue = Queue.Queue()
        self.Bind(wx.EVT_IDLE, self.__on_idle)

    def __on_start(self, _event):
        if not self.threadLocation:
            self.buttonStart.Disable()
            self.buttonStop.Enable()
            self.textRaw.SetValue('')
            self.__add_raw('Starting...')
            self.threadLocation = ThreadLocation(self.queue, self.device,
                                                 raw=True)

    def __on_stop(self, _event):
        if self.threadLocation and self.threadLocation.isAlive():
            self.__add_raw('Stopping...')
            self.threadLocation.stop()
            self.threadLocation.join()
        self.threadLocation = None
        self.buttonStart.Enable()
        self.buttonStop.Disable()

    def __on_ok(self, _event):
        self.__on_stop(None)
        self.EndModal(wx.ID_OK)

    def __on_idle(self, event):
        if not self.queue.empty():
            event = self.queue.get()
            status = event.data.get_status()
            loc = event.data.get_arg2()

            if status == Event.LOC:
                if loc[0] is not None:
                    text = str(loc[0])
                else:
                    text = ''
                self.textLon.SetValue(text)
                if loc[1] is not None:
                    text = str(loc[1])
                else:
                    text = ''
                self.textLat.SetValue(text)
                if loc[2] is not None:
                    text = str(loc[2])
                else:
                    text = ''
                self.textAlt.SetValue(text)
            elif status == Event.LOC_WARN:
                self.__on_stop(None)
                self.__add_raw('{0}'.format(loc))
            elif status == Event.LOC_RAW:
                self.__add_raw(loc)

    def __add_raw(self, text):
        text = text.replace('\n', '')
        text = text.replace('\r', '')
        terminal = self.textRaw.GetValue().split('\n')
        terminal.append(text)
        while len(terminal) > 100:
            terminal.pop(0)
        self.textRaw.SetValue('\n'.join(terminal))
        self.textRaw.ScrollPages(9999)


class DialogSaveWarn(wx.Dialog):
    def __init__(self, parent, warnType):
        self.code = -1

        wx.Dialog.__init__(self, parent=parent, title="Warning")

        prompt = ["scanning again", "opening a file",
                  "exiting", "clearing"][warnType]
        text = wx.StaticText(self,
                             label="Save plot before {0}?".format(prompt))
        icon = wx.StaticBitmap(self, wx.ID_ANY,
                               wx.ArtProvider.GetBitmap(wx.ART_INFORMATION,
                                                        wx.ART_MESSAGE_BOX))

        tbox = wx.BoxSizer(wx.HORIZONTAL)
        tbox.Add(text)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(icon, 0, wx.ALL, 5)
        hbox.Add(tbox, 0, wx.ALL, 5)

        buttonYes = wx.Button(self, wx.ID_YES, 'Yes')
        buttonNo = wx.Button(self, wx.ID_NO, 'No')
        buttonCancel = wx.Button(self, wx.ID_CANCEL, 'Cancel')

        buttonYes.Bind(wx.EVT_BUTTON, self.__on_close)
        buttonNo.Bind(wx.EVT_BUTTON, self.__on_close)

        buttons = wx.StdDialogButtonSizer()
        buttons.AddButton(buttonYes)
        buttons.AddButton(buttonNo)
        buttons.AddButton(buttonCancel)
        buttons.Realize()

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(hbox, 1, wx.ALL | wx.EXPAND, 10)
        vbox.Add(buttons, 1, wx.ALL | wx.EXPAND, 10)

        self.SetSizerAndFit(vbox)

    def __on_close(self, event):
        self.EndModal(event.GetId())
        return

    def get_code(self):
        return self.code


class DialogRefresh(wx.Dialog):
    def __init__(self, parent):

        wx.Dialog.__init__(self, parent=parent, style=0)

        text = wx.StaticText(self, label="Refreshing plot, please wait...")
        icon = wx.StaticBitmap(self, wx.ID_ANY,
                               wx.ArtProvider.GetBitmap(wx.ART_INFORMATION,
                                                        wx.ART_MESSAGE_BOX))

        box = wx.BoxSizer(wx.HORIZONTAL)
        box.Add(icon, flag=wx.ALIGN_CENTRE | wx.ALL, border=10)
        box.Add(text, flag=wx.ALIGN_CENTRE | wx.ALL, border=10)

        self.SetSizerAndFit(box)
        self.Centre()


class DialogAbout(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent=parent, title="About")

        bitmapIcon = wx.StaticBitmap(self, bitmap=load_bitmap('icon'))
        textAbout = wx.StaticText(self, label="A simple spectrum analyser for "
                                  "scanning\n with a RTL-SDR compatible USB "
                                  "device", style=wx.ALIGN_CENTRE)
        textLink = wx.HyperlinkCtrl(self, wx.ID_ANY,
                                    label="http://eartoearoak.com/software/rtlsdr-scanner",
                                    url="http://eartoearoak.com/software/rtlsdr-scanner")
        textTimestamp = wx.StaticText(self,
                                      label="Updated: " + get_version_timestamp())
        buttonOk = wx.Button(self, wx.ID_OK)

        grid = wx.GridBagSizer(10, 10)
        grid.Add(bitmapIcon, pos=(0, 0), span=(3, 1),
                 flag=wx.ALIGN_LEFT | wx.ALL, border=10)
        grid.Add(textAbout, pos=(0, 1), span=(1, 2),
                 flag=wx.ALIGN_CENTRE | wx.ALL, border=10)
        grid.Add(textLink, pos=(1, 1), span=(1, 2),
                 flag=wx.ALIGN_CENTRE | wx.ALL, border=10)
        grid.Add(textTimestamp, pos=(2, 1), span=(1, 2),
                 flag=wx.ALIGN_CENTRE | wx.ALL, border=10)
        grid.Add(buttonOk, pos=(3, 2), span=(1, 1),
                 flag=wx.ALIGN_RIGHT | wx.ALL, border=10)

        self.SetSizerAndFit(grid)
        self.Centre()


if __name__ == '__main__':
    print 'Please run rtlsdr_scan.py'
    exit(1)

########NEW FILE########
__FILENAME__ = events
#
# rtlsdr_scan
#
# http://eartoearoak.com/software/rtlsdr-scanner
#
# Copyright 2012 - 2014 Al Brown
#
# A frequency scanning GUI for the OsmoSDR rtl-sdr library at
# http://sdr.osmocom.org/trac/wiki/rtl-sdr
#
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import Queue

import wx


EVENT_THREAD = wx.NewId()


class Event:
    STARTING, STEPS, INFO, DATA, CAL, STOPPED, ERROR, FINISHED, PROCESSED, \
    LEVEL, UPDATED, DRAW, PLOTTED, PLOTTED_FULL, VER_UPD, VER_NOUPD, \
    VER_UPDFAIL, LOC, LOC_RAW, LOC_WARN = range(20)


class Status():
    def __init__(self, status, arg1, arg2):
        self.status = status
        self.arg1 = arg1
        self.arg2 = arg2

    def get_status(self):
        return self.status

    def get_arg1(self):
        return self.arg1

    def get_arg2(self):
        return self.arg2


class EventThread(wx.PyEvent):
    def __init__(self, status, arg1=None, arg2=None):
        wx.PyEvent.__init__(self)
        self.SetEventType(EVENT_THREAD)
        self.data = Status(status, arg1, arg2)


def post_event(destination, status):
    if isinstance(destination, Queue.Queue):
        destination.put(status)
    elif isinstance(destination, wx.EvtHandler):
        wx.PostEvent(destination, status)


if __name__ == '__main__':
    print 'Please run rtlsdr_scan.py'
    exit(1)

########NEW FILE########
__FILENAME__ = file
#
# rtlsdr_scan
#
# http://eartoearoak.com/software/rtlsdr-scanner
#
# Copyright 2012 - 2014 Al Brown
#
# A frequency scanning GUI for the OsmoSDR rtl-sdr library at
# http://sdr.osmocom.org/trac/wiki/rtl-sdr
#
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import cPickle
import json
import os
import tempfile
import zipfile

from PIL import Image
import matplotlib
from matplotlib.backends.backend_agg import FigureCanvasAgg
import wx

from spectrum import sort_spectrum, create_mesh


class File:
    class Types:
        SAVE, PLOT, IMAGE, GEO = range(4)

    class SaveType:
        RFS = 0

    class PlotType:
        CSV, GNUPLOT, FREEMAT = range(3)

    class ImageType:
        BMP, EPS, GIF, JPEG, PDF, PNG, PPM, TIFF = range(8)

    class GeoType:
        KMZ, CSV, BMP, EPS, GIF, JPEG, PDF, PNG, PPM, TIFF = range(10)

    SAVE = [''] * 1
    SAVE[SaveType.RFS] = 'RTLSDR frequency scan (*.rfs)|*.rfs'

    PLOT = [''] * 3
    PLOT[PlotType.CSV] = "CSV table (*.csv)|*.csv"
    PLOT[PlotType.GNUPLOT] = "gnuplot script (*.plt)|*.plt"
    PLOT[PlotType.FREEMAT] = "FreeMat script (*.m)|*.m"

    IMAGE = [''] * 8
    IMAGE[ImageType.BMP] = 'Bitmap image (*.bmp)|*.bmp'
    IMAGE[ImageType.EPS] = 'Encapsulated PostScript (*.eps)|*.eps'
    IMAGE[ImageType.GIF] = 'GIF image (*.gif)|*.gif'
    IMAGE[ImageType.JPEG] = 'JPEG image (*.jpeg)|*.jpeg'
    IMAGE[ImageType.PDF] = 'Portable Document (*.pdf)|*.pdf'
    IMAGE[ImageType.PNG] = 'Portable Network Graphics Image (*.png)|*.png'
    IMAGE[ImageType.PPM] = 'Portable Pixmap image (*.ppm)|*.ppm'
    IMAGE[ImageType.TIFF] = 'Tagged Image File (*.tiff)|*.tiff'

    GEO = [''] * 10

    GEO[GeoType.BMP] = 'Bitmap image (*.bmp)|*.bmp'
    GEO[GeoType.CSV] = 'CSV Table (*.csv)|*.csv'
    GEO[GeoType.EPS] = 'Encapsulated PostScript (*.eps)|*.eps'
    GEO[GeoType.GIF] = 'GIF image (*.gif)|*.gif'
    GEO[GeoType.JPEG] = 'JPEG image (*.jpeg)|*.jpeg'
    GEO[GeoType.KMZ] = 'Google Earth (*.kmz)|*.kmz'
    GEO[GeoType.PDF] = 'Portable Document (*.pdf)|*.pdf'
    GEO[GeoType.PNG] = 'Portable Network Graphics Image (*.png)|*.png'
    GEO[GeoType.PPM] = 'Portable Pixmap image (*.ppm)|*.ppm'
    GEO[GeoType.TIFF] = 'Tagged Image File (*.tiff)|*.tiff'

    HEADER = "RTLSDR Scanner"
    VERSION = 9

    @staticmethod
    def __get_types(type):
        return [File.SAVE, File.PLOT, File.IMAGE, File.GEO][type]

    @staticmethod
    def get_type_ext(index, type=Types.PLOT):
        types = File.__get_types(type)
        filter = types[index]
        delim = filter.index('|*')
        return filter[delim + 2:]

    @staticmethod
    def get_type_filters(type=Types.PLOT):
        types = File.__get_types(type)

        filters = ''
        length = len(types)
        for i in xrange(length):
            filters += types[i]
            if i < length - 1:
                filters += '|'

        return filters

    @staticmethod
    def get_type_pretty(type):
        types = File.__get_types(type)

        pretty = ''
        length = len(types)
        for i in xrange(length):
            pretty += File.get_type_ext(i, type)
            if i < length - 2:
                pretty += ', '
            elif i < length - 1:
                pretty += ' or '

        return pretty

    @staticmethod
    def get_type_index(extension, type=Types.PLOT):
        exports = File.__get_types(type)
        for i in xrange(len(exports)):
            if extension == File.get_type_ext(i, type):
                return i

        return -1


class ScanInfo():
    start = None
    stop = None
    dwell = None
    nfft = None
    name = None
    gain = None
    lo = None
    calibration = None
    tuner = 0
    time = None
    timeFirst = None
    timeLast = None
    lat = None
    lon = None
    desc = ''

    def setFromSettings(self, settings):
        self.start = settings.start
        self.stop = settings.stop
        self.dwell = settings.dwell
        self.nfft = settings.nfft
        device = settings.devicesRtl[settings.indexRtl]
        if device.isDevice:
            self.name = device.name
        else:
            self.name = device.server + ":" + str(device.port)
        self.gain = device.gain
        self.lo = device.lo
        self.calibration = device.calibration
        self.tuner = device.tuner

    def setToSettings(self, settings):
        settings.start = self.start
        settings.stop = self.stop
        settings.dwell = self.dwell
        settings.nfft = self.nfft


def open_plot(dirname, filename):
    pickle = True
    error = False
    dwell = 0.131
    nfft = 1024
    name = None
    gain = None
    lo = None
    calibration = None
    tuner = 0
    spectrum = {}
    time = None
    lat = None
    lon = None
    desc = ''
    location = {}

    path = os.path.join(dirname, filename)
    if not os.path.exists(path):
        return None, None, None
    handle = open(path, 'rb')
    try:
        header = cPickle.load(handle)
    except cPickle.UnpicklingError:
        pickle = False
    except EOFError:
        pickle = False

    if pickle:
        try:
            _version = cPickle.load(handle)
            start = cPickle.load(handle)
            stop = cPickle.load(handle)
            spectrum[1] = {}
            spectrum[1] = cPickle.load(handle)
        except pickle.PickleError:
            error = True
    else:
        try:
            handle.seek(0)
            data = json.loads(handle.read())
            header = data[0]
            version = data[1]['Version']
            start = data[1]['Start']
            stop = data[1]['Stop']
            if version > 1:
                dwell = data[1]['Dwell']
                nfft = data[1]['Nfft']
            if version > 2:
                name = data[1]['Device']
                gain = data[1]['Gain']
                lo = data[1]['LO']
                calibration = data[1]['Calibration']
            if version > 4:
                tuner = data[1]['Tuner']
            if version > 5:
                time = data[1]['Time']
                lat = data[1]['Latitude']
                lon = data[1]['Longitude']
            if version < 7:
                spectrum[1] = {}
                for f, p in data[1]['Spectrum'].iteritems():
                    spectrum[1][float(f)] = p
            else:
                for t, s in data[1]['Spectrum'].iteritems():
                    spectrum[float(t)] = {}
                    for f, p in s.iteritems():
                        spectrum[float(t)][float(f)] = p
            if version > 7:
                desc = data[1]['Description']
            if version > 8:
                location = {}
                for t, l in data[1]['Location'].iteritems():
                    location[float(t)] = l

        except ValueError:
            error = True
        except KeyError:
            error = True

    handle.close()

    if error or header != File.HEADER:
        wx.MessageBox('Invalid or corrupted file', 'Warning',
                  wx.OK | wx.ICON_WARNING)
        return None, None, None

    scanInfo = ScanInfo()
    scanInfo.start = start
    scanInfo.stop = stop
    scanInfo.dwell = dwell
    scanInfo.nfft = nfft
    scanInfo.name = name
    scanInfo.gain = gain
    scanInfo.lo = lo
    scanInfo.calibration = calibration
    scanInfo.tuner = tuner
    scanInfo.time = time
    scanInfo.lat = lat
    scanInfo.lon = lon
    scanInfo.desc = desc

    return scanInfo, spectrum, location


def save_plot(filename, scanInfo, spectrum, location):
    data = [File.HEADER, {'Version': File.VERSION,
                          'Start':scanInfo.start,
                          'Stop':scanInfo.stop,
                          'Dwell':scanInfo.dwell,
                          'Nfft':scanInfo.nfft,
                          'Device':scanInfo.name,
                          'Gain':scanInfo.gain,
                          'LO':scanInfo.lo,
                          'Calibration':scanInfo.calibration,
                          'Tuner':scanInfo.tuner,
                          'Time':scanInfo.time,
                          'Latitude':scanInfo.lat,
                          'Longitude':scanInfo.lon,
                          'Description':scanInfo.desc,
                          'Spectrum': spectrum,
                          'Location': location}]

    handle = open(os.path.join(filename), 'wb')
    handle.write(json.dumps(data, indent=4))
    handle.close()


def export_plot(filename, exportType, spectrum):
    spectrum = sort_spectrum(spectrum)
    handle = open(filename, 'wb')
    if exportType == File.PlotType.CSV:
        export_csv(handle, spectrum)
    elif exportType == File.PlotType.GNUPLOT:
        export_plt(handle, spectrum)
    elif exportType == File.PlotType.FREEMAT:
        export_freemat(handle, spectrum)
    handle.close()


def export_image(filename, format, figure, dpi):
    oldSize = figure.get_size_inches()
    oldDpi = figure.get_dpi()
    figure.set_size_inches((8, 4.5))
    figure.set_dpi(dpi)

    canvas = FigureCanvasAgg(figure)
    canvas.draw()
    renderer = canvas.get_renderer()
    if matplotlib.__version__ >= '1.2':
        buf = renderer.buffer_rgba()
    else:
        buf = renderer.buffer_rgba(0, 0)
    size = canvas.get_width_height()
    image = Image.frombuffer('RGBA', size, buf, 'raw', 'RGBA', 0, 1)
    image = image.convert('RGB')
    ext = File.get_type_ext(format, File.Types.IMAGE)
    image.save(filename, format=ext[1::], dpi=(dpi, dpi))

    figure.set_size_inches(oldSize)
    figure.set_dpi(oldDpi)


def export_map(filename, exportType, bounds, image, xyz):
    if exportType == File.GeoType.KMZ:
        export_kmz(filename, bounds, image)
    elif exportType == File.GeoType.CSV:
        export_xyz(filename, xyz)
    else:
        export_map_image(filename, exportType, image)


def export_csv(handle, spectrum):
    handle.write(u"Time (UTC), Frequency (MHz),Level (dB/Hz)\n")
    for plot in spectrum.iteritems():
        for freq, pwr in plot[1].iteritems():
            handle.write("{0}, {1}, {2}\n".format(plot[0], freq, pwr))


def export_plt(handle, spectrum):
    handle.write('set title "RTLSDR Scan"\n')
    handle.write('set xlabel "Frequency (MHz)"\n')
    handle.write('set ylabel "Time"\n')
    handle.write('set zlabel "Level (dB/Hz)"\n')
    handle.write('set ydata time\n')
    handle.write('set timefmt "%s"\n')
    handle.write('set format y "%H:%M:%S"\n')
    handle.write('set pm3d\n')
    handle.write('set hidden3d\n')
    handle.write('set palette rgb 33,13,10\n')
    handle.write('splot "-" using 1:2:3 notitle with lines \n')
    for plot in spectrum.iteritems():
        handle.write('\n')
        for freq, pwr in plot[1].iteritems():
            handle.write("{0} {1} {2}\n".format(freq, plot[0], pwr))


def export_freemat(handle, spectrum):
    x, y, z = create_mesh(spectrum, False)
    write_numpy(handle, x, 'x')
    write_numpy(handle, y, 'y')
    write_numpy(handle, z, 'z')
    handle.write('\n')
    handle.write('surf(x,y,z)\n')
    handle.write('view(3)\n')
    handle.write("set(gca, 'plotboxaspectratio', [3, 2, 1])\n")
    handle.write("title('RTLSDR Scan')\n")
    handle.write("xlabel('Frequency (MHz)')\n")
    handle.write("ylabel('Time')\n")
    handle.write("zlabel('Level (dB/Hz)')\n")
    handle.write("grid('on')\n")


def export_kmz(filename, bounds, image):
    tempPath = tempfile.mkdtemp()

    name = os.path.splitext(os.path.basename(filename))[0]
    filePng = name + '.png'
    fileKml = name + '.kml'

    image.save('{0}/{1}'.format(tempPath, filePng))

    handle = open('{0}/{1}'.format(tempPath, fileKml), 'wb')
    handle.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    handle.write('<kml xmlns="http://www.opengis.net/kml/2.2" '
                 'xmlns:gx="http://www.google.com/kml/ext/2.2" '
                 'xmlns:kml="http://www.opengis.net/kml/2.2" '
                 'xmlns:atom="http://www.w3.org/2005/Atom">\n')
    handle.write('<GroundOverlay>\n')
    handle.write('\t<name>RTLSDR Scanner - {0}</name>\n'.format(name))
    handle.write('\t<Icon>\n')
    handle.write('\t\t<href>files/{0}</href>\n'.format(filePng))
    handle.write('\t\t<viewBoundScale>0.75</viewBoundScale>\n')
    handle.write('\t</Icon>\n')
    handle.write('\t<LatLonBox>\n')
    handle.write('\t\t<north>{0}</north>\n'.format(bounds[3]))
    handle.write('\t\t<south>{0}</south>\n'.format(bounds[2]))
    handle.write('\t\t<east>{0}</east>\n'.format(bounds[1]))
    handle.write('\t\t<west>{0}</west>\n'.format(bounds[0]))
    handle.write('\t</LatLonBox>\n')
    handle.write('</GroundOverlay>\n')
    handle.write('</kml>\n')
    handle.close()

    kmz = zipfile.ZipFile(filename, 'w')
    kmz.write('{0}/{1}'.format(tempPath, fileKml),
              '/{0}'.format(fileKml))
    kmz.write('{0}/{1}'.format(tempPath, filePng),
              '/files/{0}'.format(filePng))
    kmz.close()

    os.remove('{0}/{1}'.format(tempPath, filePng))
    os.remove('{0}/{1}'.format(tempPath, fileKml))
    os.rmdir(tempPath)


def export_xyz(filename, xyz):
    handle = open(filename, 'wb')
    handle.write('x, y, Level (dB/Hz)\n')
    for i in range(len(xyz[0])):
        handle.write('{0}, {1}, {2}\n'.format(xyz[0][i], xyz[1][i], xyz[2][i]))
    handle.close()


def export_map_image(filename, exportType, image):
    ext = File.get_type_ext(exportType, File.Types.IMAGE)
    image.save(filename, format=ext[1::])


def write_numpy(handle, array, name):
    handle.write('{0}=[\n'.format(name))
    for i in array:
        for j in i:
            handle.write('{0} '.format(j))
        handle.write(';\n')
    handle.write(']\n')


def extension_add(fileName, index, fileType):
    _name, extCurrent = os.path.splitext(fileName)
    ext = File.get_type_ext(index, fileType)
    if extCurrent != ext:
        return fileName + ext

    return fileName


if __name__ == '__main__':
    print 'Please run rtlsdr_scan.py'
    exit(1)

########NEW FILE########
__FILENAME__ = location
#
# rtlsdr_scan
#
# http://eartoearoak.com/software/rtlsdr-scanner
#
# Copyright 2012 - 2014 Al Brown
#
# A frequency scanning GUI for the OsmoSDR rtl-sdr library at
# http://sdr.osmocom.org/trac/wiki/rtl-sdr
#
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import json
import socket
import threading
from urlparse import urlparse

import serial
from serial.serialutil import SerialException

from devices import DeviceGPS
from events import post_event, EventThread, Event


class ThreadLocation(threading.Thread):
    def __init__(self, notify, device, raw=False):
        threading.Thread.__init__(self)
        self.name = 'Location'
        self.notify = notify
        self.device = device
        self.raw = raw
        self.cancel = False
        self.comm = None

        if self.device.type in [DeviceGPS.NMEA_SERIAL, DeviceGPS.NMEA_TCP]:
            if self.__nmea_open():
                self.start()
        else:
            if self.__gpsd_open():
                self.start()

    def __tcp_connect(self, defaultPort):
        self.comm = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.comm.settimeout(5)
        self.comm.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        url = urlparse('//' + self.device.resource)
        if url.hostname is not None:
            host = url.hostname
        else:
            host = 'localhost'
        if url.port is not None:
            port = url.port
        else:
            port = defaultPort
        if self.raw:
            text = 'Opening "{0}"'.format(self.device.resource)
            post_event(self.notify, EventThread(Event.LOC_RAW, 0, text))
        try:
            self.comm.connect((host, port))
        except socket.error as error:
            post_event(self.notify, EventThread(Event.LOC_WARN,
                                                0, error))

    def __tcp_read(self):
        buf = ''
        data = True
        while data and not self.cancel:
            try:
                data = self.comm.recv(1024)
            except socket.timeout as error:
                post_event(self.notify, EventThread(Event.LOC_WARN,
                                                    0, error))
                return
            buf += data
            while buf.find('\n') != -1:
                line, buf = buf.split('\n', 1)
                yield line
                if self.raw:
                    post_event(self.notify, EventThread(Event.LOC_RAW,
                                                        0, line))
        return

    def __serial_connect(self):
        if self.raw:
            text = 'Opening "{0}"'.format(self.device.resource)
            post_event(self.notify, EventThread(Event.LOC_RAW, 0, text))
        try:
            self.comm = serial.Serial(self.device.resource,
                                      baudrate=self.device.baud,
                                      bytesize=self.device.bytes,
                                      parity=self.device.parity,
                                      stopbits=self.device.stops,
                                      xonxoff=self.device.soft,
                                      timeout=1)
        except SerialException as error:
            post_event(self.notify, EventThread(Event.LOC_WARN,
                                                0, error.message))
            return False
        return True

    def __serial_read(self):
        data = True
        while data and not self.cancel:
            data = self.comm.readline()
            yield data
            if self.raw:
                post_event(self.notify, EventThread(Event.LOC_RAW,
                                                    0, data))
        return

    def __gpsd_open(self):
        self.__tcp_connect(2947)

        try:
            if self.device.type == DeviceGPS.GPSD:
                self.comm.sendall('?WATCH={"enable": true,"json": true}')
            else:
                self.comm.sendall('w')

        except IOError as error:
            post_event(self.notify, EventThread(Event.LOC_WARN,
                                                0, error))
            self.comm.close()
            return False

        return True

    def __gpsd_read(self):
        for resp in self.__tcp_read():
            data = json.loads(resp)
            if data['class'] == 'TPV':
                if data['mode'] in [2, 3]:
                    try:
                        lat = data['lat']
                        lon = data['lon']
                    except KeyError:
                        return
                    try:
                        alt = data['alt']
                    except KeyError:
                        alt = None
                    post_event(self.notify,
                               EventThread(Event.LOC, 0,
                                           (lat, lon, alt)))

    def __gpsd_old_read(self):
        for resp in self.__tcp_read():
            data = resp.split(' ')
            if len(data) == 15 and data[0] == 'GPSD,O=GGA':
                try:
                    lat = float(data[4])
                    lon = float(data[3])
                except ValueError:
                    return
                try:
                    alt = float(data[5])
                except ValueError:
                    alt = None
                post_event(self.notify,
                           EventThread(Event.LOC, 0,
                                       (lat, lon, alt)))

    def __gpsd_close(self):
        if self.device.type == DeviceGPS.GPSD:
            self.comm.sendall('?WATCH={"enable": false}')
        else:
            self.comm.sendall('W')
        self.comm.close()

    def __nmea_open(self):
        if self.device.type == DeviceGPS.NMEA_SERIAL:
            return self.__serial_connect()
        else:
            self.__tcp_connect(10110)
            return True

    def __nmea_read(self):
        if self.device.type == DeviceGPS.NMEA_SERIAL:
            comm = self.__serial_read()
        else:
            comm = self.__tcp_read()

        for resp in comm:
            resp = resp.replace('\n', '')
            resp = resp.replace('\r', '')
            resp = resp[1::]
            resp = resp.split('*')
            if len(resp) == 2:
                checksum = self.__nmea_checksum(resp[0])
                if checksum == resp[1]:
                    data = resp[0].split(',')
                    if data[0] == 'GPGGA':
                        if data[6] in ['1', '2']:
                            lat = self.__nmea_coord(data[2], data[3])
                            lon = self.__nmea_coord(data[4], data[5])
                            try:
                                alt = float(data[9])
                            except ValueError:
                                alt = None
                            post_event(self.notify,
                                       EventThread(Event.LOC, 0,
                                                         (lat, lon, alt)))
                else:
                    error = 'Invalid checksum {0}, should be {1}'.format(resp[1],
                                                                         checksum)
                    post_event(self.notify, EventThread(Event.LOC_WARN,
                                                        0, error))

    def __nmea_checksum(self, data):
        checksum = 0
        for char in data:
            checksum ^= ord(char)
        return "{0:02X}".format(checksum)

    def __nmea_coord(self, coord, orient):
        pos = None

        if '.' in coord:
            if coord.index('.') == 4:
                try:
                    degrees = int(coord[:2])
                    minutes = float(coord[2:])
                    pos = degrees + minutes / 60.
                    if orient == 'S':
                        pos = -pos
                except ValueError:
                    pass
            elif coord.index('.') == 5:
                try:
                    degrees = int(coord[:3])
                    minutes = float(coord[3:])
                    pos = degrees + minutes / 60.
                    if orient == 'W':
                        pos = -pos
                except ValueError:
                    pass

        return pos

    def ___nmea_close(self):
        self.comm.close()

    def run(self):
        if self.device.type in [DeviceGPS.NMEA_SERIAL, DeviceGPS.NMEA_TCP]:
            self.__nmea_read()
        elif self.device.type == DeviceGPS.GPSD:
            self.__gpsd_read()
        elif self.device.type == DeviceGPS.GPSD_OLD:
            self.__gpsd_old_read()

        if self.device.type in [DeviceGPS.NMEA_SERIAL, DeviceGPS.NMEA_TCP]:
            self.___nmea_close()
        else:
            self.__gpsd_close()

    def stop(self):
        self.notify.queue.clear()
        self.cancel = True


if __name__ == '__main__':
    print 'Please run rtlsdr_scan.py'
    exit(1)

########NEW FILE########
__FILENAME__ = main_window
#
# rtlsdr_scan
#
# http://eartoearoak.com/software/rtlsdr-scanner
#
# Copyright 2012 - 2014 Al Brown
#
# A frequency scanning GUI for the OsmoSDR rtl-sdr library at
# http://sdr.osmocom.org/trac/wiki/rtl-sdr
#
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


import datetime
import math
import os.path
from threading import Thread
import threading
import time
import webbrowser

from matplotlib.dates import num2epoch
import wx
from wx.lib.masked import NumCtrl

from constants import F_MIN, F_MAX, MODE, DWELL, NFFT, DISPLAY, Warn, \
    Display, Cal, Mode
from devices import get_devices_rtl
from dialogs import DialogProperties, DialogPrefs, DialogAdvPrefs, \
    DialogDevicesRTL, DialogCompare, DialogAutoCal, DialogAbout, DialogSaveWarn, \
    DialogDevicesGPS, DialogGeo
from events import EVENT_THREAD, Event, EventThread, post_event
from file import save_plot, export_plot, open_plot, ScanInfo, export_image, \
    export_map, extension_add, File
from location import ThreadLocation
from misc import calc_samples, calc_real_dwell, \
    get_version_timestamp, get_version_timestamp_repo, add_colours
from printer import PrintOut
from scan import ThreadScan, anaylse_data, update_spectrum
from settings import Settings
from spectrum import count_points, sort_spectrum, Extent
from toolbars import Statusbar
from windows import PanelGraph


class DropTarget(wx.FileDropTarget):
    def __init__(self, window):
        wx.FileDropTarget.__init__(self)
        self.window = window

    def OnDropFiles(self, _xPos, _yPos, filenames):
        filename = filenames[0]
        if os.path.splitext(filename)[1].lower() == ".rfs":
            dirname, filename = os.path.split(filename)
            self.window.open(dirname, filename)


class RtlSdrScanner(wx.App):
    def __init__(self, pool):
        self.pool = pool
        wx.App.__init__(self, redirect=False)


class FrameMain(wx.Frame):
    def __init__(self, title, pool):

        self.grid = True

        self.pool = pool
        self.lock = threading.Lock()

        self.sdr = None
        self.threadScan = None
        self.threadUpdate = None
        self.threadLocation = None

        self.stopAtEnd = False
        self.stopScan = False

        self.dlgCal = None

        self.menuNew = None
        self.menuOpen = None
        self.menuSave = None
        self.menuExportScan = None
        self.menuExportImage = None
        self.menuExportGeo = None
        self.menuPreview = None
        self.menuPage = None
        self.menuPrint = None
        self.menuProperties = None
        self.menuPref = None
        self.menuAdvPref = None
        self.menuDevicesRtl = None
        self.menuDevicesGps = None
        self.menuReset = None
        self.menuClearSelect = None
        self.menuShowMeasure = None
        self.menuStart = None
        self.menuStop = None
        self.menuStopEnd = None
        self.menuCompare = None
        self.menuCal = None

        self.popupMenu = None
        self.popupMenuStart = None
        self.popupMenuStop = None
        self.popupMenuStopEnd = None
        self.popupMenuRangeLim = None
        self.popupMenuPointsLim = None
        self.popupMenuClearSelect = None
        self.popupMenuShowMeasure = None

        self.graph = None
        self.toolbar = None
        self.canvas = None
        self.mouseZoom = None
        self.mouseSelect = None

        self.buttonStart = None
        self.buttonStop = None
        self.controlGain = None
        self.choiceMode = None
        self.choiceDwell = None
        self.choiceNfft = None
        self.spinCtrlStart = None
        self.spinCtrlStop = None
        self.checkUpdate = None
        self.checkGrid = None
        self.choiceDisplay = None

        self.spectrum = {}
        self.scanInfo = ScanInfo()
        self.location = {}
        self.isSaved = True

        self.settings = Settings()
        self.devicesRtl = get_devices_rtl(self.settings.devicesRtl)
        self.filename = ""
        self.oldCal = 0

        self.pageConfig = wx.PageSetupDialogData()
        self.pageConfig.GetPrintData().SetOrientation(wx.LANDSCAPE)
        self.pageConfig.SetMarginTopLeft((20, 20))
        self.pageConfig.SetMarginBottomRight((20, 20))
        self.printConfig = wx.PrintDialogData(self.pageConfig.GetPrintData())
        self.printConfig.EnableSelection(False)
        self.printConfig.EnablePageNumbers(False)

        wx.Frame.__init__(self, None, title=title)

        self.Bind(wx.EVT_CLOSE, self.__on_exit)

        self.status = Statusbar(self)
        self.SetStatusBar(self.status)

        add_colours()
        self.__create_widgets()
        self.__create_menu()
        self.__create_popup_menu()
        self.__set_control_state(True)
        self.Show()

        displaySize = wx.DisplaySize()
        toolbarSize = self.toolbar.GetBestSize()
        self.SetClientSize((toolbarSize[0] + 10, displaySize[1] / 2))
        self.SetMinSize((displaySize[0] / 4, displaySize[1] / 4))

        self.Connect(-1, -1, EVENT_THREAD, self.__on_event)

        self.SetDropTarget(DropTarget(self))

        self.steps = 0
        self.stepsTotal = 0

    def __create_widgets(self):
        panel = wx.Panel(self)

        self.graph = PanelGraph(panel, self, self.settings, self.__on_motion)
        self.toolbar = wx.Panel(panel)

        self.buttonStart = wx.Button(self.toolbar, wx.ID_ANY, 'Start')
        self.buttonStop = wx.Button(self.toolbar, wx.ID_ANY, 'Stop')
        self.buttonStart.SetToolTip(wx.ToolTip('Start scan'))
        self.buttonStop.SetToolTip(wx.ToolTip('Stop scan'))
        self.Bind(wx.EVT_BUTTON, self.__on_start, self.buttonStart)
        self.Bind(wx.EVT_BUTTON, self.__on_stop, self.buttonStop)

        textRange = wx.StaticText(self.toolbar, label="Range (MHz)",
                                  style=wx.ALIGN_CENTER)
        textStart = wx.StaticText(self.toolbar, label="Start")
        textStop = wx.StaticText(self.toolbar, label="Stop")

        self.spinCtrlStart = wx.SpinCtrl(self.toolbar)
        self.spinCtrlStop = wx.SpinCtrl(self.toolbar)
        self.spinCtrlStart.SetToolTip(wx.ToolTip('Start frequency'))
        self.spinCtrlStop.SetToolTip(wx.ToolTip('Stop frequency'))
        self.spinCtrlStart.SetRange(F_MIN, F_MAX - 1)
        self.spinCtrlStop.SetRange(F_MIN + 1, F_MAX)
        self.Bind(wx.EVT_SPINCTRL, self.__on_spin, self.spinCtrlStart)
        self.Bind(wx.EVT_SPINCTRL, self.__on_spin, self.spinCtrlStop)

        textGain = wx.StaticText(self.toolbar, label="Gain (dB)")
        self.controlGain = wx.Choice(self.toolbar, choices=[''])

        textMode = wx.StaticText(self.toolbar, label="Mode")
        self.choiceMode = wx.Choice(self.toolbar, choices=MODE[::2])
        self.choiceMode.SetToolTip(wx.ToolTip('Scanning mode'))

        textDwell = wx.StaticText(self.toolbar, label="Dwell")
        self.choiceDwell = wx.Choice(self.toolbar, choices=DWELL[::2])
        self.choiceDwell.SetToolTip(wx.ToolTip('Scan time per step'))

        textNfft = wx.StaticText(self.toolbar, label="FFT size")
        self.choiceNfft = wx.Choice(self.toolbar, choices=map(str, NFFT))
        self.choiceNfft.SetToolTip(wx.ToolTip('Higher values for greater'
                                              'precision'))

        textDisplay = wx.StaticText(self.toolbar, label="Display")
        self.choiceDisplay = wx.Choice(self.toolbar, choices=DISPLAY[::2])
        self.Bind(wx.EVT_CHOICE, self.__on_choice, self.choiceDisplay)
        self.choiceDisplay.SetToolTip(wx.ToolTip('Spectrogram available in'
                                                 'continuous mode'))

        grid = wx.GridBagSizer(5, 5)
        grid.Add(self.buttonStart, pos=(0, 0), span=(3, 1),
                 flag=wx.ALIGN_CENTER)
        grid.Add(self.buttonStop, pos=(0, 1), span=(3, 1),
                 flag=wx.ALIGN_CENTER)
        grid.Add((20, 1), pos=(0, 2))
        grid.Add(textRange, pos=(0, 3), span=(1, 4), flag=wx.ALIGN_CENTER)
        grid.Add(textStart, pos=(1, 3), flag=wx.ALIGN_CENTER)
        grid.Add(self.spinCtrlStart, pos=(1, 4))
        grid.Add(textStop, pos=(1, 5), flag=wx.ALIGN_CENTER)
        grid.Add(self.spinCtrlStop, pos=(1, 6))
        grid.Add(textGain, pos=(0, 7), flag=wx.ALIGN_CENTER)
        grid.Add(self.controlGain, pos=(1, 7), flag=wx.ALIGN_CENTER)
        grid.Add((20, 1), pos=(0, 8))
        grid.Add(textMode, pos=(0, 9), flag=wx.ALIGN_CENTER)
        grid.Add(self.choiceMode, pos=(1, 9), flag=wx.ALIGN_CENTER)
        grid.Add(textDwell, pos=(0, 10), flag=wx.ALIGN_CENTER)
        grid.Add(self.choiceDwell, pos=(1, 10), flag=wx.ALIGN_CENTER)
        grid.Add(textNfft, pos=(0, 11), flag=wx.ALIGN_CENTER)
        grid.Add(self.choiceNfft, pos=(1, 11), flag=wx.ALIGN_CENTER)
        grid.Add((20, 1), pos=(0, 12))
        grid.Add(textDisplay, pos=(0, 13), flag=wx.ALIGN_CENTER)
        grid.Add(self.choiceDisplay, pos=(1, 13), flag=wx.ALIGN_CENTER)

        self.__set_controls()
        self.__set_gain_control()

        self.toolbar.SetSizer(grid)
        self.toolbar.Layout()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.graph, 1, wx.EXPAND)
        sizer.Add(self.toolbar, 0, wx.EXPAND)
        panel.SetSizer(sizer)
        panel.Layout()

    def __create_menu(self):
        menuFile = wx.Menu()
        self.menuNew = menuFile.Append(wx.ID_NEW, "&New",
                                        "New plot")
        self.menuOpen = menuFile.Append(wx.ID_OPEN, "&Open...",
                                        "Open plot")
        recent = wx.Menu()
        self.settings.fileHistory.UseMenu(recent)
        self.settings.fileHistory.AddFilesToMenu()
        menuFile.AppendMenu(wx.ID_ANY, "&Recent Files", recent)
        menuFile.AppendSeparator()
        self.menuSave = menuFile.Append(wx.ID_SAVE, "&Save As...",
                                        "Save plot")
        self.menuExportScan = menuFile.Append(wx.ID_ANY, "Export scan...",
                                              "Export scan")
        self.menuExportImage = menuFile.Append(wx.ID_ANY, "Export image...",
                                              "Export image")
        self.menuExportGeo = menuFile.Append(wx.ID_ANY, "Export map...",
                                              "Export maps")
        menuFile.AppendSeparator()
        self.menuPage = menuFile.Append(wx.ID_ANY, "Page setup...",
                                        "Page setup")
        self.menuPreview = menuFile.Append(wx.ID_ANY, "Print preview...",
                                        "Print preview")
        self.menuPrint = menuFile.Append(wx.ID_ANY, "&Print...",
                                        "Print plot")
        menuFile.AppendSeparator()
        self.menuProperties = menuFile.Append(wx.ID_ANY, "P&roperties...",
                                              "Show properties")
        menuFile.AppendSeparator()
        menuExit = menuFile.Append(wx.ID_EXIT, "E&xit", "Exit the program")

        menuEdit = wx.Menu()
        self.menuPref = menuEdit.Append(wx.ID_ANY, "&Preferences...",
                                        "Preferences")
        self.menuAdvPref = menuEdit.Append(wx.ID_ANY, "&Advanced preferences...",
                                           "Advanced preferences")
        self.menuDevicesRtl = menuEdit.Append(wx.ID_ANY, "&Radio Devices...",
                                              "Device selection and configuration")
        self.menuDevicesGps = menuEdit.Append(wx.ID_ANY, "&GPS Devices...",
                                              "GPS selection and configuration")
        menuEdit.AppendSeparator()
        self.menuReset = menuEdit.Append(wx.ID_ANY, "&Reset settings...",
                                         "Reset setting to the default")

        menuView = wx.Menu()
        self.menuClearSelect = menuView.Append(wx.ID_ANY, "Clear selection",
                                               "Clear current selection")
        self.graph.add_menu_clear_select(self.menuClearSelect)
        self.menuShowMeasure = menuView.Append(wx.ID_ANY, "Show &measurements",
                                               "Show measurements window",
                                               kind=wx.ITEM_CHECK)
        self.menuShowMeasure.Check(self.settings.showMeasure)

        menuScan = wx.Menu()
        self.menuStart = menuScan.Append(wx.ID_ANY, "&Start", "Start scan")
        self.menuStop = menuScan.Append(wx.ID_ANY, "S&top",
                                        "Stop scan immediately")
        self.menuStopEnd = menuScan.Append(wx.ID_ANY, "Stop at &end",
                                           "Complete current sweep "
                                           "before stopping")

        menuTools = wx.Menu()
        self.menuCompare = menuTools.Append(wx.ID_ANY, "&Compare...",
                                            "Compare plots")
        self.menuCal = menuTools.Append(wx.ID_ANY, "&Auto Calibration...",
                                        "Automatically calibrate to a known frequency")

        menuHelp = wx.Menu()
        menuHelpLink = menuHelp.Append(wx.ID_HELP, "&Help...",
                                       "Link to help")
        menuHelp.AppendSeparator()
        menuUpdate = menuHelp.Append(wx.ID_ANY, "&Check for updates...",
                                     "Check for updates to the program")
        menuHelp.AppendSeparator()
        menuAbout = menuHelp.Append(wx.ID_ABOUT, "&About...",
                                    "Information about this program")

        menuBar = wx.MenuBar()
        menuBar.Append(menuFile, "&File")
        menuBar.Append(menuEdit, "&Edit")
        menuBar.Append(menuView, "&View")
        menuBar.Append(menuScan, "&Scan")
        menuBar.Append(menuTools, "&Tools")
        menuBar.Append(menuHelp, "&Help")
        self.SetMenuBar(menuBar)

        self.Bind(wx.EVT_MENU, self.__on_new, self.menuNew)
        self.Bind(wx.EVT_MENU, self.__on_open, self.menuOpen)
        self.Bind(wx.EVT_MENU_RANGE, self.__on_file_history, id=wx.ID_FILE1,
                  id2=wx.ID_FILE9)
        self.Bind(wx.EVT_MENU, self.__on_save, self.menuSave)
        self.Bind(wx.EVT_MENU, self.__on_export_scan, self.menuExportScan)
        self.Bind(wx.EVT_MENU, self.__on_export_image, self.menuExportImage)
        self.Bind(wx.EVT_MENU, self.__on_export_geo, self.menuExportGeo)
        self.Bind(wx.EVT_MENU, self.__on_page, self.menuPage)
        self.Bind(wx.EVT_MENU, self.__on_preview, self.menuPreview)
        self.Bind(wx.EVT_MENU, self.__on_print, self.menuPrint)
        self.Bind(wx.EVT_MENU, self.__on_properties, self.menuProperties)
        self.Bind(wx.EVT_MENU, self.__on_exit, menuExit)
        self.Bind(wx.EVT_MENU, self.__on_pref, self.menuPref)
        self.Bind(wx.EVT_MENU, self.__on_adv_pref, self.menuAdvPref)
        self.Bind(wx.EVT_MENU, self.__on_devices_rtl, self.menuDevicesRtl)
        self.Bind(wx.EVT_MENU, self.__on_devices_gps, self.menuDevicesGps)
        self.Bind(wx.EVT_MENU, self.__on_reset, self.menuReset)
        self.Bind(wx.EVT_MENU, self.__on_clear_select, self.menuClearSelect)
        self.Bind(wx.EVT_MENU, self.__on_show_measure, self.menuShowMeasure)
        self.Bind(wx.EVT_MENU, self.__on_start, self.menuStart)
        self.Bind(wx.EVT_MENU, self.__on_stop, self.menuStop)
        self.Bind(wx.EVT_MENU, self.__on_stop_end, self.menuStopEnd)
        self.Bind(wx.EVT_MENU, self.__on_compare, self.menuCompare)
        self.Bind(wx.EVT_MENU, self.__on_cal, self.menuCal)
        self.Bind(wx.EVT_MENU, self.__on_about, menuAbout)
        self.Bind(wx.EVT_MENU, self.__on_help, menuHelpLink)
        self.Bind(wx.EVT_MENU, self.__on_update, menuUpdate)

        idF1 = wx.wx.NewId()
        self.Bind(wx.EVT_MENU, self.__on_help, id=idF1)
        accelTable = wx.AcceleratorTable([(wx.ACCEL_NORMAL, wx.WXK_F1, idF1)])
        self.SetAcceleratorTable(accelTable)

    def __create_popup_menu(self):
        self.popupMenu = wx.Menu()
        self.popupMenuStart = self.popupMenu.Append(wx.ID_ANY, "&Start",
                                                    "Start scan")
        self.popupMenuStop = self.popupMenu.Append(wx.ID_ANY, "S&top",
                                                   "Stop scan immediately")
        self.popupMenuStopEnd = self.popupMenu.Append(wx.ID_ANY, "Stop at &end",
                                                      "Complete current sweep "
                                                      "before stopping")
        self.popupMenu.AppendSeparator()
        self.popupMenuRangeLim = self.popupMenu.Append(wx.ID_ANY,
                                                       "Set range to current zoom",
                                                       "Set scanning range to the "
                                                       "current zoom")
        self.popupMenu.AppendSeparator()
        self.popupMenuPointsLim = self.popupMenu.Append(wx.ID_ANY,
                                                       "Limit points",
                                                       "Limit points to "
                                                       "increase plot speed",
                                                       kind=wx.ITEM_CHECK)
        self.popupMenuPointsLim.Check(self.settings.pointsLimit)

        self.popupMenu.AppendSeparator()
        self.popupMenuClearSelect = self.popupMenu.Append(wx.ID_ANY, "Clear selection",
                                                          "Clear current selection")
        self.graph.add_menu_clear_select(self.popupMenuClearSelect)
        self.popupMenuShowMeasure = self.popupMenu.Append(wx.ID_ANY,
                                                          "Show &measurements",
                                                          "Show measurements window",
                                                          kind=wx.ITEM_CHECK)
        self.popupMenuShowMeasure.Check(self.settings.showMeasure)

        self.Bind(wx.EVT_MENU, self.__on_start, self.popupMenuStart)
        self.Bind(wx.EVT_MENU, self.__on_stop, self.popupMenuStop)
        self.Bind(wx.EVT_MENU, self.__on_stop_end, self.popupMenuStopEnd)
        self.Bind(wx.EVT_MENU, self.__on_range_lim, self.popupMenuRangeLim)
        self.Bind(wx.EVT_MENU, self.__on_points_lim, self.popupMenuPointsLim)
        self.Bind(wx.EVT_MENU, self.__on_clear_select, self.popupMenuClearSelect)
        self.Bind(wx.EVT_MENU, self.__on_show_measure, self.popupMenuShowMeasure)

        self.Bind(wx.EVT_CONTEXT_MENU, self.__on_popup_menu)

    def __on_popup_menu(self, event):
        pos = event.GetPosition()
        pos = self.ScreenToClient(pos)
        self.PopupMenu(self.popupMenu, pos)

    def __on_new(self, _event):
        if self.__save_warn(Warn.NEW):
            return
        self.spectrum.clear()
        self.location.clear()
        self.__saved(True)
        self.__set_plot(self.spectrum, False)

    def __on_open(self, _event):
        if self.__save_warn(Warn.OPEN):
            return
        dlg = wx.FileDialog(self, "Open a scan", self.settings.dirScans,
                            self.filename,
                            File.get_type_filters(File.Types.SAVE),
                            wx.OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            self.open(dlg.GetDirectory(), dlg.GetFilename())
        dlg.Destroy()

    def __on_file_history(self, event):
        selection = event.GetId() - wx.ID_FILE1
        path = self.settings.fileHistory.GetHistoryFile(selection)
        self.settings.fileHistory.AddFileToHistory(path)
        dirname, filename = os.path.split(path)
        self.open(dirname, filename)

    def __on_save(self, _event):
        dlg = wx.FileDialog(self, "Save a scan", self.settings.dirScans,
                            self.filename,
                            File.get_type_filters(File.Types.SAVE),
                            wx.SAVE | wx.OVERWRITE_PROMPT)
        if dlg.ShowModal() == wx.ID_OK:
            self.status.set_general("Saving")
            fileName = dlg.GetFilename()
            dirName = dlg.GetDirectory()
            self.filename = os.path.splitext(fileName)[0]
            self.settings.dirScans = dirName
            fileName = extension_add(fileName, dlg.GetFilterIndex(),
                                     File.Types.SAVE)
            fullName = os.path.join(dirName, fileName)
            save_plot(fullName, self.scanInfo, self.spectrum, self.location)
            self.__saved(True)
            self.status.set_general("Finished")
            self.settings.fileHistory.AddFileToHistory(fullName)
        dlg.Destroy()

    def __on_export_scan(self, _event):
        dlg = wx.FileDialog(self, "Export a scan", self.settings.dirExport,
                            self.filename, File.get_type_filters(),
                            wx.SAVE | wx.OVERWRITE_PROMPT)
        if dlg.ShowModal() == wx.ID_OK:
            self.status.set_general("Exporting")
            fileName = dlg.GetFilename()
            dirName = dlg.GetDirectory()
            self.settings.dirExport = dirName
            fileName = extension_add(fileName, dlg.GetFilterIndex(),
                                     File.Types.PLOT)
            fullName = os.path.join(dirName, fileName)
            export_plot(fullName, dlg.GetFilterIndex(), self.spectrum)
            self.status.set_general("Finished")
        dlg.Destroy()

    def __on_export_image(self, _event):
        dlg = wx.FileDialog(self, "Export image to file",
                            self.settings.dirExport,
                            self.filename,
                            File.get_type_filters(File.Types.IMAGE),
                            wx.SAVE | wx.OVERWRITE_PROMPT)
        dlg.SetFilterIndex(File.ImageType.PNG)
        if dlg.ShowModal() == wx.ID_OK:
            self.status.set_general("Exporting")
            fileName = dlg.GetFilename()
            dirName = dlg.GetDirectory()
            self.settings.dirExport = dirName
            fileName = extension_add(fileName, dlg.GetFilterIndex(),
                                     File.Types.IMAGE)
            fullName = os.path.join(dirName, fileName)
            exportType = dlg.GetFilterIndex()
            export_image(fullName, exportType,
                         self.graph.get_figure(), self.settings.exportDpi)
            self.status.set_general("Finished")
        dlg.Destroy()

    def __on_export_geo(self, _event):
        dlgGeo = DialogGeo(self, self.spectrum, self.location, self.settings)
        if dlgGeo.ShowModal() == wx.ID_OK:
            self.status.set_general("Exporting...")
            extent = dlgGeo.get_extent()
            dlgFile = wx.FileDialog(self, "Export map to file",
                                self.settings.dirExport,
                                self.filename,
                                File.get_type_filters(File.Types.GEO),
                                wx.SAVE | wx.OVERWRITE_PROMPT)
            dlgFile.SetFilterIndex(File.GeoType.KMZ)
            if dlgFile.ShowModal() == wx.ID_OK:
                fileName = dlgFile.GetFilename()
                dirName = dlgFile.GetDirectory()
                self.settings.dirExport = dirName
                fileName = extension_add(fileName, dlgFile.GetFilterIndex(),
                                         File.Types.GEO)
                fullName = os.path.join(dirName, fileName)
                exportType = dlgFile.GetFilterIndex()
                image = None
                xyz = None
                if exportType == File.GeoType.CSV:
                    xyz = dlgGeo.get_xyz()
                else:
                    image = dlgGeo.get_image()
                export_map(fullName, exportType, extent, image, xyz)
            self.status.set_general("Finished")
            dlgFile.Destroy()
        dlgGeo.Destroy()

    def __on_page(self, _event):
        dlg = wx.PageSetupDialog(self, self.pageConfig)
        if dlg.ShowModal() == wx.ID_OK:
            self.pageConfig = wx.PageSetupDialogData(dlg.GetPageSetupDialogData())
            self.printConfig.SetPrintData(self.pageConfig.GetPrintData())
        dlg.Destroy()

    def __on_preview(self, _event):
        printout = PrintOut(self.graph, self.filename, self.pageConfig)
        printoutPrinting = PrintOut(self.graph, self.filename, self.pageConfig)
        preview = wx.PrintPreview(printout, printoutPrinting, self.printConfig)
        frame = wx.PreviewFrame(preview, self, 'Print Preview')
        frame.Initialize()
        frame.SetSize(self.GetSize())
        frame.Show(True)

    def __on_print(self, _event):
        printer = wx.Printer(self.printConfig)
        printout = PrintOut(self.graph, self.filename, self.pageConfig)
        if printer.Print(self, printout, True):
            self.printConfig = wx.PrintDialogData(printer.GetPrintDialogData())
            self.pageConfig.SetPrintData(self.printConfig.GetPrintData())

    def __on_properties(self, _event):
        if len(self.spectrum) > 0:
            self.scanInfo.timeFirst = min(self.spectrum)
            self.scanInfo.timeLast = max(self.spectrum)

        dlg = DialogProperties(self, self.scanInfo)
        dlg.ShowModal()
        dlg.Destroy()

    def __on_exit(self, _event):
        self.Unbind(wx.EVT_CLOSE)
        if self.__save_warn(Warn.EXIT):
            self.Bind(wx.EVT_CLOSE, self.__on_exit)
            return
        self.__scan_stop()
        self.__wait_background()
        self.__get_controls()
        self.graph.close()
        self.settings.dwell = DWELL[1::2][self.choiceDwell.GetSelection()]
        self.settings.nfft = NFFT[self.choiceNfft.GetSelection()]
        self.settings.devicesRtl = self.devicesRtl
        self.settings.save()
        self.Close(True)

    def __on_pref(self, _event):
        self.__get_controls()
        dlg = DialogPrefs(self, self.settings)
        if dlg.ShowModal() == wx.ID_OK:
            self.graph.create_plot()
            self.__set_control_state(True)
            self.__set_controls()
        dlg.Destroy()

    def __on_adv_pref(self, _event):
        dlg = DialogAdvPrefs(self, self.settings)
        if dlg.ShowModal() == wx.ID_OK:
            self.__set_control_state(True)
        dlg.Destroy()

    def __on_devices_rtl(self, _event):
        self.__get_controls()
        self.devicesRtl = self.__refresh_devices()
        dlg = DialogDevicesRTL(self, self.devicesRtl, self.settings)
        if dlg.ShowModal() == wx.ID_OK:
            self.devicesRtl = dlg.get_devices()
            self.settings.indexRtl = dlg.get_index()
            self.__set_gain_control()
            self.__set_control_state(True)
            self.__set_controls()
        dlg.Destroy()

    def __on_devices_gps(self, _event):
        dlg = DialogDevicesGPS(self, self.settings)
        dlg.ShowModal()
        dlg.Destroy()

    def __on_reset(self, _event):
        dlg = wx.MessageDialog(self,
                               'Reset all settings to the default values\n'
                               '(cannot be undone)?',
                               'Reset Settings',
                               wx.YES_NO | wx.ICON_QUESTION)
        if dlg.ShowModal() == wx.ID_YES:
            self.settings.reset()
            self.__set_controls()
            self.graph.create_plot()
        dlg.Destroy()

    def __on_compare(self, _event):
        dlg = DialogCompare(self, self.settings, self.filename)
        dlg.Show()

    def __on_clear_select(self, _event):
        self.graph.clear_selection()

    def __on_show_measure(self, event):
        show = event.Checked()
        self.menuShowMeasure.Check(show)
        self.popupMenuShowMeasure.Check(show)
        self.settings.showMeasure = show
        self.graph.show_measure_table(show)
        self.Layout()

    def __on_cal(self, _event):
        self.dlgCal = DialogAutoCal(self, self.settings.calFreq, self.__auto_cal)
        self.dlgCal.ShowModal()

    def __on_about(self, _event):
        dlg = DialogAbout(self)
        dlg.ShowModal()
        dlg.Destroy()

    def __on_help(self, _event):
        webbrowser.open("http://eartoearoak.com/software/rtlsdr-scanner")

    def __on_update(self, _event):
        if self.threadUpdate is None:
            self.status.set_general("Checking for updates")
            self.threadUpdate = Thread(target=self.__update_check)
            self.threadUpdate.start()

    def __on_spin(self, event):
        control = event.GetEventObject()
        if control == self.spinCtrlStart:
            self.spinCtrlStop.SetRange(self.spinCtrlStart.GetValue() + 1,
                                          F_MAX)

    def __on_choice(self, _event):
        self.__get_controls()
        self.graph.create_plot()

    def __on_start(self, _event):
        if self.settings.start >= self.settings.stop:
            wx.MessageBox('Stop frequency must be greater that start',
                          'Warning', wx.OK | wx.ICON_WARNING)
            return

        self.__get_controls()
        self.graph.clear_plots()

        self.devicesRtl = self.__refresh_devices()
        if len(self.devicesRtl) == 0:
            wx.MessageBox('No devices found',
                          'Error', wx.OK | wx.ICON_ERROR)
        else:
            self.spectrum.clear()
            self.location.clear()
            self.__scan_start()

    def __on_stop(self, _event):
        self.stopScan = True
        self.stopAtEnd = False
        self.__scan_stop()

    def __on_stop_end(self, _event):
        self.stopAtEnd = True

    def __on_range_lim(self, _event):
        xmin, xmax = self.graph.get_axes().get_xlim()
        xmin = int(xmin)
        xmax = math.ceil(xmax)
        if xmax < xmin + 1:
            xmax = xmin + 1
        self.settings.start = xmin
        self.settings.stop = xmax
        self.__set_controls()

    def __on_points_lim(self, _event):
        self.settings.pointsLimit = self.popupMenuPointsLim.IsChecked()
        self.__set_plot(self.spectrum, self.settings.annotate)

    def __on_motion(self, event):
        xpos = event.xdata
        ypos = event.ydata
        text = ""
        if xpos is None or ypos is  None or  len(self.spectrum) == 0:
            return

        if self.settings.display == Display.PLOT:
            timeStamp = max(self.spectrum)
            spectrum = self.spectrum[timeStamp]
        elif self.settings.display == Display.SPECT:
            timeStamp = num2epoch(ypos)
            if timeStamp in self.spectrum:
                spectrum = self.spectrum[timeStamp]
            else:
                nearest = min(self.spectrum.keys(),
                              key=lambda k: abs(k - timeStamp))
                spectrum = self.spectrum[nearest]
        else:
            spectrum = None

        if spectrum is not None and len(spectrum) > 0:
            x = min(spectrum.keys(), key=lambda freq: abs(freq - xpos))
            if xpos <= max(spectrum.keys(), key=float):
                y = spectrum[x]
                text = "{0:.6f} MHz, {1: .2f} dB/Hz".format(x, y)
            else:
                text = "{0:.6f} MHz".format(xpos)

        self.status.SetStatusText(text, 1)

    def __on_event(self, event):
        status = event.data.get_status()
        freq = event.data.get_arg1()
        data = event.data.get_arg2()
        if status == Event.STARTING:
            self.status.set_general("Starting")
        elif status == Event.STEPS:
            self.stepsTotal = (freq + 1) * 2
            self.steps = self.stepsTotal
            self.status.set_progress(0)
            self.status.show_progress()
        elif status == Event.CAL:
            self.__auto_cal(Cal.DONE)
        elif status == Event.INFO:
            if self.threadScan is not None:
                self.sdr = self.threadScan.get_sdr()
                if data is not None:
                    self.devicesRtl[self.settings.indexRtl].tuner = data
                    self.scanInfo.tuner = data
        elif status == Event.DATA:
            self.__saved(False)
            cal = self.devicesRtl[self.settings.indexRtl].calibration
            self.pool.apply_async(anaylse_data,
                                  (freq, data, cal,
                                   self.settings.nfft,
                                   self.settings.overlap,
                                   self.settings.winFunc),
                                  callback=self.__on_process_done)
            self.__progress()
        elif status == Event.STOPPED:
            self.__cleanup()
            self.status.set_general("Stopped")
        elif status == Event.FINISHED:
            self.threadScan = None
        elif status == Event.ERROR:
            self.__cleanup()
            self.status.set_general("Error: {0}".format(data))
            if self.dlgCal is not None:
                self.dlgCal.Destroy()
                self.dlgCal = None
        elif status == Event.PROCESSED:
            offset = self.settings.devicesRtl[self.settings.indexRtl].offset
            if self.settings.alert:
                alert = self.settings.alertLevel
            else:
                alert = None
            Thread(target=update_spectrum, name='Update',
                   args=(self, self.lock, self.settings.start,
                         self.settings.stop, freq,
                         data, offset, self.spectrum,
                         not self.settings.retainScans,
                         alert)).start()
        elif status == Event.LEVEL:
            wx.Bell()
        elif status == Event.UPDATED:
            if data and self.settings.liveUpdate:
                self.__set_plot(self.spectrum,
                                self.settings.annotate and \
                                self.settings.retainScans and \
                                self.settings.mode == Mode.CONTIN)
            self.__progress()
        elif status == Event.DRAW:
            self.graph.draw()
        elif status == Event.VER_UPD:
            self.__update_checked(True, freq, data)
        elif status == Event.VER_NOUPD:
            self.__update_checked(False)
        elif status == Event.VER_UPDFAIL:
            self.__update_checked(failed=True)
        elif status == Event.LOC_WARN:
            self.status.set_info("GPS: {0}".format(data))
        elif status == Event.LOC:
            if self.scanInfo is not None:
                if data[0] and data[1]:
                    self.scanInfo.lat = str(data[0])
                    self.scanInfo.lon = str(data[1])
                    if len(self.spectrum) > 0:
                        self.location[max(self.spectrum)] = (data[0],
                                                             data[1],
                                                             data[2])

        wx.YieldIfNeeded()

    def __on_process_done(self, data):
        timeStamp, freq, scan = data
        post_event(self, EventThread(Event.PROCESSED, freq,
                                             (timeStamp, scan)))

    def __auto_cal(self, status):
        freq = self.dlgCal.get_arg1()
        if self.dlgCal is not None:
            if status == Cal.START:
                self.spinCtrlStart.SetValue(int(freq))
                self.spinCtrlStop.SetValue(math.ceil(freq))
                self.oldCal = self.devicesRtl[self.settings.indexRtl].calibration
                self.devicesRtl[self.settings.indexRtl].calibration = 0
                self.__get_controls()
                self.spectrum.clear()
                self.location.clear()
                if not self.__scan_start(isCal=True):
                    self.dlgCal.reset_cal()
            elif status == Cal.DONE:
                ppm = self.__calc_ppm(freq)
                self.dlgCal.set_cal(ppm)
                self.__set_control_state(True)
            elif status == Cal.OK:
                self.devicesRtl[self.settings.indexRtl].calibration = self.dlgCal.get_cal()
                self.settings.calFreq = freq
                self.dlgCal = None
            elif status == Cal.CANCEL:
                self.dlgCal = None
                if len(self.devicesRtl) > 0:
                    self.devicesRtl[self.settings.indexRtl].calibration = self.oldCal

    def __calc_ppm(self, freq):
        with self.lock:
            timeStamp = max(self.spectrum)
            spectrum = self.spectrum[timeStamp].copy()

            for x, y in spectrum.iteritems():
                spectrum[x] = (((x - freq) * (x - freq)) + 1) * y
                peak = max(spectrum, key=spectrum.get)

        return ((freq - peak) / freq) * 1e6

    def __scan_start(self, isCal=False):
        if self.settings.mode == Mode.SINGLE:
            if self.__save_warn(Warn.SCAN):
                return False

        if not self.threadScan:
            self.__set_control_state(False)
            samples = calc_samples(self.settings.dwell)
            self.status.set_info('')
            self.scanInfo.setFromSettings(self.settings)
            time = datetime.datetime.utcnow().replace(microsecond=0)
            self.scanInfo.time = time.isoformat() + "Z"
            self.scanInfo.lat = None
            self.scanInfo.lon = None
            self.scanInfo.desc = ''
            self.stopAtEnd = False
            self.stopScan = False
            self.threadScan = ThreadScan(self, self.sdr, self.settings,
                                         self.settings.indexRtl, samples, isCal)
            self.filename = "Scan {0:.1f}-{1:.1f}MHz".format(self.settings.start,
                                                            self.settings.stop)
            self.graph.set_plot_title()

            if self.settings.gps:
                if self.threadLocation and self.threadLocation.isAlive():
                    self.threadLocation.stop()
                    self.threadLocation.join()
                device = self.settings.devicesGps[self.settings.indexGps]
                self.threadLocation = ThreadLocation(self, device)

            return True

    def __scan_stop(self):
        if self.threadScan:
            self.status.set_general("Stopping")
            self.threadScan.abort()
            self.threadScan.join()
        self.threadScan = None
        if self.threadLocation and self.threadLocation.isAlive():
            self.threadLocation.stop()
            self.threadLocation.join()
        self.threadLocation = None
        if self.sdr is not None:
            self.sdr.close()
        self.__set_control_state(True)

    def __progress(self):
        self.steps -= 1
        if self.steps > 0 and not self.stopScan:
            self.status.set_progress((self.stepsTotal - self.steps) * 100
                    / self.stepsTotal)
            self.status.show_progress()
            self.status.set_general("Scanning")
        else:
            self.status.hide_progress()
            self.__set_plot(self.spectrum, self.settings.annotate)
            if self.stopScan:
                self.status.set_general("Stopped")
                self.__cleanup()
            elif self.settings.mode == Mode.SINGLE:
                self.status.set_general("Finished")
                self.__cleanup()
            else:
                if self.settings.mode == Mode.CONTIN:
                    if self.dlgCal is None and not self.stopAtEnd:
                        self.__limit_spectrum()
                        self.__scan_start()
                    else:
                        self.status.set_general("Stopped")
                        self.__cleanup()

    def __cleanup(self):
        if self.sdr is not None:
            self.sdr.close()
            self.sdr = None
        if self.threadLocation and self.threadLocation.isAlive():
            self.threadLocation.stop()
            self.threadLocation.join()
        self.threadLocation = None

        self.status.hide_progress()
        self.steps = 0
        self.threadScan = None
        self.__set_control_state(True)
        self.stopAtEnd = False
        self.stopScan = True

    def __remove_last(self, data):
        while len(data) >= self.settings.retainMax:
            timeStamp = min(data)
            del data[timeStamp]

    def __limit_spectrum(self):
        with self.lock:
            self.__remove_last(self.spectrum)
            self.__remove_last(self.location)

    def __saved(self, isSaved):
        self.isSaved = isSaved
        title = "RTLSDR Scanner - " + self.filename
        if not isSaved:
            title += "*"
        self.SetTitle(title)

    def __set_plot(self, spectrum, annotate):
        if len(spectrum) > 0:
            total = count_points(spectrum)
            if total > 0:
                spectrum = sort_spectrum(spectrum)
                extent = Extent(spectrum)
                self.graph.set_plot(spectrum,
                                    self.settings.pointsLimit,
                                    self.settings.pointsMax,
                                    extent, annotate)
        else:
            self.graph.clear_plots()

    def __set_control_state(self, state):
        hasDevices = len(self.devicesRtl) > 0
        self.spinCtrlStart.Enable(state)
        self.spinCtrlStop.Enable(state)
        self.controlGain.Enable(state)
        self.choiceMode.Enable(state)
        self.choiceDwell.Enable(state)
        self.choiceNfft.Enable(state)
        self.buttonStart.Enable(state and hasDevices)
        self.buttonStop.Enable(not state and hasDevices)
        self.menuNew.Enable(state)
        self.menuOpen.Enable(state)
        self.menuSave.Enable(state and len(self.spectrum) > 0)
        self.menuExportScan.Enable(state and len(self.spectrum) > 0)
        self.menuExportImage.Enable(state)
        self.menuExportGeo.Enable(state and len(self.spectrum) > 0 \
                                  and len(self.location) > 0)
        self.menuPage.Enable(state)
        self.menuPreview.Enable(state)
        self.menuPrint.Enable(state)
        self.menuStart.Enable(state)
        self.menuStop.Enable(not state)
        self.menuPref.Enable(state)
        self.menuAdvPref.Enable(state)
        self.menuDevicesRtl.Enable(state)
        self.menuDevicesGps.Enable(state)
        self.menuReset.Enable(state)
        self.menuCal.Enable(state)
        self.popupMenuStop.Enable(not state)
        self.popupMenuStart.Enable(state)
        if self.settings.mode == Mode.CONTIN:
            self.menuStopEnd.Enable(not state)
            self.popupMenuStopEnd.Enable(not state)
        else:
            self.menuStopEnd.Enable(False)
            self.popupMenuStopEnd.Enable(False)
        self.popupMenuRangeLim.Enable(state)

    def __set_controls(self):
        self.spinCtrlStart.SetValue(self.settings.start)
        self.spinCtrlStop.SetValue(self.settings.stop)
        self.choiceMode.SetSelection(MODE[1::2].index(self.settings.mode))
        dwell = calc_real_dwell(self.settings.dwell)
        self.choiceDwell.SetSelection(DWELL[1::2].index(dwell))
        self.choiceNfft.SetSelection(NFFT.index(self.settings.nfft))
        self.choiceDisplay.SetSelection(DISPLAY[1::2].index(self.settings.display))

    def __set_gain_control(self):
        grid = self.controlGain.GetContainingSizer()
        if len(self.devicesRtl) > 0:
            self.controlGain.Destroy()
            device = self.devicesRtl[self.settings.indexRtl]
            if device.isDevice:
                gains = device.get_gains_str()
                self.controlGain = wx.Choice(self.toolbar,
                                             choices=gains)
                gain = device.get_closest_gain_str(device.gain)
                self.controlGain.SetStringSelection(gain)
            else:
                self.controlGain = NumCtrl(self.toolbar, integerWidth=3,
                                           fractionWidth=1)
                font = self.controlGain.GetFont()
                dc = wx.WindowDC(self.controlGain)
                dc.SetFont(font)
                size = dc.GetTextExtent('####.#')
                self.controlGain.SetMinSize((size[0] * 1.2, -1))
                self.controlGain.SetValue(device.gain)

            grid.Add(self.controlGain, pos=(1, 7), flag=wx.ALIGN_CENTER)
            grid.Layout()

    def __get_controls(self):
        self.settings.start = self.spinCtrlStart.GetValue()
        self.settings.stop = self.spinCtrlStop.GetValue()
        self.settings.mode = MODE[1::2][self.choiceMode.GetSelection()]
        self.settings.dwell = DWELL[1::2][self.choiceDwell.GetSelection()]
        self.settings.nfft = NFFT[self.choiceNfft.GetSelection()]
        self.settings.display = DISPLAY[1::2][self.choiceDisplay.GetSelection()]

        if len(self.devicesRtl) > 0:
            device = self.devicesRtl[self.settings.indexRtl]
            try:
                if device.isDevice:
                    device.gain = float(self.controlGain.GetStringSelection())
                else:
                    device.gain = self.controlGain.GetValue()
            except ValueError:
                device.gain = 0

    def __save_warn(self, warnType):
        if self.settings.saveWarn and not self.isSaved:
            dlg = DialogSaveWarn(self, warnType)
            code = dlg.ShowModal()
            if code == wx.ID_YES:
                self.__on_save(None)
                if self.isSaved:
                    return False
                else:
                    return True
            elif code == wx.ID_NO:
                return False
            else:
                return True

        return False

    def __update_check(self):
        local = get_version_timestamp(True)
        try:
            remote = get_version_timestamp_repo()
        except IOError:
            post_event(self, EventThread(Event.VER_UPDFAIL))
            return

        if remote > local:
            post_event(self, EventThread(Event.VER_UPD, local, remote))
        else:
            post_event(self, EventThread(Event.VER_NOUPD))

    def __update_checked(self, updateFound=False, local=None, remote=None,
                       failed=False):
        self.threadUpdate = None
        self.status.set_general("")
        if failed:
            icon = wx.ICON_ERROR
            message = "Update check failed"
        else:
            icon = wx.ICON_INFORMATION
            if updateFound:
                message = "Update found\n\n"
                message += "Local: " + time.strftime('%c',
                                                     time.localtime(local))
                message += "\nRemote: " + time.strftime('%c',
                                                        time.localtime(remote))
            else:
                message = "No updates found"

        dlg = wx.MessageDialog(self, message, "Update",
                               wx.OK | icon)
        dlg.ShowModal()
        dlg.Destroy()

    def __refresh_devices(self):
        self.settings.devicesRtl = get_devices_rtl(self.devicesRtl, self.status)
        if self.settings.indexRtl > len(self.devicesRtl) - 1:
            self.settings.indexRtl = 0
        self.settings.save()
        return self.settings.devicesRtl

    def __wait_background(self):
        self.Disconnect(-1, -1, EVENT_THREAD, self.__on_event)
        if self.threadScan:
            self.threadScan.abort()
            self.threadScan.join()
            self.threadScan = None
        self.pool.close()
        self.pool.join()

    def open(self, dirname, filename):
        if not os.path.exists(os.path.join(dirname, filename)):
            wx.MessageBox('File not found',
                          'Error', wx.OK | wx.ICON_ERROR)
            return

        self.filename = os.path.splitext(filename)[0]
        self.settings.dirScans = dirname
        self.status.set_general("Opening: {0}".format(filename))

        self.scanInfo, spectrum, location = open_plot(dirname, filename)

        if len(spectrum) > 0:
            self.scanInfo.setToSettings(self.settings)
            self.spectrum = spectrum
            self.location = location
            self.__saved(True)
            self.__set_controls()
            self.__set_control_state(True)
            self.__set_plot(spectrum, self.settings.annotate)
            self.graph.scale_plot(True)
            self.status.set_general("Finished")
            self.settings.fileHistory.AddFileToHistory(os.path.join(dirname,
                                                                    filename))
        else:
            self.status.set_general("Open failed")


if __name__ == '__main__':
    print 'Please run rtlsdr_scan.py'
    exit(1)

########NEW FILE########
__FILENAME__ = misc
#
# rtlsdr_scan
#
# http://eartoearoak.com/software/rtlsdr-scanner
#
# Copyright 2012 - 2014 Al Brown
#
# A frequency scanning GUI for the OsmoSDR rtl-sdr library at
# http://sdr.osmocom.org/trac/wiki/rtl-sdr
#
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import math
import os
import sys
import time
import urllib

from matplotlib import cm
from matplotlib.colors import LinearSegmentedColormap
import serial.tools.list_ports
import wx

from constants import SAMPLE_RATE, TIMESTAMP_FILE


class ValidatorCoord(wx.PyValidator):
    def __init__(self, isLat):
        wx.PyValidator.__init__(self)
        self.isLat = isLat

    def Validate(self, _window):
        textCtrl = self.GetWindow()
        text = textCtrl.GetValue()
        if len(text) == 0 or text == '-' or text.lower() == 'unknown':
            textCtrl.SetForegroundColour("black")
            textCtrl.Refresh()
            return True

        value = None
        try:
            value = float(text)
            if self.isLat and (value < -90 or value > 90):
                raise ValueError()
            elif value < -180 or value > 180:
                raise ValueError()
        except ValueError:
            textCtrl.SetForegroundColour("red")
            textCtrl.SetFocus()
            textCtrl.Refresh()
            return False

        textCtrl.SetForegroundColour("black")
        textCtrl.Refresh()
        return True

    def TransferToWindow(self):
        return True

    def TransferFromWindow(self):
        return True

    def Clone(self):
        return ValidatorCoord(self.isLat)


def level_to_db(level):
    return 10 * math.log10(level)


def db_to_level(dB):
    return math.pow(10, dB / 10.0)


def next_2_to_pow(val):
    val -= 1
    val |= val >> 1
    val |= val >> 2
    val |= val >> 4
    val |= val >> 8
    val |= val >> 16
    return val + 1


def calc_samples(dwell):
    samples = dwell * SAMPLE_RATE
    samples = next_2_to_pow(int(samples))
    return samples


def calc_real_dwell(dwell):
    samples = calc_samples(dwell)
    dwellReal = samples / SAMPLE_RATE
    return (int)(dwellReal * 1000.0) / 1000.0


def nearest(value, values):
    offset = [abs(value - v) for v in values]
    return values[offset.index(min(offset))]


def format_time(timeStamp, withDate=False):
    if timeStamp <= 1:
        return 'Unknown'

    if withDate:
        return time.strftime('%c', time.localtime(timeStamp))

    return time.strftime('%H:%M:%S', time.localtime(timeStamp))


def load_bitmap(name):
    scriptDir = os.path.dirname(os.path.realpath(sys.argv[0]))
    if(os.path.isdir(scriptDir + '/res')):
        resDir = os.path.normpath(scriptDir + '/res')
    else:
        resDir = os.path.normpath(scriptDir + '/../res')

    return wx.Bitmap(resDir + '/' + name + '.png', wx.BITMAP_TYPE_PNG)


def add_colours():
    r = {'red':     ((0.0, 1.0, 1.0),
                     (1.0, 1.0, 1.0)),
         'green':   ((0.0, 0.0, 0.0),
                     (1.0, 0.0, 0.0)),
         'blue':   ((0.0, 0.0, 0.0),
                         (1.0, 0.0, 0.0))
        }
    g = {'red':     ((0.0, 0.0, 0.0),
                     (1.0, 0.0, 0.0)),
         'green':   ((0.0, 1.0, 1.0),
                     (1.0, 1.0, 1.0)),
         'blue':    ((0.0, 0.0, 0.0),
                     (1.0, 0.0, 0.0))
        }
    b = {'red':     ((0.0, 0.0, 0.0),
                     (1.0, 0.0, 0.0)),
         'green':   ((0.0, 0.0, 0.0),
                     (1.0, 0.0, 0.0)),
         'blue':    ((0.0, 1.0, 1.0),
                     (1.0, 1.0, 1.0))
        }

    rMap = LinearSegmentedColormap('red_map', r)
    gMap = LinearSegmentedColormap('red_map', g)
    bMap = LinearSegmentedColormap('red_map', b)
    cm.register_cmap(name=' Pure Red', cmap=rMap)
    cm.register_cmap(name=' Pure Green', cmap=gMap)
    cm.register_cmap(name=' Pure Blue', cmap=bMap)


def get_colours():
    colours = [colour for colour in cm.cmap_d]
    colours.sort()

    return colours


def set_version_timestamp():
    scriptDir = os.path.dirname(os.path.realpath(sys.argv[0]))
    timeStamp = str(int(time.time()))
    f = open(scriptDir + '/' + TIMESTAMP_FILE, 'w')
    f.write(timeStamp)
    f.close()


def get_version_timestamp(asSeconds=False):
    scriptDir = os.path.dirname(os.path.realpath(sys.argv[0]))
    f = open(scriptDir + '/' + TIMESTAMP_FILE, 'r')
    timeStamp = int(f.readline())
    f.close()
    if asSeconds:
        return timeStamp
    else:
        return format_time(timeStamp, True)


def get_version_timestamp_repo():
    f = urllib.urlopen('https://raw.github.com/EarToEarOak/RTLSDR-Scanner/master/src/version-timestamp')
    timeStamp = int(f.readline())
    f.close()
    return timeStamp


def close_modeless():
    for child in wx.GetTopLevelWindows():
        if child.Title == 'Configure subplots':
            child.Close()


def get_serial_ports():
    ports = [port[0] for port in serial.tools.list_ports.comports()]
    if len(ports) == 0:
        if os.name == 'nt':
            ports.append('COM1')
        else:
            ports.append('/dev/ttyS0')

    return ports


if __name__ == '__main__':
    print 'Please run rtlsdr_scan.py'
    exit(1)

########NEW FILE########
__FILENAME__ = plot
#
# rtlsdr_scan
#
# http://eartoearoak.com/software/rtlsdr-scanner
#
# Copyright 2012 - 2014 Al Brown
#
# A frequency scanning GUI for the OsmoSDR rtl-sdr library at
# http://sdr.osmocom.org/trac/wiki/rtl-sdr
#
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from collections import OrderedDict
import threading

from matplotlib import patheffects
import matplotlib
from matplotlib.cm import ScalarMappable
from matplotlib.collections import LineCollection, PolyCollection
from matplotlib.colorbar import ColorbarBase
from matplotlib.colors import Normalize
from matplotlib.gridspec import GridSpec
from matplotlib.lines import Line2D
from matplotlib.text import Text
from matplotlib.ticker import ScalarFormatter, AutoMinorLocator
import numpy

from constants import Markers, PlotFunc
from events import EventThread, Event, post_event
from spectrum import Measure


class Plotter():
    def __init__(self, notify, figure, settings):
        self.notify = notify
        self.figure = figure
        self.settings = settings
        self.colourMap = self.settings.colourMap
        self.axes = None
        self.bar = None
        self.barBase = None
        self.threadPlot = None
        self.extent = None
        self.lines = {}
        self.labels = {}
        self.overflowLabels = {}
        self.overflow = {'left': [],
                         'right': [],
                         'top': [],
                         'bottom': []}

        self.__setup_plot()
        self.set_grid(self.settings.grid)

    def __setup_plot(self):
        formatter = ScalarFormatter(useOffset=False)

        gs = GridSpec(1, 2, width_ratios=[9.5, 0.5])

        self.axes = self.figure.add_subplot(gs[0],
                                            axisbg=self.settings.background)
        self.axes.set_xlabel("Frequency (MHz)")
        self.axes.set_ylabel('Level ($\mathsf{dB/\sqrt{Hz}}$)')
        self.axes.xaxis.set_major_formatter(formatter)
        self.axes.yaxis.set_major_formatter(formatter)
        self.axes.xaxis.set_minor_locator(AutoMinorLocator(10))
        self.axes.yaxis.set_minor_locator(AutoMinorLocator(10))
        self.axes.set_xlim(self.settings.start, self.settings.stop)
        self.axes.set_ylim(-50, 0)

        self.bar = self.figure.add_subplot(gs[1])
        norm = Normalize(vmin=-50, vmax=0)
        self.barBase = ColorbarBase(self.bar, norm=norm)
        self.set_colourmap_use(self.settings.colourMapUse)

        self.__setup_measure()
        self.__setup_overflow()
        self.hide_measure()

    def __setup_measure(self):
        dashesAvg = [4, 5, 1, 5, 1, 5]
        dashesGM = [5, 5, 5, 5, 1, 5, 1, 5]
        dashesHalf = [1, 5, 5, 5, 5, 5]
        self.lines[Markers.MIN] = Line2D([0, 0], [0, 0], linestyle='--',
                                         color='black')
        self.lines[Markers.MAX] = Line2D([0, 0], [0, 0], linestyle='-.',
                                         color='black')
        self.lines[Markers.AVG] = Line2D([0, 0], [0, 0], dashes=dashesAvg,
                                         color='magenta')
        self.lines[Markers.GMEAN] = Line2D([0, 0], [0, 0], dashes=dashesGM,
                                           color='green')
        self.lines[Markers.HP] = Line2D([0, 0], [0, 0], dashes=dashesHalf,
                                        color='purple')
        self.lines[Markers.HFS] = Line2D([0, 0], [0, 0], dashes=dashesHalf,
                                         color='purple')
        self.lines[Markers.HFE] = Line2D([0, 0], [0, 0], dashes=dashesHalf,
                                         color='purple')
        self.lines[Markers.OP] = Line2D([0, 0], [0, 0], dashes=dashesHalf,
                                        color='#996600')
        self.lines[Markers.OFS] = Line2D([0, 0], [0, 0], dashes=dashesHalf,
                                         color='#996600')
        self.lines[Markers.OFE] = Line2D([0, 0], [0, 0], dashes=dashesHalf,
                                         color='#996600')
        if matplotlib.__version__ >= '1.3':
            effect = patheffects.withStroke(linewidth=3, foreground="w",
                                            alpha=0.75)
            self.lines[Markers.MIN].set_path_effects([effect])
            self.lines[Markers.MAX].set_path_effects([effect])
            self.lines[Markers.AVG].set_path_effects([effect])
            self.lines[Markers.GMEAN].set_path_effects([effect])
            self.lines[Markers.HP].set_path_effects([effect])
            self.lines[Markers.HFS].set_path_effects([effect])
            self.lines[Markers.HFE].set_path_effects([effect])
            self.lines[Markers.OP].set_path_effects([effect])
            self.lines[Markers.OFS].set_path_effects([effect])
            self.lines[Markers.OFE].set_path_effects([effect])

        for line in self.lines.itervalues():
            self.axes.add_line(line)

        bbox = self.axes.bbox
        box = dict(boxstyle='round', fc='white', ec='black', clip_box=bbox)
        self.labels[Markers.MIN] = Text(0, 0, 'Min', fontsize='xx-small',
                                        ha="right", va="bottom", bbox=box,
                                        color='black')
        self.labels[Markers.MAX] = Text(0, 0, 'Max', fontsize='xx-small',
                                        ha="right", va="top", bbox=box,
                                        color='black')
        box['ec'] = 'magenta'
        self.labels[Markers.AVG] = Text(0, 0, 'Mean', fontsize='xx-small',
                                        ha="right", va="center", bbox=box,
                                        color='magenta')
        box['ec'] = 'green'
        self.labels[Markers.GMEAN] = Text(0, 0, 'GMean', fontsize='xx-small',
                                          ha="right", va="center", bbox=box,
                                          color='green')
        box['ec'] = 'purple'
        self.labels[Markers.HP] = Text(0, 0, '-3dB', fontsize='xx-small',
                                       ha="right", va="center", bbox=box,
                                       color='purple')
        self.labels[Markers.HFS] = Text(0, 0, '-3dB Start', fontsize='xx-small',
                                        ha="center", va="top", bbox=box,
                                        color='purple')
        self.labels[Markers.HFE] = Text(0, 0, '-3dB End', fontsize='xx-small',
                                        ha="center", va="top", bbox=box,
                                        color='purple')
        box['ec'] = '#996600'
        self.labels[Markers.OP] = Text(0, 0, 'OBW', fontsize='xx-small',
                                       ha="right", va="center", bbox=box,
                                       color='#996600')
        self.labels[Markers.OFS] = Text(0, 0, 'OBW Start', fontsize='xx-small',
                                        ha="center", va="top", bbox=box,
                                        color='#996600')
        self.labels[Markers.OFE] = Text(0, 0, 'OBW End', fontsize='xx-small',
                                        ha="center", va="top", bbox=box,
                                        color='#996600')

        for label in self.labels.itervalues():
            self.axes.add_artist(label)

    def __setup_overflow(self):
        bbox = self.axes.bbox
        box = dict(boxstyle='round', fc='white', ec='black', alpha=0.5,
                   clip_box=bbox)
        self.overflowLabels['left'] = Text(0, 0.9, '', fontsize='xx-small',
                                           ha="left", va="top", bbox=box,
                                           transform=self.axes.transAxes,
                                           alpha=0.5)
        self.overflowLabels['right'] = Text(1, 0.9, '', fontsize='xx-small',
                                            ha="right", va="top", bbox=box,
                                            transform=self.axes.transAxes,
                                            alpha=0.5)
        self.overflowLabels['top'] = Text(0.9, 1, '', fontsize='xx-small',
                                          ha="right", va="top", bbox=box,
                                          transform=self.axes.transAxes,
                                          alpha=0.5)
        self.overflowLabels['bottom'] = Text(0.9, 0, '', fontsize='xx-small',
                                             ha="right", va="bottom", bbox=box,
                                             transform=self.axes.transAxes,
                                             alpha=0.5)

        for label in self.overflowLabels.itervalues():
            self.axes.add_artist(label)

    def __clear_overflow(self):
        for label in self.overflowLabels:
            self.overflow[label] = []

    def __draw_hline(self, marker, y):
        line = self.lines[marker]
        label = self.labels[marker]
        xLim = self.axes.get_xlim()
        yLim = self.axes.get_ylim()
        if yLim[0] <= y <= yLim[1]:
            line.set_visible(True)
            line.set_xdata([xLim[0], xLim[1]])
            line.set_ydata([y, y])
            self.axes.draw_artist(line)
            label.set_visible(True)
            label.set_position((xLim[1], y))
            self.axes.draw_artist(label)
        elif y is not None and y < yLim[0]:
            self.overflow['bottom'].append(marker)
        elif y is not None and y > yLim[1]:
            self.overflow['top'].append(marker)

    def __draw_vline(self, marker, x):
        line = self.lines[marker]
        label = self.labels[marker]
        yLim = self.axes.get_ylim()
        xLim = self.axes.get_xlim()
        if xLim[0] <= x <= xLim[1]:
            line.set_visible(True)
            line.set_xdata([x, x])
            line.set_ydata([yLim[0], yLim[1]])
            self.axes.draw_artist(line)
            label.set_visible(True)
            label.set_position((x, yLim[1]))
            self.axes.draw_artist(label)
        elif x is not None and x < xLim[0]:
            self.overflow['left'].append(marker)
        elif x is not None and x > xLim[1]:
            self.overflow['right'].append(marker)

    def __draw_overflow(self):
        for pos, overflow in self.overflow.iteritems():
            if len(overflow) > 0:
                text = ''
                for measure in overflow:
                    if len(text) > 0:
                        text += '\n'
                    text += self.labels[measure].get_text()

                label = self.overflowLabels[pos]
                if pos == 'top':
                    textMath = '$\\blacktriangle$\n' + text
                elif pos == 'bottom':
                    textMath = '$\\blacktriangledown$\n' + text
                elif pos == 'left':
                    textMath = '$\\blacktriangleleft$\n' + text
                elif pos == 'right':
                    textMath = '$\\blacktriangleright$\n' + text

                label.set_text(textMath)
                label.set_visible(True)
                self.axes.draw_artist(label)

    def draw_measure(self, measure, show):
        if self.axes.get_renderer_cache() is None:
            return

        self.hide_measure()
        self.__clear_overflow()

        if show[Measure.MIN]:
            y = measure.get_min_p()[1]
            self.__draw_hline(Markers.MIN, y)

        if show[Measure.MAX]:
            y = measure.get_max_p()[1]
            self.__draw_hline(Markers.MAX, y)

        if show[Measure.AVG]:
            y = measure.get_avg_p()
            self.__draw_hline(Markers.AVG, y)

        if show[Measure.GMEAN]:
            y = measure.get_gmean_p()
            self.__draw_hline(Markers.GMEAN, y)

        if show[Measure.HBW]:
            xStart, xEnd, y = measure.get_hpw()
            self.__draw_hline(Markers.HP, y)
            self.__draw_vline(Markers.HFS, xStart)
            self.__draw_vline(Markers.HFE, xEnd)

        if show[Measure.OBW]:
            xStart, xEnd, y = measure.get_obw()
            self.__draw_hline(Markers.OP, y)
            self.__draw_vline(Markers.OFE, xStart)
            self.__draw_vline(Markers.OFE, xEnd)

        self.__draw_overflow()

    def hide_measure(self):
        for line in self.lines.itervalues():
            line.set_visible(False)
        for label in self.labels.itervalues():
            label.set_visible(False)
        for label in self.overflowLabels.itervalues():
            label.set_visible(False)

    def scale_plot(self, force=False):
        if self.extent is not None:
            if self.settings.autoF or force:
                self.axes.set_xlim(self.extent.get_f())
            if self.settings.autoL or force:
                self.axes.set_ylim(self.extent.get_l())
                if self.settings.plotFunc == PlotFunc.VAR and len(self.axes.collections) > 0:
                    norm = self.axes.collections[0].norm
                    self.barBase.set_clim((norm.vmin, norm.vmax))
                else:
                    self.barBase.set_clim(self.extent.get_l())
                    norm = Normalize(vmin=self.extent.get_l()[0],
                                     vmax=self.extent.get_l()[1])
                for collection in self.axes.collections:
                    collection.set_norm(norm)
                try:
                    self.barBase.draw_all()
                except:
                    pass

    def redraw_plot(self):
        if self.figure is not None:
            post_event(self.notify, EventThread(Event.DRAW))

    def get_axes(self):
        return self.axes

    def get_axes_bar(self):
        return self.barBase.ax

    def get_plot_thread(self):
        return self.threadPlot

    def set_title(self, title):
        self.axes.set_title(title, fontsize='medium')

    def set_plot(self, spectrum, extent, annotate=False):
        self.extent = extent
        self.threadPlot = ThreadPlot(self, self.axes, spectrum,
                                     self.extent,
                                     self.colourMap,
                                     self.settings.autoL,
                                     self.settings.lineWidth,
                                     self.barBase,
                                     self.settings.fadeScans,
                                     annotate, self.settings.plotFunc)
        self.threadPlot.start()

    def clear_plots(self):
        children = self.axes.get_children()
        for child in children:
            if child.get_gid() is not None:
                if child.get_gid() == "plot" or child.get_gid() == "peak":
                    child.remove()

    def set_grid(self, on):
        self.axes.grid(on)
        self.redraw_plot()

    def set_colourmap_use(self, use):
        if use:
            colourMap = self.settings.colourMap
        else:
            colourMap = ' Pure Blue'

        self.set_colourmap(colourMap)

    def set_colourmap(self, colourMap):
        self.colourMap = colourMap
        for collection in self.axes.collections:
            collection.set_cmap(colourMap)

        if colourMap.startswith(' Pure'):
            self.bar.set_visible(False)
        else:
            self.bar.set_visible(True)
        self.barBase.set_cmap(colourMap)
        try:
            self.barBase.draw_all()
        except:
            pass

    def close(self):
        self.figure.clear()
        self.figure = None


class ThreadPlot(threading.Thread):
    def __init__(self, parent, axes, data, extent,
                 colourMap, autoL, lineWidth,
                 barBase, fade, annotate, plotFunc):
        threading.Thread.__init__(self)
        self.name = "Plot"
        self.parent = parent
        self.axes = axes
        self.data = data
        self.extent = extent
        self.colourMap = colourMap
        self.autoL = autoL
        self.lineWidth = lineWidth
        self.barBase = barBase
        self.annotate = annotate
        self.fade = fade
        self.plotFunc = plotFunc

    def run(self):
        if self.data is None:
            self.parent.threadPlot = None
            return

        total = len(self.data)
        if total > 0:
            self.parent.clear_plots()

            if self.plotFunc == PlotFunc.NONE:
                peakF, peakL = self.__plot_all()
            elif self.plotFunc == PlotFunc.MIN:
                peakF, peakL = self.__plot_min()
            elif self.plotFunc == PlotFunc.MAX:
                peakF, peakL = self.__plot_max()
            elif self.plotFunc == PlotFunc.AVG:
                peakF, peakL = self.__plot_avg()
            elif self.plotFunc == PlotFunc.VAR:
                peakF, peakL = self.__plot_variance()

            if self.annotate:
                self.__annotate_plot(peakF, peakL)

            self.parent.scale_plot()
            self.parent.redraw_plot()

        self.parent.threadPlot = None

    def __calc_min(self):
        points = OrderedDict()

        for timeStamp in self.data:
            for x, y in self.data[timeStamp].items():
                if x in points:
                    points[x] = min(points[x], y)
                else:
                    points[x] = y

        return points

    def __calc_max(self):
        points = OrderedDict()

        for timeStamp in self.data:
            for x, y in self.data[timeStamp].items():
                if x in points:
                    points[x] = max(points[x], y)
                else:
                    points[x] = y

        return points

    def __plot_all(self):
        total = len(self.data)
        count = 0.0
        for timeStamp in self.data:
            if len(self.data[timeStamp]) < 2:
                self.parent.threadPlot = None
                return None, None

            if self.fade:
                alpha = (total - count) / total
            else:
                alpha = 1

            data = self.data[timeStamp].items()
            peakF, peakL = self.extent.get_peak_fl()

            segments, levels = self.__create_segments(data)
            lc = LineCollection(segments)
            lc.set_array(numpy.array(levels))
            lc.set_norm(self.__get_norm(self.autoL, self.extent))
            lc.set_cmap(self.colourMap)
            lc.set_linewidth(self.lineWidth)
            lc.set_gid('plot')
            lc.set_alpha(alpha)
            self.axes.add_collection(lc)
            count += 1

        return peakF, peakL

    def __plot_min(self):
        points = self.__calc_min()

        return self.__plot_single(points)

    def __plot_max(self):
        points = self.__calc_max()

        return self.__plot_single(points)

    def __plot_avg(self):
        points = OrderedDict()

        for timeStamp in self.data:
            if len(self.data[timeStamp]) < 2:
                return None, None

            for x, y in self.data[timeStamp].items():
                if x in points:
                    points[x] = (points[x] + y) / 2
                else:
                    points[x] = y

        return self.__plot_single(points)

    def __plot_variance(self):
        pointsMin = self.__calc_min()
        pointsMax = self.__calc_max()

        polys = []
        variance = []
        varMin = 1000
        varMax = 0
        lastX = None
        lastYMin = None
        lastYMax = None
        for x in pointsMin.iterkeys():
            if lastX is None:
                lastX = x
            if lastYMin is None:
                lastYMin = pointsMin[x]
            if lastYMax is None:
                lastYMax = pointsMax[x]
            polys.append([[x, pointsMin[x]],
                          [x, pointsMax[x]],
                          [lastX, lastYMax],
                          [lastX, lastYMin],
                          [x, pointsMin[x]]])
            lastX = x
            lastYMin = pointsMin[x]
            lastYMax = pointsMax[x]

            var = pointsMax[x] - pointsMin[x]
            variance.append(var)
            varMin = min(varMin, var)
            varMax = max(varMax, var)

        norm = Normalize(vmin=varMin, vmax=varMax)
        sm = ScalarMappable(norm, self.colourMap)
        colours = sm.to_rgba(variance)

        pc = PolyCollection(polys)
        pc.set_gid('plot')
        pc.set_norm(norm)
        pc.set_color(colours)
        self.axes.add_collection(pc)

        return None, None

    def __plot_single(self, points):
        data = points.items()
        peakF, peakL = max(data, key=lambda item: item[1])

        segments, levels = self.__create_segments(data)
        lc = LineCollection(segments)
        lc.set_array(numpy.array(levels))
        lc.set_norm(self.__get_norm(self.autoL, self.extent))
        lc.set_cmap(self.colourMap)
        lc.set_linewidth(self.lineWidth)
        lc.set_gid('plot')
        self.axes.add_collection(lc)

        return peakF, peakL

    def __create_segments(self, points):
        segments = []
        levels = []

        prev = points[0]
        for point in points:
            segment = [prev, point]
            segments.append(segment)
            levels.append((point[1] + prev[1]) / 2.0)
            prev = point

        return segments, levels

    def __get_norm(self, autoL, extent):
        if autoL:
            vmin, vmax = self.barBase.get_clim()
        else:
            yExtent = extent.get_l()
            vmin = yExtent[0]
            vmax = yExtent[1]

        return Normalize(vmin=vmin, vmax=vmax)

    def __annotate_plot(self, x, y):
        self.__clear_markers()

        if x is None or y is None:
            return

        start, stop = self.axes.get_xlim()
        textX = ((stop - start) / 50.0) + x

        text = '{0:.6f} MHz\n{1:.2f} $\mathsf{{dB/\sqrt{{Hz}}}}$'.format(x, y)
        if matplotlib.__version__ < '1.3':
            self.axes.annotate(text,
                               xy=(x, y), xytext=(textX, y),
                               ha='left', va='top', size='x-small',
                               gid='peak')
            self.axes.plot(x, y, marker='x', markersize=10, color='w',
                           mew=3, gid='peak')
            self.axes.plot(x, y, marker='x', markersize=10, color='r',
                           gid='peak')
        else:
            effect = patheffects.withStroke(linewidth=2, foreground="w",
                                            alpha=0.75)
            self.axes.annotate(text,
                               xy=(x, y), xytext=(textX, y),
                               ha='left', va='top', size='x-small',
                               path_effects=[effect], gid='peak')
            self.axes.plot(x, y, marker='x', markersize=10, color='r',
                           path_effects=[effect], gid='peak')

    def __get_plots(self):
        plots = []
        children = self.axes.get_children()
        for child in children:
            if child.get_gid() is not None:
                if child.get_gid() == "plot":
                    plots.append(child)

        return plots

    def __clear_markers(self):
        children = self.axes.get_children()
        for child in children:
            if child.get_gid() is not None:
                if child.get_gid() == 'peak':
                    child.remove()


if __name__ == '__main__':
    print 'Please run rtlsdr_scan.py'
    exit(1)

########NEW FILE########
__FILENAME__ = plot3d
#
# rtlsdr_scan
#
# http://eartoearoak.com/software/rtlsdr-scanner
#
# Copyright 2012 - 2014 Al Brown
#
# A frequency scanning GUI for the OsmoSDR rtl-sdr library at
# http://sdr.osmocom.org/trac/wiki/rtl-sdr
#
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import threading
import time

from matplotlib import cm, patheffects
import matplotlib
from matplotlib.colorbar import ColorbarBase
from matplotlib.colors import Normalize, hex2color
from matplotlib.dates import DateFormatter
from matplotlib.gridspec import GridSpec
from matplotlib.ticker import ScalarFormatter, AutoMinorLocator

from events import post_event, EventThread, Event
from misc import format_time
from mpl_toolkits.mplot3d import Axes3D  # @UnresolvedImport @UnusedImport
from spectrum import epoch_to_mpl, create_mesh


class Plotter3d():
    def __init__(self, notify, figure, settings):
        self.notify = notify
        self.figure = figure
        self.settings = settings
        self.axes = None
        self.bar = None
        self.barBase = None
        self.plot = None
        self.extent = None
        self.threadPlot = None
        self.wireframe = settings.wireframe
        self.__setup_plot()
        self.set_grid(settings.grid)

    def __setup_plot(self):
        gs = GridSpec(1, 2, width_ratios=[9.5, 0.5])
        self.axes = self.figure.add_subplot(gs[0], projection='3d')

        numformatter = ScalarFormatter(useOffset=False)
        timeFormatter = DateFormatter("%H:%M:%S")

        self.axes.set_xlabel("Frequency (MHz)")
        self.axes.set_ylabel('Time')
        self.axes.set_zlabel('Level ($\mathsf{dB/\sqrt{Hz}}$)')
        colour = hex2color(self.settings.background)
        colour += (1,)
        self.axes.w_xaxis.set_pane_color(colour)
        self.axes.w_yaxis.set_pane_color(colour)
        self.axes.w_zaxis.set_pane_color(colour)
        self.axes.xaxis.set_major_formatter(numformatter)
        self.axes.yaxis.set_major_formatter(timeFormatter)
        self.axes.zaxis.set_major_formatter(numformatter)
        self.axes.xaxis.set_minor_locator(AutoMinorLocator(10))
        self.axes.yaxis.set_minor_locator(AutoMinorLocator(10))
        self.axes.zaxis.set_minor_locator(AutoMinorLocator(10))
        self.axes.set_xlim(self.settings.start, self.settings.stop)
        now = time.time()
        self.axes.set_ylim(epoch_to_mpl(now), epoch_to_mpl(now - 10))
        self.axes.set_zlim(-50, 0)

        self.bar = self.figure.add_subplot(gs[1])
        norm = Normalize(vmin=-50, vmax=0)
        self.barBase = ColorbarBase(self.bar, norm=norm,
                                    cmap=cm.get_cmap(self.settings.colourMap))

    def scale_plot(self, force=False):
        if self.extent is not None and self.plot is not None:
            if self.settings.autoF or force:
                self.axes.set_xlim(self.extent.get_f())
            if self.settings.autoL or force:
                self.axes.set_zlim(self.extent.get_l())
                self.plot.set_clim(self.extent.get_l())
                self.barBase.set_clim(self.extent.get_l())
                try:
                    self.barBase.draw_all()
                except:
                    pass
            if self.settings.autoT or force:
                self.axes.set_ylim(self.extent.get_t())

    def draw_measure(self, *args):
        pass

    def hide_measure(self):
        pass

    def redraw_plot(self):
        if self.figure is not None:
            post_event(self.notify, EventThread(Event.DRAW))

    def get_axes(self):
        return self.axes

    def get_axes_bar(self):
        return self.barBase.ax

    def get_plot_thread(self):
        return self.threadPlot

    def set_title(self, title):
        self.axes.set_title(title, fontsize='medium')

    def set_plot(self, data, extent, annotate=False):
        self.extent = extent
        self.threadPlot = ThreadPlot(self, self.axes,
                                     data, self.extent,
                                     self.settings.retainMax,
                                     self.settings.colourMap,
                                     self.settings.autoF,
                                     self.barBase,
                                     annotate)
        self.threadPlot.start()

    def clear_plots(self):
        children = self.axes.get_children()
        for child in children:
            if child.get_gid() is not None:
                if child.get_gid() == "plot" or child.get_gid() == "peak":
                    child.remove()

    def set_grid(self, on):
        self.axes.grid(on)
        self.redraw_plot()

    def set_colourmap(self, colourMap):
        if self.plot is not None:
            self.plot.set_cmap(colourMap)
        self.barBase.set_cmap(colourMap)
        try:
            self.barBase.draw_all()
        except:
            pass

    def close(self):
        self.figure.clear()
        self.figure = None


class ThreadPlot(threading.Thread):
    def __init__(self, parent, axes, data, extent, retainMax, colourMap,
                 autoL, barBase, annotate):
        threading.Thread.__init__(self)
        self.name = "Plot"
        self.parent = parent
        self.axes = axes
        self.data = data
        self.extent = extent
        self.retainMax = retainMax
        self.colourMap = colourMap
        self.autoL = autoL
        self.barBase = barBase
        self.annotate = annotate

    def run(self):
        if self.data is None:
            self.parent.threadPlot = None
            return

        total = len(self.data)
        if total > 0:
            x, y, z = create_mesh(self.data, True)
            self.parent.clear_plots()

            if self.autoL:
                vmin, vmax = self.barBase.get_clim()
            else:
                zExtent = self.extent.get_l()
                vmin = zExtent[0]
                vmax = zExtent[1]
            if self.parent.wireframe:
                self.parent.plot = \
                self.axes.plot_wireframe(x, y, z,
                                         rstride=1, cstride=1,
                                         linewidth=0.1,
                                         cmap=cm.get_cmap(self.colourMap),
                                         gid='plot',
                                         antialiased=True,
                                         alpha=1)
            else:
                self.parent.plot = \
                self.axes.plot_surface(x, y, z,
                                       rstride=1, cstride=1,
                                       vmin=vmin, vmax=vmax,
                                       linewidth=0,
                                       cmap=cm.get_cmap(self.colourMap),
                                       gid='plot',
                                       antialiased=True,
                                       alpha=1)

            if self.annotate:
                self.__annotate_plot()

        if total > 0:
            self.parent.scale_plot()
            self.parent.redraw_plot()

        self.parent.threadPlot = None

    def __annotate_plot(self):
        f, l, t = self.extent.get_peak_flt()
        when = format_time(t)
        tPos = epoch_to_mpl(t)

        text = '{0:.6f} MHz\n{1:.2f} $\mathsf{{dB/\sqrt{{Hz}}}}$\n{2}'.format(f, l, when)
        if(matplotlib.__version__ < '1.3'):
            self.axes.text(f, tPos, l,
                           text,
                           ha='left', va='bottom', size='x-small', gid='peak')
            self.axes.plot([f], [tPos], [l], marker='x', markersize=10,
                           mew=3, color='w', gid='peak')
            self.axes.plot([f], [tPos], [l], marker='x', markersize=10,
                           color='r', gid='peak')
        else:
            effect = patheffects.withStroke(linewidth=2, foreground="w",
                                            alpha=0.75)
            self.axes.text(f, tPos, l,
                           text,
                           ha='left', va='bottom', size='x-small', gid='peak',
                           path_effects=[effect])
            self.axes.plot([f], [tPos], [l], marker='x', markersize=10,
                           color='r', gid='peak', path_effects=[effect])

    def __clear_markers(self):
        children = self.axes.get_children()
        for child in children:
            if child.get_gid() is not None:
                if child.get_gid() == 'peak':
                    child.remove()


if __name__ == '__main__':
    print 'Please run rtlsdr_scan.py'
    exit(1)

########NEW FILE########
__FILENAME__ = plot_controls
#
# rtlsdr_scan
#
# http://eartoearoak.com/software/rtlsdr-scanner
#
# Copyright 2012 - 2014 Al Brown
#
# A frequency scanning GUI for the OsmoSDR rtl-sdr library at
# http://sdr.osmocom.org/trac/wiki/rtl-sdr
#
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from matplotlib.patches import Rectangle

from plot3d import Plotter3d


class MouseZoom():
    SCALE_STEP = 1.3

    def __init__(self, toolbar, figure=None, plot=None, callbackHide=None):
        if figure is None:
            if isinstance(plot, Plotter3d):
                return

            self.axes = plot.get_axes()
            self.figure = self.axes.get_figure()
        else:
            self.axes = figure.get_axes()[0]
            self.figure = figure

        self.callbackHide = callbackHide
        self.toolbar = toolbar
        self.figure.canvas.mpl_connect('scroll_event', self.__zoom)

    def __zoom(self, event):
        if event.button == 'up':
            scale = 1 / self.SCALE_STEP
        elif event.button == 'down':
            scale = self.SCALE_STEP
        else:
            return

        if self.callbackHide is not None:
            self.callbackHide()
        self.toolbar.clear_auto()

        if self.toolbar._views.empty():
            self.toolbar.push_current()

        xLim = self.axes.get_xlim()
        yLim = self.axes.get_ylim()
        xPos = event.xdata
        yPos = event.ydata
        if not yLim[0] <= yPos <= yLim[1]:
            yPos = yLim[0] + (yLim[1] - yLim[0]) / 2

        xPosRel = (xLim[1] - xPos) / (xLim[1] - xLim[0])
        yPosRel = (yLim[1] - yPos) / (yLim[1] - yLim[0])

        newXLim = (xLim[1] - xLim[0]) * scale
        newYLim = (yLim[1] - yLim[0]) * scale
        xStart = xPos - newXLim * (1 - xPosRel)
        xStop = xPos + newXLim * xPosRel
        yStart = yPos - newYLim * (1 - yPosRel)
        yStop = yPos + newYLim * yPosRel

        self.axes.set_xlim([xStart, xStop])
        self.axes.set_ylim([yStart, yStop])

        self.toolbar.push_current()
        self.figure.canvas.draw()


class MouseSelect():
    def __init__(self, plot, callbackPre, callbackPost):
        self.selector = None
        if not isinstance(plot, Plotter3d):
            axes = plot.get_axes()
            self.selector = RangeSelector(axes, callbackPre, callbackPost)

    def draw(self, xMin, xMax):
        if self.selector is not None:
            self.selector.draw(xMin, xMax)

    def hide(self):
        if self.selector is not None:
            self.selector.hide()

    def clear(self):
        if self.selector is not None:
            self.selector.clear()


# Based on http://matplotlib.org/1.3.1/users/event_handling.html
class RangeSelector():
    def __init__(self, axes, callbackPre, callbackPost):
        self.axes = axes
        self.callbackPre = callbackPre
        self.callbackPost = callbackPost

        self.eventPressed = None
        self.eventReleased = None

        props = dict(facecolor='red', edgecolor='white', alpha=0.25, fill=True,
                     zorder=100, gid='range')
        self.rect = Rectangle((0, 0), 0, 0, **props)
        self.axes.add_patch(self.rect)

        figure = self.axes.get_figure()
        figure.canvas.mpl_connect('motion_notify_event', self.__on_move)
        figure.canvas.mpl_connect('button_press_event', self.__on_press)
        figure.canvas.mpl_connect('button_release_event', self.__on_release)

    def __on_press(self, event):
        if self.__skip_event(event):
            return

        self.eventPressed = event
        self.callbackPre()
        self.rect.set_visible(True)
        return

    def __on_move(self, event):
        if self.eventPressed is None or self.__skip_event(event):
            return

        xMin = self.eventPressed.xdata
        xMax = event.xdata
        if xMin > xMax:
            xMin, xMax = xMax, xMin
        self.callbackPost(xMin, xMax)

        return

    def __on_release(self, event):
        if self.eventPressed is None or self.__skip_event(event):
            return

        self.eventReleased = event
        xMin, xMax = self.eventPressed.xdata, self.eventReleased.xdata
        if xMin > xMax:
            xMin, xMax = xMax, xMin
        self.callbackPost(xMin, xMax)
        self.eventPressed = None
        self.eventReleased = None
        return

    def __skip_event(self, event):
        if event.button != 2:
            return True

        if self.eventPressed is None:
            return event.inaxes != self.axes

        if event.button == self.eventPressed.button and event.inaxes != self.axes:
            transform = self.axes.transData.inverted()
            (x, _y) = transform.transform_point((event.x, event.y))
            x0, x1 = self.axes.get_xbound()
            x = max(x0, x)
            x = min(x1, x)
            event.xdata = x
            return False

        return (event.inaxes != self.axes or
                event.button != self.eventPressed.button)

    def draw(self, xMin, xMax):
        self.rect.set_visible(True)
        yMin, yMax = self.axes.get_ylim()
        height = yMax - yMin
        yMin -= height * 100.0
        yMax += height * 100.0
        self.rect.set_x(xMin)
        self.rect.set_y(yMin)
        self.rect.set_width(xMax - xMin)
        self.rect.set_height(yMax - yMin)

        if self.axes._cachedRenderer is not None:
            self.axes.draw_artist(self.rect)

    def hide(self):
        self.rect.set_visible(False)

    def clear(self):
        self.rect.set_visible(False)
        canvas = self.axes.get_figure().canvas
        canvas.draw()


if __name__ == '__main__':
    print 'Please run rtlsdr_scan.py'
    exit(1)

########NEW FILE########
__FILENAME__ = printer
#
# rtlsdr_scan
#
# http://eartoearoak.com/software/rtlsdr-scanner
#
# Copyright 2012 - 2014 Al Brown
#
# A frequency scanning GUI for the OsmoSDR rtl-sdr library at
# http://sdr.osmocom.org/trac/wiki/rtl-sdr
#
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from PIL import Image
import matplotlib
from matplotlib.backends.backend_agg import FigureCanvasAgg
import wx


class PrintOut(wx.Printout):
    def __init__(self, graph, filename, pageConfig):
        wx.Printout.__init__(self, title=filename)
        self.figure = graph.get_figure()
        margins = (pageConfig.GetMarginTopLeft().Get()[0],
                   pageConfig.GetMarginTopLeft().Get()[1],
                   pageConfig.GetMarginBottomRight().Get()[0],
                   pageConfig.GetMarginBottomRight().Get()[1])
        self.margins = [v / 25.4 for v in margins]

    def __draw_image(self, sizeInches, ppi):
        oldSize = self.figure.get_size_inches()
        oldDpi = self.figure.get_dpi()
        self.figure.set_size_inches(sizeInches)
        self.figure.set_dpi(ppi)

        canvas = FigureCanvasAgg(self.figure)
        canvas.draw()
        renderer = canvas.get_renderer()
        if matplotlib.__version__ >= '1.2':
            buf = renderer.buffer_rgba()
        else:
            buf = renderer.buffer_rgba(0, 0)
        size = canvas.get_width_height()
        image = Image.frombuffer('RGBA', size, buf, 'raw', 'RGBA', 0, 1)

        self.figure.set_size_inches(oldSize)
        self.figure.set_dpi(oldDpi)

        imageWx = wx.EmptyImage(image.size[0], image.size[1])
        imageWx.SetData(image.convert('RGB').tostring())

        return imageWx

    def GetPageInfo(self):
        return 1, 1, 1, 1

    def HasPage(self, page):
        return page == 1

    def OnPrintPage(self, _page):
        dc = self.GetDC()
        if self.IsPreview():
            ppi = max(self.GetPPIScreen())
            sizePixels = dc.GetSize()
        else:
            ppi = max(self.GetPPIPrinter())
            sizePixels = self.GetPageSizePixels()
        width = (sizePixels[0] / ppi) - self.margins[1] - self.margins[3]
        height = (sizePixels[1] / ppi) - self.margins[0] - self.margins[2]
        sizeInches = (width, height)

        image = self.__draw_image(sizeInches, ppi)
        dc.DrawBitmap(image.ConvertToBitmap(),
                      self.margins[0] * ppi,
                      self.margins[1] * ppi)

        return True

########NEW FILE########
__FILENAME__ = rtlsdr_scan
#! /usr/bin/env python
#
# rtlsdr_scan
#
# http://eartoearoak.com/software/rtlsdr-scanner
#
# Copyright 2012 - 2014 Al Brown
#
# A frequency scanning GUI for the OsmoSDR rtl-sdr library at
# http://sdr.osmocom.org/trac/wiki/rtl-sdr
#
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

try:
    input = raw_input
except:
    pass

try:
    import matplotlib
    matplotlib.interactive(True)
    matplotlib.use('WXAgg')
    import rtlsdr
    import wx
except ImportError as error:
    print 'Import error: {0}'.format(error)
    input('\nError importing libraries\nPress [Return] to exit')
    exit(1)

import argparse
import multiprocessing
import os.path

from cli import Cli
from file import File
from main_window import FrameMain, RtlSdrScanner
from misc import set_version_timestamp


def __arguments():
    parser = argparse.ArgumentParser(prog="rtlsdr_scan.py",
                                     description='''
                                        Scan a range of frequencies and
                                        save the results to a file''')
    parser.add_argument("-s", "--start", help="Start frequency (MHz)",
                        type=int)
    parser.add_argument("-e", "--end", help="End frequency (MHz)", type=int)
    parser.add_argument("-g", "--gain", help="Gain (dB)", type=float, default=0)
    parser.add_argument("-d", "--dwell", help="Dwell time (seconds)",
                        type=float, default=0.1)
    parser.add_argument("-f", "--fft", help="FFT bins", type=int, default=1024)
    parser.add_argument("-l", "--lo", help="Local oscillator offset", type=int,
                        default=0)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-i", "--index", help="Device index (from 0)", type=int,
                       default=0)
    group.add_argument("-r", "--remote", help="Server IP and port", type=str)
    types = File.get_type_pretty(File.Types.SAVE)
    types += File.get_type_pretty(File.Types.PLOT)
    help = 'Output file (' + types + ')'
    parser.add_argument("file", help=help, nargs='?')
    args = parser.parse_args()

    error = None
    isGui = True
    if args.start is not None or args.end is not None:
        if args.start is not None:
            if args.end is not None:
                if args.file is not None:
                    isGui = False
                else:
                    error = "No filename specified"
            else:
                error = "No end frequency specified"
        else:
            error = "No start frequency specified"
    elif args.file is not None:
        args.dirname, args.filename = os.path.split(args.file)

    if error is not None:
        print "Error: {0}".format(error)
        parser.exit(1)

    return isGui, (args)


if __name__ == '__main__':
    multiprocessing.freeze_support()
    pool = multiprocessing.Pool()
    print "RTLSDR Scanner\n"
    if 'rtlsdr_update_timestamp'in os.environ:
        set_version_timestamp()
    isGui, args = __arguments()
    if isGui:
        app = RtlSdrScanner(pool)
        frame = FrameMain("RTLSDR Scanner", pool)
        if args.file is not None:
            frame.open(os.path.abspath(args.dirname), args.filename)
        app.MainLoop()
    else:
        Cli(pool, args)

########NEW FILE########
__FILENAME__ = rtlsdr_scan_diag
#! /usr/bin/env python

#
# rtlsdr_scan_diag
#
# http://eartoearoak.com/software/rtlsdr-scanner
#
# Copyright 2012 - 2014 Al Brown
#
# A frequency scanning GUI for the OsmoSDR rtl-sdr library at
# http://sdr.osmocom.org/trac/wiki/rtl-sdr
#
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from ctypes.util import find_library
import sys

LIBS = [('wx', 'wxPython', 'http://www.wxpython.org/download.php#stable', True, True),
        ('numpy', 'Numpy', 'http://sourceforge.net/projects/numpy/files/NumPy/', True, True),
        ('matplotlib', 'matplotlib', 'http://matplotlib.org/downloads.html', True, True),
        ('serial', 'pySerial', 'https://pypi.python.org/pypi/pyserial', True, True),
        ('rtlsdr', 'pyrtlsdr', 'https://github.com/roger-/pyrtlsdr', False, False)]


def try_import(library):
    try:
        __import__(library)
    except:
        return False

    return True

if __name__ == '__main__':

    try:
        input = raw_input
    except:
        pass

    print('rtlsdr_scan_diag\n')
    print('Tests for missing libraries\n')

    version = sys.version_info
    if(version < (2, 6)):
        print('Warning unsupported version, please use Python 2.6 or greater')

    problem = False

    if not find_library('rtlsdr') and not find_library('librtlsdr'):
        print('librtlsdr not found in path')
        print("Download from 'http://sdr.osmocom.org/trac/wiki/rtl-sdr'")
        print('')
    else:
        platform = sys.platform
        for lib, name, url, package, ports in LIBS:
            if not try_import(lib):
                problem = True
                print('{0} not found'.format(name))
                if platform == 'linux' or platform == 'linux2':
                    if package:
                        print("\tInstall using the system package manager or download from '{0}'".format(url))
                    else:
                        print("\tDownload from '{0}'".format(url))
                elif platform == 'darwin':
                    if ports:
                        print("\tInstall using MacPorts or download from '{0}'".format(url))
                    else:
                        print("\tDownload from '{0}'".format(url))
                else:
                    print("\tDownload from '{0}'".format(url))

                print('')

        if problem:
            print('Problems found, please install the libraries for Python {0}.{1}'.format(version[0], version[1]))
        else:
            print('No problems found')

    input('\nPress [Return]')

########NEW FILE########
__FILENAME__ = rtltcp
#
# rtlsdr_scan
#
# http://eartoearoak.com/software/rtlsdr-scanner
#
# Copyright 2012 - 2014 Al Brown
#
# A frequency scanning GUI for the OsmoSDR rtl-sdr library at
# http://sdr.osmocom.org/trac/wiki/rtl-sdr
#
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import array
import socket
import struct
import threading

import numpy


class RtlTcpCmd():
    SET_FREQ = 0x1
    SET_SAMPLE_RATE = 0x2
    SET_GAIN_MODE = 0x3
    SET_GAIN = 0x4


class RtlTcp():
    def __init__(self, host, port):
        self.host = host
        self.port = port

        self.threadBuffer = None
        self.tuner = 0
        self.rate = 0

        self.__setup()

    def __setup(self):
        self.threadBuffer = ThreadBuffer(self.host, self.port)
        self.__get_header()

    def __get_header(self):
        header = self.threadBuffer.get_header()
        if len(header) == 12:
            if header.startswith('RTL'):
                self.tuner = (ord(header[4]) << 24) | \
                             (ord(header[5]) << 16) | \
                             (ord(header[6]) << 8) | \
                             ord(header[7])

    def __send_command(self, command, data):
        send = array.array('c', '\0' * 5)

        struct.pack_into('>l', send, 1, data)
        send[0] = struct.pack('<b', command)

        self.threadBuffer.sendall(send)

    def __read_raw(self, samples):
        return self.threadBuffer.recv(samples * 2)

    def __raw_to_iq(self, raw):
        iq = numpy.empty(len(raw) / 2, 'complex')
        iq.real, iq.imag = raw[::2], raw[1::2]
        iq /= (255 / 2)
        iq -= 1

        return iq

    def set_sample_rate(self, rate):
        self.__send_command(RtlTcpCmd.SET_SAMPLE_RATE, rate)
        self.rate = rate

    def set_manual_gain_enabled(self, mode):
        self.__send_command(RtlTcpCmd.SET_GAIN_MODE, mode)

    def set_gain(self, gain):
        self.__send_command(RtlTcpCmd.SET_GAIN, gain * 10)

    def set_center_freq(self, freq):
        self.__send_command(RtlTcpCmd.SET_FREQ, freq)
        self.__read_raw(int(self.rate * 2 * 0.1))

    def get_tuner_type(self):
        return self.tuner

    def read_samples(self, samples):

        raw = self.__read_raw(samples)
        return self.__raw_to_iq(raw)

    def close(self):
        self.threadBuffer.abort()
        self.threadBuffer.join()


class ThreadBuffer(threading.Thread):
    name = 'Buffer'
    buffer = ""
    cancel = False
    readLen = 0
    read = 0
    done = False
    READ_SIZE = 4096

    def __init__(self, host, port):
        threading.Thread.__init__(self)

        self.condition = threading.Condition()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(5)
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.socket.connect((host, port))
        self.header = self.socket.recv(12)
        self.start()

    def run(self):
        while not self.cancel:
            if self.readLen > 0:
                self.__read_stream()
            else:
                self.__skip_stream()

        self.socket.close()
        self.__do_notify()

    def __do_wait(self):
        self.condition.acquire()
        while not self.done:
            self.condition.wait(2)
        self.done = False
        self.condition.release()

    def __do_notify(self):
        self.condition.acquire()
        self.done = True
        self.condition.notify()
        self.condition.release()

    def __read_stream(self):
        data = []
        recv = ""

        self.buffer = ""
        while self.readLen > 0:
            recv = self.socket.recv(self.readLen)
            if len(recv) == 0:
                break
            data.append(recv)
            self.readLen -= len(recv)

        self.buffer = bytearray(''.join(data))
        self.__do_notify()

    def __skip_stream(self):
        total = self.READ_SIZE
        while total > 0:
            recv = self.socket.recv(total)
            if len(recv) == 0:
                break
            total -= len(recv)

    def get_header(self):
        return self.header

    def recv(self, length):
        self.readLen = length
        self.__do_wait()
        return self.buffer

    def sendall(self, data):
        self.socket.sendall(data)

    def abort(self):
        self.cancel = True

########NEW FILE########
__FILENAME__ = scan
#
# rtlsdr_scan
#
# http://eartoearoak.com/software/rtlsdr-scanner
#
# Copyright 2012 - 2014 Al Brown
#
# A frequency scanning GUI for the OsmoSDR rtl-sdr library at
# http://sdr.osmocom.org/trac/wiki/rtl-sdr
#
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import itertools
import math
import threading
import time

import matplotlib
import rtlsdr

from constants import SAMPLE_RATE, BANDWIDTH, WINFUNC
from events import EventThread, Event, post_event
import rtltcp


class ThreadScan(threading.Thread):
    def __init__(self, notify, sdr, settings, device, samples, isCal):
        threading.Thread.__init__(self)
        self.name = 'Scan'
        self.notify = notify
        self.sdr = sdr
        self.fstart = settings.start * 1e6
        self.fstop = settings.stop * 1e6
        self.samples = int(samples)
        self.isCal = isCal
        self.indexRtl = settings.indexRtl
        self.isDevice = settings.devicesRtl[device].isDevice
        self.server = settings.devicesRtl[device].server
        self.port = settings.devicesRtl[device].port
        self.gain = settings.devicesRtl[device].gain
        self.lo = settings.devicesRtl[device].lo * 1e6
        self.offset = settings.devicesRtl[device].offset
        self.cancel = False

        post_event(self.notify, EventThread(Event.STARTING))
        steps = int((self.__f_stop() - self.__f_start()) / self.__f_step())
        post_event(self.notify, EventThread(Event.STEPS, steps))
        self.start()

    def __f_start(self):
        return self.fstart - self.offset - BANDWIDTH

    def __f_stop(self):
        return self.fstop + self.offset + BANDWIDTH * 2

    def __f_step(self):
        return BANDWIDTH / 2

    def __rtl_setup(self):

        if self.sdr is not None:
            return

        tuner = 0

        if self.isDevice:
            try:
                self.sdr = rtlsdr.RtlSdr(self.indexRtl)
                self.sdr.set_sample_rate(SAMPLE_RATE)
                self.sdr.set_manual_gain_enabled(1)
                self.sdr.set_gain(self.gain)
                tuner = self.sdr.get_tuner_type()
            except IOError as error:
                post_event(self.notify, EventThread(Event.ERROR,
                                                          0, error.message))
        else:
            try:
                self.sdr = rtltcp.RtlTcp(self.server, self.port)
                self.sdr.set_sample_rate(SAMPLE_RATE)
                self.sdr.set_manual_gain_enabled(1)
                self.sdr.set_gain(self.gain)
                tuner = self.sdr.get_tuner_type()
            except IOError as error:
                post_event(self.notify, EventThread(Event.ERROR,
                                                          0, error))

        return tuner

    def run(self):
        tuner = self.__rtl_setup()
        if self.sdr is None:
            return
        post_event(self.notify, EventThread(Event.INFO, None, tuner))

        freq = self.__f_start()
        timeStamp = math.floor(time.time())
        while freq <= self.__f_stop():
            if self.cancel:
                post_event(self.notify,
                           EventThread(Event.STOPPED))
                self.rtl_close()
                return
            try:
                scan = self.rtl_scan(freq)
                post_event(self.notify,
                           EventThread(Event.DATA, freq,
                                            (timeStamp, scan)))
            except IOError:
                if self.sdr is not None:
                    self.rtl_close()
                self.__rtl_setup()
            except (TypeError, AttributeError) as error:
                if self.notify:
                    post_event(self.notify,
                               EventThread(Event.ERROR,
                                                 0, error.message))
                return
            except WindowsError:
                if self.sdr is not None:
                    self.rtl_close()

            freq += self.__f_step()

        post_event(self.notify, EventThread(Event.FINISHED, 0, None))

        if self.isCal:
            post_event(self.notify, EventThread(Event.CAL))

    def abort(self):
        self.cancel = True

    def rtl_scan(self, freq):
        self.sdr.set_center_freq(freq + self.lo)
        capture = self.sdr.read_samples(self.samples)

        return capture

    def rtl_close(self):
        self.sdr.close()

    def get_sdr(self):
        return self.sdr


def anaylse_data(freq, data, cal, nfft, overlap, winFunc):
    spectrum = {}
    timeStamp = data[0]
    samples = data[1]
    pos = WINFUNC[::2].index(winFunc)
    function = WINFUNC[1::2][pos]
    powers, freqs = matplotlib.mlab.psd(samples,
                                        NFFT=nfft,
                                        noverlap=int((nfft) * overlap),
                                        Fs=SAMPLE_RATE / 1e6,
                                        window=function(nfft))
    for freqPsd, pwr in itertools.izip(freqs, powers):
        xr = freqPsd + (freq / 1e6)
        xr = xr + (xr * cal / 1e6)
        spectrum[xr] = pwr

    return (timeStamp, freq, spectrum)


def update_spectrum(notify, lock, start, stop, freqCentre, data, offset,
                    spectrum, average, alertLevel=None):
    with lock:
        updated = False
        if average:
            if len(spectrum) > 0:
                timeStamp = min(spectrum)
            else:
                timeStamp = data[0]
        else:
            timeStamp = data[0]
        scan = data[1]

        upperStart = freqCentre + offset
        upperEnd = freqCentre + offset + BANDWIDTH / 2
        lowerStart = freqCentre - offset - BANDWIDTH / 2
        lowerEnd = freqCentre - offset

        if not timeStamp in spectrum:
            spectrum[timeStamp] = {}

        for freq in scan:
            if start <= freq < stop:
                power = 10 * math.log10(scan[freq])
                if upperStart <= freq * 1e6 <= upperEnd or \
                   lowerStart <= freq * 1e6 <= lowerEnd:
                    if freq in spectrum[timeStamp]:
                        spectrum[timeStamp][freq] = \
                            (spectrum[timeStamp][freq] + power) / 2
                        if alertLevel is not None and \
                        spectrum[timeStamp][freq] > alertLevel:
                            post_event(notify, EventThread(Event.LEVEL))
                        updated = True
                    else:
                        spectrum[timeStamp][freq] = power
                        updated = True

    post_event(notify, EventThread(Event.UPDATED, None, updated))


if __name__ == '__main__':
    print 'Please run rtlsdr_scan.py'
    exit(1)

########NEW FILE########
__FILENAME__ = settings
#
# rtlsdr_scan
#
# http://eartoearoak.com/software/rtlsdr-scanner
#
# Copyright 2012 - 2014 Al Brown
#
# A frequency scanning GUI for the OsmoSDR rtl-sdr library at
# http://sdr.osmocom.org/trac/wiki/rtl-sdr
#
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import wx

from constants import Display, Mode, PlotFunc
from devices import DeviceRTL, format_device_rtl_name, DeviceGPS


class Settings():
    def __init__(self, load=True):
        self.cfg = None

        self.saveWarn = True
        self.fileHistory = wx.FileHistory(5)

        self.dirScans = "."
        self.dirExport = "."

        self.display = Display.PLOT

        self.annotate = True

        self.retainScans = True
        self.retainMax = 20
        self.fadeScans = True
        self.lineWidth = 0.4
        self.colourMapUse = True
        self.colourMap = 'jet'
        self.background = '#f0f0f0'
        self.wireframe = False
        self.pointsLimit = False
        self.pointsMax = 5000
        self.grid = True
        self.plotFunc = PlotFunc.NONE

        self.compareOne = True
        self.compareTwo = True
        self.compareDiff = True

        self.start = 87
        self.stop = 108
        self.mode = Mode.SINGLE
        self.dwell = 0.1
        self.nfft = 1024
        self.overlap = 0.0
        self.winFunc = "Hamming"

        self.liveUpdate = False
        self.calFreq = 1575.42
        self.autoF = True
        self.autoL = True
        self.autoT = True

        self.showMeasure = True

        self.alert = False
        self.alertLevel = -20

        self.gps = False

        self.exportDpi = 600

        self.devicesRtl = []
        self.indexRtl = 0
        self.devicesGps = []
        self.indexGps = 0

        if load:
            self.__load()

    def __clear_servers(self):
        self.cfg.SetPath("/DevicesRTL")
        group = self.cfg.GetFirstGroup()
        while group[0]:
            key = "/DevicesRTL/" + group[1]
            self.cfg.SetPath(key)
            if not self.cfg.ReadBool('isDevice', True):
                self.cfg.DeleteGroup(key)
            self.cfg.SetPath("/DevicesRTL")
            group = self.cfg.GetNextGroup(group[2])

    def __load_devices_rtl(self):
        self.cfg.SetPath("/DevicesRTL")
        group = self.cfg.GetFirstGroup()
        while group[0]:
            self.cfg.SetPath("/DevicesRTL/" + group[1])
            device = DeviceRTL()
            device.name = group[1]
            device.serial = self.cfg.Read('serial', '')
            device.isDevice = self.cfg.ReadBool('isDevice', True)
            device.server = self.cfg.Read('server', 'localhost')
            device.port = self.cfg.ReadInt('port', 1234)
            device.gain = self.cfg.ReadFloat('gain', 0)
            device.calibration = self.cfg.ReadFloat('calibration', 0)
            device.lo = self.cfg.ReadFloat('lo', 0)
            device.offset = self.cfg.ReadFloat('offset', 250e3)
            device.tuner = self.cfg.ReadInt('tuner', 0)
            self.devicesRtl.append(device)
            self.cfg.SetPath("/DevicesRTL")
            group = self.cfg.GetNextGroup(group[2])

    def __load_devices_gps(self):
        self.devicesGps = []
        self.cfg.SetPath("/DevicesGPS")
        group = self.cfg.GetFirstGroup()
        while group[0]:
            self.cfg.SetPath("/DevicesGPS/" + group[1])
            device = DeviceGPS()
            device.name = group[1]
            device.type = self.cfg.ReadInt('type', device.type)
            device.resource = self.cfg.Read('resource', device.resource)
            device.baud = self.cfg.ReadInt('baud', device.baud)
            device.bytes = self.cfg.ReadInt('bytes', device.bytes)
            device.parity = self.cfg.Read('parity', device.parity)
            device.stops = self.cfg.ReadInt('stops', device.stops)
            device.soft = self.cfg.ReadBool('soft', device.soft)
            self.devicesGps.append(device)
            self.cfg.SetPath("/DevicesGPS")
            group = self.cfg.GetNextGroup(group[2])

    def __save_devices_rtl(self):
        self.__clear_servers()

        if self.devicesRtl:
            for device in self.devicesRtl:
                if device.isDevice:
                    name = device.name
                else:
                    name = "{0}:{1}".format(device.server, device.port)
                self.cfg.SetPath("/DevicesRTL/" + format_device_rtl_name(name))
                self.cfg.Write('serial', device.serial)
                self.cfg.WriteBool('isDevice', device.isDevice)
                self.cfg.Write('server', device.server)
                self.cfg.WriteInt('port', device.port)
                self.cfg.WriteFloat('gain', device.gain)
                self.cfg.WriteFloat('lo', device.lo)
                self.cfg.WriteFloat('calibration', device.calibration)
                self.cfg.WriteFloat('offset', device.offset)
                self.cfg.WriteInt('tuner', device.tuner)

    def __save_devices_gps(self):
        self.cfg.DeleteGroup('/DevicesGPS')
        for device in self.devicesGps:
            self.cfg.SetPath("/DevicesGPS/" + device.name)
            self.cfg.WriteInt('type', device.type)
            self.cfg.Write('resource', device.resource)
            self.cfg.WriteInt('baud', device.baud)
            self.cfg.WriteInt('bytes', device.bytes)
            self.cfg.Write('parity', device.parity)
            self.cfg.WriteInt('stops', device.stops)
            self.cfg.WriteBool('soft', device.soft)

    def __load(self):
        self.cfg = wx.Config('rtlsdr-scanner')

        self.cfg.RenameGroup('Devices', 'DevicesRTL')

        self.display = self.cfg.ReadInt('display', self.display)
        self.saveWarn = self.cfg.ReadBool('saveWarn', self.saveWarn)
        self.fileHistory.Load(self.cfg)
        self.dirScans = self.cfg.Read('dirScans', self.dirScans)
        self.dirExport = self.cfg.Read('dirExport', self.dirExport)
        self.annotate = self.cfg.ReadBool('annotate', self.annotate)
        self.retainScans = self.cfg.ReadBool('retainScans', self.retainScans)
        self.fadeScans = self.cfg.ReadBool('fadeScans', self.fadeScans)
        self.lineWidth = self.cfg.ReadFloat('lineWidth', self.lineWidth)
        self.retainMax = self.cfg.ReadInt('retainMax', self.retainMax)
        self.colourMapUse = self.cfg.ReadBool('colourMapUse', self.colourMapUse)
        self.colourMap = self.cfg.Read('colourMap', self.colourMap)
        self.background = self.cfg.Read('background', self.background)
        self.wireframe = self.cfg.ReadBool('wireframe', self.wireframe)
        self.pointsLimit = self.cfg.ReadBool('pointsLimit', self.pointsLimit)
        self.pointsMax = self.cfg.ReadInt('pointsMax', self.pointsMax)
        self.grid = self.cfg.ReadBool('grid', self.grid)
        self.plotFunc = self.cfg.ReadInt('plotFunc', self.plotFunc)
        self.compareOne = self.cfg.ReadBool('compareOne', self.compareOne)
        self.compareTwo = self.cfg.ReadBool('compareTwo', self.compareTwo)
        self.compareDiff = self.cfg.ReadBool('compareDiff', self.compareDiff)
        self.start = self.cfg.ReadInt('start', self.start)
        self.stop = self.cfg.ReadInt('stop', self.stop)
        self.mode = self.cfg.ReadInt('mode', self.mode)
        self.dwell = self.cfg.ReadFloat('dwell', self.dwell)
        self.nfft = self.cfg.ReadInt('nfft', self.nfft)
        self.overlap = self.cfg.ReadFloat('overlap', self.overlap)
        self.winFunc = self.cfg.Read('winFunc', self.winFunc)
        self.liveUpdate = self.cfg.ReadBool('liveUpdate', self.liveUpdate)
        self.calFreq = self.cfg.ReadFloat('calFreq', self.calFreq)
        self.autoF = self.cfg.ReadBool('autoF', self.autoF)
        self.autoL = self.cfg.ReadBool('autoL', self.autoL)
        self.autoT = self.cfg.ReadBool('autoT', self.autoT)
        self.showMeasure = self.cfg.ReadBool('showMeasure', self.showMeasure)
        self.alert = self.cfg.ReadBool('alert', self.alert)
        self.alertLevel = self.cfg.ReadFloat('alertLevel', self.alertLevel)
        self.gps = self.cfg.ReadBool('gps', self.gps)
        self.exportDpi = self.cfg.ReadInt('exportDpi', self.exportDpi)
        self.indexRtl = self.cfg.ReadInt('index', self.indexRtl)
        self.indexRtl = self.cfg.ReadInt('indexRtl', self.indexRtl)
        self.indexGps = self.cfg.ReadInt('indexGps', self.indexGps)
        self.__load_devices_rtl()
        self.__load_devices_gps()

    def save(self):
        self.cfg.SetPath("/")
        self.cfg.WriteInt('display', self.display)
        self.cfg.WriteBool('saveWarn', self.saveWarn)
        self.fileHistory.Save(self.cfg)
        self.cfg.Write('dirScans', self.dirScans)
        self.cfg.Write('dirExport', self.dirExport)
        self.cfg.WriteBool('annotate', self.annotate)
        self.cfg.WriteBool('retainScans', self.retainScans)
        self.cfg.WriteBool('fadeScans', self.fadeScans)
        self.cfg.WriteFloat('lineWidth', self.lineWidth)
        self.cfg.WriteInt('retainMax', self.retainMax)
        self.cfg.WriteBool('colourMapUse', self.colourMapUse)
        self.cfg.Write('colourMap', self.colourMap)
        self.cfg.Write('background', self.background)
        self.cfg.WriteBool('wireframe', self.wireframe)
        self.cfg.WriteBool('pointsLimit', self.pointsLimit)
        self.cfg.WriteInt('pointsMax', self.pointsMax)
        self.cfg.WriteBool('grid', self.grid)
        self.cfg.WriteInt('plotFunc', self.plotFunc)
        self.cfg.WriteBool('compareOne', self.compareOne)
        self.cfg.WriteBool('compareTwo', self.compareTwo)
        self.cfg.WriteBool('compareDiff', self.compareDiff)
        self.cfg.WriteInt('start', self.start)
        self.cfg.WriteInt('stop', self.stop)
        self.cfg.WriteInt('mode', self.mode)
        self.cfg.WriteFloat('dwell', self.dwell)
        self.cfg.WriteInt('nfft', self.nfft)
        self.cfg.WriteFloat('overlap', self.overlap)
        self.cfg.Write("winFunc", self.winFunc)
        self.cfg.WriteBool('liveUpdate', self.liveUpdate)
        self.cfg.WriteFloat('calFreq', self.calFreq)
        self.cfg.WriteBool('autoF', self.autoF)
        self.cfg.WriteBool('autoL', self.autoL)
        self.cfg.WriteBool('autoT', self.autoT)
        self.cfg.WriteBool('showMeasure', self.showMeasure)
        self.cfg.WriteBool('alert', self.alert)
        self.cfg.WriteFloat('alertLevel', self.alertLevel)
        self.cfg.WriteBool('gps', self.gps)
        self.cfg.WriteInt('exportDpi', self.exportDpi)
        self.cfg.WriteInt('indexRtl', self.indexRtl)
        self.cfg.WriteInt('indexGps', self.indexGps)
        self.__save_devices_rtl()
        self.__save_devices_gps()

        self.cfg.DeleteEntry('autoScale')
        self.cfg.DeleteEntry('yMax')
        self.cfg.DeleteEntry('yMin')
        self.cfg.DeleteEntry('average')
        self.cfg.DeleteEntry('index')

    def reset(self):
        self.cfg.SetPath("/")
        self.cfg.DeleteAll()
        self.__init__()


if __name__ == '__main__':
    print 'Please run rtlsdr_scan.py'
    exit(1)

########NEW FILE########
__FILENAME__ = spectrogram
#
# rtlsdr_scan
#
# http://eartoearoak.com/software/rtlsdr-scanner
#
# Copyright 2012 - 2014 Al Brown
#
# A frequency scanning GUI for the OsmoSDR rtl-sdr library at
# http://sdr.osmocom.org/trac/wiki/rtl-sdr
#
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import threading
import time

from matplotlib import cm, patheffects
import matplotlib
from matplotlib.colorbar import ColorbarBase
from matplotlib.colors import Normalize
from matplotlib.dates import DateFormatter
from matplotlib.gridspec import GridSpec
from matplotlib.lines import Line2D
from matplotlib.text import Text
from matplotlib.ticker import ScalarFormatter, AutoMinorLocator
import numpy

from constants import Markers
from events import EventThread, Event, post_event
from misc import format_time
from spectrum import epoch_to_mpl, split_spectrum, Measure


class Spectrogram:
    def __init__(self, notify, figure, settings):
        self.notify = notify
        self.figure = figure
        self.settings = settings
        self.data = [[], [], []]
        self.axes = None
        self.plot = None
        self.extent = None
        self.bar = None
        self.barBase = None
        self.lines = {}
        self.labels = {}
        self.overflowLabels = {}
        self.overflow = {'left': [],
                         'right': []}

        self.threadPlot = None
        self.__setup_plot()
        self.set_grid(self.settings.grid)

    def __setup_plot(self):
        gs = GridSpec(1, 2, width_ratios=[9.5, 0.5])
        self.axes = self.figure.add_subplot(gs[0],
                                            axisbg=self.settings.background)

        self.axes.set_xlabel("Frequency (MHz)")
        self.axes.set_ylabel('Time')
        numFormatter = ScalarFormatter(useOffset=False)
        timeFormatter = DateFormatter("%H:%M:%S")

        self.axes.xaxis.set_major_formatter(numFormatter)
        self.axes.yaxis.set_major_formatter(timeFormatter)
        self.axes.xaxis.set_minor_locator(AutoMinorLocator(10))
        self.axes.yaxis.set_minor_locator(AutoMinorLocator(10))
        self.axes.set_xlim(self.settings.start, self.settings.stop)
        now = time.time()
        self.axes.set_ylim(epoch_to_mpl(now), epoch_to_mpl(now - 10))

        self.bar = self.figure.add_subplot(gs[1])
        norm = Normalize(vmin=-50, vmax=0)
        self.barBase = ColorbarBase(self.bar, norm=norm,
                                    cmap=cm.get_cmap(self.settings.colourMap))

        self.__setup_measure()
        self.__setup_overflow()
        self.hide_measure()

    def __setup_measure(self):
        dashesHalf = [1, 5, 5, 5, 5, 5]
        self.lines[Markers.HFS] = Line2D([0, 0], [0, 0], dashes=dashesHalf,
                                         color='purple')
        self.lines[Markers.HFE] = Line2D([0, 0], [0, 0], dashes=dashesHalf,
                                         color='purple')
        self.lines[Markers.OFS] = Line2D([0, 0], [0, 0], dashes=dashesHalf,
                                         color='#996600')
        self.lines[Markers.OFE] = Line2D([0, 0], [0, 0], dashes=dashesHalf,
                                         color='#996600')
        if matplotlib.__version__ >= '1.3':
            effect = patheffects.withStroke(linewidth=3, foreground="w",
                                            alpha=0.75)
            self.lines[Markers.HFS].set_path_effects([effect])
            self.lines[Markers.HFE].set_path_effects([effect])
            self.lines[Markers.OFS].set_path_effects([effect])
            self.lines[Markers.OFE].set_path_effects([effect])

        for line in self.lines.itervalues():
            self.axes.add_line(line)

        bbox = self.axes.bbox
        box = dict(boxstyle='round', fc='white', ec='purple', clip_box=bbox)
        self.labels[Markers.HFS] = Text(0, 0, '-3dB', fontsize='xx-small',
                                       ha="center", va="top", bbox=box,
                                       color='purple')
        self.labels[Markers.HFE] = Text(0, 0, '-3dB', fontsize='xx-small',
                                       ha="center", va="top", bbox=box,
                                       color='purple')
        box['ec'] = '#996600'
        self.labels[Markers.OFS] = Text(0, 0, 'OBW', fontsize='xx-small',
                                       ha="center", va="top", bbox=box,
                                       color='#996600')
        self.labels[Markers.OFE] = Text(0, 0, 'OBW', fontsize='xx-small',
                                       ha="center", va="top", bbox=box,
                                       color='#996600')

        for label in self.labels.itervalues():
            self.axes.add_artist(label)

    def __setup_overflow(self):
        bbox = self.axes.bbox
        box = dict(boxstyle='round', fc='white', ec='black', alpha=0.5,
                   clip_box=bbox)
        self.overflowLabels['left'] = Text(0, 0.9, '', fontsize='xx-small',
                                           ha="left", va="top", bbox=box,
                                           transform=self.axes.transAxes,
                                           alpha=0.5)
        self.overflowLabels['right'] = Text(1, 0.9, '', fontsize='xx-small',
                                            ha="right", va="top", bbox=box,
                                            transform=self.axes.transAxes,
                                            alpha=0.5)

        for label in self.overflowLabels.itervalues():
            self.axes.add_artist(label)

    def __clear_overflow(self):
        for label in self.overflowLabels:
            self.overflow[label] = []

    def __draw_vline(self, marker, x):
        line = self.lines[marker]
        label = self.labels[marker]
        yLim = self.axes.get_ylim()
        xLim = self.axes.get_xlim()
        if xLim[0] < x < xLim[1]:
            line.set_visible(True)
            line.set_xdata([x, x])
            line.set_ydata([yLim[0], yLim[1]])
            self.axes.draw_artist(line)
            label.set_visible(True)
            label.set_position((x, yLim[1]))
            self.axes.draw_artist(label)
        elif x is not None and x < xLim[0]:
            self.overflow['left'].append(marker)
        elif x is not None and x > xLim[1]:
            self.overflow['right'].append(marker)

    def __draw_overflow(self):
        for pos, overflow in self.overflow.iteritems():
            if len(overflow) > 0:
                text = ''
                for measure in overflow:
                    if len(text) > 0:
                        text += '\n'
                    text += self.labels[measure].get_text()

                label = self.overflowLabels[pos]
                if pos == 'left':
                    textMath = '$\\blacktriangleleft$\n' + text
                elif pos == 'right':
                    textMath = '$\\blacktriangleright$\n' + text

                label.set_text(textMath)
                label.set_visible(True)
                self.axes.draw_artist(label)

    def draw_measure(self, measure, show):
        if self.axes.get_renderer_cache() is None:
            return

        self.hide_measure()
        self.__clear_overflow()

        if show[Measure.HBW]:
            xStart, xEnd, _y = measure.get_hpw()
            self.__draw_vline(Markers.HFS, xStart)
            self.__draw_vline(Markers.HFE, xEnd)

        if show[Measure.OBW]:
            xStart, xEnd, _y = measure.get_obw()
            self.__draw_vline(Markers.OFS, xStart)
            self.__draw_vline(Markers.OFE, xEnd)

        self.__draw_overflow()

    def hide_measure(self):
        for line in self.lines.itervalues():
            line.set_visible(False)
        for label in self.labels.itervalues():
            label.set_visible(False)
        for label in self.overflowLabels.itervalues():
            label.set_visible(False)

    def scale_plot(self, force=False):
        if self.figure is not None and self.plot is not None:
            extent = self.plot.get_extent()
            if self.settings.autoF or force:
                if extent[0] == extent[1]:
                    extent[1] += 1
                self.axes.set_xlim(extent[0], extent[1])
            if self.settings.autoL or force:
                vmin, vmax = self.plot.get_clim()
                self.barBase.set_clim(vmin, vmax)
                try:
                    self.barBase.draw_all()
                except:
                    pass
            if self.settings.autoT or force:
                self.axes.set_ylim(extent[2], extent[3])

    def redraw_plot(self):
        if self.figure is not None:
            post_event(self.notify, EventThread(Event.DRAW))

    def get_axes(self):
        return self.axes

    def get_axes_bar(self):
        return self.barBase.ax

    def get_plot_thread(self):
        return self.threadPlot

    def set_title(self, title):
        self.axes.set_title(title, fontsize='medium')

    def set_plot(self, data, extent, annotate=False):
        self.extent = extent
        self.threadPlot = ThreadPlot(self, self.axes,
                                     data, self.extent,
                                     self.settings.retainMax,
                                     self.settings.colourMap,
                                     self.settings.autoL,
                                     self.barBase,
                                     annotate)
        self.threadPlot.start()

    def clear_plots(self):
        children = self.axes.get_children()
        for child in children:
            if child.get_gid() is not None:
                if child.get_gid() == "plot" or child.get_gid() == "peak":
                    child.remove()

    def set_grid(self, on):
        if on:
            self.axes.grid(True, color='w')
        else:
            self.axes.grid(False)
        self.redraw_plot()

    def set_colourmap(self, colourMap):
        if self.plot is not None:
            self.plot.set_cmap(colourMap)
        self.barBase.set_cmap(colourMap)
        try:
            self.barBase.draw_all()
        except:
            pass

    def close(self):
        self.figure.clear()
        self.figure = None


class ThreadPlot(threading.Thread):
    def __init__(self, parent, axes, data, extent, retainMax, colourMap,
                 autoL, barBase, annotate):
        threading.Thread.__init__(self)
        self.name = "Plot"
        self.parent = parent
        self.axes = axes
        self.data = data
        self.extent = extent
        self.retainMax = retainMax
        self.colourMap = colourMap
        self.autoL = autoL
        self.barBase = barBase
        self.annotate = annotate

    def run(self):
        if self.data is None:
            self.parent.threadPlot = None
            return

        total = len(self.data)
        if total > 0:
            width = len(self.data[min(self.data)])
            c = numpy.ma.masked_all((self.retainMax, width))
            self.parent.clear_plots()
            j = self.retainMax
            for ys in self.data:
                j -= 1
                _xs, zs = split_spectrum(self.data[ys])
                for i in range(len(zs)):
                    c[j, i] = zs[i]

            norm = None
            if not self.autoL:
                minY, maxY = self.barBase.get_clim()
                norm = Normalize(vmin=minY, vmax=maxY)

            extent = self.extent.get_ft()
            self.parent.plot = self.axes.imshow(c, aspect='auto',
                                                extent=extent,
                                                norm=norm,
                                                cmap=cm.get_cmap(self.colourMap),
                                                interpolation='spline16',
                                                gid="plot")

            if self.annotate:
                self.__annotate_plot()

        if total > 0:
            self.parent.scale_plot()
            self.parent.redraw_plot()

        self.parent.threadPlot = None

    def __annotate_plot(self):
        self.__clear_markers()
        fMax, lMax, tMax = self.extent.get_peak_flt()
        y = epoch_to_mpl(tMax)

        start, stop = self.axes.get_xlim()
        textX = ((stop - start) / 50.0) + fMax
        when = format_time(tMax)

        text = '{0:.6f} MHz\n{1:.2f} $\mathsf{{dB/\sqrt{{Hz}}}}$\n{2}'.format(fMax, lMax, when)
        if matplotlib.__version__ < '1.3':
            self.axes.annotate(text,
                               xy=(fMax, y), xytext=(textX, y),
                               ha='left', va='bottom', size='x-small',
                               color='w', gid='peak')
            self.axes.plot(fMax, y, marker='x', markersize=10, color='w',
                           mew=3, gid='peak')
            self.axes.plot(fMax, y, marker='x', markersize=10, color='r',
                           gid='peak')
        else:
            effect = patheffects.withStroke(linewidth=2, foreground="w",
                                            alpha=0.75)
            self.axes.annotate(text,
                               xy=(fMax, y), xytext=(textX, y),
                               ha='left', va='bottom', size='x-small',
                               path_effects=[effect], gid='peak')
            self.axes.plot(fMax, y, marker='x', markersize=10, color='r',
                           path_effects=[effect], gid='peak')

    def __clear_markers(self):
        children = self.axes.get_children()
        for child in children:
            if child.get_gid() is not None:
                if child.get_gid() == 'peak':
                    child.remove()


if __name__ == '__main__':
    print 'Please run rtlsdr_scan.py'
    exit(1)

########NEW FILE########
__FILENAME__ = spectrum
#
# rtlsdr_scan
#
# http://eartoearoak.com/software/rtlsdr-scanner
#
# Copyright 2012 - 2014 Al Brown
#
# A frequency scanning GUI for the OsmoSDR rtl-sdr library at
# http://sdr.osmocom.org/trac/wiki/rtl-sdr
#
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
from collections import OrderedDict
import datetime
from decimal import Decimal
from operator import itemgetter, mul
import time

from matplotlib.dates import date2num, seconds
import numpy

from misc import db_to_level, level_to_db


class Extent():
    def __init__(self, spectrum):
        self.__clear()
        self.__calc_extent(spectrum)

    def __clear(self):
        self.fMin = float('inf')
        self.fMax = float('-inf')
        self.lMin = float('inf')
        self.lMax = float('-inf')
        self.tMin = float('inf')
        self.tMax = float('-inf')
        self.fPeak = None
        self.lPeak = None
        self.tPeak = None

    def __calc_extent(self, spectrum):
        for timeStamp in spectrum:
            points = spectrum[timeStamp].items()
            if len(points) > 0:
                fMin = min(points, key=itemgetter(0))[0]
                fMax = max(points, key=itemgetter(0))[0]
                lMin = min(points, key=itemgetter(1))[1]
                lMax = max(points, key=itemgetter(1))[1]
                self.fMin = min(self.fMin, fMin)
                self.fMax = max(self.fMax, fMax)
                self.lMin = min(self.lMin, lMin)
                self.lMax = max(self.lMax, lMax)
        self.tMin = min(spectrum)
        self.tMax = max(spectrum)
        self.tPeak = self.tMax
        if len(spectrum[self.tMax]) > 0:
            self.fPeak, self.lPeak = max(spectrum[self.tMax].items(),
                                         key=lambda(_f, l): l)

    def get_f(self):
        if self.fMin == self.fMax:
            return self.fMin, self.fMax - 0.001
        return self.fMin, self.fMax

    def get_l(self):
        if self.lMin == self.lMax:
            return self.lMin, self.lMax - 0.001
        return self.lMin, self.lMax

    def get_t(self):
        return epoch_to_mpl(self.tMax), epoch_to_mpl(self.tMin - 1)

    def get_ft(self):
        tExtent = self.get_t()
        return [self.fMin, self.fMax, tExtent[0], tExtent[1]]

    def get_peak_fl(self):
        return self.fPeak, self.lPeak

    def get_peak_flt(self):
        return self.fPeak, self.lPeak, self.tPeak


class Measure():
    MIN, MAX, AVG, GMEAN, HBW, OBW = range(6)

    def __init__(self, spectrum, start, end):
        self.isValid = False
        self.minF = None
        self.maxF = None
        self.minP = None
        self.maxP = None
        self.avgP = None
        self.gMeanP = None
        self.flatness = None
        self.hbw = None
        self.obw = None

        self.__calculate(spectrum, start, end)

    def __calculate(self, spectrum, start, end):
        sweep = slice_spectrum(spectrum, start, end)
        if sweep is None or len(sweep) == 0:
            return

        self.minF = min(sweep)[0]
        self.maxF = max(sweep)[0]
        self.minP = min(sweep, key=lambda v: v[1])
        self.maxP = max(sweep, key=lambda v: v[1])

        powers = [Decimal(db_to_level(p[1])) for p in sweep]
        length = len(powers)

        avg = sum(powers, Decimal(0)) / length
        self.avgP = level_to_db(avg)

        product = reduce(mul, iter(powers))
        gMean = product ** (Decimal(1.0) / length)
        self.gMeanP = level_to_db(gMean)

        self.flatness = gMean / avg

        self.__calc_hbw(sweep)
        self.__calc_obw(sweep)

        self.isValid = True

    def __calc_hbw(self, sweep):
        power = self.maxP[1] - 3
        self.hbw = [None, None, power]

        if power >= self.minP[1]:
            for (f, p) in sweep:
                if p >= power:
                    self.hbw[0] = f
                    break
            for (f, p) in reversed(sweep):
                if p >= power:
                    self.hbw[1] = f
                    break

    def __calc_obw(self, sweep):
        self.obw = [None, None, None]

        totalP = 0
        for (_f, p) in sweep:
            totalP += p
        power = totalP * 0.005
        self.obw[2] = power

        if power >= self.minP[1]:
            for (f, p) in sweep:
                if p >= power:
                    self.obw[0] = f
                    break
            for (f, p) in reversed(sweep):
                if p >= power:
                    self.obw[1] = f
                    break

    def is_valid(self):
        return self.isValid

    def get_f(self):
        return self.minF, self.maxF

    def get_min_p(self):
        return self.minP

    def get_max_p(self):
        return self.maxP

    def get_avg_p(self):
        return self.avgP

    def get_gmean_p(self):
        return self.gMeanP

    def get_flatness(self):
        return self.flatness

    def get_hpw(self):
        return self.hbw

    def get_obw(self):
        return self.obw


def count_points(spectrum):
    points = 0
    for timeStamp in spectrum:
        points += len(spectrum[timeStamp])

    return points


def reduce_points(spectrum, limit):
    total = count_points(spectrum)
    if total < limit:
        return spectrum

    newSpectrum = OrderedDict()
    ratio = float(total) / limit
    for timeStamp in spectrum:
        points = spectrum[timeStamp].items()
        reduced = OrderedDict()
        for i in xrange(int(len(points) / ratio)):
            point = points[int(i * ratio):int((i + 1) * ratio)][0]
            reduced[point[0]] = point[1]
        newSpectrum[timeStamp] = reduced

    return newSpectrum


def split_spectrum(spectrum):
    freqs = spectrum.keys()
    powers = map(spectrum.get, freqs)

    return freqs, powers


def split_spectrum_sort(spectrum):
    freqs = spectrum.keys()
    freqs.sort()
    powers = map(spectrum.get, freqs)

    return freqs, powers


def slice_spectrum(spectrum, start, end):
    if spectrum is None or start is None or end is None or len(spectrum) < 1:
        return None

    sweep = spectrum[max(spectrum)]
    if len(sweep) == 0:
        return None

    if min(sweep) > start or max(sweep) < end:
        length = len(spectrum)
        if length > 1:
            sweep = spectrum.values()[length - 2]
        else:
            return None

    sweepTemp = {}
    for f, p in sweep.iteritems():
        if start <= f <= end:
            sweepTemp[f] = p
    return sorted(sweepTemp.items(), key=lambda t: t[0])


def create_mesh(spectrum, mplTime):
    total = len(spectrum)
    width = len(spectrum[min(spectrum)])
    x = numpy.empty((width, total + 1)) * numpy.nan
    y = numpy.empty((width, total + 1)) * numpy.nan
    z = numpy.empty((width, total + 1)) * numpy.nan

    j = 1
    for ys in spectrum:
        time = epoch_to_mpl(ys) if mplTime else ys
        xs, zs = split_spectrum(spectrum[ys])
        for i in range(len(xs)):
            x[i, j] = xs[i]
            y[i, j] = time
            z[i, j] = zs[i]
        j += 1

    x[:, 0] = x[:, 1]
    if mplTime:
        y[:, 0] = y[:, 1] - seconds(1)
    else:
        y[:, 0] = y[:, 1] - 1
    z[:, 0] = z[:, 1]

    return x, y, z


def sort_spectrum(spectrum):
    newSpectrum = OrderedDict()
    for timeStamp in reversed(sorted(spectrum)):
        newPoints = OrderedDict()
        points = sorted(spectrum[timeStamp].items())
        for point in points:
            newPoints[point[0]] = point[1]
        newSpectrum[timeStamp] = newPoints

    return newSpectrum


def epoch_to_local(epoch):
    local = time.localtime(epoch)
    return time.mktime(local)


def epoch_to_mpl(epoch):
    epoch = epoch_to_local(epoch)
    dt = datetime.datetime.fromtimestamp(epoch)
    return date2num(dt)

########NEW FILE########
__FILENAME__ = toolbars
#
# rtlsdr_scan
#
# http://eartoearoak.com/software/rtlsdr-scanner
#
# Copyright 2012 - 2014 Al Brown
#
# A frequency scanning GUI for the OsmoSDR rtl-sdr library at
# http://sdr.osmocom.org/trac/wiki/rtl-sdr
#
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import matplotlib
from matplotlib.backend_bases import NavigationToolbar2
from matplotlib.backends.backend_wxagg import NavigationToolbar2WxAgg
import wx

from constants import Display, PlotFunc
from misc import load_bitmap, get_colours


class Statusbar(wx.StatusBar):
    def __init__(self, parent):
        wx.StatusBar.__init__(self, parent, -1)
        self.SetFieldsCount(3)
        self.statusProgress = wx.Gauge(self, -1,
                                       style=wx.GA_HORIZONTAL | wx.GA_SMOOTH)
        self.statusProgress.Hide()
        self.Bind(wx.EVT_SIZE, self.__on_size)

    def __on_size(self, event):
        rect = self.GetFieldRect(2)
        self.statusProgress.SetPosition((rect.x + 10, rect.y + 2))
        self.statusProgress.SetSize((rect.width - 20, rect.height - 4))
        event.Skip()

    def set_general(self, text):
        self.SetStatusText(text, 0)
        self.SetToolTipString(text)

    def set_info(self, text):
        self.SetStatusText(text, 1)

    def set_progress(self, progress):
        self.statusProgress.SetValue(progress)

    def show_progress(self):
        self.statusProgress.Show()

    def hide_progress(self):
        self.statusProgress.Hide()


class NavigationToolbar(NavigationToolbar2WxAgg):
    def __init__(self, canvas, panel, settings, callBackHideOverlay):
        self.panel = panel
        self.settings = settings
        self.callbackHide = callBackHideOverlay
        self.plot = None
        self.extraTools = []
        self.panPos = None

        NavigationToolbar2WxAgg.__init__(self, canvas)
        if matplotlib.__version__ >= '1.2':
            panId = self.wx_ids['Pan']
        else:
            panId = self.FindById(self._NTB2_PAN).GetId()

        self.ToggleTool(panId, True)
        self.pan()

        self.__add_spacer()

        liveId = wx.NewId()
        self.AddCheckTool(liveId, load_bitmap('auto_refresh'),
                          shortHelp='Real time plotting\n(slow and buggy)')
        self.ToggleTool(liveId, settings.liveUpdate)
        wx.EVT_TOOL(self, liveId, self.__on_check_update)

        gridId = wx.NewId()
        self.AddCheckTool(gridId, load_bitmap('grid'),
                          shortHelp='Toggle plot grid')
        self.ToggleTool(gridId, settings.grid)
        wx.EVT_TOOL(self, gridId, self.__on_check_grid)

        peakId = wx.NewId()
        self.AddCheckTool(peakId, load_bitmap('peak'),
                          shortHelp='Label peak')
        self.ToggleTool(peakId, settings.annotate)
        wx.EVT_TOOL(self, peakId, self.__on_check_peak)

        self.__add_spacer()

        self.autoFId = wx.NewId()
        self.AddCheckTool(self.autoFId, load_bitmap('auto_f'),
                          shortHelp='Auto range frequency')
        self.ToggleTool(self.autoFId, settings.autoF)
        wx.EVT_TOOL(self, self.autoFId, self.__on_check_auto_f)

        self.autoLId = wx.NewId()
        self.AddCheckTool(self.autoLId, load_bitmap('auto_l'),
                          shortHelp='Auto range level')
        self.ToggleTool(self.autoLId, settings.autoL)
        wx.EVT_TOOL(self, self.autoLId, self.__on_check_auto_l)

        self.autoTId = None
        self.maxId = None
        self.minId = None
        self.avgId = None
        self.varId = None
        self.colourId = None

    def home(self, event):
        self.callbackHide()
        NavigationToolbar2.home(self, event)
        self.clear_auto()

    def back(self, event):
        self.callbackHide()
        NavigationToolbar2.back(self, event)
        self.clear_auto()

    def forward(self, event):
        self.callbackHide()
        NavigationToolbar2.forward(self, event)
        self.clear_auto()

    def drag_pan(self, event):
        if not self.panPos:
            self.panPos = (event.x, event.y)
        NavigationToolbar2.drag_pan(self, event)

    def release_pan(self, event):
        pos = (event.x, event.y)
        self.callbackHide()
        NavigationToolbar2.release_pan(self, event)
        if event.button != 2:
            if self.panPos and self.panPos != pos:
                self.clear_auto()
        self.panPos = None

    def release_zoom(self, event):
        self.callbackHide()
        NavigationToolbar2.release_zoom(self, event)
        self.clear_auto()

    def __on_check_auto_f(self, event):
        self.settings.autoF = event.Checked()
        self.panel.redraw_plot()

    def __on_check_auto_l(self, event):
        self.settings.autoL = event.Checked()
        self.panel.redraw_plot()

    def __on_check_auto_t(self, event):
        self.settings.autoT = event.Checked()
        self.panel.redraw_plot()

    def __on_check_update(self, event):
        self.settings.liveUpdate = event.Checked()

    def __on_check_grid(self, event):
        grid = event.Checked()
        self.panel.set_grid(grid)

    def __on_check_peak(self, event):
        peak = event.Checked()
        self.settings.annotate = peak
        self.panel.redraw_plot()

    def __on_check_fade(self, event):
        fade = event.Checked()
        self.settings.fadeScans = fade
        self.panel.redraw_plot()

    def __on_check_wire(self, event):
        wire = event.Checked()
        self.settings.wireframe = wire
        self.panel.create_plot()

    def __on_check_avg(self, event):
        check = event.Checked()
        if check:
            self.settings.plotFunc = PlotFunc.AVG
        else:
            self.settings.plotFunc = PlotFunc.NONE
        self.__set_func()
        self.panel.redraw_plot()

    def __on_check_var(self, event):
        check = event.Checked()
        if check:
            self.settings.plotFunc = PlotFunc.VAR
        else:
            self.settings.plotFunc = PlotFunc.NONE
        self.__set_func()
        self.panel.redraw_plot()

    def __on_check_min(self, event):
        check = event.Checked()
        if check:
            self.settings.plotFunc = PlotFunc.MIN
        else:
            self.settings.plotFunc = PlotFunc.NONE
        self.__set_func()
        self.panel.redraw_plot()

    def __on_check_max(self, event):
        check = event.Checked()
        if check:
            self.settings.plotFunc = PlotFunc.MAX
        else:
            self.settings.plotFunc = PlotFunc.NONE
        self.__set_func()
        self.panel.redraw_plot()

    def __on_colour(self, event):
        colourMap = event.GetString()
        self.settings.colourMap = colourMap
        self.plot.set_colourmap(colourMap)
        self.panel.redraw_plot()

    def __on_colour_use(self, event):
        check = event.Checked()
        self.settings.colourMapUse = check
        self.colourId.Enable(check)
        self.plot.set_colourmap_use(check)
        self.panel.redraw_plot()

    def __add_spacer(self):
        sepId = wx.NewId()
        self.AddCheckTool(sepId, load_bitmap('spacer'))
        self.EnableTool(sepId, False)
        return sepId

    def __set_func(self):
        buttons = [self.avgId, self.minId, self.maxId, self.varId]
        for button in buttons:
            self.ToggleTool(button, False)
        if self.settings.plotFunc != PlotFunc.NONE:
            self.ToggleTool(buttons[self.settings.plotFunc - 1], True)

    def set_auto(self, state):
        self.settings.autoF = state
        self.settings.autoL = state
        self.settings.autoT = state
        self.ToggleTool(self.autoFId, state)
        self.ToggleTool(self.autoLId, state)
        if self.autoTId is not None:
            self.ToggleTool(self.autoTId, state)

    def clear_auto(self):
        self.set_auto(False)

    def set_plot(self, plot):
        self.plot = plot

    def set_type(self, display):
        for toolId in self.extraTools:
            self.DeleteTool(toolId)
        self.extraTools = []

        if not display == Display.PLOT:
            self.autoTId = wx.NewId()
            self.AddCheckTool(self.autoTId, load_bitmap('auto_t'),
                              shortHelp='Auto range time')
            self.ToggleTool(self.autoTId, self.settings.autoT)
            wx.EVT_TOOL(self, self.autoTId, self.__on_check_auto_t)
            self.extraTools.append(self.autoTId)

        self.extraTools.append(self.__add_spacer())

        if display == Display.PLOT:
            fadeId = wx.NewId()
            self.AddCheckTool(fadeId, load_bitmap('fade'),
                              shortHelp='Fade plots')
            wx.EVT_TOOL(self, fadeId, self.__on_check_fade)
            self.ToggleTool(fadeId, self.settings.fadeScans)
            self.extraTools.append(fadeId)

            self.extraTools.append(self.__add_spacer())

            self.avgId = wx.NewId()
            self.AddCheckTool(self.avgId, load_bitmap('average'),
                              shortHelp='Show average')
            wx.EVT_TOOL(self, self.avgId, self.__on_check_avg)
            self.extraTools.append(self.avgId)
            self.minId = wx.NewId()
            self.AddCheckTool(self.minId, load_bitmap('min'),
                              shortHelp='Show minimum')
            wx.EVT_TOOL(self, self.minId, self.__on_check_min)
            self.extraTools.append(self.minId)
            self.maxId = wx.NewId()
            self.AddCheckTool(self.maxId, load_bitmap('max'),
                              shortHelp='Show maximum')
            wx.EVT_TOOL(self, self.maxId, self.__on_check_max)
            self.extraTools.append(self.maxId)
            self.varId = wx.NewId()
            self.AddCheckTool(self.varId, load_bitmap('variance'),
                              shortHelp='Show variance')
            wx.EVT_TOOL(self, self.varId, self.__on_check_var)
            self.extraTools.append(self.varId)

            self.__set_func()

            self.extraTools.append(self.__add_spacer())

        if display == Display.PLOT:
            colourUseId = wx.NewId()
            self.AddCheckTool(colourUseId, load_bitmap('colourmap'),
                              shortHelp='Use colour maps')
            wx.EVT_TOOL(self, colourUseId, self.__on_colour_use)
            self.ToggleTool(colourUseId, self.settings.colourMapUse)
            self.extraTools.append(colourUseId)

        colours = get_colours()
        colourId = wx.NewId()
        self.colourId = wx.Choice(self, id=colourId, choices=colours)
        self.colourId.SetSelection(colours.index(self.settings.colourMap))
        self.AddControl(self.colourId)
        if display == Display.PLOT:
            self.colourId.Enable(self.settings.colourMapUse)
        self.Bind(wx.EVT_CHOICE, self.__on_colour, self.colourId)
        self.extraTools.append(colourId)

        if display == Display.SURFACE:
            self.extraTools.append(self.__add_spacer())

            wireId = wx.NewId()
            self.AddCheckTool(wireId, load_bitmap('wireframe'),
                              shortHelp='Wireframe')
            wx.EVT_TOOL(self, wireId, self.__on_check_wire)
            self.ToggleTool(wireId, self.settings.wireframe)
            self.extraTools.append(wireId)

        self.Realize()


class NavigationToolbarCompare(NavigationToolbar2WxAgg):
    def __init__(self, panel):
        NavigationToolbar2WxAgg.__init__(self, panel.get_canvas())
        self.panel = panel

        self.AddSeparator()

        gridId = wx.NewId()
        self.AddCheckTool(gridId, load_bitmap('grid'),
                          shortHelp='Toggle grid')
        self.ToggleTool(gridId, True)
        wx.EVT_TOOL(self, gridId, self.__on_check_grid)

    def __on_check_grid(self, event):
        grid = event.Checked()
        self.panel.set_grid(grid)

    def clear_auto(self):
        pass


if __name__ == '__main__':
    print 'Please run rtlsdr_scan.py'
    exit(1)

########NEW FILE########
__FILENAME__ = windows
#
# rtlsdr_scan
#
# http://eartoearoak.com/software/rtlsdr-scanner
#
# Copyright 2012 - 2014 Al Brown
#
# A frequency scanning GUI for the OsmoSDR rtl-sdr library at
# http://sdr.osmocom.org/trac/wiki/rtl-sdr
#
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import copy

from matplotlib import cm, colors
import matplotlib
from matplotlib.backends.backend_wxagg import \
    FigureCanvasWxAgg as FigureCanvas
from matplotlib.colorbar import ColorbarBase
from matplotlib.colors import Normalize
from matplotlib.ticker import AutoMinorLocator, ScalarFormatter
import wx

from constants import Display
from misc import  close_modeless
from plot import Plotter
from plot3d import Plotter3d
from plot_controls import MouseZoom, MouseSelect
from spectrogram import Spectrogram
from spectrum import split_spectrum_sort, Measure, reduce_points
from toolbars import NavigationToolbar, NavigationToolbarCompare
import wx.grid as wxGrid


class CellRenderer(wxGrid.PyGridCellRenderer):
    def __init__(self):
        wxGrid.PyGridCellRenderer.__init__(self)

    def Draw(self, grid, attr, dc, rect, row, col, _isSelected):
        dc.SetBrush(wx.Brush(attr.GetBackgroundColour()))
        dc.DrawRectangleRect(rect)
        if grid.GetCellValue(row, col) == "1":
            dc.SetBrush(wx.Brush(attr.GetTextColour()))
            dc.DrawCircle(rect.x + (rect.width / 2),
                          rect.y + (rect.height / 2),
                          rect.height / 4)


# Based on http://wiki.wxpython.org/wxGrid%20ToolTips
class GridToolTips():
    def __init__(self, grid, toolTips):
        self.lastPos = (None, None)
        self.grid = grid
        self.toolTips = toolTips

        grid.GetGridWindow().Bind(wx.EVT_MOTION, self.__on_motion)

    def __on_motion(self, event):
        x, y = self.grid.CalcUnscrolledPosition(event.GetPosition())
        row = self.grid.YToRow(y)
        col = self.grid.XToCol(x)

        if (row, col) != self.lastPos:
            if row >= 0 and col >= 0:
                self.lastPos = (row, col)
                if (row, col) in self.toolTips:
                    toolTip = self.toolTips[(row, col)]
                else:
                    toolTip = ''
                self.grid.GetGridWindow().SetToolTipString(toolTip)


class PanelGraph(wx.Panel):
    def __init__(self, panel, notify, settings, callbackMotion):
        self.panel = panel
        self.notify = notify
        self.plot = None
        self.settings = settings
        self.spectrum = None
        self.isLimited = None
        self.limit = None
        self.extent = None
        self.annotate = None

        self.mouseSelect = None
        self.mouseZoom = None
        self.measureTable = None

        self.background = None

        self.selectStart = None
        self.selectEnd = None

        self.menuClearSelect = []

        self.measure = None
        self.show = None

        self.doDraw = False

        wx.Panel.__init__(self, panel)

        self.figure = matplotlib.figure.Figure(facecolor='white')
        self.canvas = FigureCanvas(self, -1, self.figure)

        self.measureTable = PanelMeasure(self)

        self.toolbar = NavigationToolbar(self.canvas, self, settings,
                                         self.__hide_overlay)
        self.toolbar.Realize()

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.canvas, 1, wx.EXPAND)
        vbox.Add(self.measureTable, 0, wx.EXPAND)
        vbox.Add(self.toolbar, 0, wx.EXPAND)
        self.SetSizer(vbox)
        vbox.Fit(self)

        self.create_plot()

        self.canvas.mpl_connect('motion_notify_event', callbackMotion)
        self.canvas.mpl_connect('draw_event', self.__on_draw)
        self.canvas.mpl_connect('idle_event', self.__on_idle)
        self.Bind(wx.EVT_SIZE, self.__on_size)

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.__on_timer, self.timer)

    def __set_fonts(self):
        axes = self.plot.get_axes()
        axes.xaxis.label.set_size('small')
        axes.yaxis.label.set_size('small')
        if self.settings.display == Display.SURFACE:
            axes.zaxis.label.set_size('small')
        axes.tick_params(axis='both', which='major', labelsize='small')
        axes = self.plot.get_axes_bar()
        axes.tick_params(axis='both', which='major', labelsize='small')

    def __enable_menu(self, state):
        for menu in self.menuClearSelect:
            menu.Enable(state)

    def __on_size(self, event):
        ppi = wx.ScreenDC().GetPPI()
        size = [float(v) for v in self.canvas.GetSize()]
        width = size[0] / ppi[0]
        height = size[1] / ppi[1]
        self.figure.set_figwidth(width)
        self.figure.set_figheight(height)
        self.figure.set_dpi(ppi[0])
        event.Skip()

    def __on_draw(self, _event):
        axes = self.plot.get_axes()
        self.background = self.canvas.copy_from_bbox(axes.bbox)
        self.__draw_overlay()

    def __on_idle(self, _event):
        if self.doDraw and self.plot.get_plot_thread() is None:
            self.__hide_overlay()
            self.canvas.draw()
            self.doDraw = False

    def __on_timer(self, _event):
        self.timer.Stop()
        self.set_plot(None, None, None, None, self.annotate)

    def __draw_overlay(self):
        if self.background is not None:
            self.canvas.restore_region(self.background)
            self.__draw_select()
            self.draw_measure()
            self.canvas.blit(self.plot.get_axes().bbox)

    def __draw_select(self):
        if self.selectStart is not None and self.selectEnd is not None:
            self.mouseSelect.draw(self.selectStart, self.selectEnd)

    def __hide_overlay(self):
        if self.plot is not None:
            self.plot.hide_measure()
        self.__hide_select()

    def __hide_select(self):
        if self.mouseSelect is not None:
            self.mouseSelect.hide()

    def create_plot(self):
        if self.plot is not None:
            self.plot.close()

        self.toolbar.set_auto(True)

        if self.settings.display == Display.PLOT:
            self.plot = Plotter(self.notify, self.figure, self.settings)
        elif self.settings.display == Display.SPECT:
            self.plot = Spectrogram(self.notify, self.figure, self.settings)
        else:
            self.plot = Plotter3d(self.notify, self.figure, self.settings)

        self.__set_fonts()

        self.toolbar.set_plot(self.plot)
        self.toolbar.set_type(self.settings.display)
        self.measureTable.set_type(self.settings.display)

        self.set_plot_title()
        self.figure.subplots_adjust(top=0.85)
        self.redraw_plot()
        self.plot.scale_plot(True)
        self.mouseZoom = MouseZoom(self.toolbar, plot=self.plot,
                                   callbackHide=self.__hide_overlay)
        self.mouseSelect = MouseSelect(self.plot, self.on_select,
                                       self.on_selected)
        self.measureTable.show(self.settings.showMeasure)
        self.panel.SetFocus()

    def on_select(self):
        self.hide_measure()

    def on_selected(self, start, end):
        self.__enable_menu(True)
        self.selectStart = start
        self.selectEnd = end
        self.measureTable.set_selected(self.spectrum, start, end)

    def add_menu_clear_select(self, menu):
        self.menuClearSelect.append(menu)
        menu.Enable(False)

    def draw(self):
        self.doDraw = True

    def show_measure_table(self, show):
        self.measureTable.show(show)
        self.Layout()

    def set_plot(self, spectrum, isLimited, limit, extent, annotate=False):
        if spectrum is not None and extent is not None:
            if isLimited is not None and limit is not None:
                self.spectrum = copy.copy(spectrum)
                self.extent = extent
                self.annotate = annotate
                self.isLimited = isLimited
                self.limit = limit

        if self.plot.get_plot_thread() is None:
            self.timer.Stop()
            self.measureTable.set_selected(self.spectrum, self.selectStart,
                                           self.selectEnd)
            if isLimited:
                spectrum = reduce_points(spectrum, limit)
            self.plot.set_plot(self.spectrum, self.extent, annotate)

        else:
            self.timer.Start(200, oneShot=True)

    def set_plot_title(self):
        if len(self.settings.devicesRtl) > 0:
            gain = self.settings.devicesRtl[self.settings.indexRtl].gain
        else:
            gain = 0
        self.plot.set_title("Frequency Spectrogram\n{0} - {1} MHz,"
                            " gain = {2}dB".format(self.settings.start,
                                                   self.settings.stop, gain))

    def redraw_plot(self):
        if self.spectrum is not None:
            self.set_plot(self.spectrum,
                          self.settings.pointsLimit,
                          self.settings.pointsMax,
                          self.extent, self.settings.annotate)

    def set_grid(self, on):
        self.plot.set_grid(on)

    def hide_measure(self):
        if self.plot is not None:
            self.plot.hide_measure()

    def draw_measure(self):
        if self.measure is not None and self.measure.is_valid():
            self.plot.draw_measure(self.measure, self.show)

    def update_measure(self, measure, show):
        self.measure = measure
        self.show = show
        self.__draw_overlay()

    def get_figure(self):
        return self.figure

    def get_axes(self):
        return self.plot.get_axes()

    def get_canvas(self):
        return self.canvas

    def get_toolbar(self):
        return self.toolbar

    def scale_plot(self, force=False):
        self.plot.scale_plot(force)

    def clear_plots(self):
        self.plot.clear_plots()
        self.spectrum = None
        self.doDraw = True

    def clear_selection(self):
        self.measure = None
        self.measureTable.clear_measurement()
        self.selectStart = None
        self.selectEnd = None
        self.mouseSelect.clear()
        self.__enable_menu(False)

    def close(self):
        close_modeless()


class PanelGraphCompare(wx.Panel):
    def __init__(self, parent, callback):
        self.callback = callback

        self.spectrum1 = None
        self.spectrum2 = None
        self.spectrumDiff = None

        self.mouseZoom = None

        formatter = ScalarFormatter(useOffset=False)

        wx.Panel.__init__(self, parent)

        figure = matplotlib.figure.Figure(facecolor='white')
        figure.set_size_inches(8, 4.5)
        figure.set_tight_layout(True)

        self.axesScan = figure.add_subplot(111)
        self.axesScan.xaxis.set_minor_locator(AutoMinorLocator(10))
        self.axesScan.yaxis.set_minor_locator(AutoMinorLocator(10))
        self.axesScan.xaxis.set_major_formatter(formatter)
        self.axesScan.yaxis.set_major_formatter(formatter)
        self.axesDiff = self.axesScan.twinx()
        self.axesDiff.yaxis.set_minor_locator(AutoMinorLocator(10))
        self.plotScan1, = self.axesScan.plot([], [], 'b-',
                                                     linewidth=0.4)
        self.plotScan2, = self.axesScan.plot([], [], 'g-',
                                                     linewidth=0.4)
        self.plotDiff, = self.axesDiff.plot([], [], 'r-', linewidth=0.4)
        self.axesScan.set_ylim(auto=True)
        self.axesDiff.set_ylim(auto=True)

        self.axesScan.set_title("Level Comparison")
        self.axesScan.set_xlabel("Frequency (MHz)")
        self.axesScan.set_ylabel('Level ($\mathsf{dB/\sqrt{Hz}}$)')
        self.axesDiff.set_ylabel('Difference ($\mathsf{dB/\sqrt{Hz}}$)')

        self.canvas = FigureCanvas(self, -1, figure)

        self.set_grid(True)

        self.textIntersect = wx.StaticText(self, label="Intersections: ")

        toolbar = NavigationToolbarCompare(self)
        toolbar.Realize()
        self.mouseZoom = MouseZoom(toolbar, figure=figure)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.canvas, 1, wx.LEFT | wx.TOP | wx.GROW)
        vbox.Add(self.textIntersect, 0, wx.EXPAND | wx.ALL, border=5)
        vbox.Add(toolbar, 0, wx.EXPAND)

        self.SetSizer(vbox)
        vbox.Fit(self)

        self.canvas.mpl_connect('motion_notify_event', self.__on_motion)

    def __on_motion(self, event):
        xpos = event.xdata
        ypos = event.ydata
        if xpos is None or ypos is  None:
            return

        locs = dict.fromkeys(['x1', 'y1', 'x2', 'y2', 'x3', 'y3'], None)

        if self.spectrum1 is not None and len(self.spectrum1) > 0:
            locs['x1'] = min(self.spectrum1.keys(),
                             key=lambda freq: abs(freq - xpos))
            locs['y1'] = self.spectrum1[locs['x1']]

        if self.spectrum2 is not None and len(self.spectrum2) > 0:
            locs['x2'] = min(self.spectrum2.keys(),
                             key=lambda freq: abs(freq - xpos))
            locs['y2'] = self.spectrum2[locs['x2']]

        if self.spectrumDiff is not None and len(self.spectrumDiff) > 0:
            locs['x3'] = min(self.spectrumDiff.keys(),
                             key=lambda freq: abs(freq - xpos))
            locs['y3'] = self.spectrumDiff[locs['x3']]

        self.callback(locs)

    def __relim(self):
        self.axesScan.relim()
        self.axesDiff.relim()

    def __plot_diff(self):
        diff = {}
        intersections = 0

        if self.spectrum1 is not None and self.spectrum2 is not None:
            set1 = set(self.spectrum1)
            set2 = set(self.spectrum2)
            intersect = set1.intersection(set2)
            intersections = len(intersect)
            for freq in intersect:
                diff[freq] = self.spectrum1[freq] - self.spectrum2[freq]
            freqs, powers = split_spectrum_sort(diff)
            self.plotDiff.set_xdata(freqs)
            self.plotDiff.set_ydata(powers)
        elif self.spectrum1 is None:
            freqs, powers = split_spectrum_sort(self.spectrum2)
            intersections = len(freqs)
            self.plotDiff.set_xdata(freqs)
            self.plotDiff.set_ydata([0] * intersections)
        else:
            freqs, powers = split_spectrum_sort(self.spectrum1)
            intersections = len(freqs)
            self.plotDiff.set_xdata(freqs)
            self.plotDiff.set_ydata([0] * intersections)

        self.spectrumDiff = diff

        self.textIntersect.SetLabel('Intersections: {0}'.format(intersections))

    def get_canvas(self):
        return self.canvas

    def show_plot1(self, enable):
        self.plotScan1.set_visible(enable)
        self.canvas.draw()

    def show_plot2(self, enable):
        self.plotScan2.set_visible(enable)
        self.canvas.draw()

    def show_plotdiff(self, enable):
        self.plotDiff.set_visible(enable)
        self.canvas.draw()

    def set_spectrum1(self, spectrum):
        timeStamp = max(spectrum)
        self.spectrum1 = spectrum[timeStamp]
        freqs, powers = split_spectrum_sort(self.spectrum1)
        self.plotScan1.set_xdata(freqs)
        self.plotScan1.set_ydata(powers)
        self.__plot_diff()
        self.__relim()
        self.autoscale()

    def set_spectrum2(self, spectrum):
        timeStamp = max(spectrum)
        self.spectrum2 = spectrum[timeStamp]
        freqs, powers = split_spectrum_sort(self.spectrum2)
        self.plotScan2.set_xdata(freqs)
        self.plotScan2.set_ydata(powers)
        self.__plot_diff()
        self.__relim()
        self.autoscale()

    def set_grid(self, grid):
        self.axesScan.grid(grid)
        self.canvas.draw()

    def autoscale(self):
        self.axesScan.autoscale_view()
        self.axesDiff.autoscale_view()
        self.canvas.draw()


class PanelColourBar(wx.Panel):
    def __init__(self, parent, colourMap):
        wx.Panel.__init__(self, parent)
        dpi = wx.ScreenDC().GetPPI()[0]
        figure = matplotlib.figure.Figure(facecolor='white', dpi=dpi)
        figure.set_size_inches(200.0 / dpi, 25.0 / dpi)
        self.canvas = FigureCanvas(self, -1, figure)
        axes = figure.add_subplot(111)
        figure.subplots_adjust(0, 0, 1, 1)
        norm = Normalize(vmin=0, vmax=1)
        self.bar = ColorbarBase(axes, norm=norm, orientation='horizontal',
                                cmap=cm.get_cmap(colourMap))
        axes.xaxis.set_visible(False)

    def set_map(self, colourMap):
        self.bar.set_cmap(colourMap)
        self.bar.changed()
        self.bar.draw_all()
        self.canvas.draw()


class PanelLine(wx.Panel):
    def __init__(self, parent, colour):
        self.colour = colour

        wx.Panel.__init__(self, parent)
        self.Bind(wx.EVT_PAINT, self.__on_paint)

    def __on_paint(self, _event):
        dc = wx.BufferedPaintDC(self)
        width, height = self.GetClientSize()
        if not width or not height:
            return

        pen = wx.Pen(self.colour, 2)
        dc.SetPen(pen)
        colourBack = self.GetBackgroundColour()
        brush = wx.Brush(colourBack, wx.SOLID)
        dc.SetBackground(brush)

        dc.Clear()
        dc.DrawLine(0, height / 2., width, height / 2.)


class PanelMeasure(wx.Panel):
    def __init__(self, graph):
        wx.Panel.__init__(self, graph)

        self.graph = graph

        self.measure = None

        self.checked = {Measure.MIN: None,
                        Measure.MAX: None,
                        Measure.AVG: None,
                        Measure.GMEAN: None,
                        Measure.HBW: None,
                        Measure.OBW: None}

        self.selected = None

        self.SetBackgroundColour('white')

        self.grid = wxGrid.Grid(self)
        self.grid.CreateGrid(3, 19)
        self.grid.EnableEditing(False)
        self.grid.EnableDragGridSize(False)
        self.grid.SetColLabelSize(1)
        self.grid.SetRowLabelSize(1)
        self.grid.SetColMinimalAcceptableWidth(1)
        self.grid.SetColSize(2, 1)
        self.grid.SetColSize(7, 1)
        self.grid.SetColSize(11, 1)
        self.grid.SetColSize(15, 1)
        self.grid.SetMargins(0, wx.SystemSettings_GetMetric(wx.SYS_HSCROLL_Y))

        for x in xrange(self.grid.GetNumberRows()):
            self.grid.SetRowLabelValue(x, '')
        for y in xrange(self.grid.GetNumberCols()):
            self.grid.SetColLabelValue(y, '')

        self.locsDesc = {'F Start': (0, 0),
                         'F End': (1, 0),
                         'F Delta': (2, 0),
                         'P Min': (0, 4),
                         'P Max': (1, 4),
                         'P Delta': (2, 4),
                         'Mean': (0, 9),
                         'GMean': (1, 9),
                         'Flatness': (2, 9),
                         '-3dB Start': (0, 13),
                         '-3dB End': (1, 13),
                         '-3dB Delta': (2, 13),
                         'OBW Start': (0, 17),
                         'OBW End': (1, 17),
                         'OBW Delta': (2, 17)}
        self.__set_descs()

        self.locsCheck = {Measure.MIN: (0, 3), Measure.MAX: (1, 3),
                          Measure.AVG: (0, 8), Measure.GMEAN: (1, 8),
                          Measure.HBW: (0, 12),
                          Measure.OBW: (0, 16)}
        self.__set_check_editor()

        colour = self.grid.GetBackgroundColour()
        self.grid.SetCellTextColour(2, 3, colour)
        self.grid.SetCellTextColour(2, 8, colour)
        self.grid.SetCellTextColour(1, 12, colour)
        self.grid.SetCellTextColour(2, 12, colour)
        self.grid.SetCellTextColour(1, 16, colour)
        self.grid.SetCellTextColour(2, 16, colour)

        self.__clear_checks()

        self.locsMeasure = {'start': (0, 1), 'end': (1, 1), 'deltaF': (2, 1),
                            'minFP': (0, 5), 'maxFP': (1, 5), 'deltaFP': (2, 5),
                            'minP': (0, 6), 'maxP': (1, 6), 'deltaP': (2, 6),
                            'avg': (0, 10), 'gmean': (1, 10), 'flat': (2, 10),
                            'hbwstart': (0, 14), 'hbwend': (1, 14), 'hbwdelta': (2, 14),
                            'obwstart': (0, 18), 'obwend': (1, 18), 'obwdelta': (2, 18)}

        fontCell = self.grid.GetDefaultCellFont()
        fontSize = fontCell.GetPointSize()
        fontStyle = fontCell.GetStyle()
        fontWeight = fontCell.GetWeight()
        font = wx.Font(fontSize, wx.FONTFAMILY_MODERN, fontStyle,
                       fontWeight)
        dc = wx.WindowDC(self.grid)
        dc.SetFont(font)
        widthMHz = dc.GetTextExtent('###.######')[0] * 1.2
        widthdB = dc.GetTextExtent('-##.##')[0] * 1.2
        for _desc, (_row, col) in self.locsDesc.iteritems():
            self.grid.AutoSizeColumn(col)
        for col in [1, 5, 14, 18]:
            self.grid.SetColSize(col, widthMHz)
            for row in xrange(self.grid.GetNumberRows()):
                self.grid.SetCellFont(row, col, font)
        for col in [6, 10]:
            self.grid.SetColSize(col, widthdB)
            for row in xrange(self.grid.GetNumberRows()):
                self.grid.SetCellFont(row, col, font)
        for _desc, (_row, col) in self.locsCheck.iteritems():
            self.grid.AutoSizeColumn(col)

        toolTips = {}
        toolTips[self.locsMeasure['start']] = 'Selection start (MHz)'
        toolTips[self.locsMeasure['end']] = 'Selection end (MHz)'
        toolTips[self.locsMeasure['deltaF']] = 'Selection bandwidth (MHz)'
        toolTips[self.locsMeasure['minFP']] = 'Minimum power location (MHz)'
        toolTips[self.locsMeasure['maxFP']] = 'Maximum power location (MHz)'
        toolTips[self.locsMeasure['deltaFP']] = 'Power location difference (MHz)'
        toolTips[self.locsMeasure['minP']] = 'Minimum power (dB)'
        toolTips[self.locsMeasure['maxP']] = 'Maximum power (dB)'
        toolTips[self.locsMeasure['deltaP']] = 'Power difference (dB)'
        toolTips[self.locsMeasure['avg']] = 'Mean power (dB)'
        toolTips[self.locsMeasure['gmean']] = 'Geometric mean power (dB)'
        toolTips[self.locsMeasure['flat']] = 'Spectral flatness'
        toolTips[self.locsMeasure['hbwstart']] = '-3db start location (MHz)'
        toolTips[self.locsMeasure['hbwend']] = '-3db end location (MHz)'
        toolTips[self.locsMeasure['hbwdelta']] = '-3db bandwidth (MHz)'
        toolTips[self.locsMeasure['obwstart']] = '99% start location (MHz)'
        toolTips[self.locsMeasure['obwend']] = '99% end location (MHz)'
        toolTips[self.locsMeasure['obwdelta']] = '99% bandwidth (MHz)'

        self.toolTips = GridToolTips(self.grid, toolTips)

        self.popupMenu = wx.Menu()
        self.popupMenuCopy = self.popupMenu.Append(wx.ID_ANY, "&Copy",
                                                   "Copy entry")
        self.Bind(wx.EVT_MENU, self.__on_copy, self.popupMenuCopy)

        self.Bind(wxGrid.EVT_GRID_CELL_RIGHT_CLICK, self.__on_popup_menu)
        self.Bind(wxGrid.EVT_GRID_CELL_LEFT_CLICK, self.__on_cell_click)

        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(self.grid, 0, wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT,
                border=10)
        self.SetSizer(box)

    def __set_descs(self):
        font = self.grid.GetCellFont(0, 0)
        font.SetWeight(wx.BOLD)

        for desc, (row, col) in self.locsDesc.iteritems():
            self.grid.SetCellValue(row, col, desc)
            self.grid.SetCellFont(row, col, font)

    def __set_check_editor(self):
        editor = wxGrid.GridCellBoolEditor()
        for _desc, (row, col) in self.locsCheck.iteritems():
            self.grid.SetCellEditor(row, col, editor)
            self.grid.SetCellAlignment(row, col, wx.ALIGN_RIGHT, wx.ALIGN_CENTRE)
            self.grid.SetColFormatBool(col)

    def __set_check_value(self, cell, value):
        (row, col) = self.locsCheck[cell]
        self.grid.SetCellValue(row, col, value)

    def __set_measure_value(self, cell, value):
        (row, col) = self.locsMeasure[cell]
        self.grid.SetCellValue(row, col, value)

    def __set_check_read_only(self, cell, readOnly):
        (row, col) = self.locsCheck[cell]
        self.grid.SetReadOnly(row, col, readOnly)
        if readOnly:
            colour = 'grey'
        else:
            colour = self.grid.GetDefaultCellTextColour()

        self.grid.SetCellTextColour(row, col, colour)

    def __get_checks(self):
        checks = {}
        for cell in self.checked:
            if self.checked[cell] == '1':
                checks[cell] = True
            else:
                checks[cell] = False

        return checks

    def __update_checks(self):
        for cell in self.checked:
            self.__set_check_value(cell, self.checked[cell])

    def __clear_checks(self):
        for cell in self.checked:
            self.checked[cell] = '0'
        self.__update_checks()

    def __on_cell_click(self, event):
        self.grid.ClearSelection()
        row = event.GetRow()
        col = event.GetCol()

        if (row, col) in self.locsCheck.values():
            if not self.grid.IsReadOnly(row, col) and self.measure is not None:
                check = self.grid.GetCellValue(row, col)
                if check == '1':
                    check = '0'
                else:
                    check = '1'
                self.grid.SetCellValue(row, col, check)

                for control, (r, c) in self.locsCheck.iteritems():
                    if (r, c) == (row, col):
                        self.checked[control] = check

                if self.selected is None:
                    self.selected = self.locsMeasure['start']
                    row = self.selected[0]
                    col = self.selected[1]
                    self.grid.SetGridCursor(row, col)
                self.update_measure()

        elif (row, col) in self.locsMeasure.itervalues():
            self.selected = (row, col)
            self.grid.SetGridCursor(row, col)
        elif self.selected is None:
            self.selected = self.locsMeasure['start']
            row = self.selected[0]
            col = self.selected[1]
            self.grid.SetGridCursor(row, col)

    def __on_popup_menu(self, _event):
        if self.selected:
            self.popupMenuCopy.Enable(True)
        else:
            self.popupMenuCopy.Enable(False)
        self.PopupMenu(self.popupMenu)

    def __on_copy(self, _event):
        value = self.grid.GetCellValue(self.selected[0], self.selected[1])
        clip = wx.TextDataObject(value)
        wx.TheClipboard.Open()
        wx.TheClipboard.SetData(clip)
        wx.TheClipboard.Close()

    def update_measure(self):
        show = self.__get_checks()
        self.graph.update_measure(self.measure, show)

    def clear_measurement(self):
        for control in self.locsMeasure:
            self.__set_measure_value(control, "")
        self.update_measure()
        self.measure = None

    def set_selected(self, spectrum, start, end):
        self.measure = Measure(spectrum, start, end)
        if not self.measure.is_valid():
            self.clear_measurement()
            return

        minF, maxF = self.measure.get_f()
        minP = self.measure.get_min_p()
        maxP = self.measure.get_max_p()
        avgP = self.measure.get_avg_p()
        gMeanP = self.measure.get_gmean_p()
        flatness = self.measure.get_flatness()
        hbw = self.measure.get_hpw()
        obw = self.measure.get_obw()

        self.__set_measure_value('start',
                               "{0:10.6f}".format(minF))
        self.__set_measure_value('end',
                               "{0:10.6f}".format(maxF))
        self.__set_measure_value('deltaF',
                               "{0:10.6f}".format(maxF - minF))

        self.__set_measure_value('minFP',
                               "{0:10.6f}".format(minP[0]))
        self.__set_measure_value('maxFP',
                               "{0:10.6f}".format(maxP[0]))
        self.__set_measure_value('deltaFP',
                               "{0:10.6f}".format(maxP[0] - minP[0]))
        self.__set_measure_value('minP',
                               "{0:6.2f}".format(minP[1]))
        self.__set_measure_value('maxP',
                               "{0:6.2f}".format(maxP[1]))
        self.__set_measure_value('deltaP',
                               "{0:6.2f}".format(maxP[1] - minP[1]))

        self.__set_measure_value('avg',
                               "{0:6.2f}".format(avgP))
        self.__set_measure_value('gmean',
                               "{0:6.2f}".format(gMeanP))
        self.__set_measure_value('flat',
                               "{0:.4f}".format(flatness))

        if hbw[0] is not None:
            text = "{0:10.6f}".format(hbw[0])
        else:
            text = ''
        self.__set_measure_value('hbwstart', text)
        if hbw[1] is not None:
            text = "{0:10.6f}".format(hbw[1])
        else:
            text = ''
        self.__set_measure_value('hbwend', text)
        if hbw[0] is not None and hbw[1] is not None:
            text = "{0:10.6f}".format(hbw[1] - hbw[0])
        else:
            text = ''
        self.__set_measure_value('hbwdelta', text)

        if obw[0] is not None:
            text = "{0:10.6f}".format(obw[0])
        else:
            text = ''
        self.__set_measure_value('obwstart', text)
        if obw[1] is not None:
            text = "{0:10.6f}".format(obw[1])
        else:
            text = ''
        self.__set_measure_value('obwend', text)
        if obw[0] is not None and obw[1] is not None:
            text = "{0:10.6f}".format(obw[1] - obw[0])
        else:
            text = ''
        self.__set_measure_value('obwdelta', text)

        self.update_measure()

    def show(self, show):
        if show:
            self.Show()
        else:
            self.Hide()
        self.Layout()

    def set_type(self, display):
        for cell in self.locsCheck:
            self.__set_check_read_only(cell, True)
        if display == Display.PLOT:
            for cell in self.locsCheck:
                self.__set_check_read_only(cell, False)
        elif display == Display.SPECT:
            self.__set_check_read_only(Measure.HBW, False)
            self.__set_check_read_only(Measure.OBW, False)

        self.grid.Refresh()


if __name__ == '__main__':
    print 'Please run rtlsdr_scan.py'
    exit(1)

########NEW FILE########
