__FILENAME__ = demo_bpm_extract
#! /usr/bin/env python

from aubio import source, tempo
from numpy import median, diff

def get_file_bpm(path, params = {}):
    """ Calculate the beats per minute (bpm) of a given file.
        path: path to the file
        param: dictionary of parameters
    """
    try:
        win_s = params['win_s']
        samplerate = params['samplerate']
        hop_s = params['hop_s']
    except:
        """
        # super fast
        samplerate, win_s, hop_s = 4000, 128, 64 
        # fast
        samplerate, win_s, hop_s = 8000, 512, 128
        """
        # default:
        samplerate, win_s, hop_s = 44100, 1024, 512

    s = source(path, samplerate, hop_s)
    samplerate = s.samplerate
    o = tempo("specdiff", win_s, hop_s, samplerate)
    # List of beats, in samples
    beats = []
    # Total number of frames read
    total_frames = 0

    while True:
        samples, read = s()
        is_beat = o(samples)
        if is_beat:
            this_beat = o.get_last_s()
            beats.append(this_beat)
            #if o.get_confidence() > .2 and len(beats) > 2.:
            #    break
        total_frames += read
        if read < hop_s:
            break

    # Convert to periods and to bpm 
    bpms = 60./diff(beats)
    b = median(bpms)
    return b

if __name__ == '__main__':
    import sys
    for f in sys.argv[1:]:
        bpm = get_file_bpm(f)
        print "%6s" % ("%.2f" % bpm), f

########NEW FILE########
__FILENAME__ = demo_filterbank
#! /usr/bin/env python

from aubio import filterbank, fvec
from pylab import loglog, show, subplot, xlim, ylim, xlabel, ylabel, title
from numpy import vstack, arange

win_s = 2048
samplerate = 48000

freq_list = [60, 80, 200, 400, 800, 1600, 3200, 6400, 12800, 24000]
n_filters = len(freq_list) - 2

f = filterbank(n_filters, win_s)
freqs = fvec(freq_list)
f.set_triangle_bands(freqs, samplerate)

coeffs = f.get_coeffs()
coeffs[4] *= 5.

f.set_coeffs(coeffs)

times = vstack([arange(win_s / 2 + 1) * samplerate / win_s] * n_filters)
title('Bank of filters built using a simple list of boundaries\nThe middle band has been amplified by 2.')
loglog(times.T, f.get_coeffs().T, '.-')
xlim([50, samplerate/2])
ylim([1.0e-6, 2.0e-2])
xlabel('log frequency (Hz)')
ylabel('log amplitude')

show()

########NEW FILE########
__FILENAME__ = demo_filterbank_slaney
#! /usr/bin/env python

from aubio import filterbank
from numpy import array, arange, vstack

win_s = 8192
samplerate = 16000

f = filterbank(40, win_s)
f.set_mel_coeffs_slaney(samplerate)

from pylab import loglog, title, show, xlim, ylim, xlabel, ylabel
xlim([0,samplerate / 2])
times = vstack([arange(win_s / 2 + 1) * samplerate / win_s] * 40)
loglog(times.T, f.get_coeffs().T, '.-')
title('Mel frequency bands coefficients')
xlim([100, 7500])
ylim([1.0e-3, 2.0e-2])
xlabel('Frequency (Hz)')
ylabel('Amplitude')
show()

########NEW FILE########
__FILENAME__ = demo_filterbank_triangle_bands
#! /usr/bin/env python

from aubio import filterbank, fvec
from pylab import loglog, show, subplot, xlim, ylim, xlabel, ylabel, title
from numpy import vstack, arange

win_s = 2048
samplerate = 48000

freq_list = [60, 80, 200, 400, 800, 1600, 3200, 6400, 12800, 24000]
n_filters = len(freq_list) - 2

f = filterbank(n_filters, win_s)
freqs = fvec(freq_list)
f.set_triangle_bands(freqs, samplerate)

subplot(211)
title('Examples of filterbank built with set_triangle_bands and set_coeffs')
times = vstack([arange(win_s / 2 + 1) * samplerate / win_s] * n_filters)
loglog(times.T, f.get_coeffs().T, '.-')
xlim([50, samplerate/2])
ylim([1.0e-6, 2.0e-2])
ylabel('Amplitude')

## build a new filterbank

freq_list = [60, 80, 200, 400, 800, 1200, 1600, 3200, 6400, 10000, 15000, 24000]
n_filters = len(freq_list) - 2

f = filterbank(n_filters, win_s)
freqs = fvec(freq_list)
f.set_triangle_bands(freqs, samplerate)

coeffs = f.get_coeffs()
coeffs[4] *= 5.

f.set_coeffs(coeffs)

subplot(212)
times = vstack([arange(win_s / 2 + 1) * samplerate / win_s] * n_filters)
loglog(times.T, f.get_coeffs().T, '.-')
xlim([50, samplerate/2])
ylim([1.0e-6, 2.0e-2])
xlabel('Frequency (Hz)')
ylabel('Amplitude')

show()

########NEW FILE########
__FILENAME__ = demo_keyboard
#! /usr/bin/env python

def get_keyboard_edges(firstnote = 21, lastnote = 108):
    octaves = 10

    # build template of white notes
    scalew  = 12/7.
    xw_temp = [i*scalew for i in range(0,7)]
    # build template of black notes
    scaleb  = 6/7.
    xb_temp = [i*scaleb for i in [1,3,7,9,11]]

    xb,xw = [],[]
    for octave in range(octaves-1):
        for i in xb_temp:
            curnote = i+12*octave
            if  curnote > firstnote-1 and curnote < lastnote+1:
                xb = xb + [curnote]
    for octave in range(octaves-1):
        for i in xw_temp:
            curnote = i+12*octave
            if  curnote > firstnote-1 and curnote < lastnote+1:
                xw = xw + [curnote]

    return xb, xw, 2/3. *scaleb, 1/2. * scalew

def create_keyboard_patches(firstnote, lastnote, ax = None):
    import numpy as np
    import matplotlib.pyplot as plt
    from matplotlib.path import Path
    import matplotlib.patches as mpatches

    blacks, whites, b_width, w_width = get_keyboard_edges(firstnote, lastnote)

    if not ax:
        fig = plt.figure()
        ax = fig.add_subplot(111)

    verts, codes = [], []
    for white in whites:
        verts += [ (white - w_width, 0), (white - w_width, 1), (white + w_width, 1),  (white + w_width, 0) ]
        verts += [ (white - w_width, 0) ]
        codes  += [Path.MOVETO] + [Path.LINETO] * 4
    path = Path(verts, codes)
    patch = mpatches.PathPatch(path, facecolor= 'white', edgecolor='black', lw=1)
    ax.add_patch(patch)

    verts, codes = [], []
    for black in blacks:
        verts +=  [ (black - b_width, 0.33), (black - b_width, 1), (black + b_width, 1),  (black + b_width, 0.33) ]
        verts += [ (black - b_width, 0.33) ]
        codes += [Path.MOVETO] + [Path.LINETO] * 4
    path = Path(verts, codes)
    patch = mpatches.PathPatch(path, facecolor= 'black', edgecolor='black', lw=1)
    ax.add_patch(patch)

    ax.axis(xmin = firstnote, xmax = lastnote)

if __name__ == '__main__':

    import matplotlib.pyplot as plt
    create_keyboard_patches(firstnote = 58, lastnote = 84)
    plt.show()

########NEW FILE########
__FILENAME__ = demo_mel-energy
#! /usr/bin/env python

import sys
from aubio import fvec, source, pvoc, filterbank
from numpy import vstack, zeros

win_s = 512                 # fft size
hop_s = win_s / 4           # hop size

if len(sys.argv) < 2:
    print "Usage: %s <filename> [samplerate]" % sys.argv[0]
    sys.exit(1)

filename = sys.argv[1]

samplerate = 0
if len( sys.argv ) > 2: samplerate = int(sys.argv[2])

s = source(filename, samplerate, hop_s)
samplerate = s.samplerate

pv = pvoc(win_s, hop_s)

f = filterbank(40, win_s)
f.set_mel_coeffs_slaney(samplerate)

energies = zeros((40,))
o = {}

total_frames = 0
downsample = 2

while True:
    samples, read = s()
    fftgrain = pv(samples)
    new_energies = f(fftgrain)
    print '%f' % (total_frames / float(samplerate) ),
    print ' '.join(['%f' % b for b in new_energies])
    energies = vstack( [energies, new_energies] )
    total_frames += read
    if read < hop_s: break

if 1:
    print "done computing, now plotting"
    import matplotlib.pyplot as plt
    from demo_waveform_plot import get_waveform_plot
    from demo_waveform_plot import set_xlabels_sample2time
    fig = plt.figure()
    plt.rc('lines',linewidth='.8')
    wave = plt.axes([0.1, 0.75, 0.8, 0.19])
    get_waveform_plot(filename, samplerate, block_size = hop_s, ax = wave )
    wave.yaxis.set_visible(False)
    wave.xaxis.set_visible(False)

    n_plots = len(energies.T)
    all_desc_times = [ x * hop_s  for x in range(len(energies)) ]
    for i, band in enumerate(energies.T):
        ax = plt.axes ( [0.1, 0.75 - ((i+1) * 0.65 / n_plots),  0.8, 0.65 / n_plots], sharex = wave )
        ax.plot(all_desc_times, band, '-', label = 'band %d' % i)
        #ax.set_ylabel(method, rotation = 0)
        ax.xaxis.set_visible(False)
        ax.yaxis.set_visible(False)
        ax.axis(xmax = all_desc_times[-1], xmin = all_desc_times[0])
        ax.annotate('band %d' % i, xy=(-10, 0),  xycoords='axes points',
                horizontalalignment='right', verticalalignment='bottom',
                size = 'xx-small',
                )
    set_xlabels_sample2time( ax, all_desc_times[-1], samplerate) 
    #plt.ylabel('spectral descriptor value')
    ax.xaxis.set_visible(True)
    plt.show()

########NEW FILE########
__FILENAME__ = demo_mfcc
#! /usr/bin/env python

import sys
from aubio import source, pvoc, mfcc
from numpy import array, vstack, zeros

win_s = 512                 # fft size
hop_s = win_s / 4           # hop size
n_filters = 40
n_coeffs = 13
samplerate = 44100

if len(sys.argv) < 2:
    print "Usage: %s <source_filename>" % sys.argv[0]
    sys.exit(1)

source_filename = sys.argv[1]

samplerate = 0
if len( sys.argv ) > 2: samplerate = int(sys.argv[2])

s = source(source_filename, samplerate, hop_s)
samplerate = s.samplerate
p = pvoc(win_s, hop_s)
m = mfcc(win_s, n_filters, n_coeffs, samplerate)

mfccs = zeros([13,])
frames_read = 0
while True:
    samples, read = s()
    spec = p(samples)
    mfcc_out = m(spec)
    mfccs = vstack((mfccs, mfcc_out))
    frames_read += read
    if read < hop_s: break

# do plotting
from numpy import arange
from demo_waveform_plot import get_waveform_plot
from demo_waveform_plot import set_xlabels_sample2time
import matplotlib.pyplot as plt

fig = plt.figure()
plt.rc('lines',linewidth='.8')
wave = plt.axes([0.1, 0.75, 0.8, 0.19])

get_waveform_plot( source_filename, samplerate, block_size = hop_s, ax = wave)
wave.xaxis.set_visible(False)
wave.yaxis.set_visible(False)

all_times = arange(mfccs.shape[0]) * hop_s
n_coeffs = mfccs.shape[1]
for i in range(n_coeffs):
    ax = plt.axes ( [0.1, 0.75 - ((i+1) * 0.65 / n_coeffs),  0.8, 0.65 / n_coeffs], sharex = wave )
    ax.xaxis.set_visible(False)
    ax.yaxis.set_visible(False)
    ax.plot(all_times, mfccs.T[i])

# add time to the last axis
set_xlabels_sample2time( ax, frames_read, samplerate) 

#plt.ylabel('spectral descriptor value')
ax.xaxis.set_visible(True)
wave.set_title('MFCC for %s' % source_filename)
plt.show()

########NEW FILE########
__FILENAME__ = demo_miditofreq
#! /usr/bin/env python

from aubio import miditofreq
from numpy import arange

upsampling = 100.
midi = arange(-10, 148 * upsampling)
midi /= upsampling
freq = miditofreq(midi)

from matplotlib import pyplot as plt

ax = plt.axes()
ax.semilogy(midi, freq, '.')
ax.set_xlabel('midi note')
ax.set_ylabel('frequency (Hz)')
plt.show()

########NEW FILE########
__FILENAME__ = demo_onset
#! /usr/bin/env python

import sys
from aubio import source, onset

win_s = 512                 # fft size
hop_s = win_s / 2           # hop size

if len(sys.argv) < 2:
    print "Usage: %s <filename> [samplerate]" % sys.argv[0]
    sys.exit(1)

filename = sys.argv[1]

samplerate = 0
if len( sys.argv ) > 2: samplerate = int(sys.argv[2])

s = source(filename, samplerate, hop_s)
samplerate = s.samplerate

o = onset("default", win_s, hop_s, samplerate)

# list of onsets, in samples
onsets = []

# total number of frames read
total_frames = 0
while True:
    samples, read = s()
    if o(samples):
        print "%f" % o.get_last_s()
        onsets.append(o.get_last())
    total_frames += read
    if read < hop_s: break
#print len(onsets)

########NEW FILE########
__FILENAME__ = demo_onset_plot
#! /usr/bin/env python

import sys
from aubio import onset, source
from numpy import array, hstack, zeros

win_s = 512                 # fft size
hop_s = win_s / 2           # hop size

if len(sys.argv) < 2:
    print "Usage: %s <filename> [samplerate]" % sys.argv[0]
    sys.exit(1)

filename = sys.argv[1]

samplerate = 0
if len( sys.argv ) > 2: samplerate = int(sys.argv[2])

s = source(filename, samplerate, hop_s)
samplerate = s.samplerate
o = onset("default", win_s, hop_s, samplerate)

# list of onsets, in samples
onsets = []

# storage for plotted data
desc = []
tdesc = []
allsamples_max = zeros(0,)
downsample = 2  # to plot n samples / hop_s

# total number of frames read
total_frames = 0
while True:
    samples, read = s()
    if o(samples):
        print "%f" % (o.get_last_s())
        onsets.append(o.get_last())
    # keep some data to plot it later
    new_maxes = (abs(samples.reshape(hop_s/downsample, downsample))).max(axis=0)
    allsamples_max = hstack([allsamples_max, new_maxes])
    desc.append(o.get_descriptor())
    tdesc.append(o.get_thresholded_descriptor())
    total_frames += read
    if read < hop_s: break

if 1:
    # do plotting
    from numpy import arange
    import matplotlib.pyplot as plt
    allsamples_max = (allsamples_max > 0) * allsamples_max
    allsamples_max_times = [ float(t) * hop_s / downsample / samplerate for t in range(len(allsamples_max)) ]
    plt1 = plt.axes([0.1, 0.75, 0.8, 0.19])
    plt2 = plt.axes([0.1, 0.1, 0.8, 0.65], sharex = plt1)
    plt.rc('lines',linewidth='.8')
    plt1.plot(allsamples_max_times,  allsamples_max, '-b')
    plt1.plot(allsamples_max_times, -allsamples_max, '-b')
    for stamp in onsets:
        stamp /= float(samplerate)
        plt1.plot([stamp, stamp], [-1., 1.], '-r')
    plt1.axis(xmin = 0., xmax = max(allsamples_max_times) )
    plt1.xaxis.set_visible(False)
    plt1.yaxis.set_visible(False)
    desc_times = [ float(t) * hop_s / samplerate for t in range(len(desc)) ]
    desc_plot = [d / max(desc) for d in desc]
    plt2.plot(desc_times, desc_plot, '-g')
    tdesc_plot = [d / max(desc) for d in tdesc]
    for stamp in onsets:
        stamp /= float(samplerate)
        plt2.plot([stamp, stamp], [min(tdesc_plot), max(desc_plot)], '-r')
    plt2.plot(desc_times, tdesc_plot, '-y')
    plt2.axis(ymin = min(tdesc_plot), ymax = max(desc_plot))
    plt.xlabel('time (s)')
    #plt.savefig('/tmp/t.png', dpi=200)
    plt.show()

########NEW FILE########
__FILENAME__ = demo_pitch
#! /usr/bin/env python

import sys
from aubio import source, pitch, freqtomidi

if len(sys.argv) < 2:
    print "Usage: %s <filename> [samplerate]" % sys.argv[0]
    sys.exit(1)

filename = sys.argv[1]

downsample = 1
samplerate = 44100 / downsample
if len( sys.argv ) > 2: samplerate = int(sys.argv[2])

win_s = 4096 / downsample # fft size
hop_s = 512  / downsample # hop size

s = source(filename, samplerate, hop_s)
samplerate = s.samplerate

tolerance = 0.8

pitch_o = pitch("yin", win_s, hop_s, samplerate)
pitch_o.set_unit("freq")
pitch_o.set_tolerance(tolerance)

pitches = []
confidences = []

# total number of frames read
total_frames = 0
while True:
    samples, read = s()
    pitch = pitch_o(samples)[0]
    #pitch = int(round(pitch))
    confidence = pitch_o.get_confidence()
    #if confidence < 0.8: pitch = 0.
    print "%f %f %f" % (total_frames / float(samplerate), pitch, confidence)
    pitches += [pitch]
    confidences += [confidence]
    total_frames += read
    if read < hop_s: break

if 0: sys.exit(0)

#print pitches
from numpy import array, ma
import matplotlib.pyplot as plt
from demo_waveform_plot import get_waveform_plot, set_xlabels_sample2time

skip = 1

pitches = array(pitches[skip:])
confidences = array(confidences[skip:])
times = [t * hop_s for t in range(len(pitches))]

fig = plt.figure()

ax1 = fig.add_subplot(311)
ax1 = get_waveform_plot(filename, samplerate = samplerate, block_size = hop_s, ax = ax1)
plt.setp(ax1.get_xticklabels(), visible = False)
ax1.set_xlabel('')

def array_from_text_file(filename, dtype = 'float'):
    import os.path
    from numpy import array
    filename = os.path.join(os.path.dirname(__file__), filename)
    return array([line.split() for line in open(filename).readlines()],
        dtype = dtype)

ax2 = fig.add_subplot(312, sharex = ax1)
import sys, os.path
ground_truth = os.path.splitext(filename)[0] + '.f0.Corrected'
if os.path.isfile(ground_truth):
    ground_truth = array_from_text_file(ground_truth)
    true_freqs = ground_truth[:,2]
    true_freqs = ma.masked_where(true_freqs < 2, true_freqs)
    true_times = float(samplerate) * ground_truth[:,0]
    ax2.plot(true_times, true_freqs, 'r')
    ax2.axis( ymin = 0.9 * true_freqs.min(), ymax = 1.1 * true_freqs.max() )
# plot raw pitches
ax2.plot(times, pitches, '--g')
# plot cleaned up pitches
cleaned_pitches = pitches
#cleaned_pitches = ma.masked_where(cleaned_pitches < 0, cleaned_pitches)
#cleaned_pitches = ma.masked_where(cleaned_pitches > 120, cleaned_pitches)
cleaned_pitches = ma.masked_where(confidences < tolerance, cleaned_pitches)
ax2.plot(times, cleaned_pitches, '.-')
#ax2.axis( ymin = 0.9 * cleaned_pitches.min(), ymax = 1.1 * cleaned_pitches.max() )
#ax2.axis( ymin = 55, ymax = 70 )
plt.setp(ax2.get_xticklabels(), visible = False)
ax2.set_ylabel('f0 (Hz)')

# plot confidence
ax3 = fig.add_subplot(313, sharex = ax1)
# plot the confidence
ax3.plot(times, confidences)
# draw a line at tolerance
ax3.plot(times, [tolerance]*len(confidences))
ax3.axis( xmin = times[0], xmax = times[-1])
ax3.set_ylabel('condidence')
set_xlabels_sample2time(ax3, times[-1], samplerate)
plt.show()
#plt.savefig(os.path.basename(filename) + '.svg')

########NEW FILE########
__FILENAME__ = demo_pitch_sinusoid
#! /usr/bin/env python

from numpy import random, sin, arange, ones, zeros
from math import pi
from aubio import fvec, pitch

def build_sinusoid(length, freqs, samplerate):
  return sin( 2. * pi * arange(length) * freqs / samplerate)

def run_pitch(p, input_vec):
  f = fvec (p.hop_size)
  cands = []
  count = 0
  for vec_slice in input_vec.reshape((-1, p.hop_size)):
    f[:] = vec_slice
    cands.append(p(f))
  return cands

methods = ['default', 'schmitt', 'fcomb', 'mcomb', 'yin', 'yinfft']

cands = {}
buf_size = 2048
hop_size = 512
samplerate = 44100
sin_length = (samplerate * 10) % 512 * 512
freqs = zeros(sin_length)

partition = sin_length / 8
pointer = 0

pointer += partition
freqs[pointer: pointer + partition] = 440

pointer += partition
pointer += partition
freqs[ pointer : pointer + partition ] = 740

pointer += partition
freqs[ pointer : pointer + partition ] = 1480

pointer += partition
pointer += partition
freqs[ pointer : pointer + partition ] = 400 + 5 * random.random(sin_length/8)

a = build_sinusoid(sin_length, freqs, samplerate)

for method in methods:
  p = pitch(method, buf_size, hop_size, samplerate)
  cands[method] = run_pitch(p, a)

print "done computing"

if 1:
  from pylab import plot, show, xlabel, ylabel, legend, ylim
  ramp = arange(0, sin_length / hop_size).astype('float') * hop_size / samplerate
  for method in methods:
    plot(ramp, cands[method],'.-')

  # plot ground truth
  ramp = arange(0, sin_length).astype('float') / samplerate
  plot(ramp, freqs, ':')

  legend(methods+['ground truth'], 'upper right')
  xlabel('time (s)')
  ylabel('frequency (Hz)')
  ylim([0,2000])
  show()


########NEW FILE########
__FILENAME__ = demo_pysoundcard_play
#! /usr/bin/env python

def play_source(source_path):
    """Play an audio file using pysoundcard."""

    from aubio import source
    from pysoundcard import Stream
    
    hop_size = 256
    f = source(source_path, hop_size = hop_size)
    samplerate = f.samplerate

    s = Stream(sample_rate = samplerate, block_length = hop_size)
    s.start()
    read = 0
    while 1:
        vec, read = f()
        s.write(vec)
        if read < hop_size: break
    s.stop()

if __name__ == '__main__':
    import sys
    play_source(sys.argv[1])

########NEW FILE########
__FILENAME__ = demo_pysoundcard_record
#! /usr/bin/env python

def record_sink(sink_path):
    """Record an audio file using pysoundcard."""

    from aubio import sink
    from pysoundcard import Stream

    hop_size = 256
    duration = 5 # in seconds
    s = Stream(block_length = hop_size)
    g = sink(sink_path, samplerate = s.sample_rate)

    s.start()
    total_frames = 0
    while total_frames < duration * s.sample_rate:
        vec = s.read(hop_size)
        # mix down to mono
        mono_vec = vec.sum(-1) / float(s.input_channels)
        g(mono_vec, hop_size)
        total_frames += hop_size
    s.stop()

if __name__ == '__main__':
    import sys
    record_sink(sys.argv[1])

########NEW FILE########
__FILENAME__ = demo_simple_robot_voice
#! /usr/bin/env python

import sys
from aubio import source, sink, pvoc

if __name__ == '__main__':
  if len(sys.argv) < 2:
    print 'usage: %s <inputfile> <outputfile>' % sys.argv[0]
    sys.exit(1)
  samplerate = 44100
  f = source(sys.argv[1], samplerate, 256)
  g = sink(sys.argv[2], samplerate)
  total_frames, read = 0, 256

  win_s = 512                 # fft size
  hop_s = win_s / 2           # hop size
  pv = pvoc(win_s, hop_s)                            # phase vocoder

  while read:
    samples, read = f()
    spectrum = pv(samples)            # compute spectrum
    #spectrum.norm *= .8               # reduce amplitude a bit
    spectrum.phas[:] = 0.             # zero phase
    new_samples = pv.rdo(spectrum)    # compute modified samples
    g(new_samples, read)              # write to output
    total_frames += read

  print "wrote", total_frames, "from", f.uri, "to", g.uri

  

########NEW FILE########
__FILENAME__ = demo_simple_spectral_weighting
#! /usr/bin/env python

import sys
from aubio import source, sink, pvoc
from numpy import arange, exp, hstack, zeros, cos
from math import pi

def gauss(size):
    return exp(- 1.0 / (size * size) * pow(2.0* arange(size) - 1. *size, 2.));

def hanningz(size):
    return 0.5 * (1. - cos(2.*pi*arange(size) / size))

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print 'usage: %s <inputfile> <outputfile>' % sys.argv[0]
        sys.exit(1)
    samplerate = 0 
    if len(sys.argv) > 3: samplerate = int(sys.argv[3])
    f = source(sys.argv[1], samplerate, 256)
    samplerate = f.samplerate
    g = sink(sys.argv[2], samplerate)

    win_s = 512 # fft size
    hop_s = win_s / 2 # hop size
    pv = pvoc(win_s, hop_s) # phase vocoder

    # spectral weighting vector
    spec_weight = hstack ( [
        .8 * hanningz(80)[40:],
        zeros( 50 ),
        1.3 * hanningz(100),
        zeros (win_s / 2 + 1 - 40 - 50 - 100),
        ] )

    if 0:
        from pylab import plot, show
        plot(spec_weight) 
        show()

    total_frames, read = 0, hop_s
    while read:
        # get new samples
        samples, read = f()
        # compute spectrum
        spectrum = pv(samples)
        # apply weight to spectral amplitudes
        spectrum.norm *= spec_weight
        # resynthesise modified samples
        new_samples = pv.rdo(spectrum)
        # write to output
        g(new_samples, read)
        total_frames += read

    print "read", total_frames / float(samplerate), "seconds from", f.uri

########NEW FILE########
__FILENAME__ = demo_sink
#! /usr/bin/env python

import sys
from aubio import source, sink

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print 'usage: %s <inputfile> <outputfile> [samplerate] [hop_size]' % sys.argv[0]
        sys.exit(1)

    if len(sys.argv) > 3: samplerate = int(sys.argv[3])
    else: samplerate = 0
    if len(sys.argv) > 4: hop_size = int(sys.argv[4])
    else: hop_size = 256

    f = source(sys.argv[1], samplerate, hop_size)
    if samplerate == 0: samplerate = f.samplerate
    g = sink(sys.argv[2], samplerate)

    total_frames, read = 0, hop_size
    while read:
        vec, read = f()
        g(vec, read)
        total_frames += read
    print "wrote", "%.2fs" % (total_frames / float(samplerate) ),
    print "(", total_frames, "frames", "in",
    print total_frames / f.hop_size, "blocks", "at", "%dHz" % f.samplerate, ")",
    print "from", f.uri,
    print "to", g.uri

########NEW FILE########
__FILENAME__ = demo_sink_create_woodblock
#! /usr/bin/env python

import sys
from math import pi, e
from aubio import sink
from numpy import arange, resize, sin, exp, zeros

if len(sys.argv) < 2:
    print 'usage: %s <outputfile> [samplerate]' % sys.argv[0]
    sys.exit(1)

samplerate = 44100 # samplerate in Hz
if len( sys.argv ) > 2: samplerate = int(sys.argv[2])

pitch = 2200            # in Hz
blocksize = 256         # in samples
duration = 0.02         # in seconds

twopi = pi * 2.

duration = int ( samplerate * duration ) # convert to samples
attack = int (samplerate * .001 )
decay = .5

period = float(samplerate) /  pitch
# create a sine lookup table
tablelen = 1000
sinetable = arange(tablelen + 1, dtype = 'float32')
sinetable = 0.7 * sin(twopi * sinetable/tablelen)
sinetone = zeros((duration,), dtype = 'float32')

# compute sinetone at floating point period
for i in range(duration):
    x = int((i % period) / float(period) * tablelen)
    idx = int(x)
    frac = x - idx
    a = sinetable[idx]
    b = sinetable[idx + 1]
    sinetone[i] = a + frac * (b -a)

# apply some envelope
float_ramp = arange(duration, dtype = 'float32')
sinetone *= exp( - e * float_ramp / duration / decay)
sinetone[:attack] *= exp( e * ( float_ramp[:attack] / attack - 1 ) )

if 1:
    import matplotlib.pyplot as plt
    plt.plot(sinetone)
    plt.show()

my_sink = sink(sys.argv[1], samplerate)

total_frames = 0
while total_frames + blocksize < duration:
    my_sink(sinetone[total_frames:total_frames+blocksize], blocksize)
    total_frames += blocksize
my_sink(sinetone[total_frames:duration], duration - total_frames)

########NEW FILE########
__FILENAME__ = demo_slicing
#! /usr/bin/env python

import sys
import os.path
from aubio import source, sink

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print 'usage: %s <inputfile> <duration>' % sys.argv[0]
        sys.exit(1)
    source_file = sys.argv[1]
    duration = float(sys.argv[2])
    source_base_name, source_ext = os.path.splitext(os.path.basename(source_file))

    hopsize = 256
    slice_n, total_frames_written, read = 0, 0, hopsize

    def new_sink_name(source_base_name, slice_n, duration = duration):
        return source_base_name + '_%02.3f' % (slice_n*duration) + '.wav'

    f = source(source_file, 0, hopsize)
    samplerate = f.samplerate
    g = sink(new_sink_name(source_base_name, slice_n), samplerate)

    #print "new slice:", slice_n, 0, "+", 0, "=", 0
    while read == hopsize:
        vec, read = f()
        start_of_next_region = int(duration * samplerate * (slice_n + 1))
        remaining = start_of_next_region - total_frames_written
        # number of samples remaining is less than what we got
        if remaining <= read:
            # write remaining samples from current region
            g(vec[0:remaining], remaining)
            # close this file
            del g
            #print "new slice", slice_n, total_frames_written, "+", remaining, "=", start_of_next_region
            slice_n += 1
            # create a new file for the new region
            g = sink(new_sink_name(source_base_name, slice_n), samplerate)
            # write the remaining samples in the new file
            g(vec[remaining:read], read - remaining)
        else:
            g(vec[0:read], read)
        total_frames_written += read
    total_duration = total_frames_written / float(samplerate)
    slice_n += 1
    print 'created %(slice_n)s slices from %(source_base_name)s%(source_ext)s' % locals(),
    print ' (total duration %(total_duration).2fs)' % locals()
    # close source and sink files
    del f, g

########NEW FILE########
__FILENAME__ = demo_source
#! /usr/bin/env python

import sys
from aubio import source

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print 'usage: %s <inputfile> [samplerate] [hop_size]' % sys.argv[0]
        sys.exit(1)
    samplerate = 0
    hop_size = 256
    if len(sys.argv) > 2: samplerate = int(sys.argv[2])
    if len(sys.argv) > 3: hop_size = int(sys.argv[3])

    f = source(sys.argv[1], samplerate, hop_size)
    samplerate = f.samplerate

    total_frames, read = 0, f.hop_size
    while read:
        vec, read = f()
        total_frames += read
        if read < f.hop_size: break
    print "read", "%.2fs" % (total_frames / float(samplerate) ),
    print "(", total_frames, "frames", "in",
    print total_frames / f.hop_size, "blocks", "at", "%dHz" % f.samplerate, ")",
    print "from", f.uri

########NEW FILE########
__FILENAME__ = demo_specdesc
#! /usr/bin/env python

import sys
from aubio import fvec, source, pvoc, specdesc
from numpy import hstack

win_s = 512                 # fft size
hop_s = win_s / 4           # hop size

if len(sys.argv) < 2:
    print "Usage: %s <filename> [samplerate]" % sys.argv[0]
    sys.exit(1)

filename = sys.argv[1]

samplerate = 0
if len( sys.argv ) > 2: samplerate = int(sys.argv[2])

s = source(filename, samplerate, hop_s)
samplerate = s.samplerate

pv = pvoc(win_s, hop_s)

methods = ['default', 'energy', 'hfc', 'complex', 'phase', 'specdiff', 'kl',
        'mkl', 'specflux', 'centroid', 'slope', 'rolloff', 'spread', 'skewness',
        'kurtosis', 'decrease',]

all_descs = {}
o = {}

for method in methods:
    cands = []
    all_descs[method] = fvec(0)
    o[method] = specdesc(method, win_s)

total_frames = 0
downsample = 2

while True:
    samples, read = s()
    fftgrain = pv(samples)
    #print "%f" % ( total_frames / float(samplerate) ),
    for method in methods:
        specdesc_val = o[method](fftgrain)[0]
        all_descs[method] = hstack ( [all_descs[method], specdesc_val] )
        #print "%f" % specdesc_val,
    #print
    total_frames += read
    if read < hop_s: break

if 1:
    print "done computing, now plotting"
    import matplotlib.pyplot as plt
    from demo_waveform_plot import get_waveform_plot
    from demo_waveform_plot import set_xlabels_sample2time
    fig = plt.figure()
    plt.rc('lines',linewidth='.8')
    wave = plt.axes([0.1, 0.75, 0.8, 0.19])
    get_waveform_plot(filename, samplerate, block_size = hop_s, ax = wave )
    wave.yaxis.set_visible(False)
    wave.xaxis.set_visible(False)

    all_desc_times = [ x * hop_s  for x in range(len(all_descs["default"])) ]
    n_methods = len(methods)
    for i, method in enumerate(methods):
        #ax = fig.add_subplot (n_methods, 1, i)
        #plt2 = plt.axes([0.1, 0.1, 0.8, 0.65], sharex = plt1)
        ax = plt.axes ( [0.1, 0.75 - ((i+1) * 0.65 / n_methods),  0.8, 0.65 / n_methods], sharex = wave )
        ax.plot(all_desc_times, all_descs[method], '-', label = method)
        #ax.set_ylabel(method, rotation = 0)
        ax.xaxis.set_visible(False)
        ax.yaxis.set_visible(False)
        ax.axis(xmax = all_desc_times[-1], xmin = all_desc_times[0])
        ax.annotate(method, xy=(-10, 0),  xycoords='axes points',
                horizontalalignment='right', verticalalignment='bottom',
                )
    set_xlabels_sample2time(ax, all_desc_times[-1], samplerate)
    #plt.ylabel('spectral descriptor value')
    ax.xaxis.set_visible(True)
    plt.show()

########NEW FILE########
__FILENAME__ = demo_spectrogram
#! /usr/bin/env python

import sys
from aubio import pvoc, source
from numpy import array, arange, zeros, shape, log10, vstack
from pylab import imshow, show, cm, axis, ylabel, xlabel, xticks, yticks

def get_spectrogram(filename, samplerate = 0):
  win_s = 512                                        # fft window size
  hop_s = win_s / 2                                  # hop size
  fft_s = win_s / 2 + 1                              # spectrum bins

  a = source(filename, samplerate, hop_s)            # source file
  if samplerate == 0: samplerate = a.samplerate
  pv = pvoc(win_s, hop_s)                            # phase vocoder
  specgram = zeros([0, fft_s], dtype='float32')      # numpy array to store spectrogram

  # analysis
  while True:
    samples, read = a()                              # read file
    specgram = vstack((specgram,pv(samples).norm))   # store new norm vector
    if read < a.hop_size: break

  # plotting
  imshow(log10(specgram.T + .001), origin = 'bottom', aspect = 'auto', cmap=cm.gray_r)
  axis([0, len(specgram), 0, len(specgram[0])])
  # show axes in Hz and seconds
  time_step = hop_s / float(samplerate)
  total_time = len(specgram) * time_step
  print "total time: %0.2fs" % total_time,
  print ", samplerate: %.2fkHz" % (samplerate / 1000.)
  n_xticks = 10
  n_yticks = 10

  def get_rounded_ticks( top_pos, step, n_ticks ):
      top_label = top_pos * step
      # get the first label
      ticks_first_label = top_pos * step / n_ticks
      # round to the closest .1
      ticks_first_label = round ( ticks_first_label * 10. ) / 10.
      # compute all labels from the first rounded one
      ticks_labels = [ ticks_first_label * n for n in range(n_ticks) ] + [ top_label ]
      # get the corresponding positions
      ticks_positions = [ ticks_labels[n] / step for n in range(n_ticks) ] + [ top_pos ]
      # convert to string
      ticks_labels = [  "%.1f" % x for x in ticks_labels ]
      # return position, label tuple to use with x/yticks
      return ticks_positions, ticks_labels

  # apply to the axis
  xticks( *get_rounded_ticks ( len(specgram), time_step, n_xticks ) )
  yticks( *get_rounded_ticks ( len(specgram[0]), (samplerate / 2. / 1000.) / len(specgram[0]), n_yticks ) )
  ylabel('Frequency (kHz)')
  xlabel('Time (s)')

if __name__ == '__main__':
  if len(sys.argv) < 2:
    print "Usage: %s <filename>" % sys.argv[0]
  else:
    for soundfile in sys.argv[1:]:
      get_spectrogram(soundfile)
      # display graph
      show()

########NEW FILE########
__FILENAME__ = demo_tempo
#! /usr/bin/env python

import sys
from aubio import tempo, source

win_s = 512                 # fft size
hop_s = win_s / 2           # hop size

if len(sys.argv) < 2:
    print "Usage: %s <filename> [samplerate]" % sys.argv[0]
    sys.exit(1)

filename = sys.argv[1]

samplerate = 0
if len( sys.argv ) > 2: samplerate = int(sys.argv[2])

s = source(filename, samplerate, hop_s)
samplerate = s.samplerate
o = tempo("default", win_s, hop_s, samplerate)

# tempo detection delay, in samples
# default to 4 blocks delay to catch up with
delay = 4. * hop_s

# list of beats, in samples
beats = []

# total number of frames read
total_frames = 0
while True:
    samples, read = s()
    is_beat = o(samples)
    if is_beat:
        this_beat = int(total_frames - delay + is_beat[0] * hop_s)
        print "%f" % (this_beat / float(samplerate))
        beats.append(this_beat)
    total_frames += read
    if read < hop_s: break
#print len(beats)

########NEW FILE########
__FILENAME__ = demo_tempo_plot
#! /usr/bin/env python

import sys
from aubio import tempo, source

win_s = 512                 # fft size
hop_s = win_s / 2           # hop size

if len(sys.argv) < 2:
    print "Usage: %s <filename> [samplerate]" % sys.argv[0]
    sys.exit(1)

filename = sys.argv[1]

samplerate = 0
if len( sys.argv ) > 2: samplerate = int(sys.argv[2])

s = source(filename, samplerate, hop_s)
samplerate = s.samplerate
o = tempo("default", win_s, hop_s, samplerate)

# tempo detection delay, in samples
# default to 4 blocks delay to catch up with
delay = 4. * hop_s

# list of beats, in samples
beats = []

# total number of frames read
total_frames = 0
while True:
    samples, read = s()
    is_beat = o(samples)
    if is_beat:
        this_beat = o.get_last_s()
        beats.append(this_beat)
    total_frames += read
    if read < hop_s: break

if len(beats) > 1:
    # do plotting
    from numpy import array, arange, mean, median, diff
    import matplotlib.pyplot as plt
    bpms = 60./ diff(beats)
    print 'mean period:', "%.2f" % mean(bpms), 'bpm', 'median', "%.2f" % median(bpms), 'bpm'
    print 'plotting', filename
    plt1 = plt.axes([0.1, 0.75, 0.8, 0.19])
    plt2 = plt.axes([0.1, 0.1, 0.8, 0.65], sharex = plt1)
    plt.rc('lines',linewidth='.8')
    for stamp in beats: plt1.plot([stamp, stamp], [-1., 1.], '-r')
    plt1.axis(xmin = 0., xmax = total_frames / float(samplerate) )
    plt1.xaxis.set_visible(False)
    plt1.yaxis.set_visible(False)

    # plot actual periods
    plt2.plot(beats[1:], bpms, '-', label = 'raw')

    # plot moving median of 5 last periods
    median_win_s = 5
    bpms_median = [ median(bpms[i:i + median_win_s:1]) for i in range(len(bpms) - median_win_s ) ]
    plt2.plot(beats[median_win_s+1:], bpms_median, '-', label = 'median of %d' % median_win_s)
    # plot moving median of 10 last periods
    median_win_s = 20
    bpms_median = [ median(bpms[i:i + median_win_s:1]) for i in range(len(bpms) - median_win_s ) ]
    plt2.plot(beats[median_win_s+1:], bpms_median, '-', label = 'median of %d' % median_win_s)

    plt2.axis(ymin = min(bpms), ymax = max(bpms))
    #plt2.axis(ymin = 40, ymax = 240)
    plt.xlabel('time (mm:ss)')
    plt.ylabel('beats per minute (bpm)')
    plt2.set_xticklabels([ "%02d:%02d" % (t/60, t%60) for t in plt2.get_xticks()[:-1]], rotation = 50)

    #plt.savefig('/tmp/t.png', dpi=200)
    plt2.legend()
    plt.show()

else:
    print 'mean period:', "%.2f" % 0, 'bpm', 'median', "%.2f" % 0, 'bpm',
    print 'nothing to plot, file too short?'

########NEW FILE########
__FILENAME__ = demo_tss
#! /usr/bin/env python

import sys
from aubio import source, sink, pvoc, tss

if __name__ == '__main__':
  if len(sys.argv) < 2:
    print 'usage: %s <inputfile> <outputfile_transient> <outputfile_steady>' % sys.argv[0]
    sys.exit(1)

  samplerate = 44100
  win_s = 1024      # fft size
  hop_s = win_s / 4 # block size
  threshold = 0.5

  f = source(sys.argv[1], samplerate, hop_s)
  g = sink(sys.argv[2], samplerate)
  h = sink(sys.argv[3], samplerate)

  pva = pvoc(win_s, hop_s)    # a phase vocoder
  pvb = pvoc(win_s, hop_s)    # another phase vocoder
  t = tss(win_s, hop_s)       # transient steady state separation

  t.set_threshold(threshold)

  read = hop_s

  while read:
    samples, read = f()               # read file
    spec = pva(samples)                # compute spectrum
    trans_spec, stead_spec = t(spec)  # transient steady-state separation
    transients = pva.rdo(trans_spec)   # overlap-add synthesis of transients
    steadstate = pvb.rdo(stead_spec)   # overlap-add synthesis of steady states
    g(transients, read)               # write transients to output
    h(steadstate, read)               # write steady states to output

  del f, g, h                         # finish writing the files now

  from demo_spectrogram import get_spectrogram
  from pylab import subplot, show
  subplot(311)
  get_spectrogram(sys.argv[1])
  subplot(312)
  get_spectrogram(sys.argv[2])
  subplot(313)
  get_spectrogram(sys.argv[3])
  show()

########NEW FILE########
__FILENAME__ = demo_waveform_plot
#! /usr/bin/env python

import sys
from aubio import pvoc, source
from numpy import zeros, hstack

def get_waveform_plot(filename, samplerate = 0, block_size = 4096, ax = None, downsample = 2**4):
    import matplotlib.pyplot as plt
    if not ax:
        fig = plt.figure()
        ax = fig.add_subplot(111)
    hop_s = block_size

    allsamples_max = zeros(0,)
    downsample = downsample  # to plot n samples / hop_s

    a = source(filename, samplerate, hop_s)            # source file
    if samplerate == 0: samplerate = a.samplerate

    total_frames = 0
    while True:
        samples, read = a()
        # keep some data to plot it later
        new_maxes = (abs(samples.reshape(hop_s/downsample, downsample))).max(axis=0)
        allsamples_max = hstack([allsamples_max, new_maxes])
        total_frames += read
        if read < hop_s: break
    allsamples_max = (allsamples_max > 0) * allsamples_max
    allsamples_max_times = [ ( float (t) / downsample ) * hop_s for t in range(len(allsamples_max)) ]

    ax.plot(allsamples_max_times,  allsamples_max, '-b')
    ax.plot(allsamples_max_times, -allsamples_max, '-b')
    ax.axis(xmin = allsamples_max_times[0], xmax = allsamples_max_times[-1])

    set_xlabels_sample2time(ax, allsamples_max_times[-1], samplerate)
    return ax

def set_xlabels_sample2time(ax, latest_sample, samplerate):
    ax.axis(xmin = 0, xmax = latest_sample)
    if latest_sample / float(samplerate) > 60:
        ax.set_xlabel('time (mm:ss)')
        ax.set_xticklabels([ "%02d:%02d" % (t/float(samplerate)/60, (t/float(samplerate))%60) for t in ax.get_xticks()[:-1]], rotation = 50)
    else:
        ax.set_xlabel('time (ss.mm)')
        ax.set_xticklabels([ "%02d.%02d" % (t/float(samplerate), 100*((t/float(samplerate))%1) ) for t in ax.get_xticks()[:-1]], rotation = 50)


if __name__ == '__main__':
    import matplotlib.pyplot as plt
    if len(sys.argv) < 2:
        print "Usage: %s <filename>" % sys.argv[0]
    else:
        for soundfile in sys.argv[1:]:
            get_waveform_plot(soundfile)
            # display graph
            plt.show()

########NEW FILE########
__FILENAME__ = midiconv
# -*- coding: utf-8 -*-

def note2midi(note):
    " convert note name to midi note number, e.g. [C-1, G9] -> [0, 127] "
    _valid_notenames = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
    _valid_modifiers = {None: 0, u'♮': 0, '#': +1, u'♯': +1, u'\udd2a': +2, 'b': -1, u'♭': -1, u'\ufffd': -2}
    _valid_octaves = range(-1, 10)
    if type(note) not in (str, unicode):
        raise TypeError, "a string is required, got %s" % note
    if not (1 < len(note) < 5):
        raise ValueError, "string of 2 to 4 characters expected, got %d (%s)" % (len(note), note)
    notename, modifier, octave = [None]*3

    if len(note) == 4:
        notename, modifier, octave_sign, octave = note
        octave = octave_sign + octave
    elif len(note) == 3:
        notename, modifier, octave = note
        if modifier == '-':
            octave = modifier + octave
            modifier = None
    else:
        notename, octave = note

    notename = notename.upper()
    octave = int(octave)

    if notename not in _valid_notenames:
        raise ValueError, "%s is not a valid note name" % notename
    if modifier not in _valid_modifiers:
        raise ValueError, "%s is not a valid modifier" % modifier
    if octave not in _valid_octaves:
        raise ValueError, "%s is not a valid octave" % octave

    midi = 12 + octave * 12 + _valid_notenames[notename] + _valid_modifiers[modifier]
    if midi > 127:
        raise ValueError, "%s is outside of the range C-2 to G8" % note
    return midi

def midi2note(midi):
    " convert midi note number to note name, e.g. [0, 127] -> [C-1, G9] "
    if type(midi) != int:
        raise TypeError, "an integer is required, got %s" % midi
    if not (-1 < midi < 128):
        raise ValueError, "an integer between 0 and 127 is excepted, got %d" % midi
    midi = int(midi)
    _valid_notenames = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    return _valid_notenames[midi % 12] + str( midi / 12 - 1)

def freq2note(freq):
    from aubio import freqtomidi
    return midi2note(int(freqtomidi(freq)))

########NEW FILE########
__FILENAME__ = slicing
from aubio import source, sink
import os

max_timestamp = 1e120

def slice_source_at_stamps(source_file, timestamps, timestamps_end = None,
        output_dir = None,
        samplerate = 0,
        hopsize = 256):

    if timestamps == None or len(timestamps) == 0:
        raise ValueError ("no timestamps given")

    if timestamps[0] != 0:
        timestamps = [0] + timestamps
        if timestamps_end != None:
            timestamps_end = [timestamps[1] - 1] + timestamps_end

    if timestamps_end != None:
        if len(timestamps_end) != len(timestamps):
            raise ValueError ("len(timestamps_end) != len(timestamps)")
    else:
        timestamps_end = [t - 1 for t in timestamps[1:] ] + [ max_timestamp ]

    regions = zip(timestamps, timestamps_end)
    #print regions

    source_base_name, source_ext = os.path.splitext(os.path.basename(source_file))
    if output_dir != None:
        if not os.path.isdir(output_dir):
            os.makedirs(output_dir)
        source_base_name = os.path.join(output_dir, source_base_name)

    def new_sink_name(source_base_name, timestamp, samplerate):
        timestamp_seconds = timestamp / float(samplerate)
        return source_base_name + "_%011.6f" % timestamp_seconds + '.wav'

    # reopen source file
    s = source(source_file, samplerate, hopsize)
    samplerate = s.get_samplerate()

    total_frames = 0
    slices = []

    while True:
        # get hopsize new samples from source
        vec, read = s.do_multi()
        # if the total number of frames read will exceed the next region start
        if len(regions) and total_frames + read >= regions[0][0]:
            #print "getting", regions[0], "at", total_frames
            # get next region
            start_stamp, end_stamp = regions.pop(0)
            # create a name for the sink
            new_sink_path = new_sink_name(source_base_name, start_stamp, samplerate)
            # create its sink
            g = sink(new_sink_path, samplerate, s.channels)
            # create a dictionary containing all this
            new_slice = {'start_stamp': start_stamp, 'end_stamp': end_stamp, 'sink': g}
            # append the dictionary to the current list of slices
            slices.append(new_slice)

        for current_slice in slices:
            start_stamp = current_slice['start_stamp']
            end_stamp = current_slice['end_stamp']
            g = current_slice['sink']
            # sample index to start writing from new source vector
            start = max(start_stamp - total_frames, 0)
            # number of samples yet to written be until end of region
            remaining = end_stamp - total_frames + 1
            #print current_slice, remaining, start
            # not enough frames remaining, time to split
            if remaining < read:
                if remaining > start:
                    # write remaining samples from current region
                    g.do_multi(vec[:,start:remaining], remaining - start)
                    #print "closing region", "remaining", remaining
                    # close this file
                    g.close()
            elif read > start:
                # write all the samples
                g.do_multi(vec[:,start:read], read - start)
        total_frames += read
        if read < hopsize: break

########NEW FILE########
__FILENAME__ = generator
#! /usr/bin/python

""" This file generates a c file from a list of cpp prototypes. """

import os, sys, shutil
from gen_pyobject import write_msg, gen_new_init, gen_do, gen_members, gen_methods, gen_finish

def get_cpp_objects():

  cpp_output = [l.strip() for l in os.popen('cpp -DAUBIO_UNSTABLE=1 -I../build/src ../src/aubio.h').readlines()]

  cpp_output = filter(lambda y: len(y) > 1, cpp_output)
  cpp_output = filter(lambda y: not y.startswith('#'), cpp_output)

  i = 1
  while 1:
      if i >= len(cpp_output): break
      if cpp_output[i-1].endswith(',') or cpp_output[i-1].endswith('{') or cpp_output[i].startswith('}'):
          cpp_output[i] = cpp_output[i-1] + ' ' + cpp_output[i]
          cpp_output.pop(i-1)
      else:
          i += 1

  typedefs = filter(lambda y: y.startswith ('typedef struct _aubio'), cpp_output)

  cpp_objects = [a.split()[3][:-1] for a in typedefs]

  return cpp_output, cpp_objects

def generate_object_files(output_path):
  if os.path.isdir(output_path): shutil.rmtree(output_path)
  os.mkdir(output_path)

  generated_objects = []
  cpp_output, cpp_objects = get_cpp_objects()
  skip_objects = [
      # already in ext/
      'fft',
      'pvoc',
      'filter',
      'filterbank',
      #'resampler',
      # AUBIO_UNSTABLE
      'hist',
      'parameter',
      'scale',
      'beattracking',
      'resampler',
      'sndfile',
      'peakpicker',
      'pitchfcomb',
      'pitchmcomb',
      'pitchschmitt',
      'pitchspecacf',
      'pitchyin',
      'pitchyinfft',
      'sink',
      'sink_apple_audio',
      'sink_sndfile',
      'sink_wavwrite',
      'source',
      'source_apple_audio',
      'source_sndfile',
      'source_avcodec',
      'source_wavread',
      #'sampler',
      'audio_unit',
      ]

  write_msg("-- INFO: %d objects in total" % len(cpp_objects))

  for this_object in cpp_objects:
      lint = 0

      if this_object[-2:] == '_t':
          object_name = this_object[:-2]
      else:
          object_name = this_object
          write_msg("-- WARNING: %s does not end in _t" % this_object)

      if object_name[:len('aubio_')] != 'aubio_':
          write_msg("-- WARNING: %s does not start n aubio_" % this_object)

      write_msg("-- INFO: looking at", object_name)
      object_methods = filter(lambda x: this_object in x, cpp_output)
      object_methods = [a.strip() for a in object_methods]
      object_methods = filter(lambda x: not x.startswith('typedef'), object_methods)
      #for method in object_methods:
      #    write_msg(method)
      new_methods = filter(lambda x: 'new_'+object_name in x, object_methods)
      if len(new_methods) > 1:
          write_msg("-- WARNING: more than one new method for", object_name)
          for method in new_methods:
              write_msg(method)
      elif len(new_methods) < 1:
          write_msg("-- WARNING: no new method for", object_name)
      elif 0:
          for method in new_methods:
              write_msg(method)

      del_methods = filter(lambda x: 'del_'+object_name in x, object_methods)
      if len(del_methods) > 1:
          write_msg("-- WARNING: more than one del method for", object_name)
          for method in del_methods:
              write_msg(method)
      elif len(del_methods) < 1:
          write_msg("-- WARNING: no del method for", object_name)

      do_methods = filter(lambda x: object_name+'_do' in x, object_methods)
      if len(do_methods) > 1:
          pass
          #write_msg("-- WARNING: more than one do method for", object_name)
          #for method in do_methods:
          #    write_msg(method)
      elif len(do_methods) < 1:
          write_msg("-- WARNING: no do method for", object_name)
      elif 0:
          for method in do_methods:
              write_msg(method)

      # check do methods return void
      for method in do_methods:
          if (method.split()[0] != 'void'):
              write_msg("-- ERROR: _do method does not return void:", method )

      get_methods = filter(lambda x: object_name+'_get_' in x, object_methods)

      set_methods = filter(lambda x: object_name+'_set_' in x, object_methods)
      for method in set_methods:
          if (method.split()[0] != 'uint_t'):
              write_msg("-- ERROR: _set method does not return uint_t:", method )

      other_methods = filter(lambda x: x not in new_methods, object_methods)
      other_methods = filter(lambda x: x not in del_methods, other_methods)
      other_methods = filter(lambda x: x not in    do_methods, other_methods)
      other_methods = filter(lambda x: x not in get_methods, other_methods)
      other_methods = filter(lambda x: x not in set_methods, other_methods)

      if len(other_methods) > 0:
          write_msg("-- WARNING: some methods for", object_name, "were unidentified")
          for method in other_methods:
              write_msg(method)


      # generate this_object
      short_name = object_name[len('aubio_'):]
      if short_name in skip_objects:
              write_msg("-- INFO: skipping object", short_name )
              continue
      if 1: #try:
          s = gen_new_init(new_methods[0], short_name)
          s += gen_do(do_methods[0], short_name)
          s += gen_members(new_methods[0], short_name)
          s += gen_methods(get_methods, set_methods, short_name)
          s += gen_finish(short_name)
          generated_filepath = os.path.join(output_path,'gen-'+short_name+'.c')
          fd = open(generated_filepath, 'w')
          fd.write(s)
      #except Exception, e:
      #        write_msg("-- ERROR:", type(e), str(e), "in", short_name)
      #        continue
      generated_objects += [this_object]

  s = """// generated list of objects created with generator.py

"""

  types_ready = []
  for each in generated_objects:
      types_ready.append("  PyType_Ready (&Py_%sType) < 0" % \
              each.replace('aubio_','').replace('_t','') )

  s = """// generated list of objects created with generator.py

#include "aubio-generated.h"
"""

  s += """
int generated_types_ready (void)
{
  return (
"""
  s += ('\n     ||').join(types_ready)
  s += """);
}
"""

  s += """
void add_generated_objects ( PyObject *m )
{"""
  for each in generated_objects:
    s += """
  Py_INCREF (&Py_%(name)sType);
  PyModule_AddObject (m, "%(name)s", (PyObject *) & Py_%(name)sType);""" % \
          { 'name': ( each.replace('aubio_','').replace('_t','') ) }

  s += """
}"""

  fd = open(os.path.join(output_path,'aubio-generated.c'), 'w')
  fd.write(s)

  s = """// generated list of objects created with generator.py

#include <Python.h>

"""

  for each in generated_objects:
      s += "extern PyTypeObject Py_%sType;\n" % \
              each.replace('aubio_','').replace('_t','')

  s+= "int generated_objects ( void );\n"
  s+= "void add_generated_objects( PyObject *m );\n"

  fd = open(os.path.join(output_path,'aubio-generated.h'), 'w')
  fd.write(s)

  from os import listdir
  generated_files = listdir(output_path)
  generated_files = filter(lambda x: x.endswith('.c'), generated_files)
  generated_files = [output_path+'/'+f for f in generated_files]
  return generated_files

if __name__ == '__main__':
  generate_object_files('gen')

########NEW FILE########
__FILENAME__ = gen_pyobject
#! /usr/bin/python

""" This madness of code is used to generate the C code of the python interface
to aubio. Don't try this at home.

The list of typedefs and functions is obtained from the command line 'cpp
aubio.h'. This list is then used to parse all the functions about this object.

I hear the ones asking "why not use swig, or cython, or something like that?"

The requirements for this extension are the following:

    - aubio vectors can be viewed as numpy arrays, and vice versa
    - aubio 'object' should be python classes, not just a bunch of functions

I haven't met any python interface generator that can meet both these
requirements. If you know of one, please let me know, it will spare me
maintaining this bizarre file.
"""

param_numbers = {
  'source': [0, 2],
  'sink':   [2, 0],
  'sampler': [1, 1],
}

# TODO
# do function: for now, only the following pattern is supported:
# void aubio_<foo>_do (aubio_foo_t * o, 
#       [input1_t * input, [output1_t * output, ..., output3_t * output]]);
# There is no way of knowing that output1 is actually input2. In the future,
# const could be used for the inputs in the C prototypes.

def write_msg(*args):
  pass
  # uncomment out for debugging
  #print args

def split_type(arg):
    """ arg = 'foo *name' 
        return ['foo*', 'name'] """
    l = arg.split()
    type_arg = {'type': l[0], 'name': l[1]}
    # ['foo', '*name'] -> ['foo*', 'name']
    if l[-1].startswith('*'):
        #return [l[0]+'*', l[1][1:]]
        type_arg['type'] = l[0] + '*'
        type_arg['name'] = l[1][1:]
    # ['foo', '*', 'name'] -> ['foo*', 'name']
    if len(l) == 3:
        #return [l[0]+l[1], l[2]]
        type_arg['type'] = l[0]+l[1]
        type_arg['name'] = l[2]
    else:
        #return l
        pass
    return type_arg

def get_params(proto):
    """ get the list of parameters from a function prototype
    example: proto = "int main (int argc, char ** argv)"
    returns: ['int argc', 'char ** argv']
    """
    import re
    paramregex = re.compile('[\(, ](\w+ \*?\*? ?\w+)[, \)]')
    return paramregex.findall(proto)

def get_params_types_names(proto):
    """ get the list of parameters from a function prototype
    example: proto = "int main (int argc, char ** argv)"
    returns: [['int', 'argc'], ['char **','argv']]
    """
    return map(split_type, get_params(proto)) 

def get_return_type(proto):
    import re
    paramregex = re.compile('(\w+ ?\*?).*')
    outputs = paramregex.findall(proto)
    assert len(outputs) == 1
    return outputs[0].replace(' ', '')

def get_name(proto):
    name = proto.split()[1].split('(')[0]
    return name.replace('*','')

# the important bits: the size of the output for each objects. this data should
# move into the C library at some point.
defaultsizes = {
    'resampler':    ['input->length * self->ratio'],
    'specdesc':     ['1'],
    'onset':        ['1'],
    'pitchyin':     ['1'],
    'pitchyinfft':  ['1'],
    'pitchschmitt': ['1'],
    'pitchmcomb':   ['1'],
    'pitchfcomb':   ['1'],
    'pitch':        ['1'],
    'tss':          ['self->buf_size', 'self->buf_size'],
    'mfcc':         ['self->n_coeffs'],
    'beattracking': ['self->hop_size'],
    'tempo':        ['1'],
    'peakpicker':   ['1'],
    'source':       ['self->hop_size', '1'],
    'sampler':      ['self->hop_size'],
    'wavetable':    ['self->hop_size'],
}

# default value for variables
aubioinitvalue = {
    'uint_t': 0,
    'smpl_t': 0,
    'lsmp_t': 0.,
    'char_t*': 'NULL',
    }

aubiodefvalue = {
    # we have some clean up to do
    'buf_size': 'Py_default_vector_length', 
    # and here too
    'hop_size': 'Py_default_vector_length / 2', 
    # these should be alright
    'samplerate': 'Py_aubio_default_samplerate', 
    # now for the non obvious ones
    'n_filters': '40', 
    'n_coeffs': '13', 
    'nelems': '10',
    'flow': '0.', 
    'fhig': '1.', 
    'ilow': '0.', 
    'ihig': '1.', 
    'thrs': '0.5',
    'ratio': '0.5',
    'method': '"default"',
    'uri': '"none"',
    }

# aubio to python
aubio2pytypes = {
    'uint_t': 'I',
    'smpl_t': 'f',
    'lsmp_t': 'd',
    'fvec_t*': 'O',
    'cvec_t*': 'O',
    'char_t*': 's',
}

# python to aubio
aubiovecfrompyobj = {
    'fvec_t*': 'PyAubio_ArrayToCFvec',
    'cvec_t*': 'PyAubio_ArrayToCCvec',
    'uint_t': '(uint_t)PyInt_AsLong',
}

# aubio to python
aubiovectopyobj = {
    'fvec_t*': 'PyAubio_CFvecToArray',
    'cvec_t*': 'PyAubio_CCvecToPyCvec',
    'smpl_t': 'PyFloat_FromDouble',
    'uint_t*': 'PyInt_FromLong',
    'uint_t': 'PyInt_FromLong',
}

def gen_new_init(newfunc, name):
    newparams = get_params_types_names(newfunc)
    # self->param1, self->param2, self->param3
    if len(newparams):
        selfparams = ', self->'+', self->'.join([p['name'] for p in newparams])
    else:
        selfparams = '' 
    # "param1", "param2", "param3"
    paramnames = ", ".join(["\""+p['name']+"\"" for p in newparams])
    pyparams = "".join(map(lambda p: aubio2pytypes[p['type']], newparams))
    paramrefs = ", ".join(["&" + p['name'] for p in newparams])
    s = """\
// WARNING: this file is generated, DO NOT EDIT

// WARNING: if you haven't read the first line yet, please do so
#include "aubiowraphell.h"

typedef struct
{
  PyObject_HEAD
  aubio_%(name)s_t * o;
""" % locals()
    for p in newparams:
        ptype = p['type']
        pname = p['name']
        s += """\
  %(ptype)s %(pname)s;
""" % locals()
    s += """\
} Py_%(name)s;

static char Py_%(name)s_doc[] = "%(name)s object";

static PyObject *
Py_%(name)s_new (PyTypeObject * pytype, PyObject * args, PyObject * kwds)
{
  Py_%(name)s *self;
""" % locals()
    for p in newparams:
        ptype = p['type']
        pname = p['name']
        initval = aubioinitvalue[ptype]
        s += """\
  %(ptype)s %(pname)s = %(initval)s;
""" % locals()
    # now the actual PyArg_Parse
    if len(paramnames):
        s += """\
  static char *kwlist[] = { %(paramnames)s, NULL };

  if (!PyArg_ParseTupleAndKeywords (args, kwds, "|%(pyparams)s", kwlist,
          %(paramrefs)s)) {
    return NULL;
  }
""" % locals()
    s += """\

  self = (Py_%(name)s *) pytype->tp_alloc (pytype, 0);

  if (self == NULL) {
    return NULL;
  }
""" % locals()
    for p in newparams:
        ptype = p['type']
        pname = p['name']
        defval = aubiodefvalue[pname]
        if ptype == 'char_t*':
            s += """\

  self->%(pname)s = %(defval)s;
  if (%(pname)s != NULL) {
    self->%(pname)s = %(pname)s;
  }
""" % locals()
        elif ptype == 'uint_t':
            s += """\

  self->%(pname)s = %(defval)s;
  if ((sint_t)%(pname)s > 0) {
    self->%(pname)s = %(pname)s;
  } else if ((sint_t)%(pname)s < 0) {
    PyErr_SetString (PyExc_ValueError,
        "can not use negative value for %(pname)s");
    return NULL;
  }
""" % locals()
        elif ptype == 'smpl_t':
            s += """\

  self->%(pname)s = %(defval)s;
  if (%(pname)s != %(defval)s) {
    self->%(pname)s = %(pname)s;
  }
""" % locals()
        else:
            write_msg ("ERROR, unknown type of parameter %s %s" % (ptype, pname) )
    s += """\

  return (PyObject *) self;
}

AUBIO_INIT(%(name)s %(selfparams)s)

AUBIO_DEL(%(name)s)

""" % locals()
    return s

def gen_do_input_params(inputparams):
  inputdefs = ''
  parseinput = ''
  inputrefs = ''
  inputvecs = ''
  pytypes = ''

  if len(inputparams):
    # build the parsing string for PyArg_ParseTuple
    pytypes = "".join([aubio2pytypes[p['type']] for p in inputparams])

    inputdefs = "  /* input vectors python prototypes */\n"
    for p in inputparams:
      if p['type'] != 'uint_t':
        inputdefs += "  PyObject * " + p['name'] + "_obj;\n"

    inputvecs = "  /* input vectors prototypes */\n  "
    inputvecs += "\n  ".join(map(lambda p: p['type'] + ' ' + p['name'] + ";", inputparams))

    parseinput = "  /* input vectors parsing */\n  "
    for p in inputparams:
        inputvec = p['name']
        if p['type'] != 'uint_t':
          inputdef = p['name'] + "_obj"
        else:
          inputdef = p['name']
        converter = aubiovecfrompyobj[p['type']]
        if p['type'] != 'uint_t':
          parseinput += """%(inputvec)s = %(converter)s (%(inputdef)s);

  if (%(inputvec)s == NULL) {
    return NULL;
  }

  """ % locals()

    # build the string for the input objects references
    inputreflist = []
    for p in inputparams:
      if p['type'] != 'uint_t':
        inputreflist += [ "&" + p['name'] + "_obj" ]
      else:
        inputreflist += [ "&" + p['name'] ]
    inputrefs = ", ".join(inputreflist)
    # end of inputs strings
  return inputdefs, parseinput, inputrefs, inputvecs, pytypes

def gen_do_output_params(outputparams, name):
  outputvecs = ""
  outputcreate = ""
  if len(outputparams):
    outputvecs = "  /* output vectors prototypes */\n"
    for p in outputparams:
      params = {
        'name': p['name'], 'pytype': p['type'], 'autype': p['type'][:-3],
        'length': defaultsizes[name].pop(0) }
      if (p['type'] == 'uint_t*'):
        outputvecs += '  uint_t' + ' ' + p['name'] + ";\n"
        outputcreate += "  %(name)s = 0;\n" % params
      else:
        outputvecs += "  " + p['type'] + ' ' + p['name'] + ";\n"
        outputcreate += "  /* creating output %(name)s as a new_%(autype)s of length %(length)s */\n" % params
        outputcreate += "  %(name)s = new_%(autype)s (%(length)s);\n" % params

  returnval = "";
  if len(outputparams) > 1:
    returnval += "  PyObject *outputs = PyList_New(0);\n"
    for p in outputparams:
      returnval += "  PyList_Append( outputs, (PyObject *)" + aubiovectopyobj[p['type']] + " (" + p['name'] + ")" +");\n"
    returnval += "  return outputs;"
  elif len(outputparams) == 1:
    if defaultsizes[name] == '1':
      returnval += "  return (PyObject *)PyFloat_FromDouble(" + p['name'] + "->data[0])"
    else:
      returnval += "  return (PyObject *)" + aubiovectopyobj[p['type']] + " (" + p['name'] + ")"
  else:
    returnval += "  Py_RETURN_NONE"
  # end of output strings
  return outputvecs, outputcreate, returnval

def gen_do(dofunc, name):
    funcname = dofunc.split()[1].split('(')[0]
    doparams = get_params_types_names(dofunc) 
    # make sure the first parameter is the object
    assert doparams[0]['type'] == "aubio_"+name+"_t*", \
        "method is not in 'aubio_<name>_t"
    # and remove it
    doparams = doparams[1:]

    n_param = len(doparams)

    if name in param_numbers.keys():
      n_input_param, n_output_param = param_numbers[name]
    else:
      n_input_param, n_output_param = 1, n_param - 1

    assert n_output_param + n_input_param == n_param, "n_output_param + n_input_param != n_param for %s" % name

    inputparams = doparams[:n_input_param]
    outputparams = doparams[n_input_param:n_input_param + n_output_param]

    inputdefs, parseinput, inputrefs, inputvecs, pytypes = gen_do_input_params(inputparams);
    outputvecs, outputcreate, returnval = gen_do_output_params(outputparams, name)

    # build strings for outputs
    # build the parameters for the  _do() call
    doparams_string = "self->o"
    for p in doparams:
      if p['type'] == 'uint_t*':
        doparams_string += ", &" + p['name']
      else:
        doparams_string += ", " + p['name']

    if n_input_param:
      arg_parse_tuple = """\
  if (!PyArg_ParseTuple (args, "%(pytypes)s", %(inputrefs)s)) {
    return NULL;
  }
""" % locals()
    else:
      arg_parse_tuple = ""
    # put it all together
    s = """\
/* function Py_%(name)s_do */
static PyObject * 
Py_%(name)s_do(Py_%(name)s * self, PyObject * args)
{
%(inputdefs)s
%(inputvecs)s
%(outputvecs)s

%(arg_parse_tuple)s

%(parseinput)s
  
%(outputcreate)s

  /* compute _do function */
  %(funcname)s (%(doparams_string)s);

%(returnval)s;
}
""" % locals()
    return s

def gen_members(new_method, name):
    newparams = get_params_types_names(new_method)
    s = """
AUBIO_MEMBERS_START(%(name)s)""" % locals()
    for param in newparams:
        if param['type'] == 'char_t*':
            s += """
  {"%(pname)s", T_STRING, offsetof (Py_%(name)s, %(pname)s), READONLY, ""},""" \
        % { 'pname': param['name'], 'ptype': param['type'], 'name': name}
        elif param['type'] == 'uint_t':
            s += """
  {"%(pname)s", T_INT, offsetof (Py_%(name)s, %(pname)s), READONLY, ""},""" \
        % { 'pname': param['name'], 'ptype': param['type'], 'name': name}
        elif param['type'] == 'smpl_t':
            s += """
  {"%(pname)s", T_FLOAT, offsetof (Py_%(name)s, %(pname)s), READONLY, ""},""" \
        % { 'pname': param['name'], 'ptype': param['type'], 'name': name}
        else:
            write_msg ("-- ERROR, unknown member type ", param )
    s += """
AUBIO_MEMBERS_STOP(%(name)s)

""" % locals()
    return s


def gen_methods(get_methods, set_methods, name):
    s = ""
    method_defs = ""
    for method in set_methods:
        method_name = get_name(method)
        params = get_params_types_names(method)
        out_type = get_return_type(method)
        assert params[0]['type'] == "aubio_"+name+"_t*", \
            "get method is not in 'aubio_<name>_t"
        write_msg (method )
        write_msg (params[1:])
        setter_args = "self->o, " +",".join([p['name'] for p in params[1:]])
        parse_args = ""
        for p in params[1:]:
            parse_args += p['type'] + " " + p['name'] + ";\n"
        argmap = "".join([aubio2pytypes[p['type']] for p in params[1:]])
        arglist = ", ".join(["&"+p['name'] for p in params[1:]])
        parse_args += """
  if (!PyArg_ParseTuple (args, "%(argmap)s", %(arglist)s)) {
    return NULL;
  } """ % locals()
        s += """
static PyObject *
Py%(funcname)s (Py_%(objname)s *self, PyObject *args)
{
  uint_t err = 0;

  %(parse_args)s

  err = %(funcname)s (%(setter_args)s);

  if (err > 0) {
    PyErr_SetString (PyExc_ValueError,
        "error running %(funcname)s");
    return NULL;
  }
  Py_RETURN_NONE;
}
""" % {'funcname': method_name, 'objname': name, 
        'out_type': out_type, 'setter_args': setter_args, 'parse_args': parse_args }
        shortname = method_name.split('aubio_'+name+'_')[-1]
        method_defs += """\
  {"%(shortname)s", (PyCFunction) Py%(method_name)s,
    METH_VARARGS, ""},
""" % locals()

    for method in get_methods:
        method_name = get_name(method)
        params = get_params_types_names(method)
        out_type = get_return_type(method)
        assert params[0]['type'] == "aubio_"+name+"_t*", \
            "get method is not in 'aubio_<name>_t %s" % params[0]['type']
        assert len(params) == 1, \
            "get method has more than one parameter %s" % params
        getter_args = "self->o" 
        returnval = "(PyObject *)" + aubiovectopyobj[out_type] + " (tmp)"
        shortname = method_name.split('aubio_'+name+'_')[-1]
        method_defs += """\
  {"%(shortname)s", (PyCFunction) Py%(method_name)s,
    METH_NOARGS, ""},
""" % locals()
        s += """
static PyObject *
Py%(funcname)s (Py_%(objname)s *self, PyObject *unused)
{
  %(out_type)s tmp = %(funcname)s (%(getter_args)s);
  return %(returnval)s;
}
""" % {'funcname': method_name, 'objname': name, 
        'out_type': out_type, 'getter_args': getter_args, 'returnval': returnval }

    s += """
static PyMethodDef Py_%(name)s_methods[] = {
""" % locals() 
    s += method_defs 
    s += """\
  {NULL} /* sentinel */
};
""" % locals() 
    return s

def gen_finish(name):
    s = """\

AUBIO_TYPEOBJECT(%(name)s, "aubio.%(name)s")
""" % locals()
    return s

########NEW FILE########
__FILENAME__ = test_aubio
#! /usr/bin/env python

from numpy.testing import TestCase, run_module_suite

class aubiomodule_test_case(TestCase):

  def test_import(self):
    """ try importing aubio """
    import aubio 

if __name__ == '__main__':
  from unittest import main
  main()


########NEW FILE########
__FILENAME__ = test_cvec
#! /usr/bin/env python

from numpy.testing import TestCase, run_module_suite
from numpy.testing import assert_equal, assert_almost_equal
from aubio import cvec
from numpy import array, shape, pi

class aubio_cvec_test_case(TestCase):

    def test_vector_created_with_zeroes(self):
        a = cvec(10)
        a
        shape(a.norm)
        shape(a.phas)
        a.norm[0]
        assert_equal(a.norm, 0.)
        assert_equal(a.phas, 0.)

    def test_vector_assign_element(self):
        a = cvec()
        a.norm[0] = 1
        assert_equal(a.norm[0], 1)
        a.phas[0] = 1
        assert_equal(a.phas[0], 1)

    def test_vector_assign_element_end(self):
        a = cvec()
        a.norm[-1] = 1
        assert_equal(a.norm[-1], 1)
        assert_equal(a.norm[len(a.norm)-1], 1)
        a.phas[-1] = 1
        assert_equal(a.phas[-1], 1)
        assert_equal(a.phas[len(a.phas)-1], 1)

    def test_assign_cvec_norm_slice(self):
        spec = cvec(1024)
        spec.norm[40:100] = 100
        assert_equal (spec.norm[0:40], 0)
        assert_equal (spec.norm[40:100], 100)
        assert_equal (spec.norm[100:-1], 0)
        assert_equal (spec.phas, 0)

    def test_assign_cvec_phas_slice(self):
        spec = cvec(1024)
        spec.phas[39:-1] = -pi
        assert_equal (spec.phas[0:39], 0)
        assert_equal (spec.phas[39:-1], -pi)
        assert_equal (spec.norm, 0)

if __name__ == '__main__':
    from unittest import main
    main()

########NEW FILE########
__FILENAME__ = test_fft
#! /usr/bin/env python

from numpy.testing import TestCase, run_module_suite
from numpy.testing import assert_equal, assert_almost_equal
from aubio import fvec, fft, cvec
from numpy import array, shape
from math import pi

class aubio_fft_test_case(TestCase):

    def test_members(self):
        """ check members are set correctly """
        win_s = 2048
        f = fft(win_s)
        assert_equal (f.win_s, win_s)

    def test_output_dimensions(self):
        """ check the dimensions of output """
        win_s = 1024
        timegrain = fvec(win_s)
        f = fft (win_s)
        fftgrain = f (timegrain)
        assert_equal (shape(fftgrain.norm), (win_s/2+1,))
        assert_equal (shape(fftgrain.phas), (win_s/2+1,))

    def test_zeros(self):
        """ check the transform of zeros is all zeros """
        win_s = 512
        timegrain = fvec(win_s)
        f = fft (win_s)
        fftgrain = f (timegrain)
        assert_equal ( fftgrain.norm, 0 )
        assert_equal ( fftgrain.phas, 0 )

    def test_impulse(self):
        """ check the transform of one impulse at a random place """
        from random import random
        from math import floor
        win_s = 256
        i = floor(random()*win_s)
        impulse = pi * random()
        f = fft(win_s)
        timegrain = fvec(win_s)
        timegrain[i] = impulse
        fftgrain = f ( timegrain )
        #self.plot_this ( fftgrain.phas )
        assert_almost_equal ( fftgrain.norm, impulse, decimal = 6 )
        assert_equal ( fftgrain.phas <= pi, True)
        assert_equal ( fftgrain.phas >= -pi, True)

    def test_impulse_negative(self):
        """ check the transform of one impulse at a random place """
        from random import random
        from math import floor
        win_s = 256
        i = 0
        impulse = -10.
        f = fft(win_s)
        timegrain = fvec(win_s)
        timegrain[i] = impulse
        fftgrain = f ( timegrain )
        #self.plot_this ( fftgrain.phas )
        assert_almost_equal ( fftgrain.norm, abs(impulse), decimal = 6 )
        if impulse < 0:
            # phase can be pi or -pi, as it is not unwrapped
            assert_almost_equal ( abs(fftgrain.phas[1:-1]) , pi, decimal = 6 )
            assert_almost_equal ( fftgrain.phas[0], pi, decimal = 6)
            assert_almost_equal ( fftgrain.phas[-1], pi, decimal = 6)
        else:
            assert_equal ( fftgrain.phas[1:-1] == 0, True)
            assert_equal ( fftgrain.phas[0] == 0, True)
            assert_equal ( fftgrain.phas[-1] == 0, True)
        # now check the resynthesis
        synthgrain = f.rdo ( fftgrain )
        #self.plot_this ( fftgrain.phas.T )
        assert_equal ( fftgrain.phas <= pi, True)
        assert_equal ( fftgrain.phas >= -pi, True)
        #self.plot_this ( synthgrain - timegrain )
        assert_almost_equal ( synthgrain, timegrain, decimal = 6 )

    def test_impulse_at_zero(self):
        """ check the transform of one impulse at a index 0 """
        win_s = 1024
        impulse = pi
        f = fft(win_s)
        timegrain = fvec(win_s)
        timegrain[0] = impulse
        fftgrain = f ( timegrain )
        #self.plot_this ( fftgrain.phas )
        assert_equal ( fftgrain.phas[0], 0)
        # could be 0 or -0 depending on fft implementation (0 for fftw3, -0 for ooura)
        assert_almost_equal ( fftgrain.phas[1], 0)
        assert_almost_equal ( fftgrain.norm[0], impulse, decimal = 6 )

    def test_rdo_before_do(self):
        """ check running fft.rdo before fft.do works """
        win_s = 1024
        impulse = pi
        f = fft(win_s)
        fftgrain = cvec(win_s)
        t = f.rdo( fftgrain )
        assert_equal ( t, 0 )

    def plot_this(self, this):
        from pylab import plot, show
        plot ( this )
        show ()

if __name__ == '__main__':
    from unittest import main
    main()


########NEW FILE########
__FILENAME__ = test_filter
#! /usr/bin/env python

from numpy.testing import TestCase, assert_equal, assert_almost_equal
from aubio import fvec, digital_filter
from numpy import array
from utils import array_from_text_file

class aubio_filter_test_case(TestCase):

  def test_members(self):
    f = digital_filter()
    assert_equal (f.order, 7)
    f = digital_filter(5)
    assert_equal (f.order, 5)
    f(fvec())
  
  def test_cweighting_error(self):
    f = digital_filter (2)
    self.assertRaises ( ValueError, f.set_c_weighting, 44100 )
    f = digital_filter (8)
    self.assertRaises ( ValueError, f.set_c_weighting, 44100 )
    f = digital_filter (5)
    self.assertRaises ( ValueError, f.set_c_weighting, 4000 )
    f = digital_filter (5)
    self.assertRaises ( ValueError, f.set_c_weighting, 193000 )
    f = digital_filter (7)
    self.assertRaises ( ValueError, f.set_a_weighting, 193000 )
    f = digital_filter (5)
    self.assertRaises ( ValueError, f.set_a_weighting, 192000 )

  def test_c_weighting(self):
    expected = array_from_text_file('c_weighting_test_simple.expected')
    f = digital_filter(5)
    f.set_c_weighting(44100)
    v = fvec(32)
    v[12] = .5
    u = f(v)
    assert_almost_equal (expected[1], u)

  def test_c_weighting_8000(self):
    expected = array_from_text_file('c_weighting_test_simple_8000.expected')
    f = digital_filter(5)
    f.set_c_weighting(8000)
    v = fvec(32)
    v[12] = .5
    u = f(v)
    assert_almost_equal (expected[1], u)

  def test_a_weighting(self):
    expected = array_from_text_file('a_weighting_test_simple.expected')
    f = digital_filter(7)
    f.set_a_weighting(44100)
    v = fvec(32)
    v[12] = .5
    u = f(v)
    assert_almost_equal (expected[1], u)

  def test_a_weighting_parted(self):
    expected = array_from_text_file('a_weighting_test_simple.expected')
    f = digital_filter(7)
    f.set_a_weighting(44100)
    v = fvec(16)
    v[12] = .5
    u = f(v)
    assert_almost_equal (expected[1][:16], u)
    # one more time
    v = fvec(16)
    u = f(v)
    assert_almost_equal (expected[1][16:], u)

if __name__ == '__main__':
  from unittest import main
  main()


########NEW FILE########
__FILENAME__ = test_filterbank
#! /usr/bin/env python

from numpy.testing import TestCase, run_module_suite
from numpy.testing import assert_equal, assert_almost_equal
from numpy import random
from math import pi
from numpy import array
from aubio import cvec, filterbank
from utils import array_from_text_file

class aubio_filterbank_test_case(TestCase):

  def test_members(self):
    f = filterbank(40, 512)
    assert_equal ([f.n_filters, f.win_s], [40, 512])

  def test_set_coeffs(self):
    f = filterbank(40, 512)
    r = random.random([40, 512 / 2 + 1]).astype('float32')
    f.set_coeffs(r)
    assert_equal (r, f.get_coeffs())

  def test_phase(self):
    f = filterbank(40, 512)
    c = cvec(512)
    c.phas[:] = pi
    assert_equal( f(c), 0);

  def test_norm(self):
    f = filterbank(40, 512)
    c = cvec(512)
    c.norm[:] = 1
    assert_equal( f(c), 0);

  def test_random_norm(self):
    f = filterbank(40, 512)
    c = cvec(512)
    c.norm[:] = random.random((512 / 2 + 1,)).astype('float32')
    assert_equal( f(c), 0)

  def test_random_coeffs(self):
    f = filterbank(40, 512)
    c = cvec(512)
    r = random.random([40, 512 / 2 + 1]).astype('float32')
    r /= r.sum()
    f.set_coeffs(r)
    c.norm[:] = random.random((512 / 2 + 1,)).astype('float32')
    assert_equal ( f(c) < 1., True )
    assert_equal ( f(c) > 0., True )

  def test_mfcc_coeffs(self):
    f = filterbank(40, 512)
    c = cvec(512)
    f.set_mel_coeffs_slaney(44100)
    c.norm[:] = random.random((512 / 2 + 1,)).astype('float32')
    assert_equal ( f(c) < 1., True )
    assert_equal ( f(c) > 0., True )

  def test_mfcc_coeffs_16000(self):
    expected = array_from_text_file('filterbank_mfcc_16000_512.expected')
    f = filterbank(40, 512)
    f.set_mel_coeffs_slaney(16000)
    assert_almost_equal ( expected, f.get_coeffs() )

if __name__ == '__main__':
  from unittest import main
  main()


########NEW FILE########
__FILENAME__ = test_filterbank_mel
#! /usr/bin/env python

from numpy.testing import TestCase, run_module_suite
from numpy.testing import assert_equal, assert_almost_equal
from numpy import array, shape
from aubio import cvec, filterbank

class aubio_filterbank_mel_test_case(TestCase):

  def test_slaney(self):
    f = filterbank(40, 512)
    f.set_mel_coeffs_slaney(16000)
    a = f.get_coeffs()
    assert_equal(shape (a), (40, 512/2 + 1) )

  def test_other_slaney(self):
    f = filterbank(40, 512*2)
    f.set_mel_coeffs_slaney(44100)
    a = f.get_coeffs()
    #print "sum is", sum(sum(a))
    for win_s in [256, 512, 1024, 2048, 4096]:
      f = filterbank(40, win_s)
      f.set_mel_coeffs_slaney(320000)
      a = f.get_coeffs()
      #print "sum is", sum(sum(a))

  def test_triangle_freqs_zeros(self):
    f = filterbank(9, 1024)
    freq_list = [40, 80, 200, 400, 800, 1600, 3200, 6400, 12800, 15000, 24000]
    freqs = array(freq_list, dtype = 'float32')
    f.set_triangle_bands(freqs, 48000)
    f.get_coeffs().T
    assert_equal ( f(cvec(1024)), 0)

  def test_triangle_freqs_ones(self):
    f = filterbank(9, 1024)
    freq_list = [40, 80, 200, 400, 800, 1600, 3200, 6400, 12800, 15000, 24000]
    freqs = array(freq_list, dtype = 'float32')
    f.set_triangle_bands(freqs, 48000)
    f.get_coeffs().T
    spec = cvec(1024)
    spec.norm[:] = 1
    assert_almost_equal ( f(spec),
            [ 0.02070313,  0.02138672,  0.02127604,  0.02135417, 
        0.02133301, 0.02133301,  0.02133311,  0.02133334,  0.02133345])

if __name__ == '__main__':
  from unittest import main
  main()



########NEW FILE########
__FILENAME__ = test_fvec
#! /usr/bin/env python

from numpy.testing import TestCase, run_module_suite
from numpy.testing import assert_equal, assert_almost_equal
from aubio import fvec, zero_crossing_rate, alpha_norm, min_removal
from numpy import array, shape

default_size = 512

class aubio_fvec_test_case(TestCase):

    def test_vector_created_with_zeroes(self):
        a = fvec(10)
        assert a.dtype == 'float32'
        assert a.shape == (10,)
        assert_equal (a, 0)

    def test_vector_create_with_list(self):
        a = fvec([0,1,2,3])
        assert a.dtype == 'float32'
        assert a.shape == (4,)
        assert_equal (range(4), a)

    def test_vector_assign_element(self):
        a = fvec(default_size)
        a[0] = 1
        assert_equal(a[0], 1)

    def test_vector_assign_element_end(self):
        a = fvec(default_size)
        a[-1] = 1
        assert_equal(a[-1], 1)
        assert_equal(a[len(a)-1], 1)

    def test_vector(self):
        a = fvec()
        a, len(a) #a.length
        a[0]
        array(a)
        a = fvec(10)
        a = fvec(1)
        a.T
        array(a).T
        a = range(len(a))

    def test_wrong_values(self):
        self.assertRaises (ValueError, fvec, -10)
  
        a = fvec(2)
        self.assertRaises (IndexError, a.__getitem__, 3)
        self.assertRaises (IndexError, a.__getitem__, 2)

    def test_alpha_norm_of_fvec(self):
        a = fvec(2)
        self.assertEquals (alpha_norm(a, 1), 0)
        a[0] = 1
        self.assertEquals (alpha_norm(a, 1), 0.5)
        a[1] = 1
        self.assertEquals (alpha_norm(a, 1), 1)
        a = array([0, 1], dtype='float32')
        from math import sqrt
        assert_almost_equal (alpha_norm(a, 2), sqrt(2)/2.)

    def test_alpha_norm_of_none(self):
        self.assertRaises (ValueError, alpha_norm, None, 1)

    def test_alpha_norm_of_array_of_float32(self):
        # check scalar fails
        a = array(1, dtype = 'float32')
        self.assertRaises (ValueError, alpha_norm, a, 1)
        # check 2d array fails
        a = array([[2],[4]], dtype = 'float32')
        self.assertRaises (ValueError, alpha_norm, a, 1)
        # check 1d array
        a = array(range(10), dtype = 'float32')
        self.assertEquals (alpha_norm(a, 1), 4.5)

    def test_alpha_norm_of_array_of_int(self):
        a = array(1, dtype = 'int')
        self.assertRaises (ValueError, alpha_norm, a, 1)
        a = array([[[1,2],[3,4]]], dtype = 'int')
        self.assertRaises (ValueError, alpha_norm, a, 1)
        a = array(range(10), dtype = 'int')
        self.assertRaises (ValueError, alpha_norm, a, 1)

    def test_alpha_norm_of_array_of_string (self):
        a = "hello"
        self.assertRaises (ValueError, alpha_norm, a, 1)

    def test_zero_crossing_rate(self):
        a = array([0,1,-1], dtype='float32')
        assert_almost_equal (zero_crossing_rate(a), 1./3. )
        a = array([0.]*100, dtype='float32')
        self.assertEquals (zero_crossing_rate(a), 0 )
        a = array([-1.]*100, dtype='float32')
        self.assertEquals (zero_crossing_rate(a), 0 )
        a = array([1.]*100, dtype='float32')
        self.assertEquals (zero_crossing_rate(a), 0 )

    def test_alpha_norm_of_array_of_float64(self):
        # check scalar fail
        a = array(1, dtype = 'float64')
        self.assertRaises (ValueError, alpha_norm, a, 1)
        # check 3d array fail
        a = array([[[1,2],[3,4]]], dtype = 'float64')
        self.assertRaises (ValueError, alpha_norm, a, 1)
        # check float64 1d array fail
        a = array(range(10), dtype = 'float64')
        self.assertRaises (ValueError, alpha_norm, a, 1)
        # check float64 2d array fail
        a = array([range(10), range(10)], dtype = 'float64')
        self.assertRaises (ValueError, alpha_norm, a, 1)

    def test_fvec_min_removal_of_array(self):
        a = array([20,1,19], dtype='float32')
        b = min_removal(a)
        assert_equal (array(b), [19, 0, 18])
        assert_equal (b, [19, 0, 18])
        assert_equal (a, b)
        a[0] = 0
        assert_equal (a, b)

    def test_fvec_min_removal_of_array_float64(self):
        a = array([20,1,19], dtype='float64')
        self.assertRaises (ValueError, min_removal, a)

    def test_fvec_min_removal_of_fvec(self):
        a = fvec(3)
        a = array([20, 1, 19], dtype = 'float32')
        b = min_removal(a)
        assert_equal (array(b), [19, 0, 18])
        assert_equal (b, [19, 0, 18])
        assert_equal (a, b)

if __name__ == '__main__':
    from unittest import main
    main()

########NEW FILE########
__FILENAME__ = test_mathutils
#! /usr/bin/env python

from numpy.testing import TestCase, run_module_suite
from numpy.testing import assert_equal, assert_almost_equal
from numpy import array, arange, isnan, isinf
from aubio import bintomidi, miditobin, freqtobin, bintofreq, freqtomidi, miditofreq
from aubio import unwrap2pi
from aubio import fvec
from math import pi

class aubio_mathutils(TestCase):

    def test_unwrap2pi(self):
        unwrap2pi(int(23))
        unwrap2pi(float(23.))
        unwrap2pi(long(23.))
        unwrap2pi(arange(10))
        unwrap2pi(arange(10).astype("int"))
        unwrap2pi(arange(10).astype("float"))
        unwrap2pi(arange(10).astype("float32"))
        unwrap2pi([1,3,5])
        unwrap2pi([23.,24.,25.])
        a = fvec(10)
        a[:] = 4.
        unwrap2pi(a)
        a = pi/100. * arange(-600,600).astype("float")
        b = unwrap2pi (a)
        #print zip(a, b)

        try:
            print unwrap2pi(["23.","24.",25.])
        except Exception, e:
            pass

    def test_unwrap2pi_takes_fvec(self):
        a = fvec(10)
        b = unwrap2pi(a)
        #print zip(a, b)
        assert ( b > -pi ).all()
        assert ( b <= pi ).all()

    def test_unwrap2pi_takes_array_of_float(self):
        a = arange(-10., 10.).astype("float")
        b = unwrap2pi(a)
        #print zip(a, b)
        assert ( b > -pi ).all()
        assert ( b <= pi ).all()

    def test_unwrap2pi_takes_array_of_float32(self):
        a = arange(-10, 10).astype("float32")
        b = unwrap2pi(a)
        #print zip(a, b)
        assert ( b > -pi ).all()
        assert ( b <= pi ).all()

    def test_freqtomidi(self):
        a = array(range(-20, 50000, 100) + [ -1e32, 1e32 ])
        b = freqtomidi(a)
        #print zip(a, b)
        assert_equal ( isnan(array(b)), False )
        assert_equal ( isinf(array(b)), False )
        assert_equal ( array(b) < 0, False )

    def test_miditofreq(self):
        a = range(-30, 200) + [-100000, 10000]
        b = miditofreq(a)
        #print zip(a, b)
        assert_equal ( isnan(b), False )
        assert_equal ( isinf(b), False )
        assert_equal ( b < 0, False )

    def test_miditobin(self):
        a = range(-30, 200) + [-100000, 10000]
        b = [ bintomidi(x, 44100, 512) for x in a ]
        #print zip(a, b)
        assert_equal ( isnan(array(b)), False )
        assert_equal ( isinf(array(b)), False )
        assert_equal ( array(b) < 0, False )

    def test_bintomidi(self):
        a = range(-100, 512)
        b = [ bintomidi(x, 44100, 512) for x in a ]
        #print zip(a, b)
        assert_equal ( isnan(array(b)), False )
        assert_equal ( isinf(array(b)), False )
        assert_equal ( array(b) < 0, False )

    def test_freqtobin(self):
        a = range(-20, 50000, 100) + [ -1e32, 1e32 ]
        b = [ freqtobin(x, 44100, 512) for x in a ]
        #print zip(a, b)
        assert_equal ( isnan(array(b)), False )
        assert_equal ( isinf(array(b)), False )
        assert_equal ( array(b) < 0, False )

    def test_bintofreq(self):
        a = range(-20, 148)
        b = [ bintofreq(x, 44100, 512) for x in a ]
        #print zip(a, b)
        assert_equal ( isnan(array(b)), False )
        assert_equal ( isinf(array(b)), False )
        assert_equal ( array(b) < 0, False )

if __name__ == '__main__':
    from unittest import main
    main()

########NEW FILE########
__FILENAME__ = test_midi2note
#! /usr/bin/env python
# -*- coding: utf-8 -*-

from aubio import midi2note
import unittest

list_of_known_midis = (
        ( 0, 'C-1' ),
        ( 1, 'C#-1' ),
        ( 38, 'D2' ),
        ( 48, 'C3' ),
        ( 59, 'B3' ),
        ( 60, 'C4' ),
        ( 127, 'G9' ),
        )

class midi2note_good_values(unittest.TestCase):

    def test_midi2note_known_values(self):
        " known values are correctly converted "
        for midi, note in list_of_known_midis:
            self.assertEqual ( midi2note(midi), note )

class midi2note_wrong_values(unittest.TestCase):

    def test_midi2note_negative_value(self):
        " fails when passed a negative value "
        self.assertRaises(ValueError, midi2note, -2)

    def test_midi2note_negative_value(self):
        " fails when passed a value greater than 127 "
        self.assertRaises(ValueError, midi2note, 128)

    def test_midi2note_floating_value(self):
        " fails when passed a floating point "
        self.assertRaises(TypeError, midi2note, 69.2)

    def test_midi2note_character_value(self):
        " fails when passed a value that can not be transformed to integer "
        self.assertRaises(TypeError, midi2note, "a")

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_note2midi
#! /usr/bin/env python
# -*- coding: utf-8 -*-

from aubio import note2midi
import unittest

list_of_known_notes = (
        ( 'C-1', 0 ),
        ( 'C#-1', 1 ),
        ( 'd2', 38 ),
        ( 'C3', 48 ),
        ( 'B3', 59 ),
        ( 'B#3', 60 ),
        ( 'A4', 69 ),
        ( 'A#4', 70 ),
        ( 'Bb4', 70 ),
        ( u'B♭4', 70 ),
        ( 'G8', 115 ),
        ( u'G♯8', 116 ),
        ( 'G9', 127 ),
        ( u'G\udd2a2', 45 ),
        ( u'B\ufffd2', 45 ),
        ( u'A♮2', 45 ),
        )

class note2midi_good_values(unittest.TestCase):

    def test_note2midi_known_values(self):
        " known values are correctly converted "
        for note, midi in list_of_known_notes:
            self.assertEqual ( note2midi(note), midi )

class note2midi_wrong_values(unittest.TestCase):

    def test_note2midi_missing_octave(self):
        " fails when passed only one character"
        self.assertRaises(ValueError, note2midi, 'C')

    def test_note2midi_wrong_modifier(self):
        " fails when passed a note with an invalid modifier "
        self.assertRaises(ValueError, note2midi, 'C.1')

    def test_note2midi_another_wrong_modifier_again(self):
        " fails when passed a note with a invalid note name "
        self.assertRaises(ValueError, note2midi, 'CB-3')

    def test_note2midi_wrong_octave(self):
        " fails when passed a wrong octave number "
        self.assertRaises(ValueError, note2midi, 'CBc')

    def test_note2midi_out_of_range(self):
        " fails when passed a out of range note"
        self.assertRaises(ValueError, note2midi, 'A9')

    def test_note2midi_wrong_data_type(self):
        " fails when passed a non-string value "
        self.assertRaises(TypeError, note2midi, 123)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_onset
#! /usr/bin/env python

from numpy.testing import TestCase, run_module_suite
from numpy.testing import assert_equal, assert_almost_equal
from aubio import onset

class aubio_onset_default(TestCase):

    def test_members(self):
        o = onset()
        assert_equal ([o.buf_size, o.hop_size, o.method, o.samplerate],
            [1024,512,'default',44100])

class aubio_onset_params(TestCase):

    samplerate = 44100

    def setUp(self):
        self.o = onset(samplerate = self.samplerate)

    def test_get_delay(self):
        assert_equal (self.o.get_delay(), int(4.3 * self.o.hop_size))

    def test_get_delay_s(self):
        assert_almost_equal (self.o.get_delay_s(), self.o.get_delay() / float(self.samplerate))

    def test_get_delay_ms(self):
        assert_almost_equal (self.o.get_delay_ms(), self.o.get_delay() * 1000. / self.samplerate, 5)

    def test_get_minioi(self):
        assert_almost_equal (self.o.get_minioi(), 0.02 * self.samplerate)

    def test_get_minioi_s(self):
        assert_almost_equal (self.o.get_minioi_s(), 0.02)

    def test_get_minioi_ms(self):
        assert_equal (self.o.get_minioi_ms(), 20.)

    def test_get_threshold(self):
        assert_almost_equal (self.o.get_threshold(), 0.3)

    def test_set_delay(self):
        val = 256
        self.o.set_delay(val)
        assert_equal (self.o.get_delay(), val)

    def test_set_delay_s(self):
        val = .05
        self.o.set_delay_s(val)
        assert_almost_equal (self.o.get_delay_s(), val)

    def test_set_delay_ms(self):
        val = 50.
        self.o.set_delay_ms(val)
        assert_almost_equal (self.o.get_delay_ms(), val)

    def test_set_minioi(self):
        val = 200
        self.o.set_minioi(val)
        assert_equal (self.o.get_minioi(), val)

    def test_set_minioi_s(self):
        val = 0.04
        self.o.set_minioi_s(val)
        assert_almost_equal (self.o.get_minioi_s(), val)

    def test_set_minioi_ms(self):
        val = 40.
        self.o.set_minioi_ms(val)
        assert_almost_equal (self.o.get_minioi_ms(), val)

    def test_set_threshold(self):
        val = 0.2
        self.o.set_threshold(val)
        assert_almost_equal (self.o.get_threshold(), val)

class aubio_onset_96000(aubio_onset_params):
    samplerate = 96000

class aubio_onset_32000(aubio_onset_params):
    samplerate = 32000

class aubio_onset_8000(aubio_onset_params):
    samplerate = 8000

if __name__ == '__main__':
    from unittest import main
    main()

########NEW FILE########
__FILENAME__ = test_phasevoc
#! /usr/bin/env python

from numpy.testing import TestCase, assert_equal, assert_almost_equal
from aubio import fvec, cvec, pvoc
from numpy import array, shape
from numpy.random import random

precision = 6

class aubio_pvoc_test_case(TestCase):
    """ pvoc object test case """

    def test_members_automatic_sizes_default(self):
        """ check object creation with default parameters """
        f = pvoc()
        assert_equal ([f.win_s, f.hop_s], [1024, 512])

    def test_members_unnamed_params(self):
        """ check object creation with unnamed parameters """
        f = pvoc(2048, 128)
        assert_equal ([f.win_s, f.hop_s], [2048, 128])

    def test_members_named_params(self):
        """ check object creation with named parameters """
        f = pvoc(hop_s = 128, win_s = 2048)
        assert_equal ([f.win_s, f.hop_s], [2048, 128])

    def test_zeros(self):
        """ check the resynthesis of zeros gives zeros """
        win_s, hop_s = 1024, 256
        f = pvoc (win_s, hop_s)
        t = fvec (hop_s)
        for time in range( 4 * win_s / hop_s ):
            s = f(t)
            r = f.rdo(s)
            assert_equal ( array(t), 0)
            assert_equal ( s.norm, 0)
            assert_equal ( s.phas, 0)
            assert_equal ( r, 0)

    def test_resynth_two_steps(self):
        """ check the resynthesis of steps is correct with 50% overlap """
        hop_s = 512
        buf_s = hop_s * 2
        f = pvoc(buf_s, hop_s)
        sigin = fvec(hop_s)
        zeros = fvec(hop_s)
        # negative step
        sigin[20:50] = -.1
        # positive step
        sigin[100:200] = .1
        s1 = f(sigin)
        r1 = f.rdo(s1)
        s2 = f(zeros)
        r2 = f.rdo(s2)
        #self.plot_this ( s2.norm.T )
        assert_almost_equal ( r2, sigin, decimal = precision )
    
    def test_resynth_three_steps(self):
        """ check the resynthesis of steps is correct with 25% overlap """
        hop_s = 16
        buf_s = hop_s * 4
        sigin = fvec(hop_s)
        zeros = fvec(hop_s)
        f = pvoc(buf_s, hop_s)
        for i in xrange(hop_s):
            sigin[i] = random() * 2. - 1.
        t2 = f.rdo( f(sigin) )
        t2 = f.rdo( f(zeros) )
        t2 = f.rdo( f(zeros) )
        t2 = f.rdo( f(zeros) )
        assert_almost_equal( sigin, t2, decimal = precision )
    
    def plot_this( self, this ):
        from pylab import semilogy, show
        semilogy ( this )
        show ()

if __name__ == '__main__':
  from unittest import main
  main()


########NEW FILE########
__FILENAME__ = test_pitch
#! /usr/bin/env python

from unittest import TestCase
from numpy.testing import assert_equal, assert_almost_equal
from numpy import random, sin, arange, mean, median, isnan
from math import pi
from aubio import fvec, pitch, freqtomidi

class aubio_pitch_Good_Values(TestCase):

    def skip_test_new_default(self):
        " creating a pitch object without parameters "
        p = pitch()
        assert_equal ( [p.method, p.buf_size, p.hop_size, p.samplerate],
            ['default', 1024, 512, 44100])

    def test_run_on_silence(self):
        " creating a pitch object with parameters "
        p = pitch('default', 2048, 512, 32000)
        assert_equal ( [p.method, p.buf_size, p.hop_size, p.samplerate],
            ['default', 2048, 512, 32000])

    def test_run_on_zeros(self):
        " running on silence gives 0 "
        p = pitch('default', 2048, 512, 32000)
        f = fvec (512)
        for i in xrange(10): assert_equal (p(f), 0.)

    def test_run_on_ones(self):
        " running on ones gives 0 "
        p = pitch('default', 2048, 512, 32000)
        f = fvec (512)
        f[:] = 1
        for i in xrange(10): assert_equal (p(f), 0.)

class aubio_pitch_Sinusoid(TestCase):

    def run_pitch_on_sinusoid(self, method, buf_size, hop_size, samplerate, freq):
        # create pitch object
        p = pitch(method, buf_size, hop_size, samplerate)
        # duration in seconds
        seconds = .3
        # duration in samples
        duration =  seconds * samplerate
        # increase to the next multiple of hop_size
        duration = duration - duration % hop_size + hop_size;
        # build sinusoid
        sinvec = self.build_sinusoid(duration, freq, samplerate)

        self.run_pitch(p, sinvec, freq)

    def build_sinusoid(self, length, freq, samplerate):
        return sin( 2. * pi * arange(length).astype('float32') * freq / samplerate)

    def run_pitch(self, p, input_vec, freq):
        count = 0
        pitches, errors = [], []
        input_blocks = input_vec.reshape((-1, p.hop_size))
        for new_block in input_blocks:
            pitch = p(new_block)[0]
            pitches.append(pitch)
            errors.append(1. - freqtomidi(pitch) / freqtomidi(freq))
        assert_equal ( len(input_blocks), len(pitches) )
        assert_equal ( isnan(pitches), False )
        # cut the first candidates
        cut = ( p.buf_size - p.hop_size ) / p.hop_size
        pitches = pitches[2:]
        errors = errors[2:]
        # check that the mean of all relative errors is less than 10%
        assert abs (mean(errors) ) < 0.1, pitches
        assert abs (mean(errors) ) < 0.1, "error is bigger than 0.1 (%f)" % mean(errors)
        #print 'len(pitches), cut:', len(pitches), cut
        #print 'mean errors: ', mean(errors), 'mean pitches: ', mean(pitches)

pitch_algorithms = [ "default", "yinfft", "yin", "schmitt", "mcomb", "fcomb" , "specacf" ]

signal_modes = [
        ( 4096,  512, 44100, 2.*882. ),
        ( 4096,  512, 44100, 882. ),
        ( 4096,  512, 44100, 440. ),
        ( 2048,  512, 44100, 440. ),
        ( 2048, 1024, 44100, 440. ),
        ( 2048, 1024, 44100, 440. ),
        ( 2048, 1024, 32000, 440. ),
        ( 2048, 1024, 22050, 440. ),
        ( 1024,  256, 16000, 440. ),
        ( 1024,  256, 8000,  440. ),
        ( 1024, 512+256, 8000, 440. ),
        ]

def create_test (algo, mode):
    def do_test_pitch(self):
        self.run_pitch_on_sinusoid(algo, mode[0], mode[1], mode[2], mode[3])
    return do_test_pitch

for algo in pitch_algorithms:
    for mode in signal_modes:
        test_method = create_test (algo, mode)
        test_method.__name__ = 'test_pitch_%s_%d_%d_%dHz_sin_%.2f' % ( algo,
                mode[0], mode[1], mode[2], mode[3] )
        setattr (aubio_pitch_Sinusoid, test_method.__name__, test_method)

if __name__ == '__main__':
    from unittest import main
    main()

########NEW FILE########
__FILENAME__ = test_sink
#! /usr/bin/env python

from numpy.testing import TestCase, assert_equal, assert_almost_equal
from aubio import fvec, source, sink
from numpy import array
from utils import list_all_sounds, get_tmp_sink_path, del_tmp_sink_path

list_of_sounds = list_all_sounds('sounds')
path = None

many_files = 300 # 256 opened files is too much

class aubio_sink_test_case(TestCase):

    def test_many_sinks(self):
        from tempfile import mkdtemp
        import os.path
        import shutil
        tmpdir = mkdtemp()
        sink_list = []
        for i in range(many_files):
            path = os.path.join(tmpdir, 'f-' + str(i) + '.wav')
            g = sink(path, 0)
            sink_list.append(g)
            write = 32
            for n in range(200):
                vec = fvec(write)
                g(vec, write)
            g.close()
        shutil.rmtree(tmpdir)

    def test_many_sinks_not_closed(self):
        from tempfile import mkdtemp
        import os.path
        import shutil
        tmpdir = mkdtemp()
        sink_list = []
        try:
            for i in range(many_files):
                path = os.path.join(tmpdir, 'f-' + str(i) + '.wav')
                g = sink(path, 0)
                sink_list.append(g)
                write = 256
                for n in range(200):
                    vec = fvec(write)
                    g(vec, write)
        except StandardError:
            pass
        else:
            self.fail("does not fail on too many files open")
        for g in sink_list:
            g.close()
        shutil.rmtree(tmpdir)

    def test_read_and_write(self):

        if not len(list_of_sounds):
            self.skipTest('add some sound files in \'python/tests/sounds\'')

        for path in list_of_sounds:
            for samplerate, hop_size in zip([0, 44100, 8000, 32000], [512, 1024, 64, 256]):
                f = source(path, samplerate, hop_size)
                if samplerate == 0: samplerate = f.samplerate
                sink_path = get_tmp_sink_path()
                g = sink(sink_path, samplerate)
                total_frames = 0
                while True:
                    vec, read = f()
                    g(vec, read)
                    total_frames += read
                    if read < f.hop_size: break
                if 0:
                    print "read", "%.2fs" % (total_frames / float(f.samplerate) ),
                    print "(", total_frames, "frames", "in",
                    print total_frames / f.hop_size, "blocks", "at", "%dHz" % f.samplerate, ")",
                    print "from", f.uri,
                    print "to", g.uri
                del_tmp_sink_path(sink_path)

    def test_read_and_write_multi(self):

        if not len(list_of_sounds):
            self.skipTest('add some sound files in \'python/tests/sounds\'')

        for path in list_of_sounds:
            for samplerate, hop_size in zip([0, 44100, 8000, 32000], [512, 1024, 64, 256]):
                f = source(path, samplerate, hop_size)
                if samplerate == 0: samplerate = f.samplerate
                sink_path = get_tmp_sink_path()
                g = sink(sink_path, samplerate, channels = f.channels)
                total_frames = 0
                while True:
                    vec, read = f.do_multi()
                    g.do_multi(vec, read)
                    total_frames += read
                    if read < f.hop_size: break
                if 0:
                    print "read", "%.2fs" % (total_frames / float(f.samplerate) ),
                    print "(", total_frames, "frames", "in",
                    print f.channels, "channels", "in",
                    print total_frames / f.hop_size, "blocks", "at", "%dHz" % f.samplerate, ")",
                    print "from", f.uri,
                    print "to", g.uri,
                    print "in", g.channels, "channels"
                del_tmp_sink_path(sink_path)

    def test_close_file(self):
        samplerate = 44100
        sink_path = get_tmp_sink_path()
        g = sink(sink_path, samplerate)
        g.close()
        del_tmp_sink_path(sink_path)

    def test_close_file_twice(self):
        samplerate = 44100
        sink_path = get_tmp_sink_path()
        g = sink(sink_path, samplerate)
        g.close()
        g.close()
        del_tmp_sink_path(sink_path)

if __name__ == '__main__':
    from unittest import main
    main()

########NEW FILE########
__FILENAME__ = test_slicing
#! /usr/bin/env python

from numpy.testing import TestCase, run_module_suite
from numpy.testing import assert_equal, assert_almost_equal

from aubio import slice_source_at_stamps
from utils import *

import tempfile
import shutil

n_slices = 4

class aubio_slicing_test_case(TestCase):

    def setUp(self):
        self.source_file = get_default_test_sound(self)
        self.output_dir = tempfile.mkdtemp(suffix = 'aubio_slicing_test_case')

    def test_slice_start_only(self):
        regions_start = [i*1000 for i in range(n_slices)]
        slice_source_at_stamps(self.source_file, regions_start, output_dir = self.output_dir)

    def test_slice_start_only_no_zero(self):
        regions_start = [i*1000 for i in range(1, n_slices)]
        slice_source_at_stamps(self.source_file, regions_start, output_dir = self.output_dir)

    def test_slice_start_beyond_end(self):
        regions_start = [i*1000 for i in range(1, n_slices)]
        regions_start += [count_samples_in_file(self.source_file) + 1000]
        slice_source_at_stamps(self.source_file, regions_start, output_dir = self.output_dir)

    def test_slice_start_every_blocksize(self):
        hopsize = 200
        regions_start = [i*hopsize for i in range(1, n_slices)]
        slice_source_at_stamps(self.source_file, regions_start, output_dir = self.output_dir,
                hopsize = 200)

    def tearDown(self):
        original_samples = count_samples_in_file(self.source_file)
        written_samples = count_samples_in_directory(self.output_dir)
        total_files = count_files_in_directory(self.output_dir)
        assert_equal(n_slices, total_files,
            "number of slices created different from expected")
        assert_equal(written_samples, original_samples,
            "number of samples written different from number of original samples")
        shutil.rmtree(self.output_dir)

class aubio_slicing_with_ends_test_case(TestCase):

    def setUp(self):
        self.source_file = get_default_test_sound(self)
        self.output_dir = tempfile.mkdtemp(suffix = 'aubio_slicing_test_case')

    def test_slice_start_and_ends_no_gap(self):
        regions_start = [i*1000 for i in range(n_slices)]
        regions_ends = [start - 1 for start in regions_start[1:]] + [1e120]
        slice_source_at_stamps(self.source_file, regions_start, regions_ends,
                output_dir = self.output_dir)
        original_samples = count_samples_in_file(self.source_file)
        written_samples = count_samples_in_directory(self.output_dir)
        total_files = count_files_in_directory(self.output_dir)
        assert_equal(n_slices, total_files,
            "number of slices created different from expected")
        assert_equal(written_samples, original_samples,
            "number of samples written different from number of original samples")

    def test_slice_start_and_ends_200_gap(self):
        regions_start = [i*1000 for i in range(n_slices)]
        regions_ends = [start + 199 for start in regions_start]
        slice_source_at_stamps(self.source_file, regions_start, regions_ends,
                output_dir = self.output_dir)
        expected_samples = 200 * n_slices
        written_samples = count_samples_in_directory(self.output_dir)
        total_files = count_files_in_directory(self.output_dir)
        assert_equal(n_slices, total_files,
            "number of slices created different from expected")
        assert_equal(written_samples, expected_samples,
            "number of samples written different from number of original samples")

    def test_slice_start_and_ends_overlaping(self):
        regions_start = [i*1000 for i in range(n_slices)]
        regions_ends = [start + 1199 for start in regions_start]
        slice_source_at_stamps(self.source_file, regions_start, regions_ends,
                output_dir = self.output_dir)
        expected_samples = 1200 * n_slices
        written_samples = count_samples_in_directory(self.output_dir)
        total_files = count_files_in_directory(self.output_dir)
        assert_equal(n_slices, total_files,
            "number of slices created different from expected")
        assert_equal(written_samples, expected_samples,
            "number of samples written different from number of original samples")

    def tearDown(self):
        shutil.rmtree(self.output_dir)


class aubio_slicing_wrong_starts_test_case(TestCase):

    def setUp(self):
        self.source_file = get_default_test_sound(self)
        self.output_dir = tempfile.mkdtemp(suffix = 'aubio_slicing_test_case')

    def test_slice_start_empty(self):
        regions_start = []
        self.assertRaises(ValueError,
                slice_source_at_stamps,
                self.source_file, regions_start, output_dir = self.output_dir)

    def test_slice_start_none(self):
        regions_start = None
        self.assertRaises(ValueError,
                slice_source_at_stamps,
                self.source_file, regions_start, output_dir = self.output_dir)

    def tearDown(self):
        shutil.rmtree(self.output_dir)

class aubio_slicing_wrong_ends_test_case(TestCase):

    def setUp(self):
        self.source_file = get_default_test_sound(self)
        self.output_dir = tempfile.mkdtemp(suffix = 'aubio_slicing_test_case')

    def test_slice_wrong_ends(self):
        regions_start = [i*1000 for i in range(1, n_slices)]
        regions_end = []
        self.assertRaises (ValueError,
            slice_source_at_stamps, self.source_file, regions_start, regions_end,
                output_dir = self.output_dir)

    def test_slice_no_ends(self):
        regions_start = [i*1000 for i in range(1, n_slices)]
        regions_end = None
        slice_source_at_stamps (self.source_file, regions_start, regions_end,
                output_dir = self.output_dir)
        total_files = count_files_in_directory(self.output_dir)
        assert_equal(n_slices, total_files,
            "number of slices created different from expected")
        original_samples = count_samples_in_file(self.source_file)
        written_samples = count_samples_in_directory(self.output_dir)
        assert_equal(written_samples, original_samples,
            "number of samples written different from number of original samples")

    def tearDown(self):
        shutil.rmtree(self.output_dir)

if __name__ == '__main__':
    from unittest import main
    main()

########NEW FILE########
__FILENAME__ = test_source
#! /usr/bin/env python

from numpy.testing import TestCase, assert_equal, assert_almost_equal
from aubio import fvec, source
from numpy import array
from utils import list_all_sounds

list_of_sounds = list_all_sounds('sounds')
path = None

class aubio_source_test_case_base(TestCase):

    def setUp(self):
        if not len(list_of_sounds): self.skipTest('add some sound files in \'python/tests/sounds\'')

class aubio_source_test_case(aubio_source_test_case_base):

    def test_close_file(self):
        samplerate = 0 # use native samplerate
        hop_size = 256
        for p in list_of_sounds:
            f = source(p, samplerate, hop_size)
            f.close()

    def test_close_file_twice(self):
        samplerate = 0 # use native samplerate
        hop_size = 256
        for p in list_of_sounds:
            f = source(p, samplerate, hop_size)
            f.close()
            f.close()

class aubio_source_read_test_case(aubio_source_test_case_base):

    def read_from_sink(self, f):
        total_frames = 0
        while True:
            vec, read = f()
            total_frames += read
            if read < f.hop_size: break
        print "read", "%.2fs" % (total_frames / float(f.samplerate) ),
        print "(", total_frames, "frames", "in",
        print total_frames / f.hop_size, "blocks", "at", "%dHz" % f.samplerate, ")",
        print "from", f.uri

    def test_samplerate_hopsize(self):
        for p in list_of_sounds:
            for samplerate, hop_size in zip([0, 44100, 8000, 32000], [ 512, 512, 64, 256]):
                f = source(p, samplerate, hop_size)
                assert f.samplerate != 0
                self.read_from_sink(f)

    def test_samplerate_none(self):
        for p in list_of_sounds:
            f = source(p)
            assert f.samplerate != 0
            self.read_from_sink(f)

    def test_samplerate_0(self):
        for p in list_of_sounds:
            f = source(p, 0)
            assert f.samplerate != 0
            self.read_from_sink(f)

    def test_wrong_samplerate(self):
        for p in list_of_sounds:
            try:
                f = source(p, -1)
            except ValueError, e:
                pass
            else:
                self.fail('negative samplerate does not raise ValueError')

    def test_wrong_hop_size(self):
        for p in list_of_sounds:
            try:
                f = source(p, 0, -1)
            except ValueError, e:
                pass
            else:
                self.fail('negative hop_size does not raise ValueError')

    def test_zero_hop_size(self):
        for p in list_of_sounds:
            f = source(p, 0, 0)
            assert f.samplerate != 0
            assert f.hop_size != 0
            self.read_from_sink(f)

class aubio_source_readmulti_test_case(aubio_source_read_test_case):

    def read_from_sink(self, f):
        total_frames = 0
        while True:
            vec, read = f.do_multi()
            total_frames += read
            if read < f.hop_size: break
        print "read", "%.2fs" % (total_frames / float(f.samplerate) ),
        print "(", total_frames, "frames", "in",
        print f.channels, "channels and",
        print total_frames / f.hop_size, "blocks", "at", "%dHz" % f.samplerate, ")",
        print "from", f.uri

if __name__ == '__main__':
    from unittest import main
    main()

########NEW FILE########
__FILENAME__ = test_specdesc
#! /usr/bin/env python

from numpy.testing import TestCase, assert_equal, assert_almost_equal
from numpy import random, arange, log, zeros
from aubio import specdesc, cvec
from math import pi

methods = ["default",
     "energy",
     "hfc",
     "complex",
     "phase",
     "specdiff",
     "kl",
     "mkl",
     "specflux",
     "centroid",
     "spread",
     "skewness",
     "kurtosis",
     "slope",
     "decrease",
     "rolloff"]
buf_size = 2048

class aubio_specdesc(TestCase):

    def test_members(self):
        o = specdesc()

        for method in methods:
          o = specdesc(method, buf_size)
          assert_equal ([o.buf_size, o.method], [buf_size, method])

          spec = cvec(buf_size)
          spec.norm[0] = 1
          spec.norm[1] = 1./2.
          #print "%20s" % method, str(o(spec))
          o(spec)
          spec.norm = random.random_sample((len(spec.norm),)).astype('float32')
          spec.phas = random.random_sample((len(spec.phas),)).astype('float32')
          #print "%20s" % method, str(o(spec))
          assert (o(spec) != 0.)

    def test_hfc(self):
        o = specdesc("hfc", buf_size)
        spec = cvec(buf_size)
        # hfc of zeros is zero
        assert_equal (o(spec), 0.)
        # hfc of ones is sum of all bin numbers
        spec.norm[:] = 1
        expected = sum(range(buf_size/2 + 2))
        assert_equal (o(spec), expected)
        # changing phase doesn't change anything
        spec.phas[:] = 1
        assert_equal (o(spec), sum(range(buf_size/2 + 2)))

    def test_phase(self):
        o = specdesc("phase", buf_size)
        spec = cvec(buf_size)
        # phase of zeros is zero
        assert_equal (o(spec), 0.)
        spec.phas = random.random_sample((len(spec.phas),)).astype('float32')
        # phase of random is not zero
        spec.norm[:] = 1
        assert (o(spec) != 0.)

    def test_specdiff(self):
        o = specdesc("phase", buf_size)
        spec = cvec(buf_size)
        # specdiff of zeros is zero
        assert_equal (o(spec), 0.)
        spec.phas = random.random_sample((len(spec.phas),)).astype('float32')
        # phase of random is not zero
        spec.norm[:] = 1
        assert (o(spec) != 0.)
    
    def test_hfc(self):
        o = specdesc("hfc")
        c = cvec()
        assert_equal( 0., o(c))
        a = arange(c.length, dtype='float32')
        c.norm = a
        assert_equal (a, c.norm)
        assert_equal ( sum(a*(a+1)), o(c))

    def test_complex(self):
        o = specdesc("complex")
        c = cvec()
        assert_equal( 0., o(c))
        a = arange(c.length, dtype='float32')
        c.norm = a
        assert_equal (a, c.norm)
        # the previous run was on zeros, so previous frames are still 0
        # so we have sqrt ( abs ( r2 ^ 2) ) == r2
        assert_equal ( sum(a), o(c))
        # second time. c.norm = a, so, r1 = r2, and the euclidian distance is 0
        assert_equal ( 0, o(c))

    def test_kl(self):
        o = specdesc("kl")
        c = cvec()
        assert_equal( 0., o(c))
        a = arange(c.length, dtype='float32')
        c.norm = a
        assert_almost_equal( sum(a * log(1.+ a/1.e-1 ) ) / o(c), 1., decimal=6)

    def test_mkl(self):
        o = specdesc("mkl")
        c = cvec()
        assert_equal( 0., o(c))
        a = arange(c.length, dtype='float32')
        c.norm = a
        assert_almost_equal( sum(log(1.+ a/1.e-1 ) ) / o(c), 1, decimal=6)

    def test_specflux(self):
        o = specdesc("specflux")
        c = cvec()
        assert_equal( 0., o(c))
        a = arange(c.length, dtype='float32')
        c.norm = a
        assert_equal( sum(a), o(c))
        assert_equal( 0, o(c))
        c.norm = zeros(c.length, dtype='float32')
        assert_equal( 0, o(c))

    def test_centroid(self):
        o = specdesc("centroid")
        c = cvec()
        # make sure centroid of zeros is zero
        assert_equal( 0., o(c))
        a = arange(c.length, dtype='float32')
        c.norm = a
        centroid = sum(a*a) / sum(a)
        assert_almost_equal (centroid, o(c), decimal = 2)

        c.norm = a * .5 
        assert_almost_equal (centroid, o(c), decimal = 2)

    def test_spread(self):
        o = specdesc("spread")
        c = cvec(2048)
        ramp = arange(c.length, dtype='float32')
        assert_equal( 0., o(c))

        a = ramp
        c.norm = a
        centroid = sum(a*a) / sum(a)
        spread = sum( a * pow(ramp - centroid, 2.) ) / sum(a)
        assert_almost_equal (o(c), spread, decimal = 1)

    def test_skewness(self):
        o = specdesc("skewness")
        c = cvec()
        assert_equal( 0., o(c))
        a = arange(c.length, dtype='float32')
        c.norm = a
        centroid = sum(a*a) / sum(a)
        spread = sum( (a - centroid)**2 *a) / sum(a)
        skewness = sum( (a - centroid)**3 *a) / sum(a) / spread **1.5
        assert_almost_equal (skewness, o(c), decimal = 2)

        c.norm = a * 3
        assert_almost_equal (skewness, o(c), decimal = 2)

    def test_kurtosis(self):
        o = specdesc("kurtosis")
        c = cvec()
        assert_equal( 0., o(c))
        a = arange(c.length, dtype='float32')
        c.norm = a
        centroid = sum(a*a) / sum(a)
        spread = sum( (a - centroid)**2 *a) / sum(a)
        kurtosis = sum( (a - centroid)**4 *a) / sum(a) / spread **2
        assert_almost_equal (kurtosis, o(c), decimal = 2)

    def test_slope(self):
        o = specdesc("slope")
        c = cvec()
        assert_equal( 0., o(c))
        a = arange(c.length * 2, 0, -2, dtype='float32')
        k = arange(c.length, dtype='float32')
        c.norm = a
        num = len(a) * sum(k*a) - sum(k)*sum(a)
        den = (len(a) * sum(k**2) - sum(k)**2)
        slope = num/den/sum(a)
        assert_almost_equal (slope, o(c), decimal = 5)

        a = arange(0, c.length * 2, +2, dtype='float32')
        c.norm = a
        num = len(a) * sum(k*a) - sum(k)*sum(a)
        den = (len(a) * sum(k**2) - sum(k)**2)
        slope = num/den/sum(a)
        assert_almost_equal (slope, o(c), decimal = 5)

        a = arange(0, c.length * 2, +2, dtype='float32')
        c.norm = a * 2
        assert_almost_equal (slope, o(c), decimal = 5)

    def test_decrease(self):
        o = specdesc("decrease")
        c = cvec()
        assert_equal( 0., o(c))
        a = arange(c.length * 2, 0, -2, dtype='float32')
        k = arange(c.length, dtype='float32')
        c.norm = a
        decrease = sum((a[1:] - a [0]) / k[1:]) / sum(a[1:]) 
        assert_almost_equal (decrease, o(c), decimal = 5)

        a = arange(0, c.length * 2, +2, dtype='float32')
        c.norm = a
        decrease = sum((a[1:] - a [0]) / k[1:]) / sum(a[1:]) 
        assert_almost_equal (decrease, o(c), decimal = 5)

        a = arange(0, c.length * 2, +2, dtype='float32')
        c.norm = a * 2
        decrease = sum((a[1:] - a [0]) / k[1:]) / sum(a[1:]) 
        assert_almost_equal (decrease, o(c), decimal = 5)

    def test_rolloff(self):
        o = specdesc("rolloff")
        c = cvec()
        assert_equal( 0., o(c))
        a = arange(c.length * 2, 0, -2, dtype='float32')
        k = arange(c.length, dtype='float32')
        c.norm = a
        cumsum = .95*sum(a*a)
        i = 0; rollsum = 0
        while rollsum < cumsum:
          rollsum += a[i]*a[i]
          i+=1
        rolloff = i 
        assert_equal (rolloff, o(c))


if __name__ == '__main__':
    from unittest import main
    main()

########NEW FILE########
__FILENAME__ = test_zero_crossing_rate
#! /usr/bin/env python

from numpy.testing import TestCase

from aubio import fvec, zero_crossing_rate

buf_size = 2048

class zero_crossing_rate_test_case(TestCase):

    def setUp(self):
        self.vector = fvec(buf_size)

    def test_zeroes(self):
        """ check zero crossing rate on a buffer of 0. """
        self.assertEqual(0., zero_crossing_rate(self.vector))

    def test_ones(self):
        """ check zero crossing rate on a buffer of 1. """
        self.vector[:] = 1.
        self.assertEqual(0., zero_crossing_rate(self.vector))

    def test_impulse(self):
        """ check zero crossing rate on a buffer with an impulse """
        self.vector[buf_size / 2] = 1.
        self.assertEqual(0., zero_crossing_rate(self.vector))

    def test_negative_impulse(self):
        """ check zero crossing rate on a buffer with a negative impulse """
        self.vector[buf_size / 2] = -1.
        self.assertEqual(2./buf_size, zero_crossing_rate(self.vector))

    def test_single(self):
        """ check zero crossing rate on single crossing """
        self.vector[buf_size / 2 - 1] = 1.
        self.vector[buf_size / 2] = -1.
        self.assertEqual(2./buf_size, zero_crossing_rate(self.vector))

    def test_single_with_gap(self):
        """ check zero crossing rate on single crossing with a gap"""
        self.vector[buf_size / 2 - 2] = 1.
        self.vector[buf_size / 2] = -1.
        self.assertEqual(2./buf_size, zero_crossing_rate(self.vector))

if __name__ == '__main__':
    from unittest import main
    main()

########NEW FILE########
__FILENAME__ = utils
#! /usr/bin/env python

def array_from_text_file(filename, dtype = 'float'):
    import os.path
    from numpy import array
    filename = os.path.join(os.path.dirname(__file__), filename)
    return array([line.split() for line in open(filename).readlines()],
        dtype = dtype)

def list_all_sounds(rel_dir):
    import os.path, glob
    datadir = os.path.join(os.path.dirname(__file__), rel_dir)
    return glob.glob(os.path.join(datadir,'*.*'))

def get_default_test_sound(TestCase, rel_dir = 'sounds'):
    all_sounds = list_all_sounds(rel_dir)
    if len(all_sounds) == 0:
        TestCase.skipTest("please add some sounds in \'python/tests/sounds\'")
    else:
        return all_sounds[0]

def get_tmp_sink_path():
    from tempfile import mkstemp
    import os
    fd, path = mkstemp()
    os.close(fd)
    return path

def del_tmp_sink_path(path):
    import os
    os.unlink(path)

def array_from_yaml_file(filename):
    import yaml
    f = open(filename)
    yaml_data = yaml.safe_load(f)
    f.close()
    return yaml_data

def count_samples_in_file(file_path):
    from aubio import source
    hopsize = 256
    s = source(file_path, 0, hopsize)
    total_frames = 0
    while True:
        samples, read = s()
        total_frames += read
        if read < hopsize: break
    return total_frames

def count_samples_in_directory(samples_dir):
    import os
    total_frames = 0
    for f in os.walk(samples_dir):
        if len(f[2]):
            for each in f[2]:
                file_path = os.path.join(f[0], each)
                if file_path:
                    total_frames += count_samples_in_file(file_path)
    return total_frames

def count_files_in_directory(samples_dir):
    import os
    total_files = 0
    for f in os.walk(samples_dir):
        if len(f[2]):
            for each in f[2]:
                file_path = os.path.join(f[0], each)
                if file_path:
                    total_files += 1
    return total_files

########NEW FILE########
__FILENAME__ = aubioclass
from aubiowrapper import *

class fvec:
    def __init__(self,size):
        self.vec = new_fvec(size)
    def __call__(self):
        return self.vec
    def __del__(self):
        del_fvec(self())
    def get(self,pos):
        return fvec_read_sample(self(),pos)
    def set(self,value,pos):
        return fvec_write_sample(self(),value,pos)
    def data(self):
        return fvec_get_data(self())

class cvec:
    def __init__(self,size):
        self.vec = new_cvec(size)
    def __call__(self):
        return self.vec
    def __del__(self):
        del_cvec(self())
    def get(self,pos):
        return self.get_norm(pos)
    def set(self,val,pos):
        self.set_norm(val,pos)
    def get_norm(self,pos):
        return cvec_read_norm(self(),pos)
    def set_norm(self,val,pos):
        cvec_write_norm(self(),val,pos)
    def get_phas(self,pos):
        return cvec_read_phas(self(),pos)
    def set_phas(self,val,pos):
        cvec_write_phas(self(),val,pos)

class sndfile:
    def __init__(self,filename,model=None):
        if (model!=None):
            self.file = new_aubio_sndfile_wo(model.file,filename)
        else:
            self.file = new_aubio_sndfile_ro(filename)
        if self.file == None:
            raise IOError, "failed opening file %s" % filename
    def __del__(self):
        if self.file != None: del_aubio_sndfile(self.file)
    def info(self):
        aubio_sndfile_info(self.file)
    def samplerate(self):
        return aubio_sndfile_samplerate(self.file)
    def channels(self):
        return aubio_sndfile_channels(self.file)
    def read(self,nfram,vecread):
        return aubio_sndfile_read_mono(self.file,nfram,vecread())
    def write(self,nfram,vecwrite):
        return aubio_sndfile_write(self.file,nfram,vecwrite())

class pvoc:
    def __init__(self,buf,hop):
        self.pv = new_aubio_pvoc(buf,hop)
    def __del__(self):
        del_aubio_pvoc(self.pv)
    def do(self,tf,tc):
        aubio_pvoc_do(self.pv,tf(),tc())
    def rdo(self,tc,tf):
        aubio_pvoc_rdo(self.pv,tc(),tf())

class onsetdetection:
    """ class for aubio_specdesc """
    def __init__(self,mode,buf):
        self.od = new_aubio_specdesc(mode,buf)
    def do(self,tc,tf):
        aubio_specdesc_do(self.od,tc(),tf())
    def __del__(self):
        del_aubio_specdesc(self.od)

class peakpick:
    """ class for aubio_peakpicker """
    def __init__(self,threshold=0.1):
        self.pp = new_aubio_peakpicker()
        self.out = new_fvec(1)
        aubio_peakpicker_set_threshold (self.pp, threshold)
    def do(self,fv):
        aubio_peakpicker_do(self.pp, fv(), self.out)
        return fvec_read_sample(self.out, 0)
    def getval(self):
        return aubio_peakpicker_get_adaptive_threshold(self.pp)
    def __del__(self):
        del_aubio_peakpicker(self.pp)

class onsetpick:
    """ superclass for aubio_pvoc + aubio_specdesc + aubio_peakpicker """
    def __init__(self,bufsize,hopsize,myvec,threshold,mode='dual',derivate=False,dcthreshold=0):
        self.myfft    = cvec(bufsize)
        self.pv       = pvoc(bufsize,hopsize)
        if mode in ['dual'] :
                self.myod     = onsetdetection("hfc",bufsize)
                self.myod2    = onsetdetection("mkl",bufsize)
                self.myonset  = fvec(1)
                self.myonset2 = fvec(1)
        else: 
                self.myod     = onsetdetection(mode,bufsize)
                self.myonset  = fvec(1)
        self.mode     = mode
        self.pp       = peakpick(float(threshold))
        self.derivate = derivate
        self.dcthreshold = dcthreshold 
        self.oldval   = 0.

    def do(self,myvec): 
        self.pv.do(myvec,self.myfft)
        self.myod.do(self.myfft,self.myonset)
        if self.mode == 'dual':
           self.myod2.do(self.myfft,self.myonset2)
           self.myonset.set(self.myonset.get(0)*self.myonset2.get(0),0)
        if self.derivate:
           val         = self.myonset.get(0)
           dval        = val - self.oldval
           self.oldval = val
           if dval > 0: self.myonset.set(dval,0)
           else:  self.myonset.set(0.,0,0)
        isonset, dval = self.pp.do(self.myonset),self.myonset.get(0)
        if self.dcthreshold:
           if dval < self.dcthreshold: isonset = 0 
        return isonset, dval

class pitch:
    def __init__(self,mode="mcomb",bufsize=2048,hopsize=1024,
        samplerate=44100.,omode="freq",tolerance=0.1):
        self.pitchp = new_aubio_pitch(mode,bufsize,hopsize,
            samplerate)
        self.mypitch = fvec(1)
        aubio_pitch_set_unit(self.pitchp,omode)
        aubio_pitch_set_tolerance(self.pitchp,tolerance)
        #self.filt     = filter(srate,"adsgn")
    def __del__(self):
        del_aubio_pitch(self.pitchp)
    def __call__(self,myvec): 
        aubio_pitch_do(self.pitchp,myvec(), self.mypitch())
        return self.mypitch.get(0)

class filter:
    def __init__(self,srate,type=None):
        if (type=="adsgn"):
            self.filter = new_aubio_adsgn_filter(srate)
    def __del__(self):
        #del_aubio_filter(self.filter)
        pass
    def __call__(self,myvec):
        aubio_filter_do(self.filter,myvec())

class beattracking:
    """ class for aubio_beattracking """
    def __init__(self,winlen,channels):
        self.p = new_aubio_beattracking(winlen,channels)
    def do(self,dfframe,out):
        return aubio_beattracking_do(self.p,dfframe(),out())
    def __del__(self):
        del_aubio_beattracking(self.p)


########NEW FILE########
__FILENAME__ = broadcast
from config import *

class run_broadcast:
        def __init__(self,command,*args):
                for host in REMOTEHOSTS:
                        command(host,args[0],args[1:])

def remote_sync(host,path='',options=''):
        optstring = ''
        for i in options:
                optstring = "%s %s" % (optstring,i)
        print RSYNC_CMD,optstring,RSYNC_OPT,' --delete', 
        print '%s%s%s%s%s' % (path,'/ ',host,':',path)


def fetch_results(host,path='',options=''):
        optstring = ''
        for i in options:
                optstring = "%s %s" % (optstring,i)
        print RSYNC_CMD,optstring,RSYNC_OPT,' --update', 
        print '%s%s%s%s%s' % (host,':',path,'/ ',path)

def remote_queue(host,command,options=''):
        print 'oarsub -p "hostname = \'',host,'\'',command
        

########NEW FILE########
__FILENAME__ = config

filefound = 0
try:
        filename = "/etc/aubio-bench.conf"
        execfile(filename)
        filefound = 1
except IOError:
        print "no system wide configuration file found in", filename

try:
        import os
        filename = "%s%s%s" % (os.getenv('HOME'),os.sep,".aubio-bench.conf")
        execfile(filename)
        filefound = 1
except IOError:
        #print "no user configuration file found in", filename
	pass

if filefound == 0:
        import sys
        print "error: no configuration file found at all"
        sys.exit(1)

########NEW FILE########
__FILENAME__ = node
from config import *
import commands,sys
import re

def runcommand(cmd,debug=0):
        if VERBOSE >= VERBOSE_CMD or debug: print cmd
        if debug: return 
        status, output = commands.getstatusoutput(cmd)
        if status == 0 or VERBOSE >= VERBOSE_OUT:
                output = output.split('\n')
        if VERBOSE >= VERBOSE_OUT: 
                for i in output: 
                        if i: print i
        if not status == 0: 
                print 'error:',status,output
                print 'command returning error was',cmd
                #sys.exit(1)
	if output == '' or output == ['']: return
        return output 

def list_files(datapath,filter='f', maxdepth = -1):
	if not os.path.exists(datapath):
		print
		print "ERR: no directory %s were found" % datapath
		sys.exit(1)
	if maxdepth >= 0: maxstring = " -maxdepth %d " % maxdepth	
	else: maxstring = ""
        cmd = '%s' * 6 % ('find ',datapath,maxstring,' -type ',filter, "| sort -n")
        return runcommand(cmd)

def list_wav_files(datapath,maxdepth = -1):
	return list_files(datapath, filter="f -name '*.wav'",maxdepth = maxdepth)

sndfile_filter = "f -name '*.wav' -o -name '*.aif' -o -name '*.aiff'"

def list_snd_files(datapath,maxdepth = -1):
	return list_files(datapath, filter=sndfile_filter, 
		maxdepth = maxdepth)

def list_res_files(datapath,maxdepth = -1):
	return list_files(datapath, filter="f -name '*.txt'", maxdepth = maxdepth)

def list_dirs(datapath):
	return list_files(datapath, filter="d")

def mkdir(path):
        cmd = '%s%s' % ('mkdir -p ',path)
        return runcommand(cmd)

def act_on_data (action,datapath,respath=None,suffix='.txt',filter='f',sub='\.wav$',**keywords):
        """ execute action(datafile,resfile) on all files in datapath """
        dirlist = list_files(datapath,filter=filter)
        if dirlist == ['']: dirlist = []
        if respath:
		respath_in_datapath = re.split(datapath, respath,maxsplit=1)[1:]
        	if(respath_in_datapath and suffix == ''): 
                	print 'error: respath in datapath and no suffix used'
        for i in dirlist:
                j = re.split(datapath, i,maxsplit=1)[1]
                j = re.sub(sub,'',j)
                #j = "%s%s%s"%(respath,j,suffix)
		if respath:
			j = "%s%s"%(respath,j)
			if sub != '':
				j = re.sub(sub,suffix,j)
			else:
				j = "%s%s" % (j,suffix)
                action(i,j,**keywords)

def act_on_results (action,datapath,respath,filter='d'):
        """ execute action(respath) an all subdirectories in respath """
        dirlist = list_files(datapath,filter='d')
        respath_in_datapath = re.split(datapath, respath,maxsplit=1)[1:]
        if(respath_in_datapath and not filter == 'd' and suffix == ''): 
                print 'warning: respath is in datapath'
        for i in dirlist:
                s = re.split(datapath, i ,maxsplit=1)[1]
                action("%s%s%s"%(respath,'/',s))

def act_on_files (action,listfiles,listres=None,suffix='.txt',filter='f',sub='\.wav$',**keywords):
        """ execute action(respath) an all subdirectories in respath """
        if listres and len(listfiles) <= len(listres): 
		for i in range(len(listfiles)):
			action(listfiles[i],listres[i],**keywords)
        else:
		for i in listfiles:
                	action(i,None,**keywords)

class bench:
	""" class to run benchmarks on directories """
	def __init__(self,datadir,resdir=None,checkres=False,checkanno=False,params=[]):
		from aubio.task.params import taskparams
		self.datadir = datadir
		# path to write results path to
		self.resdir = resdir
		# list of annotation files
		self.reslist = []
		# list used to gather results
		self.results = []
		if not params: self.params = taskparams()
		else:          self.params = params
		print "Checking data directory", self.datadir
		self.checkdata()
		if checkanno: self.checkanno()
		if checkres: self.checkres()
	
	def checkdata(self):
		if os.path.isfile(self.datadir):
			self.dirlist = os.path.dirname(self.datadir)
		elif os.path.isdir(self.datadir):
			self.dirlist = list_dirs(self.datadir)
		# allow dir* matching through find commands?
		else:
			print "ERR: path not understood"
			sys.exit(1)
		print "Listing directories in data directory",
		if self.dirlist:
			print " (%d elements)" % len(self.dirlist)
		else:
			print " (0 elements)"
			print "ERR: no directory %s were found" % self.datadir
			sys.exit(1)
		print "Listing sound files in data directory",
		self.sndlist = list_snd_files(self.datadir)
		if self.sndlist:
			print " (%d elements)" % len(self.sndlist)
		else:
			print " (0 elements)"
			print "ERR: no sound files were found in", self.datadir
			sys.exit(1)
	
	def checkanno(self):
		print "Listing annotations in data directory",
		self.reslist = list_res_files(self.datadir)
		print " (%d elements)" % len(self.reslist)
		#for each in self.reslist: print each
		if not self.reslist or len(self.reslist) < len (self.sndlist):
			print "ERR: not enough annotations"
			return -1
		else:
			print "Found enough annotations"
	
	def checkres(self):
		print "Creating results directory"
		act_on_results(mkdir,self.datadir,self.resdir,filter='d')

	def pretty_print(self,sep='|'):
		for i in self.printnames:
			print self.formats[i] % self.v[i], sep,
		print

	def pretty_titles(self,sep='|'):
		for i in self.printnames:
			print self.formats[i] % i, sep,
		print

	def dir_exec(self):
		""" run file_exec on every input file """
		self.l , self.labs = [], [] 
		self.v = {}
		for i in self.valuenames:
			self.v[i] = [] 
		for i in self.valuelists:
			self.v[i] = [] 
		act_on_files(self.file_exec,self.sndlist,self.reslist, \
			suffix='',filter=sndfile_filter)

	def dir_eval(self):
		pass

	def file_gettruth(self,input):
		""" get ground truth filenames """
		from os.path import isfile
		ftrulist = []
		# search for match as filetask.input,".txt" 
		ftru = '.'.join(input.split('.')[:-1])
		ftru = '.'.join((ftru,'txt'))
		if isfile(ftru):
			ftrulist.append(ftru)
		else:
			# search for matches for filetask.input in the list of results
			for i in range(len(self.reslist)):
				check = '.'.join(self.reslist[i].split('.')[:-1])
				check = '_'.join(check.split('_')[:-1])
				if check == '.'.join(input.split('.')[:-1]):
					ftrulist.append(self.reslist[i])
		return ftrulist

	def file_exec(self,input,output):
		""" create filetask, extract data, evaluate """
		filetask = self.task(input,params=self.params)
		computed_data = filetask.compute_all()
		ftrulist = self.file_gettruth(filetask.input)
		for i in ftrulist:
			filetask.eval(computed_data,i,mode='rocloc',vmode='')
			""" append filetask.v to self.v """
			for i in self.valuenames:
				self.v[i].append(filetask.v[i])
			for j in self.valuelists:
				if filetask.v[j]:
					for i in range(len(filetask.v[j])):
						self.v[j].append(filetask.v[j][i])
	
	def file_eval(self):
		pass
	
	def file_plot(self):
		pass

	def dir_plot(self):
		pass
	
	def run_bench(self):
		for mode in self.modes:
			self.params.mode = mode
			self.dir_exec()
			self.dir_eval()
			self.dir_plot()

	def dir_eval_print(self):
		self.dir_exec()
		self.dir_eval()
		self.pretty_print()


########NEW FILE########
__FILENAME__ = onset

from aubio.bench.node import *
from os.path import dirname,basename

def mmean(l):
	return sum(l)/max(float(len(l)),1)

def stdev(l):
	smean = 0
	if not len(l): return smean
	lmean = mmean(l)
	for i in l:
		smean += (i-lmean)**2
	smean *= 1. / len(l)
	return smean**.5

class benchonset(bench):

	""" list of values to store per file """
	valuenames = ['orig','missed','Tm','expc','bad','Td']
	""" list of lists to store per file """
	valuelists = ['l','labs']
	""" list of values to print per dir """
	printnames = [ 'mode', 'thres', 'dist', 'prec', 'recl',
		'GD', 'FP', 
		'Torig', 'Ttrue', 'Tfp',  'Tfn',  'TTm',   'TTd',
		'aTtrue', 'aTfp', 'aTfn', 'aTm',  'aTd',  
		'mean', 'smean',  'amean', 'samean']

	""" per dir """
	formats = {'mode': "%12s" , 'thres': "%5.4s", 
		'dist':  "%5.4s", 'prec': "%5.4s", 'recl':  "%5.4s",
		'Torig': "%5.4s", 'Ttrue': "%5.4s", 'Tfp':   "%5.4s", 'Tfn':   "%5.4s", 
		'TTm':    "%5.4s", 'TTd':    "%5.4s",
		'aTtrue':"%5.4s", 'aTfp':  "%5.4s", 'aTfn':  "%5.4s", 
		'aTm':   "%5.4s", 'aTd':   "%5.4s",
		'mean':  "%5.6s", 'smean': "%5.6s", 
		'amean':  "%5.6s", 'samean': "%5.6s", 
		"GD":     "%5.4s", "FP":     "%5.4s",
		"GDm":     "%5.4s", "FPd":     "%5.4s",
		"bufsize": "%5.4s", "hopsize": "%5.4s",
		"time":   "%5.4s"}

	def dir_eval(self):
		""" evaluate statistical data over the directory """
		v = self.v

		v['mode']      = self.params.onsetmode
		v['thres']     = self.params.threshold 
		v['bufsize']   = self.params.bufsize
		v['hopsize']   = self.params.hopsize
		v['silence']   = self.params.silence
		v['mintol']   = self.params.mintol

		v['Torig']     = sum(v['orig'])
		v['TTm']       = sum(v['Tm'])
		v['TTd']       = sum(v['Td'])
		v['Texpc']     = sum(v['expc'])
		v['Tbad']      = sum(v['bad'])
		v['Tmissed']   = sum(v['missed'])
		v['aTm']       = mmean(v['Tm'])
		v['aTd']       = mmean(v['Td'])

		v['mean']      = mmean(v['l'])
		v['smean']     = stdev(v['l'])

		v['amean']     = mmean(v['labs'])
		v['samean']    = stdev(v['labs'])
		
		# old type calculations
		# good detection rate 
		v['GD']  = 100.*(v['Torig']-v['Tmissed']-v['TTm'])/v['Torig']
		# false positive rate
		v['FP']  = 100.*(v['Tbad']+v['TTd'])/v['Torig']
		# good detection counting merged detections as good
		v['GDm'] = 100.*(v['Torig']-v['Tmissed'])/v['Torig'] 
		# false positives counting doubled as good
		v['FPd'] = 100.*v['Tbad']/v['Torig']                
		
		# mirex type annotations
		totaltrue = v['Texpc']-v['Tbad']-v['TTd']
		totalfp = v['Tbad']+v['TTd']
		totalfn = v['Tmissed']+v['TTm']
		self.v['Ttrue']     = totaltrue
		self.v['Tfp']       = totalfp
		self.v['Tfn']       = totalfn
		# average over the number of annotation files
		N = float(len(self.reslist))
		self.v['aTtrue']    = totaltrue/N
		self.v['aTfp']      = totalfp/N
		self.v['aTfn']      = totalfn/N

		# F-measure
		self.P = 100.*float(totaltrue)/max(totaltrue + totalfp,1)
		self.R = 100.*float(totaltrue)/max(totaltrue + totalfn,1)
		#if self.R < 0: self.R = 0
		self.F = 2.* self.P*self.R / max(float(self.P+self.R),1)
		self.v['dist']      = self.F
		self.v['prec']      = self.P
		self.v['recl']      = self.R


	"""
	Plot functions 
	"""

	def plotroc(self,d,plottitle=""):
		import Gnuplot, Gnuplot.funcutils
		gd = []
		fp = []
		for i in self.vlist:
			gd.append(i['GD']) 
			fp.append(i['FP']) 
		d.append(Gnuplot.Data(fp, gd, with_='linespoints', 
			title="%s %s" % (plottitle,i['mode']) ))

	def plotplotroc(self,d,outplot=0,extension='ps'):
		import Gnuplot, Gnuplot.funcutils
		from sys import exit
		g = Gnuplot.Gnuplot(debug=0, persist=1)
		if outplot:
			if   extension == 'ps':  ext, extension = '.ps' , 'postscript'
			elif extension == 'png': ext, extension = '.png', 'png'
			elif extension == 'svg': ext, extension = '.svg', 'svg'
			else: exit("ERR: unknown plot extension")
			g('set terminal %s' % extension)
			g('set output \'roc-%s%s\'' % (outplot,ext))
		xmax = 30 #max(fp)
		ymin = 50 
		g('set xrange [0:%f]' % xmax)
		g('set yrange [%f:100]' % ymin)
		# grid set
		g('set grid')
		g('set xtics 0,5,%f' % xmax)
		g('set ytics %f,5,100' % ymin)
		g('set key 27,65')
		#g('set format \"%g\"')
		g.title(basename(self.datadir))
		g.xlabel('false positives (%)')
		g.ylabel('correct detections (%)')
		g.plot(*d)

	def plotpr(self,d,plottitle=""):
		import Gnuplot, Gnuplot.funcutils
		x = []
		y = []
		for i in self.vlist:
			x.append(i['prec']) 
			y.append(i['recl']) 
		d.append(Gnuplot.Data(x, y, with_='linespoints', 
			title="%s %s" % (plottitle,i['mode']) ))

	def plotplotpr(self,d,outplot=0,extension='ps'):
		import Gnuplot, Gnuplot.funcutils
		from sys import exit
		g = Gnuplot.Gnuplot(debug=0, persist=1)
		if outplot:
			if   extension == 'ps':  ext, extension = '.ps' , 'postscript'
			elif extension == 'png': ext, extension = '.png', 'png'
			elif extension == 'svg': ext, extension = '.svg', 'svg'
			else: exit("ERR: unknown plot extension")
			g('set terminal %s' % extension)
			g('set output \'pr-%s%s\'' % (outplot,ext))
		g.title(basename(self.datadir))
		g.xlabel('Recall (%)')
		g.ylabel('Precision (%)')
		g.plot(*d)

	def plotfmeas(self,d,plottitle=""):
		import Gnuplot, Gnuplot.funcutils
		x,y = [],[]
		for i in self.vlist:
			x.append(i['thres']) 
			y.append(i['dist']) 
		d.append(Gnuplot.Data(x, y, with_='linespoints', 
			title="%s %s" % (plottitle,i['mode']) ))

	def plotplotfmeas(self,d,outplot="",extension='ps', title="F-measure"):
		import Gnuplot, Gnuplot.funcutils
		from sys import exit
		g = Gnuplot.Gnuplot(debug=0, persist=1)
		if outplot:
			if   extension == 'ps':  terminal = 'postscript'
			elif extension == 'png': terminal = 'png'
			elif extension == 'svg': terminal = 'svg'
			else: exit("ERR: unknown plot extension")
			g('set terminal %s' % terminal)
			g('set output \'fmeas-%s.%s\'' % (outplot,extension))
		g.xlabel('threshold \\delta')
		g.ylabel('F-measure (%)')
		g('set xrange [0:1.2]')
		g('set yrange [0:100]')
		g.title(basename(self.datadir))
		# grid set
		#g('set grid')
		#g('set xtics 0,5,%f' % xmax)
		#g('set ytics %f,5,100' % ymin)
		#g('set key 27,65')
		#g('set format \"%g\"')
		g.plot(*d)

	def plotfmeasvar(self,d,var,plottitle=""):
		import Gnuplot, Gnuplot.funcutils
		x,y = [],[]
		for i in self.vlist:
			x.append(i[var]) 
			y.append(i['dist']) 
		d.append(Gnuplot.Data(x, y, with_='linespoints', 
			title="%s %s" % (plottitle,i['mode']) ))
	
	def plotplotfmeasvar(self,d,var,outplot="",extension='ps', title="F-measure"):
		import Gnuplot, Gnuplot.funcutils
		from sys import exit
		g = Gnuplot.Gnuplot(debug=0, persist=1)
		if outplot:
			if   extension == 'ps':  terminal = 'postscript'
			elif extension == 'png': terminal = 'png'
			elif extension == 'svg': terminal = 'svg'
			else: exit("ERR: unknown plot extension")
			g('set terminal %s' % terminal)
			g('set output \'fmeas-%s.%s\'' % (outplot,extension))
		g.xlabel(var)
		g.ylabel('F-measure (%)')
		#g('set xrange [0:1.2]')
		g('set yrange [0:100]')
		g.title(basename(self.datadir))
		g.plot(*d)

	def plotdiffs(self,d,plottitle=""):
		import Gnuplot, Gnuplot.funcutils
		v = self.v
		l = v['l']
		mean   = v['mean']
		smean  = v['smean']
		amean  = v['amean']
		samean = v['samean']
		val = []
		per = [0] * 100
		for i in range(0,100):
			val.append(i*.001-.05)
			for j in l: 
				if abs(j-val[i]) <= 0.001:
					per[i] += 1
		total = v['Torig']
		for i in range(len(per)): per[i] /= total/100.

		d.append(Gnuplot.Data(val, per, with_='fsteps', 
			title="%s %s" % (plottitle,v['mode']) ))
		#d.append('mean=%f,sigma=%f,eps(x) title \"\"'% (mean,smean))
		#d.append('mean=%f,sigma=%f,eps(x) title \"\"'% (amean,samean))


	def plotplotdiffs(self,d,outplot=0,extension='ps'):
		import Gnuplot, Gnuplot.funcutils
		from sys import exit
		g = Gnuplot.Gnuplot(debug=0, persist=1)
		if outplot:
			if   extension == 'ps':  ext, extension = '.ps' , 'postscript'
			elif extension == 'png': ext, extension = '.png', 'png'
			elif extension == 'svg': ext, extension = '.svg', 'svg'
			else: exit("ERR: unknown plot extension")
			g('set terminal %s' % extension)
			g('set output \'diffhist-%s%s\'' % (outplot,ext))
		g('eps(x) = 1./(sigma*(2.*3.14159)**.5) * exp ( - ( x - mean ) ** 2. / ( 2. * sigma ** 2. ))')
		g.title(basename(self.datadir))
		g.xlabel('delay to hand-labelled onset (s)')
		g.ylabel('% number of correct detections / ms ')
		g('set xrange [-0.05:0.05]')
		g('set yrange [0:20]')
		g.plot(*d)


	def plothistcat(self,d,plottitle=""):
		import Gnuplot, Gnuplot.funcutils
		total = v['Torig']
		for i in range(len(per)): per[i] /= total/100.

		d.append(Gnuplot.Data(val, per, with_='fsteps', 
			title="%s %s" % (plottitle,v['mode']) ))
		#d.append('mean=%f,sigma=%f,eps(x) title \"\"'% (mean,smean))
		#d.append('mean=%f,sigma=%f,eps(x) title \"\"'% (amean,samean))


	def plotplothistcat(self,d,outplot=0,extension='ps'):
		import Gnuplot, Gnuplot.funcutils
		from sys import exit
		g = Gnuplot.Gnuplot(debug=0, persist=1)
		if outplot:
			if   extension == 'ps':  ext, extension = '.ps' , 'postscript'
			elif extension == 'png': ext, extension = '.png', 'png'
			elif extension == 'svg': ext, extension = '.svg', 'svg'
			else: exit("ERR: unknown plot extension")
			g('set terminal %s' % extension)
			g('set output \'diffhist-%s%s\'' % (outplot,ext))
		g('eps(x) = 1./(sigma*(2.*3.14159)**.5) * exp ( - ( x - mean ) ** 2. / ( 2. * sigma ** 2. ))')
		g.title(basename(self.datadir))
		g.xlabel('delay to hand-labelled onset (s)')
		g.ylabel('% number of correct detections / ms ')
		g('set xrange [-0.05:0.05]')
		g('set yrange [0:20]')
		g.plot(*d)



########NEW FILE########
__FILENAME__ = gnuplot
"""Copyright (C) 2004 Paul Brossier <piem@altern.org>
print aubio.__LICENSE__ for the terms of use
"""

__LICENSE__ = """\
  Copyright (C) 2004-2009 Paul Brossier <piem@aubio.org>

  This file is part of aubio.

  aubio is free software: you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  aubio is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with aubio.  If not, see <http://www.gnu.org/licenses/>.
"""


def audio_to_array(filename):
	import aubio.aubioclass
	from numpy import arange
	hopsize  = 2048
	filei    = aubio.aubioclass.sndfile(filename)
	framestep = 1/(filei.samplerate()+0.)
	channels = filei.channels()
	myvec    = aubio.aubioclass.fvec(hopsize,channels)
	data = []
	readsize = hopsize
	while (readsize==hopsize):
		readsize = filei.read(hopsize,myvec)
		#for i in range(channels):
		i = 0
		curpos = 0
		while (curpos < readsize):
			data.append(myvec.get(curpos,i))
			curpos+=1
	time = arange(len(data))*framestep
	return time,data

def plot_audio(filenames, g, options):
	todraw = len(filenames)
	xorig = 0.
	xratio = 1./todraw
	g('set multiplot;')
	while (len(filenames)):
		time,data = audio_to_array(filenames.pop(0))
		if todraw==1:
			if max(time) < 1.:
				time = [t*1000. for t in time]
				g.xlabel('Time (ms)')
			else:
				g.xlabel('Time (s)')
			g.ylabel('Amplitude')
		curplot = make_audio_plot(time,data)
		g('set size %f,%f;' % (options.xsize*xratio,options.ysize) )
		g('set origin %f,0.;' % (xorig) )
		g('set style data lines; \
			set yrange [-1.:1.]; \
			set xrange [0:%f]' % time[-1]) 
		g.plot(curplot)
		xorig += options.xsize*xratio 
	g('unset multiplot;')

def audio_to_spec(filename,minf = 0, maxf = 0, lowthres = -20., 
		bufsize= 8192, hopsize = 1024):
	from aubioclass import fvec,cvec,pvoc,sndfile
	from math import log10
	filei     = sndfile(filename)
	srate     = float(filei.samplerate())
	framestep = hopsize/srate
	freqstep  = srate/bufsize
	channels  = filei.channels()
	myvec = fvec(hopsize,channels)
	myfft = cvec(bufsize,channels)
	pv    = pvoc(bufsize,hopsize,channels)
	data,time,freq = [],[],[]

	if maxf == 0.: maxf = bufsize/2
	else: maxf = int(maxf/freqstep)
	if minf: minf = int(minf/freqstep)
	else: minf = 0 

	for f in range(minf,maxf):
		freq.append(f*freqstep)
	readsize = hopsize
	frameread = 0
	while (readsize==hopsize):
		readsize = filei.read(hopsize,myvec)
		pv.do(myvec,myfft)
		frame = []
		i = 0 #for i in range(channels):
		curpos = minf 
		while (curpos < maxf):
			frame.append(max(lowthres,20.*log10(myfft.get(curpos,i)**2+0.00001)))
			curpos+=1
		time.append(frameread*framestep)
		data.append(frame)
		frameread += 1
	# crop data if unfinished frames
	if len(data[-1]) != len(data[0]):
		data = data[0:-2]
		time = time[0:-2]
	# verify size consistency
	assert len(data) == len(time)
	assert len(data[0]) == len(freq)
	return data,time,freq

def plot_spec(filename, g, options):
	import Gnuplot
	data,time,freq = audio_to_spec(filename,
    minf=options.minf,maxf=options.maxf,
    bufsize=options.bufsize,hopsize=options.hopsize)
	xorig = 0.
	if max(time) < 1.:
		time = [t*1000. for t in time]
		g.xlabel('Time (ms)')
	else:
		g.xlabel('Time (s)')
	if options.xsize < 0.5 and not options.log and max(time) > 1.:
		freq = [f/1000. for f in freq]
		options.minf /= 1000.
		options.maxf /= 1000.
		g.ylabel('Frequency (kHz)')
	else:
		g.ylabel('Frequency (Hz)')
	g('set pm3d map')
	g('set palette rgbformulae -25,-24,-32')
	g('set cbtics 20')
	#g('set colorbox horizontal')
	g('set xrange [0.:%f]' % time[-1]) 
	if options.log:
		g('set log y')
		g('set yrange [%f:%f]' % (max(10,options.minf),options.maxf))
	else:
		g('set yrange [%f:%f]' % (options.minf,options.maxf))
	g.splot(Gnuplot.GridData(data,time,freq, binary=1))
	#xorig += 1./todraw

def downsample_audio(time,data,maxpoints=10000):
  """ resample audio data to last only maxpoints """
  from numpy import array, resize
  length = len(time)
  downsample = length/maxpoints
  if downsample == 0: downsample = 1
  x = resize(array(time),length)[0:-1:downsample]
  y = resize(array(data),length)[0:-1:downsample]
  return x,y

def make_audio_plot(time,data,maxpoints=10000):
  """ create gnuplot plot from an audio file """
  import Gnuplot, Gnuplot.funcutils
  x,y = downsample_audio(time,data,maxpoints=maxpoints)
  return Gnuplot.Data(x,y,with_='lines')

def make_audio_envelope(time,data,maxpoints=10000):
  """ create gnuplot plot from an audio file """
  from numpy import array
  import Gnuplot, Gnuplot.funcutils
  bufsize = 500
  x = [i.mean() for i in resize(array(time), (len(time)/bufsize,bufsize))] 
  y = [i.mean() for i in resize(array(data), (len(time)/bufsize,bufsize))] 
  x,y = downsample_audio(x,y,maxpoints=maxpoints)
  return Gnuplot.Data(x,y,with_='lines')

def gnuplot_addargs(parser):
  """ add common gnuplot argument to OptParser object """
  parser.add_option("-x","--xsize",
          action="store", dest="xsize", default=1., 
          type='float',help="define xsize for plot")
  parser.add_option("-y","--ysize",
          action="store", dest="ysize", default=1., 
          type='float',help="define ysize for plot")
  parser.add_option("--debug",
          action="store_true", dest="debug", default=False, 
          help="use gnuplot debug mode")
  parser.add_option("--persist",
          action="store_false", dest="persist", default=True, 
          help="do not use gnuplot persistant mode")
  parser.add_option("--lmargin",
          action="store", dest="lmargin", default=None, 
          type='int',help="define left margin for plot")
  parser.add_option("--rmargin",
          action="store", dest="rmargin", default=None, 
          type='int',help="define right margin for plot")
  parser.add_option("--bmargin",
          action="store", dest="bmargin", default=None, 
          type='int',help="define bottom margin for plot")
  parser.add_option("--tmargin",
          action="store", dest="tmargin", default=None, 
          type='int',help="define top margin for plot")
  parser.add_option("-O","--outplot",
          action="store", dest="outplot", default=None, 
          help="save plot to output.{ps,png}")

def gnuplot_create(outplot='',extension='', options=None):
  import Gnuplot
  if options:
    g = Gnuplot.Gnuplot(debug=options.debug, persist=options.persist)
  else:
    g = Gnuplot.Gnuplot(persist=1)
  if not extension or not outplot: return g
  if   extension == 'ps':  ext, extension = '.ps' , 'postscript'
  elif extension == 'eps': ext, extension = '.eps' , 'postscript enhanced'
  elif extension == 'epsc': ext, extension = '.eps' , 'postscript enhanced color'
  elif extension == 'png': ext, extension = '.png', 'png'
  elif extension == 'svg': ext, extension = '.svg', 'svg'
  else: exit("ERR: unknown plot extension")
  g('set terminal %s' % extension)
  if options and options.lmargin: g('set lmargin %i' % options.lmargin)
  if options and options.rmargin: g('set rmargin %i' % options.rmargin)
  if options and options.bmargin: g('set bmargin %i' % options.bmargin)
  if options and options.tmargin: g('set tmargin %i' % options.tmargin)
  if outplot != "stdout":
    g('set output \'%s%s\'' % (outplot,ext))
  if options: g('set size %f,%f' % (options.xsize, options.ysize))
  return g

########NEW FILE########
__FILENAME__ = median
"""Copyright (C) 2004 Paul Brossier <piem@altern.org>
print aubio.__LICENSE__ for the terms of use
"""

__LICENSE__ = """\
  Copyright (C) 2004-2009 Paul Brossier <piem@aubio.org>

  This file is part of aubio.

  aubio is free software: you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  aubio is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with aubio.  If not, see <http://www.gnu.org/licenses/>.
"""            

""" 
original author Tim Peters
modified by Paul Brossier <piem@altern.org>
inspired from http://www.ics.uci.edu/~eppstein/161/python/peters-selection.py
"""

def short_find(a, rank):
    """ find the rank-th value in sorted a """
    # copy to b before sorting
    b = a[:]
    b.sort()
    return b[rank - 1]

def percental(a, rank):
    """ Find the rank'th-smallest value in a, in worst-case linear time. """
    n = len(a)
    assert 1 <= rank <= n
    if n <= 7:
        return short_find(a, rank)

    ## Find median of median-of-7's.
    ##medians = [short_find(a[i : i+7], 4) for i in xrange(0, n-6, 7)]
    #median = find(medians, (len(medians) + 1) // 2)
    
    # modified to Find median
    median = short_find([a[0], a[-1], a[n//2]], 2)

    # Partition around the median.
    # a[:i]   <= median
    # a[j+1:] >= median
    i, j = 0, n-1
    while i <= j:
        while a[i] < median:
            i += 1
        while a[j] > median:
            j -= 1
        if i <= j:
            a[i], a[j] = a[j], a[i]
            i += 1
            j -= 1

    if rank <= i:
        return percental(a[:i], rank)
    else:
        return percental(a[i:], rank - i)


########NEW FILE########
__FILENAME__ = onsetcompare
"""Copyright (C) 2004 Paul Brossier <piem@altern.org>
print aubio.__LICENSE__ for the terms of use
"""

__LICENSE__ = """\
  Copyright (C) 2004-2009 Paul Brossier <piem@aubio.org>

  This file is part of aubio.

  aubio is free software: you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  aubio is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with aubio.  If not, see <http://www.gnu.org/licenses/>.
"""            

""" this file contains routines to compare two lists of onsets or notes.
it somewhat implements the Receiver Operating Statistic (ROC).
see http://en.wikipedia.org/wiki/Receiver_operating_characteristic
"""

def onset_roc(ltru, lexp, eps):
    """ compute differences between two lists 
          orig = hits + missed + merged 
          expc = hits + bad + doubled
        returns orig, missed, merged, expc, bad, doubled 
    """
    orig, expc = len(ltru), len(lexp)
    # if lexp is empty
    if expc == 0 : return orig,orig,0,0,0,0
    missed, bad, doubled, merged = 0, 0, 0, 0
    # find missed and doubled ones first
    for x in ltru:
        correspond = 0
        for y in lexp:
            if abs(x-y) <= eps:    correspond += 1
        if correspond == 0:        missed += 1
        elif correspond > 1:       doubled += correspond - 1 
    # then look for bad and merged ones
    for y in lexp:
        correspond = 0
        for x in ltru:
            if abs(x-y) <= eps:    correspond += 1
        if correspond == 0:        bad += 1
        elif correspond > 1:       merged += correspond - 1
    # check consistancy of the results
    assert ( orig - missed - merged == expc - bad - doubled)
    return orig, missed, merged, expc, bad, doubled 

def onset_diffs(ltru, lexp, eps):
    """ compute differences between two lists 
          orig = hits + missed + merged 
          expc = hits + bad + doubled
        returns orig, missed, merged, expc, bad, doubled 
    """
    orig, expc = len(ltru), len(lexp)
    # if lexp is empty
    l = []
    if expc == 0 : return l 
    # find missed and doubled ones first
    for x in ltru:
        correspond = 0
        for y in lexp:
            if abs(x-y) <= eps:    l.append(y-x) 
    # return list of diffs
    return l 

def onset_rocloc(ltru, lexp, eps):
    """ compute differences between two lists 
          orig = hits + missed + merged 
          expc = hits + bad + doubled
        returns orig, missed, merged, expc, bad, doubled 
    """
    orig, expc = len(ltru), len(lexp)
    l = []
    labs = []
    mean = 0
    # if lexp is empty
    if expc == 0 : return orig,orig,0,0,0,0,l,mean
    missed, bad, doubled, merged = 0, 0, 0, 0
    # find missed and doubled ones first
    for x in ltru:
        correspond = 0
        for y in lexp:
            if abs(x-y) <= eps:    correspond += 1
        if correspond == 0:        missed += 1
        elif correspond > 1:       doubled += correspond - 1 
    # then look for bad and merged ones
    for y in lexp:
        correspond = 0
        for x in ltru:
            if abs(x-y) <= eps:    
	    	correspond += 1
            	l.append(y-x) 
            	labs.append(abs(y-x))
        if correspond == 0:        bad += 1
        elif correspond > 1:       merged += correspond - 1
    # check consistancy of the results
    assert ( orig - missed - merged == expc - bad - doubled)
    return orig, missed, merged, expc, bad, doubled, l, labs

def notes_roc (la, lb, eps):
    from numpy import transpose, add, resize 
    """ creates a matrix of size len(la)*len(lb) then look for hit and miss
    in it within eps tolerance windows """
    gdn,fpw,fpg,fpa,fdo,fdp = 0,0,0,0,0,0
    m = len(la)
    n = len(lb)
    x =           resize(la[:][0],(n,m))
    y = transpose(resize(lb[:][0],(m,n)))
    teps =  (abs(x-y) <= eps[0]) 
    x =           resize(la[:][1],(n,m))
    y = transpose(resize(lb[:][1],(m,n)))
    tpitc = (abs(x-y) <= eps[1]) 
    res = teps * tpitc
    res = add.reduce(res,axis=0)
    for i in range(len(res)) :
        if res[i] > 1:
            gdn+=1
            fdo+=res[i]-1
        elif res [i] == 1:
            gdn+=1
    fpa = n - gdn - fpa
    return gdn,fpw,fpg,fpa,fdo,fdp

def load_onsets(filename) :
    """ load onsets targets / candidates files in arrays """
    l = [];
    
    f = open(filename,'ro')
    while 1:
        line = f.readline().split()
        if not line : break
        l.append(float(line[0]))
    
    return l

########NEW FILE########
__FILENAME__ = notes
__LICENSE__ = """\
  Copyright (C) 2004-2009 Paul Brossier <piem@aubio.org>

  This file is part of aubio.

  aubio is free software: you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  aubio is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with aubio.  If not, see <http://www.gnu.org/licenses/>.
"""

def plotnote(la,title=None) :
	if la[0,:].size() == 3:
	        d = plotnote_withends(la, plot_title=title)
	else: 
	    # scale data if in freq (for REF.txt files)
	    if max(la[:,1] > 128 ):
	        print "scaling frequency data to midi range"
	        la[:,1] /= 6.875
	        la[:,1] = log(la[:,1])/0.6931
	        la[:,1] *= 12
	        la[:,1] -= 3
	    d = plotnote_withoutends(la, plot_title=title)
	return d

def plotnote_multi(lalist,title=None,fileout=None) :
	d=list()
	for i in range(len(lalist)):
	    d.append(plotnote(lalist[i], title=title))
	return d
       

def plotnote_withends(la,plot_title=None) :
	from numpy import array
	import Gnuplot, Gnuplot.funcutils
	d=[]
	x_widths = array(la[:,1]-la[:,0])/2.
	d.append(Gnuplot.Data(
	        la[:,0]+x_widths,               # x centers
	        la[:,2],                        # y centers
	        x_widths,                       # x errors
	        __notesheight*ones(len(la)),    # y errors
	        title=plot_title,with_=('boxxyerrorbars fs 3')))
	return d


def plotnote_withoutends(la,plot_title=None) :
        """ bug: fails drawing last note """
	from numpy import array
	import Gnuplot, Gnuplot.funcutils
        d=[]
        x_widths = array(la[1:,0]-la[:-1,0])/2;
        d.append(Gnuplot.Data(
                la[:-1,0]+x_widths,             # x centers
                la[:-1,1],                      # y centers
                x_widths,                       # x errors
                __notesheight*ones(len(la)-1),  # y errors
                title=plot_title,with_=('boxxyerrorbars fs 3')))
        return d

def plotnote_do(d,fileout=None):
    import Gnuplot, Gnuplot.funcutils
    g = Gnuplot.Gnuplot(debug=1, persist=1)
    g.gnuplot('set style fill solid border 1; \
    set size ratio 1/6; \
    set boxwidth 0.9 relative; \
    set mxtics 2.5; \
    set mytics 2.5; \
    set xtics 5; \
    set ytics 1; \
    set grid xtics ytics mxtics mytics')

    g.xlabel('Time (s)')
    g.ylabel('Midi pitch')
    # do the plot
    #g.gnuplot('set multiplot')
    #for i in d:
    g.plot(d[0])
    #g.gnuplot('set nomultiplot') 
    if fileout != None:
        g.hardcopy(fileout, enhanced=1, color=0)


########NEW FILE########
__FILENAME__ = beat
from aubio.aubioclass import *
from onset import taskonset

class taskbeat(taskonset):
	def __init__(self,input,params=None,output=None):
		""" open the input file and initialize arguments 
		parameters should be set *before* calling this method.
		"""
		taskonset.__init__(self,input,output=None,params=params)
		self.btwinlen  = 512**2/self.params.hopsize
		self.btstep    = self.btwinlen/4
		self.btoutput  = fvec(self.btstep,self.channels)
		self.dfframe   = fvec(self.btwinlen,self.channels)
		self.bt	       = beattracking(self.btwinlen,self.channels)
		self.pos2      = 0
		self.old       = -1000

	def __call__(self):
		taskonset.__call__(self)
		#results = taskonset.__call__(self)
		# write to current file
		if self.pos2 == self.btstep - 1 : 
			self.bt.do(self.dfframe,self.btoutput)
			for i in range (self.btwinlen - self.btstep):
				self.dfframe.set(self.dfframe.get(i+self.btstep,0),i,0) 
			for i in range(self.btwinlen - self.btstep, self.btwinlen): 
				self.dfframe.set(0,i,0)
			self.pos2 = -1;
		self.pos2 += 1
		val = self.opick.pp.getval()
		#if not results: val = 0
		#else: val = results[1] 
		self.dfframe.set(val,self.btwinlen - self.btstep + self.pos2,0)
		i=0
		for i in range(1,int( self.btoutput.get(0,0) ) ):
			if self.pos2 == self.btoutput.get(i,0) and \
				aubio_silence_detection(self.myvec(),
					self.params.silence)!=1: 
				now = self.frameread-0
				period = (60 * self.params.samplerate) / ((now - self.old) * self.params.hopsize)
				self.old = now
				return now,period

	def eval(self,results,tol=0.20,tolcontext=0.25):
		obeats = self.gettruth()
		etime = [result[0] for result in results]
		otime = [obeat[0] for obeat in obeats]
		CML_tot, CML_max, CML_start, CML_end = 0,0,0,0
		AML_tot, AML_max, AML_start, AML_end = 0,0,0,0
		AMLd_tot, AMLd_max, AMLd_start, AMLd_end = 0,0,0,0
		AMLh_tot, AMLh_max, AMLh_start, AMLh_end = 0,0,0,0
		AMLo_tot, AMLo_max, AMLo_start, AMLo_end = 0,0,0,0
		# results iteration
		j = 1
		# for each annotation
		for i in range(2,len(otime)-2):
			if j+1 >= len(etime): break
			count = 0
			# look for next matching beat
			while otime[i] > etime[j] - (otime[i] - otime[i+1])*tol:
				if count > 0: 
					#print "spurious etime"
					if CML_end - CML_start > CML_max:
						CML_max = CML_end - CML_start
					CML_start, CML_end = j, j
					if AMLh_end - AMLh_start > AMLh_max:
						AMLh_max = AMLh_end - AMLh_start
					AMLh_start, AMLh_end = j, j
					if AMLd_end - AMLd_start > AMLd_max:
						AMLd_max = AMLd_end - AMLd_start
					AMLd_start, AMLd_end = j, j
					if AMLo_end - AMLo_start > AMLo_max:
						AMLo_max = AMLo_end - AMLo_start
					AMLo_start, AMLo_end = j, j
				j += 1
				count += 1
			if j+1 >= len(etime): break
			#print otime[i-1],etime[j-1]," ",otime[i],etime[j]," ",otime[i+1],etime[j+1] 
			prevtempo = (otime[i] - otime[i-1])
			nexttempo = (otime[i+1] - otime[i])

			current0  = (etime[j] > otime[i] - prevtempo*tol)
			current1  = (etime[j] < otime[i] + prevtempo*tol)

			# check correct tempo 
			prev0 = (etime[j-1] > otime[i-1] - prevtempo*tolcontext)
			prev1 = (etime[j-1] < otime[i-1] + prevtempo*tolcontext)
			next0 = (etime[j+1] > otime[i+1] - nexttempo*tolcontext)
			next1 = (etime[j+1] < otime[i+1] + nexttempo*tolcontext)

			# check for off beat
			prevoffb0 = (etime[j-1] > otime[i-1] - prevtempo/2 - prevtempo*tolcontext)
			prevoffb1 = (etime[j-1] < otime[i-1] - prevtempo/2 + prevtempo*tolcontext)
			nextoffb0 = (etime[j+1] > otime[i+1] - nexttempo/2 - nexttempo*tolcontext)
			nextoffb1 = (etime[j+1] < otime[i+1] - nexttempo/2 + nexttempo*tolcontext)

			# check half tempo 
			prevhalf0 = (etime[j-1] > otime[i-1] + prevtempo - prevtempo/2*tolcontext)
			prevhalf1 = (etime[j-1] < otime[i-1] + prevtempo + prevtempo/2*tolcontext)
			nexthalf0 = (etime[j+1] > otime[i+1] - nexttempo - nexttempo/2*tolcontext)
			nexthalf1 = (etime[j+1] < otime[i+1] - nexttempo + nexttempo/2*tolcontext)

			# check double tempo
			prevdoub0 = (etime[j-1] > otime[i-1] - prevtempo - prevtempo*2*tolcontext)
			prevdoub1 = (etime[j-1] < otime[i-1] - prevtempo + prevtempo*2*tolcontext)
			nextdoub0 = (etime[j+1] > otime[i+1] + nexttempo - nexttempo*2*tolcontext)
			nextdoub1 = (etime[j+1] < otime[i+1] + nexttempo + nexttempo*2*tolcontext)

			if current0 and current1 and prev0 and prev1 and next0 and next1: 
				#print "YES!"
				CML_end = j	
				CML_tot += 1
			else:
				if CML_end - CML_start > CML_max:
					CML_max = CML_end - CML_start
				CML_start, CML_end = j, j
			if current0 and current1 and prevhalf0 and prevhalf1 and nexthalf0 and nexthalf1: 
				AMLh_end = j
				AMLh_tot += 1
			else:
				if AMLh_end - AMLh_start > AMLh_max:
					AMLh_max = AMLh_end - AMLh_start
				AMLh_start, AMLh_end = j, j
			if current0 and current1 and prevdoub0 and prevdoub1 and nextdoub0 and nextdoub1: 
				AMLd_end = j
				AMLd_tot += 1
			else:
				if AMLd_end - AMLd_start > AMLd_max:
					AMLd_max = AMLd_end - AMLd_start
				AMLd_start, AMLd_end = j, j
			if current0 and current1 and prevoffb0 and prevoffb1 and nextoffb0 and nextoffb1: 
				AMLo_end = j
				AMLo_tot += 1
			else:
				if AMLo_end - AMLo_start > AMLo_max:
					AMLo_max = AMLo_end - AMLo_start
				AMLo_start, AMLo_end = j, j
			# look for next matching beat
			count = 0 
			while otime[i] > etime[j] - (otime[i] - otime[i+1])*tolcontext:
				j += 1
				if count > 0: 
					#print "spurious etime"
					start = j
				count += 1
		total = float(len(otime))
		CML_tot  /= total 
		AMLh_tot /= total 
		AMLd_tot /= total 
		AMLo_tot /= total 
		CML_cont  = CML_max/total
		AMLh_cont = AMLh_max/total
		AMLd_cont = AMLd_max/total
		AMLo_cont = AMLo_max/total
		return CML_cont, CML_tot, AMLh_cont, AMLh_tot, AMLd_cont, AMLd_tot, AMLo_cont, AMLo_tot

#		for i in allfreq:
#			freq.append(float(i) / 2. / N  * samplerate )
#			while freq[i]>freqs[j]:
#				j += 1
#			a0 = weight[j-1]
#			a1 = weight[j]
#			f0 = freqs[j-1]
#			f1 = freqs[j]
#			if f0!=0:
#				iweight.append((a1-a0)/(f1-f0)*freq[i] + (a0 - (a1 - a0)/(f1/f0 -1.)))
#			else:
#				iweight.append((a1-a0)/(f1-f0)*freq[i] + a0)
#			while freq[i]>freqs[j]:
#				j += 1
			
	def eval2(self,results,tol=0.2):
		truth = self.gettruth()
		obeats = [i[0] for i in truth] 
		ebeats = [i[0]*self.params.step for i in results] 
		NP = max(len(obeats), len(ebeats))
		N  = int(round(max(max(obeats), max(ebeats))*100.)+100)
		W  = int(round(tol*100.*60./median([i[1] for i in truth], len(truth)/2)))
		ofunc = [0 for i in range(N+W)]
		efunc = [0 for i in range(N+W)]
		for i in obeats: ofunc[int(round(i*100.)+W)] = 1
		for i in ebeats: efunc[int(round(i*100.)+W)] = 1
		assert len(obeats) == sum(ofunc)
		autocor = 0; m =0
		for m in range (-W, W):
			for i in range(W,N):
				autocor += ofunc[i] * efunc[i-m] 
		autocor /= float(NP)
		return autocor
	
	def evaluation(self,results,tol=0.2,start=5.):

		""" beat tracking evaluation function

		computes P-score of experimental results (ebeats)
		        against ground truth annotations (obeats) """

		from aubio.median import short_find as median
		truth = self.gettruth()
		ebeats = [i[0]*self.params.step for i in results] 
		obeats = [i[0] for i in truth] 

		# trim anything found before start
		while obeats[0] < start: obeats.pop(0)
		while ebeats[0] < start: ebeats.pop(0)
		# maximum number of beats found 
		NP = max(len(obeats), len(ebeats))
		# length of ofunc and efunc vector 
		N  = int(round(max(max(obeats), max(ebeats))*100.)+100)
		# compute W median of ground truth tempi 
		tempi = []
		for i in range(1,len(obeats)): tempi.append(obeats[i]-obeats[i-1])
		W  = int(round(tol*100.*median(tempi,len(tempi)/2)))
		# build ofunc and efunc functions, starting with W zeros  
		ofunc = [0 for i in range(N+W)]
		efunc = [0 for i in range(N+W)]
		for i in obeats: ofunc[int(round(i*100.)+W)] = 1
		for i in ebeats: efunc[int(round(i*100.)+W)] = 1
		# optional: make sure we didn't miss any beats  
		assert len(obeats) == sum(ofunc)
		assert len(ebeats) == sum(efunc)
		# compute auto correlation 
		autocor = 0; m =0
		for m in range (-W, W):
		  for i in range(W,N):
		    autocor += ofunc[i] * efunc[i-m] 
		autocor /= float(NP)
		return autocor

	def gettruth(self):
		import os.path
		from aubio.txtfile import read_datafile
		datafile = self.input.replace('.wav','.txt')
		if not os.path.isfile(datafile):
			print "no ground truth "
			return False,False
		else:
			values = read_datafile(datafile,depth=0)
			old = -1000
			for i in range(len(values)):
				now = values[i]
				period = 60 / (now - old)
				old = now
				values[i] = [now,period]
		return values
	

	def plot(self,oplots,results):
		import Gnuplot
		oplots.append(Gnuplot.Data(results,with_='linespoints',title="auto"))

	def plotplot(self,wplot,oplots,outplot=None,extension=None,xsize=1.,ysize=1.,spectro=False):
		import Gnuplot
		from aubio.gnuplot import gnuplot_create, audio_to_array, make_audio_plot
		import re
		# audio data
		#time,data = audio_to_array(self.input)
		#f = make_audio_plot(time,data)

		g = gnuplot_create(outplot=outplot, extension=extension)
		oplots = [Gnuplot.Data(self.gettruth(),with_='linespoints',title="orig")] + oplots
		g.plot(*oplots)

########NEW FILE########
__FILENAME__ = cut
from task import task
from aubio.aubioclass import *

class taskcut(task):
	def __init__(self,input,slicetimes,params=None,output=None):
		""" open the input file and initialize arguments 
		parameters should be set *before* calling this method.
		"""
		from os.path import basename,splitext
		task.__init__(self,input,output=None,params=params)
		self.soundoutbase, self.soundoutext = splitext(basename(self.input))
		self.newname   = "%s%s%09.5f%s%s" % (self.soundoutbase,".",
					self.frameread*self.params.step,".",self.soundoutext)
		self.fileo	= sndfile(self.newname,model=self.filei)
		self.myvec	= fvec(self.params.hopsize,self.channels)
		self.mycopy	= fvec(self.params.hopsize,self.channels)
		self.slicetimes = slicetimes 

	def __call__(self):
		task.__call__(self)
		# write to current file
		if len(self.slicetimes) and self.frameread >= self.slicetimes[0][0]:
			self.slicetimes.pop(0)
			# write up to 1st zero crossing
			zerocross = 0
			while ( abs( self.myvec.get(zerocross,0) ) > self.params.zerothres ):
				zerocross += 1
			writesize = self.fileo.write(zerocross,self.myvec)
			fromcross = 0
			while (zerocross < self.readsize):
				for i in range(self.channels):
					self.mycopy.set(self.myvec.get(zerocross,i),fromcross,i)
					fromcross += 1
					zerocross += 1
			del self.fileo
			self.fileo = sndfile("%s%s%09.5f%s%s" % (self.soundoutbase,".",
				self.frameread*self.params.step,".",self.soundoutext),model=self.filei)
			writesize = self.fileo.write(fromcross,self.mycopy)
		else:
			writesize = self.fileo.write(self.readsize,self.myvec)



########NEW FILE########
__FILENAME__ = notes

from aubio.task import task
from aubio.aubioclass import *

class tasknotes(task):
	def __init__(self,input,output=None,params=None):
		task.__init__(self,input,params=params)
		self.opick = onsetpick(self.params.bufsize,
			self.params.hopsize,
			self.channels,
			self.myvec,
			self.params.threshold,
			mode=self.params.onsetmode,
			dcthreshold=self.params.dcthreshold,
			derivate=self.params.derivate)
		self.pitchdet  = pitch(mode=self.params.pitchmode,
			bufsize=self.params.pbufsize,
			hopsize=self.params.phopsize,
			channels=self.channels,
			samplerate=self.srate,
			omode=self.params.omode)
		self.olist = [] 
		self.ofunc = []
		self.maxofunc = 0
		self.last = -1000
		self.oldifreq = 0
		if self.params.localmin:
			self.ovalist   = [0., 0., 0., 0., 0.]

	def __call__(self):
		from aubio.median import short_find
		task.__call__(self)
		isonset,val = self.opick.do(self.myvec)
		if (aubio_silence_detection(self.myvec(),self.params.silence)):
			isonset=0
			freq = -1.
		else:
			freq = self.pitchdet(self.myvec)
		minpitch = self.params.pitchmin
		maxpitch = self.params.pitchmax
		if maxpitch and freq > maxpitch : 
			freq = -1.
		elif minpitch and freq < minpitch :
			freq = -1.
		freq = aubio_freqtomidi(freq)
		if self.params.pitchsmooth:
			self.shortlist.append(freq)
			self.shortlist.pop(0)
			smoothfreq = short_find(self.shortlist,
				len(self.shortlist)/2)
			freq = smoothfreq
		now = self.frameread
		ifreq = int(round(freq))
		if self.oldifreq == ifreq:
			self.oldifreq = ifreq
		else:
			self.oldifreq = ifreq
			ifreq = 0 
		# take back delay
		if self.params.delay != 0.: now -= self.params.delay
		if now < 0 :
			now = 0
		if (isonset == 1):
			if self.params.mintol:
				# prune doubled 
				if (now - self.last) > self.params.mintol:
					self.last = now
					return now, 1, freq, ifreq
				else:
					return now, 0, freq, ifreq
			else:
				return now, 1, freq, ifreq 
		else:
			return now, 0, freq, ifreq


	def fprint(self,foo):
		print self.params.step*foo[0], foo[1], foo[2], foo[3]

	def compute_all(self):
		""" Compute data """
    		now, onset, freq, ifreq = [], [], [], []
		while(self.readsize==self.params.hopsize):
			n, o, f, i = self()
			now.append(n*self.params.step)
			onset.append(o)
			freq.append(f)
			ifreq.append(i)
			if self.params.verbose:
				self.fprint((n,o,f,i))
    		return now, onset, freq, ifreq 

	def plot(self,now,onset,freq,ifreq,oplots):
		import Gnuplot

		oplots.append(Gnuplot.Data(now,freq,with_='lines',
			title=self.params.pitchmode))
		oplots.append(Gnuplot.Data(now,ifreq,with_='lines',
			title=self.params.pitchmode))

		temponsets = []
		for i in onset:
			temponsets.append(i*1000)
		oplots.append(Gnuplot.Data(now,temponsets,with_='impulses',
			title=self.params.pitchmode))

	def plotplot(self,wplot,oplots,outplot=None,multiplot = 0):
		from aubio.gnuplot import gnuplot_init, audio_to_array, make_audio_plot
		import re
		import Gnuplot
		# audio data
		time,data = audio_to_array(self.input)
		f = make_audio_plot(time,data)

		# check if ground truth exists
		#timet,pitcht = self.gettruth()
		#if timet and pitcht:
		#	oplots = [Gnuplot.Data(timet,pitcht,with_='lines',
		#		title='ground truth')] + oplots

		t = Gnuplot.Data(0,0,with_='impulses') 

		g = gnuplot_init(outplot)
		g('set title \'%s\'' % (re.sub('.*/','',self.input)))
		g('set multiplot')
		# hack to align left axis
		g('set lmargin 15')
		# plot waveform and onsets
		g('set size 1,0.3')
		g('set origin 0,0.7')
		g('set xrange [0:%f]' % max(time)) 
		g('set yrange [-1:1]') 
		g.ylabel('amplitude')
		g.plot(f)
		g('unset title')
		# plot onset detection function


		g('set size 1,0.7')
		g('set origin 0,0')
		g('set xrange [0:%f]' % max(time))
		g('set yrange [20:100]')
		g('set key right top')
		g('set noclip one') 
		#g('set format x ""')
		#g('set log y')
		#g.xlabel('time (s)')
		g.ylabel('f0 (Hz)')
		if multiplot:
			for i in range(len(oplots)):
				# plot onset detection functions
				g('set size 1,%f' % (0.7/(len(oplots))))
				g('set origin 0,%f' % (float(i)*0.7/(len(oplots))))
				g('set xrange [0:%f]' % max(time))
				g.plot(oplots[i])
		else:
			g.plot(*oplots)
		#g('unset multiplot')


########NEW FILE########
__FILENAME__ = onset
from aubio.task.task import task
from aubio.aubioclass import *

class taskonset(task):
	def __init__(self,input,output=None,params=None):
		""" open the input file and initialize arguments 
		parameters should be set *before* calling this method.
		"""
		task.__init__(self,input,params=params)
		self.opick = onsetpick(self.params.bufsize,
			self.params.hopsize,
			self.myvec,
			self.params.threshold,
			mode=self.params.onsetmode,
			dcthreshold=self.params.dcthreshold,
			derivate=self.params.derivate)
		self.olist = [] 
		self.ofunc = []
		self.maxofunc = 0
		self.last = 0
		if self.params.localmin:
			self.ovalist   = [0., 0., 0., 0., 0.]

	def __call__(self):
		task.__call__(self)
		isonset,val = self.opick.do(self.myvec)
		if (aubio_silence_detection(self.myvec(),self.params.silence)):
			isonset=0
		if self.params.storefunc:
			self.ofunc.append(val)
		if self.params.localmin:
			if val > 0: self.ovalist.append(val)
			else: self.ovalist.append(0)
			self.ovalist.pop(0)
		if (isonset > 0.):
			if self.params.localmin:
				# find local minima before peak 
				i=len(self.ovalist)-1
				while self.ovalist[i-1] < self.ovalist[i] and i > 0:
					i -= 1
				now = (self.frameread+1-i)
			else:
				now = self.frameread
			# take back delay
			if self.params.delay != 0.: now -= self.params.delay
			if now < 0 :
				now = 0
			if self.params.mintol:
				# prune doubled 
				if (now - self.last) > self.params.mintol:
					self.last = now
					return now, val
			else:
				return now, val 


	def fprint(self,foo):
		print self.params.step*foo[0]

	def eval(self,inputdata,ftru,mode='roc',vmode=''):
		from aubio.txtfile import read_datafile 
		from aubio.onsetcompare import onset_roc, onset_diffs, onset_rocloc
		ltru = read_datafile(ftru,depth=0)
		lres = []
		for i in range(len(inputdata)): lres.append(inputdata[i][0]*self.params.step)
		if vmode=='verbose':
			print "Running with mode %s" % self.params.onsetmode, 
			print " and threshold %f" % self.params.threshold, 
			print " on file", self.input
		#print ltru; print lres
		if mode == 'local':
			l = onset_diffs(ltru,lres,self.params.tol)
			mean = 0
			for i in l: mean += i
			if len(l): mean = "%.3f" % (mean/len(l))
			else: mean = "?0"
			return l, mean
		elif mode == 'roc':
			self.orig, self.missed, self.merged, \
				self.expc, self.bad, self.doubled = \
				onset_roc(ltru,lres,self.params.tol)
		elif mode == 'rocloc':
			self.v = {}
			self.v['orig'], self.v['missed'], self.v['Tm'], \
				self.v['expc'], self.v['bad'], self.v['Td'], \
				self.v['l'], self.v['labs'] = \
				onset_rocloc(ltru,lres,self.params.tol)

	def plot(self,onsets,ofunc,wplot,oplots,nplot=False):
		import Gnuplot, Gnuplot.funcutils
		import aubio.txtfile
		import os.path
		from numpy import arange, array, ones
		from aubio.onsetcompare import onset_roc

		x1,y1,y1p = [],[],[]
		oplot = []
		if self.params.onsetmode in ('mkl','kl'): ofunc[0:10] = [0] * 10

		self.lenofunc = len(ofunc) 
		self.maxofunc = max(ofunc)
		# onset detection function 
		downtime = arange(len(ofunc))*self.params.step
		oplot.append(Gnuplot.Data(downtime,ofunc,with_='lines',title=self.params.onsetmode))

		# detected onsets
		if not nplot:
			for i in onsets:
				x1.append(i[0]*self.params.step)
				y1.append(self.maxofunc)
				y1p.append(-self.maxofunc)
			#x1 = array(onsets)*self.params.step
			#y1 = self.maxofunc*ones(len(onsets))
			if x1:
				oplot.append(Gnuplot.Data(x1,y1,with_='impulses'))
				wplot.append(Gnuplot.Data(x1,y1p,with_='impulses'))

		oplots.append((oplot,self.params.onsetmode,self.maxofunc))

		# check if ground truth datafile exists
		datafile = self.input.replace('.wav','.txt')
		if datafile == self.input: datafile = ""
		if not os.path.isfile(datafile):
			self.title = "" #"(no ground truth)"
		else:
			t_onsets = aubio.txtfile.read_datafile(datafile)
			x2 = array(t_onsets).resize(len(t_onsets))
			y2 = self.maxofunc*ones(len(t_onsets))
			wplot.append(Gnuplot.Data(x2,y2,with_='impulses'))
			
			tol = 0.050 

			orig, missed, merged, expc, bad, doubled = \
				onset_roc(x2,x1,tol)
			self.title = "GD %2.3f%% FP %2.3f%%" % \
				((100*float(orig-missed-merged)/(orig)),
				 (100*float(bad+doubled)/(orig)))


	def plotplot(self,wplot,oplots,outplot=None,extension=None,xsize=1.,ysize=1.,spectro=False):
		from aubio.gnuplot import gnuplot_create, audio_to_array, make_audio_plot, audio_to_spec
		import re
		# prepare the plot
		g = gnuplot_create(outplot=outplot, extension=extension)
		g('set title \'%s\'' % (re.sub('.*/','',self.input)))
		if spectro:
			g('set size %f,%f' % (xsize,1.3*ysize) )
		else:
			g('set size %f,%f' % (xsize,ysize) )
		g('set multiplot')

		# hack to align left axis
		g('set lmargin 3')
		g('set rmargin 6')

		if spectro:
			import Gnuplot
			minf = 50
			maxf = 500 
			data,time,freq = audio_to_spec(self.input,minf=minf,maxf=maxf)
			g('set size %f,%f' % (1.24*xsize , 0.34*ysize) )
			g('set origin %f,%f' % (-0.12,0.65*ysize))
			g('set xrange [0.:%f]' % time[-1]) 
			g('set yrange [%f:%f]' % (minf,maxf))
			g('set pm3d map')
			g('unset colorbox')
			g('set lmargin 0')
			g('set rmargin 0')
			g('set tmargin 0')
			g('set palette rgbformulae -25,-24,-32')
			g.xlabel('time (s)',offset=(0,1.))
			g.ylabel('freq (Hz)')
			g('set origin 0,%f' % (1.0*ysize) ) 
			g('set format x "%1.1f"')
			#if log:
			#	g('set yrange [%f:%f]' % (max(10,minf),maxf))
			#	g('set log y')
			g.splot(Gnuplot.GridData(data,time,freq, binary=1, title=''))
		else:
			# plot waveform and onsets
			time,data = audio_to_array(self.input)
			wplot = [make_audio_plot(time,data)] + wplot
			g('set origin 0,%f' % (0.7*ysize) )
			g('set size %f,%f' % (xsize,0.3*ysize))
			g('set format y "%1f"')
			g('set xrange [0:%f]' % max(time)) 
			g('set yrange [-1:1]') 
			g('set noytics')
			g('set y2tics -1,1')
			g.xlabel('time (s)',offset=(0,0.7))
			g.ylabel('amplitude')
			g.plot(*wplot)

		# default settings for next plots
		g('unset title')
		g('set format x ""')
		g('set format y "%3e"')
		g('set tmargin 0')
		g.xlabel('')

		N = len(oplots)
		y = 0.7*ysize # the vertical proportion of the plot taken by onset functions
		delta = 0.035 # the constant part of y taken by last plot label and data
		for i in range(N):
			# plot onset detection functions
			g('set size %f,%f' % ( xsize, (y-delta)/N))
			g('set origin 0,%f' % ((N-i-1)*(y-delta)/N + delta ))
			g('set nokey')
			g('set xrange [0:%f]' % (self.lenofunc*self.params.step))
			g('set yrange [0:%f]' % (1.1*oplots[i][2]))
			g('set y2tics ("0" 0, "%d" %d)' % (round(oplots[i][2]),round(oplots[i][2])))
			g.ylabel(oplots[i][1])
			if i == N-1:
				g('set size %f,%f' % ( xsize, (y-delta)/N + delta ) )
				g('set origin 0,0')
				g.xlabel('time (s)', offset=(0,0.7))
				g('set format x')
			g.plot(*oplots[i][0])

		g('unset multiplot')

########NEW FILE########
__FILENAME__ = params

class taskparams(object):
	""" default parameters for task classes """
	def __init__(self,input=None,output=None):
		self.silence = -90
		self.derivate = False
		self.localmin = False
		self.delay = 4.
		self.storefunc = False
		self.bufsize = 512
		self.hopsize = 256
		self.pbufsize = 2048
		self.phopsize =  512
		self.samplerate = 44100
		self.tol = 0.05
		self.mintol = 0.0
		self.step = float(self.hopsize)/float(self.samplerate)
		self.threshold = 0.1
		self.onsetmode = 'dual'
		self.pitchmode = 'yin'
		# best threshold for yin monophonic Mirex04 (depth of f0) 
		self.yinthresh = 0.15 
		# best thresh for yinfft monophonic Mirex04 (tradeoff sil/gd)
		# also best param for yinfft polyphonic Mirex04
		self.yinfftthresh = 0.85 
		self.pitchsmooth = 0
		self.pitchmin=20.
		self.pitchmax=20000.
		self.pitchdelay = -0.5
		self.dcthreshold = -1.
		self.omode = "freq"
		self.verbose   = False


########NEW FILE########
__FILENAME__ = pitch
from aubio.task.task import task
from aubio.task.silence import tasksilence
from aubio.aubioclass import *

class taskpitch(task):
	def __init__(self,input,params=None):
		task.__init__(self,input,params=params)
		self.shortlist = [0. for i in range(self.params.pitchsmooth)]
		if self.params.pitchmode == 'yin':
			tolerance = self.params.yinthresh
		elif self.params.pitchmode == 'yinfft':
			tolerance = self.params.yinfftthresh
		else:
			tolerance = 0.
		self.pitchdet	= pitch(mode=self.params.pitchmode,
			bufsize=self.params.bufsize,
			hopsize=self.params.hopsize,
			samplerate=self.srate,
			omode=self.params.omode,
			tolerance = tolerance)

	def __call__(self):
		from aubio.median import short_find
		task.__call__(self)
		if (aubio_silence_detection(self.myvec(),self.params.silence)==1):
			freq = -1.
		else:
			freq = self.pitchdet(self.myvec)
		minpitch = self.params.pitchmin
		maxpitch = self.params.pitchmax
		if maxpitch and freq > maxpitch : 
			freq = -1.
		elif minpitch and freq < minpitch :
			freq = -1.
		if self.params.pitchsmooth:
			self.shortlist.append(freq)
			self.shortlist.pop(0)
			smoothfreq = short_find(self.shortlist,
				len(self.shortlist)/2)
			return smoothfreq
		else:
			return freq

	def compute_all(self):
		""" Compute data """
    		mylist    = []
		while(self.readsize==self.params.hopsize):
			freq = self()
			mylist.append(freq)
			if self.params.verbose:
				self.fprint("%s\t%s" % (self.frameread*self.params.step,freq))
    		return mylist

	def gettruth(self):
		""" extract ground truth array in frequency """
		import os.path
		""" from wavfile.txt """
		datafile = self.input.replace('.wav','.txt')
		if datafile == self.input: datafile = ""
		""" from file.<midinote>.wav """
		# FIXME very weak check
		floatpit = self.input.split('.')[-2]
		if not os.path.isfile(datafile) and len(self.input.split('.')) < 3:
			print "no ground truth "
			return False,False
		elif floatpit:
			try:
				self.truth = float(floatpit)
				#print "ground truth found in filename:", self.truth
				tasksil = tasksilence(self.input,params=self.params)
				time,pitch =[],[]
				while(tasksil.readsize==tasksil.params.hopsize):
					tasksil()
					time.append(tasksil.params.step*(tasksil.frameread))
					if not tasksil.issilence:
						pitch.append(self.truth)
					else:
						pitch.append(-1.)
				return time,pitch
			except ValueError:
				# FIXME very weak check
				if not os.path.isfile(datafile):
					print "no ground truth found"
					return 0,0
				else:
					from aubio.txtfile import read_datafile
					values = read_datafile(datafile)
					time, pitch = [], []
					for i in range(len(values)):
						time.append(values[i][0])
						if values[i][1] == 0.0:
							pitch.append(-1.)
						else:
							pitch.append(aubio_freqtomidi(values[i][1]))
					return time,pitch

	def oldeval(self,results):
		def mmean(l):
			return sum(l)/max(float(len(l)),1)

		from aubio.median import percental 
		timet,pitcht = self.gettruth()
		res = []
		for i in results:
			#print i,self.truth
			if i <= 0: pass
			else: res.append(self.truth-i)
		if not res or len(res) < 3: 
			avg = self.truth; med = self.truth 
		else:
			avg = mmean(res) 
			med = percental(res,len(res)/2) 
		return self.truth, self.truth-med, self.truth-avg

	def eval(self,pitch,tol=0.5):
		timet,pitcht = self.gettruth()
		pitch = [aubio_freqtomidi(i) for i in pitch]
		for i in range(len(pitch)):
			if pitch[i] == "nan" or pitch[i] == -1:
				pitch[i] = -1
		time = [ (i+self.params.pitchdelay)*self.params.step for i in range(len(pitch)) ]
		#print len(timet),len(pitcht)
		#print len(time),len(pitch)
		if len(timet) != len(time):
			time = time[1:len(timet)+1]
			pitch = pitch[1:len(pitcht)+1]
			#pitcht = [aubio_freqtomidi(i) for i in pitcht]
			for i in range(len(pitcht)):
				if pitcht[i] == "nan" or pitcht[i] == "-inf" or pitcht[i] == -1:
					pitcht[i] = -1
		assert len(timet) == len(time)
		assert len(pitcht) == len(pitch)
		osil, esil, opit, epit, echr = 0, 0, 0, 0, 0
		for i in range(len(pitcht)):
			if pitcht[i] == -1: # currently silent
				osil += 1 # count a silence
				if pitch[i] <= 0. or pitch[i] == "nan": 
					esil += 1 # found a silence
			else:
				opit +=1
				if abs(pitcht[i] - pitch[i]) < tol:
					epit += 1
					echr += 1
				elif abs(pitcht[i] - pitch[i]) % 12. < tol:
					echr += 1
				#else:
				#	print timet[i], pitcht[i], time[i], pitch[i]
		#print "origsilence", "foundsilence", "origpitch", "foundpitch", "orig pitchroma", "found pitchchroma"
		#print 100.*esil/float(osil), 100.*epit/float(opit), 100.*echr/float(opit)
		return osil, esil, opit, epit, echr

	def plot(self,pitch,wplot,oplots,titles,outplot=None):
		import Gnuplot

		time = [ (i+self.params.pitchdelay)*self.params.step for i in range(len(pitch)) ]
		pitch = [aubio_freqtomidi(i) for i in pitch]
		oplots.append(Gnuplot.Data(time,pitch,with_='lines',
			title=self.params.pitchmode))
		titles.append(self.params.pitchmode)

			
	def plotplot(self,wplot,oplots,titles,outplot=None,extension=None,xsize=1.,ysize=1.,multiplot = 1, midi = 1, truth = 1):
		from aubio.gnuplot import gnuplot_create , audio_to_array, make_audio_plot
		import re
		import Gnuplot

		# check if ground truth exists
		if truth:
			timet,pitcht = self.gettruth()
			if timet and pitcht:
				oplots = [Gnuplot.Data(timet,pitcht,with_='lines',
					title='ground truth')] + oplots

		g = gnuplot_create(outplot=outplot, extension=extension)
		g('set title \'%s\'' % (re.sub('.*/','',self.input)))
		g('set size %f,%f' % (xsize,ysize) )
		g('set multiplot')
		# hack to align left axis
		g('set lmargin 4')
		g('set rmargin 4')
    # plot waveform
		time,data = audio_to_array(self.input)
		wplot = [make_audio_plot(time,data)]
		g('set origin 0,%f' % (0.7*ysize) )
		g('set size %f,%f' % (xsize,0.3*ysize))
		#g('set format y "%1f"')
		g('set xrange [0:%f]' % max(time)) 
		g('set yrange [-1:1]') 
		g('set noytics')
		g('set y2tics -1,1')
		g.xlabel('time (s)',offset=(0,0.7))
		g.ylabel('amplitude')
		g.plot(*wplot)

		# default settings for next plots
		g('unset title')
		g('set format x ""')
		g('set format y "%3e"')
		g('set tmargin 0')
		g.xlabel('')
		g('set noclip one') 

		if not midi:
			g('set log y')
			#g.xlabel('time (s)')
			g.ylabel('f0 (Hz)')
			g('set yrange [100:%f]' % self.params.pitchmax) 
		else: 
			g.ylabel('midi')
			g('set yrange [%f:%f]' % (aubio_freqtomidi(self.params.pitchmin), aubio_freqtomidi(self.params.pitchmax)))
			g('set y2tics %f,%f' % (round(aubio_freqtomidi(self.params.pitchmin)+.5),12))
		
		if multiplot:
			N = len(oplots)
			y = 0.7*ysize # the vertical proportion of the plot taken by onset functions
			delta = 0.035 # the constant part of y taken by last plot label and data
			for i in range(N):
				# plot pitch detection functions
				g('set size %f,%f' % ( xsize, (y-delta)/N))
				g('set origin 0,%f' % ((N-i-1)*(y-delta)/N + delta ))
				g('set nokey')
				g('set xrange [0:%f]' % max(time))
				g.ylabel(titles[i])
				if i == N-1:
					g('set size %f,%f' % (xsize, (y-delta)/N + delta ) )
					g('set origin 0,0')
					g.xlabel('time (s)', offset=(0,0.7))
					g('set format x')
				g.plot(oplots[i])
		else:
			g('set key right top')
			g.plot(*oplots)
		g('unset multiplot')


########NEW FILE########
__FILENAME__ = silence
from aubio.task.task import task
from aubio.aubioclass import *

class tasksilence(task):
	wassilence = 1
	issilence  = 1
	def __call__(self):
		task.__call__(self)
		if (aubio_silence_detection(self.myvec(),self.params.silence)==1):
			if self.wassilence == 1: self.issilence = 1
			else: self.issilence = 2
			self.wassilence = 1
		else: 
			if self.wassilence <= 0: self.issilence = 0
			else: self.issilence = -1 
			self.wassilence = 0
		if self.issilence == -1:
			return max(self.frameread-self.params.delay,0.), -1
		elif self.issilence == 2:
			return max(self.frameread+self.params.delay,0.), 2 

	def fprint(self,foo):
		print self.params.step*foo[0],
		if foo[1] == 2: print "OFF"
		else: print "ON"




########NEW FILE########
__FILENAME__ = task
from aubio.aubioclass import * 
from params import taskparams

class task(taskparams):
	""" default template class to apply tasks on a stream """
	def __init__(self,input,output=None,params=None):
		""" open the input file and initialize default argument 
		parameters should be set *before* calling this method.
		"""
		import time
		self.tic = time.time()
		if params == None: self.params = taskparams()
		else: self.params = params
		self.frameread = 0
		self.readsize  = self.params.hopsize
		self.input     = input
		self.filei     = sndfile(self.input)
		self.srate     = self.filei.samplerate()
		self.params.step = float(self.params.hopsize)/float(self.srate)
		self.myvec     = fvec(self.params.hopsize)
		self.output    = output

	def __call__(self):
		self.readsize = self.filei.read(self.params.hopsize,self.myvec)
		self.frameread += 1
		
	def compute_all(self):
		""" Compute data """
    		mylist    = []
		while(self.readsize==self.params.hopsize):
			tmp = self()
			if tmp: 
				mylist.append(tmp)
				if self.params.verbose:
					self.fprint(tmp)
    		return mylist
	
	def fprint(self,foo):
		print foo

	def eval(self,results):
		""" Eval data """
		pass

	def plot(self):
		""" Plot data """
		pass

	def time(self):
		import time
		#print "CPU time is now %f seconds," % time.clock(),
		#print "task execution took %f seconds" % (time.time() - self.tic)
		return time.time() - self.tic

########NEW FILE########
__FILENAME__ = txtfile
"""Copyright (C) 2004 Paul Brossier <piem@altern.org>
print aubio.__LICENSE__ for the terms of use
"""

__LICENSE__ = """\
  Copyright (C) 2004-2009 Paul Brossier <piem@aubio.org>

  This file is part of aubio.

  aubio is free software: you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  aubio is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with aubio.  If not, see <http://www.gnu.org/licenses/>.
"""            

def read_datafile(filename,depth=-1):
    """read list data from a text file (columns of float)"""
    if filename == '--' or filename == '-':
        import sys
        fres = sys.stdin
    else:
        fres = open(filename,'ro')
    l = []
    while 1:
        tmp = fres.readline()
        if not tmp : break
        else: tmp = tmp.split()
        if depth > 0:
            for i in range(min(depth,len(tmp))):
                tmp[i] = float(tmp[i])
            l.append(tmp)
        elif depth == 0:
            l.append(float(tmp[0]))
        else:
            for i in range(len(tmp)):
                tmp[i] = float(tmp[i])
            l.append(tmp)
    return l


########NEW FILE########
__FILENAME__ = browser
 #
 # Copyright 2004 Apache Software Foundation 
 # 
 # Licensed under the Apache License, Version 2.0 (the "License"); you
 # may not use this file except in compliance with the License.  You
 # may obtain a copy of the License at
 #
 #      http://www.apache.org/licenses/LICENSE-2.0
 #
 # Unless required by applicable law or agreed to in writing, software
 # distributed under the License is distributed on an "AS IS" BASIS,
 # WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
 # implied.  See the License for the specific language governing
 # permissions and limitations under the License.
 #
 # Originally developed by Gregory Trubetskoy.
 #
 # $Id: publisher.py,v 1.36 2004/02/16 19:47:27 grisha Exp $

"""
  This handler is conceputally similar to Zope's ZPublisher, except
  that it:

  1. Is written specifically for mod_python and is therefore much faster
  2. Does not require objects to have a documentation string
  3. Passes all arguments as simply string
  4. Does not try to match Python errors to HTTP errors
  5. Does not give special meaning to '.' and '..'.

  This is a modified version of mod_python.publisher.handler Only the first
  directory argument is matched, the rest is left for path_info. A default
  one must be provided.

"""

from mod_python import apache
from mod_python import util
from mod_python.publisher import resolve_object,process_auth,imp_suffixes

import sys
import os
import re

from types import *

def configure_handler(req,default):

    req.allow_methods(["GET", "POST"])
    if req.method not in ["GET", "POST"]:
        raise apache.SERVER_RETURN, apache.HTTP_METHOD_NOT_ALLOWED

    func_path = ""
    if req.path_info:
        func_path = req.path_info[1:] # skip first /
        #func_path = func_path.replace("/", ".")
        #if func_path[-1:] == ".":
        #    func_path = func_path[:-1] 
        # changed: only keep the first directory
        func_path = re.sub('/.*','',func_path)

    # default to 'index' if no path_info was given
    if not func_path:
        func_path = "index"

    # if any part of the path begins with "_", abort
    if func_path[0] == '_' or func_path.count("._"):
        raise apache.SERVER_RETURN, apache.HTTP_NOT_FOUND

    ## import the script
    path, module_name =  os.path.split(req.filename)
    if not module_name:
        module_name = "index"

    # get rid of the suffix
    #   explanation: Suffixes that will get stripped off
    #   are those that were specified as an argument to the
    #   AddHandler directive. Everything else will be considered
    #   a package.module rather than module.suffix
    exts = req.get_addhandler_exts()
    if not exts:
        # this is SetHandler, make an exception for Python suffixes
        exts = imp_suffixes
    if req.extension:  # this exists if we're running in a | .ext handler
        exts += req.extension[1:] 
    if exts:
        suffixes = exts.strip().split()
        exp = "\\." + "$|\\.".join(suffixes)
        suff_matcher = re.compile(exp) # python caches these, so its fast
        module_name = suff_matcher.sub("", module_name)

    # import module (or reload if needed)
    # the [path] argument tells import_module not to allow modules whose
    # full path is not in [path] or below.
    config = req.get_config()
    autoreload=int(config.get("PythonAutoReload", 1))
    log=int(config.get("PythonDebug", 0))
    try:
        module = apache.import_module(module_name,
                                      autoreload=autoreload,
                                      log=log,
                                      path=[path])
    except ImportError:
        et, ev, etb = sys.exc_info()
        # try again, using default module, perhaps this is a
        # /directory/function (as opposed to /directory/module/function)
        func_path = module_name
        module_name = "index"
        try:
            module = apache.import_module(module_name,
                                          autoreload=autoreload,
                                          log=log,
                                          path=[path])
        except ImportError:
            # raise the original exception
            raise et, ev, etb
        
    # does it have an __auth__?
    realm, user, passwd = process_auth(req, module)

    # resolve the object ('traverse')
    try:
        object = resolve_object(req, module, func_path, realm, user, passwd)
    except AttributeError:
        # changed, return the default path instead
        #raise apache.SERVER_RETURN, apache.HTTP_NOT_FOUND
        object = default
    # not callable, a class or an unbound method
    if (not callable(object) or 
        type(object) is ClassType or
        (hasattr(object, 'im_self') and not object.im_self)):

        result = str(object)
        
    else:
        # callable, (but not a class or unbound method)
        
        # process input, if any
        req.form = util.FieldStorage(req, keep_blank_values=1)
        
        result = util.apply_fs_data(object, req.form, req=req)

    if result or req.bytes_sent > 0 or req.next:
        
        if result is None:
            result = ""
        else:
            result = str(result)

        # unless content_type was manually set, we will attempt
        # to guess it
        if not req._content_type_set:
            # make an attempt to guess content-type
            if result[:100].strip()[:6].lower() == '<html>' \
               or result.find('</') > 0:
                req.content_type = 'text/html'
            else:
                req.content_type = 'text/plain'

        if req.method != "HEAD":
            req.write(result)
        else:
            req.write("")
        return apache.OK
    else:
        req.log_error("mod_python.publisher: %s returned nothing." % `object`)
        return apache.HTTP_INTERNAL_SERVER_ERROR


########NEW FILE########
__FILENAME__ = html
from aubio.bench.node import *

def parse_args(req):
    req.basehref = BASEHREF
    req.datadir = DATADIR
    if req.path_info: path_info = req.path_info
    else: path_info = '/'
    location = re.sub('^/show_[a-z0-9]*/','',path_info)
    location = re.sub('^/play_[a-z0-9]*/','',location)
    location = re.sub('^/index/','',location)
    location = re.sub('^/','',location)
    location = re.sub('/$','',location)
    datapath = "%s/%s" % (DATADIR,location)
    respath  = "%s/%s" % (DATADIR,location)
    last     = re.sub('/$','',location)
    last     = last.split('/')[-1]
    first    = path_info.split('/')[1]
    # store some of this in the mp_request
    req.location, req.datapath, req.respath = location, datapath, respath
    req.first, req.last = first, last

    if location:
        if not (os.path.isfile(datapath) or 
		os.path.isdir(datapath) or 
		location in ['feedback','email']):
		# the path was not understood
		from mod_python import apache
		req.write("<html> path not found %s</html>" % (datapath))
		raise apache.SERVER_RETURN, apache.OK
		#from mod_python import apache
		#raise apache.SERVER_RETURN, apache.HTTP_NOT_FOUND

def navigation(req):
    """ main html navigation header """
    from mod_python import psp
    req.content_type = "text/html"
    parse_args(req)
    datapath = req.datapath
    location = req.location

    # deal with session
    if req.sess.is_new():
	    msg = "<b>Welcome %s</b><br>" % req.sess['login']
    else:
	    msg = "<b>Welcome back %s</b><br>" % req.sess['login']

    # start writing
    tmpl = psp.PSP(req, filename='header.tmpl')
    tmpl.run(vars = { 'title': "aubioweb / %s / %s" % (req.first,location),
    		'basehref': '/~piem/',
		'message': msg,
    		'action': req.first})

    req.write("<h2>Content of ")
    print_link(req,"","/")
    y = location.split('/')
    for i in range(len(y)-1): 
    	print_link(req,"/".join(y[:i+1]),y[i])
	req.write(" / ")
    req.write("%s</h2>\n" % y[-1])

    a = {'show_info' : 'info',
    	 'show_sound': 'waveform',
    	 'show_onset': 'onset',
    	 'index'     : 'index',
	 'show_pitch': 'pitch',
	 'play_m3u': 'stream (m3u/ogg)',
	 'play_ogg': 'save (ogg)',
	 'play_wav': 'save (wav)',
	 }

    # print task lists (only remaining tasks)
    print_link(req,re.sub('%s.*'%req.last,'',location),"go up")
    akeys = a.keys(); akeys.sort();
    curkey = req.first
    for akey in akeys: 
        if akey != curkey:
    		req.write(":: ")
		print_link(req,"/".join((akey,location)),a[akey])
	else:
    		req.write(":: ")
		req.write("<b>%s</b>" % a[akey])
    req.write("<br>")

    # list the content of the directories
    listdir,listfiles = [],[]
    if os.path.isdir(datapath):
        listfiles = list_snd_files(datapath)
    	listdir = list_dirs(datapath)
	listdir.pop(0) # kick the current dir
    elif os.path.isfile(datapath):
        listfiles = [datapath]
	listdir = [re.sub(req.last,'',location)]

    link_list(req,listdir,title="Subdirectories")
    link_list(req,listfiles,title="Files")

def footer(req):
    """ html navigation footer """
    from mod_python import psp
    tmpl = psp.PSP(req, filename='footer.tmpl')
    tmpl.run(vars = { 'time': -req.mtime+req.request_time })

def apply_on_data(req, func,**keywords):
    # bug: hardcoded snd file filter
    act_on_data(func,req.datapath,req.respath,
    	filter="f  -maxdepth 1 -name '*.wav' -o -name '*.aif'",**keywords)

def print_link(req,target,name,basehref=BASEHREF):
    req.write("<a href='%s/%s'>%s</a>\n" % (basehref,target,name))

def print_img(req,target,name='',basehref=BASEHREF):
    if name == '': name = target
    req.write("<img src='%s/%s' alt='%s' title='%s'>\n" % (basehref,target,name,name))

def link_list(req,targetlist,basehref=BASEHREF,title=None):
    if len(targetlist) > 1:
        if title: req.write("<h3>%s</h3>"%title)
        req.write('<ul>')
        for i in targetlist:
            s = re.split('%s/'%DATADIR,i,maxsplit=1)[1]
            if s: 
        	req.write('<li>')
	    	print_link(req,s,s)
        	req.write('</li>')
        req.write('</ul>')

def print_list(req,list):
    req.write("<pre>\n")
    for i in list: req.write("%s\n" % i)
    req.write("</pre>\n")

def print_command(req,command):
    req.write("<h4>%s</h4>\n" % re.sub('%%','%',command))
    def print_runcommand(input,output):
        cmd = re.sub('(%)?%i','%s' % input, command)
        cmd = re.sub('(%)?%o','%s' % output, cmd)
        print_list(req,runcommand(cmd))
    apply_on_data(req,print_runcommand)

def datapath_to_location(input):
    location = re.sub(DATADIR,'',input)
    return re.sub('^/*','',location)

## drawing hacks
def draw_func(req,func):
    import re
    req.content_type = "image/png"
    # build location (strip the func_path, add DATADIR)
    location = re.sub('^/draw_[a-z]*/','%s/'%DATADIR,req.path_info)
    location = re.sub('.png$','',location)
    if not os.path.isfile(location):
	from mod_python import apache
	raise apache.SERVER_RETURN, apache.HTTP_NOT_FOUND
    # replace location in func
    cmd = re.sub('(%)?%i','%s' % location, func)
    # add PYTHONPATH at the beginning, 
    cmd = "%s%s 2> /dev/null" % (PYTHONPATH,cmd)
    for each in runcommand(cmd):
	req.write("%s\n"%each)

def show_task(req,task):
    def show_task_file(input,output,task):
        location = datapath_to_location(input)
        print_img(req,"draw_%s/%s" % (task,location))
    navigation(req)
    req.write("<h3>%s</h3>\n" % task)
    apply_on_data(req,show_task_file,task=task)
    footer(req)

## waveform_foo
def draw_sound(req):
    draw_func(req,"aubioplot-audio %%i stdout 2> /dev/null")

def show_sound(req):
    show_task(req,"sound")

## pitch foo
def draw_pitch(req,threshold='0.3'):
    draw_func(req,"aubiopitch -i %%i -p -m schmitt,yin,fcomb,mcomb -t %s -O stdout" % threshold)

def show_pitch(req):
    show_task(req,"pitch")

## onset foo
def draw_onset(req,threshold='0.3'):
    draw_func(req,"aubiocut -i %%i -p -m complex -t %s -O stdout" % threshold)

def show_onset(req,threshold='0.3',details=''):
    def onset_file(input,output):
        location = datapath_to_location(input)
        print_img(req,"draw_onset/%s?threshold=%s"%(location,threshold))
        print_link(req,"?threshold=%s" % (float(threshold)-0.1),"-")
        req.write("%s\n" % threshold)
        print_link(req,"?threshold=%s" % (float(threshold)+0.1),"+")
	# bug: hardcoded sndfile extension 
        anote = re.sub('\.wav$','.txt',input)
	if anote == input: anote = ""
        res = get_extract(input,threshold)
        if os.path.isfile(anote):
            tru = get_anote(anote)
            print_list(req,get_results(tru,res,0.05))
        else:
            req.write("no ground truth found<br>\n")
        if details:
            req.write("<h4>Extraction</h4>\n")
            print_list(req,res)
        else:
            req.write("<a href='%s/show_onset/%s?details=yes&amp;threshold=%s'>details</a><br>\n" %
            	(req.basehref,location,threshold))
        if details and os.path.isfile(anote):
            req.write("<h4>Computed differences</h4>\n")
            ldiffs = get_diffs(tru,res,0.05)
            print_list(req,ldiffs)
            req.write("<h4>Annotations</h4>\n")
            print_list(req,tru)
    navigation(req)
    req.write("<h3>Onset</h3>\n")
    apply_on_data(req,onset_file)
    footer(req)

def get_anote(anote):
    import aubio.onsetcompare
    # FIXME: should import with txtfile.read_datafile
    return aubio.onsetcompare.load_onsets(anote)

def get_diffs(anote,extract,tol):
    import aubio.onsetcompare
    return aubio.onsetcompare.onset_diffs(anote,extract,tol)

def get_extract(datapath,threshold='0.3'):
    cmd = "%saubiocut -v -m complex -t %s -i %s" % (PYTHONPATH,threshold,datapath)
    lo = runcommand(cmd)
    for i in range(len(lo)): lo[i] = float(lo[i])
    return lo

def get_results(anote,extract,tol):
    import aubio.onsetcompare
    orig, missed, merged, expc, bad, doubled = aubio.onsetcompare.onset_roc(anote,extract,tol)
    s =("GD %2.8f\t"        % (100*float(orig-missed-merged)/(orig)),
        "FP %2.8f\t"        % (100*float(bad+doubled)/(orig))       , 
        "GD-merged %2.8f\t" % (100*float(orig-missed)/(orig))       , 
        "FP-pruned %2.8f\t" % (100*float(bad)/(orig))		    )
    return s

# play m3u foo
def play_m3u(req):
    def show_task_file(input,output,task):
        location = datapath_to_location(input)
        req.write("http://%s%s/play_ogg/%s\n" % (HOSTNAME,BASEHREF,re.sub("play_m3u",task,location)))
    req.content_type = "audio/mpegurl"
    parse_args(req)
    apply_on_data(req,show_task_file,task="play_ogg")

# play wav foo
def play_wav(req):
    req.content_type = "audio/x-wav"
    func = "cat %%i"
    # build location (strip the func_path, add DATADIR)
    location = re.sub('^/play_wav/','%s/'%DATADIR,req.path_info)
    if not os.path.isfile(location):
	from mod_python import apache
	raise apache.SERVER_RETURN, apache.HTTP_NOT_FOUND
    # replace location in func
    cmd = re.sub('(%)?%i','%s' % location, func)
    # add PYTHONPATH at the beginning, 
    cmd = "%s 2> /dev/null" % cmd
    for each in runcommand(cmd):
	req.write("%s\n"%each)

# play ogg foo
def play_ogg(req):
    req.content_type = "application/ogg"
    func = "oggenc -o - %%i"
    # build location (strip the func_path, add DATADIR)
    location = re.sub('^/play_ogg/','%s/'%DATADIR,req.path_info)
    location = re.sub('.ogg$','',location)
    if not os.path.isfile(location):
	from mod_python import apache
	raise apache.SERVER_RETURN, apache.HTTP_NOT_FOUND
    # replace location in func
    cmd = re.sub('(%)?%i','%s' % location, func)
    # add PYTHONPATH at the beginning, 
    cmd = "%s 2> /dev/null" % cmd
    for each in runcommand(cmd):
	req.write("%s\n"%each)

########NEW FILE########
__FILENAME__ = aubioinput
#! /usr/bin/python

import pygst
pygst.require('0.10')
import gst
import gobject
gobject.threads_init ()

def gst_buffer_to_numpy_array(buffer, chan):
    import numpy
    samples = numpy.frombuffer(buffer.data, dtype=numpy.float32) 
    if chan == 1:
        return samples.T
    else:
        samples.resize([len(samples)/chan, chan])
        return samples.T

class AubioSink(gst.BaseSink):
    _caps = gst.caps_from_string('audio/x-raw-float, \
                    rate=[ 1, 2147483647 ], \
                    channels=[ 1, 2147483647 ], \
                    endianness={ 1234, 4321 }, \
                    width=32')

    __gsttemplates__ = ( 
            gst.PadTemplate ("sink",
                gst.PAD_SINK,
                gst.PAD_ALWAYS,
                _caps),
            )

    def __init__(self, name, process):
        self.__gobject_init__()
        self.set_name(name)
        self.process = process
        self.adapter = gst.Adapter()
        self.set_property('sync', False)
        self.pos = 0

    def set_property(self, name, value): 
        if name == 'hopsize':
            # blocksize is in byte, convert from hopsize 
            from struct import calcsize
            self.set_property('blocksize', value * calcsize('f'))
        else:
            super(gst.BaseSink, self).set_property(name, value)

    def do_render(self, buffer):
        blocksize = self.get_property('blocksize')
        caps = buffer.get_caps()
        chan = caps[0]['channels']
        self.adapter.push(buffer)
        while self.adapter.available() >= blocksize:
            block = self.adapter.take_buffer(blocksize)
            v = gst_buffer_to_numpy_array(block, chan)
            if self.process:
                self.process(v, self.pos)
            self.pos += 1
        remaining = self.adapter.available()
        if remaining < blocksize and remaining > 0:
            block = self.adapter.take_buffer(remaining)
            v = gst_buffer_to_numpy_array(block, chan)
            if self.process:
                self.process(v, self.pos)
            self.pos += 1
        return gst.FLOW_OK

gobject.type_register(AubioSink)

class aubioinput(gst.Bin):

    ret = 0

    def __init__(self, uri, process = None, hopsize = 512,
            caps = None):
        if uri.startswith('/'):
            from urllib import quote
            uri = 'file://'+quote(uri)
        src = gst.element_factory_make('uridecodebin')
        src.set_property('uri', uri)
        src.connect('pad-added', self.source_pad_added_cb)
        conv = gst.element_factory_make('audioconvert')
        self.conv = conv
        rsmpl = gst.element_factory_make('audioresample')
        capsfilter = gst.element_factory_make('capsfilter')
        if caps:
            capsfilter.set_property('caps', gst.caps_from_string(caps))
        sink = AubioSink("AubioSink", process = process)
        sink.set_property('hopsize', hopsize) # * calcsize('f'))

        self.pipeline = gst.Pipeline()

        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message', self.on_eos)

        self.apad = conv.get_pad('sink')

        self.pipeline.add(src, conv, rsmpl, capsfilter, sink)

        gst.element_link_many(conv, rsmpl, capsfilter, sink)

        self.mainloop = gobject.MainLoop()
        self.pipeline.set_state(gst.STATE_PLAYING)

    def run(self):
        self.mainloop.run()
        return self.ret

    def source_pad_added_cb(self, src, pad):
        name = pad.get_caps()[0].get_name()
        if name == 'audio/x-raw-float' or name == 'audio/x-raw-int':
            pad.link(self.conv.get_pad("sink"))

    def source_pad_removed_cb(self, src, pad):
        pad.unlink(self.conv.get_pad("sink"))

    def on_eos(self, bus, msg):
        if msg.type == gst.MESSAGE_EOS:
            self.bus.remove_signal_watch()
            self.pipeline.set_state(gst.STATE_PAUSED)
            self.mainloop.quit()
        elif msg.type == gst.MESSAGE_ERROR:
            print "ERROR", msg.parse_error()
            self.bus.remove_signal_watch()
            self.pipeline.set_state(gst.STATE_PAUSED)
            self.mainloop.quit()
            self.ret = 1 # set return value to 1 in case of error

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print "Usage: %s <filename>" % sys.argv[0]
        sys.exit(1)
    for filename in sys.argv[1:]:
        peak = [0.] # use a mutable 
        def process(buf, hop):
            peak[0] = max( peak[0], abs(buf.max()) )
        a = aubioinput(filename, process = process, hopsize = 512)
        if a.run() == 0: # only display the results if no 
            print "Finished reading %s, peak value is %f" % (filename, max(peak))

########NEW FILE########
__FILENAME__ = aubioweb
#!/usr/bin/python

doc = """
This script works with mod_python to browse a collection of annotated wav files
and results.

you will need to have at least the following packages need to be installed (the
name of the command line tool is precised in parenthesis):

libapache-mod-python (apache2 prefered)
sndfile-programs (sndfile-info)
vorbis-tools (oggenc)
python-gnuplot
python-numpy

Try the command line tools in aubio/python to test your installation.

NOTE: this script is probably horribly insecure.

example configuration for apache to put in your preferred virtual host.

<Directory /home/piem/public_html/aubioweb>
    # Minimal config
    AddHandler mod_python .py
    # Disable these in production
    PythonDebug On
    PythonAutoReload on
    # Default handler in url
    PythonHandler aubioweb
    ## Authentication stuff (optional)
    #PythonAuthenHandler aubioweb
    #AuthType Basic
    #AuthName "Restricted Area"
    #require valid-user
    # make default listing
    DirectoryIndex aubioweb/
</Directory>

"""

from aubio.web.html import *

def handler(req):
    from aubio.web.browser import *
    from mod_python import Session
    req.sess = Session.Session(req)
    req.sess['login']='new aubio user'
    req.sess.save()
    return configure_handler(req,index)

def index(req,threshold='0.3'):
    navigation(req)
    print_command(req,"sfinfo %%i")
    return footer(req)

def show_info(req,verbose=''):
    navigation(req)
    print_command(req,"sndfile-info %%i")
    return footer(req)

def feedback(req):
    navigation(req)
    req.write("""
    Please provide feedback below:
  <p>                           
  <form action="/~piem/aubioweb/email" method="POST">
      Name:    <input type="text" name="name"><br>
      Email:   <input type="text" name="email"><br>
      Comment: <textarea name="comment" rows=4 cols=20></textarea><br>
      <input type="submit">
  </form>
    """)

WEBMASTER='piem@calabaza'
SMTP_SERVER='localhost'

def email(req,name,email,comment):
    import smtplib
    # make sure the user provided all the parameters
    if not (name and email and comment):
        return "A required parameter is missing, \
               please go back and correct the error"
    # create the message text
    msg = """\
From: %s                                                                                                                                           
Subject: feedback
To: %s

I have the following comment:

%s

Thank You,

%s

""" % (email, WEBMASTER, comment, name)
    # send it out
    conn = smtplib.SMTP(SMTP_SERVER)
    try:
	conn.sendmail(email, [WEBMASTER], msg)
    except smtplib.SMTPSenderRefused:
	return """<html>please provide a valid email</html>"""
	
    conn.quit()
    # provide feedback to the user
    s = """\
<html>
Dear %s,<br>
Thank You for your kind comments, we
will get back to you shortly.
</html>""" % name
    return s

########NEW FILE########
__FILENAME__ = aubioonset
from template import program_test_case

class aubioonset_unit(program_test_case):
  
  import os.path
  filename = os.path.join('..','..','sounds','woodblock.aiff')
  progname = os.path.join('..','..','examples','aubioonset')

  def test_aubioonset_with_inf_silence(self):
    """ test aubioonset with -s 0  """
    self.command += " -s 0" 
    self.getOutput()
    assert len(self.output) == 0, self.output

class aubioonset_unit_finds_onset(aubioonset_unit):

  def test_aubioonset(self):
    """ test aubioonset with default parameters """
    self.getOutput()
    assert len(str(self.output)) != 0, "no output produced with command:\n" \
      + self.command

  def test_aubioonset_with_no_silence(self):
    """ test aubioonset with -s -100 """ 
    self.command += " -s -100 " 
    self.getOutput()
    # only one onset in woodblock.aiff
    self.assertNotEqual(0, len(str(self.output)), \
      "no output produced with command:\n" + self.command)
    self.assertEqual(1, len(self.output.split('\n')) )
    # onset should be at 0.00000
    self.assertEqual(0, float(self.output.strip()))

list_of_onset_modes = ["energy", "specdiff", "hfc", "complex", "phase", \
                      "kl", "mkl", "specflux"]

for name in list_of_onset_modes:
  exec("class aubioonset_"+name+"_unit(aubioonset_unit):\n\
  options = \" -O "+name+" \"")

if __name__ == '__main__': unittest.main()

########NEW FILE########
__FILENAME__ = aubiopitch
from template import *

import os.path

class aubiopitch_test_case(program_test_case):

  import os.path
  filename = os.path.join('..','..','sounds','woodblock.aiff')
  progname = "PYTHONPATH=../../python:../../python/aubio/.libs " + \
              os.path.join('..','..','python','aubiopitch')

  def test_aubiopitch(self):
    """ test aubiopitch with default parameters """
    self.getOutput()
    # FIXME: useless check
    self.assertEqual(len(self.output.split('\n')), 1)
    #self.assertEqual(float(self.output.strip()), 0.)

  def test_aubiopitch_verbose(self):
    """ test aubiopitch with -v parameter """
    self.command += " -v "
    self.getOutput()
    # FIXME: loose checking: make sure at least 8 lines are printed
    assert len(self.output) >= 8

  def test_aubiopitch_devnull(self):
    """ test aubiopitch on /dev/null """
    self.filename = "/dev/null"
    # exit status should not be 0
    self.getOutput(expected_status = 256)
    # and there should be an error message
    assert len(self.output) > 0
    # that looks like this 
    output_lines = self.output.split('\n')
    #assert output_lines[0] == "Unable to open input file /dev/null."
    #assert output_lines[1] == "Supported file format but file is malformed."
    #assert output_lines[2] == "Could not open input file /dev/null."

mode_names = ["yinfft", "yin", "fcomb", "mcomb", "schmitt"]
for name in mode_names:
  exec("class aubiopitch_test_case_" + name + "(aubiopitch_test_case):\n\
    options = \" -m " + name + " \"")

class aubiopitch_test_yinfft(program_test_case):

  filename = os.path.join('..','..','sounds','16568__acclivity__TwoCows.wav')
  url = "http://www.freesound.org/samplesViewSingle.php?id=16568"
  progname = "PYTHONPATH=../../python:../../python/aubio/.libs " + \
              os.path.join('..','..','python','aubiopitch')
  options  = " -m yinfft -t 0.75 "

  def test_aubiopitch(self):
    """ test aubiopitch with default parameters """
    if not os.path.isfile(self.filename):
      print "Warning: file 16568_acclivity_TwoCows.wav was not found in %s" % os.path.dirname(self.filename) 
      print "download it from %s to actually run test" % url
      return
    self.getOutput()
    expected_output = open(os.path.join('examples','aubiopitch','yinfft'+'.'+os.path.basename(self.filename)+'.txt')).read()
    lines = 0
    for line_out, line_exp in zip(self.output.split('\n'), expected_output.split('\n')):
      try:
        assert line_exp == line_out, line_exp + " vs. " + line_out + " at line " + str(lines)
      except:
        open(os.path.join('examples','aubiopitch','yinfft'+'.'+os.path.basename(self.filename)+'.txt.out'),'w').write(self.output)
        raise
      lines += 1

if __name__ == '__main__': unittest.main()

########NEW FILE########
__FILENAME__ = ansiterm
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import sys,os
try:
	if not(sys.stderr.isatty()and sys.stdout.isatty()):
		raise ValueError('not a tty')
	from ctypes import Structure,windll,c_short,c_ushort,c_ulong,c_int,byref,POINTER,c_long,c_char
	class COORD(Structure):
		_fields_=[("X",c_short),("Y",c_short)]
	class SMALL_RECT(Structure):
		_fields_=[("Left",c_short),("Top",c_short),("Right",c_short),("Bottom",c_short)]
	class CONSOLE_SCREEN_BUFFER_INFO(Structure):
		_fields_=[("Size",COORD),("CursorPosition",COORD),("Attributes",c_short),("Window",SMALL_RECT),("MaximumWindowSize",COORD)]
	class CONSOLE_CURSOR_INFO(Structure):
		_fields_=[('dwSize',c_ulong),('bVisible',c_int)]
	windll.kernel32.GetStdHandle.argtypes=[c_ulong]
	windll.kernel32.GetStdHandle.restype=c_ulong
	windll.kernel32.GetConsoleScreenBufferInfo.argtypes=[c_ulong,POINTER(CONSOLE_SCREEN_BUFFER_INFO)]
	windll.kernel32.GetConsoleScreenBufferInfo.restype=c_long
	windll.kernel32.SetConsoleTextAttribute.argtypes=[c_ulong,c_ushort]
	windll.kernel32.SetConsoleTextAttribute.restype=c_long
	windll.kernel32.FillConsoleOutputCharacterA.argtypes=[c_ulong,c_char,c_ulong,POINTER(COORD),POINTER(c_ulong)]
	windll.kernel32.FillConsoleOutputCharacterA.restype=c_long
	windll.kernel32.FillConsoleOutputAttribute.argtypes=[c_ulong,c_ushort,c_ulong,POINTER(COORD),POINTER(c_ulong)]
	windll.kernel32.FillConsoleOutputAttribute.restype=c_long
	windll.kernel32.SetConsoleCursorPosition.argtypes=[c_ulong,POINTER(COORD)]
	windll.kernel32.SetConsoleCursorPosition.restype=c_long
	windll.kernel32.SetConsoleCursorInfo.argtypes=[c_ulong,POINTER(CONSOLE_CURSOR_INFO)]
	windll.kernel32.SetConsoleCursorInfo.restype=c_long
	sbinfo=CONSOLE_SCREEN_BUFFER_INFO()
	csinfo=CONSOLE_CURSOR_INFO()
	hconsole=windll.kernel32.GetStdHandle(-11)
	windll.kernel32.GetConsoleScreenBufferInfo(hconsole,byref(sbinfo))
	if sbinfo.Size.X<9 or sbinfo.Size.Y<9:raise ValueError('small console')
	windll.kernel32.GetConsoleCursorInfo(hconsole,byref(csinfo))
except Exception:
	pass
else:
	import re,threading
	is_vista=getattr(sys,"getwindowsversion",None)and sys.getwindowsversion()[0]>=6
	try:
		_type=unicode
	except NameError:
		_type=str
	to_int=lambda number,default:number and int(number)or default
	wlock=threading.Lock()
	STD_OUTPUT_HANDLE=-11
	STD_ERROR_HANDLE=-12
	class AnsiTerm(object):
		def __init__(self):
			self.encoding=sys.stdout.encoding
			self.hconsole=windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
			self.cursor_history=[]
			self.orig_sbinfo=CONSOLE_SCREEN_BUFFER_INFO()
			self.orig_csinfo=CONSOLE_CURSOR_INFO()
			windll.kernel32.GetConsoleScreenBufferInfo(self.hconsole,byref(self.orig_sbinfo))
			windll.kernel32.GetConsoleCursorInfo(hconsole,byref(self.orig_csinfo))
		def screen_buffer_info(self):
			sbinfo=CONSOLE_SCREEN_BUFFER_INFO()
			windll.kernel32.GetConsoleScreenBufferInfo(self.hconsole,byref(sbinfo))
			return sbinfo
		def clear_line(self,param):
			mode=param and int(param)or 0
			sbinfo=self.screen_buffer_info()
			if mode==1:
				line_start=COORD(0,sbinfo.CursorPosition.Y)
				line_length=sbinfo.Size.X
			elif mode==2:
				line_start=COORD(sbinfo.CursorPosition.X,sbinfo.CursorPosition.Y)
				line_length=sbinfo.Size.X-sbinfo.CursorPosition.X
			else:
				line_start=sbinfo.CursorPosition
				line_length=sbinfo.Size.X-sbinfo.CursorPosition.X
			chars_written=c_ulong()
			windll.kernel32.FillConsoleOutputCharacterA(self.hconsole,c_char(' '),line_length,line_start,byref(chars_written))
			windll.kernel32.FillConsoleOutputAttribute(self.hconsole,sbinfo.Attributes,line_length,line_start,byref(chars_written))
		def clear_screen(self,param):
			mode=to_int(param,0)
			sbinfo=self.screen_buffer_info()
			if mode==1:
				clear_start=COORD(0,0)
				clear_length=sbinfo.CursorPosition.X*sbinfo.CursorPosition.Y
			elif mode==2:
				clear_start=COORD(0,0)
				clear_length=sbinfo.Size.X*sbinfo.Size.Y
				windll.kernel32.SetConsoleCursorPosition(self.hconsole,clear_start)
			else:
				clear_start=sbinfo.CursorPosition
				clear_length=((sbinfo.Size.X-sbinfo.CursorPosition.X)+sbinfo.Size.X*(sbinfo.Size.Y-sbinfo.CursorPosition.Y))
			chars_written=c_ulong()
			windll.kernel32.FillConsoleOutputCharacterA(self.hconsole,c_char(' '),clear_length,clear_start,byref(chars_written))
			windll.kernel32.FillConsoleOutputAttribute(self.hconsole,sbinfo.Attributes,clear_length,clear_start,byref(chars_written))
		def push_cursor(self,param):
			sbinfo=self.screen_buffer_info()
			self.cursor_history.append(sbinfo.CursorPosition)
		def pop_cursor(self,param):
			if self.cursor_history:
				old_pos=self.cursor_history.pop()
				windll.kernel32.SetConsoleCursorPosition(self.hconsole,old_pos)
		def set_cursor(self,param):
			y,sep,x=param.partition(';')
			x=to_int(x,1)-1
			y=to_int(y,1)-1
			sbinfo=self.screen_buffer_info()
			new_pos=COORD(min(max(0,x),sbinfo.Size.X),min(max(0,y),sbinfo.Size.Y))
			windll.kernel32.SetConsoleCursorPosition(self.hconsole,new_pos)
		def set_column(self,param):
			x=to_int(param,1)-1
			sbinfo=self.screen_buffer_info()
			new_pos=COORD(min(max(0,x),sbinfo.Size.X),sbinfo.CursorPosition.Y)
			windll.kernel32.SetConsoleCursorPosition(self.hconsole,new_pos)
		def move_cursor(self,x_offset=0,y_offset=0):
			sbinfo=self.screen_buffer_info()
			new_pos=COORD(min(max(0,sbinfo.CursorPosition.X+x_offset),sbinfo.Size.X),min(max(0,sbinfo.CursorPosition.Y+y_offset),sbinfo.Size.Y))
			windll.kernel32.SetConsoleCursorPosition(self.hconsole,new_pos)
		def move_up(self,param):
			self.move_cursor(y_offset=-to_int(param,1))
		def move_down(self,param):
			self.move_cursor(y_offset=to_int(param,1))
		def move_left(self,param):
			self.move_cursor(x_offset=-to_int(param,1))
		def move_right(self,param):
			self.move_cursor(x_offset=to_int(param,1))
		def next_line(self,param):
			sbinfo=self.screen_buffer_info()
			self.move_cursor(x_offset=-sbinfo.CursorPosition.X,y_offset=to_int(param,1))
		def prev_line(self,param):
			sbinfo=self.screen_buffer_info()
			self.move_cursor(x_offset=-sbinfo.CursorPosition.X,y_offset=-to_int(param,1))
		def rgb2bgr(self,c):
			return((c&1)<<2)|(c&2)|((c&4)>>2)
		def set_color(self,param):
			cols=param.split(';')
			sbinfo=CONSOLE_SCREEN_BUFFER_INFO()
			windll.kernel32.GetConsoleScreenBufferInfo(self.hconsole,byref(sbinfo))
			attr=sbinfo.Attributes
			for c in cols:
				if is_vista:
					c=int(c)
				else:
					c=to_int(c,0)
				if 29<c<38:
					attr=(attr&0xfff0)|self.rgb2bgr(c-30)
				elif 39<c<48:
					attr=(attr&0xff0f)|(self.rgb2bgr(c-40)<<4)
				elif c==0:
					attr=self.orig_sbinfo.Attributes
				elif c==1:
					attr|=0x08
				elif c==4:
					attr|=0x80
				elif c==7:
					attr=(attr&0xff88)|((attr&0x70)>>4)|((attr&0x07)<<4)
			windll.kernel32.SetConsoleTextAttribute(self.hconsole,attr)
		def show_cursor(self,param):
			csinfo.bVisible=1
			windll.kernel32.SetConsoleCursorInfo(self.hconsole,byref(csinfo))
		def hide_cursor(self,param):
			csinfo.bVisible=0
			windll.kernel32.SetConsoleCursorInfo(self.hconsole,byref(csinfo))
		ansi_command_table={'A':move_up,'B':move_down,'C':move_right,'D':move_left,'E':next_line,'F':prev_line,'G':set_column,'H':set_cursor,'f':set_cursor,'J':clear_screen,'K':clear_line,'h':show_cursor,'l':hide_cursor,'m':set_color,'s':push_cursor,'u':pop_cursor,}
		ansi_tokens=re.compile('(?:\x1b\[([0-9?;]*)([a-zA-Z])|([^\x1b]+))')
		def write(self,text):
			try:
				wlock.acquire()
				for param,cmd,txt in self.ansi_tokens.findall(text):
					if cmd:
						cmd_func=self.ansi_command_table.get(cmd)
						if cmd_func:
							cmd_func(self,param)
					else:
						self.writeconsole(txt)
			finally:
				wlock.release()
		def writeconsole(self,txt):
			chars_written=c_int()
			writeconsole=windll.kernel32.WriteConsoleA
			if isinstance(txt,_type):
				writeconsole=windll.kernel32.WriteConsoleW
			TINY_STEP=3000
			for x in range(0,len(txt),TINY_STEP):
				tiny=txt[x:x+TINY_STEP]
				writeconsole(self.hconsole,tiny,len(tiny),byref(chars_written),None)
		def flush(self):
			pass
		def isatty(self):
			return True
	sys.stderr=sys.stdout=AnsiTerm()
	os.environ['TERM']='vt100'

########NEW FILE########
__FILENAME__ = Build
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import os,sys,errno,re,shutil
try:
	import cPickle
except ImportError:
	import pickle as cPickle
from waflib import Runner,TaskGen,Utils,ConfigSet,Task,Logs,Options,Context,Errors
import waflib.Node
CACHE_DIR='c4che'
CACHE_SUFFIX='_cache.py'
INSTALL=1337
UNINSTALL=-1337
SAVED_ATTRS='root node_deps raw_deps task_sigs'.split()
CFG_FILES='cfg_files'
POST_AT_ONCE=0
POST_LAZY=1
POST_BOTH=2
class BuildContext(Context.Context):
	'''executes the build'''
	cmd='build'
	variant=''
	def __init__(self,**kw):
		super(BuildContext,self).__init__(**kw)
		self.is_install=0
		self.top_dir=kw.get('top_dir',Context.top_dir)
		self.run_dir=kw.get('run_dir',Context.run_dir)
		self.post_mode=POST_AT_ONCE
		self.out_dir=kw.get('out_dir',Context.out_dir)
		self.cache_dir=kw.get('cache_dir',None)
		if not self.cache_dir:
			self.cache_dir=self.out_dir+os.sep+CACHE_DIR
		self.all_envs={}
		self.task_sigs={}
		self.node_deps={}
		self.raw_deps={}
		self.cache_dir_contents={}
		self.task_gen_cache_names={}
		self.launch_dir=Context.launch_dir
		self.jobs=Options.options.jobs
		self.targets=Options.options.targets
		self.keep=Options.options.keep
		self.cache_global=Options.cache_global
		self.nocache=Options.options.nocache
		self.progress_bar=Options.options.progress_bar
		self.deps_man=Utils.defaultdict(list)
		self.current_group=0
		self.groups=[]
		self.group_names={}
	def get_variant_dir(self):
		if not self.variant:
			return self.out_dir
		return os.path.join(self.out_dir,self.variant)
	variant_dir=property(get_variant_dir,None)
	def __call__(self,*k,**kw):
		kw['bld']=self
		ret=TaskGen.task_gen(*k,**kw)
		self.task_gen_cache_names={}
		self.add_to_group(ret,group=kw.get('group',None))
		return ret
	def rule(self,*k,**kw):
		def f(rule):
			ret=self(*k,**kw)
			ret.rule=rule
			return ret
		return f
	def __copy__(self):
		raise Errors.WafError('build contexts are not supposed to be copied')
	def install_files(self,*k,**kw):
		pass
	def install_as(self,*k,**kw):
		pass
	def symlink_as(self,*k,**kw):
		pass
	def load_envs(self):
		node=self.root.find_node(self.cache_dir)
		if not node:
			raise Errors.WafError('The project was not configured: run "waf configure" first!')
		lst=node.ant_glob('**/*%s'%CACHE_SUFFIX,quiet=True)
		if not lst:
			raise Errors.WafError('The cache directory is empty: reconfigure the project')
		for x in lst:
			name=x.path_from(node).replace(CACHE_SUFFIX,'').replace('\\','/')
			env=ConfigSet.ConfigSet(x.abspath())
			self.all_envs[name]=env
			for f in env[CFG_FILES]:
				newnode=self.root.find_resource(f)
				try:
					h=Utils.h_file(newnode.abspath())
				except(IOError,AttributeError):
					Logs.error('cannot find %r'%f)
					h=Utils.SIG_NIL
				newnode.sig=h
	def init_dirs(self):
		if not(os.path.isabs(self.top_dir)and os.path.isabs(self.out_dir)):
			raise Errors.WafError('The project was not configured: run "waf configure" first!')
		self.path=self.srcnode=self.root.find_dir(self.top_dir)
		self.bldnode=self.root.make_node(self.variant_dir)
		self.bldnode.mkdir()
	def execute(self):
		self.restore()
		if not self.all_envs:
			self.load_envs()
		self.execute_build()
	def execute_build(self):
		Logs.info("Waf: Entering directory `%s'"%self.variant_dir)
		self.recurse([self.run_dir])
		self.pre_build()
		self.timer=Utils.Timer()
		if self.progress_bar:
			sys.stderr.write(Logs.colors.cursor_off)
		try:
			self.compile()
		finally:
			if self.progress_bar==1:
				c=len(self.returned_tasks)or 1
				self.to_log(self.progress_line(c,c,Logs.colors.BLUE,Logs.colors.NORMAL))
				print('')
				sys.stdout.flush()
				sys.stderr.write(Logs.colors.cursor_on)
			Logs.info("Waf: Leaving directory `%s'"%self.variant_dir)
		self.post_build()
	def restore(self):
		try:
			env=ConfigSet.ConfigSet(os.path.join(self.cache_dir,'build.config.py'))
		except(IOError,OSError):
			pass
		else:
			if env['version']<Context.HEXVERSION:
				raise Errors.WafError('Version mismatch! reconfigure the project')
			for t in env['tools']:
				self.setup(**t)
		dbfn=os.path.join(self.variant_dir,Context.DBFILE)
		try:
			data=Utils.readf(dbfn,'rb')
		except(IOError,EOFError):
			Logs.debug('build: Could not load the build cache %s (missing)'%dbfn)
		else:
			try:
				waflib.Node.pickle_lock.acquire()
				waflib.Node.Nod3=self.node_class
				try:
					data=cPickle.loads(data)
				except Exception ,e:
					Logs.debug('build: Could not pickle the build cache %s: %r'%(dbfn,e))
				else:
					for x in SAVED_ATTRS:
						setattr(self,x,data[x])
			finally:
				waflib.Node.pickle_lock.release()
		self.init_dirs()
	def store(self):
		data={}
		for x in SAVED_ATTRS:
			data[x]=getattr(self,x)
		db=os.path.join(self.variant_dir,Context.DBFILE)
		try:
			waflib.Node.pickle_lock.acquire()
			waflib.Node.Nod3=self.node_class
			x=cPickle.dumps(data,-1)
		finally:
			waflib.Node.pickle_lock.release()
		Utils.writef(db+'.tmp',x,m='wb')
		try:
			st=os.stat(db)
			os.remove(db)
			if not Utils.is_win32:
				os.chown(db+'.tmp',st.st_uid,st.st_gid)
		except(AttributeError,OSError):
			pass
		os.rename(db+'.tmp',db)
	def compile(self):
		Logs.debug('build: compile()')
		self.producer=Runner.Parallel(self,self.jobs)
		self.producer.biter=self.get_build_iterator()
		self.returned_tasks=[]
		try:
			self.producer.start()
		except KeyboardInterrupt:
			self.store()
			raise
		else:
			if self.producer.dirty:
				self.store()
		if self.producer.error:
			raise Errors.BuildError(self.producer.error)
	def setup(self,tool,tooldir=None,funs=None):
		if isinstance(tool,list):
			for i in tool:self.setup(i,tooldir)
			return
		module=Context.load_tool(tool,tooldir)
		if hasattr(module,"setup"):module.setup(self)
	def get_env(self):
		try:
			return self.all_envs[self.variant]
		except KeyError:
			return self.all_envs['']
	def set_env(self,val):
		self.all_envs[self.variant]=val
	env=property(get_env,set_env)
	def add_manual_dependency(self,path,value):
		if path is None:
			raise ValueError('Invalid input')
		if isinstance(path,waflib.Node.Node):
			node=path
		elif os.path.isabs(path):
			node=self.root.find_resource(path)
		else:
			node=self.path.find_resource(path)
		if isinstance(value,list):
			self.deps_man[id(node)].extend(value)
		else:
			self.deps_man[id(node)].append(value)
	def launch_node(self):
		try:
			return self.p_ln
		except AttributeError:
			self.p_ln=self.root.find_dir(self.launch_dir)
			return self.p_ln
	def hash_env_vars(self,env,vars_lst):
		if not env.table:
			env=env.parent
			if not env:
				return Utils.SIG_NIL
		idx=str(id(env))+str(vars_lst)
		try:
			cache=self.cache_env
		except AttributeError:
			cache=self.cache_env={}
		else:
			try:
				return self.cache_env[idx]
			except KeyError:
				pass
		lst=[env[a]for a in vars_lst]
		ret=Utils.h_list(lst)
		Logs.debug('envhash: %s %r',Utils.to_hex(ret),lst)
		cache[idx]=ret
		return ret
	def get_tgen_by_name(self,name):
		cache=self.task_gen_cache_names
		if not cache:
			for g in self.groups:
				for tg in g:
					try:
						cache[tg.name]=tg
					except AttributeError:
						pass
		try:
			return cache[name]
		except KeyError:
			raise Errors.WafError('Could not find a task generator for the name %r'%name)
	def progress_line(self,state,total,col1,col2):
		n=len(str(total))
		Utils.rot_idx+=1
		ind=Utils.rot_chr[Utils.rot_idx%4]
		pc=(100.*state)/total
		eta=str(self.timer)
		fs="[%%%dd/%%%dd][%%s%%2d%%%%%%s][%s]["%(n,n,ind)
		left=fs%(state,total,col1,pc,col2)
		right='][%s%s%s]'%(col1,eta,col2)
		cols=Logs.get_term_cols()-len(left)-len(right)+2*len(col1)+2*len(col2)
		if cols<7:cols=7
		ratio=((cols*state)//total)-1
		bar=('='*ratio+'>').ljust(cols)
		msg=Utils.indicator%(left,bar,right)
		return msg
	def declare_chain(self,*k,**kw):
		return TaskGen.declare_chain(*k,**kw)
	def pre_build(self):
		for m in getattr(self,'pre_funs',[]):
			m(self)
	def post_build(self):
		for m in getattr(self,'post_funs',[]):
			m(self)
	def add_pre_fun(self,meth):
		try:
			self.pre_funs.append(meth)
		except AttributeError:
			self.pre_funs=[meth]
	def add_post_fun(self,meth):
		try:
			self.post_funs.append(meth)
		except AttributeError:
			self.post_funs=[meth]
	def get_group(self,x):
		if not self.groups:
			self.add_group()
		if x is None:
			return self.groups[self.current_group]
		if x in self.group_names:
			return self.group_names[x]
		return self.groups[x]
	def add_to_group(self,tgen,group=None):
		assert(isinstance(tgen,TaskGen.task_gen)or isinstance(tgen,Task.TaskBase))
		tgen.bld=self
		self.get_group(group).append(tgen)
	def get_group_name(self,g):
		if not isinstance(g,list):
			g=self.groups[g]
		for x in self.group_names:
			if id(self.group_names[x])==id(g):
				return x
		return''
	def get_group_idx(self,tg):
		se=id(tg)
		for i in range(len(self.groups)):
			for t in self.groups[i]:
				if id(t)==se:
					return i
		return None
	def add_group(self,name=None,move=True):
		if name and name in self.group_names:
			Logs.error('add_group: name %s already present'%name)
		g=[]
		self.group_names[name]=g
		self.groups.append(g)
		if move:
			self.current_group=len(self.groups)-1
	def set_group(self,idx):
		if isinstance(idx,str):
			g=self.group_names[idx]
			for i in range(len(self.groups)):
				if id(g)==id(self.groups[i]):
					self.current_group=i
		else:
			self.current_group=idx
	def total(self):
		total=0
		for group in self.groups:
			for tg in group:
				try:
					total+=len(tg.tasks)
				except AttributeError:
					total+=1
		return total
	def get_targets(self):
		to_post=[]
		min_grp=0
		for name in self.targets.split(','):
			tg=self.get_tgen_by_name(name)
			if not tg:
				raise Errors.WafError('target %r does not exist'%name)
			m=self.get_group_idx(tg)
			if m>min_grp:
				min_grp=m
				to_post=[tg]
			elif m==min_grp:
				to_post.append(tg)
		return(min_grp,to_post)
	def get_all_task_gen(self):
		lst=[]
		for g in self.groups:
			lst.extend(g)
		return lst
	def post_group(self):
		if self.targets=='*':
			for tg in self.groups[self.cur]:
				try:
					f=tg.post
				except AttributeError:
					pass
				else:
					f()
		elif self.targets:
			if self.cur<self._min_grp:
				for tg in self.groups[self.cur]:
					try:
						f=tg.post
					except AttributeError:
						pass
					else:
						f()
			else:
				for tg in self._exact_tg:
					tg.post()
		else:
			ln=self.launch_node()
			if ln.is_child_of(self.bldnode):
				Logs.warn('Building from the build directory, forcing --targets=*')
				ln=self.srcnode
			elif not ln.is_child_of(self.srcnode):
				Logs.warn('CWD %s is not under %s, forcing --targets=* (run distclean?)'%(ln.abspath(),self.srcnode.abspath()))
				ln=self.srcnode
			for tg in self.groups[self.cur]:
				try:
					f=tg.post
				except AttributeError:
					pass
				else:
					if tg.path.is_child_of(ln):
						f()
	def get_tasks_group(self,idx):
		tasks=[]
		for tg in self.groups[idx]:
			try:
				tasks.extend(tg.tasks)
			except AttributeError:
				tasks.append(tg)
		return tasks
	def get_build_iterator(self):
		self.cur=0
		if self.targets and self.targets!='*':
			(self._min_grp,self._exact_tg)=self.get_targets()
		global lazy_post
		if self.post_mode!=POST_LAZY:
			while self.cur<len(self.groups):
				self.post_group()
				self.cur+=1
			self.cur=0
		while self.cur<len(self.groups):
			if self.post_mode!=POST_AT_ONCE:
				self.post_group()
			tasks=self.get_tasks_group(self.cur)
			Task.set_file_constraints(tasks)
			Task.set_precedence_constraints(tasks)
			self.cur_tasks=tasks
			self.cur+=1
			if not tasks:
				continue
			yield tasks
		while 1:
			yield[]
class inst(Task.Task):
	color='CYAN'
	def uid(self):
		lst=[self.dest,self.path]+self.source
		return Utils.h_list(repr(lst))
	def post(self):
		buf=[]
		for x in self.source:
			if isinstance(x,waflib.Node.Node):
				y=x
			else:
				y=self.path.find_resource(x)
				if not y:
					if Logs.verbose:
						Logs.warn('Could not find %s immediately (may cause broken builds)'%x)
					idx=self.generator.bld.get_group_idx(self)
					for tg in self.generator.bld.groups[idx]:
						if not isinstance(tg,inst)and id(tg)!=id(self):
							tg.post()
						y=self.path.find_resource(x)
						if y:
							break
					else:
						raise Errors.WafError('Could not find %r in %r'%(x,self.path))
			buf.append(y)
		self.inputs=buf
	def runnable_status(self):
		ret=super(inst,self).runnable_status()
		if ret==Task.SKIP_ME:
			return Task.RUN_ME
		return ret
	def __str__(self):
		return''
	def run(self):
		return self.generator.exec_task()
	def get_install_path(self,destdir=True):
		dest=Utils.subst_vars(self.dest,self.env)
		dest=dest.replace('/',os.sep)
		if destdir and Options.options.destdir:
			dest=os.path.join(Options.options.destdir,os.path.splitdrive(dest)[1].lstrip(os.sep))
		return dest
	def exec_install_files(self):
		destpath=self.get_install_path()
		if not destpath:
			raise Errors.WafError('unknown installation path %r'%self.generator)
		for x,y in zip(self.source,self.inputs):
			if self.relative_trick:
				destfile=os.path.join(destpath,y.path_from(self.path))
			else:
				destfile=os.path.join(destpath,y.name)
			self.generator.bld.do_install(y.abspath(),destfile,self.chmod)
	def exec_install_as(self):
		destfile=self.get_install_path()
		self.generator.bld.do_install(self.inputs[0].abspath(),destfile,self.chmod)
	def exec_symlink_as(self):
		destfile=self.get_install_path()
		src=self.link
		if self.relative_trick:
			src=os.path.relpath(src,os.path.dirname(destfile))
		self.generator.bld.do_link(src,destfile)
class InstallContext(BuildContext):
	'''installs the targets on the system'''
	cmd='install'
	def __init__(self,**kw):
		super(InstallContext,self).__init__(**kw)
		self.uninstall=[]
		self.is_install=INSTALL
	def do_install(self,src,tgt,chmod=Utils.O644):
		d,_=os.path.split(tgt)
		if not d:
			raise Errors.WafError('Invalid installation given %r->%r'%(src,tgt))
		Utils.check_dir(d)
		srclbl=src.replace(self.srcnode.abspath()+os.sep,'')
		if not Options.options.force:
			try:
				st1=os.stat(tgt)
				st2=os.stat(src)
			except OSError:
				pass
			else:
				if st1.st_mtime+2>=st2.st_mtime and st1.st_size==st2.st_size:
					if not self.progress_bar:
						Logs.info('- install %s (from %s)'%(tgt,srclbl))
					return False
		if not self.progress_bar:
			Logs.info('+ install %s (from %s)'%(tgt,srclbl))
		try:
			os.remove(tgt)
		except OSError:
			pass
		try:
			shutil.copy2(src,tgt)
			os.chmod(tgt,chmod)
		except IOError:
			try:
				os.stat(src)
			except(OSError,IOError):
				Logs.error('File %r does not exist'%src)
			raise Errors.WafError('Could not install the file %r'%tgt)
	def do_link(self,src,tgt):
		d,_=os.path.split(tgt)
		Utils.check_dir(d)
		link=False
		if not os.path.islink(tgt):
			link=True
		elif os.readlink(tgt)!=src:
			link=True
		if link:
			try:os.remove(tgt)
			except OSError:pass
			if not self.progress_bar:
				Logs.info('+ symlink %s (to %s)'%(tgt,src))
			os.symlink(src,tgt)
		else:
			if not self.progress_bar:
				Logs.info('- symlink %s (to %s)'%(tgt,src))
	def run_task_now(self,tsk,postpone):
		tsk.post()
		if not postpone:
			if tsk.runnable_status()==Task.ASK_LATER:
				raise self.WafError('cannot post the task %r'%tsk)
			tsk.run()
	def install_files(self,dest,files,env=None,chmod=Utils.O644,relative_trick=False,cwd=None,add=True,postpone=True):
		tsk=inst(env=env or self.env)
		tsk.bld=self
		tsk.path=cwd or self.path
		tsk.chmod=chmod
		if isinstance(files,waflib.Node.Node):
			tsk.source=[files]
		else:
			tsk.source=Utils.to_list(files)
		tsk.dest=dest
		tsk.exec_task=tsk.exec_install_files
		tsk.relative_trick=relative_trick
		if add:self.add_to_group(tsk)
		self.run_task_now(tsk,postpone)
		return tsk
	def install_as(self,dest,srcfile,env=None,chmod=Utils.O644,cwd=None,add=True,postpone=True):
		tsk=inst(env=env or self.env)
		tsk.bld=self
		tsk.path=cwd or self.path
		tsk.chmod=chmod
		tsk.source=[srcfile]
		tsk.dest=dest
		tsk.exec_task=tsk.exec_install_as
		if add:self.add_to_group(tsk)
		self.run_task_now(tsk,postpone)
		return tsk
	def symlink_as(self,dest,src,env=None,cwd=None,add=True,postpone=True,relative_trick=False):
		if Utils.is_win32:
			return
		tsk=inst(env=env or self.env)
		tsk.bld=self
		tsk.dest=dest
		tsk.path=cwd or self.path
		tsk.source=[]
		tsk.link=src
		tsk.relative_trick=relative_trick
		tsk.exec_task=tsk.exec_symlink_as
		if add:self.add_to_group(tsk)
		self.run_task_now(tsk,postpone)
		return tsk
class UninstallContext(InstallContext):
	'''removes the targets installed'''
	cmd='uninstall'
	def __init__(self,**kw):
		super(UninstallContext,self).__init__(**kw)
		self.is_install=UNINSTALL
	def do_install(self,src,tgt,chmod=Utils.O644):
		if not self.progress_bar:
			Logs.info('- remove %s'%tgt)
		self.uninstall.append(tgt)
		try:
			os.remove(tgt)
		except OSError ,e:
			if e.errno!=errno.ENOENT:
				if not getattr(self,'uninstall_error',None):
					self.uninstall_error=True
					Logs.warn('build: some files could not be uninstalled (retry with -vv to list them)')
				if Logs.verbose>1:
					Logs.warn('Could not remove %s (error code %r)'%(e.filename,e.errno))
		while tgt:
			tgt=os.path.dirname(tgt)
			try:
				os.rmdir(tgt)
			except OSError:
				break
	def do_link(self,src,tgt):
		try:
			if not self.progress_bar:
				Logs.info('- remove %s'%tgt)
			os.remove(tgt)
		except OSError:
			pass
		while tgt:
			tgt=os.path.dirname(tgt)
			try:
				os.rmdir(tgt)
			except OSError:
				break
	def execute(self):
		try:
			def runnable_status(self):
				return Task.SKIP_ME
			setattr(Task.Task,'runnable_status_back',Task.Task.runnable_status)
			setattr(Task.Task,'runnable_status',runnable_status)
			super(UninstallContext,self).execute()
		finally:
			setattr(Task.Task,'runnable_status',Task.Task.runnable_status_back)
class CleanContext(BuildContext):
	'''cleans the project'''
	cmd='clean'
	def execute(self):
		self.restore()
		if not self.all_envs:
			self.load_envs()
		self.recurse([self.run_dir])
		try:
			self.clean()
		finally:
			self.store()
	def clean(self):
		Logs.debug('build: clean called')
		if self.bldnode!=self.srcnode:
			lst=[]
			for e in self.all_envs.values():
				lst.extend(self.root.find_or_declare(f)for f in e[CFG_FILES])
			for n in self.bldnode.ant_glob('**/*',excl='.lock* *conf_check_*/** config.log c4che/*',quiet=True):
				if n in lst:
					continue
				n.delete()
		self.root.children={}
		for v in'node_deps task_sigs raw_deps'.split():
			setattr(self,v,{})
class ListContext(BuildContext):
	'''lists the targets to execute'''
	cmd='list'
	def execute(self):
		self.restore()
		if not self.all_envs:
			self.load_envs()
		self.recurse([self.run_dir])
		self.pre_build()
		self.timer=Utils.Timer()
		for g in self.groups:
			for tg in g:
				try:
					f=tg.post
				except AttributeError:
					pass
				else:
					f()
		try:
			self.get_tgen_by_name('')
		except Exception:
			pass
		lst=list(self.task_gen_cache_names.keys())
		lst.sort()
		for k in lst:
			Logs.pprint('GREEN',k)
class StepContext(BuildContext):
	'''executes tasks in a step-by-step fashion, for debugging'''
	cmd='step'
	def __init__(self,**kw):
		super(StepContext,self).__init__(**kw)
		self.files=Options.options.files
	def compile(self):
		if not self.files:
			Logs.warn('Add a pattern for the debug build, for example "waf step --files=main.c,app"')
			BuildContext.compile(self)
			return
		targets=None
		if self.targets and self.targets!='*':
			targets=self.targets.split(',')
		for g in self.groups:
			for tg in g:
				if targets and tg.name not in targets:
					continue
				try:
					f=tg.post
				except AttributeError:
					pass
				else:
					f()
			for pat in self.files.split(','):
				matcher=self.get_matcher(pat)
				for tg in g:
					if isinstance(tg,Task.TaskBase):
						lst=[tg]
					else:
						lst=tg.tasks
					for tsk in lst:
						do_exec=False
						for node in getattr(tsk,'inputs',[]):
							if matcher(node,output=False):
								do_exec=True
								break
						for node in getattr(tsk,'outputs',[]):
							if matcher(node,output=True):
								do_exec=True
								break
						if do_exec:
							ret=tsk.run()
							Logs.info('%s -> exit %r'%(str(tsk),ret))
	def get_matcher(self,pat):
		inn=True
		out=True
		if pat.startswith('in:'):
			out=False
			pat=pat.replace('in:','')
		elif pat.startswith('out:'):
			inn=False
			pat=pat.replace('out:','')
		anode=self.root.find_node(pat)
		pattern=None
		if not anode:
			if not pat.startswith('^'):
				pat='^.+?%s'%pat
			if not pat.endswith('$'):
				pat='%s$'%pat
			pattern=re.compile(pat)
		def match(node,output):
			if output==True and not out:
				return False
			if output==False and not inn:
				return False
			if anode:
				return anode==node
			else:
				return pattern.match(node.abspath())
		return match
BuildContext.store=Utils.nogc(BuildContext.store)
BuildContext.restore=Utils.nogc(BuildContext.restore)

########NEW FILE########
__FILENAME__ = ConfigSet
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import copy,re,os
from waflib import Logs,Utils
re_imp=re.compile('^(#)*?([^#=]*?)\ =\ (.*?)$',re.M)
class ConfigSet(object):
	__slots__=('table','parent')
	def __init__(self,filename=None):
		self.table={}
		if filename:
			self.load(filename)
	def __contains__(self,key):
		if key in self.table:return True
		try:return self.parent.__contains__(key)
		except AttributeError:return False
	def keys(self):
		keys=set()
		cur=self
		while cur:
			keys.update(cur.table.keys())
			cur=getattr(cur,'parent',None)
		keys=list(keys)
		keys.sort()
		return keys
	def __str__(self):
		return"\n".join(["%r %r"%(x,self.__getitem__(x))for x in self.keys()])
	def __getitem__(self,key):
		try:
			while 1:
				x=self.table.get(key,None)
				if not x is None:
					return x
				self=self.parent
		except AttributeError:
			return[]
	def __setitem__(self,key,value):
		self.table[key]=value
	def __delitem__(self,key):
		self[key]=[]
	def __getattr__(self,name):
		if name in self.__slots__:
			return object.__getattr__(self,name)
		else:
			return self[name]
	def __setattr__(self,name,value):
		if name in self.__slots__:
			object.__setattr__(self,name,value)
		else:
			self[name]=value
	def __delattr__(self,name):
		if name in self.__slots__:
			object.__delattr__(self,name)
		else:
			del self[name]
	def derive(self):
		newenv=ConfigSet()
		newenv.parent=self
		return newenv
	def detach(self):
		tbl=self.get_merged_dict()
		try:
			delattr(self,'parent')
		except AttributeError:
			pass
		else:
			keys=tbl.keys()
			for x in keys:
				tbl[x]=copy.deepcopy(tbl[x])
			self.table=tbl
	def get_flat(self,key):
		s=self[key]
		if isinstance(s,str):return s
		return' '.join(s)
	def _get_list_value_for_modification(self,key):
		try:
			value=self.table[key]
		except KeyError:
			try:value=self.parent[key]
			except AttributeError:value=[]
			if isinstance(value,list):
				value=value[:]
			else:
				value=[value]
		else:
			if not isinstance(value,list):
				value=[value]
		self.table[key]=value
		return value
	def append_value(self,var,val):
		current_value=self._get_list_value_for_modification(var)
		if isinstance(val,str):
			val=[val]
		current_value.extend(val)
	def prepend_value(self,var,val):
		if isinstance(val,str):
			val=[val]
		self.table[var]=val+self._get_list_value_for_modification(var)
	def append_unique(self,var,val):
		if isinstance(val,str):
			val=[val]
		current_value=self._get_list_value_for_modification(var)
		for x in val:
			if x not in current_value:
				current_value.append(x)
	def get_merged_dict(self):
		table_list=[]
		env=self
		while 1:
			table_list.insert(0,env.table)
			try:env=env.parent
			except AttributeError:break
		merged_table={}
		for table in table_list:
			merged_table.update(table)
		return merged_table
	def store(self,filename):
		try:
			os.makedirs(os.path.split(filename)[0])
		except OSError:
			pass
		buf=[]
		merged_table=self.get_merged_dict()
		keys=list(merged_table.keys())
		keys.sort()
		try:
			fun=ascii
		except NameError:
			fun=repr
		for k in keys:
			if k!='undo_stack':
				buf.append('%s = %s\n'%(k,fun(merged_table[k])))
		Utils.writef(filename,''.join(buf))
	def load(self,filename):
		tbl=self.table
		code=Utils.readf(filename,m='rU')
		for m in re_imp.finditer(code):
			g=m.group
			tbl[g(2)]=eval(g(3))
		Logs.debug('env: %s'%str(self.table))
	def update(self,d):
		for k,v in d.items():
			self[k]=v
	def stash(self):
		orig=self.table
		tbl=self.table=self.table.copy()
		for x in tbl.keys():
			tbl[x]=copy.deepcopy(tbl[x])
		self.undo_stack=self.undo_stack+[orig]
	def revert(self):
		self.table=self.undo_stack.pop(-1)

########NEW FILE########
__FILENAME__ = Configure
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import os,shlex,sys,time
from waflib import ConfigSet,Utils,Options,Logs,Context,Build,Errors
try:
	from urllib import request
except ImportError:
	from urllib import urlopen
else:
	urlopen=request.urlopen
BREAK='break'
CONTINUE='continue'
WAF_CONFIG_LOG='config.log'
autoconfig=False
conf_template='''# project %(app)s configured on %(now)s by
# waf %(wafver)s (abi %(abi)s, python %(pyver)x on %(systype)s)
# using %(args)s
#'''
def download_check(node):
	pass
def download_tool(tool,force=False,ctx=None):
	for x in Utils.to_list(Context.remote_repo):
		for sub in Utils.to_list(Context.remote_locs):
			url='/'.join((x,sub,tool+'.py'))
			try:
				web=urlopen(url)
				try:
					if web.getcode()!=200:
						continue
				except AttributeError:
					pass
			except Exception:
				continue
			else:
				tmp=ctx.root.make_node(os.sep.join((Context.waf_dir,'waflib','extras',tool+'.py')))
				tmp.write(web.read(),'wb')
				Logs.warn('Downloaded %s from %s'%(tool,url))
				download_check(tmp)
				try:
					module=Context.load_tool(tool)
				except Exception:
					Logs.warn('The tool %s from %s is unusable'%(tool,url))
					try:
						tmp.delete()
					except Exception:
						pass
					continue
				return module
	raise Errors.WafError('Could not load the Waf tool')
class ConfigurationContext(Context.Context):
	'''configures the project'''
	cmd='configure'
	error_handlers=[]
	def __init__(self,**kw):
		super(ConfigurationContext,self).__init__(**kw)
		self.environ=dict(os.environ)
		self.all_envs={}
		self.top_dir=None
		self.out_dir=None
		self.tools=[]
		self.hash=0
		self.files=[]
		self.tool_cache=[]
		self.setenv('')
	def setenv(self,name,env=None):
		if name not in self.all_envs or env:
			if not env:
				env=ConfigSet.ConfigSet()
				self.prepare_env(env)
			else:
				env=env.derive()
			self.all_envs[name]=env
		self.variant=name
	def get_env(self):
		return self.all_envs[self.variant]
	def set_env(self,val):
		self.all_envs[self.variant]=val
	env=property(get_env,set_env)
	def init_dirs(self):
		top=self.top_dir
		if not top:
			top=Options.options.top
		if not top:
			top=getattr(Context.g_module,Context.TOP,None)
		if not top:
			top=self.path.abspath()
		top=os.path.abspath(top)
		self.srcnode=(os.path.isabs(top)and self.root or self.path).find_dir(top)
		assert(self.srcnode)
		out=self.out_dir
		if not out:
			out=Options.options.out
		if not out:
			out=getattr(Context.g_module,Context.OUT,None)
		if not out:
			out=Options.lockfile.replace('.lock-waf_%s_'%sys.platform,'').replace('.lock-waf','')
		self.bldnode=(os.path.isabs(out)and self.root or self.path).make_node(out)
		self.bldnode.mkdir()
		if not os.path.isdir(self.bldnode.abspath()):
			conf.fatal('Could not create the build directory %s'%self.bldnode.abspath())
	def execute(self):
		self.init_dirs()
		self.cachedir=self.bldnode.make_node(Build.CACHE_DIR)
		self.cachedir.mkdir()
		path=os.path.join(self.bldnode.abspath(),WAF_CONFIG_LOG)
		self.logger=Logs.make_logger(path,'cfg')
		app=getattr(Context.g_module,'APPNAME','')
		if app:
			ver=getattr(Context.g_module,'VERSION','')
			if ver:
				app="%s (%s)"%(app,ver)
		now=time.ctime()
		pyver=sys.hexversion
		systype=sys.platform
		args=" ".join(sys.argv)
		wafver=Context.WAFVERSION
		abi=Context.ABI
		self.to_log(conf_template%vars())
		self.msg('Setting top to',self.srcnode.abspath())
		self.msg('Setting out to',self.bldnode.abspath())
		if id(self.srcnode)==id(self.bldnode):
			Logs.warn('Setting top == out (remember to use "update_outputs")')
		elif id(self.path)!=id(self.srcnode):
			if self.srcnode.is_child_of(self.path):
				Logs.warn('Are you certain that you do not want to set top="." ?')
		super(ConfigurationContext,self).execute()
		self.store()
		Context.top_dir=self.srcnode.abspath()
		Context.out_dir=self.bldnode.abspath()
		env=ConfigSet.ConfigSet()
		env['argv']=sys.argv
		env['options']=Options.options.__dict__
		env.run_dir=Context.run_dir
		env.top_dir=Context.top_dir
		env.out_dir=Context.out_dir
		env['hash']=self.hash
		env['files']=self.files
		env['environ']=dict(self.environ)
		if not self.env.NO_LOCK_IN_RUN:
			env.store(Context.run_dir+os.sep+Options.lockfile)
		if not self.env.NO_LOCK_IN_TOP:
			env.store(Context.top_dir+os.sep+Options.lockfile)
		if not self.env.NO_LOCK_IN_OUT:
			env.store(Context.out_dir+os.sep+Options.lockfile)
	def prepare_env(self,env):
		if not env.PREFIX:
			if Options.options.prefix or Utils.is_win32:
				env.PREFIX=os.path.abspath(os.path.expanduser(Options.options.prefix))
			else:
				env.PREFIX=''
		if not env.BINDIR:
			env.BINDIR=Utils.subst_vars('${PREFIX}/bin',env)
		if not env.LIBDIR:
			env.LIBDIR=Utils.subst_vars('${PREFIX}/lib',env)
	def store(self):
		n=self.cachedir.make_node('build.config.py')
		n.write('version = 0x%x\ntools = %r\n'%(Context.HEXVERSION,self.tools))
		if not self.all_envs:
			self.fatal('nothing to store in the configuration context!')
		for key in self.all_envs:
			tmpenv=self.all_envs[key]
			tmpenv.store(os.path.join(self.cachedir.abspath(),key+Build.CACHE_SUFFIX))
	def load(self,input,tooldir=None,funs=None,download=True):
		tools=Utils.to_list(input)
		if tooldir:tooldir=Utils.to_list(tooldir)
		for tool in tools:
			mag=(tool,id(self.env),funs)
			if mag in self.tool_cache:
				self.to_log('(tool %s is already loaded, skipping)'%tool)
				continue
			self.tool_cache.append(mag)
			module=None
			try:
				module=Context.load_tool(tool,tooldir)
			except ImportError ,e:
				if Options.options.download:
					module=download_tool(tool,ctx=self)
					if not module:
						self.fatal('Could not load the Waf tool %r or download a suitable replacement from the repository (sys.path %r)\n%s'%(tool,sys.path,e))
				else:
					self.fatal('Could not load the Waf tool %r from %r (try the --download option?):\n%s'%(tool,sys.path,e))
			except Exception ,e:
				self.to_log('imp %r (%r & %r)'%(tool,tooldir,funs))
				self.to_log(Utils.ex_stack())
				raise
			if funs is not None:
				self.eval_rules(funs)
			else:
				func=getattr(module,'configure',None)
				if func:
					if type(func)is type(Utils.readf):func(self)
					else:self.eval_rules(func)
			self.tools.append({'tool':tool,'tooldir':tooldir,'funs':funs})
	def post_recurse(self,node):
		super(ConfigurationContext,self).post_recurse(node)
		self.hash=Utils.h_list((self.hash,node.read('rb')))
		self.files.append(node.abspath())
	def eval_rules(self,rules):
		self.rules=Utils.to_list(rules)
		for x in self.rules:
			f=getattr(self,x)
			if not f:self.fatal("No such method '%s'."%x)
			try:
				f()
			except Exception ,e:
				ret=self.err_handler(x,e)
				if ret==BREAK:
					break
				elif ret==CONTINUE:
					continue
				else:
					raise
	def err_handler(self,fun,error):
		pass
def conf(f):
	def fun(*k,**kw):
		mandatory=True
		if'mandatory'in kw:
			mandatory=kw['mandatory']
			del kw['mandatory']
		try:
			return f(*k,**kw)
		except Errors.ConfigurationError:
			if mandatory:
				raise
	setattr(ConfigurationContext,f.__name__,fun)
	setattr(Build.BuildContext,f.__name__,fun)
	return f
@conf
def add_os_flags(self,var,dest=None):
	try:self.env.append_value(dest or var,shlex.split(self.environ[var]))
	except KeyError:pass
@conf
def cmd_to_list(self,cmd):
	if isinstance(cmd,str)and cmd.find(' '):
		try:
			os.stat(cmd)
		except OSError:
			return shlex.split(cmd)
		else:
			return[cmd]
	return cmd
@conf
def check_waf_version(self,mini='1.6.99',maxi='1.8.0'):
	self.start_msg('Checking for waf version in %s-%s'%(str(mini),str(maxi)))
	ver=Context.HEXVERSION
	if Utils.num2ver(mini)>ver:
		self.fatal('waf version should be at least %r (%r found)'%(Utils.num2ver(mini),ver))
	if Utils.num2ver(maxi)<ver:
		self.fatal('waf version should be at most %r (%r found)'%(Utils.num2ver(maxi),ver))
	self.end_msg('ok')
@conf
def find_file(self,filename,path_list=[]):
	for n in Utils.to_list(filename):
		for d in Utils.to_list(path_list):
			p=os.path.join(d,n)
			if os.path.exists(p):
				return p
	self.fatal('Could not find %r'%filename)
@conf
def find_program(self,filename,**kw):
	exts=kw.get('exts',Utils.is_win32 and'.exe,.com,.bat,.cmd'or',.sh,.pl,.py')
	environ=kw.get('environ',os.environ)
	ret=''
	filename=Utils.to_list(filename)
	var=kw.get('var','')
	if not var:
		var=filename[0].upper()
	if self.env[var]:
		ret=self.env[var]
	elif var in environ:
		ret=environ[var]
	path_list=kw.get('path_list','')
	if not ret:
		if path_list:
			path_list=Utils.to_list(path_list)
		else:
			path_list=environ.get('PATH','').split(os.pathsep)
		if not isinstance(filename,list):
			filename=[filename]
		for a in exts.split(','):
			if ret:
				break
			for b in filename:
				if ret:
					break
				for c in path_list:
					if ret:
						break
					x=os.path.expanduser(os.path.join(c,b+a))
					if os.path.isfile(x):
						ret=x
	if not ret and Utils.winreg:
		ret=Utils.get_registry_app_path(Utils.winreg.HKEY_CURRENT_USER,filename)
	if not ret and Utils.winreg:
		ret=Utils.get_registry_app_path(Utils.winreg.HKEY_LOCAL_MACHINE,filename)
	self.msg('Checking for program '+','.join(filename),ret or False)
	self.to_log('find program=%r paths=%r var=%r -> %r'%(filename,path_list,var,ret))
	if not ret:
		self.fatal(kw.get('errmsg','')or'Could not find the program %s'%','.join(filename))
	if var:
		self.env[var]=ret
	return ret
@conf
def find_perl_program(self,filename,path_list=[],var=None,environ=None,exts=''):
	try:
		app=self.find_program(filename,path_list=path_list,var=var,environ=environ,exts=exts)
	except Exception:
		self.find_program('perl',var='PERL')
		app=self.find_file(filename,os.environ['PATH'].split(os.pathsep))
		if not app:
			raise
		if var:
			self.env[var]=Utils.to_list(self.env['PERL'])+[app]
	self.msg('Checking for %r'%filename,app)

########NEW FILE########
__FILENAME__ = Context
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import os,imp,sys
from waflib import Utils,Errors,Logs
import waflib.Node
HEXVERSION=0x1070f00
WAFVERSION="1.7.15"
WAFREVISION="f63ac9793de2d4eaae884e55d4ff70a761dcbab2"
ABI=98
DBFILE='.wafpickle-%s-%d-%d'%(sys.platform,sys.hexversion,ABI)
APPNAME='APPNAME'
VERSION='VERSION'
TOP='top'
OUT='out'
WSCRIPT_FILE='wscript'
launch_dir=''
run_dir=''
top_dir=''
out_dir=''
waf_dir=''
local_repo=''
remote_repo='http://waf.googlecode.com/git/'
remote_locs=['waflib/extras','waflib/Tools']
g_module=None
STDOUT=1
STDERR=-1
BOTH=0
classes=[]
def create_context(cmd_name,*k,**kw):
	global classes
	for x in classes:
		if x.cmd==cmd_name:
			return x(*k,**kw)
	ctx=Context(*k,**kw)
	ctx.fun=cmd_name
	return ctx
class store_context(type):
	def __init__(cls,name,bases,dict):
		super(store_context,cls).__init__(name,bases,dict)
		name=cls.__name__
		if name=='ctx'or name=='Context':
			return
		try:
			cls.cmd
		except AttributeError:
			raise Errors.WafError('Missing command for the context class %r (cmd)'%name)
		if not getattr(cls,'fun',None):
			cls.fun=cls.cmd
		global classes
		classes.insert(0,cls)
ctx=store_context('ctx',(object,),{})
class Context(ctx):
	errors=Errors
	tools={}
	def __init__(self,**kw):
		try:
			rd=kw['run_dir']
		except KeyError:
			global run_dir
			rd=run_dir
		self.node_class=type("Nod3",(waflib.Node.Node,),{})
		self.node_class.__module__="waflib.Node"
		self.node_class.ctx=self
		self.root=self.node_class('',None)
		self.cur_script=None
		self.path=self.root.find_dir(rd)
		self.stack_path=[]
		self.exec_dict={'ctx':self,'conf':self,'bld':self,'opt':self}
		self.logger=None
	def __hash__(self):
		return id(self)
	def load(self,tool_list,*k,**kw):
		tools=Utils.to_list(tool_list)
		path=Utils.to_list(kw.get('tooldir',''))
		for t in tools:
			module=load_tool(t,path)
			fun=getattr(module,kw.get('name',self.fun),None)
			if fun:
				fun(self)
	def execute(self):
		global g_module
		self.recurse([os.path.dirname(g_module.root_path)])
	def pre_recurse(self,node):
		self.stack_path.append(self.cur_script)
		self.cur_script=node
		self.path=node.parent
	def post_recurse(self,node):
		self.cur_script=self.stack_path.pop()
		if self.cur_script:
			self.path=self.cur_script.parent
	def recurse(self,dirs,name=None,mandatory=True,once=True):
		try:
			cache=self.recurse_cache
		except AttributeError:
			cache=self.recurse_cache={}
		for d in Utils.to_list(dirs):
			if not os.path.isabs(d):
				d=os.path.join(self.path.abspath(),d)
			WSCRIPT=os.path.join(d,WSCRIPT_FILE)
			WSCRIPT_FUN=WSCRIPT+'_'+(name or self.fun)
			node=self.root.find_node(WSCRIPT_FUN)
			if node and(not once or node not in cache):
				cache[node]=True
				self.pre_recurse(node)
				try:
					function_code=node.read('rU')
					exec(compile(function_code,node.abspath(),'exec'),self.exec_dict)
				finally:
					self.post_recurse(node)
			elif not node:
				node=self.root.find_node(WSCRIPT)
				tup=(node,name or self.fun)
				if node and(not once or tup not in cache):
					cache[tup]=True
					self.pre_recurse(node)
					try:
						wscript_module=load_module(node.abspath())
						user_function=getattr(wscript_module,(name or self.fun),None)
						if not user_function:
							if not mandatory:
								continue
							raise Errors.WafError('No function %s defined in %s'%(name or self.fun,node.abspath()))
						user_function(self)
					finally:
						self.post_recurse(node)
				elif not node:
					if not mandatory:
						continue
					raise Errors.WafError('No wscript file in directory %s'%d)
	def exec_command(self,cmd,**kw):
		subprocess=Utils.subprocess
		kw['shell']=isinstance(cmd,str)
		Logs.debug('runner: %r'%cmd)
		Logs.debug('runner_env: kw=%s'%kw)
		if self.logger:
			self.logger.info(cmd)
		if'stdout'not in kw:
			kw['stdout']=subprocess.PIPE
		if'stderr'not in kw:
			kw['stderr']=subprocess.PIPE
		try:
			if kw['stdout']or kw['stderr']:
				p=subprocess.Popen(cmd,**kw)
				(out,err)=p.communicate()
				ret=p.returncode
			else:
				out,err=(None,None)
				ret=subprocess.Popen(cmd,**kw).wait()
		except Exception ,e:
			raise Errors.WafError('Execution failure: %s'%str(e),ex=e)
		if out:
			if not isinstance(out,str):
				out=out.decode(sys.stdout.encoding or'iso8859-1')
			if self.logger:
				self.logger.debug('out: %s'%out)
			else:
				sys.stdout.write(out)
		if err:
			if not isinstance(err,str):
				err=err.decode(sys.stdout.encoding or'iso8859-1')
			if self.logger:
				self.logger.error('err: %s'%err)
			else:
				sys.stderr.write(err)
		return ret
	def cmd_and_log(self,cmd,**kw):
		subprocess=Utils.subprocess
		kw['shell']=isinstance(cmd,str)
		Logs.debug('runner: %r'%cmd)
		if'quiet'in kw:
			quiet=kw['quiet']
			del kw['quiet']
		else:
			quiet=None
		if'output'in kw:
			to_ret=kw['output']
			del kw['output']
		else:
			to_ret=STDOUT
		kw['stdout']=kw['stderr']=subprocess.PIPE
		if quiet is None:
			self.to_log(cmd)
		try:
			p=subprocess.Popen(cmd,**kw)
			(out,err)=p.communicate()
		except Exception ,e:
			raise Errors.WafError('Execution failure: %s'%str(e),ex=e)
		if not isinstance(out,str):
			out=out.decode(sys.stdout.encoding or'iso8859-1')
		if not isinstance(err,str):
			err=err.decode(sys.stdout.encoding or'iso8859-1')
		if out and quiet!=STDOUT and quiet!=BOTH:
			self.to_log('out: %s'%out)
		if err and quiet!=STDERR and quiet!=BOTH:
			self.to_log('err: %s'%err)
		if p.returncode:
			e=Errors.WafError('Command %r returned %r'%(cmd,p.returncode))
			e.returncode=p.returncode
			e.stderr=err
			e.stdout=out
			raise e
		if to_ret==BOTH:
			return(out,err)
		elif to_ret==STDERR:
			return err
		return out
	def fatal(self,msg,ex=None):
		if self.logger:
			self.logger.info('from %s: %s'%(self.path.abspath(),msg))
		try:
			msg='%s\n(complete log in %s)'%(msg,self.logger.handlers[0].baseFilename)
		except Exception:
			pass
		raise self.errors.ConfigurationError(msg,ex=ex)
	def to_log(self,msg):
		if not msg:
			return
		if self.logger:
			self.logger.info(msg)
		else:
			sys.stderr.write(str(msg))
			sys.stderr.flush()
	def msg(self,msg,result,color=None):
		self.start_msg(msg)
		if not isinstance(color,str):
			color=result and'GREEN'or'YELLOW'
		self.end_msg(result,color)
	def start_msg(self,msg):
		try:
			if self.in_msg:
				self.in_msg+=1
				return
		except AttributeError:
			self.in_msg=0
		self.in_msg+=1
		try:
			self.line_just=max(self.line_just,len(msg))
		except AttributeError:
			self.line_just=max(40,len(msg))
		for x in(self.line_just*'-',msg):
			self.to_log(x)
		Logs.pprint('NORMAL',"%s :"%msg.ljust(self.line_just),sep='')
	def end_msg(self,result,color=None):
		self.in_msg-=1
		if self.in_msg:
			return
		defcolor='GREEN'
		if result==True:
			msg='ok'
		elif result==False:
			msg='not found'
			defcolor='YELLOW'
		else:
			msg=str(result)
		self.to_log(msg)
		Logs.pprint(color or defcolor,msg)
	def load_special_tools(self,var,ban=[]):
		global waf_dir
		lst=self.root.find_node(waf_dir).find_node('waflib/extras').ant_glob(var)
		for x in lst:
			if not x.name in ban:
				load_tool(x.name.replace('.py',''))
cache_modules={}
def load_module(path):
	try:
		return cache_modules[path]
	except KeyError:
		pass
	module=imp.new_module(WSCRIPT_FILE)
	try:
		code=Utils.readf(path,m='rU')
	except(IOError,OSError):
		raise Errors.WafError('Could not read the file %r'%path)
	module_dir=os.path.dirname(path)
	sys.path.insert(0,module_dir)
	exec(compile(code,path,'exec'),module.__dict__)
	sys.path.remove(module_dir)
	cache_modules[path]=module
	return module
def load_tool(tool,tooldir=None):
	if tool=='java':
		tool='javaw'
	elif tool=='compiler_cc':
		tool='compiler_c'
	else:
		tool=tool.replace('++','xx')
	if tooldir:
		assert isinstance(tooldir,list)
		sys.path=tooldir+sys.path
		try:
			__import__(tool)
			ret=sys.modules[tool]
			Context.tools[tool]=ret
			return ret
		finally:
			for d in tooldir:
				sys.path.remove(d)
	else:
		global waf_dir
		try:
			os.stat(os.path.join(waf_dir,'waflib','extras',tool+'.py'))
		except OSError:
			try:
				os.stat(os.path.join(waf_dir,'waflib','Tools',tool+'.py'))
			except OSError:
				d=tool
			else:
				d='waflib.Tools.%s'%tool
		else:
			d='waflib.extras.%s'%tool
		__import__(d)
		ret=sys.modules[d]
		Context.tools[tool]=ret
		return ret

########NEW FILE########
__FILENAME__ = Errors
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import traceback,sys
class WafError(Exception):
	def __init__(self,msg='',ex=None):
		self.msg=msg
		assert not isinstance(msg,Exception)
		self.stack=[]
		if ex:
			if not msg:
				self.msg=str(ex)
			if isinstance(ex,WafError):
				self.stack=ex.stack
			else:
				self.stack=traceback.extract_tb(sys.exc_info()[2])
		self.stack+=traceback.extract_stack()[:-1]
		self.verbose_msg=''.join(traceback.format_list(self.stack))
	def __str__(self):
		return str(self.msg)
class BuildError(WafError):
	def __init__(self,error_tasks=[]):
		self.tasks=error_tasks
		WafError.__init__(self,self.format_error())
	def format_error(self):
		lst=['Build failed']
		for tsk in self.tasks:
			txt=tsk.format_error()
			if txt:lst.append(txt)
		return'\n'.join(lst)
class ConfigurationError(WafError):
	pass
class TaskRescan(WafError):
	pass
class TaskNotReady(WafError):
	pass

########NEW FILE########
__FILENAME__ = compat15
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import sys
from waflib import ConfigSet,Logs,Options,Scripting,Task,Build,Configure,Node,Runner,TaskGen,Utils,Errors,Context
sys.modules['Environment']=ConfigSet
ConfigSet.Environment=ConfigSet.ConfigSet
sys.modules['Logs']=Logs
sys.modules['Options']=Options
sys.modules['Scripting']=Scripting
sys.modules['Task']=Task
sys.modules['Build']=Build
sys.modules['Configure']=Configure
sys.modules['Node']=Node
sys.modules['Runner']=Runner
sys.modules['TaskGen']=TaskGen
sys.modules['Utils']=Utils
from waflib.Tools import c_preproc
sys.modules['preproc']=c_preproc
from waflib.Tools import c_config
sys.modules['config_c']=c_config
ConfigSet.ConfigSet.copy=ConfigSet.ConfigSet.derive
ConfigSet.ConfigSet.set_variant=Utils.nada
Build.BuildContext.add_subdirs=Build.BuildContext.recurse
Build.BuildContext.new_task_gen=Build.BuildContext.__call__
Build.BuildContext.is_install=0
Node.Node.relpath_gen=Node.Node.path_from
def name_to_obj(self,s,env=None):
	Logs.warn('compat: change "name_to_obj(name, env)" by "get_tgen_by_name(name)"')
	return self.get_tgen_by_name(s)
Build.BuildContext.name_to_obj=name_to_obj
def env_of_name(self,name):
	try:
		return self.all_envs[name]
	except KeyError:
		Logs.error('no such environment: '+name)
		return None
Build.BuildContext.env_of_name=env_of_name
def set_env_name(self,name,env):
	self.all_envs[name]=env
	return env
Configure.ConfigurationContext.set_env_name=set_env_name
def retrieve(self,name,fromenv=None):
	try:
		env=self.all_envs[name]
	except KeyError:
		env=ConfigSet.ConfigSet()
		self.prepare_env(env)
		self.all_envs[name]=env
	else:
		if fromenv:Logs.warn("The environment %s may have been configured already"%name)
	return env
Configure.ConfigurationContext.retrieve=retrieve
Configure.ConfigurationContext.sub_config=Configure.ConfigurationContext.recurse
Configure.ConfigurationContext.check_tool=Configure.ConfigurationContext.load
Configure.conftest=Configure.conf
Configure.ConfigurationError=Errors.ConfigurationError
Options.OptionsContext.sub_options=Options.OptionsContext.recurse
Options.OptionsContext.tool_options=Context.Context.load
Options.Handler=Options.OptionsContext
Task.simple_task_type=Task.task_type_from_func=Task.task_factory
Task.TaskBase.classes=Task.classes
def setitem(self,key,value):
	if key.startswith('CCFLAGS'):
		key=key[1:]
	self.table[key]=value
ConfigSet.ConfigSet.__setitem__=setitem
@TaskGen.feature('d')
@TaskGen.before('apply_incpaths')
def old_importpaths(self):
	if getattr(self,'importpaths',[]):
		self.includes=self.importpaths
from waflib import Context
eld=Context.load_tool
def load_tool(*k,**kw):
	ret=eld(*k,**kw)
	if'set_options'in ret.__dict__:
		Logs.warn('compat: rename "set_options" to options')
		ret.options=ret.set_options
	if'detect'in ret.__dict__:
		Logs.warn('compat: rename "detect" to "configure"')
		ret.configure=ret.detect
	return ret
Context.load_tool=load_tool
rev=Context.load_module
def load_module(path):
	ret=rev(path)
	if'set_options'in ret.__dict__:
		Logs.warn('compat: rename "set_options" to "options" (%r)'%path)
		ret.options=ret.set_options
	if'srcdir'in ret.__dict__:
		Logs.warn('compat: rename "srcdir" to "top" (%r)'%path)
		ret.top=ret.srcdir
	if'blddir'in ret.__dict__:
		Logs.warn('compat: rename "blddir" to "out" (%r)'%path)
		ret.out=ret.blddir
	return ret
Context.load_module=load_module
old_post=TaskGen.task_gen.post
def post(self):
	self.features=self.to_list(self.features)
	if'cc'in self.features:
		Logs.warn('compat: the feature cc does not exist anymore (use "c")')
		self.features.remove('cc')
		self.features.append('c')
	if'cstaticlib'in self.features:
		Logs.warn('compat: the feature cstaticlib does not exist anymore (use "cstlib" or "cxxstlib")')
		self.features.remove('cstaticlib')
		self.features.append(('cxx'in self.features)and'cxxstlib'or'cstlib')
	if getattr(self,'ccflags',None):
		Logs.warn('compat: "ccflags" was renamed to "cflags"')
		self.cflags=self.ccflags
	return old_post(self)
TaskGen.task_gen.post=post
def waf_version(*k,**kw):
	Logs.warn('wrong version (waf_version was removed in waf 1.6)')
Utils.waf_version=waf_version
import os
@TaskGen.feature('c','cxx','d')
@TaskGen.before('apply_incpaths','propagate_uselib_vars')
@TaskGen.after('apply_link','process_source')
def apply_uselib_local(self):
	env=self.env
	from waflib.Tools.ccroot import stlink_task
	self.uselib=self.to_list(getattr(self,'uselib',[]))
	self.includes=self.to_list(getattr(self,'includes',[]))
	names=self.to_list(getattr(self,'uselib_local',[]))
	get=self.bld.get_tgen_by_name
	seen=set([])
	tmp=Utils.deque(names)
	if tmp:
		Logs.warn('compat: "uselib_local" is deprecated, replace by "use"')
	while tmp:
		lib_name=tmp.popleft()
		if lib_name in seen:
			continue
		y=get(lib_name)
		y.post()
		seen.add(lib_name)
		if getattr(y,'uselib_local',None):
			for x in self.to_list(getattr(y,'uselib_local',[])):
				obj=get(x)
				obj.post()
				if getattr(obj,'link_task',None):
					if not isinstance(obj.link_task,stlink_task):
						tmp.append(x)
		if getattr(y,'link_task',None):
			link_name=y.target[y.target.rfind(os.sep)+1:]
			if isinstance(y.link_task,stlink_task):
				env.append_value('STLIB',[link_name])
			else:
				env.append_value('LIB',[link_name])
			self.link_task.set_run_after(y.link_task)
			self.link_task.dep_nodes+=y.link_task.outputs
			tmp_path=y.link_task.outputs[0].parent.bldpath()
			if not tmp_path in env['LIBPATH']:
				env.prepend_value('LIBPATH',[tmp_path])
		for v in self.to_list(getattr(y,'uselib',[])):
			if not env['STLIB_'+v]:
				if not v in self.uselib:
					self.uselib.insert(0,v)
		if getattr(y,'export_includes',None):
			self.includes.extend(y.to_incnodes(y.export_includes))
@TaskGen.feature('cprogram','cxxprogram','cstlib','cxxstlib','cshlib','cxxshlib','dprogram','dstlib','dshlib')
@TaskGen.after('apply_link')
def apply_objdeps(self):
	names=getattr(self,'add_objects',[])
	if not names:
		return
	names=self.to_list(names)
	get=self.bld.get_tgen_by_name
	seen=[]
	while names:
		x=names[0]
		if x in seen:
			names=names[1:]
			continue
		y=get(x)
		if getattr(y,'add_objects',None):
			added=0
			lst=y.to_list(y.add_objects)
			lst.reverse()
			for u in lst:
				if u in seen:continue
				added=1
				names=[u]+names
			if added:continue
		y.post()
		seen.append(x)
		for t in getattr(y,'compiled_tasks',[]):
			self.link_task.inputs.extend(t.outputs)
@TaskGen.after('apply_link')
def process_obj_files(self):
	if not hasattr(self,'obj_files'):
		return
	for x in self.obj_files:
		node=self.path.find_resource(x)
		self.link_task.inputs.append(node)
@TaskGen.taskgen_method
def add_obj_file(self,file):
	if not hasattr(self,'obj_files'):self.obj_files=[]
	if not'process_obj_files'in self.meths:self.meths.append('process_obj_files')
	self.obj_files.append(file)
old_define=Configure.ConfigurationContext.__dict__['define']
@Configure.conf
def define(self,key,val,quote=True):
	old_define(self,key,val,quote)
	if key.startswith('HAVE_'):
		self.env[key]=1
old_undefine=Configure.ConfigurationContext.__dict__['undefine']
@Configure.conf
def undefine(self,key):
	old_undefine(self,key)
	if key.startswith('HAVE_'):
		self.env[key]=0
def set_incdirs(self,val):
	Logs.warn('compat: change "export_incdirs" by "export_includes"')
	self.export_includes=val
TaskGen.task_gen.export_incdirs=property(None,set_incdirs)

########NEW FILE########
__FILENAME__ = fixpy2
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import os
all_modifs={}
def fixdir(dir):
	global all_modifs
	for k in all_modifs:
		for v in all_modifs[k]:
			modif(os.path.join(dir,'waflib'),k,v)
def modif(dir,name,fun):
	if name=='*':
		lst=[]
		for y in'. Tools extras'.split():
			for x in os.listdir(os.path.join(dir,y)):
				if x.endswith('.py'):
					lst.append(y+os.sep+x)
		for x in lst:
			modif(dir,x,fun)
		return
	filename=os.path.join(dir,name)
	f=open(filename,'r')
	try:
		txt=f.read()
	finally:
		f.close()
	txt=fun(txt)
	f=open(filename,'w')
	try:
		f.write(txt)
	finally:
		f.close()
def subst(*k):
	def do_subst(fun):
		global all_modifs
		for x in k:
			try:
				all_modifs[x].append(fun)
			except KeyError:
				all_modifs[x]=[fun]
		return fun
	return do_subst
@subst('*')
def r1(code):
	code=code.replace(',e:',',e:')
	code=code.replace("",'')
	code=code.replace('','')
	return code
@subst('Runner.py')
def r4(code):
	code=code.replace('next(self.biter)','self.biter.next()')
	return code

########NEW FILE########
__FILENAME__ = Logs
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import os,re,traceback,sys
_nocolor=os.environ.get('NOCOLOR','no')not in('no','0','false')
try:
	if not _nocolor:
		import waflib.ansiterm
except ImportError:
	pass
try:
	import threading
except ImportError:
	if not'JOBS'in os.environ:
		os.environ['JOBS']='1'
else:
	wlock=threading.Lock()
	class sync_stream(object):
		def __init__(self,stream):
			self.stream=stream
			self.encoding=self.stream.encoding
		def write(self,txt):
			try:
				wlock.acquire()
				self.stream.write(txt)
				self.stream.flush()
			finally:
				wlock.release()
		def fileno(self):
			return self.stream.fileno()
		def flush(self):
			self.stream.flush()
		def isatty(self):
			return self.stream.isatty()
	if not os.environ.get('NOSYNC',False):
		if id(sys.stdout)==id(sys.__stdout__):
			sys.stdout=sync_stream(sys.stdout)
			sys.stderr=sync_stream(sys.stderr)
import logging
LOG_FORMAT="%(asctime)s %(c1)s%(zone)s%(c2)s %(message)s"
HOUR_FORMAT="%H:%M:%S"
zones=''
verbose=0
colors_lst={'USE':True,'BOLD':'\x1b[01;1m','RED':'\x1b[01;31m','GREEN':'\x1b[32m','YELLOW':'\x1b[33m','PINK':'\x1b[35m','BLUE':'\x1b[01;34m','CYAN':'\x1b[36m','NORMAL':'\x1b[0m','cursor_on':'\x1b[?25h','cursor_off':'\x1b[?25l',}
got_tty=not os.environ.get('TERM','dumb')in['dumb','emacs']
if got_tty:
	try:
		got_tty=sys.stderr.isatty()and sys.stdout.isatty()
	except AttributeError:
		got_tty=False
if(not got_tty and os.environ.get('TERM','dumb')!='msys')or _nocolor:
	colors_lst['USE']=False
def get_term_cols():
	return 80
try:
	import struct,fcntl,termios
except ImportError:
	pass
else:
	if got_tty:
		def get_term_cols_real():
			dummy_lines,cols=struct.unpack("HHHH",fcntl.ioctl(sys.stderr.fileno(),termios.TIOCGWINSZ,struct.pack("HHHH",0,0,0,0)))[:2]
			return cols
		try:
			get_term_cols_real()
		except Exception:
			pass
		else:
			get_term_cols=get_term_cols_real
get_term_cols.__doc__="""
	Get the console width in characters.

	:return: the number of characters per line
	:rtype: int
	"""
def get_color(cl):
	if not colors_lst['USE']:return''
	return colors_lst.get(cl,'')
class color_dict(object):
	def __getattr__(self,a):
		return get_color(a)
	def __call__(self,a):
		return get_color(a)
colors=color_dict()
re_log=re.compile(r'(\w+): (.*)',re.M)
class log_filter(logging.Filter):
	def __init__(self,name=None):
		pass
	def filter(self,rec):
		rec.c1=colors.PINK
		rec.c2=colors.NORMAL
		rec.zone=rec.module
		if rec.levelno>=logging.INFO:
			if rec.levelno>=logging.ERROR:
				rec.c1=colors.RED
			elif rec.levelno>=logging.WARNING:
				rec.c1=colors.YELLOW
			else:
				rec.c1=colors.GREEN
			return True
		m=re_log.match(rec.msg)
		if m:
			rec.zone=m.group(1)
			rec.msg=m.group(2)
		if zones:
			return getattr(rec,'zone','')in zones or'*'in zones
		elif not verbose>2:
			return False
		return True
class formatter(logging.Formatter):
	def __init__(self):
		logging.Formatter.__init__(self,LOG_FORMAT,HOUR_FORMAT)
	def format(self,rec):
		if rec.levelno>=logging.WARNING or rec.levelno==logging.INFO:
			try:
				msg=rec.msg.decode('utf-8')
			except Exception:
				msg=rec.msg
			return'%s%s%s'%(rec.c1,msg,rec.c2)
		return logging.Formatter.format(self,rec)
log=None
def debug(*k,**kw):
	if verbose:
		k=list(k)
		k[0]=k[0].replace('\n',' ')
		global log
		log.debug(*k,**kw)
def error(*k,**kw):
	global log
	log.error(*k,**kw)
	if verbose>2:
		st=traceback.extract_stack()
		if st:
			st=st[:-1]
			buf=[]
			for filename,lineno,name,line in st:
				buf.append('  File "%s", line %d, in %s'%(filename,lineno,name))
				if line:
					buf.append('	%s'%line.strip())
			if buf:log.error("\n".join(buf))
def warn(*k,**kw):
	global log
	log.warn(*k,**kw)
def info(*k,**kw):
	global log
	log.info(*k,**kw)
def init_log():
	global log
	log=logging.getLogger('waflib')
	log.handlers=[]
	log.filters=[]
	hdlr=logging.StreamHandler()
	hdlr.setFormatter(formatter())
	log.addHandler(hdlr)
	log.addFilter(log_filter())
	log.setLevel(logging.DEBUG)
def make_logger(path,name):
	logger=logging.getLogger(name)
	hdlr=logging.FileHandler(path,'w')
	formatter=logging.Formatter('%(message)s')
	hdlr.setFormatter(formatter)
	logger.addHandler(hdlr)
	logger.setLevel(logging.DEBUG)
	return logger
def make_mem_logger(name,to_log,size=10000):
	from logging.handlers import MemoryHandler
	logger=logging.getLogger(name)
	hdlr=MemoryHandler(size,target=to_log)
	formatter=logging.Formatter('%(message)s')
	hdlr.setFormatter(formatter)
	logger.addHandler(hdlr)
	logger.memhandler=hdlr
	logger.setLevel(logging.DEBUG)
	return logger
def pprint(col,str,label='',sep='\n'):
	sys.stderr.write("%s%s%s %s%s"%(colors(col),str,colors.NORMAL,label,sep))

########NEW FILE########
__FILENAME__ = Node
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import os,re,sys,shutil
from waflib import Utils,Errors
exclude_regs='''
**/*~
**/#*#
**/.#*
**/%*%
**/._*
**/CVS
**/CVS/**
**/.cvsignore
**/SCCS
**/SCCS/**
**/vssver.scc
**/.svn
**/.svn/**
**/BitKeeper
**/.git
**/.git/**
**/.gitignore
**/.bzr
**/.bzrignore
**/.bzr/**
**/.hg
**/.hg/**
**/_MTN
**/_MTN/**
**/.arch-ids
**/{arch}
**/_darcs
**/_darcs/**
**/.intlcache
**/.DS_Store'''
def split_path(path):
	return path.split('/')
def split_path_cygwin(path):
	if path.startswith('//'):
		ret=path.split('/')[2:]
		ret[0]='/'+ret[0]
		return ret
	return path.split('/')
re_sp=re.compile('[/\\\\]')
def split_path_win32(path):
	if path.startswith('\\\\'):
		ret=re.split(re_sp,path)[2:]
		ret[0]='\\'+ret[0]
		return ret
	return re.split(re_sp,path)
if sys.platform=='cygwin':
	split_path=split_path_cygwin
elif Utils.is_win32:
	split_path=split_path_win32
class Node(object):
	__slots__=('name','sig','children','parent','cache_abspath','cache_isdir','cache_sig')
	def __init__(self,name,parent):
		self.name=name
		self.parent=parent
		if parent:
			if name in parent.children:
				raise Errors.WafError('node %s exists in the parent files %r already'%(name,parent))
			parent.children[name]=self
	def __setstate__(self,data):
		self.name=data[0]
		self.parent=data[1]
		if data[2]is not None:
			self.children=data[2]
		if data[3]is not None:
			self.sig=data[3]
	def __getstate__(self):
		return(self.name,self.parent,getattr(self,'children',None),getattr(self,'sig',None))
	def __str__(self):
		return self.name
	def __repr__(self):
		return self.abspath()
	def __hash__(self):
		return id(self)
	def __eq__(self,node):
		return id(self)==id(node)
	def __copy__(self):
		raise Errors.WafError('nodes are not supposed to be copied')
	def read(self,flags='r',encoding='ISO8859-1'):
		return Utils.readf(self.abspath(),flags,encoding)
	def write(self,data,flags='w',encoding='ISO8859-1'):
		Utils.writef(self.abspath(),data,flags,encoding)
	def chmod(self,val):
		os.chmod(self.abspath(),val)
	def delete(self):
		try:
			if hasattr(self,'children'):
				shutil.rmtree(self.abspath())
			else:
				os.remove(self.abspath())
		except OSError:
			pass
		self.evict()
	def evict(self):
		del self.parent.children[self.name]
	def suffix(self):
		k=max(0,self.name.rfind('.'))
		return self.name[k:]
	def height(self):
		d=self
		val=-1
		while d:
			d=d.parent
			val+=1
		return val
	def listdir(self):
		lst=Utils.listdir(self.abspath())
		lst.sort()
		return lst
	def mkdir(self):
		if getattr(self,'cache_isdir',None):
			return
		try:
			self.parent.mkdir()
		except OSError:
			pass
		if self.name:
			try:
				os.makedirs(self.abspath())
			except OSError:
				pass
			if not os.path.isdir(self.abspath()):
				raise Errors.WafError('Could not create the directory %s'%self.abspath())
			try:
				self.children
			except AttributeError:
				self.children={}
		self.cache_isdir=True
	def find_node(self,lst):
		if isinstance(lst,str):
			lst=[x for x in split_path(lst)if x and x!='.']
		cur=self
		for x in lst:
			if x=='..':
				cur=cur.parent or cur
				continue
			try:
				ch=cur.children
			except AttributeError:
				cur.children={}
			else:
				try:
					cur=cur.children[x]
					continue
				except KeyError:
					pass
			cur=self.__class__(x,cur)
			try:
				os.stat(cur.abspath())
			except OSError:
				cur.evict()
				return None
		ret=cur
		try:
			os.stat(ret.abspath())
		except OSError:
			ret.evict()
			return None
		try:
			while not getattr(cur.parent,'cache_isdir',None):
				cur=cur.parent
				cur.cache_isdir=True
		except AttributeError:
			pass
		return ret
	def make_node(self,lst):
		if isinstance(lst,str):
			lst=[x for x in split_path(lst)if x and x!='.']
		cur=self
		for x in lst:
			if x=='..':
				cur=cur.parent or cur
				continue
			if getattr(cur,'children',{}):
				if x in cur.children:
					cur=cur.children[x]
					continue
			else:
				cur.children={}
			cur=self.__class__(x,cur)
		return cur
	def search_node(self,lst):
		if isinstance(lst,str):
			lst=[x for x in split_path(lst)if x and x!='.']
		cur=self
		for x in lst:
			if x=='..':
				cur=cur.parent or cur
			else:
				try:
					cur=cur.children[x]
				except(AttributeError,KeyError):
					return None
		return cur
	def path_from(self,node):
		c1=self
		c2=node
		c1h=c1.height()
		c2h=c2.height()
		lst=[]
		up=0
		while c1h>c2h:
			lst.append(c1.name)
			c1=c1.parent
			c1h-=1
		while c2h>c1h:
			up+=1
			c2=c2.parent
			c2h-=1
		while id(c1)!=id(c2):
			lst.append(c1.name)
			up+=1
			c1=c1.parent
			c2=c2.parent
		for i in range(up):
			lst.append('..')
		lst.reverse()
		return os.sep.join(lst)or'.'
	def abspath(self):
		try:
			return self.cache_abspath
		except AttributeError:
			pass
		if os.sep=='/':
			if not self.parent:
				val=os.sep
			elif not self.parent.name:
				val=os.sep+self.name
			else:
				val=self.parent.abspath()+os.sep+self.name
		else:
			if not self.parent:
				val=''
			elif not self.parent.name:
				val=self.name+os.sep
			else:
				val=self.parent.abspath().rstrip(os.sep)+os.sep+self.name
		self.cache_abspath=val
		return val
	def is_child_of(self,node):
		p=self
		diff=self.height()-node.height()
		while diff>0:
			diff-=1
			p=p.parent
		return id(p)==id(node)
	def ant_iter(self,accept=None,maxdepth=25,pats=[],dir=False,src=True,remove=True):
		dircont=self.listdir()
		dircont.sort()
		try:
			lst=set(self.children.keys())
		except AttributeError:
			self.children={}
		else:
			if remove:
				for x in lst-set(dircont):
					self.children[x].evict()
		for name in dircont:
			npats=accept(name,pats)
			if npats and npats[0]:
				accepted=[]in npats[0]
				node=self.make_node([name])
				isdir=os.path.isdir(node.abspath())
				if accepted:
					if isdir:
						if dir:
							yield node
					else:
						if src:
							yield node
				if getattr(node,'cache_isdir',None)or isdir:
					node.cache_isdir=True
					if maxdepth:
						for k in node.ant_iter(accept=accept,maxdepth=maxdepth-1,pats=npats,dir=dir,src=src,remove=remove):
							yield k
		raise StopIteration
	def ant_glob(self,*k,**kw):
		src=kw.get('src',True)
		dir=kw.get('dir',False)
		excl=kw.get('excl',exclude_regs)
		incl=k and k[0]or kw.get('incl','**')
		reflags=kw.get('ignorecase',0)and re.I
		def to_pat(s):
			lst=Utils.to_list(s)
			ret=[]
			for x in lst:
				x=x.replace('\\','/').replace('//','/')
				if x.endswith('/'):
					x+='**'
				lst2=x.split('/')
				accu=[]
				for k in lst2:
					if k=='**':
						accu.append(k)
					else:
						k=k.replace('.','[.]').replace('*','.*').replace('?','.').replace('+','\\+')
						k='^%s$'%k
						try:
							accu.append(re.compile(k,flags=reflags))
						except Exception ,e:
							raise Errors.WafError("Invalid pattern: %s"%k,e)
				ret.append(accu)
			return ret
		def filtre(name,nn):
			ret=[]
			for lst in nn:
				if not lst:
					pass
				elif lst[0]=='**':
					ret.append(lst)
					if len(lst)>1:
						if lst[1].match(name):
							ret.append(lst[2:])
					else:
						ret.append([])
				elif lst[0].match(name):
					ret.append(lst[1:])
			return ret
		def accept(name,pats):
			nacc=filtre(name,pats[0])
			nrej=filtre(name,pats[1])
			if[]in nrej:
				nacc=[]
			return[nacc,nrej]
		ret=[x for x in self.ant_iter(accept=accept,pats=[to_pat(incl),to_pat(excl)],maxdepth=kw.get('maxdepth',25),dir=dir,src=src,remove=kw.get('remove',True))]
		if kw.get('flat',False):
			return' '.join([x.path_from(self)for x in ret])
		return ret
	def is_src(self):
		cur=self
		x=id(self.ctx.srcnode)
		y=id(self.ctx.bldnode)
		while cur.parent:
			if id(cur)==y:
				return False
			if id(cur)==x:
				return True
			cur=cur.parent
		return False
	def is_bld(self):
		cur=self
		y=id(self.ctx.bldnode)
		while cur.parent:
			if id(cur)==y:
				return True
			cur=cur.parent
		return False
	def get_src(self):
		cur=self
		x=id(self.ctx.srcnode)
		y=id(self.ctx.bldnode)
		lst=[]
		while cur.parent:
			if id(cur)==y:
				lst.reverse()
				return self.ctx.srcnode.make_node(lst)
			if id(cur)==x:
				return self
			lst.append(cur.name)
			cur=cur.parent
		return self
	def get_bld(self):
		cur=self
		x=id(self.ctx.srcnode)
		y=id(self.ctx.bldnode)
		lst=[]
		while cur.parent:
			if id(cur)==y:
				return self
			if id(cur)==x:
				lst.reverse()
				return self.ctx.bldnode.make_node(lst)
			lst.append(cur.name)
			cur=cur.parent
		lst.reverse()
		if lst and Utils.is_win32 and len(lst[0])==2 and lst[0].endswith(':'):
			lst[0]=lst[0][0]
		return self.ctx.bldnode.make_node(['__root__']+lst)
	def find_resource(self,lst):
		if isinstance(lst,str):
			lst=[x for x in split_path(lst)if x and x!='.']
		node=self.get_bld().search_node(lst)
		if not node:
			self=self.get_src()
			node=self.find_node(lst)
		if node:
			if os.path.isdir(node.abspath()):
				return None
		return node
	def find_or_declare(self,lst):
		if isinstance(lst,str):
			lst=[x for x in split_path(lst)if x and x!='.']
		node=self.get_bld().search_node(lst)
		if node:
			if not os.path.isfile(node.abspath()):
				node.sig=None
				node.parent.mkdir()
			return node
		self=self.get_src()
		node=self.find_node(lst)
		if node:
			if not os.path.isfile(node.abspath()):
				node.sig=None
				node.parent.mkdir()
			return node
		node=self.get_bld().make_node(lst)
		node.parent.mkdir()
		return node
	def find_dir(self,lst):
		if isinstance(lst,str):
			lst=[x for x in split_path(lst)if x and x!='.']
		node=self.find_node(lst)
		try:
			if not os.path.isdir(node.abspath()):
				return None
		except(OSError,AttributeError):
			return None
		return node
	def change_ext(self,ext,ext_in=None):
		name=self.name
		if ext_in is None:
			k=name.rfind('.')
			if k>=0:
				name=name[:k]+ext
			else:
				name=name+ext
		else:
			name=name[:-len(ext_in)]+ext
		return self.parent.find_or_declare([name])
	def nice_path(self,env=None):
		return self.path_from(self.ctx.launch_node())
	def bldpath(self):
		return self.path_from(self.ctx.bldnode)
	def srcpath(self):
		return self.path_from(self.ctx.srcnode)
	def relpath(self):
		cur=self
		x=id(self.ctx.bldnode)
		while cur.parent:
			if id(cur)==x:
				return self.bldpath()
			cur=cur.parent
		return self.srcpath()
	def bld_dir(self):
		return self.parent.bldpath()
	def bld_base(self):
		s=os.path.splitext(self.name)[0]
		return self.bld_dir()+os.sep+s
	def get_bld_sig(self):
		try:
			return self.cache_sig
		except AttributeError:
			pass
		if not self.is_bld()or self.ctx.bldnode is self.ctx.srcnode:
			self.sig=Utils.h_file(self.abspath())
		self.cache_sig=ret=self.sig
		return ret
	search=search_node
pickle_lock=Utils.threading.Lock()
class Nod3(Node):
	pass

########NEW FILE########
__FILENAME__ = Options
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import os,tempfile,optparse,sys,re
from waflib import Logs,Utils,Context
cmds='distclean configure build install clean uninstall check dist distcheck'.split()
options={}
commands=[]
lockfile=os.environ.get('WAFLOCK','.lock-waf_%s_build'%sys.platform)
try:cache_global=os.path.abspath(os.environ['WAFCACHE'])
except KeyError:cache_global=''
platform=Utils.unversioned_sys_platform()
class opt_parser(optparse.OptionParser):
	def __init__(self,ctx):
		optparse.OptionParser.__init__(self,conflict_handler="resolve",version='waf %s (%s)'%(Context.WAFVERSION,Context.WAFREVISION))
		self.formatter.width=Logs.get_term_cols()
		p=self.add_option
		self.ctx=ctx
		jobs=ctx.jobs()
		p('-j','--jobs',dest='jobs',default=jobs,type='int',help='amount of parallel jobs (%r)'%jobs)
		p('-k','--keep',dest='keep',default=0,action='count',help='keep running happily even if errors are found')
		p('-v','--verbose',dest='verbose',default=0,action='count',help='verbosity level -v -vv or -vvv [default: 0]')
		p('--nocache',dest='nocache',default=False,action='store_true',help='ignore the WAFCACHE (if set)')
		p('--zones',dest='zones',default='',action='store',help='debugging zones (task_gen, deps, tasks, etc)')
		gr=optparse.OptionGroup(self,'configure options')
		self.add_option_group(gr)
		gr.add_option('-o','--out',action='store',default='',help='build dir for the project',dest='out')
		gr.add_option('-t','--top',action='store',default='',help='src dir for the project',dest='top')
		default_prefix=os.environ.get('PREFIX')
		if not default_prefix:
			if platform=='win32':
				d=tempfile.gettempdir()
				default_prefix=d[0].upper()+d[1:]
			else:
				default_prefix='/usr/local/'
		gr.add_option('--prefix',dest='prefix',default=default_prefix,help='installation prefix [default: %r]'%default_prefix)
		gr.add_option('--download',dest='download',default=False,action='store_true',help='try to download the tools if missing')
		gr=optparse.OptionGroup(self,'build and install options')
		self.add_option_group(gr)
		gr.add_option('-p','--progress',dest='progress_bar',default=0,action='count',help='-p: progress bar; -pp: ide output')
		gr.add_option('--targets',dest='targets',default='',action='store',help='task generators, e.g. "target1,target2"')
		gr=optparse.OptionGroup(self,'step options')
		self.add_option_group(gr)
		gr.add_option('--files',dest='files',default='',action='store',help='files to process, by regexp, e.g. "*/main.c,*/test/main.o"')
		default_destdir=os.environ.get('DESTDIR','')
		gr=optparse.OptionGroup(self,'install/uninstall options')
		self.add_option_group(gr)
		gr.add_option('--destdir',help='installation root [default: %r]'%default_destdir,default=default_destdir,dest='destdir')
		gr.add_option('-f','--force',dest='force',default=False,action='store_true',help='force file installation')
		gr.add_option('--distcheck-args',help='arguments to pass to distcheck',default=None,action='store')
	def get_usage(self):
		cmds_str={}
		for cls in Context.classes:
			if not cls.cmd or cls.cmd=='options':
				continue
			s=cls.__doc__ or''
			cmds_str[cls.cmd]=s
		if Context.g_module:
			for(k,v)in Context.g_module.__dict__.items():
				if k in['options','init','shutdown']:
					continue
				if type(v)is type(Context.create_context):
					if v.__doc__ and not k.startswith('_'):
						cmds_str[k]=v.__doc__
		just=0
		for k in cmds_str:
			just=max(just,len(k))
		lst=['  %s: %s'%(k.ljust(just),v)for(k,v)in cmds_str.items()]
		lst.sort()
		ret='\n'.join(lst)
		return'''waf [commands] [options]

Main commands (example: ./waf build -j4)
%s
'''%ret
class OptionsContext(Context.Context):
	cmd='options'
	fun='options'
	def __init__(self,**kw):
		super(OptionsContext,self).__init__(**kw)
		self.parser=opt_parser(self)
		self.option_groups={}
	def jobs(self):
		count=int(os.environ.get('JOBS',0))
		if count<1:
			if'NUMBER_OF_PROCESSORS'in os.environ:
				count=int(os.environ.get('NUMBER_OF_PROCESSORS',1))
			else:
				if hasattr(os,'sysconf_names'):
					if'SC_NPROCESSORS_ONLN'in os.sysconf_names:
						count=int(os.sysconf('SC_NPROCESSORS_ONLN'))
					elif'SC_NPROCESSORS_CONF'in os.sysconf_names:
						count=int(os.sysconf('SC_NPROCESSORS_CONF'))
				if not count and os.name not in('nt','java'):
					try:
						tmp=self.cmd_and_log(['sysctl','-n','hw.ncpu'],quiet=0)
					except Exception:
						pass
					else:
						if re.match('^[0-9]+$',tmp):
							count=int(tmp)
		if count<1:
			count=1
		elif count>1024:
			count=1024
		return count
	def add_option(self,*k,**kw):
		return self.parser.add_option(*k,**kw)
	def add_option_group(self,*k,**kw):
		try:
			gr=self.option_groups[k[0]]
		except KeyError:
			gr=self.parser.add_option_group(*k,**kw)
		self.option_groups[k[0]]=gr
		return gr
	def get_option_group(self,opt_str):
		try:
			return self.option_groups[opt_str]
		except KeyError:
			for group in self.parser.option_groups:
				if group.title==opt_str:
					return group
			return None
	def parse_args(self,_args=None):
		global options,commands
		(options,leftover_args)=self.parser.parse_args(args=_args)
		commands=leftover_args
		if options.destdir:
			options.destdir=os.path.abspath(os.path.expanduser(options.destdir))
		if options.verbose>=1:
			self.load('errcheck')
	def execute(self):
		super(OptionsContext,self).execute()
		self.parse_args()

########NEW FILE########
__FILENAME__ = Runner
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import random,atexit
try:
	from queue import Queue
except ImportError:
	from Queue import Queue
from waflib import Utils,Task,Errors,Logs
GAP=10
class TaskConsumer(Utils.threading.Thread):
	def __init__(self):
		Utils.threading.Thread.__init__(self)
		self.ready=Queue()
		self.setDaemon(1)
		self.start()
	def run(self):
		try:
			self.loop()
		except Exception:
			pass
	def loop(self):
		while 1:
			tsk=self.ready.get()
			if not isinstance(tsk,Task.TaskBase):
				tsk(self)
			else:
				tsk.process()
pool=Queue()
def get_pool():
	try:
		return pool.get(False)
	except Exception:
		return TaskConsumer()
def put_pool(x):
	pool.put(x)
def _free_resources():
	global pool
	lst=[]
	while pool.qsize():
		lst.append(pool.get())
	for x in lst:
		x.ready.put(None)
	for x in lst:
		x.join()
	pool=None
atexit.register(_free_resources)
class Parallel(object):
	def __init__(self,bld,j=2):
		self.numjobs=j
		self.bld=bld
		self.outstanding=[]
		self.frozen=[]
		self.out=Queue(0)
		self.count=0
		self.processed=1
		self.stop=False
		self.error=[]
		self.biter=None
		self.dirty=False
	def get_next_task(self):
		if not self.outstanding:
			return None
		return self.outstanding.pop(0)
	def postpone(self,tsk):
		if random.randint(0,1):
			self.frozen.insert(0,tsk)
		else:
			self.frozen.append(tsk)
	def refill_task_list(self):
		while self.count>self.numjobs*GAP:
			self.get_out()
		while not self.outstanding:
			if self.count:
				self.get_out()
			elif self.frozen:
				try:
					cond=self.deadlock==self.processed
				except AttributeError:
					pass
				else:
					if cond:
						msg='check the build order for the tasks'
						for tsk in self.frozen:
							if not tsk.run_after:
								msg='check the methods runnable_status'
								break
						lst=[]
						for tsk in self.frozen:
							lst.append('%s\t-> %r'%(repr(tsk),[id(x)for x in tsk.run_after]))
						raise Errors.WafError('Deadlock detected: %s%s'%(msg,''.join(lst)))
				self.deadlock=self.processed
			if self.frozen:
				self.outstanding+=self.frozen
				self.frozen=[]
			elif not self.count:
				self.outstanding.extend(self.biter.next())
				self.total=self.bld.total()
				break
	def add_more_tasks(self,tsk):
		if getattr(tsk,'more_tasks',None):
			self.outstanding+=tsk.more_tasks
			self.total+=len(tsk.more_tasks)
	def get_out(self):
		tsk=self.out.get()
		if not self.stop:
			self.add_more_tasks(tsk)
		self.count-=1
		self.dirty=True
		return tsk
	def error_handler(self,tsk):
		if not self.bld.keep:
			self.stop=True
		self.error.append(tsk)
	def add_task(self,tsk):
		try:
			self.pool
		except AttributeError:
			self.init_task_pool()
		self.ready.put(tsk)
	def init_task_pool(self):
		pool=self.pool=[get_pool()for i in range(self.numjobs)]
		self.ready=Queue(0)
		def setq(consumer):
			consumer.ready=self.ready
		for x in pool:
			x.ready.put(setq)
		return pool
	def free_task_pool(self):
		def setq(consumer):
			consumer.ready=Queue(0)
			self.out.put(self)
		try:
			pool=self.pool
		except AttributeError:
			pass
		else:
			for x in pool:
				self.ready.put(setq)
			for x in pool:
				self.get_out()
			for x in pool:
				put_pool(x)
			self.pool=[]
	def start(self):
		self.total=self.bld.total()
		while not self.stop:
			self.refill_task_list()
			tsk=self.get_next_task()
			if not tsk:
				if self.count:
					continue
				else:
					break
			if tsk.hasrun:
				self.processed+=1
				continue
			if self.stop:
				break
			try:
				st=tsk.runnable_status()
			except Exception:
				self.processed+=1
				tsk.err_msg=Utils.ex_stack()
				if not self.stop and self.bld.keep:
					tsk.hasrun=Task.SKIPPED
					if self.bld.keep==1:
						if Logs.verbose>1 or not self.error:
							self.error.append(tsk)
						self.stop=True
					else:
						if Logs.verbose>1:
							self.error.append(tsk)
					continue
				tsk.hasrun=Task.EXCEPTION
				self.error_handler(tsk)
				continue
			if st==Task.ASK_LATER:
				self.postpone(tsk)
			elif st==Task.SKIP_ME:
				self.processed+=1
				tsk.hasrun=Task.SKIPPED
				self.add_more_tasks(tsk)
			else:
				tsk.position=(self.processed,self.total)
				self.count+=1
				tsk.master=self
				self.processed+=1
				if self.numjobs==1:
					tsk.process()
				else:
					self.add_task(tsk)
		while self.error and self.count:
			self.get_out()
		assert(self.count==0 or self.stop)
		self.free_task_pool()

########NEW FILE########
__FILENAME__ = Scripting
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import os,shlex,shutil,traceback,errno,sys,stat
from waflib import Utils,Configure,Logs,Options,ConfigSet,Context,Errors,Build,Node
build_dir_override=None
no_climb_commands=['configure']
default_cmd="build"
def waf_entry_point(current_directory,version,wafdir):
	Logs.init_log()
	if Context.WAFVERSION!=version:
		Logs.error('Waf script %r and library %r do not match (directory %r)'%(version,Context.WAFVERSION,wafdir))
		sys.exit(1)
	if'--version'in sys.argv:
		Context.run_dir=current_directory
		ctx=Context.create_context('options')
		ctx.curdir=current_directory
		ctx.parse_args()
		sys.exit(0)
	Context.waf_dir=wafdir
	Context.launch_dir=current_directory
	no_climb=os.environ.get('NOCLIMB',None)
	if not no_climb:
		for k in no_climb_commands:
			if k in sys.argv:
				no_climb=True
				break
	cur=current_directory
	while cur:
		lst=os.listdir(cur)
		if Options.lockfile in lst:
			env=ConfigSet.ConfigSet()
			try:
				env.load(os.path.join(cur,Options.lockfile))
				ino=os.stat(cur)[stat.ST_INO]
			except Exception:
				pass
			else:
				for x in[env.run_dir,env.top_dir,env.out_dir]:
					if Utils.is_win32:
						if cur==x:
							load=True
							break
					else:
						try:
							ino2=os.stat(x)[stat.ST_INO]
						except OSError:
							pass
						else:
							if ino==ino2:
								load=True
								break
				else:
					Logs.warn('invalid lock file in %s'%cur)
					load=False
				if load:
					Context.run_dir=env.run_dir
					Context.top_dir=env.top_dir
					Context.out_dir=env.out_dir
					break
		if not Context.run_dir:
			if Context.WSCRIPT_FILE in lst:
				Context.run_dir=cur
		next=os.path.dirname(cur)
		if next==cur:
			break
		cur=next
		if no_climb:
			break
	if not Context.run_dir:
		if'-h'in sys.argv or'--help'in sys.argv:
			Logs.warn('No wscript file found: the help message may be incomplete')
			Context.run_dir=current_directory
			ctx=Context.create_context('options')
			ctx.curdir=current_directory
			ctx.parse_args()
			sys.exit(0)
		Logs.error('Waf: Run from a directory containing a file named %r'%Context.WSCRIPT_FILE)
		sys.exit(1)
	try:
		os.chdir(Context.run_dir)
	except OSError:
		Logs.error('Waf: The folder %r is unreadable'%Context.run_dir)
		sys.exit(1)
	try:
		set_main_module(Context.run_dir+os.sep+Context.WSCRIPT_FILE)
	except Errors.WafError ,e:
		Logs.pprint('RED',e.verbose_msg)
		Logs.error(str(e))
		sys.exit(1)
	except Exception ,e:
		Logs.error('Waf: The wscript in %r is unreadable'%Context.run_dir,e)
		traceback.print_exc(file=sys.stdout)
		sys.exit(2)
	try:
		run_commands()
	except Errors.WafError ,e:
		if Logs.verbose>1:
			Logs.pprint('RED',e.verbose_msg)
		Logs.error(e.msg)
		sys.exit(1)
	except SystemExit:
		raise
	except Exception ,e:
		traceback.print_exc(file=sys.stdout)
		sys.exit(2)
	except KeyboardInterrupt:
		Logs.pprint('RED','Interrupted')
		sys.exit(68)
def set_main_module(file_path):
	Context.g_module=Context.load_module(file_path)
	Context.g_module.root_path=file_path
	def set_def(obj):
		name=obj.__name__
		if not name in Context.g_module.__dict__:
			setattr(Context.g_module,name,obj)
	for k in[update,dist,distclean,distcheck,update]:
		set_def(k)
	if not'init'in Context.g_module.__dict__:
		Context.g_module.init=Utils.nada
	if not'shutdown'in Context.g_module.__dict__:
		Context.g_module.shutdown=Utils.nada
	if not'options'in Context.g_module.__dict__:
		Context.g_module.options=Utils.nada
def parse_options():
	Context.create_context('options').execute()
	if not Options.commands:
		Options.commands=[default_cmd]
	Options.commands=[x for x in Options.commands if x!='options']
	Logs.verbose=Options.options.verbose
	Logs.init_log()
	if Options.options.zones:
		Logs.zones=Options.options.zones.split(',')
		if not Logs.verbose:
			Logs.verbose=1
	elif Logs.verbose>0:
		Logs.zones=['runner']
	if Logs.verbose>2:
		Logs.zones=['*']
def run_command(cmd_name):
	ctx=Context.create_context(cmd_name)
	ctx.log_timer=Utils.Timer()
	ctx.options=Options.options
	ctx.cmd=cmd_name
	ctx.execute()
	return ctx
def run_commands():
	parse_options()
	run_command('init')
	while Options.commands:
		cmd_name=Options.commands.pop(0)
		ctx=run_command(cmd_name)
		Logs.info('%r finished successfully (%s)'%(cmd_name,str(ctx.log_timer)))
	run_command('shutdown')
def _can_distclean(name):
	for k in'.o .moc .exe'.split():
		if name.endswith(k):
			return True
	return False
def distclean_dir(dirname):
	for(root,dirs,files)in os.walk(dirname):
		for f in files:
			if _can_distclean(f):
				fname=root+os.sep+f
				try:
					os.remove(fname)
				except OSError:
					Logs.warn('Could not remove %r'%fname)
	for x in[Context.DBFILE,'config.log']:
		try:
			os.remove(x)
		except OSError:
			pass
	try:
		shutil.rmtree('c4che')
	except OSError:
		pass
def distclean(ctx):
	'''removes the build directory'''
	lst=os.listdir('.')
	for f in lst:
		if f==Options.lockfile:
			try:
				proj=ConfigSet.ConfigSet(f)
			except IOError:
				Logs.warn('Could not read %r'%f)
				continue
			if proj['out_dir']!=proj['top_dir']:
				try:
					shutil.rmtree(proj['out_dir'])
				except IOError:
					pass
				except OSError ,e:
					if e.errno!=errno.ENOENT:
						Logs.warn('project %r cannot be removed'%proj[Context.OUT])
			else:
				distclean_dir(proj['out_dir'])
			for k in(proj['out_dir'],proj['top_dir'],proj['run_dir']):
				try:
					os.remove(os.path.join(k,Options.lockfile))
				except OSError ,e:
					if e.errno!=errno.ENOENT:
						Logs.warn('file %r cannot be removed'%f)
		if not Options.commands:
			for x in'.waf-1. waf-1. .waf3-1. waf3-1.'.split():
				if f.startswith(x):
					shutil.rmtree(f,ignore_errors=True)
class Dist(Context.Context):
	'''creates an archive containing the project source code'''
	cmd='dist'
	fun='dist'
	algo='tar.bz2'
	ext_algo={}
	def execute(self):
		self.recurse([os.path.dirname(Context.g_module.root_path)])
		self.archive()
	def archive(self):
		import tarfile
		arch_name=self.get_arch_name()
		try:
			self.base_path
		except AttributeError:
			self.base_path=self.path
		node=self.base_path.make_node(arch_name)
		try:
			node.delete()
		except Exception:
			pass
		files=self.get_files()
		if self.algo.startswith('tar.'):
			tar=tarfile.open(arch_name,'w:'+self.algo.replace('tar.',''))
			for x in files:
				self.add_tar_file(x,tar)
			tar.close()
		elif self.algo=='zip':
			import zipfile
			zip=zipfile.ZipFile(arch_name,'w',compression=zipfile.ZIP_DEFLATED)
			for x in files:
				archive_name=self.get_base_name()+'/'+x.path_from(self.base_path)
				zip.write(x.abspath(),archive_name,zipfile.ZIP_DEFLATED)
			zip.close()
		else:
			self.fatal('Valid algo types are tar.bz2, tar.gz or zip')
		try:
			from hashlib import sha1 as sha
		except ImportError:
			from sha import sha
		try:
			digest=" (sha=%r)"%sha(node.read()).hexdigest()
		except Exception:
			digest=''
		Logs.info('New archive created: %s%s'%(self.arch_name,digest))
	def get_tar_path(self,node):
		return node.abspath()
	def add_tar_file(self,x,tar):
		p=self.get_tar_path(x)
		tinfo=tar.gettarinfo(name=p,arcname=self.get_tar_prefix()+'/'+x.path_from(self.base_path))
		tinfo.uid=0
		tinfo.gid=0
		tinfo.uname='root'
		tinfo.gname='root'
		fu=None
		try:
			fu=open(p,'rb')
			tar.addfile(tinfo,fileobj=fu)
		finally:
			if fu:
				fu.close()
	def get_tar_prefix(self):
		try:
			return self.tar_prefix
		except AttributeError:
			return self.get_base_name()
	def get_arch_name(self):
		try:
			self.arch_name
		except AttributeError:
			self.arch_name=self.get_base_name()+'.'+self.ext_algo.get(self.algo,self.algo)
		return self.arch_name
	def get_base_name(self):
		try:
			self.base_name
		except AttributeError:
			appname=getattr(Context.g_module,Context.APPNAME,'noname')
			version=getattr(Context.g_module,Context.VERSION,'1.0')
			self.base_name=appname+'-'+version
		return self.base_name
	def get_excl(self):
		try:
			return self.excl
		except AttributeError:
			self.excl=Node.exclude_regs+' **/waf-1.7.* **/.waf-1.7* **/waf3-1.7.* **/.waf3-1.7* **/*~ **/*.rej **/*.orig **/*.pyc **/*.pyo **/*.bak **/*.swp **/.lock-w*'
			nd=self.root.find_node(Context.out_dir)
			if nd:
				self.excl+=' '+nd.path_from(self.base_path)
			return self.excl
	def get_files(self):
		try:
			files=self.files
		except AttributeError:
			files=self.base_path.ant_glob('**/*',excl=self.get_excl())
		return files
def dist(ctx):
	'''makes a tarball for redistributing the sources'''
	pass
class DistCheck(Dist):
	fun='distcheck'
	cmd='distcheck'
	def execute(self):
		self.recurse([os.path.dirname(Context.g_module.root_path)])
		self.archive()
		self.check()
	def check(self):
		import tempfile,tarfile
		t=None
		try:
			t=tarfile.open(self.get_arch_name())
			for x in t:
				t.extract(x)
		finally:
			if t:
				t.close()
		cfg=[]
		if Options.options.distcheck_args:
			cfg=shlex.split(Options.options.distcheck_args)
		else:
			cfg=[x for x in sys.argv if x.startswith('-')]
		instdir=tempfile.mkdtemp('.inst',self.get_base_name())
		ret=Utils.subprocess.Popen([sys.executable,sys.argv[0],'configure','install','uninstall','--destdir='+instdir]+cfg,cwd=self.get_base_name()).wait()
		if ret:
			raise Errors.WafError('distcheck failed with code %i'%ret)
		if os.path.exists(instdir):
			raise Errors.WafError('distcheck succeeded, but files were left in %s'%instdir)
		shutil.rmtree(self.get_base_name())
def distcheck(ctx):
	'''checks if the project compiles (tarball from 'dist')'''
	pass
def update(ctx):
	'''updates the plugins from the *waflib/extras* directory'''
	lst=Options.options.files.split(',')
	if not lst:
		lst=[x for x in Utils.listdir(Context.waf_dir+'/waflib/extras')if x.endswith('.py')]
	for x in lst:
		tool=x.replace('.py','')
		try:
			Configure.download_tool(tool,force=True,ctx=ctx)
		except Errors.WafError:
			Logs.error('Could not find the tool %s in the remote repository'%x)
def autoconfigure(execute_method):
	def execute(self):
		if not Configure.autoconfig:
			return execute_method(self)
		env=ConfigSet.ConfigSet()
		do_config=False
		try:
			env.load(os.path.join(Context.top_dir,Options.lockfile))
		except Exception:
			Logs.warn('Configuring the project')
			do_config=True
		else:
			if env.run_dir!=Context.run_dir:
				do_config=True
			else:
				h=0
				for f in env['files']:
					h=Utils.h_list((h,Utils.readf(f,'rb')))
				do_config=h!=env.hash
		if do_config:
			Options.commands.insert(0,self.cmd)
			Options.commands.insert(0,'configure')
			return
		return execute_method(self)
	return execute
Build.BuildContext.execute=autoconfigure(Build.BuildContext.execute)

########NEW FILE########
__FILENAME__ = Task
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import os,shutil,re,tempfile
from waflib import Utils,Logs,Errors
NOT_RUN=0
MISSING=1
CRASHED=2
EXCEPTION=3
SKIPPED=8
SUCCESS=9
ASK_LATER=-1
SKIP_ME=-2
RUN_ME=-3
COMPILE_TEMPLATE_SHELL='''
def f(tsk):
	env = tsk.env
	gen = tsk.generator
	bld = gen.bld
	wd = getattr(tsk, 'cwd', None)
	p = env.get_flat
	tsk.last_cmd = cmd = \'\'\' %s \'\'\' % s
	return tsk.exec_command(cmd, cwd=wd, env=env.env or None)
'''
COMPILE_TEMPLATE_NOSHELL='''
def f(tsk):
	env = tsk.env
	gen = tsk.generator
	bld = gen.bld
	wd = getattr(tsk, 'cwd', None)
	def to_list(xx):
		if isinstance(xx, str): return [xx]
		return xx
	tsk.last_cmd = lst = []
	%s
	lst = [x for x in lst if x]
	return tsk.exec_command(lst, cwd=wd, env=env.env or None)
'''
def cache_outputs(cls):
	m1=cls.run
	def run(self):
		bld=self.generator.bld
		if bld.cache_global and not bld.nocache:
			if self.can_retrieve_cache():
				return 0
		return m1(self)
	cls.run=run
	m2=cls.post_run
	def post_run(self):
		bld=self.generator.bld
		ret=m2(self)
		if bld.cache_global and not bld.nocache:
			self.put_files_cache()
		return ret
	cls.post_run=post_run
	return cls
classes={}
class store_task_type(type):
	def __init__(cls,name,bases,dict):
		super(store_task_type,cls).__init__(name,bases,dict)
		name=cls.__name__
		if name.endswith('_task'):
			name=name.replace('_task','')
		if name!='evil'and name!='TaskBase':
			global classes
			if getattr(cls,'run_str',None):
				(f,dvars)=compile_fun(cls.run_str,cls.shell)
				cls.hcode=cls.run_str
				cls.run_str=None
				cls.run=f
				cls.vars=list(set(cls.vars+dvars))
				cls.vars.sort()
			elif getattr(cls,'run',None)and not'hcode'in cls.__dict__:
				cls.hcode=Utils.h_fun(cls.run)
			if not getattr(cls,'nocache',None):
				cls=cache_outputs(cls)
			getattr(cls,'register',classes)[name]=cls
evil=store_task_type('evil',(object,),{})
class TaskBase(evil):
	color='GREEN'
	ext_in=[]
	ext_out=[]
	before=[]
	after=[]
	hcode=''
	def __init__(self,*k,**kw):
		self.hasrun=NOT_RUN
		try:
			self.generator=kw['generator']
		except KeyError:
			self.generator=self
	def __repr__(self):
		return'\n\t{task %r: %s %s}'%(self.__class__.__name__,id(self),str(getattr(self,'fun','')))
	def __str__(self):
		if hasattr(self,'fun'):
			return'executing: %s\n'%self.fun.__name__
		return self.__class__.__name__+'\n'
	def __hash__(self):
		return id(self)
	def exec_command(self,cmd,**kw):
		bld=self.generator.bld
		try:
			if not kw.get('cwd',None):
				kw['cwd']=bld.cwd
		except AttributeError:
			bld.cwd=kw['cwd']=bld.variant_dir
		return bld.exec_command(cmd,**kw)
	def runnable_status(self):
		return RUN_ME
	def process(self):
		m=self.master
		if m.stop:
			m.out.put(self)
			return
		try:
			del self.generator.bld.task_sigs[self.uid()]
		except KeyError:
			pass
		try:
			self.generator.bld.returned_tasks.append(self)
			self.log_display(self.generator.bld)
			ret=self.run()
		except Exception:
			self.err_msg=Utils.ex_stack()
			self.hasrun=EXCEPTION
			m.error_handler(self)
			m.out.put(self)
			return
		if ret:
			self.err_code=ret
			self.hasrun=CRASHED
		else:
			try:
				self.post_run()
			except Errors.WafError:
				pass
			except Exception:
				self.err_msg=Utils.ex_stack()
				self.hasrun=EXCEPTION
			else:
				self.hasrun=SUCCESS
		if self.hasrun!=SUCCESS:
			m.error_handler(self)
		m.out.put(self)
	def run(self):
		if hasattr(self,'fun'):
			return self.fun(self)
		return 0
	def post_run(self):
		pass
	def log_display(self,bld):
		bld.to_log(self.display())
	def display(self):
		col1=Logs.colors(self.color)
		col2=Logs.colors.NORMAL
		master=self.master
		def cur():
			tmp=-1
			if hasattr(master,'ready'):
				tmp-=master.ready.qsize()
			return master.processed+tmp
		if self.generator.bld.progress_bar==1:
			return self.generator.bld.progress_line(cur(),master.total,col1,col2)
		if self.generator.bld.progress_bar==2:
			ela=str(self.generator.bld.timer)
			try:
				ins=','.join([n.name for n in self.inputs])
			except AttributeError:
				ins=''
			try:
				outs=','.join([n.name for n in self.outputs])
			except AttributeError:
				outs=''
			return'|Total %s|Current %s|Inputs %s|Outputs %s|Time %s|\n'%(master.total,cur(),ins,outs,ela)
		s=str(self)
		if not s:
			return None
		total=master.total
		n=len(str(total))
		fs='[%%%dd/%%%dd] %%s%%s%%s'%(n,n)
		return fs%(cur(),total,col1,s,col2)
	def attr(self,att,default=None):
		ret=getattr(self,att,self)
		if ret is self:return getattr(self.__class__,att,default)
		return ret
	def hash_constraints(self):
		cls=self.__class__
		tup=(str(cls.before),str(cls.after),str(cls.ext_in),str(cls.ext_out),cls.__name__,cls.hcode)
		h=hash(tup)
		return h
	def format_error(self):
		msg=getattr(self,'last_cmd','')
		name=getattr(self.generator,'name','')
		if getattr(self,"err_msg",None):
			return self.err_msg
		elif not self.hasrun:
			return'task in %r was not executed for some reason: %r'%(name,self)
		elif self.hasrun==CRASHED:
			try:
				return' -> task in %r failed (exit status %r): %r\n%r'%(name,self.err_code,self,msg)
			except AttributeError:
				return' -> task in %r failed: %r\n%r'%(name,self,msg)
		elif self.hasrun==MISSING:
			return' -> missing files in %r: %r\n%r'%(name,self,msg)
		else:
			return'invalid status for task in %r: %r'%(name,self.hasrun)
	def colon(self,var1,var2):
		tmp=self.env[var1]
		if isinstance(var2,str):
			it=self.env[var2]
		else:
			it=var2
		if isinstance(tmp,str):
			return[tmp%x for x in it]
		else:
			if Logs.verbose and not tmp and it:
				Logs.warn('Missing env variable %r for task %r (generator %r)'%(var1,self,self.generator))
			lst=[]
			for y in it:
				lst.extend(tmp)
				lst.append(y)
			return lst
class Task(TaskBase):
	vars=[]
	shell=False
	def __init__(self,*k,**kw):
		TaskBase.__init__(self,*k,**kw)
		self.env=kw['env']
		self.inputs=[]
		self.outputs=[]
		self.dep_nodes=[]
		self.run_after=set([])
	def __str__(self):
		env=self.env
		src_str=' '.join([a.nice_path()for a in self.inputs])
		tgt_str=' '.join([a.nice_path()for a in self.outputs])
		if self.outputs:sep=' -> '
		else:sep=''
		return'%s: %s%s%s\n'%(self.__class__.__name__.replace('_task',''),src_str,sep,tgt_str)
	def __repr__(self):
		try:
			ins=",".join([x.name for x in self.inputs])
			outs=",".join([x.name for x in self.outputs])
		except AttributeError:
			ins=",".join([str(x)for x in self.inputs])
			outs=",".join([str(x)for x in self.outputs])
		return"".join(['\n\t{task %r: '%id(self),self.__class__.__name__," ",ins," -> ",outs,'}'])
	def uid(self):
		try:
			return self.uid_
		except AttributeError:
			m=Utils.md5()
			up=m.update
			up(self.__class__.__name__)
			for x in self.inputs+self.outputs:
				up(x.abspath())
			self.uid_=m.digest()
			return self.uid_
	def set_inputs(self,inp):
		if isinstance(inp,list):self.inputs+=inp
		else:self.inputs.append(inp)
	def set_outputs(self,out):
		if isinstance(out,list):self.outputs+=out
		else:self.outputs.append(out)
	def set_run_after(self,task):
		assert isinstance(task,TaskBase)
		self.run_after.add(task)
	def signature(self):
		try:return self.cache_sig
		except AttributeError:pass
		self.m=Utils.md5()
		self.m.update(self.hcode)
		self.sig_explicit_deps()
		self.sig_vars()
		if self.scan:
			try:
				self.sig_implicit_deps()
			except Errors.TaskRescan:
				return self.signature()
		ret=self.cache_sig=self.m.digest()
		return ret
	def runnable_status(self):
		for t in self.run_after:
			if not t.hasrun:
				return ASK_LATER
		bld=self.generator.bld
		try:
			new_sig=self.signature()
		except Errors.TaskNotReady:
			return ASK_LATER
		key=self.uid()
		try:
			prev_sig=bld.task_sigs[key]
		except KeyError:
			Logs.debug("task: task %r must run as it was never run before or the task code changed"%self)
			return RUN_ME
		for node in self.outputs:
			try:
				if node.sig!=new_sig:
					return RUN_ME
			except AttributeError:
				Logs.debug("task: task %r must run as the output nodes do not exist"%self)
				return RUN_ME
		if new_sig!=prev_sig:
			return RUN_ME
		return SKIP_ME
	def post_run(self):
		bld=self.generator.bld
		sig=self.signature()
		for node in self.outputs:
			try:
				os.stat(node.abspath())
			except OSError:
				self.hasrun=MISSING
				self.err_msg='-> missing file: %r'%node.abspath()
				raise Errors.WafError(self.err_msg)
			node.sig=sig
		bld.task_sigs[self.uid()]=self.cache_sig
	def sig_explicit_deps(self):
		bld=self.generator.bld
		upd=self.m.update
		for x in self.inputs+self.dep_nodes:
			try:
				upd(x.get_bld_sig())
			except(AttributeError,TypeError):
				raise Errors.WafError('Missing node signature for %r (required by %r)'%(x,self))
		if bld.deps_man:
			additional_deps=bld.deps_man
			for x in self.inputs+self.outputs:
				try:
					d=additional_deps[id(x)]
				except KeyError:
					continue
				for v in d:
					if isinstance(v,bld.root.__class__):
						try:
							v=v.get_bld_sig()
						except AttributeError:
							raise Errors.WafError('Missing node signature for %r (required by %r)'%(v,self))
					elif hasattr(v,'__call__'):
						v=v()
					upd(v)
		return self.m.digest()
	def sig_vars(self):
		bld=self.generator.bld
		env=self.env
		upd=self.m.update
		act_sig=bld.hash_env_vars(env,self.__class__.vars)
		upd(act_sig)
		dep_vars=getattr(self,'dep_vars',None)
		if dep_vars:
			upd(bld.hash_env_vars(env,dep_vars))
		return self.m.digest()
	scan=None
	def sig_implicit_deps(self):
		bld=self.generator.bld
		key=self.uid()
		prev=bld.task_sigs.get((key,'imp'),[])
		if prev:
			try:
				if prev==self.compute_sig_implicit_deps():
					return prev
			except Exception:
				for x in bld.node_deps.get(self.uid(),[]):
					if x.is_child_of(bld.srcnode):
						try:
							os.stat(x.abspath())
						except OSError:
							try:
								del x.parent.children[x.name]
							except KeyError:
								pass
			del bld.task_sigs[(key,'imp')]
			raise Errors.TaskRescan('rescan')
		(nodes,names)=self.scan()
		if Logs.verbose:
			Logs.debug('deps: scanner for %s returned %s %s'%(str(self),str(nodes),str(names)))
		bld.node_deps[key]=nodes
		bld.raw_deps[key]=names
		self.are_implicit_nodes_ready()
		try:
			bld.task_sigs[(key,'imp')]=sig=self.compute_sig_implicit_deps()
		except Exception:
			if Logs.verbose:
				for k in bld.node_deps.get(self.uid(),[]):
					try:
						k.get_bld_sig()
					except Exception:
						Logs.warn('Missing signature for node %r (may cause rebuilds)'%k)
		else:
			return sig
	def compute_sig_implicit_deps(self):
		upd=self.m.update
		bld=self.generator.bld
		self.are_implicit_nodes_ready()
		for k in bld.node_deps.get(self.uid(),[]):
			upd(k.get_bld_sig())
		return self.m.digest()
	def are_implicit_nodes_ready(self):
		bld=self.generator.bld
		try:
			cache=bld.dct_implicit_nodes
		except AttributeError:
			bld.dct_implicit_nodes=cache={}
		try:
			dct=cache[bld.cur]
		except KeyError:
			dct=cache[bld.cur]={}
			for tsk in bld.cur_tasks:
				for x in tsk.outputs:
					dct[x]=tsk
		modified=False
		for x in bld.node_deps.get(self.uid(),[]):
			if x in dct:
				self.run_after.add(dct[x])
				modified=True
		if modified:
			for tsk in self.run_after:
				if not tsk.hasrun:
					raise Errors.TaskNotReady('not ready')
	def can_retrieve_cache(self):
		if not getattr(self,'outputs',None):
			return None
		sig=self.signature()
		ssig=Utils.to_hex(self.uid())+Utils.to_hex(sig)
		dname=os.path.join(self.generator.bld.cache_global,ssig)
		try:
			t1=os.stat(dname).st_mtime
		except OSError:
			return None
		for node in self.outputs:
			orig=os.path.join(dname,node.name)
			try:
				shutil.copy2(orig,node.abspath())
				os.utime(orig,None)
			except(OSError,IOError):
				Logs.debug('task: failed retrieving file')
				return None
		try:
			t2=os.stat(dname).st_mtime
		except OSError:
			return None
		if t1!=t2:
			return None
		for node in self.outputs:
			node.sig=sig
			if self.generator.bld.progress_bar<1:
				self.generator.bld.to_log('restoring from cache %r\n'%node.abspath())
		self.cached=True
		return True
	def put_files_cache(self):
		if getattr(self,'cached',None):
			return None
		if not getattr(self,'outputs',None):
			return None
		sig=self.signature()
		ssig=Utils.to_hex(self.uid())+Utils.to_hex(sig)
		dname=os.path.join(self.generator.bld.cache_global,ssig)
		tmpdir=tempfile.mkdtemp(prefix=self.generator.bld.cache_global+os.sep+'waf')
		try:
			shutil.rmtree(dname)
		except Exception:
			pass
		try:
			for node in self.outputs:
				dest=os.path.join(tmpdir,node.name)
				shutil.copy2(node.abspath(),dest)
		except(OSError,IOError):
			try:
				shutil.rmtree(tmpdir)
			except Exception:
				pass
		else:
			try:
				os.rename(tmpdir,dname)
			except OSError:
				try:
					shutil.rmtree(tmpdir)
				except Exception:
					pass
			else:
				try:
					os.chmod(dname,Utils.O755)
				except Exception:
					pass
def is_before(t1,t2):
	to_list=Utils.to_list
	for k in to_list(t2.ext_in):
		if k in to_list(t1.ext_out):
			return 1
	if t1.__class__.__name__ in to_list(t2.after):
		return 1
	if t2.__class__.__name__ in to_list(t1.before):
		return 1
	return 0
def set_file_constraints(tasks):
	ins=Utils.defaultdict(set)
	outs=Utils.defaultdict(set)
	for x in tasks:
		for a in getattr(x,'inputs',[])+getattr(x,'dep_nodes',[]):
			ins[id(a)].add(x)
		for a in getattr(x,'outputs',[]):
			outs[id(a)].add(x)
	links=set(ins.keys()).intersection(outs.keys())
	for k in links:
		for a in ins[k]:
			a.run_after.update(outs[k])
def set_precedence_constraints(tasks):
	cstr_groups=Utils.defaultdict(list)
	for x in tasks:
		h=x.hash_constraints()
		cstr_groups[h].append(x)
	keys=list(cstr_groups.keys())
	maxi=len(keys)
	for i in range(maxi):
		t1=cstr_groups[keys[i]][0]
		for j in range(i+1,maxi):
			t2=cstr_groups[keys[j]][0]
			if is_before(t1,t2):
				a=i
				b=j
			elif is_before(t2,t1):
				a=j
				b=i
			else:
				continue
			aval=set(cstr_groups[keys[a]])
			for x in cstr_groups[keys[b]]:
				x.run_after.update(aval)
def funex(c):
	dc={}
	exec(c,dc)
	return dc['f']
reg_act=re.compile(r"(?P<backslash>\\)|(?P<dollar>\$\$)|(?P<subst>\$\{(?P<var>\w+)(?P<code>.*?)\})",re.M)
def compile_fun_shell(line):
	extr=[]
	def repl(match):
		g=match.group
		if g('dollar'):return"$"
		elif g('backslash'):return'\\\\'
		elif g('subst'):extr.append((g('var'),g('code')));return"%s"
		return None
	line=reg_act.sub(repl,line)or line
	parm=[]
	dvars=[]
	app=parm.append
	for(var,meth)in extr:
		if var=='SRC':
			if meth:app('tsk.inputs%s'%meth)
			else:app('" ".join([a.path_from(bld.bldnode) for a in tsk.inputs])')
		elif var=='TGT':
			if meth:app('tsk.outputs%s'%meth)
			else:app('" ".join([a.path_from(bld.bldnode) for a in tsk.outputs])')
		elif meth:
			if meth.startswith(':'):
				m=meth[1:]
				if m=='SRC':
					m='[a.path_from(bld.bldnode) for a in tsk.inputs]'
				elif m=='TGT':
					m='[a.path_from(bld.bldnode) for a in tsk.outputs]'
				elif m[:3]not in('tsk','gen','bld'):
					dvars.extend([var,meth[1:]])
					m='%r'%m
				app('" ".join(tsk.colon(%r, %s))'%(var,m))
			else:
				app('%s%s'%(var,meth))
		else:
			if not var in dvars:dvars.append(var)
			app("p('%s')"%var)
	if parm:parm="%% (%s) "%(',\n\t\t'.join(parm))
	else:parm=''
	c=COMPILE_TEMPLATE_SHELL%(line,parm)
	Logs.debug('action: %s'%c.strip().splitlines())
	return(funex(c),dvars)
def compile_fun_noshell(line):
	extr=[]
	def repl(match):
		g=match.group
		if g('dollar'):return"$"
		elif g('subst'):extr.append((g('var'),g('code')));return"<<|@|>>"
		return None
	line2=reg_act.sub(repl,line)
	params=line2.split('<<|@|>>')
	assert(extr)
	buf=[]
	dvars=[]
	app=buf.append
	for x in range(len(extr)):
		params[x]=params[x].strip()
		if params[x]:
			app("lst.extend(%r)"%params[x].split())
		(var,meth)=extr[x]
		if var=='SRC':
			if meth:app('lst.append(tsk.inputs%s)'%meth)
			else:app("lst.extend([a.path_from(bld.bldnode) for a in tsk.inputs])")
		elif var=='TGT':
			if meth:app('lst.append(tsk.outputs%s)'%meth)
			else:app("lst.extend([a.path_from(bld.bldnode) for a in tsk.outputs])")
		elif meth:
			if meth.startswith(':'):
				m=meth[1:]
				if m=='SRC':
					m='[a.path_from(bld.bldnode) for a in tsk.inputs]'
				elif m=='TGT':
					m='[a.path_from(bld.bldnode) for a in tsk.outputs]'
				elif m[:3]not in('tsk','gen','bld'):
					dvars.extend([var,m])
					m='%r'%m
				app('lst.extend(tsk.colon(%r, %s))'%(var,m))
			else:
				app('lst.extend(gen.to_list(%s%s))'%(var,meth))
		else:
			app('lst.extend(to_list(env[%r]))'%var)
			if not var in dvars:dvars.append(var)
	if extr:
		if params[-1]:
			app("lst.extend(%r)"%params[-1].split())
	fun=COMPILE_TEMPLATE_NOSHELL%"\n\t".join(buf)
	Logs.debug('action: %s'%fun.strip().splitlines())
	return(funex(fun),dvars)
def compile_fun(line,shell=False):
	if line.find('<')>0 or line.find('>')>0 or line.find('&&')>0:
		shell=True
	if shell:
		return compile_fun_shell(line)
	else:
		return compile_fun_noshell(line)
def task_factory(name,func=None,vars=None,color='GREEN',ext_in=[],ext_out=[],before=[],after=[],shell=False,scan=None):
	params={'vars':vars or[],'color':color,'name':name,'ext_in':Utils.to_list(ext_in),'ext_out':Utils.to_list(ext_out),'before':Utils.to_list(before),'after':Utils.to_list(after),'shell':shell,'scan':scan,}
	if isinstance(func,str):
		params['run_str']=func
	else:
		params['run']=func
	cls=type(Task)(name,(Task,),params)
	global classes
	classes[name]=cls
	return cls
def always_run(cls):
	old=cls.runnable_status
	def always(self):
		ret=old(self)
		if ret==SKIP_ME:
			ret=RUN_ME
		return ret
	cls.runnable_status=always
	return cls
def update_outputs(cls):
	old_post_run=cls.post_run
	def post_run(self):
		old_post_run(self)
		for node in self.outputs:
			node.sig=Utils.h_file(node.abspath())
			self.generator.bld.task_sigs[node.abspath()]=self.uid()
	cls.post_run=post_run
	old_runnable_status=cls.runnable_status
	def runnable_status(self):
		status=old_runnable_status(self)
		if status!=RUN_ME:
			return status
		try:
			bld=self.generator.bld
			prev_sig=bld.task_sigs[self.uid()]
			if prev_sig==self.signature():
				for x in self.outputs:
					if not x.is_child_of(bld.bldnode):
						x.sig=Utils.h_file(x.abspath())
					if not x.sig or bld.task_sigs[x.abspath()]!=self.uid():
						return RUN_ME
				return SKIP_ME
		except OSError:
			pass
		except IOError:
			pass
		except KeyError:
			pass
		except IndexError:
			pass
		except AttributeError:
			pass
		return RUN_ME
	cls.runnable_status=runnable_status
	return cls

########NEW FILE########
__FILENAME__ = TaskGen
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import copy,re,os
from waflib import Task,Utils,Logs,Errors,ConfigSet,Node
feats=Utils.defaultdict(set)
class task_gen(object):
	mappings={}
	prec=Utils.defaultdict(list)
	def __init__(self,*k,**kw):
		self.source=''
		self.target=''
		self.meths=[]
		self.prec=Utils.defaultdict(list)
		self.mappings={}
		self.features=[]
		self.tasks=[]
		if not'bld'in kw:
			self.env=ConfigSet.ConfigSet()
			self.idx=0
			self.path=None
		else:
			self.bld=kw['bld']
			self.env=self.bld.env.derive()
			self.path=self.bld.path
			try:
				self.idx=self.bld.idx[id(self.path)]=self.bld.idx.get(id(self.path),0)+1
			except AttributeError:
				self.bld.idx={}
				self.idx=self.bld.idx[id(self.path)]=1
		for key,val in kw.items():
			setattr(self,key,val)
	def __str__(self):
		return"<task_gen %r declared in %s>"%(self.name,self.path.abspath())
	def __repr__(self):
		lst=[]
		for x in self.__dict__.keys():
			if x not in['env','bld','compiled_tasks','tasks']:
				lst.append("%s=%s"%(x,repr(getattr(self,x))))
		return"bld(%s) in %s"%(", ".join(lst),self.path.abspath())
	def get_name(self):
		try:
			return self._name
		except AttributeError:
			if isinstance(self.target,list):
				lst=[str(x)for x in self.target]
				name=self._name=','.join(lst)
			else:
				name=self._name=str(self.target)
			return name
	def set_name(self,name):
		self._name=name
	name=property(get_name,set_name)
	def to_list(self,val):
		if isinstance(val,str):return val.split()
		else:return val
	def post(self):
		if getattr(self,'posted',None):
			return False
		self.posted=True
		keys=set(self.meths)
		self.features=Utils.to_list(self.features)
		for x in self.features+['*']:
			st=feats[x]
			if not st:
				if not x in Task.classes:
					Logs.warn('feature %r does not exist - bind at least one method to it'%x)
			keys.update(list(st))
		prec={}
		prec_tbl=self.prec or task_gen.prec
		for x in prec_tbl:
			if x in keys:
				prec[x]=prec_tbl[x]
		tmp=[]
		for a in keys:
			for x in prec.values():
				if a in x:break
			else:
				tmp.append(a)
		tmp.sort()
		out=[]
		while tmp:
			e=tmp.pop()
			if e in keys:out.append(e)
			try:
				nlst=prec[e]
			except KeyError:
				pass
			else:
				del prec[e]
				for x in nlst:
					for y in prec:
						if x in prec[y]:
							break
					else:
						tmp.append(x)
		if prec:
			raise Errors.WafError('Cycle detected in the method execution %r'%prec)
		out.reverse()
		self.meths=out
		Logs.debug('task_gen: posting %s %d'%(self,id(self)))
		for x in out:
			try:
				v=getattr(self,x)
			except AttributeError:
				raise Errors.WafError('%r is not a valid task generator method'%x)
			Logs.debug('task_gen: -> %s (%d)'%(x,id(self)))
			v()
		Logs.debug('task_gen: posted %s'%self.name)
		return True
	def get_hook(self,node):
		name=node.name
		for k in self.mappings:
			if name.endswith(k):
				return self.mappings[k]
		for k in task_gen.mappings:
			if name.endswith(k):
				return task_gen.mappings[k]
		raise Errors.WafError("File %r has no mapping in %r (did you forget to load a waf tool?)"%(node,task_gen.mappings.keys()))
	def create_task(self,name,src=None,tgt=None):
		task=Task.classes[name](env=self.env.derive(),generator=self)
		if src:
			task.set_inputs(src)
		if tgt:
			task.set_outputs(tgt)
		self.tasks.append(task)
		return task
	def clone(self,env):
		newobj=self.bld()
		for x in self.__dict__:
			if x in['env','bld']:
				continue
			elif x in['path','features']:
				setattr(newobj,x,getattr(self,x))
			else:
				setattr(newobj,x,copy.copy(getattr(self,x)))
		newobj.posted=False
		if isinstance(env,str):
			newobj.env=self.bld.all_envs[env].derive()
		else:
			newobj.env=env.derive()
		return newobj
def declare_chain(name='',rule=None,reentrant=None,color='BLUE',ext_in=[],ext_out=[],before=[],after=[],decider=None,scan=None,install_path=None,shell=False):
	ext_in=Utils.to_list(ext_in)
	ext_out=Utils.to_list(ext_out)
	if not name:
		name=rule
	cls=Task.task_factory(name,rule,color=color,ext_in=ext_in,ext_out=ext_out,before=before,after=after,scan=scan,shell=shell)
	def x_file(self,node):
		ext=decider and decider(self,node)or cls.ext_out
		if ext_in:
			_ext_in=ext_in[0]
		tsk=self.create_task(name,node)
		cnt=0
		keys=list(self.mappings.keys())+list(self.__class__.mappings.keys())
		for x in ext:
			k=node.change_ext(x,ext_in=_ext_in)
			tsk.outputs.append(k)
			if reentrant!=None:
				if cnt<int(reentrant):
					self.source.append(k)
			else:
				for y in keys:
					if k.name.endswith(y):
						self.source.append(k)
						break
			cnt+=1
		if install_path:
			self.bld.install_files(install_path,tsk.outputs)
		return tsk
	for x in cls.ext_in:
		task_gen.mappings[x]=x_file
	return x_file
def taskgen_method(func):
	setattr(task_gen,func.__name__,func)
	return func
def feature(*k):
	def deco(func):
		setattr(task_gen,func.__name__,func)
		for name in k:
			feats[name].update([func.__name__])
		return func
	return deco
def before_method(*k):
	def deco(func):
		setattr(task_gen,func.__name__,func)
		for fun_name in k:
			if not func.__name__ in task_gen.prec[fun_name]:
				task_gen.prec[fun_name].append(func.__name__)
		return func
	return deco
before=before_method
def after_method(*k):
	def deco(func):
		setattr(task_gen,func.__name__,func)
		for fun_name in k:
			if not fun_name in task_gen.prec[func.__name__]:
				task_gen.prec[func.__name__].append(fun_name)
		return func
	return deco
after=after_method
def extension(*k):
	def deco(func):
		setattr(task_gen,func.__name__,func)
		for x in k:
			task_gen.mappings[x]=func
		return func
	return deco
@taskgen_method
def to_nodes(self,lst,path=None):
	tmp=[]
	path=path or self.path
	find=path.find_resource
	if isinstance(lst,self.path.__class__):
		lst=[lst]
	for x in Utils.to_list(lst):
		if isinstance(x,str):
			node=find(x)
		else:
			node=x
		if not node:
			raise Errors.WafError("source not found: %r in %r"%(x,self))
		tmp.append(node)
	return tmp
@feature('*')
def process_source(self):
	self.source=self.to_nodes(getattr(self,'source',[]))
	for node in self.source:
		self.get_hook(node)(self,node)
@feature('*')
@before_method('process_source')
def process_rule(self):
	if not getattr(self,'rule',None):
		return
	name=str(getattr(self,'name',None)or self.target or getattr(self.rule,'__name__',self.rule))
	try:
		cache=self.bld.cache_rule_attr
	except AttributeError:
		cache=self.bld.cache_rule_attr={}
	cls=None
	if getattr(self,'cache_rule','True'):
		try:
			cls=cache[(name,self.rule)]
		except KeyError:
			pass
	if not cls:
		cls=Task.task_factory(name,self.rule,getattr(self,'vars',[]),shell=getattr(self,'shell',True),color=getattr(self,'color','BLUE'),scan=getattr(self,'scan',None))
		if getattr(self,'scan',None):
			cls.scan=self.scan
		elif getattr(self,'deps',None):
			def scan(self):
				nodes=[]
				for x in self.generator.to_list(getattr(self.generator,'deps',None)):
					node=self.generator.path.find_resource(x)
					if not node:
						self.generator.bld.fatal('Could not find %r (was it declared?)'%x)
					nodes.append(node)
				return[nodes,[]]
			cls.scan=scan
		if getattr(self,'update_outputs',None):
			Task.update_outputs(cls)
		if getattr(self,'always',None):
			Task.always_run(cls)
		for x in['after','before','ext_in','ext_out']:
			setattr(cls,x,getattr(self,x,[]))
		if getattr(self,'cache_rule','True'):
			cache[(name,self.rule)]=cls
	tsk=self.create_task(name)
	if getattr(self,'target',None):
		if isinstance(self.target,str):
			self.target=self.target.split()
		if not isinstance(self.target,list):
			self.target=[self.target]
		for x in self.target:
			if isinstance(x,str):
				tsk.outputs.append(self.path.find_or_declare(x))
			else:
				x.parent.mkdir()
				tsk.outputs.append(x)
		if getattr(self,'install_path',None):
			self.bld.install_files(self.install_path,tsk.outputs)
	if getattr(self,'source',None):
		tsk.inputs=self.to_nodes(self.source)
		self.source=[]
	if getattr(self,'cwd',None):
		tsk.cwd=self.cwd
@feature('seq')
def sequence_order(self):
	if self.meths and self.meths[-1]!='sequence_order':
		self.meths.append('sequence_order')
		return
	if getattr(self,'seq_start',None):
		return
	if getattr(self.bld,'prev',None):
		self.bld.prev.post()
		for x in self.bld.prev.tasks:
			for y in self.tasks:
				y.set_run_after(x)
	self.bld.prev=self
re_m4=re.compile('@(\w+)@',re.M)
class subst_pc(Task.Task):
	def run(self):
		if getattr(self.generator,'is_copy',None):
			self.outputs[0].write(self.inputs[0].read('rb'),'wb')
			if getattr(self.generator,'chmod',None):
				os.chmod(self.outputs[0].abspath(),self.generator.chmod)
			return None
		if getattr(self.generator,'fun',None):
			self.generator.fun(self)
		code=self.inputs[0].read(encoding=getattr(self.generator,'encoding','ISO8859-1'))
		if getattr(self.generator,'subst_fun',None):
			code=self.generator.subst_fun(self,code)
			if code:
				self.outputs[0].write(code,encoding=getattr(self.generator,'encoding','ISO8859-1'))
			return
		code=code.replace('%','%%')
		lst=[]
		def repl(match):
			g=match.group
			if g(1):
				lst.append(g(1))
				return"%%(%s)s"%g(1)
			return''
		global re_m4
		code=getattr(self.generator,'re_m4',re_m4).sub(repl,code)
		try:
			d=self.generator.dct
		except AttributeError:
			d={}
			for x in lst:
				tmp=getattr(self.generator,x,'')or self.env.get_flat(x)or self.env.get_flat(x.upper())
				d[x]=str(tmp)
		code=code%d
		self.outputs[0].write(code,encoding=getattr(self.generator,'encoding','ISO8859-1'))
		self.generator.bld.raw_deps[self.uid()]=self.dep_vars=lst
		try:delattr(self,'cache_sig')
		except AttributeError:pass
		if getattr(self.generator,'chmod',None):
			os.chmod(self.outputs[0].abspath(),self.generator.chmod)
	def sig_vars(self):
		bld=self.generator.bld
		env=self.env
		upd=self.m.update
		if getattr(self.generator,'fun',None):
			upd(Utils.h_fun(self.generator.fun))
		if getattr(self.generator,'subst_fun',None):
			upd(Utils.h_fun(self.generator.subst_fun))
		vars=self.generator.bld.raw_deps.get(self.uid(),[])
		act_sig=bld.hash_env_vars(env,vars)
		upd(act_sig)
		lst=[getattr(self.generator,x,'')for x in vars]
		upd(Utils.h_list(lst))
		return self.m.digest()
@extension('.pc.in')
def add_pcfile(self,node):
	tsk=self.create_task('subst_pc',node,node.change_ext('.pc','.pc.in'))
	self.bld.install_files(getattr(self,'install_path','${LIBDIR}/pkgconfig/'),tsk.outputs)
class subst(subst_pc):
	pass
@feature('subst')
@before_method('process_source','process_rule')
def process_subst(self):
	src=Utils.to_list(getattr(self,'source',[]))
	if isinstance(src,Node.Node):
		src=[src]
	tgt=Utils.to_list(getattr(self,'target',[]))
	if isinstance(tgt,Node.Node):
		tgt=[tgt]
	if len(src)!=len(tgt):
		raise Errors.WafError('invalid number of source/target for %r'%self)
	for x,y in zip(src,tgt):
		if not x or not y:
			raise Errors.WafError('null source or target for %r'%self)
		a,b=None,None
		if isinstance(x,str)and isinstance(y,str)and x==y:
			a=self.path.find_node(x)
			b=self.path.get_bld().make_node(y)
			if not os.path.isfile(b.abspath()):
				b.sig=None
				b.parent.mkdir()
		else:
			if isinstance(x,str):
				a=self.path.find_resource(x)
			elif isinstance(x,Node.Node):
				a=x
			if isinstance(y,str):
				b=self.path.find_or_declare(y)
			elif isinstance(y,Node.Node):
				b=y
		if not a:
			raise Errors.WafError('cound not find %r for %r'%(x,self))
		has_constraints=False
		tsk=self.create_task('subst',a,b)
		for k in('after','before','ext_in','ext_out'):
			val=getattr(self,k,None)
			if val:
				has_constraints=True
				setattr(tsk,k,val)
		if not has_constraints and b.name.endswith('.h'):
			tsk.before=[k for k in('c','cxx')if k in Task.classes]
		inst_to=getattr(self,'install_path',None)
		if inst_to:
			self.bld.install_files(inst_to,b,chmod=getattr(self,'chmod',Utils.O644))
	self.source=[]

########NEW FILE########
__FILENAME__ = ar
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

from waflib.Configure import conf
@conf
def find_ar(conf):
	conf.load('ar')
def configure(conf):
	conf.find_program('ar',var='AR')
	conf.env.ARFLAGS='rcs'

########NEW FILE########
__FILENAME__ = asm
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import os,sys
from waflib import Task,Utils
import waflib.Task
from waflib.Tools.ccroot import link_task,stlink_task
from waflib.TaskGen import extension,feature
class asm(Task.Task):
	color='BLUE'
	run_str='${AS} ${ASFLAGS} ${ASMPATH_ST:INCPATHS} ${AS_SRC_F}${SRC} ${AS_TGT_F}${TGT}'
@extension('.s','.S','.asm','.ASM','.spp','.SPP')
def asm_hook(self,node):
	return self.create_compiled_task('asm',node)
class asmprogram(link_task):
	run_str='${ASLINK} ${ASLINKFLAGS} ${ASLNK_TGT_F}${TGT} ${ASLNK_SRC_F}${SRC}'
	ext_out=['.bin']
	inst_to='${BINDIR}'
class asmshlib(asmprogram):
	inst_to='${LIBDIR}'
class asmstlib(stlink_task):
	pass
def configure(conf):
	conf.env['ASMPATH_ST']='-I%s'

########NEW FILE########
__FILENAME__ = bison
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

from waflib import Task
from waflib.TaskGen import extension
class bison(Task.Task):
	color='BLUE'
	run_str='${BISON} ${BISONFLAGS} ${SRC[0].abspath()} -o ${TGT[0].name}'
	ext_out=['.h']
@extension('.y','.yc','.yy')
def big_bison(self,node):
	has_h='-d'in self.env['BISONFLAGS']
	outs=[]
	if node.name.endswith('.yc'):
		outs.append(node.change_ext('.tab.cc'))
		if has_h:
			outs.append(node.change_ext('.tab.hh'))
	else:
		outs.append(node.change_ext('.tab.c'))
		if has_h:
			outs.append(node.change_ext('.tab.h'))
	tsk=self.create_task('bison',node,outs)
	tsk.cwd=node.parent.get_bld().abspath()
	self.source.append(outs[0])
def configure(conf):
	conf.find_program('bison',var='BISON')
	conf.env.BISONFLAGS=['-d']

########NEW FILE########
__FILENAME__ = c
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

from waflib import TaskGen,Task,Utils
from waflib.Tools import c_preproc
from waflib.Tools.ccroot import link_task,stlink_task
@TaskGen.extension('.c')
def c_hook(self,node):
	return self.create_compiled_task('c',node)
class c(Task.Task):
	run_str='${CC} ${ARCH_ST:ARCH} ${CFLAGS} ${CPPFLAGS} ${FRAMEWORKPATH_ST:FRAMEWORKPATH} ${CPPPATH_ST:INCPATHS} ${DEFINES_ST:DEFINES} ${CC_SRC_F}${SRC} ${CC_TGT_F}${TGT}'
	vars=['CCDEPS']
	ext_in=['.h']
	scan=c_preproc.scan
class cprogram(link_task):
	run_str='${LINK_CC} ${LINKFLAGS} ${CCLNK_SRC_F}${SRC} ${CCLNK_TGT_F}${TGT[0].abspath()} ${RPATH_ST:RPATH} ${FRAMEWORKPATH_ST:FRAMEWORKPATH} ${FRAMEWORK_ST:FRAMEWORK} ${ARCH_ST:ARCH} ${STLIB_MARKER} ${STLIBPATH_ST:STLIBPATH} ${STLIB_ST:STLIB} ${SHLIB_MARKER} ${LIBPATH_ST:LIBPATH} ${LIB_ST:LIB}'
	ext_out=['.bin']
	vars=['LINKDEPS']
	inst_to='${BINDIR}'
class cshlib(cprogram):
	inst_to='${LIBDIR}'
class cstlib(stlink_task):
	pass

########NEW FILE########
__FILENAME__ = ccroot
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import os,re
from waflib import Task,Utils,Node,Errors
from waflib.TaskGen import after_method,before_method,feature,taskgen_method,extension
from waflib.Tools import c_aliases,c_preproc,c_config,c_osx,c_tests
from waflib.Configure import conf
SYSTEM_LIB_PATHS=['/usr/lib64','/usr/lib','/usr/local/lib64','/usr/local/lib']
USELIB_VARS=Utils.defaultdict(set)
USELIB_VARS['c']=set(['INCLUDES','FRAMEWORKPATH','DEFINES','CPPFLAGS','CCDEPS','CFLAGS','ARCH'])
USELIB_VARS['cxx']=set(['INCLUDES','FRAMEWORKPATH','DEFINES','CPPFLAGS','CXXDEPS','CXXFLAGS','ARCH'])
USELIB_VARS['d']=set(['INCLUDES','DFLAGS'])
USELIB_VARS['includes']=set(['INCLUDES','FRAMEWORKPATH','ARCH'])
USELIB_VARS['cprogram']=USELIB_VARS['cxxprogram']=set(['LIB','STLIB','LIBPATH','STLIBPATH','LINKFLAGS','RPATH','LINKDEPS','FRAMEWORK','FRAMEWORKPATH','ARCH'])
USELIB_VARS['cshlib']=USELIB_VARS['cxxshlib']=set(['LIB','STLIB','LIBPATH','STLIBPATH','LINKFLAGS','RPATH','LINKDEPS','FRAMEWORK','FRAMEWORKPATH','ARCH'])
USELIB_VARS['cstlib']=USELIB_VARS['cxxstlib']=set(['ARFLAGS','LINKDEPS'])
USELIB_VARS['dprogram']=set(['LIB','STLIB','LIBPATH','STLIBPATH','LINKFLAGS','RPATH','LINKDEPS'])
USELIB_VARS['dshlib']=set(['LIB','STLIB','LIBPATH','STLIBPATH','LINKFLAGS','RPATH','LINKDEPS'])
USELIB_VARS['dstlib']=set(['ARFLAGS','LINKDEPS'])
USELIB_VARS['asm']=set(['ASFLAGS'])
@taskgen_method
def create_compiled_task(self,name,node):
	out='%s.%d.o'%(node.name,self.idx)
	task=self.create_task(name,node,node.parent.find_or_declare(out))
	try:
		self.compiled_tasks.append(task)
	except AttributeError:
		self.compiled_tasks=[task]
	return task
@taskgen_method
def to_incnodes(self,inlst):
	lst=[]
	seen=set([])
	for x in self.to_list(inlst):
		if x in seen or not x:
			continue
		seen.add(x)
		if isinstance(x,Node.Node):
			lst.append(x)
		else:
			if os.path.isabs(x):
				lst.append(self.bld.root.make_node(x)or x)
			else:
				if x[0]=='#':
					p=self.bld.bldnode.make_node(x[1:])
					v=self.bld.srcnode.make_node(x[1:])
				else:
					p=self.path.get_bld().make_node(x)
					v=self.path.make_node(x)
				if p.is_child_of(self.bld.bldnode):
					p.mkdir()
				lst.append(p)
				lst.append(v)
	return lst
@feature('c','cxx','d','asm','fc','includes')
@after_method('propagate_uselib_vars','process_source')
def apply_incpaths(self):
	lst=self.to_incnodes(self.to_list(getattr(self,'includes',[]))+self.env['INCLUDES'])
	self.includes_nodes=lst
	self.env['INCPATHS']=[x.abspath()for x in lst]
class link_task(Task.Task):
	color='YELLOW'
	inst_to=None
	chmod=Utils.O755
	def add_target(self,target):
		if isinstance(target,str):
			pattern=self.env[self.__class__.__name__+'_PATTERN']
			if not pattern:
				pattern='%s'
			folder,name=os.path.split(target)
			if self.__class__.__name__.find('shlib')>0 and getattr(self.generator,'vnum',None):
				nums=self.generator.vnum.split('.')
				if self.env.DEST_BINFMT=='pe':
					name=name+'-'+nums[0]
				elif self.env.DEST_OS=='openbsd':
					pattern='%s.%s.%s'%(pattern,nums[0],nums[1])
			tmp=folder+os.sep+pattern%name
			target=self.generator.path.find_or_declare(tmp)
		self.set_outputs(target)
class stlink_task(link_task):
	run_str='${AR} ${ARFLAGS} ${AR_TGT_F}${TGT} ${AR_SRC_F}${SRC}'
def rm_tgt(cls):
	old=cls.run
	def wrap(self):
		try:os.remove(self.outputs[0].abspath())
		except OSError:pass
		return old(self)
	setattr(cls,'run',wrap)
rm_tgt(stlink_task)
@feature('c','cxx','d','fc','asm')
@after_method('process_source')
def apply_link(self):
	for x in self.features:
		if x=='cprogram'and'cxx'in self.features:
			x='cxxprogram'
		elif x=='cshlib'and'cxx'in self.features:
			x='cxxshlib'
		if x in Task.classes:
			if issubclass(Task.classes[x],link_task):
				link=x
				break
	else:
		return
	objs=[t.outputs[0]for t in getattr(self,'compiled_tasks',[])]
	self.link_task=self.create_task(link,objs)
	self.link_task.add_target(self.target)
	try:
		inst_to=self.install_path
	except AttributeError:
		inst_to=self.link_task.__class__.inst_to
	if inst_to:
		self.install_task=self.bld.install_files(inst_to,self.link_task.outputs[:],env=self.env,chmod=self.link_task.chmod)
@taskgen_method
def use_rec(self,name,**kw):
	if name in self.tmp_use_not or name in self.tmp_use_seen:
		return
	try:
		y=self.bld.get_tgen_by_name(name)
	except Errors.WafError:
		self.uselib.append(name)
		self.tmp_use_not.add(name)
		return
	self.tmp_use_seen.append(name)
	y.post()
	y.tmp_use_objects=objects=kw.get('objects',True)
	y.tmp_use_stlib=stlib=kw.get('stlib',True)
	try:
		link_task=y.link_task
	except AttributeError:
		y.tmp_use_var=''
	else:
		objects=False
		if not isinstance(link_task,stlink_task):
			stlib=False
			y.tmp_use_var='LIB'
		else:
			y.tmp_use_var='STLIB'
	p=self.tmp_use_prec
	for x in self.to_list(getattr(y,'use',[])):
		try:
			p[x].append(name)
		except KeyError:
			p[x]=[name]
		self.use_rec(x,objects=objects,stlib=stlib)
@feature('c','cxx','d','use','fc')
@before_method('apply_incpaths','propagate_uselib_vars')
@after_method('apply_link','process_source')
def process_use(self):
	use_not=self.tmp_use_not=set([])
	self.tmp_use_seen=[]
	use_prec=self.tmp_use_prec={}
	self.uselib=self.to_list(getattr(self,'uselib',[]))
	self.includes=self.to_list(getattr(self,'includes',[]))
	names=self.to_list(getattr(self,'use',[]))
	for x in names:
		self.use_rec(x)
	for x in use_not:
		if x in use_prec:
			del use_prec[x]
	out=[]
	tmp=[]
	for x in self.tmp_use_seen:
		for k in use_prec.values():
			if x in k:
				break
		else:
			tmp.append(x)
	while tmp:
		e=tmp.pop()
		out.append(e)
		try:
			nlst=use_prec[e]
		except KeyError:
			pass
		else:
			del use_prec[e]
			for x in nlst:
				for y in use_prec:
					if x in use_prec[y]:
						break
				else:
					tmp.append(x)
	if use_prec:
		raise Errors.WafError('Cycle detected in the use processing %r'%use_prec)
	out.reverse()
	link_task=getattr(self,'link_task',None)
	for x in out:
		y=self.bld.get_tgen_by_name(x)
		var=y.tmp_use_var
		if var and link_task:
			if var=='LIB'or y.tmp_use_stlib:
				self.env.append_value(var,[y.target[y.target.rfind(os.sep)+1:]])
				self.link_task.dep_nodes.extend(y.link_task.outputs)
				tmp_path=y.link_task.outputs[0].parent.path_from(self.bld.bldnode)
				self.env.append_value(var+'PATH',[tmp_path])
		else:
			if y.tmp_use_objects:
				self.add_objects_from_tgen(y)
		if getattr(y,'export_includes',None):
			self.includes.extend(y.to_incnodes(y.export_includes))
		if getattr(y,'export_defines',None):
			self.env.append_value('DEFINES',self.to_list(y.export_defines))
	for x in names:
		try:
			y=self.bld.get_tgen_by_name(x)
		except Exception:
			if not self.env['STLIB_'+x]and not x in self.uselib:
				self.uselib.append(x)
		else:
			for k in self.to_list(getattr(y,'uselib',[])):
				if not self.env['STLIB_'+k]and not k in self.uselib:
					self.uselib.append(k)
@taskgen_method
def accept_node_to_link(self,node):
	return not node.name.endswith('.pdb')
@taskgen_method
def add_objects_from_tgen(self,tg):
	try:
		link_task=self.link_task
	except AttributeError:
		pass
	else:
		for tsk in getattr(tg,'compiled_tasks',[]):
			for x in tsk.outputs:
				if self.accept_node_to_link(x):
					link_task.inputs.append(x)
@taskgen_method
def get_uselib_vars(self):
	_vars=set([])
	for x in self.features:
		if x in USELIB_VARS:
			_vars|=USELIB_VARS[x]
	return _vars
@feature('c','cxx','d','fc','javac','cs','uselib','asm')
@after_method('process_use')
def propagate_uselib_vars(self):
	_vars=self.get_uselib_vars()
	env=self.env
	for x in _vars:
		y=x.lower()
		env.append_unique(x,self.to_list(getattr(self,y,[])))
	for x in self.features:
		for var in _vars:
			compvar='%s_%s'%(var,x)
			env.append_value(var,env[compvar])
	for x in self.to_list(getattr(self,'uselib',[])):
		for v in _vars:
			env.append_value(v,env[v+'_'+x])
@feature('cshlib','cxxshlib','fcshlib')
@after_method('apply_link')
def apply_implib(self):
	if not self.env.DEST_BINFMT=='pe':
		return
	dll=self.link_task.outputs[0]
	if isinstance(self.target,Node.Node):
		name=self.target.name
	else:
		name=os.path.split(self.target)[1]
	implib=self.env['implib_PATTERN']%name
	implib=dll.parent.find_or_declare(implib)
	self.env.append_value('LINKFLAGS',self.env['IMPLIB_ST']%implib.bldpath())
	self.link_task.outputs.append(implib)
	if getattr(self,'defs',None)and self.env.DEST_BINFMT=='pe':
		node=self.path.find_resource(self.defs)
		if not node:
			raise Errors.WafError('invalid def file %r'%self.defs)
		if'msvc'in(self.env.CC_NAME,self.env.CXX_NAME):
			self.env.append_value('LINKFLAGS','/def:%s'%node.path_from(self.bld.bldnode))
			self.link_task.dep_nodes.append(node)
		else:
			self.link_task.inputs.append(node)
	try:
		inst_to=self.install_path
	except AttributeError:
		inst_to=self.link_task.__class__.inst_to
	if not inst_to:
		return
	self.implib_install_task=self.bld.install_as('${LIBDIR}/%s'%implib.name,implib,self.env)
re_vnum=re.compile('^([1-9]\\d*|0)[.]([1-9]\\d*|0)[.]([1-9]\\d*|0)$')
@feature('cshlib','cxxshlib','dshlib','fcshlib','vnum')
@after_method('apply_link','propagate_uselib_vars')
def apply_vnum(self):
	if not getattr(self,'vnum','')or os.name!='posix'or self.env.DEST_BINFMT not in('elf','mac-o'):
		return
	link=self.link_task
	if not re_vnum.match(self.vnum):
		raise Errors.WafError('Invalid version %r for %r'%(self.vnum,self))
	nums=self.vnum.split('.')
	node=link.outputs[0]
	libname=node.name
	if libname.endswith('.dylib'):
		name3=libname.replace('.dylib','.%s.dylib'%self.vnum)
		name2=libname.replace('.dylib','.%s.dylib'%nums[0])
	else:
		name3=libname+'.'+self.vnum
		name2=libname+'.'+nums[0]
	if self.env.SONAME_ST:
		v=self.env.SONAME_ST%name2
		self.env.append_value('LINKFLAGS',v.split())
	if self.env.DEST_OS!='openbsd':
		self.create_task('vnum',node,[node.parent.find_or_declare(name2),node.parent.find_or_declare(name3)])
	if getattr(self,'install_task',None):
		self.install_task.hasrun=Task.SKIP_ME
		bld=self.bld
		path=self.install_task.dest
		if self.env.DEST_OS=='openbsd':
			libname=self.link_task.outputs[0].name
			t1=bld.install_as('%s%s%s'%(path,os.sep,libname),node,env=self.env,chmod=self.link_task.chmod)
			self.vnum_install_task=(t1,)
		else:
			t1=bld.install_as(path+os.sep+name3,node,env=self.env,chmod=self.link_task.chmod)
			t2=bld.symlink_as(path+os.sep+name2,name3)
			t3=bld.symlink_as(path+os.sep+libname,name3)
			self.vnum_install_task=(t1,t2,t3)
	if'-dynamiclib'in self.env['LINKFLAGS']:
		try:
			inst_to=self.install_path
		except AttributeError:
			inst_to=self.link_task.__class__.inst_to
		if inst_to:
			p=Utils.subst_vars(inst_to,self.env)
			path=os.path.join(p,self.link_task.outputs[0].name)
			self.env.append_value('LINKFLAGS',['-install_name',path])
class vnum(Task.Task):
	color='CYAN'
	quient=True
	ext_in=['.bin']
	def run(self):
		for x in self.outputs:
			path=x.abspath()
			try:
				os.remove(path)
			except OSError:
				pass
			try:
				os.symlink(self.inputs[0].name,path)
			except OSError:
				return 1
class fake_shlib(link_task):
	def runnable_status(self):
		for t in self.run_after:
			if not t.hasrun:
				return Task.ASK_LATER
		for x in self.outputs:
			x.sig=Utils.h_file(x.abspath())
		return Task.SKIP_ME
class fake_stlib(stlink_task):
	def runnable_status(self):
		for t in self.run_after:
			if not t.hasrun:
				return Task.ASK_LATER
		for x in self.outputs:
			x.sig=Utils.h_file(x.abspath())
		return Task.SKIP_ME
@conf
def read_shlib(self,name,paths=[],export_includes=[],export_defines=[]):
	return self(name=name,features='fake_lib',lib_paths=paths,lib_type='shlib',export_includes=export_includes,export_defines=export_defines)
@conf
def read_stlib(self,name,paths=[],export_includes=[],export_defines=[]):
	return self(name=name,features='fake_lib',lib_paths=paths,lib_type='stlib',export_includes=export_includes,export_defines=export_defines)
lib_patterns={'shlib':['lib%s.so','%s.so','lib%s.dylib','lib%s.dll','%s.dll'],'stlib':['lib%s.a','%s.a','lib%s.dll','%s.dll','lib%s.lib','%s.lib'],}
@feature('fake_lib')
def process_lib(self):
	node=None
	names=[x%self.name for x in lib_patterns[self.lib_type]]
	for x in self.lib_paths+[self.path]+SYSTEM_LIB_PATHS:
		if not isinstance(x,Node.Node):
			x=self.bld.root.find_node(x)or self.path.find_node(x)
			if not x:
				continue
		for y in names:
			node=x.find_node(y)
			if node:
				node.sig=Utils.h_file(node.abspath())
				break
		else:
			continue
		break
	else:
		raise Errors.WafError('could not find library %r'%self.name)
	self.link_task=self.create_task('fake_%s'%self.lib_type,[],[node])
	self.target=self.name
class fake_o(Task.Task):
	def runnable_status(self):
		return Task.SKIP_ME
@extension('.o','.obj')
def add_those_o_files(self,node):
	tsk=self.create_task('fake_o',[],node)
	try:
		self.compiled_tasks.append(tsk)
	except AttributeError:
		self.compiled_tasks=[tsk]
@feature('fake_obj')
@before_method('process_source')
def process_objs(self):
	for node in self.to_nodes(self.source):
		self.add_those_o_files(node)
	self.source=[]
@conf
def read_object(self,obj):
	if not isinstance(obj,self.path.__class__):
		obj=self.path.find_resource(obj)
	return self(features='fake_obj',source=obj,name=obj.name)

########NEW FILE########
__FILENAME__ = compiler_c
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import os,sys,imp,types
from waflib.Tools import ccroot
from waflib import Utils,Configure
from waflib.Logs import debug
c_compiler={'win32':['msvc','gcc'],'cygwin':['gcc'],'darwin':['gcc'],'aix':['xlc','gcc'],'linux':['gcc','icc'],'sunos':['suncc','gcc'],'irix':['gcc','irixcc'],'hpux':['gcc'],'gnu':['gcc'],'java':['gcc','msvc','icc'],'default':['gcc'],}
def configure(conf):
	try:test_for_compiler=conf.options.check_c_compiler
	except AttributeError:conf.fatal("Add options(opt): opt.load('compiler_c')")
	for compiler in test_for_compiler.split():
		conf.env.stash()
		conf.start_msg('Checking for %r (c compiler)'%compiler)
		try:
			conf.load(compiler)
		except conf.errors.ConfigurationError ,e:
			conf.env.revert()
			conf.end_msg(False)
			debug('compiler_c: %r'%e)
		else:
			if conf.env['CC']:
				conf.end_msg(conf.env.get_flat('CC'))
				conf.env['COMPILER_CC']=compiler
				break
			conf.end_msg(False)
	else:
		conf.fatal('could not configure a c compiler!')
def options(opt):
	opt.load_special_tools('c_*.py',ban=['c_dumbpreproc.py'])
	global c_compiler
	build_platform=Utils.unversioned_sys_platform()
	possible_compiler_list=c_compiler[build_platform in c_compiler and build_platform or'default']
	test_for_compiler=' '.join(possible_compiler_list)
	cc_compiler_opts=opt.add_option_group("C Compiler Options")
	cc_compiler_opts.add_option('--check-c-compiler',default="%s"%test_for_compiler,help='On this platform (%s) the following C-Compiler will be checked by default: "%s"'%(build_platform,test_for_compiler),dest="check_c_compiler")
	for x in test_for_compiler.split():
		opt.load('%s'%x)

########NEW FILE########
__FILENAME__ = compiler_cxx
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import os,sys,imp,types
from waflib.Tools import ccroot
from waflib import Utils,Configure
from waflib.Logs import debug
cxx_compiler={'win32':['msvc','g++'],'cygwin':['g++'],'darwin':['g++'],'aix':['xlc++','g++'],'linux':['g++','icpc'],'sunos':['sunc++','g++'],'irix':['g++'],'hpux':['g++'],'gnu':['g++'],'java':['g++','msvc','icpc'],'default':['g++']}
def configure(conf):
	try:test_for_compiler=conf.options.check_cxx_compiler
	except AttributeError:conf.fatal("Add options(opt): opt.load('compiler_cxx')")
	for compiler in test_for_compiler.split():
		conf.env.stash()
		conf.start_msg('Checking for %r (c++ compiler)'%compiler)
		try:
			conf.load(compiler)
		except conf.errors.ConfigurationError ,e:
			conf.env.revert()
			conf.end_msg(False)
			debug('compiler_cxx: %r'%e)
		else:
			if conf.env['CXX']:
				conf.end_msg(conf.env.get_flat('CXX'))
				conf.env['COMPILER_CXX']=compiler
				break
			conf.end_msg(False)
	else:
		conf.fatal('could not configure a c++ compiler!')
def options(opt):
	opt.load_special_tools('cxx_*.py')
	global cxx_compiler
	build_platform=Utils.unversioned_sys_platform()
	possible_compiler_list=cxx_compiler[build_platform in cxx_compiler and build_platform or'default']
	test_for_compiler=' '.join(possible_compiler_list)
	cxx_compiler_opts=opt.add_option_group('C++ Compiler Options')
	cxx_compiler_opts.add_option('--check-cxx-compiler',default="%s"%test_for_compiler,help='On this platform (%s) the following C++ Compiler will be checked by default: "%s"'%(build_platform,test_for_compiler),dest="check_cxx_compiler")
	for x in test_for_compiler.split():
		opt.load('%s'%x)

########NEW FILE########
__FILENAME__ = compiler_d
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import os,sys,imp,types
from waflib import Utils,Configure,Options,Logs
def configure(conf):
	for compiler in conf.options.dcheck.split(','):
		conf.env.stash()
		conf.start_msg('Checking for %r (d compiler)'%compiler)
		try:
			conf.load(compiler)
		except conf.errors.ConfigurationError ,e:
			conf.env.revert()
			conf.end_msg(False)
			Logs.debug('compiler_d: %r'%e)
		else:
			if conf.env.D:
				conf.end_msg(conf.env.get_flat('D'))
				conf.env['COMPILER_D']=compiler
				break
			conf.end_msg(False)
	else:
		conf.fatal('no suitable d compiler was found')
def options(opt):
	d_compiler_opts=opt.add_option_group('D Compiler Options')
	d_compiler_opts.add_option('--check-d-compiler',default='gdc,dmd,ldc2',action='store',help='check for the compiler [Default:gdc,dmd,ldc2]',dest='dcheck')
	for d_compiler in['gdc','dmd','ldc2']:
		opt.load('%s'%d_compiler)

########NEW FILE########
__FILENAME__ = compiler_fc
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import os,sys,imp,types
from waflib import Utils,Configure,Options,Logs,Errors
from waflib.Tools import fc
fc_compiler={'win32':['gfortran','ifort'],'darwin':['gfortran','g95','ifort'],'linux':['gfortran','g95','ifort'],'java':['gfortran','g95','ifort'],'default':['gfortran'],'aix':['gfortran']}
def __list_possible_compiler(platform):
	try:
		return fc_compiler[platform]
	except KeyError:
		return fc_compiler["default"]
def configure(conf):
	try:test_for_compiler=conf.options.check_fc
	except AttributeError:conf.fatal("Add options(opt): opt.load('compiler_fc')")
	for compiler in test_for_compiler.split():
		conf.env.stash()
		conf.start_msg('Checking for %r (fortran compiler)'%compiler)
		try:
			conf.load(compiler)
		except conf.errors.ConfigurationError ,e:
			conf.env.revert()
			conf.end_msg(False)
			Logs.debug('compiler_fortran: %r'%e)
		else:
			if conf.env['FC']:
				conf.end_msg(conf.env.get_flat('FC'))
				conf.env.COMPILER_FORTRAN=compiler
				break
			conf.end_msg(False)
	else:
		conf.fatal('could not configure a fortran compiler!')
def options(opt):
	opt.load_special_tools('fc_*.py')
	build_platform=Utils.unversioned_sys_platform()
	detected_platform=Options.platform
	possible_compiler_list=__list_possible_compiler(detected_platform)
	test_for_compiler=' '.join(possible_compiler_list)
	fortran_compiler_opts=opt.add_option_group("Fortran Compiler Options")
	fortran_compiler_opts.add_option('--check-fortran-compiler',default="%s"%test_for_compiler,help='On this platform (%s) the following Fortran Compiler will be checked by default: "%s"'%(detected_platform,test_for_compiler),dest="check_fc")
	for compiler in test_for_compiler.split():
		opt.load('%s'%compiler)

########NEW FILE########
__FILENAME__ = cs
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

from waflib import Utils,Task,Options,Logs,Errors
from waflib.TaskGen import before_method,after_method,feature
from waflib.Tools import ccroot
from waflib.Configure import conf
import os,tempfile
ccroot.USELIB_VARS['cs']=set(['CSFLAGS','ASSEMBLIES','RESOURCES'])
ccroot.lib_patterns['csshlib']=['%s']
@feature('cs')
@before_method('process_source')
def apply_cs(self):
	cs_nodes=[]
	no_nodes=[]
	for x in self.to_nodes(self.source):
		if x.name.endswith('.cs'):
			cs_nodes.append(x)
		else:
			no_nodes.append(x)
	self.source=no_nodes
	bintype=getattr(self,'bintype',self.gen.endswith('.dll')and'library'or'exe')
	self.cs_task=tsk=self.create_task('mcs',cs_nodes,self.path.find_or_declare(self.gen))
	tsk.env.CSTYPE='/target:%s'%bintype
	tsk.env.OUT='/out:%s'%tsk.outputs[0].abspath()
	self.env.append_value('CSFLAGS','/platform:%s'%getattr(self,'platform','anycpu'))
	inst_to=getattr(self,'install_path',bintype=='exe'and'${BINDIR}'or'${LIBDIR}')
	if inst_to:
		mod=getattr(self,'chmod',bintype=='exe'and Utils.O755 or Utils.O644)
		self.install_task=self.bld.install_files(inst_to,self.cs_task.outputs[:],env=self.env,chmod=mod)
@feature('cs')
@after_method('apply_cs')
def use_cs(self):
	names=self.to_list(getattr(self,'use',[]))
	get=self.bld.get_tgen_by_name
	for x in names:
		try:
			y=get(x)
		except Errors.WafError:
			self.env.append_value('CSFLAGS','/reference:%s'%x)
			continue
		y.post()
		tsk=getattr(y,'cs_task',None)or getattr(y,'link_task',None)
		if not tsk:
			self.bld.fatal('cs task has no link task for use %r'%self)
		self.cs_task.dep_nodes.extend(tsk.outputs)
		self.cs_task.set_run_after(tsk)
		self.env.append_value('CSFLAGS','/reference:%s'%tsk.outputs[0].abspath())
@feature('cs')
@after_method('apply_cs','use_cs')
def debug_cs(self):
	csdebug=getattr(self,'csdebug',self.env.CSDEBUG)
	if not csdebug:
		return
	node=self.cs_task.outputs[0]
	if self.env.CS_NAME=='mono':
		out=node.parent.find_or_declare(node.name+'.mdb')
	else:
		out=node.change_ext('.pdb')
	self.cs_task.outputs.append(out)
	try:
		self.install_task.source.append(out)
	except AttributeError:
		pass
	if csdebug=='pdbonly':
		val=['/debug+','/debug:pdbonly']
	elif csdebug=='full':
		val=['/debug+','/debug:full']
	else:
		val=['/debug-']
	self.env.append_value('CSFLAGS',val)
class mcs(Task.Task):
	color='YELLOW'
	run_str='${MCS} ${CSTYPE} ${CSFLAGS} ${ASS_ST:ASSEMBLIES} ${RES_ST:RESOURCES} ${OUT} ${SRC}'
	def exec_command(self,cmd,**kw):
		bld=self.generator.bld
		try:
			if not kw.get('cwd',None):
				kw['cwd']=bld.cwd
		except AttributeError:
			bld.cwd=kw['cwd']=bld.variant_dir
		try:
			tmp=None
			if isinstance(cmd,list)and len(' '.join(cmd))>=8192:
				program=cmd[0]
				cmd=[self.quote_response_command(x)for x in cmd]
				(fd,tmp)=tempfile.mkstemp()
				os.write(fd,'\r\n'.join(i.replace('\\','\\\\')for i in cmd[1:]))
				os.close(fd)
				cmd=[program,'@'+tmp]
			ret=self.generator.bld.exec_command(cmd,**kw)
		finally:
			if tmp:
				try:
					os.remove(tmp)
				except OSError:
					pass
		return ret
	def quote_response_command(self,flag):
		if flag.lower()=='/noconfig':
			return''
		if flag.find(' ')>-1:
			for x in('/r:','/reference:','/resource:','/lib:','/out:'):
				if flag.startswith(x):
					flag='%s"%s"'%(x,'","'.join(flag[len(x):].split(',')))
					break
			else:
				flag='"%s"'%flag
		return flag
def configure(conf):
	csc=getattr(Options.options,'cscbinary',None)
	if csc:
		conf.env.MCS=csc
	conf.find_program(['csc','mcs','gmcs'],var='MCS')
	conf.env.ASS_ST='/r:%s'
	conf.env.RES_ST='/resource:%s'
	conf.env.CS_NAME='csc'
	if str(conf.env.MCS).lower().find('mcs')>-1:
		conf.env.CS_NAME='mono'
def options(opt):
	opt.add_option('--with-csc-binary',type='string',dest='cscbinary')
class fake_csshlib(Task.Task):
	color='YELLOW'
	inst_to=None
	def runnable_status(self):
		for x in self.outputs:
			x.sig=Utils.h_file(x.abspath())
		return Task.SKIP_ME
@conf
def read_csshlib(self,name,paths=[]):
	return self(name=name,features='fake_lib',lib_paths=paths,lib_type='csshlib')

########NEW FILE########
__FILENAME__ = cxx
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

from waflib import TaskGen,Task,Utils
from waflib.Tools import c_preproc
from waflib.Tools.ccroot import link_task,stlink_task
@TaskGen.extension('.cpp','.cc','.cxx','.C','.c++')
def cxx_hook(self,node):
	return self.create_compiled_task('cxx',node)
if not'.c'in TaskGen.task_gen.mappings:
	TaskGen.task_gen.mappings['.c']=TaskGen.task_gen.mappings['.cpp']
class cxx(Task.Task):
	run_str='${CXX} ${ARCH_ST:ARCH} ${CXXFLAGS} ${CPPFLAGS} ${FRAMEWORKPATH_ST:FRAMEWORKPATH} ${CPPPATH_ST:INCPATHS} ${DEFINES_ST:DEFINES} ${CXX_SRC_F}${SRC} ${CXX_TGT_F}${TGT}'
	vars=['CXXDEPS']
	ext_in=['.h']
	scan=c_preproc.scan
class cxxprogram(link_task):
	run_str='${LINK_CXX} ${LINKFLAGS} ${CXXLNK_SRC_F}${SRC} ${CXXLNK_TGT_F}${TGT[0].abspath()} ${RPATH_ST:RPATH} ${FRAMEWORKPATH_ST:FRAMEWORKPATH} ${FRAMEWORK_ST:FRAMEWORK} ${ARCH_ST:ARCH} ${STLIB_MARKER} ${STLIBPATH_ST:STLIBPATH} ${STLIB_ST:STLIB} ${SHLIB_MARKER} ${LIBPATH_ST:LIBPATH} ${LIB_ST:LIB}'
	vars=['LINKDEPS']
	ext_out=['.bin']
	inst_to='${BINDIR}'
class cxxshlib(cxxprogram):
	inst_to='${LIBDIR}'
class cxxstlib(stlink_task):
	pass

########NEW FILE########
__FILENAME__ = c_aliases
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import os,sys,re
from waflib import Utils,Build
from waflib.Configure import conf
def get_extensions(lst):
	ret=[]
	for x in Utils.to_list(lst):
		try:
			if not isinstance(x,str):
				x=x.name
			ret.append(x[x.rfind('.')+1:])
		except Exception:
			pass
	return ret
def sniff_features(**kw):
	exts=get_extensions(kw['source'])
	type=kw['_type']
	feats=[]
	if'cxx'in exts or'cpp'in exts or'c++'in exts or'cc'in exts or'C'in exts:
		feats.append('cxx')
	if'c'in exts or'vala'in exts:
		feats.append('c')
	if'd'in exts:
		feats.append('d')
	if'java'in exts:
		feats.append('java')
	if'java'in exts:
		return'java'
	if type in['program','shlib','stlib']:
		for x in feats:
			if x in['cxx','d','c']:
				feats.append(x+type)
	return feats
def set_features(kw,_type):
	kw['_type']=_type
	kw['features']=Utils.to_list(kw.get('features',[]))+Utils.to_list(sniff_features(**kw))
@conf
def program(bld,*k,**kw):
	set_features(kw,'program')
	return bld(*k,**kw)
@conf
def shlib(bld,*k,**kw):
	set_features(kw,'shlib')
	return bld(*k,**kw)
@conf
def stlib(bld,*k,**kw):
	set_features(kw,'stlib')
	return bld(*k,**kw)
@conf
def objects(bld,*k,**kw):
	set_features(kw,'objects')
	return bld(*k,**kw)

########NEW FILE########
__FILENAME__ = c_config
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import os,re,shlex,sys
from waflib import Build,Utils,Task,Options,Logs,Errors,ConfigSet,Runner
from waflib.TaskGen import after_method,feature
from waflib.Configure import conf
WAF_CONFIG_H='config.h'
DEFKEYS='define_key'
INCKEYS='include_key'
cfg_ver={'atleast-version':'>=','exact-version':'==','max-version':'<=',}
SNIP_FUNCTION='''
int main(int argc, char **argv) {
	void *p;
	(void)argc; (void)argv;
	p=(void*)(%s);
	return 0;
}
'''
SNIP_TYPE='''
int main(int argc, char **argv) {
	(void)argc; (void)argv;
	if ((%(type_name)s *) 0) return 0;
	if (sizeof (%(type_name)s)) return 0;
	return 1;
}
'''
SNIP_EMPTY_PROGRAM='''
int main(int argc, char **argv) {
	(void)argc; (void)argv;
	return 0;
}
'''
SNIP_FIELD='''
int main(int argc, char **argv) {
	char *off;
	(void)argc; (void)argv;
	off = (char*) &((%(type_name)s*)0)->%(field_name)s;
	return (size_t) off < sizeof(%(type_name)s);
}
'''
MACRO_TO_DESTOS={'__linux__':'linux','__GNU__':'gnu','__FreeBSD__':'freebsd','__NetBSD__':'netbsd','__OpenBSD__':'openbsd','__sun':'sunos','__hpux':'hpux','__sgi':'irix','_AIX':'aix','__CYGWIN__':'cygwin','__MSYS__':'msys','_UWIN':'uwin','_WIN64':'win32','_WIN32':'win32','__ENVIRONMENT_MAC_OS_X_VERSION_MIN_REQUIRED__':'darwin','__ENVIRONMENT_IPHONE_OS_VERSION_MIN_REQUIRED__':'darwin','__QNX__':'qnx','__native_client__':'nacl'}
MACRO_TO_DEST_CPU={'__x86_64__':'x86_64','__amd64__':'x86_64','__i386__':'x86','__ia64__':'ia','__mips__':'mips','__sparc__':'sparc','__alpha__':'alpha','__aarch64__':'aarch64','__thumb__':'thumb','__arm__':'arm','__hppa__':'hppa','__powerpc__':'powerpc','__ppc__':'powerpc','__convex__':'convex','__m68k__':'m68k','__s390x__':'s390x','__s390__':'s390','__sh__':'sh',}
@conf
def parse_flags(self,line,uselib_store,env=None,force_static=False):
	assert(isinstance(line,str))
	env=env or self.env
	app=env.append_value
	appu=env.append_unique
	lex=shlex.shlex(line,posix=False)
	lex.whitespace_split=True
	lex.commenters=''
	lst=list(lex)
	uselib=uselib_store
	while lst:
		x=lst.pop(0)
		st=x[:2]
		ot=x[2:]
		if st=='-I'or st=='/I':
			if not ot:ot=lst.pop(0)
			appu('INCLUDES_'+uselib,[ot])
		elif st=='-include':
			tmp=[x,lst.pop(0)]
			app('CFLAGS',tmp)
			app('CXXFLAGS',tmp)
		elif st=='-D'or(env.CXX_NAME=='msvc'and st=='/D'):
			if not ot:ot=lst.pop(0)
			app('DEFINES_'+uselib,[ot])
		elif st=='-l':
			if not ot:ot=lst.pop(0)
			prefix=force_static and'STLIB_'or'LIB_'
			appu(prefix+uselib,[ot])
		elif st=='-L':
			if not ot:ot=lst.pop(0)
			appu('LIBPATH_'+uselib,[ot])
		elif x.startswith('/LIBPATH:'):
			appu('LIBPATH_'+uselib,[x.replace('/LIBPATH:','')])
		elif x=='-pthread'or x.startswith('+')or x.startswith('-std'):
			app('CFLAGS_'+uselib,[x])
			app('CXXFLAGS_'+uselib,[x])
			app('LINKFLAGS_'+uselib,[x])
		elif x=='-framework':
			appu('FRAMEWORK_'+uselib,[lst.pop(0)])
		elif x.startswith('-F'):
			appu('FRAMEWORKPATH_'+uselib,[x[2:]])
		elif x.startswith('-Wl'):
			app('LINKFLAGS_'+uselib,[x])
		elif x.startswith('-m')or x.startswith('-f')or x.startswith('-dynamic'):
			app('CFLAGS_'+uselib,[x])
			app('CXXFLAGS_'+uselib,[x])
		elif x.startswith('-bundle'):
			app('LINKFLAGS_'+uselib,[x])
		elif x.startswith('-undefined'):
			arg=lst.pop(0)
			app('LINKFLAGS_'+uselib,[x,arg])
		elif x.startswith('-arch')or x.startswith('-isysroot'):
			tmp=[x,lst.pop(0)]
			app('CFLAGS_'+uselib,tmp)
			app('CXXFLAGS_'+uselib,tmp)
			app('LINKFLAGS_'+uselib,tmp)
		elif x.endswith('.a')or x.endswith('.so')or x.endswith('.dylib')or x.endswith('.lib'):
			appu('LINKFLAGS_'+uselib,[x])
@conf
def ret_msg(self,f,kw):
	if isinstance(f,str):
		return f
	return f(kw)
@conf
def validate_cfg(self,kw):
	if not'path'in kw:
		if not self.env.PKGCONFIG:
			self.find_program('pkg-config',var='PKGCONFIG')
		kw['path']=self.env.PKGCONFIG
	if'atleast_pkgconfig_version'in kw:
		if not'msg'in kw:
			kw['msg']='Checking for pkg-config version >= %r'%kw['atleast_pkgconfig_version']
		return
	if not'okmsg'in kw:
		kw['okmsg']='yes'
	if not'errmsg'in kw:
		kw['errmsg']='not found'
	if'modversion'in kw:
		if not'msg'in kw:
			kw['msg']='Checking for %r version'%kw['modversion']
		return
	for x in cfg_ver.keys():
		y=x.replace('-','_')
		if y in kw:
			if not'package'in kw:
				raise ValueError('%s requires a package'%x)
			if not'msg'in kw:
				kw['msg']='Checking for %r %s %s'%(kw['package'],cfg_ver[x],kw[y])
			return
	if not'msg'in kw:
		kw['msg']='Checking for %r'%(kw['package']or kw['path'])
@conf
def exec_cfg(self,kw):
	def define_it():
		self.define(self.have_define(kw.get('uselib_store',kw['package'])),1,0)
	if'atleast_pkgconfig_version'in kw:
		cmd=[kw['path'],'--atleast-pkgconfig-version=%s'%kw['atleast_pkgconfig_version']]
		self.cmd_and_log(cmd)
		if not'okmsg'in kw:
			kw['okmsg']='yes'
		return
	for x in cfg_ver:
		y=x.replace('-','_')
		if y in kw:
			self.cmd_and_log([kw['path'],'--%s=%s'%(x,kw[y]),kw['package']])
			if not'okmsg'in kw:
				kw['okmsg']='yes'
			define_it()
			break
	if'modversion'in kw:
		version=self.cmd_and_log([kw['path'],'--modversion',kw['modversion']]).strip()
		self.define('%s_VERSION'%Utils.quote_define_name(kw.get('uselib_store',kw['modversion'])),version)
		return version
	lst=[kw['path']]
	defi=kw.get('define_variable',None)
	if not defi:
		defi=self.env.PKG_CONFIG_DEFINES or{}
	for key,val in defi.items():
		lst.append('--define-variable=%s=%s'%(key,val))
	static=False
	if'args'in kw:
		args=Utils.to_list(kw['args'])
		if'--static'in args or'--static-libs'in args:
			static=True
		lst+=args
	lst.extend(Utils.to_list(kw['package']))
	if'variables'in kw:
		env=kw.get('env',self.env)
		uselib=kw.get('uselib_store',kw['package'].upper())
		vars=Utils.to_list(kw['variables'])
		for v in vars:
			val=self.cmd_and_log(lst+['--variable='+v]).strip()
			var='%s_%s'%(uselib,v)
			env[var]=val
		if not'okmsg'in kw:
			kw['okmsg']='yes'
		return
	ret=self.cmd_and_log(lst)
	if not'okmsg'in kw:
		kw['okmsg']='yes'
	define_it()
	self.parse_flags(ret,kw.get('uselib_store',kw['package'].upper()),kw.get('env',self.env),force_static=static)
	return ret
@conf
def check_cfg(self,*k,**kw):
	if k:
		lst=k[0].split()
		kw['package']=lst[0]
		kw['args']=' '.join(lst[1:])
	self.validate_cfg(kw)
	if'msg'in kw:
		self.start_msg(kw['msg'])
	ret=None
	try:
		ret=self.exec_cfg(kw)
	except self.errors.WafError:
		if'errmsg'in kw:
			self.end_msg(kw['errmsg'],'YELLOW')
		if Logs.verbose>1:
			raise
		else:
			self.fatal('The configuration failed')
	else:
		kw['success']=ret
		if'okmsg'in kw:
			self.end_msg(self.ret_msg(kw['okmsg'],kw))
	return ret
@conf
def validate_c(self,kw):
	if not'env'in kw:
		kw['env']=self.env.derive()
	env=kw['env']
	if not'compiler'in kw and not'features'in kw:
		kw['compiler']='c'
		if env['CXX_NAME']and Task.classes.get('cxx',None):
			kw['compiler']='cxx'
			if not self.env['CXX']:
				self.fatal('a c++ compiler is required')
		else:
			if not self.env['CC']:
				self.fatal('a c compiler is required')
	if not'compile_mode'in kw:
		kw['compile_mode']='c'
		if'cxx'in Utils.to_list(kw.get('features',[]))or kw.get('compiler','')=='cxx':
			kw['compile_mode']='cxx'
	if not'type'in kw:
		kw['type']='cprogram'
	if not'features'in kw:
		kw['features']=[kw['compile_mode'],kw['type']]
	else:
		kw['features']=Utils.to_list(kw['features'])
	if not'compile_filename'in kw:
		kw['compile_filename']='test.c'+((kw['compile_mode']=='cxx')and'pp'or'')
	def to_header(dct):
		if'header_name'in dct:
			dct=Utils.to_list(dct['header_name'])
			return''.join(['#include <%s>\n'%x for x in dct])
		return''
	if'framework_name'in kw:
		fwkname=kw['framework_name']
		if not'uselib_store'in kw:
			kw['uselib_store']=fwkname.upper()
		if not kw.get('no_header',False):
			if not'header_name'in kw:
				kw['header_name']=[]
			fwk='%s/%s.h'%(fwkname,fwkname)
			if kw.get('remove_dot_h',None):
				fwk=fwk[:-2]
			kw['header_name']=Utils.to_list(kw['header_name'])+[fwk]
		kw['msg']='Checking for framework %s'%fwkname
		kw['framework']=fwkname
	if'function_name'in kw:
		fu=kw['function_name']
		if not'msg'in kw:
			kw['msg']='Checking for function %s'%fu
		kw['code']=to_header(kw)+SNIP_FUNCTION%fu
		if not'uselib_store'in kw:
			kw['uselib_store']=fu.upper()
		if not'define_name'in kw:
			kw['define_name']=self.have_define(fu)
	elif'type_name'in kw:
		tu=kw['type_name']
		if not'header_name'in kw:
			kw['header_name']='stdint.h'
		if'field_name'in kw:
			field=kw['field_name']
			kw['code']=to_header(kw)+SNIP_FIELD%{'type_name':tu,'field_name':field}
			if not'msg'in kw:
				kw['msg']='Checking for field %s in %s'%(field,tu)
			if not'define_name'in kw:
				kw['define_name']=self.have_define((tu+'_'+field).upper())
		else:
			kw['code']=to_header(kw)+SNIP_TYPE%{'type_name':tu}
			if not'msg'in kw:
				kw['msg']='Checking for type %s'%tu
			if not'define_name'in kw:
				kw['define_name']=self.have_define(tu.upper())
	elif'header_name'in kw:
		if not'msg'in kw:
			kw['msg']='Checking for header %s'%kw['header_name']
		l=Utils.to_list(kw['header_name'])
		assert len(l)>0,'list of headers in header_name is empty'
		kw['code']=to_header(kw)+SNIP_EMPTY_PROGRAM
		if not'uselib_store'in kw:
			kw['uselib_store']=l[0].upper()
		if not'define_name'in kw:
			kw['define_name']=self.have_define(l[0])
	if'lib'in kw:
		if not'msg'in kw:
			kw['msg']='Checking for library %s'%kw['lib']
		if not'uselib_store'in kw:
			kw['uselib_store']=kw['lib'].upper()
	if'stlib'in kw:
		if not'msg'in kw:
			kw['msg']='Checking for static library %s'%kw['stlib']
		if not'uselib_store'in kw:
			kw['uselib_store']=kw['stlib'].upper()
	if'fragment'in kw:
		kw['code']=kw['fragment']
		if not'msg'in kw:
			kw['msg']='Checking for code snippet'
		if not'errmsg'in kw:
			kw['errmsg']='no'
	for(flagsname,flagstype)in[('cxxflags','compiler'),('cflags','compiler'),('linkflags','linker')]:
		if flagsname in kw:
			if not'msg'in kw:
				kw['msg']='Checking for %s flags %s'%(flagstype,kw[flagsname])
			if not'errmsg'in kw:
				kw['errmsg']='no'
	if not'execute'in kw:
		kw['execute']=False
	if kw['execute']:
		kw['features'].append('test_exec')
	if not'errmsg'in kw:
		kw['errmsg']='not found'
	if not'okmsg'in kw:
		kw['okmsg']='yes'
	if not'code'in kw:
		kw['code']=SNIP_EMPTY_PROGRAM
	if self.env[INCKEYS]:
		kw['code']='\n'.join(['#include <%s>'%x for x in self.env[INCKEYS]])+'\n'+kw['code']
	if not kw.get('success'):kw['success']=None
	if'define_name'in kw:
		self.undefine(kw['define_name'])
	if not'msg'in kw:
		self.fatal('missing "msg" in conf.check(...)')
@conf
def post_check(self,*k,**kw):
	is_success=0
	if kw['execute']:
		if kw['success']is not None:
			if kw.get('define_ret',False):
				is_success=kw['success']
			else:
				is_success=(kw['success']==0)
	else:
		is_success=(kw['success']==0)
	if'define_name'in kw:
		if'header_name'in kw or'function_name'in kw or'type_name'in kw or'fragment'in kw:
			if kw['execute']and kw.get('define_ret',None)and isinstance(is_success,str):
				self.define(kw['define_name'],is_success,quote=kw.get('quote',1))
			else:
				self.define_cond(kw['define_name'],is_success)
		else:
			self.define_cond(kw['define_name'],is_success)
	if'header_name'in kw:
		if kw.get('auto_add_header_name',False):
			self.env.append_value(INCKEYS,Utils.to_list(kw['header_name']))
	if is_success and'uselib_store'in kw:
		from waflib.Tools import ccroot
		_vars=set([])
		for x in kw['features']:
			if x in ccroot.USELIB_VARS:
				_vars|=ccroot.USELIB_VARS[x]
		for k in _vars:
			lk=k.lower()
			if lk in kw:
				val=kw[lk]
				if isinstance(val,str):
					val=val.rstrip(os.path.sep)
				self.env.append_unique(k+'_'+kw['uselib_store'],Utils.to_list(val))
	return is_success
@conf
def check(self,*k,**kw):
	self.validate_c(kw)
	self.start_msg(kw['msg'])
	ret=None
	try:
		ret=self.run_c_code(*k,**kw)
	except self.errors.ConfigurationError:
		self.end_msg(kw['errmsg'],'YELLOW')
		if Logs.verbose>1:
			raise
		else:
			self.fatal('The configuration failed')
	else:
		kw['success']=ret
	ret=self.post_check(*k,**kw)
	if not ret:
		self.end_msg(kw['errmsg'],'YELLOW')
		self.fatal('The configuration failed %r'%ret)
	else:
		self.end_msg(self.ret_msg(kw['okmsg'],kw))
	return ret
class test_exec(Task.Task):
	color='PINK'
	def run(self):
		if getattr(self.generator,'rpath',None):
			if getattr(self.generator,'define_ret',False):
				self.generator.bld.retval=self.generator.bld.cmd_and_log([self.inputs[0].abspath()])
			else:
				self.generator.bld.retval=self.generator.bld.exec_command([self.inputs[0].abspath()])
		else:
			env=self.env.env or{}
			env.update(dict(os.environ))
			for var in('LD_LIBRARY_PATH','DYLD_LIBRARY_PATH','PATH'):
				env[var]=self.inputs[0].parent.abspath()+os.path.pathsep+env.get(var,'')
			if getattr(self.generator,'define_ret',False):
				self.generator.bld.retval=self.generator.bld.cmd_and_log([self.inputs[0].abspath()],env=env)
			else:
				self.generator.bld.retval=self.generator.bld.exec_command([self.inputs[0].abspath()],env=env)
@feature('test_exec')
@after_method('apply_link')
def test_exec_fun(self):
	self.create_task('test_exec',self.link_task.outputs[0])
CACHE_RESULTS=1
COMPILE_ERRORS=2
@conf
def run_c_code(self,*k,**kw):
	lst=[str(v)for(p,v)in kw.items()if p!='env']
	h=Utils.h_list(lst)
	dir=self.bldnode.abspath()+os.sep+(not Utils.is_win32 and'.'or'')+'conf_check_'+Utils.to_hex(h)
	try:
		os.makedirs(dir)
	except OSError:
		pass
	try:
		os.stat(dir)
	except OSError:
		self.fatal('cannot use the configuration test folder %r'%dir)
	cachemode=getattr(Options.options,'confcache',None)
	if cachemode==CACHE_RESULTS:
		try:
			proj=ConfigSet.ConfigSet(os.path.join(dir,'cache_run_c_code'))
		except OSError:
			pass
		else:
			ret=proj['cache_run_c_code']
			if isinstance(ret,str)and ret.startswith('Test does not build'):
				self.fatal(ret)
			return ret
	bdir=os.path.join(dir,'testbuild')
	if not os.path.exists(bdir):
		os.makedirs(bdir)
	self.test_bld=bld=Build.BuildContext(top_dir=dir,out_dir=bdir)
	bld.init_dirs()
	bld.progress_bar=0
	bld.targets='*'
	if kw['compile_filename']:
		node=bld.srcnode.make_node(kw['compile_filename'])
		node.write(kw['code'])
	bld.logger=self.logger
	bld.all_envs.update(self.all_envs)
	bld.env=kw['env']
	o=bld(features=kw['features'],source=kw['compile_filename'],target='testprog')
	for k,v in kw.items():
		setattr(o,k,v)
	self.to_log("==>\n%s\n<=="%kw['code'])
	bld.targets='*'
	ret=-1
	try:
		try:
			bld.compile()
		except Errors.WafError:
			ret='Test does not build: %s'%Utils.ex_stack()
			self.fatal(ret)
		else:
			ret=getattr(bld,'retval',0)
	finally:
		proj=ConfigSet.ConfigSet()
		proj['cache_run_c_code']=ret
		proj.store(os.path.join(dir,'cache_run_c_code'))
	return ret
@conf
def check_cxx(self,*k,**kw):
	kw['compiler']='cxx'
	return self.check(*k,**kw)
@conf
def check_cc(self,*k,**kw):
	kw['compiler']='c'
	return self.check(*k,**kw)
@conf
def define(self,key,val,quote=True):
	assert key and isinstance(key,str)
	if val is True:
		val=1
	elif val in(False,None):
		val=0
	if isinstance(val,int)or isinstance(val,float):
		s='%s=%s'
	else:
		s=quote and'%s="%s"'or'%s=%s'
	app=s%(key,str(val))
	ban=key+'='
	lst=self.env['DEFINES']
	for x in lst:
		if x.startswith(ban):
			lst[lst.index(x)]=app
			break
	else:
		self.env.append_value('DEFINES',app)
	self.env.append_unique(DEFKEYS,key)
@conf
def undefine(self,key):
	assert key and isinstance(key,str)
	ban=key+'='
	lst=[x for x in self.env['DEFINES']if not x.startswith(ban)]
	self.env['DEFINES']=lst
	self.env.append_unique(DEFKEYS,key)
@conf
def define_cond(self,key,val):
	assert key and isinstance(key,str)
	if val:
		self.define(key,1)
	else:
		self.undefine(key)
@conf
def is_defined(self,key):
	assert key and isinstance(key,str)
	ban=key+'='
	for x in self.env['DEFINES']:
		if x.startswith(ban):
			return True
	return False
@conf
def get_define(self,key):
	assert key and isinstance(key,str)
	ban=key+'='
	for x in self.env['DEFINES']:
		if x.startswith(ban):
			return x[len(ban):]
	return None
@conf
def have_define(self,key):
	return(self.env.HAVE_PAT or'HAVE_%s')%Utils.quote_define_name(key)
@conf
def write_config_header(self,configfile='',guard='',top=False,env=None,defines=True,headers=False,remove=True,define_prefix=''):
	if env:
		Logs.warn('Cannot pass env to write_config_header')
	if not configfile:configfile=WAF_CONFIG_H
	waf_guard=guard or'W_%s_WAF'%Utils.quote_define_name(configfile)
	node=top and self.bldnode or self.path.get_bld()
	node=node.make_node(configfile)
	node.parent.mkdir()
	lst=['/* WARNING! All changes made to this file will be lost! */\n']
	lst.append('#ifndef %s\n#define %s\n'%(waf_guard,waf_guard))
	lst.append(self.get_config_header(defines,headers,define_prefix=define_prefix))
	lst.append('\n#endif /* %s */\n'%waf_guard)
	node.write('\n'.join(lst))
	self.env.append_unique(Build.CFG_FILES,[node.abspath()])
	if remove:
		for key in self.env[DEFKEYS]:
			self.undefine(key)
		self.env[DEFKEYS]=[]
@conf
def get_config_header(self,defines=True,headers=False,define_prefix=''):
	lst=[]
	if headers:
		for x in self.env[INCKEYS]:
			lst.append('#include <%s>'%x)
	if defines:
		for x in self.env[DEFKEYS]:
			if self.is_defined(x):
				val=self.get_define(x)
				lst.append('#define %s %s'%(define_prefix+x,val))
			else:
				lst.append('/* #undef %s */'%(define_prefix+x))
	return"\n".join(lst)
@conf
def cc_add_flags(conf):
	conf.add_os_flags('CPPFLAGS','CFLAGS')
	conf.add_os_flags('CFLAGS')
@conf
def cxx_add_flags(conf):
	conf.add_os_flags('CPPFLAGS','CXXFLAGS')
	conf.add_os_flags('CXXFLAGS')
@conf
def link_add_flags(conf):
	conf.add_os_flags('LINKFLAGS')
	conf.add_os_flags('LDFLAGS','LINKFLAGS')
@conf
def cc_load_tools(conf):
	if not conf.env.DEST_OS:
		conf.env.DEST_OS=Utils.unversioned_sys_platform()
	conf.load('c')
@conf
def cxx_load_tools(conf):
	if not conf.env.DEST_OS:
		conf.env.DEST_OS=Utils.unversioned_sys_platform()
	conf.load('cxx')
@conf
def get_cc_version(conf,cc,gcc=False,icc=False):
	cmd=cc+['-dM','-E','-']
	env=conf.env.env or None
	try:
		p=Utils.subprocess.Popen(cmd,stdin=Utils.subprocess.PIPE,stdout=Utils.subprocess.PIPE,stderr=Utils.subprocess.PIPE,env=env)
		p.stdin.write('\n')
		out=p.communicate()[0]
	except Exception:
		conf.fatal('Could not determine the compiler version %r'%cmd)
	if not isinstance(out,str):
		out=out.decode(sys.stdout.encoding or'iso8859-1')
	if gcc:
		if out.find('__INTEL_COMPILER')>=0:
			conf.fatal('The intel compiler pretends to be gcc')
		if out.find('__GNUC__')<0 and out.find('__clang__')<0:
			conf.fatal('Could not determine the compiler type')
	if icc and out.find('__INTEL_COMPILER')<0:
		conf.fatal('Not icc/icpc')
	k={}
	if icc or gcc:
		out=out.splitlines()
		for line in out:
			lst=shlex.split(line)
			if len(lst)>2:
				key=lst[1]
				val=lst[2]
				k[key]=val
		def isD(var):
			return var in k
		def isT(var):
			return var in k and k[var]!='0'
		if not conf.env.DEST_OS:
			conf.env.DEST_OS=''
		for i in MACRO_TO_DESTOS:
			if isD(i):
				conf.env.DEST_OS=MACRO_TO_DESTOS[i]
				break
		else:
			if isD('__APPLE__')and isD('__MACH__'):
				conf.env.DEST_OS='darwin'
			elif isD('__unix__'):
				conf.env.DEST_OS='generic'
		if isD('__ELF__'):
			conf.env.DEST_BINFMT='elf'
		elif isD('__WINNT__')or isD('__CYGWIN__')or isD('_WIN32'):
			conf.env.DEST_BINFMT='pe'
			conf.env.LIBDIR=conf.env.BINDIR
		elif isD('__APPLE__'):
			conf.env.DEST_BINFMT='mac-o'
		if not conf.env.DEST_BINFMT:
			conf.env.DEST_BINFMT=Utils.destos_to_binfmt(conf.env.DEST_OS)
		for i in MACRO_TO_DEST_CPU:
			if isD(i):
				conf.env.DEST_CPU=MACRO_TO_DEST_CPU[i]
				break
		Logs.debug('ccroot: dest platform: '+' '.join([conf.env[x]or'?'for x in('DEST_OS','DEST_BINFMT','DEST_CPU')]))
		if icc:
			ver=k['__INTEL_COMPILER']
			conf.env['CC_VERSION']=(ver[:-2],ver[-2],ver[-1])
		else:
			if isD('__clang__'):
				conf.env['CC_VERSION']=(k['__clang_major__'],k['__clang_minor__'],k['__clang_patchlevel__'])
			else:
				conf.env['CC_VERSION']=(k['__GNUC__'],k['__GNUC_MINOR__'],k['__GNUC_PATCHLEVEL__'])
	return k
@conf
def get_xlc_version(conf,cc):
	cmd=cc+['-qversion']
	try:
		out,err=conf.cmd_and_log(cmd,output=0)
	except Errors.WafError:
		conf.fatal('Could not find xlc %r'%cmd)
	for v in(r"IBM XL C/C\+\+.* V(?P<major>\d*)\.(?P<minor>\d*)",):
		version_re=re.compile(v,re.I).search
		match=version_re(out or err)
		if match:
			k=match.groupdict()
			conf.env['CC_VERSION']=(k['major'],k['minor'])
			break
	else:
		conf.fatal('Could not determine the XLC version.')
@conf
def get_suncc_version(conf,cc):
	cmd=cc+['-V']
	try:
		out,err=conf.cmd_and_log(cmd,output=0)
	except Errors.WafError ,e:
		if not(hasattr(e,'returncode')and hasattr(e,'stdout')and hasattr(e,'stderr')):
			conf.fatal('Could not find suncc %r'%cmd)
		out=e.stdout
		err=e.stderr
	version=(out or err)
	version=version.split('\n')[0]
	version_re=re.compile(r'cc:\s+sun\s+(c\+\+|c)\s+(?P<major>\d*)\.(?P<minor>\d*)',re.I).search
	match=version_re(version)
	if match:
		k=match.groupdict()
		conf.env['CC_VERSION']=(k['major'],k['minor'])
	else:
		conf.fatal('Could not determine the suncc version.')
@conf
def add_as_needed(self):
	if self.env.DEST_BINFMT=='elf'and'gcc'in(self.env.CXX_NAME,self.env.CC_NAME):
		self.env.append_unique('LINKFLAGS','--as-needed')
class cfgtask(Task.TaskBase):
	def display(self):
		return''
	def runnable_status(self):
		return Task.RUN_ME
	def uid(self):
		return Utils.SIG_NIL
	def run(self):
		conf=self.conf
		bld=Build.BuildContext(top_dir=conf.srcnode.abspath(),out_dir=conf.bldnode.abspath())
		bld.env=conf.env
		bld.init_dirs()
		bld.in_msg=1
		bld.logger=self.logger
		try:
			bld.check(**self.args)
		except Exception:
			return 1
@conf
def multicheck(self,*k,**kw):
	self.start_msg(kw.get('msg','Executing %d configuration tests'%len(k)))
	class par(object):
		def __init__(self):
			self.keep=False
			self.cache_global=Options.cache_global
			self.nocache=Options.options.nocache
			self.returned_tasks=[]
			self.task_sigs={}
		def total(self):
			return len(tasks)
		def to_log(self,*k,**kw):
			return
	bld=par()
	tasks=[]
	for dct in k:
		x=cfgtask(bld=bld)
		tasks.append(x)
		x.args=dct
		x.bld=bld
		x.conf=self
		x.args=dct
		x.logger=Logs.make_mem_logger(str(id(x)),self.logger)
	def it():
		yield tasks
		while 1:
			yield[]
	p=Runner.Parallel(bld,Options.options.jobs)
	p.biter=it()
	p.start()
	for x in tasks:
		x.logger.memhandler.flush()
	for x in tasks:
		if x.hasrun!=Task.SUCCESS:
			self.end_msg(kw.get('errmsg','no'),color='YELLOW')
			self.fatal(kw.get('fatalmsg',None)or'One of the tests has failed, see the config.log for more information')
	self.end_msg('ok')

########NEW FILE########
__FILENAME__ = c_osx
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import os,shutil,sys,platform
from waflib import TaskGen,Task,Build,Options,Utils,Errors
from waflib.TaskGen import taskgen_method,feature,after_method,before_method
app_info='''
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist SYSTEM "file://localhost/System/Library/DTDs/PropertyList.dtd">
<plist version="0.9">
<dict>
	<key>CFBundlePackageType</key>
	<string>APPL</string>
	<key>CFBundleGetInfoString</key>
	<string>Created by Waf</string>
	<key>CFBundleSignature</key>
	<string>????</string>
	<key>NOTE</key>
	<string>THIS IS A GENERATED FILE, DO NOT MODIFY</string>
	<key>CFBundleExecutable</key>
	<string>%s</string>
</dict>
</plist>
'''
@feature('c','cxx')
def set_macosx_deployment_target(self):
	if self.env['MACOSX_DEPLOYMENT_TARGET']:
		os.environ['MACOSX_DEPLOYMENT_TARGET']=self.env['MACOSX_DEPLOYMENT_TARGET']
	elif'MACOSX_DEPLOYMENT_TARGET'not in os.environ:
		if Utils.unversioned_sys_platform()=='darwin':
			os.environ['MACOSX_DEPLOYMENT_TARGET']='.'.join(platform.mac_ver()[0].split('.')[:2])
@taskgen_method
def create_bundle_dirs(self,name,out):
	bld=self.bld
	dir=out.parent.find_or_declare(name)
	dir.mkdir()
	macos=dir.find_or_declare(['Contents','MacOS'])
	macos.mkdir()
	return dir
def bundle_name_for_output(out):
	name=out.name
	k=name.rfind('.')
	if k>=0:
		name=name[:k]+'.app'
	else:
		name=name+'.app'
	return name
@feature('cprogram','cxxprogram')
@after_method('apply_link')
def create_task_macapp(self):
	if self.env['MACAPP']or getattr(self,'mac_app',False):
		out=self.link_task.outputs[0]
		name=bundle_name_for_output(out)
		dir=self.create_bundle_dirs(name,out)
		n1=dir.find_or_declare(['Contents','MacOS',out.name])
		self.apptask=self.create_task('macapp',self.link_task.outputs,n1)
		inst_to=getattr(self,'install_path','/Applications')+'/%s/Contents/MacOS/'%name
		self.bld.install_files(inst_to,n1,chmod=Utils.O755)
		if getattr(self,'mac_resources',None):
			res_dir=n1.parent.parent.make_node('Resources')
			inst_to=getattr(self,'install_path','/Applications')+'/%s/Resources'%name
			for x in self.to_list(self.mac_resources):
				node=self.path.find_node(x)
				if not node:
					raise Errors.WafError('Missing mac_resource %r in %r'%(x,self))
				parent=node.parent
				if os.path.isdir(node.abspath()):
					nodes=node.ant_glob('**')
				else:
					nodes=[node]
				for node in nodes:
					rel=node.path_from(parent)
					tsk=self.create_task('macapp',node,res_dir.make_node(rel))
					self.bld.install_as(inst_to+'/%s'%rel,node)
		if getattr(self.bld,'is_install',None):
			self.install_task.hasrun=Task.SKIP_ME
@feature('cprogram','cxxprogram')
@after_method('apply_link')
def create_task_macplist(self):
	if self.env['MACAPP']or getattr(self,'mac_app',False):
		out=self.link_task.outputs[0]
		name=bundle_name_for_output(out)
		dir=self.create_bundle_dirs(name,out)
		n1=dir.find_or_declare(['Contents','Info.plist'])
		self.plisttask=plisttask=self.create_task('macplist',[],n1)
		if getattr(self,'mac_plist',False):
			node=self.path.find_resource(self.mac_plist)
			if node:
				plisttask.inputs.append(node)
			else:
				plisttask.code=self.mac_plist
		else:
			plisttask.code=app_info%self.link_task.outputs[0].name
		inst_to=getattr(self,'install_path','/Applications')+'/%s/Contents/'%name
		self.bld.install_files(inst_to,n1)
@feature('cshlib','cxxshlib')
@before_method('apply_link','propagate_uselib_vars')
def apply_bundle(self):
	if self.env['MACBUNDLE']or getattr(self,'mac_bundle',False):
		self.env['LINKFLAGS_cshlib']=self.env['LINKFLAGS_cxxshlib']=[]
		self.env['cshlib_PATTERN']=self.env['cxxshlib_PATTERN']=self.env['macbundle_PATTERN']
		use=self.use=self.to_list(getattr(self,'use',[]))
		if not'MACBUNDLE'in use:
			use.append('MACBUNDLE')
app_dirs=['Contents','Contents/MacOS','Contents/Resources']
class macapp(Task.Task):
	color='PINK'
	def run(self):
		self.outputs[0].parent.mkdir()
		shutil.copy2(self.inputs[0].srcpath(),self.outputs[0].abspath())
class macplist(Task.Task):
	color='PINK'
	ext_in=['.bin']
	def run(self):
		if getattr(self,'code',None):
			txt=self.code
		else:
			txt=self.inputs[0].read()
		self.outputs[0].write(txt)

########NEW FILE########
__FILENAME__ = c_preproc
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import re,string,traceback
from waflib import Logs,Utils,Errors
from waflib.Logs import debug,error
class PreprocError(Errors.WafError):
	pass
POPFILE='-'
recursion_limit=150
go_absolute=False
standard_includes=['/usr/include']
if Utils.is_win32:
	standard_includes=[]
use_trigraphs=0
strict_quotes=0
g_optrans={'not':'!','and':'&&','bitand':'&','and_eq':'&=','or':'||','bitor':'|','or_eq':'|=','xor':'^','xor_eq':'^=','compl':'~',}
re_lines=re.compile('^[ \t]*(#|%:)[ \t]*(ifdef|ifndef|if|else|elif|endif|include|import|define|undef|pragma)[ \t]*(.*)\r*$',re.IGNORECASE|re.MULTILINE)
re_mac=re.compile("^[a-zA-Z_]\w*")
re_fun=re.compile('^[a-zA-Z_][a-zA-Z0-9_]*[(]')
re_pragma_once=re.compile('^\s*once\s*',re.IGNORECASE)
re_nl=re.compile('\\\\\r*\n',re.MULTILINE)
re_cpp=re.compile(r'//.*?$|/\*.*?\*/|\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"',re.DOTALL|re.MULTILINE)
trig_def=[('??'+a,b)for a,b in zip("=-/!'()<>",r'#~\|^[]{}')]
chr_esc={'0':0,'a':7,'b':8,'t':9,'n':10,'f':11,'v':12,'r':13,'\\':92,"'":39}
NUM='i'
OP='O'
IDENT='T'
STR='s'
CHAR='c'
tok_types=[NUM,STR,IDENT,OP]
exp_types=[r"""0[xX](?P<hex>[a-fA-F0-9]+)(?P<qual1>[uUlL]*)|L*?'(?P<char>(\\.|[^\\'])+)'|(?P<n1>\d+)[Ee](?P<exp0>[+-]*?\d+)(?P<float0>[fFlL]*)|(?P<n2>\d*\.\d+)([Ee](?P<exp1>[+-]*?\d+))?(?P<float1>[fFlL]*)|(?P<n4>\d+\.\d*)([Ee](?P<exp2>[+-]*?\d+))?(?P<float2>[fFlL]*)|(?P<oct>0*)(?P<n0>\d+)(?P<qual2>[uUlL]*)""",r'L?"([^"\\]|\\.)*"',r'[a-zA-Z_]\w*',r'%:%:|<<=|>>=|\.\.\.|<<|<%|<:|<=|>>|>=|\+\+|\+=|--|->|-=|\*=|/=|%:|%=|%>|==|&&|&=|\|\||\|=|\^=|:>|!=|##|[\(\)\{\}\[\]<>\?\|\^\*\+&=:!#;,%/\-\?\~\.]',]
re_clexer=re.compile('|'.join(["(?P<%s>%s)"%(name,part)for name,part in zip(tok_types,exp_types)]),re.M)
accepted='a'
ignored='i'
undefined='u'
skipped='s'
def repl(m):
	s=m.group(0)
	if s.startswith('/'):
		return' '
	return s
def filter_comments(filename):
	code=Utils.readf(filename)
	if use_trigraphs:
		for(a,b)in trig_def:code=code.split(a).join(b)
	code=re_nl.sub('',code)
	code=re_cpp.sub(repl,code)
	return[(m.group(2),m.group(3))for m in re.finditer(re_lines,code)]
prec={}
ops=['* / %','+ -','<< >>','< <= >= >','== !=','& | ^','&& ||',',']
for x in range(len(ops)):
	syms=ops[x]
	for u in syms.split():
		prec[u]=x
def trimquotes(s):
	if not s:return''
	s=s.rstrip()
	if s[0]=="'"and s[-1]=="'":return s[1:-1]
	return s
def reduce_nums(val_1,val_2,val_op):
	try:a=0+val_1
	except TypeError:a=int(val_1)
	try:b=0+val_2
	except TypeError:b=int(val_2)
	d=val_op
	if d=='%':c=a%b
	elif d=='+':c=a+b
	elif d=='-':c=a-b
	elif d=='*':c=a*b
	elif d=='/':c=a/b
	elif d=='^':c=a^b
	elif d=='|':c=a|b
	elif d=='||':c=int(a or b)
	elif d=='&':c=a&b
	elif d=='&&':c=int(a and b)
	elif d=='==':c=int(a==b)
	elif d=='!=':c=int(a!=b)
	elif d=='<=':c=int(a<=b)
	elif d=='<':c=int(a<b)
	elif d=='>':c=int(a>b)
	elif d=='>=':c=int(a>=b)
	elif d=='^':c=int(a^b)
	elif d=='<<':c=a<<b
	elif d=='>>':c=a>>b
	else:c=0
	return c
def get_num(lst):
	if not lst:raise PreprocError("empty list for get_num")
	(p,v)=lst[0]
	if p==OP:
		if v=='(':
			count_par=1
			i=1
			while i<len(lst):
				(p,v)=lst[i]
				if p==OP:
					if v==')':
						count_par-=1
						if count_par==0:
							break
					elif v=='(':
						count_par+=1
				i+=1
			else:
				raise PreprocError("rparen expected %r"%lst)
			(num,_)=get_term(lst[1:i])
			return(num,lst[i+1:])
		elif v=='+':
			return get_num(lst[1:])
		elif v=='-':
			num,lst=get_num(lst[1:])
			return(reduce_nums('-1',num,'*'),lst)
		elif v=='!':
			num,lst=get_num(lst[1:])
			return(int(not int(num)),lst)
		elif v=='~':
			num,lst=get_num(lst[1:])
			return(~int(num),lst)
		else:
			raise PreprocError("Invalid op token %r for get_num"%lst)
	elif p==NUM:
		return v,lst[1:]
	elif p==IDENT:
		return 0,lst[1:]
	else:
		raise PreprocError("Invalid token %r for get_num"%lst)
def get_term(lst):
	if not lst:raise PreprocError("empty list for get_term")
	num,lst=get_num(lst)
	if not lst:
		return(num,[])
	(p,v)=lst[0]
	if p==OP:
		if v==',':
			return get_term(lst[1:])
		elif v=='?':
			count_par=0
			i=1
			while i<len(lst):
				(p,v)=lst[i]
				if p==OP:
					if v==')':
						count_par-=1
					elif v=='(':
						count_par+=1
					elif v==':':
						if count_par==0:
							break
				i+=1
			else:
				raise PreprocError("rparen expected %r"%lst)
			if int(num):
				return get_term(lst[1:i])
			else:
				return get_term(lst[i+1:])
		else:
			num2,lst=get_num(lst[1:])
			if not lst:
				num2=reduce_nums(num,num2,v)
				return get_term([(NUM,num2)]+lst)
			p2,v2=lst[0]
			if p2!=OP:
				raise PreprocError("op expected %r"%lst)
			if prec[v2]>=prec[v]:
				num2=reduce_nums(num,num2,v)
				return get_term([(NUM,num2)]+lst)
			else:
				num3,lst=get_num(lst[1:])
				num3=reduce_nums(num2,num3,v2)
				return get_term([(NUM,num),(p,v),(NUM,num3)]+lst)
	raise PreprocError("cannot reduce %r"%lst)
def reduce_eval(lst):
	num,lst=get_term(lst)
	return(NUM,num)
def stringize(lst):
	lst=[str(v2)for(p2,v2)in lst]
	return"".join(lst)
def paste_tokens(t1,t2):
	p1=None
	if t1[0]==OP and t2[0]==OP:
		p1=OP
	elif t1[0]==IDENT and(t2[0]==IDENT or t2[0]==NUM):
		p1=IDENT
	elif t1[0]==NUM and t2[0]==NUM:
		p1=NUM
	if not p1:
		raise PreprocError('tokens do not make a valid paste %r and %r'%(t1,t2))
	return(p1,t1[1]+t2[1])
def reduce_tokens(lst,defs,ban=[]):
	i=0
	while i<len(lst):
		(p,v)=lst[i]
		if p==IDENT and v=="defined":
			del lst[i]
			if i<len(lst):
				(p2,v2)=lst[i]
				if p2==IDENT:
					if v2 in defs:
						lst[i]=(NUM,1)
					else:
						lst[i]=(NUM,0)
				elif p2==OP and v2=='(':
					del lst[i]
					(p2,v2)=lst[i]
					del lst[i]
					if v2 in defs:
						lst[i]=(NUM,1)
					else:
						lst[i]=(NUM,0)
				else:
					raise PreprocError("Invalid define expression %r"%lst)
		elif p==IDENT and v in defs:
			if isinstance(defs[v],str):
				a,b=extract_macro(defs[v])
				defs[v]=b
			macro_def=defs[v]
			to_add=macro_def[1]
			if isinstance(macro_def[0],list):
				del lst[i]
				accu=to_add[:]
				reduce_tokens(accu,defs,ban+[v])
				for x in range(len(accu)):
					lst.insert(i,accu[x])
					i+=1
			else:
				args=[]
				del lst[i]
				if i>=len(lst):
					raise PreprocError("expected '(' after %r (got nothing)"%v)
				(p2,v2)=lst[i]
				if p2!=OP or v2!='(':
					raise PreprocError("expected '(' after %r"%v)
				del lst[i]
				one_param=[]
				count_paren=0
				while i<len(lst):
					p2,v2=lst[i]
					del lst[i]
					if p2==OP and count_paren==0:
						if v2=='(':
							one_param.append((p2,v2))
							count_paren+=1
						elif v2==')':
							if one_param:args.append(one_param)
							break
						elif v2==',':
							if not one_param:raise PreprocError("empty param in funcall %s"%v)
							args.append(one_param)
							one_param=[]
						else:
							one_param.append((p2,v2))
					else:
						one_param.append((p2,v2))
						if v2=='(':count_paren+=1
						elif v2==')':count_paren-=1
				else:
					raise PreprocError('malformed macro')
				accu=[]
				arg_table=macro_def[0]
				j=0
				while j<len(to_add):
					(p2,v2)=to_add[j]
					if p2==OP and v2=='#':
						if j+1<len(to_add)and to_add[j+1][0]==IDENT and to_add[j+1][1]in arg_table:
							toks=args[arg_table[to_add[j+1][1]]]
							accu.append((STR,stringize(toks)))
							j+=1
						else:
							accu.append((p2,v2))
					elif p2==OP and v2=='##':
						if accu and j+1<len(to_add):
							t1=accu[-1]
							if to_add[j+1][0]==IDENT and to_add[j+1][1]in arg_table:
								toks=args[arg_table[to_add[j+1][1]]]
								if toks:
									accu[-1]=paste_tokens(t1,toks[0])
									accu.extend(toks[1:])
								else:
									accu.append((p2,v2))
									accu.extend(toks)
							elif to_add[j+1][0]==IDENT and to_add[j+1][1]=='__VA_ARGS__':
								va_toks=[]
								st=len(macro_def[0])
								pt=len(args)
								for x in args[pt-st+1:]:
									va_toks.extend(x)
									va_toks.append((OP,','))
								if va_toks:va_toks.pop()
								if len(accu)>1:
									(p3,v3)=accu[-1]
									(p4,v4)=accu[-2]
									if v3=='##':
										accu.pop()
										if v4==','and pt<st:
											accu.pop()
								accu+=va_toks
							else:
								accu[-1]=paste_tokens(t1,to_add[j+1])
							j+=1
						else:
							accu.append((p2,v2))
					elif p2==IDENT and v2 in arg_table:
						toks=args[arg_table[v2]]
						reduce_tokens(toks,defs,ban+[v])
						accu.extend(toks)
					else:
						accu.append((p2,v2))
					j+=1
				reduce_tokens(accu,defs,ban+[v])
				for x in range(len(accu)-1,-1,-1):
					lst.insert(i,accu[x])
		i+=1
def eval_macro(lst,defs):
	reduce_tokens(lst,defs,[])
	if not lst:raise PreprocError("missing tokens to evaluate")
	(p,v)=reduce_eval(lst)
	return int(v)!=0
def extract_macro(txt):
	t=tokenize(txt)
	if re_fun.search(txt):
		p,name=t[0]
		p,v=t[1]
		if p!=OP:raise PreprocError("expected open parenthesis")
		i=1
		pindex=0
		params={}
		prev='('
		while 1:
			i+=1
			p,v=t[i]
			if prev=='(':
				if p==IDENT:
					params[v]=pindex
					pindex+=1
					prev=p
				elif p==OP and v==')':
					break
				else:
					raise PreprocError("unexpected token (3)")
			elif prev==IDENT:
				if p==OP and v==',':
					prev=v
				elif p==OP and v==')':
					break
				else:
					raise PreprocError("comma or ... expected")
			elif prev==',':
				if p==IDENT:
					params[v]=pindex
					pindex+=1
					prev=p
				elif p==OP and v=='...':
					raise PreprocError("not implemented (1)")
				else:
					raise PreprocError("comma or ... expected (2)")
			elif prev=='...':
				raise PreprocError("not implemented (2)")
			else:
				raise PreprocError("unexpected else")
		return(name,[params,t[i+1:]])
	else:
		(p,v)=t[0]
		if len(t)>1:
			return(v,[[],t[1:]])
		else:
			return(v,[[],[('T','')]])
re_include=re.compile('^\s*(<(?P<a>.*)>|"(?P<b>.*)")')
def extract_include(txt,defs):
	m=re_include.search(txt)
	if m:
		if m.group('a'):return'<',m.group('a')
		if m.group('b'):return'"',m.group('b')
	toks=tokenize(txt)
	reduce_tokens(toks,defs,['waf_include'])
	if not toks:
		raise PreprocError("could not parse include %s"%txt)
	if len(toks)==1:
		if toks[0][0]==STR:
			return'"',toks[0][1]
	else:
		if toks[0][1]=='<'and toks[-1][1]=='>':
			return stringize(toks).lstrip('<').rstrip('>')
	raise PreprocError("could not parse include %s."%txt)
def parse_char(txt):
	if not txt:raise PreprocError("attempted to parse a null char")
	if txt[0]!='\\':
		return ord(txt)
	c=txt[1]
	if c=='x':
		if len(txt)==4 and txt[3]in string.hexdigits:return int(txt[2:],16)
		return int(txt[2:],16)
	elif c.isdigit():
		if c=='0'and len(txt)==2:return 0
		for i in 3,2,1:
			if len(txt)>i and txt[1:1+i].isdigit():
				return(1+i,int(txt[1:1+i],8))
	else:
		try:return chr_esc[c]
		except KeyError:raise PreprocError("could not parse char literal '%s'"%txt)
def tokenize(s):
	return tokenize_private(s)[:]
@Utils.run_once
def tokenize_private(s):
	ret=[]
	for match in re_clexer.finditer(s):
		m=match.group
		for name in tok_types:
			v=m(name)
			if v:
				if name==IDENT:
					try:v=g_optrans[v];name=OP
					except KeyError:
						if v.lower()=="true":
							v=1
							name=NUM
						elif v.lower()=="false":
							v=0
							name=NUM
				elif name==NUM:
					if m('oct'):v=int(v,8)
					elif m('hex'):v=int(m('hex'),16)
					elif m('n0'):v=m('n0')
					else:
						v=m('char')
						if v:v=parse_char(v)
						else:v=m('n2')or m('n4')
				elif name==OP:
					if v=='%:':v='#'
					elif v=='%:%:':v='##'
				elif name==STR:
					v=v[1:-1]
				ret.append((name,v))
				break
	return ret
@Utils.run_once
def define_name(line):
	return re_mac.match(line).group(0)
class c_parser(object):
	def __init__(self,nodepaths=None,defines=None):
		self.lines=[]
		if defines is None:
			self.defs={}
		else:
			self.defs=dict(defines)
		self.state=[]
		self.count_files=0
		self.currentnode_stack=[]
		self.nodepaths=nodepaths or[]
		self.nodes=[]
		self.names=[]
		self.curfile=''
		self.ban_includes=set([])
	def cached_find_resource(self,node,filename):
		try:
			nd=node.ctx.cache_nd
		except AttributeError:
			nd=node.ctx.cache_nd={}
		tup=(node,filename)
		try:
			return nd[tup]
		except KeyError:
			ret=node.find_resource(filename)
			if ret:
				if getattr(ret,'children',None):
					ret=None
				elif ret.is_child_of(node.ctx.bldnode):
					tmp=node.ctx.srcnode.search_node(ret.path_from(node.ctx.bldnode))
					if tmp and getattr(tmp,'children',None):
						ret=None
			nd[tup]=ret
			return ret
	def tryfind(self,filename):
		self.curfile=filename
		found=self.cached_find_resource(self.currentnode_stack[-1],filename)
		for n in self.nodepaths:
			if found:
				break
			found=self.cached_find_resource(n,filename)
		if found and not found in self.ban_includes:
			self.nodes.append(found)
			if filename[-4:]!='.moc':
				self.addlines(found)
		else:
			if not filename in self.names:
				self.names.append(filename)
		return found
	def addlines(self,node):
		self.currentnode_stack.append(node.parent)
		filepath=node.abspath()
		self.count_files+=1
		if self.count_files>recursion_limit:
			raise PreprocError("recursion limit exceeded")
		pc=self.parse_cache
		debug('preproc: reading file %r',filepath)
		try:
			lns=pc[filepath]
		except KeyError:
			pass
		else:
			self.lines.extend(lns)
			return
		try:
			lines=filter_comments(filepath)
			lines.append((POPFILE,''))
			lines.reverse()
			pc[filepath]=lines
			self.lines.extend(lines)
		except IOError:
			raise PreprocError("could not read the file %s"%filepath)
		except Exception:
			if Logs.verbose>0:
				error("parsing %s failed"%filepath)
				traceback.print_exc()
	def start(self,node,env):
		debug('preproc: scanning %s (in %s)',node.name,node.parent.name)
		bld=node.ctx
		try:
			self.parse_cache=bld.parse_cache
		except AttributeError:
			bld.parse_cache={}
			self.parse_cache=bld.parse_cache
		self.current_file=node
		self.addlines(node)
		if env['DEFINES']:
			try:
				lst=['%s %s'%(x[0],trimquotes('='.join(x[1:])))for x in[y.split('=')for y in env['DEFINES']]]
				lst.reverse()
				self.lines.extend([('define',x)for x in lst])
			except AttributeError:
				pass
		while self.lines:
			(token,line)=self.lines.pop()
			if token==POPFILE:
				self.count_files-=1
				self.currentnode_stack.pop()
				continue
			try:
				ve=Logs.verbose
				if ve:debug('preproc: line is %s - %s state is %s',token,line,self.state)
				state=self.state
				if token[:2]=='if':
					state.append(undefined)
				elif token=='endif':
					state.pop()
				if token[0]!='e':
					if skipped in self.state or ignored in self.state:
						continue
				if token=='if':
					ret=eval_macro(tokenize(line),self.defs)
					if ret:state[-1]=accepted
					else:state[-1]=ignored
				elif token=='ifdef':
					m=re_mac.match(line)
					if m and m.group(0)in self.defs:state[-1]=accepted
					else:state[-1]=ignored
				elif token=='ifndef':
					m=re_mac.match(line)
					if m and m.group(0)in self.defs:state[-1]=ignored
					else:state[-1]=accepted
				elif token=='include'or token=='import':
					(kind,inc)=extract_include(line,self.defs)
					if ve:debug('preproc: include found %s    (%s) ',inc,kind)
					if kind=='"'or not strict_quotes:
						self.current_file=self.tryfind(inc)
						if token=='import':
							self.ban_includes.add(self.current_file)
				elif token=='elif':
					if state[-1]==accepted:
						state[-1]=skipped
					elif state[-1]==ignored:
						if eval_macro(tokenize(line),self.defs):
							state[-1]=accepted
				elif token=='else':
					if state[-1]==accepted:state[-1]=skipped
					elif state[-1]==ignored:state[-1]=accepted
				elif token=='define':
					try:
						self.defs[define_name(line)]=line
					except Exception:
						raise PreprocError("Invalid define line %s"%line)
				elif token=='undef':
					m=re_mac.match(line)
					if m and m.group(0)in self.defs:
						self.defs.__delitem__(m.group(0))
				elif token=='pragma':
					if re_pragma_once.match(line.lower()):
						self.ban_includes.add(self.current_file)
			except Exception ,e:
				if Logs.verbose:
					debug('preproc: line parsing failed (%s): %s %s',e,line,Utils.ex_stack())
def scan(task):
	global go_absolute
	try:
		incn=task.generator.includes_nodes
	except AttributeError:
		raise Errors.WafError('%r is missing a feature such as "c", "cxx" or "includes": '%task.generator)
	if go_absolute:
		nodepaths=incn+[task.generator.bld.root.find_dir(x)for x in standard_includes]
	else:
		nodepaths=[x for x in incn if x.is_child_of(x.ctx.srcnode)or x.is_child_of(x.ctx.bldnode)]
	tmp=c_parser(nodepaths)
	tmp.start(task.inputs[0],task.env)
	if Logs.verbose:
		debug('deps: deps for %r: %r; unresolved %r'%(task.inputs,tmp.nodes,tmp.names))
	return(tmp.nodes,tmp.names)

########NEW FILE########
__FILENAME__ = c_tests
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

from waflib import Task
from waflib.Configure import conf
from waflib.TaskGen import feature,before_method,after_method
import sys
LIB_CODE='''
#ifdef _MSC_VER
#define testEXPORT __declspec(dllexport)
#else
#define testEXPORT
#endif
testEXPORT int lib_func(void) { return 9; }
'''
MAIN_CODE='''
#ifdef _MSC_VER
#define testEXPORT __declspec(dllimport)
#else
#define testEXPORT
#endif
testEXPORT int lib_func(void);
int main(int argc, char **argv) {
	(void)argc; (void)argv;
	return !(lib_func() == 9);
}
'''
@feature('link_lib_test')
@before_method('process_source')
def link_lib_test_fun(self):
	def write_test_file(task):
		task.outputs[0].write(task.generator.code)
	rpath=[]
	if getattr(self,'add_rpath',False):
		rpath=[self.bld.path.get_bld().abspath()]
	mode=self.mode
	m='%s %s'%(mode,mode)
	ex=self.test_exec and'test_exec'or''
	bld=self.bld
	bld(rule=write_test_file,target='test.'+mode,code=LIB_CODE)
	bld(rule=write_test_file,target='main.'+mode,code=MAIN_CODE)
	bld(features='%sshlib'%m,source='test.'+mode,target='test')
	bld(features='%sprogram %s'%(m,ex),source='main.'+mode,target='app',use='test',rpath=rpath)
@conf
def check_library(self,mode=None,test_exec=True):
	if not mode:
		mode='c'
		if self.env.CXX:
			mode='cxx'
	self.check(compile_filename=[],features='link_lib_test',msg='Checking for libraries',mode=mode,test_exec=test_exec,)
INLINE_CODE='''
typedef int foo_t;
static %s foo_t static_foo () {return 0; }
%s foo_t foo () {
	return 0;
}
'''
INLINE_VALUES=['inline','__inline__','__inline']
@conf
def check_inline(self,**kw):
	self.start_msg('Checking for inline')
	if not'define_name'in kw:
		kw['define_name']='INLINE_MACRO'
	if not'features'in kw:
		if self.env.CXX:
			kw['features']=['cxx']
		else:
			kw['features']=['c']
	for x in INLINE_VALUES:
		kw['fragment']=INLINE_CODE%(x,x)
		try:
			self.check(**kw)
		except self.errors.ConfigurationError:
			continue
		else:
			self.end_msg(x)
			if x!='inline':
				self.define('inline',x,quote=False)
			return x
	self.fatal('could not use inline functions')
LARGE_FRAGMENT='''#include <unistd.h>
int main(int argc, char **argv) {
	(void)argc; (void)argv;
	return !(sizeof(off_t) >= 8);
}
'''
@conf
def check_large_file(self,**kw):
	if not'define_name'in kw:
		kw['define_name']='HAVE_LARGEFILE'
	if not'execute'in kw:
		kw['execute']=True
	if not'features'in kw:
		if self.env.CXX:
			kw['features']=['cxx','cxxprogram']
		else:
			kw['features']=['c','cprogram']
	kw['fragment']=LARGE_FRAGMENT
	kw['msg']='Checking for large file support'
	ret=True
	try:
		if self.env.DEST_BINFMT!='pe':
			ret=self.check(**kw)
	except self.errors.ConfigurationError:
		pass
	else:
		if ret:
			return True
	kw['msg']='Checking for -D_FILE_OFFSET_BITS=64'
	kw['defines']=['_FILE_OFFSET_BITS=64']
	try:
		ret=self.check(**kw)
	except self.errors.ConfigurationError:
		pass
	else:
		self.define('_FILE_OFFSET_BITS',64)
		return ret
	self.fatal('There is no support for large files')
ENDIAN_FRAGMENT='''
short int ascii_mm[] = { 0x4249, 0x4765, 0x6E44, 0x6961, 0x6E53, 0x7953, 0 };
short int ascii_ii[] = { 0x694C, 0x5454, 0x656C, 0x6E45, 0x6944, 0x6E61, 0 };
int use_ascii (int i) {
	return ascii_mm[i] + ascii_ii[i];
}
short int ebcdic_ii[] = { 0x89D3, 0xE3E3, 0x8593, 0x95C5, 0x89C4, 0x9581, 0 };
short int ebcdic_mm[] = { 0xC2C9, 0xC785, 0x95C4, 0x8981, 0x95E2, 0xA8E2, 0 };
int use_ebcdic (int i) {
	return ebcdic_mm[i] + ebcdic_ii[i];
}
extern int foo;
'''
class grep_for_endianness(Task.Task):
	color='PINK'
	def run(self):
		txt=self.inputs[0].read(flags='rb').decode('iso8859-1')
		if txt.find('LiTTleEnDian')>-1:
			self.generator.tmp.append('little')
		elif txt.find('BIGenDianSyS')>-1:
			self.generator.tmp.append('big')
		else:
			return-1
@feature('grep_for_endianness')
@after_method('process_source')
def grep_for_endianness_fun(self):
	self.create_task('grep_for_endianness',self.compiled_tasks[0].outputs[0])
@conf
def check_endianness(self):
	tmp=[]
	def check_msg(self):
		return tmp[0]
	self.check(fragment=ENDIAN_FRAGMENT,features='c grep_for_endianness',msg="Checking for endianness",define='ENDIANNESS',tmp=tmp,okmsg=check_msg)
	return tmp[0]

########NEW FILE########
__FILENAME__ = d
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

from waflib import Utils,Task,Errors
from waflib.TaskGen import taskgen_method,feature,extension
from waflib.Tools import d_scan,d_config
from waflib.Tools.ccroot import link_task,stlink_task
class d(Task.Task):
	color='GREEN'
	run_str='${D} ${DFLAGS} ${DINC_ST:INCPATHS} ${D_SRC_F:SRC} ${D_TGT_F:TGT}'
	scan=d_scan.scan
class d_with_header(d):
	run_str='${D} ${DFLAGS} ${DINC_ST:INCPATHS} ${D_HDR_F:tgt.outputs[1].bldpath()} ${D_SRC_F:SRC} ${D_TGT_F:tgt.outputs[0].bldpath()}'
class d_header(Task.Task):
	color='BLUE'
	run_str='${D} ${D_HEADER} ${SRC}'
class dprogram(link_task):
	run_str='${D_LINKER} ${LINKFLAGS} ${DLNK_SRC_F}${SRC} ${DLNK_TGT_F:TGT} ${RPATH_ST:RPATH} ${DSTLIB_MARKER} ${DSTLIBPATH_ST:STLIBPATH} ${DSTLIB_ST:STLIB} ${DSHLIB_MARKER} ${DLIBPATH_ST:LIBPATH} ${DSHLIB_ST:LIB}'
	inst_to='${BINDIR}'
class dshlib(dprogram):
	inst_to='${LIBDIR}'
class dstlib(stlink_task):
	pass
@extension('.d','.di','.D')
def d_hook(self,node):
	ext=Utils.destos_to_binfmt(self.env.DEST_OS)=='pe'and'obj'or'o'
	out='%s.%d.%s'%(node.name,self.idx,ext)
	def create_compiled_task(self,name,node):
		task=self.create_task(name,node,node.parent.find_or_declare(out))
		try:
			self.compiled_tasks.append(task)
		except AttributeError:
			self.compiled_tasks=[task]
		return task
	if getattr(self,'generate_headers',None):
		tsk=create_compiled_task(self,'d_with_header',node)
		tsk.outputs.append(node.change_ext(self.env['DHEADER_ext']))
	else:
		tsk=create_compiled_task(self,'d',node)
	return tsk
@taskgen_method
def generate_header(self,filename):
	try:
		self.header_lst.append([filename,self.install_path])
	except AttributeError:
		self.header_lst=[[filename,self.install_path]]
@feature('d')
def process_header(self):
	for i in getattr(self,'header_lst',[]):
		node=self.path.find_resource(i[0])
		if not node:
			raise Errors.WafError('file %r not found on d obj'%i[0])
		self.create_task('d_header',node,node.change_ext('.di'))

########NEW FILE########
__FILENAME__ = dbus
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

from waflib import Task,Errors
from waflib.TaskGen import taskgen_method,before_method
@taskgen_method
def add_dbus_file(self,filename,prefix,mode):
	if not hasattr(self,'dbus_lst'):
		self.dbus_lst=[]
	if not'process_dbus'in self.meths:
		self.meths.append('process_dbus')
	self.dbus_lst.append([filename,prefix,mode])
@before_method('apply_core')
def process_dbus(self):
	for filename,prefix,mode in getattr(self,'dbus_lst',[]):
		node=self.path.find_resource(filename)
		if not node:
			raise Errors.WafError('file not found '+filename)
		tsk=self.create_task('dbus_binding_tool',node,node.change_ext('.h'))
		tsk.env.DBUS_BINDING_TOOL_PREFIX=prefix
		tsk.env.DBUS_BINDING_TOOL_MODE=mode
class dbus_binding_tool(Task.Task):
	color='BLUE'
	ext_out=['.h']
	run_str='${DBUS_BINDING_TOOL} --prefix=${DBUS_BINDING_TOOL_PREFIX} --mode=${DBUS_BINDING_TOOL_MODE} --output=${TGT} ${SRC}'
	shell=True
def configure(conf):
	dbus_binding_tool=conf.find_program('dbus-binding-tool',var='DBUS_BINDING_TOOL')

########NEW FILE########
__FILENAME__ = dmd
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import sys
from waflib.Tools import ar,d
from waflib.Configure import conf
@conf
def find_dmd(conf):
	conf.find_program(['dmd','dmd2','ldc'],var='D')
	out=conf.cmd_and_log([conf.env.D,'--help'])
	if out.find("D Compiler v")==-1:
		out=conf.cmd_and_log([conf.env.D,'-version'])
		if out.find("based on DMD v1.")==-1:
			conf.fatal("detected compiler is not dmd/ldc")
@conf
def common_flags_ldc(conf):
	v=conf.env
	v['DFLAGS']=['-d-version=Posix']
	v['LINKFLAGS']=[]
	v['DFLAGS_dshlib']=['-relocation-model=pic']
@conf
def common_flags_dmd(conf):
	v=conf.env
	v['D_SRC_F']=['-c']
	v['D_TGT_F']='-of%s'
	v['D_LINKER']=v['D']
	v['DLNK_SRC_F']=''
	v['DLNK_TGT_F']='-of%s'
	v['DINC_ST']='-I%s'
	v['DSHLIB_MARKER']=v['DSTLIB_MARKER']=''
	v['DSTLIB_ST']=v['DSHLIB_ST']='-L-l%s'
	v['DSTLIBPATH_ST']=v['DLIBPATH_ST']='-L-L%s'
	v['LINKFLAGS_dprogram']=['-quiet']
	v['DFLAGS_dshlib']=['-fPIC']
	v['LINKFLAGS_dshlib']=['-L-shared']
	v['DHEADER_ext']='.di'
	v.DFLAGS_d_with_header=['-H','-Hf']
	v['D_HDR_F']='%s'
def configure(conf):
	conf.find_dmd()
	if sys.platform=='win32':
		out=conf.cmd_and_log([conf.env.D,'--help'])
		if out.find("D Compiler v2.")>-1:
			conf.fatal('dmd2 on Windows is not supported, use gdc or ldc2 instead')
	conf.load('ar')
	conf.load('d')
	conf.common_flags_dmd()
	conf.d_platform_flags()
	if str(conf.env.D).find('ldc')>-1:
		conf.common_flags_ldc()

########NEW FILE########
__FILENAME__ = d_config
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

from waflib import Utils
from waflib.Configure import conf
@conf
def d_platform_flags(self):
	v=self.env
	if not v.DEST_OS:
		v.DEST_OS=Utils.unversioned_sys_platform()
	binfmt=Utils.destos_to_binfmt(self.env.DEST_OS)
	if binfmt=='pe':
		v['dprogram_PATTERN']='%s.exe'
		v['dshlib_PATTERN']='lib%s.dll'
		v['dstlib_PATTERN']='lib%s.a'
	elif binfmt=='mac-o':
		v['dprogram_PATTERN']='%s'
		v['dshlib_PATTERN']='lib%s.dylib'
		v['dstlib_PATTERN']='lib%s.a'
	else:
		v['dprogram_PATTERN']='%s'
		v['dshlib_PATTERN']='lib%s.so'
		v['dstlib_PATTERN']='lib%s.a'
DLIB='''
version(D_Version2) {
	import std.stdio;
	int main() {
		writefln("phobos2");
		return 0;
	}
} else {
	version(Tango) {
		import tango.stdc.stdio;
		int main() {
			printf("tango");
			return 0;
		}
	} else {
		import std.stdio;
		int main() {
			writefln("phobos1");
			return 0;
		}
	}
}
'''
@conf
def check_dlibrary(self,execute=True):
	ret=self.check_cc(features='d dprogram',fragment=DLIB,compile_filename='test.d',execute=execute,define_ret=True)
	if execute:
		self.env.DLIBRARY=ret.strip()

########NEW FILE########
__FILENAME__ = d_scan
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import re
from waflib import Utils,Logs
def filter_comments(filename):
	txt=Utils.readf(filename)
	i=0
	buf=[]
	max=len(txt)
	begin=0
	while i<max:
		c=txt[i]
		if c=='"'or c=="'":
			buf.append(txt[begin:i])
			delim=c
			i+=1
			while i<max:
				c=txt[i]
				if c==delim:break
				elif c=='\\':
					i+=1
				i+=1
			i+=1
			begin=i
		elif c=='/':
			buf.append(txt[begin:i])
			i+=1
			if i==max:break
			c=txt[i]
			if c=='+':
				i+=1
				nesting=1
				c=None
				while i<max:
					prev=c
					c=txt[i]
					if prev=='/'and c=='+':
						nesting+=1
						c=None
					elif prev=='+'and c=='/':
						nesting-=1
						if nesting==0:break
						c=None
					i+=1
			elif c=='*':
				i+=1
				c=None
				while i<max:
					prev=c
					c=txt[i]
					if prev=='*'and c=='/':break
					i+=1
			elif c=='/':
				i+=1
				while i<max and txt[i]!='\n':
					i+=1
			else:
				begin=i-1
				continue
			i+=1
			begin=i
			buf.append(' ')
		else:
			i+=1
	buf.append(txt[begin:])
	return buf
class d_parser(object):
	def __init__(self,env,incpaths):
		self.allnames=[]
		self.re_module=re.compile("module\s+([^;]+)")
		self.re_import=re.compile("import\s+([^;]+)")
		self.re_import_bindings=re.compile("([^:]+):(.*)")
		self.re_import_alias=re.compile("[^=]+=(.+)")
		self.env=env
		self.nodes=[]
		self.names=[]
		self.incpaths=incpaths
	def tryfind(self,filename):
		found=0
		for n in self.incpaths:
			found=n.find_resource(filename.replace('.','/')+'.d')
			if found:
				self.nodes.append(found)
				self.waiting.append(found)
				break
		if not found:
			if not filename in self.names:
				self.names.append(filename)
	def get_strings(self,code):
		self.module=''
		lst=[]
		mod_name=self.re_module.search(code)
		if mod_name:
			self.module=re.sub('\s+','',mod_name.group(1))
		import_iterator=self.re_import.finditer(code)
		if import_iterator:
			for import_match in import_iterator:
				import_match_str=re.sub('\s+','',import_match.group(1))
				bindings_match=self.re_import_bindings.match(import_match_str)
				if bindings_match:
					import_match_str=bindings_match.group(1)
				matches=import_match_str.split(',')
				for match in matches:
					alias_match=self.re_import_alias.match(match)
					if alias_match:
						match=alias_match.group(1)
					lst.append(match)
		return lst
	def start(self,node):
		self.waiting=[node]
		while self.waiting:
			nd=self.waiting.pop(0)
			self.iter(nd)
	def iter(self,node):
		path=node.abspath()
		code="".join(filter_comments(path))
		names=self.get_strings(code)
		for x in names:
			if x in self.allnames:continue
			self.allnames.append(x)
			self.tryfind(x)
def scan(self):
	env=self.env
	gruik=d_parser(env,self.generator.includes_nodes)
	node=self.inputs[0]
	gruik.start(node)
	nodes=gruik.nodes
	names=gruik.names
	if Logs.verbose:
		Logs.debug('deps: deps for %s: %r; unresolved %r'%(str(node),nodes,names))
	return(nodes,names)

########NEW FILE########
__FILENAME__ = errcheck
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

typos={'feature':'features','sources':'source','targets':'target','include':'includes','export_include':'export_includes','define':'defines','importpath':'includes','installpath':'install_path','iscopy':'is_copy',}
meths_typos=['__call__','program','shlib','stlib','objects']
from waflib import Logs,Build,Node,Task,TaskGen,ConfigSet,Errors,Utils
import waflib.Tools.ccroot
def check_same_targets(self):
	mp=Utils.defaultdict(list)
	uids={}
	def check_task(tsk):
		if not isinstance(tsk,Task.Task):
			return
		for node in tsk.outputs:
			mp[node].append(tsk)
		try:
			uids[tsk.uid()].append(tsk)
		except KeyError:
			uids[tsk.uid()]=[tsk]
	for g in self.groups:
		for tg in g:
			try:
				for tsk in tg.tasks:
					check_task(tsk)
			except AttributeError:
				check_task(tg)
	dupe=False
	for(k,v)in mp.items():
		if len(v)>1:
			dupe=True
			msg='* Node %r is created more than once%s. The task generators are:'%(k,Logs.verbose==1 and" (full message on 'waf -v -v')"or"")
			Logs.error(msg)
			for x in v:
				if Logs.verbose>1:
					Logs.error('  %d. %r'%(1+v.index(x),x.generator))
				else:
					Logs.error('  %d. %r in %r'%(1+v.index(x),x.generator.name,getattr(x.generator,'path',None)))
	if not dupe:
		for(k,v)in uids.items():
			if len(v)>1:
				Logs.error('* Several tasks use the same identifier. Please check the information on\n   http://docs.waf.googlecode.com/git/apidocs_16/Task.html#waflib.Task.Task.uid')
				for tsk in v:
					Logs.error('  - object %r (%r) defined in %r'%(tsk.__class__.__name__,tsk,tsk.generator))
def check_invalid_constraints(self):
	feat=set([])
	for x in list(TaskGen.feats.values()):
		feat.union(set(x))
	for(x,y)in TaskGen.task_gen.prec.items():
		feat.add(x)
		feat.union(set(y))
	ext=set([])
	for x in TaskGen.task_gen.mappings.values():
		ext.add(x.__name__)
	invalid=ext&feat
	if invalid:
		Logs.error('The methods %r have invalid annotations:  @extension <-> @feature/@before_method/@after_method'%list(invalid))
	for cls in list(Task.classes.values()):
		for x in('before','after'):
			for y in Utils.to_list(getattr(cls,x,[])):
				if not Task.classes.get(y,None):
					Logs.error('Erroneous order constraint %r=%r on task class %r'%(x,y,cls.__name__))
		if getattr(cls,'rule',None):
			Logs.error('Erroneous attribute "rule" on task class %r (rename to "run_str")'%cls.__name__)
def replace(m):
	oldcall=getattr(Build.BuildContext,m)
	def call(self,*k,**kw):
		ret=oldcall(self,*k,**kw)
		for x in typos:
			if x in kw:
				if x=='iscopy'and'subst'in getattr(self,'features',''):
					continue
				err=True
				Logs.error('Fix the typo %r -> %r on %r'%(x,typos[x],ret))
		return ret
	setattr(Build.BuildContext,m,call)
def enhance_lib():
	for m in meths_typos:
		replace(m)
	def ant_glob(self,*k,**kw):
		if k:
			lst=Utils.to_list(k[0])
			for pat in lst:
				if'..'in pat.split('/'):
					Logs.error("In ant_glob pattern %r: '..' means 'two dots', not 'parent directory'"%k[0])
		if kw.get('remove',True):
			try:
				if self.is_child_of(self.ctx.bldnode)and not kw.get('quiet',False):
					Logs.error('Using ant_glob on the build folder (%r) is dangerous (quiet=True to disable this warning)'%self)
			except AttributeError:
				pass
		return self.old_ant_glob(*k,**kw)
	Node.Node.old_ant_glob=Node.Node.ant_glob
	Node.Node.ant_glob=ant_glob
	old=Task.is_before
	def is_before(t1,t2):
		ret=old(t1,t2)
		if ret and old(t2,t1):
			Logs.error('Contradictory order constraints in classes %r %r'%(t1,t2))
		return ret
	Task.is_before=is_before
	def check_err_features(self):
		lst=self.to_list(self.features)
		if'shlib'in lst:
			Logs.error('feature shlib -> cshlib, dshlib or cxxshlib')
		for x in('c','cxx','d','fc'):
			if not x in lst and lst and lst[0]in[x+y for y in('program','shlib','stlib')]:
				Logs.error('%r features is probably missing %r'%(self,x))
	TaskGen.feature('*')(check_err_features)
	def check_err_order(self):
		if not hasattr(self,'rule')and not'subst'in Utils.to_list(self.features):
			for x in('before','after','ext_in','ext_out'):
				if hasattr(self,x):
					Logs.warn('Erroneous order constraint %r on non-rule based task generator %r'%(x,self))
		else:
			for x in('before','after'):
				for y in self.to_list(getattr(self,x,[])):
					if not Task.classes.get(y,None):
						Logs.error('Erroneous order constraint %s=%r on %r (no such class)'%(x,y,self))
	TaskGen.feature('*')(check_err_order)
	def check_compile(self):
		check_invalid_constraints(self)
		try:
			ret=self.orig_compile()
		finally:
			check_same_targets(self)
		return ret
	Build.BuildContext.orig_compile=Build.BuildContext.compile
	Build.BuildContext.compile=check_compile
	def use_rec(self,name,**kw):
		try:
			y=self.bld.get_tgen_by_name(name)
		except Errors.WafError:
			pass
		else:
			idx=self.bld.get_group_idx(self)
			odx=self.bld.get_group_idx(y)
			if odx>idx:
				msg="Invalid 'use' across build groups:"
				if Logs.verbose>1:
					msg+='\n  target %r\n  uses:\n  %r'%(self,y)
				else:
					msg+=" %r uses %r (try 'waf -v -v' for the full error)"%(self.name,name)
				raise Errors.WafError(msg)
		self.orig_use_rec(name,**kw)
	TaskGen.task_gen.orig_use_rec=TaskGen.task_gen.use_rec
	TaskGen.task_gen.use_rec=use_rec
	def getattri(self,name,default=None):
		if name=='append'or name=='add':
			raise Errors.WafError('env.append and env.add do not exist: use env.append_value/env.append_unique')
		elif name=='prepend':
			raise Errors.WafError('env.prepend does not exist: use env.prepend_value')
		if name in self.__slots__:
			return object.__getattr__(self,name,default)
		else:
			return self[name]
	ConfigSet.ConfigSet.__getattr__=getattri
def options(opt):
	enhance_lib()
def configure(conf):
	pass

########NEW FILE########
__FILENAME__ = fc
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import re
from waflib import Utils,Task,TaskGen,Logs
from waflib.Tools import ccroot,fc_config,fc_scan
from waflib.TaskGen import feature,before_method,after_method,extension
from waflib.Configure import conf
ccroot.USELIB_VARS['fc']=set(['FCFLAGS','DEFINES','INCLUDES'])
ccroot.USELIB_VARS['fcprogram_test']=ccroot.USELIB_VARS['fcprogram']=set(['LIB','STLIB','LIBPATH','STLIBPATH','LINKFLAGS','RPATH','LINKDEPS'])
ccroot.USELIB_VARS['fcshlib']=set(['LIB','STLIB','LIBPATH','STLIBPATH','LINKFLAGS','RPATH','LINKDEPS'])
ccroot.USELIB_VARS['fcstlib']=set(['ARFLAGS','LINKDEPS'])
@feature('fcprogram','fcshlib','fcstlib','fcprogram_test')
def dummy(self):
	pass
@extension('.f','.f90','.F','.F90','.for','.FOR')
def fc_hook(self,node):
	return self.create_compiled_task('fc',node)
@conf
def modfile(conf,name):
	return{'lower':name.lower()+'.mod','lower.MOD':name.upper()+'.MOD','UPPER.mod':name.upper()+'.mod','UPPER':name.upper()+'.MOD'}[conf.env.FC_MOD_CAPITALIZATION or'lower']
def get_fortran_tasks(tsk):
	bld=tsk.generator.bld
	tasks=bld.get_tasks_group(bld.get_group_idx(tsk.generator))
	return[x for x in tasks if isinstance(x,fc)and not getattr(x,'nomod',None)and not getattr(x,'mod_fortran_done',None)]
class fc(Task.Task):
	color='GREEN'
	run_str='${FC} ${FCFLAGS} ${FCINCPATH_ST:INCPATHS} ${FCDEFINES_ST:DEFINES} ${_FCMODOUTFLAGS} ${FC_TGT_F}${TGT[0].abspath()} ${FC_SRC_F}${SRC[0].abspath()}'
	vars=["FORTRANMODPATHFLAG"]
	def scan(self):
		tmp=fc_scan.fortran_parser(self.generator.includes_nodes)
		tmp.task=self
		tmp.start(self.inputs[0])
		if Logs.verbose:
			Logs.debug('deps: deps for %r: %r; unresolved %r'%(self.inputs,tmp.nodes,tmp.names))
		return(tmp.nodes,tmp.names)
	def runnable_status(self):
		if getattr(self,'mod_fortran_done',None):
			return super(fc,self).runnable_status()
		bld=self.generator.bld
		lst=get_fortran_tasks(self)
		for tsk in lst:
			tsk.mod_fortran_done=True
		for tsk in lst:
			ret=tsk.runnable_status()
			if ret==Task.ASK_LATER:
				for x in lst:
					x.mod_fortran_done=None
				return Task.ASK_LATER
		ins=Utils.defaultdict(set)
		outs=Utils.defaultdict(set)
		for tsk in lst:
			key=tsk.uid()
			for x in bld.raw_deps[key]:
				if x.startswith('MOD@'):
					name=bld.modfile(x.replace('MOD@',''))
					node=bld.srcnode.find_or_declare(name)
					tsk.set_outputs(node)
					outs[id(node)].add(tsk)
		for tsk in lst:
			key=tsk.uid()
			for x in bld.raw_deps[key]:
				if x.startswith('USE@'):
					name=bld.modfile(x.replace('USE@',''))
					node=bld.srcnode.find_resource(name)
					if node and node not in tsk.outputs:
						if not node in bld.node_deps[key]:
							bld.node_deps[key].append(node)
						ins[id(node)].add(tsk)
		for k in ins.keys():
			for a in ins[k]:
				a.run_after.update(outs[k])
				tmp=[]
				for t in outs[k]:
					tmp.extend(t.outputs)
				a.dep_nodes.extend(tmp)
				a.dep_nodes.sort(key=lambda x:x.abspath())
		for tsk in lst:
			try:
				delattr(tsk,'cache_sig')
			except AttributeError:
				pass
		return super(fc,self).runnable_status()
class fcprogram(ccroot.link_task):
	color='YELLOW'
	run_str='${FC} ${LINKFLAGS} ${FCLNK_SRC_F}${SRC} ${FCLNK_TGT_F}${TGT[0].abspath()} ${RPATH_ST:RPATH} ${FCSTLIB_MARKER} ${FCSTLIBPATH_ST:STLIBPATH} ${FCSTLIB_ST:STLIB} ${FCSHLIB_MARKER} ${FCLIBPATH_ST:LIBPATH} ${FCLIB_ST:LIB}'
	inst_to='${BINDIR}'
class fcshlib(fcprogram):
	inst_to='${LIBDIR}'
class fcprogram_test(fcprogram):
	def can_retrieve_cache(self):
		return False
	def runnable_status(self):
		ret=super(fcprogram_test,self).runnable_status()
		if ret==Task.SKIP_ME:
			ret=Task.RUN_ME
		return ret
	def exec_command(self,cmd,**kw):
		bld=self.generator.bld
		kw['shell']=isinstance(cmd,str)
		kw['stdout']=kw['stderr']=Utils.subprocess.PIPE
		kw['cwd']=bld.variant_dir
		bld.out=bld.err=''
		bld.to_log('command: %s\n'%cmd)
		kw['output']=0
		try:
			(bld.out,bld.err)=bld.cmd_and_log(cmd,**kw)
		except Exception ,e:
			return-1
		if bld.out:
			bld.to_log("out: %s\n"%bld.out)
		if bld.err:
			bld.to_log("err: %s\n"%bld.err)
class fcstlib(ccroot.stlink_task):
	pass

########NEW FILE########
__FILENAME__ = fc_config
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import re,shutil,os,sys,string,shlex
from waflib.Configure import conf
from waflib.TaskGen import feature,after_method,before_method
from waflib import Build,Utils
FC_FRAGMENT='        program main\n        end     program main\n'
FC_FRAGMENT2='        PROGRAM MAIN\n        END\n'
@conf
def fc_flags(conf):
	v=conf.env
	v['FC_SRC_F']=[]
	v['FC_TGT_F']=['-c','-o']
	v['FCINCPATH_ST']='-I%s'
	v['FCDEFINES_ST']='-D%s'
	if not v['LINK_FC']:v['LINK_FC']=v['FC']
	v['FCLNK_SRC_F']=[]
	v['FCLNK_TGT_F']=['-o']
	v['FCFLAGS_fcshlib']=['-fpic']
	v['LINKFLAGS_fcshlib']=['-shared']
	v['fcshlib_PATTERN']='lib%s.so'
	v['fcstlib_PATTERN']='lib%s.a'
	v['FCLIB_ST']='-l%s'
	v['FCLIBPATH_ST']='-L%s'
	v['FCSTLIB_ST']='-l%s'
	v['FCSTLIBPATH_ST']='-L%s'
	v['FCSTLIB_MARKER']='-Wl,-Bstatic'
	v['FCSHLIB_MARKER']='-Wl,-Bdynamic'
	v['SONAME_ST']='-Wl,-h,%s'
@conf
def fc_add_flags(conf):
	conf.add_os_flags('FCFLAGS')
	conf.add_os_flags('LDFLAGS','LINKFLAGS')
@conf
def check_fortran(self,*k,**kw):
	self.check_cc(fragment=FC_FRAGMENT,compile_filename='test.f',features='fc fcprogram',msg='Compiling a simple fortran app')
@conf
def check_fc(self,*k,**kw):
	kw['compiler']='fc'
	if not'compile_mode'in kw:
		kw['compile_mode']='fc'
	if not'type'in kw:
		kw['type']='fcprogram'
	if not'compile_filename'in kw:
		kw['compile_filename']='test.f90'
	if not'code'in kw:
		kw['code']=FC_FRAGMENT
	return self.check(*k,**kw)
@conf
def fortran_modifier_darwin(conf):
	v=conf.env
	v['FCFLAGS_fcshlib']=['-fPIC']
	v['LINKFLAGS_fcshlib']=['-dynamiclib','-Wl,-compatibility_version,1','-Wl,-current_version,1']
	v['fcshlib_PATTERN']='lib%s.dylib'
	v['FRAMEWORKPATH_ST']='-F%s'
	v['FRAMEWORK_ST']='-framework %s'
	v['LINKFLAGS_fcstlib']=[]
	v['FCSHLIB_MARKER']=''
	v['FCSTLIB_MARKER']=''
	v['SONAME_ST']=''
@conf
def fortran_modifier_win32(conf):
	v=conf.env
	v['fcprogram_PATTERN']=v['fcprogram_test_PATTERN']='%s.exe'
	v['fcshlib_PATTERN']='%s.dll'
	v['implib_PATTERN']='lib%s.dll.a'
	v['IMPLIB_ST']='-Wl,--out-implib,%s'
	v['FCFLAGS_fcshlib']=[]
	v.append_value('FCFLAGS_fcshlib',['-DDLL_EXPORT'])
	v.append_value('LINKFLAGS',['-Wl,--enable-auto-import'])
@conf
def fortran_modifier_cygwin(conf):
	fortran_modifier_win32(conf)
	v=conf.env
	v['fcshlib_PATTERN']='cyg%s.dll'
	v.append_value('LINKFLAGS_fcshlib',['-Wl,--enable-auto-image-base'])
	v['FCFLAGS_fcshlib']=[]
@conf
def check_fortran_dummy_main(self,*k,**kw):
	if not self.env.CC:
		self.fatal('A c compiler is required for check_fortran_dummy_main')
	lst=['MAIN__','__MAIN','_MAIN','MAIN_','MAIN']
	lst.extend([m.lower()for m in lst])
	lst.append('')
	self.start_msg('Detecting whether we need a dummy main')
	for main in lst:
		kw['fortran_main']=main
		try:
			self.check_cc(fragment='int %s() { return 0; }\n'%(main or'test'),features='c fcprogram',mandatory=True)
			if not main:
				self.env.FC_MAIN=-1
				self.end_msg('no')
			else:
				self.env.FC_MAIN=main
				self.end_msg('yes %s'%main)
			break
		except self.errors.ConfigurationError:
			pass
	else:
		self.end_msg('not found')
		self.fatal('could not detect whether fortran requires a dummy main, see the config.log')
GCC_DRIVER_LINE=re.compile('^Driving:')
POSIX_STATIC_EXT=re.compile('\S+\.a')
POSIX_LIB_FLAGS=re.compile('-l\S+')
@conf
def is_link_verbose(self,txt):
	assert isinstance(txt,str)
	for line in txt.splitlines():
		if not GCC_DRIVER_LINE.search(line):
			if POSIX_STATIC_EXT.search(line)or POSIX_LIB_FLAGS.search(line):
				return True
	return False
@conf
def check_fortran_verbose_flag(self,*k,**kw):
	self.start_msg('fortran link verbose flag')
	for x in['-v','--verbose','-verbose','-V']:
		try:
			self.check_cc(features='fc fcprogram_test',fragment=FC_FRAGMENT2,compile_filename='test.f',linkflags=[x],mandatory=True)
		except self.errors.ConfigurationError:
			pass
		else:
			if self.is_link_verbose(self.test_bld.err)or self.is_link_verbose(self.test_bld.out):
				self.end_msg(x)
				break
	else:
		self.end_msg('failure')
		self.fatal('Could not obtain the fortran link verbose flag (see config.log)')
	self.env.FC_VERBOSE_FLAG=x
	return x
LINKFLAGS_IGNORED=[r'-lang*',r'-lcrt[a-zA-Z0-9\.]*\.o',r'-lc$',r'-lSystem',r'-libmil',r'-LIST:*',r'-LNO:*']
if os.name=='nt':
	LINKFLAGS_IGNORED.extend([r'-lfrt*',r'-luser32',r'-lkernel32',r'-ladvapi32',r'-lmsvcrt',r'-lshell32',r'-lmingw',r'-lmoldname'])
else:
	LINKFLAGS_IGNORED.append(r'-lgcc*')
RLINKFLAGS_IGNORED=[re.compile(f)for f in LINKFLAGS_IGNORED]
def _match_ignore(line):
	for i in RLINKFLAGS_IGNORED:
		if i.match(line):
			return True
	return False
def parse_fortran_link(lines):
	final_flags=[]
	for line in lines:
		if not GCC_DRIVER_LINE.match(line):
			_parse_flink_line(line,final_flags)
	return final_flags
SPACE_OPTS=re.compile('^-[LRuYz]$')
NOSPACE_OPTS=re.compile('^-[RL]')
def _parse_flink_line(line,final_flags):
	lexer=shlex.shlex(line,posix=True)
	lexer.whitespace_split=True
	t=lexer.get_token()
	tmp_flags=[]
	while t:
		def parse(token):
			if _match_ignore(token):
				pass
			elif token.startswith('-lkernel32')and sys.platform=='cygwin':
				tmp_flags.append(token)
			elif SPACE_OPTS.match(token):
				t=lexer.get_token()
				if t.startswith('P,'):
					t=t[2:]
				for opt in t.split(os.pathsep):
					tmp_flags.append('-L%s'%opt)
			elif NOSPACE_OPTS.match(token):
				tmp_flags.append(token)
			elif POSIX_LIB_FLAGS.match(token):
				tmp_flags.append(token)
			else:
				pass
			t=lexer.get_token()
			return t
		t=parse(t)
	final_flags.extend(tmp_flags)
	return final_flags
@conf
def check_fortran_clib(self,autoadd=True,*k,**kw):
	if not self.env.FC_VERBOSE_FLAG:
		self.fatal('env.FC_VERBOSE_FLAG is not set: execute check_fortran_verbose_flag?')
	self.start_msg('Getting fortran runtime link flags')
	try:
		self.check_cc(fragment=FC_FRAGMENT2,compile_filename='test.f',features='fc fcprogram_test',linkflags=[self.env.FC_VERBOSE_FLAG])
	except Exception:
		self.end_msg(False)
		if kw.get('mandatory',True):
			conf.fatal('Could not find the c library flags')
	else:
		out=self.test_bld.err
		flags=parse_fortran_link(out.splitlines())
		self.end_msg('ok (%s)'%' '.join(flags))
		self.env.LINKFLAGS_CLIB=flags
		return flags
	return[]
def getoutput(conf,cmd,stdin=False):
	if stdin:
		stdin=Utils.subprocess.PIPE
	else:
		stdin=None
	env=conf.env.env or None
	try:
		p=Utils.subprocess.Popen(cmd,stdin=stdin,stdout=Utils.subprocess.PIPE,stderr=Utils.subprocess.PIPE,env=env)
		if stdin:
			p.stdin.write('\n')
		out,err=p.communicate()
	except Exception:
		conf.fatal('could not determine the compiler version %r'%cmd)
	if not isinstance(out,str):
		out=out.decode(sys.stdout.encoding or'iso8859-1')
	if not isinstance(err,str):
		err=err.decode(sys.stdout.encoding or'iso8859-1')
	return(out,err)
ROUTINES_CODE="""\
      subroutine foobar()
      return
      end
      subroutine foo_bar()
      return
      end
"""
MAIN_CODE="""
void %(dummy_func_nounder)s(void);
void %(dummy_func_under)s(void);
int %(main_func_name)s() {
  %(dummy_func_nounder)s();
  %(dummy_func_under)s();
  return 0;
}
"""
@feature('link_main_routines_func')
@before_method('process_source')
def link_main_routines_tg_method(self):
	def write_test_file(task):
		task.outputs[0].write(task.generator.code)
	bld=self.bld
	bld(rule=write_test_file,target='main.c',code=MAIN_CODE%self.__dict__)
	bld(rule=write_test_file,target='test.f',code=ROUTINES_CODE)
	bld(features='fc fcstlib',source='test.f',target='test')
	bld(features='c fcprogram',source='main.c',target='app',use='test')
def mangling_schemes():
	for u in['_','']:
		for du in['','_']:
			for c in["lower","upper"]:
				yield(u,du,c)
def mangle_name(u,du,c,name):
	return getattr(name,c)()+u+(name.find('_')!=-1 and du or'')
@conf
def check_fortran_mangling(self,*k,**kw):
	if not self.env.CC:
		self.fatal('A c compiler is required for link_main_routines')
	if not self.env.FC:
		self.fatal('A fortran compiler is required for link_main_routines')
	if not self.env.FC_MAIN:
		self.fatal('Checking for mangling requires self.env.FC_MAIN (execute "check_fortran_dummy_main" first?)')
	self.start_msg('Getting fortran mangling scheme')
	for(u,du,c)in mangling_schemes():
		try:
			self.check_cc(compile_filename=[],features='link_main_routines_func',msg='nomsg',errmsg='nomsg',mandatory=True,dummy_func_nounder=mangle_name(u,du,c,"foobar"),dummy_func_under=mangle_name(u,du,c,"foo_bar"),main_func_name=self.env.FC_MAIN)
		except self.errors.ConfigurationError:
			pass
		else:
			self.end_msg("ok ('%s', '%s', '%s-case')"%(u,du,c))
			self.env.FORTRAN_MANGLING=(u,du,c)
			break
	else:
		self.end_msg(False)
		self.fatal('mangler not found')
	return(u,du,c)
@feature('pyext')
@before_method('propagate_uselib_vars','apply_link')
def set_lib_pat(self):
	self.env['fcshlib_PATTERN']=self.env['pyext_PATTERN']
@conf
def detect_openmp(self):
	for x in['-fopenmp','-openmp','-mp','-xopenmp','-omp','-qsmp=omp']:
		try:
			self.check_fc(msg='Checking for OpenMP flag %s'%x,fragment='program main\n  call omp_get_num_threads()\nend program main',fcflags=x,linkflags=x,uselib_store='OPENMP')
		except self.errors.ConfigurationError:
			pass
		else:
			break
	else:
		self.fatal('Could not find OpenMP')

########NEW FILE########
__FILENAME__ = fc_scan
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import re
from waflib import Utils,Task,TaskGen,Logs
from waflib.TaskGen import feature,before_method,after_method,extension
from waflib.Configure import conf
INC_REGEX="""(?:^|['">]\s*;)\s*(?:|#\s*)INCLUDE\s+(?:\w+_)?[<"'](.+?)(?=["'>])"""
USE_REGEX="""(?:^|;)\s*USE(?:\s+|(?:(?:\s*,\s*(?:NON_)?INTRINSIC)?\s*::))\s*(\w+)"""
MOD_REGEX="""(?:^|;)\s*MODULE(?!\s*PROCEDURE)(?:\s+|(?:(?:\s*,\s*(?:NON_)?INTRINSIC)?\s*::))\s*(\w+)"""
re_inc=re.compile(INC_REGEX,re.I)
re_use=re.compile(USE_REGEX,re.I)
re_mod=re.compile(MOD_REGEX,re.I)
class fortran_parser(object):
	def __init__(self,incpaths):
		self.seen=[]
		self.nodes=[]
		self.names=[]
		self.incpaths=incpaths
	def find_deps(self,node):
		txt=node.read()
		incs=[]
		uses=[]
		mods=[]
		for line in txt.splitlines():
			m=re_inc.search(line)
			if m:
				incs.append(m.group(1))
			m=re_use.search(line)
			if m:
				uses.append(m.group(1))
			m=re_mod.search(line)
			if m:
				mods.append(m.group(1))
		return(incs,uses,mods)
	def start(self,node):
		self.waiting=[node]
		while self.waiting:
			nd=self.waiting.pop(0)
			self.iter(nd)
	def iter(self,node):
		path=node.abspath()
		incs,uses,mods=self.find_deps(node)
		for x in incs:
			if x in self.seen:
				continue
			self.seen.append(x)
			self.tryfind_header(x)
		for x in uses:
			name="USE@%s"%x
			if not name in self.names:
				self.names.append(name)
		for x in mods:
			name="MOD@%s"%x
			if not name in self.names:
				self.names.append(name)
	def tryfind_header(self,filename):
		found=None
		for n in self.incpaths:
			found=n.find_resource(filename)
			if found:
				self.nodes.append(found)
				self.waiting.append(found)
				break
		if not found:
			if not filename in self.names:
				self.names.append(filename)

########NEW FILE########
__FILENAME__ = flex
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import waflib.TaskGen,os,re
def decide_ext(self,node):
	if'cxx'in self.features:
		return['.lex.cc']
	return['.lex.c']
def flexfun(tsk):
	env=tsk.env
	bld=tsk.generator.bld
	wd=bld.variant_dir
	def to_list(xx):
		if isinstance(xx,str):return[xx]
		return xx
	tsk.last_cmd=lst=[]
	lst.extend(to_list(env['FLEX']))
	lst.extend(to_list(env['FLEXFLAGS']))
	inputs=[a.path_from(bld.bldnode)for a in tsk.inputs]
	if env.FLEX_MSYS:
		inputs=[x.replace(os.sep,'/')for x in inputs]
	lst.extend(inputs)
	lst=[x for x in lst if x]
	txt=bld.cmd_and_log(lst,cwd=wd,env=env.env or None,quiet=0)
	tsk.outputs[0].write(txt.replace('\r\n','\n').replace('\r','\n'))
waflib.TaskGen.declare_chain(name='flex',rule=flexfun,ext_in='.l',decider=decide_ext,)
def configure(conf):
	conf.find_program('flex',var='FLEX')
	conf.env.FLEXFLAGS=['-t']
	if re.search(r"\\msys\\[0-9.]+\\bin\\flex.exe$",conf.env.FLEX):
		conf.env.FLEX_MSYS=True

########NEW FILE########
__FILENAME__ = g95
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import re
from waflib import Utils
from waflib.Tools import fc,fc_config,fc_scan,ar
from waflib.Configure import conf
@conf
def find_g95(conf):
	fc=conf.find_program('g95',var='FC')
	fc=conf.cmd_to_list(fc)
	conf.get_g95_version(fc)
	conf.env.FC_NAME='G95'
@conf
def g95_flags(conf):
	v=conf.env
	v['FCFLAGS_fcshlib']=['-fPIC']
	v['FORTRANMODFLAG']=['-fmod=','']
	v['FCFLAGS_DEBUG']=['-Werror']
@conf
def g95_modifier_win32(conf):
	fc_config.fortran_modifier_win32(conf)
@conf
def g95_modifier_cygwin(conf):
	fc_config.fortran_modifier_cygwin(conf)
@conf
def g95_modifier_darwin(conf):
	fc_config.fortran_modifier_darwin(conf)
@conf
def g95_modifier_platform(conf):
	dest_os=conf.env['DEST_OS']or Utils.unversioned_sys_platform()
	g95_modifier_func=getattr(conf,'g95_modifier_'+dest_os,None)
	if g95_modifier_func:
		g95_modifier_func()
@conf
def get_g95_version(conf,fc):
	version_re=re.compile(r"g95\s*(?P<major>\d*)\.(?P<minor>\d*)").search
	cmd=fc+['--version']
	out,err=fc_config.getoutput(conf,cmd,stdin=False)
	if out:
		match=version_re(out)
	else:
		match=version_re(err)
	if not match:
		conf.fatal('cannot determine g95 version')
	k=match.groupdict()
	conf.env['FC_VERSION']=(k['major'],k['minor'])
def configure(conf):
	conf.find_g95()
	conf.find_ar()
	conf.fc_flags()
	conf.fc_add_flags()
	conf.g95_flags()
	conf.g95_modifier_platform()

########NEW FILE########
__FILENAME__ = gas
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import waflib.Tools.asm
from waflib.Tools import ar
def configure(conf):
	conf.find_program(['gas','gcc'],var='AS')
	conf.env.AS_TGT_F=['-c','-o']
	conf.env.ASLNK_TGT_F=['-o']
	conf.find_ar()
	conf.load('asm')

########NEW FILE########
__FILENAME__ = gcc
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

from waflib.Tools import ccroot,ar
from waflib.Configure import conf
@conf
def find_gcc(conf):
	cc=conf.find_program(['gcc','cc'],var='CC')
	cc=conf.cmd_to_list(cc)
	conf.get_cc_version(cc,gcc=True)
	conf.env.CC_NAME='gcc'
	conf.env.CC=cc
@conf
def gcc_common_flags(conf):
	v=conf.env
	v['CC_SRC_F']=[]
	v['CC_TGT_F']=['-c','-o']
	if not v['LINK_CC']:v['LINK_CC']=v['CC']
	v['CCLNK_SRC_F']=[]
	v['CCLNK_TGT_F']=['-o']
	v['CPPPATH_ST']='-I%s'
	v['DEFINES_ST']='-D%s'
	v['LIB_ST']='-l%s'
	v['LIBPATH_ST']='-L%s'
	v['STLIB_ST']='-l%s'
	v['STLIBPATH_ST']='-L%s'
	v['RPATH_ST']='-Wl,-rpath,%s'
	v['SONAME_ST']='-Wl,-h,%s'
	v['SHLIB_MARKER']='-Wl,-Bdynamic'
	v['STLIB_MARKER']='-Wl,-Bstatic'
	v['cprogram_PATTERN']='%s'
	v['CFLAGS_cshlib']=['-fPIC']
	v['LINKFLAGS_cshlib']=['-shared']
	v['cshlib_PATTERN']='lib%s.so'
	v['LINKFLAGS_cstlib']=['-Wl,-Bstatic']
	v['cstlib_PATTERN']='lib%s.a'
	v['LINKFLAGS_MACBUNDLE']=['-bundle','-undefined','dynamic_lookup']
	v['CFLAGS_MACBUNDLE']=['-fPIC']
	v['macbundle_PATTERN']='%s.bundle'
@conf
def gcc_modifier_win32(conf):
	v=conf.env
	v['cprogram_PATTERN']='%s.exe'
	v['cshlib_PATTERN']='%s.dll'
	v['implib_PATTERN']='lib%s.dll.a'
	v['IMPLIB_ST']='-Wl,--out-implib,%s'
	v['CFLAGS_cshlib']=[]
	v.append_value('LINKFLAGS',['-Wl,--enable-auto-import'])
@conf
def gcc_modifier_cygwin(conf):
	gcc_modifier_win32(conf)
	v=conf.env
	v['cshlib_PATTERN']='cyg%s.dll'
	v.append_value('LINKFLAGS_cshlib',['-Wl,--enable-auto-image-base'])
	v['CFLAGS_cshlib']=[]
@conf
def gcc_modifier_darwin(conf):
	v=conf.env
	v['CFLAGS_cshlib']=['-fPIC']
	v['LINKFLAGS_cshlib']=['-dynamiclib','-Wl,-compatibility_version,1','-Wl,-current_version,1']
	v['cshlib_PATTERN']='lib%s.dylib'
	v['FRAMEWORKPATH_ST']='-F%s'
	v['FRAMEWORK_ST']=['-framework']
	v['ARCH_ST']=['-arch']
	v['LINKFLAGS_cstlib']=[]
	v['SHLIB_MARKER']=[]
	v['STLIB_MARKER']=[]
	v['SONAME_ST']=[]
@conf
def gcc_modifier_aix(conf):
	v=conf.env
	v['LINKFLAGS_cprogram']=['-Wl,-brtl']
	v['LINKFLAGS_cshlib']=['-shared','-Wl,-brtl,-bexpfull']
	v['SHLIB_MARKER']=[]
@conf
def gcc_modifier_hpux(conf):
	v=conf.env
	v['SHLIB_MARKER']=[]
	v['STLIB_MARKER']='-Bstatic'
	v['CFLAGS_cshlib']=['-fPIC','-DPIC']
	v['cshlib_PATTERN']='lib%s.sl'
@conf
def gcc_modifier_openbsd(conf):
	conf.env.SONAME_ST=[]
@conf
def gcc_modifier_platform(conf):
	gcc_modifier_func=getattr(conf,'gcc_modifier_'+conf.env.DEST_OS,None)
	if gcc_modifier_func:
		gcc_modifier_func()
def configure(conf):
	conf.find_gcc()
	conf.find_ar()
	conf.gcc_common_flags()
	conf.gcc_modifier_platform()
	conf.cc_load_tools()
	conf.cc_add_flags()
	conf.link_add_flags()

########NEW FILE########
__FILENAME__ = gdc
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import sys
from waflib.Tools import ar,d
from waflib.Configure import conf
@conf
def find_gdc(conf):
	conf.find_program('gdc',var='D')
	out=conf.cmd_and_log([conf.env.D,'--version'])
	if out.find("gdc ")==-1:
		conf.fatal("detected compiler is not gdc")
@conf
def common_flags_gdc(conf):
	v=conf.env
	v['DFLAGS']=[]
	v['D_SRC_F']=['-c']
	v['D_TGT_F']='-o%s'
	v['D_LINKER']=v['D']
	v['DLNK_SRC_F']=''
	v['DLNK_TGT_F']='-o%s'
	v['DINC_ST']='-I%s'
	v['DSHLIB_MARKER']=v['DSTLIB_MARKER']=''
	v['DSTLIB_ST']=v['DSHLIB_ST']='-l%s'
	v['DSTLIBPATH_ST']=v['DLIBPATH_ST']='-L%s'
	v['LINKFLAGS_dshlib']=['-shared']
	v['DHEADER_ext']='.di'
	v.DFLAGS_d_with_header='-fintfc'
	v['D_HDR_F']='-fintfc-file=%s'
def configure(conf):
	conf.find_gdc()
	conf.load('ar')
	conf.load('d')
	conf.common_flags_gdc()
	conf.d_platform_flags()

########NEW FILE########
__FILENAME__ = gfortran
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import re
from waflib import Utils
from waflib.Tools import fc,fc_config,fc_scan,ar
from waflib.Configure import conf
@conf
def find_gfortran(conf):
	fc=conf.find_program(['gfortran','g77'],var='FC')
	fc=conf.cmd_to_list(fc)
	conf.get_gfortran_version(fc)
	conf.env.FC_NAME='GFORTRAN'
@conf
def gfortran_flags(conf):
	v=conf.env
	v['FCFLAGS_fcshlib']=['-fPIC']
	v['FORTRANMODFLAG']=['-J','']
	v['FCFLAGS_DEBUG']=['-Werror']
@conf
def gfortran_modifier_win32(conf):
	fc_config.fortran_modifier_win32(conf)
@conf
def gfortran_modifier_cygwin(conf):
	fc_config.fortran_modifier_cygwin(conf)
@conf
def gfortran_modifier_darwin(conf):
	fc_config.fortran_modifier_darwin(conf)
@conf
def gfortran_modifier_platform(conf):
	dest_os=conf.env['DEST_OS']or Utils.unversioned_sys_platform()
	gfortran_modifier_func=getattr(conf,'gfortran_modifier_'+dest_os,None)
	if gfortran_modifier_func:
		gfortran_modifier_func()
@conf
def get_gfortran_version(conf,fc):
	version_re=re.compile(r"GNU\s*Fortran",re.I).search
	cmd=fc+['--version']
	out,err=fc_config.getoutput(conf,cmd,stdin=False)
	if out:match=version_re(out)
	else:match=version_re(err)
	if not match:
		conf.fatal('Could not determine the compiler type')
	cmd=fc+['-dM','-E','-']
	out,err=fc_config.getoutput(conf,cmd,stdin=True)
	if out.find('__GNUC__')<0:
		conf.fatal('Could not determine the compiler type')
	k={}
	out=out.split('\n')
	import shlex
	for line in out:
		lst=shlex.split(line)
		if len(lst)>2:
			key=lst[1]
			val=lst[2]
			k[key]=val
	def isD(var):
		return var in k
	def isT(var):
		return var in k and k[var]!='0'
	conf.env['FC_VERSION']=(k['__GNUC__'],k['__GNUC_MINOR__'],k['__GNUC_PATCHLEVEL__'])
def configure(conf):
	conf.find_gfortran()
	conf.find_ar()
	conf.fc_flags()
	conf.fc_add_flags()
	conf.gfortran_flags()
	conf.gfortran_modifier_platform()

########NEW FILE########
__FILENAME__ = glib2
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import os
from waflib import Task,Utils,Options,Errors,Logs
from waflib.TaskGen import taskgen_method,before_method,after_method,feature
@taskgen_method
def add_marshal_file(self,filename,prefix):
	if not hasattr(self,'marshal_list'):
		self.marshal_list=[]
	self.meths.append('process_marshal')
	self.marshal_list.append((filename,prefix))
@before_method('process_source')
def process_marshal(self):
	for f,prefix in getattr(self,'marshal_list',[]):
		node=self.path.find_resource(f)
		if not node:
			raise Errors.WafError('file not found %r'%f)
		h_node=node.change_ext('.h')
		c_node=node.change_ext('.c')
		task=self.create_task('glib_genmarshal',node,[h_node,c_node])
		task.env.GLIB_GENMARSHAL_PREFIX=prefix
	self.source=self.to_nodes(getattr(self,'source',[]))
	self.source.append(c_node)
class glib_genmarshal(Task.Task):
	def run(self):
		bld=self.inputs[0].__class__.ctx
		get=self.env.get_flat
		cmd1="%s %s --prefix=%s --header > %s"%(get('GLIB_GENMARSHAL'),self.inputs[0].srcpath(),get('GLIB_GENMARSHAL_PREFIX'),self.outputs[0].abspath())
		ret=bld.exec_command(cmd1)
		if ret:return ret
		c='''#include "%s"\n'''%self.outputs[0].name
		self.outputs[1].write(c)
		cmd2="%s %s --prefix=%s --body >> %s"%(get('GLIB_GENMARSHAL'),self.inputs[0].srcpath(),get('GLIB_GENMARSHAL_PREFIX'),self.outputs[1].abspath())
		return bld.exec_command(cmd2)
	vars=['GLIB_GENMARSHAL_PREFIX','GLIB_GENMARSHAL']
	color='BLUE'
	ext_out=['.h']
@taskgen_method
def add_enums_from_template(self,source='',target='',template='',comments=''):
	if not hasattr(self,'enums_list'):
		self.enums_list=[]
	self.meths.append('process_enums')
	self.enums_list.append({'source':source,'target':target,'template':template,'file-head':'','file-prod':'','file-tail':'','enum-prod':'','value-head':'','value-prod':'','value-tail':'','comments':comments})
@taskgen_method
def add_enums(self,source='',target='',file_head='',file_prod='',file_tail='',enum_prod='',value_head='',value_prod='',value_tail='',comments=''):
	if not hasattr(self,'enums_list'):
		self.enums_list=[]
	self.meths.append('process_enums')
	self.enums_list.append({'source':source,'template':'','target':target,'file-head':file_head,'file-prod':file_prod,'file-tail':file_tail,'enum-prod':enum_prod,'value-head':value_head,'value-prod':value_prod,'value-tail':value_tail,'comments':comments})
@before_method('process_source')
def process_enums(self):
	for enum in getattr(self,'enums_list',[]):
		task=self.create_task('glib_mkenums')
		env=task.env
		inputs=[]
		source_list=self.to_list(enum['source'])
		if not source_list:
			raise Errors.WafError('missing source '+str(enum))
		source_list=[self.path.find_resource(k)for k in source_list]
		inputs+=source_list
		env['GLIB_MKENUMS_SOURCE']=[k.abspath()for k in source_list]
		if not enum['target']:
			raise Errors.WafError('missing target '+str(enum))
		tgt_node=self.path.find_or_declare(enum['target'])
		if tgt_node.name.endswith('.c'):
			self.source.append(tgt_node)
		env['GLIB_MKENUMS_TARGET']=tgt_node.abspath()
		options=[]
		if enum['template']:
			template_node=self.path.find_resource(enum['template'])
			options.append('--template %s'%(template_node.abspath()))
			inputs.append(template_node)
		params={'file-head':'--fhead','file-prod':'--fprod','file-tail':'--ftail','enum-prod':'--eprod','value-head':'--vhead','value-prod':'--vprod','value-tail':'--vtail','comments':'--comments'}
		for param,option in params.items():
			if enum[param]:
				options.append('%s %r'%(option,enum[param]))
		env['GLIB_MKENUMS_OPTIONS']=' '.join(options)
		task.set_inputs(inputs)
		task.set_outputs(tgt_node)
class glib_mkenums(Task.Task):
	run_str='${GLIB_MKENUMS} ${GLIB_MKENUMS_OPTIONS} ${GLIB_MKENUMS_SOURCE} > ${GLIB_MKENUMS_TARGET}'
	color='PINK'
	ext_out=['.h']
@taskgen_method
def add_settings_schemas(self,filename_list):
	if not hasattr(self,'settings_schema_files'):
		self.settings_schema_files=[]
	if not isinstance(filename_list,list):
		filename_list=[filename_list]
	self.settings_schema_files.extend(filename_list)
@taskgen_method
def add_settings_enums(self,namespace,filename_list):
	if hasattr(self,'settings_enum_namespace'):
		raise Errors.WafError("Tried to add gsettings enums to '%s' more than once"%self.name)
	self.settings_enum_namespace=namespace
	if type(filename_list)!='list':
		filename_list=[filename_list]
	self.settings_enum_files=filename_list
def r_change_ext(self,ext):
	name=self.name
	k=name.rfind('.')
	if k>=0:
		name=name[:k]+ext
	else:
		name=name+ext
	return self.parent.find_or_declare([name])
@feature('glib2')
def process_settings(self):
	enums_tgt_node=[]
	install_files=[]
	settings_schema_files=getattr(self,'settings_schema_files',[])
	if settings_schema_files and not self.env['GLIB_COMPILE_SCHEMAS']:
		raise Errors.WafError("Unable to process GSettings schemas - glib-compile-schemas was not found during configure")
	if hasattr(self,'settings_enum_files'):
		enums_task=self.create_task('glib_mkenums')
		source_list=self.settings_enum_files
		source_list=[self.path.find_resource(k)for k in source_list]
		enums_task.set_inputs(source_list)
		enums_task.env['GLIB_MKENUMS_SOURCE']=[k.abspath()for k in source_list]
		target=self.settings_enum_namespace+'.enums.xml'
		tgt_node=self.path.find_or_declare(target)
		enums_task.set_outputs(tgt_node)
		enums_task.env['GLIB_MKENUMS_TARGET']=tgt_node.abspath()
		enums_tgt_node=[tgt_node]
		install_files.append(tgt_node)
		options='--comments "<!-- @comment@ -->" --fhead "<schemalist>" --vhead "  <@type@ id=\\"%s.@EnumName@\\">" --vprod "    <value nick=\\"@valuenick@\\" value=\\"@valuenum@\\"/>" --vtail "  </@type@>" --ftail "</schemalist>" '%(self.settings_enum_namespace)
		enums_task.env['GLIB_MKENUMS_OPTIONS']=options
	for schema in settings_schema_files:
		schema_task=self.create_task('glib_validate_schema')
		schema_node=self.path.find_resource(schema)
		if not schema_node:
			raise Errors.WafError("Cannot find the schema file '%s'"%schema)
		install_files.append(schema_node)
		source_list=enums_tgt_node+[schema_node]
		schema_task.set_inputs(source_list)
		schema_task.env['GLIB_COMPILE_SCHEMAS_OPTIONS']=[("--schema-file="+k.abspath())for k in source_list]
		target_node=r_change_ext(schema_node,'.xml.valid')
		schema_task.set_outputs(target_node)
		schema_task.env['GLIB_VALIDATE_SCHEMA_OUTPUT']=target_node.abspath()
	def compile_schemas_callback(bld):
		if not bld.is_install:return
		Logs.pprint('YELLOW','Updating GSettings schema cache')
		command=Utils.subst_vars("${GLIB_COMPILE_SCHEMAS} ${GSETTINGSSCHEMADIR}",bld.env)
		ret=self.bld.exec_command(command)
	if self.bld.is_install:
		if not self.env['GSETTINGSSCHEMADIR']:
			raise Errors.WafError('GSETTINGSSCHEMADIR not defined (should have been set up automatically during configure)')
		if install_files:
			self.bld.install_files(self.env['GSETTINGSSCHEMADIR'],install_files)
			if not hasattr(self.bld,'_compile_schemas_registered'):
				self.bld.add_post_fun(compile_schemas_callback)
				self.bld._compile_schemas_registered=True
class glib_validate_schema(Task.Task):
	run_str='rm -f ${GLIB_VALIDATE_SCHEMA_OUTPUT} && ${GLIB_COMPILE_SCHEMAS} --dry-run ${GLIB_COMPILE_SCHEMAS_OPTIONS} && touch ${GLIB_VALIDATE_SCHEMA_OUTPUT}'
	color='PINK'
def configure(conf):
	conf.find_program('glib-genmarshal',var='GLIB_GENMARSHAL')
	conf.find_perl_program('glib-mkenums',var='GLIB_MKENUMS')
	conf.find_program('glib-compile-schemas',var='GLIB_COMPILE_SCHEMAS',mandatory=False)
	def getstr(varname):
		return getattr(Options.options,varname,getattr(conf.env,varname,''))
	gsettingsschemadir=getstr('GSETTINGSSCHEMADIR')
	if not gsettingsschemadir:
		datadir=getstr('DATADIR')
		if not datadir:
			prefix=conf.env['PREFIX']
			datadir=os.path.join(prefix,'share')
		gsettingsschemadir=os.path.join(datadir,'glib-2.0','schemas')
	conf.env['GSETTINGSSCHEMADIR']=gsettingsschemadir
def options(opt):
	opt.add_option('--gsettingsschemadir',help='GSettings schema location [Default: ${datadir}/glib-2.0/schemas]',default='',dest='GSETTINGSSCHEMADIR')

########NEW FILE########
__FILENAME__ = gnu_dirs
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import os
from waflib import Utils,Options,Context
_options=[x.split(', ')for x in'''
bindir, user executables, ${EXEC_PREFIX}/bin
sbindir, system admin executables, ${EXEC_PREFIX}/sbin
libexecdir, program executables, ${EXEC_PREFIX}/libexec
sysconfdir, read-only single-machine data, ${PREFIX}/etc
sharedstatedir, modifiable architecture-independent data, ${PREFIX}/com
localstatedir, modifiable single-machine data, ${PREFIX}/var
libdir, object code libraries, ${EXEC_PREFIX}/lib
includedir, C header files, ${PREFIX}/include
oldincludedir, C header files for non-gcc, /usr/include
datarootdir, read-only arch.-independent data root, ${PREFIX}/share
datadir, read-only architecture-independent data, ${DATAROOTDIR}
infodir, info documentation, ${DATAROOTDIR}/info
localedir, locale-dependent data, ${DATAROOTDIR}/locale
mandir, man documentation, ${DATAROOTDIR}/man
docdir, documentation root, ${DATAROOTDIR}/doc/${PACKAGE}
htmldir, html documentation, ${DOCDIR}
dvidir, dvi documentation, ${DOCDIR}
pdfdir, pdf documentation, ${DOCDIR}
psdir, ps documentation, ${DOCDIR}
'''.split('\n')if x]
def configure(conf):
	def get_param(varname,default):
		return getattr(Options.options,varname,'')or default
	env=conf.env
	env.LIBDIR=env.BINDIR=[]
	env.EXEC_PREFIX=get_param('EXEC_PREFIX',env.PREFIX)
	env.PACKAGE=getattr(Context.g_module,'APPNAME',None)or env.PACKAGE
	complete=False
	iter=0
	while not complete and iter<len(_options)+1:
		iter+=1
		complete=True
		for name,help,default in _options:
			name=name.upper()
			if not env[name]:
				try:
					env[name]=Utils.subst_vars(get_param(name,default).replace('/',os.sep),env)
				except TypeError:
					complete=False
	if not complete:
		lst=[name for name,_,_ in _options if not env[name.upper()]]
		raise conf.errors.WafError('Variable substitution failure %r'%lst)
def options(opt):
	inst_dir=opt.add_option_group('Installation directories','By default, "waf install" will put the files in\
 "/usr/local/bin", "/usr/local/lib" etc. An installation prefix other\
 than "/usr/local" can be given using "--prefix", for example "--prefix=$HOME"')
	for k in('--prefix','--destdir'):
		option=opt.parser.get_option(k)
		if option:
			opt.parser.remove_option(k)
			inst_dir.add_option(option)
	inst_dir.add_option('--exec-prefix',help='installation prefix [Default: ${PREFIX}]',default='',dest='EXEC_PREFIX')
	dirs_options=opt.add_option_group('Pre-defined installation directories','')
	for name,help,default in _options:
		option_name='--'+name
		str_default=default
		str_help='%s [Default: %s]'%(help,str_default)
		dirs_options.add_option(option_name,help=str_help,default='',dest=name.upper())

########NEW FILE########
__FILENAME__ = gxx
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

from waflib.Tools import ccroot,ar
from waflib.Configure import conf
@conf
def find_gxx(conf):
	cxx=conf.find_program(['g++','c++'],var='CXX')
	cxx=conf.cmd_to_list(cxx)
	conf.get_cc_version(cxx,gcc=True)
	conf.env.CXX_NAME='gcc'
	conf.env.CXX=cxx
@conf
def gxx_common_flags(conf):
	v=conf.env
	v['CXX_SRC_F']=[]
	v['CXX_TGT_F']=['-c','-o']
	if not v['LINK_CXX']:v['LINK_CXX']=v['CXX']
	v['CXXLNK_SRC_F']=[]
	v['CXXLNK_TGT_F']=['-o']
	v['CPPPATH_ST']='-I%s'
	v['DEFINES_ST']='-D%s'
	v['LIB_ST']='-l%s'
	v['LIBPATH_ST']='-L%s'
	v['STLIB_ST']='-l%s'
	v['STLIBPATH_ST']='-L%s'
	v['RPATH_ST']='-Wl,-rpath,%s'
	v['SONAME_ST']='-Wl,-h,%s'
	v['SHLIB_MARKER']='-Wl,-Bdynamic'
	v['STLIB_MARKER']='-Wl,-Bstatic'
	v['cxxprogram_PATTERN']='%s'
	v['CXXFLAGS_cxxshlib']=['-fPIC']
	v['LINKFLAGS_cxxshlib']=['-shared']
	v['cxxshlib_PATTERN']='lib%s.so'
	v['LINKFLAGS_cxxstlib']=['-Wl,-Bstatic']
	v['cxxstlib_PATTERN']='lib%s.a'
	v['LINKFLAGS_MACBUNDLE']=['-bundle','-undefined','dynamic_lookup']
	v['CXXFLAGS_MACBUNDLE']=['-fPIC']
	v['macbundle_PATTERN']='%s.bundle'
@conf
def gxx_modifier_win32(conf):
	v=conf.env
	v['cxxprogram_PATTERN']='%s.exe'
	v['cxxshlib_PATTERN']='%s.dll'
	v['implib_PATTERN']='lib%s.dll.a'
	v['IMPLIB_ST']='-Wl,--out-implib,%s'
	v['CXXFLAGS_cxxshlib']=[]
	v.append_value('LINKFLAGS',['-Wl,--enable-auto-import'])
@conf
def gxx_modifier_cygwin(conf):
	gxx_modifier_win32(conf)
	v=conf.env
	v['cxxshlib_PATTERN']='cyg%s.dll'
	v.append_value('LINKFLAGS_cxxshlib',['-Wl,--enable-auto-image-base'])
	v['CXXFLAGS_cxxshlib']=[]
@conf
def gxx_modifier_darwin(conf):
	v=conf.env
	v['CXXFLAGS_cxxshlib']=['-fPIC']
	v['LINKFLAGS_cxxshlib']=['-dynamiclib','-Wl,-compatibility_version,1','-Wl,-current_version,1']
	v['cxxshlib_PATTERN']='lib%s.dylib'
	v['FRAMEWORKPATH_ST']='-F%s'
	v['FRAMEWORK_ST']=['-framework']
	v['ARCH_ST']=['-arch']
	v['LINKFLAGS_cxxstlib']=[]
	v['SHLIB_MARKER']=[]
	v['STLIB_MARKER']=[]
	v['SONAME_ST']=[]
@conf
def gxx_modifier_aix(conf):
	v=conf.env
	v['LINKFLAGS_cxxprogram']=['-Wl,-brtl']
	v['LINKFLAGS_cxxshlib']=['-shared','-Wl,-brtl,-bexpfull']
	v['SHLIB_MARKER']=[]
@conf
def gxx_modifier_hpux(conf):
	v=conf.env
	v['SHLIB_MARKER']=[]
	v['STLIB_MARKER']='-Bstatic'
	v['CFLAGS_cxxshlib']=['-fPIC','-DPIC']
	v['cxxshlib_PATTERN']='lib%s.sl'
@conf
def gxx_modifier_openbsd(conf):
	conf.env.SONAME_ST=[]
@conf
def gxx_modifier_platform(conf):
	gxx_modifier_func=getattr(conf,'gxx_modifier_'+conf.env.DEST_OS,None)
	if gxx_modifier_func:
		gxx_modifier_func()
def configure(conf):
	conf.find_gxx()
	conf.find_ar()
	conf.gxx_common_flags()
	conf.gxx_modifier_platform()
	conf.cxx_load_tools()
	conf.cxx_add_flags()
	conf.link_add_flags()

########NEW FILE########
__FILENAME__ = icc
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import os,sys
from waflib.Tools import ccroot,ar,gcc
from waflib.Configure import conf
@conf
def find_icc(conf):
	if sys.platform=='cygwin':
		conf.fatal('The Intel compiler does not work on Cygwin')
	v=conf.env
	cc=None
	if v['CC']:cc=v['CC']
	elif'CC'in conf.environ:cc=conf.environ['CC']
	if not cc:cc=conf.find_program('icc',var='CC')
	if not cc:cc=conf.find_program('ICL',var='CC')
	if not cc:conf.fatal('Intel C Compiler (icc) was not found')
	cc=conf.cmd_to_list(cc)
	conf.get_cc_version(cc,icc=True)
	v['CC']=cc
	v['CC_NAME']='icc'
def configure(conf):
	conf.find_icc()
	conf.find_ar()
	conf.gcc_common_flags()
	conf.gcc_modifier_platform()
	conf.cc_load_tools()
	conf.cc_add_flags()
	conf.link_add_flags()

########NEW FILE########
__FILENAME__ = icpc
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import os,sys
from waflib.Tools import ccroot,ar,gxx
from waflib.Configure import conf
@conf
def find_icpc(conf):
	if sys.platform=='cygwin':
		conf.fatal('The Intel compiler does not work on Cygwin')
	v=conf.env
	cxx=None
	if v['CXX']:cxx=v['CXX']
	elif'CXX'in conf.environ:cxx=conf.environ['CXX']
	if not cxx:cxx=conf.find_program('icpc',var='CXX')
	if not cxx:conf.fatal('Intel C++ Compiler (icpc) was not found')
	cxx=conf.cmd_to_list(cxx)
	conf.get_cc_version(cxx,icc=True)
	v['CXX']=cxx
	v['CXX_NAME']='icc'
def configure(conf):
	conf.find_icpc()
	conf.find_ar()
	conf.gxx_common_flags()
	conf.gxx_modifier_platform()
	conf.cxx_load_tools()
	conf.cxx_add_flags()
	conf.link_add_flags()

########NEW FILE########
__FILENAME__ = ifort
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import re
from waflib import Utils
from waflib.Tools import fc,fc_config,fc_scan,ar
from waflib.Configure import conf
@conf
def find_ifort(conf):
	fc=conf.find_program('ifort',var='FC')
	fc=conf.cmd_to_list(fc)
	conf.get_ifort_version(fc)
	conf.env.FC_NAME='IFORT'
@conf
def ifort_modifier_cygwin(conf):
	raise NotImplementedError("Ifort on cygwin not yet implemented")
@conf
def ifort_modifier_win32(conf):
	fc_config.fortran_modifier_win32(conf)
@conf
def ifort_modifier_darwin(conf):
	fc_config.fortran_modifier_darwin(conf)
@conf
def ifort_modifier_platform(conf):
	dest_os=conf.env['DEST_OS']or Utils.unversioned_sys_platform()
	ifort_modifier_func=getattr(conf,'ifort_modifier_'+dest_os,None)
	if ifort_modifier_func:
		ifort_modifier_func()
@conf
def get_ifort_version(conf,fc):
	version_re=re.compile(r"ifort\s*\(IFORT\)\s*(?P<major>\d*)\.(?P<minor>\d*)",re.I).search
	cmd=fc+['--version']
	out,err=fc_config.getoutput(conf,cmd,stdin=False)
	if out:
		match=version_re(out)
	else:
		match=version_re(err)
	if not match:
		conf.fatal('cannot determine ifort version.')
	k=match.groupdict()
	conf.env['FC_VERSION']=(k['major'],k['minor'])
def configure(conf):
	conf.find_ifort()
	conf.find_program('xiar',var='AR')
	conf.env.ARFLAGS='rcs'
	conf.fc_flags()
	conf.fc_add_flags()
	conf.ifort_modifier_platform()

########NEW FILE########
__FILENAME__ = intltool
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import os,re
from waflib import Configure,TaskGen,Task,Utils,Runner,Options,Build,Logs
import waflib.Tools.ccroot
from waflib.TaskGen import feature,before_method
from waflib.Logs import error
@before_method('process_source')
@feature('intltool_in')
def apply_intltool_in_f(self):
	try:self.meths.remove('process_source')
	except ValueError:pass
	if not self.env.LOCALEDIR:
		self.env.LOCALEDIR=self.env.PREFIX+'/share/locale'
	for i in self.to_list(self.source):
		node=self.path.find_resource(i)
		podir=getattr(self,'podir','po')
		podirnode=self.path.find_dir(podir)
		if not podirnode:
			error("could not find the podir %r"%podir)
			continue
		cache=getattr(self,'intlcache','.intlcache')
		self.env['INTLCACHE']=os.path.join(self.path.bldpath(),podir,cache)
		self.env['INTLPODIR']=podirnode.bldpath()
		self.env['INTLFLAGS']=getattr(self,'flags',['-q','-u','-c'])
		task=self.create_task('intltool',node,node.change_ext(''))
		inst=getattr(self,'install_path','${LOCALEDIR}')
		if inst:
			self.bld.install_files(inst,task.outputs)
@feature('intltool_po')
def apply_intltool_po(self):
	try:self.meths.remove('process_source')
	except ValueError:pass
	if not self.env.LOCALEDIR:
		self.env.LOCALEDIR=self.env.PREFIX+'/share/locale'
	appname=getattr(self,'appname','set_your_app_name')
	podir=getattr(self,'podir','')
	inst=getattr(self,'install_path','${LOCALEDIR}')
	linguas=self.path.find_node(os.path.join(podir,'LINGUAS'))
	if linguas:
		file=open(linguas.abspath())
		langs=[]
		for line in file.readlines():
			if not line.startswith('#'):
				langs+=line.split()
		file.close()
		re_linguas=re.compile('[-a-zA-Z_@.]+')
		for lang in langs:
			if re_linguas.match(lang):
				node=self.path.find_resource(os.path.join(podir,re_linguas.match(lang).group()+'.po'))
				task=self.create_task('po',node,node.change_ext('.mo'))
				if inst:
					filename=task.outputs[0].name
					(langname,ext)=os.path.splitext(filename)
					inst_file=inst+os.sep+langname+os.sep+'LC_MESSAGES'+os.sep+appname+'.mo'
					self.bld.install_as(inst_file,task.outputs[0],chmod=getattr(self,'chmod',Utils.O644),env=task.env)
	else:
		Logs.pprint('RED',"Error no LINGUAS file found in po directory")
class po(Task.Task):
	run_str='${MSGFMT} -o ${TGT} ${SRC}'
	color='BLUE'
class intltool(Task.Task):
	run_str='${INTLTOOL} ${INTLFLAGS} ${INTLCACHE} ${INTLPODIR} ${SRC} ${TGT}'
	color='BLUE'
def configure(conf):
	conf.find_program('msgfmt',var='MSGFMT')
	conf.find_perl_program('intltool-merge',var='INTLTOOL')
	prefix=conf.env.PREFIX
	datadir=conf.env.DATADIR
	if not datadir:
		datadir=os.path.join(prefix,'share')
	conf.define('LOCALEDIR',os.path.join(datadir,'locale').replace('\\','\\\\'))
	conf.define('DATADIR',datadir.replace('\\','\\\\'))
	if conf.env.CC or conf.env.CXX:
		conf.check(header_name='locale.h')

########NEW FILE########
__FILENAME__ = irixcc
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import os
from waflib import Utils
from waflib.Tools import ccroot,ar
from waflib.Configure import conf
@conf
def find_irixcc(conf):
	v=conf.env
	cc=None
	if v['CC']:cc=v['CC']
	elif'CC'in conf.environ:cc=conf.environ['CC']
	if not cc:cc=conf.find_program('cc',var='CC')
	if not cc:conf.fatal('irixcc was not found')
	cc=conf.cmd_to_list(cc)
	try:
		conf.cmd_and_log(cc+['-version'])
	except Exception:
		conf.fatal('%r -version could not be executed'%cc)
	v['CC']=cc
	v['CC_NAME']='irix'
@conf
def irixcc_common_flags(conf):
	v=conf.env
	v['CC_SRC_F']=''
	v['CC_TGT_F']=['-c','-o']
	v['CPPPATH_ST']='-I%s'
	v['DEFINES_ST']='-D%s'
	if not v['LINK_CC']:v['LINK_CC']=v['CC']
	v['CCLNK_SRC_F']=''
	v['CCLNK_TGT_F']=['-o']
	v['LIB_ST']='-l%s'
	v['LIBPATH_ST']='-L%s'
	v['STLIB_ST']='-l%s'
	v['STLIBPATH_ST']='-L%s'
	v['cprogram_PATTERN']='%s'
	v['cshlib_PATTERN']='lib%s.so'
	v['cstlib_PATTERN']='lib%s.a'
def configure(conf):
	conf.find_irixcc()
	conf.find_cpp()
	conf.find_ar()
	conf.irixcc_common_flags()
	conf.cc_load_tools()
	conf.cc_add_flags()
	conf.link_add_flags()

########NEW FILE########
__FILENAME__ = javaw
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import os,re,tempfile,shutil
from waflib import TaskGen,Task,Utils,Options,Build,Errors,Node,Logs
from waflib.Configure import conf
from waflib.TaskGen import feature,before_method,after_method
from waflib.Tools import ccroot
ccroot.USELIB_VARS['javac']=set(['CLASSPATH','JAVACFLAGS'])
SOURCE_RE='**/*.java'
JAR_RE='**/*'
class_check_source='''
public class Test {
	public static void main(String[] argv) {
		Class lib;
		if (argv.length < 1) {
			System.err.println("Missing argument");
			System.exit(77);
		}
		try {
			lib = Class.forName(argv[0]);
		} catch (ClassNotFoundException e) {
			System.err.println("ClassNotFoundException");
			System.exit(1);
		}
		lib = null;
		System.exit(0);
	}
}
'''
@feature('javac')
@before_method('process_source')
def apply_java(self):
	Utils.def_attrs(self,jarname='',classpath='',sourcepath='.',srcdir='.',jar_mf_attributes={},jar_mf_classpath=[])
	nodes_lst=[]
	outdir=getattr(self,'outdir',None)
	if outdir:
		if not isinstance(outdir,Node.Node):
			outdir=self.path.get_bld().make_node(self.outdir)
	else:
		outdir=self.path.get_bld()
	outdir.mkdir()
	self.outdir=outdir
	self.env['OUTDIR']=outdir.abspath()
	self.javac_task=tsk=self.create_task('javac')
	tmp=[]
	srcdir=getattr(self,'srcdir','')
	if isinstance(srcdir,Node.Node):
		srcdir=[srcdir]
	for x in Utils.to_list(srcdir):
		if isinstance(x,Node.Node):
			y=x
		else:
			y=self.path.find_dir(x)
			if not y:
				self.bld.fatal('Could not find the folder %s from %s'%(x,self.path))
		tmp.append(y)
	tsk.srcdir=tmp
	if getattr(self,'compat',None):
		tsk.env.append_value('JAVACFLAGS',['-source',self.compat])
	if hasattr(self,'sourcepath'):
		fold=[isinstance(x,Node.Node)and x or self.path.find_dir(x)for x in self.to_list(self.sourcepath)]
		names=os.pathsep.join([x.srcpath()for x in fold])
	else:
		names=[x.srcpath()for x in tsk.srcdir]
	if names:
		tsk.env.append_value('JAVACFLAGS',['-sourcepath',names])
@feature('javac')
@after_method('apply_java')
def use_javac_files(self):
	lst=[]
	self.uselib=self.to_list(getattr(self,'uselib',[]))
	names=self.to_list(getattr(self,'use',[]))
	get=self.bld.get_tgen_by_name
	for x in names:
		try:
			y=get(x)
		except Exception:
			self.uselib.append(x)
		else:
			y.post()
			lst.append(y.jar_task.outputs[0].abspath())
			self.javac_task.set_run_after(y.jar_task)
	if lst:
		self.env.append_value('CLASSPATH',lst)
@feature('javac')
@after_method('apply_java','propagate_uselib_vars','use_javac_files')
def set_classpath(self):
	self.env.append_value('CLASSPATH',getattr(self,'classpath',[]))
	for x in self.tasks:
		x.env.CLASSPATH=os.pathsep.join(self.env.CLASSPATH)+os.pathsep
@feature('jar')
@after_method('apply_java','use_javac_files')
@before_method('process_source')
def jar_files(self):
	destfile=getattr(self,'destfile','test.jar')
	jaropts=getattr(self,'jaropts',[])
	manifest=getattr(self,'manifest',None)
	basedir=getattr(self,'basedir',None)
	if basedir:
		if not isinstance(self.basedir,Node.Node):
			basedir=self.path.get_bld().make_node(basedir)
	else:
		basedir=self.path.get_bld()
	if not basedir:
		self.bld.fatal('Could not find the basedir %r for %r'%(self.basedir,self))
	self.jar_task=tsk=self.create_task('jar_create')
	if manifest:
		jarcreate=getattr(self,'jarcreate','cfm')
		node=self.path.find_node(manifest)
		tsk.dep_nodes.append(node)
		jaropts.insert(0,node.abspath())
	else:
		jarcreate=getattr(self,'jarcreate','cf')
	if not isinstance(destfile,Node.Node):
		destfile=self.path.find_or_declare(destfile)
	if not destfile:
		self.bld.fatal('invalid destfile %r for %r'%(destfile,self))
	tsk.set_outputs(destfile)
	tsk.basedir=basedir
	jaropts.append('-C')
	jaropts.append(basedir.bldpath())
	jaropts.append('.')
	tsk.env['JAROPTS']=jaropts
	tsk.env['JARCREATE']=jarcreate
	if getattr(self,'javac_task',None):
		tsk.set_run_after(self.javac_task)
@feature('jar')
@after_method('jar_files')
def use_jar_files(self):
	lst=[]
	self.uselib=self.to_list(getattr(self,'uselib',[]))
	names=self.to_list(getattr(self,'use',[]))
	get=self.bld.get_tgen_by_name
	for x in names:
		try:
			y=get(x)
		except Exception:
			self.uselib.append(x)
		else:
			y.post()
			self.jar_task.run_after.update(y.tasks)
class jar_create(Task.Task):
	color='GREEN'
	run_str='${JAR} ${JARCREATE} ${TGT} ${JAROPTS}'
	def runnable_status(self):
		for t in self.run_after:
			if not t.hasrun:
				return Task.ASK_LATER
		if not self.inputs:
			global JAR_RE
			try:
				self.inputs=[x for x in self.basedir.ant_glob(JAR_RE,remove=False)if id(x)!=id(self.outputs[0])]
			except Exception:
				raise Errors.WafError('Could not find the basedir %r for %r'%(self.basedir,self))
		return super(jar_create,self).runnable_status()
class javac(Task.Task):
	color='BLUE'
	nocache=True
	vars=['CLASSPATH','JAVACFLAGS','JAVAC','OUTDIR']
	def runnable_status(self):
		for t in self.run_after:
			if not t.hasrun:
				return Task.ASK_LATER
		if not self.inputs:
			global SOURCE_RE
			self.inputs=[]
			for x in self.srcdir:
				self.inputs.extend(x.ant_glob(SOURCE_RE,remove=False))
		return super(javac,self).runnable_status()
	def run(self):
		env=self.env
		gen=self.generator
		bld=gen.bld
		wd=bld.bldnode.abspath()
		def to_list(xx):
			if isinstance(xx,str):return[xx]
			return xx
		cmd=[]
		cmd.extend(to_list(env['JAVAC']))
		cmd.extend(['-classpath'])
		cmd.extend(to_list(env['CLASSPATH']))
		cmd.extend(['-d'])
		cmd.extend(to_list(env['OUTDIR']))
		cmd.extend(to_list(env['JAVACFLAGS']))
		files=[a.path_from(bld.bldnode)for a in self.inputs]
		tmp=None
		try:
			if len(str(files))+len(str(cmd))>8192:
				(fd,tmp)=tempfile.mkstemp(dir=bld.bldnode.abspath())
				try:
					os.write(fd,'\n'.join(files))
				finally:
					if tmp:
						os.close(fd)
				if Logs.verbose:
					Logs.debug('runner: %r'%(cmd+files))
				cmd.append('@'+tmp)
			else:
				cmd+=files
			ret=self.exec_command(cmd,cwd=wd,env=env.env or None)
		finally:
			if tmp:
				os.remove(tmp)
		return ret
	def post_run(self):
		for n in self.generator.outdir.ant_glob('**/*.class'):
			n.sig=Utils.h_file(n.abspath())
		self.generator.bld.task_sigs[self.uid()]=self.cache_sig
@feature('javadoc')
@after_method('process_rule')
def create_javadoc(self):
	tsk=self.create_task('javadoc')
	tsk.classpath=getattr(self,'classpath',[])
	self.javadoc_package=Utils.to_list(self.javadoc_package)
	if not isinstance(self.javadoc_output,Node.Node):
		self.javadoc_output=self.bld.path.find_or_declare(self.javadoc_output)
class javadoc(Task.Task):
	color='BLUE'
	def __str__(self):
		return'%s: %s -> %s\n'%(self.__class__.__name__,self.generator.srcdir,self.generator.javadoc_output)
	def run(self):
		env=self.env
		bld=self.generator.bld
		wd=bld.bldnode.abspath()
		srcpath=self.generator.path.abspath()+os.sep+self.generator.srcdir
		srcpath+=os.pathsep
		srcpath+=self.generator.path.get_bld().abspath()+os.sep+self.generator.srcdir
		classpath=env.CLASSPATH
		classpath+=os.pathsep
		classpath+=os.pathsep.join(self.classpath)
		classpath="".join(classpath)
		self.last_cmd=lst=[]
		lst.extend(Utils.to_list(env['JAVADOC']))
		lst.extend(['-d',self.generator.javadoc_output.abspath()])
		lst.extend(['-sourcepath',srcpath])
		lst.extend(['-classpath',classpath])
		lst.extend(['-subpackages'])
		lst.extend(self.generator.javadoc_package)
		lst=[x for x in lst if x]
		self.generator.bld.cmd_and_log(lst,cwd=wd,env=env.env or None,quiet=0)
	def post_run(self):
		nodes=self.generator.javadoc_output.ant_glob('**')
		for x in nodes:
			x.sig=Utils.h_file(x.abspath())
		self.generator.bld.task_sigs[self.uid()]=self.cache_sig
def configure(self):
	java_path=self.environ['PATH'].split(os.pathsep)
	v=self.env
	if'JAVA_HOME'in self.environ:
		java_path=[os.path.join(self.environ['JAVA_HOME'],'bin')]+java_path
		self.env['JAVA_HOME']=[self.environ['JAVA_HOME']]
	for x in'javac java jar javadoc'.split():
		self.find_program(x,var=x.upper(),path_list=java_path)
		self.env[x.upper()]=self.cmd_to_list(self.env[x.upper()])
	if'CLASSPATH'in self.environ:
		v['CLASSPATH']=self.environ['CLASSPATH']
	if not v['JAR']:self.fatal('jar is required for making java packages')
	if not v['JAVAC']:self.fatal('javac is required for compiling java classes')
	v['JARCREATE']='cf'
	v['JAVACFLAGS']=[]
@conf
def check_java_class(self,classname,with_classpath=None):
	javatestdir='.waf-javatest'
	classpath=javatestdir
	if self.env['CLASSPATH']:
		classpath+=os.pathsep+self.env['CLASSPATH']
	if isinstance(with_classpath,str):
		classpath+=os.pathsep+with_classpath
	shutil.rmtree(javatestdir,True)
	os.mkdir(javatestdir)
	Utils.writef(os.path.join(javatestdir,'Test.java'),class_check_source)
	self.exec_command(self.env['JAVAC']+[os.path.join(javatestdir,'Test.java')],shell=False)
	cmd=self.env['JAVA']+['-cp',classpath,'Test',classname]
	self.to_log("%s\n"%str(cmd))
	found=self.exec_command(cmd,shell=False)
	self.msg('Checking for java class %s'%classname,not found)
	shutil.rmtree(javatestdir,True)
	return found
@conf
def check_jni_headers(conf):
	if not conf.env.CC_NAME and not conf.env.CXX_NAME:
		conf.fatal('load a compiler first (gcc, g++, ..)')
	if not conf.env.JAVA_HOME:
		conf.fatal('set JAVA_HOME in the system environment')
	javaHome=conf.env['JAVA_HOME'][0]
	dir=conf.root.find_dir(conf.env.JAVA_HOME[0]+'/include')
	if dir is None:
		dir=conf.root.find_dir(conf.env.JAVA_HOME[0]+'/../Headers')
	if dir is None:
		conf.fatal('JAVA_HOME does not seem to be set properly')
	f=dir.ant_glob('**/(jni|jni_md).h')
	incDirs=[x.parent.abspath()for x in f]
	dir=conf.root.find_dir(conf.env.JAVA_HOME[0])
	f=dir.ant_glob('**/*jvm.(so|dll|dylib)')
	libDirs=[x.parent.abspath()for x in f]or[javaHome]
	f=dir.ant_glob('**/*jvm.(lib)')
	if f:
		libDirs=[[x,y.parent.abspath()]for x in libDirs for y in f]
	for d in libDirs:
		try:
			conf.check(header_name='jni.h',define_name='HAVE_JNI_H',lib='jvm',libpath=d,includes=incDirs,uselib_store='JAVA',uselib='JAVA')
		except Exception:
			pass
		else:
			break
	else:
		conf.fatal('could not find lib jvm in %r (see config.log)'%libDirs)

########NEW FILE########
__FILENAME__ = kde4
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import os,sys,re
from waflib import Options,TaskGen,Task,Utils
from waflib.TaskGen import feature,after_method
@feature('msgfmt')
def apply_msgfmt(self):
	for lang in self.to_list(self.langs):
		node=self.path.find_resource(lang+'.po')
		task=self.create_task('msgfmt',node,node.change_ext('.mo'))
		langname=lang.split('/')
		langname=langname[-1]
		inst=getattr(self,'install_path','${KDE4_LOCALE_INSTALL_DIR}')
		self.bld.install_as(inst+os.sep+langname+os.sep+'LC_MESSAGES'+os.sep+getattr(self,'appname','set_your_appname')+'.mo',task.outputs[0],chmod=getattr(self,'chmod',Utils.O644))
class msgfmt(Task.Task):
	color='BLUE'
	run_str='${MSGFMT} ${SRC} -o ${TGT}'
def configure(self):
	kdeconfig=self.find_program('kde4-config')
	prefix=self.cmd_and_log('%s --prefix'%kdeconfig).strip()
	fname='%s/share/apps/cmake/modules/KDELibsDependencies.cmake'%prefix
	try:os.stat(fname)
	except OSError:
		fname='%s/share/kde4/apps/cmake/modules/KDELibsDependencies.cmake'%prefix
		try:os.stat(fname)
		except OSError:self.fatal('could not open %s'%fname)
	try:
		txt=Utils.readf(fname)
	except(OSError,IOError):
		self.fatal('could not read %s'%fname)
	txt=txt.replace('\\\n','\n')
	fu=re.compile('#(.*)\n')
	txt=fu.sub('',txt)
	setregexp=re.compile('([sS][eE][tT]\s*\()\s*([^\s]+)\s+\"([^"]+)\"\)')
	found=setregexp.findall(txt)
	for(_,key,val)in found:
		self.env[key]=val
	self.env['LIB_KDECORE']=['kdecore']
	self.env['LIB_KDEUI']=['kdeui']
	self.env['LIB_KIO']=['kio']
	self.env['LIB_KHTML']=['khtml']
	self.env['LIB_KPARTS']=['kparts']
	self.env['LIBPATH_KDECORE']=[os.path.join(self.env.KDE4_LIB_INSTALL_DIR,'kde4','devel'),self.env.KDE4_LIB_INSTALL_DIR]
	self.env['INCLUDES_KDECORE']=[self.env['KDE4_INCLUDE_INSTALL_DIR']]
	self.env.append_value('INCLUDES_KDECORE',[self.env['KDE4_INCLUDE_INSTALL_DIR']+os.sep+'KDE'])
	self.find_program('msgfmt',var='MSGFMT')

########NEW FILE########
__FILENAME__ = ldc2
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import sys
from waflib.Tools import ar,d
from waflib.Configure import conf
@conf
def find_ldc2(conf):
	conf.find_program(['ldc2'],var='D')
	out=conf.cmd_and_log([conf.env.D,'-version'])
	if out.find("based on DMD v2.")==-1:
		conf.fatal("detected compiler is not ldc2")
@conf
def common_flags_ldc2(conf):
	v=conf.env
	v['D_SRC_F']=['-c']
	v['D_TGT_F']='-of%s'
	v['D_LINKER']=v['D']
	v['DLNK_SRC_F']=''
	v['DLNK_TGT_F']='-of%s'
	v['DINC_ST']='-I%s'
	v['DSHLIB_MARKER']=v['DSTLIB_MARKER']=''
	v['DSTLIB_ST']=v['DSHLIB_ST']='-L-l%s'
	v['DSTLIBPATH_ST']=v['DLIBPATH_ST']='-L-L%s'
	v['LINKFLAGS_dshlib']=['-L-shared']
	v['DHEADER_ext']='.di'
	v['DFLAGS_d_with_header']=['-H','-Hf']
	v['D_HDR_F']='%s'
	v['LINKFLAGS']=[]
	v['DFLAGS_dshlib']=['-relocation-model=pic']
def configure(conf):
	conf.find_ldc2()
	conf.load('ar')
	conf.load('d')
	conf.common_flags_ldc2()
	conf.d_platform_flags()

########NEW FILE########
__FILENAME__ = lua
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

from waflib.TaskGen import extension
from waflib import Task,Utils
@extension('.lua')
def add_lua(self,node):
	tsk=self.create_task('luac',node,node.change_ext('.luac'))
	inst_to=getattr(self,'install_path',self.env.LUADIR and'${LUADIR}'or None)
	if inst_to:
		self.bld.install_files(inst_to,tsk.outputs)
	return tsk
class luac(Task.Task):
	run_str='${LUAC} -s -o ${TGT} ${SRC}'
	color='PINK'
def configure(conf):
	conf.find_program('luac',var='LUAC')

########NEW FILE########
__FILENAME__ = msvc
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import os,sys,re,tempfile
from waflib import Utils,Task,Logs,Options,Errors
from waflib.Logs import debug,warn
from waflib.TaskGen import after_method,feature
from waflib.Configure import conf
from waflib.Tools import ccroot,c,cxx,ar,winres
g_msvc_systemlibs='''
aclui activeds ad1 adptif adsiid advapi32 asycfilt authz bhsupp bits bufferoverflowu cabinet
cap certadm certidl ciuuid clusapi comctl32 comdlg32 comsupp comsuppd comsuppw comsuppwd comsvcs
credui crypt32 cryptnet cryptui d3d8thk daouuid dbgeng dbghelp dciman32 ddao35 ddao35d
ddao35u ddao35ud delayimp dhcpcsvc dhcpsapi dlcapi dnsapi dsprop dsuiext dtchelp
faultrep fcachdll fci fdi framedyd framedyn gdi32 gdiplus glauxglu32 gpedit gpmuuid
gtrts32w gtrtst32hlink htmlhelp httpapi icm32 icmui imagehlp imm32 iphlpapi iprop
kernel32 ksguid ksproxy ksuser libcmt libcmtd libcpmt libcpmtd loadperf lz32 mapi
mapi32 mgmtapi minidump mmc mobsync mpr mprapi mqoa mqrt msacm32 mscms mscoree
msdasc msimg32 msrating mstask msvcmrt msvcurt msvcurtd mswsock msxml2 mtx mtxdm
netapi32 nmapinmsupp npptools ntdsapi ntdsbcli ntmsapi ntquery odbc32 odbcbcp
odbccp32 oldnames ole32 oleacc oleaut32 oledb oledlgolepro32 opends60 opengl32
osptk parser pdh penter pgobootrun pgort powrprof psapi ptrustm ptrustmd ptrustu
ptrustud qosname rasapi32 rasdlg rassapi resutils riched20 rpcndr rpcns4 rpcrt4 rtm
rtutils runtmchk scarddlg scrnsave scrnsavw secur32 sensapi setupapi sfc shell32
shfolder shlwapi sisbkup snmpapi sporder srclient sti strsafe svcguid tapi32 thunk32
traffic unicows url urlmon user32 userenv usp10 uuid uxtheme vcomp vcompd vdmdbg
version vfw32 wbemuuid  webpost wiaguid wininet winmm winscard winspool winstrm
wintrust wldap32 wmiutils wow32 ws2_32 wsnmp32 wsock32 wst wtsapi32 xaswitch xolehlp
'''.split()
all_msvc_platforms=[('x64','amd64'),('x86','x86'),('ia64','ia64'),('x86_amd64','amd64'),('x86_ia64','ia64'),('x86_arm','arm')]
all_wince_platforms=[('armv4','arm'),('armv4i','arm'),('mipsii','mips'),('mipsii_fp','mips'),('mipsiv','mips'),('mipsiv_fp','mips'),('sh4','sh'),('x86','cex86')]
all_icl_platforms=[('intel64','amd64'),('em64t','amd64'),('ia32','x86'),('Itanium','ia64')]
def options(opt):
	opt.add_option('--msvc_version',type='string',help='msvc version, eg: "msvc 10.0,msvc 9.0"',default='')
	opt.add_option('--msvc_targets',type='string',help='msvc targets, eg: "x64,arm"',default='')
def setup_msvc(conf,versions,arch=False):
	platforms=getattr(Options.options,'msvc_targets','').split(',')
	if platforms==['']:
		platforms=Utils.to_list(conf.env['MSVC_TARGETS'])or[i for i,j in all_msvc_platforms+all_icl_platforms+all_wince_platforms]
	desired_versions=getattr(Options.options,'msvc_version','').split(',')
	if desired_versions==['']:
		desired_versions=conf.env['MSVC_VERSIONS']or[v for v,_ in versions][::-1]
	versiondict=dict(versions)
	for version in desired_versions:
		try:
			targets=dict(versiondict[version])
			for target in platforms:
				try:
					arch,(p1,p2,p3)=targets[target]
					compiler,revision=version.rsplit(' ',1)
					if arch:
						return compiler,revision,p1,p2,p3,arch
					else:
						return compiler,revision,p1,p2,p3
				except KeyError:continue
		except KeyError:continue
	conf.fatal('msvc: Impossible to find a valid architecture for building (in setup_msvc)')
@conf
def get_msvc_version(conf,compiler,version,target,vcvars):
	debug('msvc: get_msvc_version: %r %r %r',compiler,version,target)
	batfile=conf.bldnode.make_node('waf-print-msvc.bat')
	batfile.write("""@echo off
set INCLUDE=
set LIB=
call "%s" %s
echo PATH=%%PATH%%
echo INCLUDE=%%INCLUDE%%
echo LIB=%%LIB%%;%%LIBPATH%%
"""%(vcvars,target))
	sout=conf.cmd_and_log(['cmd','/E:on','/V:on','/C',batfile.abspath()])
	lines=sout.splitlines()
	if not lines[0]:
		lines.pop(0)
	MSVC_PATH=MSVC_INCDIR=MSVC_LIBDIR=None
	for line in lines:
		if line.startswith('PATH='):
			path=line[5:]
			MSVC_PATH=path.split(';')
		elif line.startswith('INCLUDE='):
			MSVC_INCDIR=[i for i in line[8:].split(';')if i]
		elif line.startswith('LIB='):
			MSVC_LIBDIR=[i for i in line[4:].split(';')if i]
	if None in(MSVC_PATH,MSVC_INCDIR,MSVC_LIBDIR):
		conf.fatal('msvc: Could not find a valid architecture for building (get_msvc_version_3)')
	env=dict(os.environ)
	env.update(PATH=path)
	compiler_name,linker_name,lib_name=_get_prog_names(conf,compiler)
	cxx=conf.find_program(compiler_name,path_list=MSVC_PATH)
	cxx=conf.cmd_to_list(cxx)
	if'CL'in env:
		del(env['CL'])
	try:
		try:
			conf.cmd_and_log(cxx+['/help'],env=env)
		except Exception ,e:
			debug('msvc: get_msvc_version: %r %r %r -> failure'%(compiler,version,target))
			debug(str(e))
			conf.fatal('msvc: cannot run the compiler (in get_msvc_version)')
		else:
			debug('msvc: get_msvc_version: %r %r %r -> OK',compiler,version,target)
	finally:
		conf.env[compiler_name]=''
	return(MSVC_PATH,MSVC_INCDIR,MSVC_LIBDIR)
@conf
def gather_wsdk_versions(conf,versions):
	version_pattern=re.compile('^v..?.?\...?.?')
	try:
		all_versions=Utils.winreg.OpenKey(Utils.winreg.HKEY_LOCAL_MACHINE,'SOFTWARE\\Wow6432node\\Microsoft\\Microsoft SDKs\\Windows')
	except WindowsError:
		try:
			all_versions=Utils.winreg.OpenKey(Utils.winreg.HKEY_LOCAL_MACHINE,'SOFTWARE\\Microsoft\\Microsoft SDKs\\Windows')
		except WindowsError:
			return
	index=0
	while 1:
		try:
			version=Utils.winreg.EnumKey(all_versions,index)
		except WindowsError:
			break
		index=index+1
		if not version_pattern.match(version):
			continue
		try:
			msvc_version=Utils.winreg.OpenKey(all_versions,version)
			path,type=Utils.winreg.QueryValueEx(msvc_version,'InstallationFolder')
		except WindowsError:
			continue
		if os.path.isfile(os.path.join(path,'bin','SetEnv.cmd')):
			targets=[]
			for target,arch in all_msvc_platforms:
				try:
					targets.append((target,(arch,conf.get_msvc_version('wsdk',version,'/'+target,os.path.join(path,'bin','SetEnv.cmd')))))
				except conf.errors.ConfigurationError:
					pass
			versions.append(('wsdk '+version[1:],targets))
def gather_wince_supported_platforms():
	supported_wince_platforms=[]
	try:
		ce_sdk=Utils.winreg.OpenKey(Utils.winreg.HKEY_LOCAL_MACHINE,'SOFTWARE\\Wow6432node\\Microsoft\\Windows CE Tools\\SDKs')
	except WindowsError:
		try:
			ce_sdk=Utils.winreg.OpenKey(Utils.winreg.HKEY_LOCAL_MACHINE,'SOFTWARE\\Microsoft\\Windows CE Tools\\SDKs')
		except WindowsError:
			ce_sdk=''
	if not ce_sdk:
		return supported_wince_platforms
	ce_index=0
	while 1:
		try:
			sdk_device=Utils.winreg.EnumKey(ce_sdk,ce_index)
		except WindowsError:
			break
		ce_index=ce_index+1
		sdk=Utils.winreg.OpenKey(ce_sdk,sdk_device)
		try:
			path,type=Utils.winreg.QueryValueEx(sdk,'SDKRootDir')
		except WindowsError:
			try:
				path,type=Utils.winreg.QueryValueEx(sdk,'SDKInformation')
				path,xml=os.path.split(path)
			except WindowsError:
				continue
		path=str(path)
		path,device=os.path.split(path)
		if not device:
			path,device=os.path.split(path)
		for arch,compiler in all_wince_platforms:
			platforms=[]
			if os.path.isdir(os.path.join(path,device,'Lib',arch)):
				platforms.append((arch,compiler,os.path.join(path,device,'Include',arch),os.path.join(path,device,'Lib',arch)))
			if platforms:
				supported_wince_platforms.append((device,platforms))
	return supported_wince_platforms
def gather_msvc_detected_versions():
	version_pattern=re.compile('^(\d\d?\.\d\d?)(Exp)?$')
	detected_versions=[]
	for vcver,vcvar in[('VCExpress','Exp'),('VisualStudio','')]:
		try:
			prefix='SOFTWARE\\Wow6432node\\Microsoft\\'+vcver
			all_versions=Utils.winreg.OpenKey(Utils.winreg.HKEY_LOCAL_MACHINE,prefix)
		except WindowsError:
			try:
				prefix='SOFTWARE\\Microsoft\\'+vcver
				all_versions=Utils.winreg.OpenKey(Utils.winreg.HKEY_LOCAL_MACHINE,prefix)
			except WindowsError:
				continue
		index=0
		while 1:
			try:
				version=Utils.winreg.EnumKey(all_versions,index)
			except WindowsError:
				break
			index=index+1
			match=version_pattern.match(version)
			if not match:
				continue
			else:
				versionnumber=float(match.group(1))
			detected_versions.append((versionnumber,version+vcvar,prefix+"\\"+version))
	def fun(tup):
		return tup[0]
	detected_versions.sort(key=fun)
	return detected_versions
@conf
def gather_msvc_targets(conf,versions,version,vc_path):
	targets=[]
	if os.path.isfile(os.path.join(vc_path,'vcvarsall.bat')):
		for target,realtarget in all_msvc_platforms[::-1]:
			try:
				targets.append((target,(realtarget,conf.get_msvc_version('msvc',version,target,os.path.join(vc_path,'vcvarsall.bat')))))
			except conf.errors.ConfigurationError:
				pass
	elif os.path.isfile(os.path.join(vc_path,'Common7','Tools','vsvars32.bat')):
		try:
			targets.append(('x86',('x86',conf.get_msvc_version('msvc',version,'x86',os.path.join(vc_path,'Common7','Tools','vsvars32.bat')))))
		except conf.errors.ConfigurationError:
			pass
	elif os.path.isfile(os.path.join(vc_path,'Bin','vcvars32.bat')):
		try:
			targets.append(('x86',('x86',conf.get_msvc_version('msvc',version,'',os.path.join(vc_path,'Bin','vcvars32.bat')))))
		except conf.errors.ConfigurationError:
			pass
	if targets:
		versions.append(('msvc '+version,targets))
@conf
def gather_wince_targets(conf,versions,version,vc_path,vsvars,supported_platforms):
	for device,platforms in supported_platforms:
		cetargets=[]
		for platform,compiler,include,lib in platforms:
			winCEpath=os.path.join(vc_path,'ce')
			if not os.path.isdir(winCEpath):
				continue
			try:
				common_bindirs,_1,_2=conf.get_msvc_version('msvc',version,'x86',vsvars)
			except conf.errors.ConfigurationError:
				continue
			if os.path.isdir(os.path.join(winCEpath,'lib',platform)):
				bindirs=[os.path.join(winCEpath,'bin',compiler),os.path.join(winCEpath,'bin','x86_'+compiler)]+common_bindirs
				incdirs=[os.path.join(winCEpath,'include'),os.path.join(winCEpath,'atlmfc','include'),include]
				libdirs=[os.path.join(winCEpath,'lib',platform),os.path.join(winCEpath,'atlmfc','lib',platform),lib]
				cetargets.append((platform,(platform,(bindirs,incdirs,libdirs))))
		if cetargets:
			versions.append((device+' '+version,cetargets))
@conf
def gather_winphone_targets(conf,versions,version,vc_path,vsvars):
	targets=[]
	for target,realtarget in all_msvc_platforms[::-1]:
		try:
			targets.append((target,(realtarget,conf.get_msvc_version('winphone',version,target,vsvars))))
		except conf.errors.ConfigurationError ,e:
			pass
	if targets:
		versions.append(('winphone '+version,targets))
@conf
def gather_msvc_versions(conf,versions):
	vc_paths=[]
	for(v,version,reg)in gather_msvc_detected_versions():
		try:
			try:
				msvc_version=Utils.winreg.OpenKey(Utils.winreg.HKEY_LOCAL_MACHINE,reg+"\\Setup\\VC")
			except WindowsError:
				msvc_version=Utils.winreg.OpenKey(Utils.winreg.HKEY_LOCAL_MACHINE,reg+"\\Setup\\Microsoft Visual C++")
			path,type=Utils.winreg.QueryValueEx(msvc_version,'ProductDir')
			vc_paths.append((version,os.path.abspath(str(path))))
		except WindowsError:
			continue
	wince_supported_platforms=gather_wince_supported_platforms()
	for version,vc_path in vc_paths:
		vs_path=os.path.dirname(vc_path)
		vsvars=os.path.join(vs_path,'Common7','Tools','vsvars32.bat')
		if wince_supported_platforms and os.path.isfile(vsvars):
			conf.gather_wince_targets(versions,version,vc_path,vsvars,wince_supported_platforms)
		vsvars=os.path.join(vs_path,'VC','WPSDK','WP80','vcvarsphoneall.bat')
		if os.path.isfile(vsvars):
			conf.gather_winphone_targets(versions,'8.0',vc_path,vsvars)
	for version,vc_path in vc_paths:
		vs_path=os.path.dirname(vc_path)
		conf.gather_msvc_targets(versions,version,vc_path)
@conf
def gather_icl_versions(conf,versions):
	version_pattern=re.compile('^...?.?\....?.?')
	try:
		all_versions=Utils.winreg.OpenKey(Utils.winreg.HKEY_LOCAL_MACHINE,'SOFTWARE\\Wow6432node\\Intel\\Compilers\\C++')
	except WindowsError:
		try:
			all_versions=Utils.winreg.OpenKey(Utils.winreg.HKEY_LOCAL_MACHINE,'SOFTWARE\\Intel\\Compilers\\C++')
		except WindowsError:
			return
	index=0
	while 1:
		try:
			version=Utils.winreg.EnumKey(all_versions,index)
		except WindowsError:
			break
		index=index+1
		if not version_pattern.match(version):
			continue
		targets=[]
		for target,arch in all_icl_platforms:
			try:
				if target=='intel64':targetDir='EM64T_NATIVE'
				else:targetDir=target
				Utils.winreg.OpenKey(all_versions,version+'\\'+targetDir)
				icl_version=Utils.winreg.OpenKey(all_versions,version)
				path,type=Utils.winreg.QueryValueEx(icl_version,'ProductDir')
				batch_file=os.path.join(path,'bin','iclvars.bat')
				if os.path.isfile(batch_file):
					try:
						targets.append((target,(arch,conf.get_msvc_version('intel',version,target,batch_file))))
					except conf.errors.ConfigurationError:
						pass
			except WindowsError:
				pass
		for target,arch in all_icl_platforms:
			try:
				icl_version=Utils.winreg.OpenKey(all_versions,version+'\\'+target)
				path,type=Utils.winreg.QueryValueEx(icl_version,'ProductDir')
				batch_file=os.path.join(path,'bin','iclvars.bat')
				if os.path.isfile(batch_file):
					try:
						targets.append((target,(arch,conf.get_msvc_version('intel',version,target,batch_file))))
					except conf.errors.ConfigurationError:
						pass
			except WindowsError:
				continue
		major=version[0:2]
		versions.append(('intel '+major,targets))
@conf
def gather_intel_composer_versions(conf,versions):
	version_pattern=re.compile('^...?.?\...?.?.?')
	try:
		all_versions=Utils.winreg.OpenKey(Utils.winreg.HKEY_LOCAL_MACHINE,'SOFTWARE\\Wow6432node\\Intel\\Suites')
	except WindowsError:
		try:
			all_versions=Utils.winreg.OpenKey(Utils.winreg.HKEY_LOCAL_MACHINE,'SOFTWARE\\Intel\\Suites')
		except WindowsError:
			return
	index=0
	while 1:
		try:
			version=Utils.winreg.EnumKey(all_versions,index)
		except WindowsError:
			break
		index=index+1
		if not version_pattern.match(version):
			continue
		targets=[]
		for target,arch in all_icl_platforms:
			try:
				if target=='intel64':targetDir='EM64T_NATIVE'
				else:targetDir=target
				try:
					defaults=Utils.winreg.OpenKey(all_versions,version+'\\Defaults\\C++\\'+targetDir)
				except WindowsError:
					if targetDir=='EM64T_NATIVE':
						defaults=Utils.winreg.OpenKey(all_versions,version+'\\Defaults\\C++\\EM64T')
					else:
						raise WindowsError
				uid,type=Utils.winreg.QueryValueEx(defaults,'SubKey')
				Utils.winreg.OpenKey(all_versions,version+'\\'+uid+'\\C++\\'+targetDir)
				icl_version=Utils.winreg.OpenKey(all_versions,version+'\\'+uid+'\\C++')
				path,type=Utils.winreg.QueryValueEx(icl_version,'ProductDir')
				batch_file=os.path.join(path,'bin','iclvars.bat')
				if os.path.isfile(batch_file):
					try:
						targets.append((target,(arch,conf.get_msvc_version('intel',version,target,batch_file))))
					except conf.errors.ConfigurationError ,e:
						pass
				compilervars_warning_attr='_compilervars_warning_key'
				if version[0:2]=='13'and getattr(conf,compilervars_warning_attr,True):
					setattr(conf,compilervars_warning_attr,False)
					patch_url='http://software.intel.com/en-us/forums/topic/328487'
					compilervars_arch=os.path.join(path,'bin','compilervars_arch.bat')
					for vscomntool in['VS110COMNTOOLS','VS100COMNTOOLS']:
						if vscomntool in os.environ:
							vs_express_path=os.environ[vscomntool]+r'..\IDE\VSWinExpress.exe'
							dev_env_path=os.environ[vscomntool]+r'..\IDE\devenv.exe'
							if(r'if exist "%VS110COMNTOOLS%..\IDE\VSWinExpress.exe"'in Utils.readf(compilervars_arch)and not os.path.exists(vs_express_path)and not os.path.exists(dev_env_path)):
								Logs.warn(('The Intel compilervar_arch.bat only checks for one Visual Studio SKU ''(VSWinExpress.exe) but it does not seem to be installed at %r. ''The intel command line set up will fail to configure unless the file %r''is patched. See: %s')%(vs_express_path,compilervars_arch,patch_url))
			except WindowsError:
				pass
		major=version[0:2]
		versions.append(('intel '+major,targets))
@conf
def get_msvc_versions(conf):
	if not conf.env['MSVC_INSTALLED_VERSIONS']:
		lst=[]
		conf.gather_icl_versions(lst)
		conf.gather_intel_composer_versions(lst)
		conf.gather_wsdk_versions(lst)
		conf.gather_msvc_versions(lst)
		conf.env['MSVC_INSTALLED_VERSIONS']=lst
	return conf.env['MSVC_INSTALLED_VERSIONS']
@conf
def print_all_msvc_detected(conf):
	for version,targets in conf.env['MSVC_INSTALLED_VERSIONS']:
		Logs.info(version)
		for target,l in targets:
			Logs.info("\t"+target)
@conf
def detect_msvc(conf,arch=False):
	versions=get_msvc_versions(conf)
	return setup_msvc(conf,versions,arch)
@conf
def find_lt_names_msvc(self,libname,is_static=False):
	lt_names=['lib%s.la'%libname,'%s.la'%libname,]
	for path in self.env['LIBPATH']:
		for la in lt_names:
			laf=os.path.join(path,la)
			dll=None
			if os.path.exists(laf):
				ltdict=Utils.read_la_file(laf)
				lt_libdir=None
				if ltdict.get('libdir',''):
					lt_libdir=ltdict['libdir']
				if not is_static and ltdict.get('library_names',''):
					dllnames=ltdict['library_names'].split()
					dll=dllnames[0].lower()
					dll=re.sub('\.dll$','',dll)
					return(lt_libdir,dll,False)
				elif ltdict.get('old_library',''):
					olib=ltdict['old_library']
					if os.path.exists(os.path.join(path,olib)):
						return(path,olib,True)
					elif lt_libdir!=''and os.path.exists(os.path.join(lt_libdir,olib)):
						return(lt_libdir,olib,True)
					else:
						return(None,olib,True)
				else:
					raise self.errors.WafError('invalid libtool object file: %s'%laf)
	return(None,None,None)
@conf
def libname_msvc(self,libname,is_static=False):
	lib=libname.lower()
	lib=re.sub('\.lib$','',lib)
	if lib in g_msvc_systemlibs:
		return lib
	lib=re.sub('^lib','',lib)
	if lib=='m':
		return None
	(lt_path,lt_libname,lt_static)=self.find_lt_names_msvc(lib,is_static)
	if lt_path!=None and lt_libname!=None:
		if lt_static==True:
			return os.path.join(lt_path,lt_libname)
	if lt_path!=None:
		_libpaths=[lt_path]+self.env['LIBPATH']
	else:
		_libpaths=self.env['LIBPATH']
	static_libs=['lib%ss.lib'%lib,'lib%s.lib'%lib,'%ss.lib'%lib,'%s.lib'%lib,]
	dynamic_libs=['lib%s.dll.lib'%lib,'lib%s.dll.a'%lib,'%s.dll.lib'%lib,'%s.dll.a'%lib,'lib%s_d.lib'%lib,'%s_d.lib'%lib,'%s.lib'%lib,]
	libnames=static_libs
	if not is_static:
		libnames=dynamic_libs+static_libs
	for path in _libpaths:
		for libn in libnames:
			if os.path.exists(os.path.join(path,libn)):
				debug('msvc: lib found: %s'%os.path.join(path,libn))
				return re.sub('\.lib$','',libn)
	self.fatal("The library %r could not be found"%libname)
	return re.sub('\.lib$','',libname)
@conf
def check_lib_msvc(self,libname,is_static=False,uselib_store=None):
	libn=self.libname_msvc(libname,is_static)
	if not uselib_store:
		uselib_store=libname.upper()
	if False and is_static:
		self.env['STLIB_'+uselib_store]=[libn]
	else:
		self.env['LIB_'+uselib_store]=[libn]
@conf
def check_libs_msvc(self,libnames,is_static=False):
	for libname in Utils.to_list(libnames):
		self.check_lib_msvc(libname,is_static)
def configure(conf):
	conf.autodetect(True)
	conf.find_msvc()
	conf.msvc_common_flags()
	conf.cc_load_tools()
	conf.cxx_load_tools()
	conf.cc_add_flags()
	conf.cxx_add_flags()
	conf.link_add_flags()
	conf.visual_studio_add_flags()
@conf
def no_autodetect(conf):
	conf.env.NO_MSVC_DETECT=1
	configure(conf)
@conf
def autodetect(conf,arch=False):
	v=conf.env
	if v.NO_MSVC_DETECT:
		return
	if arch:
		compiler,version,path,includes,libdirs,arch=conf.detect_msvc(True)
		v['DEST_CPU']=arch
	else:
		compiler,version,path,includes,libdirs=conf.detect_msvc()
	v['PATH']=path
	v['INCLUDES']=includes
	v['LIBPATH']=libdirs
	v['MSVC_COMPILER']=compiler
	try:
		v['MSVC_VERSION']=float(version)
	except Exception:
		v['MSVC_VERSION']=float(version[:-3])
def _get_prog_names(conf,compiler):
	if compiler=='intel':
		compiler_name='ICL'
		linker_name='XILINK'
		lib_name='XILIB'
	else:
		compiler_name='CL'
		linker_name='LINK'
		lib_name='LIB'
	return compiler_name,linker_name,lib_name
@conf
def find_msvc(conf):
	if sys.platform=='cygwin':
		conf.fatal('MSVC module does not work under cygwin Python!')
	v=conf.env
	path=v['PATH']
	compiler=v['MSVC_COMPILER']
	version=v['MSVC_VERSION']
	compiler_name,linker_name,lib_name=_get_prog_names(conf,compiler)
	v.MSVC_MANIFEST=(compiler=='msvc'and version>=8)or(compiler=='wsdk'and version>=6)or(compiler=='intel'and version>=11)
	cxx=None
	if v['CXX']:cxx=v['CXX']
	elif'CXX'in conf.environ:cxx=conf.environ['CXX']
	cxx=conf.find_program(compiler_name,var='CXX',path_list=path)
	cxx=conf.cmd_to_list(cxx)
	env=dict(conf.environ)
	if path:env.update(PATH=';'.join(path))
	if not conf.cmd_and_log(cxx+['/nologo','/help'],env=env):
		conf.fatal('the msvc compiler could not be identified')
	v['CC']=v['CXX']=cxx
	v['CC_NAME']=v['CXX_NAME']='msvc'
	if not v['LINK_CXX']:
		link=conf.find_program(linker_name,path_list=path)
		if link:v['LINK_CXX']=link
		else:conf.fatal('%s was not found (linker)'%linker_name)
		v['LINK']=link
	if not v['LINK_CC']:
		v['LINK_CC']=v['LINK_CXX']
	if not v['AR']:
		stliblink=conf.find_program(lib_name,path_list=path,var='AR')
		if not stliblink:return
		v['ARFLAGS']=['/NOLOGO']
	if v.MSVC_MANIFEST:
		conf.find_program('MT',path_list=path,var='MT')
		v['MTFLAGS']=['/NOLOGO']
	try:
		conf.load('winres')
	except Errors.WafError:
		warn('Resource compiler not found. Compiling resource file is disabled')
@conf
def visual_studio_add_flags(self):
	v=self.env
	try:v.prepend_value('INCLUDES',[x for x in self.environ['INCLUDE'].split(';')if x])
	except Exception:pass
	try:v.prepend_value('LIBPATH',[x for x in self.environ['LIB'].split(';')if x])
	except Exception:pass
@conf
def msvc_common_flags(conf):
	v=conf.env
	v['DEST_BINFMT']='pe'
	v.append_value('CFLAGS',['/nologo'])
	v.append_value('CXXFLAGS',['/nologo'])
	v['DEFINES_ST']='/D%s'
	v['CC_SRC_F']=''
	v['CC_TGT_F']=['/c','/Fo']
	v['CXX_SRC_F']=''
	v['CXX_TGT_F']=['/c','/Fo']
	if(v.MSVC_COMPILER=='msvc'and v.MSVC_VERSION>=8)or(v.MSVC_COMPILER=='wsdk'and v.MSVC_VERSION>=6):
		v['CC_TGT_F']=['/FC']+v['CC_TGT_F']
		v['CXX_TGT_F']=['/FC']+v['CXX_TGT_F']
	v['CPPPATH_ST']='/I%s'
	v['AR_TGT_F']=v['CCLNK_TGT_F']=v['CXXLNK_TGT_F']='/OUT:'
	v['CFLAGS_CONSOLE']=v['CXXFLAGS_CONSOLE']=['/SUBSYSTEM:CONSOLE']
	v['CFLAGS_NATIVE']=v['CXXFLAGS_NATIVE']=['/SUBSYSTEM:NATIVE']
	v['CFLAGS_POSIX']=v['CXXFLAGS_POSIX']=['/SUBSYSTEM:POSIX']
	v['CFLAGS_WINDOWS']=v['CXXFLAGS_WINDOWS']=['/SUBSYSTEM:WINDOWS']
	v['CFLAGS_WINDOWSCE']=v['CXXFLAGS_WINDOWSCE']=['/SUBSYSTEM:WINDOWSCE']
	v['CFLAGS_CRT_MULTITHREADED']=v['CXXFLAGS_CRT_MULTITHREADED']=['/MT']
	v['CFLAGS_CRT_MULTITHREADED_DLL']=v['CXXFLAGS_CRT_MULTITHREADED_DLL']=['/MD']
	v['CFLAGS_CRT_MULTITHREADED_DBG']=v['CXXFLAGS_CRT_MULTITHREADED_DBG']=['/MTd']
	v['CFLAGS_CRT_MULTITHREADED_DLL_DBG']=v['CXXFLAGS_CRT_MULTITHREADED_DLL_DBG']=['/MDd']
	v['LIB_ST']='%s.lib'
	v['LIBPATH_ST']='/LIBPATH:%s'
	v['STLIB_ST']='%s.lib'
	v['STLIBPATH_ST']='/LIBPATH:%s'
	v.append_value('LINKFLAGS',['/NOLOGO'])
	if v['MSVC_MANIFEST']:
		v.append_value('LINKFLAGS',['/MANIFEST'])
	v['CFLAGS_cshlib']=[]
	v['CXXFLAGS_cxxshlib']=[]
	v['LINKFLAGS_cshlib']=v['LINKFLAGS_cxxshlib']=['/DLL']
	v['cshlib_PATTERN']=v['cxxshlib_PATTERN']='%s.dll'
	v['implib_PATTERN']='%s.lib'
	v['IMPLIB_ST']='/IMPLIB:%s'
	v['LINKFLAGS_cstlib']=[]
	v['cstlib_PATTERN']=v['cxxstlib_PATTERN']='%s.lib'
	v['cprogram_PATTERN']=v['cxxprogram_PATTERN']='%s.exe'
@after_method('apply_link')
@feature('c','cxx')
def apply_flags_msvc(self):
	if self.env.CC_NAME!='msvc'or not getattr(self,'link_task',None):
		return
	is_static=isinstance(self.link_task,ccroot.stlink_task)
	subsystem=getattr(self,'subsystem','')
	if subsystem:
		subsystem='/subsystem:%s'%subsystem
		flags=is_static and'ARFLAGS'or'LINKFLAGS'
		self.env.append_value(flags,subsystem)
	if not is_static:
		for f in self.env.LINKFLAGS:
			d=f.lower()
			if d[1:]=='debug':
				pdbnode=self.link_task.outputs[0].change_ext('.pdb')
				self.link_task.outputs.append(pdbnode)
				try:
					self.install_task.source.append(pdbnode)
				except AttributeError:
					pass
				break
@feature('cprogram','cshlib','cxxprogram','cxxshlib')
@after_method('apply_link')
def apply_manifest(self):
	if self.env.CC_NAME=='msvc'and self.env.MSVC_MANIFEST and getattr(self,'link_task',None):
		out_node=self.link_task.outputs[0]
		man_node=out_node.parent.find_or_declare(out_node.name+'.manifest')
		self.link_task.outputs.append(man_node)
		self.link_task.do_manifest=True
def exec_mf(self):
	env=self.env
	mtool=env['MT']
	if not mtool:
		return 0
	self.do_manifest=False
	outfile=self.outputs[0].abspath()
	manifest=None
	for out_node in self.outputs:
		if out_node.name.endswith('.manifest'):
			manifest=out_node.abspath()
			break
	if manifest is None:
		return 0
	mode=''
	if'cprogram'in self.generator.features or'cxxprogram'in self.generator.features:
		mode='1'
	elif'cshlib'in self.generator.features or'cxxshlib'in self.generator.features:
		mode='2'
	debug('msvc: embedding manifest in mode %r'%mode)
	lst=[]
	lst.append(env['MT'])
	lst.extend(Utils.to_list(env['MTFLAGS']))
	lst.extend(['-manifest',manifest])
	lst.append('-outputresource:%s;%s'%(outfile,mode))
	lst=[lst]
	return self.exec_command(*lst)
def quote_response_command(self,flag):
	if flag.find(' ')>-1:
		for x in('/LIBPATH:','/IMPLIB:','/OUT:','/I'):
			if flag.startswith(x):
				flag='%s"%s"'%(x,flag[len(x):])
				break
		else:
			flag='"%s"'%flag
	return flag
def exec_response_command(self,cmd,**kw):
	try:
		tmp=None
		if sys.platform.startswith('win')and isinstance(cmd,list)and len(' '.join(cmd))>=8192:
			program=cmd[0]
			cmd=[self.quote_response_command(x)for x in cmd]
			(fd,tmp)=tempfile.mkstemp()
			os.write(fd,'\r\n'.join(i.replace('\\','\\\\')for i in cmd[1:]))
			os.close(fd)
			cmd=[program,'@'+tmp]
		ret=self.generator.bld.exec_command(cmd,**kw)
	finally:
		if tmp:
			try:
				os.remove(tmp)
			except OSError:
				pass
	return ret
def exec_command_msvc(self,*k,**kw):
	if isinstance(k[0],list):
		lst=[]
		carry=''
		for a in k[0]:
			if a=='/Fo'or a=='/doc'or a[-1]==':':
				carry=a
			else:
				lst.append(carry+a)
				carry=''
		k=[lst]
	if self.env['PATH']:
		env=dict(self.env.env or os.environ)
		env.update(PATH=';'.join(self.env['PATH']))
		kw['env']=env
	bld=self.generator.bld
	try:
		if not kw.get('cwd',None):
			kw['cwd']=bld.cwd
	except AttributeError:
		bld.cwd=kw['cwd']=bld.variant_dir
	ret=self.exec_response_command(k[0],**kw)
	if not ret and getattr(self,'do_manifest',None):
		ret=self.exec_mf()
	return ret
def wrap_class(class_name):
	cls=Task.classes.get(class_name,None)
	if not cls:
		return None
	derived_class=type(class_name,(cls,),{})
	def exec_command(self,*k,**kw):
		if self.env['CC_NAME']=='msvc':
			return self.exec_command_msvc(*k,**kw)
		else:
			return super(derived_class,self).exec_command(*k,**kw)
	derived_class.exec_command=exec_command
	derived_class.exec_response_command=exec_response_command
	derived_class.quote_response_command=quote_response_command
	derived_class.exec_command_msvc=exec_command_msvc
	derived_class.exec_mf=exec_mf
	return derived_class
for k in'c cxx cprogram cxxprogram cshlib cxxshlib cstlib cxxstlib'.split():
	wrap_class(k)
def make_winapp(self,family):
	append=self.env.append_unique
	append('DEFINES','WINAPI_FAMILY=%s'%family)
	append('CXXFLAGS','/ZW')
	append('CXXFLAGS','/TP')
	for lib_path in self.env.LIBPATH:
		append('CXXFLAGS','/AI%s'%lib_path)
@feature('winphoneapp')
@after_method('process_use')
@after_method('propagate_uselib_vars')
def make_winphone_app(self):
	make_winapp(self,'WINAPI_FAMILY_PHONE_APP')
	conf.env.append_unique('LINKFLAGS','/NODEFAULTLIB:ole32.lib')
	conf.env.append_unique('LINKFLAGS','PhoneAppModelHost.lib')
@feature('winapp')
@after_method('process_use')
@after_method('propagate_uselib_vars')
def make_windows_app(self):
	make_winapp(self,'WINAPI_FAMILY_DESKTOP_APP')

########NEW FILE########
__FILENAME__ = nasm
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import os
import waflib.Tools.asm
from waflib.TaskGen import feature
@feature('asm')
def apply_nasm_vars(self):
	self.env.append_value('ASFLAGS',self.to_list(getattr(self,'nasm_flags',[])))
def configure(conf):
	nasm=conf.find_program(['nasm','yasm'],var='AS')
	conf.env.AS_TGT_F=['-o']
	conf.env.ASLNK_TGT_F=['-o']
	conf.load('asm')
	conf.env.ASMPATH_ST='-I%s'+os.sep

########NEW FILE########
__FILENAME__ = perl
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import os
from waflib import Task,Options,Utils
from waflib.Configure import conf
from waflib.TaskGen import extension,feature,before_method
@before_method('apply_incpaths','apply_link','propagate_uselib_vars')
@feature('perlext')
def init_perlext(self):
	self.uselib=self.to_list(getattr(self,'uselib',[]))
	if not'PERLEXT'in self.uselib:self.uselib.append('PERLEXT')
	self.env['cshlib_PATTERN']=self.env['cxxshlib_PATTERN']=self.env['perlext_PATTERN']
@extension('.xs')
def xsubpp_file(self,node):
	outnode=node.change_ext('.c')
	self.create_task('xsubpp',node,outnode)
	self.source.append(outnode)
class xsubpp(Task.Task):
	run_str='${PERL} ${XSUBPP} -noprototypes -typemap ${EXTUTILS_TYPEMAP} ${SRC} > ${TGT}'
	color='BLUE'
	ext_out=['.h']
@conf
def check_perl_version(self,minver=None):
	res=True
	if minver:
		cver='.'.join(map(str,minver))
	else:
		cver=''
	self.start_msg('Checking for minimum perl version %s'%cver)
	perl=getattr(Options.options,'perlbinary',None)
	if not perl:
		perl=self.find_program('perl',var='PERL')
	if not perl:
		self.end_msg("Perl not found",color="YELLOW")
		return False
	self.env['PERL']=perl
	version=self.cmd_and_log([perl,"-e",'printf \"%vd\", $^V'])
	if not version:
		res=False
		version="Unknown"
	elif not minver is None:
		ver=tuple(map(int,version.split(".")))
		if ver<minver:
			res=False
	self.end_msg(version,color=res and"GREEN"or"YELLOW")
	return res
@conf
def check_perl_module(self,module):
	cmd=[self.env['PERL'],'-e','use %s'%module]
	self.start_msg('perl module %s'%module)
	try:
		r=self.cmd_and_log(cmd)
	except Exception:
		self.end_msg(False)
		return None
	self.end_msg(r or True)
	return r
@conf
def check_perl_ext_devel(self):
	env=self.env
	perl=env.PERL
	if not perl:
		self.fatal('find perl first')
	def read_out(cmd):
		return Utils.to_list(self.cmd_and_log(perl+cmd))
	env['LINKFLAGS_PERLEXT']=read_out(" -MConfig -e'print $Config{lddlflags}'")
	env['INCLUDES_PERLEXT']=read_out(" -MConfig -e'print \"$Config{archlib}/CORE\"'")
	env['CFLAGS_PERLEXT']=read_out(" -MConfig -e'print \"$Config{ccflags} $Config{cccdlflags}\"'")
	env['XSUBPP']=read_out(" -MConfig -e'print \"$Config{privlib}/ExtUtils/xsubpp$Config{exe_ext}\"'")
	env['EXTUTILS_TYPEMAP']=read_out(" -MConfig -e'print \"$Config{privlib}/ExtUtils/typemap\"'")
	if not getattr(Options.options,'perlarchdir',None):
		env['ARCHDIR_PERL']=self.cmd_and_log(perl+" -MConfig -e'print $Config{sitearch}'")
	else:
		env['ARCHDIR_PERL']=getattr(Options.options,'perlarchdir')
	env['perlext_PATTERN']='%s.'+self.cmd_and_log(perl+" -MConfig -e'print $Config{dlext}'")
def options(opt):
	opt.add_option('--with-perl-binary',type='string',dest='perlbinary',help='Specify alternate perl binary',default=None)
	opt.add_option('--with-perl-archdir',type='string',dest='perlarchdir',help='Specify directory where to install arch specific files',default=None)

########NEW FILE########
__FILENAME__ = python
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import os,sys
from waflib import Utils,Options,Errors,Logs
from waflib.TaskGen import extension,before_method,after_method,feature
from waflib.Configure import conf
FRAG='''
#include <Python.h>
#ifdef __cplusplus
extern "C" {
#endif
	void Py_Initialize(void);
	void Py_Finalize(void);
#ifdef __cplusplus
}
#endif
int main(int argc, char **argv)
{
   (void)argc; (void)argv;
   Py_Initialize();
   Py_Finalize();
   return 0;
}
'''
INST='''
import sys, py_compile
py_compile.compile(sys.argv[1], sys.argv[2], sys.argv[3])
'''
DISTUTILS_IMP=['from distutils.sysconfig import get_config_var, get_python_lib']
@extension('.py')
def process_py(self,node):
	try:
		if not self.bld.is_install:
			return
	except AttributeError:
		return
	try:
		if not self.install_path:
			return
	except AttributeError:
		self.install_path='${PYTHONDIR}'
	def inst_py(ctx):
		install_from=getattr(self,'install_from',None)
		if install_from:
			install_from=self.path.find_dir(install_from)
		install_pyfile(self,node,install_from)
	self.bld.add_post_fun(inst_py)
def install_pyfile(self,node,install_from=None):
	from_node=install_from or node.parent
	tsk=self.bld.install_as(self.install_path+'/'+node.path_from(from_node),node,postpone=False)
	path=tsk.get_install_path()
	if self.bld.is_install<0:
		Logs.info("+ removing byte compiled python files")
		for x in'co':
			try:
				os.remove(path+x)
			except OSError:
				pass
	if self.bld.is_install>0:
		try:
			st1=os.stat(path)
		except OSError:
			Logs.error('The python file is missing, this should not happen')
		for x in['c','o']:
			do_inst=self.env['PY'+x.upper()]
			try:
				st2=os.stat(path+x)
			except OSError:
				pass
			else:
				if st1.st_mtime<=st2.st_mtime:
					do_inst=False
			if do_inst:
				lst=(x=='o')and[self.env['PYFLAGS_OPT']]or[]
				(a,b,c)=(path,path+x,tsk.get_install_path(destdir=False)+x)
				argv=self.env['PYTHON']+lst+['-c',INST,a,b,c]
				Logs.info('+ byte compiling %r'%(path+x))
				env=self.env.env or None
				ret=Utils.subprocess.Popen(argv,env=env).wait()
				if ret:
					raise Errors.WafError('py%s compilation failed %r'%(x,path))
@feature('py')
def feature_py(self):
	pass
@feature('pyext')
@before_method('propagate_uselib_vars','apply_link')
@after_method('apply_bundle')
def init_pyext(self):
	self.uselib=self.to_list(getattr(self,'uselib',[]))
	if not'PYEXT'in self.uselib:
		self.uselib.append('PYEXT')
	self.env.cshlib_PATTERN=self.env.cxxshlib_PATTERN=self.env.macbundle_PATTERN=self.env.pyext_PATTERN
	self.env.fcshlib_PATTERN=self.env.dshlib_PATTERN=self.env.pyext_PATTERN
	try:
		if not self.install_path:
			return
	except AttributeError:
		self.install_path='${PYTHONARCHDIR}'
@feature('pyext')
@before_method('apply_link','apply_bundle')
def set_bundle(self):
	if Utils.unversioned_sys_platform()=='darwin':
		self.mac_bundle=True
@before_method('propagate_uselib_vars')
@feature('pyembed')
def init_pyembed(self):
	self.uselib=self.to_list(getattr(self,'uselib',[]))
	if not'PYEMBED'in self.uselib:
		self.uselib.append('PYEMBED')
@conf
def get_python_variables(self,variables,imports=None):
	if not imports:
		try:
			imports=self.python_imports
		except AttributeError:
			imports=DISTUTILS_IMP
	program=list(imports)
	program.append('')
	for v in variables:
		program.append("print(repr(%s))"%v)
	os_env=dict(os.environ)
	try:
		del os_env['MACOSX_DEPLOYMENT_TARGET']
	except KeyError:
		pass
	try:
		out=self.cmd_and_log(self.env.PYTHON+['-c','\n'.join(program)],env=os_env)
	except Errors.WafError:
		self.fatal('The distutils module is unusable: install "python-devel"?')
	self.to_log(out)
	return_values=[]
	for s in out.split('\n'):
		s=s.strip()
		if not s:
			continue
		if s=='None':
			return_values.append(None)
		elif(s[0]=="'"and s[-1]=="'")or(s[0]=='"'and s[-1]=='"'):
			return_values.append(eval(s))
		elif s[0].isdigit():
			return_values.append(int(s))
		else:break
	return return_values
@conf
def check_python_headers(conf):
	env=conf.env
	if not env['CC_NAME']and not env['CXX_NAME']:
		conf.fatal('load a compiler first (gcc, g++, ..)')
	if not env['PYTHON_VERSION']:
		conf.check_python_version()
	pybin=conf.env.PYTHON
	if not pybin:
		conf.fatal('Could not find the python executable')
	v='prefix SO LDFLAGS LIBDIR LIBPL INCLUDEPY Py_ENABLE_SHARED MACOSX_DEPLOYMENT_TARGET LDSHARED CFLAGS'.split()
	try:
		lst=conf.get_python_variables(["get_config_var('%s') or ''"%x for x in v])
	except RuntimeError:
		conf.fatal("Python development headers not found (-v for details).")
	vals=['%s = %r'%(x,y)for(x,y)in zip(v,lst)]
	conf.to_log("Configuration returned from %r:\n%r\n"%(pybin,'\n'.join(vals)))
	dct=dict(zip(v,lst))
	x='MACOSX_DEPLOYMENT_TARGET'
	if dct[x]:
		conf.env[x]=conf.environ[x]=dct[x]
	env['pyext_PATTERN']='%s'+dct['SO']
	all_flags=dct['LDFLAGS']+' '+dct['CFLAGS']
	conf.parse_flags(all_flags,'PYEMBED')
	all_flags=dct['LDFLAGS']+' '+dct['LDSHARED']+' '+dct['CFLAGS']
	conf.parse_flags(all_flags,'PYEXT')
	result=None
	for name in('python'+env['PYTHON_VERSION'],'python'+env['PYTHON_VERSION']+'m','python'+env['PYTHON_VERSION'].replace('.','')):
		if not result and env['LIBPATH_PYEMBED']:
			path=env['LIBPATH_PYEMBED']
			conf.to_log("\n\n# Trying default LIBPATH_PYEMBED: %r\n"%path)
			result=conf.check(lib=name,uselib='PYEMBED',libpath=path,mandatory=False,msg='Checking for library %s in LIBPATH_PYEMBED'%name)
		if not result and dct['LIBDIR']:
			path=[dct['LIBDIR']]
			conf.to_log("\n\n# try again with -L$python_LIBDIR: %r\n"%path)
			result=conf.check(lib=name,uselib='PYEMBED',libpath=path,mandatory=False,msg='Checking for library %s in LIBDIR'%name)
		if not result and dct['LIBPL']:
			path=[dct['LIBPL']]
			conf.to_log("\n\n# try again with -L$python_LIBPL (some systems don't install the python library in $prefix/lib)\n")
			result=conf.check(lib=name,uselib='PYEMBED',libpath=path,mandatory=False,msg='Checking for library %s in python_LIBPL'%name)
		if not result:
			path=[os.path.join(dct['prefix'],"libs")]
			conf.to_log("\n\n# try again with -L$prefix/libs, and pythonXY name rather than pythonX.Y (win32)\n")
			result=conf.check(lib=name,uselib='PYEMBED',libpath=path,mandatory=False,msg='Checking for library %s in $prefix/libs'%name)
		if result:
			break
	if result:
		env['LIBPATH_PYEMBED']=path
		env.append_value('LIB_PYEMBED',[name])
	else:
		conf.to_log("\n\n### LIB NOT FOUND\n")
	if(Utils.is_win32 or sys.platform.startswith('os2')or dct['Py_ENABLE_SHARED']):
		env['LIBPATH_PYEXT']=env['LIBPATH_PYEMBED']
		env['LIB_PYEXT']=env['LIB_PYEMBED']
	num='.'.join(env['PYTHON_VERSION'].split('.')[:2])
	conf.find_program([''.join(pybin)+'-config','python%s-config'%num,'python-config-%s'%num,'python%sm-config'%num],var='PYTHON_CONFIG',mandatory=False)
	includes=[]
	if conf.env.PYTHON_CONFIG:
		for incstr in conf.cmd_and_log([conf.env.PYTHON_CONFIG,'--includes']).strip().split():
			if(incstr.startswith('-I')or incstr.startswith('/I')):
				incstr=incstr[2:]
			if incstr not in includes:
				includes.append(incstr)
		conf.to_log("Include path for Python extensions (found via python-config --includes): %r\n"%(includes,))
		env['INCLUDES_PYEXT']=includes
		env['INCLUDES_PYEMBED']=includes
	else:
		conf.to_log("Include path for Python extensions ""(found via distutils module): %r\n"%(dct['INCLUDEPY'],))
		env['INCLUDES_PYEXT']=[dct['INCLUDEPY']]
		env['INCLUDES_PYEMBED']=[dct['INCLUDEPY']]
	if env['CC_NAME']=='gcc':
		env.append_value('CFLAGS_PYEMBED',['-fno-strict-aliasing'])
		env.append_value('CFLAGS_PYEXT',['-fno-strict-aliasing'])
	if env['CXX_NAME']=='gcc':
		env.append_value('CXXFLAGS_PYEMBED',['-fno-strict-aliasing'])
		env.append_value('CXXFLAGS_PYEXT',['-fno-strict-aliasing'])
	if env.CC_NAME=="msvc":
		from distutils.msvccompiler import MSVCCompiler
		dist_compiler=MSVCCompiler()
		dist_compiler.initialize()
		env.append_value('CFLAGS_PYEXT',dist_compiler.compile_options)
		env.append_value('CXXFLAGS_PYEXT',dist_compiler.compile_options)
		env.append_value('LINKFLAGS_PYEXT',dist_compiler.ldflags_shared)
	try:
		conf.check(header_name='Python.h',define_name='HAVE_PYTHON_H',uselib='PYEMBED',fragment=FRAG,errmsg=':-(')
	except conf.errors.ConfigurationError:
		xx=conf.env.CXX_NAME and'cxx'or'c'
		flags=['--cflags','--libs','--ldflags']
		for f in flags:
			conf.check_cfg(msg='Asking python-config for pyembed %s flags'%f,path=conf.env.PYTHON_CONFIG,package='',uselib_store='PYEMBED',args=[f])
		conf.check(header_name='Python.h',define_name='HAVE_PYTHON_H',msg='Getting pyembed flags from python-config',fragment=FRAG,errmsg='Could not build a python embedded interpreter',features='%s %sprogram pyembed'%(xx,xx))
		for f in flags:
			conf.check_cfg(msg='Asking python-config for pyext %s flags'%f,path=conf.env.PYTHON_CONFIG,package='',uselib_store='PYEXT',args=[f])
		conf.check(header_name='Python.h',define_name='HAVE_PYTHON_H',msg='Getting pyext flags from python-config',features='%s %sshlib pyext'%(xx,xx),fragment=FRAG,errmsg='Could not build python extensions')
@conf
def check_python_version(conf,minver=None):
	assert minver is None or isinstance(minver,tuple)
	pybin=conf.env['PYTHON']
	if not pybin:
		conf.fatal('could not find the python executable')
	cmd=pybin+['-c','import sys\nfor x in sys.version_info: print(str(x))']
	Logs.debug('python: Running python command %r'%cmd)
	lines=conf.cmd_and_log(cmd).split()
	assert len(lines)==5,"found %i lines, expected 5: %r"%(len(lines),lines)
	pyver_tuple=(int(lines[0]),int(lines[1]),int(lines[2]),lines[3],int(lines[4]))
	result=(minver is None)or(pyver_tuple>=minver)
	if result:
		pyver='.'.join([str(x)for x in pyver_tuple[:2]])
		conf.env['PYTHON_VERSION']=pyver
		if'PYTHONDIR'in conf.environ:
			pydir=conf.environ['PYTHONDIR']
		else:
			if Utils.is_win32:
				(python_LIBDEST,pydir)=conf.get_python_variables(["get_config_var('LIBDEST') or ''","get_python_lib(standard_lib=0, prefix=%r) or ''"%conf.env['PREFIX']])
			else:
				python_LIBDEST=None
				(pydir,)=conf.get_python_variables(["get_python_lib(standard_lib=0, prefix=%r) or ''"%conf.env['PREFIX']])
			if python_LIBDEST is None:
				if conf.env['LIBDIR']:
					python_LIBDEST=os.path.join(conf.env['LIBDIR'],"python"+pyver)
				else:
					python_LIBDEST=os.path.join(conf.env['PREFIX'],"lib","python"+pyver)
		if'PYTHONARCHDIR'in conf.environ:
			pyarchdir=conf.environ['PYTHONARCHDIR']
		else:
			(pyarchdir,)=conf.get_python_variables(["get_python_lib(plat_specific=1, standard_lib=0, prefix=%r) or ''"%conf.env['PREFIX']])
			if not pyarchdir:
				pyarchdir=pydir
		if hasattr(conf,'define'):
			conf.define('PYTHONDIR',pydir)
			conf.define('PYTHONARCHDIR',pyarchdir)
		conf.env['PYTHONDIR']=pydir
		conf.env['PYTHONARCHDIR']=pyarchdir
	pyver_full='.'.join(map(str,pyver_tuple[:3]))
	if minver is None:
		conf.msg('Checking for python version',pyver_full)
	else:
		minver_str='.'.join(map(str,minver))
		conf.msg('Checking for python version',pyver_tuple,">= %s"%(minver_str,)and'GREEN'or'YELLOW')
	if not result:
		conf.fatal('The python version is too old, expecting %r'%(minver,))
PYTHON_MODULE_TEMPLATE='''
import %s as current_module
version = getattr(current_module, '__version__', None)
if version is not None:
    print(str(version))
else:
    print('unknown version')
'''
@conf
def check_python_module(conf,module_name,condition=''):
	msg='Python module %s'%module_name
	if condition:
		msg='%s (%s)'%(msg,condition)
	conf.start_msg(msg)
	try:
		ret=conf.cmd_and_log(conf.env['PYTHON']+['-c',PYTHON_MODULE_TEMPLATE%module_name])
	except Exception:
		conf.end_msg(False)
		conf.fatal('Could not find the python module %r'%module_name)
	ret=ret.strip()
	if condition:
		conf.end_msg(ret)
		if ret=='unknown version':
			conf.fatal('Could not check the %s version'%module_name)
		from distutils.version import LooseVersion
		def num(*k):
			if isinstance(k[0],int):
				return LooseVersion('.'.join([str(x)for x in k]))
			else:
				return LooseVersion(k[0])
		d={'num':num,'ver':LooseVersion(ret)}
		ev=eval(condition,{},d)
		if not ev:
			conf.fatal('The %s version does not satisfy the requirements'%module_name)
	else:
		if ret=='unknown version':
			conf.end_msg(True)
		else:
			conf.end_msg(ret)
def configure(conf):
	try:
		conf.find_program('python',var='PYTHON')
	except conf.errors.ConfigurationError:
		Logs.warn("could not find a python executable, setting to sys.executable '%s'"%sys.executable)
		conf.env.PYTHON=sys.executable
	if conf.env.PYTHON!=sys.executable:
		Logs.warn("python executable %r differs from system %r"%(conf.env.PYTHON,sys.executable))
	conf.env.PYTHON=conf.cmd_to_list(conf.env.PYTHON)
	v=conf.env
	v['PYCMD']='"import sys, py_compile;py_compile.compile(sys.argv[1], sys.argv[2])"'
	v['PYFLAGS']=''
	v['PYFLAGS_OPT']='-O'
	v['PYC']=getattr(Options.options,'pyc',1)
	v['PYO']=getattr(Options.options,'pyo',1)
def options(opt):
	opt.add_option('--nopyc',action='store_false',default=1,help='Do not install bytecode compiled .pyc files (configuration) [Default:install]',dest='pyc')
	opt.add_option('--nopyo',action='store_false',default=1,help='Do not install optimised compiled .pyo files (configuration) [Default:install]',dest='pyo')

########NEW FILE########
__FILENAME__ = qt4
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

try:
	from xml.sax import make_parser
	from xml.sax.handler import ContentHandler
except ImportError:
	has_xml=False
	ContentHandler=object
else:
	has_xml=True
import os,sys
from waflib.Tools import c_preproc,cxx
from waflib import Task,Utils,Options,Errors
from waflib.TaskGen import feature,after_method,extension
from waflib.Configure import conf
from waflib import Logs
MOC_H=['.h','.hpp','.hxx','.hh']
EXT_RCC=['.qrc']
EXT_UI=['.ui']
EXT_QT4=['.cpp','.cc','.cxx','.C']
QT4_LIBS="QtCore QtGui QtUiTools QtNetwork QtOpenGL QtSql QtSvg QtTest QtXml QtXmlPatterns QtWebKit Qt3Support QtHelp QtScript QtDeclarative QtDesigner"
class qxx(Task.classes['cxx']):
	def __init__(self,*k,**kw):
		Task.Task.__init__(self,*k,**kw)
		self.moc_done=0
	def scan(self):
		(nodes,names)=c_preproc.scan(self)
		lst=[]
		for x in nodes:
			if x.name.endswith('.moc'):
				s=x.path_from(self.inputs[0].parent.get_bld())
				if s not in names:
					names.append(s)
			else:
				lst.append(x)
		return(lst,names)
	def runnable_status(self):
		if self.moc_done:
			return Task.Task.runnable_status(self)
		else:
			for t in self.run_after:
				if not t.hasrun:
					return Task.ASK_LATER
			self.add_moc_tasks()
			return Task.Task.runnable_status(self)
	def create_moc_task(self,h_node,m_node):
		try:
			moc_cache=self.generator.bld.moc_cache
		except AttributeError:
			moc_cache=self.generator.bld.moc_cache={}
		try:
			return moc_cache[h_node]
		except KeyError:
			tsk=moc_cache[h_node]=Task.classes['moc'](env=self.env,generator=self.generator)
			tsk.set_inputs(h_node)
			tsk.set_outputs(m_node)
			gen=self.generator.bld.producer
			gen.outstanding.insert(0,tsk)
			gen.total+=1
			return tsk
	def add_moc_tasks(self):
		node=self.inputs[0]
		bld=self.generator.bld
		try:
			self.signature()
		except KeyError:
			pass
		else:
			delattr(self,'cache_sig')
		moctasks=[]
		mocfiles=[]
		try:
			tmp_lst=bld.raw_deps[self.uid()]
			bld.raw_deps[self.uid()]=[]
		except KeyError:
			tmp_lst=[]
		for d in tmp_lst:
			if not d.endswith('.moc'):
				continue
			if d in mocfiles:
				Logs.error("paranoia owns")
				continue
			mocfiles.append(d)
			h_node=None
			try:ext=Options.options.qt_header_ext.split()
			except AttributeError:pass
			if not ext:ext=MOC_H
			base2=d[:-4]
			for x in[node.parent]+self.generator.includes_nodes:
				for e in ext:
					h_node=x.find_node(base2+e)
					if h_node:
						break
				if h_node:
					m_node=h_node.change_ext('.moc')
					break
			else:
				for k in EXT_QT4:
					if base2.endswith(k):
						for x in[node.parent]+self.generator.includes_nodes:
							h_node=x.find_node(base2)
							if h_node:
								break
					if h_node:
						m_node=h_node.change_ext(k+'.moc')
						break
			if not h_node:
				raise Errors.WafError('no header found for %r which is a moc file'%d)
			bld.node_deps[(self.inputs[0].parent.abspath(),m_node.name)]=h_node
			task=self.create_moc_task(h_node,m_node)
			moctasks.append(task)
		tmp_lst=bld.raw_deps[self.uid()]=mocfiles
		lst=bld.node_deps.get(self.uid(),())
		for d in lst:
			name=d.name
			if name.endswith('.moc'):
				task=self.create_moc_task(bld.node_deps[(self.inputs[0].parent.abspath(),name)],d)
				moctasks.append(task)
		self.run_after.update(set(moctasks))
		self.moc_done=1
	run=Task.classes['cxx'].__dict__['run']
class trans_update(Task.Task):
	run_str='${QT_LUPDATE} ${SRC} -ts ${TGT}'
	color='BLUE'
Task.update_outputs(trans_update)
class XMLHandler(ContentHandler):
	def __init__(self):
		self.buf=[]
		self.files=[]
	def startElement(self,name,attrs):
		if name=='file':
			self.buf=[]
	def endElement(self,name):
		if name=='file':
			self.files.append(str(''.join(self.buf)))
	def characters(self,cars):
		self.buf.append(cars)
@extension(*EXT_RCC)
def create_rcc_task(self,node):
	rcnode=node.change_ext('_rc.cpp')
	rcctask=self.create_task('rcc',node,rcnode)
	cpptask=self.create_task('cxx',rcnode,rcnode.change_ext('.o'))
	try:
		self.compiled_tasks.append(cpptask)
	except AttributeError:
		self.compiled_tasks=[cpptask]
	return cpptask
@extension(*EXT_UI)
def create_uic_task(self,node):
	uictask=self.create_task('ui4',node)
	uictask.outputs=[self.path.find_or_declare(self.env['ui_PATTERN']%node.name[:-3])]
@extension('.ts')
def add_lang(self,node):
	self.lang=self.to_list(getattr(self,'lang',[]))+[node]
@feature('qt4')
@after_method('apply_link')
def apply_qt4(self):
	if getattr(self,'lang',None):
		qmtasks=[]
		for x in self.to_list(self.lang):
			if isinstance(x,str):
				x=self.path.find_resource(x+'.ts')
			qmtasks.append(self.create_task('ts2qm',x,x.change_ext('.qm')))
		if getattr(self,'update',None)and Options.options.trans_qt4:
			cxxnodes=[a.inputs[0]for a in self.compiled_tasks]+[a.inputs[0]for a in self.tasks if getattr(a,'inputs',None)and a.inputs[0].name.endswith('.ui')]
			for x in qmtasks:
				self.create_task('trans_update',cxxnodes,x.inputs)
		if getattr(self,'langname',None):
			qmnodes=[x.outputs[0]for x in qmtasks]
			rcnode=self.langname
			if isinstance(rcnode,str):
				rcnode=self.path.find_or_declare(rcnode+'.qrc')
			t=self.create_task('qm2rcc',qmnodes,rcnode)
			k=create_rcc_task(self,t.outputs[0])
			self.link_task.inputs.append(k.outputs[0])
	lst=[]
	for flag in self.to_list(self.env['CXXFLAGS']):
		if len(flag)<2:continue
		f=flag[0:2]
		if f in['-D','-I','/D','/I']:
			if(f[0]=='/'):
				lst.append('-'+flag[1:])
			else:
				lst.append(flag)
	self.env.append_value('MOC_FLAGS',lst)
@extension(*EXT_QT4)
def cxx_hook(self,node):
	return self.create_compiled_task('qxx',node)
class rcc(Task.Task):
	color='BLUE'
	run_str='${QT_RCC} -name ${SRC[0].name} ${SRC[0].abspath()} ${RCC_ST} -o ${TGT}'
	ext_out=['.h']
	def scan(self):
		node=self.inputs[0]
		if not has_xml:
			Logs.error('no xml support was found, the rcc dependencies will be incomplete!')
			return([],[])
		parser=make_parser()
		curHandler=XMLHandler()
		parser.setContentHandler(curHandler)
		fi=open(self.inputs[0].abspath(),'r')
		try:
			parser.parse(fi)
		finally:
			fi.close()
		nodes=[]
		names=[]
		root=self.inputs[0].parent
		for x in curHandler.files:
			nd=root.find_resource(x)
			if nd:nodes.append(nd)
			else:names.append(x)
		return(nodes,names)
class moc(Task.Task):
	color='BLUE'
	run_str='${QT_MOC} ${MOC_FLAGS} ${MOCCPPPATH_ST:INCPATHS} ${MOCDEFINES_ST:DEFINES} ${SRC} ${MOC_ST} ${TGT}'
class ui4(Task.Task):
	color='BLUE'
	run_str='${QT_UIC} ${SRC} -o ${TGT}'
	ext_out=['.h']
class ts2qm(Task.Task):
	color='BLUE'
	run_str='${QT_LRELEASE} ${QT_LRELEASE_FLAGS} ${SRC} -qm ${TGT}'
class qm2rcc(Task.Task):
	color='BLUE'
	after='ts2qm'
	def run(self):
		txt='\n'.join(['<file>%s</file>'%k.path_from(self.outputs[0].parent)for k in self.inputs])
		code='<!DOCTYPE RCC><RCC version="1.0">\n<qresource>\n%s\n</qresource>\n</RCC>'%txt
		self.outputs[0].write(code)
def configure(self):
	self.find_qt4_binaries()
	self.set_qt4_libs_to_check()
	self.set_qt4_defines()
	self.find_qt4_libraries()
	self.add_qt4_rpath()
	self.simplify_qt4_libs()
@conf
def find_qt4_binaries(self):
	env=self.env
	opt=Options.options
	qtdir=getattr(opt,'qtdir','')
	qtbin=getattr(opt,'qtbin','')
	paths=[]
	if qtdir:
		qtbin=os.path.join(qtdir,'bin')
	if not qtdir:
		qtdir=os.environ.get('QT4_ROOT','')
		qtbin=os.environ.get('QT4_BIN',None)or os.path.join(qtdir,'bin')
	if qtbin:
		paths=[qtbin]
	if not qtdir:
		paths=os.environ.get('PATH','').split(os.pathsep)
		paths.append('/usr/share/qt4/bin/')
		try:
			lst=Utils.listdir('/usr/local/Trolltech/')
		except OSError:
			pass
		else:
			if lst:
				lst.sort()
				lst.reverse()
				qtdir='/usr/local/Trolltech/%s/'%lst[0]
				qtbin=os.path.join(qtdir,'bin')
				paths.append(qtbin)
	cand=None
	prev_ver=['4','0','0']
	for qmk in['qmake-qt4','qmake4','qmake']:
		try:
			qmake=self.find_program(qmk,path_list=paths)
		except self.errors.ConfigurationError:
			pass
		else:
			try:
				version=self.cmd_and_log([qmake,'-query','QT_VERSION']).strip()
			except self.errors.WafError:
				pass
			else:
				if version:
					new_ver=version.split('.')
					if new_ver>prev_ver:
						cand=qmake
						prev_ver=new_ver
	if cand:
		self.env.QMAKE=cand
	else:
		self.fatal('Could not find qmake for qt4')
	qtbin=self.cmd_and_log([self.env.QMAKE,'-query','QT_INSTALL_BINS']).strip()+os.sep
	def find_bin(lst,var):
		if var in env:
			return
		for f in lst:
			try:
				ret=self.find_program(f,path_list=paths)
			except self.errors.ConfigurationError:
				pass
			else:
				env[var]=ret
				break
	find_bin(['uic-qt3','uic3'],'QT_UIC3')
	find_bin(['uic-qt4','uic'],'QT_UIC')
	if not env['QT_UIC']:
		self.fatal('cannot find the uic compiler for qt4')
	try:
		uicver=self.cmd_and_log(env['QT_UIC']+" -version 2>&1").strip()
	except self.errors.ConfigurationError:
		self.fatal('this uic compiler is for qt3, add uic for qt4 to your path')
	uicver=uicver.replace('Qt User Interface Compiler ','').replace('User Interface Compiler for Qt','')
	self.msg('Checking for uic version','%s'%uicver)
	if uicver.find(' 3.')!=-1:
		self.fatal('this uic compiler is for qt3, add uic for qt4 to your path')
	find_bin(['moc-qt4','moc'],'QT_MOC')
	find_bin(['rcc'],'QT_RCC')
	find_bin(['lrelease-qt4','lrelease'],'QT_LRELEASE')
	find_bin(['lupdate-qt4','lupdate'],'QT_LUPDATE')
	env['UIC3_ST']='%s -o %s'
	env['UIC_ST']='%s -o %s'
	env['MOC_ST']='-o'
	env['ui_PATTERN']='ui_%s.h'
	env['QT_LRELEASE_FLAGS']=['-silent']
	env.MOCCPPPATH_ST='-I%s'
	env.MOCDEFINES_ST='-D%s'
@conf
def find_qt4_libraries(self):
	qtlibs=getattr(Options.options,'qtlibs',None)or os.environ.get("QT4_LIBDIR",None)
	if not qtlibs:
		try:
			qtlibs=self.cmd_and_log([self.env.QMAKE,'-query','QT_INSTALL_LIBS']).strip()
		except Errors.WafError:
			qtdir=self.cmd_and_log([self.env.QMAKE,'-query','QT_INSTALL_PREFIX']).strip()+os.sep
			qtlibs=os.path.join(qtdir,'lib')
	self.msg('Found the Qt4 libraries in',qtlibs)
	qtincludes=os.environ.get("QT4_INCLUDES",None)or self.cmd_and_log([self.env.QMAKE,'-query','QT_INSTALL_HEADERS']).strip()
	env=self.env
	if not'PKG_CONFIG_PATH'in os.environ:
		os.environ['PKG_CONFIG_PATH']='%s:%s/pkgconfig:/usr/lib/qt4/lib/pkgconfig:/opt/qt4/lib/pkgconfig:/usr/lib/qt4/lib:/opt/qt4/lib'%(qtlibs,qtlibs)
	try:
		if os.environ.get("QT4_XCOMPILE",None):
			raise self.errors.ConfigurationError()
		self.check_cfg(atleast_pkgconfig_version='0.1')
	except self.errors.ConfigurationError:
		for i in self.qt4_vars:
			uselib=i.upper()
			if Utils.unversioned_sys_platform()=="darwin":
				frameworkName=i+".framework"
				qtDynamicLib=os.path.join(qtlibs,frameworkName,i)
				if os.path.exists(qtDynamicLib):
					env.append_unique('FRAMEWORK_'+uselib,i)
					self.msg('Checking for %s'%i,qtDynamicLib,'GREEN')
				else:
					self.msg('Checking for %s'%i,False,'YELLOW')
				env.append_unique('INCLUDES_'+uselib,os.path.join(qtlibs,frameworkName,'Headers'))
			elif env.DEST_OS!="win32":
				qtDynamicLib=os.path.join(qtlibs,"lib"+i+".so")
				qtStaticLib=os.path.join(qtlibs,"lib"+i+".a")
				if os.path.exists(qtDynamicLib):
					env.append_unique('LIB_'+uselib,i)
					self.msg('Checking for %s'%i,qtDynamicLib,'GREEN')
				elif os.path.exists(qtStaticLib):
					env.append_unique('LIB_'+uselib,i)
					self.msg('Checking for %s'%i,qtStaticLib,'GREEN')
				else:
					self.msg('Checking for %s'%i,False,'YELLOW')
				env.append_unique('LIBPATH_'+uselib,qtlibs)
				env.append_unique('INCLUDES_'+uselib,qtincludes)
				env.append_unique('INCLUDES_'+uselib,os.path.join(qtincludes,i))
			else:
				for k in("lib%s.a","lib%s4.a","%s.lib","%s4.lib"):
					lib=os.path.join(qtlibs,k%i)
					if os.path.exists(lib):
						env.append_unique('LIB_'+uselib,i+k[k.find("%s")+2:k.find('.')])
						self.msg('Checking for %s'%i,lib,'GREEN')
						break
				else:
					self.msg('Checking for %s'%i,False,'YELLOW')
				env.append_unique('LIBPATH_'+uselib,qtlibs)
				env.append_unique('INCLUDES_'+uselib,qtincludes)
				env.append_unique('INCLUDES_'+uselib,os.path.join(qtincludes,i))
				uselib=i.upper()+"_debug"
				for k in("lib%sd.a","lib%sd4.a","%sd.lib","%sd4.lib"):
					lib=os.path.join(qtlibs,k%i)
					if os.path.exists(lib):
						env.append_unique('LIB_'+uselib,i+k[k.find("%s")+2:k.find('.')])
						self.msg('Checking for %s'%i,lib,'GREEN')
						break
				else:
					self.msg('Checking for %s'%i,False,'YELLOW')
				env.append_unique('LIBPATH_'+uselib,qtlibs)
				env.append_unique('INCLUDES_'+uselib,qtincludes)
				env.append_unique('INCLUDES_'+uselib,os.path.join(qtincludes,i))
	else:
		for i in self.qt4_vars_debug+self.qt4_vars:
			self.check_cfg(package=i,args='--cflags --libs',mandatory=False)
@conf
def simplify_qt4_libs(self):
	env=self.env
	def process_lib(vars_,coreval):
		for d in vars_:
			var=d.upper()
			if var=='QTCORE':
				continue
			value=env['LIBPATH_'+var]
			if value:
				core=env[coreval]
				accu=[]
				for lib in value:
					if lib in core:
						continue
					accu.append(lib)
				env['LIBPATH_'+var]=accu
	process_lib(self.qt4_vars,'LIBPATH_QTCORE')
	process_lib(self.qt4_vars_debug,'LIBPATH_QTCORE_DEBUG')
@conf
def add_qt4_rpath(self):
	env=self.env
	if getattr(Options.options,'want_rpath',False):
		def process_rpath(vars_,coreval):
			for d in vars_:
				var=d.upper()
				value=env['LIBPATH_'+var]
				if value:
					core=env[coreval]
					accu=[]
					for lib in value:
						if var!='QTCORE':
							if lib in core:
								continue
						accu.append('-Wl,--rpath='+lib)
					env['RPATH_'+var]=accu
		process_rpath(self.qt4_vars,'LIBPATH_QTCORE')
		process_rpath(self.qt4_vars_debug,'LIBPATH_QTCORE_DEBUG')
@conf
def set_qt4_libs_to_check(self):
	if not hasattr(self,'qt4_vars'):
		self.qt4_vars=QT4_LIBS
	self.qt4_vars=Utils.to_list(self.qt4_vars)
	if not hasattr(self,'qt4_vars_debug'):
		self.qt4_vars_debug=[a+'_debug'for a in self.qt4_vars]
	self.qt4_vars_debug=Utils.to_list(self.qt4_vars_debug)
@conf
def set_qt4_defines(self):
	if sys.platform!='win32':
		return
	for x in self.qt4_vars:
		y=x[2:].upper()
		self.env.append_unique('DEFINES_%s'%x.upper(),'QT_%s_LIB'%y)
		self.env.append_unique('DEFINES_%s_DEBUG'%x.upper(),'QT_%s_LIB'%y)
def options(opt):
	opt.add_option('--want-rpath',action='store_true',default=False,dest='want_rpath',help='enable the rpath for qt libraries')
	opt.add_option('--header-ext',type='string',default='',help='header extension for moc files',dest='qt_header_ext')
	for i in'qtdir qtbin qtlibs'.split():
		opt.add_option('--'+i,type='string',default='',dest=i)
	opt.add_option('--translate',action="store_true",help="collect translation strings",dest="trans_qt4",default=False)

########NEW FILE########
__FILENAME__ = ruby
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import os
from waflib import Task,Options,Utils
from waflib.TaskGen import before_method,feature,after_method,Task,extension
from waflib.Configure import conf
@feature('rubyext')
@before_method('apply_incpaths','apply_lib_vars','apply_bundle','apply_link')
def init_rubyext(self):
	self.install_path='${ARCHDIR_RUBY}'
	self.uselib=self.to_list(getattr(self,'uselib',''))
	if not'RUBY'in self.uselib:
		self.uselib.append('RUBY')
	if not'RUBYEXT'in self.uselib:
		self.uselib.append('RUBYEXT')
@feature('rubyext')
@before_method('apply_link','propagate_uselib')
def apply_ruby_so_name(self):
	self.env['cshlib_PATTERN']=self.env['cxxshlib_PATTERN']=self.env['rubyext_PATTERN']
@conf
def check_ruby_version(self,minver=()):
	if Options.options.rubybinary:
		self.env.RUBY=Options.options.rubybinary
	else:
		self.find_program('ruby',var='RUBY')
	ruby=self.env.RUBY
	try:
		version=self.cmd_and_log([ruby,'-e','puts defined?(VERSION) ? VERSION : RUBY_VERSION']).strip()
	except Exception:
		self.fatal('could not determine ruby version')
	self.env.RUBY_VERSION=version
	try:
		ver=tuple(map(int,version.split(".")))
	except Exception:
		self.fatal('unsupported ruby version %r'%version)
	cver=''
	if minver:
		if ver<minver:
			self.fatal('ruby is too old %r'%ver)
		cver='.'.join([str(x)for x in minver])
	else:
		cver=ver
	self.msg('Checking for ruby version %s'%str(minver or''),cver)
@conf
def check_ruby_ext_devel(self):
	if not self.env.RUBY:
		self.fatal('ruby detection is required first')
	if not self.env.CC_NAME and not self.env.CXX_NAME:
		self.fatal('load a c/c++ compiler first')
	version=tuple(map(int,self.env.RUBY_VERSION.split(".")))
	def read_out(cmd):
		return Utils.to_list(self.cmd_and_log([self.env.RUBY,'-rrbconfig','-e',cmd]))
	def read_config(key):
		return read_out('puts Config::CONFIG[%r]'%key)
	ruby=self.env['RUBY']
	archdir=read_config('archdir')
	cpppath=archdir
	if version>=(1,9,0):
		ruby_hdrdir=read_config('rubyhdrdir')
		cpppath+=ruby_hdrdir
		cpppath+=[os.path.join(ruby_hdrdir[0],read_config('arch')[0])]
	self.check(header_name='ruby.h',includes=cpppath,errmsg='could not find ruby header file')
	self.env.LIBPATH_RUBYEXT=read_config('libdir')
	self.env.LIBPATH_RUBYEXT+=archdir
	self.env.INCLUDES_RUBYEXT=cpppath
	self.env.CFLAGS_RUBYEXT=read_config('CCDLFLAGS')
	self.env.rubyext_PATTERN='%s.'+read_config('DLEXT')[0]
	flags=read_config('LDSHARED')
	while flags and flags[0][0]!='-':
		flags=flags[1:]
	if len(flags)>1 and flags[1]=="ppc":
		flags=flags[2:]
	self.env.LINKFLAGS_RUBYEXT=flags
	self.env.LINKFLAGS_RUBYEXT+=read_config('LIBS')
	self.env.LINKFLAGS_RUBYEXT+=read_config('LIBRUBYARG_SHARED')
	if Options.options.rubyarchdir:
		self.env.ARCHDIR_RUBY=Options.options.rubyarchdir
	else:
		self.env.ARCHDIR_RUBY=read_config('sitearchdir')[0]
	if Options.options.rubylibdir:
		self.env.LIBDIR_RUBY=Options.options.rubylibdir
	else:
		self.env.LIBDIR_RUBY=read_config('sitelibdir')[0]
@conf
def check_ruby_module(self,module_name):
	self.start_msg('Ruby module %s'%module_name)
	try:
		self.cmd_and_log([self.env['RUBY'],'-e','require \'%s\';puts 1'%module_name])
	except Exception:
		self.end_msg(False)
		self.fatal('Could not find the ruby module %r'%module_name)
	self.end_msg(True)
@extension('.rb')
def process(self,node):
	tsk=self.create_task('run_ruby',node)
class run_ruby(Task.Task):
	run_str='${RUBY} ${RBFLAGS} -I ${SRC[0].parent.abspath()} ${SRC}'
def options(opt):
	opt.add_option('--with-ruby-archdir',type='string',dest='rubyarchdir',help='Specify directory where to install arch specific files')
	opt.add_option('--with-ruby-libdir',type='string',dest='rubylibdir',help='Specify alternate ruby library path')
	opt.add_option('--with-ruby-binary',type='string',dest='rubybinary',help='Specify alternate ruby binary')

########NEW FILE########
__FILENAME__ = suncc
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import os
from waflib import Utils
from waflib.Tools import ccroot,ar
from waflib.Configure import conf
@conf
def find_scc(conf):
	v=conf.env
	cc=None
	if v['CC']:cc=v['CC']
	elif'CC'in conf.environ:cc=conf.environ['CC']
	if not cc:cc=conf.find_program('cc',var='CC')
	if not cc:conf.fatal('Could not find a Sun C compiler')
	cc=conf.cmd_to_list(cc)
	try:
		conf.cmd_and_log(cc+['-flags'])
	except Exception:
		conf.fatal('%r is not a Sun compiler'%cc)
	v['CC']=cc
	v['CC_NAME']='sun'
	conf.get_suncc_version(cc)
@conf
def scc_common_flags(conf):
	v=conf.env
	v['CC_SRC_F']=[]
	v['CC_TGT_F']=['-c','-o']
	if not v['LINK_CC']:v['LINK_CC']=v['CC']
	v['CCLNK_SRC_F']=''
	v['CCLNK_TGT_F']=['-o']
	v['CPPPATH_ST']='-I%s'
	v['DEFINES_ST']='-D%s'
	v['LIB_ST']='-l%s'
	v['LIBPATH_ST']='-L%s'
	v['STLIB_ST']='-l%s'
	v['STLIBPATH_ST']='-L%s'
	v['SONAME_ST']='-Wl,-h,%s'
	v['SHLIB_MARKER']='-Bdynamic'
	v['STLIB_MARKER']='-Bstatic'
	v['cprogram_PATTERN']='%s'
	v['CFLAGS_cshlib']=['-Kpic','-DPIC']
	v['LINKFLAGS_cshlib']=['-G']
	v['cshlib_PATTERN']='lib%s.so'
	v['LINKFLAGS_cstlib']=['-Bstatic']
	v['cstlib_PATTERN']='lib%s.a'
def configure(conf):
	conf.find_scc()
	conf.find_ar()
	conf.scc_common_flags()
	conf.cc_load_tools()
	conf.cc_add_flags()
	conf.link_add_flags()

########NEW FILE########
__FILENAME__ = suncxx
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import os
from waflib import Utils
from waflib.Tools import ccroot,ar
from waflib.Configure import conf
@conf
def find_sxx(conf):
	v=conf.env
	cc=None
	if v['CXX']:cc=v['CXX']
	elif'CXX'in conf.environ:cc=conf.environ['CXX']
	if not cc:cc=conf.find_program('CC',var='CXX')
	if not cc:cc=conf.find_program('c++',var='CXX')
	if not cc:conf.fatal('Could not find a Sun C++ compiler')
	cc=conf.cmd_to_list(cc)
	try:
		conf.cmd_and_log(cc+['-flags'])
	except Exception:
		conf.fatal('%r is not a Sun compiler'%cc)
	v['CXX']=cc
	v['CXX_NAME']='sun'
	conf.get_suncc_version(cc)
@conf
def sxx_common_flags(conf):
	v=conf.env
	v['CXX_SRC_F']=[]
	v['CXX_TGT_F']=['-c','-o']
	if not v['LINK_CXX']:v['LINK_CXX']=v['CXX']
	v['CXXLNK_SRC_F']=[]
	v['CXXLNK_TGT_F']=['-o']
	v['CPPPATH_ST']='-I%s'
	v['DEFINES_ST']='-D%s'
	v['LIB_ST']='-l%s'
	v['LIBPATH_ST']='-L%s'
	v['STLIB_ST']='-l%s'
	v['STLIBPATH_ST']='-L%s'
	v['SONAME_ST']='-Wl,-h,%s'
	v['SHLIB_MARKER']='-Bdynamic'
	v['STLIB_MARKER']='-Bstatic'
	v['cxxprogram_PATTERN']='%s'
	v['CXXFLAGS_cxxshlib']=['-Kpic','-DPIC']
	v['LINKFLAGS_cxxshlib']=['-G']
	v['cxxshlib_PATTERN']='lib%s.so'
	v['LINKFLAGS_cxxstlib']=['-Bstatic']
	v['cxxstlib_PATTERN']='lib%s.a'
def configure(conf):
	conf.find_sxx()
	conf.find_ar()
	conf.sxx_common_flags()
	conf.cxx_load_tools()
	conf.cxx_add_flags()
	conf.link_add_flags()

########NEW FILE########
__FILENAME__ = tex
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import os,re
from waflib import Utils,Task,Errors,Logs
from waflib.TaskGen import feature,before_method
re_bibunit=re.compile(r'\\(?P<type>putbib)\[(?P<file>[^\[\]]*)\]',re.M)
def bibunitscan(self):
	node=self.inputs[0]
	nodes=[]
	if not node:return nodes
	code=node.read()
	for match in re_bibunit.finditer(code):
		path=match.group('file')
		if path:
			for k in['','.bib']:
				Logs.debug('tex: trying %s%s'%(path,k))
				fi=node.parent.find_resource(path+k)
				if fi:
					nodes.append(fi)
			else:
				Logs.debug('tex: could not find %s'%path)
	Logs.debug("tex: found the following bibunit files: %s"%nodes)
	return nodes
exts_deps_tex=['','.ltx','.tex','.bib','.pdf','.png','.eps','.ps']
exts_tex=['.ltx','.tex']
re_tex=re.compile(r'\\(?P<type>include|bibliography|putbib|includegraphics|input|import|bringin|lstinputlisting)(\[[^\[\]]*\])?{(?P<file>[^{}]*)}',re.M)
g_bibtex_re=re.compile('bibdata',re.M)
class tex(Task.Task):
	bibtex_fun,_=Task.compile_fun('${BIBTEX} ${BIBTEXFLAGS} ${SRCFILE}',shell=False)
	bibtex_fun.__doc__="""
	Execute the program **bibtex**
	"""
	makeindex_fun,_=Task.compile_fun('${MAKEINDEX} ${MAKEINDEXFLAGS} ${SRCFILE}',shell=False)
	makeindex_fun.__doc__="""
	Execute the program **makeindex**
	"""
	def exec_command(self,cmd,**kw):
		bld=self.generator.bld
		try:
			if not kw.get('cwd',None):
				kw['cwd']=bld.cwd
		except AttributeError:
			bld.cwd=kw['cwd']=bld.variant_dir
		return Utils.subprocess.Popen(cmd,**kw).wait()
	def scan_aux(self,node):
		nodes=[node]
		re_aux=re.compile(r'\\@input{(?P<file>[^{}]*)}',re.M)
		def parse_node(node):
			code=node.read()
			for match in re_aux.finditer(code):
				path=match.group('file')
				found=node.parent.find_or_declare(path)
				if found and found not in nodes:
					Logs.debug('tex: found aux node '+found.abspath())
					nodes.append(found)
					parse_node(found)
		parse_node(node)
		return nodes
	def scan(self):
		node=self.inputs[0]
		nodes=[]
		names=[]
		seen=[]
		if not node:return(nodes,names)
		def parse_node(node):
			if node in seen:
				return
			seen.append(node)
			code=node.read()
			global re_tex
			for match in re_tex.finditer(code):
				for path in match.group('file').split(','):
					if path:
						add_name=True
						found=None
						for k in exts_deps_tex:
							Logs.debug('tex: trying %s%s'%(path,k))
							found=node.parent.find_resource(path+k)
							for tsk in self.generator.tasks:
								if not found or found in tsk.outputs:
									break
							else:
								nodes.append(found)
								add_name=False
								for ext in exts_tex:
									if found.name.endswith(ext):
										parse_node(found)
										break
						if add_name:
							names.append(path)
		parse_node(node)
		for x in nodes:
			x.parent.get_bld().mkdir()
		Logs.debug("tex: found the following : %s and names %s"%(nodes,names))
		return(nodes,names)
	def check_status(self,msg,retcode):
		if retcode!=0:
			raise Errors.WafError("%r command exit status %r"%(msg,retcode))
	def bibfile(self):
		for aux_node in self.aux_nodes:
			try:
				ct=aux_node.read()
			except(OSError,IOError):
				Logs.error('Error reading %s: %r'%aux_node.abspath())
				continue
			if g_bibtex_re.findall(ct):
				Logs.warn('calling bibtex')
				self.env.env={}
				self.env.env.update(os.environ)
				self.env.env.update({'BIBINPUTS':self.TEXINPUTS,'BSTINPUTS':self.TEXINPUTS})
				self.env.SRCFILE=aux_node.name[:-4]
				self.check_status('error when calling bibtex',self.bibtex_fun())
	def bibunits(self):
		try:
			bibunits=bibunitscan(self)
		except OSError:
			Logs.error('error bibunitscan')
		else:
			if bibunits:
				fn=['bu'+str(i)for i in xrange(1,len(bibunits)+1)]
				if fn:
					Logs.warn('calling bibtex on bibunits')
				for f in fn:
					self.env.env={'BIBINPUTS':self.TEXINPUTS,'BSTINPUTS':self.TEXINPUTS}
					self.env.SRCFILE=f
					self.check_status('error when calling bibtex',self.bibtex_fun())
	def makeindex(self):
		try:
			idx_path=self.idx_node.abspath()
			os.stat(idx_path)
		except OSError:
			Logs.warn('index file %s absent, not calling makeindex'%idx_path)
		else:
			Logs.warn('calling makeindex')
			self.env.SRCFILE=self.idx_node.name
			self.env.env={}
			self.check_status('error when calling makeindex %s'%idx_path,self.makeindex_fun())
	def bibtopic(self):
		p=self.inputs[0].parent.get_bld()
		if os.path.exists(os.path.join(p.abspath(),'btaux.aux')):
			self.aux_nodes+=p.ant_glob('*[0-9].aux')
	def run(self):
		env=self.env
		if not env['PROMPT_LATEX']:
			env.append_value('LATEXFLAGS','-interaction=batchmode')
			env.append_value('PDFLATEXFLAGS','-interaction=batchmode')
			env.append_value('XELATEXFLAGS','-interaction=batchmode')
		fun=self.texfun
		node=self.inputs[0]
		srcfile=node.abspath()
		texinputs=self.env.TEXINPUTS or''
		self.TEXINPUTS=node.parent.get_bld().abspath()+os.pathsep+node.parent.get_src().abspath()+os.pathsep+texinputs+os.pathsep
		self.cwd=self.inputs[0].parent.get_bld().abspath()
		Logs.warn('first pass on %s'%self.__class__.__name__)
		self.env.env={}
		self.env.env.update(os.environ)
		self.env.env.update({'TEXINPUTS':self.TEXINPUTS})
		self.env.SRCFILE=srcfile
		self.check_status('error when calling latex',fun())
		self.aux_nodes=self.scan_aux(node.change_ext('.aux'))
		self.idx_node=node.change_ext('.idx')
		self.bibtopic()
		self.bibfile()
		self.bibunits()
		self.makeindex()
		hash=''
		for i in range(10):
			prev_hash=hash
			try:
				hashes=[Utils.h_file(x.abspath())for x in self.aux_nodes]
				hash=Utils.h_list(hashes)
			except(OSError,IOError):
				Logs.error('could not read aux.h')
				pass
			if hash and hash==prev_hash:
				break
			Logs.warn('calling %s'%self.__class__.__name__)
			self.env.env={}
			self.env.env.update(os.environ)
			self.env.env.update({'TEXINPUTS':self.TEXINPUTS})
			self.env.SRCFILE=srcfile
			self.check_status('error when calling %s'%self.__class__.__name__,fun())
class latex(tex):
	texfun,vars=Task.compile_fun('${LATEX} ${LATEXFLAGS} ${SRCFILE}',shell=False)
class pdflatex(tex):
	texfun,vars=Task.compile_fun('${PDFLATEX} ${PDFLATEXFLAGS} ${SRCFILE}',shell=False)
class xelatex(tex):
	texfun,vars=Task.compile_fun('${XELATEX} ${XELATEXFLAGS} ${SRCFILE}',shell=False)
class dvips(Task.Task):
	run_str='${DVIPS} ${DVIPSFLAGS} ${SRC} -o ${TGT}'
	color='BLUE'
	after=['latex','pdflatex','xelatex']
class dvipdf(Task.Task):
	run_str='${DVIPDF} ${DVIPDFFLAGS} ${SRC} ${TGT}'
	color='BLUE'
	after=['latex','pdflatex','xelatex']
class pdf2ps(Task.Task):
	run_str='${PDF2PS} ${PDF2PSFLAGS} ${SRC} ${TGT}'
	color='BLUE'
	after=['latex','pdflatex','xelatex']
@feature('tex')
@before_method('process_source')
def apply_tex(self):
	if not getattr(self,'type',None)in['latex','pdflatex','xelatex']:
		self.type='pdflatex'
	tree=self.bld
	outs=Utils.to_list(getattr(self,'outs',[]))
	self.env['PROMPT_LATEX']=getattr(self,'prompt',1)
	deps_lst=[]
	if getattr(self,'deps',None):
		deps=self.to_list(self.deps)
		for filename in deps:
			n=self.path.find_resource(filename)
			if not n:
				self.bld.fatal('Could not find %r for %r'%(filename,self))
			if not n in deps_lst:
				deps_lst.append(n)
	for node in self.to_nodes(self.source):
		if self.type=='latex':
			task=self.create_task('latex',node,node.change_ext('.dvi'))
		elif self.type=='pdflatex':
			task=self.create_task('pdflatex',node,node.change_ext('.pdf'))
		elif self.type=='xelatex':
			task=self.create_task('xelatex',node,node.change_ext('.pdf'))
		task.env=self.env
		if deps_lst:
			try:
				lst=tree.node_deps[task.uid()]
				for n in deps_lst:
					if not n in lst:
						lst.append(n)
			except KeyError:
				tree.node_deps[task.uid()]=deps_lst
		v=dict(os.environ)
		p=node.parent.abspath()+os.pathsep+self.path.abspath()+os.pathsep+self.path.get_bld().abspath()+os.pathsep+v.get('TEXINPUTS','')+os.pathsep
		v['TEXINPUTS']=p
		if self.type=='latex':
			if'ps'in outs:
				tsk=self.create_task('dvips',task.outputs,node.change_ext('.ps'))
				tsk.env.env=dict(v)
			if'pdf'in outs:
				tsk=self.create_task('dvipdf',task.outputs,node.change_ext('.pdf'))
				tsk.env.env=dict(v)
		elif self.type=='pdflatex':
			if'ps'in outs:
				self.create_task('pdf2ps',task.outputs,node.change_ext('.ps'))
	self.source=[]
def configure(self):
	v=self.env
	for p in'tex latex pdflatex xelatex bibtex dvips dvipdf ps2pdf makeindex pdf2ps'.split():
		try:
			self.find_program(p,var=p.upper())
		except self.errors.ConfigurationError:
			pass
	v['DVIPSFLAGS']='-Ppdf'

########NEW FILE########
__FILENAME__ = vala
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import os.path,shutil,re
from waflib import Context,Task,Utils,Logs,Options,Errors
from waflib.TaskGen import extension,taskgen_method
from waflib.Configure import conf
class valac(Task.Task):
	vars=["VALAC","VALAC_VERSION","VALAFLAGS"]
	ext_out=['.h']
	def run(self):
		cmd=[self.env['VALAC']]+self.env['VALAFLAGS']
		cmd.extend([a.abspath()for a in self.inputs])
		ret=self.exec_command(cmd,cwd=self.outputs[0].parent.abspath())
		if ret:
			return ret
		for x in self.outputs:
			if id(x.parent)!=id(self.outputs[0].parent):
				shutil.move(self.outputs[0].parent.abspath()+os.sep+x.name,x.abspath())
		if self.generator.dump_deps_node:
			self.generator.dump_deps_node.write('\n'.join(self.generator.packages))
		return ret
valac=Task.update_outputs(valac)
@taskgen_method
def init_vala_task(self):
	self.profile=getattr(self,'profile','gobject')
	if self.profile=='gobject':
		self.uselib=Utils.to_list(getattr(self,'uselib',[]))
		if not'GOBJECT'in self.uselib:
			self.uselib.append('GOBJECT')
	def addflags(flags):
		self.env.append_value('VALAFLAGS',flags)
	if self.profile:
		addflags('--profile=%s'%self.profile)
	if hasattr(self,'threading'):
		if self.profile=='gobject':
			if not'GTHREAD'in self.uselib:
				self.uselib.append('GTHREAD')
		else:
			Logs.warn("Profile %s means no threading support"%self.profile)
			self.threading=False
		if self.threading:
			addflags('--threading')
	valatask=self.valatask
	self.is_lib='cprogram'not in self.features
	if self.is_lib:
		addflags('--library=%s'%self.target)
		h_node=self.path.find_or_declare('%s.h'%self.target)
		valatask.outputs.append(h_node)
		addflags('--header=%s'%h_node.name)
		valatask.outputs.append(self.path.find_or_declare('%s.vapi'%self.target))
		if getattr(self,'gir',None):
			gir_node=self.path.find_or_declare('%s.gir'%self.gir)
			addflags('--gir=%s'%gir_node.name)
			valatask.outputs.append(gir_node)
	self.vala_target_glib=getattr(self,'vala_target_glib',getattr(Options.options,'vala_target_glib',None))
	if self.vala_target_glib:
		addflags('--target-glib=%s'%self.vala_target_glib)
	addflags(['--define=%s'%x for x in getattr(self,'vala_defines',[])])
	packages_private=Utils.to_list(getattr(self,'packages_private',[]))
	addflags(['--pkg=%s'%x for x in packages_private])
	def _get_api_version():
		api_version='1.0'
		if hasattr(Context.g_module,'API_VERSION'):
			version=Context.g_module.API_VERSION.split(".")
			if version[0]=="0":
				api_version="0."+version[1]
			else:
				api_version=version[0]+".0"
		return api_version
	self.includes=Utils.to_list(getattr(self,'includes',[]))
	self.uselib=self.to_list(getattr(self,'uselib',[]))
	valatask.install_path=getattr(self,'install_path','')
	valatask.vapi_path=getattr(self,'vapi_path','${DATAROOTDIR}/vala/vapi')
	valatask.pkg_name=getattr(self,'pkg_name',self.env['PACKAGE'])
	valatask.header_path=getattr(self,'header_path','${INCLUDEDIR}/%s-%s'%(valatask.pkg_name,_get_api_version()))
	valatask.install_binding=getattr(self,'install_binding',True)
	self.packages=packages=Utils.to_list(getattr(self,'packages',[]))
	self.vapi_dirs=vapi_dirs=Utils.to_list(getattr(self,'vapi_dirs',[]))
	includes=[]
	if hasattr(self,'use'):
		local_packages=Utils.to_list(self.use)[:]
		seen=[]
		while len(local_packages)>0:
			package=local_packages.pop()
			if package in seen:
				continue
			seen.append(package)
			try:
				package_obj=self.bld.get_tgen_by_name(package)
			except Errors.WafError:
				continue
			package_name=package_obj.target
			package_node=package_obj.path
			package_dir=package_node.path_from(self.path)
			for task in package_obj.tasks:
				for output in task.outputs:
					if output.name==package_name+".vapi":
						valatask.set_run_after(task)
						if package_name not in packages:
							packages.append(package_name)
						if package_dir not in vapi_dirs:
							vapi_dirs.append(package_dir)
						if package_dir not in includes:
							includes.append(package_dir)
			if hasattr(package_obj,'use'):
				lst=self.to_list(package_obj.use)
				lst.reverse()
				local_packages=[pkg for pkg in lst if pkg not in seen]+local_packages
	addflags(['--pkg=%s'%p for p in packages])
	for vapi_dir in vapi_dirs:
		v_node=self.path.find_dir(vapi_dir)
		if not v_node:
			Logs.warn('Unable to locate Vala API directory: %r'%vapi_dir)
		else:
			addflags('--vapidir=%s'%v_node.abspath())
			addflags('--vapidir=%s'%v_node.get_bld().abspath())
	self.dump_deps_node=None
	if self.is_lib and self.packages:
		self.dump_deps_node=self.path.find_or_declare('%s.deps'%self.target)
		valatask.outputs.append(self.dump_deps_node)
	self.includes.append(self.bld.srcnode.abspath())
	self.includes.append(self.bld.bldnode.abspath())
	for include in includes:
		try:
			self.includes.append(self.path.find_dir(include).abspath())
			self.includes.append(self.path.find_dir(include).get_bld().abspath())
		except AttributeError:
			Logs.warn("Unable to locate include directory: '%s'"%include)
	if self.is_lib and valatask.install_binding:
		headers_list=[o for o in valatask.outputs if o.suffix()==".h"]
		try:
			self.install_vheader.source=headers_list
		except AttributeError:
			self.install_vheader=self.bld.install_files(valatask.header_path,headers_list,self.env)
		vapi_list=[o for o in valatask.outputs if(o.suffix()in(".vapi",".deps"))]
		try:
			self.install_vapi.source=vapi_list
		except AttributeError:
			self.install_vapi=self.bld.install_files(valatask.vapi_path,vapi_list,self.env)
		gir_list=[o for o in valatask.outputs if o.suffix()=='.gir']
		try:
			self.install_gir.source=gir_list
		except AttributeError:
			self.install_gir=self.bld.install_files(getattr(self,'gir_path','${DATAROOTDIR}/gir-1.0'),gir_list,self.env)
@extension('.vala','.gs')
def vala_file(self,node):
	try:
		valatask=self.valatask
	except AttributeError:
		valatask=self.valatask=self.create_task('valac')
		self.init_vala_task()
	valatask.inputs.append(node)
	c_node=node.change_ext('.c')
	valatask.outputs.append(c_node)
	self.source.append(c_node)
@conf
def find_valac(self,valac_name,min_version):
	valac=self.find_program(valac_name,var='VALAC')
	try:
		output=self.cmd_and_log(valac+' --version')
	except Exception:
		valac_version=None
	else:
		ver=re.search(r'\d+.\d+.\d+',output).group(0).split('.')
		valac_version=tuple([int(x)for x in ver])
	self.msg('Checking for %s version >= %r'%(valac_name,min_version),valac_version,valac_version and valac_version>=min_version)
	if valac and valac_version<min_version:
		self.fatal("%s version %r is too old, need >= %r"%(valac_name,valac_version,min_version))
	self.env['VALAC_VERSION']=valac_version
	return valac
@conf
def check_vala(self,min_version=(0,8,0),branch=None):
	if not branch:
		branch=min_version[:2]
	try:
		find_valac(self,'valac-%d.%d'%(branch[0],branch[1]),min_version)
	except self.errors.ConfigurationError:
		find_valac(self,'valac',min_version)
@conf
def check_vala_deps(self):
	if not self.env['HAVE_GOBJECT']:
		pkg_args={'package':'gobject-2.0','uselib_store':'GOBJECT','args':'--cflags --libs'}
		if getattr(Options.options,'vala_target_glib',None):
			pkg_args['atleast_version']=Options.options.vala_target_glib
		self.check_cfg(**pkg_args)
	if not self.env['HAVE_GTHREAD']:
		pkg_args={'package':'gthread-2.0','uselib_store':'GTHREAD','args':'--cflags --libs'}
		if getattr(Options.options,'vala_target_glib',None):
			pkg_args['atleast_version']=Options.options.vala_target_glib
		self.check_cfg(**pkg_args)
def configure(self):
	self.load('gnu_dirs')
	self.check_vala_deps()
	self.check_vala()
	self.env.VALAFLAGS=['-C','--quiet']
def options(opt):
	opt.load('gnu_dirs')
	valaopts=opt.add_option_group('Vala Compiler Options')
	valaopts.add_option('--vala-target-glib',default=None,dest='vala_target_glib',metavar='MAJOR.MINOR',help='Target version of glib for Vala GObject code generation')

########NEW FILE########
__FILENAME__ = waf_unit_test
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import os,sys
from waflib.TaskGen import feature,after_method
from waflib import Utils,Task,Logs,Options
testlock=Utils.threading.Lock()
@feature('test')
@after_method('apply_link')
def make_test(self):
	if getattr(self,'link_task',None):
		self.create_task('utest',self.link_task.outputs)
class utest(Task.Task):
	color='PINK'
	after=['vnum','inst']
	vars=[]
	def runnable_status(self):
		if getattr(Options.options,'no_tests',False):
			return Task.SKIP_ME
		ret=super(utest,self).runnable_status()
		if ret==Task.SKIP_ME:
			if getattr(Options.options,'all_tests',False):
				return Task.RUN_ME
		return ret
	def run(self):
		filename=self.inputs[0].abspath()
		self.ut_exec=getattr(self.generator,'ut_exec',[filename])
		if getattr(self.generator,'ut_fun',None):
			self.generator.ut_fun(self)
		try:
			fu=getattr(self.generator.bld,'all_test_paths')
		except AttributeError:
			fu=os.environ.copy()
			lst=[]
			for g in self.generator.bld.groups:
				for tg in g:
					if getattr(tg,'link_task',None):
						s=tg.link_task.outputs[0].parent.abspath()
						if s not in lst:
							lst.append(s)
			def add_path(dct,path,var):
				dct[var]=os.pathsep.join(Utils.to_list(path)+[os.environ.get(var,'')])
			if Utils.is_win32:
				add_path(fu,lst,'PATH')
			elif Utils.unversioned_sys_platform()=='darwin':
				add_path(fu,lst,'DYLD_LIBRARY_PATH')
				add_path(fu,lst,'LD_LIBRARY_PATH')
			else:
				add_path(fu,lst,'LD_LIBRARY_PATH')
			self.generator.bld.all_test_paths=fu
		cwd=getattr(self.generator,'ut_cwd','')or self.inputs[0].parent.abspath()
		testcmd=getattr(Options.options,'testcmd',False)
		if testcmd:
			self.ut_exec=(testcmd%self.ut_exec[0]).split(' ')
		proc=Utils.subprocess.Popen(self.ut_exec,cwd=cwd,env=fu,stderr=Utils.subprocess.PIPE,stdout=Utils.subprocess.PIPE)
		(stdout,stderr)=proc.communicate()
		tup=(filename,proc.returncode,stdout,stderr)
		self.generator.utest_result=tup
		testlock.acquire()
		try:
			bld=self.generator.bld
			Logs.debug("ut: %r",tup)
			try:
				bld.utest_results.append(tup)
			except AttributeError:
				bld.utest_results=[tup]
		finally:
			testlock.release()
def summary(bld):
	lst=getattr(bld,'utest_results',[])
	if lst:
		Logs.pprint('CYAN','execution summary')
		total=len(lst)
		tfail=len([x for x in lst if x[1]])
		Logs.pprint('CYAN','  tests that pass %d/%d'%(total-tfail,total))
		for(f,code,out,err)in lst:
			if not code:
				Logs.pprint('CYAN','    %s'%f)
		Logs.pprint('CYAN','  tests that fail %d/%d'%(tfail,total))
		for(f,code,out,err)in lst:
			if code:
				Logs.pprint('CYAN','    %s'%f)
def set_exit_code(bld):
	lst=getattr(bld,'utest_results',[])
	for(f,code,out,err)in lst:
		if code:
			msg=[]
			if out:
				msg.append('stdout:%s%s'%(os.linesep,out.decode('utf-8')))
			if err:
				msg.append('stderr:%s%s'%(os.linesep,err.decode('utf-8')))
			bld.fatal(os.linesep.join(msg))
def options(opt):
	opt.add_option('--notests',action='store_true',default=False,help='Exec no unit tests',dest='no_tests')
	opt.add_option('--alltests',action='store_true',default=False,help='Exec all unit tests',dest='all_tests')
	opt.add_option('--testcmd',action='store',default=False,help='Run the unit tests using the test-cmd string'' example "--test-cmd="valgrind --error-exitcode=1'' %s" to run under valgrind',dest='testcmd')

########NEW FILE########
__FILENAME__ = winres
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import re,traceback
from waflib import Task,Logs,Utils
from waflib.TaskGen import extension
from waflib.Tools import c_preproc
@extension('.rc')
def rc_file(self,node):
	obj_ext='.rc.o'
	if self.env['WINRC_TGT_F']=='/fo':
		obj_ext='.res'
	rctask=self.create_task('winrc',node,node.change_ext(obj_ext))
	try:
		self.compiled_tasks.append(rctask)
	except AttributeError:
		self.compiled_tasks=[rctask]
re_lines=re.compile('(?:^[ \t]*(#|%:)[ \t]*(ifdef|ifndef|if|else|elif|endif|include|import|define|undef|pragma)[ \t]*(.*?)\s*$)|''(?:^\w+[ \t]*(ICON|BITMAP|CURSOR|HTML|FONT|MESSAGETABLE|TYPELIB|REGISTRY|D3DFX)[ \t]*(.*?)\s*$)',re.IGNORECASE|re.MULTILINE)
class rc_parser(c_preproc.c_parser):
	def filter_comments(self,filepath):
		code=Utils.readf(filepath)
		if c_preproc.use_trigraphs:
			for(a,b)in c_preproc.trig_def:code=code.split(a).join(b)
		code=c_preproc.re_nl.sub('',code)
		code=c_preproc.re_cpp.sub(c_preproc.repl,code)
		ret=[]
		for m in re.finditer(re_lines,code):
			if m.group(2):
				ret.append((m.group(2),m.group(3)))
			else:
				ret.append(('include',m.group(5)))
		return ret
	def addlines(self,node):
		self.currentnode_stack.append(node.parent)
		filepath=node.abspath()
		self.count_files+=1
		if self.count_files>c_preproc.recursion_limit:
			raise c_preproc.PreprocError("recursion limit exceeded")
		pc=self.parse_cache
		Logs.debug('preproc: reading file %r',filepath)
		try:
			lns=pc[filepath]
		except KeyError:
			pass
		else:
			self.lines.extend(lns)
			return
		try:
			lines=self.filter_comments(filepath)
			lines.append((c_preproc.POPFILE,''))
			lines.reverse()
			pc[filepath]=lines
			self.lines.extend(lines)
		except IOError:
			raise c_preproc.PreprocError("could not read the file %s"%filepath)
		except Exception:
			if Logs.verbose>0:
				Logs.error("parsing %s failed"%filepath)
				traceback.print_exc()
class winrc(Task.Task):
	run_str='${WINRC} ${WINRCFLAGS} ${CPPPATH_ST:INCPATHS} ${DEFINES_ST:DEFINES} ${WINRC_TGT_F} ${TGT} ${WINRC_SRC_F} ${SRC}'
	color='BLUE'
	def scan(self):
		tmp=rc_parser(self.generator.includes_nodes)
		tmp.start(self.inputs[0],self.env)
		nodes=tmp.nodes
		names=tmp.names
		if Logs.verbose:
			Logs.debug('deps: deps for %s: %r; unresolved %r'%(str(self),nodes,names))
		return(nodes,names)
def configure(conf):
	v=conf.env
	v['WINRC_TGT_F']='-o'
	v['WINRC_SRC_F']='-i'
	if not conf.env.WINRC:
		if v.CC_NAME=='msvc':
			conf.find_program('RC',var='WINRC',path_list=v['PATH'])
			v['WINRC_TGT_F']='/fo'
			v['WINRC_SRC_F']=''
		else:
			conf.find_program('windres',var='WINRC',path_list=v['PATH'])
	if not conf.env.WINRC:
		conf.fatal('winrc was not found!')
	v['WINRCFLAGS']=[]

########NEW FILE########
__FILENAME__ = xlc
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

from waflib.Tools import ccroot,ar
from waflib.Configure import conf
@conf
def find_xlc(conf):
	cc=conf.find_program(['xlc_r','xlc'],var='CC')
	cc=conf.cmd_to_list(cc)
	conf.get_xlc_version(cc)
	conf.env.CC_NAME='xlc'
	conf.env.CC=cc
@conf
def xlc_common_flags(conf):
	v=conf.env
	v['CC_SRC_F']=[]
	v['CC_TGT_F']=['-c','-o']
	if not v['LINK_CC']:v['LINK_CC']=v['CC']
	v['CCLNK_SRC_F']=[]
	v['CCLNK_TGT_F']=['-o']
	v['CPPPATH_ST']='-I%s'
	v['DEFINES_ST']='-D%s'
	v['LIB_ST']='-l%s'
	v['LIBPATH_ST']='-L%s'
	v['STLIB_ST']='-l%s'
	v['STLIBPATH_ST']='-L%s'
	v['RPATH_ST']='-Wl,-rpath,%s'
	v['SONAME_ST']=[]
	v['SHLIB_MARKER']=[]
	v['STLIB_MARKER']=[]
	v['LINKFLAGS_cprogram']=['-Wl,-brtl']
	v['cprogram_PATTERN']='%s'
	v['CFLAGS_cshlib']=['-fPIC']
	v['LINKFLAGS_cshlib']=['-G','-Wl,-brtl,-bexpfull']
	v['cshlib_PATTERN']='lib%s.so'
	v['LINKFLAGS_cstlib']=[]
	v['cstlib_PATTERN']='lib%s.a'
def configure(conf):
	conf.find_xlc()
	conf.find_ar()
	conf.xlc_common_flags()
	conf.cc_load_tools()
	conf.cc_add_flags()
	conf.link_add_flags()

########NEW FILE########
__FILENAME__ = xlcxx
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

from waflib.Tools import ccroot,ar
from waflib.Configure import conf
@conf
def find_xlcxx(conf):
	cxx=conf.find_program(['xlc++_r','xlc++'],var='CXX')
	cxx=conf.cmd_to_list(cxx)
	conf.get_xlc_version(cxx)
	conf.env.CXX_NAME='xlc++'
	conf.env.CXX=cxx
@conf
def xlcxx_common_flags(conf):
	v=conf.env
	v['CXX_SRC_F']=[]
	v['CXX_TGT_F']=['-c','-o']
	if not v['LINK_CXX']:v['LINK_CXX']=v['CXX']
	v['CXXLNK_SRC_F']=[]
	v['CXXLNK_TGT_F']=['-o']
	v['CPPPATH_ST']='-I%s'
	v['DEFINES_ST']='-D%s'
	v['LIB_ST']='-l%s'
	v['LIBPATH_ST']='-L%s'
	v['STLIB_ST']='-l%s'
	v['STLIBPATH_ST']='-L%s'
	v['RPATH_ST']='-Wl,-rpath,%s'
	v['SONAME_ST']=[]
	v['SHLIB_MARKER']=[]
	v['STLIB_MARKER']=[]
	v['LINKFLAGS_cxxprogram']=['-Wl,-brtl']
	v['cxxprogram_PATTERN']='%s'
	v['CXXFLAGS_cxxshlib']=['-fPIC']
	v['LINKFLAGS_cxxshlib']=['-G','-Wl,-brtl,-bexpfull']
	v['cxxshlib_PATTERN']='lib%s.so'
	v['LINKFLAGS_cxxstlib']=[]
	v['cxxstlib_PATTERN']='lib%s.a'
def configure(conf):
	conf.find_xlcxx()
	conf.find_ar()
	conf.xlcxx_common_flags()
	conf.cxx_load_tools()
	conf.cxx_add_flags()
	conf.link_add_flags()

########NEW FILE########
__FILENAME__ = Utils
#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import os,sys,errno,traceback,inspect,re,shutil,datetime,gc
import subprocess
try:
	from collections import deque
except ImportError:
	class deque(list):
		def popleft(self):
			return self.pop(0)
try:
	import _winreg as winreg
except ImportError:
	try:
		import winreg
	except ImportError:
		winreg=None
from waflib import Errors
try:
	from collections import UserDict
except ImportError:
	from UserDict import UserDict
try:
	from hashlib import md5
except ImportError:
	try:
		from md5 import md5
	except ImportError:
		pass
try:
	import threading
except ImportError:
	class threading(object):
		pass
	class Lock(object):
		def acquire(self):
			pass
		def release(self):
			pass
	threading.Lock=threading.Thread=Lock
else:
	run_old=threading.Thread.run
	def run(*args,**kwargs):
		try:
			run_old(*args,**kwargs)
		except(KeyboardInterrupt,SystemExit):
			raise
		except Exception:
			sys.excepthook(*sys.exc_info())
	threading.Thread.run=run
SIG_NIL='iluvcuteoverload'
O644=420
O755=493
rot_chr=['\\','|','/','-']
rot_idx=0
try:
	from collections import defaultdict
except ImportError:
	class defaultdict(dict):
		def __init__(self,default_factory):
			super(defaultdict,self).__init__()
			self.default_factory=default_factory
		def __getitem__(self,key):
			try:
				return super(defaultdict,self).__getitem__(key)
			except KeyError:
				value=self.default_factory()
				self[key]=value
				return value
is_win32=sys.platform in('win32','cli')
indicator='\x1b[K%s%s%s\r'
if is_win32 and'NOCOLOR'in os.environ:
	indicator='%s%s%s\r'
def readf(fname,m='r',encoding='ISO8859-1'):
	if sys.hexversion>0x3000000 and not'b'in m:
		m+='b'
		f=open(fname,m)
		try:
			txt=f.read()
		finally:
			f.close()
		txt=txt.decode(encoding)
	else:
		f=open(fname,m)
		try:
			txt=f.read()
		finally:
			f.close()
	return txt
def writef(fname,data,m='w',encoding='ISO8859-1'):
	if sys.hexversion>0x3000000 and not'b'in m:
		data=data.encode(encoding)
		m+='b'
	f=open(fname,m)
	try:
		f.write(data)
	finally:
		f.close()
def h_file(fname):
	f=open(fname,'rb')
	m=md5()
	try:
		while fname:
			fname=f.read(200000)
			m.update(fname)
	finally:
		f.close()
	return m.digest()
if hasattr(os,'O_NOINHERIT')and sys.hexversion<0x3040000:
	def readf_win32(f,m='r',encoding='ISO8859-1'):
		flags=os.O_NOINHERIT|os.O_RDONLY
		if'b'in m:
			flags|=os.O_BINARY
		if'+'in m:
			flags|=os.O_RDWR
		try:
			fd=os.open(f,flags)
		except OSError:
			raise IOError('Cannot read from %r'%f)
		if sys.hexversion>0x3000000 and not'b'in m:
			m+='b'
			f=os.fdopen(fd,m)
			try:
				txt=f.read()
			finally:
				f.close()
			txt=txt.decode(encoding)
		else:
			f=os.fdopen(fd,m)
			try:
				txt=f.read()
			finally:
				f.close()
		return txt
	def writef_win32(f,data,m='w',encoding='ISO8859-1'):
		if sys.hexversion>0x3000000 and not'b'in m:
			data=data.encode(encoding)
			m+='b'
		flags=os.O_CREAT|os.O_TRUNC|os.O_WRONLY|os.O_NOINHERIT
		if'b'in m:
			flags|=os.O_BINARY
		if'+'in m:
			flags|=os.O_RDWR
		try:
			fd=os.open(f,flags)
		except OSError:
			raise IOError('Cannot write to %r'%f)
		f=os.fdopen(fd,m)
		try:
			f.write(data)
		finally:
			f.close()
	def h_file_win32(fname):
		try:
			fd=os.open(fname,os.O_BINARY|os.O_RDONLY|os.O_NOINHERIT)
		except OSError:
			raise IOError('Cannot read from %r'%fname)
		f=os.fdopen(fd,'rb')
		m=md5()
		try:
			while fname:
				fname=f.read(200000)
				m.update(fname)
		finally:
			f.close()
		return m.digest()
	readf_old=readf
	writef_old=writef
	h_file_old=h_file
	readf=readf_win32
	writef=writef_win32
	h_file=h_file_win32
try:
	x=''.encode('hex')
except LookupError:
	import binascii
	def to_hex(s):
		ret=binascii.hexlify(s)
		if not isinstance(ret,str):
			ret=ret.decode('utf-8')
		return ret
else:
	def to_hex(s):
		return s.encode('hex')
to_hex.__doc__="""
Return the hexadecimal representation of a string

:param s: string to convert
:type s: string
"""
listdir=os.listdir
if is_win32:
	def listdir_win32(s):
		if not s:
			try:
				import ctypes
			except ImportError:
				return[x+':\\'for x in list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')]
			else:
				dlen=4
				maxdrives=26
				buf=ctypes.create_string_buffer(maxdrives*dlen)
				ndrives=ctypes.windll.kernel32.GetLogicalDriveStringsA(maxdrives*dlen,ctypes.byref(buf))
				return[str(buf.raw[4*i:4*i+2].decode('ascii'))for i in range(int(ndrives/dlen))]
		if len(s)==2 and s[1]==":":
			s+=os.sep
		if not os.path.isdir(s):
			e=OSError('%s is not a directory'%s)
			e.errno=errno.ENOENT
			raise e
		return os.listdir(s)
	listdir=listdir_win32
def num2ver(ver):
	if isinstance(ver,str):
		ver=tuple(ver.split('.'))
	if isinstance(ver,tuple):
		ret=0
		for i in range(4):
			if i<len(ver):
				ret+=256**(3-i)*int(ver[i])
		return ret
	return ver
def ex_stack():
	exc_type,exc_value,tb=sys.exc_info()
	exc_lines=traceback.format_exception(exc_type,exc_value,tb)
	return''.join(exc_lines)
def to_list(sth):
	if isinstance(sth,str):
		return sth.split()
	else:
		return sth
re_nl=re.compile('\r*\n',re.M)
def str_to_dict(txt):
	tbl={}
	lines=re_nl.split(txt)
	for x in lines:
		x=x.strip()
		if not x or x.startswith('#')or x.find('=')<0:
			continue
		tmp=x.split('=')
		tbl[tmp[0].strip()]='='.join(tmp[1:]).strip()
	return tbl
def split_path(path):
	return path.split('/')
def split_path_cygwin(path):
	if path.startswith('//'):
		ret=path.split('/')[2:]
		ret[0]='/'+ret[0]
		return ret
	return path.split('/')
re_sp=re.compile('[/\\\\]')
def split_path_win32(path):
	if path.startswith('\\\\'):
		ret=re.split(re_sp,path)[2:]
		ret[0]='\\'+ret[0]
		return ret
	return re.split(re_sp,path)
if sys.platform=='cygwin':
	split_path=split_path_cygwin
elif is_win32:
	split_path=split_path_win32
split_path.__doc__="""
Split a path by / or \\. This function is not like os.path.split

:type  path: string
:param path: path to split
:return:     list of strings
"""
def check_dir(path):
	if not os.path.isdir(path):
		try:
			os.makedirs(path)
		except OSError ,e:
			if not os.path.isdir(path):
				raise Errors.WafError('Cannot create the folder %r'%path,ex=e)
def def_attrs(cls,**kw):
	for k,v in kw.items():
		if not hasattr(cls,k):
			setattr(cls,k,v)
def quote_define_name(s):
	fu=re.compile("[^a-zA-Z0-9]").sub("_",s)
	fu=fu.upper()
	return fu
def h_list(lst):
	m=md5()
	m.update(str(lst))
	return m.digest()
def h_fun(fun):
	try:
		return fun.code
	except AttributeError:
		try:
			h=inspect.getsource(fun)
		except IOError:
			h="nocode"
		try:
			fun.code=h
		except AttributeError:
			pass
		return h
reg_subst=re.compile(r"(\\\\)|(\$\$)|\$\{([^}]+)\}")
def subst_vars(expr,params):
	def repl_var(m):
		if m.group(1):
			return'\\'
		if m.group(2):
			return'$'
		try:
			return params.get_flat(m.group(3))
		except AttributeError:
			return params[m.group(3)]
	return reg_subst.sub(repl_var,expr)
def destos_to_binfmt(key):
	if key=='darwin':
		return'mac-o'
	elif key in('win32','cygwin','uwin','msys'):
		return'pe'
	return'elf'
def unversioned_sys_platform():
	s=sys.platform
	if s=='java':
		from java.lang import System
		s=System.getProperty('os.name')
		if s=='Mac OS X':
			return'darwin'
		elif s.startswith('Windows '):
			return'win32'
		elif s=='OS/2':
			return'os2'
		elif s=='HP-UX':
			return'hpux'
		elif s in('SunOS','Solaris'):
			return'sunos'
		else:s=s.lower()
	if s=='powerpc':
		return'darwin'
	if s=='win32'or s.endswith('os2')and s!='sunos2':return s
	return re.split('\d+$',s)[0]
def nada(*k,**kw):
	pass
class Timer(object):
	def __init__(self):
		self.start_time=datetime.datetime.utcnow()
	def __str__(self):
		delta=datetime.datetime.utcnow()-self.start_time
		days=int(delta.days)
		hours=delta.seconds//3600
		minutes=(delta.seconds-hours*3600)//60
		seconds=delta.seconds-hours*3600-minutes*60+float(delta.microseconds)/1000/1000
		result=''
		if days:
			result+='%dd'%days
		if days or hours:
			result+='%dh'%hours
		if days or hours or minutes:
			result+='%dm'%minutes
		return'%s%.3fs'%(result,seconds)
if is_win32:
	old=shutil.copy2
	def copy2(src,dst):
		old(src,dst)
		shutil.copystat(src,dst)
	setattr(shutil,'copy2',copy2)
if os.name=='java':
	try:
		gc.disable()
		gc.enable()
	except NotImplementedError:
		gc.disable=gc.enable
def read_la_file(path):
	sp=re.compile(r'^([^=]+)=\'(.*)\'$')
	dc={}
	for line in readf(path).splitlines():
		try:
			_,left,right,_=sp.split(line.strip())
			dc[left]=right
		except ValueError:
			pass
	return dc
def nogc(fun):
	def f(*k,**kw):
		try:
			gc.disable()
			ret=fun(*k,**kw)
		finally:
			gc.enable()
		return ret
	f.__doc__=fun.__doc__
	return f
def run_once(fun):
	cache={}
	def wrap(k):
		try:
			return cache[k]
		except KeyError:
			ret=fun(k)
			cache[k]=ret
			return ret
	wrap.__cache__=cache
	return wrap
def get_registry_app_path(key,filename):
	if not winreg:
		return None
	try:
		result=winreg.QueryValue(key,"Software\\Microsoft\\Windows\\CurrentVersion\\App Paths\\%s.exe"%filename[0])
	except WindowsError:
		pass
	else:
		if os.path.isfile(result):
			return result

########NEW FILE########
