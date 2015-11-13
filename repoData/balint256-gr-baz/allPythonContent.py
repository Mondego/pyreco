__FILENAME__ = am_fft
#!/usr/bin/env python
#
# Copyright 2004,2005,2007,2008,2010 Free Software Foundation, Inc.
# 
# This file is part of GNU Radio
# 
# GNU Radio is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# GNU Radio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with GNU Radio; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
# 

# usrp_fft.py modified for AM by Balint Seeber (http://wiki.spench.net/wiki/gr-baz)

from gnuradio import gr, gru
from gnuradio import usrp
from gnuradio import eng_notation
from gnuradio.eng_option import eng_option
from gnuradio.wxgui import stdgui2, fftsink2, waterfallsink2, scopesink2, form, slider
from optparse import OptionParser
import wx
import sys
import numpy

def pick_subdevice(u):
    """
    The user didn't specify a subdevice on the command line.
    If there's a daughterboard on A, select A.
    If there's a daughterboard on B, select B.
    Otherwise, select A.
    """
    if u.db(0, 0).dbid() >= 0:       # dbid is < 0 if there's no d'board or a problem
        return (0, 0)
    if u.db(1, 0).dbid() >= 0:
        return (1, 0)
    return (0, 0)


class app_top_block(stdgui2.std_top_block):
    def __init__(self, frame, panel, vbox, argv):
        stdgui2.std_top_block.__init__(self, frame, panel, vbox, argv)

        self.frame = frame
        self.panel = panel
        
        parser = OptionParser(option_class=eng_option)
        parser.add_option("-w", "--which", type="int", default=0,
                          help="select which USRP (0, 1, ...) default is %default", metavar="NUM")
        parser.add_option("-R", "--rx-subdev-spec", type="subdev", default=None,
                          help="select USRP Rx side A or B (default=first one with a daughterboard)")
        parser.add_option("-A", "--antenna", default=None,
                          help="select Rx Antenna (only on RFX-series boards)")
        parser.add_option("-d", "--decim", type="int", default=16,
                          help="set fgpa decimation rate to DECIM [default=%default]")
        parser.add_option("-f", "--freq", type="eng_float", default=None,
                          help="set frequency to FREQ", metavar="FREQ")
        parser.add_option("-g", "--gain", type="eng_float", default=None,
                          help="set gain in dB [default is midpoint]")
        parser.add_option("-W", "--waterfall", action="store_true", default=False,
                          help="Enable waterfall display")
        parser.add_option("-8", "--width-8", action="store_true", default=False,
                          help="Enable 8-bit samples across USB")
        parser.add_option( "--no-hb", action="store_true", default=False,
                          help="don't use halfband filter in usrp")
        parser.add_option("-S", "--oscilloscope", action="store_true", default=False,
                          help="Enable oscilloscope display")
        parser.add_option("", "--avg-alpha", type="eng_float", default=1e-1,
                          help="Set fftsink averaging factor, [default=%default]")
        parser.add_option("", "--ref-scale", type="eng_float", default=13490.0,
                          help="Set dBFS=0dB input value, [default=%default]")
        parser.add_option("", "--fft-size", type="int", default=1024,
                          help="Set FFT frame size, [default=%default]");

        (options, args) = parser.parse_args()
        if len(args) != 0:
            parser.print_help()
            sys.exit(1)
        self.options = options
        self.show_debug_info = True
        
        # build the graph
        if options.no_hb or (options.decim<8):
          #Min decimation of this firmware is 4. 
          #contains 4 Rx paths without halfbands and 0 tx paths.
          self.fpga_filename="std_4rx_0tx.rbf"
          self.u = usrp.source_c(which=options.which, decim_rate=options.decim, fpga_filename=self.fpga_filename)
        else:
          #Min decimation of standard firmware is 8. 
          #standard fpga firmware "std_2rxhb_2tx.rbf" 
          #contains 2 Rx paths with halfband filters and 2 tx paths (the default)
          self.u = usrp.source_c(which=options.which, decim_rate=options.decim)

        if options.rx_subdev_spec is None:
            options.rx_subdev_spec = pick_subdevice(self.u)
        self.u.set_mux(usrp.determine_rx_mux_value(self.u, options.rx_subdev_spec))

        if options.width_8:
            width = 8
            shift = 8
            format = self.u.make_format(width, shift)
            print "format =", hex(format)
            r = self.u.set_format(format)
            print "set_format =", r
            
        # determine the daughterboard subdevice we're using
        self.subdev = usrp.selected_subdev(self.u, options.rx_subdev_spec)

        input_rate = self.u.adc_freq() / self.u.decim_rate()

        if options.waterfall:
            self.scope = \
              waterfallsink2.waterfall_sink_f (panel, fft_size=options.fft_size, sample_rate=input_rate)
        elif options.oscilloscope:
            self.scope = scopesink2.scope_sink_f(panel, sample_rate=input_rate)	#v_scale, t_scale, v_offset, frame_rate
        else:
            self.scope = fftsink2.fft_sink_f (panel, fft_size=options.fft_size, sample_rate=input_rate, 
                ref_scale=options.ref_scale, ref_level=0.0, y_divs = 10, avg_alpha=options.avg_alpha)

        self.MAG = gr.complex_to_mag()	# AM
        self.connect(self.u, self.MAG, self.scope)

        self._build_gui(vbox)
        self._setup_events()

        # set initial values

        if options.gain is None:
            # if no gain was specified, use the mid-point in dB
            g = self.subdev.gain_range()
            options.gain = float(g[0]+g[1])/2

        if options.freq is None:
            # if no freq was specified, use the mid-point
            r = self.subdev.freq_range()
            options.freq = float(r[0]+r[1])/2

        self.set_gain(options.gain)

        if options.antenna is not None:
            #print "Selecting antenna %s" % (options.antenna,)
            #self.subdev.select_rx_antenna(options.antenna)
            self.set_antenna(options.antenna)

        if self.show_debug_info:
            self.myform['decim'].set_value(self.u.decim_rate())
            self.myform['fs@usb'].set_value(self.u.adc_freq() / self.u.decim_rate())
            self.myform['dbname'].set_value(self.subdev.name())
            self.myform['baseband'].set_value(0)
            self.myform['ddc'].set_value(0)

        if not(self.set_freq(options.freq)):
            self._set_status_msg("Failed to set initial frequency")

    def _set_status_msg(self, msg):
        self.frame.GetStatusBar().SetStatusText(msg, 0)

    def _build_gui(self, vbox):

        def _form_set_freq(kv):
            return self.set_freq(kv['freq'])
            
        vbox.Add(self.scope.win, 1, wx.EXPAND)	# Proportion used to be 10
        
        # add control area at the bottom
        self.myform = myform = form.form()
        hbox = wx.BoxSizer(wx.HORIZONTAL)	# Create row sizer

        hbox.Add((5,0), 0, 0)

        myform['freq'] = form.float_field(
            parent=self.panel, sizer=hbox, label="Center freq", weight=1,
            callback=myform.check_input_and_call(_form_set_freq, self._set_status_msg))

        myform['antenna'] = form.radiobox_field(parent=self.panel, sizer=hbox, label="Antenna",
            value=None, callback=self.set_antenna_callback,
            choices=["TX/RX", "RX2", "RXA", "RXB", "RXAB"],major_dimension=5, weight=3)

        hbox.Add((5,0), 0, 0)

        g = self.subdev.gain_range()
        myform['gain'] = form.slider_field(parent=self.panel, sizer=hbox, label="Gain",
                                           weight=6, # 3
                                           min=int(g[0]), max=int(g[1]),
                                           callback=self.set_gain)

        hbox.Add((5,0), 0, 0)

        vbox.Add(hbox, 0, wx.EXPAND)

        self._build_subpanel(vbox)
    
    def set_antenna_callback(self, antenna):
        self.set_antenna(antenna, False)
    
    def set_antenna(self, antenna, gui_update=True):
        print "Antenna:", antenna
        self.subdev.select_rx_antenna(str(antenna))
        if gui_update:
            self.myform['antenna'].set_value(antenna)

    def _build_subpanel(self, vbox_arg):
        # build a secondary information panel (sometimes hidden)

        # FIXME figure out how to have this be a subpanel that is always
        # created, but has its visibility controlled by foo.Show(True/False)
        
        def _form_set_decim(kv):
            return self.set_decim(kv['decim'])

        if not(self.show_debug_info):
            return

        panel = self.panel
        vbox = vbox_arg
        myform = self.myform

        #panel = wx.Panel(self.panel, -1)
        #vbox = wx.BoxSizer(wx.VERTICAL)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add((5,0), 0)

        myform['decim'] = form.int_field(
            parent=panel, sizer=hbox, label="Decim",
            callback=myform.check_input_and_call(_form_set_decim, self._set_status_msg))

        hbox.Add((5,0), 1)
        myform['fs@usb'] = form.static_float_field(
            parent=panel, sizer=hbox, label="Fs@USB")

        hbox.Add((5,0), 1)
        myform['dbname'] = form.static_text_field(
            parent=panel, sizer=hbox)

        hbox.Add((5,0), 1)
        myform['baseband'] = form.static_float_field(
            parent=panel, sizer=hbox, label="Analog BB")

        hbox.Add((5,0), 1)
        myform['ddc'] = form.static_float_field(
            parent=panel, sizer=hbox, label="DDC")

        hbox.Add((5,0), 0)
	
        vbox.Add(hbox, 0, wx.EXPAND)

        
    def set_freq(self, target_freq):
        """
        Set the center frequency we're interested in.

        @param target_freq: frequency in Hz
        @rypte: bool

        Tuning is a two step process.  First we ask the front-end to
        tune as close to the desired frequency as it can.  Then we use
        the result of that operation and our target_frequency to
        determine the value for the digital down converter.
        """
        r = self.u.tune(0, self.subdev, target_freq)
        
        if r:
            self.myform['freq'].set_value(target_freq)     # update displayed value
            if self.show_debug_info:
                self.myform['baseband'].set_value(r.baseband_freq)
                self.myform['ddc'].set_value(r.dxc_freq)
	    if not self.options.oscilloscope:
		self.scope.set_baseband_freq(target_freq)
    	    return True

        return False

    def set_gain(self, gain):
        self.myform['gain'].set_value(gain)     # update displayed value
        self.subdev.set_gain(gain)

    def set_decim(self, decim):
        ok = self.u.set_decim_rate(decim)
        if not ok:
            print "set_decim failed"
        input_rate = self.u.adc_freq() / self.u.decim_rate()
        self.scope.set_sample_rate(input_rate)
        if self.show_debug_info:  # update displayed values
            self.myform['decim'].set_value(self.u.decim_rate())
            self.myform['fs@usb'].set_value(self.u.adc_freq() / self.u.decim_rate())
        return ok

    def _setup_events(self):
	if not self.options.waterfall and not self.options.oscilloscope:
	    self.scope.win.Bind(wx.EVT_LEFT_DCLICK, self.evt_left_dclick)
	    
    def evt_left_dclick(self, event):
	(ux, uy) = self.scope.win.GetXY(event)
	if event.CmdDown():
	    # Re-center on maximum power
	    points = self.scope.win._points
	    if self.scope.win.peak_hold:
		if self.scope.win.peak_vals is not None:
		    ind = numpy.argmax(self.scope.win.peak_vals)
		else:
		    ind = int(points.shape()[0]/2)
	    else:
        	ind = numpy.argmax(points[:,1])
            (freq, pwr) = points[ind]
	    target_freq = freq/self.scope.win._scale_factor
	    print ind, freq, pwr
            self.set_freq(target_freq)            
	else:
	    # Re-center on clicked frequency
	    target_freq = ux/self.scope.win._scale_factor
	    self.set_freq(target_freq)
	    

def main ():
    app = stdgui2.stdapp(app_top_block, "USRP AM FFT/Scope", nstatus=1)
    app.MainLoop()

if __name__ == '__main__':
    main ()

########NEW FILE########
__FILENAME__ = borip_RTL
#!/usr/bin/env python
##################################################
# Gnuradio Python Flow Graph
# Title: Borip Rtl
# Generated: Sun Jun  3 21:31:43 2012
##################################################

from gnuradio import eng_notation
from gnuradio import gr
from gnuradio.eng_option import eng_option
from gnuradio import filter 
from gnuradio.filter import firdes
from optparse import OptionParser
import baz

class borip_RTL(gr.top_block):

	def __init__(self, tuner="", buf=True, readlen=0):
		gr.top_block.__init__(self, "Borip Rtl")

		##################################################
		# Parameters
		##################################################
		self.tuner = tuner
		self.buf = buf
		self.readlen = readlen

		##################################################
		# Variables
		##################################################
		self.master_clock = master_clock = 3200000

		##################################################
		# Message Queues
		##################################################
		source_msgq_out = sink_msgq_in = gr.msg_queue(2)

		##################################################
		# Blocks
		##################################################
		self.sink = baz.udp_sink(gr.sizeof_short*1, "127.0.0.1", 28888, 1472, False, True)
		self.sink.set_status_msgq(sink_msgq_in)
		self.source = baz.rtl_source_c(defer_creation=True, output_size=gr.sizeof_short)
		self.source.set_verbose(True)
		self.source.set_vid(0x0)
		self.source.set_pid(0x0)
		self.source.set_tuner_name(tuner)
		self.source.set_default_timeout(0)
		self.source.set_use_buffer(buf)
		self.source.set_fir_coefficients(([]))
		
		self.source.set_read_length(0)
		
		
		
		
		if self.source.create() == False: raise Exception("Failed to create RTL2832 Source: source")
		
		
		self.source.set_sample_rate(1000000)
		
		self.source.set_frequency(0)
		
		
		self.source.set_status_msgq(source_msgq_out)
		
		self.source.set_auto_gain_mode(False)
		self.source.set_relative_gain(False)
		self.source.set_gain(0)
		  

		##################################################
		# Connections
		##################################################
		self.connect((self.source, 0), (self.sink, 0))

	def set_tuner(self, tuner):
		self.tuner = tuner

	def set_buf(self, buf):
		self.buf = buf

	def set_readlen(self, readlen):
		self.readlen = readlen

	def set_master_clock(self, master_clock):
		self.master_clock = master_clock

if __name__ == '__main__':
	parser = OptionParser(option_class=eng_option, usage="%prog: [options]")
	parser.add_option("", "--tuner", dest="tuner", type="string", default="",
		help="Set Tuner [default=%default]")
	parser.add_option("", "--readlen", dest="readlen", type="intx", default=0,
		help="Set ReadLen [default=%default]")
	(options, args) = parser.parse_args()
	tb = borip_RTL(tuner=options.tuner, readlen=options.readlen)
	tb.start()
	raw_input('Press Enter to quit: ')
	tb.stop()


########NEW FILE########
__FILENAME__ = borip_RTL2
#!/usr/bin/env python
##################################################
# Gnuradio Python Flow Graph
# Title: Borip Rtl2
# Generated: Mon May 28 17:08:30 2012
##################################################

from gnuradio import eng_notation
from gnuradio import gr
from gnuradio.eng_option import eng_option
from gnuradio import filter 
from gnuradio.filter import firdes
from optparse import OptionParser
import baz

class borip_RTL2(gr.top_block):

	def __init__(self, buf=True, tuner=""):
		gr.top_block.__init__(self, "Borip Rtl2")

		##################################################
		# Parameters
		##################################################
		self.buf = buf
		self.tuner = tuner

		##################################################
		# Variables
		##################################################
		self.master_clock = master_clock = 3200000

		##################################################
		# Message Queues
		##################################################
		source_msgq_out = sink_msgq_in = gr.msg_queue(2)

		##################################################
		# Blocks
		##################################################
		self.sink = gr.udp_sink(gr.sizeof_short*1, "127.0.0.1", 28888, 1472, False, True)
		self.sink.set_status_msgq(sink_msgq_in)
		self.source = baz.rtl_source_c(defer_creation=True, output_size=gr.sizeof_short)
		self.source.set_verbose(True)
		self.source.set_vid(0x0)
		self.source.set_pid(0x0)
		self.source.set_tuner_name(tuner)
		self.source.set_default_timeout(0)
		self.source.set_use_buffer(buf)
		self.source.set_fir_coefficients(([]))
		
		self.source.set_read_length(0)
		
		
		
		
		if self.source.create() == False: raise Exception("Failed to create RTL2832 Source: source")
		
		
		self.source.set_sample_rate(1000000)
		
		self.source.set_frequency(0)
		
		
		self.source.set_status_msgq(source_msgq_out)
		
		self.source.set_auto_gain_mode(False)
		self.source.set_relative_gain(False)
		self.source.set_gain(0)
		  

		##################################################
		# Connections
		##################################################
		self.connect((self.source, 0), (self.sink, 0))

	def set_buf(self, buf):
		self.buf = buf

	def set_tuner(self, tuner):
		self.tuner = tuner

	def set_master_clock(self, master_clock):
		self.master_clock = master_clock

if __name__ == '__main__':
	parser = OptionParser(option_class=eng_option, usage="%prog: [options]")
	parser.add_option("", "--tuner", dest="tuner", type="string", default="",
		help="Set Tuner [default=%default]")
	(options, args) = parser.parse_args()
	tb = borip_RTL2(tuner=options.tuner)
	tb.start()
	raw_input('Press Enter to quit: ')
	tb.stop()


########NEW FILE########
__FILENAME__ = borip_server
#!/usr/bin/env python

from baz import borip_server

if __name__ == "__main__":
    borip_server.main()

########NEW FILE########
__FILENAME__ = borip_usrp_legacy
#!/usr/bin/env python
##################################################
# Gnuradio Python Flow Graph
# Title: Borip Usrp Legacy
# Generated: Thu Nov 22 22:37:47 2012
##################################################

from gnuradio import eng_notation
from gnuradio import gr
from gnuradio.eng_option import eng_option
from gnuradio import filter 
from gnuradio.filter import firdes
from grc_gnuradio import usrp as grc_usrp
from optparse import OptionParser
import baz

class borip_usrp_legacy(gr.top_block):

	def __init__(self, unit=0, side="A"):
		gr.top_block.__init__(self, "Borip Usrp Legacy")

		##################################################
		# Parameters
		##################################################
		self.unit = unit
		self.side = side

		##################################################
		# Variables
		##################################################
		self.tr_to_list = tr_to_list = lambda req, tr: [req, tr.baseband_freq, tr.dxc_freq + tr.residual_freq, tr.dxc_freq]
		self.serial = serial = lambda: self.source._get_u().serial_number()
		self.master_clock = master_clock = lambda: self.source._get_u().fpga_master_clock_freq()
		self.tune_tolerance = tune_tolerance = 1
		self.source_name = source_name = lambda: "USRP (" + serial() + ")"
		self.set_samp_rate = set_samp_rate = lambda r: self.source.set_decim_rate(self.master_clock()//r)
		self.set_freq = set_freq = lambda f: self.tr_to_list(f, self.source._get_u().tune(0, self.source._subdev, f))
		self.set_antenna = set_antenna = lambda a: self.source._subdev.select_rx_antenna(a)
		self.samp_rate = samp_rate = lambda: self.master_clock()/self.source._get_u().decim_rate()
		self.gain_range = gain_range = lambda: self.source._subdev.gain_range()
		self.antennas = antennas = ["TX/RX","RX2","RXA","RXB","RXAB"]

		##################################################
		# Message Queues
		##################################################
		source_msgq_out = sink_msgq_in = gr.msg_queue(2)

		##################################################
		# Blocks
		##################################################
		self.source = grc_usrp.simple_source_s(which=unit, side=side, rx_ant="")
		self.source.set_decim_rate(256)
		self.source.set_frequency(0, verbose=True)
		self.source.set_gain(0)
		if hasattr(self.source, '_get_u') and hasattr(self.source._get_u(), 'set_status_msgq'): self.source._get_u().set_status_msgq(source_msgq_out)
		self.sink = baz.udp_sink(gr.sizeof_short*1, "", 28888, 1472, False, True)
		self.sink.set_status_msgq(sink_msgq_in)

		##################################################
		# Connections
		##################################################
		self.connect((self.source, 0), (self.sink, 0))

	def get_unit(self):
		return self.unit

	def set_unit(self, unit):
		self.unit = unit

	def get_side(self):
		return self.side

	def set_side(self, side):
		self.side = side

	def get_tr_to_list(self):
		return self.tr_to_list

	def set_tr_to_list(self, tr_to_list):
		self.tr_to_list = tr_to_list
		self.set_set_freq(lambda f: self.self.tr_to_list(f, self.source._get_u().tune(0, self.source._subdev, f)))

	def get_serial(self):
		return self.serial

	def set_serial(self, serial):
		self.serial = serial
		self.set_source_name(lambda: "USRP (" + self.serial() + ")")

	def get_master_clock(self):
		return self.master_clock

	def set_master_clock(self, master_clock):
		self.master_clock = master_clock
		self.set_set_samp_rate(lambda r: self.source.set_decim_rate(self.self.master_clock()//r))
		self.self.set_samp_rate(lambda: self.self.master_clock()/self.source._get_u().decim_rate())

	def get_tune_tolerance(self):
		return self.tune_tolerance

	def set_tune_tolerance(self, tune_tolerance):
		self.tune_tolerance = tune_tolerance

	def get_source_name(self):
		return self.source_name

	def set_source_name(self, source_name):
		self.source_name = source_name

	def get_set_samp_rate(self):
		return self.set_samp_rate

	def set_set_samp_rate(self, set_samp_rate):
		self.set_samp_rate = set_samp_rate
		self.self.set_samp_rate(lambda: self.self.master_clock()/self.source._get_u().decim_rate())

	def get_set_freq(self):
		return self.set_freq

	def set_set_freq(self, set_freq):
		self.set_freq = set_freq

	def get_set_antenna(self):
		return self.set_antenna

	def set_set_antenna(self, set_antenna):
		self.set_antenna = set_antenna

	def get_samp_rate(self):
		return self.samp_rate

	def set_samp_rate(self, samp_rate):
		self.samp_rate = samp_rate

	def get_gain_range(self):
		return self.gain_range

	def set_gain_range(self, gain_range):
		self.gain_range = gain_range
		self.set_gain_range(lambda: self.source._subdev.self.gain_range())

	def get_antennas(self):
		return self.antennas

	def set_antennas(self, antennas):
		self.antennas = antennas

if __name__ == '__main__':
	parser = OptionParser(option_class=eng_option, usage="%prog: [options]")
	parser.add_option("", "--unit", dest="unit", type="intx", default=0,
		help="Set Unit [default=%default]")
	parser.add_option("", "--side", dest="side", type="string", default="A",
		help="Set Side [default=%default]")
	(options, args) = parser.parse_args()
	tb = borip_usrp_legacy(unit=options.unit, side=options.side)
	tb.start()
	raw_input('Press Enter to quit: ')
	tb.stop()


########NEW FILE########
__FILENAME__ = borip_usrp_uhd
#!/usr/bin/env python
##################################################
# Gnuradio Python Flow Graph
# Title: Borip Usrp Uhd
# Generated: Tue Nov 20 23:43:41 2012
##################################################

from gnuradio import eng_notation
from gnuradio import gr
from gnuradio import uhd
from gnuradio.eng_option import eng_option
from gnuradio import filter 
from gnuradio.filter import firdes
from optparse import OptionParser
import baz

class borip_usrp_uhd(gr.top_block):

	def __init__(self, addr="", subdev=""):
		gr.top_block.__init__(self, "Borip Usrp Uhd")

		##################################################
		# Parameters
		##################################################
		self.addr = addr
		self.subdev = subdev

		##################################################
		# Variables
		##################################################
		self.source_name = source_name = lambda: "USRP (" + self.source.get_usrp_info().get("mboard_id") + ")"
		self.serial = serial = lambda: self.source.get_usrp_info().get("mboard_serial")

		##################################################
		# Blocks
		##################################################
		self.source = uhd.usrp_source(
			device_addr=addr,
			stream_args=uhd.stream_args(
				cpu_format="sc16",
				channels=range(1),
			),
		)
		#self.source.set_samp_rate(0)
		#self.source.set_center_freq(0, 0)
		#self.source.set_gain(0, 0)
		self.sink = baz.udp_sink(gr.sizeof_short*2, "", 28888, 1472, False, True)

		##################################################
		# Connections
		##################################################
		self.connect((self.source, 0), (self.sink, 0))

	def get_addr(self):
		return self.addr

	def set_addr(self, addr):
		self.addr = addr

	def get_subdev(self):
		return self.subdev

	def set_subdev(self, subdev):
		self.subdev = subdev

	def get_source_name(self):
		return self.source_name

	def set_source_name(self, source_name):
		self.source_name = source_name

	def get_serial(self):
		return self.serial

	def set_serial(self, serial):
		self.serial = serial

if __name__ == '__main__':
	parser = OptionParser(option_class=eng_option, usage="%prog: [options]")
	parser.add_option("-a", "--addr", dest="addr", type="string", default="",
		help="Set Address [default=%default]")
	parser.add_option("-s", "--subdev", dest="subdev", type="string", default="",
		help="Set Sub Dev [default=%default]")
	(options, args) = parser.parse_args()
	tb = borip_usrp_uhd(addr=options.addr, subdev=options.subdev)
	tb.start()
	raw_input('Press Enter to quit: ')
	tb.stop()


########NEW FILE########
__FILENAME__ = control_loop_calc
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  control_loop_calc.py
#  
#  Copyright 2013 Balint Seeber <balint@ettus.com>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#  

import math
from optparse import OptionParser
from gnuradio.eng_option import eng_option

def main():
	usage="%prog: [options]"
	parser = OptionParser(option_class=eng_option, usage=usage)
	parser.add_option("-a", "--alpha", type="float", default=None, help="Alpha [default=%default]")
	parser.add_option("-b", "--beta", type="float", default=None, help="Beta [default=%default]")
	parser.add_option("-l", "--loop-bandwidth", type="float", default=None, help="Loop bandwidth [default=%default]")
	parser.add_option("-d", "--damping", type="float", default=None, help="Damping [default=%default]")
	(options, args) = parser.parse_args()
	if options.alpha is not None and options.beta is not None:
		bw = math.sqrt(options.beta / (4 - 2*options.alpha - options.beta))
		d = (options.alpha * (-1 - bw*bw)) / (2 * bw * (options.alpha - 2))
		print "Bandwidth:\t%f\nDamping:\t%f" % (bw, d)
	if options.loop_bandwidth is not None and options.damping is not None:
		denom = (1 + 2 * options.damping * options.loop_bandwidth + options.loop_bandwidth*options.loop_bandwidth)
		a = (4 * options.damping * options.loop_bandwidth) / denom
		b = (4 * options.loop_bandwidth*options.loop_bandwidth) / denom
		print "Alpha:\t%f\nBeta:\t%f" % (a, b)
	if options.alpha is not None and options.damping is not None:
		b = 2 * options.alpha * options.damping - 4 * options.damping
		p1 = -b
		p2 = math.sqrt(b*b - 4 * options.alpha*options.alpha)
		denom = 2 * options.alpha
		x1 = (p1 + p2) / denom
		x2 = (p1 - p2) / denom
		print "Bandwidth 1:\t%f\nBandwidth 2:\t%f" % (x1, x2)
	if options.beta is not None and options.damping is not None:
		b = -2 * options.beta * options.damping
		p1 = -b
		p2 = math.sqrt(b*b - 4 * (4 - options.beta) * (-options.beta))
		denom = 2 * (4 - options.beta)
		x1 = (p1 + p2) / denom
		x2 = (p1 - p2) / denom
		print "Bandwidth 1:\t%f\nBandwidth 2:\t%f" % (x1, x2)
	return 0

if __name__ == '__main__':
	main()

########NEW FILE########
__FILENAME__ = usrp_fac
#!/usr/bin/env python
#
# Copyright 2004,2005 Free Software Foundation, Inc.
# 
# This file is part of GNU Radio
# 
# GNU Radio is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# GNU Radio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with GNU Radio; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
# 

# Modified by Balint Seeber (http://wiki.spench.net/wiki/gr-baz)
# Part of http://wiki.spench.net/wiki/Fast_Auto-correlation

from gnuradio import gr, gru
from gnuradio import usrp
from gnuradio import eng_notation
from gnuradio.eng_option import eng_option
from gnuradio.wxgui import stdgui2, fftsink2, waterfallsink2, scopesink2, form, slider
from optparse import OptionParser

from baz import facsink

import wx
import sys

def pick_subdevice(u):
    """
    The user didn't specify a subdevice on the command line.
    If there's a daughterboard on A, select A.
    If there's a daughterboard on B, select B.
    Otherwise, select A.
    """
    if u.db(0, 0).dbid() >= 0:       # dbid is < 0 if there's no d'board or a problem
        return (0, 0)
    if u.db(1, 0).dbid() >= 0:
        return (1, 0)
    return (0, 0)


class app_flow_graph(stdgui2.std_top_block):
    def __init__(self, frame, panel, vbox, argv):
        stdgui2.std_top_block.__init__(self, frame, panel, vbox, argv)

        self.frame = frame
        self.panel = panel
        
        parser = OptionParser(option_class=eng_option)
        parser.add_option("-R", "--rx-subdev-spec", type="subdev", default=None,
                          help="select USRP Rx side A or B (default=first one with a daughterboard)")
        parser.add_option("-d", "--decim", type="int", default=16,
                          help="set fgpa decimation rate to DECIM [default=%default]")
        parser.add_option("-f", "--freq", type="eng_float", default=None,
                          help="set frequency to FREQ", metavar="FREQ")
        parser.add_option("-g", "--gain", type="eng_float", default=None,
                          help="set gain in dB (default is midpoint)")
        parser.add_option("-W", "--waterfall", action="store_true", default=False,
                          help="Enable waterfall display")
        parser.add_option("-8", "--width-8", action="store_true", default=False,
                          help="Enable 8-bit samples across USB")
        parser.add_option("-S", "--oscilloscope", action="store_true", default=False,
                          help="Enable oscilloscope display")
        (options, args) = parser.parse_args()
        if len(args) != 0:
            parser.print_help()
            sys.exit(1)

        self.show_debug_info = True
        
        # build the graph

        self.u = usrp.source_c(decim_rate=options.decim)
        if options.rx_subdev_spec is None:
            options.rx_subdev_spec = pick_subdevice(self.u)
        self.u.set_mux(usrp.determine_rx_mux_value(self.u, options.rx_subdev_spec))

        if options.width_8:
            width = 8
            shift = 8
            format = self.u.make_format(width, shift)
            print "format =", hex(format)
            r = self.u.set_format(format)
            print "set_format =", r
            
        # determine the daughterboard subdevice we're using
        self.subdev = usrp.selected_subdev(self.u, options.rx_subdev_spec)

        input_rate = self.u.adc_freq() / self.u.decim_rate()

        if options.waterfall:
            self.scope = \
              waterfallsink2.waterfall_sink_c (panel, fft_size=1024, sample_rate=input_rate, title = "Waterfall")
        elif options.oscilloscope:
            self.scope = scopesink2.scope_sink_c(panel, sample_rate=input_rate, title = "Scope" )
        else:
            self.scope = fftsink2.fft_sink_c (panel, fft_size=512, sample_rate=input_rate, title = "FFT")
        self.connect(self.u, self.scope)


        # setup fac sink...  Main FFT Size determined here...
        self.fac = facsink.fac_sink_c (panel, fac_size=32768, sample_rate=input_rate, title = "Auto Correlation")
        self.connect(self.u, self.fac)


        self._build_gui(vbox)

        # set initial values

        if options.gain is None:
            # if no gain was specified, use the mid-point in dB
            g = self.subdev.gain_range()
            options.gain = float(g[0]+g[1])/2

        if options.freq is None:
            # if no freq was specified, use the mid-point
            r = self.subdev.freq_range()
            options.freq = float(r[0]+r[1])/2

        self.set_gain(options.gain)

        if self.show_debug_info:
            self.myform['decim'].set_value(self.u.decim_rate())
            self.myform['fs@usb'].set_value(self.u.adc_freq() / self.u.decim_rate())
            self.myform['dbname'].set_value(self.subdev.name())
            self.myform['baseband'].set_value(0)
            self.myform['ddc'].set_value(0)

        if not(self.set_freq(options.freq)):
            self._set_status_msg("Failed to set initial frequency")

    def _set_status_msg(self, msg):
        self.frame.GetStatusBar().SetStatusText(msg, 0)

    def _build_gui(self, vbox):

        def _form_set_freq(kv):
            return self.set_freq(kv['freq'])


        vbox.Add(self.scope.win, 10, wx.EXPAND)
        # and add fac display below scope/fft/waterfall
        vbox.Add(self.fac.win, 10, wx.EXPAND)            

        
        # add control area at the bottom
        self.myform = myform = form.form()
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add((5,0), 0, 0)
        myform['freq'] = form.float_field(
            parent=self.panel, sizer=hbox, label="Center freq", weight=1,
            callback=myform.check_input_and_call(_form_set_freq, self._set_status_msg))

        hbox.Add((5,0), 0, 0)
        g = self.subdev.gain_range()
        myform['gain'] = form.slider_field(parent=self.panel, sizer=hbox, label="Gain",
                                           weight=3,
                                           min=int(g[0]), max=int(g[1]),
                                           callback=self.set_gain)

        hbox.Add((5,0), 0, 0)
        vbox.Add(hbox, 0, wx.EXPAND)

        self._build_subpanel(vbox)

    def _build_subpanel(self, vbox_arg):
        # build a secondary information panel (sometimes hidden)

        # FIXME figure out how to have this be a subpanel that is always
        # created, but has its visibility controlled by foo.Show(True/False)
        
        def _form_set_decim(kv):
            return self.set_decim(kv['decim'])

        if not(self.show_debug_info):
            return

        panel = self.panel
        vbox = vbox_arg
        myform = self.myform

        #panel = wx.Panel(self.panel, -1)
        #vbox = wx.BoxSizer(wx.VERTICAL)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add((5,0), 0)

        myform['decim'] = form.int_field(
            parent=panel, sizer=hbox, label="Decim",
            callback=myform.check_input_and_call(_form_set_decim, self._set_status_msg))

        hbox.Add((5,0), 1)
        myform['fs@usb'] = form.static_float_field(
            parent=panel, sizer=hbox, label="Fs@USB")

        hbox.Add((5,0), 1)
        myform['dbname'] = form.static_text_field(
            parent=panel, sizer=hbox)

        hbox.Add((5,0), 1)
        myform['baseband'] = form.static_float_field(
            parent=panel, sizer=hbox, label="Analog BB")

        hbox.Add((5,0), 1)
        myform['ddc'] = form.static_float_field(
            parent=panel, sizer=hbox, label="DDC")

        hbox.Add((5,0), 0)
        vbox.Add(hbox, 0, wx.EXPAND)

        
    def set_freq(self, target_freq):
        """
        Set the center frequency we're interested in.

        @param target_freq: frequency in Hz
        @rypte: bool

        Tuning is a two step process.  First we ask the front-end to
        tune as close to the desired frequency as it can.  Then we use
        the result of that operation and our target_frequency to
        determine the value for the digital down converter.
        """
        r = self.u.tune(0, self.subdev, target_freq)
        
        if r:
            self.myform['freq'].set_value(target_freq)     # update displayed value
            if self.show_debug_info:
                self.myform['baseband'].set_value(r.baseband_freq)
                self.myform['ddc'].set_value(r.dxc_freq)
            return True

        return False

    def set_gain(self, gain):
        self.myform['gain'].set_value(gain)     # update displayed value
        self.subdev.set_gain(gain)

    def set_decim(self, decim):
        ok = self.u.set_decim_rate(decim)
        if not ok:
            print "set_decim failed"
        input_rate = self.u.adc_freq() / self.u.decim_rate()
        self.scope.set_sample_rate(input_rate)
        self.fac.set_sample_rate(input_rate)
        if self.show_debug_info:  # update displayed values
            self.myform['decim'].set_value(self.u.decim_rate())
            self.myform['fs@usb'].set_value(self.u.adc_freq() / self.u.decim_rate())
        return ok

def main ():
    app = stdgui2.stdapp(app_flow_graph, "USRP FastAutoCorrelation", nstatus=1)
    app.MainLoop()

if __name__ == '__main__':
    main ()

########NEW FILE########
__FILENAME__ = base
#
# Copyright 2010 Free Software Foundation, Inc.
#
# This file is part of GNU Radio
#
# GNU Radio is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# GNU Radio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GNU Radio; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#
"""
A base class is created.

Classes based upon this are used to make more user-friendly interfaces
to the doxygen xml docs than the generated classes provide.
"""

import os
import pdb

from xml.parsers.expat import ExpatError

from generated import compound


class Base(object):

    class Duplicate(StandardError):
        pass

    class NoSuchMember(StandardError):
        pass

    class ParsingError(StandardError):
        pass

    def __init__(self, parse_data, top=None):
        self._parsed = False
        self._error = False
        self._parse_data = parse_data
        self._members = []
        self._dict_members = {}
        self._in_category = {}
        self._data = {}
        if top is not None:
            self._xml_path = top._xml_path
            # Set up holder of references
        else:
            top = self
            self._refs = {}
            self._xml_path = parse_data
        self.top = top

    @classmethod
    def from_refid(cls, refid, top=None):
        """ Instantiate class from a refid rather than parsing object. """
        # First check to see if its already been instantiated.
        if top is not None and refid in top._refs:
            return top._refs[refid]
        # Otherwise create a new instance and set refid.
        inst = cls(None, top=top)
        inst.refid = refid
        inst.add_ref(inst)
        return inst

    @classmethod
    def from_parse_data(cls, parse_data, top=None):
        refid = getattr(parse_data, 'refid', None)
        if refid is not None and top is not None and refid in top._refs:
            return top._refs[refid]
        inst = cls(parse_data, top=top)
        if refid is not None:
            inst.refid = refid
            inst.add_ref(inst)
        return inst

    def add_ref(self, obj):
        if hasattr(obj, 'refid'):
            self.top._refs[obj.refid] = obj

    mem_classes = []

    def get_cls(self, mem):
        for cls in self.mem_classes:
            if cls.can_parse(mem):
                return cls
        raise StandardError(("Did not find a class for object '%s'." \
                                 % (mem.get_name())))

    def convert_mem(self, mem):
        try:
            cls = self.get_cls(mem)
            converted = cls.from_parse_data(mem, self.top)
            if converted is None:
                raise StandardError('No class matched this object.')
            self.add_ref(converted)
            return converted
        except StandardError, e:
            print e

    @classmethod
    def includes(cls, inst):
        return isinstance(inst, cls)

    @classmethod
    def can_parse(cls, obj):
        return False

    def _parse(self):
        self._parsed = True

    def _get_dict_members(self, cat=None):
        """
        For given category a dictionary is returned mapping member names to
        members of that category.  For names that are duplicated the name is
        mapped to None.
        """
        self.confirm_no_error()
        if cat not in self._dict_members:
            new_dict = {}
            for mem in self.in_category(cat):
                if mem.name() not in new_dict:
                    new_dict[mem.name()] = mem
                else:
                    new_dict[mem.name()] = self.Duplicate
            self._dict_members[cat] = new_dict
        return self._dict_members[cat]

    def in_category(self, cat):
        self.confirm_no_error()
        if cat is None:
            return self._members
        if cat not in self._in_category:
            self._in_category[cat] = [mem for mem in self._members
                                      if cat.includes(mem)]
        return self._in_category[cat]

    def get_member(self, name, cat=None):
        self.confirm_no_error()
        # Check if it's in a namespace or class.
        bits = name.split('::')
        first = bits[0]
        rest = '::'.join(bits[1:])
        member = self._get_dict_members(cat).get(first, self.NoSuchMember)
        # Raise any errors that are returned.
        if member in set([self.NoSuchMember, self.Duplicate]):
            raise member()
        if rest:
            return member.get_member(rest, cat=cat)
        return member

    def has_member(self, name, cat=None):
        try:
            mem = self.get_member(name, cat=cat)
            return True
        except self.NoSuchMember:
            return False

    def data(self):
        self.confirm_no_error()
        return self._data

    def members(self):
        self.confirm_no_error()
        return self._members

    def process_memberdefs(self):
        mdtss = []
        for sec in self._retrieved_data.compounddef.sectiondef:
            mdtss += sec.memberdef
        # At the moment we lose all information associated with sections.
        # Sometimes a memberdef is in several sectiondef.
        # We make sure we don't get duplicates here.
        uniques = set([])
        for mem in mdtss:
            converted = self.convert_mem(mem)
            pair = (mem.name, mem.__class__)
            if pair not in uniques:
                uniques.add(pair)
                self._members.append(converted)

    def retrieve_data(self):
        filename = os.path.join(self._xml_path, self.refid + '.xml')
        try:
            self._retrieved_data = compound.parse(filename)
        except ExpatError:
            print('Error in xml in file %s' % filename)
            self._error = True
            self._retrieved_data = None

    def check_parsed(self):
        if not self._parsed:
            self._parse()

    def confirm_no_error(self):
        self.check_parsed()
        if self._error:
            raise self.ParsingError()

    def error(self):
        self.check_parsed()
        return self._error

    def name(self):
        # first see if we can do it without processing.
        if self._parse_data is not None:
            return self._parse_data.name
        self.check_parsed()
        return self._retrieved_data.compounddef.name

########NEW FILE########
__FILENAME__ = doxyindex
#
# Copyright 2010 Free Software Foundation, Inc.
#
# This file is part of GNU Radio
#
# GNU Radio is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# GNU Radio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GNU Radio; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#
"""
Classes providing more user-friendly interfaces to the doxygen xml
docs than the generated classes provide.
"""

import os

from generated import index
from base import Base
from text import description

class DoxyIndex(Base):
    """
    Parses a doxygen xml directory.
    """

    __module__ = "gnuradio.utils.doxyxml"

    def _parse(self):
        if self._parsed:
            return
        super(DoxyIndex, self)._parse()
        self._root = index.parse(os.path.join(self._xml_path, 'index.xml'))
        for mem in self._root.compound:
            converted = self.convert_mem(mem)
            # For files we want the contents to be accessible directly
            # from the parent rather than having to go through the file
            # object.
            if self.get_cls(mem) == DoxyFile:
                if mem.name.endswith('.h'):
                    self._members += converted.members()
                    self._members.append(converted)
            else:
                self._members.append(converted)


def generate_swig_doc_i(self):
    """
    %feature("docstring") gr_make_align_on_samplenumbers_ss::align_state "
    Wraps the C++: gr_align_on_samplenumbers_ss::align_state";
    """
    pass


class DoxyCompMem(Base):


    kind = None

    def __init__(self, *args, **kwargs):
        super(DoxyCompMem, self).__init__(*args, **kwargs)

    @classmethod
    def can_parse(cls, obj):
        return obj.kind == cls.kind

    def set_descriptions(self, parse_data):
        bd = description(getattr(parse_data, 'briefdescription', None))
        dd = description(getattr(parse_data, 'detaileddescription', None))
        self._data['brief_description'] = bd
        self._data['detailed_description'] = dd

class DoxyCompound(DoxyCompMem):
    pass

class DoxyMember(DoxyCompMem):
    pass


class DoxyFunction(DoxyMember):

    __module__ = "gnuradio.utils.doxyxml"

    kind = 'function'

    def _parse(self):
        if self._parsed:
            return
        super(DoxyFunction, self)._parse()
        self.set_descriptions(self._parse_data)
        self._data['params'] = []
        prms = self._parse_data.param
        for prm in prms:
            self._data['params'].append(DoxyParam(prm))

    brief_description = property(lambda self: self.data()['brief_description'])
    detailed_description = property(lambda self: self.data()['detailed_description'])
    params = property(lambda self: self.data()['params'])

Base.mem_classes.append(DoxyFunction)


class DoxyParam(DoxyMember):

    __module__ = "gnuradio.utils.doxyxml"

    def _parse(self):
        if self._parsed:
            return
        super(DoxyParam, self)._parse()
        self.set_descriptions(self._parse_data)
        self._data['declname'] = self._parse_data.declname

    brief_description = property(lambda self: self.data()['brief_description'])
    detailed_description = property(lambda self: self.data()['detailed_description'])
    declname = property(lambda self: self.data()['declname'])

class DoxyClass(DoxyCompound):

    __module__ = "gnuradio.utils.doxyxml"

    kind = 'class'

    def _parse(self):
        if self._parsed:
            return
        super(DoxyClass, self)._parse()
        self.retrieve_data()
        if self._error:
            return
        self.set_descriptions(self._retrieved_data.compounddef)
        # Sectiondef.kind tells about whether private or public.
        # We just ignore this for now.
        self.process_memberdefs()

    brief_description = property(lambda self: self.data()['brief_description'])
    detailed_description = property(lambda self: self.data()['detailed_description'])

Base.mem_classes.append(DoxyClass)


class DoxyFile(DoxyCompound):

    __module__ = "gnuradio.utils.doxyxml"

    kind = 'file'

    def _parse(self):
        if self._parsed:
            return
        super(DoxyFile, self)._parse()
        self.retrieve_data()
        self.set_descriptions(self._retrieved_data.compounddef)
        if self._error:
            return
        self.process_memberdefs()

    brief_description = property(lambda self: self.data()['brief_description'])
    detailed_description = property(lambda self: self.data()['detailed_description'])

Base.mem_classes.append(DoxyFile)


class DoxyNamespace(DoxyCompound):

    __module__ = "gnuradio.utils.doxyxml"

    kind = 'namespace'

Base.mem_classes.append(DoxyNamespace)


class DoxyGroup(DoxyCompound):

    __module__ = "gnuradio.utils.doxyxml"

    kind = 'group'

    def _parse(self):
        if self._parsed:
            return
        super(DoxyGroup, self)._parse()
        self.retrieve_data()
        if self._error:
            return
        cdef = self._retrieved_data.compounddef
        self._data['title'] = description(cdef.title)
        # Process inner groups
        grps = cdef.innergroup
        for grp in grps:
            converted = DoxyGroup.from_refid(grp.refid, top=self.top)
            self._members.append(converted)
        # Process inner classes
        klasses = cdef.innerclass
        for kls in klasses:
            converted = DoxyClass.from_refid(kls.refid, top=self.top)
            self._members.append(converted)
        # Process normal members
        self.process_memberdefs()

    title = property(lambda self: self.data()['title'])


Base.mem_classes.append(DoxyGroup)


class DoxyFriend(DoxyMember):

    __module__ = "gnuradio.utils.doxyxml"

    kind = 'friend'

Base.mem_classes.append(DoxyFriend)


class DoxyOther(Base):

    __module__ = "gnuradio.utils.doxyxml"

    kinds = set(['variable', 'struct', 'union', 'define', 'typedef', 'enum', 'dir', 'page'])

    @classmethod
    def can_parse(cls, obj):
        return obj.kind in cls.kinds

Base.mem_classes.append(DoxyOther)


########NEW FILE########
__FILENAME__ = compound
#!/usr/bin/env python

"""
Generated Mon Feb  9 19:08:05 2009 by generateDS.py.
"""

from string import lower as str_lower
from xml.dom import minidom
from xml.dom import Node

import sys

import compoundsuper as supermod
from compoundsuper import MixedContainer


class DoxygenTypeSub(supermod.DoxygenType):
    def __init__(self, version=None, compounddef=None):
        supermod.DoxygenType.__init__(self, version, compounddef)

    def find(self, details):

        return self.compounddef.find(details)

supermod.DoxygenType.subclass = DoxygenTypeSub
# end class DoxygenTypeSub


class compounddefTypeSub(supermod.compounddefType):
    def __init__(self, kind=None, prot=None, id=None, compoundname='', title='', basecompoundref=None, derivedcompoundref=None, includes=None, includedby=None, incdepgraph=None, invincdepgraph=None, innerdir=None, innerfile=None, innerclass=None, innernamespace=None, innerpage=None, innergroup=None, templateparamlist=None, sectiondef=None, briefdescription=None, detaileddescription=None, inheritancegraph=None, collaborationgraph=None, programlisting=None, location=None, listofallmembers=None):
        supermod.compounddefType.__init__(self, kind, prot, id, compoundname, title, basecompoundref, derivedcompoundref, includes, includedby, incdepgraph, invincdepgraph, innerdir, innerfile, innerclass, innernamespace, innerpage, innergroup, templateparamlist, sectiondef, briefdescription, detaileddescription, inheritancegraph, collaborationgraph, programlisting, location, listofallmembers)

    def find(self, details):

        if self.id == details.refid:
            return self

        for sectiondef in self.sectiondef:
            result = sectiondef.find(details)
            if result:
                return result


supermod.compounddefType.subclass = compounddefTypeSub
# end class compounddefTypeSub


class listofallmembersTypeSub(supermod.listofallmembersType):
    def __init__(self, member=None):
        supermod.listofallmembersType.__init__(self, member)
supermod.listofallmembersType.subclass = listofallmembersTypeSub
# end class listofallmembersTypeSub


class memberRefTypeSub(supermod.memberRefType):
    def __init__(self, virt=None, prot=None, refid=None, ambiguityscope=None, scope='', name=''):
        supermod.memberRefType.__init__(self, virt, prot, refid, ambiguityscope, scope, name)
supermod.memberRefType.subclass = memberRefTypeSub
# end class memberRefTypeSub


class compoundRefTypeSub(supermod.compoundRefType):
    def __init__(self, virt=None, prot=None, refid=None, valueOf_='', mixedclass_=None, content_=None):
        supermod.compoundRefType.__init__(self, mixedclass_, content_)
supermod.compoundRefType.subclass = compoundRefTypeSub
# end class compoundRefTypeSub


class reimplementTypeSub(supermod.reimplementType):
    def __init__(self, refid=None, valueOf_='', mixedclass_=None, content_=None):
        supermod.reimplementType.__init__(self, mixedclass_, content_)
supermod.reimplementType.subclass = reimplementTypeSub
# end class reimplementTypeSub


class incTypeSub(supermod.incType):
    def __init__(self, local=None, refid=None, valueOf_='', mixedclass_=None, content_=None):
        supermod.incType.__init__(self, mixedclass_, content_)
supermod.incType.subclass = incTypeSub
# end class incTypeSub


class refTypeSub(supermod.refType):
    def __init__(self, prot=None, refid=None, valueOf_='', mixedclass_=None, content_=None):
        supermod.refType.__init__(self, mixedclass_, content_)
supermod.refType.subclass = refTypeSub
# end class refTypeSub



class refTextTypeSub(supermod.refTextType):
    def __init__(self, refid=None, kindref=None, external=None, valueOf_='', mixedclass_=None, content_=None):
        supermod.refTextType.__init__(self, mixedclass_, content_)

supermod.refTextType.subclass = refTextTypeSub
# end class refTextTypeSub

class sectiondefTypeSub(supermod.sectiondefType):


    def __init__(self, kind=None, header='', description=None, memberdef=None):
        supermod.sectiondefType.__init__(self, kind, header, description, memberdef)

    def find(self, details):

        for memberdef in self.memberdef:
            if memberdef.id == details.refid:
                return memberdef

        return None


supermod.sectiondefType.subclass = sectiondefTypeSub
# end class sectiondefTypeSub


class memberdefTypeSub(supermod.memberdefType):
    def __init__(self, initonly=None, kind=None, volatile=None, const=None, raise_=None, virt=None, readable=None, prot=None, explicit=None, new=None, final=None, writable=None, add=None, static=None, remove=None, sealed=None, mutable=None, gettable=None, inline=None, settable=None, id=None, templateparamlist=None, type_=None, definition='', argsstring='', name='', read='', write='', bitfield='', reimplements=None, reimplementedby=None, param=None, enumvalue=None, initializer=None, exceptions=None, briefdescription=None, detaileddescription=None, inbodydescription=None, location=None, references=None, referencedby=None):
        supermod.memberdefType.__init__(self, initonly, kind, volatile, const, raise_, virt, readable, prot, explicit, new, final, writable, add, static, remove, sealed, mutable, gettable, inline, settable, id, templateparamlist, type_, definition, argsstring, name, read, write, bitfield, reimplements, reimplementedby, param, enumvalue, initializer, exceptions, briefdescription, detaileddescription, inbodydescription, location, references, referencedby)
supermod.memberdefType.subclass = memberdefTypeSub
# end class memberdefTypeSub


class descriptionTypeSub(supermod.descriptionType):
    def __init__(self, title='', para=None, sect1=None, internal=None, mixedclass_=None, content_=None):
        supermod.descriptionType.__init__(self, mixedclass_, content_)
supermod.descriptionType.subclass = descriptionTypeSub
# end class descriptionTypeSub


class enumvalueTypeSub(supermod.enumvalueType):
    def __init__(self, prot=None, id=None, name='', initializer=None, briefdescription=None, detaileddescription=None, mixedclass_=None, content_=None):
        supermod.enumvalueType.__init__(self, mixedclass_, content_)
supermod.enumvalueType.subclass = enumvalueTypeSub
# end class enumvalueTypeSub


class templateparamlistTypeSub(supermod.templateparamlistType):
    def __init__(self, param=None):
        supermod.templateparamlistType.__init__(self, param)
supermod.templateparamlistType.subclass = templateparamlistTypeSub
# end class templateparamlistTypeSub


class paramTypeSub(supermod.paramType):
    def __init__(self, type_=None, declname='', defname='', array='', defval=None, briefdescription=None):
        supermod.paramType.__init__(self, type_, declname, defname, array, defval, briefdescription)
supermod.paramType.subclass = paramTypeSub
# end class paramTypeSub


class linkedTextTypeSub(supermod.linkedTextType):
    def __init__(self, ref=None, mixedclass_=None, content_=None):
        supermod.linkedTextType.__init__(self, mixedclass_, content_)
supermod.linkedTextType.subclass = linkedTextTypeSub
# end class linkedTextTypeSub


class graphTypeSub(supermod.graphType):
    def __init__(self, node=None):
        supermod.graphType.__init__(self, node)
supermod.graphType.subclass = graphTypeSub
# end class graphTypeSub


class nodeTypeSub(supermod.nodeType):
    def __init__(self, id=None, label='', link=None, childnode=None):
        supermod.nodeType.__init__(self, id, label, link, childnode)
supermod.nodeType.subclass = nodeTypeSub
# end class nodeTypeSub


class childnodeTypeSub(supermod.childnodeType):
    def __init__(self, relation=None, refid=None, edgelabel=None):
        supermod.childnodeType.__init__(self, relation, refid, edgelabel)
supermod.childnodeType.subclass = childnodeTypeSub
# end class childnodeTypeSub


class linkTypeSub(supermod.linkType):
    def __init__(self, refid=None, external=None, valueOf_=''):
        supermod.linkType.__init__(self, refid, external)
supermod.linkType.subclass = linkTypeSub
# end class linkTypeSub


class listingTypeSub(supermod.listingType):
    def __init__(self, codeline=None):
        supermod.listingType.__init__(self, codeline)
supermod.listingType.subclass = listingTypeSub
# end class listingTypeSub


class codelineTypeSub(supermod.codelineType):
    def __init__(self, external=None, lineno=None, refkind=None, refid=None, highlight=None):
        supermod.codelineType.__init__(self, external, lineno, refkind, refid, highlight)
supermod.codelineType.subclass = codelineTypeSub
# end class codelineTypeSub


class highlightTypeSub(supermod.highlightType):
    def __init__(self, class_=None, sp=None, ref=None, mixedclass_=None, content_=None):
        supermod.highlightType.__init__(self, mixedclass_, content_)
supermod.highlightType.subclass = highlightTypeSub
# end class highlightTypeSub


class referenceTypeSub(supermod.referenceType):
    def __init__(self, endline=None, startline=None, refid=None, compoundref=None, valueOf_='', mixedclass_=None, content_=None):
        supermod.referenceType.__init__(self, mixedclass_, content_)
supermod.referenceType.subclass = referenceTypeSub
# end class referenceTypeSub


class locationTypeSub(supermod.locationType):
    def __init__(self, bodystart=None, line=None, bodyend=None, bodyfile=None, file=None, valueOf_=''):
        supermod.locationType.__init__(self, bodystart, line, bodyend, bodyfile, file)
supermod.locationType.subclass = locationTypeSub
# end class locationTypeSub


class docSect1TypeSub(supermod.docSect1Type):
    def __init__(self, id=None, title='', para=None, sect2=None, internal=None, mixedclass_=None, content_=None):
        supermod.docSect1Type.__init__(self, mixedclass_, content_)
supermod.docSect1Type.subclass = docSect1TypeSub
# end class docSect1TypeSub


class docSect2TypeSub(supermod.docSect2Type):
    def __init__(self, id=None, title='', para=None, sect3=None, internal=None, mixedclass_=None, content_=None):
        supermod.docSect2Type.__init__(self, mixedclass_, content_)
supermod.docSect2Type.subclass = docSect2TypeSub
# end class docSect2TypeSub


class docSect3TypeSub(supermod.docSect3Type):
    def __init__(self, id=None, title='', para=None, sect4=None, internal=None, mixedclass_=None, content_=None):
        supermod.docSect3Type.__init__(self, mixedclass_, content_)
supermod.docSect3Type.subclass = docSect3TypeSub
# end class docSect3TypeSub


class docSect4TypeSub(supermod.docSect4Type):
    def __init__(self, id=None, title='', para=None, internal=None, mixedclass_=None, content_=None):
        supermod.docSect4Type.__init__(self, mixedclass_, content_)
supermod.docSect4Type.subclass = docSect4TypeSub
# end class docSect4TypeSub


class docInternalTypeSub(supermod.docInternalType):
    def __init__(self, para=None, sect1=None, mixedclass_=None, content_=None):
        supermod.docInternalType.__init__(self, mixedclass_, content_)
supermod.docInternalType.subclass = docInternalTypeSub
# end class docInternalTypeSub


class docInternalS1TypeSub(supermod.docInternalS1Type):
    def __init__(self, para=None, sect2=None, mixedclass_=None, content_=None):
        supermod.docInternalS1Type.__init__(self, mixedclass_, content_)
supermod.docInternalS1Type.subclass = docInternalS1TypeSub
# end class docInternalS1TypeSub


class docInternalS2TypeSub(supermod.docInternalS2Type):
    def __init__(self, para=None, sect3=None, mixedclass_=None, content_=None):
        supermod.docInternalS2Type.__init__(self, mixedclass_, content_)
supermod.docInternalS2Type.subclass = docInternalS2TypeSub
# end class docInternalS2TypeSub


class docInternalS3TypeSub(supermod.docInternalS3Type):
    def __init__(self, para=None, sect3=None, mixedclass_=None, content_=None):
        supermod.docInternalS3Type.__init__(self, mixedclass_, content_)
supermod.docInternalS3Type.subclass = docInternalS3TypeSub
# end class docInternalS3TypeSub


class docInternalS4TypeSub(supermod.docInternalS4Type):
    def __init__(self, para=None, mixedclass_=None, content_=None):
        supermod.docInternalS4Type.__init__(self, mixedclass_, content_)
supermod.docInternalS4Type.subclass = docInternalS4TypeSub
# end class docInternalS4TypeSub


class docURLLinkSub(supermod.docURLLink):
    def __init__(self, url=None, valueOf_='', mixedclass_=None, content_=None):
        supermod.docURLLink.__init__(self, mixedclass_, content_)
supermod.docURLLink.subclass = docURLLinkSub
# end class docURLLinkSub


class docAnchorTypeSub(supermod.docAnchorType):
    def __init__(self, id=None, valueOf_='', mixedclass_=None, content_=None):
        supermod.docAnchorType.__init__(self, mixedclass_, content_)
supermod.docAnchorType.subclass = docAnchorTypeSub
# end class docAnchorTypeSub


class docFormulaTypeSub(supermod.docFormulaType):
    def __init__(self, id=None, valueOf_='', mixedclass_=None, content_=None):
        supermod.docFormulaType.__init__(self, mixedclass_, content_)
supermod.docFormulaType.subclass = docFormulaTypeSub
# end class docFormulaTypeSub


class docIndexEntryTypeSub(supermod.docIndexEntryType):
    def __init__(self, primaryie='', secondaryie=''):
        supermod.docIndexEntryType.__init__(self, primaryie, secondaryie)
supermod.docIndexEntryType.subclass = docIndexEntryTypeSub
# end class docIndexEntryTypeSub


class docListTypeSub(supermod.docListType):
    def __init__(self, listitem=None):
        supermod.docListType.__init__(self, listitem)
supermod.docListType.subclass = docListTypeSub
# end class docListTypeSub


class docListItemTypeSub(supermod.docListItemType):
    def __init__(self, para=None):
        supermod.docListItemType.__init__(self, para)
supermod.docListItemType.subclass = docListItemTypeSub
# end class docListItemTypeSub


class docSimpleSectTypeSub(supermod.docSimpleSectType):
    def __init__(self, kind=None, title=None, para=None):
        supermod.docSimpleSectType.__init__(self, kind, title, para)
supermod.docSimpleSectType.subclass = docSimpleSectTypeSub
# end class docSimpleSectTypeSub


class docVarListEntryTypeSub(supermod.docVarListEntryType):
    def __init__(self, term=None):
        supermod.docVarListEntryType.__init__(self, term)
supermod.docVarListEntryType.subclass = docVarListEntryTypeSub
# end class docVarListEntryTypeSub


class docRefTextTypeSub(supermod.docRefTextType):
    def __init__(self, refid=None, kindref=None, external=None, valueOf_='', mixedclass_=None, content_=None):
        supermod.docRefTextType.__init__(self, mixedclass_, content_)
supermod.docRefTextType.subclass = docRefTextTypeSub
# end class docRefTextTypeSub


class docTableTypeSub(supermod.docTableType):
    def __init__(self, rows=None, cols=None, row=None, caption=None):
        supermod.docTableType.__init__(self, rows, cols, row, caption)
supermod.docTableType.subclass = docTableTypeSub
# end class docTableTypeSub


class docRowTypeSub(supermod.docRowType):
    def __init__(self, entry=None):
        supermod.docRowType.__init__(self, entry)
supermod.docRowType.subclass = docRowTypeSub
# end class docRowTypeSub


class docEntryTypeSub(supermod.docEntryType):
    def __init__(self, thead=None, para=None):
        supermod.docEntryType.__init__(self, thead, para)
supermod.docEntryType.subclass = docEntryTypeSub
# end class docEntryTypeSub


class docHeadingTypeSub(supermod.docHeadingType):
    def __init__(self, level=None, valueOf_='', mixedclass_=None, content_=None):
        supermod.docHeadingType.__init__(self, mixedclass_, content_)
supermod.docHeadingType.subclass = docHeadingTypeSub
# end class docHeadingTypeSub


class docImageTypeSub(supermod.docImageType):
    def __init__(self, width=None, type_=None, name=None, height=None, valueOf_='', mixedclass_=None, content_=None):
        supermod.docImageType.__init__(self, mixedclass_, content_)
supermod.docImageType.subclass = docImageTypeSub
# end class docImageTypeSub


class docDotFileTypeSub(supermod.docDotFileType):
    def __init__(self, name=None, valueOf_='', mixedclass_=None, content_=None):
        supermod.docDotFileType.__init__(self, mixedclass_, content_)
supermod.docDotFileType.subclass = docDotFileTypeSub
# end class docDotFileTypeSub


class docTocItemTypeSub(supermod.docTocItemType):
    def __init__(self, id=None, valueOf_='', mixedclass_=None, content_=None):
        supermod.docTocItemType.__init__(self, mixedclass_, content_)
supermod.docTocItemType.subclass = docTocItemTypeSub
# end class docTocItemTypeSub


class docTocListTypeSub(supermod.docTocListType):
    def __init__(self, tocitem=None):
        supermod.docTocListType.__init__(self, tocitem)
supermod.docTocListType.subclass = docTocListTypeSub
# end class docTocListTypeSub


class docLanguageTypeSub(supermod.docLanguageType):
    def __init__(self, langid=None, para=None):
        supermod.docLanguageType.__init__(self, langid, para)
supermod.docLanguageType.subclass = docLanguageTypeSub
# end class docLanguageTypeSub


class docParamListTypeSub(supermod.docParamListType):
    def __init__(self, kind=None, parameteritem=None):
        supermod.docParamListType.__init__(self, kind, parameteritem)
supermod.docParamListType.subclass = docParamListTypeSub
# end class docParamListTypeSub


class docParamListItemSub(supermod.docParamListItem):
    def __init__(self, parameternamelist=None, parameterdescription=None):
        supermod.docParamListItem.__init__(self, parameternamelist, parameterdescription)
supermod.docParamListItem.subclass = docParamListItemSub
# end class docParamListItemSub


class docParamNameListSub(supermod.docParamNameList):
    def __init__(self, parametername=None):
        supermod.docParamNameList.__init__(self, parametername)
supermod.docParamNameList.subclass = docParamNameListSub
# end class docParamNameListSub


class docParamNameSub(supermod.docParamName):
    def __init__(self, direction=None, ref=None, mixedclass_=None, content_=None):
        supermod.docParamName.__init__(self, mixedclass_, content_)
supermod.docParamName.subclass = docParamNameSub
# end class docParamNameSub


class docXRefSectTypeSub(supermod.docXRefSectType):
    def __init__(self, id=None, xreftitle=None, xrefdescription=None):
        supermod.docXRefSectType.__init__(self, id, xreftitle, xrefdescription)
supermod.docXRefSectType.subclass = docXRefSectTypeSub
# end class docXRefSectTypeSub


class docCopyTypeSub(supermod.docCopyType):
    def __init__(self, link=None, para=None, sect1=None, internal=None):
        supermod.docCopyType.__init__(self, link, para, sect1, internal)
supermod.docCopyType.subclass = docCopyTypeSub
# end class docCopyTypeSub


class docCharTypeSub(supermod.docCharType):
    def __init__(self, char=None, valueOf_=''):
        supermod.docCharType.__init__(self, char)
supermod.docCharType.subclass = docCharTypeSub
# end class docCharTypeSub

class docParaTypeSub(supermod.docParaType):
    def __init__(self, char=None, valueOf_=''):
        supermod.docParaType.__init__(self, char)

        self.parameterlist = []
        self.simplesects = []
        self.content = []

    def buildChildren(self, child_, nodeName_):
        supermod.docParaType.buildChildren(self, child_, nodeName_)

        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
                nodeName_ == "ref":
            obj_ = supermod.docRefTextType.factory()
            obj_.build(child_)
            self.content.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
                nodeName_ == 'parameterlist':
            obj_ = supermod.docParamListType.factory()
            obj_.build(child_)
            self.parameterlist.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
                nodeName_ == 'simplesect':
            obj_ = supermod.docSimpleSectType.factory()
            obj_.build(child_)
            self.simplesects.append(obj_)


supermod.docParaType.subclass = docParaTypeSub
# end class docParaTypeSub



def parse(inFilename):
    doc = minidom.parse(inFilename)
    rootNode = doc.documentElement
    rootObj = supermod.DoxygenType.factory()
    rootObj.build(rootNode)
    return rootObj



########NEW FILE########
__FILENAME__ = compoundsuper
#!/usr/bin/env python

#
# Generated Thu Jun 11 18:44:25 2009 by generateDS.py.
#

import sys
import getopt
from string import lower as str_lower
from xml.dom import minidom
from xml.dom import Node

#
# User methods
#
# Calls to the methods in these classes are generated by generateDS.py.
# You can replace these methods by re-implementing the following class
#   in a module named generatedssuper.py.

try:
    from generatedssuper import GeneratedsSuper
except ImportError, exp:

    class GeneratedsSuper:
        def format_string(self, input_data, input_name=''):
            return input_data
        def format_integer(self, input_data, input_name=''):
            return '%d' % input_data
        def format_float(self, input_data, input_name=''):
            return '%f' % input_data
        def format_double(self, input_data, input_name=''):
            return '%e' % input_data
        def format_boolean(self, input_data, input_name=''):
            return '%s' % input_data


#
# If you have installed IPython you can uncomment and use the following.
# IPython is available from http://ipython.scipy.org/.
#

## from IPython.Shell import IPShellEmbed
## args = ''
## ipshell = IPShellEmbed(args,
##     banner = 'Dropping into IPython',
##     exit_msg = 'Leaving Interpreter, back to program.')

# Then use the following line where and when you want to drop into the
# IPython shell:
#    ipshell('<some message> -- Entering ipshell.\nHit Ctrl-D to exit')

#
# Globals
#

ExternalEncoding = 'ascii'

#
# Support/utility functions.
#

def showIndent(outfile, level):
    for idx in range(level):
        outfile.write('    ')

def quote_xml(inStr):
    s1 = (isinstance(inStr, basestring) and inStr or
          '%s' % inStr)
    s1 = s1.replace('&', '&amp;')
    s1 = s1.replace('<', '&lt;')
    s1 = s1.replace('>', '&gt;')
    return s1

def quote_attrib(inStr):
    s1 = (isinstance(inStr, basestring) and inStr or
          '%s' % inStr)
    s1 = s1.replace('&', '&amp;')
    s1 = s1.replace('<', '&lt;')
    s1 = s1.replace('>', '&gt;')
    if '"' in s1:
        if "'" in s1:
            s1 = '"%s"' % s1.replace('"', "&quot;")
        else:
            s1 = "'%s'" % s1
    else:
        s1 = '"%s"' % s1
    return s1

def quote_python(inStr):
    s1 = inStr
    if s1.find("'") == -1:
        if s1.find('\n') == -1:
            return "'%s'" % s1
        else:
            return "'''%s'''" % s1
    else:
        if s1.find('"') != -1:
            s1 = s1.replace('"', '\\"')
        if s1.find('\n') == -1:
            return '"%s"' % s1
        else:
            return '"""%s"""' % s1


class MixedContainer:
    # Constants for category:
    CategoryNone = 0
    CategoryText = 1
    CategorySimple = 2
    CategoryComplex = 3
    # Constants for content_type:
    TypeNone = 0
    TypeText = 1
    TypeString = 2
    TypeInteger = 3
    TypeFloat = 4
    TypeDecimal = 5
    TypeDouble = 6
    TypeBoolean = 7
    def __init__(self, category, content_type, name, value):
        self.category = category
        self.content_type = content_type
        self.name = name
        self.value = value
    def getCategory(self):
        return self.category
    def getContenttype(self, content_type):
        return self.content_type
    def getValue(self):
        return self.value
    def getName(self):
        return self.name
    def export(self, outfile, level, name, namespace):
        if self.category == MixedContainer.CategoryText:
            outfile.write(self.value)
        elif self.category == MixedContainer.CategorySimple:
            self.exportSimple(outfile, level, name)
        else:    # category == MixedContainer.CategoryComplex
            self.value.export(outfile, level, namespace,name)
    def exportSimple(self, outfile, level, name):
        if self.content_type == MixedContainer.TypeString:
            outfile.write('<%s>%s</%s>' % (self.name, self.value, self.name))
        elif self.content_type == MixedContainer.TypeInteger or \
                self.content_type == MixedContainer.TypeBoolean:
            outfile.write('<%s>%d</%s>' % (self.name, self.value, self.name))
        elif self.content_type == MixedContainer.TypeFloat or \
                self.content_type == MixedContainer.TypeDecimal:
            outfile.write('<%s>%f</%s>' % (self.name, self.value, self.name))
        elif self.content_type == MixedContainer.TypeDouble:
            outfile.write('<%s>%g</%s>' % (self.name, self.value, self.name))
    def exportLiteral(self, outfile, level, name):
        if self.category == MixedContainer.CategoryText:
            showIndent(outfile, level)
            outfile.write('MixedContainer(%d, %d, "%s", "%s"),\n' % \
                (self.category, self.content_type, self.name, self.value))
        elif self.category == MixedContainer.CategorySimple:
            showIndent(outfile, level)
            outfile.write('MixedContainer(%d, %d, "%s", "%s"),\n' % \
                (self.category, self.content_type, self.name, self.value))
        else:    # category == MixedContainer.CategoryComplex
            showIndent(outfile, level)
            outfile.write('MixedContainer(%d, %d, "%s",\n' % \
                (self.category, self.content_type, self.name,))
            self.value.exportLiteral(outfile, level + 1)
            showIndent(outfile, level)
            outfile.write(')\n')


class _MemberSpec(object):
    def __init__(self, name='', data_type='', container=0):
        self.name = name
        self.data_type = data_type
        self.container = container
    def set_name(self, name): self.name = name
    def get_name(self): return self.name
    def set_data_type(self, data_type): self.data_type = data_type
    def get_data_type(self): return self.data_type
    def set_container(self, container): self.container = container
    def get_container(self): return self.container


#
# Data representation classes.
#

class DoxygenType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, version=None, compounddef=None):
        self.version = version
        self.compounddef = compounddef
    def factory(*args_, **kwargs_):
        if DoxygenType.subclass:
            return DoxygenType.subclass(*args_, **kwargs_)
        else:
            return DoxygenType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_compounddef(self): return self.compounddef
    def set_compounddef(self, compounddef): self.compounddef = compounddef
    def get_version(self): return self.version
    def set_version(self, version): self.version = version
    def export(self, outfile, level, namespace_='', name_='DoxygenType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='DoxygenType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='DoxygenType'):
        outfile.write(' version=%s' % (quote_attrib(self.version), ))
    def exportChildren(self, outfile, level, namespace_='', name_='DoxygenType'):
        if self.compounddef:
            self.compounddef.export(outfile, level, namespace_, name_='compounddef')
    def hasContent_(self):
        if (
            self.compounddef is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='DoxygenType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.version is not None:
            showIndent(outfile, level)
            outfile.write('version = "%s",\n' % (self.version,))
    def exportLiteralChildren(self, outfile, level, name_):
        if self.compounddef:
            showIndent(outfile, level)
            outfile.write('compounddef=model_.compounddefType(\n')
            self.compounddef.exportLiteral(outfile, level, name_='compounddef')
            showIndent(outfile, level)
            outfile.write('),\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('version'):
            self.version = attrs.get('version').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'compounddef':
            obj_ = compounddefType.factory()
            obj_.build(child_)
            self.set_compounddef(obj_)
# end class DoxygenType


class compounddefType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, kind=None, prot=None, id=None, compoundname=None, title=None, basecompoundref=None, derivedcompoundref=None, includes=None, includedby=None, incdepgraph=None, invincdepgraph=None, innerdir=None, innerfile=None, innerclass=None, innernamespace=None, innerpage=None, innergroup=None, templateparamlist=None, sectiondef=None, briefdescription=None, detaileddescription=None, inheritancegraph=None, collaborationgraph=None, programlisting=None, location=None, listofallmembers=None):
        self.kind = kind
        self.prot = prot
        self.id = id
        self.compoundname = compoundname
        self.title = title
        if basecompoundref is None:
            self.basecompoundref = []
        else:
            self.basecompoundref = basecompoundref
        if derivedcompoundref is None:
            self.derivedcompoundref = []
        else:
            self.derivedcompoundref = derivedcompoundref
        if includes is None:
            self.includes = []
        else:
            self.includes = includes
        if includedby is None:
            self.includedby = []
        else:
            self.includedby = includedby
        self.incdepgraph = incdepgraph
        self.invincdepgraph = invincdepgraph
        if innerdir is None:
            self.innerdir = []
        else:
            self.innerdir = innerdir
        if innerfile is None:
            self.innerfile = []
        else:
            self.innerfile = innerfile
        if innerclass is None:
            self.innerclass = []
        else:
            self.innerclass = innerclass
        if innernamespace is None:
            self.innernamespace = []
        else:
            self.innernamespace = innernamespace
        if innerpage is None:
            self.innerpage = []
        else:
            self.innerpage = innerpage
        if innergroup is None:
            self.innergroup = []
        else:
            self.innergroup = innergroup
        self.templateparamlist = templateparamlist
        if sectiondef is None:
            self.sectiondef = []
        else:
            self.sectiondef = sectiondef
        self.briefdescription = briefdescription
        self.detaileddescription = detaileddescription
        self.inheritancegraph = inheritancegraph
        self.collaborationgraph = collaborationgraph
        self.programlisting = programlisting
        self.location = location
        self.listofallmembers = listofallmembers
    def factory(*args_, **kwargs_):
        if compounddefType.subclass:
            return compounddefType.subclass(*args_, **kwargs_)
        else:
            return compounddefType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_compoundname(self): return self.compoundname
    def set_compoundname(self, compoundname): self.compoundname = compoundname
    def get_title(self): return self.title
    def set_title(self, title): self.title = title
    def get_basecompoundref(self): return self.basecompoundref
    def set_basecompoundref(self, basecompoundref): self.basecompoundref = basecompoundref
    def add_basecompoundref(self, value): self.basecompoundref.append(value)
    def insert_basecompoundref(self, index, value): self.basecompoundref[index] = value
    def get_derivedcompoundref(self): return self.derivedcompoundref
    def set_derivedcompoundref(self, derivedcompoundref): self.derivedcompoundref = derivedcompoundref
    def add_derivedcompoundref(self, value): self.derivedcompoundref.append(value)
    def insert_derivedcompoundref(self, index, value): self.derivedcompoundref[index] = value
    def get_includes(self): return self.includes
    def set_includes(self, includes): self.includes = includes
    def add_includes(self, value): self.includes.append(value)
    def insert_includes(self, index, value): self.includes[index] = value
    def get_includedby(self): return self.includedby
    def set_includedby(self, includedby): self.includedby = includedby
    def add_includedby(self, value): self.includedby.append(value)
    def insert_includedby(self, index, value): self.includedby[index] = value
    def get_incdepgraph(self): return self.incdepgraph
    def set_incdepgraph(self, incdepgraph): self.incdepgraph = incdepgraph
    def get_invincdepgraph(self): return self.invincdepgraph
    def set_invincdepgraph(self, invincdepgraph): self.invincdepgraph = invincdepgraph
    def get_innerdir(self): return self.innerdir
    def set_innerdir(self, innerdir): self.innerdir = innerdir
    def add_innerdir(self, value): self.innerdir.append(value)
    def insert_innerdir(self, index, value): self.innerdir[index] = value
    def get_innerfile(self): return self.innerfile
    def set_innerfile(self, innerfile): self.innerfile = innerfile
    def add_innerfile(self, value): self.innerfile.append(value)
    def insert_innerfile(self, index, value): self.innerfile[index] = value
    def get_innerclass(self): return self.innerclass
    def set_innerclass(self, innerclass): self.innerclass = innerclass
    def add_innerclass(self, value): self.innerclass.append(value)
    def insert_innerclass(self, index, value): self.innerclass[index] = value
    def get_innernamespace(self): return self.innernamespace
    def set_innernamespace(self, innernamespace): self.innernamespace = innernamespace
    def add_innernamespace(self, value): self.innernamespace.append(value)
    def insert_innernamespace(self, index, value): self.innernamespace[index] = value
    def get_innerpage(self): return self.innerpage
    def set_innerpage(self, innerpage): self.innerpage = innerpage
    def add_innerpage(self, value): self.innerpage.append(value)
    def insert_innerpage(self, index, value): self.innerpage[index] = value
    def get_innergroup(self): return self.innergroup
    def set_innergroup(self, innergroup): self.innergroup = innergroup
    def add_innergroup(self, value): self.innergroup.append(value)
    def insert_innergroup(self, index, value): self.innergroup[index] = value
    def get_templateparamlist(self): return self.templateparamlist
    def set_templateparamlist(self, templateparamlist): self.templateparamlist = templateparamlist
    def get_sectiondef(self): return self.sectiondef
    def set_sectiondef(self, sectiondef): self.sectiondef = sectiondef
    def add_sectiondef(self, value): self.sectiondef.append(value)
    def insert_sectiondef(self, index, value): self.sectiondef[index] = value
    def get_briefdescription(self): return self.briefdescription
    def set_briefdescription(self, briefdescription): self.briefdescription = briefdescription
    def get_detaileddescription(self): return self.detaileddescription
    def set_detaileddescription(self, detaileddescription): self.detaileddescription = detaileddescription
    def get_inheritancegraph(self): return self.inheritancegraph
    def set_inheritancegraph(self, inheritancegraph): self.inheritancegraph = inheritancegraph
    def get_collaborationgraph(self): return self.collaborationgraph
    def set_collaborationgraph(self, collaborationgraph): self.collaborationgraph = collaborationgraph
    def get_programlisting(self): return self.programlisting
    def set_programlisting(self, programlisting): self.programlisting = programlisting
    def get_location(self): return self.location
    def set_location(self, location): self.location = location
    def get_listofallmembers(self): return self.listofallmembers
    def set_listofallmembers(self, listofallmembers): self.listofallmembers = listofallmembers
    def get_kind(self): return self.kind
    def set_kind(self, kind): self.kind = kind
    def get_prot(self): return self.prot
    def set_prot(self, prot): self.prot = prot
    def get_id(self): return self.id
    def set_id(self, id): self.id = id
    def export(self, outfile, level, namespace_='', name_='compounddefType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='compounddefType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='compounddefType'):
        if self.kind is not None:
            outfile.write(' kind=%s' % (quote_attrib(self.kind), ))
        if self.prot is not None:
            outfile.write(' prot=%s' % (quote_attrib(self.prot), ))
        if self.id is not None:
            outfile.write(' id=%s' % (self.format_string(quote_attrib(self.id).encode(ExternalEncoding), input_name='id'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='compounddefType'):
        if self.compoundname is not None:
            showIndent(outfile, level)
            outfile.write('<%scompoundname>%s</%scompoundname>\n' % (namespace_, self.format_string(quote_xml(self.compoundname).encode(ExternalEncoding), input_name='compoundname'), namespace_))
        if self.title is not None:
            showIndent(outfile, level)
            outfile.write('<%stitle>%s</%stitle>\n' % (namespace_, self.format_string(quote_xml(self.title).encode(ExternalEncoding), input_name='title'), namespace_))
        for basecompoundref_ in self.basecompoundref:
            basecompoundref_.export(outfile, level, namespace_, name_='basecompoundref')
        for derivedcompoundref_ in self.derivedcompoundref:
            derivedcompoundref_.export(outfile, level, namespace_, name_='derivedcompoundref')
        for includes_ in self.includes:
            includes_.export(outfile, level, namespace_, name_='includes')
        for includedby_ in self.includedby:
            includedby_.export(outfile, level, namespace_, name_='includedby')
        if self.incdepgraph:
            self.incdepgraph.export(outfile, level, namespace_, name_='incdepgraph')
        if self.invincdepgraph:
            self.invincdepgraph.export(outfile, level, namespace_, name_='invincdepgraph')
        for innerdir_ in self.innerdir:
            innerdir_.export(outfile, level, namespace_, name_='innerdir')
        for innerfile_ in self.innerfile:
            innerfile_.export(outfile, level, namespace_, name_='innerfile')
        for innerclass_ in self.innerclass:
            innerclass_.export(outfile, level, namespace_, name_='innerclass')
        for innernamespace_ in self.innernamespace:
            innernamespace_.export(outfile, level, namespace_, name_='innernamespace')
        for innerpage_ in self.innerpage:
            innerpage_.export(outfile, level, namespace_, name_='innerpage')
        for innergroup_ in self.innergroup:
            innergroup_.export(outfile, level, namespace_, name_='innergroup')
        if self.templateparamlist:
            self.templateparamlist.export(outfile, level, namespace_, name_='templateparamlist')
        for sectiondef_ in self.sectiondef:
            sectiondef_.export(outfile, level, namespace_, name_='sectiondef')
        if self.briefdescription:
            self.briefdescription.export(outfile, level, namespace_, name_='briefdescription')
        if self.detaileddescription:
            self.detaileddescription.export(outfile, level, namespace_, name_='detaileddescription')
        if self.inheritancegraph:
            self.inheritancegraph.export(outfile, level, namespace_, name_='inheritancegraph')
        if self.collaborationgraph:
            self.collaborationgraph.export(outfile, level, namespace_, name_='collaborationgraph')
        if self.programlisting:
            self.programlisting.export(outfile, level, namespace_, name_='programlisting')
        if self.location:
            self.location.export(outfile, level, namespace_, name_='location')
        if self.listofallmembers:
            self.listofallmembers.export(outfile, level, namespace_, name_='listofallmembers')
    def hasContent_(self):
        if (
            self.compoundname is not None or
            self.title is not None or
            self.basecompoundref is not None or
            self.derivedcompoundref is not None or
            self.includes is not None or
            self.includedby is not None or
            self.incdepgraph is not None or
            self.invincdepgraph is not None or
            self.innerdir is not None or
            self.innerfile is not None or
            self.innerclass is not None or
            self.innernamespace is not None or
            self.innerpage is not None or
            self.innergroup is not None or
            self.templateparamlist is not None or
            self.sectiondef is not None or
            self.briefdescription is not None or
            self.detaileddescription is not None or
            self.inheritancegraph is not None or
            self.collaborationgraph is not None or
            self.programlisting is not None or
            self.location is not None or
            self.listofallmembers is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='compounddefType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.kind is not None:
            showIndent(outfile, level)
            outfile.write('kind = "%s",\n' % (self.kind,))
        if self.prot is not None:
            showIndent(outfile, level)
            outfile.write('prot = "%s",\n' % (self.prot,))
        if self.id is not None:
            showIndent(outfile, level)
            outfile.write('id = %s,\n' % (self.id,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('compoundname=%s,\n' % quote_python(self.compoundname).encode(ExternalEncoding))
        if self.title:
            showIndent(outfile, level)
            outfile.write('title=model_.xsd_string(\n')
            self.title.exportLiteral(outfile, level, name_='title')
            showIndent(outfile, level)
            outfile.write('),\n')
        showIndent(outfile, level)
        outfile.write('basecompoundref=[\n')
        level += 1
        for basecompoundref in self.basecompoundref:
            showIndent(outfile, level)
            outfile.write('model_.basecompoundref(\n')
            basecompoundref.exportLiteral(outfile, level, name_='basecompoundref')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('derivedcompoundref=[\n')
        level += 1
        for derivedcompoundref in self.derivedcompoundref:
            showIndent(outfile, level)
            outfile.write('model_.derivedcompoundref(\n')
            derivedcompoundref.exportLiteral(outfile, level, name_='derivedcompoundref')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('includes=[\n')
        level += 1
        for includes in self.includes:
            showIndent(outfile, level)
            outfile.write('model_.includes(\n')
            includes.exportLiteral(outfile, level, name_='includes')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('includedby=[\n')
        level += 1
        for includedby in self.includedby:
            showIndent(outfile, level)
            outfile.write('model_.includedby(\n')
            includedby.exportLiteral(outfile, level, name_='includedby')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
        if self.incdepgraph:
            showIndent(outfile, level)
            outfile.write('incdepgraph=model_.graphType(\n')
            self.incdepgraph.exportLiteral(outfile, level, name_='incdepgraph')
            showIndent(outfile, level)
            outfile.write('),\n')
        if self.invincdepgraph:
            showIndent(outfile, level)
            outfile.write('invincdepgraph=model_.graphType(\n')
            self.invincdepgraph.exportLiteral(outfile, level, name_='invincdepgraph')
            showIndent(outfile, level)
            outfile.write('),\n')
        showIndent(outfile, level)
        outfile.write('innerdir=[\n')
        level += 1
        for innerdir in self.innerdir:
            showIndent(outfile, level)
            outfile.write('model_.innerdir(\n')
            innerdir.exportLiteral(outfile, level, name_='innerdir')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('innerfile=[\n')
        level += 1
        for innerfile in self.innerfile:
            showIndent(outfile, level)
            outfile.write('model_.innerfile(\n')
            innerfile.exportLiteral(outfile, level, name_='innerfile')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('innerclass=[\n')
        level += 1
        for innerclass in self.innerclass:
            showIndent(outfile, level)
            outfile.write('model_.innerclass(\n')
            innerclass.exportLiteral(outfile, level, name_='innerclass')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('innernamespace=[\n')
        level += 1
        for innernamespace in self.innernamespace:
            showIndent(outfile, level)
            outfile.write('model_.innernamespace(\n')
            innernamespace.exportLiteral(outfile, level, name_='innernamespace')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('innerpage=[\n')
        level += 1
        for innerpage in self.innerpage:
            showIndent(outfile, level)
            outfile.write('model_.innerpage(\n')
            innerpage.exportLiteral(outfile, level, name_='innerpage')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('innergroup=[\n')
        level += 1
        for innergroup in self.innergroup:
            showIndent(outfile, level)
            outfile.write('model_.innergroup(\n')
            innergroup.exportLiteral(outfile, level, name_='innergroup')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
        if self.templateparamlist:
            showIndent(outfile, level)
            outfile.write('templateparamlist=model_.templateparamlistType(\n')
            self.templateparamlist.exportLiteral(outfile, level, name_='templateparamlist')
            showIndent(outfile, level)
            outfile.write('),\n')
        showIndent(outfile, level)
        outfile.write('sectiondef=[\n')
        level += 1
        for sectiondef in self.sectiondef:
            showIndent(outfile, level)
            outfile.write('model_.sectiondef(\n')
            sectiondef.exportLiteral(outfile, level, name_='sectiondef')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
        if self.briefdescription:
            showIndent(outfile, level)
            outfile.write('briefdescription=model_.descriptionType(\n')
            self.briefdescription.exportLiteral(outfile, level, name_='briefdescription')
            showIndent(outfile, level)
            outfile.write('),\n')
        if self.detaileddescription:
            showIndent(outfile, level)
            outfile.write('detaileddescription=model_.descriptionType(\n')
            self.detaileddescription.exportLiteral(outfile, level, name_='detaileddescription')
            showIndent(outfile, level)
            outfile.write('),\n')
        if self.inheritancegraph:
            showIndent(outfile, level)
            outfile.write('inheritancegraph=model_.graphType(\n')
            self.inheritancegraph.exportLiteral(outfile, level, name_='inheritancegraph')
            showIndent(outfile, level)
            outfile.write('),\n')
        if self.collaborationgraph:
            showIndent(outfile, level)
            outfile.write('collaborationgraph=model_.graphType(\n')
            self.collaborationgraph.exportLiteral(outfile, level, name_='collaborationgraph')
            showIndent(outfile, level)
            outfile.write('),\n')
        if self.programlisting:
            showIndent(outfile, level)
            outfile.write('programlisting=model_.listingType(\n')
            self.programlisting.exportLiteral(outfile, level, name_='programlisting')
            showIndent(outfile, level)
            outfile.write('),\n')
        if self.location:
            showIndent(outfile, level)
            outfile.write('location=model_.locationType(\n')
            self.location.exportLiteral(outfile, level, name_='location')
            showIndent(outfile, level)
            outfile.write('),\n')
        if self.listofallmembers:
            showIndent(outfile, level)
            outfile.write('listofallmembers=model_.listofallmembersType(\n')
            self.listofallmembers.exportLiteral(outfile, level, name_='listofallmembers')
            showIndent(outfile, level)
            outfile.write('),\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('kind'):
            self.kind = attrs.get('kind').value
        if attrs.get('prot'):
            self.prot = attrs.get('prot').value
        if attrs.get('id'):
            self.id = attrs.get('id').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'compoundname':
            compoundname_ = ''
            for text__content_ in child_.childNodes:
                compoundname_ += text__content_.nodeValue
            self.compoundname = compoundname_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'title':
            obj_ = docTitleType.factory()
            obj_.build(child_)
            self.set_title(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'basecompoundref':
            obj_ = compoundRefType.factory()
            obj_.build(child_)
            self.basecompoundref.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'derivedcompoundref':
            obj_ = compoundRefType.factory()
            obj_.build(child_)
            self.derivedcompoundref.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'includes':
            obj_ = incType.factory()
            obj_.build(child_)
            self.includes.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'includedby':
            obj_ = incType.factory()
            obj_.build(child_)
            self.includedby.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'incdepgraph':
            obj_ = graphType.factory()
            obj_.build(child_)
            self.set_incdepgraph(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'invincdepgraph':
            obj_ = graphType.factory()
            obj_.build(child_)
            self.set_invincdepgraph(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'innerdir':
            obj_ = refType.factory()
            obj_.build(child_)
            self.innerdir.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'innerfile':
            obj_ = refType.factory()
            obj_.build(child_)
            self.innerfile.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'innerclass':
            obj_ = refType.factory()
            obj_.build(child_)
            self.innerclass.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'innernamespace':
            obj_ = refType.factory()
            obj_.build(child_)
            self.innernamespace.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'innerpage':
            obj_ = refType.factory()
            obj_.build(child_)
            self.innerpage.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'innergroup':
            obj_ = refType.factory()
            obj_.build(child_)
            self.innergroup.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'templateparamlist':
            obj_ = templateparamlistType.factory()
            obj_.build(child_)
            self.set_templateparamlist(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'sectiondef':
            obj_ = sectiondefType.factory()
            obj_.build(child_)
            self.sectiondef.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'briefdescription':
            obj_ = descriptionType.factory()
            obj_.build(child_)
            self.set_briefdescription(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'detaileddescription':
            obj_ = descriptionType.factory()
            obj_.build(child_)
            self.set_detaileddescription(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'inheritancegraph':
            obj_ = graphType.factory()
            obj_.build(child_)
            self.set_inheritancegraph(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'collaborationgraph':
            obj_ = graphType.factory()
            obj_.build(child_)
            self.set_collaborationgraph(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'programlisting':
            obj_ = listingType.factory()
            obj_.build(child_)
            self.set_programlisting(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'location':
            obj_ = locationType.factory()
            obj_.build(child_)
            self.set_location(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'listofallmembers':
            obj_ = listofallmembersType.factory()
            obj_.build(child_)
            self.set_listofallmembers(obj_)
# end class compounddefType


class listofallmembersType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, member=None):
        if member is None:
            self.member = []
        else:
            self.member = member
    def factory(*args_, **kwargs_):
        if listofallmembersType.subclass:
            return listofallmembersType.subclass(*args_, **kwargs_)
        else:
            return listofallmembersType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_member(self): return self.member
    def set_member(self, member): self.member = member
    def add_member(self, value): self.member.append(value)
    def insert_member(self, index, value): self.member[index] = value
    def export(self, outfile, level, namespace_='', name_='listofallmembersType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='listofallmembersType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='listofallmembersType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='listofallmembersType'):
        for member_ in self.member:
            member_.export(outfile, level, namespace_, name_='member')
    def hasContent_(self):
        if (
            self.member is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='listofallmembersType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('member=[\n')
        level += 1
        for member in self.member:
            showIndent(outfile, level)
            outfile.write('model_.member(\n')
            member.exportLiteral(outfile, level, name_='member')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'member':
            obj_ = memberRefType.factory()
            obj_.build(child_)
            self.member.append(obj_)
# end class listofallmembersType


class memberRefType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, virt=None, prot=None, refid=None, ambiguityscope=None, scope=None, name=None):
        self.virt = virt
        self.prot = prot
        self.refid = refid
        self.ambiguityscope = ambiguityscope
        self.scope = scope
        self.name = name
    def factory(*args_, **kwargs_):
        if memberRefType.subclass:
            return memberRefType.subclass(*args_, **kwargs_)
        else:
            return memberRefType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_scope(self): return self.scope
    def set_scope(self, scope): self.scope = scope
    def get_name(self): return self.name
    def set_name(self, name): self.name = name
    def get_virt(self): return self.virt
    def set_virt(self, virt): self.virt = virt
    def get_prot(self): return self.prot
    def set_prot(self, prot): self.prot = prot
    def get_refid(self): return self.refid
    def set_refid(self, refid): self.refid = refid
    def get_ambiguityscope(self): return self.ambiguityscope
    def set_ambiguityscope(self, ambiguityscope): self.ambiguityscope = ambiguityscope
    def export(self, outfile, level, namespace_='', name_='memberRefType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='memberRefType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='memberRefType'):
        if self.virt is not None:
            outfile.write(' virt=%s' % (quote_attrib(self.virt), ))
        if self.prot is not None:
            outfile.write(' prot=%s' % (quote_attrib(self.prot), ))
        if self.refid is not None:
            outfile.write(' refid=%s' % (self.format_string(quote_attrib(self.refid).encode(ExternalEncoding), input_name='refid'), ))
        if self.ambiguityscope is not None:
            outfile.write(' ambiguityscope=%s' % (self.format_string(quote_attrib(self.ambiguityscope).encode(ExternalEncoding), input_name='ambiguityscope'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='memberRefType'):
        if self.scope is not None:
            showIndent(outfile, level)
            outfile.write('<%sscope>%s</%sscope>\n' % (namespace_, self.format_string(quote_xml(self.scope).encode(ExternalEncoding), input_name='scope'), namespace_))
        if self.name is not None:
            showIndent(outfile, level)
            outfile.write('<%sname>%s</%sname>\n' % (namespace_, self.format_string(quote_xml(self.name).encode(ExternalEncoding), input_name='name'), namespace_))
    def hasContent_(self):
        if (
            self.scope is not None or
            self.name is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='memberRefType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.virt is not None:
            showIndent(outfile, level)
            outfile.write('virt = "%s",\n' % (self.virt,))
        if self.prot is not None:
            showIndent(outfile, level)
            outfile.write('prot = "%s",\n' % (self.prot,))
        if self.refid is not None:
            showIndent(outfile, level)
            outfile.write('refid = %s,\n' % (self.refid,))
        if self.ambiguityscope is not None:
            showIndent(outfile, level)
            outfile.write('ambiguityscope = %s,\n' % (self.ambiguityscope,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('scope=%s,\n' % quote_python(self.scope).encode(ExternalEncoding))
        showIndent(outfile, level)
        outfile.write('name=%s,\n' % quote_python(self.name).encode(ExternalEncoding))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('virt'):
            self.virt = attrs.get('virt').value
        if attrs.get('prot'):
            self.prot = attrs.get('prot').value
        if attrs.get('refid'):
            self.refid = attrs.get('refid').value
        if attrs.get('ambiguityscope'):
            self.ambiguityscope = attrs.get('ambiguityscope').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'scope':
            scope_ = ''
            for text__content_ in child_.childNodes:
                scope_ += text__content_.nodeValue
            self.scope = scope_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'name':
            name_ = ''
            for text__content_ in child_.childNodes:
                name_ += text__content_.nodeValue
            self.name = name_
# end class memberRefType


class scope(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_=''):
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if scope.subclass:
            return scope.subclass(*args_, **kwargs_)
        else:
            return scope(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='scope', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='scope')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='scope'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='scope'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='scope'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class scope


class name(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_=''):
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if name.subclass:
            return name.subclass(*args_, **kwargs_)
        else:
            return name(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='name', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='name')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='name'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='name'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='name'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class name


class compoundRefType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, virt=None, prot=None, refid=None, valueOf_='', mixedclass_=None, content_=None):
        self.virt = virt
        self.prot = prot
        self.refid = refid
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if compoundRefType.subclass:
            return compoundRefType.subclass(*args_, **kwargs_)
        else:
            return compoundRefType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_virt(self): return self.virt
    def set_virt(self, virt): self.virt = virt
    def get_prot(self): return self.prot
    def set_prot(self, prot): self.prot = prot
    def get_refid(self): return self.refid
    def set_refid(self, refid): self.refid = refid
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='compoundRefType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='compoundRefType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='compoundRefType'):
        if self.virt is not None:
            outfile.write(' virt=%s' % (quote_attrib(self.virt), ))
        if self.prot is not None:
            outfile.write(' prot=%s' % (quote_attrib(self.prot), ))
        if self.refid is not None:
            outfile.write(' refid=%s' % (self.format_string(quote_attrib(self.refid).encode(ExternalEncoding), input_name='refid'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='compoundRefType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='compoundRefType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.virt is not None:
            showIndent(outfile, level)
            outfile.write('virt = "%s",\n' % (self.virt,))
        if self.prot is not None:
            showIndent(outfile, level)
            outfile.write('prot = "%s",\n' % (self.prot,))
        if self.refid is not None:
            showIndent(outfile, level)
            outfile.write('refid = %s,\n' % (self.refid,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('virt'):
            self.virt = attrs.get('virt').value
        if attrs.get('prot'):
            self.prot = attrs.get('prot').value
        if attrs.get('refid'):
            self.refid = attrs.get('refid').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class compoundRefType


class reimplementType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, refid=None, valueOf_='', mixedclass_=None, content_=None):
        self.refid = refid
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if reimplementType.subclass:
            return reimplementType.subclass(*args_, **kwargs_)
        else:
            return reimplementType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_refid(self): return self.refid
    def set_refid(self, refid): self.refid = refid
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='reimplementType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='reimplementType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='reimplementType'):
        if self.refid is not None:
            outfile.write(' refid=%s' % (self.format_string(quote_attrib(self.refid).encode(ExternalEncoding), input_name='refid'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='reimplementType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='reimplementType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.refid is not None:
            showIndent(outfile, level)
            outfile.write('refid = %s,\n' % (self.refid,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('refid'):
            self.refid = attrs.get('refid').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class reimplementType


class incType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, local=None, refid=None, valueOf_='', mixedclass_=None, content_=None):
        self.local = local
        self.refid = refid
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if incType.subclass:
            return incType.subclass(*args_, **kwargs_)
        else:
            return incType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_local(self): return self.local
    def set_local(self, local): self.local = local
    def get_refid(self): return self.refid
    def set_refid(self, refid): self.refid = refid
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='incType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='incType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='incType'):
        if self.local is not None:
            outfile.write(' local=%s' % (quote_attrib(self.local), ))
        if self.refid is not None:
            outfile.write(' refid=%s' % (self.format_string(quote_attrib(self.refid).encode(ExternalEncoding), input_name='refid'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='incType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='incType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.local is not None:
            showIndent(outfile, level)
            outfile.write('local = "%s",\n' % (self.local,))
        if self.refid is not None:
            showIndent(outfile, level)
            outfile.write('refid = %s,\n' % (self.refid,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('local'):
            self.local = attrs.get('local').value
        if attrs.get('refid'):
            self.refid = attrs.get('refid').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class incType


class refType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, prot=None, refid=None, valueOf_='', mixedclass_=None, content_=None):
        self.prot = prot
        self.refid = refid
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if refType.subclass:
            return refType.subclass(*args_, **kwargs_)
        else:
            return refType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_prot(self): return self.prot
    def set_prot(self, prot): self.prot = prot
    def get_refid(self): return self.refid
    def set_refid(self, refid): self.refid = refid
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='refType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='refType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='refType'):
        if self.prot is not None:
            outfile.write(' prot=%s' % (quote_attrib(self.prot), ))
        if self.refid is not None:
            outfile.write(' refid=%s' % (self.format_string(quote_attrib(self.refid).encode(ExternalEncoding), input_name='refid'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='refType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='refType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.prot is not None:
            showIndent(outfile, level)
            outfile.write('prot = "%s",\n' % (self.prot,))
        if self.refid is not None:
            showIndent(outfile, level)
            outfile.write('refid = %s,\n' % (self.refid,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('prot'):
            self.prot = attrs.get('prot').value
        if attrs.get('refid'):
            self.refid = attrs.get('refid').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class refType


class refTextType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, refid=None, kindref=None, external=None, valueOf_='', mixedclass_=None, content_=None):
        self.refid = refid
        self.kindref = kindref
        self.external = external
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if refTextType.subclass:
            return refTextType.subclass(*args_, **kwargs_)
        else:
            return refTextType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_refid(self): return self.refid
    def set_refid(self, refid): self.refid = refid
    def get_kindref(self): return self.kindref
    def set_kindref(self, kindref): self.kindref = kindref
    def get_external(self): return self.external
    def set_external(self, external): self.external = external
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='refTextType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='refTextType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='refTextType'):
        if self.refid is not None:
            outfile.write(' refid=%s' % (self.format_string(quote_attrib(self.refid).encode(ExternalEncoding), input_name='refid'), ))
        if self.kindref is not None:
            outfile.write(' kindref=%s' % (quote_attrib(self.kindref), ))
        if self.external is not None:
            outfile.write(' external=%s' % (self.format_string(quote_attrib(self.external).encode(ExternalEncoding), input_name='external'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='refTextType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='refTextType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.refid is not None:
            showIndent(outfile, level)
            outfile.write('refid = %s,\n' % (self.refid,))
        if self.kindref is not None:
            showIndent(outfile, level)
            outfile.write('kindref = "%s",\n' % (self.kindref,))
        if self.external is not None:
            showIndent(outfile, level)
            outfile.write('external = %s,\n' % (self.external,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('refid'):
            self.refid = attrs.get('refid').value
        if attrs.get('kindref'):
            self.kindref = attrs.get('kindref').value
        if attrs.get('external'):
            self.external = attrs.get('external').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class refTextType


class sectiondefType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, kind=None, header=None, description=None, memberdef=None):
        self.kind = kind
        self.header = header
        self.description = description
        if memberdef is None:
            self.memberdef = []
        else:
            self.memberdef = memberdef
    def factory(*args_, **kwargs_):
        if sectiondefType.subclass:
            return sectiondefType.subclass(*args_, **kwargs_)
        else:
            return sectiondefType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_header(self): return self.header
    def set_header(self, header): self.header = header
    def get_description(self): return self.description
    def set_description(self, description): self.description = description
    def get_memberdef(self): return self.memberdef
    def set_memberdef(self, memberdef): self.memberdef = memberdef
    def add_memberdef(self, value): self.memberdef.append(value)
    def insert_memberdef(self, index, value): self.memberdef[index] = value
    def get_kind(self): return self.kind
    def set_kind(self, kind): self.kind = kind
    def export(self, outfile, level, namespace_='', name_='sectiondefType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='sectiondefType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='sectiondefType'):
        if self.kind is not None:
            outfile.write(' kind=%s' % (quote_attrib(self.kind), ))
    def exportChildren(self, outfile, level, namespace_='', name_='sectiondefType'):
        if self.header is not None:
            showIndent(outfile, level)
            outfile.write('<%sheader>%s</%sheader>\n' % (namespace_, self.format_string(quote_xml(self.header).encode(ExternalEncoding), input_name='header'), namespace_))
        if self.description:
            self.description.export(outfile, level, namespace_, name_='description')
        for memberdef_ in self.memberdef:
            memberdef_.export(outfile, level, namespace_, name_='memberdef')
    def hasContent_(self):
        if (
            self.header is not None or
            self.description is not None or
            self.memberdef is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='sectiondefType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.kind is not None:
            showIndent(outfile, level)
            outfile.write('kind = "%s",\n' % (self.kind,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('header=%s,\n' % quote_python(self.header).encode(ExternalEncoding))
        if self.description:
            showIndent(outfile, level)
            outfile.write('description=model_.descriptionType(\n')
            self.description.exportLiteral(outfile, level, name_='description')
            showIndent(outfile, level)
            outfile.write('),\n')
        showIndent(outfile, level)
        outfile.write('memberdef=[\n')
        level += 1
        for memberdef in self.memberdef:
            showIndent(outfile, level)
            outfile.write('model_.memberdef(\n')
            memberdef.exportLiteral(outfile, level, name_='memberdef')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('kind'):
            self.kind = attrs.get('kind').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'header':
            header_ = ''
            for text__content_ in child_.childNodes:
                header_ += text__content_.nodeValue
            self.header = header_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'description':
            obj_ = descriptionType.factory()
            obj_.build(child_)
            self.set_description(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'memberdef':
            obj_ = memberdefType.factory()
            obj_.build(child_)
            self.memberdef.append(obj_)
# end class sectiondefType


class memberdefType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, initonly=None, kind=None, volatile=None, const=None, raisexx=None, virt=None, readable=None, prot=None, explicit=None, new=None, final=None, writable=None, add=None, static=None, remove=None, sealed=None, mutable=None, gettable=None, inline=None, settable=None, id=None, templateparamlist=None, type_=None, definition=None, argsstring=None, name=None, read=None, write=None, bitfield=None, reimplements=None, reimplementedby=None, param=None, enumvalue=None, initializer=None, exceptions=None, briefdescription=None, detaileddescription=None, inbodydescription=None, location=None, references=None, referencedby=None):
        self.initonly = initonly
        self.kind = kind
        self.volatile = volatile
        self.const = const
        self.raisexx = raisexx
        self.virt = virt
        self.readable = readable
        self.prot = prot
        self.explicit = explicit
        self.new = new
        self.final = final
        self.writable = writable
        self.add = add
        self.static = static
        self.remove = remove
        self.sealed = sealed
        self.mutable = mutable
        self.gettable = gettable
        self.inline = inline
        self.settable = settable
        self.id = id
        self.templateparamlist = templateparamlist
        self.type_ = type_
        self.definition = definition
        self.argsstring = argsstring
        self.name = name
        self.read = read
        self.write = write
        self.bitfield = bitfield
        if reimplements is None:
            self.reimplements = []
        else:
            self.reimplements = reimplements
        if reimplementedby is None:
            self.reimplementedby = []
        else:
            self.reimplementedby = reimplementedby
        if param is None:
            self.param = []
        else:
            self.param = param
        if enumvalue is None:
            self.enumvalue = []
        else:
            self.enumvalue = enumvalue
        self.initializer = initializer
        self.exceptions = exceptions
        self.briefdescription = briefdescription
        self.detaileddescription = detaileddescription
        self.inbodydescription = inbodydescription
        self.location = location
        if references is None:
            self.references = []
        else:
            self.references = references
        if referencedby is None:
            self.referencedby = []
        else:
            self.referencedby = referencedby
    def factory(*args_, **kwargs_):
        if memberdefType.subclass:
            return memberdefType.subclass(*args_, **kwargs_)
        else:
            return memberdefType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_templateparamlist(self): return self.templateparamlist
    def set_templateparamlist(self, templateparamlist): self.templateparamlist = templateparamlist
    def get_type(self): return self.type_
    def set_type(self, type_): self.type_ = type_
    def get_definition(self): return self.definition
    def set_definition(self, definition): self.definition = definition
    def get_argsstring(self): return self.argsstring
    def set_argsstring(self, argsstring): self.argsstring = argsstring
    def get_name(self): return self.name
    def set_name(self, name): self.name = name
    def get_read(self): return self.read
    def set_read(self, read): self.read = read
    def get_write(self): return self.write
    def set_write(self, write): self.write = write
    def get_bitfield(self): return self.bitfield
    def set_bitfield(self, bitfield): self.bitfield = bitfield
    def get_reimplements(self): return self.reimplements
    def set_reimplements(self, reimplements): self.reimplements = reimplements
    def add_reimplements(self, value): self.reimplements.append(value)
    def insert_reimplements(self, index, value): self.reimplements[index] = value
    def get_reimplementedby(self): return self.reimplementedby
    def set_reimplementedby(self, reimplementedby): self.reimplementedby = reimplementedby
    def add_reimplementedby(self, value): self.reimplementedby.append(value)
    def insert_reimplementedby(self, index, value): self.reimplementedby[index] = value
    def get_param(self): return self.param
    def set_param(self, param): self.param = param
    def add_param(self, value): self.param.append(value)
    def insert_param(self, index, value): self.param[index] = value
    def get_enumvalue(self): return self.enumvalue
    def set_enumvalue(self, enumvalue): self.enumvalue = enumvalue
    def add_enumvalue(self, value): self.enumvalue.append(value)
    def insert_enumvalue(self, index, value): self.enumvalue[index] = value
    def get_initializer(self): return self.initializer
    def set_initializer(self, initializer): self.initializer = initializer
    def get_exceptions(self): return self.exceptions
    def set_exceptions(self, exceptions): self.exceptions = exceptions
    def get_briefdescription(self): return self.briefdescription
    def set_briefdescription(self, briefdescription): self.briefdescription = briefdescription
    def get_detaileddescription(self): return self.detaileddescription
    def set_detaileddescription(self, detaileddescription): self.detaileddescription = detaileddescription
    def get_inbodydescription(self): return self.inbodydescription
    def set_inbodydescription(self, inbodydescription): self.inbodydescription = inbodydescription
    def get_location(self): return self.location
    def set_location(self, location): self.location = location
    def get_references(self): return self.references
    def set_references(self, references): self.references = references
    def add_references(self, value): self.references.append(value)
    def insert_references(self, index, value): self.references[index] = value
    def get_referencedby(self): return self.referencedby
    def set_referencedby(self, referencedby): self.referencedby = referencedby
    def add_referencedby(self, value): self.referencedby.append(value)
    def insert_referencedby(self, index, value): self.referencedby[index] = value
    def get_initonly(self): return self.initonly
    def set_initonly(self, initonly): self.initonly = initonly
    def get_kind(self): return self.kind
    def set_kind(self, kind): self.kind = kind
    def get_volatile(self): return self.volatile
    def set_volatile(self, volatile): self.volatile = volatile
    def get_const(self): return self.const
    def set_const(self, const): self.const = const
    def get_raise(self): return self.raisexx
    def set_raise(self, raisexx): self.raisexx = raisexx
    def get_virt(self): return self.virt
    def set_virt(self, virt): self.virt = virt
    def get_readable(self): return self.readable
    def set_readable(self, readable): self.readable = readable
    def get_prot(self): return self.prot
    def set_prot(self, prot): self.prot = prot
    def get_explicit(self): return self.explicit
    def set_explicit(self, explicit): self.explicit = explicit
    def get_new(self): return self.new
    def set_new(self, new): self.new = new
    def get_final(self): return self.final
    def set_final(self, final): self.final = final
    def get_writable(self): return self.writable
    def set_writable(self, writable): self.writable = writable
    def get_add(self): return self.add
    def set_add(self, add): self.add = add
    def get_static(self): return self.static
    def set_static(self, static): self.static = static
    def get_remove(self): return self.remove
    def set_remove(self, remove): self.remove = remove
    def get_sealed(self): return self.sealed
    def set_sealed(self, sealed): self.sealed = sealed
    def get_mutable(self): return self.mutable
    def set_mutable(self, mutable): self.mutable = mutable
    def get_gettable(self): return self.gettable
    def set_gettable(self, gettable): self.gettable = gettable
    def get_inline(self): return self.inline
    def set_inline(self, inline): self.inline = inline
    def get_settable(self): return self.settable
    def set_settable(self, settable): self.settable = settable
    def get_id(self): return self.id
    def set_id(self, id): self.id = id
    def export(self, outfile, level, namespace_='', name_='memberdefType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='memberdefType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='memberdefType'):
        if self.initonly is not None:
            outfile.write(' initonly=%s' % (quote_attrib(self.initonly), ))
        if self.kind is not None:
            outfile.write(' kind=%s' % (quote_attrib(self.kind), ))
        if self.volatile is not None:
            outfile.write(' volatile=%s' % (quote_attrib(self.volatile), ))
        if self.const is not None:
            outfile.write(' const=%s' % (quote_attrib(self.const), ))
        if self.raisexx is not None:
            outfile.write(' raise=%s' % (quote_attrib(self.raisexx), ))
        if self.virt is not None:
            outfile.write(' virt=%s' % (quote_attrib(self.virt), ))
        if self.readable is not None:
            outfile.write(' readable=%s' % (quote_attrib(self.readable), ))
        if self.prot is not None:
            outfile.write(' prot=%s' % (quote_attrib(self.prot), ))
        if self.explicit is not None:
            outfile.write(' explicit=%s' % (quote_attrib(self.explicit), ))
        if self.new is not None:
            outfile.write(' new=%s' % (quote_attrib(self.new), ))
        if self.final is not None:
            outfile.write(' final=%s' % (quote_attrib(self.final), ))
        if self.writable is not None:
            outfile.write(' writable=%s' % (quote_attrib(self.writable), ))
        if self.add is not None:
            outfile.write(' add=%s' % (quote_attrib(self.add), ))
        if self.static is not None:
            outfile.write(' static=%s' % (quote_attrib(self.static), ))
        if self.remove is not None:
            outfile.write(' remove=%s' % (quote_attrib(self.remove), ))
        if self.sealed is not None:
            outfile.write(' sealed=%s' % (quote_attrib(self.sealed), ))
        if self.mutable is not None:
            outfile.write(' mutable=%s' % (quote_attrib(self.mutable), ))
        if self.gettable is not None:
            outfile.write(' gettable=%s' % (quote_attrib(self.gettable), ))
        if self.inline is not None:
            outfile.write(' inline=%s' % (quote_attrib(self.inline), ))
        if self.settable is not None:
            outfile.write(' settable=%s' % (quote_attrib(self.settable), ))
        if self.id is not None:
            outfile.write(' id=%s' % (self.format_string(quote_attrib(self.id).encode(ExternalEncoding), input_name='id'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='memberdefType'):
        if self.templateparamlist:
            self.templateparamlist.export(outfile, level, namespace_, name_='templateparamlist')
        if self.type_:
            self.type_.export(outfile, level, namespace_, name_='type')
        if self.definition is not None:
            showIndent(outfile, level)
            outfile.write('<%sdefinition>%s</%sdefinition>\n' % (namespace_, self.format_string(quote_xml(self.definition).encode(ExternalEncoding), input_name='definition'), namespace_))
        if self.argsstring is not None:
            showIndent(outfile, level)
            outfile.write('<%sargsstring>%s</%sargsstring>\n' % (namespace_, self.format_string(quote_xml(self.argsstring).encode(ExternalEncoding), input_name='argsstring'), namespace_))
        if self.name is not None:
            showIndent(outfile, level)
            outfile.write('<%sname>%s</%sname>\n' % (namespace_, self.format_string(quote_xml(self.name).encode(ExternalEncoding), input_name='name'), namespace_))
        if self.read is not None:
            showIndent(outfile, level)
            outfile.write('<%sread>%s</%sread>\n' % (namespace_, self.format_string(quote_xml(self.read).encode(ExternalEncoding), input_name='read'), namespace_))
        if self.write is not None:
            showIndent(outfile, level)
            outfile.write('<%swrite>%s</%swrite>\n' % (namespace_, self.format_string(quote_xml(self.write).encode(ExternalEncoding), input_name='write'), namespace_))
        if self.bitfield is not None:
            showIndent(outfile, level)
            outfile.write('<%sbitfield>%s</%sbitfield>\n' % (namespace_, self.format_string(quote_xml(self.bitfield).encode(ExternalEncoding), input_name='bitfield'), namespace_))
        for reimplements_ in self.reimplements:
            reimplements_.export(outfile, level, namespace_, name_='reimplements')
        for reimplementedby_ in self.reimplementedby:
            reimplementedby_.export(outfile, level, namespace_, name_='reimplementedby')
        for param_ in self.param:
            param_.export(outfile, level, namespace_, name_='param')
        for enumvalue_ in self.enumvalue:
            enumvalue_.export(outfile, level, namespace_, name_='enumvalue')
        if self.initializer:
            self.initializer.export(outfile, level, namespace_, name_='initializer')
        if self.exceptions:
            self.exceptions.export(outfile, level, namespace_, name_='exceptions')
        if self.briefdescription:
            self.briefdescription.export(outfile, level, namespace_, name_='briefdescription')
        if self.detaileddescription:
            self.detaileddescription.export(outfile, level, namespace_, name_='detaileddescription')
        if self.inbodydescription:
            self.inbodydescription.export(outfile, level, namespace_, name_='inbodydescription')
        if self.location:
            self.location.export(outfile, level, namespace_, name_='location', )
        for references_ in self.references:
            references_.export(outfile, level, namespace_, name_='references')
        for referencedby_ in self.referencedby:
            referencedby_.export(outfile, level, namespace_, name_='referencedby')
    def hasContent_(self):
        if (
            self.templateparamlist is not None or
            self.type_ is not None or
            self.definition is not None or
            self.argsstring is not None or
            self.name is not None or
            self.read is not None or
            self.write is not None or
            self.bitfield is not None or
            self.reimplements is not None or
            self.reimplementedby is not None or
            self.param is not None or
            self.enumvalue is not None or
            self.initializer is not None or
            self.exceptions is not None or
            self.briefdescription is not None or
            self.detaileddescription is not None or
            self.inbodydescription is not None or
            self.location is not None or
            self.references is not None or
            self.referencedby is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='memberdefType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.initonly is not None:
            showIndent(outfile, level)
            outfile.write('initonly = "%s",\n' % (self.initonly,))
        if self.kind is not None:
            showIndent(outfile, level)
            outfile.write('kind = "%s",\n' % (self.kind,))
        if self.volatile is not None:
            showIndent(outfile, level)
            outfile.write('volatile = "%s",\n' % (self.volatile,))
        if self.const is not None:
            showIndent(outfile, level)
            outfile.write('const = "%s",\n' % (self.const,))
        if self.raisexx is not None:
            showIndent(outfile, level)
            outfile.write('raisexx = "%s",\n' % (self.raisexx,))
        if self.virt is not None:
            showIndent(outfile, level)
            outfile.write('virt = "%s",\n' % (self.virt,))
        if self.readable is not None:
            showIndent(outfile, level)
            outfile.write('readable = "%s",\n' % (self.readable,))
        if self.prot is not None:
            showIndent(outfile, level)
            outfile.write('prot = "%s",\n' % (self.prot,))
        if self.explicit is not None:
            showIndent(outfile, level)
            outfile.write('explicit = "%s",\n' % (self.explicit,))
        if self.new is not None:
            showIndent(outfile, level)
            outfile.write('new = "%s",\n' % (self.new,))
        if self.final is not None:
            showIndent(outfile, level)
            outfile.write('final = "%s",\n' % (self.final,))
        if self.writable is not None:
            showIndent(outfile, level)
            outfile.write('writable = "%s",\n' % (self.writable,))
        if self.add is not None:
            showIndent(outfile, level)
            outfile.write('add = "%s",\n' % (self.add,))
        if self.static is not None:
            showIndent(outfile, level)
            outfile.write('static = "%s",\n' % (self.static,))
        if self.remove is not None:
            showIndent(outfile, level)
            outfile.write('remove = "%s",\n' % (self.remove,))
        if self.sealed is not None:
            showIndent(outfile, level)
            outfile.write('sealed = "%s",\n' % (self.sealed,))
        if self.mutable is not None:
            showIndent(outfile, level)
            outfile.write('mutable = "%s",\n' % (self.mutable,))
        if self.gettable is not None:
            showIndent(outfile, level)
            outfile.write('gettable = "%s",\n' % (self.gettable,))
        if self.inline is not None:
            showIndent(outfile, level)
            outfile.write('inline = "%s",\n' % (self.inline,))
        if self.settable is not None:
            showIndent(outfile, level)
            outfile.write('settable = "%s",\n' % (self.settable,))
        if self.id is not None:
            showIndent(outfile, level)
            outfile.write('id = %s,\n' % (self.id,))
    def exportLiteralChildren(self, outfile, level, name_):
        if self.templateparamlist:
            showIndent(outfile, level)
            outfile.write('templateparamlist=model_.templateparamlistType(\n')
            self.templateparamlist.exportLiteral(outfile, level, name_='templateparamlist')
            showIndent(outfile, level)
            outfile.write('),\n')
        if self.type_:
            showIndent(outfile, level)
            outfile.write('type_=model_.linkedTextType(\n')
            self.type_.exportLiteral(outfile, level, name_='type')
            showIndent(outfile, level)
            outfile.write('),\n')
        showIndent(outfile, level)
        outfile.write('definition=%s,\n' % quote_python(self.definition).encode(ExternalEncoding))
        showIndent(outfile, level)
        outfile.write('argsstring=%s,\n' % quote_python(self.argsstring).encode(ExternalEncoding))
        showIndent(outfile, level)
        outfile.write('name=%s,\n' % quote_python(self.name).encode(ExternalEncoding))
        showIndent(outfile, level)
        outfile.write('read=%s,\n' % quote_python(self.read).encode(ExternalEncoding))
        showIndent(outfile, level)
        outfile.write('write=%s,\n' % quote_python(self.write).encode(ExternalEncoding))
        showIndent(outfile, level)
        outfile.write('bitfield=%s,\n' % quote_python(self.bitfield).encode(ExternalEncoding))
        showIndent(outfile, level)
        outfile.write('reimplements=[\n')
        level += 1
        for reimplements in self.reimplements:
            showIndent(outfile, level)
            outfile.write('model_.reimplements(\n')
            reimplements.exportLiteral(outfile, level, name_='reimplements')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('reimplementedby=[\n')
        level += 1
        for reimplementedby in self.reimplementedby:
            showIndent(outfile, level)
            outfile.write('model_.reimplementedby(\n')
            reimplementedby.exportLiteral(outfile, level, name_='reimplementedby')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('param=[\n')
        level += 1
        for param in self.param:
            showIndent(outfile, level)
            outfile.write('model_.param(\n')
            param.exportLiteral(outfile, level, name_='param')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('enumvalue=[\n')
        level += 1
        for enumvalue in self.enumvalue:
            showIndent(outfile, level)
            outfile.write('model_.enumvalue(\n')
            enumvalue.exportLiteral(outfile, level, name_='enumvalue')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
        if self.initializer:
            showIndent(outfile, level)
            outfile.write('initializer=model_.linkedTextType(\n')
            self.initializer.exportLiteral(outfile, level, name_='initializer')
            showIndent(outfile, level)
            outfile.write('),\n')
        if self.exceptions:
            showIndent(outfile, level)
            outfile.write('exceptions=model_.linkedTextType(\n')
            self.exceptions.exportLiteral(outfile, level, name_='exceptions')
            showIndent(outfile, level)
            outfile.write('),\n')
        if self.briefdescription:
            showIndent(outfile, level)
            outfile.write('briefdescription=model_.descriptionType(\n')
            self.briefdescription.exportLiteral(outfile, level, name_='briefdescription')
            showIndent(outfile, level)
            outfile.write('),\n')
        if self.detaileddescription:
            showIndent(outfile, level)
            outfile.write('detaileddescription=model_.descriptionType(\n')
            self.detaileddescription.exportLiteral(outfile, level, name_='detaileddescription')
            showIndent(outfile, level)
            outfile.write('),\n')
        if self.inbodydescription:
            showIndent(outfile, level)
            outfile.write('inbodydescription=model_.descriptionType(\n')
            self.inbodydescription.exportLiteral(outfile, level, name_='inbodydescription')
            showIndent(outfile, level)
            outfile.write('),\n')
        if self.location:
            showIndent(outfile, level)
            outfile.write('location=model_.locationType(\n')
            self.location.exportLiteral(outfile, level, name_='location')
            showIndent(outfile, level)
            outfile.write('),\n')
        showIndent(outfile, level)
        outfile.write('references=[\n')
        level += 1
        for references in self.references:
            showIndent(outfile, level)
            outfile.write('model_.references(\n')
            references.exportLiteral(outfile, level, name_='references')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('referencedby=[\n')
        level += 1
        for referencedby in self.referencedby:
            showIndent(outfile, level)
            outfile.write('model_.referencedby(\n')
            referencedby.exportLiteral(outfile, level, name_='referencedby')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('initonly'):
            self.initonly = attrs.get('initonly').value
        if attrs.get('kind'):
            self.kind = attrs.get('kind').value
        if attrs.get('volatile'):
            self.volatile = attrs.get('volatile').value
        if attrs.get('const'):
            self.const = attrs.get('const').value
        if attrs.get('raise'):
            self.raisexx = attrs.get('raise').value
        if attrs.get('virt'):
            self.virt = attrs.get('virt').value
        if attrs.get('readable'):
            self.readable = attrs.get('readable').value
        if attrs.get('prot'):
            self.prot = attrs.get('prot').value
        if attrs.get('explicit'):
            self.explicit = attrs.get('explicit').value
        if attrs.get('new'):
            self.new = attrs.get('new').value
        if attrs.get('final'):
            self.final = attrs.get('final').value
        if attrs.get('writable'):
            self.writable = attrs.get('writable').value
        if attrs.get('add'):
            self.add = attrs.get('add').value
        if attrs.get('static'):
            self.static = attrs.get('static').value
        if attrs.get('remove'):
            self.remove = attrs.get('remove').value
        if attrs.get('sealed'):
            self.sealed = attrs.get('sealed').value
        if attrs.get('mutable'):
            self.mutable = attrs.get('mutable').value
        if attrs.get('gettable'):
            self.gettable = attrs.get('gettable').value
        if attrs.get('inline'):
            self.inline = attrs.get('inline').value
        if attrs.get('settable'):
            self.settable = attrs.get('settable').value
        if attrs.get('id'):
            self.id = attrs.get('id').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'templateparamlist':
            obj_ = templateparamlistType.factory()
            obj_.build(child_)
            self.set_templateparamlist(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'type':
            obj_ = linkedTextType.factory()
            obj_.build(child_)
            self.set_type(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'definition':
            definition_ = ''
            for text__content_ in child_.childNodes:
                definition_ += text__content_.nodeValue
            self.definition = definition_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'argsstring':
            argsstring_ = ''
            for text__content_ in child_.childNodes:
                argsstring_ += text__content_.nodeValue
            self.argsstring = argsstring_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'name':
            name_ = ''
            for text__content_ in child_.childNodes:
                name_ += text__content_.nodeValue
            self.name = name_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'read':
            read_ = ''
            for text__content_ in child_.childNodes:
                read_ += text__content_.nodeValue
            self.read = read_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'write':
            write_ = ''
            for text__content_ in child_.childNodes:
                write_ += text__content_.nodeValue
            self.write = write_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'bitfield':
            bitfield_ = ''
            for text__content_ in child_.childNodes:
                bitfield_ += text__content_.nodeValue
            self.bitfield = bitfield_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'reimplements':
            obj_ = reimplementType.factory()
            obj_.build(child_)
            self.reimplements.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'reimplementedby':
            obj_ = reimplementType.factory()
            obj_.build(child_)
            self.reimplementedby.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'param':
            obj_ = paramType.factory()
            obj_.build(child_)
            self.param.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'enumvalue':
            obj_ = enumvalueType.factory()
            obj_.build(child_)
            self.enumvalue.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'initializer':
            obj_ = linkedTextType.factory()
            obj_.build(child_)
            self.set_initializer(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'exceptions':
            obj_ = linkedTextType.factory()
            obj_.build(child_)
            self.set_exceptions(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'briefdescription':
            obj_ = descriptionType.factory()
            obj_.build(child_)
            self.set_briefdescription(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'detaileddescription':
            obj_ = descriptionType.factory()
            obj_.build(child_)
            self.set_detaileddescription(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'inbodydescription':
            obj_ = descriptionType.factory()
            obj_.build(child_)
            self.set_inbodydescription(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'location':
            obj_ = locationType.factory()
            obj_.build(child_)
            self.set_location(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'references':
            obj_ = referenceType.factory()
            obj_.build(child_)
            self.references.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'referencedby':
            obj_ = referenceType.factory()
            obj_.build(child_)
            self.referencedby.append(obj_)
# end class memberdefType


class definition(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_=''):
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if definition.subclass:
            return definition.subclass(*args_, **kwargs_)
        else:
            return definition(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='definition', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='definition')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='definition'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='definition'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='definition'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class definition


class argsstring(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_=''):
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if argsstring.subclass:
            return argsstring.subclass(*args_, **kwargs_)
        else:
            return argsstring(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='argsstring', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='argsstring')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='argsstring'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='argsstring'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='argsstring'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class argsstring


class read(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_=''):
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if read.subclass:
            return read.subclass(*args_, **kwargs_)
        else:
            return read(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='read', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='read')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='read'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='read'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='read'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class read


class write(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_=''):
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if write.subclass:
            return write.subclass(*args_, **kwargs_)
        else:
            return write(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='write', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='write')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='write'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='write'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='write'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class write


class bitfield(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_=''):
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if bitfield.subclass:
            return bitfield.subclass(*args_, **kwargs_)
        else:
            return bitfield(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='bitfield', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='bitfield')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='bitfield'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='bitfield'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='bitfield'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class bitfield


class descriptionType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, title=None, para=None, sect1=None, internal=None, mixedclass_=None, content_=None):
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if descriptionType.subclass:
            return descriptionType.subclass(*args_, **kwargs_)
        else:
            return descriptionType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_title(self): return self.title
    def set_title(self, title): self.title = title
    def get_para(self): return self.para
    def set_para(self, para): self.para = para
    def add_para(self, value): self.para.append(value)
    def insert_para(self, index, value): self.para[index] = value
    def get_sect1(self): return self.sect1
    def set_sect1(self, sect1): self.sect1 = sect1
    def add_sect1(self, value): self.sect1.append(value)
    def insert_sect1(self, index, value): self.sect1[index] = value
    def get_internal(self): return self.internal
    def set_internal(self, internal): self.internal = internal
    def export(self, outfile, level, namespace_='', name_='descriptionType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='descriptionType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='descriptionType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='descriptionType'):
        for item_ in self.content_:
            item_.export(outfile, level, item_.name, namespace_)
    def hasContent_(self):
        if (
            self.title is not None or
            self.para is not None or
            self.sect1 is not None or
            self.internal is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='descriptionType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'title':
            childobj_ = docTitleType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'title', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'para':
            childobj_ = docParaType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'para', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'sect1':
            childobj_ = docSect1Type.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'sect1', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'internal':
            childobj_ = docInternalType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'internal', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
# end class descriptionType


class enumvalueType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, prot=None, id=None, name=None, initializer=None, briefdescription=None, detaileddescription=None, mixedclass_=None, content_=None):
        self.prot = prot
        self.id = id
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if enumvalueType.subclass:
            return enumvalueType.subclass(*args_, **kwargs_)
        else:
            return enumvalueType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_name(self): return self.name
    def set_name(self, name): self.name = name
    def get_initializer(self): return self.initializer
    def set_initializer(self, initializer): self.initializer = initializer
    def get_briefdescription(self): return self.briefdescription
    def set_briefdescription(self, briefdescription): self.briefdescription = briefdescription
    def get_detaileddescription(self): return self.detaileddescription
    def set_detaileddescription(self, detaileddescription): self.detaileddescription = detaileddescription
    def get_prot(self): return self.prot
    def set_prot(self, prot): self.prot = prot
    def get_id(self): return self.id
    def set_id(self, id): self.id = id
    def export(self, outfile, level, namespace_='', name_='enumvalueType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='enumvalueType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='enumvalueType'):
        if self.prot is not None:
            outfile.write(' prot=%s' % (quote_attrib(self.prot), ))
        if self.id is not None:
            outfile.write(' id=%s' % (self.format_string(quote_attrib(self.id).encode(ExternalEncoding), input_name='id'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='enumvalueType'):
        for item_ in self.content_:
            item_.export(outfile, level, item_.name, namespace_)
    def hasContent_(self):
        if (
            self.name is not None or
            self.initializer is not None or
            self.briefdescription is not None or
            self.detaileddescription is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='enumvalueType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.prot is not None:
            showIndent(outfile, level)
            outfile.write('prot = "%s",\n' % (self.prot,))
        if self.id is not None:
            showIndent(outfile, level)
            outfile.write('id = %s,\n' % (self.id,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('prot'):
            self.prot = attrs.get('prot').value
        if attrs.get('id'):
            self.id = attrs.get('id').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'name':
            value_ = []
            for text_ in child_.childNodes:
                value_.append(text_.nodeValue)
            valuestr_ = ''.join(value_)
            obj_ = self.mixedclass_(MixedContainer.CategorySimple,
                MixedContainer.TypeString, 'name', valuestr_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'initializer':
            childobj_ = linkedTextType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'initializer', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'briefdescription':
            childobj_ = descriptionType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'briefdescription', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'detaileddescription':
            childobj_ = descriptionType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'detaileddescription', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
# end class enumvalueType


class templateparamlistType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, param=None):
        if param is None:
            self.param = []
        else:
            self.param = param
    def factory(*args_, **kwargs_):
        if templateparamlistType.subclass:
            return templateparamlistType.subclass(*args_, **kwargs_)
        else:
            return templateparamlistType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_param(self): return self.param
    def set_param(self, param): self.param = param
    def add_param(self, value): self.param.append(value)
    def insert_param(self, index, value): self.param[index] = value
    def export(self, outfile, level, namespace_='', name_='templateparamlistType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='templateparamlistType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='templateparamlistType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='templateparamlistType'):
        for param_ in self.param:
            param_.export(outfile, level, namespace_, name_='param')
    def hasContent_(self):
        if (
            self.param is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='templateparamlistType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('param=[\n')
        level += 1
        for param in self.param:
            showIndent(outfile, level)
            outfile.write('model_.param(\n')
            param.exportLiteral(outfile, level, name_='param')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'param':
            obj_ = paramType.factory()
            obj_.build(child_)
            self.param.append(obj_)
# end class templateparamlistType


class paramType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, type_=None, declname=None, defname=None, array=None, defval=None, briefdescription=None):
        self.type_ = type_
        self.declname = declname
        self.defname = defname
        self.array = array
        self.defval = defval
        self.briefdescription = briefdescription
    def factory(*args_, **kwargs_):
        if paramType.subclass:
            return paramType.subclass(*args_, **kwargs_)
        else:
            return paramType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_type(self): return self.type_
    def set_type(self, type_): self.type_ = type_
    def get_declname(self): return self.declname
    def set_declname(self, declname): self.declname = declname
    def get_defname(self): return self.defname
    def set_defname(self, defname): self.defname = defname
    def get_array(self): return self.array
    def set_array(self, array): self.array = array
    def get_defval(self): return self.defval
    def set_defval(self, defval): self.defval = defval
    def get_briefdescription(self): return self.briefdescription
    def set_briefdescription(self, briefdescription): self.briefdescription = briefdescription
    def export(self, outfile, level, namespace_='', name_='paramType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='paramType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='paramType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='paramType'):
        if self.type_:
            self.type_.export(outfile, level, namespace_, name_='type')
        if self.declname is not None:
            showIndent(outfile, level)
            outfile.write('<%sdeclname>%s</%sdeclname>\n' % (namespace_, self.format_string(quote_xml(self.declname).encode(ExternalEncoding), input_name='declname'), namespace_))
        if self.defname is not None:
            showIndent(outfile, level)
            outfile.write('<%sdefname>%s</%sdefname>\n' % (namespace_, self.format_string(quote_xml(self.defname).encode(ExternalEncoding), input_name='defname'), namespace_))
        if self.array is not None:
            showIndent(outfile, level)
            outfile.write('<%sarray>%s</%sarray>\n' % (namespace_, self.format_string(quote_xml(self.array).encode(ExternalEncoding), input_name='array'), namespace_))
        if self.defval:
            self.defval.export(outfile, level, namespace_, name_='defval')
        if self.briefdescription:
            self.briefdescription.export(outfile, level, namespace_, name_='briefdescription')
    def hasContent_(self):
        if (
            self.type_ is not None or
            self.declname is not None or
            self.defname is not None or
            self.array is not None or
            self.defval is not None or
            self.briefdescription is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='paramType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        if self.type_:
            showIndent(outfile, level)
            outfile.write('type_=model_.linkedTextType(\n')
            self.type_.exportLiteral(outfile, level, name_='type')
            showIndent(outfile, level)
            outfile.write('),\n')
        showIndent(outfile, level)
        outfile.write('declname=%s,\n' % quote_python(self.declname).encode(ExternalEncoding))
        showIndent(outfile, level)
        outfile.write('defname=%s,\n' % quote_python(self.defname).encode(ExternalEncoding))
        showIndent(outfile, level)
        outfile.write('array=%s,\n' % quote_python(self.array).encode(ExternalEncoding))
        if self.defval:
            showIndent(outfile, level)
            outfile.write('defval=model_.linkedTextType(\n')
            self.defval.exportLiteral(outfile, level, name_='defval')
            showIndent(outfile, level)
            outfile.write('),\n')
        if self.briefdescription:
            showIndent(outfile, level)
            outfile.write('briefdescription=model_.descriptionType(\n')
            self.briefdescription.exportLiteral(outfile, level, name_='briefdescription')
            showIndent(outfile, level)
            outfile.write('),\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'type':
            obj_ = linkedTextType.factory()
            obj_.build(child_)
            self.set_type(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'declname':
            declname_ = ''
            for text__content_ in child_.childNodes:
                declname_ += text__content_.nodeValue
            self.declname = declname_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'defname':
            defname_ = ''
            for text__content_ in child_.childNodes:
                defname_ += text__content_.nodeValue
            self.defname = defname_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'array':
            array_ = ''
            for text__content_ in child_.childNodes:
                array_ += text__content_.nodeValue
            self.array = array_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'defval':
            obj_ = linkedTextType.factory()
            obj_.build(child_)
            self.set_defval(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'briefdescription':
            obj_ = descriptionType.factory()
            obj_.build(child_)
            self.set_briefdescription(obj_)
# end class paramType


class declname(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_=''):
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if declname.subclass:
            return declname.subclass(*args_, **kwargs_)
        else:
            return declname(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='declname', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='declname')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='declname'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='declname'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='declname'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class declname


class defname(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_=''):
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if defname.subclass:
            return defname.subclass(*args_, **kwargs_)
        else:
            return defname(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='defname', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='defname')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='defname'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='defname'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='defname'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class defname


class array(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_=''):
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if array.subclass:
            return array.subclass(*args_, **kwargs_)
        else:
            return array(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='array', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='array')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='array'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='array'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='array'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class array


class linkedTextType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, ref=None, mixedclass_=None, content_=None):
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if linkedTextType.subclass:
            return linkedTextType.subclass(*args_, **kwargs_)
        else:
            return linkedTextType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_ref(self): return self.ref
    def set_ref(self, ref): self.ref = ref
    def add_ref(self, value): self.ref.append(value)
    def insert_ref(self, index, value): self.ref[index] = value
    def export(self, outfile, level, namespace_='', name_='linkedTextType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='linkedTextType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='linkedTextType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='linkedTextType'):
        for item_ in self.content_:
            item_.export(outfile, level, item_.name, namespace_)
    def hasContent_(self):
        if (
            self.ref is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='linkedTextType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'ref':
            childobj_ = docRefTextType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'ref', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
# end class linkedTextType


class graphType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, node=None):
        if node is None:
            self.node = []
        else:
            self.node = node
    def factory(*args_, **kwargs_):
        if graphType.subclass:
            return graphType.subclass(*args_, **kwargs_)
        else:
            return graphType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_node(self): return self.node
    def set_node(self, node): self.node = node
    def add_node(self, value): self.node.append(value)
    def insert_node(self, index, value): self.node[index] = value
    def export(self, outfile, level, namespace_='', name_='graphType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='graphType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='graphType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='graphType'):
        for node_ in self.node:
            node_.export(outfile, level, namespace_, name_='node')
    def hasContent_(self):
        if (
            self.node is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='graphType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('node=[\n')
        level += 1
        for node in self.node:
            showIndent(outfile, level)
            outfile.write('model_.node(\n')
            node.exportLiteral(outfile, level, name_='node')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'node':
            obj_ = nodeType.factory()
            obj_.build(child_)
            self.node.append(obj_)
# end class graphType


class nodeType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, id=None, label=None, link=None, childnode=None):
        self.id = id
        self.label = label
        self.link = link
        if childnode is None:
            self.childnode = []
        else:
            self.childnode = childnode
    def factory(*args_, **kwargs_):
        if nodeType.subclass:
            return nodeType.subclass(*args_, **kwargs_)
        else:
            return nodeType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_label(self): return self.label
    def set_label(self, label): self.label = label
    def get_link(self): return self.link
    def set_link(self, link): self.link = link
    def get_childnode(self): return self.childnode
    def set_childnode(self, childnode): self.childnode = childnode
    def add_childnode(self, value): self.childnode.append(value)
    def insert_childnode(self, index, value): self.childnode[index] = value
    def get_id(self): return self.id
    def set_id(self, id): self.id = id
    def export(self, outfile, level, namespace_='', name_='nodeType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='nodeType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='nodeType'):
        if self.id is not None:
            outfile.write(' id=%s' % (self.format_string(quote_attrib(self.id).encode(ExternalEncoding), input_name='id'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='nodeType'):
        if self.label is not None:
            showIndent(outfile, level)
            outfile.write('<%slabel>%s</%slabel>\n' % (namespace_, self.format_string(quote_xml(self.label).encode(ExternalEncoding), input_name='label'), namespace_))
        if self.link:
            self.link.export(outfile, level, namespace_, name_='link')
        for childnode_ in self.childnode:
            childnode_.export(outfile, level, namespace_, name_='childnode')
    def hasContent_(self):
        if (
            self.label is not None or
            self.link is not None or
            self.childnode is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='nodeType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.id is not None:
            showIndent(outfile, level)
            outfile.write('id = %s,\n' % (self.id,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('label=%s,\n' % quote_python(self.label).encode(ExternalEncoding))
        if self.link:
            showIndent(outfile, level)
            outfile.write('link=model_.linkType(\n')
            self.link.exportLiteral(outfile, level, name_='link')
            showIndent(outfile, level)
            outfile.write('),\n')
        showIndent(outfile, level)
        outfile.write('childnode=[\n')
        level += 1
        for childnode in self.childnode:
            showIndent(outfile, level)
            outfile.write('model_.childnode(\n')
            childnode.exportLiteral(outfile, level, name_='childnode')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('id'):
            self.id = attrs.get('id').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'label':
            label_ = ''
            for text__content_ in child_.childNodes:
                label_ += text__content_.nodeValue
            self.label = label_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'link':
            obj_ = linkType.factory()
            obj_.build(child_)
            self.set_link(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'childnode':
            obj_ = childnodeType.factory()
            obj_.build(child_)
            self.childnode.append(obj_)
# end class nodeType


class label(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_=''):
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if label.subclass:
            return label.subclass(*args_, **kwargs_)
        else:
            return label(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='label', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='label')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='label'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='label'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='label'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class label


class childnodeType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, relation=None, refid=None, edgelabel=None):
        self.relation = relation
        self.refid = refid
        if edgelabel is None:
            self.edgelabel = []
        else:
            self.edgelabel = edgelabel
    def factory(*args_, **kwargs_):
        if childnodeType.subclass:
            return childnodeType.subclass(*args_, **kwargs_)
        else:
            return childnodeType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_edgelabel(self): return self.edgelabel
    def set_edgelabel(self, edgelabel): self.edgelabel = edgelabel
    def add_edgelabel(self, value): self.edgelabel.append(value)
    def insert_edgelabel(self, index, value): self.edgelabel[index] = value
    def get_relation(self): return self.relation
    def set_relation(self, relation): self.relation = relation
    def get_refid(self): return self.refid
    def set_refid(self, refid): self.refid = refid
    def export(self, outfile, level, namespace_='', name_='childnodeType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='childnodeType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='childnodeType'):
        if self.relation is not None:
            outfile.write(' relation=%s' % (quote_attrib(self.relation), ))
        if self.refid is not None:
            outfile.write(' refid=%s' % (self.format_string(quote_attrib(self.refid).encode(ExternalEncoding), input_name='refid'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='childnodeType'):
        for edgelabel_ in self.edgelabel:
            showIndent(outfile, level)
            outfile.write('<%sedgelabel>%s</%sedgelabel>\n' % (namespace_, self.format_string(quote_xml(edgelabel_).encode(ExternalEncoding), input_name='edgelabel'), namespace_))
    def hasContent_(self):
        if (
            self.edgelabel is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='childnodeType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.relation is not None:
            showIndent(outfile, level)
            outfile.write('relation = "%s",\n' % (self.relation,))
        if self.refid is not None:
            showIndent(outfile, level)
            outfile.write('refid = %s,\n' % (self.refid,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('edgelabel=[\n')
        level += 1
        for edgelabel in self.edgelabel:
            showIndent(outfile, level)
            outfile.write('%s,\n' % quote_python(edgelabel).encode(ExternalEncoding))
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('relation'):
            self.relation = attrs.get('relation').value
        if attrs.get('refid'):
            self.refid = attrs.get('refid').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'edgelabel':
            edgelabel_ = ''
            for text__content_ in child_.childNodes:
                edgelabel_ += text__content_.nodeValue
            self.edgelabel.append(edgelabel_)
# end class childnodeType


class edgelabel(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_=''):
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if edgelabel.subclass:
            return edgelabel.subclass(*args_, **kwargs_)
        else:
            return edgelabel(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='edgelabel', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='edgelabel')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='edgelabel'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='edgelabel'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='edgelabel'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class edgelabel


class linkType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, refid=None, external=None, valueOf_=''):
        self.refid = refid
        self.external = external
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if linkType.subclass:
            return linkType.subclass(*args_, **kwargs_)
        else:
            return linkType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_refid(self): return self.refid
    def set_refid(self, refid): self.refid = refid
    def get_external(self): return self.external
    def set_external(self, external): self.external = external
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='linkType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='linkType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='linkType'):
        if self.refid is not None:
            outfile.write(' refid=%s' % (self.format_string(quote_attrib(self.refid).encode(ExternalEncoding), input_name='refid'), ))
        if self.external is not None:
            outfile.write(' external=%s' % (self.format_string(quote_attrib(self.external).encode(ExternalEncoding), input_name='external'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='linkType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='linkType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.refid is not None:
            showIndent(outfile, level)
            outfile.write('refid = %s,\n' % (self.refid,))
        if self.external is not None:
            showIndent(outfile, level)
            outfile.write('external = %s,\n' % (self.external,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('refid'):
            self.refid = attrs.get('refid').value
        if attrs.get('external'):
            self.external = attrs.get('external').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class linkType


class listingType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, codeline=None):
        if codeline is None:
            self.codeline = []
        else:
            self.codeline = codeline
    def factory(*args_, **kwargs_):
        if listingType.subclass:
            return listingType.subclass(*args_, **kwargs_)
        else:
            return listingType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_codeline(self): return self.codeline
    def set_codeline(self, codeline): self.codeline = codeline
    def add_codeline(self, value): self.codeline.append(value)
    def insert_codeline(self, index, value): self.codeline[index] = value
    def export(self, outfile, level, namespace_='', name_='listingType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='listingType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='listingType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='listingType'):
        for codeline_ in self.codeline:
            codeline_.export(outfile, level, namespace_, name_='codeline')
    def hasContent_(self):
        if (
            self.codeline is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='listingType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('codeline=[\n')
        level += 1
        for codeline in self.codeline:
            showIndent(outfile, level)
            outfile.write('model_.codeline(\n')
            codeline.exportLiteral(outfile, level, name_='codeline')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'codeline':
            obj_ = codelineType.factory()
            obj_.build(child_)
            self.codeline.append(obj_)
# end class listingType


class codelineType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, external=None, lineno=None, refkind=None, refid=None, highlight=None):
        self.external = external
        self.lineno = lineno
        self.refkind = refkind
        self.refid = refid
        if highlight is None:
            self.highlight = []
        else:
            self.highlight = highlight
    def factory(*args_, **kwargs_):
        if codelineType.subclass:
            return codelineType.subclass(*args_, **kwargs_)
        else:
            return codelineType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_highlight(self): return self.highlight
    def set_highlight(self, highlight): self.highlight = highlight
    def add_highlight(self, value): self.highlight.append(value)
    def insert_highlight(self, index, value): self.highlight[index] = value
    def get_external(self): return self.external
    def set_external(self, external): self.external = external
    def get_lineno(self): return self.lineno
    def set_lineno(self, lineno): self.lineno = lineno
    def get_refkind(self): return self.refkind
    def set_refkind(self, refkind): self.refkind = refkind
    def get_refid(self): return self.refid
    def set_refid(self, refid): self.refid = refid
    def export(self, outfile, level, namespace_='', name_='codelineType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='codelineType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='codelineType'):
        if self.external is not None:
            outfile.write(' external=%s' % (quote_attrib(self.external), ))
        if self.lineno is not None:
            outfile.write(' lineno="%s"' % self.format_integer(self.lineno, input_name='lineno'))
        if self.refkind is not None:
            outfile.write(' refkind=%s' % (quote_attrib(self.refkind), ))
        if self.refid is not None:
            outfile.write(' refid=%s' % (self.format_string(quote_attrib(self.refid).encode(ExternalEncoding), input_name='refid'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='codelineType'):
        for highlight_ in self.highlight:
            highlight_.export(outfile, level, namespace_, name_='highlight')
    def hasContent_(self):
        if (
            self.highlight is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='codelineType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.external is not None:
            showIndent(outfile, level)
            outfile.write('external = "%s",\n' % (self.external,))
        if self.lineno is not None:
            showIndent(outfile, level)
            outfile.write('lineno = %s,\n' % (self.lineno,))
        if self.refkind is not None:
            showIndent(outfile, level)
            outfile.write('refkind = "%s",\n' % (self.refkind,))
        if self.refid is not None:
            showIndent(outfile, level)
            outfile.write('refid = %s,\n' % (self.refid,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('highlight=[\n')
        level += 1
        for highlight in self.highlight:
            showIndent(outfile, level)
            outfile.write('model_.highlight(\n')
            highlight.exportLiteral(outfile, level, name_='highlight')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('external'):
            self.external = attrs.get('external').value
        if attrs.get('lineno'):
            try:
                self.lineno = int(attrs.get('lineno').value)
            except ValueError, exp:
                raise ValueError('Bad integer attribute (lineno): %s' % exp)
        if attrs.get('refkind'):
            self.refkind = attrs.get('refkind').value
        if attrs.get('refid'):
            self.refid = attrs.get('refid').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'highlight':
            obj_ = highlightType.factory()
            obj_.build(child_)
            self.highlight.append(obj_)
# end class codelineType


class highlightType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, classxx=None, sp=None, ref=None, mixedclass_=None, content_=None):
        self.classxx = classxx
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if highlightType.subclass:
            return highlightType.subclass(*args_, **kwargs_)
        else:
            return highlightType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_sp(self): return self.sp
    def set_sp(self, sp): self.sp = sp
    def add_sp(self, value): self.sp.append(value)
    def insert_sp(self, index, value): self.sp[index] = value
    def get_ref(self): return self.ref
    def set_ref(self, ref): self.ref = ref
    def add_ref(self, value): self.ref.append(value)
    def insert_ref(self, index, value): self.ref[index] = value
    def get_class(self): return self.classxx
    def set_class(self, classxx): self.classxx = classxx
    def export(self, outfile, level, namespace_='', name_='highlightType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='highlightType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='highlightType'):
        if self.classxx is not None:
            outfile.write(' class=%s' % (quote_attrib(self.classxx), ))
    def exportChildren(self, outfile, level, namespace_='', name_='highlightType'):
        for item_ in self.content_:
            item_.export(outfile, level, item_.name, namespace_)
    def hasContent_(self):
        if (
            self.sp is not None or
            self.ref is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='highlightType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.classxx is not None:
            showIndent(outfile, level)
            outfile.write('classxx = "%s",\n' % (self.classxx,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('class'):
            self.classxx = attrs.get('class').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'sp':
            value_ = []
            for text_ in child_.childNodes:
                value_.append(text_.nodeValue)
            valuestr_ = ''.join(value_)
            obj_ = self.mixedclass_(MixedContainer.CategorySimple,
                MixedContainer.TypeString, 'sp', valuestr_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'ref':
            childobj_ = docRefTextType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'ref', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
# end class highlightType


class sp(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_=''):
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if sp.subclass:
            return sp.subclass(*args_, **kwargs_)
        else:
            return sp(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='sp', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='sp')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='sp'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='sp'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='sp'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class sp


class referenceType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, endline=None, startline=None, refid=None, compoundref=None, valueOf_='', mixedclass_=None, content_=None):
        self.endline = endline
        self.startline = startline
        self.refid = refid
        self.compoundref = compoundref
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if referenceType.subclass:
            return referenceType.subclass(*args_, **kwargs_)
        else:
            return referenceType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_endline(self): return self.endline
    def set_endline(self, endline): self.endline = endline
    def get_startline(self): return self.startline
    def set_startline(self, startline): self.startline = startline
    def get_refid(self): return self.refid
    def set_refid(self, refid): self.refid = refid
    def get_compoundref(self): return self.compoundref
    def set_compoundref(self, compoundref): self.compoundref = compoundref
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='referenceType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='referenceType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='referenceType'):
        if self.endline is not None:
            outfile.write(' endline="%s"' % self.format_integer(self.endline, input_name='endline'))
        if self.startline is not None:
            outfile.write(' startline="%s"' % self.format_integer(self.startline, input_name='startline'))
        if self.refid is not None:
            outfile.write(' refid=%s' % (self.format_string(quote_attrib(self.refid).encode(ExternalEncoding), input_name='refid'), ))
        if self.compoundref is not None:
            outfile.write(' compoundref=%s' % (self.format_string(quote_attrib(self.compoundref).encode(ExternalEncoding), input_name='compoundref'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='referenceType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='referenceType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.endline is not None:
            showIndent(outfile, level)
            outfile.write('endline = %s,\n' % (self.endline,))
        if self.startline is not None:
            showIndent(outfile, level)
            outfile.write('startline = %s,\n' % (self.startline,))
        if self.refid is not None:
            showIndent(outfile, level)
            outfile.write('refid = %s,\n' % (self.refid,))
        if self.compoundref is not None:
            showIndent(outfile, level)
            outfile.write('compoundref = %s,\n' % (self.compoundref,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('endline'):
            try:
                self.endline = int(attrs.get('endline').value)
            except ValueError, exp:
                raise ValueError('Bad integer attribute (endline): %s' % exp)
        if attrs.get('startline'):
            try:
                self.startline = int(attrs.get('startline').value)
            except ValueError, exp:
                raise ValueError('Bad integer attribute (startline): %s' % exp)
        if attrs.get('refid'):
            self.refid = attrs.get('refid').value
        if attrs.get('compoundref'):
            self.compoundref = attrs.get('compoundref').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class referenceType


class locationType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, bodystart=None, line=None, bodyend=None, bodyfile=None, file=None, valueOf_=''):
        self.bodystart = bodystart
        self.line = line
        self.bodyend = bodyend
        self.bodyfile = bodyfile
        self.file = file
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if locationType.subclass:
            return locationType.subclass(*args_, **kwargs_)
        else:
            return locationType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_bodystart(self): return self.bodystart
    def set_bodystart(self, bodystart): self.bodystart = bodystart
    def get_line(self): return self.line
    def set_line(self, line): self.line = line
    def get_bodyend(self): return self.bodyend
    def set_bodyend(self, bodyend): self.bodyend = bodyend
    def get_bodyfile(self): return self.bodyfile
    def set_bodyfile(self, bodyfile): self.bodyfile = bodyfile
    def get_file(self): return self.file
    def set_file(self, file): self.file = file
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='locationType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='locationType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='locationType'):
        if self.bodystart is not None:
            outfile.write(' bodystart="%s"' % self.format_integer(self.bodystart, input_name='bodystart'))
        if self.line is not None:
            outfile.write(' line="%s"' % self.format_integer(self.line, input_name='line'))
        if self.bodyend is not None:
            outfile.write(' bodyend="%s"' % self.format_integer(self.bodyend, input_name='bodyend'))
        if self.bodyfile is not None:
            outfile.write(' bodyfile=%s' % (self.format_string(quote_attrib(self.bodyfile).encode(ExternalEncoding), input_name='bodyfile'), ))
        if self.file is not None:
            outfile.write(' file=%s' % (self.format_string(quote_attrib(self.file).encode(ExternalEncoding), input_name='file'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='locationType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='locationType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.bodystart is not None:
            showIndent(outfile, level)
            outfile.write('bodystart = %s,\n' % (self.bodystart,))
        if self.line is not None:
            showIndent(outfile, level)
            outfile.write('line = %s,\n' % (self.line,))
        if self.bodyend is not None:
            showIndent(outfile, level)
            outfile.write('bodyend = %s,\n' % (self.bodyend,))
        if self.bodyfile is not None:
            showIndent(outfile, level)
            outfile.write('bodyfile = %s,\n' % (self.bodyfile,))
        if self.file is not None:
            showIndent(outfile, level)
            outfile.write('file = %s,\n' % (self.file,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('bodystart'):
            try:
                self.bodystart = int(attrs.get('bodystart').value)
            except ValueError, exp:
                raise ValueError('Bad integer attribute (bodystart): %s' % exp)
        if attrs.get('line'):
            try:
                self.line = int(attrs.get('line').value)
            except ValueError, exp:
                raise ValueError('Bad integer attribute (line): %s' % exp)
        if attrs.get('bodyend'):
            try:
                self.bodyend = int(attrs.get('bodyend').value)
            except ValueError, exp:
                raise ValueError('Bad integer attribute (bodyend): %s' % exp)
        if attrs.get('bodyfile'):
            self.bodyfile = attrs.get('bodyfile').value
        if attrs.get('file'):
            self.file = attrs.get('file').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class locationType


class docSect1Type(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, id=None, title=None, para=None, sect2=None, internal=None, mixedclass_=None, content_=None):
        self.id = id
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docSect1Type.subclass:
            return docSect1Type.subclass(*args_, **kwargs_)
        else:
            return docSect1Type(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_title(self): return self.title
    def set_title(self, title): self.title = title
    def get_para(self): return self.para
    def set_para(self, para): self.para = para
    def add_para(self, value): self.para.append(value)
    def insert_para(self, index, value): self.para[index] = value
    def get_sect2(self): return self.sect2
    def set_sect2(self, sect2): self.sect2 = sect2
    def add_sect2(self, value): self.sect2.append(value)
    def insert_sect2(self, index, value): self.sect2[index] = value
    def get_internal(self): return self.internal
    def set_internal(self, internal): self.internal = internal
    def get_id(self): return self.id
    def set_id(self, id): self.id = id
    def export(self, outfile, level, namespace_='', name_='docSect1Type', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docSect1Type')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docSect1Type'):
        if self.id is not None:
            outfile.write(' id=%s' % (self.format_string(quote_attrib(self.id).encode(ExternalEncoding), input_name='id'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docSect1Type'):
        for item_ in self.content_:
            item_.export(outfile, level, item_.name, namespace_)
    def hasContent_(self):
        if (
            self.title is not None or
            self.para is not None or
            self.sect2 is not None or
            self.internal is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docSect1Type'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.id is not None:
            showIndent(outfile, level)
            outfile.write('id = %s,\n' % (self.id,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('id'):
            self.id = attrs.get('id').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'title':
            childobj_ = docTitleType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'title', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'para':
            childobj_ = docParaType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'para', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'sect2':
            childobj_ = docSect2Type.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'sect2', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'internal':
            childobj_ = docInternalS1Type.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'internal', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
# end class docSect1Type


class docSect2Type(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, id=None, title=None, para=None, sect3=None, internal=None, mixedclass_=None, content_=None):
        self.id = id
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docSect2Type.subclass:
            return docSect2Type.subclass(*args_, **kwargs_)
        else:
            return docSect2Type(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_title(self): return self.title
    def set_title(self, title): self.title = title
    def get_para(self): return self.para
    def set_para(self, para): self.para = para
    def add_para(self, value): self.para.append(value)
    def insert_para(self, index, value): self.para[index] = value
    def get_sect3(self): return self.sect3
    def set_sect3(self, sect3): self.sect3 = sect3
    def add_sect3(self, value): self.sect3.append(value)
    def insert_sect3(self, index, value): self.sect3[index] = value
    def get_internal(self): return self.internal
    def set_internal(self, internal): self.internal = internal
    def get_id(self): return self.id
    def set_id(self, id): self.id = id
    def export(self, outfile, level, namespace_='', name_='docSect2Type', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docSect2Type')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docSect2Type'):
        if self.id is not None:
            outfile.write(' id=%s' % (self.format_string(quote_attrib(self.id).encode(ExternalEncoding), input_name='id'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docSect2Type'):
        for item_ in self.content_:
            item_.export(outfile, level, item_.name, namespace_)
    def hasContent_(self):
        if (
            self.title is not None or
            self.para is not None or
            self.sect3 is not None or
            self.internal is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docSect2Type'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.id is not None:
            showIndent(outfile, level)
            outfile.write('id = %s,\n' % (self.id,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('id'):
            self.id = attrs.get('id').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'title':
            childobj_ = docTitleType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'title', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'para':
            childobj_ = docParaType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'para', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'sect3':
            childobj_ = docSect3Type.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'sect3', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'internal':
            childobj_ = docInternalS2Type.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'internal', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
# end class docSect2Type


class docSect3Type(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, id=None, title=None, para=None, sect4=None, internal=None, mixedclass_=None, content_=None):
        self.id = id
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docSect3Type.subclass:
            return docSect3Type.subclass(*args_, **kwargs_)
        else:
            return docSect3Type(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_title(self): return self.title
    def set_title(self, title): self.title = title
    def get_para(self): return self.para
    def set_para(self, para): self.para = para
    def add_para(self, value): self.para.append(value)
    def insert_para(self, index, value): self.para[index] = value
    def get_sect4(self): return self.sect4
    def set_sect4(self, sect4): self.sect4 = sect4
    def add_sect4(self, value): self.sect4.append(value)
    def insert_sect4(self, index, value): self.sect4[index] = value
    def get_internal(self): return self.internal
    def set_internal(self, internal): self.internal = internal
    def get_id(self): return self.id
    def set_id(self, id): self.id = id
    def export(self, outfile, level, namespace_='', name_='docSect3Type', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docSect3Type')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docSect3Type'):
        if self.id is not None:
            outfile.write(' id=%s' % (self.format_string(quote_attrib(self.id).encode(ExternalEncoding), input_name='id'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docSect3Type'):
        for item_ in self.content_:
            item_.export(outfile, level, item_.name, namespace_)
    def hasContent_(self):
        if (
            self.title is not None or
            self.para is not None or
            self.sect4 is not None or
            self.internal is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docSect3Type'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.id is not None:
            showIndent(outfile, level)
            outfile.write('id = %s,\n' % (self.id,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('id'):
            self.id = attrs.get('id').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'title':
            childobj_ = docTitleType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'title', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'para':
            childobj_ = docParaType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'para', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'sect4':
            childobj_ = docSect4Type.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'sect4', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'internal':
            childobj_ = docInternalS3Type.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'internal', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
# end class docSect3Type


class docSect4Type(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, id=None, title=None, para=None, internal=None, mixedclass_=None, content_=None):
        self.id = id
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docSect4Type.subclass:
            return docSect4Type.subclass(*args_, **kwargs_)
        else:
            return docSect4Type(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_title(self): return self.title
    def set_title(self, title): self.title = title
    def get_para(self): return self.para
    def set_para(self, para): self.para = para
    def add_para(self, value): self.para.append(value)
    def insert_para(self, index, value): self.para[index] = value
    def get_internal(self): return self.internal
    def set_internal(self, internal): self.internal = internal
    def get_id(self): return self.id
    def set_id(self, id): self.id = id
    def export(self, outfile, level, namespace_='', name_='docSect4Type', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docSect4Type')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docSect4Type'):
        if self.id is not None:
            outfile.write(' id=%s' % (self.format_string(quote_attrib(self.id).encode(ExternalEncoding), input_name='id'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docSect4Type'):
        for item_ in self.content_:
            item_.export(outfile, level, item_.name, namespace_)
    def hasContent_(self):
        if (
            self.title is not None or
            self.para is not None or
            self.internal is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docSect4Type'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.id is not None:
            showIndent(outfile, level)
            outfile.write('id = %s,\n' % (self.id,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('id'):
            self.id = attrs.get('id').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'title':
            childobj_ = docTitleType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'title', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'para':
            childobj_ = docParaType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'para', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'internal':
            childobj_ = docInternalS4Type.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'internal', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
# end class docSect4Type


class docInternalType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, para=None, sect1=None, mixedclass_=None, content_=None):
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docInternalType.subclass:
            return docInternalType.subclass(*args_, **kwargs_)
        else:
            return docInternalType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_para(self): return self.para
    def set_para(self, para): self.para = para
    def add_para(self, value): self.para.append(value)
    def insert_para(self, index, value): self.para[index] = value
    def get_sect1(self): return self.sect1
    def set_sect1(self, sect1): self.sect1 = sect1
    def add_sect1(self, value): self.sect1.append(value)
    def insert_sect1(self, index, value): self.sect1[index] = value
    def export(self, outfile, level, namespace_='', name_='docInternalType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docInternalType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docInternalType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docInternalType'):
        for item_ in self.content_:
            item_.export(outfile, level, item_.name, namespace_)
    def hasContent_(self):
        if (
            self.para is not None or
            self.sect1 is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docInternalType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'para':
            childobj_ = docParaType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'para', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'sect1':
            childobj_ = docSect1Type.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'sect1', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
# end class docInternalType


class docInternalS1Type(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, para=None, sect2=None, mixedclass_=None, content_=None):
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docInternalS1Type.subclass:
            return docInternalS1Type.subclass(*args_, **kwargs_)
        else:
            return docInternalS1Type(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_para(self): return self.para
    def set_para(self, para): self.para = para
    def add_para(self, value): self.para.append(value)
    def insert_para(self, index, value): self.para[index] = value
    def get_sect2(self): return self.sect2
    def set_sect2(self, sect2): self.sect2 = sect2
    def add_sect2(self, value): self.sect2.append(value)
    def insert_sect2(self, index, value): self.sect2[index] = value
    def export(self, outfile, level, namespace_='', name_='docInternalS1Type', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docInternalS1Type')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docInternalS1Type'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docInternalS1Type'):
        for item_ in self.content_:
            item_.export(outfile, level, item_.name, namespace_)
    def hasContent_(self):
        if (
            self.para is not None or
            self.sect2 is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docInternalS1Type'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'para':
            childobj_ = docParaType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'para', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'sect2':
            childobj_ = docSect2Type.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'sect2', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
# end class docInternalS1Type


class docInternalS2Type(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, para=None, sect3=None, mixedclass_=None, content_=None):
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docInternalS2Type.subclass:
            return docInternalS2Type.subclass(*args_, **kwargs_)
        else:
            return docInternalS2Type(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_para(self): return self.para
    def set_para(self, para): self.para = para
    def add_para(self, value): self.para.append(value)
    def insert_para(self, index, value): self.para[index] = value
    def get_sect3(self): return self.sect3
    def set_sect3(self, sect3): self.sect3 = sect3
    def add_sect3(self, value): self.sect3.append(value)
    def insert_sect3(self, index, value): self.sect3[index] = value
    def export(self, outfile, level, namespace_='', name_='docInternalS2Type', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docInternalS2Type')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docInternalS2Type'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docInternalS2Type'):
        for item_ in self.content_:
            item_.export(outfile, level, item_.name, namespace_)
    def hasContent_(self):
        if (
            self.para is not None or
            self.sect3 is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docInternalS2Type'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'para':
            childobj_ = docParaType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'para', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'sect3':
            childobj_ = docSect3Type.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'sect3', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
# end class docInternalS2Type


class docInternalS3Type(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, para=None, sect3=None, mixedclass_=None, content_=None):
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docInternalS3Type.subclass:
            return docInternalS3Type.subclass(*args_, **kwargs_)
        else:
            return docInternalS3Type(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_para(self): return self.para
    def set_para(self, para): self.para = para
    def add_para(self, value): self.para.append(value)
    def insert_para(self, index, value): self.para[index] = value
    def get_sect3(self): return self.sect3
    def set_sect3(self, sect3): self.sect3 = sect3
    def add_sect3(self, value): self.sect3.append(value)
    def insert_sect3(self, index, value): self.sect3[index] = value
    def export(self, outfile, level, namespace_='', name_='docInternalS3Type', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docInternalS3Type')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docInternalS3Type'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docInternalS3Type'):
        for item_ in self.content_:
            item_.export(outfile, level, item_.name, namespace_)
    def hasContent_(self):
        if (
            self.para is not None or
            self.sect3 is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docInternalS3Type'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'para':
            childobj_ = docParaType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'para', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'sect3':
            childobj_ = docSect4Type.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'sect3', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
# end class docInternalS3Type


class docInternalS4Type(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, para=None, mixedclass_=None, content_=None):
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docInternalS4Type.subclass:
            return docInternalS4Type.subclass(*args_, **kwargs_)
        else:
            return docInternalS4Type(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_para(self): return self.para
    def set_para(self, para): self.para = para
    def add_para(self, value): self.para.append(value)
    def insert_para(self, index, value): self.para[index] = value
    def export(self, outfile, level, namespace_='', name_='docInternalS4Type', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docInternalS4Type')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docInternalS4Type'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docInternalS4Type'):
        for item_ in self.content_:
            item_.export(outfile, level, item_.name, namespace_)
    def hasContent_(self):
        if (
            self.para is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docInternalS4Type'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'para':
            childobj_ = docParaType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'para', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
# end class docInternalS4Type


class docTitleType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_='', mixedclass_=None, content_=None):
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docTitleType.subclass:
            return docTitleType.subclass(*args_, **kwargs_)
        else:
            return docTitleType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='docTitleType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docTitleType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docTitleType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docTitleType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docTitleType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class docTitleType


class docParaType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_='', mixedclass_=None, content_=None):
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docParaType.subclass:
            return docParaType.subclass(*args_, **kwargs_)
        else:
            return docParaType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='docParaType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docParaType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docParaType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docParaType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docParaType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class docParaType


class docMarkupType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_='', mixedclass_=None, content_=None):
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docMarkupType.subclass:
            return docMarkupType.subclass(*args_, **kwargs_)
        else:
            return docMarkupType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='docMarkupType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docMarkupType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docMarkupType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docMarkupType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docMarkupType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class docMarkupType


class docURLLink(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, url=None, valueOf_='', mixedclass_=None, content_=None):
        self.url = url
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docURLLink.subclass:
            return docURLLink.subclass(*args_, **kwargs_)
        else:
            return docURLLink(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_url(self): return self.url
    def set_url(self, url): self.url = url
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='docURLLink', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docURLLink')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docURLLink'):
        if self.url is not None:
            outfile.write(' url=%s' % (self.format_string(quote_attrib(self.url).encode(ExternalEncoding), input_name='url'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docURLLink'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docURLLink'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.url is not None:
            showIndent(outfile, level)
            outfile.write('url = %s,\n' % (self.url,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('url'):
            self.url = attrs.get('url').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class docURLLink


class docAnchorType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, id=None, valueOf_='', mixedclass_=None, content_=None):
        self.id = id
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docAnchorType.subclass:
            return docAnchorType.subclass(*args_, **kwargs_)
        else:
            return docAnchorType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_id(self): return self.id
    def set_id(self, id): self.id = id
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='docAnchorType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docAnchorType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docAnchorType'):
        if self.id is not None:
            outfile.write(' id=%s' % (self.format_string(quote_attrib(self.id).encode(ExternalEncoding), input_name='id'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docAnchorType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docAnchorType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.id is not None:
            showIndent(outfile, level)
            outfile.write('id = %s,\n' % (self.id,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('id'):
            self.id = attrs.get('id').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class docAnchorType


class docFormulaType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, id=None, valueOf_='', mixedclass_=None, content_=None):
        self.id = id
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docFormulaType.subclass:
            return docFormulaType.subclass(*args_, **kwargs_)
        else:
            return docFormulaType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_id(self): return self.id
    def set_id(self, id): self.id = id
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='docFormulaType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docFormulaType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docFormulaType'):
        if self.id is not None:
            outfile.write(' id=%s' % (self.format_string(quote_attrib(self.id).encode(ExternalEncoding), input_name='id'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docFormulaType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docFormulaType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.id is not None:
            showIndent(outfile, level)
            outfile.write('id = %s,\n' % (self.id,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('id'):
            self.id = attrs.get('id').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class docFormulaType


class docIndexEntryType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, primaryie=None, secondaryie=None):
        self.primaryie = primaryie
        self.secondaryie = secondaryie
    def factory(*args_, **kwargs_):
        if docIndexEntryType.subclass:
            return docIndexEntryType.subclass(*args_, **kwargs_)
        else:
            return docIndexEntryType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_primaryie(self): return self.primaryie
    def set_primaryie(self, primaryie): self.primaryie = primaryie
    def get_secondaryie(self): return self.secondaryie
    def set_secondaryie(self, secondaryie): self.secondaryie = secondaryie
    def export(self, outfile, level, namespace_='', name_='docIndexEntryType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docIndexEntryType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docIndexEntryType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docIndexEntryType'):
        if self.primaryie is not None:
            showIndent(outfile, level)
            outfile.write('<%sprimaryie>%s</%sprimaryie>\n' % (namespace_, self.format_string(quote_xml(self.primaryie).encode(ExternalEncoding), input_name='primaryie'), namespace_))
        if self.secondaryie is not None:
            showIndent(outfile, level)
            outfile.write('<%ssecondaryie>%s</%ssecondaryie>\n' % (namespace_, self.format_string(quote_xml(self.secondaryie).encode(ExternalEncoding), input_name='secondaryie'), namespace_))
    def hasContent_(self):
        if (
            self.primaryie is not None or
            self.secondaryie is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docIndexEntryType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('primaryie=%s,\n' % quote_python(self.primaryie).encode(ExternalEncoding))
        showIndent(outfile, level)
        outfile.write('secondaryie=%s,\n' % quote_python(self.secondaryie).encode(ExternalEncoding))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'primaryie':
            primaryie_ = ''
            for text__content_ in child_.childNodes:
                primaryie_ += text__content_.nodeValue
            self.primaryie = primaryie_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'secondaryie':
            secondaryie_ = ''
            for text__content_ in child_.childNodes:
                secondaryie_ += text__content_.nodeValue
            self.secondaryie = secondaryie_
# end class docIndexEntryType


class docListType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, listitem=None):
        if listitem is None:
            self.listitem = []
        else:
            self.listitem = listitem
    def factory(*args_, **kwargs_):
        if docListType.subclass:
            return docListType.subclass(*args_, **kwargs_)
        else:
            return docListType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_listitem(self): return self.listitem
    def set_listitem(self, listitem): self.listitem = listitem
    def add_listitem(self, value): self.listitem.append(value)
    def insert_listitem(self, index, value): self.listitem[index] = value
    def export(self, outfile, level, namespace_='', name_='docListType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docListType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docListType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docListType'):
        for listitem_ in self.listitem:
            listitem_.export(outfile, level, namespace_, name_='listitem')
    def hasContent_(self):
        if (
            self.listitem is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docListType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('listitem=[\n')
        level += 1
        for listitem in self.listitem:
            showIndent(outfile, level)
            outfile.write('model_.listitem(\n')
            listitem.exportLiteral(outfile, level, name_='listitem')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'listitem':
            obj_ = docListItemType.factory()
            obj_.build(child_)
            self.listitem.append(obj_)
# end class docListType


class docListItemType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, para=None):
        if para is None:
            self.para = []
        else:
            self.para = para
    def factory(*args_, **kwargs_):
        if docListItemType.subclass:
            return docListItemType.subclass(*args_, **kwargs_)
        else:
            return docListItemType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_para(self): return self.para
    def set_para(self, para): self.para = para
    def add_para(self, value): self.para.append(value)
    def insert_para(self, index, value): self.para[index] = value
    def export(self, outfile, level, namespace_='', name_='docListItemType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docListItemType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docListItemType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docListItemType'):
        for para_ in self.para:
            para_.export(outfile, level, namespace_, name_='para')
    def hasContent_(self):
        if (
            self.para is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docListItemType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('para=[\n')
        level += 1
        for para in self.para:
            showIndent(outfile, level)
            outfile.write('model_.para(\n')
            para.exportLiteral(outfile, level, name_='para')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'para':
            obj_ = docParaType.factory()
            obj_.build(child_)
            self.para.append(obj_)
# end class docListItemType


class docSimpleSectType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, kind=None, title=None, para=None):
        self.kind = kind
        self.title = title
        if para is None:
            self.para = []
        else:
            self.para = para
    def factory(*args_, **kwargs_):
        if docSimpleSectType.subclass:
            return docSimpleSectType.subclass(*args_, **kwargs_)
        else:
            return docSimpleSectType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_title(self): return self.title
    def set_title(self, title): self.title = title
    def get_para(self): return self.para
    def set_para(self, para): self.para = para
    def add_para(self, value): self.para.append(value)
    def insert_para(self, index, value): self.para[index] = value
    def get_kind(self): return self.kind
    def set_kind(self, kind): self.kind = kind
    def export(self, outfile, level, namespace_='', name_='docSimpleSectType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docSimpleSectType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docSimpleSectType'):
        if self.kind is not None:
            outfile.write(' kind=%s' % (quote_attrib(self.kind), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docSimpleSectType'):
        if self.title:
            self.title.export(outfile, level, namespace_, name_='title')
        for para_ in self.para:
            para_.export(outfile, level, namespace_, name_='para')
    def hasContent_(self):
        if (
            self.title is not None or
            self.para is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docSimpleSectType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.kind is not None:
            showIndent(outfile, level)
            outfile.write('kind = "%s",\n' % (self.kind,))
    def exportLiteralChildren(self, outfile, level, name_):
        if self.title:
            showIndent(outfile, level)
            outfile.write('title=model_.docTitleType(\n')
            self.title.exportLiteral(outfile, level, name_='title')
            showIndent(outfile, level)
            outfile.write('),\n')
        showIndent(outfile, level)
        outfile.write('para=[\n')
        level += 1
        for para in self.para:
            showIndent(outfile, level)
            outfile.write('model_.para(\n')
            para.exportLiteral(outfile, level, name_='para')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('kind'):
            self.kind = attrs.get('kind').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'title':
            obj_ = docTitleType.factory()
            obj_.build(child_)
            self.set_title(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'para':
            obj_ = docParaType.factory()
            obj_.build(child_)
            self.para.append(obj_)
# end class docSimpleSectType


class docVarListEntryType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, term=None):
        self.term = term
    def factory(*args_, **kwargs_):
        if docVarListEntryType.subclass:
            return docVarListEntryType.subclass(*args_, **kwargs_)
        else:
            return docVarListEntryType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_term(self): return self.term
    def set_term(self, term): self.term = term
    def export(self, outfile, level, namespace_='', name_='docVarListEntryType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docVarListEntryType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docVarListEntryType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docVarListEntryType'):
        if self.term:
            self.term.export(outfile, level, namespace_, name_='term', )
    def hasContent_(self):
        if (
            self.term is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docVarListEntryType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        if self.term:
            showIndent(outfile, level)
            outfile.write('term=model_.docTitleType(\n')
            self.term.exportLiteral(outfile, level, name_='term')
            showIndent(outfile, level)
            outfile.write('),\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'term':
            obj_ = docTitleType.factory()
            obj_.build(child_)
            self.set_term(obj_)
# end class docVarListEntryType


class docVariableListType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_=''):
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if docVariableListType.subclass:
            return docVariableListType.subclass(*args_, **kwargs_)
        else:
            return docVariableListType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='docVariableListType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docVariableListType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docVariableListType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docVariableListType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docVariableListType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class docVariableListType


class docRefTextType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, refid=None, kindref=None, external=None, valueOf_='', mixedclass_=None, content_=None):
        self.refid = refid
        self.kindref = kindref
        self.external = external
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docRefTextType.subclass:
            return docRefTextType.subclass(*args_, **kwargs_)
        else:
            return docRefTextType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_refid(self): return self.refid
    def set_refid(self, refid): self.refid = refid
    def get_kindref(self): return self.kindref
    def set_kindref(self, kindref): self.kindref = kindref
    def get_external(self): return self.external
    def set_external(self, external): self.external = external
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='docRefTextType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docRefTextType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docRefTextType'):
        if self.refid is not None:
            outfile.write(' refid=%s' % (self.format_string(quote_attrib(self.refid).encode(ExternalEncoding), input_name='refid'), ))
        if self.kindref is not None:
            outfile.write(' kindref=%s' % (quote_attrib(self.kindref), ))
        if self.external is not None:
            outfile.write(' external=%s' % (self.format_string(quote_attrib(self.external).encode(ExternalEncoding), input_name='external'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docRefTextType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docRefTextType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.refid is not None:
            showIndent(outfile, level)
            outfile.write('refid = %s,\n' % (self.refid,))
        if self.kindref is not None:
            showIndent(outfile, level)
            outfile.write('kindref = "%s",\n' % (self.kindref,))
        if self.external is not None:
            showIndent(outfile, level)
            outfile.write('external = %s,\n' % (self.external,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('refid'):
            self.refid = attrs.get('refid').value
        if attrs.get('kindref'):
            self.kindref = attrs.get('kindref').value
        if attrs.get('external'):
            self.external = attrs.get('external').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class docRefTextType


class docTableType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, rows=None, cols=None, row=None, caption=None):
        self.rows = rows
        self.cols = cols
        if row is None:
            self.row = []
        else:
            self.row = row
        self.caption = caption
    def factory(*args_, **kwargs_):
        if docTableType.subclass:
            return docTableType.subclass(*args_, **kwargs_)
        else:
            return docTableType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_row(self): return self.row
    def set_row(self, row): self.row = row
    def add_row(self, value): self.row.append(value)
    def insert_row(self, index, value): self.row[index] = value
    def get_caption(self): return self.caption
    def set_caption(self, caption): self.caption = caption
    def get_rows(self): return self.rows
    def set_rows(self, rows): self.rows = rows
    def get_cols(self): return self.cols
    def set_cols(self, cols): self.cols = cols
    def export(self, outfile, level, namespace_='', name_='docTableType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docTableType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docTableType'):
        if self.rows is not None:
            outfile.write(' rows="%s"' % self.format_integer(self.rows, input_name='rows'))
        if self.cols is not None:
            outfile.write(' cols="%s"' % self.format_integer(self.cols, input_name='cols'))
    def exportChildren(self, outfile, level, namespace_='', name_='docTableType'):
        for row_ in self.row:
            row_.export(outfile, level, namespace_, name_='row')
        if self.caption:
            self.caption.export(outfile, level, namespace_, name_='caption')
    def hasContent_(self):
        if (
            self.row is not None or
            self.caption is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docTableType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.rows is not None:
            showIndent(outfile, level)
            outfile.write('rows = %s,\n' % (self.rows,))
        if self.cols is not None:
            showIndent(outfile, level)
            outfile.write('cols = %s,\n' % (self.cols,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('row=[\n')
        level += 1
        for row in self.row:
            showIndent(outfile, level)
            outfile.write('model_.row(\n')
            row.exportLiteral(outfile, level, name_='row')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
        if self.caption:
            showIndent(outfile, level)
            outfile.write('caption=model_.docCaptionType(\n')
            self.caption.exportLiteral(outfile, level, name_='caption')
            showIndent(outfile, level)
            outfile.write('),\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('rows'):
            try:
                self.rows = int(attrs.get('rows').value)
            except ValueError, exp:
                raise ValueError('Bad integer attribute (rows): %s' % exp)
        if attrs.get('cols'):
            try:
                self.cols = int(attrs.get('cols').value)
            except ValueError, exp:
                raise ValueError('Bad integer attribute (cols): %s' % exp)
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'row':
            obj_ = docRowType.factory()
            obj_.build(child_)
            self.row.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'caption':
            obj_ = docCaptionType.factory()
            obj_.build(child_)
            self.set_caption(obj_)
# end class docTableType


class docRowType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, entry=None):
        if entry is None:
            self.entry = []
        else:
            self.entry = entry
    def factory(*args_, **kwargs_):
        if docRowType.subclass:
            return docRowType.subclass(*args_, **kwargs_)
        else:
            return docRowType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_entry(self): return self.entry
    def set_entry(self, entry): self.entry = entry
    def add_entry(self, value): self.entry.append(value)
    def insert_entry(self, index, value): self.entry[index] = value
    def export(self, outfile, level, namespace_='', name_='docRowType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docRowType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docRowType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docRowType'):
        for entry_ in self.entry:
            entry_.export(outfile, level, namespace_, name_='entry')
    def hasContent_(self):
        if (
            self.entry is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docRowType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('entry=[\n')
        level += 1
        for entry in self.entry:
            showIndent(outfile, level)
            outfile.write('model_.entry(\n')
            entry.exportLiteral(outfile, level, name_='entry')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'entry':
            obj_ = docEntryType.factory()
            obj_.build(child_)
            self.entry.append(obj_)
# end class docRowType


class docEntryType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, thead=None, para=None):
        self.thead = thead
        if para is None:
            self.para = []
        else:
            self.para = para
    def factory(*args_, **kwargs_):
        if docEntryType.subclass:
            return docEntryType.subclass(*args_, **kwargs_)
        else:
            return docEntryType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_para(self): return self.para
    def set_para(self, para): self.para = para
    def add_para(self, value): self.para.append(value)
    def insert_para(self, index, value): self.para[index] = value
    def get_thead(self): return self.thead
    def set_thead(self, thead): self.thead = thead
    def export(self, outfile, level, namespace_='', name_='docEntryType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docEntryType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docEntryType'):
        if self.thead is not None:
            outfile.write(' thead=%s' % (quote_attrib(self.thead), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docEntryType'):
        for para_ in self.para:
            para_.export(outfile, level, namespace_, name_='para')
    def hasContent_(self):
        if (
            self.para is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docEntryType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.thead is not None:
            showIndent(outfile, level)
            outfile.write('thead = "%s",\n' % (self.thead,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('para=[\n')
        level += 1
        for para in self.para:
            showIndent(outfile, level)
            outfile.write('model_.para(\n')
            para.exportLiteral(outfile, level, name_='para')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('thead'):
            self.thead = attrs.get('thead').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'para':
            obj_ = docParaType.factory()
            obj_.build(child_)
            self.para.append(obj_)
# end class docEntryType


class docCaptionType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_='', mixedclass_=None, content_=None):
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docCaptionType.subclass:
            return docCaptionType.subclass(*args_, **kwargs_)
        else:
            return docCaptionType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='docCaptionType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docCaptionType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docCaptionType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docCaptionType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docCaptionType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class docCaptionType


class docHeadingType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, level=None, valueOf_='', mixedclass_=None, content_=None):
        self.level = level
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docHeadingType.subclass:
            return docHeadingType.subclass(*args_, **kwargs_)
        else:
            return docHeadingType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_level(self): return self.level
    def set_level(self, level): self.level = level
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='docHeadingType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docHeadingType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docHeadingType'):
        if self.level is not None:
            outfile.write(' level="%s"' % self.format_integer(self.level, input_name='level'))
    def exportChildren(self, outfile, level, namespace_='', name_='docHeadingType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docHeadingType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.level is not None:
            showIndent(outfile, level)
            outfile.write('level = %s,\n' % (self.level,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('level'):
            try:
                self.level = int(attrs.get('level').value)
            except ValueError, exp:
                raise ValueError('Bad integer attribute (level): %s' % exp)
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class docHeadingType


class docImageType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, width=None, type_=None, name=None, height=None, valueOf_='', mixedclass_=None, content_=None):
        self.width = width
        self.type_ = type_
        self.name = name
        self.height = height
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docImageType.subclass:
            return docImageType.subclass(*args_, **kwargs_)
        else:
            return docImageType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_width(self): return self.width
    def set_width(self, width): self.width = width
    def get_type(self): return self.type_
    def set_type(self, type_): self.type_ = type_
    def get_name(self): return self.name
    def set_name(self, name): self.name = name
    def get_height(self): return self.height
    def set_height(self, height): self.height = height
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='docImageType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docImageType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docImageType'):
        if self.width is not None:
            outfile.write(' width=%s' % (self.format_string(quote_attrib(self.width).encode(ExternalEncoding), input_name='width'), ))
        if self.type_ is not None:
            outfile.write(' type=%s' % (quote_attrib(self.type_), ))
        if self.name is not None:
            outfile.write(' name=%s' % (self.format_string(quote_attrib(self.name).encode(ExternalEncoding), input_name='name'), ))
        if self.height is not None:
            outfile.write(' height=%s' % (self.format_string(quote_attrib(self.height).encode(ExternalEncoding), input_name='height'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docImageType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docImageType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.width is not None:
            showIndent(outfile, level)
            outfile.write('width = %s,\n' % (self.width,))
        if self.type_ is not None:
            showIndent(outfile, level)
            outfile.write('type_ = "%s",\n' % (self.type_,))
        if self.name is not None:
            showIndent(outfile, level)
            outfile.write('name = %s,\n' % (self.name,))
        if self.height is not None:
            showIndent(outfile, level)
            outfile.write('height = %s,\n' % (self.height,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('width'):
            self.width = attrs.get('width').value
        if attrs.get('type'):
            self.type_ = attrs.get('type').value
        if attrs.get('name'):
            self.name = attrs.get('name').value
        if attrs.get('height'):
            self.height = attrs.get('height').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class docImageType


class docDotFileType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, name=None, valueOf_='', mixedclass_=None, content_=None):
        self.name = name
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docDotFileType.subclass:
            return docDotFileType.subclass(*args_, **kwargs_)
        else:
            return docDotFileType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_name(self): return self.name
    def set_name(self, name): self.name = name
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='docDotFileType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docDotFileType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docDotFileType'):
        if self.name is not None:
            outfile.write(' name=%s' % (self.format_string(quote_attrib(self.name).encode(ExternalEncoding), input_name='name'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docDotFileType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docDotFileType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.name is not None:
            showIndent(outfile, level)
            outfile.write('name = %s,\n' % (self.name,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('name'):
            self.name = attrs.get('name').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class docDotFileType


class docTocItemType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, id=None, valueOf_='', mixedclass_=None, content_=None):
        self.id = id
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docTocItemType.subclass:
            return docTocItemType.subclass(*args_, **kwargs_)
        else:
            return docTocItemType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_id(self): return self.id
    def set_id(self, id): self.id = id
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='docTocItemType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docTocItemType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docTocItemType'):
        if self.id is not None:
            outfile.write(' id=%s' % (self.format_string(quote_attrib(self.id).encode(ExternalEncoding), input_name='id'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docTocItemType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docTocItemType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.id is not None:
            showIndent(outfile, level)
            outfile.write('id = %s,\n' % (self.id,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('id'):
            self.id = attrs.get('id').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class docTocItemType


class docTocListType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, tocitem=None):
        if tocitem is None:
            self.tocitem = []
        else:
            self.tocitem = tocitem
    def factory(*args_, **kwargs_):
        if docTocListType.subclass:
            return docTocListType.subclass(*args_, **kwargs_)
        else:
            return docTocListType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_tocitem(self): return self.tocitem
    def set_tocitem(self, tocitem): self.tocitem = tocitem
    def add_tocitem(self, value): self.tocitem.append(value)
    def insert_tocitem(self, index, value): self.tocitem[index] = value
    def export(self, outfile, level, namespace_='', name_='docTocListType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docTocListType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docTocListType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docTocListType'):
        for tocitem_ in self.tocitem:
            tocitem_.export(outfile, level, namespace_, name_='tocitem')
    def hasContent_(self):
        if (
            self.tocitem is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docTocListType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('tocitem=[\n')
        level += 1
        for tocitem in self.tocitem:
            showIndent(outfile, level)
            outfile.write('model_.tocitem(\n')
            tocitem.exportLiteral(outfile, level, name_='tocitem')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'tocitem':
            obj_ = docTocItemType.factory()
            obj_.build(child_)
            self.tocitem.append(obj_)
# end class docTocListType


class docLanguageType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, langid=None, para=None):
        self.langid = langid
        if para is None:
            self.para = []
        else:
            self.para = para
    def factory(*args_, **kwargs_):
        if docLanguageType.subclass:
            return docLanguageType.subclass(*args_, **kwargs_)
        else:
            return docLanguageType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_para(self): return self.para
    def set_para(self, para): self.para = para
    def add_para(self, value): self.para.append(value)
    def insert_para(self, index, value): self.para[index] = value
    def get_langid(self): return self.langid
    def set_langid(self, langid): self.langid = langid
    def export(self, outfile, level, namespace_='', name_='docLanguageType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docLanguageType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docLanguageType'):
        if self.langid is not None:
            outfile.write(' langid=%s' % (self.format_string(quote_attrib(self.langid).encode(ExternalEncoding), input_name='langid'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docLanguageType'):
        for para_ in self.para:
            para_.export(outfile, level, namespace_, name_='para')
    def hasContent_(self):
        if (
            self.para is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docLanguageType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.langid is not None:
            showIndent(outfile, level)
            outfile.write('langid = %s,\n' % (self.langid,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('para=[\n')
        level += 1
        for para in self.para:
            showIndent(outfile, level)
            outfile.write('model_.para(\n')
            para.exportLiteral(outfile, level, name_='para')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('langid'):
            self.langid = attrs.get('langid').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'para':
            obj_ = docParaType.factory()
            obj_.build(child_)
            self.para.append(obj_)
# end class docLanguageType


class docParamListType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, kind=None, parameteritem=None):
        self.kind = kind
        if parameteritem is None:
            self.parameteritem = []
        else:
            self.parameteritem = parameteritem
    def factory(*args_, **kwargs_):
        if docParamListType.subclass:
            return docParamListType.subclass(*args_, **kwargs_)
        else:
            return docParamListType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_parameteritem(self): return self.parameteritem
    def set_parameteritem(self, parameteritem): self.parameteritem = parameteritem
    def add_parameteritem(self, value): self.parameteritem.append(value)
    def insert_parameteritem(self, index, value): self.parameteritem[index] = value
    def get_kind(self): return self.kind
    def set_kind(self, kind): self.kind = kind
    def export(self, outfile, level, namespace_='', name_='docParamListType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docParamListType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docParamListType'):
        if self.kind is not None:
            outfile.write(' kind=%s' % (quote_attrib(self.kind), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docParamListType'):
        for parameteritem_ in self.parameteritem:
            parameteritem_.export(outfile, level, namespace_, name_='parameteritem')
    def hasContent_(self):
        if (
            self.parameteritem is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docParamListType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.kind is not None:
            showIndent(outfile, level)
            outfile.write('kind = "%s",\n' % (self.kind,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('parameteritem=[\n')
        level += 1
        for parameteritem in self.parameteritem:
            showIndent(outfile, level)
            outfile.write('model_.parameteritem(\n')
            parameteritem.exportLiteral(outfile, level, name_='parameteritem')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('kind'):
            self.kind = attrs.get('kind').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'parameteritem':
            obj_ = docParamListItem.factory()
            obj_.build(child_)
            self.parameteritem.append(obj_)
# end class docParamListType


class docParamListItem(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, parameternamelist=None, parameterdescription=None):
        if parameternamelist is None:
            self.parameternamelist = []
        else:
            self.parameternamelist = parameternamelist
        self.parameterdescription = parameterdescription
    def factory(*args_, **kwargs_):
        if docParamListItem.subclass:
            return docParamListItem.subclass(*args_, **kwargs_)
        else:
            return docParamListItem(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_parameternamelist(self): return self.parameternamelist
    def set_parameternamelist(self, parameternamelist): self.parameternamelist = parameternamelist
    def add_parameternamelist(self, value): self.parameternamelist.append(value)
    def insert_parameternamelist(self, index, value): self.parameternamelist[index] = value
    def get_parameterdescription(self): return self.parameterdescription
    def set_parameterdescription(self, parameterdescription): self.parameterdescription = parameterdescription
    def export(self, outfile, level, namespace_='', name_='docParamListItem', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docParamListItem')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docParamListItem'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docParamListItem'):
        for parameternamelist_ in self.parameternamelist:
            parameternamelist_.export(outfile, level, namespace_, name_='parameternamelist')
        if self.parameterdescription:
            self.parameterdescription.export(outfile, level, namespace_, name_='parameterdescription', )
    def hasContent_(self):
        if (
            self.parameternamelist is not None or
            self.parameterdescription is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docParamListItem'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('parameternamelist=[\n')
        level += 1
        for parameternamelist in self.parameternamelist:
            showIndent(outfile, level)
            outfile.write('model_.parameternamelist(\n')
            parameternamelist.exportLiteral(outfile, level, name_='parameternamelist')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
        if self.parameterdescription:
            showIndent(outfile, level)
            outfile.write('parameterdescription=model_.descriptionType(\n')
            self.parameterdescription.exportLiteral(outfile, level, name_='parameterdescription')
            showIndent(outfile, level)
            outfile.write('),\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'parameternamelist':
            obj_ = docParamNameList.factory()
            obj_.build(child_)
            self.parameternamelist.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'parameterdescription':
            obj_ = descriptionType.factory()
            obj_.build(child_)
            self.set_parameterdescription(obj_)
# end class docParamListItem


class docParamNameList(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, parametername=None):
        if parametername is None:
            self.parametername = []
        else:
            self.parametername = parametername
    def factory(*args_, **kwargs_):
        if docParamNameList.subclass:
            return docParamNameList.subclass(*args_, **kwargs_)
        else:
            return docParamNameList(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_parametername(self): return self.parametername
    def set_parametername(self, parametername): self.parametername = parametername
    def add_parametername(self, value): self.parametername.append(value)
    def insert_parametername(self, index, value): self.parametername[index] = value
    def export(self, outfile, level, namespace_='', name_='docParamNameList', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docParamNameList')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docParamNameList'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docParamNameList'):
        for parametername_ in self.parametername:
            parametername_.export(outfile, level, namespace_, name_='parametername')
    def hasContent_(self):
        if (
            self.parametername is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docParamNameList'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('parametername=[\n')
        level += 1
        for parametername in self.parametername:
            showIndent(outfile, level)
            outfile.write('model_.parametername(\n')
            parametername.exportLiteral(outfile, level, name_='parametername')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'parametername':
            obj_ = docParamName.factory()
            obj_.build(child_)
            self.parametername.append(obj_)
# end class docParamNameList


class docParamName(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, direction=None, ref=None, mixedclass_=None, content_=None):
        self.direction = direction
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docParamName.subclass:
            return docParamName.subclass(*args_, **kwargs_)
        else:
            return docParamName(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_ref(self): return self.ref
    def set_ref(self, ref): self.ref = ref
    def get_direction(self): return self.direction
    def set_direction(self, direction): self.direction = direction
    def export(self, outfile, level, namespace_='', name_='docParamName', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docParamName')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docParamName'):
        if self.direction is not None:
            outfile.write(' direction=%s' % (quote_attrib(self.direction), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docParamName'):
        for item_ in self.content_:
            item_.export(outfile, level, item_.name, namespace_)
    def hasContent_(self):
        if (
            self.ref is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docParamName'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.direction is not None:
            showIndent(outfile, level)
            outfile.write('direction = "%s",\n' % (self.direction,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('content_ = [\n')
        for item_ in self.content_:
            item_.exportLiteral(outfile, level, name_)
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('direction'):
            self.direction = attrs.get('direction').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'ref':
            childobj_ = docRefTextType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'ref', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
# end class docParamName


class docXRefSectType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, id=None, xreftitle=None, xrefdescription=None):
        self.id = id
        if xreftitle is None:
            self.xreftitle = []
        else:
            self.xreftitle = xreftitle
        self.xrefdescription = xrefdescription
    def factory(*args_, **kwargs_):
        if docXRefSectType.subclass:
            return docXRefSectType.subclass(*args_, **kwargs_)
        else:
            return docXRefSectType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_xreftitle(self): return self.xreftitle
    def set_xreftitle(self, xreftitle): self.xreftitle = xreftitle
    def add_xreftitle(self, value): self.xreftitle.append(value)
    def insert_xreftitle(self, index, value): self.xreftitle[index] = value
    def get_xrefdescription(self): return self.xrefdescription
    def set_xrefdescription(self, xrefdescription): self.xrefdescription = xrefdescription
    def get_id(self): return self.id
    def set_id(self, id): self.id = id
    def export(self, outfile, level, namespace_='', name_='docXRefSectType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docXRefSectType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docXRefSectType'):
        if self.id is not None:
            outfile.write(' id=%s' % (self.format_string(quote_attrib(self.id).encode(ExternalEncoding), input_name='id'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docXRefSectType'):
        for xreftitle_ in self.xreftitle:
            showIndent(outfile, level)
            outfile.write('<%sxreftitle>%s</%sxreftitle>\n' % (namespace_, self.format_string(quote_xml(xreftitle_).encode(ExternalEncoding), input_name='xreftitle'), namespace_))
        if self.xrefdescription:
            self.xrefdescription.export(outfile, level, namespace_, name_='xrefdescription', )
    def hasContent_(self):
        if (
            self.xreftitle is not None or
            self.xrefdescription is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docXRefSectType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.id is not None:
            showIndent(outfile, level)
            outfile.write('id = %s,\n' % (self.id,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('xreftitle=[\n')
        level += 1
        for xreftitle in self.xreftitle:
            showIndent(outfile, level)
            outfile.write('%s,\n' % quote_python(xreftitle).encode(ExternalEncoding))
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
        if self.xrefdescription:
            showIndent(outfile, level)
            outfile.write('xrefdescription=model_.descriptionType(\n')
            self.xrefdescription.exportLiteral(outfile, level, name_='xrefdescription')
            showIndent(outfile, level)
            outfile.write('),\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('id'):
            self.id = attrs.get('id').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'xreftitle':
            xreftitle_ = ''
            for text__content_ in child_.childNodes:
                xreftitle_ += text__content_.nodeValue
            self.xreftitle.append(xreftitle_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'xrefdescription':
            obj_ = descriptionType.factory()
            obj_.build(child_)
            self.set_xrefdescription(obj_)
# end class docXRefSectType


class docCopyType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, link=None, para=None, sect1=None, internal=None):
        self.link = link
        if para is None:
            self.para = []
        else:
            self.para = para
        if sect1 is None:
            self.sect1 = []
        else:
            self.sect1 = sect1
        self.internal = internal
    def factory(*args_, **kwargs_):
        if docCopyType.subclass:
            return docCopyType.subclass(*args_, **kwargs_)
        else:
            return docCopyType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_para(self): return self.para
    def set_para(self, para): self.para = para
    def add_para(self, value): self.para.append(value)
    def insert_para(self, index, value): self.para[index] = value
    def get_sect1(self): return self.sect1
    def set_sect1(self, sect1): self.sect1 = sect1
    def add_sect1(self, value): self.sect1.append(value)
    def insert_sect1(self, index, value): self.sect1[index] = value
    def get_internal(self): return self.internal
    def set_internal(self, internal): self.internal = internal
    def get_link(self): return self.link
    def set_link(self, link): self.link = link
    def export(self, outfile, level, namespace_='', name_='docCopyType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docCopyType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docCopyType'):
        if self.link is not None:
            outfile.write(' link=%s' % (self.format_string(quote_attrib(self.link).encode(ExternalEncoding), input_name='link'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docCopyType'):
        for para_ in self.para:
            para_.export(outfile, level, namespace_, name_='para')
        for sect1_ in self.sect1:
            sect1_.export(outfile, level, namespace_, name_='sect1')
        if self.internal:
            self.internal.export(outfile, level, namespace_, name_='internal')
    def hasContent_(self):
        if (
            self.para is not None or
            self.sect1 is not None or
            self.internal is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docCopyType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.link is not None:
            showIndent(outfile, level)
            outfile.write('link = %s,\n' % (self.link,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('para=[\n')
        level += 1
        for para in self.para:
            showIndent(outfile, level)
            outfile.write('model_.para(\n')
            para.exportLiteral(outfile, level, name_='para')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
        showIndent(outfile, level)
        outfile.write('sect1=[\n')
        level += 1
        for sect1 in self.sect1:
            showIndent(outfile, level)
            outfile.write('model_.sect1(\n')
            sect1.exportLiteral(outfile, level, name_='sect1')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
        if self.internal:
            showIndent(outfile, level)
            outfile.write('internal=model_.docInternalType(\n')
            self.internal.exportLiteral(outfile, level, name_='internal')
            showIndent(outfile, level)
            outfile.write('),\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('link'):
            self.link = attrs.get('link').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'para':
            obj_ = docParaType.factory()
            obj_.build(child_)
            self.para.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'sect1':
            obj_ = docSect1Type.factory()
            obj_.build(child_)
            self.sect1.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'internal':
            obj_ = docInternalType.factory()
            obj_.build(child_)
            self.set_internal(obj_)
# end class docCopyType


class docCharType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, char=None, valueOf_=''):
        self.char = char
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if docCharType.subclass:
            return docCharType.subclass(*args_, **kwargs_)
        else:
            return docCharType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_char(self): return self.char
    def set_char(self, char): self.char = char
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='docCharType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docCharType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docCharType'):
        if self.char is not None:
            outfile.write(' char=%s' % (quote_attrib(self.char), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docCharType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docCharType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.char is not None:
            showIndent(outfile, level)
            outfile.write('char = "%s",\n' % (self.char,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('char'):
            self.char = attrs.get('char').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class docCharType


class docEmptyType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_=''):
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if docEmptyType.subclass:
            return docEmptyType.subclass(*args_, **kwargs_)
        else:
            return docEmptyType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='docEmptyType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docEmptyType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docEmptyType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docEmptyType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='docEmptyType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        pass
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('valueOf_ = "%s",\n' % (self.valueOf_,))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class docEmptyType


USAGE_TEXT = """
Usage: python <Parser>.py [ -s ] <in_xml_file>
Options:
    -s        Use the SAX parser, not the minidom parser.
"""

def usage():
    print USAGE_TEXT
    sys.exit(1)


def parse(inFileName):
    doc = minidom.parse(inFileName)
    rootNode = doc.documentElement
    rootObj = DoxygenType.factory()
    rootObj.build(rootNode)
    # Enable Python to collect the space used by the DOM.
    doc = None
    sys.stdout.write('<?xml version="1.0" ?>\n')
    rootObj.export(sys.stdout, 0, name_="doxygen",
        namespacedef_='')
    return rootObj


def parseString(inString):
    doc = minidom.parseString(inString)
    rootNode = doc.documentElement
    rootObj = DoxygenType.factory()
    rootObj.build(rootNode)
    # Enable Python to collect the space used by the DOM.
    doc = None
    sys.stdout.write('<?xml version="1.0" ?>\n')
    rootObj.export(sys.stdout, 0, name_="doxygen",
        namespacedef_='')
    return rootObj


def parseLiteral(inFileName):
    doc = minidom.parse(inFileName)
    rootNode = doc.documentElement
    rootObj = DoxygenType.factory()
    rootObj.build(rootNode)
    # Enable Python to collect the space used by the DOM.
    doc = None
    sys.stdout.write('from compound import *\n\n')
    sys.stdout.write('rootObj = doxygen(\n')
    rootObj.exportLiteral(sys.stdout, 0, name_="doxygen")
    sys.stdout.write(')\n')
    return rootObj


def main():
    args = sys.argv[1:]
    if len(args) == 1:
        parse(args[0])
    else:
        usage()


if __name__ == '__main__':
    main()
    #import pdb
    #pdb.run('main()')


########NEW FILE########
__FILENAME__ = index
#!/usr/bin/env python

"""
Generated Mon Feb  9 19:08:05 2009 by generateDS.py.
"""

from xml.dom import minidom

import os
import sys
import compound

import indexsuper as supermod

class DoxygenTypeSub(supermod.DoxygenType):
    def __init__(self, version=None, compound=None):
        supermod.DoxygenType.__init__(self, version, compound)

    def find_compounds_and_members(self, details):
        """
        Returns a list of all compounds and their members which match details
        """

        results = []
        for compound in self.compound:
            members = compound.find_members(details)
            if members:
                results.append([compound, members])
            else:
                if details.match(compound):
                    results.append([compound, []])

        return results

supermod.DoxygenType.subclass = DoxygenTypeSub
# end class DoxygenTypeSub


class CompoundTypeSub(supermod.CompoundType):
    def __init__(self, kind=None, refid=None, name='', member=None):
        supermod.CompoundType.__init__(self, kind, refid, name, member)

    def find_members(self, details):
        """
        Returns a list of all members which match details
        """

        results = []

        for member in self.member:
            if details.match(member):
                results.append(member)

        return results

supermod.CompoundType.subclass = CompoundTypeSub
# end class CompoundTypeSub


class MemberTypeSub(supermod.MemberType):

    def __init__(self, kind=None, refid=None, name=''):
        supermod.MemberType.__init__(self, kind, refid, name)

supermod.MemberType.subclass = MemberTypeSub
# end class MemberTypeSub


def parse(inFilename):

    doc = minidom.parse(inFilename)
    rootNode = doc.documentElement
    rootObj = supermod.DoxygenType.factory()
    rootObj.build(rootNode)

    return rootObj


########NEW FILE########
__FILENAME__ = indexsuper
#!/usr/bin/env python

#
# Generated Thu Jun 11 18:43:54 2009 by generateDS.py.
#

import sys
import getopt
from string import lower as str_lower
from xml.dom import minidom
from xml.dom import Node

#
# User methods
#
# Calls to the methods in these classes are generated by generateDS.py.
# You can replace these methods by re-implementing the following class
#   in a module named generatedssuper.py.

try:
    from generatedssuper import GeneratedsSuper
except ImportError, exp:

    class GeneratedsSuper:
        def format_string(self, input_data, input_name=''):
            return input_data
        def format_integer(self, input_data, input_name=''):
            return '%d' % input_data
        def format_float(self, input_data, input_name=''):
            return '%f' % input_data
        def format_double(self, input_data, input_name=''):
            return '%e' % input_data
        def format_boolean(self, input_data, input_name=''):
            return '%s' % input_data


#
# If you have installed IPython you can uncomment and use the following.
# IPython is available from http://ipython.scipy.org/.
#

## from IPython.Shell import IPShellEmbed
## args = ''
## ipshell = IPShellEmbed(args,
##     banner = 'Dropping into IPython',
##     exit_msg = 'Leaving Interpreter, back to program.')

# Then use the following line where and when you want to drop into the
# IPython shell:
#    ipshell('<some message> -- Entering ipshell.\nHit Ctrl-D to exit')

#
# Globals
#

ExternalEncoding = 'ascii'

#
# Support/utility functions.
#

def showIndent(outfile, level):
    for idx in range(level):
        outfile.write('    ')

def quote_xml(inStr):
    s1 = (isinstance(inStr, basestring) and inStr or
          '%s' % inStr)
    s1 = s1.replace('&', '&amp;')
    s1 = s1.replace('<', '&lt;')
    s1 = s1.replace('>', '&gt;')
    return s1

def quote_attrib(inStr):
    s1 = (isinstance(inStr, basestring) and inStr or
          '%s' % inStr)
    s1 = s1.replace('&', '&amp;')
    s1 = s1.replace('<', '&lt;')
    s1 = s1.replace('>', '&gt;')
    if '"' in s1:
        if "'" in s1:
            s1 = '"%s"' % s1.replace('"', "&quot;")
        else:
            s1 = "'%s'" % s1
    else:
        s1 = '"%s"' % s1
    return s1

def quote_python(inStr):
    s1 = inStr
    if s1.find("'") == -1:
        if s1.find('\n') == -1:
            return "'%s'" % s1
        else:
            return "'''%s'''" % s1
    else:
        if s1.find('"') != -1:
            s1 = s1.replace('"', '\\"')
        if s1.find('\n') == -1:
            return '"%s"' % s1
        else:
            return '"""%s"""' % s1


class MixedContainer:
    # Constants for category:
    CategoryNone = 0
    CategoryText = 1
    CategorySimple = 2
    CategoryComplex = 3
    # Constants for content_type:
    TypeNone = 0
    TypeText = 1
    TypeString = 2
    TypeInteger = 3
    TypeFloat = 4
    TypeDecimal = 5
    TypeDouble = 6
    TypeBoolean = 7
    def __init__(self, category, content_type, name, value):
        self.category = category
        self.content_type = content_type
        self.name = name
        self.value = value
    def getCategory(self):
        return self.category
    def getContenttype(self, content_type):
        return self.content_type
    def getValue(self):
        return self.value
    def getName(self):
        return self.name
    def export(self, outfile, level, name, namespace):
        if self.category == MixedContainer.CategoryText:
            outfile.write(self.value)
        elif self.category == MixedContainer.CategorySimple:
            self.exportSimple(outfile, level, name)
        else:    # category == MixedContainer.CategoryComplex
            self.value.export(outfile, level, namespace,name)
    def exportSimple(self, outfile, level, name):
        if self.content_type == MixedContainer.TypeString:
            outfile.write('<%s>%s</%s>' % (self.name, self.value, self.name))
        elif self.content_type == MixedContainer.TypeInteger or \
                self.content_type == MixedContainer.TypeBoolean:
            outfile.write('<%s>%d</%s>' % (self.name, self.value, self.name))
        elif self.content_type == MixedContainer.TypeFloat or \
                self.content_type == MixedContainer.TypeDecimal:
            outfile.write('<%s>%f</%s>' % (self.name, self.value, self.name))
        elif self.content_type == MixedContainer.TypeDouble:
            outfile.write('<%s>%g</%s>' % (self.name, self.value, self.name))
    def exportLiteral(self, outfile, level, name):
        if self.category == MixedContainer.CategoryText:
            showIndent(outfile, level)
            outfile.write('MixedContainer(%d, %d, "%s", "%s"),\n' % \
                (self.category, self.content_type, self.name, self.value))
        elif self.category == MixedContainer.CategorySimple:
            showIndent(outfile, level)
            outfile.write('MixedContainer(%d, %d, "%s", "%s"),\n' % \
                (self.category, self.content_type, self.name, self.value))
        else:    # category == MixedContainer.CategoryComplex
            showIndent(outfile, level)
            outfile.write('MixedContainer(%d, %d, "%s",\n' % \
                (self.category, self.content_type, self.name,))
            self.value.exportLiteral(outfile, level + 1)
            showIndent(outfile, level)
            outfile.write(')\n')


class _MemberSpec(object):
    def __init__(self, name='', data_type='', container=0):
        self.name = name
        self.data_type = data_type
        self.container = container
    def set_name(self, name): self.name = name
    def get_name(self): return self.name
    def set_data_type(self, data_type): self.data_type = data_type
    def get_data_type(self): return self.data_type
    def set_container(self, container): self.container = container
    def get_container(self): return self.container


#
# Data representation classes.
#

class DoxygenType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, version=None, compound=None):
        self.version = version
        if compound is None:
            self.compound = []
        else:
            self.compound = compound
    def factory(*args_, **kwargs_):
        if DoxygenType.subclass:
            return DoxygenType.subclass(*args_, **kwargs_)
        else:
            return DoxygenType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_compound(self): return self.compound
    def set_compound(self, compound): self.compound = compound
    def add_compound(self, value): self.compound.append(value)
    def insert_compound(self, index, value): self.compound[index] = value
    def get_version(self): return self.version
    def set_version(self, version): self.version = version
    def export(self, outfile, level, namespace_='', name_='DoxygenType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='DoxygenType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='DoxygenType'):
        outfile.write(' version=%s' % (self.format_string(quote_attrib(self.version).encode(ExternalEncoding), input_name='version'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='DoxygenType'):
        for compound_ in self.compound:
            compound_.export(outfile, level, namespace_, name_='compound')
    def hasContent_(self):
        if (
            self.compound is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='DoxygenType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.version is not None:
            showIndent(outfile, level)
            outfile.write('version = %s,\n' % (self.version,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('compound=[\n')
        level += 1
        for compound in self.compound:
            showIndent(outfile, level)
            outfile.write('model_.compound(\n')
            compound.exportLiteral(outfile, level, name_='compound')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('version'):
            self.version = attrs.get('version').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'compound':
            obj_ = CompoundType.factory()
            obj_.build(child_)
            self.compound.append(obj_)
# end class DoxygenType


class CompoundType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, kind=None, refid=None, name=None, member=None):
        self.kind = kind
        self.refid = refid
        self.name = name
        if member is None:
            self.member = []
        else:
            self.member = member
    def factory(*args_, **kwargs_):
        if CompoundType.subclass:
            return CompoundType.subclass(*args_, **kwargs_)
        else:
            return CompoundType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_name(self): return self.name
    def set_name(self, name): self.name = name
    def get_member(self): return self.member
    def set_member(self, member): self.member = member
    def add_member(self, value): self.member.append(value)
    def insert_member(self, index, value): self.member[index] = value
    def get_kind(self): return self.kind
    def set_kind(self, kind): self.kind = kind
    def get_refid(self): return self.refid
    def set_refid(self, refid): self.refid = refid
    def export(self, outfile, level, namespace_='', name_='CompoundType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='CompoundType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='CompoundType'):
        outfile.write(' kind=%s' % (quote_attrib(self.kind), ))
        outfile.write(' refid=%s' % (self.format_string(quote_attrib(self.refid).encode(ExternalEncoding), input_name='refid'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='CompoundType'):
        if self.name is not None:
            showIndent(outfile, level)
            outfile.write('<%sname>%s</%sname>\n' % (namespace_, self.format_string(quote_xml(self.name).encode(ExternalEncoding), input_name='name'), namespace_))
        for member_ in self.member:
            member_.export(outfile, level, namespace_, name_='member')
    def hasContent_(self):
        if (
            self.name is not None or
            self.member is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='CompoundType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.kind is not None:
            showIndent(outfile, level)
            outfile.write('kind = "%s",\n' % (self.kind,))
        if self.refid is not None:
            showIndent(outfile, level)
            outfile.write('refid = %s,\n' % (self.refid,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('name=%s,\n' % quote_python(self.name).encode(ExternalEncoding))
        showIndent(outfile, level)
        outfile.write('member=[\n')
        level += 1
        for member in self.member:
            showIndent(outfile, level)
            outfile.write('model_.member(\n')
            member.exportLiteral(outfile, level, name_='member')
            showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        showIndent(outfile, level)
        outfile.write('],\n')
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('kind'):
            self.kind = attrs.get('kind').value
        if attrs.get('refid'):
            self.refid = attrs.get('refid').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'name':
            name_ = ''
            for text__content_ in child_.childNodes:
                name_ += text__content_.nodeValue
            self.name = name_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'member':
            obj_ = MemberType.factory()
            obj_.build(child_)
            self.member.append(obj_)
# end class CompoundType


class MemberType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, kind=None, refid=None, name=None):
        self.kind = kind
        self.refid = refid
        self.name = name
    def factory(*args_, **kwargs_):
        if MemberType.subclass:
            return MemberType.subclass(*args_, **kwargs_)
        else:
            return MemberType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_name(self): return self.name
    def set_name(self, name): self.name = name
    def get_kind(self): return self.kind
    def set_kind(self, kind): self.kind = kind
    def get_refid(self): return self.refid
    def set_refid(self, refid): self.refid = refid
    def export(self, outfile, level, namespace_='', name_='MemberType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='MemberType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='MemberType'):
        outfile.write(' kind=%s' % (quote_attrib(self.kind), ))
        outfile.write(' refid=%s' % (self.format_string(quote_attrib(self.refid).encode(ExternalEncoding), input_name='refid'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='MemberType'):
        if self.name is not None:
            showIndent(outfile, level)
            outfile.write('<%sname>%s</%sname>\n' % (namespace_, self.format_string(quote_xml(self.name).encode(ExternalEncoding), input_name='name'), namespace_))
    def hasContent_(self):
        if (
            self.name is not None
            ):
            return True
        else:
            return False
    def exportLiteral(self, outfile, level, name_='MemberType'):
        level += 1
        self.exportLiteralAttributes(outfile, level, name_)
        if self.hasContent_():
            self.exportLiteralChildren(outfile, level, name_)
    def exportLiteralAttributes(self, outfile, level, name_):
        if self.kind is not None:
            showIndent(outfile, level)
            outfile.write('kind = "%s",\n' % (self.kind,))
        if self.refid is not None:
            showIndent(outfile, level)
            outfile.write('refid = %s,\n' % (self.refid,))
    def exportLiteralChildren(self, outfile, level, name_):
        showIndent(outfile, level)
        outfile.write('name=%s,\n' % quote_python(self.name).encode(ExternalEncoding))
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('kind'):
            self.kind = attrs.get('kind').value
        if attrs.get('refid'):
            self.refid = attrs.get('refid').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'name':
            name_ = ''
            for text__content_ in child_.childNodes:
                name_ += text__content_.nodeValue
            self.name = name_
# end class MemberType


USAGE_TEXT = """
Usage: python <Parser>.py [ -s ] <in_xml_file>
Options:
    -s        Use the SAX parser, not the minidom parser.
"""

def usage():
    print USAGE_TEXT
    sys.exit(1)


def parse(inFileName):
    doc = minidom.parse(inFileName)
    rootNode = doc.documentElement
    rootObj = DoxygenType.factory()
    rootObj.build(rootNode)
    # Enable Python to collect the space used by the DOM.
    doc = None
    sys.stdout.write('<?xml version="1.0" ?>\n')
    rootObj.export(sys.stdout, 0, name_="doxygenindex",
        namespacedef_='')
    return rootObj


def parseString(inString):
    doc = minidom.parseString(inString)
    rootNode = doc.documentElement
    rootObj = DoxygenType.factory()
    rootObj.build(rootNode)
    # Enable Python to collect the space used by the DOM.
    doc = None
    sys.stdout.write('<?xml version="1.0" ?>\n')
    rootObj.export(sys.stdout, 0, name_="doxygenindex",
        namespacedef_='')
    return rootObj


def parseLiteral(inFileName):
    doc = minidom.parse(inFileName)
    rootNode = doc.documentElement
    rootObj = DoxygenType.factory()
    rootObj.build(rootNode)
    # Enable Python to collect the space used by the DOM.
    doc = None
    sys.stdout.write('from index import *\n\n')
    sys.stdout.write('rootObj = doxygenindex(\n')
    rootObj.exportLiteral(sys.stdout, 0, name_="doxygenindex")
    sys.stdout.write(')\n')
    return rootObj


def main():
    args = sys.argv[1:]
    if len(args) == 1:
        parse(args[0])
    else:
        usage()




if __name__ == '__main__':
    main()
    #import pdb
    #pdb.run('main()')


########NEW FILE########
__FILENAME__ = text
#
# Copyright 2010 Free Software Foundation, Inc.
#
# This file is part of GNU Radio
#
# GNU Radio is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# GNU Radio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GNU Radio; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#
"""
Utilities for extracting text from generated classes.
"""

def is_string(txt):
    if isinstance(txt, str):
        return True
    try:
        if isinstance(txt, unicode):
            return True
    except NameError:
        pass
    return False

def description(obj):
    if obj is None:
        return None
    return description_bit(obj).strip()

def description_bit(obj):
    if hasattr(obj, 'content'):
        contents = [description_bit(item) for item in obj.content]
        result = ''.join(contents)
    elif hasattr(obj, 'content_'):
        contents = [description_bit(item) for item in obj.content_]
        result = ''.join(contents)
    elif hasattr(obj, 'value'):
        result = description_bit(obj.value)
    elif is_string(obj):
        return obj
    else:
        raise StandardError('Expecting a string or something with content, content_ or value attribute')
    # If this bit is a paragraph then add one some line breaks.
    if hasattr(obj, 'name') and obj.name == 'para':
        result += "\n\n"
    return result

########NEW FILE########
__FILENAME__ = swig_doc
#
# Copyright 2010,2011 Free Software Foundation, Inc.
#
# This file is part of GNU Radio
#
# GNU Radio is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# GNU Radio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GNU Radio; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#
"""
Creates the swig_doc.i SWIG interface file.
Execute using: python swig_doc.py xml_path outputfilename

The file instructs SWIG to transfer the doxygen comments into the
python docstrings.

"""

import sys

try:
    from doxyxml import DoxyIndex, DoxyClass, DoxyFriend, DoxyFunction, DoxyFile, base
except ImportError:
    from gnuradio.doxyxml import DoxyIndex, DoxyClass, DoxyFriend, DoxyFunction, DoxyFile, base


def py_name(name):
    bits = name.split('_')
    return '_'.join(bits[1:])

def make_name(name):
    bits = name.split('_')
    return bits[0] + '_make_' + '_'.join(bits[1:])


class Block(object):
    """
    Checks if doxyxml produced objects correspond to a gnuradio block.
    """

    @classmethod
    def includes(cls, item):
        if not isinstance(item, DoxyClass):
            return False
        # Check for a parsing error.
        if item.error():
            return False
        return item.has_member(make_name(item.name()), DoxyFriend)


def utoascii(text):
    """
    Convert unicode text into ascii and escape quotes.
    """
    if text is None:
        return ''
    out = text.encode('ascii', 'replace')
    out = out.replace('"', '\\"')
    return out


def combine_descriptions(obj):
    """
    Combines the brief and detailed descriptions of an object together.
    """
    description = []
    bd = obj.brief_description.strip()
    dd = obj.detailed_description.strip()
    if bd:
        description.append(bd)
    if dd:
        description.append(dd)
    return utoascii('\n\n'.join(description)).strip()


entry_templ = '%feature("docstring") {name} "{docstring}"'
def make_entry(obj, name=None, templ="{description}", description=None):
    """
    Create a docstring entry for a swig interface file.

    obj - a doxyxml object from which documentation will be extracted.
    name - the name of the C object (defaults to obj.name())
    templ - an optional template for the docstring containing only one
            variable named 'description'.
    description - if this optional variable is set then it's value is
            used as the description instead of extracting it from obj.
    """
    if name is None:
        name=obj.name()
    if "operator " in name:
        return ''
    if description is None:
        description = combine_descriptions(obj)
    docstring = templ.format(description=description)
    if not docstring:
        return ''
    return entry_templ.format(
        name=name,
        docstring=docstring,
        )


def make_func_entry(func, name=None, description=None, params=None):
    """
    Create a function docstring entry for a swig interface file.

    func - a doxyxml object from which documentation will be extracted.
    name - the name of the C object (defaults to func.name())
    description - if this optional variable is set then it's value is
            used as the description instead of extracting it from func.
    params - a parameter list that overrides using func.params.
    """
    if params is None:
        params = func.params
    params = [prm.declname for prm in params]
    if params:
        sig = "Params: (%s)" % ", ".join(params)
    else:
        sig = "Params: (NONE)"
    templ = "{description}\n\n" + sig
    return make_entry(func, name=name, templ=utoascii(templ),
                      description=description)


def make_class_entry(klass, description=None):
    """
    Create a class docstring for a swig interface file.
    """
    output = []
    output.append(make_entry(klass, description=description))
    for func in klass.in_category(DoxyFunction):
        name = klass.name() + '::' + func.name()
        output.append(make_func_entry(func, name=name))
    return "\n\n".join(output)


def make_block_entry(di, block):
    """
    Create class and function docstrings of a gnuradio block for a
    swig interface file.
    """
    descriptions = []
    # Get the documentation associated with the class.
    class_desc = combine_descriptions(block)
    if class_desc:
        descriptions.append(class_desc)
    # Get the documentation associated with the make function
    make_func = di.get_member(make_name(block.name()), DoxyFunction)
    make_func_desc = combine_descriptions(make_func)
    if make_func_desc:
        descriptions.append(make_func_desc)
    # Get the documentation associated with the file
    try:
        block_file = di.get_member(block.name() + ".h", DoxyFile)
        file_desc = combine_descriptions(block_file)
        if file_desc:
            descriptions.append(file_desc)
    except base.Base.NoSuchMember:
        # Don't worry if we can't find a matching file.
        pass
    # And join them all together to make a super duper description.
    super_description = "\n\n".join(descriptions)
    # Associate the combined description with the class and
    # the make function.
    output = []
    output.append(make_class_entry(block, description=super_description))
    creator = block.get_member(block.name(), DoxyFunction)
    output.append(make_func_entry(make_func, description=super_description,
                                  params=creator.params))
    return "\n\n".join(output)


def make_swig_interface_file(di, swigdocfilename, custom_output=None):

    output = ["""
/*
 * This file was automatically generated using swig_doc.py.
 *
 * Any changes to it will be lost next time it is regenerated.
 */
"""]

    if custom_output is not None:
        output.append(custom_output)

    # Create docstrings for the blocks.
    blocks = di.in_category(Block)
    make_funcs = set([])
    for block in blocks:
        try:
            make_func = di.get_member(make_name(block.name()), DoxyFunction)
            make_funcs.add(make_func.name())
            output.append(make_block_entry(di, block))
        except block.ParsingError:
            print('Parsing error for block %s' % block.name())

    # Create docstrings for functions
    # Don't include the make functions since they have already been dealt with.
    funcs = [f for f in di.in_category(DoxyFunction) if f.name() not in make_funcs]
    for f in funcs:
        try:
            output.append(make_func_entry(f))
        except f.ParsingError:
            print('Parsing error for function %s' % f.name())

    # Create docstrings for classes
    block_names = [block.name() for block in blocks]
    klasses = [k for k in di.in_category(DoxyClass) if k.name() not in block_names]
    for k in klasses:
        try:
            output.append(make_class_entry(k))
        except k.ParsingError:
            print('Parsing error for class %s' % k.name())

    # Docstrings are not created for anything that is not a function or a class.
    # If this excludes anything important please add it here.

    output = "\n\n".join(output)

    swig_doc = file(swigdocfilename, 'w')
    swig_doc.write(output)
    swig_doc.close()

if __name__ == "__main__":
    # Parse command line options and set up doxyxml.
    err_msg = "Execute using: python swig_doc.py xml_path outputfilename"
    if len(sys.argv) != 3:
        raise StandardError(err_msg)
    xml_path = sys.argv[1]
    swigdocfilename = sys.argv[2]
    di = DoxyIndex(xml_path)

    # gnuradio.gr.msq_queue.insert_tail and delete_head create errors unless docstrings are defined!
    # This is presumably a bug in SWIG.
    #msg_q = di.get_member(u'gr_msg_queue', DoxyClass)
    #insert_tail = msg_q.get_member(u'insert_tail', DoxyFunction)
    #delete_head = msg_q.get_member(u'delete_head', DoxyFunction)
    output = []
    #output.append(make_func_entry(insert_tail, name='gr_py_msg_queue__insert_tail'))
    #output.append(make_func_entry(delete_head, name='gr_py_msg_queue__delete_head'))
    custom_output = "\n\n".join(output)

    # Generate the docstrings interface file.
    make_swig_interface_file(di, swigdocfilename, custom_output=custom_output)

########NEW FILE########
__FILENAME__ = gr_baz_attach
#!/usr/bin/env python

import sys
import os

if __name__ == '__main__':
    if len(sys.argv) == 1:
        print 'usage: gr_baz_attach.py [path to gnuradio src tree]'
        exit()
    top_gr_cmakelists = os.path.join(sys.argv[1], 'CMakeLists.txt')
    gr_baz_src_dir = os.path.dirname(os.path.abspath(__file__)).replace("\\","\\\\")
    content = open(top_gr_cmakelists).read()
    if 'BazSubProj.cmake' not in content:
        content = content.replace('add_subdirectory(grc)',
"""add_subdirectory(grc)
file(TO_CMAKE_PATH %s GR_BAZ_SRC_DIR)
include(${GR_BAZ_SRC_DIR}/BazSubProj.cmake)"""%gr_baz_src_dir)
    open(top_gr_cmakelists, 'w').write(content)

########NEW FILE########
__FILENAME__ = sitecustomize
import os, sys

_sc_path = os.path.abspath( __file__ )
try:
	print "Customising for:", _sc_path.split(os.sep)[-5]
except:
	print "[!] Customising for:", _sc_path

_gr_base_path = None
try:
	_gr_base_path = os.path.dirname(_sc_path)
	sys.path = [os.path.join(_gr_base_path, 'gnuradio')] + sys.path
except:
	print "Failed to add gnuradio in sitecustomize:", _gr_base_path

import op25		# From local sitecustomize'd gnuradio directory
import gnuradio		# From global installation
gnuradio.op25 = op25	# Inject local module into global

########NEW FILE########
__FILENAME__ = acars_printer
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  acars_printer.py
#  
#  Copyright 2013 Balint Seeber <balint@crawfish>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#  

"""
	
	enum flags_t
	{
		FLAG_NONE	= 0x00,
		FLAG_SOH	= 0x01,
		FLAG_STX	= 0x02,
		FLAG_ETX	= 0x04,
		FLAG_DLE	= 0x08
	};
	
	struct packet
	{
		float prekey_average;
		int prekey_ones;
		unsigned char bytes[MAX_PACKET_SIZE];
		unsigned char byte_error[MAX_PACKET_SIZE];
		int parity_error_count;
		int byte_count;
		unsigned char flags;
		int etx_index;
	};
"""

_MAX_PACKET_SIZE = 252

#import threading
import gnuradio.gr.gr_threading as _threading
import struct, datetime, time, traceback
from aviation import acars

class acars_struct():
	def __init__(self, data):
		try:
			fmt_str = "=ffi%is%isiiBi" % (_MAX_PACKET_SIZE, _MAX_PACKET_SIZE)	# '=' for #pragma pack(1)
			struct_size = struct.calcsize(fmt_str)
			
			(self.reference_level,
			self.prekey_average,
			self.prekey_ones,
			self.byte_data,
			self.byte_error,
			self.parity_error_count,
			self.byte_count,
			self.flags,
			self.etx_index) = struct.unpack(fmt_str, data[:struct_size])
			
			self.station_name = "".join(data[struct_size:])
			
			#print "Data:", self.byte_data
			#print "Errors:", self.byte_error
		except Exception, e:
			print "Exception unpacking data of length %i: %s" % (len(data), str(e))
			raise e

class queue_watcher_thread(_threading.Thread):
	def __init__(self, msgq, callback=None):
		_threading.Thread.__init__(self)
		self.setDaemon(1)
		self.msgq = msgq
		self.callback = callback
		self.keep_running = True
		self.start()
	def stop(self):
		print "Stopping..."
		self.keep_running = False
	def run(self):
		while self.keep_running:
			msg = self.msgq.delete_head()
			#msg.type() flags
			msg_str = msg.to_string()
			try:
				unpacked = acars_struct(msg_str)
				#print "==> Received ACARS struct with %i pre-key ones" % (unpacked.prekey_ones)
				if self.callback:
					self.callback(unpacked)
				else:
					print "==> Reference level:", unpacked.reference_level	# msg.arg2()
					d = {}
					start = 1	# Skip SOH
					end = unpacked.byte_count-(1+2)	# Skip BCS and DEL
					d['Message'] = unpacked.byte_data[start:end]
					if unpacked.parity_error_count > 0:
						#print "==> Parity error count:", unpacked.parity_error_count
						error_indices = unpacked.byte_error[start:end]
						if '\x01' in error_indices:
							d['ErrorIndices'] = error_indices
							#print map(ord, d['ErrorIndices'])
					d['Time'] = int(time.time() * 1000)
					d['FeedParameters'] = {'StationName':unpacked.station_name, 'Frequency':msg.arg1()/1e6}
					try:
						acars_payload = acars.payload.parse(d)
						print str(acars_payload)
					except Exception, e:
						print "Exception parsing ACARS message: ", e
						traceback.print_exc()
			except Exception, e:
				print "Exception unpacking ACARS message: ", e
				traceback.print_exc()

def main():
	return 0

if __name__ == '__main__':
	main()

########NEW FILE########
__FILENAME__ = auto_fec
#!/usr/bin/env python

"""
Automatically try each combination of FEC parameters until the correct one is found.
The deFEC routine is inside decode_ccsds_27_fb (NASA Voyager, k=7, 1/2 rate).
Parameters are controller by auto_fec_xform.
Keep an eye on the console to watch the progress of the parameter search.
The auto_fec block creation arguments control its behaviour.
Ordinarily leave sample_rate at 0 to have the other durations/periods interpreted as sample counts.
If the sample rate is specified, you can also engage the internal throttle if playing back from a file.
Part of gr-baz. More info: http://wiki.spench.net/wiki/gr-baz
By Balint Seeber (http://spench.net/contact)
"""

from __future__ import with_statement

import threading, math, time
import wx
import numpy

from gnuradio import gr, blocks
from grc_gnuradio import blks2 as grc_blks2
import baz

_puncture_matrices = [
		('1/2', [1,1], (1, 2)),
		('2/3', [1,1,0,1], (2, 3)),
		('3/4', [1,1,0,1,1,0], (3, 4)),
		('5/6', [1,1,0,1,1,0,0,1,1,0], (5, 6)),
		('7/8', [1,1,0,1,0,1,0,1,1,0,0,1,1,0], (7, 8)),
		('2/3*', [1,1,1,0], (2, 3)),
		('3/4*', [1,1,1,0,0,1], (3, 4)),
		('5/6*', [1,1,1,0,0,1,1,0,0,1], (5, 6)),
		('7/8*', [1,1,1,0,1,0,1,0,0,1,1,0,0,1], (7, 8))
	]

_phase_multiplication = [
		('0', 1),
		('90', 1j),
		# Others are just inverse of former - inverted stream can be fixed manually
		#('180', -1),
		#('270', -1j)
	]

class auto_fec_xform():
	#CHANGE_EVERYTHING = -1
	#CHANGE_NOTHING = 0
	CHANGE_ROTATION = 1
	CHANGE_CONJUGATION = 2
	CHANGE_INVERSION = 3
	CHANGE_PUNCTURE_DELAY = 4
	CHANGE_VITERBI_DELAY = 5
	CHANGE_VITERBI_SWAP = 6
	_clonable = [
			'conjugate',
			'rotation',
			'invert',
			'puncture_delay',
			'viterbi_delay',
			'viterbi_delay',
			'viterbi_swap'
		]
	def __init__(self):
		self.conjugate = False
		self.rotation = 0
		self.invert = False
		self.puncture_delay = 0
		self.viterbi_delay = False
		self.viterbi_swap = False
	def copy(self):
		clone = auto_fec_xform()
		#for k in auto_fec_xform._clonable:
		#	clone[k] = self[k]
		clone.conjugate = self.conjugate
		clone.rotation = self.rotation
		clone.invert = self.invert
		clone.puncture_delay = self.puncture_delay
		clone.viterbi_delay = self.viterbi_delay
		clone.viterbi_swap = self.viterbi_swap
		return clone
	def get_conjugation_index(self):
		if self.conjugate:
			return 0
		return 1
	def get_rotation(self):
		return _phase_multiplication[self.rotation][1]
	def get_inversion(self):
		if self.invert:
			return -1
		return 1
	def get_puncture_delay(self):
		return self.puncture_delay
	def get_viterbi_delay(self):
		if self.viterbi_delay:
			return 1
		return 0
	def get_viterbi_swap(self):
		return self.viterbi_swap
	def next(self, ref, fec_rate, psk_order=4):
		changes = []
		
		changes += [auto_fec_xform.CHANGE_ROTATION]
		# FIXME: Handle arbitrary PSK order
		self.rotation = (self.rotation + 1) % len(_phase_multiplication)	# Not doing inversion as this takes care of it
		if self.rotation != ref.rotation:
			return (True, changes)
		
		changes += [auto_fec_xform.CHANGE_CONJUGATION]
		self.conjugate = not self.conjugate
		if self.conjugate != ref.conjugate:
			return (True, changes)
		
		# Skipping inversion (handled by constellation rotation)
		
		changes += [auto_fec_xform.CHANGE_VITERBI_DELAY]
		self.viterbi_delay = not self.viterbi_delay
		if self.viterbi_delay != ref.viterbi_delay:
			return (True, changes)
		
		changes += [auto_fec_xform.CHANGE_VITERBI_SWAP]
		self.viterbi_swap = not self.viterbi_swap
		if self.viterbi_swap != ref.viterbi_swap:
			return (True, changes)
		
		changes += [auto_fec_xform.CHANGE_PUNCTURE_DELAY]
		self.puncture_delay = (self.puncture_delay + 1) % (2 * fec_rate[0])
		if self.puncture_delay != ref.puncture_delay:
			return (True, changes)
		
		return (False, changes)	# Back to reference point (if FEC unlocked, try next rate)

class auto_fec_input_watcher (threading.Thread):
	def __init__ (self, auto_fec_block, **kwds):
		threading.Thread.__init__ (self, **kwds)
		self.setDaemon(1)
		
		self.afb = auto_fec_block
		
		self.keep_running = True
		#self.skip = 0
		self.total_samples = 0
		self.last_sample_count_report = 0
		self.last_msg_time = None
		
		self.lock = threading.Lock()
		
		self.sample_rate = self.afb.sample_rate
		self.set_sample_rate(self.afb.sample_rate)
		self.ber_duration = self.afb.ber_duration
		self.settling_period = self.afb.settling_period
		self.pre_lock_duration = self.afb.pre_lock_duration
		
		###############################
		#self.excess_ber_count = 0
		#self.samples_since_excess = 0
		
		#self.fec_found = False
		#self.puncture_matrix = 0
		#self.xform_search = None
		#self.xform_lock = auto_fec_xform()
		self.reset()
		###############################
		
		self.skip_samples = self.settling_period	# + self.ber_duration
	def set_sample_rate(self, rate):
		#print "Adjusting durations with new sample rate:", rate
		if rate is None or rate <= 0:
			#rate = 1000
			return
		with self.lock:
			self.sample_rate = rate
			#self.ber_duration = int((self.afb.ber_duration / 1000.0) * rate)
			#self.settling_period = int((self.afb.settling_period / 1000.0) * rate)
			#self.pre_lock_duration = int((self.afb.pre_lock_duration / 1000.0) * rate)
			#print "\tber_duration:\t\t", self.ber_duration
			#print "\tsettling_period:\t", self.settling_period
			#print "\tpre_lock_duration:\t", self.pre_lock_duration
			#print ""
	def reset(self):
		self.excess_ber_count = 0
		self.samples_since_excess = 0
		self.excess_ber_sum = 0
		
		self.fec_found = False
		self.puncture_matrix = 0
		self.xform_search = None
		self.xform_lock = auto_fec_xform()
	def set_reset(self):
		with self.lock:
			print "==> Resetting..."
			self.reset()
			self.afb.update_matrix(_puncture_matrices[self.puncture_matrix][1])
			self.afb.update_xform(self.xform_lock)
			self.afb.update_lock(0)
			#print "    Reset."
	def set_puncture_matrix(self, matrix):
		# Not applying, just trigger another search
		self.set_reset()
	def run (self):
		print "Auto-FEC thread started:", self.getName()
		print "Skipping initial samples while MPSK receiver locks:", self.skip_samples
		print ""
		
		# Already applied in CTOR
		#print "Applying default FEC parameters..."
		#self.afb.update_matrix(_puncture_matrices[self.puncture_matrix][1])
		#self.afb.update_xform(self.xform_lock)
		#print "Completed applying default FEC parameters."
		#print ""
		
		while (self.keep_running):
			msg = self.afb.msg_q.delete_head()	# blocking read of message queue
			nchan = int(msg.arg1())				# number of channels of data in msg
			nsamples = int(msg.arg2())			# number of samples in each channel
			
			if self.last_msg_time is None:
				self.last_msg_time = time.time()
			
			self.total_samples += nsamples
			
			with self.lock:
				if self.sample_rate > 0 and (self.total_samples - self.last_sample_count_report) >= self.sample_rate:
					diff = self.total_samples - self.last_sample_count_report - self.sample_rate
					print "==> Received total samples:", self.total_samples, "diff:", diff
					time_now = time.time()
					time_diff = time_now - self.last_msg_time
					print "==> Time diff:", time_diff
					self.last_msg_time = time_now
					self.last_sample_count_report = self.total_samples - diff
			
			if self.skip_samples >= nsamples:
				self.skip_samples -= nsamples
				continue
			
			start = self.skip_samples * gr.sizeof_float	#max(0, self.skip_samples - (self.skip_samples % gr.sizeof_float))
			self.skip_samples = 0
			#if start > 0:
			#	print "Starting sample processing at byte index:", start, "total samples received:", self.total_samples
			
			data = msg.to_string()
			assert nsamples == (len(data) / 4)
			data = data[start:]
			samples = numpy.fromstring(data, numpy.float32)
			
			with self.lock:
				#print "Processing samples:", len(samples)
				
				excess_ber = False
				for x in samples:
					if x >= self.afb.ber_threshold:
						self.excess_ber_count += 1
						self.excess_ber_sum += x
						if self.excess_ber_count >= self.ber_duration:
							excess_ber = True
							#self.excess_ber_count = 0
							break
					else:
						if self.excess_ber_count > 0:
							if self.fec_found:
								print "Excess BER count was:", self.excess_ber_count
							self.excess_ber_count = 0
							self.excess_ber_sum = 0
				
				if excess_ber:
					excess_ber_ave = self.excess_ber_sum / self.excess_ber_count
					self.excess_ber_sum = 0
					self.excess_ber_count = 0
					print "Reached excess BER limit:", excess_ber_ave, ", locked:", self.fec_found, ", current puncture matrix:", self.puncture_matrix, ", total samples received:", self.total_samples
					self.samples_since_excess = 0
					
					if self.xform_search is None:
						self.afb.update_lock(0)
						print "Beginning search..."
						self.xform_search = self.xform_lock.copy()
					
					(more, changes) = self.xform_search.next(self.xform_lock, _puncture_matrices[self.puncture_matrix][2])
					if more == False:
						print "Completed XForm cycle"
						if self.fec_found == False:
							self.puncture_matrix = (self.puncture_matrix + 1) % len(_puncture_matrices)
							print "----------------------------"
							print "Trying next puncture matrix:", _puncture_matrices[self.puncture_matrix][0], "[", _puncture_matrices[self.puncture_matrix][1], "]"
							print "----------------------------"
							self.afb.update_matrix(_puncture_matrices[self.puncture_matrix][1])
						else:
							pass	# Keep looping
					self.afb.update_xform(self.xform_search, changes)
					#print "Skipping samples for settling period:", self.settling_period
					self.skip_samples = self.settling_period	# Wait some time for new parameters to take effect
				else:
					self.samples_since_excess += len(samples)
					
					if self.xform_search is not None or self.fec_found == False:
						if self.samples_since_excess > self.pre_lock_duration:
							print "Locking current XForm"
							if self.xform_search is not None:
								self.xform_lock = self.xform_search
								self.xform_search = None
							if self.fec_found == False:
								print "========================================================="
								print "FEC locked:", _puncture_matrices[self.puncture_matrix][0]
								print "========================================================="
								self.fec_found = True
							self.afb.update_lock(1)
				
				#########################
				
				#self.msg_string += msg.to_string()	# body of the msg as a string

				#bytes_needed = (samples) * gr.sizeof_float
				#if (len(self.msg_string) < bytes_needed):
				#	continue

				#records = []
				#start = 0	#self.skip * gr.sizeof_float
				#chan_data = self.msg_string[start:start+bytes_needed]
				#rec = numpy.fromstring (chan_data, numpy.float32)
				#records.append (rec)
				#self.msg_string = ""

				#unused = nsamples - (self.num_plots*self.samples_per_symbol)
				#unused -= (start / gr.sizeof_float)
				#self.skip = self.samples_per_symbol - (unused % self.samples_per_symbol)
				# print "reclen = %d totsamp %d appended %d skip %d start %d unused %d" % (nsamples, self.total_samples, len(rec), self.skip, start/gr.sizeof_float, unused)

				#de = datascope_DataEvent (records, self.samples_per_symbol, self.num_plots)
			
			#wx.PostEvent (self.event_receiver, de)
			#records = []
			#del de

			#self.skip_samples = self.num_plots * self.samples_per_symbol * self.sym_decim   # lower values = more frequent plots, but higher CPU usage
			#self.skip_samples = self.afb.ber_sample_skip -
		print "Auto-FEC thread exiting:", self.getName()

class auto_fec(gr.hier_block2):
	def __init__(self,
		sample_rate,
		ber_threshold=0,	# Above which to do search
		ber_smoothing=0,	# Alpha of BER smoother (0.01)
		ber_duration=0,		# Length before trying next combo
		ber_sample_decimation=1,
		settling_period=0,
		pre_lock_duration=0,
		#ber_sample_skip=0
		**kwargs):
		
		use_throttle = False
		base_duration = 1024
		if sample_rate > 0:
			use_throttle = True
			base_duration *= 4	# Has to be high enough for block-delay
		
		if ber_threshold == 0:
			ber_threshold = 512 * 4
		if ber_smoothing == 0:
			ber_smoothing = 0.01
		if ber_duration == 0:
			ber_duration = base_duration * 2 # 1000ms
		if settling_period == 0:
			settling_period = base_duration * 1 # 500ms
		if pre_lock_duration == 0:
			pre_lock_duration = base_duration * 2 #1000ms
		
		print "Creating Auto-FEC:"
		print "\tsample_rate:\t\t", sample_rate
		print "\tber_threshold:\t\t", ber_threshold
		print "\tber_smoothing:\t\t", ber_smoothing
		print "\tber_duration:\t\t", ber_duration
		print "\tber_sample_decimation:\t", ber_sample_decimation
		print "\tsettling_period:\t", settling_period
		print "\tpre_lock_duration:\t", pre_lock_duration
		print ""
		
		self.sample_rate = sample_rate
		self.ber_threshold = ber_threshold
		#self.ber_smoothing = ber_smoothing
		self.ber_duration = ber_duration
		self.settling_period = settling_period
		self.pre_lock_duration = pre_lock_duration
		#self.ber_sample_skip = ber_sample_skip
		
		self.data_lock = threading.Lock()

		gr.hier_block2.__init__(self, "auto_fec",
			gr.io_signature(1, 1, gr.sizeof_gr_complex),			# Post MPSK-receiver complex input
			gr.io_signature3(3, 3, gr.sizeof_char, gr.sizeof_float, gr.sizeof_float))	# Decoded packed bytes, BER metric, lock
		
		self.input_watcher = auto_fec_input_watcher(self)
		default_xform = self.input_watcher.xform_lock
		
		self.gr_conjugate_cc_0 = gr.conjugate_cc()
		self.connect((self, 0), (self.gr_conjugate_cc_0, 0))	# Input
		
		self.blks2_selector_0 = grc_blks2.selector(
			item_size=gr.sizeof_gr_complex*1,
			num_inputs=2,
			num_outputs=1,
			input_index=default_xform.get_conjugation_index(),
			output_index=0,
		)
		self.connect((self.gr_conjugate_cc_0, 0), (self.blks2_selector_0, 0))
		self.connect((self, 0), (self.blks2_selector_0, 1))		# Input
		
		self.gr_multiply_const_vxx_3 = gr.multiply_const_vcc((0.707*(1+1j), ))
		self.connect((self.blks2_selector_0, 0), (self.gr_multiply_const_vxx_3, 0))
		
		self.gr_multiply_const_vxx_2 = gr.multiply_const_vcc((default_xform.get_rotation(), ))	# phase_mult
		self.connect((self.gr_multiply_const_vxx_3, 0), (self.gr_multiply_const_vxx_2, 0))
		
		self.gr_complex_to_float_0_0 = gr.complex_to_float(1)
		self.connect((self.gr_multiply_const_vxx_2, 0), (self.gr_complex_to_float_0_0, 0))
		
		self.gr_interleave_1 = gr.interleave(gr.sizeof_float*1)
		self.connect((self.gr_complex_to_float_0_0, 1), (self.gr_interleave_1, 1))
		self.connect((self.gr_complex_to_float_0_0, 0), (self.gr_interleave_1, 0))
		
		self.gr_multiply_const_vxx_0 = gr.multiply_const_vff((1, ))	# invert
		self.connect((self.gr_interleave_1, 0), (self.gr_multiply_const_vxx_0, 0))
		
		self.baz_delay_2 = baz.delay(gr.sizeof_float*1, default_xform.get_puncture_delay())	# delay_puncture
		self.connect((self.gr_multiply_const_vxx_0, 0), (self.baz_delay_2, 0))
		
		self.depuncture_ff_0 = baz.depuncture_ff((_puncture_matrices[self.input_watcher.puncture_matrix][1]))	# puncture_matrix
		self.connect((self.baz_delay_2, 0), (self.depuncture_ff_0, 0))
		
		self.baz_delay_1 = baz.delay(gr.sizeof_float*1, default_xform.get_viterbi_delay())	# delay_viterbi
		self.connect((self.depuncture_ff_0, 0), (self.baz_delay_1, 0))
		
		self.swap_ff_0 = baz.swap_ff(default_xform.get_viterbi_swap())	# swap_viterbi
		self.connect((self.baz_delay_1, 0), (self.swap_ff_0, 0))
		
		self.gr_decode_ccsds_27_fb_0 = gr.decode_ccsds_27_fb()
		
		if use_throttle:
			print "==> Using throttle at sample rate:", self.sample_rate
			self.gr_throttle_0 = gr.throttle(gr.sizeof_float, self.sample_rate)
			self.connect((self.swap_ff_0, 0), (self.gr_throttle_0, 0))
			self.connect((self.gr_throttle_0, 0), (self.gr_decode_ccsds_27_fb_0, 0))
		else:
			self.connect((self.swap_ff_0, 0), (self.gr_decode_ccsds_27_fb_0, 0))
		
		self.connect((self.gr_decode_ccsds_27_fb_0, 0), (self, 0))	# Output bytes
		
		self.gr_add_const_vxx_1 = gr.add_const_vff((-4096, ))
		self.connect((self.gr_decode_ccsds_27_fb_0, 1), (self.gr_add_const_vxx_1, 0))
		
		self.gr_multiply_const_vxx_1 = gr.multiply_const_vff((-1, ))
		self.connect((self.gr_add_const_vxx_1, 0), (self.gr_multiply_const_vxx_1, 0))
		self.connect((self.gr_multiply_const_vxx_1, 0), (self, 1))	# Output BER
		
		self.gr_single_pole_iir_filter_xx_0 = gr.single_pole_iir_filter_ff(ber_smoothing, 1)
		self.connect((self.gr_multiply_const_vxx_1, 0), (self.gr_single_pole_iir_filter_xx_0, 0))
		
		self.gr_keep_one_in_n_0 = blocks.keep_one_in_n(gr.sizeof_float, ber_sample_decimation)
		self.connect((self.gr_single_pole_iir_filter_xx_0, 0), (self.gr_keep_one_in_n_0, 0))
		
		self.const_source_x_0 = gr.sig_source_f(0, gr.GR_CONST_WAVE, 0, 0, 0)	# Last param is const value
		if use_throttle:
			lock_throttle_rate = self.sample_rate // 16
			print "==> Using lock throttle rate:", lock_throttle_rate
			self.gr_throttle_1 = gr.throttle(gr.sizeof_float, lock_throttle_rate)
			self.connect((self.const_source_x_0, 0), (self.gr_throttle_1, 0))
			self.connect((self.gr_throttle_1, 0), (self, 2))
		else:
			self.connect((self.const_source_x_0, 0), (self, 2))
		
		self.msg_q = gr.msg_queue(2*256)	# message queue that holds at most 2 messages, increase to speed up process
		self.msg_sink = gr.message_sink(gr.sizeof_float, self.msg_q, dont_block=0)	# Block to speed up process
		self.connect((self.gr_keep_one_in_n_0, 0), self.msg_sink)
		
		self.input_watcher.start()
	def update_xform(self, xform, changes=None):
		#with self.data_lock:
			#print "\tBeginning application..."
			if changes is None or auto_fec_xform.CHANGE_ROTATION in changes:
				print "\tApplying rotation:", xform.get_rotation()
				self.gr_multiply_const_vxx_2.set_k((xform.get_rotation(), ))
			if changes is None or auto_fec_xform.CHANGE_CONJUGATION in changes:
				print "\tApplying conjugation:", xform.get_conjugation_index()
				self.blks2_selector_0.set_input_index(xform.get_conjugation_index())
			if changes is None or auto_fec_xform.CHANGE_INVERSION in changes:
				pass
			if changes is None or auto_fec_xform.CHANGE_PUNCTURE_DELAY in changes:
				print "\tApplying puncture delay:", xform.get_puncture_delay()
				self.baz_delay_2.set_delay(xform.get_puncture_delay())
			if changes is None or auto_fec_xform.CHANGE_VITERBI_DELAY in changes:
				print "\tApplying viterbi delay:", xform.get_viterbi_delay()
				self.baz_delay_1.set_delay(xform.get_viterbi_delay())
			if changes is None or auto_fec_xform.CHANGE_VITERBI_SWAP in changes:
				print "\tApplying viterbi swap:", xform.get_viterbi_swap()
				self.swap_ff_0.set_swap(xform.get_viterbi_swap())
			#print "\tApplication complete."
			print ""
	def update_matrix(self, matrix):
		#with self.data_lock:
			print "\tApplying puncture matrix:", matrix
			self.depuncture_ff_0.set_matrix(matrix)
	def update_lock(self, locked):
		#with self.data_lock:
			print "\tApplying lock value:", locked
			self.const_source_x_0.set_offset(locked)
	def set_sample_rate(self, rate):
		self.sample_rate = rate
		self.input_watcher.set_sample_rate(rate)
	def set_ber_threshold(self, threshold):
		pass
	def set_ber_smoothing(self, smoothing):
		pass
	def set_ber_duration(self, duration):
		pass
	def set_ber_sample_decimation(self, rate):
		self.gr_keep_one_in_n_0.set_n(rate)
	def set_settling_period(self, period):
		pass
	def set_pre_lock_duration(self, duration):
		pass
	def set_puncture_matrix(self, matrix):
		# Not applying, just cause another search
		self.input_watcher.set_puncture_matrix(matrix)
	def set_reset(self, dummy):
		self.input_watcher.set_reset()

########NEW FILE########
__FILENAME__ = baudline
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  baudline.py
#  
#  Copyright 2013 Balint Seeber <balint@crawfish>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#  

# le32f	- 1 Msps
# le16	- 4 Msps
# Pipe mode kill works, FIFO doesn't

import sys, subprocess, tempfile, os, signal

from gnuradio import gr, gru, blocks

class baudline_sink(gr.hier_block2):
	def __init__(self, fmt, item_size, channels, is_complex, sample_rate,
		flip_complex=True, baseband_freq=None, decimation=1, scale=1.0, overlap=None, slide_size=None, fft_size=None, jump_step=None, x_slip=None,
		mode='pipe', buffered=True, kill_on_del=True, memory=None, peak_hold=False, **kwds):
		
		gr.hier_block2.__init__(self, "baudline_sink",
								gr.io_signature(1, 1, item_size),
								gr.io_signature(0, 0, 0))
		
		baudline_path = gr.prefs().get_string('baudline', 'path', 'baudline')
		
		#tf = tempfile.NamedTemporaryFile(delete=False)
		#tf.write(gp)
		#tf.close()
		#print tf.name
		
		self.mode = mode
		self.kill_on_del = kill_on_del
		
		if mode == 'fifo':
			fifo_name = 'baudline_fifo'
			self.tmpdir = tempfile.mkdtemp()
			self.filename = os.path.join(self.tmpdir, fifo_name)
			print self.filename
			try:
				os.mkfifo(self.filename)
			except OSError, e:
				print "Failed to create FIFO: %s" % e
				raise
		
		baudline_exec = [
			baudline_path,
			"-stdin",
			"-record",
			"-spacebar", "recordpause",
			"-samplerate", str(int(sample_rate)),
			"-channels", str(channels),
			"-format", fmt,
			"-backingstore",
			
			# #
			#"-threads",
			#"-pipeline",
			#"-memory",	# MB
			#"-verticalsync"
			
			#"-realtime",
			#"-psd"
			#"-reversetimeaxis",
			#"-overclock",
			
			#"-debug",
			#"-debugtimer", str(1000)
			#"-debugfragments",
			#"-debugcadence",
			#"-debugjitter",
			#"-debugrate",
			#"-debugmeasure
		]
		
		if is_complex:
			baudline_exec += ["-quadrature"]
		if flip_complex:
			baudline_exec += ["-flipcomplex"]
		if baseband_freq is not None and baseband_freq > 0:
			baudline_exec += ["-basefrequency", str(baseband_freq)]
		if decimation > 1:
			baudline_exec += ["-decimateby", str(decimation)]
		if scale != 1.0:
			baudline_exec += ["-scaleby", str(scale)]
		if overlap is not None and overlap > 0:
			baudline_exec += ["-overlap", str(overlap)]
			#"-slidesize"
		if slide_size is not None and slide_size > 0:
			baudline_exec += ["-slidesize", str(slide_size)]
		if fft_size is not None and fft_size > 0:
			baudline_exec += ["-fftsize", str(fft_size)]
		if jump_step is not None and jump_step > 0:
			baudline_exec += ["-jumpstep", str(jump_step)]
		if x_slip is not None and x_slip > 0:
			baudline_exec += ["-xslip", str(x_slip)]
		if memory is not None and memory > 0:
			baudline_exec += ["-memory", str(memory)]
		if peak_hold:
			baudline_exec += ["-peakhold"]
		
		for k in kwds.keys():
			arg = str(k).strip()
			if arg[0] != '-':
				arg = "-" + arg
			baudline_exec += [arg]
			val = kwds[k]
			if val is not None:
				val = str(val).strip()
				if val.find(' ') > -1 and len(val) > 1:
					if val[0] != '\"':
						val = "\"" + val
					if val[-1] != '\"':
						val += "\""
				baudline_exec += [val]

		if mode == 'fifo':
			baudline_exec += ["<", self.filename]
			#baudline_exec = ["cat", self.filename, "|"] + baudline_exec
		
			baudline_exec = [" ".join(baudline_exec)]
		
		self.p = None
		#res = 0
		try:
			#res = subprocess.call(gp_exec)
			print baudline_exec
			if mode == 'pipe':
				self.p = subprocess.Popen(baudline_exec, stdin=subprocess.PIPE)	# , stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=16384 or -1
			elif mode == 'fifo':
				self.p = subprocess.Popen(baudline_exec, shell=True)
			#self.p.communicate(input=)
			
			#self.p.stdin.write()
			#self.p.wait()
		#except KeyboardInterrupt:
		#	print "Caught CTRL+C"
		except Exception, e:
			print e
			raise
		#if self.p is not None and not self.p.returncode == 0:
		#	print "Failed to run subprocess (result: %d)" % (self.p.returncode)
		#if res != 0:
		#	print "Failed to run subprocess (result: %d)" % (res)
		
		if mode == 'pipe':
			print "==> Using FD:", self.p.stdin.fileno()
			self.file_sink = blocks.file_descriptor_sink(item_size, self.p.stdin.fileno())	# os.dup
		elif mode == 'fifo':
			self.file_sink = blocks.file_sink(item_size, self.filename)	# os.dup
			self.file_sink.set_unbuffered(not buffered)	# Flowgraph won't die if baudline exits
		
		self.connect(self, self.file_sink)
		
	def __del__(self):
		#os.unlink(tf.name)
		
		if self.p is not None:	# Won't work in FIFO mode as it blocks
			if self.kill_on_del:
				print "==> Killing baudline..."
				#self.p.kill()
				#self.p.terminate()
				os.kill(self.p.pid, signal.SIGTERM)
		
		if self.mode == 'fifo':
			try:
				print "==> Deleting:", self.filename
				os.unlink(self.filename)
				os.rmdir(self.tmpdir)
			except OSError, e:
				print "Failed to delete FIFO: %s" % e
				raise

def main():
	
	return 0

if __name__ == '__main__':
	main()

########NEW FILE########
__FILENAME__ = borip
#!/usr/bin/env python

"""
BorIP client for GNU Radio.
Enables access to a remote USRP via BorIP server through a LAN.
Uses gr_udp_source with modifications to enable BorIP packet support.
Hooks usrp.source_c so BorIP will automatically attempt to connect to a remote server if a local USRP is not present.
To specify a default server, add 'server=<server>' to the '[borip]' section of your ~/.gnuradio/config.conf (see other settings below).
More information regarding operational modes, seamless integration and settings: http://wiki.spench.net/wiki/gr-baz#borip
BorIP protocol specification: http://spench.net/r/BorIP
By Balint Seeber (http://spench.net/contact)
"""

# NOTES:
# Wait-for-OK will fail if socket fails, despite 'destroy' reconnect recovery
# GRC generated doesn't honour external config 'reconnect_attempts'

from __future__ import with_statement

import time, os, sys, threading, thread
from string import split, join
#from optparse import OptionParser
import socket
import threading
#import SocketServer

from gnuradio import gr, gru
import baz

if sys.modules.has_key('gnuradio.usrp'):
	usrp =  sys.modules['gnuradio.usrp']
else:
	from gnuradio import usrp

_default_port = 28888
_reconnect_interval = 5
_keepalive_interval = 5
_verbose = False
_reconnect_attempts = 0

_prefs = gr.prefs()
_default_server_address = _prefs.get_string('borip', 'server', '')
try:
	_reconnect_attempts = int(_prefs.get_string('borip', 'reconnect_attempts', str(_reconnect_attempts)))
except:
	pass
try:
	_reconnect_interval = int(_prefs.get_string('borip', 'reconnect_interval', str(_reconnect_interval)))
except:
	pass
try:
	_verbose = not ((_prefs.get_string('borip', 'verbose', str(_verbose))).strip().lower() in ['false', 'f', 'n', '0', ''])
except:
	pass
try:
	_default_port = int(_prefs.get_string('borip', 'default_port', str(_default_port)))
except:
	pass
try:
	_keepalive_interval = int(_prefs.get_string('borip', 'keepalive_interval', str(_keepalive_interval)))
except:
	pass

class keepalive_thread(threading.Thread):
	def __init__(self, rd, interval=_keepalive_interval, **kwds):
		threading.Thread.__init__ (self, **kwds)
		self.setDaemon(1)
		self.rd = rd
		self.interval = interval
	def start(self):
		self.active = True
		threading.Thread.start(self)
	def stop(self):
		self.active = False
	def run(self):
		while self.active:
			time.sleep(self.interval)
			with self.rd._socket_lock:
				if self.active == False:
					break
				try:
					(cmd, res, data) = self.rd._send("PING")
					#print "Keepalive: %s -> %s" % (cmd, res)	# Ignore response
				except socket.error, (e, msg):
					self.active = False
					break
		#print "Keepalive thread exiting"

class remote_usrp(gr.hier_block2):
	"""
	Remote USRP via BorIP
	"""
	def __init__(self, address, which=0, decim_rate=0, packet_size=0, reconnect_attempts=None):
		"""
		Remote USRP. Remember to call 'create'
		"""
		gr.hier_block2.__init__(self, "remote_usrp",
			gr.io_signature(0, 0, 0),
			gr.io_signature(1, 1, gr.sizeof_gr_complex))
		
		self._decim_rate = decim_rate
		self._address = address
		self._which = which
		
		self.s = None
		self._adc_freq = int(64e6)
		self._buffer = ""
		self._gain_range = (0, 1)
		#self._tune_result = None
		self._name = "(Remote device)"
		self._gain_step = 0
		self._packet_size = packet_size
		self._created = False
		self._listen_only = False
		self._socket_lock = threading.RLock()			# Re-entrant!
		self._keepalive_thread = None
		if reconnect_attempts is not None:
			self._reconnect_attempts = reconnect_attempts
		else:
			self._reconnect_attempts = _reconnect_attempts
		self._reconnect_attempts_to_go = self._reconnect_attempts
		
		self.udp_source = None
		self.vec2stream = None
		self.ishort2complex = None
		
		self._last_address = None
		self._last_which = None
		self._last_subdev_spec = None
		
		self._reset_last_params()
	
	def _reset_last_params(self):
		self._last_freq = None
		self._last_gain = None
		self._last_antenna = None
	
	def __del__(self):
		self.destroy()
	
	def _send_raw(self, command, data=None):
		if self._listen_only:
			return False
		if data is not None:
			command += " " + str(data)
		with self._socket_lock:
			if self.s is None:
				return False
			try:
				command = command.strip()
				if _verbose:
					print "-> " + command
				self.s.send(command + "\n")
			except socket.error, (e, msg):
				#if (e != 32): # Broken pipe
				if self.destroy(e) is not True:
					raise socket.error, (e, msg)
			return True
	
	def _send(self, command, data=None):
		with self._socket_lock:
			if self._send_raw(command, data) == False:
				return (command, None, None)
			return self._recv()
	
	def _send_and_wait_for_ok(self, command, data=None):
		(cmd, res, data) = self._send(command, data)
		if (cmd != command):
			raise Exception, "Receive command %s != %s" % (cmd, command)
		if res != "OK":
			raise Exception, "Expecting OK, received %s" % (res)
	
	def _recv(self):
		with self._socket_lock:
			if self.s is None:
				return (command, None, None)
			while True:
				try:
					response = self.s.recv(1024)
				except socket.error, (e, msg):
					#if e != 104:    # Connection reset by peer
					#	pass
					if self.destroy(e) is not True:
						raise socket.error, (e, msg)
					else:
						return (None, None, None)
				
				#if len(response) == 0:
				#	#return (None, None, None)
				#	self.destory()
				#	raise Exception, "Disconnected"
				
				self._buffer += response
				lines = self._buffer.splitlines(True)
				
				#for line in lines:
				if len(lines) > 0:	# Should only be one line at a time
					line = lines[0]
					
					if line[-1] != '\n':
						self._buffer = line
						continue
					
					line = line.strip()
					
					if _verbose:
						print "<- " + line
					
					cmd = line
					res = None
					data = None
					
					idx = cmd.find(" ")
					if idx > -1:
						res = (cmd[idx + 1:]).strip()
						cmd = (cmd[0:idx]).upper()
						
						if cmd != "DEVICE":
							idx = res.find(" ")
							if idx > -1:
								data = (res[idx + 1:]).strip()
								res = (res[0:idx])
							res = res.upper()
					elif cmd.upper() == "BUSY":
						pass
					else:
						raise Exception, "Response without result: " + line
					
					if res == "FAIL":
						#raise Exception, "Failure: " + line
						pass
					elif res == "DEVICE":
						#raise Exception, "Need to create device first"
						pass
					elif cmd == "DEVICE":
						if res == "-":
							if data is not None:
								raise Exception, "Failed to create device: \"%s\"" % data
						else:
							parts = res.split("|")
							try:
								if parts[0] == "":
									self._name = "(No name)"
								else:
									self._name = parts[0]
								self._gain_range = (float(parts[1]), float(parts[2]))
								self._gain_step = float(parts[3])
								self._adc_freq = int(float(parts[4]))
								self._packet_size = int(parts[5]) * 2 * 2
								# FIXME: Antennas
							except:
								raise Exception, "Malformed device response: " + res
					elif cmd == "RATE":
						pass
					elif cmd == "GAIN":
						pass
					elif cmd == "ANTENNA":
						pass
					elif cmd == "FREQ":
						if res == "OK":
							parts = data.split(" ")
							data = usrp.usrp_tune_result(baseband=float(parts[1]), dxc=float(parts[3]), residual=0)
						pass
					#elif cmd == "BUSY":
					#	raise "Client is busy"
					#elif cmd == "GO":
					#	pass
					#else:
					#	print "Unhandled response: " + line
					
					self._buffer = "".join(lines[1:])
					
					return (cmd, res, data)
				else:
					if self.destroy(32) is not True:	# Broken pipe
						raise Exception, "No data received (server connection was closed)"
						#pass	# Will signal
					else:
						return (None, None, None)
	
	def destroy(self, error=None):
		if self.s is not None:
			self.s.close()
			self.s = None
		
		self._buffer = ""
		self._created = False
		
		if self._keepalive_thread is not None:
			self._keepalive_thread.stop()
			self._keepalive_thread = None
		
		if error is not None:
			#print "Destroy: %s" % (error)
			assert self._listen_only == False
			while True:
				if (self._reconnect_attempts_to_go > 0) or (self._reconnect_attempts_to_go < 0):
					if (self._reconnect_attempts_to_go > 0):
						print "Reconnect attempts remaining: %s" % (self._reconnect_attempts_to_go)
					
					self._reconnect_attempts_to_go = self._reconnect_attempts_to_go - 1
					
					try:
						self.create(address=self._last_address, which=self._last_which, subdev_spec=self._last_subdev_spec, reconnect=True)
						return True
					except:
						try:
							time.sleep(_reconnect_interval)
							continue
						except KeyboardInterrupt:
							pass	# Fall through to EOS
				#else:
				self.udp_source.signal_eos()
				return False
		
		return None
	
	def create(self, address=None, decim_rate=0, which=None, subdev_spec="", udp_port=None, sample_rate=None, packet_size=0, reconnect=False):
		if address is None:
			address = self._address
		if (address is None) or (isinstance(address, str) and address == ""):
			address = _default_server_address
		if address == "":
			raise Exception, "Server address required"
		
		if decim_rate == 0:
			decim_rate = self._decim_rate
		if decim_rate == 0:
			#raise Exception, "Decimation rate required"
			decim_rate = 256
		
		if which is None:
			which = self._which
		
		self._last_address = address
		self._last_which = which
		self._last_subdev_spec = subdev_spec
		
		if reconnect is False:
			self._reset_last_params()
		
		self.destroy()
		
		self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		
		#print "Connecting to: " + str(address)
		
		port = _default_port
		if isinstance(address, str):
			parts = address.split(":")
			if len(parts) > 1:
				port = int(parts[1])
			address = (parts[0], port)
		
		if udp_port is None:
			udp_port = port
		
		if address[0] == "-":
			self._listen_only = True
			if (self._packet_size == 0) or (packet_size > 0):
				if packet_size == 0:
					packet_size = 4096 * 2 * 2	# FCD testing: 9216
				self._packet_size = packet_size
			print "BorIP client only listening on port %d (MTU: %d)" % (udp_port, self._packet_size)
		else:
			self._listen_only = False
			
			reconnect_attempts = self._reconnect_attempts
			
			while True:
				try:
					self.s.connect(address)
					#print "BorIP client connected to: %s" % (str(address))
				except socket.error, (e, msg):
					if (e == 111) and (reconnect is False) and ((self._reconnect_attempts < 0) or ((self._reconnect_attempts > 0) and (reconnect_attempts > 0))):	# Connection refused
						error_str = "Connection refused, trying again"
						if (self._reconnect_attempts > 0):
							error_str = error_str + (" (%s attempts remaining)" % (reconnect_attempts))
						print error_str
						reconnect_attempts = reconnect_attempts - 1
						
						try:
							time.sleep(_reconnect_interval)
							continue
						except KeyboardInterrupt:
							raise socket.error, (e, msg)
							
					print "Failed to connect to server: %s %s" % (e, msg)
					raise socket.error, (e, msg)
				break
			
			self._reconnect_attempts_to_go = self._reconnect_attempts
			
			(cmd, res, data) = self._recv()
			if cmd != "DEVICE":
				if cmd == "BUSY":
					raise Exception, "Server is busy"
				else:
					raise Exception, "Unexpected greeting: " + cmd
				
			#print "Server ready"
			
			if (res == "-") or (which is not None):
				hint = str(which)
				if ((subdev_spec is not None) and (not isinstance(subdev_spec, str))) or (isinstance(subdev_spec, str) and (subdev_spec != "")):
					if isinstance(subdev_spec, str) == False:
						if isinstance(subdev_spec, tuple):
							if len(subdev_spec) > 1:
								subdev_spec = "%s:%s" % (subdev_spec[0], subdev_spec[1])
							else:
								subdev_spec = str(subdev_spec[0])
						else:
							raise Exception, "Unknown sub-device specification: " + str(subdev_spec)
					hint += " " + subdev_spec
				self._send("DEVICE", hint)
			
			self._created = True
			#print "Created remote device: %s" % (self._name)
			
			#self._send("HEADER", "OFF")	# Enhanced udp_source
			
			if sample_rate is not None:
				self._send_and_wait_for_ok("RATE", sample_rate)
			else:
				#sample_rate = self.adc_freq() / decim_rate
				if self.set_decim_rate(decim_rate) == False:
					raise Exception, "Invalid decimation: %s (sample rate: %s)" % (decim_rate, sample_rate)
		
		if self.udp_source is None:
			assert self.vec2stream is None and self.ishort2complex is None
			udp_interface = "0.0.0.0"	# MAGIC
			self.udp_source = baz.udp_source(gr.sizeof_short * 2, udp_interface, udp_port, self._packet_size, True, True, True)
			#print "--> UDP Source listening on port:", udp_port, "interface:", udp_interface, "MTU:", self._packet_size
			self.vec2stream = gr.vector_to_stream(gr.sizeof_short * 1, 2)
			self.ishort2complex = gr.interleaved_short_to_complex()
		
			self.connect(self.udp_source, self.vec2stream, self.ishort2complex, self)
		else:
			assert self.vec2stream is not None and self.ishort2complex is not None
		
		if self._listen_only == False:
			if self._last_antenna is not None:
				self.select_rx_antenna(self._last_antenna)
			if self._last_freq is not None:
				self.set_freq(self._last_freq)
			if self._last_gain is not None:
				self.set_gain(self._last_gain)
			
			self._send_and_wait_for_ok("GO")	# Will STOP on disconnect
			
			self._keepalive_thread = keepalive_thread(self)
			self._keepalive_thread.start()
	
	#def __repr__(self):
	#	pass
	
	def set_freq(self, freq):
		self._last_freq = freq
		(cmd, res, data) = self._send("FREQ", freq)
		return data	# usrp.usrp_tune_result
	
	def __str__(self):
		return self.name()
	
	def tune(self, unit, subdev, freq):
		return self.set_freq(freq)
	
	def adc_freq(self):
		return self._adc_freq
	
	def decim_rate(self):
		return self._decim_rate
	
	def set_mux(self, mux):
		pass
	
	def pick_subdev(self, opts):
		return ""	# subdev_spec
	
	def determine_rx_mux_value(self, subdev_spec, subdev_spec_=None):
		return 0	# Passed to set_mux
	
	def selected_subdev(self, subdev_spec):
		if (self._created == False):
			self.create(subdev_spec=subdev_spec)
		return self
	
	def set_decim_rate(self, decim_rate):
		if self.s is None:
			self._decim_rate = decim_rate
			return
		sample_rate = self.adc_freq() / decim_rate
		(cmd, res, data) = self._send("RATE", sample_rate)
		if (res == "OK"):
			self._decim_rate = decim_rate
			return True
		return False

	def db(self, side_idx, subdev_idx):
		return self
	
	def converter_rate(self):
		return self.adc_freq()
	
	## Daughter-board #################
	
	def dbid(self):
		return 0
	
	## Sub-device #####################

	def gain_range(self):
		return self._gain_range
	
	def gain_min(self):
		return self._gain_range[0]
	
	def gain_max(self):
		return self._gain_range[1]
	
	def set_gain(self, gain):
		self._last_gain = gain
		(cmd, res, data) = self._send("GAIN", gain)
		return (res == "OK")
	
	def select_rx_antenna(self, antenna):
		self._last_antenna = antenna
		(cmd, res, data) = self._send("ANTENNA", antenna)
		return (res == "OK")

	def name(self):
		return self._name
	
	def side_and_name(self):
		return self.name()

###########################################################

#if ('usrp' in locals()):
if hasattr(usrp, '_orig_source_c') == False:
	usrp._orig_source_c = usrp.source_c
	
	def _borip_source_c(which=0, decim_rate=256, nchan=None):
		#global _default_server_address
		if _default_server_address == "":
			return usrp._orig_source_c(which=which, decim_rate=decim_rate)
		try:
			return usrp._orig_source_c(which=which, decim_rate=decim_rate)
		except:
			return remote_usrp(None, which, decim_rate)
	
	usrp.source_c = _borip_source_c
	
	###################
	
	#if hasattr(usrp, '_orig_pick_subdev') == False:
	#	usrp._orig_pick_subdev = usrp.pick_subdev
	#	
	#	def _borip_pick_subdev(u, opts):
	#		if isinstance(u, remote_usrp):
	#			return ""	# subdev_spec
	#		return usrp._orig_pick_subdev(u, opts)
	#	
	#	usrp.pick_subdev = _borip_pick_subdev
	
	###################
	
	#if hasattr(usrp, '_orig_determine_rx_mux_value') == False:
	#	usrp._orig_determine_rx_mux_value = usrp.determine_rx_mux_value
	#	
	#	def _borip_determine_rx_mux_value(u, subdev_spec):
	#		if isinstance(u, remote_usrp):
	#			return 0	# Passed to set_mux
	#		return usrp._orig_determine_rx_mux_value(u, subdev_spec)
	#	
	#	usrp.determine_rx_mux_value = _borip_determine_rx_mux_value
	
	###################
	
	#if hasattr(usrp, '_orig_selected_subdev') == False:
	#	usrp._orig_selected_subdev = usrp.selected_subdev
	#	
	#	def _borip_selected_subdev(u, subdev_spec):
	#		if isinstance(u, remote_usrp):
	#			if (u._created == False):
	#				u.create(subdev_spec=subdev_spec)
	#			return u
	#		return usrp._orig_selected_subdev(u, subdev_spec)
	#	
	#	usrp.selected_subdev = _borip_selected_subdev

########NEW FILE########
__FILENAME__ = borip_server
#!/usr/bin/env python

"""
BorIP Server
By Balint Seeber
Part of gr-baz (http://wiki.spench.net/wiki/gr-baz)
Protocol specification: http://wiki.spench.net/wiki/BorIP
"""

from __future__ import with_statement

import time, os, sys, threading, thread, traceback  # , gc
from string import split, join
from optparse import OptionParser
import socket
import threading
import SocketServer

from gnuradio import gr
import baz

class server(gr.hier_block2):   # Stand-alone block
    def __init__(self, size=gr.sizeof_gr_complex, mul=1, server=False, parent=None, verbose=False):    # 'parent' should be flowgraph in which this is the 'BorIP Sink' block
        gr.hier_block2.__init__(self, "borip_server",
            gr.io_signature(1, 1, size),
            gr.io_signature(0, 0, 0))
        
        src = self
        udp_type_size = gr.sizeof_short
        if size == gr.sizeof_gr_complex:
            if mul != 1:
                if verbose:
                    print "**> Applying constant multiplication:", mul
                self.mul = gr.multiply_const_cc(mul)
                self.connect(src, self.mul)
                src = self.mul
            
            self.c2is = gr.complex_to_interleaved_short()
            self.connect(src, self.c2is)
            src = self.c2is
        elif (size == (2 * gr.sizeof_short)):   # Short * 2 (vlen = 2)
            udp_type_size = gr.sizeof_short * 2
        elif not (size == gr.sizeof_short):     # not IShort
            raise Exception, "Invalid input size (must be gr_complex or interleaved short)"
        
        self.sink = baz.udp_sink(udp_type_size, None, 28888, 1024, False, True)
        
        self.connect(src, self.sink)
        
        self.verbose = verbose
        
        self.parent = None
        if server:
            self.parent = parent
            self.server = borip_server(block=self)
            self.server.options.verbose = verbose
            self.server.options.fixed_flowgraph = True
            self.server.options.lock = True
            self.server.start()
    
    def set_status_msgq(self, msgq):
        self.sink.set_status_msgq(msgq)

class ServerWrapper(gr.top_block):  # Wrapper for hier_block with output pad
    def __init__(self, flowgraph, options):
        gr.top_block.__init__(self, "ServerWrapper for " + flowgraph.name())
        
        self.flowgraph = flowgraph
        self.options = options
        
        mul = getattr(flowgraph, 'rescale', 1.0)
        if hasattr(mul, '__call__'):
            mul = mul()
            
        self.server = server(size=self.flowgraph.output_signature().sizeof_stream_item(0), mul=mul, server=False, verbose=options.verbose)
        
        self.connect((self.flowgraph, 0), (self.server, 0))
        
        self.sink = self.server.sink
        
        if hasattr(self.flowgraph, 'source'):
            if options.verbose:
                print "**> Using internal source:", self.flowgraph.source
            self.source = self.flowgraph.source
        
        if hasattr(self.flowgraph, 'status') and hasattr(self.flowgraph.status, 'msgq'):
            #if isinstance(self.flowgraph.status, message_callback.message_callback):   # Doesn't work, need to 'import baz' and prepend 'baz.'
                if options.verbose:
                    print "**> Using status msgq from:", self.flowgraph.status
                
                if hasattr(self.flowgraph.status.msgq, '__call__'):
                    msgq = self.flowgraph.status.msgq()
                else:
                    msgq = self.flowgraph.status.msgq
                    
                self.server.sink.set_status_msgq(msgq)

def _default_device_hint_mapper(hint):
    if hint is None or len(hint) == 0 or hint == "-":
        return "usrp_uhd"
    parts = hint.split(" ")
    try:
        idx = int(parts[0])
        return "usrp_legacy"
    except:
        pass
    try:
        kv = parts[0].index('=')    # key=value
        parts = hint.split(",")		# Assumes no use of "
        args = []
        subdev = None
        for part in parts:
            part = part.strip()
            if len(part) == 1 and part[0].lower() >= 'a' and part[0].lower() <= 'z':
                subdev = part + ":0"
                continue
            idx = part.find(':')
            if idx > 0 and part[0].lower() >= 'a' and part[0].lower() <= 'z':	# "?:"
                subdev = part
                continue
            args += [part]
        combined = ["addr=\"" + ",".join(args) + "\""]
        if subdev is not None:
            combined += ["subdev=\"" + subdev + "\""]
        return {'module': "usrp_uhd", 'args': combined}
    except:
        pass
    return parts[0].upper() # FCD, RTL

_device_hint_mapper = _default_device_hint_mapper

try:
    import borip_server_devmap
    _device_hint_mapper = borip_server_devmap.device_hint_mapper
except:
    pass

class TuneResult():
    def __init__(self, target_rf_freq=0.0, actual_rf_freq=0.0, target_dsp_freq=0.0, actual_dsp_freq=0.0):
        self.target_rf_freq = target_rf_freq
        self.actual_rf_freq = actual_rf_freq
        self.target_dsp_freq = target_dsp_freq
        self.actual_dsp_freq = actual_dsp_freq
    def __str__(self):
        return str(self.target_rf_freq) + ": " + str(self.actual_rf_freq) + " + " + str(self.target_dsp_freq) + " (" + str(self.actual_dsp_freq) + ")"
    def duck_copy(self, src):
        try:
            elems = filter(lambda x: (x[0] != "_") and hasattr(self, x), dir(src))
            map(lambda x: setattr(self, x, getattr(src, x)), elems)
            #for v in elems:
            #    print v
            #    setattr(self, v, getattr(src, v))
            return len(elems) > 0
        except Exception, e:
            print "~~> Failed to duck copy tune result:", src
            traceback.print_exc()

class GainRange():
    def __init__(self, start=0.0, stop=1.0, step=1.0):
        self.start = start
        self.stop = stop
        self.step = step

class Device():
    def __init__(self):
        self._running = False
        self._frequency = 0.0
        self._frequency_requested = 0.0
        self._gain = 0.0
        self._sample_rate = 0.0
        self._antenna = None
        self._last_error = None
    def is_running(self):
        return self._running
    def last_error(self):
        return self._last_error
    def start(self):
        if self.is_running():
            return True
        self._running = True
        return True
    def stop(self):
        if self.is_running() == False:
            return True
        self._running = False
        return True
    def open(self):
        self._antenna = self.antennas()[0]
        return True
    def close(self):
        if self.is_running():
            self.stop()
    def name(self):
        return "(no name)"
    def serial(self):
        return self.name()
    def gain_range(self):
        return GainRange()
    def master_clock(self):
        return 0
    def samples_per_packet(self):
        return 1024
    def antennas(self):
        return ["(Default)"]
    def gain(self, gain=None):
        if gain is not None:
            self._gain = gain
            return True
        return self._gain
    def sample_rate(self, rate=None):
        if rate is not None:
            if rate <= 0:
                return False
            self._sample_rate = rate
            return True
        return self._sample_rate
    def freq(self, freq=None, requested=None):
        if freq is not None:
            if freq > 0:
                if requested is not None and requested > 0:
                    self._frequency_requested = requested
                else:
                    self._frequency_requested = freq
                self._frequency = freq
                return True
            else:
                return False
        return self._frequency
    def was_tune_successful(self):
        return 0
    def last_tune_result(self):
        return TuneResult(self._frequency_requested, self.freq())
    def antenna(self, antenna=None):
        if antenna is not None:
            if type(antenna) == str:
                if len(antenna) == 0:
                    return False
                self._antenna = antenna
            elif type(antenna) == int:
                num = len(self.antennas())
                if antenna < 0 or antenna >= num:
                    return False
                self._antenna = self.antennas()[antenna]
            else:
                return False
            return True
        return self._antenna
    #def set_antenna(self, antenna):
    #    return True

class NetworkTransport():
    def __init__(self, default_port=28888):
        self._header = True
        self._default_port = default_port
        self._destination = ("127.0.0.1", default_port)
        self._payload_size = 0
    def destination(self, dest=None):
        if dest:
            if type(dest) == str:
                idx = dest.find(":")
                if idx > -1:
                    try:
                        port = int(dest[idx+1:])
                    except:
                        return False
                    dest = dest[0:idx].strip()
                    if len(dest) == 0 or port <= 0:
                        return False
                    self._destination = (dest, port)
                else:
                    self._destination = (dest, self._default_port)
            elif type(dest) == tuple:
                self._destination = dest
            else:
                return False
            return True
        return self._destination
    def header(self, enable=None):
        if enable is not None:
            self._header = enable
        return self._header
    def payload_size(self,size=None):
        if size is not None:
            self._payload_size = size
        return self._payload_size

def _delete_blocks(tb, done=[], verbose=False):
    tb.disconnect_all()
    for i in dir(tb):
        #if i == "_tb": # Must delete this too!
        #    continue
        obj = getattr(tb, i)
        if str(obj) in done:
            continue
        delete = False
        if issubclass(obj.__class__, gr.hier_block2):
            if verbose:
                print ">>> Descending:", i
            _delete_blocks(obj, done + [str(obj)])   # Prevent self-referential loops
            delete = True
        if delete or '__swig_destroy__' in dir(obj):
            done += [str(obj)]
            if verbose:
                print ">>> Deleting:", i
            exec "del tb." + i
    #while len(done) > 0:    # Necessary
    #    del done[0]

class GnuRadioDevice(Device, NetworkTransport):
    def __init__(self, flowgraph, options, sink=None, fixed_flowgraph=False):
        Device.__init__(self)
        NetworkTransport.__init__(self, options.port)
        self.flowgraph = flowgraph
        self.options = options
        self.sink = sink
        self.no_delete = fixed_flowgraph
        self.no_stop = fixed_flowgraph
        if fixed_flowgraph:
            self._running = True
        self._last_tune_result = None
    def open(self): # Can raise exceptions
        #try:
        if self.sink is None:
            if hasattr(self.flowgraph, 'sink') == False:
                print "~~> Failed to find 'sink' block in flowgraph"
                return False
            self.sink = self.flowgraph.sink
        payload_size = self.samples_per_packet() * 2 * 2    # short I/Q
        max_payload_size = (65536 - 29) # Max UDP payload
        max_payload_size -= (max_payload_size % 512)
        if payload_size > max_payload_size:
            print "!!> Restricting calculated payload size:", payload_size, "to maximum:", max_payload_size
            payload_size = max_payload_size
        self.payload_size(payload_size)
        return Device.open(self)
        #except Exception, e:
        #    print "Exception while initialising GNU Radio wrapper:", str(e)
        #return False
    def close(self):
        Device.close(self)
        if self.no_delete == False:
            _delete_blocks(self.flowgraph, verbose=self.options.debug)
    # Helpers
    def _get_helper(self, names, fallback=None, _targets=[]):
        if isinstance(names, str):
            names = [names]
        targets = _targets + ["", ".source", ".flowgraph"]  # Second 'flowgraph' for 'ServerWrapper'
        target = None
        name = None
        for n in names:
            for t in targets:
                #parts = t.split('.')
                #accum = []
                #next = False
                #for part in parts:
                #    if hasattr(eval("self.flowgraph" + ".".join(accum)), part) == False:
                #        next = True
                #        break
                #    accum += [part]
                #if next:
                #    continue
                try:
                    if hasattr(eval("self.flowgraph" + t), n) == False:
                        #print "    Not found:", t, "in:", n
                        continue
                except AttributeError:
                    #print "    AttributeError:", t, "in:", n
                    continue
                #print "    Found:", t, "in:", n
                target = t
                name = n
                break
            if target is not None:
                #print "    Using:", t, "in:", n
                break
        if target is None:
            if self.options.debug:
                print "##> Helper fallback:", names, fallback
            return fallback
        helper_name = "self.flowgraph" + target + "." + name
        helper = eval(helper_name)
        if self.options.debug:
            print "##> Helper found:", helper_name, helper
        if hasattr(helper, '__call__'):
            return helper
        return lambda: helper
    # Device
    def start(self):
        if self.is_running():
            return True
        try:
            self.flowgraph.start()
        except Exception, e:
            self._last_error = str(e)
            return False
        return Device.start(self)
    def stop(self):
        if self.is_running() == False:
            return True
        if self.no_stop == False:
            try:
                self.flowgraph.stop()
                self.flowgraph.wait()
            except Exception, e:
                self._last_error = str(e)
                return False
        return Device.stop(self)
    def name(self): # Raises
        try:
            fn = self._get_helper('source_name')
            if fn:
                return fn()
            return self._get_helper('name', self.flowgraph.name, [".source"])()
        except Exception, e:
            self._last_error = str(e)
            raise Exception, e
    def serial(self): # Raises
        try:
            return self._get_helper(['serial', 'serial_number'], lambda: Device.serial(self))()
        except Exception, e:
            self._last_error = str(e)
            raise Exception, e
    def gain_range(self): # Raises
        try:
            fn = self._get_helper(['gain_range', 'get_gain_range'])
            if fn is None:
                return Device.gain_range(self)
            _gr = fn()
            if isinstance(_gr, GainRange):
                return _gr
            try:
                gr = GainRange(_gr[0], _gr[1])
                if len(_gr) > 2:
				    gr.step = _gr[2]
                return gr
            except:
                pass
            try:
                gr = GainRange(_gr.start(), _gr.stop())
                if hasattr(_gr, 'step'):
                    gr.step = _gr.step()
                return gr
            except:
                pass
            raise Exception, "Unknown type returned from gain_range"
        except Exception, e:
            self._last_error = str(e)
            #return Device.gain_range(self)
            raise Exception, e
    def master_clock(self): # Raises
        return self._get_helper(['master_clock', 'get_clock_rate'], lambda: Device.master_clock(self))()
    def samples_per_packet(self):
        return self._get_helper(['samples_per_packet', 'recv_samples_per_packet'], lambda: Device.samples_per_packet(self))()
    def antennas(self):
        return self._get_helper(['antennas', 'get_antennas'], lambda: Device.antennas(self))()
    def gain(self, gain=None):
        if gain is not None:
            fn = self._get_helper('set_gain')
            if fn:
                res = fn(gain)
                if res is not None and res == False:
                    return False
            return Device.gain(self, gain)
        return self._get_helper(['gain', 'get_gain'], lambda: Device.gain(self))()
    def sample_rate(self, rate=None):
        if rate is not None:
            fn = self._get_helper(['set_sample_rate', 'set_samp_rate'])
            if fn:
                res = fn(rate)
                if res is not None and res == False:
                    return False
            return Device.sample_rate(self, rate)
        return self._get_helper(['sample_rate', 'samp_rate', 'get_sample_rate', 'get_samp_rate'], lambda: Device.sample_rate(self))()
    def freq(self, freq=None):
        if freq is not None:
            fn = self._get_helper(['set_freq', 'set_frequency', 'set_center_freq'])
            res = None
            if fn:
                res = fn(freq)
                if res is not None and res == False:
                    return False
                self._last_tune_result = None
            #if type(res) is int or type(res) is float:
            tuned = freq
            if res is not None and type(res) is not bool:
                try:
                    if self.options.debug:
                        print "##> Frequency set returned:", res
                    if type(res) is list or type(res) is tuple:
                        self._last_tune_result = TuneResult(freq, tuned)   # Should be same as res[0]
                        try:
                            #self._last_tune_result.target_rf_freq = res[0]
                            self._last_tune_result.actual_rf_freq = res[1]
                            self._last_tune_result.target_dsp_freq = res[2]
                            self._last_tune_result.actual_dsp_freq = res[3]
                            if self.options.debug:
                                print "##> Stored tune result:", self._last_tune_result
                        except Exception, e:
                            if self.options.debug:
                                print "##> Error while storing tune result:", e
                        tuned = self._last_tune_result.actual_rf_freq + self._last_tune_result.actual_dsp_freq
                    else:
                        temp_tune_result = TuneResult(freq, tuned)
                        if temp_tune_result.duck_copy(res):
                            if self.options.debug:
                                print "##> Duck copied tune result"
                            self._last_tune_result = temp_tune_result
                        else:
                            if self.options.debug:
                                print "##> Casting tune result to float"
                            tuned = float(res)
                            self._last_tune_result = None   # Will be created in call to Device
                except Exception, e:
                    if self.options.verbose:
                        print "##> Unknown exception while using response from frequency set:", str(res), "-", str(e)
            return Device.freq(self, tuned, freq)
        return self._get_helper(['freq', 'frequency', 'get_center_freq'], lambda: Device.freq(self))()
    def was_tune_successful(self):
        fn = self._get_helper(['was_tune_successful', 'was_tuning_successful'])
        if fn:
            return fn()
        tolerance = None
        fn = self._get_helper(['tune_tolerance', 'tuning_tolerance'])
        if fn:
            tolerance = fn()
        if tolerance is not None:
            tr = self.last_tune_result()
            diff = self.freq() - (tr.actual_rf_freq + tr.actual_dsp_freq)   # self.actual_dsp_freq
            if abs(diff) > tolerance:
                print "    Difference", diff, ">", tolerance, "for", tr
                if diff > 0:
                    return 1
                else:
                    return -1
        return Device.was_tune_successful(self)
    def last_tune_result(self):
        fn = self._get_helper(['last_tune_result'])
        if fn:
            return fn()
        if self._last_tune_result is not None:
            return self._last_tune_result
        return Device.last_tune_result(self)
    def antenna(self, antenna=None):
        if antenna is not None:
            fn = self._get_helper('set_antenna')
            if fn:
                if type(antenna) == int:
                    num = len(self.antennas())
                    if antenna < 0 or antenna >= num:
                        return False
                    antenna = self.antennas()[antenna]
                if len(antenna) == 0:
                    return False
                try:
                    res = fn(antenna)
                    if res is not None and res == False:
                        return False
                except:
                    return False
            return Device.antenna(self, antenna)
        return self._get_helper(['antenna', 'get_antenna'], lambda: Device.antenna(self))()
    # Network Transport
    def destination(self, dest=None):
        if dest is not None:
            prev = self._destination
            if NetworkTransport.destination(self, dest) == False:
                return False
            try:
                #print "--> Connecting UDP Sink:", self._destination[0], self._destination[1]
                self.sink.connect(self._destination[0], self._destination[1])
            except Exception, e:
                NetworkTransport.destination(self, prev)
                self._last_error = str(e)
                return False
            return True
        return NetworkTransport.destination(self)
    def header(self, enable=None):
        if enable is not None:
            self.sink.set_borip(enable)
        return NetworkTransport.header(self, enable)
    def payload_size(self,size=None):
        if size is not None:
            self.sink.set_payload_size(size)
        return NetworkTransport.payload_size(self, size)

def _format_error(error, pad=True):
    if error is None or len(error) == 0:
        return ""
    error = error.strip()
    error.replace("\\", "\\\\")
    error.replace("\r", "\\r")
    error.replace("\n", "\\n")
    if pad:
        error = " " + error
    return error

def _format_device(device, transport):
    if device is None or transport is None:
        return "-"
    return "%s|%f|%f|%f|%f|%d|%s|%s" % (
        device.name(),
        device.gain_range().start,
        device.gain_range().stop,
        device.gain_range().step,
        device.master_clock(),
        #device.samples_per_packet(),
        (transport.payload_size()/2/2),
        ",".join(device.antennas()),
        device.serial()
    )

def _create_device(hint, options):
    if options.verbose:
        print "--> Creating device with hint:", hint
    id = None
    if (options.default is not None) and (hint is None or len(hint) == 0 or hint == "-"):
        id = options.default
    if (id is None) or (len(id) == 0):
        id = _device_hint_mapper(hint)
    if options.debug:
        print "--> ID:", id
    if id is None or len(id) == 0:
        #return None
        raise Exception, "Empty ID"
    
    if isinstance(id, dict):
        args = []
        for arg in id['args']:
            check = _remove_quoted(arg)
            if check.count("(") != check.count(")"):
                continue
            args += [arg]
        id = id['module']   # Must come last
    else:
        parts = hint.split(" ")
        if len(parts) > 0 and parts[0].lower() == id.lower():
            parts = parts[1:]
        if len(parts) > 0:
            if options.debug:
                print "--> Hint parts:", parts
        args = []
        append = False
        accum = ""
        for part in parts:
            quote_list = _find_quotes(part)
            
            if (len(quote_list) % 2) != 0:  # Doesn't handle "a""b" as separate args
                if append == False:
                    append = True
                    accum = part
                    continue
                else:
                    part = accum + part
                    accum = ""
                    append = False
                    quote_list = _find_quotes(part)
            elif append == True:
                accum += part
                continue
            
            quotes = True
            key = None
            value = part
            
            idx = part.find("=")
            if idx > -1 and (len(quote_list) == 0 or idx < quote_list[0]):
                key = part[0:idx]
                value = part[idx + 1:]
            
            if len(quote_list) >= 2 and quote_list[0] == 0 and quote_list[-1] == (len(part) - 1):
                quotes = False
            else:
                if quotes:
                    try:
                        dummy = float(value)
                        quotes = False
                    except:
                        pass
                
                if quotes:
                    try:
                        dummy = int(value, 16)
                        quotes = False
                        dummy = value.lower()
                        if len(dummy) < 2 or dummy[0:2] != "0x":
                            value = "0x" + value
                    except:
                        pass
            
            arg = ""
            if key:
                arg = key + "="
            
            if quotes:
                value = value.replace("\"", "\\\"")
                arg += "\"" + value + "\""
            else:
                arg += value
            
            check = _remove_quoted(arg)
            if check.count("(") != check.count(")"):
                continue
            
            args += [arg]
    
    args_str = ",".join(args)
    if len(args_str) > 0:
        if options.debug:
            print "--> Args:", args_str
    
    if sys.modules.has_key("borip_" + id):
        if options.no_reload == False:
            try:
                #exec "reload(borip_" + id + ")"
                module = sys.modules["borip_" + id]
                print "--> Reloading:", module
                reload(module)
            except Exception, e:
                print "~~> Failed to reload:", str(e)
                #return None
                raise Exception, e
        
    #    try:
    #        device = module["borip_" + id + "(" + args_str + ")")
    #    except Exception, e:
    #        print "~~> Failed to create from module:", str(e)
    #        #return None
    #        raise Exception, e
    #else:
    try:
        exec "import borip_" + id
    except Exception, e:
        print "~~> Failed to import:", str(e)
        traceback.print_exc()
        #return None
        raise Exception, e
    
    try:
        device = eval("borip_" + id + ".borip_" + id + "(" + args_str + ")")
    except Exception, e:
        print "~~> Failed to create:", str(e)
        traceback.print_exc()
        #return None
        raise Exception, e
    
    device = _wrap_device(device, options)
    print "--> Created device:", device
    return device

def _wrap_device(device, options):
    #parents = device.__class__.__bases__
    #if Device not in parents:
    if issubclass(device.__class__, Device) == False:
        try:
            if isinstance(device, server) and device.parent is not None:
                print "--> Using GnuRadioDevice wrapper for parent", device.parent, "of", device
                device = GnuRadioDevice(device.parent, options, device.sink, options.fixed_flowgraph)
            #if gr.top_block in parents:
            elif issubclass(device.__class__, gr.top_block):
                print "--> Using GnuRadioDevice wrapper for", device
                device = GnuRadioDevice(device, options)
            elif issubclass(device.__class__, gr.hier_block2):
                print "--> Using Server and GnuRadioDevice wrapper for", device
                device = GnuRadioDevice(ServerWrapper(device, options), options)
            else:
                print "~~> Device interface in", device, "not found:", parents
                #return None
                raise Exception, "Device interface not found"
        except Exception, e:
            print "~~> Failed to wrap:", str(e)
            traceback.print_exc()
            #return None
            raise Exception, e
    
    #parents = device.__class__.__bases__
    #if NetworkTransport not in parents:
    if issubclass(device.__class__, NetworkTransport) == False:
        print "~~> NetworkTransport interface in", device, "not found:", parents
        #return None
        raise Exception, "NetworkTransport interface not found"
    
    try:
        if device.open() == False:
            print "~~> Failed to initialise device:", device
            device.close()
            #return None
            raise Exception, "Failed to initialise device"
    except Exception, e:
        print "~~> Failed to open:", str(e)
        traceback.print_exc()
        #return None
        raise Exception, e
    
    return device

def _find_quotes(s):
    b = False
    e = False
    list = []
    i = -1
    for c in s:
        i += 1
        if c == '\\':
            e = True
            continue
        elif e:
            e = False
            continue
        
        if c == '"':
            list += [i]
    return list

def _remove_quoted(data):
    r = ""
    list = _find_quotes(data)
    if len(list) == 0:
        return data
    last = 0
    b = False
    for l in list:
        if b == False:
            r += data[last:l]
            b = True
        else:
            last = l + 1
            b = False
    if b == False:
        r += data[last:]
    return r

class ThreadedTCPRequestHandler(SocketServer.StreamRequestHandler): # BaseRequestHandler
    # No __init__
    def setup(self):
        SocketServer.StreamRequestHandler.setup(self)
        
        print "==> Connection from:", self.client_address
        
        self.device = None
        self.transport = NetworkTransport() # Create dummy to avoid 'None' checks in code
        
        device = None
        if self.server.block:
            if self.server.device:
                self.server.device.close()
                self.server.device = None
            device = _wrap_device(self.server.block, self.server.options)
        elif self.server.device:
            device = self.server.device
        if device:
            transport = device # MAGIC
            if transport.destination(self.client_address[0]):
                self.device = device
                self.transport = transport
            else:
                device.close()
        
        with self.server.clients_lock:
            self.server.clients.append(self)
        
        first_response = "DEVICE " + _format_device(self.device, self.transport)
        if self.server.options.command:
            print "< " + first_response
        self.send(first_response)
    def handle(self):
        buffer = ""
        while True:
            data = ""   # Initialise to nothing so if there's an exception it'll disconnect
            
            try:
                data = self.request.recv(1024)  # 4096
            except socket.error, (e, msg):
                if e != 104:    # Connection reset by peer
                    print "==>", self.client_address, "-", msg
            
            #data = self.rfile.readline().strip()
            if len(data) == 0:
                break
            
            #cur_thread = threading.currentThread()
            #response = "%s: %s" % (cur_thread.getName(), data)
            #self.request.send(response)
            
            buffer += data
            lines = buffer.splitlines(True)
            for line in lines:
                if line[-1] != '\n':
                    buffer = line
                    break
                line = line.strip()
                if self.process_client_command(line) == False:
                    break
            else:
                buffer = ""
    def finish(self):
        print "==> Disconnection from:", self.client_address
        
        if self.device:
            print "--> Closing device:", self.device
        self.close_device()
        
        with self.server.clients_lock:
            self.server.clients.remove(self)
        
        try:
            SocketServer.StreamRequestHandler.finish(self)
        except socket.error, (e, msg):
            if e != 32:    # Broken pipe
                print "==>", self.client_address, "-", msg
    def close_device(self):
        if self.device:
            self.device.close()
            #del self.device
            #gc.collect()
            self.device = None
        self.transport = NetworkTransport() # MAGIC
    def process_client_command(self, command):
        if self.server.options.command:
            print ">", command
        data = None
        idx = command.find(" ")
        if idx > -1:
            data = command[idx+1:].strip();
            command = command[0:idx]
        command = command.upper()
        result = "OK"
        
        try:
            if command == "GO":
                if self.device:
                    if self.device.is_running():
                        result += " RUNNING"
                    else:
                        if self.device.start() != True:
                            result = "FAIL" + _format_error(self.device.last_error())
                else:
                    result = "DEVICE"
            
            elif command == "STOP":
                if self.device:
                    if self.device.is_running():
                        result += " STOPPED"
                    self.device.stop()
                else:
                    result = "DEVICE"
            
            elif command == "DEVICE":
                error = ""
                if (self.server.options.lock == False) and (len(data) > 0):
                    self.close_device()
                    
                    if data != "!":
                        try:
                            device = _create_device(data, self.server.options)
                            if device:
                                transport = device    # MAGIC
                                if transport.destination(self.client_address[0]) == False:
                                    error = "Failed to initialise NetworkTransport"
                                    device.close()
                            else:
                                error = "Failed to create device"
                        except Exception, e:
                            traceback.print_exc()
                            error = str(e)
                        if len(error) == 0:
                            self.device = device
                            self.transport = transport
                result = _format_device(self.device, self.transport) + _format_error(error)
            
            elif command == "FREQ":
                if self.device:
                    if data is None:
                        result = str(self.device.freq())
                    else:
                        freq = 0.0
                        try:
                            freq = float(data)
                        except:
                            pass
                        
                        if self.device.freq(freq):
                            success = self.device.was_tune_successful()
                            if success < 0:
                                result = "LOW"
                            elif success > 0:
                                result = "HIGH"
                            
                            tune_result = self.device.last_tune_result()
                            result += " %f %f %f %f" % (tune_result.target_rf_freq, tune_result.actual_rf_freq, tune_result.target_dsp_freq, tune_result.actual_dsp_freq)
                else:
                    result = "DEVICE"
            
            elif command == "ANTENNA":
                if self.device:
                    if data is None:
                        result = str(self.device.antenna())
                        if result is None or len(result) == 0:
                            result = "UNKNOWN"
                    else:
                        if self.device.antenna(data) == False:
                            result = "FAIL" + _format_error(self.device.last_error())
                else:
                    result = "DEVICE"
            
            elif command == "GAIN":
                if self.device:
                    if data is None:
                        result = str(self.device.gain())
                    else:
                        gain = 0.0
                        try:
                            gain = float(data)
                        except:
                            pass
                        
                        if self.device.gain(gain):
                            #result += " " + str(self.device.gain())
                            pass
                        else:
                            result = "FAIL" + _format_error(self.device.last_error())
                else:
                    result = "DEVICE"
            
            elif command == "RATE":
                if self.device:
                    if data is None:
                        result = str(self.device.sample_rate())
                    else:
                        rate = 0.0
                        try:
                            rate = float(data)
                        except:
                            pass
                        
                        if self.device.sample_rate(rate):
                            result += " " + str(self.device.sample_rate())
                        else:
                            result = "FAIL" + _format_error(self.device.last_error())
                else:
                    result = "DEVICE"
            
            elif command == "DEST":
                if data is None:
                    result = self.transport.destination()[0] + ":" + str(self.transport.destination()[1])
                else:
                    if data == "-":
                        data = self.client_address[0]
                    
                    if self.transport.destination(data):
                        result += " " + self.transport.destination()[0] + ":" + str(self.transport.destination()[1])
                    else:
                        result = "FAIL Failed to set destination"
            
            elif command == "HEADER":
                if data is None:
                    if self.transport.header():
                        result = "ON"
                    else:
                        result = "OFF"
                else:
                    self.transport.header(data.upper() == "OFF")
            
            #########################################
            
            #elif command == "SHUTDOWN":
            #    quit_event.set()
            #    return False
            
            #########################################
            
            else:
                result = "UNKNOWN"
        except Exception, e:
            if command == "DEVICE":
                result = "-"
            else:
                result = "FAIL"
            result += " " + str(e)
            traceback.print_exc()
        
        if result is None or len(result) == 0:
            return True
        
        result = command + " " + result
        
        if self.server.options.command:
            print "<", result
        
        return self.send(result)
    def send(self, data):
        try:
            self.wfile.write(data + "\n")
            return True
        except socket.error, (e, msg):
            if e != 32:    # Broken pipe
                print "==>", self.client_address, "-", msg
        return False

class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    allow_reuse_address = True

def _generate_options(args=None):
    usage="%prog: [options]"
    parser = OptionParser(usage=usage)  #option_class=eng_option, 
    parser.add_option("-l", "--listen", type="int", help="server listen port", default=28888)  #, metavar="SUBDEV"
    parser.add_option("-p", "--port", type="int", help="default data port", default=28888)
    parser.add_option("-v", "--verbose", action="store_true", help="verbose output", default=False)
    parser.add_option("-g", "--debug", action="store_true", help="debug output", default=False)
    parser.add_option("-c", "--command", action="store_true", help="command output", default=False)
    parser.add_option("-r", "--realtime", action="store_true", help="realtime scheduling", default=False)
    parser.add_option("-R", "--no-reload", action="store_true", help="disable dynamic reload", default=False)
    parser.add_option("-d", "--device", type="string", help="immediately create device", default=None)
    parser.add_option("-L", "--lock", action="store_true", help="lock device", default=False)
    parser.add_option("-D", "--default", type="string", help="device to create when default hint supplied", default=None)
    
    if args:
        if not isinstance(args, list):
            args = [args]
        (options, args) = parser.parse_args(args)
    else:
        (options, args) = parser.parse_args()
    
    options.fixed_flowgraph = False
    
    return (options, args)

class borip_server():
    def __init__(self, block=None, options=None):
        self.server = None
        self.server_thread = None
        
        if options is None or isinstance(options, str):
            (options, args) = _generate_options(options)
        self.options = options
        
        self.block = block
    def __del__(self):
        self.stop()
    def start(self):
        if self.server is not None:
            return True
        
        device = None
        if self.block is None and self.options.device is not None:
            try:
                device = _create_device(self.options.device, self.options)
            except Exception, e:
                print "!!> Failed to create initial device with hint:", self.options.device
        
        HOST, PORT = "", self.options.listen
        print "==> Starting TCP server on port:", PORT
        while True:
            try:
                self.server = ThreadedTCPServer((HOST, PORT), ThreadedTCPRequestHandler)
                self.server.options = self.options
                self.server.block = self.block
                self.server.device = device
                self.server.clients_lock = threading.Lock()
                self.server.clients = []
                #ip, port = self.server.server_address
                self.server_thread = threading.Thread(target=self.server.serve_forever)
                self.server_thread.setDaemon(True)
                self.server_thread.start()
                print "==> TCP server running on", self.server.server_address, "in thread:", self.server_thread.getName()
            except socket.error, (e, msg):
                print "    Socket error:", msg
                if (e == 98):   # Still in use
                    print "    Waiting, then trying again..."
                    try:
                        time.sleep(5)
                    except KeyboardInterrupt:
                        print "    Aborting"
                        sys.exit(1)
                    continue
                sys.exit(1)
            break
        
        if self.options.realtime:
            if gr.enable_realtime_scheduling() == gr.RT_OK:
                print "==> Enabled realtime scheduling"
            else:
                print "!!> Failed to enable realtime scheduling"
        return True
    def stop(self):
        if self.server is None:
            return True
        print "==> Closing server..."
        self.server.server_close()   # Clients still exist
        with self.server.clients_lock:
            # Calling 'shutdown' here causes clients not to handle close via 'finish'
            for client in self.server.clients:
                print "<<< Closing:", client.client_address
                try:
                    client.request.shutdown(socket.SHUT_RDWR)
                    client.request.close()
                except:
                    pass
            self.server.shutdown()
            self.server_thread.join()
        self.server = None
        return True

def main():
    server = borip_server()
    server.start()
    
    try:
        while True:
            raw_input()
    except KeyboardInterrupt:
        print
    except EOFError:
        pass
    except Exception, e:
        print "==> Unhandled exception:", str(e)
    
    server.stop()
    print "==> Done"

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = colours
#!/usr/bin/env python

class Callable:
    def __init__(self, anycallable):
        self.__call__ = anycallable

class TerminalColours:
	Esc = '\033['
	EscFin = 'm'
	
	_Reset = 0
	_Bold = 1
	_Italic = 3
	_Underline = 4
	_DefaultBackground = 49
	Colours = range(8)
	(_Blk, _R, _G, _Y, _B, _M, _C, _W) = Colours
	
	Reset = Esc + str(_Reset) + EscFin
	Bold = Esc + str(_Bold) + EscFin
	Italic = Esc + str(_Italic) + EscFin
	Underline = Esc + str(_Underline) + EscFin
	DefaultBackground = Esc + str(_DefaultBackground) + EscFin
	
	def _lo(colour):
		return str(30 + colour)
	_lo = Callable(_lo)
	
	def _hi(colour):
		return str(90 + colour)
	_hi = Callable(_hi)
	
	def _bk(colour):
		return str(40 + colour)
	_bk = Callable(_bk)
	
	def _bkhi(colour):
		return str(100 + colour)
	_bkhi = Callable(_bkhi)
	
	def esc(colour):
		return TerminalColours.Esc + str(colour) + TerminalColours.EscFin
	esc = Callable(esc)
	
	def lo(colour):
		return TerminalColours.esc(TerminalColours._lo(colour))
	lo = Callable(lo)
	
	def hi(colour):
		return TerminalColours.esc(TerminalColours._hi(colour))
	hi = Callable(hi)
	
	def bk(colour):
		return TerminalColours.esc(TerminalColours._bk(colour))
	bk = Callable(bk)
	
	def bkhi(colour):
		return TerminalColours.esc(TerminalColours._bkhi(colour))
	bkhi = Callable(bkhi)
	
	#(Black, Red, Green, Yellow, Blue, Magenta, Cyan, White) = map(lo, Colours)
	#(Blk, R, G, Y, B, M, C, W) = map(TerminalColours.lo, Colours)
	#(BlackHi, RedHi, GreenHi, YellowHi, BlueHi, MagentaHi, CyanHi, WhiteHi)
	#(BlkHi, RHi, GHi, YHi, BHi, MHi, CHi, WHi) = map(hi, Colours)
	#(BackBlack, BackRed, BackGreen, BackYellow, BackBlue, BackMagenta, BackCyan, BackWhite)
	#(BkBlk, BkR, BkG, BkY, BkB, BkM, BkC, BkW) = map(bk, Colours)
	#(BackBlackHi, BackRedHi, BackGreenHi, BackYellowHi, BackBlueHi, BackMagentaHi, BackCyanHi, BackWhiteHi)
	#(BkBlkHi, BkRHi, BkGHi, BkYHi, BkBHi, BkMHi, BkCHi, BkWHi) = map(bkhi, Colours)
	
	def reset(str=""):
		return TerminalColours.Reset + str;
	reset = Callable(reset)
	
	def bold(str):
		return TerminalColours.Bold + str + TerminalColours.Reset;
	bold = Callable(bold)
	
	def italic(str):
		return TerminalColours.Italic + str + TerminalColours.Reset;
	italic = Callable(italic)

	def underline(str):
		return TerminalColours.Underline + str + TerminalColours.Reset;
	underline = Callable(underline)
	
	def colour(colour, msg):
		if isinstance(colour, int) or colour[0] != '\033':
			colour = TerminalColours.esc(colour)
		return colour + str(msg) + TerminalColours.Reset
	colour = Callable(colour)
	
	def pick_colour(colour, hi=False, bk=False):
		if hi:
			if bk:
				return TerminalColours.bkhi(colour)
			else:
				return TerminalColours.hi(colour)
		if bk:
			return TerminalColours.bk(colour)
		return TerminalColours.lo(colour)
	pick_colour = Callable(pick_colour)

	#def blk(str, hi, bk):
	#	return colour(pick_colour(_Blk, hi, bk), str)
	
	#(blk, r, g, y, b, m, c, w) = map(lambda x: (lambda y, z1=False, z2=False: colour(y, pick_colour(x, z1, z2))), Colours)
	
	def colours(str, colours, mapping):
		prev = None
		res = ""
		while i in range(len(str)):
			if prev is None or mapping[i] != prev:
				if mapping[i] < 0 or mapping[i] >= len(colours):
					colour = TerminalColours.Reset
				else:
					colour = colours[mapping[i]]
				str += colour
				if i < len(mapping):
					prev = mapping[i]
			res += str[i]
		return res + TerminalColours.Reset
	colours = Callable(colours)

tc = TerminalColours

(tc.Blk, tc.R, tc.G, tc.Y, tc.B, tc.M, tc.C, tc.W) = map(TerminalColours.lo, TerminalColours.Colours)
(tc.BlkHi, tc.RHi, tc.GHi, tc.YHi, tc.BHi, tc.MHi, tc.CHi, tc.WHi) = map(TerminalColours.hi, TerminalColours.Colours)
(tc.BkBlk, tc.BkR, tc.BkG, tc.BkY, tc.BkB, tc.BkM, tc.BkC, tc.BkW) = map(TerminalColours.bk, TerminalColours.Colours)
(tc.BkBlkHi, tc.BkRHi, tc.BkGHi, tc.BkYHi, tc.BkBHi, tc.BkMHi, tc.BkCHi, tc.BkWHi) = map(TerminalColours.bkhi, TerminalColours.Colours)
#(tc.blk, tc.r, tc.g, tc.y, tc.b, tc.m, tc.c, tc.w) = map(lambda (c): Callable(lambda (x): (lambda (y, z1, z2): TerminalColours.colour(y, TerminalColours.pick_colour(x, z1, z2)))), TerminalColours.Colours)
(tc.blk, tc.r, tc.g, tc.y, tc.b, tc.m, tc.c, tc.w) = map(lambda (c): Callable(c), map(lambda x: (lambda y, z1=None, z2=None: TerminalColours.colour(TerminalColours.pick_colour(x, z1, z2), y)), TerminalColours.Colours))

########NEW FILE########
__FILENAME__ = doa_compass_control
from doa_compass_plotter import compass_plotter
from gnuradio.wxgui import forms
from gnuradio.gr import pubsub
import wx

########################################################################
# Controller keys
########################################################################
BEAM_AZM_KEY = 'beam_azm'
BEAM_ENB_KEY = 'beam_enb'

########################################################################
# Constants
########################################################################
POINTER_WIDTH = 3 #degrees
SLIDER_STEP_SIZE = 3 #degrees
BEAM_COLOR_SPEC = (0, 0, 1)
PLOTTER_SIZE = (450, 450)

########################################################################
# Main controller GUI
########################################################################
class compass_control(pubsub.pubsub, wx.Panel):
    def __init__(self, parent, ps=None, direction_key='__direction_key__', callback=None, direction=None, text=None, text_visible=None):
        #init
        if ps is None: ps = pubsub.pubsub()
        if direction is not None: ps[direction_key] = direction
        pubsub.pubsub.__init__(self)
        wx.Panel.__init__(self, parent)
        #proxy keys
        self.proxy(BEAM_AZM_KEY, ps, direction_key)
        #build gui and add plotter
        vbox = wx.BoxSizer(wx.VERTICAL)
        self.plotter = compass_plotter(self)
        self.plotter.SetSize(wx.Size(*PLOTTER_SIZE))
        self.plotter.SetSizeHints(*PLOTTER_SIZE)
        vbox.Add(self.plotter, 1, wx.EXPAND) # | wx.SHAPED #keep aspect ratio
        #build the control box
        #beam_box = forms.static_box_sizer(
            #parent=self,
            #label='Beam Control',
            #bold=True,
        #)
        #vbox.Add(beam_box, 0, wx.EXPAND)
        #beam_box.Add(_beam_control(self, label='Beam', azm_key=BEAM_AZM_KEY, enb_key=BEAM_ENB_KEY), 0, wx.EXPAND)
        #beam_box.Add(_beam_control(self, label='Null', azm_key=NULL_AZM_KEY, enb_key=NULL_ENB_KEY), 0, wx.EXPAND)
        #self[BEAM_ENB_KEY] = True
        #self[NULL_ENB_KEY] = True
        #self[PATTERN_KEY] = 'ant0'
        #forms.drop_down(
            #label='Pattern',
            #ps=self,
            #key=PATTERN_KEY,
            #choices=PATTERN_KEYS,
            #labels=PATTERN_NAMES,
            #sizer=beam_box,
            #parent=self,
            #proportion=0,
        #)
        self.SetSizerAndFit(vbox)
        #subscribe keys to the update methods
        self.subscribe(BEAM_AZM_KEY, self.update)
        
        #self.update_enables() #initial updates
        self.set_direction(direction)
        self.plotter.set_text(text)
        self.plotter.set_text_visible(text_visible, True)

        #do last as to not force initial update
        if callback: self.subscribe(TAPS_KEY, callback)

    def update_enables(self, *args):
        """
        Called when the pattern is changed. 
        Update the beam and null enable states based on the pattern.
        """
        for key, name, beam_enb, null_enb in PATTERNS:
            if self[PATTERN_KEY] != key: continue
            self[BEAM_ENB_KEY] = beam_enb
            self[NULL_ENB_KEY] = null_enb
            self.update()
            return

    def update(self, *args):
        """
        """
        #update the null and beam arrows
        for (enb_key, azm_key, color_spec) in (
            (BEAM_ENB_KEY, BEAM_AZM_KEY, BEAM_COLOR_SPEC),
        ):
            profile = self[enb_key] and [
                (0, self[azm_key]),
                (1.0, self[azm_key]-POINTER_WIDTH/2.0),
                (1.0, self[azm_key]+POINTER_WIDTH/2.0),
            ] or []
            self.plotter.set_profile(
                key='1'+azm_key, color_spec=color_spec,
                fill=True, profile=profile,
            )
        self.plotter.update()
    
    def set_direction(self, direction):
        if direction is None:
            self[BEAM_ENB_KEY] = False
        else:
            self[BEAM_ENB_KEY] = True
            self[BEAM_AZM_KEY] = direction
        self.update()
    
    def set_text(self, text):
        self.plotter.set_text(text)

    def set_text_visible(self, visible):
        self.plotter.set_text_visible(visible)

########NEW FILE########
__FILENAME__ = doa_compass_plotter
#!/usr/bin/env python

import wx
import wx.glcanvas
from OpenGL import GL
from gnuradio.wxgui.plotter.plotter_base import plotter_base
from gnuradio.wxgui.plotter import gltext
import math

COMPASS_LINE_COLOR_SPEC = (.6, .6, .6)
TXT_FONT_SIZE = 13
TXT_SCALE_FACTOR = 1000
TXT_RAD = 0.465
CIRCLE_RAD = 0.4
BIG_TICK_LEN = 0.05
MED_TICK_LEN = 0.035
SMALL_TICK_LEN = 0.01
TICK_LINE_WIDTH = 1.5
PROFILE_LINE_WIDTH = 1.5

def polar2rect(*coors):
	return [(r*math.cos(math.radians(a)), r*math.sin(math.radians(a))) for r, a in coors]

class compass_plotter(plotter_base):

	def __init__(self, parent):
		plotter_base.__init__(self, parent)
		#setup profile cache
		self._profiles = dict()
		self._profile_cache = self.new_gl_cache(self._draw_profile, 50)
		#setup compass cache
		self._compass_cache = self.new_gl_cache(self._draw_compass, 25)
		self._text_cache = self.new_gl_cache(self._draw_text, 65)
		self._text = None
		self._text_visible = False
		self._gl_text = None
		#init compass plotter
		self.register_init(self._init_compass_plotter)

	def _init_compass_plotter(self):
		"""
		Run gl initialization tasks.
		"""
		GL.glEnableClientState(GL.GL_VERTEX_ARRAY)

	def _setup_antialiasing(self):
		#enable antialiasing
		GL.glEnable(GL.GL_BLEND)
		GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
		for type, hint in (
			(GL.GL_LINE_SMOOTH, GL.GL_LINE_SMOOTH_HINT),
			(GL.GL_POINT_SMOOTH, GL.GL_POINT_SMOOTH_HINT),
			(GL.GL_POLYGON_SMOOTH, GL.GL_POLYGON_SMOOTH_HINT),
		):
			GL.glEnable(type)
			GL.glHint(hint, GL.GL_NICEST)

	def _draw_compass(self):
		"""
		Draw the compass rose tick marks and tick labels.
		"""
		self._setup_antialiasing()
		GL.glLineWidth(TICK_LINE_WIDTH)
		#calculate points for the compass
		points = list()
		for degree in range(0, 360):
			if degree%10 == 0: tick_len = BIG_TICK_LEN
			elif degree%5 == 0: tick_len = MED_TICK_LEN
			else: tick_len = SMALL_TICK_LEN
			points.append((CIRCLE_RAD, degree))
			points.append((CIRCLE_RAD+tick_len, degree))
		points = polar2rect(*points)
		#scale with matrix transform
		GL.glPushMatrix()
		GL.glScalef(self.width, self.height, 1)
		GL.glTranslatef(0.5, 0.5, 0)
		GL.glRotatef(-90, 0, 0, 1)
		#set color and draw
		GL.glColor3f(*COMPASS_LINE_COLOR_SPEC)
		GL.glVertexPointerf(points)
		GL.glDrawArrays(GL.GL_LINES, 0, len(points))
		#draw the labels
		GL.glScalef(1.0/TXT_SCALE_FACTOR, 1.0/TXT_SCALE_FACTOR, 1)
		for degree in range(0, 360, 10):
			position = wx.Point(*(polar2rect((TXT_SCALE_FACTOR*TXT_RAD, degree))[0]))
			txt = gltext.Text('%d'%degree, font_size=TXT_FONT_SIZE, centered=True)
			txt.draw_text(position=position, rotation=-degree-90)
		GL.glPopMatrix()
	
	def _draw_text(self):
		#if self._text is None or len(self._text) == 0:
			#return
		#if type(self._text_visible) == bool and self._text_visible == False:
			#return
		#if type(self._text_visible) == int and self._text_visible < 0:
			#return
		
		#text = self._text
		#idx = self._text_visible
		#if type(idx) == bool:
			#idx = 0
		#if type(text) == list:
			#text = text[idx]
		
		self._setup_antialiasing()
		GL.glPushMatrix()
		GL.glScalef(self.width, self.height, 1)
		GL.glTranslatef(0.5, 0.65, 0)
		#GL.glRotatef(-90, 0, 0, 1)
		GL.glScalef(1.0/TXT_SCALE_FACTOR, 1.0/TXT_SCALE_FACTOR, 1)
		#GL.glScalef(1.0, 1.0, 1)
		position = wx.Point(*(.0,.0))
		if self._gl_text is not None:
			txt = gltext.Text(self._gl_text, font_size=96, centered=True, foreground=wx.RED)
			txt.draw_text(position=position, rotation=0)
		GL.glPopMatrix()
		#print "Drawn"

	def _draw_profile(self):
		"""
		Draw the profiles into the compass rose as polygons.
		"""
		self._setup_antialiasing()
		GL.glLineWidth(PROFILE_LINE_WIDTH)
		#scale with matrix transform
		GL.glPushMatrix()
		GL.glScalef(self.width, self.height, 1)
		GL.glTranslatef(0.5, 0.5, 0)
		GL.glScalef(CIRCLE_RAD, CIRCLE_RAD, 1)
		GL.glRotatef(-90, 0, 0, 1)
		#draw the profile
		for key in sorted(self._profiles.keys()):
			color_spec, fill, profile = self._profiles[key]
			if not profile: continue
			points = polar2rect(*profile)
			GL.glColor3f(*color_spec)
			GL.glVertexPointerf(points)
			GL.glDrawArrays(fill and GL.GL_POLYGON or GL.GL_LINE_LOOP, 0, len(points))
		GL.glPopMatrix()

	def set_profile(self, key='', color_spec=(0, 0, 0), fill=True, profile=[]):
		"""
		Set a profile onto the compass rose.
		A polar coordinate tuple is of the form (radius, angle).
		Where radius is between -1 and 1 and angle is in degrees.
		@param key unique identifier for profile
		@param color_spec a 3-tuple gl color spec
		@param fill true to fill in the polygon or false for outline
		@param profile a list of polar coordinate tuples
		"""
		self.lock()
		self._profiles[key] = color_spec, fill, profile
		self._profile_cache.changed(True)
		self.unlock()
	
	def set_text(self, text, visible=None):
		#print "set_text", text, visible
		if self._text == text:
			return
		self._text = text
		if visible is not None:
			self._text_visible = visible
		self._update_text()
	
	def set_text_visible(self, visible, force=False):
		#if type(visible) == float or type(visible) == int:
		#	visible = visible != 0
		if force == False and self._text_visible == visible:
			return
		#print "set_text_visible", self._text, visible
		self._text_visible = visible
		self._update_text()
	
	def _update_text(self):
		_text = None
		
		if self._text is None or len(self._text) == 0:
			return
		if type(self._text_visible) == bool and self._text_visible == False:
			return
		if type(self._text_visible) == int and self._text_visible < 0:
			return
		
		_text = self._text
		idx = self._text_visible
		if type(idx) == bool:
			idx = 0
		if type(self._text) == list:
			_text = self._text[idx]
		
		self.lock()
		if _text is None:
			self._gl_text = None
		else:
			#print _text
			self._gl_text = _text
		self._text_cache.changed(True)
		self.unlock()

if __name__ == '__main__':
	app = wx.PySimpleApp()
	frame = wx.Frame(None, -1, 'Demo', wx.DefaultPosition)
	vbox = wx.BoxSizer(wx.VERTICAL)

	plotter = compass_plotter(frame)
	import random
	plotter.set_profile(key='1', color_spec=(1, 1, 0), fill=True, profile=[(random.random(), degree) for degree in range(0, 360, 3)])
	plotter.set_profile(key='2', color_spec=(0, 0, 1), fill=False, profile=[(random.random(), degree) for degree in range(0, 360, 3)])
	plotter.set_text("Hello World", True)
	vbox.Add(plotter, 1, wx.EXPAND)

	frame.SetSizerAndFit(vbox)
	frame.SetSize(wx.Size(600, 600))
	frame.Show()
	app.MainLoop()

########NEW FILE########
__FILENAME__ = eye
#!/usr/bin/env python

"""
Draws an eye diagram of an incoming float sample stream.
Certain parameters are adjustable at runtime (also exposed in GRC block).
This code is based on the Data Scope in OP25 (http://op25.osmocom.org/), which was created by Max Parke (KA1RBI).
This file is part of gr-baz. More info: http://wiki.spench.net/wiki/gr-baz
By Balint Seeber (http://spench.net/contact)
"""

from __future__ import with_statement

import threading, math
import wx
import numpy

from gnuradio import gr
import gnuradio.wxgui.plot as plot

# sample_rate/v_scale/t_scale is unused

# add datascope
#self.data_scope = datascope_sink_f(self.notebook, samples_per_symbol = 10, num_plots = 100)
#self.data_plotter = self.data_scope.win.graph
#wx.EVT_RADIOBOX(self.data_scope.win.radio_box, 11103, self.filter_select)
#wx.EVT_RADIOBOX(self.data_scope.win.radio_box_speed, 11104, self.speed_select)
#self.data_scope.win.radio_box_speed.SetSelection(self.current_speed)
#self.notebook.AddPage(self.data_scope.win, "Datascope")

default_scopesink_size = (640, 320)
default_v_scale = None  #1000
default_frame_decim = gr.prefs().get_long('wxgui', 'frame_decim', 1)

#####################################################################

#speeds = [300, 600, 900, 1200, 1440, 1800, 1920, 2400, 2880, 3200, 3600, 3840, 4000, 4800, 6400, 7200, 8000, 9600, 14400, 19200]

#class window_with_ctlbox(wx.Panel):
#    def __init__(self, parent, id = -1):
#        wx.Panel.__init__(self, parent, id)
#    def make_control_box (self):
#        global speeds
#        ctrlbox = wx.BoxSizer (wx.HORIZONTAL)
#
#        ctrlbox.Add ((5,0) ,0)
#
#        run_stop = wx.Button (self, 11102, "Run/Stop")
#        run_stop.SetToolTipString ("Toggle Run/Stop mode")
#        wx.EVT_BUTTON (self, 11102, self.run_stop)
#        ctrlbox.Add (run_stop, 0, wx.EXPAND)
#
#        self.radio_box = wx.RadioBox(self, 11103, "Viewpoint", style=wx.RA_SPECIFY_ROWS,
#                        choices = ["Raw", "Filtered"] )
#        self.radio_box.SetToolTipString("Viewpoint Before Or After Symbol Filter")
#        self.radio_box.SetSelection(1)
#        ctrlbox.Add (self.radio_box, 0, wx.EXPAND)
#
#        ctrlbox.Add ((5, 0) ,0)            # stretchy space
#
#        speed_str = []
#        for speed in speeds:
#            speed_str.append("%d" % speed)
#            
#            self.radio_box_speed = wx.RadioBox(self, 11104, "Symbol Rate", style=wx.RA_SPECIFY_ROWS, majorDimension=2, choices = speed_str)
#            self.radio_box_speed.SetToolTipString("Symbol Rate")
#            ctrlbox.Add (self.radio_box_speed, 0, wx.EXPAND)
#            ctrlbox.Add ((10, 0) ,1)            # stretchy space
#        
#        return ctrlbox

#####################################################################

class eye_sink_f(gr.hier_block2):
    def __init__(self,
            parent,
            title='Eye Diagram',
            sample_rate=1,
            size=default_scopesink_size,
            frame_decim=default_frame_decim,
            samples_per_symbol=10,
            num_plots=100,
            sym_decim=20,
            v_scale=default_v_scale,
            t_scale=None,
            num_inputs=1,
            **kwargs):
        
        if t_scale == 0:
            t_scale = None
        if v_scale == 0:
            v_scale = default_v_scale

        gr.hier_block2.__init__(self, "datascope_sink_f",
                                gr.io_signature(num_inputs, num_inputs, gr.sizeof_float),
                                gr.io_signature(0,0,0))

        msgq = gr.msg_queue(2)  # message queue that holds at most 2 messages
        self.st = gr.message_sink(gr.sizeof_float, msgq, dont_block=1)
        self.connect((self, 0), self.st)

        self.win = datascope_window(
            datascope_win_info(
                msgq,
                sample_rate,
                frame_decim,
                v_scale,
                t_scale,
                #None,  # scopesink (not used)
                title=title),
            parent,
            samples_per_symbol=samples_per_symbol,
            num_plots=num_plots,
            sym_decim=sym_decim,
            size=size)
    def set_sample_rate(self, sample_rate):
        #self.guts.set_sample_rate(sample_rate)
        self.win.info.set_sample_rate(sample_rate)
    def set_samples_per_symbol(self, samples_per_symbol):
        self.win.set_samples_per_symbol(samples_per_symbol)
    def set_num_plots(self, num_plots):
        self.win.set_num_plots(num_plots)
    def set_sym_decim(self, sym_decim):
        self.win.set_sym_decim(sym_decim)

wxDATA_EVENT = wx.NewEventType()

def EVT_DATA_EVENT(win, func):
    win.Connect(-1, -1, wxDATA_EVENT, func)

class datascope_DataEvent(wx.PyEvent):
    def __init__(self, data, samples_per_symbol, num_plots):
        wx.PyEvent.__init__(self)
        self.SetEventType (wxDATA_EVENT)
        self.data = data
        self.samples_per_symbol = samples_per_symbol
        self.num_plots = num_plots
    def Clone (self): 
        self.__class__ (self.GetId())

class datascope_win_info (object):
    __slots__ = ['msgq', 'sample_rate', 'frame_decim', 'v_scale', 
                 'scopesink', 'title',
                 'time_scale_cursor', 'v_scale_cursor', 'marker', 'xy',
                 'autorange', 'running']
    def __init__ (self, msgq, sample_rate, frame_decim, v_scale, t_scale,
                  scopesink=None, title = "Oscilloscope", xy=False):
        self.msgq = msgq
        self.sample_rate = sample_rate
        self.frame_decim = frame_decim
        self.scopesink = scopesink
        self.title = title
        self.v_scale = v_scale
        self.marker = 'line'
        self.xy = xy
        self.autorange = not v_scale
        self.running = True
    def set_sample_rate(self, sample_rate):
        self.sample_rate = sample_rate
    def get_sample_rate (self):
        return self.sample_rate
    #def get_decimation_rate (self):
    #    return 1.0
    def set_marker (self, s):
        self.marker = s
    def get_marker (self):
        return self.marker
    #def set_samples_per_symbol(self, samples_per_symbol):
    #    pass
    #def set_num_plots(self, num_plots):
    #    pass

class datascope_input_watcher (threading.Thread):
    def __init__ (self, msgq, event_receiver, frame_decim, samples_per_symbol, num_plots, sym_decim, **kwds):
        threading.Thread.__init__ (self, **kwds)
        self.setDaemon (1)
        self.msgq = msgq
        self.event_receiver = event_receiver
        self.frame_decim = frame_decim
        self.samples_per_symbol = samples_per_symbol
        self.num_plots = num_plots
        self.sym_decim = sym_decim
        self.iscan = 0
        self.keep_running = True
        self.skip = 0
        self.totsamp = 0
        self.skip_samples = 0
        self.msg_string = ""
        self.lock = threading.Lock()
        self.start ()
    def set_samples_per_symbol(self, samples_per_symbol):
        with self.lock:
            self.samples_per_symbol = samples_per_symbol
            self.reset()
    def set_num_plots(self, num_plots):
        with self.lock:
            self.num_plots = num_plots
            self.reset()
    def set_sym_decim(self, sym_decim):
        with self.lock:
            self.sym_decim = sym_decim
            self.reset()
    def reset(self):
        self.msg_string = ""
        self.skip_samples = 0
    def run (self):
        # print "datascope_input_watcher: pid = ", os.getpid ()
        print "Num plots: %d, samples per symbol: %d" % (self.num_plots, self.samples_per_symbol)
        while (self.keep_running):
            msg = self.msgq.delete_head()   # blocking read of message queue
            nchan = int(msg.arg1())    # number of channels of data in msg
            nsamples = int(msg.arg2()) # number of samples in each channel
            
            self.totsamp += nsamples
            
            if self.skip_samples >= nsamples:
               self.skip_samples -= nsamples
               continue

            with self.lock:
                self.msg_string += msg.to_string()      # body of the msg as a string
            
                bytes_needed = (self.num_plots*self.samples_per_symbol) * gr.sizeof_float
                if (len(self.msg_string) < bytes_needed):
                    continue
    
                records = []
                # start = self.skip * gr.sizeof_float
                start = 0
                chan_data = self.msg_string[start:start+bytes_needed]
                rec = numpy.fromstring (chan_data, numpy.float32)
                records.append (rec)
                self.msg_string = ""
    
                unused = nsamples - (self.num_plots*self.samples_per_symbol)
                unused -= (start/gr.sizeof_float)
                self.skip = self.samples_per_symbol - (unused % self.samples_per_symbol)
                # print "reclen = %d totsamp %d appended %d skip %d start %d unused %d" % (nsamples, self.totsamp, len(rec), self.skip, start/gr.sizeof_float, unused)
    
                de = datascope_DataEvent (records, self.samples_per_symbol, self.num_plots)
            wx.PostEvent (self.event_receiver, de)
            records = []
            del de

            self.skip_samples = self.num_plots * self.samples_per_symbol * self.sym_decim   # lower values = more frequent plots, but higher CPU usage

class datascope_window(wx.Panel):
    def __init__(self,
                  info,
                  parent,
                  id=-1,
                  samples_per_symbol=10,
                  num_plots=100,
                  sym_decim=20,
                  pos=wx.DefaultPosition,
                  size=wx.DefaultSize,
                  name=""):
        #window_with_ctlbox.__init__ (self, parent, -1)
        wx.Panel.__init__(self, parent, id, pos, size, wx.DEFAULT_FRAME_STYLE, name)
        
        self.info = info

        vbox = wx.BoxSizer(wx.VERTICAL)
        self.graph = datascope_graph_window(
            info,
            self,
            -1,
            samples_per_symbol=samples_per_symbol,
            num_plots=num_plots,
            sym_decim=sym_decim,
            size=size)

        vbox.Add (self.graph, 1, wx.EXPAND)
        #vbox.Add (self.make_control_box(), 0, wx.EXPAND)
        #vbox.Add (self.make_control2_box(), 0, wx.EXPAND)

        self.sizer = vbox
        self.SetSizer (self.sizer)
        self.SetAutoLayout (True)
        self.sizer.Fit (self)
    # second row of control buttons etc. appears BELOW control_box
    #def make_control2_box (self):
    #    ctrlbox = wx.BoxSizer (wx.HORIZONTAL)
    #    ctrlbox.Add ((5,0) ,0) # left margin space
    #    return ctrlbox
    def run_stop (self, evt):
        self.info.running = not self.info.running
    def set_samples_per_symbol(self, samples_per_symbol):
        self.graph.set_samples_per_symbol(samples_per_symbol)
    def set_num_plots(self, num_plots):
        self.graph.set_num_plots(num_plots)
    def set_sym_decim(self, sym_decim):
        self.graph.set_sym_decim(sym_decim)

class datascope_graph_window (plot.PlotCanvas):
    def __init__(self,
            info,
            parent,
            id=-1,
            pos=wx.DefaultPosition,
            size=wx.DefaultSize,    #(140, 140),
            samples_per_symbol=10,
            num_plots=100,
            sym_decim=20,
            style = wx.DEFAULT_FRAME_STYLE,
            name = ""):
        plot.PlotCanvas.__init__ (self, parent, id, pos, size, style, name)

        self.SetXUseScopeTicks (True)
        self.SetEnableGrid (False)
        self.SetEnableZoom (True)
        self.SetEnableLegend(True)
        # self.SetBackgroundColour ('black')
        
        self.info = info;
        self.total_points = 0
        if info.v_scale is not None or info.v_scale == 0:
            self.y_range = (-info.v_scale, info.v_scale) #(-1., 1.)
        else:
            self.y_range = None
        #self.samples_per_symbol = samples_per_symbol
        #self.num_plots = num_plots

        EVT_DATA_EVENT (self, self.format_data)

        self.input_watcher = datascope_input_watcher(
            info.msgq,
            self,
            info.frame_decim,
            samples_per_symbol,
            num_plots,
            sym_decim)
    def set_samples_per_symbol(self, samples_per_symbol):
        self.input_watcher.set_samples_per_symbol(samples_per_symbol)
        #self.samples_per_symbol = samples_per_symbol
    def set_num_plots(self, num_plots):
        self.input_watcher.set_num_plots(num_plots)
        #self.num_plots = num_plots
    def set_sym_decim(self, sym_decim):
        self.input_watcher.set_sym_decim(sym_decim)
    def format_data (self, evt):
        if not self.info.running:
            return
        
        info = self.info
        records = evt.data
        nchannels = len(records)
        npoints = len(records[0])
        self.total_points += npoints

        x_vals = numpy.arange (0, evt.samples_per_symbol)

        self.SetXUseScopeTicks (True)   # use 10 divisions, no labels

        objects = []
        colors = ['red','orange','yellow','green','blue','violet','cyan','magenta','brown','black']

        r = records[0]  # input data
        v_min = None
        v_max = None
        for i in range(evt.num_plots):
            points = []
            for j in range(evt.samples_per_symbol):
                v = r[ i*evt.samples_per_symbol + j ]
                if (v_min is None) or (v < v_min):
                    v_min = v
                if (v_max is None) or (v > v_max):
                    v_max = v
                p = [ j, v ]
                points.append(p)
            objects.append (plot.PolyLine (points, colour=colors[i % len(colors)], legend=('')))

        graphics = plot.PlotGraphics (objects,
                                      title=self.info.title,
                                      xLabel = 'Time', yLabel = 'Amplitude')
        x_range = (0., 0. + (evt.samples_per_symbol-1)) # ranges are tuples!
        if self.y_range is None:
            v_scale = max(abs(v_min), abs(v_max))
            y_range = (-v_scale, v_scale)
            #y_range = (min, max)
        else:
            y_range = self.y_range
        self.Draw (graphics, xAxis=x_range, yAxis=y_range)

########NEW FILE########
__FILENAME__ = facsink
#!/usr/bin/env python
#
# Copyright 2003,2004,2005,2006 Free Software Foundation, Inc.
# 
# This file is part of GNU Radio
# 
# GNU Radio is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# GNU Radio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with GNU Radio; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
# 

# Originally created by Frank of radiorausch (http://sites.google.com/site/radiorausch/USRPFastAutocorrelation.html)
# Upgraded for blks2 compatibility by Balint Seeber (http://wiki.spench.net/wiki/Fast_Auto-correlation)

#from gnuradio import gr, gru, window, blocks, fft, filter
from gnuradio import gr, gru, blocks, fft, filter   # +kai for gnuradio 3.7

from gnuradio.wxgui import stdgui2, common
import wx
import gnuradio.wxgui.plot as plot
#import Numeric
import numpy
import threading
import math

default_facsink_size = (640,240)
default_fac_rate = gr.prefs().get_long('wxgui', 'fac_rate', 10) # was 15, 3

class fac_sink_base(gr.hier_block2, common.wxgui_hb):
    def __init__(self, input_is_real=False, baseband_freq=0, y_per_div=10, ref_level=50,
                 sample_rate=1, fac_size=512,
                 fac_rate=default_fac_rate,
                 average=False, avg_alpha=None, title='', peak_hold=False):

        self._item_size = gr.sizeof_gr_complex
        if input_is_real:
            self._item_size = gr.sizeof_float

        gr.hier_block2.__init__(
                self,
                "Fast AutoCorrelation",
                gr.io_signature(1, 1, self._item_size),
                gr.io_signature(0, 0, 0),
            )

        # initialize common attributes
        self.baseband_freq = baseband_freq
        self.y_divs = 8
        self.y_per_div=y_per_div
        self.ref_level = ref_level
        self.sample_rate = sample_rate
        self.fac_size = fac_size
        self.fac_rate = fac_rate
        self.average = average
        if (avg_alpha is None) or (avg_alpha <= 0):
            self.avg_alpha = 0.20 / fac_rate	# averaging needed to be slowed down for very slow rates
        else:
            self.avg_alpha = avg_alpha
        self.title = title
        self.peak_hold = peak_hold
        self.input_is_real = input_is_real
        self.msgq = gr.msg_queue(2)         # queue that holds a maximum of 2 messages

    def set_y_per_div(self, y_per_div):
        self.y_per_div = y_per_div

    def set_ref_level(self, ref_level):
        self.ref_level = ref_level

    def set_average(self, average):
        self.average = average
        if average:
            self.avg.set_taps(self.avg_alpha)
            self.set_peak_hold(False)
        else:
            self.avg.set_taps(1.0)

    def set_peak_hold(self, enable):
        self.peak_hold = enable
        if enable:
            self.set_average(False)
        self.win.set_peak_hold(enable)

    def set_avg_alpha(self, avg_alpha):
        self.avg_alpha = avg_alpha

    def set_baseband_freq(self, baseband_freq):
        self.baseband_freq = baseband_freq

    def set_sample_rate(self, sample_rate):
        self.sample_rate = sample_rate
        self._set_n()

    def _set_n(self):
        self.one_in_n.set_n(max(1, int(self.sample_rate/self.fac_size/self.fac_rate)))
        

class fac_sink_f(fac_sink_base):
    def __init__(self, parent, baseband_freq=0,
                 y_per_div=10, ref_level=50, sample_rate=1, fac_size=512,
                 fac_rate=default_fac_rate, 
                 average=False, avg_alpha=None,
                 title='', size=default_facsink_size, peak_hold=False):

        fac_sink_base.__init__(self, input_is_real=True, baseband_freq=baseband_freq,
                               y_per_div=y_per_div, ref_level=ref_level,
                               sample_rate=sample_rate, fac_size=fac_size,
                               fac_rate=fac_rate,  
                               average=average, avg_alpha=avg_alpha, title=title,
                               peak_hold=peak_hold)
                               
        s2p = blocks.stream_to_vector(gr.sizeof_float, self.fac_size)
        self.one_in_n = blocks.keep_one_in_n(gr.sizeof_float * self.fac_size,
                                         max(1, int(self.sample_rate/self.fac_size/self.fac_rate)))

        # windowing removed... 

        #fac = gr.fft_vfc(self.fac_size, True, ())
        fac = fft.fft_vfc(self.fac_size, True, ())

        c2mag = blocks.complex_to_mag(self.fac_size)
        self.avg = filter.single_pole_iir_filter_ff_make(1.0, self.fac_size)

        fac_fac   = fft.fft_vfc(self.fac_size, True, ())
        fac_c2mag = blocks.complex_to_mag_make(fac_size)

        # FIXME  We need to add 3dB to all bins but the DC bin
        log = blocks.nlog10_ff_make(20, self.fac_size,
                           -20*math.log10(self.fac_size) )
        sink = blocks.message_sink(gr.sizeof_float * self.fac_size, self.msgq, True)

        self.connect(s2p, self.one_in_n, fac, c2mag,  fac_fac, fac_c2mag, self.avg, log, sink)

#        gr.hier_block.__init__(self, fg, s2p, sink)

        self.win = fac_window(self, parent, size=size)
        self.set_average(self.average)

        self.wxgui_connect(self, s2p)


class fac_sink_c(fac_sink_base):
    def __init__(self, parent, baseband_freq=0,
                 y_per_div=10, ref_level=50, sample_rate=1, fac_size=512,
                 fac_rate=default_fac_rate, 
                 average=False, avg_alpha=None,
                 title='', size=default_facsink_size, peak_hold=False):

        fac_sink_base.__init__(self, input_is_real=False, baseband_freq=baseband_freq,
                               y_per_div=y_per_div, ref_level=ref_level,
                               sample_rate=sample_rate, fac_size=fac_size,
                               fac_rate=fac_rate, 
                               average=average, avg_alpha=avg_alpha, title=title,
                               peak_hold=peak_hold)

        s2p = blocks.stream_to_vector(gr.sizeof_gr_complex, self.fac_size)
        self.one_in_n = blocks.keep_one_in_n(gr.sizeof_gr_complex * self.fac_size,
                                         max(1, int(self.sample_rate/self.fac_size/self.fac_rate)))

        # windowing removed ...
     
        fac =  fft.fft_vcc(self.fac_size, True, ())
        c2mag = blocks.complex_to_mag_make(fac_size)

        # Things go off into the weeds if we try for an inverse FFT so a forward FFT will have to do...
        fac_fac   = fft.fft_vfc(self.fac_size, True, ())
        fac_c2mag = blocks.complex_to_mag_make(fac_size)

        self.avg = filter.single_pole_iir_filter_ff_make(1.0, fac_size)

        log = blocks.nlog10_ff_make(20, self.fac_size, 
                           -20*math.log10(self.fac_size)  ) #  - 20*math.log10(norm) ) # - self.avg[0] )
        sink = blocks.message_sink_make(gr.sizeof_float * fac_size, self.msgq, True)

        self.connect(s2p, self.one_in_n, fac, c2mag,  fac_fac, fac_c2mag, self.avg, log, sink)

#        gr.hier_block2.__init__(self, fg, s2p, sink)

        self.win = fac_window(self, parent, size=size)
        self.set_average(self.average)

        self.wxgui_connect(self, s2p)


# ------------------------------------------------------------------------

myDATA_EVENT = wx.NewEventType()
EVT_DATA_EVENT = wx.PyEventBinder (myDATA_EVENT, 0)


class DataEvent(wx.PyEvent):
    def __init__(self, data):
        wx.PyEvent.__init__(self)
        self.SetEventType (myDATA_EVENT)
        self.data = data

    def Clone (self): 
        self.__class__ (self.GetId())


class input_watcher (threading.Thread):
    def __init__ (self, msgq, fac_size, event_receiver, **kwds):
        threading.Thread.__init__ (self, **kwds)
        self.setDaemon (1)
        self.msgq = msgq
        self.fac_size = fac_size
        self.event_receiver = event_receiver
        self.keep_running = True
        self.start ()

    def run (self):
        while (self.keep_running):
            msg = self.msgq.delete_head()  # blocking read of message queue
            itemsize = int(msg.arg1())
            nitems = int(msg.arg2())

            s = msg.to_string()            # get the body of the msg as a string

            # There may be more than one fac frame in the message.
            # If so, we take only the last one
            if nitems > 1:
                start = itemsize * (nitems - 1)
                s = s[start:start+itemsize]

            complex_data = numpy.fromstring (s, numpy.float32)
            de = DataEvent (complex_data)
            wx.PostEvent (self.event_receiver, de)
            del de


class fac_window (plot.PlotCanvas):
    def __init__ (self, facsink, parent, id = -1,
                  pos = wx.DefaultPosition, size = wx.DefaultSize,
                  style = wx.DEFAULT_FRAME_STYLE, name = ""):
        plot.PlotCanvas.__init__ (self, parent, id, pos, size, style, name)

        self.y_range = None
        self.facsink = facsink
        self.peak_hold = False
        self.peak_vals = None

        self.SetEnableGrid (True)
        #self.SetEnableZoom (True)
        #self.SetBackgroundColour ('black')
        
        self.build_popup_menu()
        
        EVT_DATA_EVENT (self, self.set_data)
        wx.EVT_CLOSE (self, self.on_close_window)
        self.Bind(wx.EVT_RIGHT_UP, self.on_right_click)

        self.input_watcher = input_watcher(facsink.msgq, facsink.fac_size, self)
        
        #mouse wheel event
        def on_mouse_wheel(event):
            if event.GetWheelRotation() < 0: self.on_incr_ref_level(event)
            else: self.on_decr_ref_level(event)
        self.Bind(wx.EVT_MOUSEWHEEL, on_mouse_wheel)

    def on_close_window (self, event):
        print "fac_window:on_close_window"
        self.keep_running = False


    def set_data (self, evt):
        dB = evt.data
        L = len (dB)

        if self.peak_hold:
            if self.peak_vals is None:
                self.peak_vals = dB
            else:
                self.peak_vals = numpy.maximum(dB, self.peak_vals)
                dB = self.peak_vals

        x = max(abs(self.facsink.sample_rate), abs(self.facsink.baseband_freq))
        sf = 1000.0
        units = "ms"

        x_vals = ((numpy.arange (L/2)
                       * ( (sf / self.facsink.sample_rate  ) )) )
        points = numpy.zeros((len(x_vals), 2), numpy.float64)
        points[:,0] = x_vals
        points[:,1] = dB[0:L/2]

        lines = plot.PolyLine (points, colour='green')	# DARKRED

        graphics = plot.PlotGraphics ([lines],
                                      title=self.facsink.title,
                                      xLabel = units, yLabel = "dB")

        self.Draw (graphics, xAxis=None, yAxis=self.y_range)
        self.update_y_range ()

    def set_peak_hold(self, enable):
        self.peak_hold = enable
        self.peak_vals = None

    def update_y_range (self):
        ymax = self.facsink.ref_level
        ymin = self.facsink.ref_level - self.facsink.y_per_div * self.facsink.y_divs
        self.y_range = self._axisInterval ('min', ymin, ymax)

    def on_average(self, evt):
        # print "on_average"
        self.facsink.set_average(evt.IsChecked())

    def on_peak_hold(self, evt):
        # print "on_peak_hold"
        self.facsink.set_peak_hold(evt.IsChecked())

    def on_incr_ref_level(self, evt):
        # print "on_incr_ref_level"
        self.facsink.set_ref_level(self.facsink.ref_level
                                   + self.facsink.y_per_div)

    def on_decr_ref_level(self, evt):
        # print "on_decr_ref_level"
        self.facsink.set_ref_level(self.facsink.ref_level
                                   - self.facsink.y_per_div)

    def on_incr_y_per_div(self, evt):
        # print "on_incr_y_per_div"
        self.facsink.set_y_per_div(next_up(self.facsink.y_per_div, (1,2,5,10,20)))

    def on_decr_y_per_div(self, evt):
        # print "on_decr_y_per_div"
        self.facsink.set_y_per_div(next_down(self.facsink.y_per_div, (1,2,5,10,20)))

    def on_y_per_div(self, evt):
        # print "on_y_per_div"
        Id = evt.GetId()
        if Id == self.id_y_per_div_1:
            self.facsink.set_y_per_div(1)
        elif Id == self.id_y_per_div_2:
            self.facsink.set_y_per_div(2)
        elif Id == self.id_y_per_div_5:
            self.facsink.set_y_per_div(5)
        elif Id == self.id_y_per_div_10:
            self.facsink.set_y_per_div(10)
        elif Id == self.id_y_per_div_20:
            self.facsink.set_y_per_div(20)

        
    def on_right_click(self, event):
        menu = self.popup_menu
        for id, pred in self.checkmarks.items():
            item = menu.FindItemById(id)
            item.Check(pred())
        self.PopupMenu(menu, event.GetPosition())


    def build_popup_menu(self):
        self.id_incr_ref_level = wx.NewId()
        self.id_decr_ref_level = wx.NewId()
        self.id_incr_y_per_div = wx.NewId()
        self.id_decr_y_per_div = wx.NewId()
        self.id_y_per_div_1 = wx.NewId()
        self.id_y_per_div_2 = wx.NewId()
        self.id_y_per_div_5 = wx.NewId()
        self.id_y_per_div_10 = wx.NewId()
        self.id_y_per_div_20 = wx.NewId()
        self.id_average = wx.NewId()
        self.id_peak_hold = wx.NewId()

        self.Bind(wx.EVT_MENU, self.on_average, id=self.id_average)
        self.Bind(wx.EVT_MENU, self.on_peak_hold, id=self.id_peak_hold)
        self.Bind(wx.EVT_MENU, self.on_incr_ref_level, id=self.id_incr_ref_level)
        self.Bind(wx.EVT_MENU, self.on_decr_ref_level, id=self.id_decr_ref_level)
        self.Bind(wx.EVT_MENU, self.on_incr_y_per_div, id=self.id_incr_y_per_div)
        self.Bind(wx.EVT_MENU, self.on_decr_y_per_div, id=self.id_decr_y_per_div)
        self.Bind(wx.EVT_MENU, self.on_y_per_div, id=self.id_y_per_div_1)
        self.Bind(wx.EVT_MENU, self.on_y_per_div, id=self.id_y_per_div_2)
        self.Bind(wx.EVT_MENU, self.on_y_per_div, id=self.id_y_per_div_5)
        self.Bind(wx.EVT_MENU, self.on_y_per_div, id=self.id_y_per_div_10)
        self.Bind(wx.EVT_MENU, self.on_y_per_div, id=self.id_y_per_div_20)

        # make a menu
        menu = wx.Menu()
        self.popup_menu = menu
        menu.AppendCheckItem(self.id_average, "Average")
        menu.AppendCheckItem(self.id_peak_hold, "Peak Hold")
        menu.Append(self.id_incr_ref_level, "Incr Ref Level")
        menu.Append(self.id_decr_ref_level, "Decr Ref Level")
        # menu.Append(self.id_incr_y_per_div, "Incr dB/div")
        # menu.Append(self.id_decr_y_per_div, "Decr dB/div")
        menu.AppendSeparator()
        # we'd use RadioItems for these, but they're not supported on Mac
        menu.AppendCheckItem(self.id_y_per_div_1, "1 dB/div")
        menu.AppendCheckItem(self.id_y_per_div_2, "2 dB/div")
        menu.AppendCheckItem(self.id_y_per_div_5, "5 dB/div")
        menu.AppendCheckItem(self.id_y_per_div_10, "10 dB/div")
        menu.AppendCheckItem(self.id_y_per_div_20, "20 dB/div")

        self.checkmarks = {
            self.id_average : lambda : self.facsink.average,
            self.id_peak_hold : lambda : self.facsink.peak_hold,
            self.id_y_per_div_1 : lambda : self.facsink.y_per_div == 1,
            self.id_y_per_div_2 : lambda : self.facsink.y_per_div == 2,
            self.id_y_per_div_5 : lambda : self.facsink.y_per_div == 5,
            self.id_y_per_div_10 : lambda : self.facsink.y_per_div == 10,
            self.id_y_per_div_20 : lambda : self.facsink.y_per_div == 20,
            }


def next_up(v, seq):
    """
    Return the first item in seq that is > v.
    """
    for s in seq:
        if s > v:
            return s
    return v

def next_down(v, seq):
    """
    Return the last item in seq that is < v.
    """
    rseq = list(seq[:])
    rseq.reverse()

    for s in rseq:
        if s < v:
            return s
    return v


# ----------------------------------------------------------------
#          	      Deprecated interfaces
# ----------------------------------------------------------------

# returns (block, win).
#   block requires a single input stream of float
#   win is a subclass of wxWindow

def make_fac_sink_f(parent, title, fac_size, input_rate, ymin = 0, ymax=50):
    
    block = fac_sink_f(parent, title=title, fac_size=fac_size, sample_rate=input_rate,
                       y_per_div=(ymax - ymin)/8, ref_level=ymax)
    return (block, block.win)

# returns (block, win).
#   block requires a single input stream of gr_complex
#   win is a subclass of wxWindow

def make_fac_sink_c(parent, title, fac_size, input_rate, ymin=0, ymax=50):
    block = fac_sink_c(parent, title=title, fac_size=fac_size, sample_rate=input_rate,
                       y_per_div=(ymax - ymin)/8, ref_level=ymax)
    return (block, block.win)


# ----------------------------------------------------------------
# Standalone test app
# ----------------------------------------------------------------

class test_app_flow_graph (stdgui2.std_top_block):
    def __init__(self, frame, panel, vbox, argv):
        stdgui2.std_top_block	.__init__ (self, frame, panel, vbox, argv)

        fac_size = 256

        # build our flow graph
        input_rate = 20.48e3

        # Generate a complex sinusoid
        #src1 = gr.sig_source_c (input_rate, gr.GR_SIN_WAVE, 2e3, 1)
        src1 = gr.sig_source_c (input_rate, gr.GR_CONST_WAVE, 5.75e3, 1)

        # We add these throttle blocks so that this demo doesn't
        # suck down all the CPU available.  Normally you wouldn't use these.
        thr1 = gr.throttle(gr.sizeof_gr_complex, input_rate)

        sink1 = fac_sink_c (panel, title="Complex Data", fac_size=fac_size,
                            sample_rate=input_rate, baseband_freq=100e3,
                            ref_level=0, y_per_div=20)
        vbox.Add (sink1.win, 1, wx.EXPAND)
        self.connect (src1, thr1, sink1)

        #src2 = gr.sig_source_f (input_rate, gr.GR_SIN_WAVE, 2e3, 1)
        src2 = gr.sig_source_f (input_rate, gr.GR_CONST_WAVE, 5.75e3, 1)
        thr2 = gr.throttle(gr.sizeof_float, input_rate)
        sink2 = fac_sink_f (panel, title="Real Data", fac_size=fac_size*2,
                            sample_rate=input_rate, baseband_freq=100e3,
                            ref_level=0, y_per_div=20)
        vbox.Add (sink2.win, 1, wx.EXPAND)
        self.connect (src2, thr2, sink2)

def main ():
    app = stdgui2.stdapp (test_app_flow_graph, "fac Sink Test App")
    app.MainLoop ()

if __name__ == '__main__':
    main ()

########NEW FILE########
__FILENAME__ = gen_char_to_float_lut
#!/usr/bin/env python

import sys

sys.stdout.write("{ ");
for i in range(256):
	f = (float(i) - 128.0) / 128.0
	sys.stdout.write("%ff" % (f))
	if i < 255:
		sys.stdout.write(", ")
print(" };")

########NEW FILE########
__FILENAME__ = gen_char_to_short
#!/usr/bin/env python

import sys

sys.stdout.write("{ ");
for i in range(256):
	f = (float(i) - 128.0) / 128.0
	d = int(f * 32768)
	sys.stdout.write("%d" % (d))
	if i < 255:
		sys.stdout.write(", ")
print(" };")

########NEW FILE########
__FILENAME__ = message_callback
#!/usr/bin/env python

import threading, traceback, sys

from gnuradio import gr

_valid_parts = ['msg', 'type', 'arg1', 'arg2', 'length']

class queue_watcher(threading.Thread):
    def __init__(self, msgq,  callback, msg_parts, print_stdout, **kwds):
        threading.Thread.__init__(self, **kwds)
        self.setDaemon(True)
        self.msgq = msgq
        self.callback = callback
        self.msg_parts = msg_parts
        self.print_stdout = print_stdout
        self.keep_running = True
        self.start()
    def run(self):
        while self.msgq and self.keep_running:
            msg = self.msgq.delete_head()
            if self.keep_running == False:
                break
            if self.print_stdout:
                print msg.to_string()
            if self.callback:
                try:
                    to_eval = "self.callback(" + ",".join(map(lambda x: "msg." + x + "()", self.msg_parts)) + ")"
                    try:
                        eval(to_eval)
                    except Exception, e:
                        sys.stderr.write("Exception while evaluating:\n" + to_eval + "\n" + str(e) + "\n")
                        traceback.print_exc(None, sys.stderr)
                except Exception, e:
                    sys.stderr.write("Exception while forming call string using parts: " + str(self.msg_parts) + "\n" + str(e) + "\n")
                    traceback.print_exc(None, sys.stderr)

class message_callback():
    def __init__(self, msgq, callback=None, msg_part='arg1', custom_parts="", dummy=False, consume_dummy=False, print_stdout=False):
        if msgq is None:
            raise Exception, "message_callback requires a message queue"
        self._msgq = msgq
        self._watcher = None
        if dummy and consume_dummy == False:
            #print "[Message Callback] Dummy mode"
            return
        #print "[Message Callback] Starting..."
        if msg_part in _valid_parts:
            msg_parts = [msg_part]
        else:
            msg_parts = filter(lambda x: x in _valid_parts, map(lambda x: x.strip(), custom_parts.split(',')))
        self._watcher = queue_watcher(msgq, callback, msg_parts, print_stdout)
    def __del__(self):
        self.stop()
    def stop(self):
        if self._watcher is None:
            return
        self._watcher.keep_running = False
        msg = gr.message()  # Empty message to signal end
        self._msgq.insert_tail(msg)
    def msgq(self):
        return self._msgq

########NEW FILE########
__FILENAME__ = message_relay
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  message_relay.py
#  
#  Copyright 2013 Balint Seeber <balint@crawfish>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#  

import threading

from gnuradio import gr

class queue_watcher(threading.Thread):
	def __init__(self, tx_msgq, rx_msgq, **kwds):
		threading.Thread.__init__(self, **kwds)
		self.setDaemon(True)
		self.tx_msgq = tx_msgq
		self.rx_msgq = rx_msgq
		self.keep_running = True
		self.start()
	def run(self):
		if self.rx_msgq:
			while self.keep_running:
				msg = self.rx_msgq.delete_head()
				if self.keep_running == False:
					break
				try:
					if self.tx_msgq:
						self.tx_msgq.insert_tail(msg)
						#if self.tx_msgq.full_p():
						#	print "==> Dropping message!"
						#else:
						#	self.tx_msgq.handle(msg)
						#print "==> Message relay forwarded message"
				except:
					pass

class message_relay():
	def __init__(self, tx_msgq, rx_msgq):
		if tx_msgq is None:
			raise Exception, "message_relay requires a TX message queue"
		if rx_msgq is None:
			raise Exception, "message_relay requires a RX message queue"
		self._tx_msgq = tx_msgq
		if isinstance(rx_msgq, str):
			rx_msgq = eval(str)
		self._rx_msgq = rx_msgq
		self._watcher = queue_watcher(tx_msgq=tx_msgq, rx_msgq=rx_msgq)
	def __del__(self):
		self.stop()
	def stop(self):
		if self._watcher is None:
			return
		self._watcher.keep_running = False
		msg = gr.message()  # Empty message to signal end
		self._rx_msgq.insert_tail(msg)
	def tx_msgq(self):
		return self._tx_msgq
	def rx_msgq(self):
		return self._rx_msgq

def main():
	return 0

if __name__ == '__main__':
	main()

########NEW FILE########
__FILENAME__ = message_server
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  message_server.py
#  
#  Copyright 2013 Balint Seeber <balint@crawfish>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#  

from __future__ import with_statement

import threading, traceback, socket, SocketServer, time

from gnuradio import gr, gru

class ThreadedTCPRequestHandler(SocketServer.StreamRequestHandler): # BaseRequestHandler
    # No __init__
    def setup(self):
        SocketServer.StreamRequestHandler.setup(self)
        print "==> Connection from:", self.client_address
        self.request.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)
        with self.server.client_lock:
            self.server.clients.append(self)
        self.server.connect_event.set()
        #self.server.command_queue.insert_tail(gr.message_from_string("", -1))
    def handle(self):
        buffer = ""
        while True:
            data = ""   # Initialise to nothing so if there's an exception it'll disconnect
            try:
                data = self.request.recv(1024)
            except socket.error, (e, msg):
                if e != 104:    # Connection reset by peer
                    print "==>", self.client_address, "-", msg
            #data = self.rfile.readline().strip()
            if len(data) == 0:
                break
            
            #print "==> Received from", self.client_address, ":", data
            
            #cur_thread = threading.currentThread()
            #response = "%s: %s" % (cur_thread.getName(), data)
            #self.request.send(response)
            
            buffer += data
            lines = buffer.splitlines(True)
            for line in lines:
                if line[-1] != '\n':
                    buffer = line
                    break
                line = line.strip()
                #print "==> Submitting command:", line
                #msg = gr.message_from_string(line, -1)
                #self.server.command_queue.insert_tail(msg)
            else:
                buffer = ""
    def finish(self):
        print "==> Disconnection from:", self.client_address
        with self.server.client_lock:
            self.server.clients.remove(self)
            if len(self.server.clients) == 0:
                self.server.connect_event.clear()
        try:
            SocketServer.StreamRequestHandler.finish(self)
        except socket.error, (e, msg):
            if (e != 32): # Broken pipe
                print "==>", self.client_address, "-", msg

class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    pass

class message_server_thread(threading.Thread):
	def __init__(self, msgq, port, start=True, **kwds):
		threading.Thread.__init__(self, **kwds)
		self.setDaemon(True)
		self.msgq = msgq
		self.keep_running = True
		self.stop_event = threading.Event()
		
		HOST, PORT = "", port   # "localhost"
		print "==> Starting TCP server on port:", port
		while True:
			try:
				self.server = ThreadedTCPServer((HOST, PORT), ThreadedTCPRequestHandler)
				
				self.server.command_queue = msgq
				self.server.client_lock = threading.Lock()
				self.server.clients = []
				self.server.connect_event = threading.Event()
				
				ip, port = self.server.server_address
				self.server_thread = threading.Thread(target=self.server.serve_forever)
				self.server_thread.setDaemon(True)
				self.server_thread.start()
			except socket.error, (e, msg):
				print "    Socket error:", msg
				if (e == 98):
					print "    Waiting, then trying again..."
					time.sleep(5)
					continue
			break
		print "==> TCP server running in thread:", self.server_thread.getName()
		
		if start:
			self.start()
	def start(self):
		print "Starting..."
		threading.Thread.start(self)
	def stop(self):
		print "Stopping..."
		self.keep_running = False
		msg = gr.message()  # Empty message to signal end
		self.msgq.insert_tail(msg)
		self.stop_event.wait()
		self.server.shutdown()
		print "Stopped"
	#def __del__(self):
	#	print "DTOR"
	def run(self):
		if self.msgq:
			while self.keep_running:
				msg = self.msgq.delete_head()
				if self.keep_running == False:
					break
				try:
					#msg.type()
					
					msg_str = msg.to_string()
					with self.server.client_lock:
						for client in self.server.clients:
							try:
								client.wfile.write(msg_str + "\n")
							except socket.error, (e, msg):
								if (e != 32): # Broken pipe
									print "==>", client.client_address, "-", msg
				except Exception, e:
					print e
					traceback.print_exc()
		self.stop_event.set()

class message_server(gr.hier_block2):
	def __init__(self, msgq, port, **kwds):
		gr.hier_block2.__init__(self, "message_server",
								gr.io_signature(0, 0, 0),
								gr.io_signature(0, 0, 0))
		self.thread = message_server_thread(msgq, port, start=False, **kwds)
		self.start()
	def start(self):
		self.thread.start()
	def stop(self):
		self.thread.stop()
	def __del__(self):
		self.stop()

def main():
	return 0

if __name__ == '__main__':
	main()

########NEW FILE########
__FILENAME__ = missile_launcher
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  missile_launcher.py
#  
#  Copyright 2013 Balint Seeber <balint@crawfish>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#  

from __future__ import with_statement

import time, math, threading
import usb.core

# sec/degree
_AZIMUTH_RATE = (3.0 / 175.0)
_ELEVATION_RATE = (0.6 / 45.0)
_AZIMUTH_LIMITS = (-135.0,135.0)
_ELEVATION_LIMITS = (-5.0,25.0)
_FIRE_LOCKOUT_TIME = 3.8	# seconds (~3.7, need to wait for turret to rotate)

class missile_launcher:
	def __init__(self, azimuth=0.0, elevation=0.0, threshold=0.0, reset=True):
		#print "==> Movement threshold:", threshold
		self.dev = usb.core.find(idVendor=0x2123, idProduct=0x1010)
		if self.dev is None:
			raise ValueError('Launcher not found.')
		if self.dev.is_kernel_driver_active(0) is True:
			self.dev.detach_kernel_driver(0)
		self.dev.set_configuration()
		
		self.azimuth = 0.0
		self.elevation = 0.0
		self.fire_state = False
		self.threshold = threshold
		self.lockout = None
		self.total_azimuth_travel = 0.0
		self.calibrating = False
		self.cmd_delay = 0.1
		
		if reset:
			self.reset()
		
		self.set_elevation(elevation)
		self.set_azimuth(azimuth)
	
	def reset(self):
		print "==> Resetting turret..."
		self.calibrating = True
		self.set_elevation(-90.0, False, -5.0)
		self.set_azimuth(350.0, False, 151-7) # MAGIC # Calc'd: 141.1
		#self.set_azimuth(-350.0, False, -139.7)
		self.set_elevation(0.0)
		self.set_azimuth(0.0, from_limit=True)
		self.calibrating = False
		self.total_azimuth_travel = 0.0
		print "==> Done."
	
	def get_total_azimuth_travel(self):
		return self.total_azimuth_travel
	
	def set_azimuth(self, azimuth, check=True, actual=None, from_limit=False):
		if math.isnan(azimuth):
			return
		if azimuth == self.azimuth:
			return
		if check:
			azimuth = max(min(azimuth,_AZIMUTH_LIMITS[1]),_AZIMUTH_LIMITS[0])
		diff = azimuth - self.azimuth
		#print "==> Diff", diff
		if abs(diff) < self.threshold:
			return
		if not self._check_lockout():	# Will not fire if moved
			return
		if from_limit:
		#if False:
			if diff > 0.0:
				delay = (abs(diff) - 2.80 - 1.90) / 57.8
				#print "==> From limit CW delay:", delay
			else:
				delay = (abs(diff) - 4.16 - 0.49) / 58.85
				#print "==> From limit CCW delay:", delay
		else:
			#if diff > 0.0:
			#	delay = (abs(diff) - 7.08 + 0.65) / 57.5
			#else:
			#	delay = (abs(diff) - 10.56 + 0.82) / 57.62
			delay = (abs(diff) - 5) / 55
		if delay < 0.15:	# MAGIC
			#print "==> Fixing delay on angle diff", diff
			#delay = 0.0
			#delay = abs(diff) * _AZIMUTH_RATE
			print "==> Skipping angle", diff
			return
		if diff > 0.0:
			#print "==> Right", abs(diff)
			self.turretRight()
		else:
			#print "==> Left", abs(diff)
			self.turretLeft()
		time.sleep(delay)
		self.turretStop()
		if check and actual is None:
			self.total_azimuth_travel += abs(diff)
		
		if actual is None:
			self.azimuth = azimuth
		else:
			self.azimuth = actual
		print "==> Azimuth is now:", self.azimuth

	def set_elevation(self, elevation, check=True, actual=None):
		if math.isnan(elevation):
			return
		if elevation == self.elevation:
			return
		if check:
			elevation = max(min(elevation,_ELEVATION_LIMITS[1]),_ELEVATION_LIMITS[0])
		diff = elevation - self.elevation
		if abs(diff) < self.threshold:
			return
		if not self._check_lockout():	# Will not fire if moved
			return
		if diff > 0.0:
			self.turretUp()
		else:
			self.turretDown()
		time.sleep(abs(diff) * _ELEVATION_RATE)
		self.turretStop()
		
		if actual is None:
			self.elevation = elevation
		else:
			self.elevation = actual
	
	def launch(self, confirm=True, auto_reset=True):
		confirm = bool(confirm)
		if confirm == self.fire_state:
			return
		if confirm and self._check_lockout():
			print "==> Firing!"
			self.turretFire()
			self.lockout = time.time()
		if auto_reset:
			self.fire_state = False
		else:
			self.fire_state = confirm
	
	def is_firing(self):
		return self.fire_state
	
	def is_calibrating(self):
		return self.calibrating
	
	def _check_lockout(self):
		if self.lockout is None:
			return True
		now = time.time()
		if (now - self.lockout) < _FIRE_LOCKOUT_TIME:
			return False
		self.lockout = None
		return True
	
	def turretUp(self):
		self.dev.ctrl_transfer(0x21,0x09,0,0,[0x02,0x02,0x00,0x00,0x00,0x00,0x00,0x00])
		time.sleep(self.cmd_delay)

	def turretDown(self):
		self.dev.ctrl_transfer(0x21,0x09,0,0,[0x02,0x01,0x00,0x00,0x00,0x00,0x00,0x00])
		time.sleep(self.cmd_delay)

	def turretLeft(self):
		self.dev.ctrl_transfer(0x21,0x09,0,0,[0x02,0x04,0x00,0x00,0x00,0x00,0x00,0x00])
		time.sleep(self.cmd_delay)

	def turretRight(self):
		self.dev.ctrl_transfer(0x21,0x09,0,0,[0x02,0x08,0x00,0x00,0x00,0x00,0x00,0x00])
		time.sleep(self.cmd_delay)

	def turretStop(self):
		self.dev.ctrl_transfer(0x21,0x09,0,0,[0x02,0x20,0x00,0x00,0x00,0x00,0x00,0x00])
		time.sleep(self.cmd_delay)

	def turretFire(self):
		self.dev.ctrl_transfer(0x21,0x09,0,0,[0x02,0x10,0x00,0x00,0x00,0x00,0x00,0x00])
		time.sleep(self.cmd_delay)

class async_missile_launcher_thread(threading.Thread):
	def __init__(self, ml, streaming=False, recal_threshold=0, **kwds):
		threading.Thread.__init__ (self, **kwds)
		self.setDaemon(1)
		self.active = False
		self.ml = ml
		self.recal_threshold = recal_threshold
		self.q = []
		self.e = threading.Event()
		self.l = threading.Lock()
		self.streaming = streaming
	def get_lock(self):
		return self.l
	def start(self):
		self.active = True
		threading.Thread.start(self)
	def stop(self):
		self.e.set()
		self.active = False
	def run(self):
		while self.active:
			self.e.wait()
			self.e.clear()
			while True:
				evt = None
				with self.l:
					if len(self.q) == 0:
						break
					else:
						evt = self.q.pop()
				#print "<", evt
				evt[0](**evt[1])
				if self.recal_threshold > 0 and self.ml.get_total_azimuth_travel() > self.recal_threshold:
					print "==> Recalibration threshold reached"
					last_el = self.ml.elevation
					self.ml.reset()
					print "==> Restoring last elevation:", last_el
					self.ml.set_elevation(last_el)	# HACK
					if self.streaming:
						with self.l:
							self.q = []
	def post(self, fn, **kwds):
		with self.l:
			item = [(fn, kwds)]
			#print ">", item
			self.q = item + self.q
			self.e.set()
			return True
	def get_queue(self):
		return self.q

class async_missile_launcher():
	def __init__(self, streaming=True, recal_threshold=0, **kwds):
		self._ml = missile_launcher(**kwds)
		self._thread = async_missile_launcher_thread(self._ml, streaming, recal_threshold)
		self.streaming = streaming
		self._thread.start()
	def __del__(self):
		self._thread.stop()
	def _check_queue(self):
		if not self.streaming:
			return True
		with self._thread.get_lock():
			if len(self._thread.get_queue()) > 0:
				#print "==> Skipping"
				return False
		return True
	def set_azimuth(self, azimuth):
		if math.isnan(azimuth):
			return
		if self._check_queue():
			self._thread.post(self._ml.set_azimuth, azimuth=azimuth)
	def set_elevation(self, elevation):
		if math.isnan(elevation):
			return
		if self._check_queue():
			self._thread.post(self._ml.set_elevation, elevation=elevation)
	def launch(self, confirm=True, auto_reset=True):
		confirm = bool(confirm)
		if self.streaming:
			with self._thread.get_lock():
				if confirm == self._ml.is_firing():
					return
		self._thread.post(self._ml.launch, confirm=confirm, auto_reset=auto_reset)
	def is_calibrating(self):
		return self._ml.is_calibrating()
	def calibrate(self, cal=True):
		if cal == False:
			return
		#print "Calibrating..."
		#print "==> Recalibration threshold reached"
		#last_el = self._ml.elevation
		#self._ml.reset()
		#print "==> Restoring last elevation:", last_el
		self._thread.post(self._ml.reset)

def main():
	ml = missile_launcher(reset=False)
	ml.reset()
	# 1
	#ml.set_azimuth(270.0, False, 135.0)
	#ml.turretRight()
	#time.sleep(5)
	#ml.turretStop()
	# 2
	#ml.set_azimuth(-270.0, False, -135.0)
	#ml.turretLeft()
	#time.sleep(5)
	#ml.turretStop()
	# 3
	#ml.set_azimuth(270.0, False, 135.0)
	#ml.turretRight()
	#time.sleep(6)
	#ml.turretStop()
	#time.sleep(1)
	#ml.turretLeft()
	#time.sleep(3)
	#ml.turretStop()
	# 4
	#ml.turretLeft()
	#time.sleep(6)
	#ml.turretStop()
	#time.sleep(1)
	#ml.turretRight()
	#time.sleep(1)
	#ml.turretStop()
	# 5
	#ml.turretRight()
	#time.sleep(6)
	#ml.turretStop()
	#time.sleep(1)
	#ml.turretLeft()
	#time.sleep(1)
	#ml.turretStop()
	#raw_input()
	#ml.turretLeft()
	#time.sleep(3)
	#ml.turretStop()
	# 6
	#ml.turretLeft()
	#time.sleep(6)
	#ml.turretStop()
	#time.sleep(1)
	#ml.turretRight()
	#time.sleep(1)
	#ml.turretStop()
	#raw_input()
	#ml.turretRight()
	#time.sleep(3)
	#ml.turretStop()

def calibrate(ml):
	start = time.time()
	#ml.turretLeft()
	ml.turretUp()
	raw_input()
	ml.turretStop()
	stop = time.time()
	print (stop - start)

if __name__ == '__main__':
	main()

########NEW FILE########
__FILENAME__ = multi_channel_decoder
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  untitled.py
#  
#  Copyright 2013 Balint Seeber <balint@crawfish>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#  

import sys
from gnuradio import gr, gru
from baz import message_relay

class multi_channel_decoder(gr.hier_block2):
	def __init__(self, msgq, baseband_freq, frequencies, decoder, decoder_args=None, params={}, per_freq_params={}, **kwargs):
		gr.hier_block2.__init__(self, "multi_channel_decoder",
			gr.io_signature(1, 1, gr.sizeof_gr_complex),
			gr.io_signature(0, 0, 0))
		
		self.msgq = msgq
		self.decoder = decoder
		self.decoder_args = decoder_args or ""
		self.params = params
		self.kwargs = kwargs
		self.per_freq_params = per_freq_params
		
		self.decoders = []
		self.decoders_unused = []
		
		self.set_baseband_freq(baseband_freq)
		
		self.set_frequencies(frequencies)
	
	def set_frequencies(self, freq_list):
		current_freqs = []
		map_freqs = {}
		for decoder in self.decoders:
			current_freqs += [decoder.get_freq()]
			map_freqs[decoder.get_freq()] = decoder
		create = [f for f in freq_list if f not in current_freqs]
		remove = [f for f in current_freqs if f not in freq_list]
		try:
			decoder_factory = self.decoder
			if isinstance(self.decoder, str):
				decoder_factory = eval(self.decoder)
			#factory_eval_str = "decoder_factory(baseband_freq=%s,freq=%f,%s)" % (self.baseband_freq, f, self.decoder_args)
			for f in create:
				#d = eval(factory_eval_str)
				combined_args = self.kwargs
				combined_args['baseband_freq'] = self.baseband_freq
				combined_args['freq'] = f
				if f in self.per_freq_params:
					for k in self.per_freq_params[f].keys():
						combined_args[k] = self.per_freq_params[f][k]
				print "==> Creating decoder:", decoder_factory, "with", combined_args
				#d = decoder_factory(baseband_freq=self.baseband_freq, freq=f, **combined_args)
				d = decoder_factory(**combined_args)
				d._msgq_relay = message_relay.message_relay(self.msgq, d.msg_out.msgq())
				self.connect(self, d)
				self.decoders += [d]
		except Exception, e:
			print "Failed to create decoder:", e#, factory_eval_str
		try:
			for f in remove:
				decoder = map_freqs[f]
				self.disconnect(self, decoder)
				#self.decoders_unused += [decoder]	# FIXME: Re-use mode
		except Exception, e:
			print "Failed to remove decoder:", e
	
	def set_baseband_freq(self, baseband_freq):
		self.baseband_freq = baseband_freq
		for decoder in self.decoders:
			decoder.set_baseband_freq(baseband_freq)
	
	def update_parameters(self, params):
		for k in params:
			if k not in self.params or self.params[k] != params[k]:	# Only update those that don't exist yet or have changed
				print "Updating parameter:", k, params[k]
				for decoder in self.decoders:
					try:
						fn = getattr(decoder, k)
						fn(params[k])
					except Exception, e:
						print "Exception updating parameter in:", decoder, k, params[k]
						traceback.print_exc()
				self.params[k] = params[k]

def main():
	return 0

if __name__ == '__main__':
	main()

########NEW FILE########
__FILENAME__ = music_doa_helper
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  music_doa.py
#  
#  Copyright 2013 Balint Seeber <balint@crawfish>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#  

from gnuradio import gr, gru
import numpy
import baz

def unit_vect(theta):
    return numpy.array([numpy.cos(theta), numpy.sin(theta)])

def calculate_antenna_array_response(antenna_array, angular_resolution, l):
	response = []
	#for angle in xrange(0.0, 360.0*((angular_resolution-1)/angular_resolution), (360.0/angular_resolution)):
	for step in xrange(0, angular_resolution):
		angle = (step * 360.0 / angular_resolution) * (numpy.pi / 180.0)
		
		response_step = []
		for antenna in antenna_array:
			phase_offset = numpy.inner(antenna, unit_vect(angle)) / l	# NEGATIVISM # -angle - numpy.pi/2.0
			antenna_response = numpy.exp(-1j * 2.0 * numpy.pi * phase_offset)			# NEGATIVISM
			response_step += [antenna_response]
		
		response += [response_step]
	
	return response

class music_doa_helper(gr.hier_block2):
	def __init__(self, m, n, nsamples, angular_resolution, frequency, array_spacing, antenna_array, output_spectrum=False):
		
		self.m = m
		self.n = n
		self.nsamples = nsamples
		self.angular_resolution = angular_resolution
		self.l = 299792458.0 / frequency
		self.antenna_array = [[array_spacing * x, array_spacing * y] for [x,y] in antenna_array]
		
		if (nsamples % m) != 0:
			raise Exception("nsamples must be multiple of m")
		
		if output_spectrum:
			output_sig = gr.io_signature3(3, 3, (gr.sizeof_float * n), (gr.sizeof_float * n), (gr.sizeof_float * angular_resolution))
		else:
			output_sig = gr.io_signature2(2, 2, (gr.sizeof_float * n), (gr.sizeof_float * n))
		#	output_sig = gr.io_signature2(2, 2, (gr.sizeof_float * n), (gr.sizeof_float * angular_resolution))
		#else:
		#	output_sig = gr.io_signature(1, 1, (gr.sizeof_float * n))
		
		gr.hier_block2.__init__(self, "music_doa_helper",
								gr.io_signature(1, 1, (gr.sizeof_gr_complex * nsamples)),
								output_sig)
								#gr.io_signature3(1, 3,	(gr.sizeof_float * n),
								#						(gr.sizeof_float * angular_resolution),
								#						(gr.sizeof_float * angular_resolution)))
		
		print "MUSIC DOA Helper: M: %d, N: %d, # samples: %d, steps of %f degress, lambda: %f, array: %s" % (
			self.m,
			self.n,
			self.nsamples,
			(360.0/self.angular_resolution),
			self.l,
			str(self.antenna_array)
		)
		
		#print "--> Calculating array response..."
		self.array_response = calculate_antenna_array_response(self.antenna_array, self.angular_resolution, self.l)
		#print "--> Done."
		#print self.array_response
		self.impl = baz.music_doa(self.m, self.n, self.nsamples, self.array_response, self.angular_resolution)
		
		self.connect(self, self.impl)
		
		self.connect((self.impl, 0), (self, 0))
		self.connect((self.impl, 1), (self, 1))
		if output_spectrum:
			self.connect((self.impl, 2), (self, 2))
		#if
		#self.connect((self.impl, 2), (self, 2))
	
	def set_frequency(self, frequency):
		self.l = 299792458.0 / frequency
		self.array_response = calculate_antenna_array_response(self.antenna_array, self.angular_resolution, self.l)
		self.impl.set_array_response(self.array_response)

########NEW FILE########
__FILENAME__ = op25
#
# Copyright 2007 Free Software Foundation, Inc.
#
# This file is part of GNU Radio
#
# GNU Radio is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# GNU Radio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GNU Radio; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#

_verbose = True

import math
from gnuradio import gr, gru, op25 as _op25

try:
    from gnuradio import fsk4   # LEGACY
    if _verbose:
        print "Imported legacy fsk4"
except:
    pass

SYMBOL_DEVIATION = 600
SYMBOL_RATE = 4800

class op25_fsk4(gr.hier_block2):
    def __init__(self, channel_rate, auto_tune_msgq=None):
        gr.hier_block2.__init__(self, "op25_fsk4",
                              gr.io_signature(1, 1, gr.sizeof_float),
                              gr.io_signature(1, 1, gr.sizeof_float))
        
        self.symbol_rate = SYMBOL_RATE
        
        #print "Channel rate:", channel_rate
        self.channel_rate = channel_rate
        self.auto_tune_msgq = auto_tune_msgq
        
        if self.auto_tune_msgq is None:
            self.auto_tune_msgq = gr.msg_queue(2)
        
        # C4FM demodulator
        #print "Symbol rate:", self.symbol_rate
        try:
            self.demod_fsk4 = _op25.fsk4_demod_ff(self.auto_tune_msgq, self.channel_rate, self.symbol_rate)
            if _verbose:
                print "Using new fsk4_demod_ff"
        except:
            try:
                self.demod_fsk4 = fsk4.demod_ff(self.auto_tune_msgq, self.channel_rate, self.symbol_rate)   # LEGACY
                if _verbose:
                    print "Using legacy fsk4.demod_ff"
            except:
                raise Exception("Could not find a FSK4 demodulator to use")
        
        self.connect(self, self.demod_fsk4, self)

class op25_decoder_simple(gr.hier_block2):
    def __init__(self, traffic_msgq=None, key=None):
        gr.hier_block2.__init__(self, "op25_decoder",
                              gr.io_signature(1, 1, gr.sizeof_float),
                              gr.io_signature(1, 1, gr.sizeof_float))
        
        self.traffic_msgq = traffic_msgq
        self.key = key
        
        if self.traffic_msgq is None:
            self.traffic_msgq = gr.msg_queue(2)
        
        self.slicer = None
        try:
            levels = [ -2.0, 0.0, 2.0, 4.0 ]
            self.slicer = _op25.fsk4_slicer_fb(levels)
            self.p25_decoder = _op25.decoder_bf()
            self.p25_decoder.set_msgq(self.traffic_msgq)
            if _verbose:
                print "Using new decoder_bf"
        except:
            try:
                self.p25_decoder = _op25.decoder_ff(self.traffic_msgq)   # LEGACY
                if _verbose:
                    print "Using legacy decoder_ff"
            except:
                raise Exception("Could not find a decoder to use")
        
        if (self.key is not None) and (len(self.key) > 0): # Relates to key string passed in from GRC block
            self.set_key(self.key)
        
        if self.slicer:
            self.connect(self, self.slicer, self.p25_decoder)
        else:
            self.connect(self, self.p25_decoder)
        self.connect(self.p25_decoder, self)
    
    def set_key(self, key):
        try:
            if type(key) == str:
                if len(key) == 0:	# FIXME: Go back into the clear
                    #print "Cannot set key using empty string"
                    return False
                key = int(key, 16) # Convert from hex string
            if not hasattr(self.p25_decoder, 'set_key'):
                print "This version of the OP25 decoder does not support decryption"
                return False
            self.p25_decoder.set_key(key)
            return True
        except Exception, e:
            print "Exception while setting key:", e
            return False

class op25_decoder(gr.hier_block2):
    def __init__(self, channel_rate, auto_tune_msgq=None, defer_creation=False, output_dibits=False, key=None, traffic_msgq=None):
        num_outputs = 1
        if output_dibits:
            num_outputs += 1
        
        gr.hier_block2.__init__(self, "op25",
                              gr.io_signature(1, 1, gr.sizeof_float),
                              gr.io_signature(num_outputs, num_outputs, gr.sizeof_float))
        
        self.symbol_rate = SYMBOL_RATE
        
        #print "Channel rate:", channel_rate
        self.channel_rate = channel_rate
        self.auto_tune_msgq = auto_tune_msgq
        self.traffic_msgq = traffic_msgq
        self.output_dibits = output_dibits
        self.key = key
        self.traffic_msgq = gr.msg_queue(2)
        
        if defer_creation == False:
            self.create()
    
    def create(self):
        self.fsk4 = op25_fsk4(channel_rate=self.channel_rate, auto_tune_msgq=self.auto_tune_msgq)
        self.decoder = op25_decoder_simple(traffic_msgq=self.traffic_msgq, key=self.key)
        
        # Reference code
        #self.decode_watcher = decode_watcher(self.op25_msgq, self.traffic)
        
        # Reference code
        #trans_width = 12.5e3 / 2;
        #trans_centre = trans_width + (trans_width / 2)
        # discriminator tap doesn't do freq. xlation, FM demodulation, etc.
        #    coeffs = gr.firdes.low_pass(1.0, capture_rate, trans_centre, trans_width, gr.firdes.WIN_HANN)
        #    self.channel_filter = gr.freq_xlating_fir_filter_ccf(channel_decim, coeffs, 0.0, capture_rate)
        #    self.set_channel_offset(0.0, 0, self.spectrum.win._units)
        #    # power squelch
        #    squelch_db = 0
        #    self.squelch = gr.pwr_squelch_cc(squelch_db, 1e-3, 0, True)
        #    self.set_squelch_threshold(squelch_db)
        #    # FM demodulator
        #    fm_demod_gain = channel_rate / (2.0 * pi * self.symbol_deviation)
        #    fm_demod = gr.quadrature_demod_cf(fm_demod_gain)
        # symbol filter        
        #symbol_decim = 1
        #symbol_coeffs = gr.firdes.root_raised_cosine(1.0, channel_rate, self.symbol_rate, 0.2, 500)
        # boxcar coefficients for "integrate and dump" filter
        #samples_per_symbol = channel_rate // self.symbol_rate
        #symbol_duration = float(self.symbol_rate) / channel_rate
        #print "Symbol duration:", symbol_duration
        #print "Samples per symbol:", samples_per_symbol
        #symbol_coeffs = (1.0/samples_per_symbol,)*samples_per_symbol
        #self.symbol_filter = gr.fir_filter_fff(symbol_decim, symbol_coeffs)
        
        # Reference code
        #self.demod_watcher = demod_watcher(autotuneq, self.adjust_channel_offset)
        #list = [[self, self.channel_filter, self.squelch, fm_demod, self.symbol_filter, demod_fsk4, self.p25_decoder, self.sink]]
        
        self.connect(self, self.fsk4, self.decoder, (self, 0))
        
        if self.output_dibits:
            self.connect(self.fsk4, (self, 1))
    
    def set_key(self, key):
        try:
            if type(key) == str:
                if len(key) == 0:	# FIXME: Go back into the clear
                    #print "Cannot set key using empty string"
                    return False
                key = int(key, 16) # Convert from hex string
            if not hasattr(self.p25_decoder, 'set_key'):
                print "This version of the OP25 decoder does not support decryption"
                return False
            self.p25_decoder.set_key(key)
            return True
        except Exception, e:
            print "Exception while setting key:", e
            return False
    
    # Reference code
    #def adjust_channel_offset(self, delta_hz):
    #    max_delta_hz = 12000.0
    #    delta_hz *= self.symbol_deviation      
    #    delta_hz = max(delta_hz, -max_delta_hz)
    #    delta_hz = min(delta_hz, max_delta_hz)
    #    self.channel_filter.set_center_freq(self.channel_offset - delta_hz)

########NEW FILE########
__FILENAME__ = op25_traffic_pane
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  op25_traffic_panel.py
#  
#  Copyright 2013 Balint Seeber <balint@crawfish>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#  

import wx
import cPickle as pickle
import gnuradio.gr.gr_threading as _threading

wxDATA_EVENT = wx.NewEventType()

def EVT_DATA_EVENT(win, func):
	win.Connect(-1, -1, wxDATA_EVENT, func)

class DataEvent(wx.PyEvent):
	def __init__(self, data):
		wx.PyEvent.__init__(self)
		self.SetEventType (wxDATA_EVENT)
		self.data = data

	def Clone (self):
		self.__class__ (self.GetId())

class traffic_watcher_thread(_threading.Thread):
	def __init__(self, rcvd_pktq, event_receiver):
		_threading.Thread.__init__(self)
		self.setDaemon(1)
		self.rcvd_pktq = rcvd_pktq
		self.event_receiver = event_receiver
		self.keep_running = True
		self.start()

	def stop(self):
		self.keep_running = False

	def run(self):
		while self.keep_running:
			msg = self.rcvd_pktq.delete_head()
			de = DataEvent (msg)
			wx.PostEvent (self.event_receiver, de)
			del de

# A snapshot of important fields in current traffic
#
class TrafficPane(wx.Panel):

    # Initializer
    #
    def __init__(self, parent, msgq):
        wx.Panel.__init__(self, parent)
        
        self.msgq = msgq
        
        sizer = wx.GridBagSizer(hgap=10, vgap=10)
        self.fields = {}

        label = wx.StaticText(self, -1, "DUID:")
        sizer.Add(label, pos=(1,1))
        field = wx.TextCtrl(self, -1, "", size=(144, -1), style=wx.TE_READONLY)
        sizer.Add(field, pos=(1,2))
        self.fields["duid"] = field;

        label = wx.StaticText(self, -1, "NAC:")
        sizer.Add(label, pos=(2,1))
        field = wx.TextCtrl(self, -1, "", size=(144, -1), style=wx.TE_READONLY)
        sizer.Add(field, pos=(2,2))
        self.fields["nac"] = field;

        label = wx.StaticText(self, -1, "Source:")
        sizer.Add(label, pos=(3,1))
        field = wx.TextCtrl(self, -1, "", size=(144, -1), style=wx.TE_READONLY)
        sizer.Add(field, pos=(3,2))
        self.fields["source"] = field;

        label = wx.StaticText(self, -1, "Destination:")
        sizer.Add(label, pos=(4,1))
        field = wx.TextCtrl(self, -1, "", size=(144, -1), style=wx.TE_READONLY)
        sizer.Add(field, pos=(4,2))
        self.fields["dest"] = field;

        label = wx.StaticText(self, -1, "MFID:")
        sizer.Add(label, pos=(1,4))
        field = wx.TextCtrl(self, -1, "", size=(144, -1), style=wx.TE_READONLY)
        sizer.Add(field, pos=(1,5))
        self.fields["mfid"] = field;

        label = wx.StaticText(self, -1, "ALGID:")
        sizer.Add(label, pos=(2,4))
        field = wx.TextCtrl(self, -1, "", size=(144, -1), style=wx.TE_READONLY)
        sizer.Add(field, pos=(2,5))
        self.fields["algid"] = field;

        label = wx.StaticText(self, -1, "KID:")
        sizer.Add(label, pos=(3,4))
        field = wx.TextCtrl(self, -1, "", size=(144, -1), style=wx.TE_READONLY)
        sizer.Add(field, pos=(3,5))
        self.fields["kid"] = field;

        label = wx.StaticText(self, -1, "MI:")
        sizer.Add(label, pos=(4,4))
        field = wx.TextCtrl(self, -1, "", size=(216, -1), style=wx.TE_READONLY)
        sizer.Add(field, pos=(4,5))
        self.fields["mi"] = field;

        label = wx.StaticText(self, -1, "TGID:")
        sizer.Add(label, pos=(5,4))
        field = wx.TextCtrl(self, -1, "", size=(144, -1), style=wx.TE_READONLY)
        sizer.Add(field, pos=(5,5))
        self.fields["tgid"] = field;

        self.SetSizer(sizer)
        self.Fit()
        
        EVT_DATA_EVENT(self, self.display_data)
        self.watcher = traffic_watcher_thread(self.msgq, self)

    # Clear the field values
    #
    def clear(self):
        for v in self.fields.values():
            v.Clear()
    
    def display_data(self,event):
        message = event.data
        pickled_dict = message.to_string()
        attrs = pickle.loads(pickled_dict)
        self.update(attrs)

    # Update the field values
    #
    def update(self, field_values):
        if field_values['duid'] == 'hdu':
            self.clear()
        for k,v in self.fields.items():
            f = field_values.get(k, None)
            if f:
                v.SetValue(f)

def main():
	return 0

if __name__ == '__main__':
	main()

########NEW FILE########
__FILENAME__ = parallel_scanner_fsm
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  parallel_scanner_fsm.py
#  
#  Copyright 2013 Balint Seeber <balint@crawfish>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#  

import gnuradio.gr.gr_threading as _threading
import struct, datetime, time, traceback, itertools

class fsm(_threading.Thread):
	def __init__(self, msgq, callback=None, sink=None, baseband_freq=0):
		_threading.Thread.__init__(self)
		self.setDaemon(1)
		self.msgq = msgq
		self.callback = callback
		self.sink = sink
		self.baseband_freq = baseband_freq
		self.keep_running = True
		#self.unmuted = False
		self.active_freq = None
		self.start()
	def stop(self):
		print "Stopping..."
		self.keep_running = False
	def run(self):
		while self.keep_running:
			msg = self.msgq.delete_head()
			
			try:
				msg_str = msg.to_string()
				offset = struct.unpack("Q", msg_str[0:8])
				msg_str = msg_str[8:]
				
				params = msg_str.split('\0')
				src_id = None
				key = None
				val = None
				appended = None
				freq_offset = None
				
				try:
					src_id = params[0]
					key = params[1]
					val = params[2]
					appended = params[3]
					freq_offset = float(appended)
				except Exception, e:
					print "Exception while unpacking message:", e
					traceback.print_exc()
				
				#print src_id, key, val, appended
				
				if val == 'unmuted':
					print "[", self.active_freq, "]", src_id, key, val, appended
					colour = (0.,0.,0.)
					if self.active_freq == None:
						print "Unmuted at", self.baseband_freq+freq_offset
						#self.unmuted = True
						self.active_freq = freq_offset
						self.callback(freq_offset)
						colour = (0.0,0.8,0.0)
					if self.sink is not None:
						self.sink.set_line({'id':freq_offset,'type':'v','offset':self.baseband_freq+freq_offset,'action':True,'colour':colour})
				elif val == 'muted':
					if self.sink is not None:
						self.sink.set_line({'id':freq_offset,'action':False})
					print "[", self.active_freq, "]", src_id, key, val, appended
					if self.active_freq == freq_offset:
						print "Muted."
						self.active_freq = None
			except Exception, e:
					print "Exception while decoding message:", e
					traceback.print_exc()

def main():
	return 0

if __name__ == '__main__':
	main()

########NEW FILE########
__FILENAME__ = plot_sink
#
# Copyright 2008,2009,2010 Free Software Foundation, Inc.
#
# This file is part of GNU Radio
#
# GNU Radio is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# GNU Radio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GNU Radio; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#

from __future__ import division

##################################################
# Imports
##################################################
from gnuradio import gr, blks2
from gnuradio.wxgui import common
from gnuradio.wxgui.pubsub import pubsub
from gnuradio.wxgui.constants import *
import math

import plot_window

##################################################
# Plot sink block (wrapper for old wxgui)
##################################################
class plot_sink_f(gr.hier_block2, common.wxgui_hb):
	"""
	An plotting block with real inputs and a gui window.
	"""
	def __init__(
		self,
		parent,
		ref_scale=2.0,
		y_per_div=10,
		y_divs=8,
		ref_level=50,
		sample_rate=1,
		data_len=1024,
		update_rate=plot_window.DEFAULT_FRAME_RATE,
		average=False,
		avg_alpha=None,
		title='',
		size=plot_window.DEFAULT_WIN_SIZE,
		peak_hold=False,
		use_persistence=False,
		persist_alpha=None,
		**kwargs #do not end with a comma
	):
		#ensure avg alpha
		if avg_alpha is None:
			avg_alpha = 2.0/update_rate
		#ensure analog alpha
		if persist_alpha is None:
			actual_update_rate=float(sample_rate/data_len)/float(max(1,int(float((sample_rate/data_len)/update_rate))))
			#print "requested_specest_rate ",update_rate
			#print "actual_update_rate    ",actual_update_rate
			analog_cutoff_freq=0.5 # Hertz
			#calculate alpha from wanted cutoff freq
			persist_alpha = 1.0 - math.exp(-2.0*math.pi*analog_cutoff_freq/actual_update_rate)
		
		self._average = average
		self._avg_alpha = avg_alpha
		self._sample_rate = sample_rate
		
		#init
		gr.hier_block2.__init__(
			self,
			"plot_sink",
			gr.io_signature(1, 1, gr.sizeof_float*data_len),
			gr.io_signature(0, 0, 0),
		)
		#blocks
		msgq = gr.msg_queue(2)
		sink = gr.message_sink(gr.sizeof_float*data_len, msgq, True)
		
		#controller
		self.controller = pubsub()
		self.controller.subscribe(AVERAGE_KEY, self.set_average)
		self.controller.publish(AVERAGE_KEY, self.average)
		self.controller.subscribe(AVG_ALPHA_KEY, self.set_avg_alpha)
		self.controller.publish(AVG_ALPHA_KEY, self.avg_alpha)
		self.controller.subscribe(SAMPLE_RATE_KEY, self.set_sample_rate)
		self.controller.publish(SAMPLE_RATE_KEY, self.sample_rate)
		#start input watcher
		common.input_watcher(msgq, self.controller, MSG_KEY)
		#create window
		self.win = plot_window.plot_window(
			parent=parent,
			controller=self.controller,
			size=size,
			title=title,
			data_len=data_len,
			sample_rate_key=SAMPLE_RATE_KEY,
			y_per_div=y_per_div,
			y_divs=y_divs,
			ref_level=ref_level,
			average_key=AVERAGE_KEY,
			avg_alpha_key=AVG_ALPHA_KEY,
			peak_hold=peak_hold,
			msg_key=MSG_KEY,
			use_persistence=use_persistence,
			persist_alpha=persist_alpha,
		)
		common.register_access_methods(self, self.win)
		setattr(self.win, 'set_peak_hold', getattr(self, 'set_peak_hold')) #BACKWARDS
		self.wxgui_connect(self, sink)
	def set_average(self, ave):
		self._average = ave
	def average(self):
		return self._average
	def set_avg_alpha(self, ave):
		self._avg_alpha = ave
	def avg_alpha(self):
		return self._avg_alpha
	def set_sample_rate(self, rate):
		self._sample_rate = rate
	def sample_rate(self):
		return self._sample_rate

# ----------------------------------------------------------------
# Standalone test app
# ----------------------------------------------------------------

import wx
from gnuradio.wxgui import stdgui2

class test_app_block (stdgui2.std_top_block):
	def __init__(self, frame, panel, vbox, argv):
		stdgui2.std_top_block.__init__ (self, frame, panel, vbox, argv)

		data_len = 1024

		# build our flow graph
		input_rate = 2e6

		#Generate some noise
		noise = gr.noise_source_c(gr.GR_GAUSSIAN, 1.0/10)

		# Generate a complex sinusoid
		#source = gr.file_source(gr.sizeof_gr_complex, 'foobar2.dat', repeat=True)

		src1 = gr.sig_source_c (input_rate, gr.GR_SIN_WAVE, -500e3, 1)
		src2 = gr.sig_source_c (input_rate, gr.GR_SIN_WAVE, 500e3, 1)
		src3 = gr.sig_source_c (input_rate, gr.GR_SIN_WAVE, -250e3, 2)

		# We add these throttle blocks so that this demo doesn't
		# suck down all the CPU available.  Normally you wouldn't use these.
		thr1 = gr.throttle(gr.sizeof_gr_complex, input_rate)

		sink1 = plot_sink_f (panel, title="Spectrum Sink", data_len=data_len,
							sample_rate=input_rate,
							ref_level=0, y_per_div=20, y_divs=10)
		vbox.Add (sink1.win, 1, wx.EXPAND)

		combine1=gr.add_cc()
		self.connect(src1,(combine1,0))
		self.connect(src2,(combine1,1))
		self.connect(src3,(combine1,2))
		self.connect(noise, (combine1,3))
		self.connect(combine1,thr1, sink1)

def main ():
	app = stdgui2.stdapp (test_app_block, "Plot Sink Test App")
	app.MainLoop ()

if __name__ == '__main__':
	main ()

########NEW FILE########
__FILENAME__ = plot_window
#
# Copyright 2008, 2009, 2010 Free Software Foundation, Inc.
#
# This file is part of GNU Radio
#
# GNU Radio is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# GNU Radio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GNU Radio; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#

##################################################
# Imports
##################################################
from gnuradio.wxgui import plotter, common, pubsub
import wx
import numpy
import math
from gnuradio.wxgui.constants import *
from gnuradio import gr #for gr.prefs
from gnuradio.wxgui import forms

##################################################
# Constants
##################################################
SLIDER_STEPS = 100
AVG_ALPHA_MIN_EXP, AVG_ALPHA_MAX_EXP = -3, 0
PERSIST_ALPHA_MIN_EXP, PERSIST_ALPHA_MAX_EXP = -2, 0
DEFAULT_WIN_SIZE = (600, 300)
DEFAULT_FRAME_RATE = gr.prefs().get_long('wxgui', 'fft_rate', 30)
DB_DIV_MIN, DB_DIV_MAX = 1, 20
SPECTRUM_PLOT_COLOR_SPEC = (0.3, 0.3, 1.0)
PEAK_VALS_COLOR_SPEC = (0.0, 0.8, 0.0)
EMPTY_TRACE = list()
TRACES = ('A', 'B')
TRACES_COLOR_SPEC = {
	'A': (1.0, 0.0, 0.0),
	'B': (0.8, 0.0, 0.8),
}

##################################################
# Spectrum window control panel
##################################################
class control_panel(wx.Panel):
	"""
	A control panel with wx widgits to control the plotter and specest block chain.
	"""

	def __init__(self, parent):
		"""
		Create a new control panel.
		@param parent the wx parent window
		"""
		self.parent = parent
		wx.Panel.__init__(self, parent, style=wx.SUNKEN_BORDER)
		parent[SHOW_CONTROL_PANEL_KEY] = True
		parent.subscribe(SHOW_CONTROL_PANEL_KEY, self.Show)
		control_box = wx.BoxSizer(wx.VERTICAL)
		control_box.AddStretchSpacer()
		#checkboxes for average and peak hold
		options_box = forms.static_box_sizer(
			parent=self, sizer=control_box, label='Trace Options',
			bold=True, orient=wx.VERTICAL,
		)
		forms.check_box(
			sizer=options_box, parent=self, label='Peak Hold',
			ps=parent, key=PEAK_HOLD_KEY,
		)
		forms.check_box(
			sizer=options_box, parent=self, label='Average',
			ps=parent, key=AVERAGE_KEY,
		)
		#static text and slider for averaging
		avg_alpha_text = forms.static_text(
			sizer=options_box, parent=self, label='Avg Alpha',
			converter=forms.float_converter(lambda x: '%.4f'%x),
			ps=parent, key=AVG_ALPHA_KEY, width=50,
		)
		avg_alpha_slider = forms.log_slider(
			sizer=options_box, parent=self,
			min_exp=AVG_ALPHA_MIN_EXP,
			max_exp=AVG_ALPHA_MAX_EXP,
			num_steps=SLIDER_STEPS,
			ps=parent, key=AVG_ALPHA_KEY,
		)
		for widget in (avg_alpha_text, avg_alpha_slider):
			parent.subscribe(AVERAGE_KEY, widget.Enable)
			widget.Enable(parent[AVERAGE_KEY])
			parent.subscribe(AVERAGE_KEY, widget.ShowItems)
                        #allways show initially, so room is reserved for them
			widget.ShowItems(True) # (parent[AVERAGE_KEY])
                parent.subscribe(AVERAGE_KEY, self._update_layout)

		forms.check_box(
			sizer=options_box, parent=self, label='Persistence',
			ps=parent, key=USE_PERSISTENCE_KEY,
		)
		#static text and slider for persist alpha
		persist_alpha_text = forms.static_text(
			sizer=options_box, parent=self, label='Persist Alpha',
			converter=forms.float_converter(lambda x: '%.4f'%x),
			ps=parent, key=PERSIST_ALPHA_KEY, width=50,
		)
		persist_alpha_slider = forms.log_slider(
			sizer=options_box, parent=self,
			min_exp=PERSIST_ALPHA_MIN_EXP,
			max_exp=PERSIST_ALPHA_MAX_EXP,
			num_steps=SLIDER_STEPS,
			ps=parent, key=PERSIST_ALPHA_KEY,
		)
		for widget in (persist_alpha_text, persist_alpha_slider):
			parent.subscribe(USE_PERSISTENCE_KEY, widget.Enable)
			widget.Enable(parent[USE_PERSISTENCE_KEY])
			parent.subscribe(USE_PERSISTENCE_KEY, widget.ShowItems)
                        #allways show initially, so room is reserved for them
			widget.ShowItems(True) # (parent[USE_PERSISTENCE_KEY])
                parent.subscribe(USE_PERSISTENCE_KEY, self._update_layout)

		#trace menu
		for trace in TRACES:
			trace_box = wx.BoxSizer(wx.HORIZONTAL)
			options_box.Add(trace_box, 0, wx.EXPAND)
			forms.check_box(
				sizer=trace_box, parent=self,
				ps=parent, key=TRACE_SHOW_KEY+trace,
				label='Trace %s'%trace,
			)
			trace_box.AddSpacer(10)
			forms.single_button(
				sizer=trace_box, parent=self,
				ps=parent, key=TRACE_STORE_KEY+trace,
				label='Store', style=wx.BU_EXACTFIT,
			)
			trace_box.AddSpacer(10)
		#radio buttons for div size
		control_box.AddStretchSpacer()
		y_ctrl_box = forms.static_box_sizer(
			parent=self, sizer=control_box, label='Axis Options',
			bold=True, orient=wx.VERTICAL,
		)
		forms.incr_decr_buttons(
			parent=self, sizer=y_ctrl_box, label='dB/Div',
			on_incr=self._on_incr_db_div, on_decr=self._on_decr_db_div,
		)
		#ref lvl buttons
		forms.incr_decr_buttons(
			parent=self, sizer=y_ctrl_box, label='Ref Level',
			on_incr=self._on_incr_ref_level, on_decr=self._on_decr_ref_level,
		)
		y_ctrl_box.AddSpacer(2)
		#autoscale
		forms.single_button(
			sizer=y_ctrl_box, parent=self, label='Autoscale',
			callback=self.parent.autoscale,
		)
		#run/stop
		control_box.AddStretchSpacer()
		forms.toggle_button(
			sizer=control_box, parent=self,
			true_label='Stop', false_label='Run',
			ps=parent, key=RUNNING_KEY,
		)
		#set sizer
		self.SetSizerAndFit(control_box)

		#mouse wheel event
		def on_mouse_wheel(event):
			if event.GetWheelRotation() < 0: self._on_incr_ref_level(event)
			else: self._on_decr_ref_level(event)
		parent.plotter.Bind(wx.EVT_MOUSEWHEEL, on_mouse_wheel)

	##################################################
	# Event handlers
	##################################################
	def _on_incr_ref_level(self, event):
		self.parent[REF_LEVEL_KEY] = self.parent[REF_LEVEL_KEY] + self.parent[Y_PER_DIV_KEY]
	def _on_decr_ref_level(self, event):
		self.parent[REF_LEVEL_KEY] = self.parent[REF_LEVEL_KEY] - self.parent[Y_PER_DIV_KEY]
	def _on_incr_db_div(self, event):
		self.parent[Y_PER_DIV_KEY] = min(DB_DIV_MAX, common.get_clean_incr(self.parent[Y_PER_DIV_KEY]))
	def _on_decr_db_div(self, event):
		self.parent[Y_PER_DIV_KEY] = max(DB_DIV_MIN, common.get_clean_decr(self.parent[Y_PER_DIV_KEY]))
	##################################################
	# subscriber handlers
	##################################################
        def _update_layout(self,key):
          # Just ignore the key value we get
          # we only need to now that the visability or size of something has changed
          self.parent.Layout()
          #self.parent.Fit()

##################################################
# Spectrum window with plotter and control panel
##################################################
class plot_window(wx.Panel, pubsub.pubsub):
	def __init__(
		self,
		parent,
		controller,
		size,
		title,
		data_len,
		sample_rate_key,
		y_per_div,
		y_divs,
		ref_level,
		average_key,
		avg_alpha_key,
		peak_hold,
		msg_key,
		use_persistence,
		persist_alpha,
		baseband_freq=0,
	):
		self.data_len = data_len
		pubsub.pubsub.__init__(self)
		#setup
		self.samples = EMPTY_TRACE
		self.data_len = data_len
		self._reset_peak_vals()
		self._traces = dict()
		#proxy the keys
		self.proxy(MSG_KEY, controller, msg_key)
		self.proxy(AVERAGE_KEY, controller, average_key)
		self.proxy(AVG_ALPHA_KEY, controller, avg_alpha_key)
		self.proxy(SAMPLE_RATE_KEY, controller, sample_rate_key)
		#initialize values
		self[PEAK_HOLD_KEY] = peak_hold
		self[Y_PER_DIV_KEY] = y_per_div
		self[Y_DIVS_KEY] = y_divs
		self[X_DIVS_KEY] = 8 #approximate
		self[REF_LEVEL_KEY] = ref_level
		self[BASEBAND_FREQ_KEY] = baseband_freq
		self[RUNNING_KEY] = True
		self[USE_PERSISTENCE_KEY] = use_persistence
		self[PERSIST_ALPHA_KEY] = persist_alpha
		for trace in TRACES:
			#a function that returns a function
			#so the function wont use local trace
			def new_store_trace(my_trace):
				def store_trace(*args):
					self._traces[my_trace] = self.samples
					self.update_grid()
				return store_trace
			def new_toggle_trace(my_trace):
				def toggle_trace(toggle):
					#do an automatic store if toggled on and empty trace
					if toggle and not len(self._traces[my_trace]):
						self._traces[my_trace] = self.samples
					self.update_grid()
				return toggle_trace
			self._traces[trace] = EMPTY_TRACE
			self[TRACE_STORE_KEY+trace] = False
			self[TRACE_SHOW_KEY+trace] = False
			self.subscribe(TRACE_STORE_KEY+trace, new_store_trace(trace))
			self.subscribe(TRACE_SHOW_KEY+trace, new_toggle_trace(trace))
		#init panel and plot
		wx.Panel.__init__(self, parent, style=wx.SIMPLE_BORDER)
		self.plotter = plotter.channel_plotter(self)
		self.plotter.SetSize(wx.Size(*size))
		self.plotter.set_title(title)
		self.plotter.enable_legend(True)
		self.plotter.enable_point_label(True)
		self.plotter.enable_grid_lines(True)
		self.plotter.set_use_persistence(use_persistence)
		self.plotter.set_persist_alpha(persist_alpha)
		#setup the box with plot and controls
		self.control_panel = control_panel(self)
		main_box = wx.BoxSizer(wx.HORIZONTAL)
		main_box.Add(self.plotter, 1, wx.EXPAND)
		main_box.Add(self.control_panel, 0, wx.EXPAND)
		self.SetSizerAndFit(main_box)
		#register events
		self.subscribe(AVERAGE_KEY, self._reset_peak_vals)
		self.subscribe(MSG_KEY, self.handle_msg)
		self.subscribe(SAMPLE_RATE_KEY, self.update_grid)
		for key in (
			BASEBAND_FREQ_KEY,
			Y_PER_DIV_KEY, X_DIVS_KEY,
			Y_DIVS_KEY, REF_LEVEL_KEY,
		): self.subscribe(key, self.update_grid)
		self.subscribe(USE_PERSISTENCE_KEY, self.plotter.set_use_persistence)
		self.subscribe(PERSIST_ALPHA_KEY, self.plotter.set_persist_alpha)
		#initial update
		self.update_grid()

	def get_exp(self,num):
		"""
		Get the exponent of the number in base 10.
		@param num the floating point number
		@return the exponent as an integer
		"""
		if num == 0: return 0
		return int(math.floor(math.log10(abs(num))))

	def get_clean_num(self,num):
		"""
		Get the closest clean number match to num with bases 1, 2, 5.
		@param num the number
		@return the closest number
		"""
		if num == 0: return 0
		sign = num > 0 and 1 or -1
		exp = self.get_exp(num)
		nums = numpy.array((1, 2, 5, 10))*(10**exp)
		print nums
		print num
		return sign*nums[numpy.argmin(numpy.abs(nums - abs(num)))]

	def autoscale(self, *args):
		"""
		Autoscale the plot to the last frame.
		Set the dynamic range and reference level.
		"""
		if not len(self.samples): return
		min_level, max_level = common.get_min_max_fft(self.samples)
		#set the range to a clean number of the dynamic range
		self[Y_PER_DIV_KEY] = self.get_clean_num(1+(max_level - min_level)/self[Y_DIVS_KEY])
		#set the reference level to a multiple of y per div
		self[REF_LEVEL_KEY] = self[Y_PER_DIV_KEY]*round(.5+max_level/self[Y_PER_DIV_KEY])

	def _reset_peak_vals(self, *args): self.peak_vals = EMPTY_TRACE

	def handle_msg(self, msg):
		"""
		Handle the message from the sink message queue.
		Plot the samples onto the grid as channel 1.
		If peak hold is enabled, plot peak vals as channel 2.
		@param msg the array as a character array
		"""
		if not self[RUNNING_KEY]: return
		#convert to floating point numbers
		samples = numpy.fromstring(msg, numpy.float32)[:self.data_len] #only take first frame
		num_samps = len(samples)
		self.samples = samples
		#peak hold calculation
		if self[PEAK_HOLD_KEY]:
			if len(self.peak_vals) != len(samples): self.peak_vals = samples
			self.peak_vals = numpy.maximum(samples, self.peak_vals)
			#plot the peak hold
			self.plotter.set_waveform(
				channel='Peak',
				samples=self.peak_vals,
				color_spec=PEAK_VALS_COLOR_SPEC,
			)
		else:
			self._reset_peak_vals()
			self.plotter.clear_waveform(channel='Peak')
		#plot the spectrum
		self.plotter.set_waveform(
			channel='Data',
			samples=samples,
			color_spec=SPECTRUM_PLOT_COLOR_SPEC,
		)
		#update the plotter
		self.plotter.update()

	def update_grid(self, *args):
		"""
		Update the plotter grid.
		This update method is dependent on the variables below.
		Determine the x and y axis grid parameters.
		The x axis depends on sample rate, baseband freq, and x divs.
		The y axis depends on y per div, y divs, and ref level.
		"""
		for trace in TRACES:
			channel = '%s'%trace.upper()
			if self[TRACE_SHOW_KEY+trace]:
				self.plotter.set_waveform(
					channel=channel,
					samples=self._traces[trace],
					color_spec=TRACES_COLOR_SPEC[trace],
				)
			else: self.plotter.clear_waveform(channel=channel)
		#grid parameters
		sample_rate = self[SAMPLE_RATE_KEY]
		baseband_freq = self[BASEBAND_FREQ_KEY]
		y_per_div = self[Y_PER_DIV_KEY]
		y_divs = self[Y_DIVS_KEY]
		x_divs = self[X_DIVS_KEY]
		ref_level = self[REF_LEVEL_KEY]
		#determine best fitting x_per_div
		x_width = self.data_len/1.0
		x_per_div = common.get_clean_num(x_width/x_divs)
		#update the x grid
		self.plotter.set_x_grid(
			0,				#baseband_freq - sample_rate/2.0,
			self.data_len/1.0,	#baseband_freq + sample_rate/2.0,
			x_per_div, True,
		)
		#update x units
		self.plotter.set_x_label('Data', '')	# 'Hz'
		#update y grid
		self.plotter.set_y_grid(ref_level-y_per_div*y_divs, ref_level, y_per_div)
		#update y units
		self.plotter.set_y_label('Amplitude', 'dB')
		#update plotter
		self.plotter.update()

########NEW FILE########
__FILENAME__ = qa_howto
#!/usr/bin/env python
#
# Copyright 2004,2007 Free Software Foundation, Inc.
# 
# This file is part of GNU Radio
# 
# GNU Radio is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# GNU Radio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with GNU Radio; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
# 

from gnuradio import gr, gr_unittest
import baz_swig

class qa_baz (gr_unittest.TestCase):

    def setUp (self):
        self.tb = gr.top_block ()

    def tearDown (self):
        self.tb = None

    #def test_001_square_ff (self):
    #    src_data = (-3, 4, -5.5, 2, 3)
    #    expected_result = (9, 16, 30.25, 4, 9)
    #    src = gr.vector_source_f (src_data)
    #    sqr = howto_swig.square_ff ()
    #    dst = gr.vector_sink_f ()
    #    self.tb.connect (src, sqr)
    #    self.tb.connect (sqr, dst)
    #    self.tb.run ()
    #    result_data = dst.data ()
    #    self.assertFloatTuplesAlmostEqual (expected_result, result_data, 6)

    #def test_002_square2_ff (self):
    #    src_data = (-3, 4, -5.5, 2, 3)
    #    expected_result = (9, 16, 30.25, 4, 9)
    #    src = gr.vector_source_f (src_data)
    #    sqr = howto_swig.square2_ff ()
    #    dst = gr.vector_sink_f ()
    #    self.tb.connect (src, sqr)
    #    self.tb.connect (sqr, dst)
    #    self.tb.run ()
    #    result_data = dst.data ()
    #    self.assertFloatTuplesAlmostEqual (expected_result, result_data, 6)
        
if __name__ == '__main__':
    gr_unittest.main ()

########NEW FILE########
__FILENAME__ = radar_server
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  radar_server.py
#  
#  Copyright 2013 Balint Seeber <balint@crawfish>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#  

from __future__ import with_statement

import threading, traceback, socket, SocketServer, time, base64, sys

from gnuradio import gr, gru

class my_queue():
    def __init__(self):
        self.lock = threading.Lock()
        self.q = []
        self.event = threading.Event()
    def insert_tail(self, msg):
        with self.lock:
            self.q += [msg]
            self.event.set()
    def wait(self):
        self.event.wait()
        self.event.clear()
    def delete_head(self, blocking=True):
        if blocking:
            self.event.wait()
            self.event.clear()
        with self.lock:
            if len(self.q) == 0:
                return None
            msg = self.q[0]
            self.q = self.q[1:]
            return msg
    #def is_empty(self):
    #    pass

class ThreadedTCPRequestHandler(SocketServer.StreamRequestHandler): # BaseRequestHandler
    # No __init__
    def setup(self):
        SocketServer.StreamRequestHandler.setup(self)
        print "==> Connection from:", self.client_address
        self.request.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)
        with self.server.client_lock:
            self.server.clients.append(self)
        self.server.connect_event.set()
        #self.server.command_queue.insert_tail("")
    def handle(self):
        buffer = ""
        while True:
            data = ""   # Initialise to nothing so if there's an exception it'll disconnect
            try:
                data = self.request.recv(1024)
            except socket.error, (e, msg):
                if e != 104:    # Connection reset by peer
                    print "==>", self.client_address, "-", msg
            #data = self.rfile.readline().strip()
            if len(data) == 0:
                break
            
            #print "==> Received from", self.client_address, ":", data
            
            #cur_thread = threading.currentThread()
            #response = "%s: %s" % (cur_thread.getName(), data)
            #self.request.send(response)
            
            buffer += data
            lines = buffer.splitlines(True)
            for line in lines:
                if line[-1] != '\n':
                    buffer = line
                    break
                line = line.strip()
                #print "==> Submitting command:", line
                self.server.command_queue.insert_tail(line)
            else:
                buffer = ""
    def finish(self):
        print "==> Disconnection from:", self.client_address
        with self.server.client_lock:
            self.server.clients.remove(self)
            if len(self.server.clients) == 0:
                self.server.connect_event.clear()
        try:
            SocketServer.StreamRequestHandler.finish(self)
        except socket.error, (e, msg):
            if (e != 32): # Broken pipe
                print "==>", self.client_address, "-", msg

class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    pass

class radar_server_control_thread(threading.Thread):
	def __init__(self, radar, port, start=True, **kwds):
		threading.Thread.__init__(self, **kwds)
		self.setDaemon(True)
		self.keep_running = True
		self.stop_event = threading.Event()
		self.radar = radar
		
		HOST, PORT = "", port   # "localhost"
		print "==> Starting TCP server on port:", port
		while True:
			try:
				self.server = ThreadedTCPServer((HOST, PORT), ThreadedTCPRequestHandler)
				
				self.server.command_queue = my_queue()
				self.server.client_lock = threading.Lock()
				self.server.clients = []
				self.server.connect_event = threading.Event()
				
				ip, port = self.server.server_address
				self.server_thread = threading.Thread(target=self.server.serve_forever)
				self.server_thread.setDaemon(True)
				self.server_thread.start()
			except socket.error, (e, msg):
				print "    Socket error:", msg
				if (e == 98):
					print "    Waiting, then trying again..."
					time.sleep(5)
					continue
			break
		print "==> TCP server running in thread:", self.server_thread.getName()
		
		if start:
			self.start()
	def start(self):
		print "Starting..."
		threading.Thread.start(self)
	def stop(self):
		print "Stopping..."
		self.keep_running = False
		msg = ""  # Empty message to signal end
		self.server.command_queue.insert_tail(msg)
		self.stop_event.wait()
		self.server.shutdown()
		print "Stopped"
	#def __del__(self):
	#	print "DTOR"
	def send_to_clients(self, strMsg):
		strMsg = strMsg.strip("\r\n") + "\n"

		with self.server.client_lock:
			for client in self.server.clients:
				try:
					client.wfile.write(strMsg)
				except socket.error, (e, msg):
					if (e != 32): # Broken pipe
						print "==>", client.client_address, "-", msg
	def run(self):
		#self.server.connect_event.wait()	# Wait for first connection
		
		radar = self.radar
		
		running = False
		freq = None
		freq_start = 4920
		freq_stop = 6100
		freq_step = 5
		interval = 1.0
		
		while self.keep_running:
			try:
				strMsg = None
				
				if not running:
					self.server.command_queue.wait()
				
				while True:
					command = self.server.command_queue.delete_head(False)
					
					if self.keep_running == False:
						break
					
					if command is not None:
						print "  > Processing command: \"%s\"" % (command)
						
						parts = command.split(" ")
						command = parts[0].upper()
						try:
							if command == "FREQ" and len(parts) > 1:
								freq = int(parts[1])
								if freq_start == freq_stop:
									freq_start = freq_stop = freq
								if radar.set_freq(freq):
									radar.clear_radar_queue()
									strMsg = "FREQ " + str(freq)
								else:
									print "Failed to set frequency %d" % (freq)
							
							elif (command == "FIRPWR" or command == "RSSI" or command == "PHEIGHT" or command == "PRSSI" or command == "INBAND") and len(parts) > 1:
								value = int(parts[1])
								#param = command.lower()
								#cmd = param + " " + str(value)
								#radar.write_param(cmd)
								radar.set_param(command, value)
							
							elif command == "STOP":
								running = False
							
							elif command == "START":
								if len(parts) > 1:
									freq_start = int(parts[1])
								if len(parts) > 2:
									freq_stop = int(parts[2])
								if len(parts) > 3:
									freq_step = abs(int(parts[3]))
								if len(parts) > 4:
									interval = float(parts[4])
								running = True
								freq = None
							
							elif command == "QUIT" or command == "EXIT":
								break
						except Exception, e:
							print e
					else:
						break
				
				if running:
					freq_change = False
				
					if freq is not None:
						if freq_start == freq_stop:
							pass
						else:
							if freq_start < freq_stop:
								freq += freq_step
								if freq > freq_stop:
									running = False
							else:
								freq -= freq_step
								if freq < freq_stop:
									running = False
							if running:
								freq_change = True
					else:
						freq = freq_start
						freq_change = True
					
					if running:
						go = True
					
						if freq_change:
							#print "Setting frequency %d" % (freq)
							if radar.set_freq(freq):
								radar.clear_radar_queue()
							else:
								print "Failed to set frequency %d" % (freq)
								go = False
						
						if go:
							time.sleep(interval)
							
							(cnt, data) = radar.read_queue(True)
							
							#print "Queue: %d items (length: %d)" % (cnt, len(data))
							
							#strMsg = "DATA " + str(freq) + " " + str(cnt)# + " " + data	# No longer using this way
							strMsg = "DATA " + str(freq) + " " + base64.b64encode(data)
							
							#if options.progress:
							#	sys.stdout.write(".")
							#	sys.stdout.flush()
					else:
						strMsg = "END"
				
				if strMsg is not None:
					self.send_to_clients(strMsg)
				
				with self.server.client_lock:
					if len(self.server.clients) == 0 and running:
						running = False
			except Exception, e:
				print e
				traceback.print_exc()
		self.stop_event.set()

class radar_error():
	def __init__(self, item):
		self.tsf = item[0]
		self.rssi = ord(item[1])
		self.width = ord(item[2])
		self.type = ord(item[3])
		self.subtype = ord(item[4])
		self.overflow = 0

class radar_server_message_thread(threading.Thread):
	def __init__(self, msgq, fg, detector=None, queue_size=2048, start=True, **kwds):
		threading.Thread.__init__(self, **kwds)
		self.setDaemon(True)
		self.msgq = msgq
		self.fg = fg
		self.detector = detector
		self.keep_running = True
		self.stop_event = threading.Event()
		
		self.reports = []
		self.queue_size = queue_size
		
		if start:
			self.start()
	def start(self):
		print "Starting..."
		threading.Thread.start(self)
	def stop(self):
		print "Stopping..."
		self.keep_running = False
		msg = gr.message()  # Empty message to signal end
		self.msgq.insert_tail(msg)
		self.stop_event.wait()
		self.server.shutdown()
		print "Stopped"
	def clear_radar_queue(self):
		self.reports = []
	def read_queue(self, raw=False, clear=True):
		reports = self.reports
		if clear:
			self.clear_radar_queue()
		if raw:
			return (len(reports), "".join(reports))
		overflows = 0
		l = []
		last = None
		sizeof_radar_error = 4+1+1+1+1
		for report in reports:
			item = struct.unpack("Icccc", report)  # tsf, rssi, width
			
			# Un-initialised memory, so don't bother checking
			#if (ord(item[3]) != 0):
			#    print "First pad byte = %d" % (ord(item[3]))
			#if (ord(item[4]) != 0):
			#    print "Second pad byte = %d" % (ord(item[4]))
			
			re = radar_error(item)
			#print "TSF = %d, RSSI = %d, width = %d" % (re.tsf, re.rssi, re.width)
			l += [re]
			
			if last is not None:
				if (re.tsf < last.tsf):
					overflows += 1
					#print "ROLLOVER: %d (%d)" % (overflows, time_diff)
			re.overflow = overflows
			
			last = re
		
		overflow_amount = (0x7fff + 1)    # 15-bit TSF
		for re in l:
			re.tsf -= (overflow_amount * (overflows - re.overflow))
		
		return l
	#def write_param(self, param):
	#	pass
	def set_param(self, param, value):
		#"FIRPWR"
		#"RSSI"
		#"PHEIGHT"
		#"PRSSI"
		#"INBAND"
		if self.detector is not None:
			self.detector.set_param(param, value)
	def set_freq(self, freq):
		self.fg.set_freq(freq * 1e6)
		return True
	#def __del__(self):
	#	print "DTOR"
	def run(self):
		if self.msgq:
			while self.keep_running:
				msg = self.msgq.delete_head()
				if self.keep_running == False:
					break
				try:
					#msg.type()
					
					msg_str = msg.to_string()
					if len(self.reports) < self.queue_size:
						self.reports += [msg_str]
					#else:
					#	print "RADAR queue full"
				except Exception, e:
					print e
					traceback.print_exc()
		self.stop_event.set()

class radar_server(gr.hier_block2):
	def __init__(self, fg, msgq, detector=None, queue_size=2048, port=5256, **kwds):
		gr.hier_block2.__init__(self, "radar_server",
								gr.io_signature(0, 0, 0),
								gr.io_signature(0, 0, 0))
		self.radar = radar_server_message_thread(msgq, fg, detector, queue_size, start=False, **kwds)
		self.control = radar_server_control_thread(self.radar, port, start=False, **kwds)
		self.start()
	def start(self):
		self.control.start()
		self.radar.start()
	def stop(self):
		self.radar.stop()
		self.control.stop()
	def __del__(self):
		self.stop()

def main():
	return 0

if __name__ == '__main__':
	main()

########NEW FILE########
__FILENAME__ = static_text
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  static_text.py
#  
#  Copyright 2013 Balint Seeber <balint@crawfish>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#  

import threading
import wx
#from gnuradio.wxgui import forms
from gnuradio.wxgui.forms import forms
from gnuradio.wxgui.forms.forms import *
from gnuradio.wxgui.forms import converters
from gnuradio.wxgui.pubsub import pubsub

def make_bold(widget):
	font = widget.GetFont()
	font.SetWeight(wx.FONTWEIGHT_BOLD)
	widget.SetFont(font)

#class panel_base(forms._form_base):
	#def __init__(self, converter, **kwargs):
	#	forms._form_base.__init__(self, converter=converter, **kwargs)
class panel_base2(pubsub, wx.Panel):
	def __init__(self, parent=None, sizer=None, proportion=0, flag=wx.EXPAND, ps=None, key='', value=None, callback=None, converter=converters.identity_converter(), size=None, *args, **kwds):
		pubsub.__init__(self)
		#wx.BoxSizer.__init__(self, wx.VERTICAL)
		if size is not None and size != (-1, -1):
			print "Size:", size
		#	kwds['size'] = size
		#wx.Panel.__init__(self, parent, *args, **kwds)
		wx.Panel.__init__ ( self, parent, id = wx.ID_ANY, pos = wx.DefaultPosition, size = wx.Size( 500,300 ), style = wx.TAB_TRAVERSAL )
		if size is not None and size != (-1, -1):
			self.SetMinSize(size)
			#self.SetSizeHints(*size)
		self._parent = parent
		self._key = key
		self._converter = converter
		self._callback = callback
		self._widgets = list()
		#add to the sizer if provided
		if sizer: sizer.Add(self, proportion, flag)
		#proxy the pubsub and key into this form
		if ps is not None:
			assert key
			self.proxy(EXT_KEY, ps, key)
		#no pubsub passed, must set initial value
		else: self.set_value(value)
		
		self._sizer = wx.BoxSizer(wx.VERTICAL)
		if size is not None and size != (-1, -1):
			self._sizer.SetMinSize(size)
			self._sizer.SetSizeHints(self)

		self.SetSizer(self._sizer)
		
		self.SetBackgroundColour(wx.BLACK)
	
	def __str__(self):
		return "Form: %s -> %s"%(self.__class__, self._key)

	def _add_widget(self, widget, label='', flag=0, label_prop=0, widget_prop=1, sizer=None):
		"""
		Add the main widget to this object sizer.
		If label is passed, add a label as well.
		Register the widget and the label in the widgets list (for enable/disable).
		Bind the update handler to the widget for data events.
		This ensures that the gui thread handles updating widgets.
		Setup the pusub triggers for external and internal.
		@param widget the main widget
		@param label the optional label
		@param flag additional flags for widget
		@param label_prop the proportion for the label
		@param widget_prop the proportion for the widget
		"""
		#setup data event
		widget.Bind(EVT_DATA, lambda x: self._update(x.data))
		update = lambda x: wx.PostEvent(widget, DataEvent(x))
		
		#register widget
		self._widgets.append(widget)
		
		widget_flags = wx.ALIGN_CENTER | flag # wx.ALIGN_CENTER_VERTICAL
		#create optional label
		if label:
			print "Label:", label
			label_text = wx.StaticText(self._parent, label='%s: '%label)
			self._widgets.append(label_text)
			self.Add(label_text, label_prop, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT)
			widget_flags = widget_flags | wx.ALIGN_RIGHT
		
		to_add = sizer or widget
		self._sizer.Add(to_add, widget_prop, widget_flags)
		#self.Add(widget, widget_prop, widget_flags)
		
		#self._parent.Layout()
		#self.Layout()
		#self._parent.Layout()
		self.Layout()
		
		#initialize without triggering pubsubs
		self._translate_external_to_internal(self[EXT_KEY])
		update(self[INT_KEY])
		
		#subscribe all the functions
		self.subscribe(INT_KEY, update)
		self.subscribe(INT_KEY, self._translate_internal_to_external)
		self.subscribe(EXT_KEY, self._translate_external_to_internal)

	def _translate_external_to_internal(self, external):
		try:
			internal = self._converter.external_to_internal(external)
			#prevent infinite loop between internal and external pubsub keys by only setting if changed
			if self[INT_KEY] != internal: self[INT_KEY] = internal
		except Exception, e:
			self._err_msg(external, e)
			self[INT_KEY] = self[INT_KEY] #reset to last good setting

	def _translate_internal_to_external(self, internal):
		try:
			external = self._converter.internal_to_external(internal)
			#prevent infinite loop between internal and external pubsub keys by only setting if changed
			if self[EXT_KEY] != external: self[EXT_KEY] = external
		except Exception, e:
			self._err_msg(internal, e)
			self[EXT_KEY] = self[EXT_KEY] #reset to last good setting
		if self._callback: self._callback(self[EXT_KEY])

	def _err_msg(self, value, e):
		print >> sys.stderr, self, 'Error translating value: "%s"\n\t%s\n\t%s'%(value, e, self._converter.help())

	#override in subclasses to handle the wxgui object
	def _update(self, value): raise NotImplementedError
	def _handle(self, event): raise NotImplementedError

	#provide a set/get interface for this form
	def get_value(self): return self[EXT_KEY]
	def set_value(self, value): self[EXT_KEY] = value

	def Disable(self, disable=True): self.Enable(not disable)
	def Enable(self, enable=True):
		if enable:
			for widget in self._widgets: widget.Enable()
		else:
			for widget in self._widgets: widget.Disable()


class panel_base(forms._form_base):
	def __init__(self, converter, orientation = wx.VERTICAL, size = (-1,-1), **kwargs):
		if size is not None and size != (-1, -1):
			print "Size:", size
		#	kwds['size'] = size
		
		forms._form_base.__init__(self, converter=converter, **kwargs)
		
		self.SetOrientation(orientation)
		self.SetMinSize(size)
		#wx.Panel.__init__(self, parent, *args, **kwds)
		self._creator_thread = threading.current_thread()
	
	def _add_widget(self, widget, label='', flag=0, label_prop=0, widget_prop=1):
		"""
		Add the main widget to this object sizer.
		If label is passed, add a label as well.
		Register the widget and the label in the widgets list (for enable/disable).
		Bind the update handler to the widget for data events.
		This ensures that the gui thread handles updating widgets.
		Setup the pusub triggers for external and internal.
		@param widget the main widget
		@param label the optional label
		@param flag additional flags for widget
		@param label_prop the proportion for the label
		@param widget_prop the proportion for the widget
		"""
		#setup data event
		widget.Bind(EVT_DATA, lambda x: self._update(x.data))
		update = lambda x: wx.PostEvent(widget, DataEvent(x))
		
		#register widget
		self._widgets.append(widget)
		
		widget_flags = wx.ALIGN_CENTER | flag # wx.ALIGN_CENTER_VERTICAL
		#create optional label
		if label:
			label_text = wx.StaticText(self._parent, label='%s: '%label)
			self._widgets.append(label_text)
			self.Add(label_text, label_prop, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT)
			widget_flags = widget_flags# | wx.ALIGN_RIGHT
		
		self.Add(widget, widget_prop, widget_flags)
		
		#initialize without triggering pubsubs
		self._translate_external_to_internal(self[EXT_KEY])
		update(self[INT_KEY])
		
		#subscribe all the functions
		self.subscribe(INT_KEY, update)
		self.subscribe(INT_KEY, self._translate_internal_to_external)
		self.subscribe(EXT_KEY, self._translate_external_to_internal)

wxUPDATE_EVENT = wx.NewEventType()

def EVT_UPDATE_EVENT(win, func):
	win.Connect(-1, -1, wxUPDATE_EVENT, func)

class UpdateEvent(wx.PyEvent):
	def __init__(self, data):
		wx.PyEvent.__init__(self)
		self.SetEventType(wxUPDATE_EVENT)
		self.data = data
	def Clone (self):
		self.__class__(self.GetId())

class static_text(panel_base):
	"""
	A text box form.
	@param parent the parent widget
	@param sizer add this widget to sizer if provided (optional)
	@param proportion the proportion when added to the sizer (default=0)
	@param flag the flag argument when added to the sizer (default=wx.EXPAND)
	@param ps the pubsub object (optional)
	@param key the pubsub key (optional)
	@param value the default value (optional)
	@param label title label for this widget (optional)
	@param width the width of the form in px
	@param bold true to bold-ify the text (default=False)
	@param units a suffix to add after the text
	@param converter forms.str_converter(), int_converter(), float_converter()...
	"""
	def __init__(self, label='', size=(-1,-1), bold=False, font_size=16, units='', converter=converters.str_converter(), **kwargs):
		self._units = units
		panel_base.__init__(self, converter=converter, size=size, **kwargs)
		
		self._static_text = wx.StaticText(self._parent)	#, size=size #, style=wx.ALIGN_CENTRE | wx.ST_NO_AUTORESIZE
		#self._static_text.Wrap(-1)
		#self._static_text.SetMinSize(size)
		font = wx.Font(font_size, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "")
		#font = wx.Font( 36, 70, 90, 90, False, wx.EmptyString )
		self._static_text.SetFont(font)
		#self._static_text.SetBackgroundColour(wx.GREEN)
		
		#self._static_text = wx.StaticText( self, wx.ID_ANY, u"MyLabel", wx.DefaultPosition, wx.Size( -1,-1 ), 0 )
		#self._static_text.Wrap( -1 )
		#self._static_text.SetFont(  )
		#self._static_text.SetForegroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_INFOBK ) )
		#self._static_text.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_INACTIVECAPTIONTEXT ) )
		
		if bold:
			make_bold(self._static_text)
		
		#self.bSizerV = wx.BoxSizer( wx.VERTICAL )
		#self.bSizerV.Add( self._static_text, 0, wx.ALIGN_CENTER, 5 ) # 5 is border
		#self.SetOrientation(wx.VERTICAL)
		
		self._add_widget(self._static_text, label)
		#self._add_widget(self._static_text, label, sizer=self.bSizerV)
		
		#self.Layout()
		
		EVT_UPDATE_EVENT(self._parent, self.posted_update)
	
	def posted_update(self, event):
		data = event.data
		#print data
		data['fn'](*data['args'])
	
	def _update(self, label):
		if threading.current_thread() != self._creator_thread:
			wx.PostEvent(self._parent, UpdateEvent({'fn': self._update, 'args': [label]}))
			return
		if self._units:
			label += ' ' + self._units
		self._static_text.SetLabel(label)
		#self._parent.Layout()
		self.Layout()
	
	def set_colour(self, colour):
		if threading.current_thread() != self._creator_thread:
			wx.PostEvent(self._parent, UpdateEvent({'fn': self.set_colour, 'args': [colour]}))
			return
		if isinstance(colour, str):
			colour = eval(colour)
		self._static_text.SetForegroundColour(colour)

def main():
	return 0

if __name__ == '__main__':
	main()

########NEW FILE########
__FILENAME__ = std_flusher
#!/usr/bin/env python

import threading, traceback, sys, time

class _flusher(threading.Thread):
    def __init__(self, **kwds):
        threading.Thread.__init__(self, **kwds)
        self.setDaemon(True)
        self.keep_running = True
        sys.stderr.write("Starting std flusher...\n")
        self.start()
    def run(self):
        while self.keep_running:
          sys.stdout.flush()
          sys.stderr.flush()
          time.sleep(0.5)

_the_flusher = _flusher()

########NEW FILE########
__FILENAME__ = time_panel
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  time_panel.py
#  
#  Copyright 2013 Balint Seeber <balint@crawfish>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#  

import math, time

import wx

from gnuradio import gr
from gnuradio.wxgui import common

import baz

from time_panel_gen import *

_FUZ = (60 * 60 * 24) * 2	# 2 days tolerance from computer's clock

# http://wiki.wxpython.org/Timer
class time_panel(TimePanel):
	def __init__(self, parent, rate, time_keeper, relative=False, mode=None, **kwds):
		TimePanel.__init__(self, parent)
		self.time_keeper = time_keeper
		self.timer_id = wx.NewId()
		self.relative = relative
		self.set_display_mode(mode)
		self.timer = wx.Timer(self, self.timer_id)
		wx.EVT_TIMER(self, self.timer_id, self.on_timer)
		wx.EVT_CLOSE(self, self.on_close)
		self.set_rate(rate)
	def on_timer(self, event):
		t = self.time_keeper.time(self.relative)
		whole_seconds = int(math.floor(t))
		fractional_seconds = t - whole_seconds
		
		if self.mode == 'absolute' or ((self.mode == 'auto') and (abs(t - time.time()) > _FUZ)):
			seconds = whole_seconds % 60
			minutes = ((whole_seconds - seconds) / 60) % 60
			hours = ((((whole_seconds - seconds) / 60) - minutes) / 60) % 24
			days = ((((((whole_seconds - seconds) / 60) - minutes) / 60) - hours) / 24)
			time_str = "%02i:%02i:%02i:%02i.%03i" % (days, hours, minutes, seconds, int(fractional_seconds*1000))
		else:
			ts = time.localtime(t)
			time_str = time.strftime("%a, %d %b %Y %H:%M:%S", ts)
			time_str += ".%03i" % (int(fractional_seconds*1000))
			#offset = time.timezone / 3600
			#ts.tm_isdst
			tz_str = time.strftime("%Z", ts)
			if len(tz_str) > 0:
				time_str += " " + tz_str
		
		update_count = self.time_keeper.update_count()
		if update_count > 0:
			time_str += " (#%i)" % (update_count)
			
		self.m_staticTime.SetLabel(time_str)
	def on_close(self, event):
		self.timer.Stop()
		self.Destroy()
	def set_rate(self, rate, start=True):
		self.timer.Stop()
		if rate <= 0:
			return
		self.rate = rate
		if start:
			self.timer.Start(int(1000.0/self.rate))
	def set_relative(self, relative):
		self.relative = relative
	def set_display_mode(self, mode=None):
		if mode is None:
			mode = 'auto'
		self.mode = mode

class time_panel_sink(gr.hier_block2, common.wxgui_hb):
	def __init__(self, parent, item_size, sample_rate, rate=1.0, relative=False, mode=None, **kwds):
		gr.hier_block2.__init__(self, "time_panel_sink",
			gr.io_signature(1, 1, item_size),
			gr.io_signature(0, 0, 0)
		)
		self.time_keeper = baz.time_keeper(item_size, sample_rate)
		self.win = time_panel(parent, rate, self.time_keeper, relative, mode)
		self.wxgui_connect(self, self.time_keeper)
	def set_rate(self, rate):
		self.win.set_rate(rate)
	def set_relative(self, relative):
		self.win.set_relative(relative)
	def ignore_next(self, dummy, **kwds):
		self.time_keeper.ignore_next()
	def set_display_mode(self, mode=None):
		self.win.set_display_mode(mode)

def main():
	return 0

if __name__ == '__main__':
	main()

########NEW FILE########
__FILENAME__ = time_panel_gen
# -*- coding: utf-8 -*- 

###########################################################################
## Python code generated with wxFormBuilder (version Oct  8 2012)
## http://www.wxformbuilder.org/
##
## PLEASE DO "NOT" EDIT THIS FILE!
###########################################################################

import wx
import wx.xrc

###########################################################################
## Class TimePanel
###########################################################################

class TimePanel ( wx.Panel ):
	
	def __init__( self, parent ):
		wx.Panel.__init__ ( self, parent, id = wx.ID_ANY, pos = wx.DefaultPosition, size = wx.Size( 500,300 ), style = wx.TAB_TRAVERSAL )
		
		bSizer2 = wx.BoxSizer( wx.HORIZONTAL )
		
		self.m_staticText1 = wx.StaticText( self, wx.ID_ANY, u"Time:", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_staticText1.Wrap( -1 )
		bSizer2.Add( self.m_staticText1, 0, wx.ALL, 5 )
		
		self.m_staticTime = wx.StaticText( self, wx.ID_ANY, u"00:00:00:00.000", wx.DefaultPosition, wx.DefaultSize, wx.ALIGN_CENTRE )
		self.m_staticTime.Wrap( -1 )
		self.m_staticTime.SetFont( wx.Font( wx.NORMAL_FONT.GetPointSize(), 70, 90, 92, False, wx.EmptyString ) )
		
		bSizer2.Add( self.m_staticTime, 0, wx.ALL, 5 )
		
		
		self.SetSizer( bSizer2 )
		self.Layout()
	
	def __del__( self ):
		pass
	


########NEW FILE########
__FILENAME__ = common
# Copyright 2009 Free Software Foundation, Inc.
#
# This file is part of GNU Radio
#
# GNU Radio is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# GNU Radio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GNU Radio; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#

import sys
from gnuradio import usrp, gr

##################################################
# USRP base class with common methods
##################################################
class usrp_helper(object):
	def _make_usrp(self, *args, **kwargs): self._u = self._usrp_args[0](*args, **kwargs)
	def _get_u(self): return self._u
	def _get_io_size(self): return self._usrp_args[1]
	def _set_frequency(self, chan, subdev, frequency, verbose=False):
		"""
		Set the carrier frequency for the given subdevice.
		@param chan specifies the DDC/DUC number
		@param frequency the carrier frequency in Hz
		@param verbose if true, print usrp tuning information
		"""
		r = self._get_u().tune(chan, subdev, frequency)
		if not verbose: return
		print subdev.side_and_name()
		if r:
			print "\tr.baseband_frequency =", r.baseband_freq
			print "\tr.dxc_frequency =", r.dxc_freq
			print "\tr.residual_frequency =", r.residual_freq
			print "\tr.inverted =", r.inverted, "\n"
		else: print >> sys.stderr, 'Error calling tune on subdevice.'
	def set_format(self, width, shift): self._get_u().set_format(self._get_u().make_format(width, shift))

##################################################
# Classes to associate usrp constructor w/ io size
##################################################
class usrp_source_c(usrp_helper): _usrp_args = (usrp.source_c, gr.sizeof_gr_complex)
class usrp_source_s(usrp_helper): _usrp_args = (usrp.source_s, gr.sizeof_short)
class usrp_sink_c(usrp_helper): _usrp_args = (usrp.sink_c, gr.sizeof_gr_complex)
class usrp_sink_s(usrp_helper): _usrp_args = (usrp.sink_s, gr.sizeof_short)

##################################################
# Side spec and antenna spec functions
##################################################
def is_flex(rx_ant): return rx_ant.upper() in ('TX/RX', 'RX2')
def to_spec(side, rx_ant='RXA'):
	"""
	Convert the side to a spec number.
	@param side A or B
	@param rx_ant antenna type
	@return the spec (0/1, 0/1/2)
	"""
	#determine the side spec
	try: side_spec = {'A': 0, 'B': 1}[side.upper()]
	except: raise ValueError, 'Side A or B expected.'
	#determine the subdevice spec
	if rx_ant.upper() == 'RXB': subdev_spec = 1
	elif rx_ant.upper() == 'RXAB': subdev_spec = 2
	else: subdev_spec = 0
	return (side_spec, subdev_spec)

########NEW FILE########
__FILENAME__ = dual_usrp
# Copyright 2009, 2010 Free Software Foundation, Inc.
#
# This file is part of GNU Radio
#
# GNU Radio is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# GNU Radio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GNU Radio; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#

import common
from gnuradio import gr

####################################################################
# Dual USRP Source
####################################################################
class _dual_source(gr.hier_block2):
	"""A dual usrp source of IO type short or complex."""

	def __init__(self, which, rx_ant_a='RXA', rx_ant_b='RXA', rx_source_a='A', rx_source_b='B'):
		"""
		USRP dual source contructor.
		@param which the unit number
		@param rx_ant_a the antenna choice
		@param rx_ant_b the antenna choice
		"""
		#initialize hier2 block
		gr.hier_block2.__init__(
			self, 'usrp_dual_source',
			gr.io_signature(0, 0, 0),
			gr.io_signature(2, 2, self._get_io_size()),
		)
		#create usrp object
		self._make_usrp(which=which, nchan=2)
		subdev_spec_a = common.to_spec(rx_source_a, rx_ant_a)
		subdev_spec_b = common.to_spec(rx_source_b, rx_ant_b)
		self._get_u().set_mux(self._get_u().determine_rx_mux_value(subdev_spec_a, subdev_spec_b))
		self._subdev_a = self._get_u().selected_subdev(subdev_spec_a)
		self._subdev_b = self._get_u().selected_subdev(subdev_spec_b)
		#connect
		deinter = gr.deinterleave(self._get_io_size())
		self.connect(self._get_u(), deinter)
		for i in range(2): self.connect((deinter, i), (self, i))

	def set_decim_rate(self, decim): self._get_u().set_decim_rate(int(decim))
	def set_frequency_a(self, frequency, verbose=False, lo_offset=None):
		if lo_offset is not None: self._subdev_a.set_lo_offset(lo_offset)
		self._set_frequency(
			chan=0, #ddc0
			subdev=self._subdev_a,
			frequency=frequency,
			verbose=verbose,
		)
	def set_frequency_b(self, frequency, verbose=False, lo_offset=None):
		if lo_offset is not None: self._subdev_b.set_lo_offset(lo_offset)
		self._set_frequency(
			chan=1, #ddc1
			subdev=self._subdev_b,
			frequency=frequency,
			verbose=verbose,
		)
	def set_gain_a(self, gain): self._subdev_a.set_gain(gain)
	def set_gain_b(self, gain): self._subdev_b.set_gain(gain)

class dual_source_c(_dual_source, common.usrp_source_c): pass
class dual_source_s(_dual_source, common.usrp_source_s): pass

####################################################################
# Dual USRP Sink
####################################################################
class _dual_sink(gr.hier_block2):
	"""A dual usrp sink of IO type short or complex."""

	def __init__(self, which):
		"""
		USRP simple sink contructor.
		@param which the unit number
		"""
		#initialize hier2 block
		gr.hier_block2.__init__(
			self, 'usrp_dual_sink',
			gr.io_signature(2, 2, self._get_io_size()),
			gr.io_signature(0, 0, 0),
		)
		#create usrp object
		self._make_usrp(which=which, nchan=2)
		subdev_spec_a = common.to_spec('A')
		subdev_spec_b = common.to_spec('B')
		self._get_u().set_mux(self._get_u().determine_tx_mux_value(subdev_spec_a, subdev_spec_b))
		self._subdev_a = self._get_u().selected_subdev(subdev_spec_a)
		self._subdev_b = self._get_u().selected_subdev(subdev_spec_b)
		#connect
		inter = gr.interleave(self._get_io_size())
		self.connect(inter, self._get_u())
		for i in range(2): self.connect((self, i), (inter, i))

	def set_interp_rate(self, interp): self._get_u().set_interp_rate(int(interp))
	def set_frequency_a(self, frequency, verbose=False, lo_offset=None):
		if lo_offset is not None: self._subdev_a.set_lo_offset(lo_offset)
		self._set_frequency(
			chan=self._subdev_a.which(),
			subdev=self._subdev_a,
			frequency=frequency,
			verbose=verbose,
		)
	def set_frequency_b(self, frequency, verbose=False, lo_offset=None):
		if lo_offset is not None: self._subdev_b.set_lo_offset(lo_offset)
		self._set_frequency(
			chan=self._subdev_b.which(),
			subdev=self._subdev_b,
			frequency=frequency,
			verbose=verbose,
		)
	def set_gain_a(self, gain): self._subdev_a.set_gain(gain)
	def set_gain_b(self, gain): self._subdev_b.set_gain(gain)
	def set_enable_a(self, enable): self._subdev_a.set_enable(enable)
	def set_enable_b(self, enable): self._subdev_b.set_enable(enable)
	def set_auto_tr_a(self, auto_tr): self._subdev_a.set_auto_tr(auto_tr)
	def set_auto_tr_b(self, auto_tr): self._subdev_b.set_auto_tr(auto_tr)

class dual_sink_c(_dual_sink, common.usrp_sink_c): pass
class dual_sink_s(_dual_sink, common.usrp_sink_s): pass

########NEW FILE########
__FILENAME__ = simple_usrp
# Copyright 2009 Free Software Foundation, Inc.
#
# This file is part of GNU Radio
#
# GNU Radio is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# GNU Radio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GNU Radio; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#

import common
from gnuradio import gr

####################################################################
# Simple USRP Source
####################################################################
class _simple_source(gr.hier_block2):
	"""A single usrp source of IO type short or complex."""

	def __init__(self, which, side='A', rx_ant='RXA', no_hb=False):
		"""
		USRP simple source contructor.
		@param which the unit number
		@param side the usrp side A or B
		@param rx_ant the antenna choice
		@param no_hb disable half band filters
		"""
		self._no_hb = no_hb
		#initialize hier2 block
		gr.hier_block2.__init__(
			self, 'usrp_simple_source',
			gr.io_signature(0, 0, 0),
			gr.io_signature(1, 1, self._get_io_size()),
		)
		#create usrp object
		if self._no_hb: self._make_usrp(which=which, nchan=1, fpga_filename="std_4rx_0tx.rbf")
		else: self._make_usrp(which=which, nchan=1)
		subdev_spec = common.to_spec(side, rx_ant)
		self._get_u().set_mux(self._get_u().determine_rx_mux_value(subdev_spec))
		self._subdev = self._get_u().selected_subdev(subdev_spec)
		if common.is_flex(rx_ant): self._subdev.select_rx_antenna(rx_ant)
		#connect
		self.connect(self._get_u(), self)

	def set_decim_rate(self, decim):
		self._get_u().set_decim_rate(int(decim))
		if self._no_hb: #set the BW to half the sample rate
			self._subdev.set_bw(self._get_u().converter_rate()/decim/2)
	def set_frequency(self, frequency, verbose=False, lo_offset=None):
		if lo_offset is not None: self._subdev.set_lo_offset(lo_offset)
		self._set_frequency(
			chan=0, #ddc0
			subdev=self._subdev,
			frequency=frequency,
			verbose=verbose,
		)
	def set_gain(self, gain): self._subdev.set_gain(gain)

class simple_source_c(_simple_source, common.usrp_source_c): pass
class simple_source_s(_simple_source, common.usrp_source_s): pass

####################################################################
# Simple USRP Sink
####################################################################
class _simple_sink(gr.hier_block2):
	"""A single usrp sink of IO type short or complex."""

	def __init__(self, which, side='A'):
		"""
		USRP simple sink contructor.
		@param which the unit number
		@param side the usrp side A or B
		"""
		#initialize hier2 block
		gr.hier_block2.__init__(
			self, 'usrp_simple_sink',
			gr.io_signature(1, 1, self._get_io_size()),
			gr.io_signature(0, 0, 0),
		)
		#create usrp object
		self._make_usrp(which=which, nchan=1)
		subdev_spec = common.to_spec(side)
		self._get_u().set_mux(self._get_u().determine_tx_mux_value(subdev_spec))
		self._subdev = self._get_u().selected_subdev(subdev_spec)
		#connect
		self.connect(self, self._get_u())

	def set_interp_rate(self, interp): self._get_u().set_interp_rate(int(interp))
	def set_frequency(self, frequency, verbose=False, lo_offset=None):
		if lo_offset is not None: self._subdev.set_lo_offset(lo_offset)
		self._set_frequency(
			chan=self._subdev.which(),
			subdev=self._subdev,
			frequency=frequency,
			verbose=verbose,
		)
	def set_gain(self, gain): self._subdev.set_gain(gain)
	def set_enable(self, enable): self._subdev.set_enable(enable)
	def set_auto_tr(self, auto_tr): self._subdev.set_auto_tr(auto_tr)

class simple_sink_c(_simple_sink, common.usrp_sink_c): pass
class simple_sink_s(_simple_sink, common.usrp_sink_s): pass


########NEW FILE########
__FILENAME__ = usrp
#!/usr/bin/env python

"""
Provides the Legacy USRP interface via UHD
WARNING: This interface is only very basic!

http://wiki.spench.net/wiki/gr-baz
By Balint Seeber (http://spench.net/contact)
"""

from __future__ import with_statement

import time, os, sys, threading, thread
from string import split, join

from gnuradio import gr, gru, uhd, blocks

_prefs = gr.prefs()
_default_address = _prefs.get_string('legacy_usrp', 'address', '')

def determine_rx_mux_value(u, subdev_spec, subdev_spec_b=None):
	return 0

def selected_subdev(u, subdev_spec):	# Returns subdevice object
	return u.selected_subdev(subdev_spec)

def tune(u, unit, subdev, freq):
	return u.tune(unit, subdev, freq)

class tune_result:
	def __init__(self, baseband_freq=0, actual_rf_freq=0, dxc_freq=0, residual_freq=0, inverted=False):
		self.baseband_freq = baseband_freq
		self.actual_rf_freq = actual_rf_freq
		self.dxc_freq = dxc_freq
		self.residual_freq = residual_freq
		self.inverted = inverted

class usrp_tune_result(tune_result):
	def __init__(self, baseband=None, dxc=None, residual=None, **kwds):
		tune_result.__init__(self, **kwds)
		if baseband is not None:
			self.baseband_freq = self.baseband = baseband
		if dxc is not None:
			self.dxc_freq = self.dxc = dxc
		if residual is not None:
			self.residual_freq = self.residual = residual

def pick_subdev(u, candidates=[]):
    return u.pick_subdev(candidates)

def pick_tx_subdevice(u):
	return (0, 0)

def pick_rx_subdevice(u):
	return (0, 0)

class device(gr.hier_block2):
	"""
	Legacy USRP via UHD
	Assumes 64MHz clock in USRP 1
	'address' as None implies check config for default
	"""
	def __init__(self, address=None, which=0, decim_rate=0, nchan=1, adc_freq=64e6, defer_creation=True, scale=8192):	# FIXME: 'which', 'nchan'
		"""
		UHD USRP Source
		"""
		if self._args[1] == "fc32":
			format_size = gr.sizeof_gr_complex
		elif self._args[1] == "sc16":
			format_size = gr.sizeof_short * 2
		
		empty_io = gr.io_signature(0, 0, 0)
		format_io = gr.io_signature(1, 1, format_size)
		
		if self._args[0]:
			io = (format_io, empty_io)
		else:
			io = (empty_io, format_io)
		
		gr.hier_block2.__init__(self, "uhd_usrp_wrapper",
			io[0],
			io[1])
		
		self._decim_rate = decim_rate
		self._address = address
		self._which = which
		
		self._adc_freq = int(adc_freq)
		self._gain_range = (0, 1, 1)
		self._freq_range = (0, 0, 0)
		self._tune_result = None
		self._name = "(Legacy USRP)"
		self._serial = "(Legacy)"
		self._gain_step = 0
		self._created = False
		
		self._scale = scale
		
		self._last_address = address
		self._last_which = None
		self._last_subdev_spec = None
		
		self._reset_last_params()
		
		self._uhd_device = None
		
		if defer_creation == False:	# Deferred until 'selected_subdev' is called
			self.create()
	
	def _reset_last_params(self):
		self._last_freq = None
		self._last_gain = None
		self._last_antenna = None
	
	def __del__(self):
		self.destroy()
	
	def destroy(self, error=None):
		pass
	
	def create(self, address=None, decim_rate=0, which=None, subdev_spec="", sample_rate=None):
		if self._uhd_device is not None:	# Not supporting re-creation
			return True
		
		if address is None:
			address = self._address
		if (address is None):	# or (isinstance(address, str) and address == "")
			address = _default_address
		
		if isinstance(address, int):
			# FIXME: Check 'which'
			which = address
			address = ""
		
		if decim_rate == 0:
			decim_rate = self._decim_rate
		if decim_rate == 0:
			#raise Exception, "Decimation rate required"
			decim_rate = 256
		
		if which is None:
			which = self._which
		
		self._last_address = address
		self._last_which = which
		self._last_subdev_spec = subdev_spec
		
		self.destroy()
		
		# FIXME: 'which'
		
		if ((subdev_spec is not None) and (not isinstance(subdev_spec, str))) or (isinstance(subdev_spec, str) and (subdev_spec != "")):
			if isinstance(subdev_spec, str) == False:
				if isinstance(subdev_spec, tuple):
					if len(subdev_spec) > 1:
						subdev_spec = "%s:%s" % (chr(ord('A') + subdev_spec[0]), subdev_spec[1])
					else:
						subdev_spec = chr(ord('A') + subdev_spec[0])
				else:
					raise Exception, "Unknown sub-device specification: " + str(subdev_spec)
		
		stream_args = uhd.stream_args(
			cpu_format=self._args[1],
			channels=range(1),
		)
		
		if self._args[0]:
			self._uhd_device = uhd.usrp_sink(
				device_addr=address,
				stream_args=stream_args,
			)
		else:
			self._uhd_device = uhd.usrp_source(
				device_addr=address,
				stream_args=stream_args,
			)
		
		if subdev_spec is not None:
			self._uhd_device.set_subdev_spec(subdev_spec, 0)
		
		try:
			info = self._uhd_device.get_usrp_info(0)
			self._name = info.get("mboard_id")
			self._serial = info.get("mboard_serial")
			if self._serial != "":
				self._name += (" (%s)" % (self._serial))
		except:
			pass
		
		_gr = self._uhd_device.get_gain_range(0)
		self._gain_range = (_gr.start(), _gr.stop(), _gr.step())
		self._gain_step = _gr.step()
		
		external_port = self
		self._multiplier = None
		if self._scale != 1.0:
			scale = self._scale
			if self._args[0]:
				scale = 1.0 / scale
			#print "Scaling by", self._scale
			self._multiplier = external_port = gr.multiply_const_vcc((scale,))
			if self._args[0]:
				self.connect(self, self._multiplier)
			else:
				self.connect(self._multiplier, self)
		
		_fr = self._uhd_device.get_freq_range(0)
		self._freq_range = (_fr.start(), _fr.stop(), _fr.step())
		
		if self._args[0]:
			if self._args[1] == "sc16":
				self._s2v = blocks.stream_to_vector(gr.sizeof_short, 2)
				self.connect(external_port, self._s2v, self._uhd_device)
			else:
				self.connect(external_port, self._uhd_device)
		else:
			if self._args[1] == "sc16":
				self._v2s = gr.vector_to_stream(gr.sizeof_short, 2)
				self.connect(self._uhd_device, self._v2s, external_port)
			else:
				self.connect(self._uhd_device, external_port)
		
		self._created = True
		
		if sample_rate is not None:
			self._uhd_device.set_samp_rate(sample_rate)
		else:
			if self.set_decim_rate(decim_rate) == False:
				raise Exception, "Invalid decimation: %s (sample rate: %s)" % (decim_rate, sample_rate)
		
		#if self._last_antenna is not None:
		#	self.select_rx_antenna(self._last_antenna)
		#if self._last_freq is not None:
		#	self.set_freq(self._last_freq)
		#if self._last_gain is not None:
		#	self.set_gain(self._last_gain)
	
	#def __repr__(self):
	#	pass
	
	def __str__(self):
		return self.name()
	
	def set_freq(self, freq):
		self._last_freq = freq
		self._tune_result = self._uhd_device.set_center_freq(freq, 0)
		#print "[UHD]", freq, "=", self._tune_result
		#return self._tune_result	# usrp.usrp_tune_result
		tr = tune_result(
			baseband_freq = self._tune_result.actual_rf_freq,
			dxc_freq = self._tune_result.actual_dsp_freq,
			residual_freq = (freq - self._tune_result.actual_rf_freq - self._tune_result.actual_dsp_freq))
		return tr
	
	def tune(self, unit, subdev, freq):
		return self.set_freq(freq)
	
	def adc_freq(self):
		return self._adc_freq
	
	def adc_rate(self):
		return self.adc_freq()
	
	def decim_rate(self):
		return self._decim_rate
	
	def set_mux(self, mux):
		pass
	
	def pick_subdev(self, candidates=[]):
		return ""	# subdev_spec (side, subdev)
	
	def pick_tx_subdevice(self):
		return (0, 0)
	
	def pick_rx_subdevice(self):
		return (0, 0)
	
	def determine_rx_mux_value(self, subdev_spec, subdev_spec_=None):
		return 0	# Passed to set_mux
	
	def selected_subdev(self, subdev_spec):
		if (self._created == False):
			self.create(subdev_spec=subdev_spec)
		return self
	
	def set_decim_rate(self, decim_rate):
		self._decim_rate = decim_rate
		if self._uhd_device is None:
			return True
		sample_rate = self.adc_freq() / decim_rate
		#print "[UHD] Setting sample rate:", sample_rate
		return self._uhd_device.set_samp_rate(sample_rate)

	def db(self, side_idx, subdev_idx):
		return self
	
	def converter_rate(self):
		return self.adc_freq()
	
	def fpga_master_clock_freq(self):
		return self.adc_freq()
	
	## Daughter-board #################
	
	def dbid(self):
		return 0
	
	## Sub-device #####################

	def gain_range(self):
		return self._gain_range
	
	def gain_min(self):
		return self._gain_range[0]
	
	def gain_max(self):
		return self._gain_range[1]
	
	def set_gain(self, gain):
		self._last_gain = gain
		return self._uhd_device.set_gain(gain, 0)
	
	def freq_range(self):
		return self._freq_range
	
	def select_rx_antenna(self, antenna):
		self._last_antenna = antenna
		return self._uhd_device.set_antenna(antenna, 0)
	
	def name(self):
		return self._name
	
	def serial_number(self):
		return self._serial
	
	def side_and_name(self):
		try:
			info = self._uhd_device.get_usrp_info(0)
			return "%s [%s]" % (self.name(), info.get("rx_subdev_name"))
		except:
			return self.name()

class source_c(device): _args = (False, "fc32")
class source_s(device): _args = (False, "sc16")
class sink_c(device): _args = (True, "fc32")
class sink_s(device): _args = (True, "sc16")

########NEW FILE########
__FILENAME__ = usrp_dbid
#
# Machine generated by gen_usrp_dbid.py from usrp_dbid.dat
# Do not edit by hand.  All edits will be overwritten.
#

#
# USRP Daughterboard ID's
#

BASIC_TX         = 0x0000
BASIC_RX         = 0x0001
DBS_RX           = 0x0002
TV_RX            = 0x0003
FLEX_400_RX      = 0x0004
FLEX_900_RX      = 0x0005
FLEX_1200_RX     = 0x0006
FLEX_2400_RX     = 0x0007
FLEX_400_TX      = 0x0008
FLEX_900_TX      = 0x0009
FLEX_1200_TX     = 0x000a
FLEX_2400_TX     = 0x000b
TV_RX_REV_2      = 0x000c
DBS_RX_CLKMOD    = 0x000d
LF_TX            = 0x000e
LF_RX            = 0x000f
FLEX_400_RX_MIMO_A = 0x0014
FLEX_900_RX_MIMO_A = 0x0015
FLEX_1200_RX_MIMO_A = 0x0016
FLEX_2400_RX_MIMO_A = 0x0017
FLEX_400_TX_MIMO_A = 0x0018
FLEX_900_TX_MIMO_A = 0x0019
FLEX_1200_TX_MIMO_A = 0x001a
FLEX_2400_TX_MIMO_A = 0x001b
FLEX_400_RX_MIMO_B = 0x0024
FLEX_900_RX_MIMO_B = 0x0025
FLEX_1200_RX_MIMO_B = 0x0026
FLEX_2400_RX_MIMO_B = 0x0027
FLEX_400_TX_MIMO_B = 0x0028
FLEX_900_TX_MIMO_B = 0x0029
FLEX_1200_TX_MIMO_B = 0x002a
FLEX_2400_TX_MIMO_B = 0x002b
FLEX_1800_RX     = 0x0030
FLEX_1800_TX     = 0x0031
FLEX_1800_RX_MIMO_A = 0x0032
FLEX_1800_TX_MIMO_A = 0x0033
FLEX_1800_RX_MIMO_B = 0x0034
FLEX_1800_TX_MIMO_B = 0x0035
TV_RX_REV_3      = 0x0040
DTT754           = 0x0041
DTT768           = 0x0042
TV_RX_MIMO       = 0x0043
TV_RX_REV_2_MIMO = 0x0044
TV_RX_REV_3_MIMO = 0x0045
WBX_LO_TX        = 0x0050
WBX_LO_RX        = 0x0051
WBX_NG_TX        = 0x0052
WBX_NG_RX        = 0x0053
XCVR2450_TX      = 0x0060
XCVR2450_RX      = 0x0061
EXPERIMENTAL_TX  = 0xfffe
EXPERIMENTAL_RX  = 0xffff

########NEW FILE########
