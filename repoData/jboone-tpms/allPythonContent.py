__FILENAME__ = bit_coding
#!/usr/bin/env python

#
# Copyright 2013 Jared Boone
#
# This file is part of the TPMS project.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#

# import numpy

# def copy_truncated(a, mod_n):
# 	return a[:(len(a) / mod_n) * mod_n].copy()

# def differential_manchester_decode(a):
# 	last_bit = 0
# 	a = copy_truncated(a, 2)
# 	a = a.reshape((-1, 2))
# 	result = []
# 	for pair in a:
# 		if pair[0] == pair[1]:
# 			result.append('X')
# 		elif last_bit != pair[0]:
# 			result.append('0')
# 		else:
# 			result.append('1')
# 		last_bit = pair[1]
# 	return result

# def biphase_decode(a):
# 	a = copy_truncated(a, 2)
# 	a = a.reshape((-1, 2))
# 	result = []
# 	for pair in a:
# 		if pair[0] != pair[1]:
# 			result.append('1')
# 		else:
# 			result.append('0')
# 	return result
	
# def manchester_decode(a):
# 	a = copy_truncated(a, 2)
# 	a = a.reshape((-1, 2))
# 	result = []
# 	for pair in a:
# 		if pair[0] == pair[1]:
# 			result.append('X')
# 		else:
# 			result.append(str(pair[1]))
# 	return result

def string_to_symbols(s, symbol_length):
	return [s[n:n+symbol_length] for n in range(0, len(s), symbol_length)]

def differential_manchester_decode(s):
	symbols = string_to_symbols(s, 2)
	last_bit = '0'
	result = []
	for symbol in symbols:
		if len(symbol) == 2:
			if symbol[0] == symbol[1]:
				result.append('X')
			elif last_bit != symbol[0]:
				result.append('0')
			else:
				result.append('1')
			last_bit = symbol[1]
		else:
			result.append('X')
	return ''.join(result)

def manchester_decode(s):
	symbols = string_to_symbols(s, 2)
	result = []
	for symbol in symbols:
		if len(symbol) == 2:
			if symbol[0] == symbol[1]:
				result.append('X')
			else:
				result.append(symbol[1])
		else:
			result.append('X')
	return ''.join(result)
########NEW FILE########
__FILENAME__ = burst_detector
#!/usr/bin/env python

#
# Copyright 2013 Jared Boone
#
# This file is part of the TPMS project.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#

# Burst detection

import math

from gnuradio import gr

import numpy
import scipy.signal
import pyfftw

# http://gnuradio.org/redmine/projects/gnuradio/wiki/BlocksCodingGuide

class burst_detector(gr.basic_block):
	def __init__(self):
		super(burst_detector, self).__init__(
			name="Burst Detector",
			in_sig=[numpy.complex64],
			out_sig=[numpy.complex64]
		)

		self._burst_tag_symbol = gr.pmt.string_to_symbol('burst')
		self._burst = False

		self.block_size = 256
		
		self.hysteresis_timeout = 3 #int(math.ceil(768 / self.block_size))
		self.hysteresis_count = 0

		self.fft_window = scipy.signal.hanning(self.block_size)
		self.fft_in = pyfftw.n_byte_align_empty((self.block_size,), self.block_size, dtype='complex64')
		self.fft_out = pyfftw.n_byte_align_empty((self.block_size,), self.block_size, dtype='complex64')
		self.fft = pyfftw.FFTW(self.fft_in, self.fft_out)

	def forecast(self, noutput_items, ninput_items_required):
		block_count = int(math.ceil(float(noutput_items) / self.block_size))
		ninput_items_required[0] = block_count * self.block_size
		#print('for %d items, require %d' % (noutput_items, ninput_items_required[0]))

	def general_work(self, input_items, output_items):
		input_item = input_items[0]
		
		samples_to_consume = min(len(input_items[0]), len(output_items[0]))
		block_count = int(math.floor(samples_to_consume / self.block_size))
		samples_to_consume = block_count * self.block_size

		nitems_written = self.nitems_written(0)
		for block_n in range(block_count):
			index_start = block_n * self.block_size
			index_end = index_start + self.block_size
			block = input_item[index_start:index_end]
			#block_spectrum = numpy.fft.fft(block)
			self.fft_in[:] = block * self.fft_window
			self.fft()
			block_spectrum = self.fft_out
			block_abs = numpy.abs(block_spectrum)
			block_max = max(block_abs)
			block_sum = numpy.sum(block_abs)
			block_avg = block_sum / self.block_size
			block_spread = block_max / block_avg
			#graph = '*' * int(round(block_spread))
			#print('%.1f %s' % (block_spread, graph))
			
			if block_spread >= 10:
				self.hysteresis_count = self.hysteresis_timeout
			elif block_spread < 5:
				self.hysteresis_count -= 1
				
			#if block_max >= self.threshold_rise:
			#	self.hysteresis_count = self.hysteresis_timeout
			#elif block_max <= self.threshold_fall:
			#	self.hysteresis_count -= 1
			
			if self.hysteresis_count > 0:
				if self._burst == False:
					tag_sample_index = nitems_written + index_start - self.block_size
					if tag_sample_index >= 0:
						#print('T: %d, %d' % (tag_sample_index, nitems_written))
						self.add_item_tag(0, tag_sample_index, self._burst_tag_symbol, gr.pmt.PMT_T)
						self._burst = True
				#print('%6d %.3f' % (datetime.datetime.now().microsecond, block_max))
			else:
				if self._burst == True:
					#print('F: %d, %d' % (nitems_written + index_start, nitems_written))
					self.add_item_tag(0, nitems_written + index_start, self._burst_tag_symbol, gr.pmt.PMT_F)
					self._burst = False

		output_items[0][:samples_to_consume] = input_items[0][:samples_to_consume]

		self.consume_each(samples_to_consume)

		return samples_to_consume

########NEW FILE########
__FILENAME__ = burst_inspect
#!/usr/bin/env python

#
# Copyright 2013 Jared Boone
#
# This file is part of the TPMS project.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#

import sys
import math
import glob
import os
import os.path

import numpy
import scipy.signal

import yaml

from PySide import QtCore
from PySide import QtGui

from gnuradio import blocks
from gnuradio import gr
from gnuradio import digital

from numpy_block import NumpySource, NumpySink
#from packet import packet_classify

class TimeData(object):
	def __init__(self, data, sampling_rate):
		self._data = data
		self._sampling_rate = sampling_rate
		self._min = None
		self._max = None
		self._abs = None
		self._abs_max = None

	@property
	def sample_count(self):
		return len(self._data)

	@property
	def sampling_rate(self):
		return self._sampling_rate

	@property
	def sampling_interval(self):
		return 1.0 / self.sampling_rate

	@property
	def duration(self):
		return float(self.sample_count) / self.sampling_rate

	@property
	def samples(self):
		return self._data

	@property
	def min(self):
		if self._min is None:
			self._min = numpy.min(self._data)
		return self._min

	@property
	def max(self):
		if self._max is None:
			self._max = numpy.max(self._data)
		return self._max

	@property
	def abs(self):
		if self._abs is None:
			self._abs = numpy.absolute(self._data)
		return TimeData(self._abs, self.sampling_rate)

	@property
	def abs_max(self):
		if self._abs_max is None:
			self._abs_max = numpy.max(self.abs.samples)
		return self._abs_max

	def __sub__(self, other):
		if isinstance(other, int) or isinstance(other, float):
			return TimeData(self.samples - other, self.sampling_rate)

class Handle(QtGui.QGraphicsLineItem):
	class Signals(QtCore.QObject):
		position_changed = QtCore.Signal(float)

	def __init__(self):
		super(Handle, self).__init__()

		self.signals = Handle.Signals()

		pen = QtGui.QPen()
		pen.setColor(QtCore.Qt.yellow)
		pen.setWidth(3)

		self.setPen(pen)
		self.setFlag(QtGui.QGraphicsItem.ItemIsMovable)

	def setHeight(self, value):
		self.setLine(0, 0, 0, value)

	def mouseMoveEvent(self, event):
		super(Handle, self).mouseMoveEvent(event)
		self.setY(0)
		self.signals.position_changed.emit(self.x())

class WaveformItem(QtGui.QGraphicsPathItem):
	def __init__(self):
		super(WaveformItem, self).__init__()

		self._data = None

	@property
	def data(self):
		return self._data

	@data.setter
	def data(self, value):
		self._data = value
		self.setPath(self._generate_path())

	def _generate_path(self):
		path = QtGui.QPainterPath()

		if self.data is not None:
			sampling_interval = self.data.sampling_interval
			path.moveTo(0, 0)
			for i in range(self.data.sample_count):
				x = i * sampling_interval
				y = self.data.samples[i]
				path.lineTo(x, y)
			path.lineTo(self.data.duration, 0)
		return path

class HistogramItem(QtGui.QGraphicsPathItem):
	def __init__(self):
		super(HistogramItem, self).__init__()

		self._data = None
		self._bin_count = None

	@property
	def bin_count(self):
		return self._bin_count

	@bin_count.setter
	def bin_count(self, value):
		self._bin_count = value

	@property
	def data(self):
		return self._data

	@data.setter
	def data(self, value):
		self._data = value
		self.setPath(self._generate_path())

	def _generate_path(self):
		path = QtGui.QPainterPath()

		if self.data is not None:
			histogram = numpy.histogram(self.data, bins=self.bin_count)
			path.moveTo(0, histogram[1][0])
			for i in range(len(histogram[1]) - 1):
				x = histogram[0][i]
				y = (histogram[1][i] + histogram[1][i+1]) / 2.0
				path.lineTo(x, y)
			path.lineTo(0, histogram[1][-1])
		return path

class WaveformView(QtGui.QGraphicsView):
	def __init__(self, parent=None):
		super(WaveformView, self).__init__(parent)
		self.setFrameStyle(QtGui.QFrame.NoFrame)
		self.setBackgroundBrush(QtCore.Qt.black)
		self.setMouseTracking(True)
		self.setRenderHint(QtGui.QPainter.Antialiasing)
		self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
		self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

		self.grabGesture(QtCore.Qt.GestureType.PinchGesture)
		#self.grabGesture(QtCore.Qt.GestureType.PanGesture)

		#self.dragMode = QtGui.QGraphicsView.ScrollHandDrag
		#self.dragMode = QtGui.QGraphicsView.RubberBandDrag
		#self.interactive = True

		#self.resizeAnchor = QtGui.QGraphicsView.AnchorUnderMouse
		#self.transformationAnchor = QtGui.QGraphicsView.AnchorUnderMouse
		#self.viewportAnchor = QtGui.QGraphicsView.AnchorUnderMouse
		self.setTransformationAnchor(QtGui.QGraphicsView.AnchorUnderMouse)

		self.scene = QtGui.QGraphicsScene()
		self.setScene(self.scene)

		color_data = QtGui.QColor(0, 255, 0)
		pen_data = QtGui.QPen(color_data)
		self.data_path = WaveformItem()
		self.data_path.setPen(pen_data)
		self.scene.addItem(self.data_path)

	@property
	def data(self):
		return self.data_path.data

	@data.setter
	def data(self, value):
		self.data_path.data = value
		self.resetTransform()
		self._data_changed()

	def posXToTime(self, x):
		return float(self.mapToScene(x, 0).x()) #* self.data.sampling_interval

	def mouseMoveEvent(self, event):
		t_ms = self.posXToTime(event.x()) * 1000.0
		QtGui.QToolTip.showText(event.globalPos(), '%.2f ms' % (t_ms,))
		return super(WaveformView, self).mouseMoveEvent(event)

	def resizeEvent(self, event):
		super(WaveformView, self).resizeEvent(event)
		self.resetTransform()
		self._scale_changed()

	def event(self, evt):
		if evt.type() == QtCore.QEvent.Type.Gesture:
			return self.gestureEvent(evt)
		return super(WaveformView, self).event(evt)

	def gestureEvent(self, event):
		pinch_gesture = event.gesture(QtCore.Qt.GestureType.PinchGesture)
		scale_factor = pinch_gesture.scaleFactor()
		center = pinch_gesture.centerPoint()

		if pinch_gesture.state() == QtCore.Qt.GestureState.GestureStarted:
			self._gesture_start_transform = self.transform()
		elif pinch_gesture.state() == QtCore.Qt.GestureState.GestureFinished:
			pass
		elif pinch_gesture.state() == QtCore.Qt.GestureState.GestureUpdated:
			pass

		self.scale(self._gesture_start_transform.m11() * scale_factor / self.transform().m11(), 1.0)

		return super(WaveformView, self).event(event)

class GenericWaveformView(WaveformView):
	def _data_changed(self):
		if self.data is not None:
			self.setSceneRect(0, self.data.max, self.data.duration, -(self.data.max - self.data.min))
		self._scale_changed()

	def _scale_changed(self):
		if self.data is not None:
			new_size = self.size()
			self.scale(float(self.width()) / self.data.duration, self.height() / -(self.data.max - self.data.min))
			self.translate(0.0, self.height())

class WaveWidget(QtGui.QWidget):
	range_changed = QtCore.Signal(float, float)

	def __init__(self, parent=None):
		super(WaveWidget, self).__init__(parent=parent)

		self._data = None

		self.waveform_view = GenericWaveformView(self)

	def get_data(self):
		return self._data

	def set_data(self, data):
		self._data = data
		if self.data is not None:
			self.waveform_view.data = self.data
			#self.histogram_path.data = data
		else:
			self.waveform_view.data = None
	data = property(get_data, set_data)

	def sizeHint(self):
		return QtCore.QSize(50, 50)

	def resizeEvent(self, event):
		super(WaveWidget, self).resizeEvent(event)
		self.waveform_view.resize(event.size())

class AMWaveformView(WaveformView):
	def _data_changed(self):
		if self.data is not None:
			self.setSceneRect(0, 0, self.data.duration, self.data.abs_max)
		self._scale_changed()

	def _scale_changed(self):
		if self.data is not None:
			new_size = self.size()
			self.scale(float(new_size.width()) / self.data.duration, float(new_size.height()) / -self.data.abs_max)
			self.translate(0.0, new_size.height())
	
class AMWidget(QtGui.QWidget):
	range_changed = QtCore.Signal(float, float)

	def __init__(self, parent=None):
		super(AMWidget, self).__init__(parent=parent)

		self._data = None

		self.waveform_view = AMWaveformView(self)

	def get_data(self):
		return self._data

	def set_data(self, data):
		self._data = data
		if self.data is not None:
			self.waveform_view.data = TimeData(self.data.abs.samples, self.data.sampling_rate)
			#self.histogram_path.data = data
		else:
			self.waveform_view.data = None
	data = property(get_data, set_data)

	def sizeHint(self):
		return QtCore.QSize(50, 50)

	def resizeEvent(self, event):
		super(AMWidget, self).resizeEvent(event)
		self.waveform_view.resize(event.size())

class FMWaveformView(WaveformView):
	def _data_changed(self):
		if self.data is not None:
			self.setSceneRect(0, -numpy.pi, self.data.duration, numpy.pi * 2.0)
		self._scale_changed()

	def _scale_changed(self):
		if self.data is not None:
			new_size = self.size()
			self.scale(float(self.width()) / self.data.duration, self.height() / (numpy.pi * -2.0))
			self.translate(0.0, self.height())

class FMWidget(QtGui.QWidget):
	def __init__(self, parent=None):
		super(FMWidget, self).__init__(parent=parent)

		self._data = None

		self.waveform_view = FMWaveformView(self)

	def get_data(self):
		return self._data

	def set_data(self, data):
		self._data = data
		if self.data is not None:
			values = numpy.angle(self.data.samples[1:] * numpy.conjugate(self.data.samples[:-1]))



			#print('FM HISTOGRAM: %s' % str(numpy.histogram(values, 100)))
			#count_hi = len([x for x in values if x >= 0.0])
			#count_lo = len(values) - count_hi
			#print('%d %d' % (count_lo, count_hi))

			# hist = numpy.histogram(values, 100)
			# def arg_hz(n):
			#   return (n - 50) / 100.0 * self.data.sampling_rate
			# #print('ARGMAX: %f' % (numpy.argmax(hist[0]) / 100.0))
			# print('ARGSORT: %s' % map(arg_hz, numpy.argsort(hist[0])[::-1]))




			self.waveform_view.data = TimeData(values, self.data.sampling_rate)
			#self.histogram_path.data = data
		else:
			self.waveform_view.data = None
	data = property(get_data, set_data)

	def sizeHint(self):
		return QtCore.QSize(50, 50)

	def resizeEvent(self, event):
		super(FMWidget, self).resizeEvent(event)
		self.waveform_view.resize(event.size())

class EyeView(QtGui.QGraphicsView):
	def __init__(self, parent=None):
		super(EyeView, self).__init__(parent=parent)
		self.setFrameStyle(QtGui.QFrame.NoFrame)
		self.setBackgroundBrush(QtCore.Qt.black)
		self.setMouseTracking(True)
		self.setRenderHint(QtGui.QPainter.Antialiasing)
		self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
		self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

		#self.dragMode = QtGui.QGraphicsView.ScrollHandDrag
		#self.dragMode = QtGui.QGraphicsView.RubberBandDrag
		#self.interactive = True

		#self.resizeAnchor = QtGui.QGraphicsView.NoAnchor
		#self.transformationAnchor = QtGui.QGraphicsView.NoAnchor

		self.scene = QtGui.QGraphicsScene()
		self.setScene(self.scene)

		color_1 = QtGui.QColor(0, 255, 0)
		pen_1 = QtGui.QPen(color_1)
		color_2 = QtGui.QColor(255, 255, 0)
		pen_2 = QtGui.QPen(color_2)
		
		self.path_1 = WaveformItem()
		self.path_1.setPen(pen_1)
		self.scene.addItem(self.path_1)
		
		self.path_2 = WaveformItem()
		self.path_2.setPen(pen_2)
		self.scene.addItem(self.path_2)

		self._data_1 = None
		self._data_2 = None

		# TODO: Assert that data_1 and data_2 are compatible? Same sampling rates?

	def posXToTime(self, x):
		return float(self.mapToScene(x, 0).x())

	def mouseMoveEvent(self, event):
		t_ms = self.posXToTime(event.x()) * 1000.0
		QtGui.QToolTip.showText(event.globalPos(), '%.2f ms' % (t_ms,))
		return super(EyeView, self).mouseMoveEvent(event)

	def resizeEvent(self, event):
		super(EyeView, self).resizeEvent(event)
		self.resetTransform()
		self._data_changed()

	def get_data_1(self):
		return self._data_1

	def set_data_1(self, data):
		self._data_1 = data
		self.path_1.data = self._data_1
		#self.histogram_path.data = data
		self.resetTransform()
		self._data_changed()
	data_1 = property(get_data_1, set_data_1)

	def get_data_2(self):
		return self._data_2

	def set_data_2(self, data):
		self._data_2 = data
		self.path_2.data = self._data_2
		#self.histogram_path.data = data
		self.resetTransform()
		self._scale_changed()
	data_2 = property(get_data_2, set_data_2)

	def _data_changed(self):
		if (self.data_1 is not None) and (self.data_2 is not None):
			new_size = self.size()
			abs_max = max(self.data_1.abs_max, self.data_2.abs_max)
			self.setSceneRect(0, 0, self.data_1.duration, abs_max)
		self._scale_changed()

	def _scale_changed(self):
		if (self.data_1 is not None) and (self.data_2 is not None):
			new_size = self.size()
			abs_max = max(self.data_1.abs_max, self.data_2.abs_max)
			self.scale(float(self.width()) / self.data_1.duration, self.height() / -abs_max)
			self.translate(0.0, self.height())

class EyeWidget(QtGui.QWidget):
	def __init__(self, parent=None):
		super(EyeWidget, self).__init__(parent=parent)

		self.eye_view = EyeView(self)

		self._data = None

	def get_data(self):
		return self._data

	def set_data(self, data):
		self._data = data
		self.eye_view.data_1 = data[0]
		self.eye_view.data_2 = data[1]

	data = property(get_data, set_data)

	def sizeHint(self):
		return QtCore.QSize(50, 50)

	def resizeEvent(self, event):
		super(EyeWidget, self).resizeEvent(event)
		self.eye_view.resize(event.size())

class SlicerView(WaveformView):
	def _data_changed(self):
		if self.data is not None:
			self.setSceneRect(0, -self.data.abs_max, self.data.duration, 2.0 * self.data.abs_max)
		self._scale_changed()

	def _scale_changed(self):
		if self.data is not None:
			new_size = self.size()
			self.scale(float(self.width()) / self.data.duration, self.height() / -(2.0 * self.data.abs_max))
			self.translate(0.0, self.height())

class SlicerWidget(QtGui.QWidget):
	def __init__(self, parent=None):
		super(SlicerWidget, self).__init__(parent=parent)
		self.slicer_view = SlicerView(self)
		self._data = None

	def get_data(self):
		return self._data

	def set_data(self, data):
		self._data = data
		self.slicer_view.data = data
	data = property(get_data, set_data)

	def sizeHint(self):
		return QtCore.QSize(50, 50)

	def resizeEvent(self, event):
		super(SlicerWidget, self).resizeEvent(event)
		self.slicer_view.resize(event.size())

# def classify_burst(data):
#   return packet_classify(data.samples, data.sampling_rate)
	
# def estimate_fsk_carrier(data):
#   spectrum = numpy.fft.fftshift(numpy.fft.fft(data.samples))
#   mag_spectrum = numpy.log(numpy.absolute(spectrum))
#   argsort = numpy.argsort(mag_spectrum)[::-1]

#   def argsort_hz(n):
#       return ((n / float(len(mag_spectrum))) - 0.5) * data.sampling_rate

#   argsort_peak1_n = argsort[0]

#   n_delta_min = 10e3 / data.sampling_rate * len(mag_spectrum)
#   argsort_2nd = [n for n in argsort[:10] if abs(n - argsort_peak1_n) > n_delta_min]
#   if len(argsort_2nd) > 0:
#       argsort_peak2_n = argsort_2nd[0]

#       shift = argsort_hz((argsort_peak1_n + argsort_peak2_n) / 2.0)
#       return (shift, abs(argsort_hz(argsort_peak2_n) - argsort_hz(argsort_peak1_n)))
#   else:
#       return (0.0, None)

class SpectrumView(QtGui.QWidget):
	translation_frequency_changing = QtCore.Signal(float)
	translation_frequency_changed = QtCore.Signal(float)

	def __init__(self, parent=None):
		super(SpectrumView, self).__init__(parent)
		self.setMouseTracking(True)

		self._burst = None
		self._drag_x = None
		self._carrier_estimate = 0.0

	@property
	def carrier_estimate(self):
		return self._carrier_estimate

	@property
	def burst(self):
		return self._burst

	@burst.setter
	def burst(self, value):
		self._burst = value
		if self.burst is not None:
			windowed_samples = self.burst.samples * scipy.signal.hanning(len(self.burst.samples))
			spectrum = numpy.fft.fftshift(numpy.fft.fft(windowed_samples))
			self._mag_spectrum = numpy.log(numpy.absolute(spectrum))
			self._burst_max = max(self._mag_spectrum)
		self.update()

	def paintEvent(self, event):
		painter = QtGui.QPainter()
		painter.begin(self)
		painter.fillRect(self.rect(), QtCore.Qt.black)

		painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
		if self.burst is not None:
			#painter.setPen(QtCore.Qt.green)
			path = QtGui.QPainterPath()
			path.moveTo(0, 0)
			for x in range(len(self._mag_spectrum)):
				y = self._mag_spectrum[x]
				path.lineTo(x, y)
			path.lineTo(len(self._mag_spectrum), 0)

			#if self._drag_x:
			painter.save()
			painter.translate(self.width(), self.height())
			scale_y = float(self.height()) / self._burst_max
			painter.scale(-self.scale_x, -scale_y)
			brush = QtGui.QBrush(QtCore.Qt.red)
			painter.fillPath(path, brush)
			painter.restore()
			
			painter.save()
			painter.translate(0, self.height())
			scale_y = float(self.height()) / self._burst_max
			painter.scale(self.scale_x, -scale_y)
			brush = QtGui.QBrush(QtCore.Qt.green)
			painter.fillPath(path, brush)
			painter.restore()
			
		painter.end()

	@property
	def scale_x(self):
		if self.burst is None:
			return 1.0
		else:
			return float(self.width()) / len(self._mag_spectrum)

	def mousePressEvent(self, event):
		self._drag_x = event.pos().x()
		return super(SpectrumView, self).mousePressEvent(event)

	def _moveDeltaF(self, event):
		delta_x = event.pos().x() - self._drag_x
		delta_f = float(delta_x) / self.width() * self.burst.sampling_rate
		return delta_f

	def mouseMoveEvent(self, event):
		f = (float(event.x()) / self.width() - 0.5) * self.burst.sampling_rate
		QtGui.QToolTip.showText(event.globalPos(), '%.0f Hz' % (f,))
		if event.buttons() and QtCore.Qt.LeftButton:
			self.translation_frequency_changing.emit(self._moveDeltaF(event))
		return super(SpectrumView, self).mouseMoveEvent(event)

	def mouseReleaseEvent(self, event):
		if event.button() == QtCore.Qt.LeftButton:
			self.translation_frequency_changed.emit(self._moveDeltaF(event))
			self._drag_x = None
		return super(SpectrumView, self).mouseReleaseEvent(event)

	def sizeHint(self):
		return QtCore.QSize(50, 50)

def get_cfile_list(path):
	path_glob = os.path.join(path, 'file*.dat')
	#path_glob = os.path.join(path, '*.cfile')
	filenames = glob.glob(path_glob)
	filenames = sorted(filenames, key=lambda s: int(s.split('_')[1]))
	return filenames

def translate_burst(burst, new_frequency):
	if burst is None:
		return None
	mix = numpy.arange(burst.sample_count, dtype=numpy.float32) * 2.0j * numpy.pi * new_frequency / burst.sampling_rate
	mix = numpy.exp(mix) * burst.samples
	return TimeData(mix, burst.sampling_rate)

class Slider(QtGui.QWidget):
	value_changed = QtCore.Signal(float)

	def __init__(self, name, low_value, high_value, increment, default_value, parent=None):
		super(Slider, self).__init__(parent=parent)

		self._increment = increment
		low_int = int(math.floor(float(low_value) / increment))
		high_int = int(math.ceil(float(high_value) / increment))

		self.label = QtGui.QLabel(self)
		self.label.setText(name)
		
		self.slider = QtGui.QSlider(QtCore.Qt.Horizontal, self)
		self.slider.setRange(low_int, high_int)
		self.slider.valueChanged[int].connect(self._value_changed)

		self.text = QtGui.QLabel(self)
		self.text.setText(str(self.value))

		self.layout = QtGui.QBoxLayout(QtGui.QBoxLayout.LeftToRight)
		self.layout.addWidget(self.label)
		self.layout.addWidget(self.slider)
		self.layout.addWidget(self.text)

		self.setLayout(self.layout)

		self.value = default_value

	@property
	def value(self):
		return self.slider.sliderPosition() * self._increment

	@value.setter
	def value(self, new_value):
		#self.slider.setTracking(false)
		self.slider.setSliderPosition(int(round(float(new_value) / self._increment)))
		#self.slider.setTracking(true)

	def _value_changed(self, value):
		self.text.setText(str(self.value))
		self.value_changed.emit(self.value)

class QFileListWidget(QtGui.QListWidget):
	file_changed = QtCore.Signal(str)
	file_deleted = QtCore.Signal(str)

	def __init__(self, file_paths, parent=None):
		super(QFileListWidget, self).__init__(parent)

		for file_path in file_paths:
			file_dir, file_name = os.path.split(file_path)
			file_item = QtGui.QListWidgetItem(file_name)
			file_item.setData(32, file_path)
			self.addItem(file_item)
		self.currentItemChanged.connect(self._file_changed)

	def keyPressEvent(self, event):
		if event.matches(QtGui.QKeySequence.Delete):
			self._delete_selected_items()
		super(QFileListWidget, self).keyPressEvent(event)

	def _file_changed(self, selected, deselected):
		file_path = selected.data(32)
		self.file_changed.emit(file_path)

	def _delete_selected_items(self):
		for item in self.selectedItems():
			file_path = item.data(32)
			self.file_deleted.emit(file_path)
			row = self.row(item)
			self.takeItem(row)

class ASKData(QtCore.QObject):
	channel_bandwidth_changed = QtCore.Signal(float)

	def __init__(self):
		super(ASKData, self).__init__()
		self._channel_bandwidth = 10000

	@property
	def channel_bandwidth(self):
		return self._channel_bandwidth

	@channel_bandwidth.setter
	def channel_bandwidth(self, new_value):
		self._channel_bandwidth = new_value
		self.channel_bandwidth_changed.emit(self._channel_bandwidth)

class FSKData(QtCore.QObject):
	deviation_changed = QtCore.Signal(float)

	def __init__(self):
		super(FSKData, self).__init__()
		self._deviation = 38400

	@property
	def deviation(self):
		return self._deviation

	@deviation.setter
	def deviation(self, new_value):
		self._deviation = new_value
		self.deviation_changed.emit(self._deviation)

class Burst(QtCore.QObject):
	symbol_rate_changed = QtCore.Signal(float)
	center_frequency_changed = QtCore.Signal(float)
	modulation_changed = QtCore.Signal(str)

	raw_changed = QtCore.Signal(object)
	translated_changed = QtCore.Signal(object)
	filtered_changed = QtCore.Signal(object)

	def __init__(self):
		super(Burst, self).__init__()
		self._symbol_rate = 19200
		self._center_frequency = 0
		self._modulation = 'fsk'
		self._raw = None
		self._translated = None
		self._filtered = None

	@property
	def symbol_rate(self):
		return self._symbol_rate

	@symbol_rate.setter
	def symbol_rate(self, new_value):
		self._symbol_rate = new_value
		self.symbol_rate_changed.emit(self._symbol_rate)
	
	@property
	def center_frequency(self):
		return self._center_frequency

	@center_frequency.setter
	def center_frequency(self, new_value):
		self._center_frequency = new_value
		self.center_frequency_changed.emit(self._center_frequency)
	
	@property
	def modulation(self):
		return self._modulation

	@modulation.setter
	def modulation(self, new_value):
		self._modulation = new_value
		self.modulation_changed.emit(self._modulation)
	
	@property
	def raw(self):
		return self._raw

	@raw.setter
	def raw(self, new_value):
		self._raw = new_value
		self.raw_changed.emit(self._raw)

	@property
	def translated(self):
		return self._translated

	@translated.setter
	def translated(self, new_value):
		self._translated = new_value
		self.translated_changed.emit(self._translated)

	@property
	def filtered(self):
		return self._filtered

	@filtered.setter
	def filtered(self, new_value):
		self._filtered = new_value
		self.filtered_changed.emit(self._filtered)

class ASKWidget(QtGui.QWidget):
	def __init__(self, burst, parent=None):
		super(ASKWidget, self).__init__(parent)

		self._taps = None

		self.burst = burst
		self.burst.translated_changed[object].connect(self.translated_changed)

		self.modulation = ASKData()
		self.modulation.channel_bandwidth_changed[float].connect(self.channel_bandwidth_changed)

		self.filtered_view = WaveWidget(self)

		self.channel_bandwidth_slider = Slider("Channel BW", 2.5e3, 25e3, 100, self.modulation.channel_bandwidth, self)
		self.channel_bandwidth_slider.value_changed[float].connect(self.channel_bandwidth_slider_changed)

		self.views_layout = QtGui.QGridLayout()
		self.views_layout.setContentsMargins(0, 0, 0, 0)
		self.views_layout.addWidget(self.channel_bandwidth_slider, 0, 0)
		self.views_layout.addWidget(self.filtered_view, 1, 0)
		self.setLayout(self.views_layout)

	def channel_bandwidth_slider_changed(self, value):
		self.modulation.channel_bandwidth = value

	def channel_bandwidth_changed(self, value):
		self.channel_bandwidth_slider.value = value
		self._update_filter(self.burst.translated)

	def translated_changed(self, translated):
		self._update_filtered(translated)

	def _update_filter(self, translated):
		if translated is not None:
			bands = (0, self.modulation.channel_bandwidth * 0.5, self.modulation.channel_bandwidth * 0.6, translated.sampling_rate * 0.5)
			gains = (1.0, 0.0)
			self._taps = scipy.signal.remez(257, bands, gains, Hz=translated.sampling_rate)
		else:
			self._taps = None
		self._update_filtered(translated)

	def _update_filtered(self, translated):
		if translated is not None and self._taps is not None:
			filtered = TimeData(numpy.complex64(scipy.signal.lfilter(self._taps, 1, translated.samples)), translated.sampling_rate)
			filtered_abs = filtered.abs

			data_source = filtered_abs.samples
			numpy_source = NumpySource(data_source)
			peak_detector = blocks.peak_detector_fb(1.0, 0.3, 10, 0.001)
			sample_and_hold = blocks.sample_and_hold_ff()
			multiply_const = blocks.multiply_const_vff((0.5, ))
			subtract = blocks.sub_ff(1)
			numpy_sink = NumpySink(numpy.float32)
			top = gr.top_block()
			top.connect((numpy_source, 0), (peak_detector, 0))
			top.connect((numpy_source, 0), (sample_and_hold, 0))
			top.connect((numpy_source, 0), (subtract, 0))
			top.connect((peak_detector, 0), (sample_and_hold, 1))
			top.connect((sample_and_hold, 0), (multiply_const, 0))
			top.connect((multiply_const, 0), (subtract, 1))
			top.connect((subtract, 0), (numpy_sink, 0))
			top.run()
			filtered = TimeData(numpy_sink.data, translated.sampling_rate)

			self.filtered_view.data = filtered
			# abs_min = filtered.abs.min
			# abs_max = filtered.abs.max
			# abs_mid = (abs_min + abs_max) / 2.0

			# self.burst.filtered = filtered.abs - abs_mid
			self.burst.filtered = filtered
		else:
			self.filtered_view.data = None
			self.burst.filtered = None

class FSKWidget(QtGui.QWidget):
	def __init__(self, burst, parent=None):
		super(FSKWidget, self).__init__(parent)

		self._taps_p = None
		self._taps_n = None

		self.burst = burst
		self.burst.symbol_rate_changed[float].connect(self.symbol_rate_changed)
		self.burst.translated_changed[object].connect(self.translated_changed)

		self.modulation = FSKData()
		self.modulation.deviation_changed[float].connect(self.deviation_changed)

		self.eye_view = EyeWidget(self)

		self.deviation_slider = Slider("Deviation", 5e3, 50e3, 100, self.modulation.deviation, self)
		self.deviation_slider.value_changed[float].connect(self.deviation_slider_changed)

		self.views_layout = QtGui.QGridLayout()
		self.views_layout.setContentsMargins(0, 0, 0, 0)
		self.views_layout.addWidget(self.deviation_slider, 0, 0)
		self.views_layout.addWidget(self.eye_view, 1, 0)
		self.setLayout(self.views_layout)

	def translated_changed(self, translated):
		if self.isVisible():
			self._update_filtered(translated)

	def deviation_slider_changed(self, value):
		self.modulation.deviation = value

	def symbol_rate_changed(self, value):
		if self.isVisible():
			self._update_filter(self.burst.translated)

	def deviation_changed(self, value):
		self.deviation_slider.value = value
		self._update_filter(self.burst.translated)

	def _update_filter(self, translated):
		if translated is not None:
			samples_per_symbol = translated.sampling_rate / self.burst.symbol_rate
			tap_count = int(math.floor(samples_per_symbol))
			x = numpy.arange(tap_count, dtype=numpy.float32) * 2.0j * numpy.pi / translated.sampling_rate
			self._taps_n = numpy.exp(x * -self.modulation.deviation)
			self._taps_p = numpy.exp(x *  self.modulation.deviation)
		else:
			self._taps_n = None
			self._taps_p = None
		self._update_filtered(translated)

	def _update_filtered(self, translated):
		if translated is not None and self._taps_n is not None and self._taps_p is not None:
			filtered_data_1 = TimeData(numpy.complex64(scipy.signal.lfilter(self._taps_n, 1, translated.samples)), translated.sampling_rate)
			filtered_data_2 = TimeData(numpy.complex64(scipy.signal.lfilter(self._taps_p, 1, translated.samples)), translated.sampling_rate)
			self.eye_view.data = (filtered_data_1.abs, filtered_data_2.abs)
			self.burst.filtered = TimeData(filtered_data_2.abs.samples - filtered_data_1.abs.samples, filtered_data_1.sampling_rate)
		else:
			self.eye_view.data = (None, None)
			self.burst.filtered = None

class Browser(QtGui.QWidget):
	def __init__(self, path, parent=None):
		super(Browser, self).__init__(parent)
		self.setGeometry(0, 0, 1500, 700)

		self.burst = Burst()
		self.burst.symbol_rate_changed[float].connect(self.symbol_rate_changed)
		self.burst.raw_changed[object].connect(self.raw_changed)
		self.burst.filtered_changed[object].connect(self.filtered_changed)

		self.file_path = None

		file_paths = get_cfile_list(path)
		self.file_list_view = QFileListWidget(file_paths)
		self.file_list_view.file_changed.connect(self.set_file)
		self.file_list_view.file_deleted.connect(self.delete_file)

		self.views_widget = QtGui.QFrame()
		#self.views_widget.setFrameStyle(QtGui.QFrame.NoFrame)
		#self.views_widget.setContentsMargins(0, 0, 0, 0)

		self.splitter = QtGui.QSplitter()
		self.splitter.addWidget(self.file_list_view)
		self.splitter.addWidget(self.views_widget)
		self.splitter.setSizes([200, 0])
		self.splitter.setStretchFactor(0, 0)
		self.splitter.setStretchFactor(1, 1)

		self.am_view = AMWidget(self)
		self.am_view.range_changed.connect(self.range_changed)

		self.fm_view = FMWidget(self)

		self.spectrum_view = SpectrumView()
		self.spectrum_view.translation_frequency_changing.connect(self.translation_frequency_changing)
		self.spectrum_view.translation_frequency_changed.connect(self.translation_frequency_changed)

		self.modulation_tabs = QtGui.QTabWidget()
		self.modulation_tabs.currentChanged[int].connect(self.modulation_tab_changed)
		self.tab_ask = ASKWidget(self.burst)
		self.modulation_tabs.addTab(self.tab_ask, "ASK")
		self.tab_fsk = FSKWidget(self.burst)
		self.modulation_tabs.addTab(self.tab_fsk, "FSK")
		self.modulation_tabs.setCurrentWidget(self.tab_fsk)

		self.translation_frequency_slider = Slider("F Shift", -200e3, 200e3, 1e3, self.burst.center_frequency, self)
		self.translation_frequency_slider.value_changed[float].connect(self.translation_frequency_slider_changed)

		self.symbol_rate_slider = Slider("Symbol Rate", 5e3, 25e3, 10, self.burst.symbol_rate, self)
		self.symbol_rate_slider.value_changed[float].connect(self.symbol_rate_slider_changed)

		self.slicer_view = SlicerWidget(self)
		self.sliced_view = SlicerWidget(self)

		self._gain_mu = 0.2
		self._gain_omega = 0.25 * self._gain_mu * self._gain_mu
		self._omega_relative_limit = 0.001

		self.views_layout = QtGui.QGridLayout()
		self.views_layout.setContentsMargins(0, 0, 0, 0)
		self.views_layout.addWidget(self.am_view, 0, 0)
		self.views_layout.addWidget(self.fm_view, 1, 0)
		self.views_layout.addWidget(self.spectrum_view, 2, 0)
		self.views_layout.addWidget(self.translation_frequency_slider, 3, 0)
		self.views_layout.addWidget(self.modulation_tabs, 4, 0)
		self.views_layout.addWidget(self.symbol_rate_slider, 5, 0)
		self.views_layout.addWidget(self.slicer_view, 6, 0)
		self.views_layout.addWidget(self.sliced_view, 7, 0)
		self.views_layout.setRowStretch(0, 0)
		self.views_layout.setRowStretch(1, 0)
		self.views_layout.setRowStretch(2, 0)
		self.views_layout.setRowStretch(3, 0)
		self.views_layout.setRowStretch(4, 0)
		self.views_layout.setRowStretch(5, 0)
		self.views_layout.setRowStretch(6, 0)
		self.views_layout.setRowStretch(7, 0)
		self.views_layout.setRowStretch(8, 1)
		self.views_widget.setLayout(self.views_layout)

		self.top_layout = QtGui.QVBoxLayout()
		self.top_layout.addWidget(self.splitter)

		self.setLayout(self.top_layout)

	def modulation_tab_changed(self, tab_index):
		modulation_tab = self.modulation_tabs.widget(tab_index)
		if modulation_tab == self.tab_ask:
			self.burst.modulation = 'ask'
		elif modulation_tab == self.tab_fsk:
			self.burst.modulation = 'fsk'
		else:
			self.burst.modulation = None

	def symbol_rate_changed(self, value):
		self.symbol_rate_slider.value = value
		self._update_sliced(self.burst.filtered)

	def symbol_rate_slider_changed(self, value):
		self.burst.symbol_rate = value

	def range_changed(self, start_time, end_time):
		print('%f %f' % (start_time, end_time))
		start_sample = int(start_time * self.burst.raw.sampling_rate)
		end_sample = int(end_time * self.burst.raw.sampling_rate)
		self.burst.translated = TimeData(self.burst.raw.samples[start_sample:end_sample], self.burst.raw.sampling_rate)
		self.spectrum_view.burst = self.burst.translated

	def shift_translation_frequency(self, frequency_shift):
		new_frequency = self.burst.center_frequency + frequency_shift
		sampling_rate = self.burst.raw.sampling_rate
		nyquist_frequency = sampling_rate / 2.0
		while new_frequency < -nyquist_frequency:
			new_frequency += sampling_rate
		while new_frequency >= nyquist_frequency:
			new_frequency -= sampling_rate
		return new_frequency

	def translation_frequency_changing(self, frequency_shift):
		new_frequency = self.shift_translation_frequency(frequency_shift)
		self.burst.translated = translate_burst(self.burst.raw, new_frequency)
		self.spectrum_view.burst = self.burst.translated

	def translation_frequency_changed(self, frequency_shift):
		self.burst.center_frequency = self.shift_translation_frequency(frequency_shift)
		self.translation_frequency_slider.value = self.burst.center_frequency
		self._update_translation(self.burst.raw)

	def translation_frequency_slider_changed(self, translation_frequency):
		self.burst.center_frequency = translation_frequency
		self._update_translation(self.burst.raw)

	def raw_changed(self, data):
		self.am_view.data = self.burst.raw
		self.fm_view.data = self.burst.raw
		self._update_translation(data)

	def filtered_changed(self, data):
		self._update_sliced(data)

	# carrier_frequency, spread_frequency = estimate_fsk_carrier(self._burst)
	#burst_characteristics = classify_burst(self._burst)

	#self._translation_frequency = -burst_characteristics['carrier']
	#if burst_characteristics['modulation'] == 'fsk':
	#   self.deviation_slider.value = burst_characteristics['deviation']

	@property
	def metadata_filename(self):
		if self.file_path:
			file_basename, file_extension = os.path.splitext(self.file_path)
			return '%s%s' % (file_basename, '.yaml')
		else:
			return None

	def _update_yaml(self):
		if self.metadata_filename:
			data = {
				'symbol_rate': self.burst.symbol_rate,
				'modulation': {
					'type': self.burst.modulation,
				},
				'center_frequency': self.burst.center_frequency,
			}
			if self.burst.modulation == 'ask':
				data['modulation']['channel_bandwidth'] = self.tab_ask.modulation.channel_bandwidth
			if self.burst.modulation == 'fsk':
				data['modulation']['deviation'] = self.tab_fsk.modulation.deviation
			data_yaml = yaml.dump(data)
			f_yaml = open(self.metadata_filename, 'w')
			f_yaml.write(data_yaml)
			f_yaml.close()

	def set_file(self, file_path):
		if self.metadata_filename:
			self._update_yaml()

		self.file_path = file_path

		if os.path.exists(self.metadata_filename):
			f_yaml = open(self.metadata_filename, 'r')
			metadata = yaml.load(f_yaml)
			self.burst.symbol_rate = metadata['symbol_rate']
			self.burst.center_frequency = metadata['center_frequency']
			if 'modulation' in metadata:
				modulation = metadata['modulation']
				if modulation['type'] == 'ask':
					self.tab_ask.modulation.channel_bandwidth = modulation['channel_bandwidth']
					self.modulation_tabs.setCurrentWidget(self.tab_ask)
				elif modulation['type'] == 'fsk':
					self.tab_fsk.modulation.deviation = modulation['deviation']
					self.modulation_tabs.setCurrentWidget(self.tab_fsk)

		data = numpy.fromfile(file_path, dtype=numpy.complex64)
		sampling_rate = 400e3
		self.burst.raw = TimeData(data, sampling_rate)

	def delete_file(self, file_path):
		file_base, file_ext = os.path.splitext(file_path)
		file_glob = '%s%s' % (file_base, '.*')
		for matched_file_path in glob.glob(file_glob):
			os.remove(matched_file_path)

	def _update_translation(self, raw_data):
		self.burst.translated = translate_burst(raw_data, self.burst.center_frequency)
		self.spectrum_view.burst = self.burst.translated

	def _update_sliced(self, filtered_symbols):
		self.slicer_view.data = filtered_symbols

		if filtered_symbols is None:
			self.sliced_view.data = None
			return

		omega = float(filtered_symbols.sampling_rate) / self.burst.symbol_rate
		mu = 0.5

		data_source = filtered_symbols.samples
		numpy_source = NumpySource(data_source)
		clock_recovery = digital.clock_recovery_mm_ff(omega, self._gain_omega, mu, self._gain_mu, self._omega_relative_limit)
		numpy_sink = NumpySink(numpy.float32)
		top = gr.top_block()
		top.connect(numpy_source, clock_recovery)
		top.connect(clock_recovery, numpy_sink)
		top.run()
		symbol_data = numpy_sink.data

		# TODO: Adjust sampling rate
		bits = []
		for i in range(len(symbol_data)):
			if symbol_data[i] >= 0:
				symbol_data[i] = 1
				bits.append('1')
			else:
				symbol_data[i] = -1
				bits.append('0')
		bits = ''.join(bits)
		#print(bits)

		self.sliced_view.data = TimeData(symbol_data, self.burst.symbol_rate)

if __name__ == '__main__':
	app = QtGui.QApplication(sys.argv)

	browser = Browser(sys.argv[1])
	browser.show()

	sys.exit(app.exec_())

########NEW FILE########
__FILENAME__ = extract_bursts
#!/usr/bin/env python

#
# Copyright 2013 Jared Boone
#
# This file is part of the TPMS project.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#

from gnuradio import blocks
from gnuradio import eng_notation
from gnuradio import filter
from gnuradio import gr
from gnuradio.eng_option import eng_option
from gnuradio.filter import firdes
from optparse import OptionParser
import math
import sys
import os.path
import datetime
import pytz
from iso8601 import iso8601

from burst_detector import *

class top_block(gr.top_block):

    def __init__(self, source_path):
        gr.top_block.__init__(self, "Top Block")

        source_directory, source_filename = os.path.split(source_path)
        source_filename, source_extension = os.path.splitext(source_filename)
        target_signal, carrier_freq, sampling_rate, start_date, start_time, capture_device = source_filename.split('_')

        if sampling_rate[-1].upper() == 'M':
            sampling_rate = float(sampling_rate[:-1]) * 1e6
        else:
            raise RuntimeError('Unsupported sampling rate "%s"' % sampling_rate)

        start_timestamp = iso8601.datetime.strptime(start_date + ' ' + start_time, '%Y%m%d %H%M%Sz')
        utc = pytz.utc
        start_timestamp = utc.localize(start_timestamp)
        f_ts = open('timestamp.txt', 'w')
        f_ts.write(start_timestamp.isoformat())
        f_ts.close()

        ##################################################
        # Variables
        ##################################################
        self.samp_rate = samp_rate = sampling_rate
        self.average_window = average_window = 1000

        ##################################################
        # Blocks
        ##################################################
        self.blocks_file_source_0 = blocks.file_source(gr.sizeof_gr_complex*1, source_path, False)
        self.burst_detector = burst_detector()
        self.blocks_tagged_file_sink_0 = blocks.tagged_file_sink(gr.sizeof_gr_complex*1, samp_rate)

        ##################################################
        # Connections
        ##################################################
        self.connect((self.blocks_file_source_0, 0), (self.burst_detector, 0))
        self.connect((self.burst_detector, 0), (self.blocks_tagged_file_sink_0, 0))

if __name__ == '__main__':
    parser = OptionParser(option_class=eng_option, usage="%prog: [options]")
    (options, args) = parser.parse_args()
    tb = top_block(sys.argv[1])
    tb.start()
    tb.wait()


########NEW FILE########
__FILENAME__ = numpy_block
#!/usr/bin/env python

#
# Copyright 2013 Jared Boone
#
# This file is part of the TPMS project.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#

from gnuradio import gr

import numpy

class NumpySource(gr.sync_block):
	def __init__(self, data):
		super(NumpySource, self).__init__("NumpySource", None, [data.dtype])
		self._data = data

	def work(self, input_items, output_items):
		if len(self._data) == 0:
			return -1

		noutput_items = min(len(output_items[0]), len(self._data))
		#print('source %s' % noutput_items)
		output_items[0][:noutput_items] = self._data[:noutput_items]
		self._data = self._data[noutput_items:]
		return noutput_items

class NumpySink(gr.sync_block):
	def __init__(self, dtype=None):
		super(NumpySink, self).__init__("NumpySink", [dtype], None)

		self._data = numpy.empty((0,), dtype=dtype)

	def work(self, input_items, output_items):
		noutput_items = len(input_items[0])
		if noutput_items > 0:
			#print('sink %s' % noutput_items)
			self._data = numpy.concatenate((self._data, input_items[0]))
		return noutput_items

	@property
	def data(self):
		return self._data

########NEW FILE########
__FILENAME__ = packet
#!/usr/bin/env python

#
# Copyright 2013 Jared Boone
#
# This file is part of the TPMS project.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#

from gnuradio import gr

import math
import numpy

def packet_format(l):
	if 'X' in l:
		return None
	else:
		return ''.join(map(str, l))

def packet_print(l):
	formatted = packet_format(l)
	if formatted is not None:
		print(formatted)

class Packetizer(gr.sync_block):
	def __init__(self):
		super(Packetizer, self).__init__(
			"Packetizer",
			[numpy.uint8],
			None
		)
		self._data = None

	@property
	def data(self):
		return self._data

	def work(self, input_items, output_items):
		nitems = len(input_items[0])
		
		if self._data is None:
			self._data = input_items[0].copy()
		else:
			self._data = numpy.concatenate((self._data, input_items[0]))
			
		return len(input_items[0])





def blank_array_range(data, center, deviation):
	low_n = max(center - deviation, 0)
	high_n = min(center + deviation, len(data))
	data[low_n:high_n] = 0



from matplotlib import pyplot
import scipy.stats
import scipy.signal




def packet_classify(data, sampling_rate):
	# From "Automatic Modulation Recognition of Communication Signals"
	#
	# a = numpy.absolute(data)
	# m_a = sum(a) / len(data)
	# #print('m_a', m_a)
	# a_n = a / m_a
	# a_cn = a_n - 1.0
	# a_cn_dft = numpy.absolute(numpy.fft.fftshift(numpy.fft.fft(a_cn)))
	# gamma_max = numpy.max(numpy.power(a_cn_dft, 2.0))
	# t_gamma_max = 10000
	# if gamma_max < t_gamma_max:
	# 	modulation_alt = 'fsk'
	# else:
	# 	modulation_alt = 'ask'
	# a_t = 0.5

	# From "Fuzzy logic classifier for radio signals recognition"
	#
	# envelope = a
	# k1 = scipy.stats.kurtosis(envelope, fisher=False, bias=False)
	# print(k1)

	windowed_samples = data * scipy.signal.hanning(len(data))
	spectrum = numpy.fft.fftshift(numpy.fft.fft(windowed_samples))
	spectrum_mag = numpy.absolute(spectrum)
	# spectrum_mag_sum = sum(spectrum_mag)
	# spectrum_mag_avg = spectrum_mag_sum / len(spectrum_mag)

	def arg_hz(n):
		return ((n / float(len(spectrum_mag))) - 0.5) * sampling_rate

	mute_offset_hz = 2e3
	mute_offset_n = int(math.ceil(float(mute_offset_hz) / sampling_rate * len(spectrum_mag)))
	
	peak1_n = numpy.argmax(spectrum_mag)
	peak1_hz = arg_hz(peak1_n)
	peak1_mag = spectrum_mag[peak1_n]
	#print('peak 1: %s %s' % (peak1_hz, peak1_mag))
	blank_array_range(spectrum_mag, peak1_n, mute_offset_n)

	#peak2_n_boundary = max(0, peak1_n - mute_offset_n)
	#peak2_n = numpy.argmax(spectrum_mag[:peak2_n_boundary])
	peak2_n = numpy.argmax(spectrum_mag)
	peak2_hz = arg_hz(peak2_n)
	peak2_mag = spectrum_mag[peak2_n]
	#peak2_avg = sum(spectrum_mag[peak2_n-mute_offset_n:peak2_n+mute_offset_n]) / (2 * mute_offset_n)
	#print('peak 2: %s %s' % (peak2_hz, peak2_mag))
	blank_array_range(spectrum_mag, peak2_n, mute_offset_n)

	#peak3_n_boundary = min(len(spectrum_mag), peak1_n + mute_offset_n)
	#peak3_n = numpy.argmax(spectrum_mag[peak3_n_boundary:]) + peak3_n_boundary
	peak3_n = numpy.argmax(spectrum_mag)
	peak3_hz = arg_hz(peak3_n)
	peak3_mag = spectrum_mag[peak3_n]
	#peak3_avg = sum(spectrum_mag[peak3_n-mute_offset_n:peak3_n+mute_offset_n]) / (2 * mute_offset_n)
	#print('peak 3: %s %s' % (peak3_hz, peak3_mag))
	#blank_array_range(spectrum_mag, peak3_n, mute_offset_n)

	#print('lobes: %s / %s' % (peak2_avg, peak3_avg))

	peak23_hz_avg = (peak2_hz + peak3_hz) / 2.0

	# peak_threshold = spectrum_mag_avg * 5.0
	# peaks = [x for x in spectrum_mag if x > peak_threshold]
	# total_weight = len(peaks)
	# if total_weight > 0:
	# 	centroid = sum([arg_hz(i) for i in range(len(spectrum_mag)) if spectrum_mag[i] > peak_threshold])
	# 	print(total_weight, centroid, centroid / total_weight)
	# else:
	# 	print('too much noise')

	result = {}
	# result['modulation_alt'] = modulation_alt

	# If all three peaks are within 1kHz, it's probably AM.
	is_ask = abs(peak1_hz - peak23_hz_avg) < 1e3

	# is_ask = k1 > 3.2
	# is_fsk = not is_ask

	if is_ask:
		shift_hz = peak1_hz
		baud_rate = (abs(peak3_hz - peak1_hz) + abs(peak2_hz - peak1_hz)) / 2.0
		result['modulation'] = 'ask'
		result['carrier'] = shift_hz
		result['baud_rate'] = baud_rate
	else:
		peak2_1_delta = peak1_n - peak2_n
		peak1_3_delta = peak3_n - peak1_n

		# peak2_1_avg = sum(spectrum_mag[peak2_n:peak1_n]) / float(peak2_1_delta)
		# print('peak2_1_avg:', peak2_1_avg)
		# peak1_3_avg = sum(spectrum_mag[peak1_n:peak3_n]) / float(peak1_3_delta)
		# print('peak1_3_avg:', peak1_3_avg)

		# print('lo lobe mag:', spectrum_mag[peak2_n - peak1_3_delta])
		# print('hi lobe mag:', spectrum_mag[peak3_n + peak2_1_delta])

		# peak_lo_lobe_avg = sum(spectrum_mag[peak2_n - peak1_3_delta:peak2_n]) / float(peak1_3_delta)
		# peak_lo_1_3_ratio = peak_lo_lobe_avg / peak1_3_avg
		# print('peak_lo_lobe_avg:', peak_lo_lobe_avg)
		# print('low lobe ratio:', peak_lo_1_3_ratio)
		# peak_hi_lobe_avg = sum(spectrum_mag[peak3_n:peak3_n + peak2_1_delta]) / float(peak2_1_delta)
		# peak_hi_2_1_ratio = peak_hi_lobe_avg / peak2_1_avg
		# print('peak_hi_lobe_avg:', peak_hi_lobe_avg)
		# print('high lobe ratio:', peak_hi_2_1_ratio)

		# peak1_3_center_n = int(round((peak1_n + peak3_n) / 2.0))
		# peak1_3_center_lo_avg = sum(spectrum_mag[peak1_n:peak1_3_center_n]) / float(peak1_3_center_n - peak1_n)
		# peak1_3_center_hi_avg = sum(spectrum_mag[peak1_3_center_n:peak3_n]) / float(peak3_n - peak1_3_center_n)
		# peak1_3_center_ratio = peak1_3_center_lo_avg / peak1_3_center_hi_avg
		# print('peak1_3 center avg:', peak1_3_center_lo_avg, peak1_3_center_hi_avg, peak1_3_center_ratio)
		# peak2_1_center_n = int(round((peak2_n + peak1_n) / 2.0))
		# peak2_1_center_lo_avg = sum(spectrum_mag[peak2_n:peak2_1_center_n]) / float(peak2_1_center_n - peak2_n)
		# peak2_1_center_hi_avg = sum(spectrum_mag[peak2_1_center_n:peak1_n]) / float(peak1_n - peak2_1_center_n)
		# peak2_1_center_ratio = peak2_1_center_lo_avg / peak2_1_center_hi_avg
		# print('peak2_1 center avg:', peak2_1_center_lo_avg, peak2_1_center_hi_avg, peak2_1_center_ratio)

		# Mirroring stuff for correlation?
		# spectrum_mag[peak2_n:peak2_1_center_n]
		# spectrum_mag[peak1_n:peak2_1_center_n:-1]

		#other_peak_hz = peak3_hz if peak3_mag > peak2_mag else peak2_hz
		if peak2_1_delta > peak1_3_delta:
			other_peak_hz = peak2_hz
		else:
			other_peak_hz = peak3_hz

		shift_hz = (peak1_hz + other_peak_hz) / 2.0
		diff_hz = abs(other_peak_hz - peak1_hz)
		deviation_hz = diff_hz / 2.0




		# translated = numpy.arange(len(data), dtype=numpy.float32) * 2.0j * numpy.pi * -shift_hz / sampling_rate
		# translated = numpy.exp(translated) * data
		# fm_demod = numpy.angle(translated[1:] * numpy.conjugate(translated[:-1]))
		# x = numpy.arange(len(fm_demod)) * (1.0 / sampling_rate)
		# # plot(spectrum_mag)
		# plot(x, fm_demod)
		# show()




		result['modulation'] = 'fsk'
		result['carrier'] = shift_hz
		result['deviation'] = deviation_hz

	# print('%s: %s %s' % (
	# 	result['modulation'],
	# 	result['carrier'],
	# 	result['deviation'] if 'deviation' in result else result['baud_rate'],
	# ))

	#print('%s / %s (%s)' % (result['modulation_alt'], result['modulation'], gamma_max))

	# pyplot.subplot(411)
	# x = numpy.arange(len(data)) / sampling_rate
	# pyplot.plot(x, numpy.absolute(data))

	# pyplot.subplot(412)
	# fm_demod = numpy.angle(data[1:] * numpy.conjugate(data[:-1]))
	# x = numpy.arange(len(fm_demod)) / sampling_rate
	# pyplot.plot(x, fm_demod)
	
	# pyplot.subplot(413)
	# x = numpy.fft.fftshift(numpy.fft.fftfreq(len(data))) * sampling_rate
	# mag = numpy.absolute(numpy.fft.fftshift(numpy.fft.fft(data)))
	# db = numpy.log10(mag) * 10.0
	# mag_max = max(mag)
	# mag_avg = sum(mag) / len(mag)
	# snr = math.log10(mag_max / mag_avg) * 10.0
	# print('SNR: %f - %f = %f' % (mag_max, mag_avg, snr))
	# pyplot.plot(x, db)

	# pyplot.subplot(414)
	# correlation = scipy.signal.correlate(spectrum_mag, spectrum_mag[::-1])
	# correlation_n = numpy.argmax(correlation) - len(correlation) / 2.0
	# print(correlation_n)
	# #convolution_f = float(convolution_n) / len(spectrum_mag) / 2.0 * sampling_rate
	# pyplot.plot(correlation)
	# pyplot.show()

	# cwt = scipy.signal.cwt(data, scipy.signal.ricker, (10, 11,))
	# pyplot.plot(cwt)
	# pyplot.show()

	return result

########NEW FILE########
__FILENAME__ = packet_decode
#!/usr/bin/env python

#
# Copyright 2013 Jared Boone
#
# This file is part of the TPMS project.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#

import sys
import pytz
from iso8601 import iso8601


def decode_packet_candidates(packet_info, decoder_fns):
	results = {}

	for decoder_fn in decoder_fns:
		decoded_set = set()
		for actual_access_code, data in packet_info:
			decoded = decoder_fn(data)
			decoded = ''.join(decoded)
			decoded = decoded.split('X')[0]
			if len(decoded) >= 32:
				#print('R %s %s' % (''.join(map(str, actual_access_code)), ''.join(map(str, data))))
				decoded_set.add(decoded)

		if decoded_set:
			results[decoder_fn.__name__] = decoded_set

	return results

packet_data = open(sys.argv[1], 'r')

for packet_info in packet_data:
	timestamp, encoding, access_code, payload, modulation, f_offset, deviation, bit_rate, filename = packet_info.split()
	timestamp = iso8601.parse_date(timestamp)

	decoded_packets = decode_packet_candidates(packet_info,
		(manchester_decode, differential_manchester_decode)
	)
	for decoder_type, decoder_data in decoded_packets.iteritems():
		results.append({
			'decoder': decoder_type,
			'data': decoder_data,
			'carrier': carrier_hz,
			'modulation': 'fsk',
			'symbol_rate': symbol_rate,
			'deviation': deviation,
			'access_code': access_code,
		})

	print(timestamp)
########NEW FILE########
__FILENAME__ = packet_graph
#!/usr/bin/env python

#
# Copyright 2013 Jared Boone
#
# This file is part of the TPMS project.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#

import sys
from argparse import ArgumentParser

from iso8601 import iso8601

from matplotlib import pyplot

parser = ArgumentParser()
parser.add_argument('--range', type=str, help="Range of bits to graph")
args = parser.parse_args()

args.range = tuple(map(int, args.range.split(',')))

decoded_packets = []

packet_fields = ('timestamp', 'access_code', 'payload', 'modulation', 'carrier', 'deviation', 'symbol_rate', 'filename')

for packet_line in sys.stdin:
	packet = dict(zip(packet_fields, packet_line.split()))
	packet['timestamp'] = iso8601.parse_date(packet['timestamp'])
	packet['carrier'] = float(packet['carrier'])
	packet['deviation'] = float(packet['deviation'])
	packet['symbol_rate'] = float(packet['symbol_rate'])

	decoded_packets.append(packet)

pyplot.title('Range %d:%d' % args.range)
pyplot.xlabel('Time UTC')
pyplot.ylabel('Value')
x = []
y = []
for packet in sorted(decoded_packets, key=lambda a: a['timestamp']):
	x.append(packet['timestamp'])
	y.append(int(packet['payload'][args.range[0]:args.range[1]], 2))
pyplot.plot(x, y)
pyplot.show()

########NEW FILE########
__FILENAME__ = packet_stats
#!/usr/bin/env python

#
# Copyright 2013 Jared Boone
#
# This file is part of the TPMS project.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#

import sys
import math
from collections import defaultdict
from argparse import ArgumentParser

import pytz
from iso8601 import iso8601

from bit_coding import *

def split_string_bytes(data, start_offset):
	yield data[:start_offset]
	for n in range(start_offset, len(data), 8):
		yield data[n:n+8]

parser = ArgumentParser()
parser.add_argument('-l', '--length', type=int, default=None, help="Required packet decoded symbol length (longer packets will be truncated)")
parser.add_argument('-e', '--encoding', type=str, default='raw', help="Bit encoding (man, diffman)")
parser.add_argument('--decoded', action="store_true", help="Display decoded packets")
parser.add_argument('--ruler', action="store_true", help="Display bit-index ruler along with decoded packets")
parser.add_argument('--lengthstats', action="store_true", help="Display statistics on packet length distribution")
parser.add_argument('--bitstats', action="store_true", help="Display statistics on each bit across all packets")
parser.add_argument('--brutecrc', type=int, default=None, help="Display packet data for brute force CRC, with packet occurrence above threshold")
parser.add_argument('--rangestats', type=str, default=None, help="Display statistics on a range of bits")
parser.add_argument('-v', '--verbose', action="store_true", default=False, help="Show more detail (if available)")
args = parser.parse_args()

if args.rangestats:
	args.rangestats = tuple(map(int, args.rangestats.split(',')))

decoder_map = {
	'man': manchester_decode,
	'diffman': differential_manchester_decode,
	'raw': lambda s: s,
}
decoder_fn = decoder_map[args.encoding]

packet_length_counts = defaultdict(int)
unique_packet_counts = defaultdict(int)

if args.length:
	byte_stats = [defaultdict(int) for n in range(int(math.ceil(args.length / 8.0)) + 1)]
	packet_first_byte_offset = args.length % 8

decoded_packets = []

packet_fields = ('timestamp', 'access_code', 'payload', 'modulation', 'carrier', 'deviation', 'symbol_rate', 'filename')

packet_count = 0
ruler_interval = 5

for packet_line in sys.stdin:
	packet_line = packet_line.strip()

	# TODO: Hack to skip the VOLK message that GNU Radio insists on writing to stdout.
	if packet_line.startswith('Using Volk machine: '):
		continue

	if len(packet_line) == 0:
		continue

	packet_line_split = packet_line.split()
	if len(packet_line_split) > 1:
		packet = dict(zip(packet_fields, packet_line_split))
		packet['timestamp'] = iso8601.parse_date(packet['timestamp'])
		packet['carrier'] = float(packet['carrier'])
		packet['deviation'] = float(packet['deviation'])
		packet['symbol_rate'] = float(packet['symbol_rate'])
	else:
		packet = {}
		packet['payload'] = packet_line_split[0]

	packet['payload'] = decoder_fn(packet['payload']).split('X')[0]
	if len(packet['payload']) == 0:
		continue

	if args.length:
		if len(packet['payload']) < args.length:
			continue
		# Truncate
		packet['payload'] = packet['payload'][:args.length]
		bytes = tuple(split_string_bytes(packet['payload'], packet_first_byte_offset))

		for n in range(len(bytes)):
			byte_stats[n][bytes[n]] += 1

	decoded_packets.append(packet)

	packet_length_counts[len(packet['payload'])] += 1
	unique_packet_counts[packet['payload']] += 1

	if args.decoded:
		if args.ruler and (packet_count % ruler_interval) == 0:
			s = []
			for i in range(10):
				s.append('%d----+----' % i)
			print(''.join(s))
		if args.verbose:
			print('%s %s %s %s %d %d %d %s' % (
				packet['timestamp'].isoformat(),
				packet['access_code'],
				packet['payload'],
				packet['modulation'],
				packet['carrier'],
				packet['deviation'],
				packet['symbol_rate'],
				packet['filename'],
			))
		else:
			print(packet['payload'])

	packet_count += 1

# if unique_packet_counts:
# 	print('Unique packets')
# 	for payload in sorted(unique_packet_counts.keys(), key=lambda a: len(a)):
# 		count = unique_packet_counts[payload]
# 		if args.length:
# 			payload_bytes_str = tuple(split_string_bytes(payload, packet_first_byte_offset))
# 			payload_bytes = map(lambda s: int(s, 2), payload_bytes_str)
# 			payload_sum = sum(payload_bytes[:-1])
# 			payload_sum_trunc = payload_sum & 0xff
# 			checksum = payload_bytes[-1]
# 			payload_sum_minus_checksum = payload_sum - checksum
# 			payload_sum_minus_checksum_trunc = payload_sum_minus_checksum & 0xff
# 			# TODO: Check for Hamming distance in payload and candidate checksum field.
# 			print('%s %4d sum=%s(%3d) diff=%s(%3d)' % (
# 				' '.join(payload_bytes_str), count,
# 				'{:0>8b}'.format(payload_sum_trunc), payload_sum_trunc,
# 				'{:0>8b}'.format(payload_sum_minus_checksum_trunc), payload_sum_minus_checksum_trunc
# 			))
# 		else:
# 			print(payload)
# 	print

if args.lengthstats:
	print('Length statistics:')
	length_accumulator = 0
	for n in sorted(packet_length_counts, reverse=True):
		length_accumulator += packet_length_counts[n]
		print('\t%2d: %3d   | %4d' % (n, packet_length_counts[n], length_accumulator))
	print

if args.brutecrc:
	for payload in sorted(unique_packet_counts.keys(), key=lambda a: unique_packet_counts[a], reverse=True):
		count = unique_packet_counts[payload]
		if count > args.brutecrc:
			print(payload)

if args.bitstats:
	print('Bit value statistics:')
	bit_stats = defaultdict(lambda: [0, 0])
	for payload in unique_packet_counts.keys():
		for n in range(len(payload)):
			value = payload[n]
			bit_stats[n][int(value)] += 1
	for n in sorted(bit_stats.keys()):
		stats = bit_stats[n]
		stat_h = stats[1]
		stat_l = stats[0]
		ratio_1 = float(stat_h) / float(stat_h + stat_l)
		bar = '*' * int(round(ratio_1 * 20))
		print('\t%3d: %4d/%4d %4d %5.1f%% %s' % (n, stat_h, stat_l, stat_h+stat_l, ratio_1 * 100, bar))
	print

if args.rangestats:
	if args.ruler:
		s = ' ' * args.rangestats[0] + '^' * (args.rangestats[1] - args.rangestats[0])
		print(s)
	print('Range %d:%d' % args.rangestats)
	range_stats = defaultdict(int)
	for payload in unique_packet_counts.keys():
		range_value = payload[args.rangestats[0]:args.rangestats[1]]
		range_stats[range_value] += unique_packet_counts[payload]
	for key in sorted(range_stats):
		print('%9x %12d %s: %3d %s' % (int(key, 2), int(key, 2), key, range_stats[key], '*' * range_stats[key]))
	print

# if args.length:
# 	print('Byte value statistics:')
# 	for n in range(len(byte_stats)):
# 		print('\tbyte %d:' % n)
# 		for key in sorted(byte_stats[n].keys()):
# 			count = byte_stats[n][key]
# 			print('\t\t%s: %d' % (key, count))
# 	print

########NEW FILE########
__FILENAME__ = ride_1_decode
#!/usr/bin/env python

#
# Copyright 2013 Jared Boone
#
# This file is part of the TPMS project.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#

import sys
from collections import defaultdict

import pytz
from iso8601 import iso8601

def split_string_bytes(data, start_offset):
	for n in range(start_offset, len(data), 8):
		yield data[n:n+8]

decoded_data = []

for packet_info in sys.stdin:
	timestamp, access_code, payload, modulation, f_offset, deviation, bit_rate, filename = packet_info.split()
	timestamp = iso8601.parse_date(timestamp)
	payload_bytes_str = tuple(split_string_bytes(payload, 1))
	payload_bytes = map(lambda v: int(v, 2), payload_bytes_str)
	payload_str = ''.join(map(chr, payload_bytes))
	device_id = ''.join(payload_bytes_str[0:4])
	flags = payload_bytes[6]
	calculated_checksum = (6 + sum(payload_bytes[0:7])) & 0xff
	packet_checksum = payload_bytes[7]
	checksum_ok = (calculated_checksum == packet_checksum)

	if checksum_ok:
		print('%s %s %d %d %d' % (
			timestamp.isoformat(),
			device_id,
			payload_bytes[4],
			payload_bytes[5],
			flags,
		))

########NEW FILE########
__FILENAME__ = ride_1_graph
#!/usr/bin/env python

#
# Copyright 2013 Jared Boone
#
# This file is part of the TPMS project.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#

import sys
from collections import defaultdict

from matplotlib import pyplot

from iso8601 import iso8601

decoded_data = []
for line in sys.stdin:
	line = line.split()
	item = {
		'timestamp': iso8601.parse_date(line[0]),
		'device_id': line[1],
		'value_1': float(line[2]),
		'value_2': float(line[3]),
		'flags': int(line[4]),
	}
	decoded_data.append(item)

by_device = defaultdict(list)
for item in decoded_data:
	by_device[item['device_id']].append(item)

pyplot.subplot(211)
pyplot.title('Value 1')
pyplot.xlabel('Time UTC')
pyplot.ylabel('???')
for device_id, items in by_device.iteritems():
	items = sorted(items, key=lambda v: v['timestamp'])
	by_device[device_id] = items
	x = [item['timestamp'] for item in items]
	y = [item['value_1'] for item in items]
	pyplot.plot(x, y, label=device_id)

pyplot.subplot(212)
pyplot.title('Value 2')
pyplot.xlabel('Time UTC')
pyplot.ylabel('???')
for device_id, items in by_device.iteritems():
	items = sorted(items, key=lambda v: v['timestamp'])
	by_device[device_id] = items
	x = [item['timestamp'] for item in items]
	y = [item['value_2'] for item in items]
	pyplot.plot(x, y, label=device_id)

pyplot.show()
########NEW FILE########
__FILENAME__ = ride_2_decode
#!/usr/bin/env python

#
# Copyright 2013 Jared Boone
#
# This file is part of the TPMS project.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#

import sys
from collections import defaultdict

import pytz
from iso8601 import iso8601

import crcmod

def split_string_bytes(data, start_offset):
	for n in range(start_offset, len(data), 8):
		yield data[n:n+8]

crc8 = crcmod.mkCrcFun(0x107, rev=False, initCrc=0, xorOut=0)

decoded_data = []

for packet_info in sys.stdin:
	timestamp, access_code, payload, modulation, f_offset, deviation, bit_rate, filename = packet_info.split()
	timestamp = iso8601.parse_date(timestamp)
	payload_bytes_str = tuple(split_string_bytes(payload, 5))
	payload_bytes = map(lambda v: int(v, 2), payload_bytes_str)
	payload_str = ''.join(map(chr, payload_bytes))
	pressure = payload_bytes[0] / 5.0
	temperature = payload_bytes[1]
	device_id = ''.join(payload_bytes_str[2:6])
	flags = payload_bytes[6]
	calculated_crc = crc8(payload_str[0:7])
	packet_crc = payload_bytes[7]
	crc_ok = (calculated_crc == packet_crc)

	if crc_ok:
		print('%s %s %.1f %d %d' % (
			timestamp.isoformat(),
			device_id,
			pressure,
			temperature,
			flags,
		))

########NEW FILE########
__FILENAME__ = ride_2_graph
#!/usr/bin/env python

#
# Copyright 2013 Jared Boone
#
# This file is part of the TPMS project.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#

import sys
from collections import defaultdict

from matplotlib import pyplot

from iso8601 import iso8601

decoded_data = []
for line in sys.stdin:
	line = line.split()
	item = {
		'timestamp': iso8601.parse_date(line[0]),
		'device_id': line[1],
		'pressure': float(line[2]),
		'temperature': float(line[3]),
		'flags': int(line[4]),
	}
	decoded_data.append(item)

by_device = defaultdict(list)
for item in decoded_data:
	#if item['device_id'] in device_description_map:
	by_device[item['device_id']].append(item)
	#else:
	#	print(item)

pyplot.subplot(211)
pyplot.title('Pressure')
pyplot.xlabel('Time UTC')
pyplot.ylabel('PSI')
for device_id, items in by_device.iteritems():
	items = sorted(items, key=lambda v: v['timestamp'])
	by_device[device_id] = items
	x = [item['timestamp'] for item in items]
	y = [item['pressure'] for item in items]
	pyplot.plot(x, y)

pyplot.subplot(212)
pyplot.title('Temperature')
pyplot.xlabel('Time UTC')
pyplot.ylabel('Degrees F')
for device_id, items in by_device.iteritems():
	items = sorted(items, key=lambda v: v['timestamp'])
	by_device[device_id] = items
	x = [item['timestamp'] for item in items]
	y = [item['temperature'] for item in items]
	pyplot.plot(x, y)

pyplot.show()

########NEW FILE########
__FILENAME__ = tpms_ask
#!/usr/bin/env python

#
# Copyright 2013 Jared Boone
#
# This file is part of the TPMS project.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#

from gnuradio import blks2
from gnuradio import blocks
from gnuradio import digital
from gnuradio import eng_notation
from gnuradio import filter
from gnuradio import gr
from gnuradio.eng_option import eng_option
from gnuradio.filter import firdes
from gnuradio.gr import firdes
#from gnuradio.wxgui import forms
#from gnuradio.wxgui import scopesink2
#from grc_gnuradio import wxgui as grc_wxgui
from optparse import OptionParser
#import wx

import numpy
import sys

from bit_coding import *
from packet import Packetizer

class top_block(gr.top_block):

	def __init__(self, filepath_in):
		gr.top_block.__init__(self)
		#grc_wxgui.top_block_gui.__init__(self, title="Top Block")

		##################################################
		# Variables
		##################################################
		self.samp_rate = samp_rate = 200e3
		self.bb_interpolation = bb_interpolation = 100
		self.bb_decimation = bb_decimation = 612
		self.samples_per_symbol = samples_per_symbol = 4
		self.gain_mu = gain_mu = 0.03
		self.bb_rate = bb_rate = float(samp_rate) * bb_interpolation / bb_decimation
		self.bb_filter_freq = bb_filter_freq = 10e3
		self.omega = omega = samples_per_symbol
		self.mu = mu = 0.5
		self.gain_omega = gain_omega = 0.25 * gain_mu * gain_mu
		self.bb_taps = bb_taps = gr.firdes.low_pass(1.0, samp_rate, bb_filter_freq, bb_filter_freq * 0.1)
		self.baud_rate = baud_rate = bb_rate / samples_per_symbol
		#self.average = average = 64

		##################################################
		# Blocks
		##################################################
		# self.wxgui_scopesink2_1_0_0 = scopesink2.scope_sink_f(
		# 			self.GetWin(),
		# 			title="Scope Plot",
		# 			sample_rate=baud_rate,
		# 			v_scale=0,
		# 			v_offset=0,
		# 			t_scale=0,
		# 			ac_couple=False,
		# 			xy_mode=False,
		# 			num_inputs=1,
		# 			trig_mode=gr.gr_TRIG_MODE_NORM,
		# 			y_axis_label="Counts",
		# 		)
		# self.Add(self.wxgui_scopesink2_1_0_0.win)
		#self.freq_xlating_fir_filter_xxx_0 = filter.freq_xlating_fir_filter_ccc(1, (bb_taps), 6e3, samp_rate)
		self.digital_correlate_access_code_bb_0 = digital.correlate_access_code_bb("10101010101010101010101010101", 1)
		self.digital_clock_recovery_mm_xx_0 = digital.clock_recovery_mm_ff(omega, gain_omega, mu, gain_mu, 0.0002)
		self.digital_binary_slicer_fb_0 = digital.binary_slicer_fb()
		self.dc_blocker_xx_0 = filter.dc_blocker_ff(64, True)
		#self.blocks_uchar_to_float_0_0 = blocks.uchar_to_float()
		#self.blocks_throttle_0 = blocks.throttle(gr.sizeof_gr_complex*1, samp_rate)
		#self.blocks_file_source_0_0 = blocks.file_source(gr.sizeof_gr_complex*1, "/mnt/hgfs/tmp/rf_captures/315.000m_200.000k_20130623_133451_extract_am_2.cfile", True)
		self.blocks_file_source_0_0 = blocks.file_source(gr.sizeof_gr_complex*1, filepath_in, False)
		self.blocks_complex_to_mag_0 = blocks.complex_to_mag(1)
		self.blks2_rational_resampler_xxx_0 = blks2.rational_resampler_fff(
			interpolation=bb_interpolation,
			decimation=bb_decimation,
			taps=None,
			fractional_bw=None,
		)
		# _bb_filter_freq_sizer = wx.BoxSizer(wx.VERTICAL)
		# self._bb_filter_freq_text_box = forms.text_box(
		# 	parent=self.GetWin(),
		# 	sizer=_bb_filter_freq_sizer,
		# 	value=self.bb_filter_freq,
		# 	callback=self.set_bb_filter_freq,
		# 	label="BB Freq",
		# 	converter=forms.int_converter(),
		# 	proportion=0,
		# )
		# self._bb_filter_freq_slider = forms.slider(
		# 	parent=self.GetWin(),
		# 	sizer=_bb_filter_freq_sizer,
		# 	value=self.bb_filter_freq,
		# 	callback=self.set_bb_filter_freq,
		# 	minimum=5e3,
		# 	maximum=30e3,
		# 	num_steps=250,
		# 	style=wx.SL_HORIZONTAL,
		# 	cast=int,
		# 	proportion=1,
		# )
		# self.Add(_bb_filter_freq_sizer)
		# _average_sizer = wx.BoxSizer(wx.VERTICAL)
		# self._average_text_box = forms.text_box(
		# 	parent=self.GetWin(),
		# 	sizer=_average_sizer,
		# 	value=self.average,
		# 	callback=self.set_average,
		# 	label="Average Length",
		# 	converter=forms.int_converter(),
		# 	proportion=0,
		# )
		# self._average_slider = forms.slider(
		# 	parent=self.GetWin(),
		# 	sizer=_average_sizer,
		# 	value=self.average,
		# 	callback=self.set_average,
		# 	minimum=0,
		# 	maximum=256,
		# 	num_steps=256,
		# 	style=wx.SL_HORIZONTAL,
		# 	cast=int,
		# 	proportion=1,
		# )
		# self.Add(_average_sizer)

		##################################################
		# Connections
		##################################################
		self.connect((self.digital_clock_recovery_mm_xx_0, 0), (self.digital_binary_slicer_fb_0, 0))
		self.connect((self.digital_binary_slicer_fb_0, 0), (self.digital_correlate_access_code_bb_0, 0))
		#self.connect((self.digital_correlate_access_code_bb_0, 0), (self.blocks_uchar_to_float_0_0, 0))
		#self.connect((self.blocks_throttle_0, 0), (self.freq_xlating_fir_filter_xxx_0, 0))
		#self.connect((self.freq_xlating_fir_filter_xxx_0, 0), (self.blocks_complex_to_mag_0, 0))
		self.connect((self.blocks_complex_to_mag_0, 0), (self.blks2_rational_resampler_xxx_0, 0))
		self.connect((self.blks2_rational_resampler_xxx_0, 0), (self.dc_blocker_xx_0, 0))
		self.connect((self.dc_blocker_xx_0, 0), (self.digital_clock_recovery_mm_xx_0, 0))
		#self.connect((self.blocks_uchar_to_float_0_0, 0), (self.wxgui_scopesink2_1_0_0, 0))
		#self.connect((self.blocks_file_source_0_0, 0), (self.blocks_throttle_0, 0))
		#self.connect((self.blocks_file_source_0_0, 0), (self.freq_xlating_fir_filter_xxx_0, 0))
		self.connect((self.blocks_file_source_0_0, 0), (self.blocks_complex_to_mag_0, 0))
		
		self.packetizer = Packetizer(82)
		self.connect((self.digital_correlate_access_code_bb_0, 0), (self.packetizer, 0))


	def get_samp_rate(self):
		return self.samp_rate

	def set_samp_rate(self, samp_rate):
		self.samp_rate = samp_rate
		self.set_bb_rate(float(self.samp_rate) * self.bb_interpolation / self.bb_decimation)
		self.set_bb_taps(gr.firdes.low_pass(1.0, self.samp_rate, self.bb_filter_freq, self.bb_filter_freq * 0.1))
		self.blocks_throttle_0.set_sample_rate(self.samp_rate)

	def get_bb_interpolation(self):
		return self.bb_interpolation

	def set_bb_interpolation(self, bb_interpolation):
		self.bb_interpolation = bb_interpolation
		self.set_bb_rate(float(self.samp_rate) * self.bb_interpolation / self.bb_decimation)

	def get_bb_decimation(self):
		return self.bb_decimation

	def set_bb_decimation(self, bb_decimation):
		self.bb_decimation = bb_decimation
		self.set_bb_rate(float(self.samp_rate) * self.bb_interpolation / self.bb_decimation)

	def get_samples_per_symbol(self):
		return self.samples_per_symbol

	def set_samples_per_symbol(self, samples_per_symbol):
		self.samples_per_symbol = samples_per_symbol
		self.set_baud_rate(self.bb_rate / self.samples_per_symbol)
		self.set_omega(self.samples_per_symbol)

	def get_gain_mu(self):
		return self.gain_mu

	def set_gain_mu(self, gain_mu):
		self.gain_mu = gain_mu
		self.digital_clock_recovery_mm_xx_0.set_gain_mu(self.gain_mu)
		self.set_gain_omega(0.25 * self.gain_mu * self.gain_mu)

	def get_bb_rate(self):
		return self.bb_rate

	def set_bb_rate(self, bb_rate):
		self.bb_rate = bb_rate
		self.set_baud_rate(self.bb_rate / self.samples_per_symbol)

	def get_bb_filter_freq(self):
		return self.bb_filter_freq

	def set_bb_filter_freq(self, bb_filter_freq):
		self.bb_filter_freq = bb_filter_freq
		self._bb_filter_freq_slider.set_value(self.bb_filter_freq)
		self._bb_filter_freq_text_box.set_value(self.bb_filter_freq)
		self.set_bb_taps(gr.firdes.low_pass(1.0, self.samp_rate, self.bb_filter_freq, self.bb_filter_freq * 0.1))

	def get_omega(self):
		return self.omega

	def set_omega(self, omega):
		self.omega = omega
		self.digital_clock_recovery_mm_xx_0.set_omega(self.omega)

	def get_mu(self):
		return self.mu

	def set_mu(self, mu):
		self.mu = mu
		self.digital_clock_recovery_mm_xx_0.set_mu(self.mu)

	def get_gain_omega(self):
		return self.gain_omega

	def set_gain_omega(self, gain_omega):
		self.gain_omega = gain_omega
		self.digital_clock_recovery_mm_xx_0.set_gain_omega(self.gain_omega)

	def get_bb_taps(self):
		return self.bb_taps

	def set_bb_taps(self, bb_taps):
		self.bb_taps = bb_taps
		self.freq_xlating_fir_filter_xxx_0.set_taps((self.bb_taps))

	def get_baud_rate(self):
		return self.baud_rate

	def set_baud_rate(self, baud_rate):
		self.baud_rate = baud_rate
		self.wxgui_scopesink2_1_0_0.set_sample_rate(self.baud_rate)

	def get_average(self):
		return self.average

	def set_average(self, average):
		self.average = average
		self._average_slider.set_value(self.average)
		self._average_text_box.set_value(self.average)

if __name__ == '__main__':
	parser = OptionParser(option_class=eng_option, usage="%prog: [options]")
	(options, args) = parser.parse_args()
	tb = top_block(sys.argv[1])
	#tb.Run(True)
	tb.run()
	
########NEW FILE########
__FILENAME__ = tpms_fsk
#!/usr/bin/env python

#
# Copyright 2013 Jared Boone
#
# This file is part of the TPMS project.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#

from gnuradio import blocks
from gnuradio import digital
from gnuradio import eng_notation
from gnuradio import filter
from gnuradio import gr

from argparse import ArgumentParser

import numpy
import sys
import math
import os
import os.path
import glob
import datetime
from iso8601 import iso8601

from collections import defaultdict

from packet import Packetizer, packet_format, packet_classify
from numpy_block import *

class FSKDemodulator(gr.top_block):
	def __init__(self, source_data, sampling_rate, carrier_hz, symbol_rate, deviation, access_code):
		super(FSKDemodulator, self).__init__()

		self._decoded = {}

		self._carrier_hz = carrier_hz
		self._deviation = deviation
		self._access_code = access_code

		samp_rate = sampling_rate
		#symbol_rate = 9920
		self.samples_per_symbol = float(samp_rate) / symbol_rate

		omega = self.samples_per_symbol * 1.0
		mu = 0.0
		gain_mu = 0.2
		gain_omega = 0.25 * gain_mu * gain_mu
		omega_relative_limit = 0.001

		tap_count = int(math.floor(self.samples_per_symbol))

		hz_n = (carrier_hz - deviation)
		taps_n = numpy.exp(numpy.arange(tap_count, dtype=numpy.float32) * 2.0j * numpy.pi * hz_n / samp_rate)
		hz_p = (carrier_hz + deviation)
		taps_p = numpy.exp(numpy.arange(tap_count, dtype=numpy.float32) * 2.0j * numpy.pi * hz_p / samp_rate)

		#source = blocks.file_source(gr.sizeof_gr_complex*1, filepath_in, False)
		# Concatenate data to compensate for correlate_access_code_bb latency
		source_data_padding_count = int(math.ceil(self.samples_per_symbol * 64))
		source_data = numpy.concatenate((source_data, numpy.zeros((source_data_padding_count,), dtype=numpy.complex64)))
		source = NumpySource(source_data)

		filter_n = filter.fir_filter_ccc(1, taps_n.tolist())
		self.connect(source, filter_n)
		filter_p = filter.fir_filter_ccc(1, taps_p.tolist())
		self.connect(source, filter_p)

		mag_n = blocks.complex_to_mag(1)
		self.connect(filter_n, mag_n)
		mag_p = blocks.complex_to_mag(1)
		self.connect(filter_p, mag_p)

		sub_pn = blocks.sub_ff()
		self.connect(mag_p, (sub_pn, 0))
		self.connect(mag_n, (sub_pn, 1))

		clock_recovery = digital.clock_recovery_mm_ff(omega, gain_omega, mu, gain_mu, omega_relative_limit)
		self.connect(sub_pn, clock_recovery)

		slicer = digital.binary_slicer_fb()
		self.connect(clock_recovery, slicer)

		access_code_correlator = digital.correlate_access_code_bb(access_code, 0)
		self.connect(slicer, access_code_correlator)

		self.packetizer = Packetizer()
		self.connect(access_code_correlator, self.packetizer)

		# sink_n = blocks.file_sink(gr.sizeof_float*1, 'out_n.rfile')
		# self.connect(mag_n, sink_n)
		# sink_p = blocks.file_sink(gr.sizeof_float*1, 'out_p.rfile')
		# self.connect(mag_p, sink_p)
		# sink_diff = blocks.file_sink(gr.sizeof_float*1, 'out_diff.rfile')
		# self.connect(sub_pn, sink_diff)
		# sink_sync = blocks.file_sink(gr.sizeof_float*1, 'out_sync.rfile')
		# self.connect(clock_recovery, sink_sync)
		# sink_slicer = blocks.file_sink(gr.sizeof_char*1, 'out_slicer.u8')
		# self.connect(slicer, sink_slicer)
		# sink_correlator = blocks.file_sink(gr.sizeof_char*1, 'out_correlator.u8')
		# self.connect(access_code_correlator, sink_correlator)

	@property
	def packets(self):
		results = []
		data = self.packetizer.data
		#print('P %s' % ''.join(map(str, data)))
		for i in range(len(data)):
			symbol = data[i]
			if symbol & 2:
				if len(data[i:]) >= 64:
					access_code_n = i - len(self._access_code)
					result = (
						data[access_code_n:i] & 1,
						data[i:] & 1,
					)
					results.append(result)
		return results[-1:]

def demodulate_ask(packet_info, source_data):
	return False

def demodulate_fsk(packet_info, source_data):
	symbol_rate = packet_info['symbol_rate']
	access_code = packet_info['preamble']
	carrier_hz = packet_info['carrier']
	deviation = packet_info['deviation']

	demodulator = FSKDemodulator(source_data, sampling_rate, carrier_hz, symbol_rate, deviation, access_code)
	demodulator.run()

	packets = demodulator.packets
	results = []
	for actual_access_code, data in packets:
		results.append({
			'decoder': 'raw',
			'data': ''.join(map(str, data)),
			'carrier': carrier_hz,
			'modulation': 'fsk',
			'symbol_rate': symbol_rate,
			'deviation': deviation,
			'access_code': access_code,
			'actual_access_code': ''.join(map(str, actual_access_code)),
		})

	return results

if __name__ == '__main__':
	parser = ArgumentParser()
	parser.add_argument('burst_directory', nargs='+', type=str)
	parser.add_argument('-r', '--rate', type=float, help="Sampling rate of data files")
	parser.add_argument('-m', '--modulation', type=str, default='fsk', help="Modulation type (fsk")
	parser.add_argument('-c', '--carrier', type=float, help="Carrier frequency within data files")
	parser.add_argument('-d', '--deviation', type=float, help="Frequency deviation")
	parser.add_argument('-p', '--preamble', type=str, help="Packet preamble or access code")
	parser.add_argument('-s', '--symbol-rate', type=float, help="Symbol rate")
	args = parser.parse_args()

	sampling_rate = args.rate

	for data_path in args.burst_directory:
		path_glob = os.path.join(data_path, '*.dat')
		files = glob.glob(path_glob)

		start_timestamp_path = os.path.join(data_path, 'timestamp.txt')
		start_timestamp = open(start_timestamp_path).read()
		start_timestamp = iso8601.parse_date(start_timestamp)

		for path in files:
			head, tail = os.path.split(path)
			filename = tail

			offset_seconds = filename.split('_')[2]
			offset_seconds = float(offset_seconds.split('.dat')[0])
			burst_timestamp = start_timestamp + iso8601.timedelta(seconds=offset_seconds)

			source_data = numpy.fromfile(path, dtype=numpy.complex64)
			#packet_info = packet_classify(source_data, sampling_rate)

			packet_info = {
				'modulation': args.modulation.lower(),
				'carrier': args.carrier,
				'deviation': args.deviation,
				'symbol_rate': args.symbol_rate,
				'preamble': args.preamble,
			}

			results = []
			if packet_info['modulation'] == 'ask':
				results = demodulate_ask(packet_info, source_data)
			elif packet_info['modulation'] == 'fsk':
				results = demodulate_fsk(packet_info, source_data)
			else:
				continue

			for result in results:
				data = result['data']

				print('%s %s %s %s %d %d %d %s' % (
					burst_timestamp.isoformat(),
					result['access_code'],
					data,
					result['modulation'],
					result['carrier'],
					result['deviation'],
					result['symbol_rate'],
					filename,
				))

	# from pylab import *

	# diff = numpy.fromfile('out_diff.rfile', dtype=numpy.float32)
	# x_diff = numpy.arange(len(diff))
	# plot(x_diff, diff)

	# sync = numpy.fromfile('out_sync.rfile', dtype=numpy.float32)
	# x_sync = numpy.arange(len(sync)) * tb.samples_per_symbol
	# plot(x_sync, sync)

	# slicer = numpy.fromfile('out_slicer.u8', dtype=numpy.uint8)
	# x_slicer = numpy.arange(len(slicer)) #* tb.samples_per_symbol
	# plot(x_slicer, slicer)

	# correlator = numpy.fromfile('out_correlator.u8', dtype=numpy.uint8)
	# x_correlator = numpy.arange(len(correlator)) #* tb.samples_per_symbol
	# plot(x_correlator, correlator)
	
	# show()

########NEW FILE########
