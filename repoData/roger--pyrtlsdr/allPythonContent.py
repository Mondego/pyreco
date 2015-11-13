__FILENAME__ = demo_waterfall
#    This file is part of pyrlsdr.
#    Copyright (C) 2013 by Roger <https://github.com/roger-/pyrtlsdr>
#
#    pyrlsdr is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    pyrlsdr is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with pyrlsdr.  If not, see <http://www.gnu.org/licenses/>.


from __future__ import division
import matplotlib.animation as animation
from matplotlib.mlab import psd
import pylab as pyl
import numpy as np
import sys
from rtlsdr import RtlSdr

# A simple waterfall, spectrum plotter
#
# Controls:
#
# * Scroll mouse-wheel up or down, or press the left or right arrow keys, to
#   change the center frequency (hold shift for finer control).
# * Press "+" and "-" to control gain, and space to enable AGC.
# * Type a frequency (in MHz) and press enter to directly change the center frequency

NFFT = 1024*4
NUM_SAMPLES_PER_SCAN = NFFT*16
NUM_BUFFERED_SWEEPS = 100

# change this to control the number of scans that are combined in a single sweep
# (e.g. 2, 3, 4, etc.) Note that it can slow things down
NUM_SCANS_PER_SWEEP = 1

# these are the increments when scrolling the mouse wheel or pressing '+' or '-'
FREQ_INC_COARSE = 1e6
FREQ_INC_FINE = 0.1e6
GAIN_INC = 5

class Waterfall(object):
    keyboard_buffer = []
    shift_key_down = False
    image_buffer = -100*np.ones((NUM_BUFFERED_SWEEPS,\
                                 NUM_SCANS_PER_SWEEP*NFFT))

    def __init__(self, sdr=None, fig=None):
        self.fig = fig if fig else pyl.figure()
        self.sdr = sdr if sdr else RtlSdr()

        self.init_plot()

    def init_plot(self):
        self.ax = self.fig.add_subplot(1,1,1)
        self.image = self.ax.imshow(self.image_buffer, aspect='auto',\
                                    interpolation='nearest', vmin=-50, vmax=10)
        self.ax.set_xlabel('Current frequency (MHz)')
        self.ax.get_yaxis().set_visible(False)

        self.fig.canvas.mpl_connect('scroll_event', self.on_scroll)
        self.fig.canvas.mpl_connect('key_press_event', self.on_key_press)
        self.fig.canvas.mpl_connect('key_release_event', self.on_key_release)

    def update_plot_labels(self):
        fc = self.sdr.fc
        rs = self.sdr.rs
        freq_range = (fc - rs/2)/1e6, (fc + rs*(NUM_SCANS_PER_SWEEP - 0.5))/1e6

        self.image.set_extent(freq_range + (0, 1))
        self.fig.canvas.draw_idle()

    def on_scroll(self, event):
        if event.button == 'up':
            self.sdr.fc += FREQ_INC_FINE if self.shift_key_down else FREQ_INC_COARSE
            self.update_plot_labels()
        elif event.button == 'down':
            self.sdr.fc -= FREQ_INC_FINE if self.shift_key_down else FREQ_INC_COARSE
            self.update_plot_labels()

    def on_key_press(self, event):
        if event.key == '+':
            self.sdr.gain += GAIN_INC
        elif event.key == '-':
            self.sdr.gain -= GAIN_INC
        elif event.key == ' ':
            self.sdr.gain = 'auto'
        elif event.key == 'shift':
            self.shift_key_down = True
        elif event.key == 'right':
            self.sdr.fc += FREQ_INC_FINE if self.shift_key_down else FREQ_INC_COARSE
            self.update_plot_labels()
        elif event.key == 'left':
            self.sdr.fc -= FREQ_INC_FINE if self.shift_key_down else FREQ_INC_COARSE
            self.update_plot_labels()
        elif event.key == 'enter':
            # see if valid frequency was entered, then change center frequency
            try:
                # join individual key presses into a string
                input = ''.join(self.keyboard_buffer)

                # if we're doing multiple adjacent scans, we need to figure out
                # the appropriate center freq for the leftmost scan
                center_freq = float(input)*1e6 + (self.sdr.rs/2)*(1 - NUM_SCANS_PER_SWEEP)
                self.sdr.fc = center_freq

                self.update_plot_labels()
            except ValueError:
                pass

            self.keyboard_buffer = []
        else:
            self.keyboard_buffer.append(event.key)

    def on_key_release(self, event):
        if event.key == 'shift':
            self.shift_key_down = False

    def update(self, *args):
        # save center freq. since we're gonna be changing it
        start_fc = self.sdr.fc

        # prepare space in buffer
        # TODO: use indexing to avoid recreating buffer each time
        self.image_buffer = np.roll(self.image_buffer, 1, axis=0)

        for scan_num, start_ind in enumerate(range(0, NUM_SCANS_PER_SWEEP*NFFT, NFFT)):
            self.sdr.fc += self.sdr.rs*scan_num

            # estimate PSD for one scan
            samples = self.sdr.read_samples(NUM_SAMPLES_PER_SCAN)
            psd_scan, f = psd(samples, NFFT=NFFT)

            self.image_buffer[0, start_ind: start_ind+NFFT] = 10*np.log10(psd_scan)

        # plot entire sweep
        self.image.set_array(self.image_buffer)

        # restore original center freq.
        self.sdr.fc = start_fc

        return self.image,

    def start(self):
        self.update_plot_labels()
        if sys.platform == 'darwin':
            # Disable blitting. The matplotlib.animation's restore_region()
            # method is only implemented for the Agg-based backends,
            # which the macosx backend is not.
            blit = False
        else:
            blit = True
        ani = animation.FuncAnimation(self.fig, self.update, interval=50,
                blit=blit)

        pyl.show()

        return


def main():
    sdr = RtlSdr()
    wf = Waterfall(sdr)

    # some defaults
    sdr.rs = 2.4e6
    sdr.fc = 100e6
    sdr.gain = 10

    wf.start()

    # cleanup
    sdr.close()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = helpers
#    This file is part of pyrlsdr.
#    Copyright (C) 2013 by Roger <https://github.com/roger-/pyrtlsdr>
#
#    pyrlsdr is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    pyrlsdr is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with pyrlsdr.  If not, see <http://www.gnu.org/licenses/>.


from __future__ import division
from functools import wraps
import time

def limit_time(max_seconds):
    '''Decorator to cancel async reads after "max_seconds" seconds elapse.
    Call to read_samples_async() or read_bytes_async() must not override context
    parameter.
    '''
    def decorator(f):
        f._start_time = None

        @wraps(f)
        def wrapper(buffer, rtlsdr_obj):
            if f._start_time is None:
                f._start_time = time.time()

            elapsed = time.time() - f._start_time
            if elapsed < max_seconds:
                return f(buffer, rtlsdr_obj)

            rtlsdr_obj.cancel_read_async()

            return

        return wrapper
    return decorator


def limit_calls(max_calls):
    '''Decorator to cancel async reads after "max_calls" function calls occur.
    Call to read_samples_async() or read_bytes_async() must not override context
    parameter.
    '''
    def decorator(f):
        f._num_calls = 0

        @wraps(f)
        def wrapper(buffer, rtlsdr_obj):
            f._num_calls += 1

            if f._num_calls <= max_calls:
                return f(buffer, rtlsdr_obj)

            rtlsdr_obj.cancel_read_async()

            return

        return wrapper
    return decorator


@limit_time(0.01)
@limit_calls(20)
def test_callback(buffer, rtlsdr_obj):
    print 'In callback'
    print '   signal mean:', sum(buffer)/len(buffer)


def main():
    from rtlsdr import RtlSdr

    sdr = RtlSdr()

    print 'Configuring SDR...'
    sdr.rs = 1e6
    sdr.fc = 70e6
    sdr.gain = 5
    print '   sample rate: %0.6f MHz' % (sdr.rs/1e6)
    print '   center ferquency %0.6f MHz' % (sdr.fc/1e6)
    print '   gain: %d dB' % sdr.gain

    print 'Testing callback...'
    sdr.read_samples_async(test_callback)


if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = librtlsdr
#    This file is part of pyrlsdr.
#    Copyright (C) 2013 by Roger <https://github.com/roger-/pyrtlsdr>
#
#    pyrlsdr is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    pyrlsdr is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with pyrlsdr.  If not, see <http://www.gnu.org/licenses/>.


from ctypes import *
from ctypes.util import find_library

def load_librtlsdr():
    driver_files = ['rtlsdr.dll', 'librtlsdr.so']
    driver_files += ['..//rtlsdr.dll', '..//librtlsdr.so']
    driver_files += ['rtlsdr//rtlsdr.dll', 'rtlsdr//librtlsdr.so']
    driver_files += [find_library('rtlsdr'), find_library('librtlsdr')]

    dll = None

    for driver in driver_files:
        try:
            dll = CDLL(driver)
            break
        except:
            pass
    else:
        raise ImportError('Error loading librtlsdr. Make sure librtlsdr '\
                          '(and all of its dependencies) are in your path')

    return dll

librtlsdr = load_librtlsdr()

# we don't care about the rtlsdr_dev struct and it's allocated by librtlsdr, so
# we won't even bother filling it in
p_rtlsdr_dev = c_void_p

# async callbacks must be passed through this function
# typedef void(*rtlsdr_read_async_cb_t)(unsigned char *buf, uint32_t len, void *ctx);
rtlsdr_read_async_cb_t = CFUNCTYPE(None, POINTER(c_ubyte), c_int, py_object)

# uint32_t rtlsdr_get_device_count(void);
f = librtlsdr.rtlsdr_get_device_count
f.restype, f.argtypes = c_uint, []

# const char* rtlsdr_get_device_name(uint32_t index);
f = librtlsdr.rtlsdr_get_device_name
f.restype, f.argtypes = c_char_p, [c_uint]

# int rtlsdr_get_device_usb_strings(uint32_t index, char *manufact,
#                                   char *product, char *serial)
f = librtlsdr.rtlsdr_get_device_usb_strings
f.restype, f.argtypes = c_int, [c_uint,
                                POINTER(c_ubyte),
                                POINTER(c_ubyte),
                                POINTER(c_ubyte)]

# int rtlsdr_open(rtlsdr_dev_t **dev, uint32_t index);
f = librtlsdr.rtlsdr_open
f.restype, f.argtypes = c_int, [POINTER(p_rtlsdr_dev), c_uint]

# int rtlsdr_close(rtlsdr_dev_t *dev);
f = librtlsdr.rtlsdr_close
f.restype, f.argtypes = c_int, [p_rtlsdr_dev]

# /* configuration functions */

# int rtlsdr_set_center_freq(rtlsdr_dev_t *dev, uint32_t freq);
f = librtlsdr.rtlsdr_set_center_freq
f.restype, f.argtypes = c_int, [p_rtlsdr_dev, c_uint]

# int rtlsdr_get_center_freq(rtlsdr_dev_t *dev);
f = librtlsdr.rtlsdr_get_center_freq
f.restype, f.argtypes = c_uint, [p_rtlsdr_dev]

# int rtlsdr_set_freq_correction(rtlsdr_dev_t *dev, int ppm);
f = librtlsdr.rtlsdr_set_freq_correction
f.restype, f.argtypes = c_int, [p_rtlsdr_dev, c_int]

# int rtlsdr_get_freq_correction(rtlsdr_dev_t *dev);
f = librtlsdr.rtlsdr_get_freq_correction
f.restype, f.argtypes = c_int, [p_rtlsdr_dev]

# enum rtlsdr_tuner rtlsdr_get_tuner_type(rtlsdr_dev_t *dev);
f = librtlsdr.rtlsdr_get_tuner_type
f.restype, f.argtypes = c_int, [p_rtlsdr_dev]

# int rtlsdr_set_tuner_gain(rtlsdr_dev_t *dev, int gain);
f = librtlsdr.rtlsdr_set_tuner_gain
f.restype, f.argtypes = c_int, [p_rtlsdr_dev, c_int]

# int rtlsdr_get_tuner_gain(rtlsdr_dev_t *dev);
f = librtlsdr.rtlsdr_get_tuner_gain
f.restype, f.argtypes = c_int, [p_rtlsdr_dev]

# int rtlsdr_get_tuner_gains(rtlsdr_dev_t *dev, int *gains)
f = librtlsdr.rtlsdr_get_tuner_gains
f.restype, f.argtypes = c_int, [p_rtlsdr_dev, POINTER(c_int)]

# RTLSDR_API int rtlsdr_set_tuner_gain_mode(rtlsdr_dev_t *dev, int manual);
f = librtlsdr.rtlsdr_set_tuner_gain_mode
f.restype, f.argtypes = c_int, [p_rtlsdr_dev, c_int]

# RTLSDR_API int rtlsdr_set_agc_mode(rtlsdr_dev_t *dev, int on);
f = librtlsdr.rtlsdr_set_agc_mode
f.restype, f.argtypes = c_int, [p_rtlsdr_dev, c_int]

# RTLSDR_API  int rtlsdr_set_direct_sampling(rtlsdr_dev_t *dev, int on)
f = librtlsdr.rtlsdr_set_direct_sampling
f.restype, f.argtypes = c_int, [p_rtlsdr_dev, c_int]


# int rtlsdr_set_sample_rate(rtlsdr_dev_t *dev, uint32_t rate);
f = librtlsdr.rtlsdr_set_sample_rate
f.restype, f.argtypes = c_int, [p_rtlsdr_dev, c_uint]

# int rtlsdr_get_sample_rate(rtlsdr_dev_t *dev);
f = librtlsdr.rtlsdr_get_sample_rate
f.restype, f.argtypes = c_uint, [p_rtlsdr_dev]

#/* streaming functions */

# int rtlsdr_reset_buffer(rtlsdr_dev_t *dev);
f = librtlsdr.rtlsdr_reset_buffer
f.restype, f.argtypes = c_int, [p_rtlsdr_dev]

# int rtlsdr_read_sync(rtlsdr_dev_t *dev, void *buf, int len, int *n_read);
f = librtlsdr.rtlsdr_read_sync
f.restype, f.argtypes = c_int, [p_rtlsdr_dev, c_void_p, c_int, POINTER(c_int)]

# int rtlsdr_wait_async(rtlsdr_dev_t *dev, rtlsdr_read_async_cb_t cb, void *ctx);
f = librtlsdr.rtlsdr_wait_async
f.restype, f.argtypes = c_int, [p_rtlsdr_dev, POINTER(rtlsdr_read_async_cb_t), py_object]

#int rtlsdr_read_async(rtlsdr_dev_t *dev,
#				 rtlsdr_read_async_cb_t cb,
#				 void *ctx,
#				 uint32_t buf_num,
#				 uint32_t buf_len);
f = librtlsdr.rtlsdr_read_async
f.restype, f.argtypes = c_int, [p_rtlsdr_dev, rtlsdr_read_async_cb_t, py_object, c_uint, c_uint]

# int rtlsdr_cancel_async(rtlsdr_dev_t *dev);
f = librtlsdr.rtlsdr_cancel_async
f.restype, f.argtypes = c_int, [p_rtlsdr_dev]

# RTLSDR_API int rtlsdr_set_xtal_freq(rtlsdr_dev_t *dev, uint32_t rtl_freq,
#				    uint32_t tuner_freq);
f = librtlsdr.rtlsdr_set_xtal_freq
f.restype, f.argtypes = c_int, [p_rtlsdr_dev, c_uint, c_uint]

# RTLSDR_API int rtlsdr_get_xtal_freq(rtlsdr_dev_t *dev, uint32_t *rtl_freq,
#				    uint32_t *tuner_freq);
f = librtlsdr.rtlsdr_get_xtal_freq
f.restype, f.argtypes = c_int, [p_rtlsdr_dev, POINTER(c_uint), POINTER(c_uint)]

# RTLSDR_API int rtlsdr_set_testmode(rtlsdr_dev_t *dev, int on);
f = librtlsdr.rtlsdr_set_testmode
f.restype, f.argtypes = c_int, [p_rtlsdr_dev, c_int]

__all__  = ['librtlsdr', 'p_rtlsdr_dev', 'rtlsdr_read_async_cb_t']
########NEW FILE########
__FILENAME__ = rtlsdr
#    This file is part of pyrlsdr.
#    Copyright (C) 2013 by Roger <https://github.com/roger-/pyrtlsdr>
#
#    pyrlsdr is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    pyrlsdr is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with pyrlsdr.  If not, see <http://www.gnu.org/licenses/>.


from __future__ import division
from ctypes import *
from librtlsdr import librtlsdr, p_rtlsdr_dev, rtlsdr_read_async_cb_t
from itertools import izip

# see if NumPy is available
has_numpy = True
try:
    import numpy as np
except ImportError:
    has_numpy = False


class BaseRtlSdr(object):
    # some default values for various parameters
    DEFAULT_GAIN = 'auto'
    DEFAULT_FC = 80e6
    DEFAULT_RS = 1.024e6
    DEFAULT_READ_SIZE = 1024

    CRYSTAL_FREQ = 28800000

    gain_values = []
    valid_gains_db = []
    buffer = []
    num_bytes_read = c_int32(0)
    device_opened = False

    def __init__(self, device_index=0, test_mode_enabled=False):
        ''' Initialize RtlSdr object.
        The test_mode_enabled parameter can be used to enable a special test mode, which will return the value of an
        internal RTL2832 8-bit counter with calls to read_bytes()
        '''

        # this is the pointer to the device structure used by all librtlsdr
        # functions
        self.dev_p = p_rtlsdr_dev(None)

        # initialize device
        result = librtlsdr.rtlsdr_open(self.dev_p, device_index)
        if result < 0:
            raise IOError('Error code %d when opening SDR (device index = %d)'\
                          % (result, device_index))

        # enable test mode if necessary
        result = librtlsdr.rtlsdr_set_testmode(self.dev_p, int(test_mode_enabled))
        if result < 0:
            raise IOError('Error code %d when setting test mode'\
                          % (result))

        # reset buffers
        result = librtlsdr.rtlsdr_reset_buffer(self.dev_p)
        if result < 0:
            raise IOError('Error code %d when resetting buffer (device index = %d)'\
                          % (result, device_index))

        self.gain_values = self.get_gains()
        self.valid_gains_db = [val/10 for val in self.gain_values]

        self.device_opened = True

        # set default state
        self.set_sample_rate(self.DEFAULT_RS)
        self.set_center_freq(self.DEFAULT_FC)
        self.set_gain(self.DEFAULT_GAIN)

    def close(self):
        if not self.device_opened:
            return

        librtlsdr.rtlsdr_close(self.dev_p)
        self.device_opened = False

    def __del__(self):
        self.close()

    def set_center_freq(self, freq):
        ''' Set center frequency of tuner (in Hz).
        Use get_center_freq() to see the precise frequency used. '''

        freq = int(freq)

        result = librtlsdr.rtlsdr_set_center_freq(self.dev_p, freq)
        if result < 0:
            self.close()
            raise IOError('Error code %d when setting center freq. to %d Hz'\
                          % (result, freq))

        return

    def get_center_freq(self):
        ''' Return center frequency of tuner (in Hz). '''

        result = librtlsdr.rtlsdr_get_center_freq(self.dev_p)
        if result < 0:
            self.close()
            raise IOError('Error code %d when getting center freq.'\
                          % (result))

        # FIXME: the E4000 rounds to kHz, this may not be true for other tuners
        reported_center_freq = result
        center_freq = round(reported_center_freq, -3)

        return center_freq

    def set_freq_correction(self, err_ppm):
        ''' Set frequency offset of tuner (in PPM). '''

        freq = int(err_ppm)

        result = librtlsdr.rtlsdr_set_freq_correction(self.dev_p, err_ppm)
        if result < 0:
            self.close()
            raise IOError('Error code %d when setting freq. offset to %d ppm'\
                          % (result, err_ppm))

        return

    def get_freq_correction(self):
        ''' Get frequency offset of tuner (in PPM). '''

        result = librtlsdr.rtlsdr_get_freq_correction(self.dev_p)
        if result < 0:
            self.close()
            raise IOError('Error code %d when getting freq. offset in ppm.'\
                          % (result))
        return

    def set_sample_rate(self, rate):
        ''' Set sample rate of tuner (in Hz).
        Use get_sample_rate() to see the precise sample rate used. '''

        rate = int(rate)

        result = librtlsdr.rtlsdr_set_sample_rate(self.dev_p, rate)
        if result < 0:
            self.close()
            raise IOError('Error code %d when setting sample rate to %d Hz'\
                          % (result, rate))

        return

    def get_sample_rate(self):
        ''' Get sample rate of tuner (in Hz) '''

        result = librtlsdr.rtlsdr_get_sample_rate(self.dev_p)
        if result < 0:
            self.close()
            raise IOError('Error code %d when getting sample rate'\
                          % (result))

        # figure out actual sample rate, taken directly from librtlsdr
        reported_sample_rate = result
        rsamp_ratio = (self.CRYSTAL_FREQ * pow(2, 22)) // reported_sample_rate
        rsamp_ratio &= ~3
        real_rate = (self.CRYSTAL_FREQ * pow(2, 22)) / rsamp_ratio;

        return real_rate

    def set_gain(self, gain):
        ''' Set gain of tuner.
        If gain is 'auto', AGC mode is enabled; otherwise gain is in dB. The actual
        gain used is rounded to the nearest value supported by the device (see the
        values in RtlSdr.valid_gains_db).
        '''
        if isinstance(gain, str) and gain == 'auto':
            # disable manual gain -> enable AGC
            self.set_manual_gain_enabled(False)

            return

        # find supported gain nearest to one requested
        errors = [abs(10*gain - g) for g in self.gain_values]
        nearest_gain_ind = errors.index(min(errors))

        # disable AGC
        self.set_manual_gain_enabled(True)

        result = librtlsdr.rtlsdr_set_tuner_gain(self.dev_p,
                                                 self.gain_values[nearest_gain_ind])
        if result < 0:
            self.close()
            raise IOError('Error code %d when setting gain to %d'\
                          % (result, gain))

        return

    def get_gain(self):
        ''' Get gain of tuner (in dB). '''

        result = librtlsdr.rtlsdr_get_tuner_gain(self.dev_p)
        if result == 0:
            self.close()
            raise IOError('Error when getting gain')

        return result/10

    def get_gains(self):
        ''' Get list of supported gains from driver
        All gains are in tenths of a dB
        '''
        buffer = (c_int *50)()
        result = librtlsdr.rtlsdr_get_tuner_gains(self.dev_p, buffer)
        if result == 0:
            self.close()
            raise IOError('Error when getting gains')

        gains = []
        for i in range(result):
            gains.append(buffer[i])

        return gains

    def set_manual_gain_enabled(self, enabled):
        ''' Enable manual gain control of tuner.
        If enabled is False, then AGC is used. Use set_gain() instead of calling
        this directly.
        '''
        result = librtlsdr.rtlsdr_set_tuner_gain_mode(self.dev_p, int(enabled))
        if result < 0:
            raise IOError('Error code %d when setting gain mode'\
                          % (result))

        return

    def set_agc_mode(self, enabled):
        ''' Enable RTL2832 AGC
        '''
        result = librtlsdr.rtlsdr_set_agc_mode(self.dev_p, int(enabled))
        if result < 0:
            raise IOError('Error code %d when setting AGC mode'\
                          % (result))

        return result

    def set_direct_sampling(self, direct):
        ''' Enable direct sampling.
        direct -- sampling mode
        If direct is False or 0, disable direct sampling
        If direct is 'i' or 1, use ADC I input
        If direct is 'q' or 2, use ADC Q input
        '''

        # convert parameter
        if isinstance(direct, str):
            if direct.lower() == 'i':
                direct = 1
            elif direct.lower() == 'q':
                direct = 2
            else:
                raise SyntaxError('invalid value "%s"' % direct)

        # make sure False works as an option
        if not direct:
            direct = 0

        result = librtlsdr.rtlsdr_set_direct_sampling(self.dev_p, direct)
        if result < 0:
            raise IOError('Error code %d when setting AGC mode'\
                          % (result))

        return result

    def get_tuner_type(self):
        ''' Get the tuner type.
        '''
        result = librtlsdr.rtlsdr_get_tuner_type(self.dev_p)
        if result < 0:
            raise IOError('Error code %d when getting tuner type'\
                          % (result))

        return result

    def read_bytes(self, num_bytes=DEFAULT_READ_SIZE):
        ''' Read specified number of bytes from tuner. Does not attempt to unpack
        complex samples (see read_samples()), and data may be unsafe as buffer is
        reused.
        '''
        # FIXME: libsdrrtl may not be able to read an arbitrary number of bytes

        num_bytes = int(num_bytes)

        # create buffer, as necessary
        if len(self.buffer) != num_bytes:
            array_type = (c_ubyte*num_bytes)
            self.buffer = array_type()

        result = librtlsdr.rtlsdr_read_sync(self.dev_p, self.buffer, num_bytes,\
                                            byref(self.num_bytes_read))
        if result < 0:
            self.close()
            raise IOError('Error code %d when reading %d bytes'\
                          % (result, num_bytes))

        if self.num_bytes_read.value != num_bytes:
            self.close()
            raise IOError('Short read, requested %d bytes, received %d'\
                          % (num_bytes, self.num_bytes_read.value))

        return self.buffer

    def read_samples(self, num_samples=DEFAULT_READ_SIZE):
        ''' Read specified number of complex samples from tuner. Real and imaginary
        parts are normalized to be in the range [-1, 1]. Data is safe after
        this call (will not get overwritten by another one).
        '''
        num_bytes = 2*num_samples

        raw_data = self.read_bytes(num_bytes)
        iq = self.packed_bytes_to_iq(raw_data)

        return iq

    def packed_bytes_to_iq(self, bytes):
        ''' Convenience function to unpack array of bytes to Python list/array
        of complex numbers and normalize range. Called automatically by read_samples()
        '''
        if has_numpy:
            # use NumPy array
            iq = np.empty(len(bytes)//2, 'complex')
            iq.real, iq.imag = bytes[::2], bytes[1::2]
            iq /= (255/2)
            iq -= (1 + 1j)
        else:
            # use normal list
            iq = [complex(i/(255/2) - 1, q/(255/2) - 1) for i, q in izip(bytes[::2], bytes[1::2])]

        return iq

    center_freq = fc = property(get_center_freq, set_center_freq)
    sample_rate = rs = property(get_sample_rate, set_sample_rate)
    gain = property(get_gain, set_gain)
    freq_correction = property(get_freq_correction, set_freq_correction)


# This adds async read support to base class BaseRtlSdr (don't use that one)
class RtlSdr(BaseRtlSdr):
    DEFAULT_ASYNC_BUF_NUMBER = 32
    DEFAULT_READ_SIZE = 1024

    read_async_canceling = False

    def read_bytes_async(self, callback, num_bytes=DEFAULT_READ_SIZE, context=None):
        ''' Continuously read "num_bytes" bytes from tuner and call Python function
        "callback" with the result. "context" is any Python object that will be
        make available to callback function (default supplies this RtlSdr object).
        Data may be overwritten (see read_bytes()).
        '''
        num_bytes = int(num_bytes)

        # we don't call the provided callback directly, but add a layer inbetween
        # to convert the raw buffer to a safer type

        # save requested callback
        self._callback_bytes = callback

        # convert Python callback function to a librtlsdr callback
        rtlsdr_callback = rtlsdr_read_async_cb_t(self._bytes_converter_callback)

        # use this object as context if none provided
        if not context:
            context = self

        self.read_async_canceling = False
        result = librtlsdr.rtlsdr_read_async(self.dev_p, rtlsdr_callback,\
                    context, self.DEFAULT_ASYNC_BUF_NUMBER, num_bytes)
        if result < 0:
            self.close()
            raise IOError('Error code %d when requesting %d bytes'\
                          % (result, num_bytes))

        self.read_async_canceling = False

        return

    def _bytes_converter_callback(self, raw_buffer, num_bytes, context):
        # convert buffer to safer type
        array_type = (c_ubyte*num_bytes)
        values = cast(raw_buffer, POINTER(array_type)).contents

        # skip callback if cancel_read_async() called
        if self.read_async_canceling:
            return

        self._callback_bytes(values, context)

    def read_samples_async(self, callback, num_samples=DEFAULT_READ_SIZE, context=None):
        ''' Combination of read_samples() and read_bytes_async() '''

        num_bytes = 2*num_samples

        self._callback_samples = callback
        self.read_bytes_async(self._samples_converter_callback, num_bytes, context)

        return

    def _samples_converter_callback(self, buffer, context):
        iq = self.packed_bytes_to_iq(buffer)

        self._callback_samples(iq, context)

    def cancel_read_async(self):
        ''' Cancel async read. This should be called eventually when using async
        reads, or callbacks will never stop. See also decorators limit_time()
        and limit_calls() in helpers.py.
        '''

        result = librtlsdr.rtlsdr_cancel_async(self.dev_p)
        # sometimes we get additional callbacks after canceling an async read,
        # in this case we don't raise exceptions
        if result < 0 and not self.read_async_canceling:
            self.close()
            raise IOError('Error code %d when canceling async read'\
                          % (result))

        self.read_async_canceling = True


def test_callback(buffer, rtlsdr_obj):
    print '  in callback'
    print '  signal mean:', sum(buffer)/len(buffer)

    # note we may get additional callbacks even after calling this
    rtlsdr_obj.cancel_read_async()


def main():
    sdr = RtlSdr()

    print 'Configuring SDR...'
    sdr.rs = 2.4e6
    sdr.fc = 70e6
    sdr.gain = 4
    print '  sample rate: %0.6f MHz' % (sdr.rs/1e6)
    print '  center frequency %0.6f MHz' % (sdr.fc/1e6)
    print '  gain: %d dB' % sdr.gain

    print 'Reading samples...'
    samples = sdr.read_samples(1024)
    print '  signal mean:', sum(samples)/len(samples)

    print 'Testing callback...'
    sdr.read_samples_async(test_callback)

    sdr.close()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test
#    This file is part of pyrlsdr.
#    Copyright (C) 2013 by Roger <https://github.com/roger-/pyrtlsdr>
#
#    pyrlsdr is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    pyrlsdr is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with pyrlsdr.  If not, see <http://www.gnu.org/licenses/>.


from __future__ import division
from rtlsdr import *

@limit_calls(2)
def test_callback(samples, rtlsdr_obj):
    print '  in callback'
    print '  signal mean:', sum(samples)/len(samples)

def main():
    sdr = RtlSdr()

    print 'Configuring SDR...'
    sdr.rs = 2.4e6
    sdr.fc = 100e6
    sdr.gain = 10
    print '  sample rate: %0.6f MHz' % (sdr.rs/1e6)
    print '  center frequency %0.6f MHz' % (sdr.fc/1e6)
    print '  gain: %d dB' % sdr.gain

    print 'Reading samples...'
    samples = sdr.read_samples(256*1024)
    print '  signal mean:', sum(samples)/len(samples)

    print 'Testing callback...'
    sdr.read_samples_async(test_callback, 256*1024)

    try:
        import pylab as mpl

        print 'Testing spectrum plotting...'
        mpl.figure()
        mpl.psd(samples, NFFT=1024, Fc=sdr.fc/1e6, Fs=sdr.rs/1e6)

        mpl.show()
    except:
        # matplotlib not installed/working
        pass

    print 'Done\n'
    sdr.close()

if __name__ == '__main__':
    main()
########NEW FILE########
