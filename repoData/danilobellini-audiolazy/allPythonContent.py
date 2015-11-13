__FILENAME__ = lazy_analysis
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Sun Jul 29 2012
# danilo [dot] bellini [at] gmail [dot] com
"""
Audio analysis and block processing module
"""

from __future__ import division

from math import cos, pi
from collections import deque, Sequence, Iterable
import operator

# Audiolazy internal imports
from .lazy_core import StrategyDict
from .lazy_stream import tostream, thub, Stream
from .lazy_math import cexp, ceil
from .lazy_filters import lowpass, z
from .lazy_compat import xrange, xmap, xzip

__all__ = ["window", "acorr", "lag_matrix", "dft", "zcross", "envelope",
           "maverage", "clip", "unwrap", "amdf", "overlap_add"]


window = StrategyDict("window")


@window.strategy("hamming")
def window(size):
  """
  Hamming window function with the given size.

  Returns
  -------
  List with the desired window samples. Max value is one (1.0).

  """

  if size == 1:
    return [1.0]
  return [.54 - .46 * cos(2 * pi * n / (size - 1))
          for n in xrange(size)]


@window.strategy("rectangular", "rect")
def window(size):
  """
  Rectangular window function with the given size.

  Returns
  -------
  List with the desired window samples. All values are ones (1.0).

  """
  return [1.0 for n in xrange(size)]


@window.strategy("bartlett")
def window(size):
  """
  Bartlett (triangular with zero-valued endpoints) window function with the
  given size.

  Returns
  -------
  List with the desired window samples. Max value is one (1.0).

  See Also
  --------
  window.triangular :
    Triangular with no zero end-point.

  """
  if size == 1:
    return [1.0]
  return [1 - 2.0 / (size - 1) * abs(n - (size - 1) / 2.0)
          for n in xrange(size)]


@window.strategy("triangular", "triangle")
def window(size):
  """
  Triangular (with no zero end-point) window function with the given size.

  Returns
  -------
  List with the desired window samples. Max value is one (1.0).

  See Also
  --------
  window.bartlett :
    Bartlett window, triangular with zero-valued end-points.

  """
  if size == 1:
    return [1.0]
  return [1 - 2.0 / (size + 1) * abs(n - (size - 1) / 2.0)
          for n in xrange(size)]


@window.strategy("hann", "hanning")
def window(size):
  """
  Hann window function with the given size.

  Returns
  -------
  List with the desired window samples. Max value is one (1.0).

  """
  if size == 1:
    return [1.0]
  return [.5 * (1 - cos(2 * pi * n / (size - 1))) for n in xrange(size)]


@window.strategy("blackman")
def window(size, alpha=.16):
  """
  Blackman window function with the given size.

  Parameters
  ----------
  size :
    Window size in samples.
  alpha :
    Blackman window alpha value. Defaults to 0.16.

  Returns
  -------
  List with the desired window samples. Max value is one (1.0).

  """
  if size == 1:
    return [1.0]
  return [alpha / 2 * cos(4 * pi * n / (size - 1))
          -.5 * cos(2 * pi * n / (size - 1)) + (1 - alpha) / 2
          for n in xrange(size)]


def acorr(blk, max_lag=None):
  """
  Calculate the autocorrelation of a given 1-D block sequence.

  Parameters
  ----------
  blk :
    An iterable with well-defined length. Don't use this function with Stream
    objects!
  max_lag :
    The size of the result, the lags you'd need. Defaults to ``len(blk) - 1``,
    since any lag beyond would result in zero.

  Returns
  -------
  A list with lags from 0 up to max_lag, where its ``i``-th element has the
  autocorrelation for a lag equals to ``i``. Be careful with negative lags!
  You should use abs(lag) indexes when working with them.

  Examples
  --------
  >>> seq = [1, 2, 3, 4, 3, 4, 2]
  >>> acorr(seq) # Default max_lag is len(seq) - 1
  [59, 52, 42, 30, 17, 8, 2]
  >>> acorr(seq, 9) # Zeros at the end
  [59, 52, 42, 30, 17, 8, 2, 0, 0, 0]
  >>> len(acorr(seq, 3)) # Resulting length is max_lag + 1
  4
  >>> acorr(seq, 3)
  [59, 52, 42, 30]

  """
  if max_lag is None:
    max_lag = len(blk) - 1
  return [sum(blk[n] * blk[n + tau] for n in xrange(len(blk) - tau))
          for tau in xrange(max_lag + 1)]


def lag_matrix(blk, max_lag=None):
  """
  Finds the lag matrix for a given 1-D block sequence.

  Parameters
  ----------
  blk :
    An iterable with well-defined length. Don't use this function with Stream
    objects!
  max_lag :
    The size of the result, the lags you'd need. Defaults to ``len(blk) - 1``,
    the maximum lag that doesn't create fully zeroed matrices.

  Returns
  -------
  The covariance matrix as a list of lists. Each cell (i, j) contains the sum
  of ``blk[n - i] * blk[n - j]`` elements for all n that allows such without
  padding the given block.

  """
  if max_lag is None:
    max_lag = len(blk) - 1
  elif max_lag >= len(blk):
    raise ValueError("Block length should be higher than order")

  return [[sum(blk[n - i] * blk[n - j] for n in xrange(max_lag, len(blk))
              ) for i in xrange(max_lag + 1)
          ] for j in xrange(max_lag + 1)]


def dft(blk, freqs, normalize=True):
  """
  Complex non-optimized Discrete Fourier Transform

  Finds the DFT for values in a given frequency list, in order, over the data
  block seen as periodic.

  Parameters
  ----------
  blk :
    An iterable with well-defined length. Don't use this function with Stream
    objects!
  freqs :
    List of frequencies to find the DFT, in rad/sample. FFT implementations
    like numpy.fft.ftt finds the coefficients for N frequencies equally
    spaced as ``line(N, 0, 2 * pi, finish=False)`` for N frequencies.
  normalize :
    If True (default), the coefficient sums are divided by ``len(blk)``,
    and the coefficient for the DC level (frequency equals to zero) is the
    mean of the block. If False, that coefficient would be the sum of the
    data in the block.

  Returns
  -------
  A list of DFT values for each frequency, in the same order that they appear
  in the freqs input.

  Note
  ----
  This isn't a FFT implementation, and performs :math:`O(M . N)` float
  pointing operations, with :math:`M` and :math:`N` equals to the length of
  the inputs. This function can find the DFT for any specific frequency, with
  no need for zero padding or finding all frequencies in a linearly spaced
  band grid with N frequency bins at once.

  """
  dft_data = (sum(xn * cexp(-1j * n * f) for n, xn in enumerate(blk))
                                         for f in freqs)
  if normalize:
    lblk = len(blk)
    return [v / lblk for v in dft_data]
  return list(dft_data)


@tostream
def zcross(seq, hysteresis=0, first_sign=0):
  """
  Zero-crossing stream.

  Parameters
  ----------
  seq :
    Any iterable to be used as input for the zero crossing analysis
  hysteresis :
    Crossing exactly zero might happen many times too fast due to high
    frequency oscilations near zero. To avoid this, you can make two
    threshold limits for the zero crossing detection: ``hysteresis`` and
    ``-hysteresis``. Defaults to zero (0), which means no hysteresis and only
    one threshold.
  first_sign :
    Optional argument with the sign memory from past. Gets the sig from any
    signed number. Defaults to zero (0), which means "any", and the first sign
    will be the first one found in data.

  Returns
  -------
  A Stream instance that outputs 1 for each crossing detected, 0 otherwise.

  """
  neg_hyst = -hysteresis
  seq_iter = iter(seq)

  # Gets the first sign
  if first_sign == 0:
    last_sign = 0
    for el in seq_iter:
      yield 0
      if (el > hysteresis) or (el < neg_hyst): # Ignores hysteresis region
        last_sign = -1 if el < 0 else 1 # Define the first sign
        break
  else:
    last_sign = -1 if first_sign < 0 else 1

  # Finds the full zero-crossing sequence
  for el in seq_iter: # Keep the same iterator (needed for non-generators)
    if el * last_sign < neg_hyst:
      last_sign = -1 if el < 0 else 1
      yield 1
    else:
      yield 0


envelope = StrategyDict("envelope")


@envelope.strategy("rms")
def envelope(sig, cutoff=pi/512):
  """
  Envelope non-linear filter.

  This strategy finds a RMS by passing the squared data through a low pass
  filter and taking its square root afterwards.

  Parameters
  ----------
  sig :
    The signal to be filtered.
  cutoff :
    Lowpass filter cutoff frequency, in rad/sample. Defaults to ``pi/512``.

  Returns
  -------
  A Stream instance with the envelope, without any decimation.

  See Also
  --------
  maverage :
    Moving average linear filter.

  """
  return lowpass(cutoff)(thub(sig, 1) ** 2) ** .5


@envelope.strategy("abs")
def envelope(sig, cutoff=pi/512):
  """
  Envelope non-linear filter.

  This strategy make an ideal half wave rectification (get the absolute value
  of each signal) and pass the resulting data through a low pass filter.

  Parameters
  ----------
  sig :
    The signal to be filtered.
  cutoff :
    Lowpass filter cutoff frequency, in rad/sample. Defaults to ``pi/512``.

  Returns
  -------
  A Stream instance with the envelope, without any decimation.

  See Also
  --------
  maverage :
    Moving average linear filter.

  """
  return lowpass(cutoff)(abs(thub(sig, 1)))


@envelope.strategy("squared")
def envelope(sig, cutoff=pi/512):
  """
  Squared envelope non-linear filter.

  This strategy squares the input, and apply a low pass filter afterwards.

  Parameters
  ----------
  sig :
    The signal to be filtered.
  cutoff :
    Lowpass filter cutoff frequency, in rad/sample. Defaults to ``pi/512``.

  Returns
  -------
  A Stream instance with the envelope, without any decimation.

  See Also
  --------
  maverage :
    Moving average linear filter.

  """
  return lowpass(cutoff)(thub(sig, 1) ** 2)


maverage = StrategyDict("maverage")


@maverage.strategy("deque")
def maverage(size):
  """
  Moving average

  This is the only strategy that uses a ``collections.deque`` object
  instead of a ZFilter instance. Fast, but without extra capabilites such
  as a frequency response plotting method.

  Parameters
  ----------
  size :
    Data block window size. Should be an integer.

  Returns
  -------
  A callable that accepts two parameters: a signal ``sig`` and the starting
  memory element ``zero`` that behaves like the ``LinearFilter.__call__``
  arguments. The output from that callable is a Stream instance, and has
  no decimation applied.

  See Also
  --------
  envelope :
    Signal envelope (time domain) strategies.

  """
  size_inv = 1. / size

  @tostream
  def maverage_filter(sig, zero=0.):
    data = deque((zero * size_inv for _ in xrange(size)), maxlen=size)
    mean_value = zero
    for el in sig:
      mean_value -= data.popleft()
      new_value = el * size_inv
      data.append(new_value)
      mean_value += new_value
      yield mean_value

  return maverage_filter


@maverage.strategy("recursive", "feedback")
def maverage(size):
  """
  Moving average

  Linear filter implementation as a recursive / feedback ZFilter.

  Parameters
  ----------
  size :
    Data block window size. Should be an integer.

  Returns
  -------
  A ZFilter instance with the feedback filter.

  See Also
  --------
  envelope :
    Signal envelope (time domain) strategies.

  """
  return (1. / size) * (1 - z ** -size) / (1 - z ** -1)


@maverage.strategy("fir")
def maverage(size):
  """
  Moving average

  Linear filter implementation as a FIR ZFilter.

  Parameters
  ----------
  size :
    Data block window size. Should be an integer.

  Returns
  -------
  A ZFilter instance with the FIR filter.

  See Also
  --------
  envelope :
    Signal envelope (time domain) strategies.

  """
  return sum((1. / size) * z ** -i for i in xrange(size))


def clip(sig, low=-1., high=1.):
  """
  Clips the signal up to both a lower and a higher limit.

  Parameters
  ----------
  sig :
    The signal to be clipped, be it a Stream instance, a list or any iterable.
  low, high :
    Lower and higher clipping limit, "saturating" the input to them. Defaults
    to -1.0 and 1.0, respectively. These can be None when needed one-sided
    clipping. When both limits are set to None, the output will be a Stream
    that yields exactly the ``sig`` input data.

  Returns
  -------
  Clipped signal as a Stream instance.

  """
  if low is None:
    if high is None:
      return Stream(sig)
    return Stream(el if el < high else high for el in sig)
  if high is None:
    return Stream(el if el > low else low for el in sig)
  if high < low:
    raise ValueError("Higher clipping limit is smaller than lower one")
  return Stream(high if el > high else
                (low if el < low else el) for el in sig)


@tostream
def unwrap(sig, max_delta=pi, step=2*pi):
  """
  Parametrized signal unwrapping.

  Parameters
  ----------
  sig :
    An iterable seen as an input signal.
  max_delta :
    Maximum value of :math:`\Delta = sig_i - sig_{i-1}` to keep output
    without another minimizing step change. Defaults to :math:`\pi`.
  step :
    The change in order to minimize the delta is an integer multiple of this
    value. Defaults to :math:`2 . \pi`.

  Returns
  -------
  The signal unwrapped as a Stream, minimizing the step difference when any
  adjacency step in the input signal is higher than ``max_delta`` by
  summing/subtracting ``step``.

  """
  idata = iter(sig)
  d0 = next(idata)
  yield d0
  delta = d0 - d0 # Get the zero (e.g., integer, float) from data
  for d1 in idata:
    d_diff = d1 - d0
    if abs(d_diff) > max_delta:
      delta += - d_diff + min((d_diff) % step,
                              (d_diff) % -step, key=lambda x: abs(x))
    yield d1 + delta
    d0 = d1


def amdf(lag, size):
  """
  Average Magnitude Difference Function non-linear filter for a given
  size and a fixed lag.

  Parameters
  ----------
  lag :
    Time lag, in samples. See ``freq2lag`` if needs conversion from
    frequency values.
  size :
    Moving average size.

  Returns
  -------
  A callable that accepts two parameters: a signal ``sig`` and the starting
  memory element ``zero`` that behaves like the ``LinearFilter.__call__``
  arguments. The output from that callable is a Stream instance, and has
  no decimation applied.

  See Also
  --------
  freq2lag :
    Frequency (in rad/sample) to lag (in samples) converter.

  """
  filt = (1 - z ** -lag).linearize()

  @tostream
  def amdf_filter(sig, zero=0.):
    return maverage(size)(abs(filt(sig, zero=zero)), zero=zero)

  return amdf_filter


overlap_add = StrategyDict("overlap_add")


@overlap_add.strategy("numpy")
@tostream
def overlap_add(blk_sig, size=None, hop=None, wnd=window.triangular,
                normalize=True):
  """
  Overlap-add algorithm using Numpy arrays.

  Parameters
  ----------
  blk_sig :
    An iterable of blocks (sequences), such as the ``Stream.blocks`` result.
  size :
    Block size for each ``blk_sig`` element, in samples.
  hop :
    Number of samples for two adjacent blocks (defaults to the size).
  wnd :
    Windowing function to be applied to each block (defaults to
    ``window.triangular``), or any iterable with exactly ``size``
    elements. If ``None``, applies a rectangular window.
  normalize :
    Flag whether the window should be normalized so that the process could
    happen in the [-1; 1] range, dividing the window by its hop gain.
    Default is ``True``.

  Returns
  -------
  A Stream instance with the blocks overlapped and added.

  See Also
  --------
  Stream.blocks :
    Splits the Stream instance into blocks with given size and hop.
  blocks :
    Same to Stream.blocks but for without using the Stream class.
  chain :
    Lazily joins all iterables given as parameters.
  chain.from_iterable :
    Same to ``chain(*data)``, but the ``data`` evaluation is lazy.

  Note
  ----
  Each block has the window function applied to it and the result is the
  sum of the blocks without any edge-case special treatment for the first
  and last few blocks.
  """
  import numpy as np

  # Finds the size from data, if needed
  if size is None:
    blk_sig = Stream(blk_sig)
    size = len(blk_sig.peek())
  if hop is None:
    hop = size

  # Find the right windowing function to be applied
  if wnd is None:
    wnd = np.ones(size)
  elif callable(wnd) and not isinstance(wnd, Stream):
    wnd = wnd(size)
  if isinstance(wnd, Sequence):
    wnd = np.array(wnd)
  elif isinstance(wnd, Iterable):
    wnd = np.hstack(wnd)
  else:
    raise TypeError("Window should be an iterable or a callable")

  # Normalization to the [-1; 1] range
  if normalize:
    steps = Stream(wnd).blocks(hop).map(np.array)
    gain = np.sum(np.abs(np.vstack(steps)), 0).max()
    if gain: # If gain is zero, normalization couldn't have any effect
      wnd = wnd / gain # Can't use "/=" nor "*=" as Numpy would keep datatype

  # Overlap-add algorithm
  old = np.zeros(size)
  for blk in (wnd * blk for blk in blk_sig):
    blk[:-hop] += old[hop:]
    for el in blk[:hop]:
      yield el
    old = blk
  for el in old[hop:]: # No more blocks, finish yielding the last one
    yield el


@overlap_add.strategy("list")
@tostream
def overlap_add(blk_sig, size=None, hop=None, wnd=window.triangular,
                normalize=True):
  """
  Overlap-add algorithm using lists instead of Numpy arrays. The behavior
  is the same to the ``overlap_add.numpy`` strategy.
  """
  # Finds the size from data, if needed
  if size is None:
    blk_sig = Stream(blk_sig)
    size = len(blk_sig.peek())
  if hop is None:
    hop = size

  # Find the window to be applied, resulting on a list or None
  if wnd is not None:
    if callable(wnd) and not isinstance(wnd, Stream):
      wnd = wnd(size)
    if isinstance(wnd, Iterable):
      wnd = list(wnd)
    else:
      raise TypeError("Window should be an iterable or a callable")

  # Normalization to the [-1; 1] range
  if normalize:
    if wnd:
      steps = Stream(wnd).map(abs).blocks(hop).map(tuple)
      gain = max(xmap(sum, xzip(*steps)))
      if gain: # If gain is zero, normalization couldn't have any effect
        wnd[:] = (w / gain for w in wnd)
    else:
      wnd = [1 / ceil(size / hop)] * size

  # Window application
  if wnd:
    mul = operator.mul
    if len(wnd) != size:
      raise ValueError("Incompatible window size")
    wnd = wnd + [0.] # Allows detecting when block size is wrong
    blk_sig = (xmap(mul, wnd, blk) for blk in blk_sig)

  # Overlap-add algorithm
  add = operator.add
  mem = [0.] * size
  s_h = size - hop
  for blk in xmap(iter, blk_sig):
    mem[:s_h] = xmap(add, mem[hop:], blk)
    mem[s_h:] = blk # Remaining elements
    if len(mem) != size:
      raise ValueError("Wrong block size or declared")
    for el in mem[:hop]:
      yield el
  for el in mem[hop:]: # No more blocks, finish yielding the last one
    yield el

########NEW FILE########
__FILENAME__ = lazy_auditory
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Fri Sep 21 2012
# danilo [dot] bellini [at] gmail [dot] com
"""
Peripheral auditory modeling module
"""

import math

# Audiolazy internal imports
from .lazy_core import StrategyDict
from .lazy_misc import elementwise
from .lazy_filters import z, CascadeFilter, ZFilter, resonator
from .lazy_math import pi, exp, cos, sin, sqrt, factorial
from .lazy_stream import thub
from .lazy_compat import xzip

__all__ = ["erb", "gammatone", "gammatone_erb_constants", "phon2dB"]


erb = StrategyDict("erb")


@erb.strategy("gm90", "glasberg_moore_90", "glasberg_moore")
@elementwise("freq", 0)
def erb(freq, Hz=None):
  """
  ERB model from Glasberg and Moore in 1990.

    ``B. R. Glasberg and B. C. J. Moore, "Derivation of auditory filter
    shapes from notched-noise data". Hearing Research, vol. 47, 1990, pp.
    103-108.``

  Parameters
  ----------
  freq :
    Frequency, in rad/sample if second parameter is given, in Hz otherwise.
  Hz :
    Frequency conversion "Hz" from sHz function, i.e., ``sHz(rate)[1]``.
    If this value is not given, both input and output will be in Hz.

  Returns
  -------
  Frequency range size, in rad/sample if second parameter is given, in Hz
  otherwise.

  """
  if Hz is None:
    if freq < 7: # Perhaps user tried something up to 2 * pi
      raise ValueError("Frequency out of range.")
    Hz = 1
  fHz = freq / Hz
  result = 24.7 * (4.37e-3 * fHz + 1.)
  return result * Hz


@erb.strategy("mg83", "moore_glasberg_83")
@elementwise("freq", 0)
def erb(freq, Hz=None):
  """
  ERB model from Moore and Glasberg in 1983.

    ``B. C. J. Moore and B. R. Glasberg, "Suggested formulae for calculating
    auditory filter bandwidths and excitation patterns". J. Acoust. Soc.
    Am., 74, 1983, pp. 750-753.``

  Parameters
  ----------
  freq :
    Frequency, in rad/sample if second parameter is given, in Hz otherwise.
  Hz :
    Frequency conversion "Hz" from sHz function, i.e., ``sHz(rate)[1]``.
    If this value is not given, both input and output will be in Hz.

  Returns
  -------
  Frequency range size, in rad/sample if second parameter is given, in Hz
  otherwise.

  """
  if Hz is None:
    if freq < 7: # Perhaps user tried something up to 2 * pi
      raise ValueError("Frequency out of range.")
    Hz = 1
  fHz = freq / Hz
  result = 6.23e-6 * fHz ** 2 + 93.39e-3 * fHz + 28.52
  return result * Hz


def gammatone_erb_constants(n):
  """
  Constants for using the real bandwidth in the gammatone filter, given its
  order. Returns a pair :math:`(x, y) = (1/a_n, c_n)`.

  Based on equations from:

    ``Holdsworth, J.; Patterson, R.; Nimmo-Smith, I.; Rice, P. Implementing a
    GammaTone Filter Bank. In: SVOS Final Report, Annex C, Part A: The
    Auditory Filter Bank. 1988.``

  First returned value is a bandwidth compensation for direct use in the
  gammatone formula:

  >>> x, y = gammatone_erb_constants(4)
  >>> central_frequency = 1000
  >>> round(x, 3)
  1.019
  >>> bandwidth = x * erb["moore_glasberg_83"](central_frequency)
  >>> round(bandwidth, 2)
  130.52

  Second returned value helps us find the ``3 dB`` bandwidth as:

  >>> x, y = gammatone_erb_constants(4)
  >>> central_frequency = 1000
  >>> bandwidth3dB = x * y * erb["moore_glasberg_83"](central_frequency)
  >>> round(bandwidth3dB, 2)
  113.55

  """
  tnt = 2 * n - 2
  return (factorial(n - 1) ** 2 / (pi * factorial(tnt) * 2 ** -tnt),
          2 * (2 ** (1. / n) - 1) ** .5
         )


gammatone = StrategyDict("gammatone")


@gammatone.strategy("sampled")
def gammatone(freq, bandwidth, phase=0, eta=4):
  """
  Gammatone filter based on a sampled impulse response.

    ``n ** (eta - 1) * exp(-bandwidth * n) * cos(freq * n + phase)``

  Parameters
  ----------
  freq :
    Frequency, in rad/sample.
  bandwidth :
    Frequency range size, in rad/sample. See gammatone_erb_constants for
    more information about how you can find this.
  phase :
    Phase, in radians. Defaults to zero (cosine).
  eta :
    Gammatone filter order. Defaults to 4.

  Returns
  -------
  A CascadeFilter object with ZFilter filters, each of them a pole-conjugated
  IIR filter model.
  Gain is normalized to have peak with 0 dB (1.0 amplitude).
  The total number of poles is twice the value of eta (conjugated pairs), one
  pair for each ZFilter.

  """
  assert eta >= 1

  A = exp(-bandwidth)
  numerator = cos(phase) - A * cos(freq - phase) * z ** -1
  denominator = 1 - 2 * A * cos(freq) * z ** -1 + A ** 2 * z ** -2
  filt = (numerator / denominator).diff(n=eta-1, mul_after=-z)

  # Filter is done, but the denominator might have some numeric loss
  f0 = ZFilter(filt.numpoly) / denominator
  f0 /= abs(f0.freq_response(freq)) # Max gain == 1.0 (0 dB)
  fn = 1 / denominator
  fn /= abs(fn.freq_response(freq))
  return CascadeFilter([f0] + [fn] * (eta - 1))


@gammatone.strategy("slaney")
def gammatone(freq, bandwidth):
  """
  Gammatone filter based on Malcolm Slaney's IIR cascading filter model.

  Model is described in:

    ``Slaney, M. "An Efficient Implementation of the Patterson-Holdsworth
    Auditory Filter Bank", Apple Computer Technical Report #35, 1993.``

  Parameters
  ----------
  freq :
    Frequency, in rad/sample.
  bandwidth :
    Frequency range size, in rad/sample. See gammatone_erb_constants for
    more information about how you can find this.

  Returns
  -------
  A CascadeFilter object with ZFilter filters, each of them a pole-conjugated
  IIR filter model.
  Gain is normalized to have peak with 0 dB (1.0 amplitude).
  The total number of poles is twice the value of eta (conjugated pairs), one
  pair for each ZFilter.

  """
  A = exp(-bandwidth)
  cosw = cos(freq)
  sinw = sin(freq)
  sig = [1., -1.]
  coeff = [cosw + s1 * (sqrt(2) + s2) * sinw for s1 in sig for s2 in sig]
  numerator = [1 - A * c * z ** -1 for c in coeff]
  denominator = 1 - 2 * A * cosw * z ** -1 + A ** 2 * z ** -2

  filt = CascadeFilter(num / denominator for num in numerator)
  return CascadeFilter(f / abs(f.freq_response(freq)) for f in filt)


@gammatone.strategy("klapuri")
def gammatone(freq, bandwidth):
  """
  Gammatone filter based on Anssi Klapuri's IIR cascading filter model.

  Model is described in:

    ``A. Klapuri, "Multipich Analysis of Polyphonic Music and Speech Signals
    Using an Auditory Model". IEEE Transactions on Audio, Speech and Language
    Processing, vol. 16, no. 2, 2008, pp. 255-266.``

  Parameters
  ----------
  freq :
    Frequency, in rad/sample.
  bandwidth :
    Frequency range size, in rad/sample. See gammatone_erb_constants for
    more information about how you can find this.

  Returns
  -------
  A CascadeFilter object with ZFilter filters, each of them a pole-conjugated
  IIR filter model.
  Gain is normalized to have peak with 0 dB (1.0 amplitude).
  The total number of poles is twice the value of eta (conjugated pairs), one
  pair for each ZFilter.

  """
  bw = thub(bandwidth, 1)
  bw2 = thub(bw * 2, 4)
  freq = thub(freq, 4)
  resons = [resonator.z_exp, resonator.poles_exp] * 2
  return CascadeFilter(reson(freq, bw2) for reson in resons)


phon2dB = StrategyDict("phon2dB")


@phon2dB.strategy("iso226", "iso226_2003", "iso_fdis_226_2003")
def phon2dB(loudness=None):
  """
  Loudness in phons to Sound Pressure Level (SPL) in dB using the
  ISO/FDIS 226:2003 model.

  This function needs Scipy, as ``scipy.interpolate.UnivariateSpline``
  objects are used as interpolators.

  Parameters
  ----------
  loudness :
    The loudness value in phons to be converted, or None (default) to get
    the threshold of hearing.

  Returns
  -------
  A callable that returns the SPL dB value for each given frequency in hertz.

  Note
  ----
  See ``phon2dB.iso226.schema`` and ``phon2dB.iso226.table`` to know the
  original frequency used for the result. The result for any other value is
  an interpolation (spline). Don't trust on values nor lower nor higher than
  the frequency limits there (20Hz and 12.5kHz) as they're not part of
  ISO226 and no value was collected to estimate them (they're just a spline
  interpolation to reach 1000dB at -30Hz and 32kHz). Likewise, the trustful
  loudness input range is from 20 to 90 phon, as written on ISO226, although
  other values aren't found by a spline interpolation but by using the
  formula on section 4.1 of ISO226.

  Hint
  ----
  The ``phon2dB.iso226.table`` also have other useful information, such as
  the threshold values in SPL dB.

  """
  from scipy.interpolate import UnivariateSpline

  table = phon2dB.iso226.table
  schema = phon2dB.iso226.schema
  freqs = [row[schema.index("freq")] for row in table]

  if loudness is None: # Threshold levels
    spl = [row[schema.index("threshold")] for row in table]

  else: # Curve for a specific phon value
    def get_pressure_level(freq, alpha, loudness_base, threshold):
      return 10 / alpha * math.log10(
        4.47e-3 * (10 ** (.025 * loudness) - 1.14) +
        (.4 * 10 ** ((threshold + loudness_base) / 10 - 9)) ** alpha
      ) - loudness_base + 94

    spl = [get_pressure_level(**dict(xzip(schema, args))) for args in table]

  interpolator = UnivariateSpline(freqs, spl, s=0)
  interpolator_low = UnivariateSpline([-30] + freqs, [1e3] + spl, s=0)
  interpolator_high = UnivariateSpline(freqs + [32000], spl + [1e3], s=0)

  @elementwise("freq", 0)
  def freq2dB_spl(freq):
    if freq < 20:
      return interpolator_low(freq).tolist()
    if freq > 12500:
      return interpolator_high(freq).tolist()
    return interpolator(freq).tolist()
  return freq2dB_spl

# ISO226 Table 1
phon2dB.iso226.schema = ("freq", "alpha", "loudness_base", "threshold")
phon2dB.iso226.table = (
  (   20, 0.532, -31.6, 78.5),
  (   25, 0.506, -27.2, 68.7),
  ( 31.5, 0.480, -23.0, 59.5),
  (   40, 0.455, -19.1, 51.1),
  (   50, 0.432, -15.9, 44.0),
  (   63, 0.409, -13.0, 37.5),
  (   80, 0.387, -10.3, 31.5),
  (  100, 0.367,  -8.1, 26.5),
  (  125, 0.349,  -6.2, 22.1),
  (  160, 0.330,  -4.5, 17.9),
  (  200, 0.315,  -3.1, 14.4),
  (  250, 0.301,  -2.0, 11.4),
  (  315, 0.288,  -1.1,  8.6),
  (  400, 0.276,  -0.4,  6.2),
  (  500, 0.267,   0.0,  4.4),
  (  630, 0.259,   0.3,  3.0),
  (  800, 0.253,   0.5,  2.2),
  ( 1000, 0.250,   0.0,  2.4),
  ( 1250, 0.246,  -2.7,  3.5),
  ( 1600, 0.244,  -4.1,  1.7),
  ( 2000, 0.243,  -1.0, -1.3),
  ( 2500, 0.243,   1.7, -4.2),
  ( 3150, 0.243,   2.5, -6.0),
  ( 4000, 0.242,   1.2, -5.4),
  ( 5000, 0.242,  -2.1, -1.5),
  ( 6300, 0.245,  -7.1,  6.0),
  ( 8000, 0.254, -11.2, 12.6),
  (10000, 0.271, -10.7, 13.9),
  (12500, 0.301,  -3.1, 12.3),
)

########NEW FILE########
__FILENAME__ = lazy_compat
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Tue May 14 2013
# danilo [dot] bellini [at] gmail [dot] com
"""
Compatibility tools to keep the same source working in both Python 2 and 3
"""

import types
import itertools as it
import sys

__all__ = ["orange", "PYTHON2", "builtins", "xrange", "xzip", "xzip_longest",
           "xmap", "xfilter", "STR_TYPES", "INT_TYPES", "SOME_GEN_TYPES",
           "NEXT_NAME", "iteritems", "itervalues", "im_func", "meta"]


def orange(*args, **kwargs):
  """
  Old Python 2 range (returns a list), working both in Python 2 and 3.
  """
  return list(range(*args, **kwargs))


PYTHON2 = sys.version_info.major == 2
if PYTHON2:
  builtins = sys.modules["__builtin__"]
else:
  import builtins


xrange = getattr(builtins, "xrange", range)
xzip = getattr(it, "izip", zip)
xzip_longest = getattr(it, "izip_longest", getattr(it, "zip_longest", None))
xmap = getattr(it, "imap", map)
xfilter = getattr(it, "ifilter", filter)


STR_TYPES = (getattr(builtins, "basestring", str),)
INT_TYPES = (int, getattr(builtins, "long", None)) if PYTHON2 else (int,)
SOME_GEN_TYPES = (types.GeneratorType, xrange(0).__class__, enumerate, xzip,
                  xzip_longest, xmap, xfilter)
NEXT_NAME = "next" if PYTHON2 else "__next__"


def iteritems(dictionary):
  """
  Function to use the generator-based items iterator over built-in
  dictionaries in both Python 2 and 3.
  """
  try:
    return getattr(dictionary, "iteritems")()
  except AttributeError:
    return iter(getattr(dictionary, "items")())


def itervalues(dictionary):
  """
  Function to use the generator-based value iterator over built-in
  dictionaries in both Python 2 and 3.
  """
  try:
    return getattr(dictionary, "itervalues")()
  except AttributeError:
    return iter(getattr(dictionary, "values")())


def im_func(method):
  """ Gets the function from the method in both Python 2 and 3. """
  return getattr(method, "im_func", method)


def meta(*bases, **kwargs):
  """
  Allows unique syntax similar to Python 3 for working with metaclasses in
  both Python 2 and Python 3.

  Examples
  --------
  >>> class BadMeta(type): # An usual metaclass definition
  ...   def __new__(mcls, name, bases, namespace):
  ...     if "bad" not in namespace: # A bad constraint
  ...       raise Exception("Oops, not bad enough")
  ...     value = len(name) # To ensure this metaclass is called again
  ...     def really_bad(self):
  ...       return self.bad() * value
  ...     namespace["really_bad"] = really_bad
  ...     return super(BadMeta, mcls).__new__(mcls, name, bases, namespace)
  ...
  >>> class Bady(meta(object, metaclass=BadMeta)):
  ...   def bad(self):
  ...     return "HUA "
  ...
  >>> class BadGuy(Bady):
  ...   def bad(self):
  ...     return "R"
  ...
  >>> issubclass(BadGuy, Bady)
  True
  >>> Bady().really_bad() # Here value = 4
  'HUA HUA HUA HUA '
  >>> BadGuy().really_bad() # Called metaclass ``__new__`` again, so value = 6
  'RRRRRR'

  """
  metaclass = kwargs.get("metaclass", type)
  if not bases:
    bases = (object,)
  class NewMeta(type):
    def __new__(mcls, name, mbases, namespace):
      if name:
        return metaclass.__new__(metaclass, name, bases, namespace)
      return super(NewMeta, mcls).__new__(mcls, "", mbases, {})
  return NewMeta("", tuple(), {})

########NEW FILE########
__FILENAME__ = lazy_core
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Mon Oct 08 2012
# danilo [dot] bellini [at] gmail [dot] com
"""
Core classes module
"""

import sys
import operator
from collections import Iterable
from abc import ABCMeta
import itertools as it

# Audiolazy internal imports
from .lazy_compat import STR_TYPES, iteritems, itervalues

__all__ = ["OpMethod", "AbstractOperatorOverloaderMeta", "MultiKeyDict",
           "StrategyDict"]


class OpMethod(object):
  """
  Internal class to represent an operator method metadata.

  You can acess operator methods directly by using the OpMethod.get() class
  method, which always returns a generator from a query.
  This might be helpful if you need to acess the operator module from
  symbols. Given an instance "op", it has the following data:

  ========= ===========================================================
  Attribute Contents (and an example with OpMethod.get("__radd__"))
  ========= ===========================================================
  op.name   Operator name string, e.g. ``"radd"``.
  op.dname  Dunder name string, e.g. ``"__radd__"``.
  op.func   Function reference, e.g. ``operator.__add__``.
  op.symbol Operator symbol if in a code as a string, e.g. ``"+"``.
  op.rev    Boolean telling if the operator is reversed, e.g. ``True``.
  op.arity  Number of operands, e.g. ``2``.
  ========= ===========================================================

  See the ``OpMethod.get`` docstring for more information and examples.

  """
  _all = {}

  @classmethod
  def get(cls, key="all", without=None):
    """
    Returns a list with every OpMethod instance that match the key.

    The valid values for query parameters are:

    * Operator method names such as ``add`` or ``radd`` or ``pos``, with or
      without the double underscores. These would select only one operator;
    * Strings with the operator symbols such as ``"+"``, ``"&"`` or ``"**"``.
      These would select all the binary, reversed binary and unary operators
      when these apply;
    * ``"all"`` for selecting every operator available;
    * ``"r"`` gets only the reversed operators;
    * ``1`` or ``"1"`` for unary operators;
    * ``2`` or ``"2"`` for binary operators (including reversed binary);
    * ``None`` for no operators at all;
    * Operator functions from the ``operator`` module with the double
      underscores (e.g. ``operator.__add__``), for all the operations
      that use the operator function (it and the reversed);

    Parameters
    ----------
    key :
      A query value, a string with whitespace-separated query names, or an
      iterable with valid query values (as listed above). This parameter
      defaults to "all".
    without :
      The same as key, but used to tell the query something that shouldn't
      appear in the result. Defaults to None.

    Returns
    -------
    Generator with all OpMethod instances that matches the query once, keeping
    the order in which it is asked for. For a given symbol with 3 operator
    methods (e.g., "+", which yields __add__, __radd__ and __pos__), the
    yielding order is <binary>, <reversed binary> and <unary>.

    Examples
    --------
    >>> list(OpMethod.get("*")) # By symbol
    [<mul operator method ('*' symbol)>, <rmul operator method ('*' symbol)>]
    >>> OpMethod.get(">>")
    <generator object get at 0x...>
    >>> len(list(_)) # Found __rshift__ and __rrshift__, as a generator
    2
    >>> next(OpMethod.get("__add__")).func(2, 3) # By name, finds 2 + 3
    5
    >>> next(OpMethod.get("rsub")).symbol # Name is without underscores
    '-'
    >>> mod = list(OpMethod.get("%"))
    >>> mod[0].rev # Is it reversed? The __mod__ isn't.
    False
    >>> mod[1].rev # But the __rmod__ is!
    True
    >>> mod[1].arity # Number of operands, the __rmod__ is binary
    2
    >>> add = list(OpMethod.get("+"))
    >>> add[2].arity # Unary "+"
    1
    >>> add[2] is next(OpMethod.get("pos"))
    True
    >>> import operator
    >>> next(OpMethod.get(operator.add)).symbol # Using the operator function
    '+'
    >>> len(list(OpMethod.get(operator.add))) # __add__ and __radd__
    2
    >>> len(list(OpMethod.get("<< >>"))) # Multiple inputs
    4
    >>> len(list(OpMethod.get("<< >>", without="r"))) # Without reversed
    2
    >>> list(OpMethod.get(["+", "&"], without=[operator.add, "r"]))
    [<pos operator method ('+' symbol)>, <and operator method ('&' symbol)>]
    >>> len(set(OpMethod.get(2, without=["- + *", "%", "r"])))
    14
    >>> len(set(OpMethod.get("all"))) # How many operator methods there are?
    33

    """
    ignore = set() if without is None else set(cls.get(without))
    if key is None:
      return
    if isinstance(key, STR_TYPES) or not isinstance(key, Iterable):
      key = [key]
    key = it.chain.from_iterable(el.split() if isinstance(el, STR_TYPES)
                                            else [el] for el in key)
    for op_descr in key:
      try:
        for op in cls._all[op_descr]:
          if op not in ignore:
            yield op
      except KeyError:
        if op_descr in ["div", "__div__", "rdiv", "__rdiv__"]:
          raise ValueError("Use only 'truediv' for division")
        raise ValueError("Operator '{}' unknown".format(op_descr))

  @classmethod
  def _insert(cls, name, symbol):
    self = cls()
    self.name = name
    self.symbol = symbol
    self.rev = name.startswith("r") and name != "rshift"
    self.dname = "__{}__".format(name) # Dunder name
    self.arity = 1 if name in ["pos", "neg", "invert"] else 2
    self.func = getattr(operator, "__{}__".format(name[self.rev:]))

    # Updates the "all" dictionary
    keys = ["all", self.symbol, self.name, self.dname, self.func,
            self.arity, str(self.arity)]
    if self.rev:
      keys.append("r")
    for key in keys:
      if key not in cls._all:
        cls._all[key] = [self]
      else:
        cls._all[key].append(self)

  @classmethod
  def _initialize(cls):
    """
    Internal method to initialize the class by creating all
    the operator metadata to be used afterwards.
    """
    op_symbols = """
      + add radd pos
      - sub rsub neg
      * mul rmul
      / truediv rtruediv
      // floordiv rfloordiv
      % mod rmod
      ** pow rpow
      >> rshift rrshift
      << lshift rlshift
      ~ invert
      & and rand
      | or ror
      ^ xor rxor
      < lt
      <= le
      == eq
      != ne
      > gt
      >= ge
    """
    for op_line in op_symbols.strip().splitlines():
      symbol, names = op_line.split(None, 1)
      for name in names.split():
        cls._insert(name, symbol)

  def __repr__(self):
    return "<{} operator method ('{}' symbol)>".format(self.name, self.symbol)


# Creates all operators
OpMethod._initialize()


class AbstractOperatorOverloaderMeta(ABCMeta):
  """
  Abstract metaclass for classes with massively overloaded operators.

  Dunders dont't appear within "getattr" nor "getattribute", and they should
  be inside the class dictionary, not the class instance one, otherwise they
  won't be found by the usual mechanism. That's why we have to be eager here.
  You need a concrete class inherited from this one, and the "abstract"
  enforcement and specification is:

  - Override __operators__ and __without__ with a ``OpMethod.get()`` valid
    query inputs, see that method docstring for more information and examples.
    Its a good idea to tell all operators that will be used, including the
    ones that should be defined in the instance namespace, since the
    metaclass will enforce their existance without overwriting.

    These should be overridden by a string or a list with all operator names,
    symbols or operator functions (from the `operator` module) to be
    overloaded (or neglect, in the __without__).

    - When using names, reversed operators should be given explicitly.
    - When using symbols the reversed operators and the unary are implicit.
    - When using operator functions, the ooperators and the unary are
      implicit.

    By default, __operators__ is "all" and __without__ is None.

  - All operators should be implemented by the metaclass hierarchy or by
    the class directly, and the class has priority when both exists,
    neglecting the method builder in this case.

  - There are three method builders which should be written in the concrete
    metaclass: ``__binary__``, ``__rbinary__`` and ``__unary__``.
    All receives 2 parameters (the class being instantiated and a OpMethod
    instance) and should return a function for the specific dunder, probably
    doing so based on general-use templates.

  Note
  ----
  Don't use "div"! In Python 2.x it'll be a copy of truediv.

  """
  __operators__ = "all"
  __without__ = None

  def __new__(mcls, name, bases, namespace):
    cls = super(AbstractOperatorOverloaderMeta,
                mcls).__new__(mcls, name, bases, namespace)

    # Inserts each operator into the class
    for op in OpMethod.get(mcls.__operators__, without=mcls.__without__):
      if op.dname not in namespace: # Added manually shouldn't use template

        # Creates the dunder method
        dunder = {(False, 1): mcls.__unary__,
                  (False, 2): mcls.__binary__,
                  (True, 2): mcls.__rbinary__,
                 }[op.rev, op.arity](cls, op)

        # Abstract enforcement
        if not callable(dunder):
          msg = "Class '{}' has no builder/template for operator method '{}'"
          raise TypeError(msg.format(cls.__name__, op.dname))

        # Inserts the dunder into the class
        dunder.__name__ = op.dname
        setattr(cls, dunder.__name__, dunder)
      else:
        dunder = namespace[op.dname]

      if sys.version_info.major == 2 and op.name in ["truediv", "rtruediv"]:
        new_name = op.dname.replace("true", "")
        if new_name not in namespace: # If wasn't insert manually
          setattr(cls, new_name, dunder)

    return cls

  # The 3 methods below should be overloaded, but they shouldn't be
  # "abstractmethod" since it's unuseful (and perhaps undesirable)
  # when there could be only one type of operator being massively overloaded.
  def __binary__(cls, op):
    """
    This method should be overridden to return the dunder for the given
    operator function.

    """
    return NotImplemented
  __unary__ = __rbinary__ = __binary__


class MultiKeyDict(dict):
  """
  Multiple keys dict.

  Can be thought as an "inversible" dict where you can ask for the one
  hashable value from one of the keys. By default it iterates through the
  values, if you need an iterator for all tuples of keys,
  use iterkeys method instead.

  Examples
  --------
  Assignments one by one:

  >>> mk = MultiKeyDict()
  >>> mk[1] = 3
  >>> mk[2] = 3
  >>> mk
  {(1, 2): 3}
  >>> mk[4] = 2
  >>> mk[1] = 2
  >>> len(mk)
  2
  >>> mk[1]
  2
  >>> mk[2]
  3
  >>> mk[4]
  2
  >>> sorted(mk)
  [2, 3]
  >>> sorted(mk.keys())
  [(2,), (4, 1)]

  Casting from another dict:

  >>> mkd = MultiKeyDict({1:4, 2:5, -7:4})
  >>> len(mkd)
  2
  >>> sorted(mkd)
  [4, 5]
  >>> del mkd[2]
  >>> len(mkd)
  1
  >>> sorted(list(mkd.keys())[0]) # Sorts the only key tuple
  [-7, 1]

  """
  def __init__(self, *args, **kwargs):
    self._keys_dict = {}
    self._inv_dict = {}
    super(MultiKeyDict, self).__init__()
    for key, value in iteritems(dict(*args, **kwargs)):
      self[key] = value

  def __getitem__(self, key):
    if isinstance(key, tuple): # Avoid errors with IPython
      return super(MultiKeyDict, self).__getitem__(key)
    return super(MultiKeyDict, self).__getitem__(self._keys_dict[key])

  def __setitem__(self, key, value):
    # We want only tuples
    if not isinstance(key, tuple):
      key = (key,)

    # Finds the full new tuple keys
    if value in self._inv_dict:
      key = self._inv_dict[value] + key

    # Remove duplicated keys
    key_list = []
    for k in key:
      if k not in key_list:
        key_list.append(k)
    key = tuple(key_list)

    # Remove the overwritten data
    for k in key:
      if k in self._keys_dict:
        del self[k]

    # Do the assignment
    for k in key:
      self._keys_dict[k] = key
    self._inv_dict[value] = key
    super(MultiKeyDict, self).__setitem__(key, value)

  def __delitem__(self, key):
    key_tuple = self._keys_dict[key]
    value = self[key]
    new_key = tuple(k for k in key_tuple if k != key)

    # Remove the old data
    del self._keys_dict[key]
    del self._inv_dict[value]
    super(MultiKeyDict, self).__delitem__(key_tuple)

    # Do the assignment (when it makes sense)
    if len(new_key) > 0:
      for k in new_key:
        self._keys_dict[k] = new_key
      self._inv_dict[value] = new_key
      super(MultiKeyDict, self).__setitem__(new_key, value)

  def __iter__(self):
    return iter(self._inv_dict)


class StrategyDict(MultiKeyDict):
  """
  Strategy dictionary manager creator with default, mainly done for callables
  and multiple implementation algorithms / models.

  Each strategy might have multiple names. The names can be any hashable.
  The "strategy" method creates a decorator for the given strategy names.
  Default is the first strategy you insert, but can be changed afterwards.
  The default strategy is the attribute StrategyDict.default, and might be
  anything outside the dictionary (i.e., it won't be changed if you remove
  the strategy).

  It iterates through the values (i.e., for each strategy, not its name).

  Examples
  --------
  >>> sd = StrategyDict()
  >>> @sd.strategy("sum") # First strategy is default
  ... def sd(a, b, c):
  ...     return a + b + c
  >>> @sd.strategy("min", "m") # Multiple names
  ... def sd(a, b, c):
  ...     return min(a, b, c)
  >>> sd(2, 5, 0)
  7
  >>> sd["min"](2, 5, 0)
  0
  >>> sd["m"](7, -5, -2)
  -5
  >>> sd.default = sd["min"]
  >>> sd(-19, 1e18, 0)
  -19

  Note
  ----
  The StrategyDict constructor creates a new class inheriting from
  StrategyDict, and then instantiates it before returning the requested
  instance. This singleton subclassing is needed for docstring
  personalization.

  Warning
  -------
  Every strategy you insert have as a side-effect a change into its module
  ``__test__`` dictionary, to allow the doctests finder locate your
  strategies. Make sure your strategy ``__module__`` attribute is always
  right. Set it to ``None`` (or anything that evaluates to ``False``) if
  you don't want this behaviour.

  """
  def __new__(self, name="strategy_dict_unnamed_instance"):
    """
    Creates a new StrategyDict class and returns an instance of it.
    The new class is needed to ensure it'll have a personalized docstring.

    """
    class StrategyDictInstance(StrategyDict):

      def __new__(cls, name=name):
        del StrategyDictInstance.__new__ # Should be called only once
        return MultiKeyDict.__new__(StrategyDictInstance)

      def __init__(self, name=name):
        self.__name__ = name
        super(StrategyDict, self).__init__()

      @property
      def __doc__(self):
        from .lazy_text import small_doc
        docbase = "This is a StrategyDict instance object called\n" \
                  "``{0}``. Strategies stored: {1}.\n"
        doc = [docbase.format(self.__name__, len(self))]

        pairs = sorted(iteritems(self))
        if self.default not in list(self.values()):
          pairs = it.chain(pairs, [(tuple(), self.default)])

        for key_tuple, value in pairs:
          # First find the part of the docstring related to the keys
          strategies = ["{0}.{1}".format(self.__name__, name)
                        for name in key_tuple]
          if len(strategies) == 0:
            doc.extend("\nDefault unnamed strategy")
          else:
            if value == self.default:
              strategies[0] += " (Default)"
            doc.extend(["\n**Strategy ", strategies[0], "**.\n"]),
            if len(strategies) == 2:
              doc.extend(["An alias for it is ``", strategies[1], "``.\n"])
            elif len(strategies) > 2:
              doc.extend(["Aliases available are ``",
                          "``, ``".join(strategies[1:]), "``.\n"])

          # Get first description paragraph as the docstring related to value
          doc.append("Docstring starts with:\n")
          doc.extend(small_doc(value, indent="\n  "))
          doc.append("\n")

        doc.append("\nNote"
                   "\n----\n"
                   "StrategyDict instances like this one have lazy\n"
                   "self-generated docstrings. If you change something in\n"
                   "the dict, the next docstrings will follow the change.\n"
                   "Calling this instance directly will have the same\n"
                   "effect as calling the default strategy.\n"
                   "You can see the full strategies docstrings for more\n"
                   "details, as well as the StrategyDict class\n"
                   "documentation.\n"
                  )
        return "".join(doc)

    return StrategyDictInstance(name)

  default = lambda: NotImplemented

  def strategy(self, *names):
    def decorator(func):
      func.__name__ = str(names[0])
      self[names] = func
      return self
    return decorator

  def __setitem__(self, key, value):
    if "default" not in self.__dict__: # Avoiding hasattr due to __getattr__
      self.default = value
    super(StrategyDict, self).__setitem__(key, value)

    # Also register strategy into module __test__ (allow doctests)
    if "__doc__" in getattr(value, "__dict__", {}):
      module_name = getattr(value, "__module__", False)
      if module_name:
        module = sys.modules[module_name]
        if not hasattr(module, "__test__"):
          setattr(module, "__test__", {})
        strategy_name = ".".join([self.__name__, value.__name__])
        module.__test__[strategy_name] = value

  def __call__(self, *args, **kwargs):
    return self.default(*args, **kwargs)

  def __getattr__(self, name):
    if name in self._keys_dict:
      return self[name]
    raise AttributeError("Unknown attribute '{0}'".format(name))

  def __iter__(self):
    return itervalues(self)

########NEW FILE########
__FILENAME__ = lazy_filters
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Wed Jul 18 2012
# danilo [dot] bellini [at] gmail [dot] com
"""
Stream filtering module
"""

from __future__ import division

import operator
from cmath import exp as complex_exp
from collections import Iterable, OrderedDict
import itertools as it
from functools import reduce

# Audiolazy internal imports
from .lazy_stream import Stream, avoid_stream, thub
from .lazy_misc import elementwise, zero_pad, sHz, almost_eq
from .lazy_text import (float_str, multiplication_formatter,
                        pair_strings_sum_formatter)
from .lazy_compat import meta, iteritems, xrange, im_func
from .lazy_poly import Poly
from .lazy_core import AbstractOperatorOverloaderMeta, StrategyDict
from .lazy_math import exp, sin, cos, sqrt, pi, nan, dB20, phase, e, inf

__all__ = ["LinearFilterProperties", "LinearFilter", "ZFilterMeta", "ZFilter",
           "z", "FilterListMeta", "FilterList", "CascadeFilter",
           "ParallelFilter", "comb", "resonator", "lowpass", "highpass"]


class LinearFilterProperties(object):
  """
  Class with common properties in a linear filter that can be used as a mixin.

  The classes that inherits this one should implement the ``numpoly`` and
  ``denpoly`` properties, and these should return a Poly instance.

  """
  def numlist(self):
    if any(key < 0 for key, value in self.numpoly.terms()):
      raise ValueError("Non-causal filter")
    return list(self.numpoly.values())
  numerator = property(numlist)
  numlist = property(numlist)

  def denlist(self):
    if any(key < 0 for key, value in self.denpoly.terms()):
      raise ValueError("Non-causal filter")
    return list(self.denpoly.values())
  denominator = property(denlist)
  denlist = property(denlist)

  @property
  def numdict(self):
    return OrderedDict(self.numpoly.terms())

  @property
  def dendict(self):
    return OrderedDict(self.denpoly.terms())

  @property
  def numpolyz(self):
    """
    Like numpoly, the linear filter numerator (or forward coefficients) as a
    Poly instance based on ``x = z`` instead of numpoly's ``x = z ** -1``,
    useful for taking roots.

    """
    return Poly(self.numerator[::-1])

  @property
  def denpolyz(self):
    """
    Like denpoly, the linear filter denominator (or backward coefficients) as
    a Poly instance based on ``x = z`` instead of denpoly's ``x = z ** -1``,
    useful for taking roots.

    """
    return Poly(self.denominator[::-1])


def _exec_eval(data, expr):
  """
  Internal function to isolate an exec. Executes ``data`` and returns the
  ``expr`` evaluation afterwards.

  """
  ns = {}
  exec(data, ns)
  return eval(expr, ns)


@avoid_stream
class LinearFilter(LinearFilterProperties):
  """
  Base class for Linear filters, time invariant or not.
  """
  def __init__(self, numerator=None, denominator=None):
    if isinstance(numerator, LinearFilter):
      # Filter type cast
      if denominator is not None:
        numerator = operator.truediv(numerator, denominator)
      self.numpoly = numerator.numpoly
      self.denpoly = numerator.denpoly
    else:
      # Filter from coefficients
      self.numpoly = Poly(numerator)
      self.denpoly = Poly({0: 1} if denominator is None else denominator)

    # Ensure denominator has only negative powers of z (positive powers here),
    # and a not null gain constant
    power = min(key for key, value in self.denpoly.terms())
    if power != 0:
      poly_delta = Poly([0, 1]) ** -power
      self.numpoly *= poly_delta
      self.denpoly *= poly_delta

  def __iter__(self):
    yield self.numdict
    yield self.dendict

  def __hash__(self):
    return hash(tuple(self.numdict) + tuple(self.dendict))

  def __call__(self, seq, memory=None, zero=0.):
    """
    IIR, FIR and time variant linear filtering.

    Parameters
    ----------
    seq :
      Any iterable to be seem as the input stream for the filter.
    memory :
      Might be an iterable or a callable. Generally, as a iterable, the first
      needed elements from this input will be used directly as the memory
      (not the last ones!), and as a callable, it will be called with the
      size as the only positional argument, and should return an iterable.
      If ``None`` (default), memory is initialized with zeros.
    zero :
      Value to fill the memory, when needed, and to be seem as previous
      input when there's a delay. Defaults to ``0.0``.

    Returns
    -------
    A Stream that have the data from the input sequence filtered.

    """
    # Data check
    if any(key < 0 for key, value in it.chain(self.numpoly.terms(),
                                              self.denpoly.terms())
          ):
      raise ValueError("Non-causal filter")
    if isinstance(self.denpoly[0], Stream): # Variable output gain
      den = self.denpoly
      inv_gain = 1 / den[0]
      den[0] = 0
      den *= inv_gain.copy()
      den[0] = 1
      return ZFilter(self.numpoly * inv_gain, den)(seq, memory=memory,
                                                   zero=zero)
    if self.denpoly[0] == 0:
      raise ZeroDivisionError("Invalid filter gain")

    # Lengths
    la, lb = len(self.denominator), len(self.numerator)
    lm = la - 1 # Memory size

    # Convert memory input to a list with size exactly equals to lm
    if memory is None:
      memory = [zero for unused in xrange(lm)]
    else: # Get data from iterable
      if not isinstance(memory, Iterable): # Function with 1 parameter: size
        memory = memory(lm)
      tw = it.takewhile(lambda pair: pair[0] < lm,
                        enumerate(memory))
      memory = [data for idx, data in tw]
      actual_len = len(memory)
      if actual_len < lm:
        memory = list(zero_pad(memory, lm - actual_len, zero=zero))

    # Creates the expression in a string
    data_sum = []

    num_iterables = []
    for delay, coeff in iteritems(self.numdict):
      if isinstance(coeff, Iterable):
        num_iterables.append(delay)
        data_sum.append("next(b{idx}) * d{idx}".format(idx=delay))
      elif coeff == 1:
        data_sum.append("d{idx}".format(idx=delay))
      elif coeff == -1:
        data_sum.append("-d{idx}".format(idx=delay))
      elif coeff != 0:
        data_sum.append("{value} * d{idx}".format(idx=delay, value=coeff))

    den_iterables = []
    for delay, coeff in iteritems(self.dendict):
      if isinstance(coeff, Iterable):
        den_iterables.append(delay)
        data_sum.append("-next(a{idx}) * m{idx}".format(idx=delay))
      elif delay == 0:
        gain = coeff
      elif coeff == -1:
        data_sum.append("m{idx}".format(idx=delay))
      elif coeff == 1:
        data_sum.append("-m{idx}".format(idx=delay))
      elif coeff != 0:
        data_sum.append("-{value} * m{idx}".format(idx=delay, value=coeff))

    # Creates the generator function for this call
    if len(data_sum) == 0:
      gen_func =  ["def gen(seq, memory, zero):",
                   "  for unused in seq:",
                   "    yield {zero}".format(zero=zero)
                  ]
    else:
      expr = " + ".join(data_sum)
      if gain == -1:
        expr = "-({expr})".format(expr=expr)
      elif gain != 1:
        expr = "({expr}) / {gain}".format(expr=expr, gain=gain)

      arg_names = ["seq", "memory", "zero"]
      arg_names.extend("b{idx}".format(idx=idx) for idx in num_iterables)
      arg_names.extend("a{idx}".format(idx=idx) for idx in den_iterables)
      gen_func =  ["def gen({args}):".format(args=", ".join(arg_names))]
      if la > 1:
        gen_func += ["  {m_vars} = memory".format(m_vars=" ".join(
                      ["m{} ,".format(el) for el in xrange(1, la)]
                    ))]
      if lb > 1:
        gen_func += ["  {d_vars} = zero".format(d_vars=" = ".join(
                      ["d{}".format(el) for el in xrange(1, lb)]
                    ))]
      gen_func += ["  for d0 in seq:",
                   "    m0 = {expr}".format(expr=expr),
                   "    yield m0"]
      gen_func += ["    m{idx} = m{idxold}".format(idx=idx, idxold=idx - 1)
                   for idx in xrange(lm, 0, -1)]
      gen_func += ["    d{idx} = d{idxold}".format(idx=idx, idxold=idx - 1)
                   for idx in xrange(lb - 1, 0, -1)]

    # Uses the generator function to return the desired values
    gen = _exec_eval("\n".join(gen_func), "gen")
    arguments = [iter(seq), memory, zero]
    arguments.extend(iter(self.numpoly[idx]) for idx in num_iterables)
    arguments.extend(iter(self.denpoly[idx]) for idx in den_iterables)
    return Stream(gen(*arguments))


  @elementwise("freq", 1)
  def freq_response(self, freq):
    """
    Frequency response for this filter.

    Parameters
    ----------
    freq :
      Frequency, in rad/sample. Can be an iterable with frequencies.

    Returns
    -------
    Complex number with the frequency response of the filter.

    See Also
    --------
    dB10 :
      Logarithmic power magnitude from data with squared magnitude.
    dB20 :
      Logarithmic power magnitude from raw complex data or data with linear
      amplitude.
    phase :
      Phase from complex data.
    LinearFilter.plot :
      Method to plot the LTI filter frequency and phase response into a
      Matplotlib figure.

    """
    z_ = complex_exp(-1j * freq)
    num = self.numpoly(z_)
    den = self.denpoly(z_)
    if not isinstance(den, Stream):
      if den == 0:
        return nan
    return num / den

  def is_lti(self):
    """
    Test if this filter is LTI (Linear Time Invariant).

    Returns
    -------
    Boolean returning True if this filter is LTI, False otherwise.

    """
    return not any(isinstance(value, Iterable)
                   for delay, value in it.chain(self.numpoly.terms(),
                                                self.denpoly.terms()))

  def is_causal(self):
    """
    Causality test for this filter.

    Returns
    -------
    Boolean returning True if this filter is causal, False otherwise.

    """
    return all(delay >= 0 for delay, value in self.numpoly.terms())

  def copy(self):
    """
    Returns a filter copy.

    It'll return a LinearFilter instance (more specific class when
    subclassing) with the same terms in both numerator and denominator, but
    as a "T" (tee) copy when the coefficients are Stream instances, allowing
    maths using a filter more than once.

    """
    return type(self)(self.numpoly.copy(), self.denpoly.copy())

  def linearize(self):
    """
    Linear interpolation of fractional delay values.

    Returns
    -------
    A new linear filter, with the linearized delay values.

    Examples
    --------

    >>> filt = z ** -4.3
    >>> filt.linearize()
    0.7 * z^-4 + 0.3 * z^-5

    """
    data = []
    for poly in [self.numpoly, self.denpoly]:
      data.append({})
      new_poly = data[-1]
      for k, v in poly.terms():
        if isinstance(k, int) or (isinstance(k, float) and k.is_integer()):
          pairs = [(int(k), v)]
        else:
          left = int(k)
          right = left + 1
          weight_right = k - left
          weight_left = 1. - weight_right
          pairs = [(left, v * weight_left), (right, v * weight_right)]
        for key, value in pairs:
          if key in new_poly:
            new_poly[key] += value
          else:
            new_poly[key] = value
    return self.__class__(*data)

  def plot(self, fig=None, samples=2048, rate=None, min_freq=0., max_freq=pi,
           blk=None, unwrap=True, freq_scale="linear", mag_scale="dB"):
    """
    Plots the filter frequency response into a formatted MatPlotLib figure
    with two subplots, labels and title, including the magnitude response
    and the phase response.

    Parameters
    ----------
    fig :
      A matplotlib.figure.Figure instance. Defaults to None, which means that
      it will create a new figure.
    samples :
      Number of samples (frequency values) to plot. Defaults to 2048.
    rate :
      Given rate (samples/second) or "s" object from ``sHz``. Defaults to 300.
    min_freq, max_freq :
      Frequency range to be drawn, in rad/sample. Defaults to [0, pi].
    blk :
      Sequence block. Plots the block DFT together with the filter frequency.
      Defaults to None (no block).
    unwrap :
      Boolean that chooses whether should unwrap the data phase or keep it as
      is. Defaults to True.
    freq_scale :
      Chooses whether plot is "linear" or "log" with respect to the frequency
      axis. Defaults to "linear". Case insensitive.
    mag_scale :
      Chooses whether magnitude plot scale should be "linear", "squared" or
      "dB". Defaults do "dB". Case insensitive.

    Returns
    -------
    The matplotlib.figure.Figure instance.

    See Also
    --------
    sHz :
      Second and hertz constants from samples/second rate.
    LinearFilter.zplot :
      Zeros-poles diagram plotting.
    dB20 :
      Elementwise casting from an amplitude value to a logarithmic power
      gain (in decibels).
    phase :
      Phase from complex data.
    LinearFilter.freq_response :
      Get the complex frequency response of a filter for specific frequency
      values.
    LinearFilter.zplot :
      Filter zero-pole plane plot.

    """
    if not self.is_lti():
      raise AttributeError("Filter is not time invariant (LTI)")
    fscale = freq_scale.lower()
    mscale = mag_scale.lower()
    mscale = "dB" if mag_scale == "db" else mag_scale
    if fscale not in ["linear", "log"]:
      raise ValueError("Unknown frequency scale")
    if mscale not in ["linear", "squared", "dB"]:
      raise ValueError("Unknown magnitude scale")

    from .lazy_synth import line
    from .lazy_analysis import dft, unwrap as unwrap_func
    from matplotlib import pyplot as plt

    if fig is None:
      fig = plt.figure()

    # Units! Bizarre "pi/12" just to help MaxNLocator, corrected by fmt_func
    Hz = pi / 12. if rate == None else sHz(rate)[1]
    funit = "rad/sample" if rate == None else "Hz"

    # Sample the frequency range linearly (data scale) and get the data
    freqs = list(line(samples, min_freq, max_freq, finish=True))
    freqs_label = list(line(samples, min_freq / Hz, max_freq / Hz,
                            finish=True))
    data = self.freq_response(freqs)
    if blk is not None:
      fft_data = dft(blk, freqs)

    # Plots the magnitude response
    mag_plot = fig.add_subplot(2, 1, 1)
    if fscale == "symlog":
      mag_plot.set_xscale(fscale, basex=2., basey=2.,
                          steps=[1., 1.25, 1.5, 1.75])
    else:
      mag_plot.set_xscale(fscale)
    mag_plot.set_title("Frequency response")
    mag = {"linear": lambda v: [abs(vi) for vi in v],
           "squared": lambda v: [abs(vi) ** 2 for vi in v],
           "dB": dB20
          }[mscale]
    if blk is not None:
      mag_plot.plot(freqs_label, mag(fft_data))
    mag_plot.plot(freqs_label, mag(data))
    mag_plot.set_ylabel("Magnitude ({munit})".format(munit=mscale))
    mag_plot.grid(True)
    plt.setp(mag_plot.get_xticklabels(), visible = False)

    # Plots the phase response
    ph_plot = fig.add_subplot(2, 1, 2, sharex = mag_plot)
    ph = (lambda x: unwrap_func(phase(x))) if unwrap else phase
    if blk is not None:
      ph_plot.plot(freqs_label, [xi * 12 / pi for xi in ph(fft_data)])
    ph_plot.plot(freqs_label, [xi * 12 / pi for xi in ph(data)])
    ph_plot.set_ylabel("Phase (rad)")
    ph_plot.set_xlabel("Frequency ({funit})".format(funit=funit))
    ph_plot.set_xlim(freqs_label[0], freqs_label[-1])
    ph_plot.grid(True)

    # X Ticks (gets strange unit "7.5 * degrees / sample" back ) ...
    fmt_func = lambda value, pos: float_str(value * pi / 12., "p", [8])
    if rate is None:
      if fscale == "linear":
        loc = plt.MaxNLocator(steps=[1, 2, 3, 4, 6, 8, 10])
      elif fscale == "log":
        loc = plt.LogLocator(base=2.)
        loc_minor = plt.LogLocator(base=2., subs=[1.25, 1.5, 1.75])
        ph_plot.xaxis.set_minor_locator(loc_minor)
      ph_plot.xaxis.set_major_locator(loc)
      ph_plot.xaxis.set_major_formatter(plt.FuncFormatter(fmt_func))

    # ... and Y Ticks
    loc = plt.MaxNLocator(steps=[1, 2, 3, 4, 6, 8, 10])
    ph_plot.yaxis.set_major_locator(loc)
    ph_plot.yaxis.set_major_formatter(plt.FuncFormatter(fmt_func))

    mag_plot.yaxis.get_major_locator().set_params(prune="lower")
    ph_plot.yaxis.get_major_locator().set_params(prune="upper")
    fig.subplots_adjust(hspace=0.)
    return fig

  def zplot(self, fig=None, circle=True):
    """
    Plots the filter zero-pole plane into a formatted MatPlotLib figure
    with one subplot, labels and title.

    Parameters
    ----------
    fig :
      A matplotlib.figure.Figure instance. Defaults to None, which means that
      it will create a new figure.
    circle :
      Chooses whether to include the unit circle in the plot. Defaults to
      True.

    Returns
    -------
    The matplotlib.figure.Figure instance.

    Note
    ----
    Multiple roots detection is slow, and roots may suffer from numerical
    errors (e.g., filter ``f = 1 - 2 * z ** -1 + 1 * z ** -2`` has twice the
    root ``1``, but ``f ** 3`` suffer noise from the root finding algorithm).
    For the exact number of poles and zeros, see the result title, or the
    length of LinearFilter.poles() and LinearFilter.zeros().

    See Also
    --------
    LinearFilter.plot :
      Frequency response plotting. Needs MatPlotLib.
    LinearFilter.zeros, LinearFilter.poles :
      Filter zeros and poles, as a list. Needs NumPy.

    """
    if not self.is_lti():
      raise AttributeError("Filter is not time invariant (LTI)")

    from matplotlib import pyplot as plt
    from matplotlib import transforms

    if fig is None:
      fig = plt.figure()

    # Configure the plot matplotlib.axes.Axes artist and circle background
    zp_plot = fig.add_subplot(1, 1, 1)
    if circle:
      zp_plot.add_patch(plt.Circle((0., 0.), radius=1., fill=False,
                                   linewidth=1., color="gray",
                                   linestyle="dashed"))

    # Plot the poles and zeros
    zeros = self.zeros # Start with zeros to avoid overdrawn hidden poles
    for zero in zeros:
      zp_plot.plot(zero.real, zero.imag, "o", markersize=8.,
                   markeredgewidth=1.5, markerfacecolor="c",
                   markeredgecolor="b")
    poles = self.poles
    for pole in poles:
      zp_plot.plot(pole.real, pole.imag, "x", markersize=8.,
                   markeredgewidth=2.5, markerfacecolor="r",
                   markeredgecolor="r")

    # Configure the axis (top/right is translated by 1 internally in pyplot)
    # Note: older MPL versions (e.g. 1.0.1) still don't have the color
    # matplotlib.colors.cname["lightgray"], which is the same to "#D3D3D3"
    zp_plot.spines["top"].set_position(("data", -1.))
    zp_plot.spines["right"].set_position(("data", -1.))
    zp_plot.spines["top"].set_color("#D3D3D3")
    zp_plot.spines["right"].set_color("#D3D3D3")
    zp_plot.axis("scaled") # Keep aspect ratio

    # Configure the plot limits
    border_width = .1
    zp_plot.set_xlim(xmin=zp_plot.dataLim.xmin - border_width,
                     xmax=zp_plot.dataLim.xmax + border_width)
    zp_plot.set_ylim(ymin=zp_plot.dataLim.ymin - border_width,
                     ymax=zp_plot.dataLim.ymax + border_width)

    # Multiple roots (or slightly same roots) detection
    def get_repeats(pairs):
      """
      Find numbers that are almost equal, for the printing sake.
      Input: list of number pairs (tuples with size two)
      Output: dict of pairs {pair: amount_of_repeats}
      """
      result = {idx: {idx} for idx, pair in enumerate(pairs)}
      for idx1, idx2 in it.combinations(xrange(len(pairs)), 2):
        p1 = pairs[idx1]
        p2 = pairs[idx2]
        if almost_eq(p1, p2):
          result[idx1] = result[idx1].union(result[idx2])
          result[idx2] = result[idx1]
      to_verify = [pair for pair in pairs]
      while to_verify:
        idx = to_verify.pop()
        if idx in result:
          for idxeq in result[idx]:
            if idxeq != idx and idx in result:
              del result[idx]
              to_verify.remove(idx)
      return {pairs[k]: len(v) for k, v in iteritems(result) if len(v) > 1}

    # Multiple roots text printing
    td = zp_plot.transData
    tpole = transforms.offset_copy(td, x=7, y=6, units="dots")
    tzero = transforms.offset_copy(td, x=7, y=-6, units="dots")
    tdi = td.inverted()
    zero_pos = [tuple(td.transform((zero.real, zero.imag)))
                for zero in zeros]
    pole_pos = [tuple(td.transform((pole.real, pole.imag)))
                for pole in poles]
    for zero, zrep in iteritems(get_repeats(zero_pos)):
      px, py = tdi.transform(zero)
      txt = zp_plot.text(px, py, "{0:d}".format(zrep), color="darkgreen",
                         transform=tzero, ha="center", va="center",
                         fontsize=10)
      txt.set_bbox(dict(facecolor="white", edgecolor="None", alpha=.4))
    for pole, prep in iteritems(get_repeats(pole_pos)):
      px, py = tdi.transform(pole)
      txt = zp_plot.text(px, py, "{0:d}".format(prep), color="black",
                         transform=tpole, ha="center", va="center",
                         fontsize=10)
      txt.set_bbox(dict(facecolor="white", edgecolor="None", alpha=.4))

    # Labels, title and finish
    zp_plot.set_title("Zero-Pole plot ({0:d} zeros, {1:d} poles)"
                      .format(len(zeros), len(poles)))
    zp_plot.set_xlabel("Real part")
    zp_plot.set_ylabel("Imaginary part")
    return fig

  @property
  def poles(self):
    """
    Returns a list with all poles (denominator roots in ``z``). Needs Numpy.

    See Also
    --------
    LinearFilterProperties.numpoly:
      Numerator polynomials where *x* is ``z ** -1``.
    LinearFilterProperties.denpoly:
      Denominator polynomials where *x* is ``z ** -1``.
    LinearFilterProperties.numpolyz:
      Numerator polynomials where *x* is ``z``.
    LinearFilterProperties.denpolyz:
      Denominator polynomials where *x* is ``z``.

    """
    return self.denpolyz.roots

  @property
  def zeros(self):
    """
    Returns a list with all zeros (numerator roots in ``z``), besides the
    zero-valued "zeros" that might arise from the difference between the
    numerator and denominator order (i.e., the roots returned are the inverse
    from the ``numpoly.roots()`` in ``z ** -1``). Needs Numpy.

    See Also
    --------
    LinearFilterProperties.numpoly:
      Numerator polynomials where *x* is ``z ** -1``.
    LinearFilterProperties.denpoly:
      Denominator polynomials where *x* is ``z ** -1``.
    LinearFilterProperties.numpolyz:
      Numerator polynomials where *x* is ``z``.
    LinearFilterProperties.denpolyz:
      Denominator polynomials where *x* is ``z``.

    """
    return self.numpolyz.roots

  def __eq__(self, other):
    if isinstance(other, LinearFilter):
      return self.numpoly == other.numpoly and self.denpoly == other.denpoly
    return False

  def __ne__(self, other):
    if isinstance(other, LinearFilter):
      return self.numpoly != other.numpoly and self.denpoly != other.denpoly
    return False


class ZFilterMeta(AbstractOperatorOverloaderMeta):
  __operators__ = "+ - * / **"

  def __rbinary__(cls, op):
    op_func = op.func
    def dunder(self, other):
      if isinstance(other, cls):
        raise ValueError("Filter equations have different domains")
      return op_func(cls([other]), self) # The "other" is probably a number
    return dunder

  def __unary__(cls, op):
    op_func = op.func
    def dunder(self):
      return cls(op_func(self.numpoly), self.denpoly)
    return dunder


@avoid_stream
class ZFilter(meta(LinearFilter, metaclass=ZFilterMeta)):
  """
  Linear filters based on Z-transform frequency domain equations.

  Examples
  --------

  Using the ``z`` object (float output because default filter memory has
  float zeros, and the delay in the numerator creates another float zero as
  "pre-input"):

  >>> filt = (1 + z ** -1) / (1 - z ** -1)
  >>> data = [1, 5, -4, -7, 9]
  >>> stream_result = filt(data) # Lazy iterable
  >>> list(stream_result) # Freeze
  [1.0, 7.0, 8.0, -3.0, -1.0]

  Same example with the same filter, but with a memory input, and using
  lists for filter numerator and denominator instead of the ``z`` object:

  >>> b = [1, 1]
  >>> a = [1, -1] # Each index ``i`` has the coefficient for z ** -i
  >>> filt = ZFilter(b, a)
  >>> data = [1, 5, -4, -7, 9]
  >>> stream_result = filt(data, memory=[3], zero=0) # Lazy iterable
  >>> result = list(stream_result) # Freeze
  >>> result
  [4, 10, 11, 0, 2]
  >>> filt2 = filt * z ** -1 # You can add a delay afterwards easily
  >>> final_result = filt2(result, zero=0)
  >>> list(final_result)
  [0, 4, 18, 39, 50]

  """
  def __add__(self, other):
    if isinstance(other, ZFilter):
      if self.denpoly == other.denpoly:
        return ZFilter(self.numpoly + other.numpoly, self.denpoly)
      return ZFilter(self.numpoly * other.denpoly.copy() +
                     other.numpoly * self.denpoly.copy(),
                     self.denpoly * other.denpoly)
    if isinstance(other, LinearFilter):
      raise ValueError("Filter equations have different domains")
    return self + ZFilter([other]) # Other is probably a number

  def __sub__(self, other):
    return self + (-other)

  def __mul__(self, other):
    if isinstance(other, ZFilter):
      return ZFilter(self.numpoly * other.numpoly,
                     self.denpoly * other.denpoly)
    if isinstance(other, LinearFilter):
      raise ValueError("Filter equations have different domains")
    return ZFilter(self.numpoly * other, self.denpoly)

  def __truediv__(self, other):
    if isinstance(other, ZFilter):
      return ZFilter(self.numpoly * other.denpoly,
                     self.denpoly * other.numpoly)
    if isinstance(other, LinearFilter):
      raise ValueError("Filter equations have different domains")
    return self * operator.truediv(1, other)

  def __pow__(self, other):
    if (other < 0) and (len(self.numpoly) >= 2 or len(self.denpoly) >= 2):
      return ZFilter(self.denpoly, self.numpoly) ** -other
    if isinstance(other, (int, float)):
      return ZFilter(self.numpoly ** other, self.denpoly ** other)
    raise ValueError("Z-transform powers only valid with integers")

  def __str__(self):
    num_term_strings = []
    for power, value in self.numpoly.terms():
      if isinstance(value, Iterable):
        value = "b{}".format(power).replace(".", "_").replace("-", "m")
      if value != 0.:
        num_term_strings.append(multiplication_formatter(-power, value, "z"))
    num = "0" if len(num_term_strings) == 0 else \
          reduce(pair_strings_sum_formatter, num_term_strings)

    den_term_strings = []
    for power, value in self.denpoly.terms():
      if isinstance(value, Iterable):
        value = "a{}".format(power).replace(".", "_").replace("-", "m")
      if value != 0.:
        den_term_strings.append(multiplication_formatter(-power, value, "z"))
    den = reduce(pair_strings_sum_formatter, den_term_strings)

    if den == "1": # No feedback
      return num

    line = "-" * max(len(num), len(den))
    spacer_offset = abs(len(num) - len(den)) // 2
    if spacer_offset > 0:
      centralize_spacer = " " * spacer_offset
      if len(num) > len(den):
        den = centralize_spacer + den
      else: # len(den) > len(num)
        num = centralize_spacer + num

    breaks = len(line) // 80
    slices = [slice(b * 80,(b + 1) * 80) for b in xrange(breaks + 1)]
    outputs = ["\n".join([num[s], line[s], den[s]]) for s in slices]
    return "\n\n    ...continue...\n\n".join(outputs)

  __repr__ = __str__

  def diff(self, n=1, mul_after=1):
    """
    Takes n-th derivative, multiplying each m-th derivative filter by
    mul_after before taking next (m+1)-th derivative or returning.
    """
    if isinstance(mul_after, ZFilter):
      den = ZFilter(self.denpoly)
      return reduce(lambda num, order: mul_after *
                      (num.diff() * den - order * num * den.diff()),
                    xrange(1, n + 1),
                    ZFilter(self.numpoly)
                   ) / den ** (n + 1)

    inv_sign = Poly({-1: 1}) # Since poly variable is z ** -1
    den = self.denpoly(inv_sign)
    return ZFilter(reduce(lambda num, order: mul_after *
                            (num.diff() * den - order * num * den.diff()),
                          xrange(1, n + 1),
                          self.numpoly(inv_sign))(inv_sign),
                   self.denpoly ** (n + 1))

  def __call__(self, seq, memory=None, zero=0.):
    """
    IIR, FIR and time variant linear filtering.

    Parameters
    ----------
    seq :
      Any iterable to be seem as the input stream for the filter, or another
      ZFilter for substituition.
    memory :
      Might be an iterable or a callable. Generally, as a iterable, the first
      needed elements from this input will be used directly as the memory
      (not the last ones!), and as a callable, it will be called with the
      size as the only positional argument, and should return an iterable.
      If ``None`` (default), memory is initialized with zeros. Neglect when
      ``seq`` input is a ZFilter.
    zero :
      Value to fill the memory, when needed, and to be seem as previous
      input when there's a delay. Defaults to ``0.0``. Neglect when ``seq``
      input is a ZFilter.

    Returns
    -------
    A Stream that have the data from the input sequence filtered.

    Examples
    --------
    With ZFilter instances:

    >>> filt = 1 + z ** -1
    >>> filt(z ** -1)
    z + 1
    >>> filt(- z ** 2)
    1 - z^-2

    With any iterable (but ZFilter instances):

    >>> filt = 1 + z ** -1
    >>> data = filt([1.0, 2.0, 3.0])
    >>> data
    <audiolazy.lazy_stream.Stream object at ...>
    >>> list(data)
    [1.0, 3.0, 5.0]

    """
    if isinstance(seq, ZFilter):
      return sum(v * seq ** -k for k, v in self.numpoly.terms()) / \
             sum(v * seq ** -k for k, v in self.denpoly.terms())
    else:
      return super(ZFilter, self).__call__(seq, memory=memory, zero=zero)


z = ZFilter({-1: 1})


class FilterListMeta(AbstractOperatorOverloaderMeta):
  __operators__ = "add * > >= < <="

  def __binary__(cls, op):
    op_dname = op.dname
    def dunder(self, other):
      "This operator acts just like it would do with lists."
      return cls(getattr(super(cls, self), op_dname)(other))
    return dunder

  __rbinary__ = __binary__


class FilterList(meta(list, LinearFilterProperties, metaclass=FilterListMeta)):
  """
  Class from which CascadeFilter and ParallelFilter inherits the common part
  of their contents. You probably won't need to use this directly.

  """
  def __init__(self, *filters):
    if len(filters) == 1 and not callable(filters[0]) \
                         and isinstance(filters[0], Iterable):
      filters = filters[0]
    self.extend(filters)

  def is_linear(self):
    """
    Tests whether all filters in the list are linear. CascadeFilter and
    ParallelFilter instances are also linear if all filters they group are
    linear.

    """
    return all(isinstance(filt, LinearFilter) or
               (hasattr(filt, "is_linear") and filt.is_linear())
               for filt in self.callables)

  def is_lti(self):
    """
    Tests whether all filters in the list are linear time invariant (LTI).
    CascadeFilter and ParallelFilter instances are also LTI if all filters
    they group are LTI.

    """
    return self.is_linear() and all(filt.is_lti() for filt in self.callables)

  def is_causal(self):
    """
    Tests whether all filters in the list are causal (i.e., no future-data
    delay in positive ``z`` exponents). Non-linear filters are seem as causal
    by default. CascadeFilter and ParallelFilter are causal if all the
    filters they group are causal.

    """
    return all(filt.is_causal() for filt in self.callables
                                if hasattr(filt, "is_causal"))

  plot = im_func(LinearFilter.plot)
  zplot = im_func(LinearFilter.zplot)

  def __eq__(self, other):
    return type(self) == type(other) and list.__eq__(self, other)

  def __ne__(self, other):
    return type(self) != type(other) or list.__ne__(self, other)

  @property
  def callables(self):
    """
    List of callables with all filters, casting to LinearFilter each one that
    isn't callable.

    """
    return [(filt if callable(filt) else LinearFilter(filt)) for filt in self]


@avoid_stream
class CascadeFilter(FilterList):
  """
  Filter cascade as a list of filters.

  Note
  ----
  A filter is any callable that receives an iterable as input and returns a
  Stream.

  Examples
  --------
  >>> filt = CascadeFilter(z ** -1, 2 * (1 - z ** -3))
  >>> data = Stream(1, 3, 5, 3, 1, -1, -3, -5, -3, -1) # Endless
  >>> filt(data, zero=0).take(15)
  [0, 2, 6, 10, 4, -4, -12, -12, -12, -4, 4, 12, 12, 12, 4]

  """
  def __call__(self, *args, **kwargs):
    return reduce(lambda data, filt: filt(data, *args[1:], **kwargs),
                  self.callables, args[0])

  @property
  def numpoly(self):
    try:
      return reduce(operator.mul, (filt.numpoly for filt in self.callables))
    except AttributeError:
      raise AttributeError("Non-linear filter")

  @property
  def denpoly(self):
    try:
      return reduce(operator.mul, (filt.denpoly for filt in self.callables))
    except AttributeError:
      raise AttributeError("Non-linear filter")

  @elementwise("freq", 1)
  def freq_response(self, freq):
    return reduce(operator.mul, (filt.freq_response(freq)
                                 for filt in self.callables))

  @property
  def poles(self):
    if not self.is_lti():
      raise AttributeError("Not a LTI filter")
    return reduce(operator.concat, (filt.poles for filt in self.callables))

  @property
  def zeros(self):
    if not self.is_lti():
      raise AttributeError("Not a LTI filter")
    return reduce(operator.concat, (filt.zeros for filt in self.callables))


@avoid_stream
class ParallelFilter(FilterList):
  """
  Filters in parallel as a list of filters.

  This list of filters that behaves as a filter, returning the sum of all
  signals that results from applying the the same given input into all
  filters. Besides the name, the data processing done isn't parallel.

  Note
  ----
  A filter is any callable that receives an iterable as input and returns a
  Stream.

  Examples
  --------
  >>> filt = 1 + z ** -1 -  z ** -2
  >>> pfilt = ParallelFilter(1 + z ** -1, - z ** -2)
  >>> list(filt(range(100))) == list(pfilt(range(100)))
  True
  >>> list(filt(range(10), zero=0))
  [0, 1, 3, 4, 5, 6, 7, 8, 9, 10]

  """
  def __call__(self, *args, **kwargs):
    if len(self) == 0:
      return Stream(kwargs["zero"] if "zero" in kwargs else 0.
                    for _ in args[0])
    arg0 = thub(args[0], len(self))
    return reduce(operator.add, (filt(arg0, *args[1:], **kwargs)
                                 for filt in self.callables))

  @property
  def numpoly(self):
    if not self.is_linear():
      raise AttributeError("Non-linear filter")
    return reduce(operator.add, self).numpoly

  @property
  def denpoly(self):
    try:
      return reduce(operator.mul, (filt.denpoly for filt in self.callables))
    except AttributeError:
      raise AttributeError("Non-linear filter")

  @elementwise("freq", 1)
  def freq_response(self, freq):
    return reduce(operator.add, (filt.freq_response(freq)
                                 for filt in self.callables))

  @property
  def poles(self):
    if not self.is_lti():
      raise AttributeError("Not a LTI filter")
    return reduce(operator.concat, (filt.poles for filt in self.callables))

  @property
  def zeros(self):
    if not self.is_lti():
      raise AttributeError("Not a LTI filter")
    return reduce(operator.add, (ZFilter(filt) for filt in self)).zeros


comb = StrategyDict("comb")


@comb.strategy("fb", "alpha", "fb_alpha", "feedback_alpha")
def comb(delay, alpha=1):
  """
  Feedback comb filter for a given alpha and delay.

    ``y[n] = x[n] + alpha * y[n - delay]``

  Parameters
  ----------
  delay :
    Feedback delay (lag), in number of samples.
  alpha :
    Exponential decay gain. You can find it from time decay ``tau`` in the
    impulse response, bringing us ``alpha = e ** (-delay / tau)``. See
    ``comb.tau`` strategy if that's the case. Defaults to 1 (no decay).

  Returns
  -------
  A ZFilter instance with the comb filter.

  See Also
  --------
  freq2lag :
    Frequency (in rad/sample) to delay (in samples) converter.

  """
  return 1 / (1 - alpha * z ** -delay)


@comb.strategy("tau", "fb_tau", "feedback_tau")
def comb(delay, tau=inf):
  """
  Feedback comb filter for a given time constant (and delay).

    ``y[n] = x[n] + alpha * y[n - delay]``

  Parameters
  ----------
  delay :
    Feedback delay (lag), in number of samples.
  tau :
    Time decay (up to ``1/e``, or -8.686 dB), in number of samples, which
    allows finding ``alpha = e ** (-delay / tau)``. Defaults to ``inf``
    (infinite), which means alpha = 1.

  Returns
  -------
  A ZFilter instance with the comb filter.

  See Also
  --------
  freq2lag :
    Frequency (in rad/sample) to delay (in samples) converter.

  """
  alpha = e ** (-delay / tau)
  return 1 / (1 - alpha * z ** -delay)


@comb.strategy("ff", "ff_alpha", "feedforward_alpha")
def comb(delay, alpha=1):
  """
  Feedforward comb filter for a given alpha (and delay).

    ``y[n] = x[n] + alpha * x[n - delay]``

  Parameters
  ----------
  delay :
    Feedback delay (lag), in number of samples.
  alpha :
    Memory value gain.

  Returns
  -------
  A ZFilter instance with the comb filter.

  See Also
  --------
  freq2lag :
    Frequency (in rad/sample) to delay (in samples) converter.

  """
  return 1 + alpha * z ** -delay


resonator = StrategyDict("resonator")


@resonator.strategy("poles_exp")
def resonator(freq, bandwidth):
  """
  Resonator filter with 2-poles (conjugated pair) and no zeros (constant
  numerator), with exponential approximation for bandwidth calculation.

  Parameters
  ----------
  freq :
    Resonant frequency in rad/sample (max gain).
  bandwidth :
    Bandwidth frequency range in rad/sample following the equation:

      ``R = exp(-bandwidth / 2)``

    where R is the pole amplitude (radius).

  Returns
  -------
  A ZFilter object.
  Gain is normalized to have peak with 0 dB (1.0 amplitude).

  """
  bandwidth = thub(bandwidth, 1)
  R = exp(-bandwidth * .5)
  R = thub(R, 5)
  cost = cos(freq) * (2 * R) / (1 + R ** 2)
  cost = thub(cost, 2)
  gain = (1 - R ** 2) * sqrt(1 - cost ** 2)
  denominator = 1 - 2 * R * cost * z ** -1 + R ** 2 * z ** -2
  return gain / denominator


@resonator.strategy("freq_poles_exp")
def resonator(freq, bandwidth):
  """
  Resonator filter with 2-poles (conjugated pair) and no zeros (constant
  numerator), with exponential approximation for bandwidth calculation.
  Given frequency is the denominator frequency, not the resonant frequency.

  Parameters
  ----------
  freq :
    Denominator frequency in rad/sample (not the one with max gain).
  bandwidth :
    Bandwidth frequency range in rad/sample following the equation:

      ``R = exp(-bandwidth / 2)``

    where R is the pole amplitude (radius).

  Returns
  -------
  A ZFilter object.
  Gain is normalized to have peak with 0 dB (1.0 amplitude).

  """
  bandwidth = thub(bandwidth, 1)
  R = exp(-bandwidth * .5)
  R = thub(R, 3)
  freq = thub(freq, 2)
  gain = (1 - R ** 2) * sin(freq)
  denominator = 1 - 2 * R * cos(freq) * z ** -1 + R ** 2 * z ** -2
  return gain / denominator


@resonator.strategy("z_exp")
def resonator(freq, bandwidth):
  """
  Resonator filter with 2-zeros and 2-poles (conjugated pair). The zeros are
  at the `1` and `-1` (both at the real axis, i.e., at the DC and the Nyquist
  rate), with exponential approximation for bandwidth calculation.

  Parameters
  ----------
  freq :
    Resonant frequency in rad/sample (max gain).
  bandwidth :
    Bandwidth frequency range in rad/sample following the equation:

      ``R = exp(-bandwidth / 2)``

    where R is the pole amplitude (radius).

  Returns
  -------
  A ZFilter object.
  Gain is normalized to have peak with 0 dB (1.0 amplitude).

  """
  bandwidth = thub(bandwidth, 1)
  R = exp(-bandwidth * .5)
  R = thub(R, 5)
  cost = cos(freq) * (1 + R ** 2) / (2 * R)
  gain = (1 - R ** 2) * .5
  numerator = 1 - z ** -2
  denominator = 1 - 2 * R * cost * z ** -1 + R ** 2 * z ** -2
  return gain * numerator / denominator


@resonator.strategy("freq_z_exp")
def resonator(freq, bandwidth):
  """
  Resonator filter with 2-zeros and 2-poles (conjugated pair). The zeros are
  at the `1` and `-1` (both at the real axis, i.e., at the DC and the Nyquist
  rate), with exponential approximation for bandwidth calculation.
  Given frequency is the denominator frequency, not the resonant frequency.

  Parameters
  ----------
  freq :
    Denominator frequency in rad/sample (not the one with max gain).
  bandwidth :
    Bandwidth frequency range in rad/sample following the equation:

      ``R = exp(-bandwidth / 2)``

    where R is the pole amplitude (radius).

  Returns
  -------
  A ZFilter object.
  Gain is normalized to have peak with 0 dB (1.0 amplitude).

  """
  bandwidth = thub(bandwidth, 1)
  R = exp(-bandwidth * .5)
  R = thub(R, 3)
  gain = (1 - R ** 2) * .5
  numerator = 1 - z ** -2
  denominator = 1 - 2 * R * cos(freq) * z ** -1 + R ** 2 * z ** -2
  return gain * numerator / denominator


lowpass = StrategyDict("lowpass")


@lowpass.strategy("pole")
def lowpass(cutoff):
  """
  Low-pass filter with one pole and no zeros (constant numerator), with
  high-precision cut-off frequency calculation.

  Parameters
  ----------
  cutoff :
    Cut-off frequency in rad/sample. It defines the filter frequency in which
    the squared gain is `50%` (a.k.a. magnitude gain is `sqrt(2) / 2` and
    power gain is about `3.0103 dB`).
    Should be a value between 0 and pi.

  Returns
  -------
  A ZFilter object.
  Gain is normalized to have peak with 0 dB (1.0 amplitude) at the DC
  frequency (zero rad/sample).

  """
  cutoff = thub(cutoff, 1)
  x = 2 - cos(cutoff)
  x = thub(x,2)
  R = x - sqrt(x ** 2 - 1)
  R = thub(R, 2)
  return (1 - R) / (1 - R * z ** -1)


@lowpass.strategy("pole_exp")
def lowpass(cutoff):
  """
  Low-pass filter with one pole and no zeros (constant numerator), with
  exponential approximation for cut-off frequency calculation, found by
  matching the one-pole Laplace lowpass filter.

  Parameters
  ----------
  cutoff :
    Cut-off frequency in rad/sample following the equation:

      ``R = exp(-cutoff)``

    where R is the pole amplitude (radius).

  Returns
  -------
  A ZFilter object.
  Gain is normalized to have peak with 0 dB (1.0 amplitude) at the DC
  frequency (zero rad/sample).
  Cut-off frequency is unreliable outside the [0; pi / 6] range.

  """
  cutoff = thub(cutoff, 1)
  R = exp(-cutoff)
  R = thub(R, 2)
  return (1 - R) / (1 - R * z ** -1)


highpass = StrategyDict("highpass")


@highpass.strategy("pole")
def highpass(cutoff):
  """
  High-pass filter with one pole and no zeros (constant numerator), with
  high-precision cut-off frequency calculation.

  Parameters
  ----------
  cutoff :
    Cut-off frequency in rad/sample. It defines the filter frequency in which
    the squared gain is `50%` (a.k.a. magnitude gain is `sqrt(2) / 2` and
    power gain is about `3.0103 dB`).
    Should be a value between 0 and pi.

  Returns
  -------
  A ZFilter object.
  Gain is normalized to have peak with 0 dB (1.0 amplitude) at the Nyquist
  frequency (pi rad/sample).

  """
  rev_cutoff = thub(pi - cutoff, 1)
  x = 2 - cos(rev_cutoff)
  x = thub(x,2)
  R = x - sqrt(x ** 2 - 1)
  R = thub(R, 2)
  return (1 - R) / (1 + R * z ** -1)


@highpass.strategy("pole_exp")
def highpass(cutoff):
  """
  High-pass filter with one pole and no zeros (constant numerator), with
  exponential approximation for cut-off frequency calculation, found by
  matching the one-pole Laplace lowpass filter and mirroring the resulting
  pole to be negative.

  Parameters
  ----------
  cutoff :
    Cut-off frequency in rad/sample following the equation:

      ``R = exp(cutoff - pi)``

    where R is the pole amplitude (radius).

  Returns
  -------
  A ZFilter object.
  Gain is normalized to have peak with 0 dB (1.0 amplitude) at the Nyquist
  frequency (pi rad/sample).
  Cut-off frequency is unreliable outside the [5 * pi / 6; pi] range.

  """
  R = thub(exp(thub(cutoff - pi, 1)), 2)
  return (1 - R) / (1 + R * z ** -1)

########NEW FILE########
__FILENAME__ = lazy_io
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Fri Jul 20 2012
# danilo [dot] bellini [at] gmail [dot] com
"""
Audio recording input and playing output module
"""

import threading
import struct
import array

# Audiolazy internal imports
from .lazy_stream import Stream
from .lazy_misc import DEFAULT_SAMPLE_RATE, blocks
from .lazy_compat import xrange, xmap
from .lazy_math import inf
from .lazy_core import StrategyDict

__all__ = ["chunks", "RecStream", "AudioIO", "AudioThread"]


# Conversion dict from structs.Struct() format symbols to PyAudio constants
_STRUCT2PYAUDIO = {"f": 1, #pyaudio.paFloat32
                   "i": 2, #pyaudio.paInt32
                   "h": 8, #pyaudio.paInt16
                   "b": 16, #pyaudio.paInt8
                   "B": 32, #pyaudio.paUInt8
                  }


chunks = StrategyDict("chunks")
chunks.__class__.size = 2048 # Samples


@chunks.strategy("struct")
def chunks(seq, size=None, dfmt="f", byte_order=None, padval=0.):
  """
  Chunk generator based on the struct module (Python standard library).

  Low-level data blockenizer for homogeneous data as a generator, to help
  writing an iterable into a file.
  The dfmt should be one char, chosen from the ones in link:

    `<http://docs.python.org/library/struct.html#format-characters>`_

  Useful examples (integer are signed, use upper case for unsigned ones):

  - "b" for 8 bits (1 byte) integer
  - "h" for 16 bits (2 bytes) integer
  - "i" for 32 bits (4 bytes) integer
  - "f" for 32 bits (4 bytes) float (default)
  - "d" for 64 bits (8 bytes) float (double)

  Byte order follows native system defaults. Other options are in the site:

    `<http://docs.python.org/library/struct.html#struct-alignment>`_

  They are:

  - "<" means little-endian
  - ">" means big-endian

  Note
  ----
  Default chunk size can be accessed (and changed) via chunks.size.

  """
  if size is None:
    size = chunks.size
  dfmt = str(size) + dfmt
  if byte_order is None:
    struct_string = dfmt
  else:
    struct_string = byte_order + dfmt
  s = struct.Struct(struct_string)
  for block in blocks(seq, size, padval=padval):
    yield s.pack(*block)


@chunks.strategy("array")
def chunks(seq, size=None, dfmt="f", byte_order=None, padval=0.):
  """
  Chunk generator based on the array module (Python standard library).

  See chunk.struct for more help. This strategy uses array.array (random access
  by indexing management) instead of struct.Struct and blocks/deque (circular
  queue appending) from the chunks.struct strategy.

  Hint
  ----
  Try each one to find the faster one for your machine, and chooses
  the default one by assigning ``chunks.default = chunks.strategy_name``.
  It'll be the one used by the AudioIO/AudioThread playing mechanism.

  Note
  ----
  The ``dfmt`` symbols for arrays might differ from structs' defaults.

  """
  if size is None:
    size = chunks.size
  chunk = array.array(dfmt, xrange(size))
  idx = 0

  for el in seq:
    chunk[idx] = el
    idx += 1
    if idx == size:
      yield chunk.tostring()
      idx = 0

  if idx != 0:
    for idx in xrange(idx, size):
      chunk[idx] = padval
    yield chunk.tostring()


class RecStream(Stream):
  """
  Recording Stream

  A common Stream class with a ``stop`` method for input data recording
  and a ``recording`` read-only property for status.
  """
  def __init__(self, device_manager, file_obj, chunk_size, dfmt):
    if chunk_size is None:
      chunk_size = chunks.size
    s = struct.Struct("{0}{1}".format(chunk_size, dfmt))

    def rec():
      try:
        while self._recording:
          for k in s.unpack(file_obj.read(chunk_size)):
            yield k
      finally:
        file_obj.close()
        self._recording = False # Loop can be broken by StopIteration
        self.device_manager.recording_finished(self)

    super(RecStream, self).__init__(rec())
    self._recording = True
    self.device_manager = device_manager

  def stop(self):
    """ Finishes the recording stream, so it can raise StopIteration """
    self._recording = False

  @property
  def recording(self):
    return self._recording


class AudioIO(object):
  """
  Multi-thread stream manager wrapper for PyAudio.

  """

  def __init__(self, wait=False, api=None):
    """
    Constructor to PyAudio Multi-thread manager audio IO interface.
    The "wait" input is a boolean about the behaviour on closing the
    instance, if it should or not wait for the streaming audio to finish.
    Defaults to False. Only works if the close method is explicitly
    called.
    """
    import pyaudio
    self._pa = pa = pyaudio.PyAudio()
    self._threads = []
    self.wait = wait # Wait threads to finish at end (constructor parameter)
    self._recordings = []

    # Lockers
    self.halting = threading.Lock() # Only for "close" method
    self.lock = threading.Lock() # "_threads" access locking
    self.finished = False

    # Choosing the PortAudio API (needed to use Jack)
    if not (api is None):
      api_count = pa.get_host_api_count()
      apis_gen = xmap(pa.get_host_api_info_by_index, xrange(api_count))
      try:
        self.api = next(el for el in apis_gen
                           if el["name"].lower().startswith(api))
      except StopIteration:
        raise RuntimeError("API '{}' not found".format(api))

  def __del__(self):
    """
    Default destructor. Use close method instead, or use the class
    instance as the expression of a with block.
    """
    self.close()

  def __exit__(self, etype, evalue, etraceback):
    """
    Closing destructor for use internally in a with-expression.
    """
    self.close()

  def __enter__(self):
    """
    To be used only internally, in the with-expression protocol.
    """
    return self

  def close(self):
    """
    Destructor for this audio interface. Waits the threads to finish their
    streams, if desired.
    """
    with self.halting: # Avoid simultaneous "close" threads

      if not self.finished:  # Ignore all "close" calls, but the first,
        self.finished = True # and any call to play would raise ThreadError

        # Closes all playing AudioThread instances
        while True:
          with self.lock: # Ensure there's no other thread messing around
            try:
              thread = self._threads[0] # Needless to say: pop = deadlock
            except IndexError: # Empty list
              break # No more threads

          if not self.wait:
            thread.stop()
          thread.join()

        # Closes all recording RecStream instances
        while self._recordings:
          recst = self._recordings[-1]
          recst.stop()
          recst.take(inf) # Ensure it'll be closed

        # Finishes
        assert not self._pa._streams # No stream should survive
        self._pa.terminate()

  def terminate(self):
    """
    Same as "close".
    """
    self.close() # Avoids direct calls to inherited "terminate"

  def play(self, audio, **kwargs):
    """
    Start another thread playing the given audio sample iterable (e.g. a
    list, a generator, a NumPy np.ndarray with samples), and play it.
    The arguments are used to customize behaviour of the new thread, as
    parameters directly sent to PyAudio's new stream opening method, see
    AudioThread.__init__ for more.
    """
    with self.lock:
      if self.finished:
        raise threading.ThreadError("Trying to play an audio stream while "
                                    "halting the AudioIO manager object")
      new_thread = AudioThread(self, audio, **kwargs)
      self._threads.append(new_thread)
      new_thread.start()
      return new_thread

  def thread_finished(self, thread):
    """
    Updates internal status about open threads. Should be called only by
    the internal closing mechanism of AudioThread instances.
    """
    with self.lock:
      self._threads.remove(thread)

  def recording_finished(self, recst):
    """
    Updates internal status about open recording streams. Should be called
    only by the internal closing mechanism of children RecStream instances.
    """
    self._recordings.remove(recst)

  def record(self, chunk_size = None,
                   dfmt = "f",
                   nchannels = 1,
                   rate = DEFAULT_SAMPLE_RATE,
                   **kwargs
            ):
    """
    Records audio from device into a Stream.

    Parameters
    ----------
    chunk_size :
      Number of samples per chunk (block sent to device).
    dfmt :
      Format, as in chunks(). Default is "f" (Float32).
    num_channels :
      Channels in audio stream (serialized).
    rate :
      Sample rate (same input used in sHz).

    Returns
    -------
    Endless Stream instance that gather data from the audio input device.

    """
    if chunk_size is None:
      chunk_size = chunks.size

    if hasattr(self, "api"):
      kwargs.setdefault("input_device_index", self.api["defaultInputDevice"])

    input_stream = RecStream(self,
                             self._pa.open(format=_STRUCT2PYAUDIO[dfmt],
                                           channels=nchannels,
                                           rate=rate,
                                           frames_per_buffer=chunk_size,
                                           input=True,
                                           **kwargs),
                             chunk_size,
                             dfmt
                            )
    self._recordings.append(input_stream)
    return input_stream


class AudioThread(threading.Thread):
  """
  Audio output thread.

  This class is a wrapper to ease the use of PyAudio using iterables of
  numbers (Stream instances, lists, tuples, NumPy 1D arrays, generators) as
  audio data streams.

  """
  def __init__(self, device_manager, audio,
                     chunk_size = None,
                     dfmt = "f",
                     nchannels = 1,
                     rate = DEFAULT_SAMPLE_RATE,
                     daemon = True, # This shouldn't survive after crashes
                     **kwargs
              ):
    """
    Sets a new thread to play the given audio.

    Parameters
    ----------
    chunk_size :
      Number of samples per chunk (block sent to device).
    dfmt :
      Format, as in chunks(). Default is "f" (Float32).
    num_channels :
      Channels in audio stream (serialized).
    rate :
      Sample rate (same input used in sHz).
    daemon :
      Boolean telling if thread should be daemon. Default is True.

    """
    super(AudioThread, self).__init__()
    self.daemon = daemon # threading.Thread property, couldn't be assigned
                         # before the superclass constructor

    # Stores data needed by the run method
    self.audio = audio
    self.device_manager = device_manager
    self.dfmt = dfmt
    self.nchannels = nchannels
    self.chunk_size = chunks.size if chunk_size is None else chunk_size

    # Lockers
    self.lock = threading.Lock() # Avoid control methods simultaneous call
    self.go = threading.Event() # Communication between the 2 threads
    self.go.set()
    self.halting = False # The stop message

    # Get the streaming function
    import _portaudio # Just to be slightly faster (per chunk!)
    self.write_stream = _portaudio.write_stream

    if hasattr(device_manager, "api"):
      kwargs.setdefault("output_device_index",
                        device_manager.api["defaultOutputDevice"])

    # Open a new audio output stream
    self.stream = device_manager._pa.open(format=_STRUCT2PYAUDIO[dfmt],
                                          channels=nchannels,
                                          rate=rate,
                                          frames_per_buffer=self.chunk_size,
                                          output=True,
                                          **kwargs)

  def run(self):
    """
    Plays the audio. This method plays the audio, and shouldn't be called
    explicitly, let the constructor do so.
    """
    # From now on, it's multi-thread. Let the force be with them.
    st = self.stream._stream

    for chunk in chunks(self.audio,
                        size=self.chunk_size*self.nchannels,
                        dfmt=self.dfmt):
      #Below is a faster way to call:
      #  self.stream.write(chunk, self.chunk_size)
      self.write_stream(st, chunk, self.chunk_size, False)
      if not self.go.is_set():
        self.stream.stop_stream()
        if self.halting:
          break
        self.go.wait()
        self.stream.start_stream()

    # Finished playing! Destructor-like step: let's close the thread
    with self.lock:
      if self in self.device_manager._threads: # If not already closed
        self.stream.close()
        self.device_manager.thread_finished(self)

  def stop(self):
    """ Stops the playing thread and close """
    with self.lock:
      self.halting = True
      self.go.clear()

  def pause(self):
    """ Pauses the audio. """
    with self.lock:
      self.go.clear()

  def play(self):
    """ Resume playing the audio. """
    with self.lock:
      self.go.set()

########NEW FILE########
__FILENAME__ = lazy_itertools
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Sat Oct 06 2012
# danilo [dot] bellini [at] gmail [dot] com
"""
Itertools module "decorated" replica, where all outputs are Stream instances
"""

import itertools as it
from collections import Iterator

# Audiolazy internal imports
from .lazy_stream import tostream, Stream
from .lazy_compat import xrange, xzip, PYTHON2
from .lazy_core import StrategyDict
from .lazy_filters import z


# "Decorates" all functions from itertools
__all__ = ["chain", "izip", "tee", "accumulate"]
it_names = set(dir(it)).difference(__all__)
for func in filter(callable, [getattr(it, name) for name in it_names]):
  name = func.__name__
  if name in ["filterfalse", "zip_longest"]: # These were renamed in Python 3
    name = "i" + name # In AudioLazy, keep the Python 2 names
  __all__.append(name)
  locals()[name] = tostream(func, module_name=__name__)


# StrategyDict chain, following "from_iterable" from original itertool
chain = StrategyDict("chain")
chain.strategy("chain")(tostream(it.chain, module_name=__name__))
chain.strategy("star", "from_iterable")(tostream(it.chain.from_iterable,
                                                 module_name=__name__))


# StrategyDict izip, allowing izip.longest instead of izip_longest
izip = StrategyDict("izip")
izip.strategy("izip", "smallest")(tostream(xzip, module_name=__name__))
izip["longest"] = izip_longest


# Includes the imap and ifilter (they're not from itertools in Python 3)
for name, func in zip(["imap", "ifilter"], [map, filter]):
  if name not in __all__:
    __all__.append(name)
    locals()[name] = tostream(func, module_name=__name__)


accumulate = StrategyDict("accumulate")
if not PYTHON2:
  accumulate.strategy("accumulate", "itertools") \
                     (tostream(it.accumulate, module_name=__name__))


@accumulate.strategy("func", "pure_python")
@tostream
def accumulate(iterable):
  " Return series of accumulated sums. "
  iterator = iter(iterable)
  sum_data = next(iterator)
  yield sum_data
  for el in iterator:
    sum_data += el
    yield sum_data


accumulate.strategy("z")(1 / (1 - z ** -1))


def tee(data, n=2):
  """
  Tee or "T" copy to help working with Stream instances as well as with
  numbers.

  Parameters
  ----------
  data :
    Input to be copied. Can be anything.
  n :
    Size of returned tuple. Defaults to 2.

  Returns
  -------
  Tuple of n independent Stream instances, if the input is a Stream or an
  iterator, otherwise a tuple with n times the same object.

  See Also
  --------
  thub :
    use Stream instances *almost* like constants in your equations.

  """
  if isinstance(data, (Stream, Iterator)):
    return tuple(Stream(cp) for cp in it.tee(data, n))
  else:
    return tuple(data for unused in xrange(n))

########NEW FILE########
__FILENAME__ = lazy_lpc
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Wed Jul 18 2012
# danilo [dot] bellini [at] gmail [dot] com
"""
Linear Predictive Coding (LPC) module
"""

from __future__ import division
from functools import reduce
import operator

# Audiolazy internal imports
from .lazy_stream import Stream
from .lazy_filters import ZFilter, z
from .lazy_math import phase
from .lazy_core import StrategyDict
from .lazy_misc import blocks
from .lazy_compat import xrange, xzip
from .lazy_analysis import acorr, lag_matrix

__all__ = ["ParCorError", "toeplitz", "levinson_durbin", "lpc", "parcor",
           "parcor_stable", "lsf", "lsf_stable"]


class ParCorError(ZeroDivisionError):
  """
  Error when trying to find the partial correlation coefficients
  (reflection coefficients) and there's no way to find them.
  """


def toeplitz(vect):
  """
  Find the toeplitz matrix as a list of lists given its first line/column.
  """
  return [[vect[abs(i-j)] for i in xrange(len(vect))]
                          for j in xrange(len(vect))]


def levinson_durbin(acdata, order=None):
  """
  Solve the Yule-Walker linear system of equations.

  They're given by:

  .. math::

    R . a = r

  where :math:`R` is a simmetric Toeplitz matrix where each element are lags
  from the given autocorrelation list. :math:`R` and :math:`r` are defined
  (Python indexing starts with zero and slices don't include the last
  element):

  .. math::

    R[i][j] = acdata[abs(j - i)]

    r = acdata[1 : order + 1]

  Parameters
  ----------
  acdata :
    Autocorrelation lag list, commonly the ``acorr`` function output.
  order :
    The order of the resulting ZFilter object. Defaults to
    ``len(acdata) - 1``.

  Returns
  -------
  A FIR filter, as a ZFilter object. The mean squared error over the given
  data (variance of the white noise) is in its "error" attribute.

  See Also
  --------
  acorr:
    Calculate the autocorrelation of a given block.
  lpc :
    Calculate the Linear Predictive Coding (LPC) coefficients.
  parcor :
    Partial correlation coefficients (PARCOR), or reflection coefficients,
    relative to the lattice implementation of a filter, obtained by reversing
    the Levinson-Durbin algorithm.

  Examples
  --------
  >>> data = [2, 2, 0, 0, -1, -1, 0, 0, 1, 1]
  >>> acdata = acorr(data)
  >>> acdata
  [12, 6, 0, -3, -6, -3, 0, 2, 4, 2]
  >>> ldfilt = levinson_durbin(acorr(data), 3)
  >>> ldfilt
  1 - 0.625 * z^-1 + 0.25 * z^-2 + 0.125 * z^-3
  >>> ldfilt.error # Squared! See lpc for more information about this
  7.875

  Notes
  -----
  The Levinson-Durbin algorithm used to solve the equations needs
  :math:`O(order^2)` floating point operations.

  """
  if order is None:
    order = len(acdata) - 1
  elif order >= len(acdata):
    acdata = Stream(acdata).append(0).take(order + 1)

  # Inner product for filters based on above statistics
  def inner(a, b): # Be careful, this depends on acdata !!!
    return sum(acdata[abs(i-j)] * ai * bj
               for i, ai in enumerate(a.numlist)
               for j, bj in enumerate(b.numlist)
              )

  try:
    A = ZFilter(1)
    for m in xrange(1, order + 1):
      B = A(1 / z) * z ** -m
      A -= inner(A, z ** -m) / inner(B, B) * B
  except ZeroDivisionError:
    raise ParCorError("Can't find next PARCOR coefficient")

  A.error = inner(A, A)
  return A


lpc = StrategyDict("lpc")


@lpc.strategy("autocor", "acorr", "autocorrelation", "auto_correlation")
def lpc(blk, order=None):
  """
  Find the Linear Predictive Coding (LPC) coefficients as a ZFilter object,
  the analysis whitening filter. This implementation uses the autocorrelation
  method, using the Levinson-Durbin algorithm or Numpy pseudo-inverse for
  linear system solving, when needed.

  Parameters
  ----------
  blk :
    An iterable with well-defined length. Don't use this function with Stream
    objects!
  order :
    The order of the resulting ZFilter object. Defaults to ``len(blk) - 1``.

  Returns
  -------
  A FIR filter, as a ZFilter object. The mean squared error over the given
  block is in its "error" attribute.

  Hint
  ----
  See ``lpc.kautocor`` example, which should apply equally for this strategy.

  See Also
  --------
  levinson_durbin :
    Levinson-Durbin algorithm for solving Yule-Walker equations (Toeplitz
    matrix linear system).
  lpc.nautocor:
    LPC coefficients from linear system solved with Numpy pseudo-inverse.
  lpc.kautocor:
    LPC coefficients obtained with Levinson-Durbin algorithm.

  """
  if order < 100:
    return lpc.nautocor(blk, order)
  try:
    return lpc.kautocor(blk, order)
  except ParCorError:
    return lpc.nautocor(blk, order)


@lpc.strategy("nautocor", "nacorr", "nautocorrelation", "nauto_correlation")
def lpc(blk, order=None):
  """
  Find the Linear Predictive Coding (LPC) coefficients as a ZFilter object,
  the analysis whitening filter. This implementation uses the autocorrelation
  method, using numpy.linalg.pinv as a linear system solver.

  Parameters
  ----------
  blk :
    An iterable with well-defined length. Don't use this function with Stream
    objects!
  order :
    The order of the resulting ZFilter object. Defaults to ``len(blk) - 1``.

  Returns
  -------
  A FIR filter, as a ZFilter object. The mean squared error over the given
  block is in its "error" attribute.

  Hint
  ----
  See ``lpc.kautocor`` example, which should apply equally for this strategy.

  See Also
  --------
  lpc.autocor:
    LPC coefficients by using one of the autocorrelation method strategies.
  lpc.kautocor:
    LPC coefficients obtained with Levinson-Durbin algorithm.

  """
  from numpy import matrix
  from numpy.linalg import pinv
  acdata = acorr(blk, order)
  coeffs = pinv(toeplitz(acdata[:-1])) * -matrix(acdata[1:]).T
  coeffs = coeffs.T.tolist()[0]
  filt = 1  + sum(ai * z ** -i for i, ai in enumerate(coeffs, 1))
  filt.error = acdata[0] + sum(a * c for a, c in xzip(acdata[1:], coeffs))
  return filt


@lpc.strategy("kautocor", "kacorr", "kautocorrelation", "kauto_correlation")
def lpc(blk, order=None):
  """
  Find the Linear Predictive Coding (LPC) coefficients as a ZFilter object,
  the analysis whitening filter. This implementation uses the autocorrelation
  method, using the Levinson-Durbin algorithm.

  Parameters
  ----------
  blk :
    An iterable with well-defined length. Don't use this function with Stream
    objects!
  order :
    The order of the resulting ZFilter object. Defaults to ``len(blk) - 1``.

  Returns
  -------
  A FIR filter, as a ZFilter object. The mean squared error over the given
  block is in its "error" attribute.

  Examples
  --------
  >>> data = [-1, 0, 1, 0] * 4
  >>> len(data) # Small data
  16
  >>> filt = lpc.kautocor(data, 2)
  >>> filt # The analysis filter
  1 + 0.875 * z^-2
  >>> filt.numerator # List of coefficients
  [1, 0.0, 0.875]
  >>> filt.error # Prediction error (squared!)
  1.875

  See Also
  --------
  levinson_durbin :
    Levinson-Durbin algorithm for solving Yule-Walker equations (Toeplitz
    matrix linear system).
  lpc.autocor:
    LPC coefficients by using one of the autocorrelation method strategies.
  lpc.nautocor:
    LPC coefficients from linear system solved with Numpy pseudo-inverse.

  """
  return levinson_durbin(acorr(blk, order), order)


@lpc.strategy("covar", "cov", "covariance", "ncovar", "ncov", "ncovariance")
def lpc(blk, order=None):
  """
  Find the Linear Predictive Coding (LPC) coefficients as a ZFilter object,
  the analysis whitening filter. This implementation uses the covariance
  method, assuming a zero-mean stochastic process, using numpy.linalg.pinv
  as a linear system solver.

  """
  from numpy import matrix
  from numpy.linalg import pinv

  lagm = lag_matrix(blk, order)
  phi = matrix(lagm)
  psi = phi[1:, 0]
  coeffs = pinv(phi[1:, 1:]) * -psi
  coeffs = coeffs.T.tolist()[0]
  filt = 1  + sum(ai * z ** -i for i, ai in enumerate(coeffs, 1))
  filt.error = phi[0, 0] + sum(a * c for a, c in xzip(lagm[0][1:], coeffs))
  return filt


@lpc.strategy("kcovar", "kcov", "kcovariance")
def lpc(blk, order=None):
  """
  Find the Linear Predictive Coding (LPC) coefficients as a ZFilter object,
  the analysis whitening filter. This implementation is based on the
  covariance method, assuming a zero-mean stochastic process, finding
  the coefficients iteratively and greedily like the lattice implementation
  in Levinson-Durbin algorithm, although the lag matrix found from the given
  block don't have to be toeplitz. Slow, but this strategy don't need NumPy.

  """
  # Calculate the covariance for each lag pair
  phi = lag_matrix(blk, order)
  order = len(phi) - 1

  # Inner product for filters based on above statistics
  def inner(a, b):
    return sum(phi[i][j] * ai * bj
               for i, ai in enumerate(a.numlist)
               for j, bj in enumerate(b.numlist)
              )

  A = ZFilter(1)
  B = [z ** -1]
  beta = [inner(B[0], B[0])]

  m = 1
  while True:
    try:
      k = -inner(A, z ** -m) / beta[m - 1] # Last one is really a PARCOR coeff
    except ZeroDivisionError:
      raise ZeroDivisionError("Can't find next coefficient")
    if k >= 1 or k <= -1:
      raise ValueError("Unstable filter")
    A += k * B[m - 1]

    if m >= order:
      A.error = inner(A, A)
      return A

    gamma = [inner(z ** -(m + 1), B[q]) / beta[q] for q in xrange(m)]
    B.append(z ** -(m + 1) - sum(gamma[q] * B[q] for q in xrange(m)))
    beta.append(inner(B[m], B[m]))
    m += 1


def parcor(fir_filt):
  """
  Find the partial correlation coefficients (PARCOR), or reflection
  coefficients, relative to the lattice implementation of a given LTI FIR
  LinearFilter with a constant denominator (i.e., LPC analysis filter, or
  any filter without feedback).

  Parameters
  ----------
  fir_filt :
    A ZFilter object, causal, LTI and with a constant denominator.

  Returns
  -------
  A generator that results in each partial correlation coefficient from
  iterative decomposition, reversing the Levinson-Durbin algorithm.

  Examples
  --------
  >>> filt = levinson_durbin([1, 2, 3, 4, 5, 3, 2, 1])
  >>> filt
  1 - 0.275 * z^-1 - 0.275 * z^-2 - 0.4125 * z^-3 + 1.5 * z^-4 """\
  """- 0.9125 * z^-5 - 0.275 * z^-6 - 0.275 * z^-7
  >>> round(filt.error, 4)
  1.9125
  >>> k_generator = parcor(filt)
  >>> k_generator
  <generator object parcor at ...>
  >>> [round(k, 7) for k in k_generator]
  [-0.275, -0.3793103, -1.4166667, -0.2, -0.25, -0.3333333, -2.0]

  See Also
  --------
  levinson_durbin :
    Levinson-Durbin algorithm for solving Yule-Walker equations (Toeplitz
    matrix linear system).

  """
  den = fir_filt.denominator
  if len(den) != 1:
    raise ValueError("Filter has feedback")
  elif den[0] != 1: # So we don't have to worry with the denominator anymore
    fir_filt /= den[0]

  for m in xrange(len(fir_filt.numerator) - 1, 0, -1):
    k = fir_filt.numpoly[m]
    yield k
    zB = fir_filt(1 / z) * z ** -m
    try:
      fir_filt = (fir_filt - k * zB) / (1 - k ** 2)
    except ZeroDivisionError:
      raise ParCorError("Can't find next PARCOR coefficient")
    fir_filt = (fir_filt - fir_filt.numpoly[0]) + 1 # Avoid rounding errors


def parcor_stable(filt):
  """
  Tests whether the given filter is stable or not by using the partial
  correlation coefficients (reflection coefficients) of the given filter.

  Parameters
  ----------
  filt :
    A LTI filter as a LinearFilter object.

  Returns
  -------
  A boolean that is true only when all correlation coefficients are inside the
  unit circle. Critical stability (i.e., when outer coefficient has magnitude
  equals to one) is seem as an instability, and returns False.

  See Also
  --------
  parcor :
    Partial correlation coefficients generator.
  lsf_stable :
    Tests filter stability with Line Spectral Frequencies (LSF) values.

  """
  try:
    return all(abs(k) < 1 for k in parcor(ZFilter(filt.denpoly)))
  except ParCorError:
    return False


def lsf(fir_filt):
  """
  Find the Line Spectral Frequencies (LSF) from a given FIR filter.

  Parameters
  ----------
  filt :
    A LTI FIR filter as a LinearFilter object.

  Returns
  -------
  A tuple with all LSFs in rad/sample, alternating from the forward prediction
  and backward prediction filters, starting with the lowest LSF value.

  """
  den = fir_filt.denominator
  if len(den) != 1:
    raise ValueError("Filter has feedback")
  elif den[0] != 1: # So we don't have to worry with the denominator anymore
    fir_filt /= den[0]

  from numpy import roots
  rev_filt = ZFilter(fir_filt.numerator[::-1]) * z ** -1
  P = fir_filt + rev_filt
  Q = fir_filt - rev_filt
  roots_p = roots(P.numerator[::-1])
  roots_q = roots(Q.numerator[::-1])
  lsf_p = sorted(phase(roots_p))
  lsf_q = sorted(phase(roots_q))
  return reduce(operator.concat, xzip(*sorted([lsf_p, lsf_q])), tuple())


def lsf_stable(filt):
  """
  Tests whether the given filter is stable or not by using the Line Spectral
  Frequencies (LSF) of the given filter. Needs NumPy.

  Parameters
  ----------
  filt :
    A LTI filter as a LinearFilter object.

  Returns
  -------
  A boolean that is true only when the LSF values from forward and backward
  prediction filters alternates. Critical stability (both forward and backward
  filters has the same LSF value) is seem as an instability, and returns
  False.

  See Also
  --------
  lsf :
    Gets the Line Spectral Frequencies from a filter. Needs NumPy.
  parcor_stable :
    Tests filter stability with partial correlation coefficients (reflection
    coefficients).

  """
  lsf_data = lsf(ZFilter(filt.denpoly))
  return all(a < b for a, b in blocks(lsf_data, size=2, hop=1))

########NEW FILE########
__FILENAME__ = lazy_math
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Thu Nov 08 2012
# danilo [dot] bellini [at] gmail [dot] com
"""
Math modules "decorated" and complemented to work elementwise when needed
"""

import math
import cmath
import operator
import itertools as it
from functools import reduce

# Audiolazy internal imports
from .lazy_misc import elementwise
from .lazy_compat import INT_TYPES

__all__ = ["absolute", "pi", "e", "cexp", "ln", "log", "log1p", "log10",
           "log2", "factorial", "dB10", "dB20", "inf", "nan", "phase", "sign"]

# All functions from math with one numeric input
_math_names = ["acos", "acosh", "asin", "asinh", "atan", "atanh", "ceil",
               "cos", "cosh", "degrees", "erf", "erfc", "exp", "expm1",
               "fabs", "floor", "frexp", "gamma", "isinf", "isnan", "lgamma",
               "modf", "radians", "sin", "sinh", "sqrt", "tan", "tanh",
               "trunc"]
__all__.extend(_math_names)


for func in [getattr(math, name) for name in _math_names]:
  locals()[func.__name__] = elementwise("x", 0)(func)


@elementwise("x", 0)
def log(x, base=None):
  if base is None:
    if x == 0:
      return -inf
    elif isinstance(x, complex) or x < 0:
      return cmath.log(x)
    else:
      return math.log(x)
  else: # base is given
    if base <= 0 or base == 1:
      raise ValueError("Not a valid logarithm base")
    elif x == 0:
      return -inf
    elif isinstance(x, complex) or x < 0:
      return cmath.log(x, base)
    else:
      return math.log(x, base)


@elementwise("x", 0)
def log1p(x):
  if x == -1:
    return -inf
  elif isinstance(x, complex) or x < -1:
    return cmath.log(1 + x)
  else:
    return math.log1p(x)


def log10(x):
  return log(x, 10)


def log2(x):
  return log(x, 2)


ln = log
absolute = elementwise("number", 0)(abs)
pi = math.pi
e = math.e
cexp = elementwise("x", 0)(cmath.exp)
inf = float("inf")
nan = float("nan")
phase = elementwise("z", 0)(cmath.phase)


@elementwise("n", 0)
def factorial(n):
  """
  Factorial function that works with really big numbers.
  """
  if isinstance(n, float):
    if n.is_integer():
      n = int(n)
  if not isinstance(n, INT_TYPES):
    raise TypeError("Non-integer input (perhaps you need Euler Gamma "
                    "function or Gauss Pi function)")
  if n < 0:
    raise ValueError("Input shouldn't be negative")
  return reduce(operator.mul,
                it.takewhile(lambda m: m <= n, it.count(2)),
                1)


@elementwise("data", 0)
def dB10(data):
  """
  Convert a gain value to dB, from a squared amplitude value to a power gain.
  """
  return 10 * math.log10(abs(data)) if data != 0 else -inf


@elementwise("data", 0)
def dB20(data):
  """
  Convert a gain value to dB, from an amplitude value to a power gain.
  """
  return 20 * math.log10(abs(data)) if data != 0 else -inf


@elementwise("x", 0)
def sign(x):
  return cmp(x, 0)

########NEW FILE########
__FILENAME__ = lazy_midi
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Wed Jul 18 2012
# danilo [dot] bellini [at] gmail [dot] com
"""
MIDI representation data & note-frequency relationship
"""

import itertools as it

# Audiolazy internal imports
from .lazy_misc import elementwise
from .lazy_math import log2, nan, isinf, isnan

__all__ = ["MIDI_A4", "FREQ_A4", "SEMITONE_RATIO", "str2freq",
           "str2midi", "freq2str", "freq2midi", "midi2freq", "midi2str",
           "octaves"]

# Useful constants
MIDI_A4 = 69   # MIDI Pitch number
FREQ_A4 = 440. # Hz
SEMITONE_RATIO = 2. ** (1. / 12.) # Ascending


@elementwise("midi_number", 0)
def midi2freq(midi_number):
  """
  Given a MIDI pitch number, returns its frequency in Hz.
  """
  return FREQ_A4 * 2 ** ((midi_number - MIDI_A4) * (1./12.))


@elementwise("note_string", 0)
def str2midi(note_string):
  """
  Given a note string name (e.g. "Bb4"), returns its MIDI pitch number.
  """
  if note_string == "?":
    return nan
  data = note_string.strip().lower()
  name2delta = {"c": -9, "d": -7, "e": -5, "f": -4, "g": -2, "a": 0, "b": 2}
  accident2delta = {"b": -1, "#": 1, "x": 2}
  accidents = list(it.takewhile(lambda el: el in accident2delta, data[1:]))
  octave_delta = int(data[len(accidents) + 1:]) - 4
  return (MIDI_A4 +
          name2delta[data[0]] + # Name
          sum(accident2delta[ac] for ac in accidents) + # Accident
          12 * octave_delta # Octave
         )


def str2freq(note_string):
  """
  Given a note string name (e.g. "F#2"), returns its frequency in Hz.
  """
  return midi2freq(str2midi(note_string))


@elementwise("freq", 0)
def freq2midi(freq):
  """
  Given a frequency in Hz, returns its MIDI pitch number.
  """
  result = 12 * (log2(freq) - log2(FREQ_A4)) + MIDI_A4
  return nan if isinstance(result, complex) else result


@elementwise("midi_number", 0)
def midi2str(midi_number, sharp=True):
  """
  Given a MIDI pitch number, returns its note string name (e.g. "C3").
  """
  if isinf(midi_number) or isnan(midi_number):
    return "?"
  num = midi_number - (MIDI_A4 - 4 * 12 - 9)
  note = (num + .5) % 12 - .5
  rnote = int(round(note))
  error = note - rnote
  octave = str(int(round((num - note) / 12.)))
  if sharp:
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
  else:
    names = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
  names = names[rnote] + octave
  if abs(error) < 1e-4:
    return names
  else:
    err_sig = "+" if error > 0 else "-"
    err_str = err_sig + str(round(100 * abs(error), 2)) + "%"
    return names + err_str


def freq2str(freq):
  """
  Given a frequency in Hz, returns its note string name (e.g. "D7").
  """
  return midi2str(freq2midi(freq))


def octaves(freq, fmin=20., fmax=2e4):
  """
  Given a frequency and a frequency range, returns all frequencies in that
  range that is an integer number of octaves related to the given frequency.

  Parameters
  ----------
  freq :
    Frequency, in any (linear) unit.
  fmin, fmax :
    Frequency range, in the same unit of ``freq``. Defaults to 20.0 and
    20,000.0, respectively.

  Returns
  -------
  A list of frequencies, in the same unit of ``freq`` and in ascending order.

  Examples
  --------
  >>> from audiolazy import octaves, sHz
  >>> octaves(440.)
  [27.5, 55.0, 110.0, 220.0, 440.0, 880.0, 1760.0, 3520.0, 7040.0, 14080.0]
  >>> octaves(440., fmin=3000)
  [3520.0, 7040.0, 14080.0]
  >>> Hz = sHz(44100)[1] # Conversion unit from sample rate
  >>> freqs = octaves(440 * Hz, fmin=300 * Hz, fmax = 1000 * Hz) # rad/sample
  >>> len(freqs) # Number of octaves
  2
  >>> [round(f, 6) for f in freqs] # Values in rad/sample
  [0.062689, 0.125379]
  >>> [round(f / Hz, 6) for f in freqs] # Values in Hz
  [440.0, 880.0]

  """
  # Input validation
  if any(f <= 0 for f in (freq, fmin, fmax)):
    raise ValueError("Frequencies have to be positive")

  # If freq is out of range, avoid range extension
  while freq < fmin:
    freq *= 2
  while freq > fmax:
    freq /= 2
  if freq < fmin: # Gone back and forth
    return []

  # Finds the range for a valid input
  return list(it.takewhile(lambda x: x > fmin,
                           (freq * 2 ** harm for harm in it.count(0, -1))
                          ))[::-1] \
       + list(it.takewhile(lambda x: x < fmax,
                           (freq * 2 ** harm for harm in it.count(1))
                          ))

########NEW FILE########
__FILENAME__ = lazy_misc
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Fri Jul 20 2012
# danilo [dot] bellini [at] gmail [dot] com
"""
Common miscellanous tools and constants for general use
"""

from collections import deque, Iterable
from functools import wraps
import itertools as it
import sys
from math import pi
import operator

# Audiolazy internal imports
from . import _internals
from .lazy_compat import (xrange, xzip_longest, STR_TYPES, SOME_GEN_TYPES,
                          iteritems)
from .lazy_core import StrategyDict

__all__ = ["DEFAULT_SAMPLE_RATE", "rint", "blocks", "zero_pad", "elementwise",
           "almost_eq", "sHz", "freq2lag", "lag2freq", "freq_to_lag",
           "lag_to_freq"]

DEFAULT_SAMPLE_RATE = 44100 # Hz (samples/second)


def rint(x, step=1):
  """
  Round to integer.

  Parameters
  ----------
  x :
    Input number (integer or float) to be rounded.
  step :
    Quantization level (defaults to 1). If set to 2, the output will be the
    "best" even number.

  Result
  ------
  The step multiple nearest to x. When x is exactly halfway between two
  possible outputs, it'll result the one farthest to zero.

  """
  div, mod = divmod(x, step)
  err = min(step / 10., .1)
  result = div * step
  if x > 0:
    result += err
  elif x < 0:
    result -= err
  if (operator.ge if x >= 0 else operator.gt)(2 * mod, step):
    result += step
  return int(result)


def blocks(seq, size=None, hop=None, padval=0.):
  """
  General iterable blockenizer.

  Generator that gets ``size`` elements from ``seq``, and outputs them in a
  collections.deque (mutable circular queue) sequence container. Next output
  starts ``hop`` elements after the first element in last output block. Last
  block may be appended with ``padval``, if needed to get the desired size.

  The ``seq`` can have hybrid / hetherogeneous data, it just need to be an
  iterable. You can use other type content as padval (e.g. None) to help
  segregate the padding at the end, if desired.

  Note
  ----
  When hop is less than size, changing the returned contents will keep the
  new changed value in the next yielded container.

  """
  # Initialization
  res = deque(maxlen=size) # Circular queue
  idx = 0
  last_idx = size - 1
  if hop is None:
    hop = size
  reinit_idx = size - hop

  # Yields each block, keeping last values when needed
  if hop <= size:
    for el in seq:
      res.append(el)
      if idx == last_idx:
        yield res
        idx = reinit_idx
      else:
        idx += 1

  # Yields each block and skips (loses) data due to hop > size
  else:
    for el in seq:
      if idx < 0: # Skips data
        idx += 1
      else:
        res.append(el)
        if idx == last_idx:
          yield res
          #res = dtype()
          idx = size-hop
        else:
          idx += 1

  # Padding to finish
  if idx > max(size-hop, 0):
    for _ in xrange(idx,size):
      res.append(padval)
    yield res


def zero_pad(seq, left=0, right=0, zero=0.):
  """
  Zero padding sample generator (not a Stream!).

  Parameters
  ----------
  seq :
    Sequence to be padded.
  left :
    Integer with the number of elements to be padded at left (before).
    Defaults to zero.
  right :
    Integer with the number of elements to be padded at right (after).
    Defaults to zero.
  zero :
    Element to be padded. Defaults to a float zero (0.0).

  Returns
  -------
  A generator that pads the given ``seq`` with samples equals to ``zero``,
  ``left`` times before and ``right`` times after it.

  """
  for unused in xrange(left):
    yield zero
  for item in seq:
    yield item
  for unused in xrange(right):
    yield zero


def elementwise(name="", pos=None):
  """
  Function auto-map decorator broadcaster.

  Creates an "elementwise" decorator for one input parameter. To create such,
  it should know the name (for use as a keyword argument and the position
  "pos" (input as a positional argument). Without a name, only the
  positional argument will be used. Without both name and position, the
  first positional argument will be used.

  """
  if (name == "") and (pos is None):
    pos = 0
  def elementwise_decorator(func):
    """
    Element-wise decorator for functions known to have 1 input and 1
    output be applied directly on iterables. When made to work with more
    than 1 input, all "secondary" parameters will the same in all
    function calls (i.e., they will not even be a copy).

    """
    @wraps(func)
    def wrapper(*args, **kwargs):

      # Find the possibly Iterable argument
      positional = (pos is not None) and (pos < len(args))
      arg = args[pos] if positional else kwargs[name]

      if isinstance(arg, Iterable) and not isinstance(arg, STR_TYPES):
        if positional:
          data = (func(*(args[:pos] + (x,) + args[pos+1:]),
                       **kwargs)
                  for x in arg)
        else:
          data = (func(*args,
                       **dict(it.chain(iteritems(kwargs), [(name, x)])))
                  for x in arg)

        # Generators should still return generators
        if isinstance(arg, SOME_GEN_TYPES):
          return data

        # Cast to numpy array or matrix, if needed, without actually
        # importing its package
        type_arg = type(arg)
        try:
          is_numpy = type_arg.__module__ == "numpy"
        except AttributeError:
          is_numpy = False
        if is_numpy:
          np_type = {"ndarray": sys.modules["numpy"].array,
                     "matrix": sys.modules["numpy"].mat
                    }[type_arg.__name__]
          return np_type(list(data))

        # If it's a Stream, let's use the Stream constructor
        from .lazy_stream import Stream
        if issubclass(type_arg, Stream):
          return Stream(data)

        # Tuple, list, set, dict, deque, etc.. all falls here
        return type_arg(data)

      return func(*args, **kwargs) # wrapper returned value
    return wrapper # elementwise_decorator returned value
  return elementwise_decorator


almost_eq = StrategyDict("almost_eq")


@almost_eq.strategy("bits")
def almost_eq(a, b, bits=32, tol=1, ignore_type=True, pad=0.):
  """
  Almost equal, based on the amount of floating point significand bits.

  Alternative to "a == b" for float numbers and iterables with float numbers,
  and tests for sequence contents (i.e., an elementwise a == b, that also
  works with generators, nested lists, nested generators, etc.). If the type
  of both the contents and the containers should be tested too, set the
  ignore_type keyword arg to False.
  Default version is based on 32 bits IEEE 754 format (23 bits significand).
  Could use 64 bits (52 bits significand) but needs a
  native float type with at least that size in bits.
  If a and b sizes differ, at least one will be padded with the pad input
  value to keep going with the comparison.

  Note
  ----
  Be careful with endless generators!

  """
  if not (ignore_type or type(a) == type(b)):
    return False
  is_it_a = isinstance(a, Iterable)
  is_it_b = isinstance(b, Iterable)
  if is_it_a != is_it_b:
    return False
  if is_it_a:
    return all(almost_eq.bits(ai, bi, bits, tol, ignore_type)
               for ai, bi in xzip_longest(a, b, fillvalue=pad))
  significand = {32: 23, 64: 52, 80: 63, 128: 112
                }[bits] # That doesn't include the sign bit
  power = tol - significand - 1
  return abs(a - b) <= 2 ** power * abs(a + b)


@almost_eq.strategy("diff")
def almost_eq(a, b, max_diff=1e-7, ignore_type=True, pad=0.):
  """
  Almost equal, based on the :math:`|a - b|` value.

  Alternative to "a == b" for float numbers and iterables with float numbers.
  See almost_eq for more information.

  This version based on the non-normalized absolute diff, similar to what
  unittest does with its assertAlmostEquals. If a and b sizes differ, at least
  one will be padded with the pad input value to keep going with the
  comparison.

  Note
  ----
  Be careful with endless generators!

  """
  if not (ignore_type or type(a) == type(b)):
    return False
  is_it_a = isinstance(a, Iterable)
  is_it_b = isinstance(b, Iterable)
  if is_it_a != is_it_b:
    return False
  if is_it_a:
    return all(almost_eq.diff(ai, bi, max_diff, ignore_type)
               for ai, bi in xzip_longest(a, b, fillvalue=pad))
  return abs(a - b) <= max_diff


def sHz(rate):
  """
  Unit conversion constants.

  Useful for casting to/from the default package units (number of samples for
  time and rad/second for frequency). You can use expressions like
  ``440 * Hz`` to get a frequency value, or assign like ``kHz = 1e3 * Hz`` to
  get other unit, as you wish.

  Parameters
  ----------
  rate :
    Sample rate in samples per second

  Returns
  -------
  A tuple ``(s, Hz)``, where ``s`` is the second unit and ``Hz`` is the hertz
  unit, as the number of samples and radians per sample, respectively.

  """
  return float(rate), 2 * pi / rate


def freq2lag(v):
  """ Converts from frequency (rad/sample) to lag (number of samples). """
  return 2 * pi / v
freq_to_lag = _internals.deprecate(freq2lag)


def lag2freq(v):
  """ Converts from lag (number of samples) to frequency (rad/sample). """
  return 2 * pi / v
lag_to_freq = _internals.deprecate(freq2lag)

########NEW FILE########
__FILENAME__ = lazy_poly
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Sun Oct 07 2012
# danilo [dot] bellini [at] gmail [dot] com
"""
Polynomial model and Waring-Lagrange polynomial interpolator
"""

from __future__ import division

import operator
from collections import Iterable, deque
from functools import reduce
import itertools as it

# Audiolazy internal imports
from .lazy_core import AbstractOperatorOverloaderMeta, StrategyDict
from .lazy_text import multiplication_formatter, pair_strings_sum_formatter
from .lazy_misc import rint
from .lazy_compat import (meta, iteritems, xrange, xzip, INT_TYPES,
                          xzip_longest)
from .lazy_stream import Stream, tostream, thub

__all__ = ["PolyMeta", "Poly", "x", "lagrange", "resample"]


class PolyMeta(AbstractOperatorOverloaderMeta):
  """
  Poly metaclass. This class overloads few operators to the Poly class.
  All binary dunders (non reverse) should be implemented on the Poly class
  """
  __operators__ = ("+ - " # elementwise
                   "* " # cross
                   "pow truediv " # when other is not Poly (no reverse)
                   "eq ne ") # comparison of Poly terms

  def __rbinary__(cls, op):
    op_func = op.func
    def dunder(self, other): # The "other" is probably a number
      return op_func(cls(other, zero=self.zero), self)
    return dunder

  def __unary__(cls, op):
    op_func = op.func
    def dunder(self):
      return cls({k: op_func(v) for k, v in self.terms()},
                 zero=self.zero)
    return dunder


class Poly(meta(metaclass=PolyMeta)):
  """
  Model for a polynomial, Laurent polynomial or a sum of powers.

  That's not a dict and not a list but behaves like something in between.
  The "values" method allows casting to list with list(Poly.values())
  The "terms" method allows casting to dict with dict(Poly.terms()), and give
  the terms sorted by their power value if used in a loop instead of casting.

  Usually the instances of this class should be seen as immutable (this is
  a hashable instance), although there's no enforcement for that (and item
  set is allowed).

  You can use the ``x`` object and operators to create your own instances.

  Examples
  --------
  >>> x ** 5 - x + 7
  7 - x + x^5
  >>> type(x + 1)
  <class 'audiolazy.lazy_poly.Poly'>
  >>> (x + 2)(17)
  19
  >>> (x ** 2 + 2 * x + 1)(2)
  9
  >>> (x ** 2 + 2 * x + 1)(.5)
  2.25
  >>> (x ** -2 + x)(10)
  10.01
  >>> spow = x ** -2.1 + x ** .3 + x ** -1 + x - 6
  >>> value = spow(5)
  >>> "{:.6f}".format(value) # Just to see the first few digits
  '0.854710'

  """
  def __init__(self, data=None, zero=None):
    """
    Inits a polynomial from given data, which can be a list or a dict.

    A list :math:`[a_0, a_1, a_2, a_3, ...]` inits a polynomial like

    .. math::

      a_0 + a_1 . x + a_2 . x^2 + a_3 . x^3 + ...

    If data is a dictionary, powers are the keys and the :math:`a_i` factors
    are the values, so negative powers are allowed and you can neglect the
    zeros in between, i.e., a dict vith terms like ``{power: value}`` can also
    be used.

    """
    self.zero = 0. if zero is None else zero
    if isinstance(data, list):
      self._data = {power: value for power, value in enumerate(data)}
    elif isinstance(data, dict):
      self._data = dict(data)
    elif isinstance(data, Poly):
      self._data = data._data.copy()
      self.zero = data.zero if zero is None else zero
    elif data is None:
      self._data = {}
    else:
      self._data = {0: data}

    # Compact zeros
    for key, value in list(iteritems(self._data)):
      if isinstance(key, float):
        if key.is_integer():
          del self._data[key]
          key = rint(key)
          self._data[key] = value
      if not isinstance(value, Stream):
        if value == 0:
          del self._data[key]

  def __hash__(self):
    self._hashed = True
    return hash(tuple(self.terms()))

  def values(self):
    """
    Array values generator for powers from zero to upper power. Useful to cast
    as list/tuple and for numpy/scipy integration (be careful: numpy use the
    reversed from the output of this function used as input to a list or a
    tuple constructor).
    """
    if self._data:
      for key in xrange(self.order + 1):
        yield self[key]

  def terms(self):
    """
    Pairs (2-tuple) generator where each tuple has a (power, value) term,
    sorted by power. Useful for casting as dict.
    """
    for key in sorted(self._data):
      yield key, self._data[key]

  def __len__(self):
    """
    Number of terms, not values (be careful).
    """
    return len(self._data)

  def is_polynomial(self):
    """
    Tells whether it is a linear combination of natural powers of ``x``.
    """
    return all(isinstance(k, INT_TYPES) and k >= 0 for k in self._data)

  def is_laurent(self):
    """
    Boolean that indicates whether is a Laurent polynomial or not.

    A Laurent polynomial is any sum of integer powers of ``x``.

    Examples
    --------
    >>> (x + 4).is_laurent()
    True
    >>> (x ** -3 + 4).is_laurent()
    True
    >>> (x ** -3 + 4).is_polynomial()
    False
    >>> (x ** 1.1 + 4).is_laurent()
    False

    """
    return all(isinstance(k, INT_TYPES) for k in self._data)

  @property
  def order(self):
    """
    Finds the polynomial order.

    Examples
    --------
    >>> (x + 4).order
    1
    >>> (x + 4 - x ** 18).order
    18
    >>> (x - x).order
    0
    >>> (x ** -3 + 4).order
    Traceback (most recent call last):
      ...
    AttributeError: Power needs to be positive integers

    """
    if not self.is_polynomial():
      raise AttributeError("Power needs to be positive integers")
    return max(key for key in self._data) if self._data else 0

  def copy(self, zero=None):
    """
    Returns a Poly instance with the same terms, but as a "T" (tee) copy
    when they're Stream instances, allowing maths using a polynomial more
    than once.
    """
    return Poly({k: v.copy() if isinstance(v, Stream) else v
                 for k, v in self.terms()},
                zero=self.zero if zero is None else zero)

  def diff(self, n=1):
    """
    Differentiate (n-th derivative, where the default n is 1).
    """
    return Poly(reduce(lambda d, order: # Derivative order can be ignored
                         {k - 1: k * v for k, v in iteritems(d) if k != 0},
                       xrange(n), self._data),
                zero=self.zero)

  def integrate(self):
    """
    Integrate without adding an integration constant.
    """
    if -1 in self._data:
      raise ValueError("Unable to integrate term that powers to -1")
    return Poly({k + 1: v / (k + 1) for k, v in self.terms()},
                zero=self.zero)

  def __call__(self, value):
    """
    Apply value to the Poly, where value can be other Poly.
    When value is a number, a Horner-like scheme is done.
    """
    if isinstance(value, Poly):
      return Poly(sum(coeff * value ** power
                      for power, coeff in iteritems(self._data)),
                  self.zero)
    if not self._data:
      return self.zero
    if not isinstance(value, Stream):
      if value == 0:
        return self[0]

    value = thub(value, len(self))
    return reduce(
      lambda old, new: (new[0], new[1] + old[1] * value ** (old[0] - new[0])),
      sorted(iteritems(self._data), reverse=True) + [(0, 0)]
    )[1]

  def __getitem__(self, item):
    if item in self._data:
      return self._data[item]
    else:
      return self.zero

  def __setitem__(self, power, item):
    if getattr(self, "_hashed", False):
      raise TypeError("Used this Poly instance as a hashable before")
    self._data[power] = item

  # ---------------------
  # Elementwise operators
  # ---------------------
  def __add__(self, other):
    if not isinstance(other, Poly):
      other = Poly(other) # The "other" is probably a number
    intersect = [(key, self._data[key] + other._data[key])
                 for key in set(self._data).intersection(other._data)]
    return Poly(dict(it.chain(iteritems(self._data),
                              iteritems(other._data), intersect)),
                zero=self.zero)

  def __sub__(self, other):
    return self + (-other)

  # -----------------------------
  # Cross-product based operators
  # -----------------------------
  def __mul__(self, other):
    if not isinstance(other, Poly):
      other = Poly(other) # The "other" is probably a number
    new_data = {}
    thubbed_self = [(k, thub(v, len(other._data)))
                    for k, v in iteritems(self._data)]
    thubbed_other = [(k, thub(v, len(self._data)))
                     for k, v in iteritems(other._data)]
    for k1, v1 in thubbed_self:
      for k2, v2 in thubbed_other:
        if k1 + k2 in new_data:
          new_data[k1 + k2] += v1 * v2
        else:
          new_data[k1 + k2] = v1 * v2
    return Poly(new_data, zero=self.zero)

  # ----------
  # Comparison
  # ----------
  def __eq__(self, other):
    if not isinstance(other, Poly):
      other = Poly(other, zero=self.zero) # The "other" is probably a number

    def sorted_flattenizer(instance):
      return reduce(operator.concat, instance.terms(), tuple())

    def is_pair_equal(a, b):
      if isinstance(a, Stream) or isinstance(b, Stream):
        return a is b
      return a == b

    for pair in xzip_longest(sorted_flattenizer(self),
                             sorted_flattenizer(other)):
      if not is_pair_equal(*pair):
        return False
    return is_pair_equal(self.zero, other.zero)

  def __ne__(self, other):
    return not(self == other)

  # -----------------------------------------
  # Operators (mainly) for non-Poly instances
  # -----------------------------------------
  def __pow__(self, other):
    """
    Power operator. The "other" parameter should be an int (or anything like),
    but it works with float when the Poly has only one term.
    """
    if isinstance(other, Poly):
      if any(k != 0 for k, v in other.terms()):
        raise NotImplementedError("Can't power general Poly instances")
      other = other[0]
    if other == 0:
      return Poly(1, zero=self.zero)
    if len(self._data) == 0:
      return Poly(zero=self.zero)
    if len(self._data) == 1:
      return Poly({k * other: 1 if v == 1 else v ** other # To avoid casting
                   for k, v in iteritems(self._data)},
                  zero=self.zero)
    return reduce(operator.mul, [self.copy()] * (other - 1) + [self])

  def __truediv__(self, other):
    if isinstance(other, Poly):
      if len(other) == 1:
        delta, value = next(iteritems(other._data))
        return Poly({(k - delta): operator.truediv(v, value)
                     for k, v in iteritems(self._data)},
                    zero=self.zero)
      elif len(other) == 0:
        raise ZeroDivisionError("Dividing Poly instance by zero")
      raise NotImplementedError("Can't divide general Poly instances")
    other = thub(other, len(self))
    return Poly({k: operator.truediv(v, other)
                 for k, v in iteritems(self._data)},
                zero=self.zero)

  # ---------------------
  # String representation
  # ---------------------
  def __str__(self):
    term_strings = []
    for power, value in self.terms():
      if isinstance(value, Iterable):
        value = "a{}".format(power).replace(".", "_").replace("-", "m")
      if value != 0.:
        term_strings.append(multiplication_formatter(power, value, "x"))
    return "0" if len(term_strings) == 0 else \
           reduce(pair_strings_sum_formatter, term_strings)

  __repr__ = __str__

  # -----------
  # NumPy-based
  # -----------
  @property
  def roots(self):
    """
    Returns a list with all roots. Needs Numpy.
    """
    import numpy as np
    return np.roots(list(self.values())[::-1]).tolist()


x = Poly({1: 1})
lagrange = StrategyDict("lagrange")


@lagrange.strategy("func")
def lagrange(pairs):
  """
  Waring-Lagrange interpolator function.

  Parameters
  ----------
  pairs :
    Iterable with pairs (tuples with two values), corresponding to points
    ``(x, y)`` of the function.

  Returns
  -------
  A function that returns the interpolator result for a given ``x``.

  """
  prod = lambda args: reduce(operator.mul, args)
  xv, yv = xzip(*pairs)
  return lambda k: sum( yv[j] * prod( (k - rk) / (rj - rk)
                                      for rk in xv if rj != rk )
                        for j, rj in enumerate(xv) )


@lagrange.strategy("poly")
def lagrange(pairs):
  """
  Waring-Lagrange interpolator polynomial.

  Parameters
  ----------
  pairs :
    Iterable with pairs (tuples with two values), corresponding to points
    ``(x, y)`` of the function.

  Returns
  -------
  A Poly instance that allows finding the interpolated value for any ``x``.

  """
  return lagrange.func(pairs)(x)


@tostream
def resample(sig, old=1, new=1, order=3, zero=0.):
  """
  Generic resampler based on Waring-Lagrange interpolators.

  Parameters
  ----------
  sig :
    Input signal (any iterable).
  old :
    Time duration reference (defaults to 1, allowing percentages to the ``new``
    keyword argument). This can be float number, or perhaps a Stream instance.
  new :
    Time duration that the reference will have after resampling.
    For example, if ``old = 1, new = 2``, then
    there will be 2 samples yielded for each sample from input.
    This can be a float number, or perhaps a Stream instance.
  order :
    Lagrange interpolator order. The amount of neighboring samples to be used by
    the interpolator is ``order + 1``.
  zero :
    The input should be thought as zero-padded from the left with this value.

  Returns
  -------
  The first value will be the first sample from ``sig``, and then the
  interpolator will find the next samples towards the end of the ``sig``.
  The actual sampling interval (or time step) for this interpolator obeys to
  the ``old / new`` relationship.

  Hint
  ----
  The time step can also be time-varying, although that's certainly difficult
  to synchonize (one sample is needed for each output sample). Perhaps the
  best approach for this case would be a ControlStream keeping the desired
  value at any time.

  Note
  ----
  The input isn't zero-padded at right. It means that the last output will be
  one with interpolated with known data. For endless inputs that's ok, this
  makes no difference, but for finite inputs that may be undesirable.

  """
  sig = Stream(sig)
  threshold = .5 * (order + 1)
  step = old / new
  data = deque([zero] * (order + 1), maxlen=order + 1)
  data.extend(sig.take(rint(threshold)))
  idx = int(threshold)
  isig = iter(sig)
  if isinstance(step, Iterable):
    step = iter(step)
    while True:
      yield lagrange(enumerate(data))(idx)
      idx += next(step)
      while idx > threshold:
        data.append(next(isig))
        idx -= 1
  else:
    while True:
      yield lagrange(enumerate(data))(idx)
      idx += step
      while idx > threshold:
        data.append(next(isig))
        idx -= 1

########NEW FILE########
__FILENAME__ = lazy_stream
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Sun Jul 22 2012
# danilo [dot] bellini [at] gmail [dot] com
"""
Stream class definition module
"""

import itertools as it
from collections import Iterable, deque
from functools import wraps
from warnings import warn
from math import isinf

# Audiolazy internal imports
from .lazy_misc import blocks, rint
from .lazy_compat import meta, xrange, xmap, xfilter, NEXT_NAME
from .lazy_core import AbstractOperatorOverloaderMeta
from .lazy_math import inf

__all__ = ["StreamMeta", "Stream", "avoid_stream", "tostream",
           "ControlStream", "MemoryLeakWarning", "StreamTeeHub", "thub",
           "Streamix"]


class StreamMeta(AbstractOperatorOverloaderMeta):
  """
  Stream metaclass. This class overloads all operators to the Stream class,
  but cmp/rcmp (deprecated), ternary pow (could be called with Stream.map) as
  well as divmod (same as pow, but this will result in a Stream of tuples).
  """
  def __binary__(cls, op):
    op_func = op.func
    def dunder(self, other):
      if isinstance(other, cls.__ignored_classes__):
        return NotImplemented
      if isinstance(other, Iterable):
        return Stream(xmap(op_func, iter(self), iter(other)))
      return Stream(xmap(lambda a: op_func(a, other), iter(self)))
    return dunder

  def __rbinary__(cls, op):
    op_func = op.func
    def dunder(self, other):
      if isinstance(other, cls.__ignored_classes__):
        return NotImplemented
      if isinstance(other, Iterable):
        return Stream(xmap(op_func, iter(other), iter(self)))
      return Stream(xmap(lambda a: op_func(other, a), iter(self)))
    return dunder

  def __unary__(cls, op):
    op_func = op.func
    def dunder(self):
      return Stream(xmap(op_func, iter(self)))
    return dunder


class Stream(meta(Iterable, metaclass=StreamMeta)):
  """
  Stream class. Stream instances are iterables that can be seem as generators
  with elementwise operators.

  Examples
  --------
  If you want something like:

  >>> import itertools
  >>> x = itertools.count()
  >>> y = itertools.repeat(3)
  >>> z = 2*x + y
  Traceback (most recent call last):
      ...
  TypeError: unsupported operand type(s) for *: 'int' and ...

  That won't work with standard itertools. That's an error, and not only
  __mul__ but also __add__ isn't supported by their types. On the other hand,
  you can use this Stream class:

  >>> x = Stream(itertools.count()) # Iterable
  >>> y = Stream(3) # Non-iterable repeats endlessly
  >>> z = 2*x + y
  >>> z
  <audiolazy.lazy_stream.Stream object at 0x...>
  >>> z.take(12)
  [3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25]

  If you just want to use your existing code, an "itertools" alternative is
  already done to help you:

  >>> from audiolazy import lazy_itertools as itertools
  >>> x = itertools.count()
  >>> y = itertools.repeat(3)
  >>> z = 2*x + y
  >>> w = itertools.takewhile(lambda pair: pair[0] < 10, enumerate(z))
  >>> list(el for idx, el in w)
  [3, 5, 7, 9, 11, 13, 15, 17, 19, 21]

  All operations over Stream objects are lazy and not thread-safe.

  See Also
  --------
  thub :
    "Tee" hub to help using the Streams like numbers in equations and filters.
  tee :
    Just like itertools.tee, but returns a tuple of Stream instances.
  Stream.tee :
    Keeps the Stream usable and returns a copy to be used safely.
  Stream.copy :
    Same to ``Stream.tee``.

  Notes
  -----
  In that example, after declaring z as function of x and y, you should
  not use x and y anymore. Use the thub() or the tee() functions, or
  perhaps the x.tee() or x.copy() Stream methods instead, if you need
  to use x again otherwhere.

  """
  __ignored_classes__ = tuple()

  def __init__(self, *dargs):
    """
    Constructor for a Stream.

    Parameters
    ----------
    *dargs:
      The parameters should be iterables that will be chained together. If
      they're not iterables, the stream will be an endless repeat of the
      given elements. If any parameter is a generator and its contents is
      used elsewhere, you should use the "tee" (Stream method or itertools
      function) before.

    Notes
    -----
    All operations that works on the elements will work with this iterator
    in a element-wise fashion (like Numpy 1D arrays). When the stream
    sizes differ, the resulting stream have the size of the shortest
    operand.

    Examples
    --------
    A finite sequence:

    >>> x = Stream([1,2,3]) + Stream([8,5]) # Finite constructor
    >>> x
    <audiolazy.lazy_stream.Stream object at 0x...>
    >>> tuple(x)
    (9, 7)

    But be careful:

    >>> x = Stream(1,2,3) + Stream(8,5) # Periodic constructor
    >>> x
    <audiolazy.lazy_stream.Stream object at 0x...>
    >>> x.take(15) # Don't try "tuple" or "list": this Stream is endless!
    [9, 7, 11, 6, 10, 8, 9, 7, 11, 6, 10, 8, 9, 7, 11]

    """
    if len(dargs) == 0:
      raise TypeError("Missing argument(s)")

    elif len(dargs) == 1:
      if isinstance(dargs[0], Iterable):
        self._data = iter(dargs[0])
      else:
        self._data = it.repeat(dargs[0])

    else:
      if all(isinstance(arg, Iterable) for arg in dargs):
        self._data = it.chain(*dargs)
      elif not any(isinstance(arg, Iterable) for arg in dargs):
        self._data = it.cycle(dargs)
      else:
        raise TypeError("Input with both iterables and non-iterables")

  def __iter__(self):
    """ Returns the Stream contents iterator. """
    return self._data

  def __bool__(self):
    """
    Boolean value of a stream, called by the bool() built-in and by "if"
    tests. As boolean operators "and", "or" and "not" couldn't be overloaded,
    any trial to cast an instance of this class to a boolean should be seen
    as a mistake.
    """
    raise TypeError("Streams can't be used as booleans.\n"
                    "If you need a boolean stream, try using bitwise "
                    "operators & and | instead of 'and' and 'or'. If using "
                    "'not', you can use the inversion operator ~, casting "
                    "its returned int back to bool.\n"
                    "If you're using it in a 'if' comparison (e.g. for unit "
                    "testing), try to freeze the stream before with "
                    "list(my_stream) or tuple(my_stream).")

  __nonzero__ = __bool__ # For Python 2.x compatibility

  def blocks(self, *args, **kwargs):
    """
    Interface to apply audiolazy.blocks directly in a stream, returning
    another stream. Use keyword args.
    """
    return Stream(blocks(iter(self), *args, **kwargs))

  def take(self, n=None, constructor=list):
    """
    Returns a container with the n first elements from the Stream, or less if
    there aren't enough. Use this without args if you need only one element
    outside a list.

    Parameters
    ----------
    n :
      Number of elements to be taken. Defaults to None.
      Rounded when it's a float, and this can be ``inf`` for taking all.
    constructor :
      Container constructor function that can receie a generator as input.
      Defaults to ``list``.

    Returns
    -------
    The first ``n`` elements of the Stream sequence, created by the given
    constructor unless ``n == None``, which means returns the next element
    from the sequence outside any container.
    If ``n`` is None, this can raise StopIteration due to lack of data in
    the Stream. When ``n`` is a number, there's no such exception.

    Examples
    --------
    >>> Stream(5).take(3) # Three elements
    [5, 5, 5]
    >>> Stream(1.2, 2, 3).take() # One element, outside a container
    1.2
    >>> Stream(1.2, 2, 3).take(1) # With n = 1 argument, it'll be in a list
    [1.2]
    >>> Stream(1.2, 2, 3).take(1, constructor=tuple) # Why not a tuple?
    (1.2,)
    >>> Stream([1, 2]).take(3) # More than the Stream size, n is integer
    [1, 2]
    >>> Stream([]).take() # More than the Stream size, n is None
    Traceback (most recent call last):
      ...
    StopIteration

    Taking rounded float quantities and "up to infinity" elements
    (don't try using ``inf`` with endless Stream instances):

    >>> Stream([4, 3, 2, 3, 2]).take(3.4)
    [4, 3, 2]
    >>> Stream([4, 3, 2, 3, 2]).take(3.6)
    [4, 3, 2, 3]
    >>> Stream([4, 3, 2, 3, 2]).take(inf)
    [4, 3, 2, 3, 2]

    See Also
    --------
    Stream.peek :
      Returns the n first elements from the Stream, without removing them.

    Note
    ----
    You should avoid using take() as if this would be an iterator. Streams
    are iterables that can be easily part of a "for" loop, and their
    iterators (the ones automatically used in for loops) are slightly faster.
    Use iter() builtin if you need that, instead, or perhaps the blocks
    method.

    """
    if n is None:
      return next(self._data)
    if isinf(n) and n > 0:
      return constructor(self._data)
    if isinstance(n, float):
      n = rint(n) if n > 0 else 0 # So this works with -inf and nan
    return constructor(next(self._data) for _ in xrange(n))

  def copy(self):
    """
    Returns a "T" (tee) copy of the given stream, allowing the calling
    stream to continue being used.
    """
    a, b = it.tee(self._data) # 2 generators, not thread-safe
    self._data = a
    return Stream(b)

  def peek(self, n=None, constructor=list):
    """
    Sees/peeks the next few items in the Stream, without removing them.

    Besides that this functions keeps the Stream items, it's the same to the
    ``Stream.take()`` method.

    See Also
    --------
    Stream.take :
      Returns the n first elements from the Stream, removing them.

    Note
    ----
    When applied in a StreamTeeHub, this method doesn't consume a copy.
    Data evaluation is done only once, i.e., after peeking the data is simply
    stored to be yielded again when asked for.

    """
    return self.copy().take(n=n, constructor=constructor)

  def skip(self, n):
    """
    Throws away the first ``n`` values from the Stream.

    Note
    ----
    Performs the evaluation lazily, i.e., the values are thrown away only
    after requesting the next value.

    """
    def skipper(data):
      for _ in xrange(int(round(n))):
        next(data)
      for el in data:
        yield el

    self._data = skipper(self._data)
    return self

  def limit(self, n):
    """
    Enforces the Stream to finish after ``n`` items.
    """
    data = self._data
    self._data = (next(data) for _ in xrange(int(round(n))))
    return self

  def __getattr__(self, name):
    """
    Returns a Stream of attributes or methods, got in an elementwise fashion.
    """
    if name == NEXT_NAME:
      raise AttributeError("Streams are iterable, not iterators")
    return Stream(getattr(a, name) for a in self._data)

  def __call__(self, *args, **kwargs):
    """
    Returns the results from calling elementwise (where each element is
    assumed to be callable), with the same arguments.
    """
    return Stream(a(*args, **kwargs) for a in self._data)

  def append(self, *other):
    """
    Append self with other stream(s). Chaining this way has the behaviour:

      ``self = Stream(self, *others)``

    """
    self._data = it.chain(self._data, Stream(*other)._data)
    return self

  def map(self, func):
    """
    A lazy way to apply the given function to each element in the stream.
    Useful for type casting, like:

    >>> from audiolazy import count
    >>> count().take(5)
    [0, 1, 2, 3, 4]
    >>> my_stream = count().map(float)
    >>> my_stream.take(5) # A float counter
    [0.0, 1.0, 2.0, 3.0, 4.0]

    """
    self._data = xmap(func, self._data)
    return self

  def filter(self, func):
    """
    A lazy way to skip elements in the stream that gives False for the given
    function.
    """
    self._data = xfilter(func, self._data)
    return self

  @classmethod
  def register_ignored_class(cls, ignore):
    cls.__ignored_classes__ += (ignore,)

  def __abs__(self):
    return self.map(abs)


def avoid_stream(cls):
  """
  Decorator to a class whose instances should avoid casting to a Stream when
  used with operators applied to them.
  """
  Stream.register_ignored_class(cls)
  return cls


def tostream(func, module_name=None):
  """
  Decorator to convert the function output into a Stream. Useful for
  generator functions.

  Note
  ----
  Always use the ``module_name`` input when "decorating" a function that was
  defined in other module.

  """
  @wraps(func)
  def new_func(*args, **kwargs):
    return Stream(func(*args, **kwargs))
  if module_name is not None:
    new_func.__module__ = module_name
  return new_func


class ControlStream(Stream):
  """
  A Stream that yields a control value that can be changed at any time.
  You just need to set the attribute "value" for doing so, and the next
  value the Stream will yield is the given value.

  Examples
  --------

  >>> cs = ControlStream(7)
  >>> data = Stream(1, 3) # [1, 3, 1, 3, 1, 3, ...] endless iterable
  >>> res = data + cs
  >>> res.take(5)
  [8, 10, 8, 10, 8]
  >>> cs.value = 9
  >>> res.take(5)
  [12, 10, 12, 10, 12]

  """
  def __init__(self, value):
    self.value = value

    def data_generator():
      while True:
        yield self.value

    super(ControlStream, self).__init__(data_generator())


class MemoryLeakWarning(Warning):
  """ A warning to be used when a memory leak is detected. """


class StreamTeeHub(Stream):
  """
  A Stream that returns a different iterator each time it is used.

  See Also
  --------
  thub :
    Auto-copy "tee hub" and helpful constructor alternative for this class.

  """
  def __init__(self, data, n):
    super(StreamTeeHub, self).__init__(data)
    iter_self = super(StreamTeeHub, self).__iter__()
    self._iters = list(it.tee(iter_self, n))

  def __iter__(self):
    try:
      return self._iters.pop()
    except IndexError:
      raise IndexError("StreamTeeHub has no more copies left to use.")

  def __del__(self):
    if self._iters != []:
      warn("StreamTeeHub requesting {0} more copies than "
           "needed".format(len(self._iters)), MemoryLeakWarning)

  def take(self, *args, **kwargs):
    """
    Fake function just to avoid using inherited Stream.take implicitly.

    Warning
    -------
    You shouldn't need to call this method directly.
    If you need a Stream instance to work progressively changing it, try:

    >>> data = thub([1, 2, 3], 2) # A StreamTeeHub instance
    >>> first_copy = Stream(data)
    >>> first_copy.take(2)
    [1, 2]
    >>> list(data) # Gets the second copy
    [1, 2, 3]
    >>> first_copy.take()
    3

    If you just want to see the first few values, try
    ``self.peek(*args, **kwargs)`` instead.

    >>> data = thub((9, -1, 0, 4), 2) # StreamTeeHub instance
    >>> data.peek()
    9
    >>> data.peek(3)
    [9, -1, 0]
    >>> list(data) # First copy
    [9, -1, 0, 4]
    >>> data.peek(1)
    [9]
    >>> second_copy = Stream(data)
    >>> second_copy.peek(2)
    [9, -1]
    >>> data.peek() # There's no third copy
    Traceback (most recent call last):
        ...
    IndexError: StreamTeeHub has no more copies left to use.

    If you want to consume from every StreamTeeHub copy, you probably
    should change your code before calling the ``thub()``,
    but you still might use:

    >>> data = thub(Stream(1, 2, 3), 2)
    >>> Stream.take(data, n=2)
    [1, 2]
    >>> Stream(data).take() # First copy
    3
    >>> Stream(data).take(1) # Second copy
    [3]
    >>> Stream(data)
    Traceback (most recent call last):
        ...
    IndexError: StreamTeeHub has no more copies left to use.

    """
    raise AttributeError("Use peek or cast to Stream.")

  def copy(self):
    """
    Returns a new "T" (tee) copy of this StreamTeeHub without consuming
    any of the copies done with the constructor.
    """
    if self._iters:
      a, b = it.tee(self._iters[0])
      self._iters[0] = a
      return Stream(b)
    iter(self) # Try to consume (so it'll raise the same error as usual)

  limit = wraps(Stream.limit)(lambda self, n: Stream(self).limit(n))
  skip = wraps(Stream.skip)(lambda self, n: Stream(self).skip(n))
  append = wraps(Stream.append)( lambda self, *other:
                                   Stream(self).append(*other) )
  map = wraps(Stream.map)(lambda self, func: Stream(self).map(func))
  filter = wraps(Stream.filter)(lambda self, func: Stream(self).filter(func))


def thub(data, n):
  """
  Tee or "T" hub auto-copier to help working with Stream instances as well as
  with numbers.

  Parameters
  ----------
  data :
    Input to be copied. Can be anything.
  n :
    Number of copies.

  Returns
  -------
  A StreamTeeHub instance, if input data is iterable.
  The data itself, otherwise.

  Examples
  --------

  >>> def sub_sum(x, y):
  ...   x = thub(x, 2) # Casts to StreamTeeHub, when needed
  ...   y = thub(y, 2)
  ...   return (x - y) / (x + y) # Return type might be number or Stream

  With numbers:

  >>> sub_sum(1, 1.)
  0.0

  Combining number with iterable:

  >>> sub_sum(3., [1, 2, 3])
  <audiolazy.lazy_stream.Stream object at 0x...>
  >>> list(sub_sum(3., [1, 2, 3]))
  [0.5, 0.2, 0.0]

  Both iterables (the Stream input behaves like an endless [6, 1, 6, 1, ...]):

  >>> list(sub_sum([4., 3., 2., 1.], [1, 2, 3]))
  [0.6, 0.2, -0.2]
  >>> list(sub_sum([4., 3., 2., 1.], Stream(6, 1)))
  [-0.2, 0.5, -0.5, 0.0]

  This function can also be used as a an alternative to the Stream
  constructor when your function has only one parameter, to avoid casting
  when that's not needed:

  >>> func = lambda x: 250 * thub(x, 1)
  >>> func(1)
  250
  >>> func([2] * 10)
  <audiolazy.lazy_stream.Stream object at 0x...>
  >>> func([2] * 10).take(5)
  [500, 500, 500, 500, 500]

  """
  return StreamTeeHub(data, n) if isinstance(data, Iterable) else data


class Streamix(Stream):
  """
  Stream mixer of iterables.

  Examples
  --------

  With integer iterables:

  >>> s1 = [-1, 1, 3, 2]
  >>> s2 = Stream([4, 4, 4])
  >>> s3 = tuple([-3, -5, -7, -5, -7, -1])
  >>> smix = Streamix(zero=0) # Default zero is 0.0, changed to keep integers
  >>> smix.add(0, s1) # 1st number = delta time (in samples) from last added
  >>> smix.add(2, s2)
  >>> smix.add(0, s3)
  >>> smix
  <audiolazy.lazy_stream.Streamix object at ...>
  >>> list(smix)
  [-1, 1, 4, 1, -3, -5, -7, -1]

  With time constants:

  >>> from audiolazy import sHz, line
  >>> s, Hz = sHz(10) # You probably will use 44100 or something alike, not 10
  >>> sdata = list(line(2 * s, 1, -1, finish=True))
  >>> smix = Streamix()
  >>> smix.add(0.0 * s, sdata)
  >>> smix.add(0.5 * s, sdata)
  >>> smix.add(1.0 * s, sdata)
  >>> result = [round(sm, 2) for sm in smix]
  >>> len(result)
  35
  >>> 0.5 * s # Let's see how many samples this is
  5.0
  >>> result[:7]
  [1.0, 0.89, 0.79, 0.68, 0.58, 1.47, 1.26]
  >>> result[10:17]
  [0.42, 0.21, 0.0, -0.21, -0.42, 0.37, 0.05]
  >>> result[-1]
  -1.0

  See Also
  --------
  ControlStream :
    Stream (iterable with operators)
  sHz :
    Time in seconds (s) and frequency in hertz (Hz) constants from sample
    rate in samples/second.

  """
  def __init__(self, keep=False, zero=0.):
    self._not_playing = deque() # Tuples (integer delta, iterable)
    self._playing = []
    self.keep = keep

    def data_generator():
      count = 0.5
      to_remove = []

      while True:
        # Find if there's anything new to start "playing"
        while self._not_playing and (count >= self._not_playing[0][0]):
          delta, newdata = self._not_playing.popleft()
          self._playing.append(newdata)
          count -= delta # Delta might be float (less error propagation)

        # Sum the data to be played, seeing if something finished
        data = zero
        for snd in self._playing:
          try:
            data += next(snd)
          except StopIteration:
            to_remove.append(snd)

        # Remove finished
        if to_remove:
          for snd in to_remove:
            self._playing.remove(snd)
          to_remove = []

        # Tests whether there were any data (finite Streamix had finished?)
        if not (self.keep or self._playing or self._not_playing):
          break # Stops the iterator

        # Finish iteration
        yield data
        count += 1.

    super(Streamix, self).__init__(data_generator())

  def add(self, delta, data):
    """
    Adds (enqueues) an iterable event to the mixer.

    Parameters
    ----------
    delta :
      Time in samples since last added event. This can be zero and can be
      float. Use "s" object from sHz for time conversion.
    data :
      Iterable (e.g. a list, a tuple, a Stream) to be "played" by the mixer at
      the given time delta.

    See Also
    --------
    sHz :
      Time in seconds (s) and frequency in hertz (Hz) constants from sample
      rate in samples/second.

    """
    if delta < 0:
      raise ValueError("Delta time should be always positive")
    self._not_playing.append((delta, iter(data)))

########NEW FILE########
__FILENAME__ = lazy_synth
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Wed Jul 18 2012
# danilo [dot] bellini [at] gmail [dot] com
"""
Simple audio/stream synthesis module
"""

from math import sin, pi, ceil, isinf
import collections
import random

# Audiolazy internal imports
from .lazy_stream import Stream, tostream, AbstractOperatorOverloaderMeta
from .lazy_itertools import cycle
from .lazy_filters import comb
from .lazy_compat import meta, iteritems, xrange, xzip
from .lazy_misc import rint

__all__ = ["modulo_counter", "line", "fadein", "fadeout", "attack", "ones",
           "zeros", "zeroes", "adsr", "white_noise", "gauss_noise",
           "TableLookupMeta", "TableLookup", "DEFAULT_TABLE_SIZE",
           "sin_table", "saw_table", "sinusoid", "impulse", "karplus_strong"]


@tostream
def modulo_counter(start=0., modulo=256., step=1.):
  """
  Creates a lazy endless counter stream with the given modulo, i.e., its
  values ranges from 0. to the given "modulo", somewhat equivalent to:\n
    Stream(itertools.count(start, step)) % modulo\n
  Yet the given step can be an iterable, and doen't create unneeded big
  ints. All inputs can be float. Input order remembers slice/range inputs.
  All inputs can also be iterables. If any of them is an iterable, the end
  of this counter happen when there's no more data in one of those inputs.
  to continue iteration.
  """
  if isinstance(start, collections.Iterable):
    lastp = 0.
    c = 0.
    if isinstance(step, collections.Iterable):
      if isinstance(modulo, collections.Iterable):
        for p, m, s in xzip(start, modulo, step):
          c += p - lastp
          c = c % m % m
          yield c
          c += s
          lastp = p
      else:
        for p, s in xzip(start, step):
          c += p - lastp
          c = c % modulo % modulo
          yield c
          c += s
          lastp = p
    else:
      if isinstance(modulo, collections.Iterable):
        for p, m in xzip(start, modulo):
          c += p - lastp
          c = c % m % m
          yield c
          c += step
          lastp = p
      else: # Only start is iterable. This should be optimized!
        if step == 0:
          for p in start:
            yield p % modulo % modulo
        else:
          steps = int(modulo / step)
          if steps > 1:
            n = 0
            for p in start:
              c += p - lastp
              yield (c + n * step) % modulo % modulo
              lastp = p
              n += 1
              if n == steps:
                n = 0
                c = (c + steps * step) % modulo % modulo
          else:
            for p in start:
              c += p - lastp
              c = c % modulo % modulo
              yield c
              c += step
              lastp = p
  else:
    c = start
    if isinstance(step, collections.Iterable):
      if isinstance(modulo, collections.Iterable):
        for m, s in xzip(modulo, step):
          c = c % m % m
          yield c
          c += s
      else: # Only step is iterable. This should be optimized!
        for s in step:
          c = c % modulo % modulo
          yield c
          c += s
    else:
      if isinstance(modulo, collections.Iterable):
        for m in modulo:
          c = c % m % m
          yield c
          c += step
      else: # None is iterable
        if step == 0:
          c = start % modulo % modulo
          while True:
            yield c
        else:
          steps = int(modulo / step)
          if steps > 1:
            n = 0
            while True:
              yield (c + n * step) % modulo % modulo
              n += 1
              if n == steps:
                n = 0
                c = (c + steps * step) % modulo % modulo
          else:
            while True:
              c = c % modulo % modulo
              yield c
              c += step


@tostream
def line(dur, begin=0., end=1., finish=False):
  """
  Finite Stream with a straight line, could be used as fade in/out effects.

  Parameters
  ----------
  dur :
    Duration, given in number of samples. Use the sHz function to help with
    durations in seconds.
  begin, end :
    First and last (or stop) values to be yielded. Defaults to [0., 1.],
    respectively.
  finish :
    Choose if ``end`` it the last to be yielded or it shouldn't be yield at
    all. Defauts to False, which means that ``end`` won't be yield. The last
    sample won't have "end" amplitude unless finish is True, i.e., without
    explicitly saying "finish=True", the "end" input works like a "stop" range
    parameter, although it can [should] be a float. This is so to help
    concatenating several lines.

  Returns
  -------
  A finite Stream with the linearly spaced data.

  Examples
  --------
  With ``finish = True``, it works just like NumPy ``np.linspace``, besides
  argument order and lazyness:

  >>> import numpy as np
  >>> np.linspace(.2, .7, 6)
  array([ 0.2,  0.3,  0.4,  0.5,  0.6,  0.7])
  >>> line(6, .1, .7, finish=True)
  <audiolazy.lazy_stream.Stream object at 0x...>
  >>> list(line(6, .2, .7, finish=True))
  [0.2, 0.3, 0.4, 0.5, 0.6, 0.7]
  >>> list(line(6, 1, 4)) # With finish = False (default)
  [1.0, 1.5, 2.0, 2.5, 3.0, 3.5]

  Line also works with Numpy arrays and matrices

  >>> a = np.mat([[1, 2], [3, 4]])
  >>> b = np.mat([[3, 2], [2, 1]])
  >>> for el in line(4, a, b):
  ...   print(el)
  [[ 1.  2.]
   [ 3.  4.]]
  [[ 1.5   2.  ]
   [ 2.75  3.25]]
  [[ 2.   2. ]
   [ 2.5  2.5]]
  [[ 2.5   2.  ]
   [ 2.25  1.75]]

  And also with ZFilter instances:

  >>> from audiolazy import z
  >>> for el in line(4, z ** 2 - 5, z + 2):
  ...   print(el)
  z^2 - 5
  0.75 * z^2 + 0.25 * z - 3.25
  0.5 * z^2 + 0.5 * z - 1.5
  0.25 * z^2 + 0.75 * z + 0.25

  Note
  ----
  Amplitudes commonly should be float numbers between -1 and 1.
  Using line(<inputs>).append([end]) you can finish the line with one extra
  sample without worrying with the "finish" input.

  See Also
  --------
  sHz :
    Second and hertz constants from samples/second rate.

  """
  m = (end - begin) / (dur - (1. if finish else 0.))
  for sample in xrange(int(dur + .5)):
    yield begin + sample * m


def fadein(dur):
  """
  Linear fading in.

  Parameters
  ----------
  dur :
    Duration, in number of samples.

  Returns
  -------
  Stream instance yielding a line from zero to one.
  """
  return line(dur)


def fadeout(dur):
  """
  Linear fading out. Multiply by this one at end to finish and avoid clicks.

  Parameters
  ----------
  dur :
    Duration, in number of samples.

  Returns
  -------
  Stream instance yielding the line. The starting amplitude is is 1.0.
  """
  return line(dur, 1., 0.)


def attack(a, d, s):
  """
  Linear ADS fading attack stream generator, useful to be multiplied with a
  given stream.

  Parameters
  ----------
  a :
    "Attack" time, in number of samples.
  d :
    "Decay" time, in number of samples.
  s :
    "Sustain" amplitude level (should be based on attack amplitude).
    The sustain can be a Stream, if desired.

  Returns
  -------
  Stream instance yielding an endless envelope, or a finite envelope if the
  sustain input is a finite Stream. The attack amplitude is is 1.0.

  """
  # Configure sustain possibilities
  if isinstance(s, collections.Iterable):
    it_s = iter(s)
    s = next(it_s)
  else:
    it_s = None

  # Attack and decay lines
  m_a = 1. / a
  m_d = (s - 1.) / d
  len_a = int(a + .5)
  len_d = int(d + .5)
  for sample in xrange(len_a):
    yield sample * m_a
  for sample in xrange(len_d):
    yield 1. + sample * m_d

  # Sustain!
  if it_s is None:
    while True:
      yield s
  else:
    for s in it_s:
      yield s


@tostream
def ones(dur=None):
  """
  Ones stream generator.
  You may multiply your endless stream by this to enforce an end to it.

  Parameters
  ----------
  dur :
    Duration, in number of samples; endless if not given.

  Returns
  -------
  Stream that repeats "1.0" during a given time duration (if any) or
  endlessly.

  """
  if dur is None or (isinf(dur) and dur > 0):
    while True:
      yield 1.0
  for x in xrange(int(.5 + dur)):
    yield 1.0


@tostream
def zeros(dur=None):
  """
  Zeros/zeroes stream generator.
  You may sum your endless stream by this to enforce an end to it.

  Parameters
  ----------
  dur :
    Duration, in number of samples; endless if not given.

  Returns
  -------
  Stream that repeats "0.0" during a given time duration (if any) or
  endlessly.

  """
  if dur is None or (isinf(dur) and dur > 0):
    while True:
      yield 0.0
  for x in xrange(int(.5 + dur)):
    yield 0.0

zeroes = zeros


@tostream
def adsr(dur, a, d, s, r):
  """
  Linear ADSR envelope.

  Parameters
  ----------
  dur :
    Duration, in number of samples, including the release time.
  a :
    "Attack" time, in number of samples.
  d :
    "Decay" time, in number of samples.
  s :
    "Sustain" amplitude level (should be based on attack amplitude).
  r :
    "Release" time, in number of samples.

  Returns
  -------
  Stream instance yielding a finite ADSR envelope, starting and finishing with
  0.0, having peak value of 1.0.

  """
  m_a = 1. / a
  m_d = (s - 1.) / d
  m_r = - s * 1. / r
  len_a = int(a + .5)
  len_d = int(d + .5)
  len_r = int(r + .5)
  len_s = int(dur + .5) - len_a - len_d - len_r
  for sample in xrange(len_a):
    yield sample * m_a
  for sample in xrange(len_d):
    yield 1. + sample * m_d
  for sample in xrange(len_s):
    yield s
  for sample in xrange(len_r):
    yield s + sample * m_r


@tostream
def white_noise(dur=None, low=-1., high=1.):
  """
  White noise stream generator.

  Parameters
  ----------
  dur :
    Duration, in number of samples; endless if not given (or None).
  low, high :
    Lower and higher limits. Defaults to the [-1; 1] range.

  Returns
  -------
  Stream yielding random numbers between -1 and 1.

  """
  if dur is None or (isinf(dur) and dur > 0):
    while True:
      yield random.uniform(low, high)
  for x in xrange(rint(dur)):
    yield random.uniform(low, high)


@tostream
def gauss_noise(dur=None, mu=0., sigma=1.):
  """
  Gaussian (normal) noise stream generator.

  Parameters
  ----------
  dur :
    Duration, in number of samples; endless if not given (or None).
  mu :
    Distribution mean. Defaults to zero.
  sigma :
    Distribution standard deviation. Defaults to one.

  Returns
  -------
  Stream yielding Gaussian-distributed random numbers.

  Warning
  -------
  This function can yield values outside the [-1; 1] range, and you might
  need to clip its results.

  See Also
  --------
  clip:
    Clips the signal up to both a lower and a higher limit.

  """
  if dur is None or (isinf(dur) and dur > 0):
    while True:
      yield random.gauss(mu, sigma)
  for x in xrange(rint(dur)):
    yield random.gauss(mu, sigma)


class TableLookupMeta(AbstractOperatorOverloaderMeta):
  """
  Table lookup metaclass. This class overloads all operators to the
  TableLookup class, applying them to the table contents, elementwise.
  Table length and number of cycles should be equal for this to work.
  """
  __operators__ = "+ - * / // % ** << >> & | ^ ~"

  def __binary__(cls, op):
    op_func = op.func
    def dunder(self, other):
      if isinstance(other, TableLookup):
        if self.cycles != other.cycles:
          raise ValueError("Incompatible number of cycles")
        if len(self) != len(other):
          raise ValueError("Incompatible sizes")
        zip_tables = xzip(self.table, other.table)
        new_table = [op_func(data1, data2) for data1, data2 in zip_tables]
        return TableLookup(new_table, self.cycles)
      if isinstance(other, (int, float, complex)):
        new_table = [op_func(data, other) for data in self.table]
        return TableLookup(new_table, self.cycles)
      raise NotImplementedError("Unknown action do be done")
    return dunder

  def __rbinary__(cls, op):
    op_func = op.func
    def dunder(self, other):
      if isinstance(other, (int, float, complex)):
        new_table = [op_func(other, data) for data in self.table]
        return TableLookup(new_table, self.cycles)
      raise NotImplementedError("Unknown action do be done")
    return dunder

  def __unary__(cls, op):
    op_func = op.func
    def dunder(self):
      new_table = [op_func(data) for data in self.table]
      return TableLookup(new_table, self.cycles)
    return dunder


class TableLookup(meta(metaclass=TableLookupMeta)):
  """
  Table lookup synthesis class, also allowing multi-cycle tables as input.
  """
  def __init__(self, table, cycles=1):
    """
    Inits a table lookup. The given table should be a sequence, like a list.
    The cycles input should have the number of cycles in table for frequency
    calculation afterwards.
    """
    self.table = table
    self.cycles = cycles

  @property
  def table(self):
    return self._table

  @table.setter
  def table(self, value):
    self._table = value
    self._len = len(value)

  def __len__(self):
    return self._len

  def __call__(self, freq, phase=0.):
    """
    Returns a wavetable lookup synthesis endless stream. Play it with the
    given frequency and starting phase. Phase is given in rads, and frequency
    in rad/sample. Accepts streams of numbers, as well as numbers, for both
    frequency and phase inputs.
    """
    total_length = len(self)
    total_len_float = float(total_length)
    cycle_length = total_len_float / (self.cycles * 2 * pi)
    step = cycle_length * freq
    part = cycle_length * phase
    tbl_iter = modulo_counter(part, total_len_float, step)
    tbl = self.table
    #return Stream(tbl[int(idx)] for idx in tbl_iter)
    return Stream(tbl[int(idx)] * (1. - (idx - int(idx))) +
                  tbl[int(ceil(idx)) - total_length] * (idx - int(idx))
                  for idx in tbl_iter)

  def __getitem__(self, idx):
    """
    Gets an item from the table from its index, which can possibly be a float.
    The data is linearly interpolated.
    """
    total_length = len(self)
    tbl = self.table
    return tbl[int(idx) % total_length] * (1. - (idx - int(idx))) + \
           tbl[int(ceil(idx)) % total_length] * (idx - int(idx))

  def __eq__(self, other):
    if isinstance(other, TableLookup):
      return (self.cycles == other.cycles) and (self.table == other.table)
    return False

  def __ne__(self, other):
    return not self == other

  def harmonize(self, harmonics_dict):
    """
    Returns a "harmonized" table lookup instance by using a "harmonics"
    dictionary with {partial: amplitude} terms, where all "partial" keys have
    to be integers.
    """
    data = sum(cycle(self.table[::partial+1]) * amplitude
               for partial, amplitude in iteritems(harmonics_dict))
    return TableLookup(data.take(len(self)), cycles=self.cycles)

  def normalize(self):
    """
    Returns a new table with values ranging from -1 to 1, reaching at least
    one of these, unless there's no data.
    """
    max_abs = max(self.table, key=abs)
    if max_abs == 0:
      raise ValueError("Can't normalize zeros")
    return self / max_abs


# Create the instance for each default table
DEFAULT_TABLE_SIZE = 2**16
sin_table = TableLookup([sin(x * 2 * pi / DEFAULT_TABLE_SIZE)
                         for x in xrange(DEFAULT_TABLE_SIZE)])
saw_table = TableLookup(list(line(DEFAULT_TABLE_SIZE, -1, 1, finish=True)))


@tostream
def sinusoid(freq, phase=0.):
  """
  Sinusoid based on the optimized math.sin
  """
  # When at 44100 samples / sec, 5 seconds of this leads to an error of 8e-14
  # peak to peak. That's fairly enough.
  for n in modulo_counter(start=phase, modulo=2 * pi, step=freq):
    yield sin(n)


@tostream
def impulse(dur=None, one=1., zero=0.):
  """
  Impulse stream generator.

  Parameters
  ----------
  dur :
    Duration, in number of samples; endless if not given.

  Returns
  -------
  Stream that repeats "0.0" during a given time duration (if any) or
  endlessly, but starts with one (and only one) "1.0".

  """
  if dur is None or (isinf(dur) and dur > 0):
    yield one
    while True:
      yield zero
  elif dur >= .5:
    num_samples = int(dur - .5)
    yield one
    for x in xrange(num_samples):
      yield zero


def karplus_strong(freq, tau=2e4, memory=white_noise):
  """
  Karplus-Strong "digitar" synthesis algorithm.

  Parameters
  ----------
  freq :
    Frequency, in rad/sample.
  tau :
    Time decay (up to ``1/e``, or -8.686 dB), in number of samples. Defaults
    to 2e4. Be careful: using the default value will make duration different
    on each sample rate value. Use ``sHz`` if you need that independent from
    the sample rate and in seconds unit.
  memory :
    Memory data for the comb filter (delayed "output" data in memory).
    Defaults to the ``white_noise`` function.

  Returns
  -------
  Stream instance with the synthesized data.

  Note
  ----
  The fractional delays are solved by exponent linearization.

  See Also
  --------
  sHz :
    Second and hertz constants from samples/second rate.
  white_noise :
    White noise stream generator.

  """
  return comb.tau(2 * pi / freq, tau).linearize()(zeros(), memory=memory)
########NEW FILE########
__FILENAME__ = lazy_text
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Tue May 14 2013
# danilo [dot] bellini [at] gmail [dot] com
"""
Strings, reStructuredText, docstrings and other general text processing
"""

from __future__ import division

import itertools as it
from fractions import Fraction

# Audiolazy internal imports
from .lazy_compat import xzip, xzip_longest, iteritems
from .lazy_misc import rint, elementwise, blocks
from .lazy_core import StrategyDict
from .lazy_math import pi

__all__ = ["multiplication_formatter", "pair_strings_sum_formatter",
           "float_str", "rst_table", "small_doc"]


def multiplication_formatter(power, value, symbol):
  """
  Formats a ``value * symbol ** power`` as a string.

  Usually ``symbol`` is already a string and both other inputs are numbers,
  however this isn't strictly needed. If ``symbol`` is a number, the
  multiplication won't be done, keeping its default string formatting as is.

  """
  if isinstance(value, float):
    if value.is_integer():
      value = rint(value) # Hides ".0" when possible
    else:
      value = "{:g}".format(value)
  if power != 0:
    suffix = "" if power == 1 else "^{p}".format(p=power)
    if value == 1:
      return "{0}{1}".format(symbol, suffix)
    if value == -1:
      return "-{0}{1}".format(symbol, suffix)
    return "{v} * {0}{1}".format(symbol, suffix, v=value)
  else:
    return str(value)


def pair_strings_sum_formatter(a, b):
  """
  Formats the sum of a and b.

  Note
  ----
  Both inputs are numbers already converted to strings.

  """
  if b[:1] == "-":
    return "{0} - {1}".format(a, b[1:])
  return "{0} + {1}".format(a, b)


float_str = StrategyDict("float_str")
float_str.__class__.pi_symbol = r"$\pi$"
float_str.__class__.pi_value = pi


@float_str.strategy("auto")
def float_str(value, order="pprpr", size=[4, 5, 3, 6, 4],
              after=False, max_denominator=1000000):
  """
  Pretty string from int/float.

  "Almost" automatic string formatter for integer fractions, fractions of
  :math:`\pi` and float numbers with small number of digits.

  Outputs a representation among ``float_str.pi``, ``float_str.frac`` (without
  a symbol) strategies, as well as the usual float representation. The
  formatter is chosen by counting the resulting length, trying each one in the
  given ``order`` until one gets at most the given ``size`` limit parameter as
  its length.

  Parameters
  ----------
  value :
    A float number or an iterable with floats.
  order :
    A string that gives the order to try formatting. Each char should be:

    - ``"p"`` for pi formatter (``float_str.pi``);
    - ``"r"`` for ratio without symbol (``float_str.frac``);
    - ``"f"`` for the float usual base 10 decimal representation.

    Defaults to ``"pprpr"``. If no trial has the desired size, returns the
    float representation.
  size :
    The max size allowed for each formatting in the ``order``, respectively.
    Defaults to ``[4, 5, 3, 6, 4]``.
  after :
    Chooses the place where the :math:`\pi` symbol should appear, when such
    formatter apply. If ``True``, that's the end of the string. If ``False``,
    that's in between the numerator and the denominator, before the slash.
    Defaults to ``False``.
  max_denominator :
    The data in ``value`` is rounded following the limit given by this
    parameter when trying to represent it as a fraction/ratio.
    Defaults to the integer 1,000,000 (one million).

  Returns
  -------
  A string with the number written into.

  Note
  ----
  You probably want to keep ``max_denominator`` high to avoid rounding.

  """
  if len(order) != len(size):
    raise ValueError("Arguments 'order' and 'size' should have the same size")

  str_data = {
    "p": float_str.pi(value, after=after, max_denominator=max_denominator),
    "r": float_str.frac(value, max_denominator=max_denominator),
    "f": elementwise("v", 0)(lambda v: "{0:g}".format(v))(value)
  }

  sizes = {k: len(v) for k, v in iteritems(str_data)}
  sizes["p"] = max(1, sizes["p"] - len(float_str.pi_symbol) + 1)

  for char, max_size in xzip(order, size):
    if sizes[char] <= max_size:
      return str_data[char]
  return str_data["f"]


@float_str.strategy("frac", "fraction", "ratio", "rational")
@elementwise("value", 0)
def float_str(value, symbol_str="", symbol_value=1, after=False,
              max_denominator=1000000):
  """
  Pretty rational string from float numbers.

  Converts a given numeric value to a string based on rational fractions of
  the given symbol, useful for labels in plots.

  Parameters
  ----------
  value :
    A float number or an iterable with floats.
  symbol_str :
    String data that will be in the output representing the data as a
    numerator multiplier, if needed. Defaults to an empty string.
  symbol_value :
    The conversion value for the given symbol (e.g. pi = 3.1415...). Defaults
    to one (no effect).
  after :
    Chooses the place where the ``symbol_str`` should be written. If ``True``,
    that's the end of the string. If ``False``, that's in between the
    numerator and the denominator, before the slash. Defaults to ``False``.
  max_denominator :
    An int instance, used to round the float following the given limit.
    Defaults to the integer 1,000,000 (one million).

  Returns
  -------
  A string with the rational number written into as a fraction, with or
  without a multiplying symbol.

  Examples
  --------
  >>> float_str.frac(12.5)
  '25/2'
  >>> float_str.frac(0.333333333333333)
  '1/3'
  >>> float_str.frac(0.333)
  '333/1000'
  >>> float_str.frac(0.333, max_denominator=100)
  '1/3'
  >>> float_str.frac(0.125, symbol_str="steps")
  'steps/8'
  >>> float_str.frac(0.125, symbol_str=" Hz",
  ...                after=True) # The symbol includes whitespace!
  '1/8 Hz'

  See Also
  --------
  float_str.pi :
    This fraction/ratio formatter, but configured with the "pi" symbol.

  """
  if value == 0:
    return "0"

  frac = Fraction(value/symbol_value).limit_denominator(max_denominator)
  num, den = frac.numerator, frac.denominator

  output_data = []

  if num < 0:
    num = -num
    output_data.append("-")

  if (num != 1) or (symbol_str == "") or after:
    output_data.append(str(num))

  if (value != 0) and not after:
    output_data.append(symbol_str)

  if den != 1:
    output_data.extend(["/", str(den)])

  if after:
    output_data.append(symbol_str)

  return "".join(output_data)


@float_str.strategy("pi")
def float_str(value, after=False, max_denominator=1000000):
  """
  String formatter for fractions of :math:`\pi`.

  Alike the rational_formatter, but fixed to the symbol string
  ``float_str.pi_symbol`` and value ``float_str.pi_value`` (both can be
  changed, if needed), mainly intended for direct use with MatPlotLib labels.

  Examples
  --------
  >>> float_str.pi_symbol = "pi" # Just for printing sake
  >>> float_str.pi(pi / 2)
  'pi/2'
  >>> float_str.pi(pi * .333333333333333)
  'pi/3'
  >>> float_str.pi(pi * .222222222222222)
  '2pi/9'
  >>> float_str.pi_symbol = " PI" # With the space
  >>> float_str.pi(pi / 2, after=True)
  '1/2 PI'
  >>> float_str.pi(pi * .333333333333333, after=True)
  '1/3 PI'
  >>> float_str.pi(pi * .222222222222222, after=True)
  '2/9 PI'

  See Also
  --------
  float_str.frac :
    Float to string conversion, perhaps with a symbol as a multiplier.

  """
  return float_str.frac(value, symbol_str=float_str.pi_symbol,
                        symbol_value=float_str.pi_value, after=after,
                        max_denominator=max_denominator)


def rst_table(data, schema=None):
  """
  Creates a reStructuredText simple table (list of strings) from a list of
  lists.
  """
  # Process multi-rows (replaced by rows with empty columns when needed)
  pdata = []
  for row in data:
    prow = [el if isinstance(el, list) else [el] for el in row]
    pdata.extend(pr for pr in xzip_longest(*prow, fillvalue=""))

  # Find the columns sizes
  sizes = [max(len("{0}".format(el)) for el in column)
           for column in xzip(*pdata)]
  sizes = [max(size, len(sch)) for size, sch in xzip(sizes, schema)]

  # Creates the title and border rows
  if schema is None:
    schema = pdata[0]
    pdata = pdata[1:]
  border = " ".join("=" * size for size in sizes)
  titles = " ".join("{1:^{0}}".format(*pair)
                    for pair in xzip(sizes, schema))

  # Creates the full table and returns
  rows = [border, titles, border]
  rows.extend(" ".join("{1:<{0}}".format(*pair)
                       for pair in xzip(sizes, row))
              for row in pdata)
  rows.append(border)
  return rows


def small_doc(obj, indent="", max_width=80):
  """
  Finds a useful small doc representation of an object.

  Parameters
  ----------
  obj :
    Any object, which the documentation representation should be taken from.
  indent :
    Result indentation string to be insert in front of all lines.
  max_width :
    Each line of the result may have at most this length.

  Returns
  -------
  For classes, modules, functions, methods, properties and StrategyDict
  instances, returns the first paragraph in the doctring of the given object,
  as a list of strings, stripped at right and with indent at left.
  For other inputs, it will use themselves cast to string as their docstring.

  """
  if not getattr(obj, "__doc__", False):
    data = [el.strip() for el in str(obj).splitlines()]
    if len(data) == 1:
      if data[0].startswith("<audiolazy.lazy_"): # Instance
        data = data[0].split("0x", -1)[0] + "0x...>" # Hide its address
      else:
        data = "".join(["``", data[0], "``"])
    else:
      data = " ".join(data)

  # No docstring
  elif (not obj.__doc__) or (obj.__doc__.strip() == ""):
    data = "\ * * * * ...no docstring... * * * * \ "

  # Docstring
  else:
    data = (el.strip() for el in obj.__doc__.strip().splitlines())
    data = " ".join(it.takewhile(lambda el: el != "", data))

  # Ensure max_width (word wrap)
  max_width -= len(indent)
  result = []
  for word in data.split():
    if len(word) <= max_width:
      if result:
        if len(result[-1]) + len(word) + 1 <= max_width:
          word = " ".join([result.pop(), word])
        result.append(word)
      else:
        result = [word]
    else: # Splits big words
      result.extend("".join(w) for w in blocks(word, max_width, padval=""))

  # Apply indentation and finishes
  return [indent + el for el in result]

########NEW FILE########
__FILENAME__ = test_analysis
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Tue Aug 07 2012
# danilo [dot] bellini [at] gmail [dot] com
"""
Testing module for the lazy_analysis module
"""

from __future__ import division

import pytest
p = pytest.mark.parametrize

from functools import reduce

# Audiolazy internal imports
from ..lazy_analysis import (window, zcross, envelope, maverage, clip,
                             unwrap, amdf, overlap_add)
from ..lazy_stream import Stream, thub
from ..lazy_misc import almost_eq
from ..lazy_compat import xrange, orange, xzip, xmap
from ..lazy_synth import line, white_noise, ones, sinusoid, zeros
from ..lazy_math import ceil, inf, pi
from ..lazy_core import OpMethod
from ..lazy_itertools import chain

class TestWindow(object):

  @p("wnd", window)
  def test_empty(self, wnd):
    assert wnd(0) == []

  @p("wnd", window)
  @p("M", [1, 2, 3, 4, 16, 128, 256, 512, 1024, 768])
  def test_min_max_len_symmetry(self, wnd, M):
    data = wnd(M)
    assert max(data) <= 1.0
    assert min(data) >= 0.0
    assert len(data) == M
    assert almost_eq(data, data[::-1])


class TestZCross(object):

  def test_empty(self):
    assert list(zcross([])) == []

  @p("n", orange(1, 5))
  def test_small_sizes_no_cross(self, n):
    output = zcross(xrange(n))
    assert isinstance(output, Stream)
    assert list(output) == [0] * n

  @p("d0", [-1, 0, 1])
  @p("d1", [-1, 0, 1])
  def test_pair_combinations(self, d0, d1):
    crossed = 1 if (d0 + d1 == 0) and (d0 != 0) else 0
    assert tuple(zcross([d0, d1])) == (0, crossed)

  @p(("data", "expected"),
     [((0., .1, .5, 1.), (0, 0, 0, 0)),
      ((0., .12, -1.), (0, 0, 1)),
      ((0, -.1, 1), (0, 0, 0)),
      ((1., 0., -.09, .5, -1.), (0, 0, 0, 0, 1)),
      ((1., -.1, -.1, -.2, .05, .1, .05, .2), (0, 0, 0, 1, 0, 0, 0, 1))
     ])
  def test_inputs_with_dot_one_hysteresis(self, data, expected):
    assert tuple(zcross(data, hysteresis=.1)) == expected

  @p("sign", [1, -1])
  def test_first_sign(self, sign):
    data = [0, 1, -1, 3, -4, -.1, .1, 2]
    output = zcross(data, first_sign=sign)
    assert isinstance(output, Stream)
    expected = list(zcross([sign] + data))[1:] # Skip first "zero" sample
    assert list(output) == expected


class TestEnvelope(object):
  sig = [-5, -2.2, -1, 2, 4., 5., -1., -1.8, -22, -57., 1., 12.]

  @p("env", envelope)
  def test_always_positive_and_keep_size(self, env):
    out_stream = env(self.sig)
    assert isinstance(out_stream, Stream)
    out_list = list(out_stream)
    assert len(out_list) == len(self.sig)
    for el in out_list:
      assert el >= 0.


class TestMAverage(object):

  @p("val", [0, 1, 2, 3., 4.8])
  @p("size", [2, 8, 15, 23])
  @p("strategy", maverage)
  def test_const_input(self, val, size, strategy):
    signal = Stream(val)
    result = strategy(size)(signal)
    small_result = result.take(size - 1)
    assert almost_eq(small_result, list(line(size, 0., val))[1:])
    const_result = result.take(int(2.5 * size))
    for el in const_result:
      assert almost_eq(el, val)


class TestClip(object):

  @p("low", [None, 0, -3])
  @p("high", [None, 0, 5])
  def test_with_list_based_range(self, low, high):
    data = orange(-10, 10)
    result = clip(data, low=low, high=high)
    assert isinstance(result, Stream)
    if low is None or low < -10:
      low = -10
    if high is None or high > 10:
      high = 10
    expected = [low] * (10 + low) + orange(low, high) + [high] * (10 - high)
    assert expected == list(result)

  def test_with_inverted_high_and_low(self):
    with pytest.raises(ValueError):
      clip([], low=4, high=3.9)


class TestUnwrap(object):

  @p(("data", "out_data"),[
    ([0, 27, 11, 19, -1, -19, 48, 12], [0, -3, 1, 9, 9, 11, 8, 12]),
    ([0, 10, -10, 20, -20, 30, -30, 40, -40, 50], [0] * 10),
    ([-55, -49, -40, -38, -29, -17, -25], [-55, -49, -50, -48, -49, -47, -55]),
  ])
  def test_max_delta_8_step_10(self, data, out_data):
    assert list(unwrap(data, max_delta=8, step=10)) == out_data


class TestAMDF(object):

  schema = ("sig", "lag", "size", "expected")
  signal = [1.0, 2.0, 3.0, 2.0, 1.0, 2.0, 3.0, 2.0, 1.0]
  table_test = [
    (signal, 1, 1, [1.0,  1.0,  1.0,  1.0,  1.0,  1.0, 1.0, 1.0, 1.0]),
    (signal, 2, 1, [1.0,  2.0,  2.0,  0.0,  2.0,  0.0, 2.0, 0.0, 2.0]),
    (signal, 3, 1, [1.0,  2.0,  3.0,  1.0,  1.0,  1.0, 1.0, 1.0, 1.0]),
    (signal, 1, 2, [0.5,  1.0,  1.0,  1.0,  1.0,  1.0, 1.0, 1.0, 1.0]),
    (signal, 2, 2, [0.5,  1.5,  2.0,  1.0,  1.0,  1.0, 1.0, 1.0, 1.0]),
    (signal, 3, 2, [0.5,  1.5,  2.5,  2.0,  1.0,  1.0, 1.0, 1.0, 1.0]),
    (signal, 1, 4, [0.25, 0.5,  0.75, 1.0,  1.0,  1.0, 1.0, 1.0, 1.0]),
    (signal, 2, 4, [0.25, 0.75, 1.25, 1.25, 1.5,  1.0, 1.0, 1.0, 1.0]),
    (signal, 3, 4, [0.25, 0.75, 1.5,  1.75, 1.75, 1.5, 1.0, 1.0, 1.0]),
  ]

  @p(schema, table_test)
  def test_input_output_mapping(self, sig, lag, size, expected):
    filt = amdf(lag, size)
    assert callable(filt)
    assert almost_eq(list(filt(sig)), expected)

  @p("size", [1, 12])
  def test_lag_zero(self, size):
    sig_size = 200
    zero = 0
    filt = amdf(lag=0, size=size)
    sig = list(white_noise(sig_size))
    assert callable(filt)
    assert list(filt(sig, zero=zero)) == [zero for el in sig]


@p("oadd", overlap_add)
class TestOverlapAdd(object):

  # A list of 7-sized lists (blocks) without any zero
  list_data = [[ .1,  .6,  .17,  .4, -.8,  .1,  -.7],
               [ .8,  .7,  .9,  -.6,  .7, -.15,  .3],
               [ .4, -.2,  .4,   .1,  .1, -.3,  -.95],
               [-.3,  .54, .12,  .1, -.8, -.3,   .8],
               [.04, -.8, -.43,  .2,  .1,  .9,  -.5]]

  def test_simple_size_7_hop_3_from_lists(self, oadd):
    wnd = [.1, .2, .3, .4, .3, .2, .1]
    ratio = .6 # Expected normalization ratio
    result = oadd(self.list_data, hop=3, wnd=wnd, normalize=False)
    assert isinstance(result, Stream)
    result_list = list(result)
    # Resulting size is (number of blocks - 1) * hop + size
    length = (len(self.list_data) - 1) * 3 + 7
    assert len(result_list) == length

    # Try applying the window externally
    wdata = [[w * r for w, r in xzip(wnd, row)] for row in self.list_data]
    pre_windowed_result = oadd(wdata, hop=3, wnd=None, normalize=False)
    assert result_list == list(pre_windowed_result)

    # Overlapping and adding manually to a list (for size=7 and hop=3)
    expected = [0.] * length
    for blk_idx, blk in enumerate(wdata):
      start = blk_idx * 3
      stop = start + 7
      expected[start:stop] = list(expected[start:stop] + Stream(blk))
    assert expected == result_list

    # Try comparing with the normalized version
    result_norm = oadd(self.list_data, hop=3, wnd=wnd, normalize=True)
    assert almost_eq(expected[0] / result_norm.peek(), ratio)
    assert almost_eq(result_list, list(result_norm * ratio))

  def test_empty(self, oadd):
    data = oadd([])
    assert isinstance(data, Stream)
    assert list(data) == []

  @p("wnd", [None, window.rect, window.triangular])
  def test_size_1_hop_1_sameness(self, oadd, wnd):
    raw_data = [1., -4., 3., -1., 5., -4., 2., 3.]
    blk_sig = Stream(raw_data).blocks(size=1, hop=1)
    data = oadd(blk_sig).take(200)
    assert list(data) ==  raw_data

  @p("size", [512, 128, 12, 2])
  @p("dur", [1038, 719, 18])
  def test_ones_detect_size_with_hop_half_no_normalize(self, oadd, size, dur):
    hop = size // 2
    blk_sig = ones(dur).blocks(size, hop)
    result = oadd(blk_sig, hop=hop, wnd=None, normalize=False)
    data = list(result)
    length = int(ceil(dur / hop) * hop) if dur >= hop else 0
    assert len(data) == length
    one_again = max(0, length - hop)
    twos_start = hop if dur > size else 0
    assert all(el == 1. for el in data[:twos_start])
    assert all(el == 2. for el in data[twos_start:one_again])
    assert all(el == 1. for el in data[one_again:dur])
    assert all(el == 0. for el in data[dur:])

  @p("wnd", [None, window.rect])
  @p("normalize", [True, False])
  def test_size_5_hop_2_rect_window(self, oadd, wnd, normalize):
    raw_data = [5, 4, 3, -2, -3, 4] * 7 # 42-sampled example
    blk_sig = Stream(raw_data).blocks(size=5, hop=2) # 43 (1-sample zero pad)
    result = oadd(blk_sig, size=5, hop=2, wnd=wnd, normalize=normalize)
    assert isinstance(result, Stream)
    result_list = result.take(100)
    weights = [1, 1, 2] + Stream(2, 3).take(37) + [2, 1]
    expected_no_normalize = [x * w for x, w in xzip(raw_data, weights)] + [0.]
    if normalize:
      assert almost_eq([el / 3 for el in expected_no_normalize], result_list)
    else:
      assert list(expected_no_normalize) == result_list

  data1 = list(line(197, .4, -7.7) ** 3 * Stream(.7, .9, .4)) # Arbitrary
  data2 = (sinusoid(freq=.2, phase=pi * sinusoid(.07389) ** 5) * 18).take(314)

  @p("size", [8, 6, 4, 17])
  @p("wnd", [window.triangle, window.hamming, window.hann, window.bartlett])
  @p("data", [data1, data2])
  def test_size_minus_hop_is_3_and_detect_size_no_normalize(self, oadd, size,
                                                            wnd, data):
    hop = size - 3
    result = oadd(Stream(data).blocks(size=size, hop=hop),
                  hop=hop, wnd=wnd, normalize=False).take(inf)
    wnd_list = wnd(size)
    expected = None
    for blk in Stream(data).blocks(size=size, hop=hop):
      blk_windowed = [bi * wi for bi, wi in xzip(blk, wnd_list)]
      if expected:
        expected[-3] += blk_windowed[0]
        expected[-2] += blk_windowed[1]
        expected[-1] += blk_windowed[2]
        expected.extend(blk_windowed[3:])
      else: # First time
        expected = blk_windowed
    assert almost_eq(expected, list(result))

  @p(("size", "hop"), [
    (256, 255),
    (200, 50),
    (128, 9),
    (128, 100),
    (128, 64),
    (100, 100),
    (17, 3),
    (3, 2),
    (2, 1),
  ])
  @p("wnd", [
    window.triangle, window.hamming, window.hann, window.bartlett,
    zeros, # Just for fun (this shouldn't break)
    None,  # Rectangular
    lambda n: line(n) ** 2,                       # Asymmetric iterable
    lambda n: (line(n, -2, 1) ** 3).take(inf),    # Negative value
    lambda n: [-el for el in window.triangle(n)], # Negative-only value
  ])
  def test_normalize(self, oadd, size, hop, wnd):
    # Apply the overlap_add
    length = 719
    result = oadd(ones(length).blocks(size=size, hop=hop),
                  hop=hop, wnd=wnd, normalize=True).take(inf)
    assert len(result) >= length

    # Content verification
    wnd_list = [1.] * size if wnd is None else list(wnd(size))
    if all(el == 0. for el in wnd_list): # Zeros! (or bartlett(2))
      assert all(el == 0. for el in result)
    else:

      # All common cases with a valid window
      assert all(el == 0. for el in result[length:]) # Blockenizing zero pad
      one = 1 + 2e-16 # For one significand bit tolerance (needed for
                      # size = 128; hop in [9, 64]; and
                      # wnd in [triangle, negatived triangle])
      assert all(-one <= el <= one for el in result[:length])

      wnd_gain = max(abs(el) for el in wnd_list)
      wnd_list = [el / wnd_gain for el in wnd_list]
      wnd_max = max(wnd_list)
      wnd_min = min(wnd_list)

      if wnd_max * wnd_min >= 0: # Same signal (perhaps including zero)
        if wnd_max >= abs(wnd_min): # No negative values
          assert almost_eq(max(result[:length]), wnd_max)
        else: # No positive values
          assert almost_eq(min(result[:length]), wnd_min)

        for op in OpMethod.get("> >= < <="):
          if all(op.func(el, 0) for el in wnd_list):
            assert all(op.func(el, 0) for el in result[:length])

      else: # Can subtract, do it all again with the abs(wnd)
        wnd_pos = list(xmap(abs, wnd_list))
        rmax = oadd(ones(length).blocks(size=size, hop=hop),
                    hop=hop, wnd=wnd_pos, normalize=True).take(inf)

        assert all(-1 <= el <= 1 for el in rmax[:length]) # Need no tolerance!
        assert len(rmax) == len(result)
        assert all(rmi >= abs(ri) for rmi, ri in xzip(rmax, result))
        assert almost_eq(max(rmax[:length]), max(wnd_pos))

        if 0. in wnd_pos:
          assert all(el >= 0 for el in rmax[:length])
        else:
          assert all(el > 0 for el in rmax[:length])

  @p("wnd", [25, lambda n: 42, lambda n: None])
  def test_invalid_window(self, oadd, wnd):
    result = oadd(ones(500).blocks(1), wnd=wnd)
    with pytest.raises(TypeError) as exc:
      result.take()
    msg_words = ["window", "should", "iterable", "callable"]
    message = str(exc.value).lower()
    assert all(word in message for word in msg_words)

  @p("wdclass", [float, int])
  @p("sdclass", [float, int])
  @p("wconstructor", [tuple, list, Stream, iter])
  def test_float_ints_for_iterable_window_and_signal(self, oadd, wdclass,
                                                     sdclass, wconstructor):
    size = 3 # For a [1, 2, 3] window
    hop = 2

    wnd = wconstructor(wdclass(el) for el in [1, 2, 3])
    wnd_normalized = wconstructor([.25, .5, .75]) # This can't be int

    sig = thub(Stream(7, 9, -2, 1).map(sdclass), 2)
    result_no_norm = oadd(sig.blocks(size=size, hop=hop),
                          hop=hop, wnd=wnd_normalized, normalize=False)
    result_norm = oadd(sig.blocks(size=size, hop=hop),
                       hop=hop, wnd=wnd, normalize=True)
    expected = chain([1], Stream(2, 4)) * Stream(7, 9, -2, 1) * .25

    # Powers of 2 in wnd_normalized allows equalness testing for floats
    assert result_no_norm.peek(250) == expected.take(250)
    assert result_no_norm.take(400) == result_norm.take(400)

  @p("size", [8, 6]) # Actual size of each block in list_data is 7
  def test_wrong_declared_size(self, oadd, size):
    result = oadd(self.list_data, size=size, hop=3)
    with pytest.raises(ValueError):
      result.peek()

  @p("size", [8, 6])
  def test_wrong_window_size(self, oadd, size):
    result = oadd(self.list_data, hop=3, wnd=window.triangle(size))
    with pytest.raises(ValueError):
      result.peek()

  def test_no_hop(self, oadd):
    concat = lambda seq: reduce(lambda a, b: a + b, seq)
    wnd = window.triangle(len(self.list_data[0]))
    wdata = [[w * r for w, r in xzip(wnd, row)] for row in self.list_data]
    result_no_wnd = oadd(self.list_data, wnd=None)
    result_wnd = oadd(self.list_data, wnd=wnd)
    assert concat(self.list_data) == list(result_no_wnd)
    assert concat(wdata) == list(result_wnd)

########NEW FILE########
__FILENAME__ = test_analysis_numpy
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Mon Feb 25 2013
# danilo [dot] bellini [at] gmail [dot] com
"""
Testing module for the lazy_analysis module by using numpy as an oracle
"""

import pytest
p = pytest.mark.parametrize

from numpy.fft import fft as np_fft

# Audiolazy internal imports
from ..lazy_analysis import dft
from ..lazy_math import pi
from ..lazy_misc import almost_eq, rint
from ..lazy_synth import line


class TestDFT(object):

  blk_table = [
    [20],
    [1, 2, 3],
    [0, 1, 0, -1],
    [5] * 8,
  ]

  @p("blk", blk_table)
  @p("size_multiplier", [.5, 1, 2, 3, 1.5, 1.2])
  def test_empty(self, blk, size_multiplier):
    full_size = len(blk)
    size = rint(full_size * size_multiplier)
    np_data = np_fft(blk, size).tolist()
    lz_data = dft(blk[:size],
                  line(size, 0, 2 * pi, finish=False),
                  normalize=False
                 )
    assert almost_eq.diff(np_data, lz_data, max_diff=1e-12)

########NEW FILE########
__FILENAME__ = test_auditory
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Sun Sep 09 2012
# danilo [dot] bellini [at] gmail [dot] com
"""
Testing module for the lazy_auditory module
"""

from __future__ import division

import pytest
p = pytest.mark.parametrize

import itertools as it
import os, json

# Audiolazy internal imports
from ..lazy_auditory import erb, gammatone_erb_constants, gammatone, phon2dB
from ..lazy_misc import almost_eq, sHz
from ..lazy_math import pi
from ..lazy_filters import CascadeFilter
from ..lazy_stream import Stream
from ..lazy_compat import iteritems


class TestERB(object):

  @p(("freq", "bandwidth"),
     [(1000, 132.639),
      (3000, 348.517),
     ])
  def test_glasberg_moore_slaney_example(self, freq, bandwidth):
    assert almost_eq.diff(erb["gm90"](freq), bandwidth, max_diff=5e-4)

  @p("erb_func", erb)
  @p("rate", [8000, 22050, 44100])
  @p("freq", [440, 20, 2e4])
  def test_two_input_methods(self, erb_func, rate, freq):
    Hz = sHz(rate)[1]
    assert almost_eq(erb_func(freq) * Hz, erb_func(freq * Hz, Hz))
    if freq < rate:
      with pytest.raises(ValueError):
        erb_func(freq * Hz)


class TestGammatoneERBConstants(object):

  @p(("n", "an",  "aninv", "cn",  "cninv"), # Some paper values were changed:
     [(1,   3.142, 0.318,   2.000, 0.500),  # + a1 was 3.141 (it should be pi)
      (2,   1.571, 0.637,   1.287, 0.777),  # + a2 was 1.570, c2 was 1.288
      (3,   1.178, 0.849,   1.020, 0.981),  # + 1/c3 was 0.980
      (4,   0.982, 1.019,   0.870, 1.149),
      (5,   0.859, 1.164,   0.771, 1.297),  # + a5 was 0.889 (typo?), c5 was
      (6,   0.773, 1.293,   0.700, 1.429),  #   0.772 and 1/c5 was 1.296
      (7,   0.709, 1.411,   0.645, 1.550),  # + c7 was 0.646
      (8,   0.658, 1.520,   0.602, 1.662),  # Doctests also suffered from this
      (9,   0.617, 1.621,   0.566, 1.767)   # rounding issue.
     ])
  def test_annex_c_table_1(self, n, an, aninv, cn, cninv):
    x, y = gammatone_erb_constants(n)
    assert almost_eq.diff(x, aninv, max_diff=5e-4)
    assert almost_eq.diff(y, cn, max_diff=5e-4)
    assert almost_eq.diff(1./x, an, max_diff=5e-4)
    assert almost_eq.diff(1./y, cninv, max_diff=5e-4)


class TestGammatone(object):

  some_data = [pi / 7, Stream(0, 1, 2, 1), [pi/3, pi/4, pi/5, pi/6]]

  @p(("filt_func", "freq", "bw"),
     [(gf, pi / 5, pi / 19) for gf in gammatone] +
     [(gammatone.klapuri, freq, bw) for freq, bw
                                    in it.product(some_data,some_data)]
    )
  def test_number_of_poles_order(self, filt_func, freq, bw):
    cfilt = filt_func(freq=freq, bandwidth=bw)
    assert isinstance(cfilt, CascadeFilter)
    assert len(cfilt) == 4
    for filt in cfilt:
      assert len(filt.denominator) == 3


class TestPhon2DB(object):

  # Values from image analysis over the figure A.1 in the ISO/FDIS 226:2003
  # Annex A, page 5
  directory = os.path.split(__file__)[0]
  iso226_json_filename = os.path.join(directory, "iso226.json")
  with open(iso226_json_filename) as f:
    iso226_image_data = {None if k == "None" else int(k): v
                         for k, v in iteritems(json.load(f))}

  @p(("loudness", "curve_data"), iso226_image_data.items())
  def test_match_curve_from_image_data(self, loudness, curve_data):
    freq2dB = phon2dB(loudness)
    for freq, spl in curve_data:
      assert almost_eq.diff(freq2dB(freq), spl, max_diff=.5)

########NEW FILE########
__FILENAME__ = test_core
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Sat Oct 13 2012
# danilo [dot] bellini [at] gmail [dot] com
"""
Testing module for the lazy_core module
"""

import pytest
p = pytest.mark.parametrize

from types import GeneratorType
import operator

# Audiolazy internal imports
from ..lazy_core import OpMethod, AbstractOperatorOverloaderMeta, StrategyDict
from ..lazy_compat import meta


class TestOpMethod(object):

  def test_get_no_input(self):
    assert set(OpMethod.get()) == set(OpMethod.get("all"))

  def test_get_empty(self):
    for el in [OpMethod.get(None), OpMethod.get(None, without="+"),
               OpMethod.get(without="all"), OpMethod.get("+ -", "- +")]:
      assert isinstance(el, GeneratorType)
      assert list(el) == []

  @p("name", ["cmp", "almosteq", "div"])
  def test_get_wrong_input(self, name):
    for el in [OpMethod.get(name),
               OpMethod.get(without=name),
               OpMethod.get("all", without=name),
               OpMethod.get(name, without="all")]:
      with pytest.raises(ValueError) as exc:
        next(el)
      assert name in str(exc.value)
      assert ("unknown" in str(exc.value)) is (name != "div")

  def test_get_reversed(self):
    has_rev = sorted("+ - * / // % ** >> << & | ^".split())
    result_all_rev = list(OpMethod.get("r"))
    result_no_rev = list(OpMethod.get("all", without="r"))
    result_all = list(OpMethod.get("all"))
    assert len(result_all_rev) == len(has_rev)
    assert has_rev == sorted(op.symbol for op in result_all_rev)
    assert not any(el in has_rev for el in result_no_rev)
    assert set(result_no_rev).union(set(result_all_rev)) == set(result_all)

  @p(("symbol", "name"), {"+": "add",
                          "-": "sub",
                          "*": "mul",
                          "/": "truediv",
                          "//": "floordiv",
                          "%": "mod",
                          "**": "pow",
                          ">>": "rshift",
                          "<<": "lshift",
                          "~": "invert",
                          "&": "and",
                          "|": "or",
                          "^": "xor",
                          "<": "lt",
                          "<=": "le",
                          "==": "eq",
                          "!=": "ne",
                          ">": "gt",
                          ">=": "ge"}.items())
  def test_get_by_all_criteria_for_one_symbol(self, symbol, name):
    # Useful constants
    third_name = {"+": "pos",
                  "-": "neg"}
    without_binary = ["~"]
    has_rev = "+ - * / // % ** >> << & | ^".split()

    # Search by symbol
    result = list(OpMethod.get(symbol))

    # Dunder name
    for res in result:
      assert res.dname == res.name.join(["__", "__"])

    # Name, arity, reversed and function
    assert result[0].name == name
    assert result[0].arity == (1 if symbol in without_binary else 2)
    assert not result[0].rev
    func = getattr(operator, name.join(["__", "__"]))
    assert result[0].func is func
    if symbol in has_rev:
      assert result[1].name == "r" + name
      assert result[1].arity == 2
      assert result[1].rev
      assert result[0].func is result[1].func
    if symbol in third_name:
      assert result[2].name == third_name[symbol]
      assert result[2].arity == 1
      assert not result[2].rev
      unary_func = getattr(operator, third_name[symbol].join(["__", "__"]))
      assert result[2].func is unary_func
      assert not (result[0].func is result[2].func)

    # Length
    if symbol in third_name:
      assert len(result) == 3
    elif symbol in has_rev:
      assert len(result) == 2
    else:
      assert len(result) == 1

    # Search by name
    result_name = list(OpMethod.get(name))
    assert len(result_name) == 1
    assert result_name[0] is result[0]

    # Search by dunder name
    result_dname = list(OpMethod.get(name.join(["__", "__"])))
    assert len(result_dname) == 1
    assert result_dname[0] is result[0]

    # Search by function
    result_func = list(OpMethod.get(func))
    assert len(result_func) == min(2, len(result))
    assert result_func[0] is result[0]
    assert result_func[-1] is result[:2][-1]
    if symbol in third_name:
      result_unary_func = list(OpMethod.get(unary_func))
      assert len(result_unary_func) == 1
      assert result_unary_func[0] is result[2]

  def test_get_by_arity(self):
    comparison_symbols = "> >= == != < <=" # None is "reversed" here

    # Queries to be used
    res_unary = set(OpMethod.get("1"))
    res_binary = set(OpMethod.get("2"))
    res_reversed = set(OpMethod.get("r"))
    res_not_unary = set(OpMethod.get(without="1"))
    res_not_binary = set(OpMethod.get(without="2"))
    res_not_reversed = set(OpMethod.get(without="r"))
    res_not_reversed_nor_unary = set(OpMethod.get(without="r 1"))
    res_all = set(OpMethod.get("all"))
    res_comparison = set(OpMethod.get(comparison_symbols))

    # Compare!
    assert len(res_unary) == 3
    assert set(op.name for op in res_unary) == {"pos", "neg", "invert"}
    assert len(res_binary) == 2 * len(res_reversed) + len(res_comparison)
    assert all(op in res_binary for op in res_reversed)
    assert all(op in res_binary for op in res_not_reversed_nor_unary)
    assert all(op in res_binary for op in res_comparison)
    assert all(op in res_not_reversed_nor_unary for op in res_comparison)
    assert all(op in res_not_reversed for op in res_not_reversed_nor_unary)
    assert all(op in res_not_reversed for op in res_unary)
    assert all((op in res_reversed) or (op in res_not_reversed_nor_unary)
               for op in res_binary)
    assert all(op in res_binary for op in res_not_reversed_nor_unary)

    # Excluded middle: an operator is always either unary or binary
    assert len(res_all) == len(res_unary) + len(res_binary)
    assert not any(op in res_binary for op in res_unary)
    assert not any(op in res_unary for op in res_binary)
    assert res_not_unary == res_binary
    assert res_not_binary == res_unary

    # Query using other datatypes
    assert res_unary == set(OpMethod.get(1))
    assert res_binary == set(OpMethod.get(2))
    assert res_not_reversed_nor_unary == \
           set(OpMethod.get(without=["r", 1])) == \
           set(OpMethod.get(without=["r", "1"]))

  def test_mixed_format_query(self):
    a = set(OpMethod.get(["+", "invert", "sub rsub >"], without="radd"))
    b = set(OpMethod.get(["+ invert", "sub rsub >"], without="radd"))
    c = set(OpMethod.get(["add invert", "sub rsub >", operator.__pos__]))
    d = set(OpMethod.get("add invert pos sub rsub >"))
    e = set(OpMethod.get(["+ -", operator.__invert__, "__gt__"],
                         without="__radd__ neg"))
    assert a == b == c == d == e


class TestAbstractOperatorOverloaderMeta(object):

  def test_empty_directly_as_metaclass(self):
    with pytest.raises(TypeError):
      try:
        class unnamed(meta(metaclass=AbstractOperatorOverloaderMeta)):
          pass
      except TypeError as excep:
        msg = "Class 'unnamed' has no builder/template for operator method '"
        assert str(excep).startswith(msg)
        raise

  def test_empty_invalid_subclass(self):
    class MyAbstractClass(AbstractOperatorOverloaderMeta):
      pass
    with pytest.raises(TypeError):
      try:
        class DummyClass(meta(metaclass=MyAbstractClass)):
          pass
      except TypeError as excep:
        msg = "Class 'DummyClass' has no builder/template for operator method"
        assert str(excep).startswith(msg)
        raise


class TestStrategyDict(object):

  def test_1x_strategy(self):
    sd = StrategyDict()

    assert len(sd) == 0

    @sd.strategy("test", "t2")
    def sd(a):
      return a + 18

    assert len(sd) == 1

    assert sd["test"](0) == 18
    assert sd.test(0) == 18
    assert sd.t2(15) == 33
    assert sd(-19) == -1
    assert sd.default == sd["test"]


  def test_same_key_twice(self):
    sd = StrategyDict()

    @sd.strategy("data", "main", "data")
    def sd():
      return True

    @sd.strategy("only", "only", "main")
    def sd():
      return False

    assert len(sd) == 2 # Strategies
    assert sd["data"] == sd.default
    assert sd["data"] != sd["main"]
    assert sd["only"] == sd["main"]
    assert sd()
    assert sd["data"]()
    assert not sd["only"]()
    assert not sd["main"]()
    assert sd.data()
    assert not sd.only()
    assert not sd.main()
    sd_keys = list(sd.keys())
    assert ("data",) in sd_keys
    assert ("only", "main") in sd_keys


  @p("add_names", [("t1", "t2"), ("t1", "t2", "t3")])
  @p("mul_names", [("t3",),
                   ("t1", "t2"),
                   ("t1", "t3"),
                   ("t3", "t1"),
                   ("t3", "t2"),
                   ("t1", "t2", "t3"),
                   ("t1")
                  ])
  def test_2x_strategy(self, add_names, mul_names):
    sd = StrategyDict()

    @sd.strategy(*add_names)
    def sd(a, b):
      return a + b

    @sd.strategy(*mul_names)
    def sd(a, b):
      return a * b

    add_names_valid = [name for name in add_names if name not in mul_names]
    if len(add_names_valid) == 0:
      assert len(sd) == 1
    else:
      assert len(sd) == 2

    for name in add_names_valid:
      assert sd[name](5, 7) == 12
      assert sd[name](1, 3) == 4
    for name in mul_names:
      assert sd[name](5, 7) == 35
      assert sd[name](1, 3) == 3

    if len(add_names_valid) > 0:
      assert sd(-19, 3) == -16
    sd.default = sd[mul_names[0]]
    assert sd(-19, 3) == -57

########NEW FILE########
__FILENAME__ = test_filters
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Sun Sep 09 2012
# danilo [dot] bellini [at] gmail [dot] com
"""
Testing module for the lazy_filters module
"""

import pytest
p = pytest.mark.parametrize

import operator
import itertools as it
from math import pi
from functools import reduce

# Audiolazy internal imports
from ..lazy_filters import (ZFilter, z, CascadeFilter, ParallelFilter,
                            resonator, lowpass, highpass)
from ..lazy_misc import almost_eq, zero_pad
from ..lazy_compat import orange, xrange, xzip, xmap
from ..lazy_itertools import cycle, chain
from ..lazy_stream import Stream, thub
from ..lazy_math import dB10, dB20, inf
from ..lazy_synth import line

from . import skipper
operator.div = getattr(operator, "div", skipper("There's no operator.div"))


class TestZFilter(object):
  data = [-7, 3] + orange(10) + [-50, 0] + orange(70, -70, -11) # Only ints
  alpha = [-.5, -.2, -.1, 0, .1, .2, .5] # Attenuation Value for filters
  delays = orange(1, 5)

  def test_z_identity(self):
    my_filter = z ** 0
    assert list(my_filter(self.data)) == self.data

  @p("amp_factor", [-10, 3, 0, .2, 8])
  def test_z_simple_amplification(self, amp_factor):
    my_filter1 = amp_factor * z ** 0
    my_filter2 = z ** 0 * amp_factor
    expected = [amp_factor * di for di in self.data]
    op = operator.eq if isinstance(amp_factor, int) else almost_eq
    assert op(list(my_filter1(self.data)), expected)
    assert op(list(my_filter2(self.data)), expected)


  @p("delay", orange(1, 5)) # Slice with zero would make data empty
  def test_z_int_delay(self, delay):
    my_filter = + z ** -delay
    assert list(my_filter(self.data)) == [0] * delay + self.data[:-delay]

  @p("amp_factor", [1, -105, 43, 0, .128, 18])
  @p("delay", orange(1, 7)) # Slice with zero would make data empty
  def test_z_int_delay_with_amplification(self, amp_factor, delay):
    my_filter1 = amp_factor * z ** -delay
    my_filter2 = z ** -delay * amp_factor
    expected = [amp_factor * di for di in ([0.] * delay + self.data[:-delay])]
    op = operator.eq if isinstance(amp_factor, int) else almost_eq
    assert op(list(my_filter1(self.data)), expected)
    assert op(list(my_filter2(self.data)), expected)

  def test_z_fir_size_2(self):
    my_filter = 1 + z ** -1
    expected = [a + b for a, b in xzip(self.data, [0] + self.data[:-1])]
    assert list(my_filter(self.data)) == expected

  def test_z_fir_size_2_hybrid_amplification(self):
    my_filter = 2 * (3. - 5 * z ** -1)
    expected = (6.*a - 10*b for a, b in xzip(self.data,
                                             [0.] + self.data[:-1]))
    assert almost_eq(my_filter(self.data), expected)

  amp_list = [1, -15, 45, 0, .81, 17]
  @p( ("num_delays", "amp_factor"),
      chain.from_iterable(
        (lambda amps, dls: [
          [(d, a) for a in it.combinations_with_replacement(amps, d + 1)]
          for d in dls
        ])(amp_list, delays)
      ).take(inf)
  )
  def test_z_many_fir_sizes_and_amplifications(self, num_delays, amp_factor):
    my_filter = sum(amp_factor[delay] * z ** -delay
                    for delay in xrange(num_delays + 1))
    expected = sum(amp_factor[delay] * (z ** -delay)(self.data)
                   for delay in xrange(num_delays + 1))
    assert almost_eq(my_filter(self.data), expected)

  def test_z_fir_multiplication(self):
    my_filter = 8 * (2 * z**-3 - 5 * z**-4) * z ** 2 * 7
    expected = [56*2*a - 56*5*b for a, b in xzip([0] + self.data[:-1],
                                                 [0, 0] + self.data[:-2])]
    assert list(my_filter(self.data)) == expected
  @p("a", alpha)
  def test_z_one_pole(self, a):
    my_filter = 1 / (1 + a * z ** -1)
    expected = [x for x in self.data]
    for idx in xrange(1,len(expected)):
      expected[idx] -= a * expected[idx-1]
    assert almost_eq(my_filter(self.data), expected)

  @p("a", alpha)
  @p("b", alpha)
  def test_z_division(self, a, b):
    idx_den1 = -1
    idx_num2 = -2
    for idx_num1 in orange(-3,1):
      for idx_den2 in orange(-18,1):
        fa, fb, fc, fd = (a * z ** idx_num1, 2 + b * z ** idx_den1,
                          3 * z ** idx_num2, 1 + 5 * z ** idx_den2)
        my_filter1 = fa / fb
        my_filter2 = fc / fd
        my_filt = my_filter1 / my_filter2
        idx_corr = max(idx_num2, idx_num2 + idx_den1)
        num_filter = fa * fd * (z ** -idx_corr)
        den_filter = fb * fc * (z ** -idx_corr)
        assert almost_eq(my_filt.numpoly.terms(), num_filter.numpoly.terms())
        assert almost_eq(my_filt.denpoly.terms(), den_filter.numpoly.terms())

  @p("filt", [1 / z / 1,
              (1 / z) ** 1,
              (1 / z ** -1) ** -1,
             ])
  def test_z_power_alone(self, filt):
    assert almost_eq(filt(self.data), [0.] + self.data[:-1])

  @p("a", [a for a in alpha if a != 0])
  @p("div", [operator.div, operator.truediv])
  @p("zero", [0., 0])
  def test_z_div_truediv_unit_delay_divided_by_constant(self, a, div, zero):
    for el in [a, int(10 * a)]:
      div_filter = div(z ** -1, a)
      div_expected = xmap(lambda x: operator.truediv(x, a),
                          [zero] + self.data[:-1])
      assert almost_eq(div_filter(self.data, zero=zero), div_expected)

  @p("a", alpha)
  def test_z_div_truediv_constant_over_delay(self, a):
    div_inv_filter = operator.div(a, 1 + z ** -1)
    truediv_inv_filter = operator.truediv(a, 1 + z ** -1)
    expected = [a*x for x in self.data]
    for idx in xrange(1,len(expected)):
      expected[idx] -= expected[idx-1]
    assert almost_eq(div_inv_filter(self.data), expected)
    assert almost_eq(truediv_inv_filter(self.data), expected)

  def test_z_power_with_denominator(self):
    my_filter = (z ** -1 / (1 + z ** -2)) ** 1 # y[n] == x[n-1] - y[n-2]
    expected = []
    mem2, mem1, xlast = 0., 0., 0.
    for di in self.data:
      newy = xlast - mem2
      mem2, mem1, xlast = mem1, newy, di
      expected.append(newy)
    assert almost_eq(my_filter(self.data), expected)

  @p("a", alpha)
  def test_z_grouped_powers(self, a):
    base_filter = (1 + a * z ** -1)
    my_filter1 = base_filter ** -1
    my_filter2 = 3 * base_filter ** -2
    my_filter3 = base_filter ** 2
    my_filter4 = a * base_filter ** 0
    my_filter5 = (base_filter ** 3) * (base_filter ** -4)
    my_filter6 = ((1 - a * z ** -1) / base_filter ** 2) ** 2
    assert almost_eq(my_filter1.numerator, [1.])
    assert almost_eq(my_filter1.denominator, [1., a] if a != 0 else [1.])
    assert almost_eq(my_filter2.numerator, [3.])
    assert almost_eq(my_filter2.denominator, [1., 2*a, a*a]
                                             if a != 0 else [1.])
    assert almost_eq(my_filter3.numerator, [1., 2*a, a*a] if a != 0 else [1.])
    assert almost_eq(my_filter3.denominator, [1.])
    assert almost_eq(my_filter4.numerator, [a] if a != 0 else [])
    assert almost_eq(my_filter4.denominator, [1.])
    assert almost_eq(my_filter5.numerator, [1., 3*a, 3*a*a, a*a*a]
                                           if a != 0 else [1.])
    assert almost_eq(my_filter5.denominator,
                     [1., 4*a, 6*a*a, 4*a*a*a, a*a*a*a] if a != 0 else [1.])
    assert almost_eq(my_filter6.numerator, [1., -2*a, a*a]
                                           if a != 0 else [1.])
    assert almost_eq(my_filter6.denominator,
                     [1., 4*a, 6*a*a, 4*a*a*a, a*a*a*a] if a != 0 else [1.])

  @p("a", alpha)
  def test_z_one_pole_neg_afterwards(self, a):
    my_filter = -(1 / (1 + a * z ** -1))
    expected = [x for x in self.data]
    for idx in xrange(1,len(expected)):
      expected[idx] -= a * expected[idx-1]
    expected = (-x for x in expected)
    assert almost_eq(my_filter(self.data), expected)

  @p("a", alpha)
  def test_z_one_pole_added_one_pole(self, a):
    my_filter1 = -(3 / (1 + a * z ** -1))
    my_filter2 = +(2 / (1 - a * z ** -1))
    my_filter = my_filter1 + my_filter2
    assert almost_eq(my_filter.numerator, [-1., 5*a] if a != 0 else [-1.])
    assert almost_eq(my_filter.denominator, [1., 0., -a*a]
                                            if a != 0 else [1.])

  @p("a", alpha)
  def test_z_one_pole_added_to_a_number(self, a):
    my_filter = -(5 / (1 - a * z ** -1)) + a
    assert almost_eq(my_filter.numerator, [-5 + a, -a*a] if a != 0 else [-5])
    assert almost_eq(my_filter.denominator, [1., -a] if a != 0 else [1.])

  @p("a", alpha)
  def test_one_pole_numerator_denominator_constructor(self, a):
    my_filter = ZFilter(numerator=[1.], denominator=[1., -a])
    expected = [x for x in self.data]
    for idx in xrange(1,len(expected)):
      expected[idx] += a * expected[idx-1]
    assert almost_eq(list(my_filter(self.data)), expected)

  @p("delay", orange(1, 7))
  def test_diff_twice_only_numerator_one_delay(self, delay):
    data = z ** -delay
    ddz = data.diff()
    assert almost_eq(ddz.numerator,
                     [0] * delay + [0, -delay])
    assert almost_eq(ddz.denominator, [1])
    ddz2 = ddz.diff()
    assert almost_eq(ddz2.numerator,
                     [0] * delay + [0, 0, delay * (delay + 1)])
    assert almost_eq(ddz2.denominator, [1])
    ddz2_alt = data.diff(2)
    assert almost_eq(ddz2.numerator, ddz2_alt.numerator)
    assert almost_eq(ddz2.denominator, ddz2_alt.denominator)

  def test_diff(self):
    filt = (1 + z ** -1) / (1 - z ** -1)
    ddz = filt.diff()
    assert almost_eq(ddz.numerator, [0, 0, -2])
    assert almost_eq(ddz.denominator, [1, -2, 1])

  @p("a", alpha)
  @p("A", [.9, -.2])
  @p("mul", [-z, 1/(1 + z**-2), 8])
  def test_diff_with_eq_operator_and_mul_after(self, a, A, mul):
    num = a - A * (1 - a) * z ** -1
    den = 1 - A * z ** -1 + A ** 2 * z ** -2
    filt = num / den
    numd = A * (1 - a) * z ** -2
    dend = A * z ** -2 - 2 * A ** 2 * z ** -3
    muld = mul.diff() if isinstance(mul, ZFilter) else 0
    assert almost_eq(num.diff(), numd)
    assert almost_eq(den.diff(), dend)
    assert almost_eq(num.diff(mul_after=mul), numd * mul)
    assert almost_eq(den.diff(mul_after=mul), dend * mul)
    filtd_num = numd * den - dend * num
    filtd = filtd_num / den ** 2
    assert almost_eq(filt.diff(), filtd)
    assert almost_eq(filt.diff(mul_after=mul), filtd * mul)
    numd2 = -2 * A * (1 - a) * z ** -3
    numd2ma = (numd2 * mul + muld * numd) * mul
    dend2 = -2 * A * z ** -3 + 6 * A ** 2 * z ** -4
    dend2ma = (dend2 * mul + muld * dend) * mul
    assert almost_eq(num.diff(2), numd2)
    assert almost_eq(den.diff(2), dend2)
    assert almost_eq(num.diff(n=2, mul_after=mul), numd2ma)
    assert almost_eq(den.diff(n=2, mul_after=mul), dend2ma)

    filtd2 = ((numd2 * den - num * dend2) * den - 2 * filtd_num * dend
             ) / den ** 3
    filt_to_test = filt.diff(n=2)
    assert almost_eq.diff(filt_to_test.numerator, filtd2.numerator,
                          max_diff=1e-10)
    assert almost_eq.diff(filt_to_test.denominator, filtd2.denominator,
                          max_diff=1e-10)

    if 1/(1 + z**-2) != mul: # Too difficult to group together with others
      filtd2ma = ((numd2 * den - num * dend2) * mul * den +
                  filtd_num * (muld * den - 2 * mul * dend)
                 ) * mul / den ** 3
      filt_to_testma = filt.diff(n=2, mul_after=mul)
      assert almost_eq.diff(filt_to_testma.numerator, filtd2ma.numerator,
                            max_diff=1e-10)
      assert almost_eq.diff(filt_to_testma.denominator, filtd2ma.denominator,
                            max_diff=1e-10)

  @p("delay", delays)
  def test_one_delay_variable_gain(self, delay):
    gain = cycle(self.alpha)
    filt = gain * z ** -delay
    length = 50
    assert isinstance(filt, ZFilter)
    data_stream = cycle(self.alpha) * zero_pad(cycle(self.data), left=delay)
    expected = data_stream.take(length)
    result_stream = filt(cycle(self.data))
    assert isinstance(result_stream, Stream)
    result = result_stream.take(length)
    assert almost_eq(result, expected)

  def test_variable_gain_in_denominator(self):
    a = Stream(1, 2, 3)
    filt = 1 / (a - z ** -1)
    assert isinstance(filt, ZFilter)
    ainv = Stream(1, .5, 1./3)
    expected_filt1 = ainv.copy() / (1 - ainv.copy() * z ** -1)
    assert isinstance(expected_filt1, ZFilter)
    ai = thub(ainv, 2)
    expected_filt2 = ai / (1 - ai * z ** -1)
    assert isinstance(expected_filt2, ZFilter)
    length = 50
    expected1 = expected_filt1(cycle(self.data))
    expected2 = expected_filt2(cycle(self.data))
    result = filt(cycle(self.data))
    assert isinstance(expected1, Stream)
    assert isinstance(expected2, Stream)
    assert isinstance(result, Stream)
    r = result.take(length)
    ex1, ex2 = expected1.take(length), expected2.take(length)
    assert almost_eq(r, ex1)
    assert almost_eq(r, ex2)
    assert almost_eq(ex1, ex2)

  @p("delay", delays)
  def test_fir_time_variant_sum(self, delay):
    gain1 = cycle(self.alpha)
    gain2 = cycle(self.alpha[-2::-1])
    filt = gain1 * z ** -delay + gain2 * z ** -self.delays[0]
    length = 50
    assert isinstance(filt, ZFilter)
    data_stream1 = cycle(self.alpha) * zero_pad(cycle(self.data), left=delay)
    data_stream2 = cycle(self.alpha[-2::-1]) * zero_pad(cycle(self.data),
                                                        left=self.delays[0])
    expected = data_stream1 + data_stream2
    result = filt(cycle(self.data))
    assert isinstance(expected, Stream)
    assert isinstance(result, Stream)
    r, ex = result.take(length), expected.take(length)
    assert almost_eq(r, ex)

  @p("delay", delays)
  def test_iir_time_variant_sum(self, delay):
    gain1 = cycle(self.alpha)
    gain2 = cycle(self.alpha[-2::-1])
    gain3 = Stream(1, 2, 3)
    gain4 = Stream(.1, .7, -.5, -1e-3)
    gain5 = Stream(.1, .2)
    gain6 = Stream(3, 2, 1, 0)
    num1 = gain1.copy() * z ** -delay + gain2.copy() * z ** -self.delays[0]
    assert isinstance(num1, ZFilter)
    den1 = 1 + gain3.copy() * z ** -(delay + 2)
    assert isinstance(den1, ZFilter)
    filt1 = num1 / den1
    assert isinstance(filt1, ZFilter)
    num2 = gain4.copy() * z ** -delay + gain5.copy() * z ** -self.delays[-1]
    assert isinstance(num1, ZFilter)
    den2 = 1 + gain6.copy() * z ** -(delay - 1)
    assert isinstance(den2, ZFilter)
    filt2 = num2 / den2
    assert isinstance(filt2, ZFilter)
    filt = filt1 + filt2
    assert isinstance(filt, ZFilter)
    length = 90
    expected_filter = (
      gain1.copy() * z ** -delay +
      gain2.copy() * z ** -self.delays[0] +
      gain1.copy() * gain6.copy() * z ** -(2 * delay - 1) +
      gain2.copy() * gain6.copy() * z ** -(delay + self.delays[0] - 1) +
      gain4.copy() * z ** -delay +
      gain5.copy() * z ** -self.delays[-1] +
      gain4.copy() * gain3.copy() * z ** -(2 * delay + 2) +
      gain5.copy() * gain3.copy() * z ** -(delay + self.delays[-1] + 2)
    ) / (
      1 +
      gain3.copy() * z ** -(delay + 2) +
      gain6.copy() * z ** -(delay - 1) +
      gain3.copy() * gain6.copy() * z ** -(2 * delay + 1)
    )
    assert isinstance(expected_filter, ZFilter)
    expected = expected_filter(cycle(self.data))
    result = filt(cycle(self.data))
    assert isinstance(expected, Stream)
    assert isinstance(result, Stream)
    r, ex = result.take(length), expected.take(length)
    assert almost_eq(r, ex)

  @p("delay", delays)
  def test_fir_time_variant_multiplication(self, delay):
    gain1 = cycle(self.alpha)
    gain2 = cycle(self.alpha[::2])
    gain3 = 2 + cycle(self.alpha[::3])
    filt1 = gain1.copy() * z ** -delay + gain2.copy() * z ** -(delay + 1)
    filt2 = gain2.copy() * z ** -delay + gain3.copy() * z ** -(delay - 1)
    filt = filt1 * filt2
    expected_filter = (
      (gain1.copy() + gain3.copy())* gain2.copy() * z ** -(2 * delay) +
      gain1.copy() * gain3.copy() * z ** -(2 * delay - 1) +
      gain2.copy() ** 2 * z ** -(2 * delay + 1)
    )
    length = 80
    assert isinstance(filt1, ZFilter)
    assert isinstance(filt2, ZFilter)
    assert isinstance(expected_filter, ZFilter)
    expected = expected_filter(cycle(self.data))
    result = filt(cycle(self.data))
    assert isinstance(expected, Stream)
    assert isinstance(result, Stream)
    r, ex = result.take(length), expected.take(length)
    assert almost_eq(r, ex)

  @p("delay", delays)
  def test_iir_time_variant_multiplication(self, delay):
    gain1 = cycle([4, 5, 6, 5, 4, 3])
    gain2 = cycle(self.alpha[::-1])
    gain3 = Stream(*(self.alpha + [1, 2, 3]))
    gain4 = Stream(.1, -.2, .3)
    gain5 = Stream(.1, .1, .1, -7)
    gain6 = Stream(3, 2)
    num1 = gain1.copy() * z ** -delay + gain2.copy() * z ** -self.delays[0]
    assert isinstance(num1, ZFilter)
    den1 = 1 + gain3.copy() * z ** -(delay - 1)
    assert isinstance(den1, ZFilter)
    filt1 = num1 / den1
    assert isinstance(filt1, ZFilter)
    num2 = gain4.copy() * z ** -delay + gain5.copy() * z ** -self.delays[-1]
    assert isinstance(num1, ZFilter)
    den2 = 1 + gain6.copy() * z ** -(delay + 5)
    assert isinstance(den2, ZFilter)
    filt2 = num2 / den2
    assert isinstance(filt2, ZFilter)
    filt = filt1 * filt2
    assert isinstance(filt, ZFilter)
    length = 90
    expected_filter = (
      gain1.copy() * gain4.copy() * z ** -(2 * delay) +
      gain2.copy() * gain4.copy() * z ** -(delay + self.delays[0]) +
      gain1.copy() * gain5.copy() * z ** -(delay + self.delays[-1]) +
      gain2.copy() * gain5.copy() * z ** -(self.delays[0] + self.delays[-1])
    ) / (
      1 +
      gain3.copy() * z ** -(delay - 1) +
      gain6.copy() * z ** -(delay + 5) +
      gain3.copy() * gain6.copy() * z ** -(2 * delay + 4)
    )
    assert isinstance(expected_filter, ZFilter)
    expected = expected_filter(cycle(self.data))
    result = filt(cycle(self.data))
    assert isinstance(expected, Stream)
    assert isinstance(result, Stream)
    r, ex = result.take(length), expected.take(length)
    assert almost_eq(r, ex)

  def test_copy(self):
    filt1 = (2 + Stream(1, 2, 3) * z ** -1) / Stream(1, 5)
    filt2 = filt1.copy()
    assert isinstance(filt2, ZFilter)
    assert filt1 is not filt2
    filt_ex = Stream(2, .4) + Stream(1, .4, 3, .2, 2, .6) * z ** -1
    length = 50
    r1 = filt1(cycle(self.data[::-1])).take(length)
    r2 = filt2(cycle(self.data[::-1])).take(length)
    ex = filt_ex(cycle(self.data[::-1])).take(length)
    assert almost_eq(r1, ex)
    assert almost_eq(r2, ex)
    assert almost_eq(r1, r2)

  @p("delay", delays)
  def test_iir_time_variant_sum_with_copy(self, delay):
    k = thub(min(self.alpha) + 2 + cycle(self.alpha), 3)
    filt = z ** -2 / k + Stream(5, 7) * z / (1 + z ** -delay)
    filt += filt.copy()
    filt *= z ** -1
    assert isinstance(filt, ZFilter)
    length = 40
    expected_filter = (
      2 / k * z ** -3 +
      2 / k * z ** -(delay + 3) +
      Stream(10, 14)
    ) / (1 + z ** -delay)
    assert isinstance(expected_filter, ZFilter)
    expected = expected_filter(cycle(self.data))
    result = filt(cycle(self.data))
    assert isinstance(expected, Stream)
    assert isinstance(result, Stream)
    r, ex = result.take(length), expected.take(length)
    assert almost_eq(r, ex)

  def test_hashable(self):
    filt = 1 / (7 + z ** -1)
    my_set = {filt, 17, z, z ** -1, object}
    assert z in my_set
    assert z ** -1 in my_set
    assert filt in my_set
    assert -z not in my_set


@p("filt_class", [CascadeFilter, ParallelFilter])
class TestCascadeAndParallelFilters(object):

  def test_add(self, filt_class):
    filt1 = filt_class(z)
    filt2 = filt_class(z + 3)
    filt_sum = filt1 + filt2
    assert isinstance(filt_sum, filt_class)
    assert filt_sum == filt_class(z, z + 3)

  def test_mul(self, filt_class):
    filt = filt_class(1 - z ** -1)
    filt_prod = filt * 3
    assert isinstance(filt_prod, filt_class)
    assert filt_prod == filt_class(1 - z ** -1, 1 - z ** -1, 1 - z ** -1)

  @p("filts",
     [(lambda data: data ** 2),
      (z ** -1, lambda data: data + 4),
      (1 / z ** -2, (lambda data: 0.), z** -1),
     ])
  def test_non_linear(self, filts, filt_class):
    filt = filt_class(filts)
    assert isinstance(filt, filt_class)
    assert not filt.is_linear()
    with pytest.raises(AttributeError):
      filt.numpoly
    with pytest.raises(AttributeError):
      filt.denpoly
    with pytest.raises(AttributeError):
      filt.freq_response(pi / 2)

  def test_const_filter(self, filt_class):
    data = [2, 4, 3, 7 -1, -8]
    filt1 = filt_class(*data)
    filt2 = filt_class(data)
    func = operator.mul if filt_class == CascadeFilter else operator.add
    expected_value = reduce(func, data)
    count = 10
    for d in data:
      expected = [d * expected_value] * count
      assert filt1(Stream(d)).take(count) == expected
      assert filt2(Stream(d)).take(count) == expected


class TestCascadeOrParallelFilter(object):

  data_values = [orange(3),
                 Stream([5., 4., 6., 7., 12., -2.]),
                 [.2, .5, .4, .1]
                ]

  @p("data", data_values)
  def test_call_empty_cascade(self, data):
    dtest = data.copy() if isinstance(data, Stream) else data
    for el, elt in xzip(CascadeFilter()(data), dtest):
      assert el == elt

  @p("data", data_values)
  def test_call_empty_parallel(self, data):
    for el in ParallelFilter()(data):
      assert el == 0.


class TestResonator(object):

  @p("func", resonator)
  def test_zeros_and_number_of_poles(self, func):
    names = set(resonator.__name__.split("_"))
    filt = func(pi / 2, pi / 18) # Values in rad / sample
    assert isinstance(filt, ZFilter)
    assert len(filt.denominator) == 3
    num = filt.numerator
    if "z" in names:
      assert len(num) == 3
      assert num[1] == 0
      assert num[0] == -num[2]
    if "poles" in names:
      assert len(filt.numerator) == 1 # Just a constant

  @p("func", resonator)
  @p("freq", [pi / 2, pi / 3, 2 * pi / 3])
  @p("bw", [pi * k / 15 for k in xrange(1, 5)])
  def test_radius_range(self, func, freq, bw):
    filt = func(freq, bw)
    R_squared = filt.denominator[2]
    assert 0 < R_squared < 1

  @p("func", [r for r in resonator if "freq" not in r.__name__.split("_")])
  @p("freq", [pi * k / 7 for k in xrange(1, 7)])
  @p("bw", [pi / 25, pi / 30])
  def test_gain_0dB_at_given_freq(self, func, freq, bw):
    filt = func(freq, bw)
    gain = dB20(filt.freq_response(freq))
    assert almost_eq.diff(gain, 0., max_diff=5e-14)


class TestLowpassHighpass(object):

  @p("filt_func", [lowpass.pole, highpass.pole])
  @p("freq", [pi * k / 7 for k in xrange(1, 7)])
  def test_3dB_gain(self, filt_func, freq):
    filt = filt_func(freq)
    ref_gain = dB10(.5) # -3.0103 dB
    assert almost_eq(dB20(filt.freq_response(freq)), ref_gain)

  @p("sdict", [lowpass, highpass])
  @p(("freq", "tol"), list(xzip(
    [pi/300, pi / 30, pi / 15, pi/10, 2 * pi/15, pi / 6],
    [7, 13, 15, 16, 17, 18] # At least 5 significand bits should be ok!
  )))
  def test_pole_exp_for_small_cutoff_frequencies(self, sdict, freq, tol):
    if sdict is highpass:
      freq = pi - freq # To use the reliable range
    filt = sdict.pole_exp(freq)
    expected = sdict.pole(freq)
    assert almost_eq(filt.numerator, expected.numerator, tol=tol)
    assert almost_eq(filt.denominator, expected.denominator, tol=tol)
    assert almost_eq(abs(filt.freq_response(freq)), .5 ** .5, tol=tol)
    assert almost_eq.diff(dB20(filt.freq_response(freq)), dB10(.5),
                          max_diff=.1)

  @p("filt_func", lowpass)
  @p("freq", [pi * k / 7 for k in xrange(1, 7)])
  def test_lowpass_is_lowpass(self, filt_func, freq):
    filt = filt_func(freq)
    assert almost_eq(abs(filt.freq_response(0.)), 1.)
    freqs = line(50, 0, pi)
    for a, b in filt.freq_response(freqs).map(abs).blocks(size=2, hop=1):
      assert b < a

  @p("filt_func", highpass)
  @p("freq", [pi * k / 7 for k in xrange(1, 7)])
  def test_highpass_is_highpass(self, filt_func, freq):
    filt = filt_func(freq)
    assert almost_eq(abs(filt.freq_response(pi)), 1.)
    freqs = line(50, 0, pi)
    for a, b in filt.freq_response(freqs).map(abs).blocks(size=2, hop=1):
      assert a < b

########NEW FILE########
__FILENAME__ = test_filters_extdep
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Sat Oct 06 2012
# danilo [dot] bellini [at] gmail [dot] com
"""
Testing module for the lazy_filters module by using Numpy/Scipy/Sympy
"""

import pytest
p = pytest.mark.parametrize

from scipy.signal import lfilter
from scipy.optimize import fminbound
from math import cos, pi, sqrt
from numpy import mat
from sympy import symbols, Matrix, sqrt as symb_sqrt

# Audiolazy internal imports
from ..lazy_filters import ZFilter, resonator, z
from ..lazy_misc import almost_eq
from ..lazy_compat import orange, xrange, xzip, xmap
from ..lazy_math import dB20
from ..lazy_itertools import repeat, cycle, count
from ..lazy_stream import Stream, thub


class TestZFilterNumpyScipySympy(object):

  @p("a", [[1.], [3.], [1., 3.], [15., -17.2], [-18., 9.8, 0., 14.3]])
  @p("b", [[1.], [-1.], [1., 0., -1.], [1., 3.]])
  @p("data", [orange(5), orange(5, 0, -1), [7, 22, -5], [8., 3., 15.]])
  def test_lfilter(self, a, b, data):
    filt = ZFilter(b, a)
    expected = lfilter(b, a, data).tolist()
    assert almost_eq(filt(data), expected)

  def test_matrix_coefficients_multiplication(self):
    m = mat([[1, 2], [2, 2]])
    n1 = mat([[1.2, 3.2], [1.2, 1.1]])
    n2 = mat([[-1, 2], [-1, 2]])
    a = mat([[.3, .4], [.5, .6]])

    # Time-varying filter with 2x2 matrices as coeffs
    mc = repeat(m) # "Constant" coeff
    nc = cycle([n1, n2]) # Periodic coeff
    ac = repeat(a)
    filt = (mc + nc * z ** -1) / (1 - ac * z ** -1)

    # For a time-varying 2x3 matrix signal
    data = [
      Stream(1, 2),
      count(),
      count(start=1, step=2),
      cycle([.2, .33, .77, pi, cos(3)]),
      repeat(pi),
      count(start=sqrt(2), step=pi/3),
    ]

    # Copy just for a future verification of the result
    data_copy = [el.copy() for el in data]

    # Build the 2x3 matrix input signal and find the result!
    sig = Stream(mat(vect).reshape(2, 3) for vect in xzip(*data))
    zero = mat([[0, 0, 0], [0, 0, 0]])
    result = filt(sig, zero=zero).limit(30)

    # Result found, let's just find if they're what they should be
    in_sample = old_expected_out_sample = zero
    n, not_n = n1, n2
    for out_sample in result:
      old_in_sample = in_sample
      in_sample = mat([s.take() for s in data_copy]).reshape(2, 3)
      expected_out_sample = m * in_sample + n * old_in_sample \
                                          + a * old_expected_out_sample
      assert almost_eq(out_sample.tolist(), expected_out_sample.tolist())
      n, not_n = not_n, n
      old_expected_out_sample = expected_out_sample

  def test_symbolic_signal_and_coeffs(self):
    symbol_tuple = symbols("a b c d")
    a, b, c, d = symbol_tuple
    ac, bc, cc = xmap(repeat, symbol_tuple[:-1]) # Coeffs (Stream instances)
    zero = a - a # Symbolic zero

    filt = (ac * z ** -1 + bc * z ** -2) / (1 + cc * z ** -2)
    sig = Stream([d] * 5, repeat(zero))
    result = filt(sig, zero=zero)

    # Let's find if that worked:
    expected = [ # out[n] = a * in[n - 1] + b * in[n - 2] - c * out[n - 2]
      zero,                      # input: d
      a*d,                       # input: d
      a*d + b*d,                 # input: d
      a*d + b*d - c*a*d,         # input: d
      a*d + b*d - c*(a*d + b*d), # input: d (last non-zero input)
      a*d + b*d - c*(a*d + b*d - c*a*d),
      b*d - c*(a*d + b*d - c*(a*d + b*d)),
      -c*(a*d + b*d - c*(a*d + b*d - c*a*d)),
    ]
    for unused in range(50): # Create some more samples
      expected.append(-c * expected[-2])
    size = len(expected)
    assert result.peek(size) == expected

    # Let's try again, now defining c as zero (with sub method from sympy)
    another_result = result.subs(c, zero).take(size)
    another_expected = [zero] * size
    for idx in xrange(5):
      another_expected[idx+1] += a*d
      another_expected[idx+2] += b*d
    assert another_result == another_expected

  def test_symbolic_matrices_sig_and_coeffs_state_space_filters(self):
    # Create symbols k[0], k[1], k[2], ..., k[30]
    k = symbols(" ".join("k{}".format(idx) for idx in range(31)))

    # Matrices for coeffs
    am = [                  # Internal state delta matrix
      Matrix([[k[0], k[1]], # (as a periodic sequence)
              [k[2], k[3]]]),
      Matrix([[k[1], k[2]], [k[3], k[0]]]),
      Matrix([[k[2], k[3]], [k[0], k[1]]]),
      Matrix([[k[3], k[0]], [k[1], k[2]]]),
    ]
    bm = Matrix([[k[4], k[5], k[6],  k[7]], # Input to internal state matrix
                 [k[8], k[9], k[10], k[11]]])
    cm = Matrix([[k[12], k[13]], # Internal state to output matrix
                 [k[14], k[15]],
                 [k[16], k[17]]])
    dm = Matrix([[k[18], k[19], k[20], k[21]], # Input to output matrix
                 [k[22], k[23], k[24], k[25]],
                 [k[26], k[27], k[28], k[29]]])

    # Zero is needed, not only the symbol but the matrices
    zero = k[30] - k[30]
    zero_state = Matrix([[zero]] * 2)
    zero_input = Matrix([[zero]] * 4)
    zero_kwargs = dict(zero=zero_input, memory=repeat(zero_state))

    # The state filter itself
    #   x[n] = A[n] * x[n-1] + B[n] * u[n-1]
    #   y[n] = C[n] * x[n]   + D[n] * u[n]
    ac = cycle(am)
    bc, cc, dc = xmap(repeat, [bm, cm, dm])
    xfilt = (bc * z ** -1) / (1 - ac * z ** -1)
    def filt(data):
      data = thub(data, 2)
      return cc * xfilt(data, **zero_kwargs) + dc * data

    # Data to be used as input: u[n] = k[30] / (n + r),
    # where n >= 0 and r is the row, 1 to 4
    sigs = [repeat(k[30]) / count(start=r, step=1) for r in [1, 2, 3, 4]]
    u = Stream(Matrix(vect) for vect in xzip(*sigs))
    result = filt(u)

    # Result verification
    u_list = [
      Matrix([[k[30] / el] for el in [i, i+1, i+2, i+3]])
      for i in range(1, 50)
    ]
    expected = [dm * u_list[0]]
    internal = [bm * u_list[0]]
    for idx, ui in enumerate(u_list[1:], 2):
      expected.append(cm * internal[-1] + dm * ui)
      internal.append(am[idx % 4] * internal[-1] + bm * ui)
    size = len(expected)
    assert result.peek(size) == expected

  def test_symbolic_fixed_matrices_sig_and_coeffs_state_space_filters(self):
    k = symbols("k")
    size = 100
    s2, s3, s6 = xmap(symb_sqrt, [2, 3, 6])

    # Same idea from the test above, but with numbers as symbolic coeffs
    uf = [Matrix([k / el for el in [i, i+1, i+2, i+3]])
          for i in range(1, size+1)]
    af = [
      Matrix([[1, 0], [0, 0]]),
      Matrix([[0, 0], [0, 1]]),
      Matrix([[0, 0], [1, 0]]),
      Matrix([[0, 1], [0, 0]]),
    ]
    bf = Matrix([[1, 1, 1, 1], [-1, -1, -1, -1]])
    cf = Matrix([[s3, 0], [0, s3], [0, 0]])
    df = Matrix([[s2, 0, 0, 0], [0, s2, 0, 0], [0, 0, s2, 0]])

    # Zero is needed, not only the symbol but the matrices
    zero = k - k
    zero_state = Matrix([[zero]] * 2)
    zero_input = Matrix([[zero]] * 4)
    zero_kwargs = dict(zero=zero_input, memory=repeat(zero_state))

    # Calculates the whole symbolical sequence (fixed numbers)
    afc = cycle(af)
    bfc, cfc, dfc = xmap(repeat, [bf, cf, df])
    xffilt = (bfc * z ** -1) / (1 - afc * z ** -1)
    def ffilt(data):
      data = thub(data, 2)
      return cfc * xffilt(data, **zero_kwargs) + dfc * data
    result_f = ffilt(Stream(uf)).subs(k, s6).take(size)

    expected_f = [df * uf[0].subs(k, s6)]
    internal_f = [bf * uf[0].subs(k, s6)]
    for idx, ufi in enumerate(uf[1:], 2):
      ufis = ufi.subs(k, s6)
      expected_f.append(cf * internal_f[-1] + df * ufis)
      internal_f.append(af[idx % 4] * internal_f[-1] + bf * ufis)
    assert result_f == expected_f

    # Numerical!
    to_numpy = lambda mlist: [mat(m.applyfunc(float).tolist()) for m in mlist]
    un = to_numpy(ui.subs(k, s6) for ui in uf)
    an = to_numpy(af)
    bn, cn, dn = to_numpy([bf, cf, df])

    expected_n = [dn * un[0]]
    internal_n = [bn * un[0]]
    for idx, uni in enumerate(un[1:], 2):
      expected_n.append(cn * internal_n[-1] + dn * uni)
      internal_n.append(an[idx % 4] * internal_n[-1] + bn * uni)
    result_n = [el.tolist() for el in to_numpy(result_f)]
    assert almost_eq(result_n, [m.tolist() for m in expected_n])


class TestResonatorScipy(object):

  @p("func", resonator)
  @p("freq", [pi * k / 9 for k in xrange(1, 9)])
  @p("bw", [pi / 23, pi / 31])
  def test_max_gain_is_at_resonance(self, func, freq, bw):
    names = func.__name__.split("_")
    filt = func(freq, bw)
    resonance_freq = fminbound(lambda x: -dB20(filt.freq_response(x)),
                               0, pi, xtol=1e-10)
    resonance_gain = dB20(filt.freq_response(resonance_freq))
    assert almost_eq.diff(resonance_gain, 0., max_diff=1e-12)

    if "freq" in names: # Given frequency is at the denominator
      R = sqrt(filt.denominator[2])
      assert 0 < R < 1
      cosf = cos(freq)
      cost = -filt.denominator[1] / (2 * R)
      assert almost_eq(cosf, cost)

      if "z" in names:
        cosw = cosf * (2 * R) / (1 + R ** 2)
      elif "poles" in names:
        cosw = cosf * (1 + R ** 2) / (2 * R)

      assert almost_eq(cosw, cos(resonance_freq))

    else: # Given frequency is the resonance frequency
      assert almost_eq(freq, resonance_freq)

########NEW FILE########
__FILENAME__ = test_io
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Wed Mar 06 2013
# danilo [dot] bellini [at] gmail [dot] com
"""
Testing module for the lazy_io module
"""

import pytest
p = pytest.mark.parametrize

import pyaudio
import _portaudio
from collections import deque
from time import sleep
import struct

# Audiolazy internal imports
from ..lazy_io import AudioIO, chunks
from ..lazy_synth import white_noise
from ..lazy_stream import Stream
from ..lazy_misc import almost_eq
from ..lazy_compat import orange


class WaitStream(Stream):
  """
  FIFO ControlStream-like class in which ``value`` is a deque object that
  waits a given duration when there's no more data available.
  """

  def __init__(self, duration=.01):
    """ Constructor. Duration in seconds """
    self.value = deque()
    self.active = True

    def data_generator():
      while self.active or self.value:
        try:
          yield self.value.popleft()
        except:
          sleep(duration)

    super(WaitStream, self).__init__(data_generator())


class MockPyAudio(object):
  """
  Fake pyaudio.PyAudio I/O manager class to work with only one output.
  """
  def __init__(self):
    self.fake_output = Stream(0.)
    self._streams = set()
    self.terminated = False

  def terminate(self):
    assert len(self._streams) == 0
    self.terminated = True

  def open(self, **kwargs):
    new_pastream = pyaudio.Stream(self, **kwargs)
    self._streams.add(new_pastream)
    return new_pastream


class MockStream(object):
  """
  Fake pyaudio.Stream class for testing.
  """
  def __init__(self, pa_manager, **kwargs):
    self._pa = pa_manager
    self._stream = self
    self.output = "output" in kwargs and kwargs["output"]
    if self.output:
      pa_manager.fake_output = WaitStream()

  def close(self):
    if self.output: # This is the only output
      self._pa.fake_output.active = False
    self._pa._streams.remove(self)


def mock_write_stream(pa_stream, data, chunk_size, should_throw_exception):
  """
  Fake _portaudio.write_stream function for testing.
  """
  sdata = struct.unpack("{0}{1}".format(chunk_size, "f"), data)
  pa_stream._pa.fake_output.value.extend(sdata)


@p("data", [orange(25), white_noise(100) + 3.])
@pytest.mark.timeout(2)
def test_output_only(monkeypatch, data):
  monkeypatch.setattr(pyaudio, "PyAudio", MockPyAudio)
  monkeypatch.setattr(pyaudio, "Stream", MockStream)
  monkeypatch.setattr(_portaudio, "write_stream", mock_write_stream)

  chunk_size = 16
  data = list(data)
  with AudioIO(True) as player:
    player.play(data, chunk_size=chunk_size)

    played_data = list(player._pa.fake_output)
    ld, lpd = len(data), len(played_data)
    assert all(isinstance(x, float) for x in played_data)
    assert lpd % chunk_size == 0
    assert lpd - ld == -ld % chunk_size
    assert all(x == 0. for x in played_data[ld - lpd:]) # Zero-pad at end
    assert almost_eq(played_data, data) # Data loss (64-32bits conversion)

  assert player._pa.terminated # Test whether "terminate" was called


@p("func", chunks)
class TestChunks(object):

  data = [17., -3.42, 5.4, 8.9, 27., 45.2, 1e-5, -3.7e-4, 7.2, .8272, -4.]
  ld = len(data)
  sizes = [1, 2, 3, 4, ld - 1, ld, ld + 1, 2 * ld, 2 * ld + 1]
  data_segments = (lambda d: [d[:idx] for idx, unused in enumerate(d)])(data)

  @p("size", sizes)
  @p("given_data", data_segments)
  def test_chunks(self, func, given_data, size):
    dfmt="f"
    padval=0.
    data = b"".join(func(given_data, size=size, dfmt=dfmt, padval=padval))
    samples_in = len(given_data)
    samples_out = samples_in
    if samples_in % size != 0:
      samples_out -= samples_in % -size
      assert samples_out > samples_in # Testing the tester...
    restored_data = struct.Struct(dfmt * samples_out).unpack(data)
    assert almost_eq(given_data,
                     restored_data[:samples_in],
                     ignore_type=True)
    assert almost_eq([padval]*(samples_out - samples_in),
                     restored_data[samples_in:],
                     ignore_type=True)

  @p("size", sizes)
  def test_default_size(self, func, size):
    dsize = chunks.size
    assert list(func(self.data)) == list(func(self.data, size=dsize))
    try:
      chunks.size = size
      assert list(func(self.data)) == list(func(self.data, size=size))
    finally:
      chunks.size = dsize

########NEW FILE########
__FILENAME__ = test_itertools
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Sun Mai 12 2013
# danilo [dot] bellini [at] gmail [dot] com
"""
Testing module for the lazy_itertools module
"""

import pytest
p = pytest.mark.parametrize

import operator
from functools import reduce

# Audiolazy internal imports
from ..lazy_itertools import accumulate, chain, izip, count
from ..lazy_stream import Stream
from ..lazy_math import inf
from ..lazy_poly import x


@p("acc", accumulate)
class TestAccumulate(object):

  @p("empty", [[], tuple(), set(), Stream([])])
  def test_empty_input(self, acc, empty):
    data = acc(empty)
    assert isinstance(data, Stream)
    assert list(data) == []

  def test_one_input(self, acc):
    for k in [1, -5, 1e3, inf, x]:
      data = acc([k])
      assert isinstance(data, Stream)
      assert list(data) == [k]

  def test_few_numbers(self, acc):
    data = acc(Stream([4, 7, 5, 3, -2, -3, -1, 12, 8, .5, -13]))
    assert isinstance(data, Stream)
    assert list(data) == [4, 11, 16, 19, 17, 14, 13, 25, 33, 33.5, 20.5]


class TestCount(object):

  def test_no_input(self):
    data = count()
    assert isinstance(data, Stream)
    assert data.take(14) == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
    assert data.take(3) == [14, 15, 16]

  @p("start", [0, -1, 7])
  def test_starting_value(self, start):
    data1 = count(start)
    data2 = count(start=start)
    assert isinstance(data1, Stream)
    assert isinstance(data2, Stream)
    expected_zero = Stream([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13])
    expected = (expected_zero + start).take(20)
    after = [14 + start, 15 + start, 16 + start]
    assert data1.take(14) == expected
    assert data2.take(13) == expected[:-1]
    assert data1.take(3) == after
    assert data2.take(4) == expected[-1:] + after

  @p("start", [0, -5, 1])
  @p("step", [1, -1, 3])
  def test_two_inputs(self, start, step):
    data1 = count(start, step)
    data2 = count(start=start, step=step)
    assert isinstance(data1, Stream)
    assert isinstance(data2, Stream)
    expected_zero = Stream([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13])
    expected = (expected_zero * step + start).take(20)
    after = list(Stream([14, 15, 16]) * step + start)
    assert data1.take(14) == expected
    assert data2.take(13) == expected[:-1]
    assert data1.take(3) == after
    assert data2.take(4) == expected[-1:] + after


class TestChain(object):

  data = [1, 5, 3, 17, -2, 8, chain, izip, pytest, lambda x: x, 8.2]
  some_lists = [data, data[:5], data[3:], data[::-1], data[::2], data[1::3]]

  @p("blk", some_lists)
  def test_with_one_list_three_times(self, blk):
    expected = blk + blk + blk
    result = chain(blk, blk, blk)
    assert isinstance(result, Stream)
    assert list(result) == expected
    result = chain.from_iterable(3 * [blk])
    assert isinstance(result, Stream)
    assert result.take(inf) == expected

  def test_with_lists(self):
    blk = self.some_lists
    result = chain(*blk)
    assert isinstance(result, Stream)
    expected = list(reduce(operator.concat, blk))
    assert list(result) == expected
    result = chain.from_iterable(blk)
    assert isinstance(result, Stream)
    assert list(result) == expected
    result = chain.star(blk)
    assert isinstance(result, Stream)
    assert list(result) == expected

  def test_with_endless_stream(self):
    expected = [1, 2, -3, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    result = chain([1, 2, -3], count())
    assert isinstance(result, Stream)
    assert result.take(len(expected)) == expected
    result = chain.from_iterable(([1, 2, -3], count()))
    assert isinstance(result, Stream)
    assert result.take(len(expected)) == expected

  def test_star_with_generator_input(self):
    def gen():
      yield [5, 5, 5]
      yield [2, 2]
      yield count(-4, 2)
    expected = [5, 5, 5, 2, 2, -4, -2, 0, 2, 4, 6, 8, 10, 12]
    result = chain.star(gen())
    assert isinstance(result, Stream)
    assert result.take(len(expected)) == expected
    assert chain.star is chain.from_iterable

  @pytest.mark.timeout(2)
  def test_star_with_endless_generator_input(self):
    def gen(): # Yields [], [1], [2, 2], [3, 3, 3], ...
      for c in count():
        yield [c] * c
    expected = [1, 2, 2, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 5, 6]
    result = chain.star(gen())
    assert isinstance(result, Stream)
    assert result.take(len(expected)) == expected


class TestIZip(object):

  def test_smallest(self):
    for func in [izip, izip.smallest]:
      result = func([1, 2, 3], [4, 5])
      assert isinstance(result, Stream)
      assert list(result) == [(1, 4), (2, 5)]

  def test_longest(self):
    result = izip.longest([1, 2, 3], [4, 5])
    assert isinstance(result, Stream)
    assert list(result) == [(1, 4), (2, 5), (3, None)]

  def test_longest_fillvalue(self):
    result = izip.longest([1, -2, 3], [4, 5], fillvalue=0)
    assert isinstance(result, Stream)
    assert list(result) == [(1, 4), (-2, 5), (3, 0)]

########NEW FILE########
__FILENAME__ = test_lpc
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Wed Jan 23 2012
# danilo [dot] bellini [at] gmail [dot] com
"""
Testing module for the lazy_lpc module
"""

import pytest
p = pytest.mark.parametrize

import itertools as it
import operator
from functools import reduce

# Audiolazy internal imports
from ..lazy_lpc import (toeplitz, levinson_durbin, lpc, parcor,
                        parcor_stable, lsf, lsf_stable)
from ..lazy_misc import almost_eq
from ..lazy_compat import xrange, xmap
from ..lazy_filters import z, ZFilter


class TestLPCParcorLSFAndStability(object):

  # Some audio sequences as examples
  block_alternate = [1., 1./2., -1./8., 1./32., -1./128., 1./256., -1./512.,
                     1./1024., -1./4096., 1./8192.]
  real_block = [3744, 2336, -400, -3088, -5808, -6512, -6016, -4576, -3088,
    -1840, -944, 176, 1600, 2976, 3808, 3600, 2384, 656, -688, -1872, -2576,
    -3184, -3920, -4144, -3584, -2080, 144, 2144, 3472, 4032, 4064, 4048,
    4016, 3984, 4032, 4080, 3888, 1712, -1296, -4208, -6720, -6848, -5904,
    -4080, -2480, -1200, -560, 592, 1856, 3264, 4128, 3936, 2480, 480, -1360,
    -2592, -3184, -3456, -3760, -3856, -3472, -2160, -80, 2112, 3760, 4416,
    4304, 3968, 3616, 3568, 3840, 4160, 4144, 2176, -1024, -4144, -6800,
    -7120, -5952, -3920, -2096, -800, -352, 352, 1408, 2768, 4032, 4304,
    3280, 1168, -992, -2640, -3584, -3664, -3680, -3504, -3136, -2304, -800,
    1232, 3088, 4352, 4720, 4432, 3840, 3312, 3248, 3664, 4144, 2928, 96,
    -3088, -6448, -7648, -6928, -4864, -2416, -512, 208, 544, 976, 1760, 3104,
    4064, 4016, 2624, 416, -1904, -3696, -4368, -4320, -3744, -2960, -1984,
    -848, 576, 2112, 3504, 4448, 4832, 4656, 4048, 3552, 3360, 3616, 2912,
    736, -1920, -5280, -7264, -7568, -6320, -3968, -1408, 288, 1184, 1600,
    1744, 2416, 3184
  ]

  # Each dictionary entry is a massive test family, for each strategy. The
  # dictionary entry "k" have the PARCOR coefficients, but not reversed
  table_data = [
    {"blk": block_alternate,
     "strategies": (lpc.autocor, lpc.nautocor, lpc.kautocor),
     "order": 3,
     "lpc": 1 - 0.457681292332 * z ** -1 \
               + 0.297451538058 * z ** -2 \
               - 0.162014679229 * z ** -3,
     "lpc_error": 1.03182436137,
     "k": [-0.342081949224, 0.229319810099, -0.162014679229],
     "lsf": (-2.0461731139434804, -1.4224191795241481, -0.69583069081054594,
             0.0, 0.69583069081054594, 1.4224191795241481, 2.0461731139434804,
             3.1415926535897931),
     "stable": True,
    },

    {"blk": block_alternate,
     "strategies": (lpc.covar, lpc.kcovar),
     "order": 3,
     "lpc": 1 + 0.712617839203 * z ** -1 \
              + 0.114426147267 * z ** -2 \
              + 0.000614348391636 * z ** -3,
     "lpc_error": 3.64963839634e-06,
     "k": [0.6396366551286051, 0.1139883946659675, 0.000614348391636012],
     "lsf": (-2.6203603524613603, -1.9347821510481453, -1.0349253486092844,
             0.0, 1.0349253486092844, 1.9347821510481453, 2.6203603524613603,
             3.1415926535897931),
     "stable": True,
    },

    {"blk": real_block,
     "strategies": (lpc.covar, lpc.kcovar),
     "order": 2,
     "lpc": 1 - 1.765972108770 * z ** -1 \
              + 0.918762660191 * z ** -2,
     "lpc_error": 47473016.7152,
     "k": [-0.9203702705945026, 0.9187626601910946],
     "lsf": (-0.5691351064785074, -0.39341656885093923, 0.0,
             0.39341656885093923, 0.5691351064785074, 3.1415926535897931),
     "stable": True,
    },

    {"blk": real_block,
     "strategies": (lpc.covar, lpc.kcovar),
     "order": 6,
     "lpc": 1 - 2.05030891 * z ** -1 \
              + 1.30257925 * z ** -2 \
              + 0.22477252 * z ** -3 \
              - 0.25553702 * z ** -4 \
              - 0.47493330 * z ** -5 \
              + 0.43261407 * z ** -6,
     "lpc_error": 17271980.6421,
     "k": [-0.9211953262806057, 0.9187524349022875, -0.5396255901174379,
           0.1923394201597473, 0.5069344687875105, 0.4326140684936846],
     "lsf": (-2.5132553398123534, -1.9109023033210299, -0.89749807383952362,
             -0.79811198176990206, -0.38473054441488624, -0.33510868444931502,
             0.0, 0.33510868444931502, 0.38473054441488624,
             0.79811198176990206, 0.89749807383952362, 1.9109023033210299,
             2.5132553398123534, 3.1415926535897931),
     "stable": True,
    },
  ]

  @p(("strategy", "data"),
     [(strategy, data) for data in table_data
                       for strategy in data["strategies"]
     ])
  def test_block_info(self, strategy, data):
    filt = strategy(data["blk"], data["order"])
    assert almost_eq(filt, data["lpc"])
    assert almost_eq(filt.error, data["lpc_error"])
    assert almost_eq(list(parcor(filt))[::-1], data["k"])
    assert almost_eq(lsf(filt), data["lsf"])
    assert parcor_stable(1 / filt) == data["stable"]
    assert lsf_stable(1 / filt) == data["stable"]


class TestLPC(object):

  small_block = [-1, 0, 1.2, -1, -2.7, 3, 7.1, 9, 12.3]
  big_block = list((1 - 2 * z ** -1)(xrange(150), zero=0))
  block_list = [
    [1, 5, 3],
    [1, 2, 3, 3, 2, 1],
    small_block,
    TestLPCParcorLSFAndStability.block_alternate,
    big_block,
  ]
  order_list = [1, 2, 3, 7, 17, 18]
  kcovar_zdiv_error_cases = [ # tuples (blk, order)
    ([1, 5, 3], 2),
    (TestLPCParcorLSFAndStability.block_alternate, 7),
  ]
  blk_order_pairs = list(it.product(block_list, order_list))
  covars_value_error_cases = [(blk, order) for blk, order in blk_order_pairs
                                           if len(blk) <= order]
  kcovar_value_error_cases = (lambda bb, sb, ol: ( # Due to zero "k" coeffs
    [(bb, order) for order in ol if order <= 18] +
    [(sb, order) for order in ol if order <= 7]
  ))(bb=big_block, sb=small_block, ol=order_list)
  kcovar_valid_cases = (lambda ok_pairs, not_ok_pairs:
    [pair for pair in ok_pairs if pair not in not_ok_pairs]
  )(ok_pairs = blk_order_pairs,
    not_ok_pairs = kcovar_zdiv_error_cases + covars_value_error_cases +
                   kcovar_value_error_cases)

  @p(("blk", "order"), blk_order_pairs)
  def test_equalness_all_autocorrelation_strategies(self, blk, order):
    # Common case, tests whether all solutions are the same
    strategy_names = ("autocor", "nautocor", "kautocor")
    filts = [lpc[name](blk, order) for name in strategy_names]
    for f1, f2 in it.combinations(filts, 2):
      assert almost_eq(f1, f2) # But filter comparison don't include errors
      assert almost_eq(f1.error, f2.error)
      assert f1.error >= 0.
      assert f2.error >= 0.

  @p(("blk", "order"), kcovar_zdiv_error_cases)
  def test_kcovar_zdiv_error(self, blk, order):
    with pytest.raises(ZeroDivisionError):
      lpc.kcovar(blk, order)

  @p(("blk", "order"), covars_value_error_cases)
  def test_covar_kcovar_value_error_scenario(self, blk, order):
    for name in ("covar", "kcovar"):
      with pytest.raises(ValueError):
        lpc[name](blk, order)

  @p(("blk", "order"), kcovar_value_error_cases)
  def test_kcovar_value_error_scenario_invalid_coeffs(self, blk, order):
    with pytest.raises(ValueError):
      lpc.kcovar(blk, order)

    # Filter should not be stable
    filt = lpc.covar(blk, order)
    try:
      assert not parcor_stable(1 / filt)

    # See if a PARCOR is "almost one" (stability test isn't "stable")
    except AssertionError:
      assert max(xmap(abs, parcor(filt))) + 1e-7 > 1.

  @p(("blk", "order"), kcovar_valid_cases)
  def test_equalness_covar_kcovar_valid_scenario(self, blk, order):
    # Common case, tests whether all solutions are the same
    strategy_names = ("covar", "kcovar")
    filts = [lpc[name](blk, order) for name in strategy_names]
    f1, f2 = filts
    assert almost_eq(f1, f2) # But filter comparison don't include errors
    try:
      assert almost_eq(f1.error, f2.error)
    except AssertionError: # Near zero? Try again with absolute value
      max_diff = 1e-10 * min(abs(x) for x in f1.numerator + f2.numerator
                                    if x != 0)
      assert almost_eq.diff(f1.error, f2.error, max_diff=max_diff)
      assert almost_eq.diff(f1.error, 0, max_diff=max_diff)
      assert almost_eq.diff(0, f2.error, max_diff=max_diff)
    assert f1.error >= 0.
    assert f2.error >= 0.

  @p("strategy", [lpc.autocor, lpc.kautocor, lpc.nautocor])
  def test_docstring_in_all_autocor_strategies(self, strategy):
    data = [-1, 0, 1, 0] * 4
    filt = strategy(data, 2)
    assert almost_eq(filt, 1 + 0.875 * z ** -2)
    assert almost_eq.diff(filt.numerator, [1, 0., .875])
    assert almost_eq(filt.error, 1.875)


class TestParcorStableLSFStable(object):

  @p("filt", [ZFilter(1),
              1 / (1 - .5 * z ** -1),
              1 / (1 + .5 * z ** -1),
             ])
  def test_stable_filters(self, filt):
    assert parcor_stable(filt)
    assert lsf_stable(filt)

  @p("filt", [z ** -1 / (1 - z ** -1),
              1 / (1 + z ** -1),
              z ** -2 / (1 - z ** -2),
              1 / (1 - 1.2 * z ** -1),
             ])
  def test_unstable_filters(self, filt):
    assert not parcor_stable(filt)
    assert not lsf_stable(filt)


class TestParcor(object):

  filt_e4 = (1 - 0.6752 * z ** -1) * \
            (1 - 1.6077 * z ** -1 + 0.8889 * z ** -2) * \
            (1 - 1.3333 * z ** -1 + 0.8889 * z ** -2) * \
            (1 + 0.4232 * z ** -1 + 0.8217 * z ** -2) * \
            (1 + 1.6750 * z ** -1 + 0.8217 * z ** -2)

  def test_parcor_filt_e4(self):
    parcor_calculated = list(parcor(self.filt_e4))
    assert reduce(operator.mul, (1. / (1. - k ** 2)
                                 for k in parcor_calculated))
    parcor_coeff = [-0.8017212633, 0.912314348674, 0.0262174844236,
                    -0.16162324325, 0.0530245390264, 0.110480347197,
                    0.258134095686, 0.297257621307, -0.360217510101]
    assert almost_eq(parcor_calculated[::-1], parcor_coeff)
    assert parcor_stable(1 / self.filt_e4)


class TestLSF(object):

  filt_e4 = TestParcor.filt_e4

  def test_lsf_filt_e4(self):
    lsf_values_alternated = [-2.76679191844, -2.5285195589, -1.88933753141,
      -1.72283612758, -1.05267495205, -0.798045657668, -0.686406969195,
      -0.554578828901, -0.417528956381, 0.0, 0.417528956381, 0.554578828901,
      0.686406969195, 0.798045657668, 1.05267495205, 1.72283612758,
      1.88933753141, 2.5285195589, 2.76679191844, 3.14159265359]
    assert almost_eq(lsf(self.filt_e4), lsf_values_alternated)
    assert lsf_stable(1 / self.filt_e4)


class TestLevinsonDurbin(object):

  def test_one_five_three(self):
    acdata = [1, 5, 3]
    filt = levinson_durbin(acdata)
    assert almost_eq(filt, 1 - 5./12. * z ** -1 - 11./12. * z ** -2)
    err = (1 - (11./12.) ** 2) * (1 - 5 ** 2)
    assert almost_eq(filt.error, err) # Unstable filter, error is invalid
    assert almost_eq(tuple(parcor(filt)), (-11./12., -5.))
    assert not parcor_stable(1 / filt)
    assert not lsf_stable(1 / filt)


class TestToeplitz(object):

  table_schema = ("vect", "out_data")
  table_data = [
    ([18.2], [[18.2]]),
    ([-1, 19.1], [[-1, 19.1],
                  [19.1, -1]]),
    ([1, 2, 3], [[1, 2, 3],
                 [2, 1, 2],
                 [3, 2, 1]]),
  ]

  @p(table_schema, table_data)
  def test_mapping_io(self, vect, out_data):
    assert toeplitz(vect) == out_data

########NEW FILE########
__FILENAME__ = test_math
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Thu Nov 08 2012
# danilo [dot] bellini [at] gmail [dot] com
"""
Testing module for the lazy_math module
"""

import pytest
p = pytest.mark.parametrize

import itertools as it

# Audiolazy internal imports
from ..lazy_math import (factorial, dB10, dB20, inf, ln, log, log2, log10,
                         log1p, pi, e, absolute)
from ..lazy_misc import almost_eq


class TestLog(object):

  funcs = {ln: e, log2: 2, log10: 10,
           (lambda x: log1p(x - 1)): e}

  @p("func", list(funcs))
  def test_zero(self, func):
    assert func(0) == func(0.) == func(0 + 0.j) == -inf

  @p("func", list(funcs))
  def test_one(self, func):
    assert func(1) == func(1.) == func(1. + 0j) == 0

  @p(("func", "base"), list(funcs.items()))
  def test_minus_one(self, func, base):
    for pair in it.combinations([func(-1),
                                 func(-1.),
                                 func(-1. + 0j),
                                 1j * pi * func(e),
                                ], 2):
      assert almost_eq(*pair)

  @p("base", [-1, -.5, 0., 1.])
  def test_invalid_bases(self, base):
    for val in [-10, 0, 10, base, base*base]:
      with pytest.raises(ValueError):
        log(val, base=base)


class TestFactorial(object):

  @p(("n", "expected"), [(0, 1),
                         (1, 1),
                         (2, 2),
                         (3, 6),
                         (4, 24),
                         (5, 120),
                         (10, 3628800),
                         (14, 87178291200),
                         (29, 8841761993739701954543616000000),
                         (30, 265252859812191058636308480000000),
                         (6.0, 720),
                         (7.0, 5040)
                        ]
    )
  def test_valid_values(self, n, expected):
    assert factorial(n) == expected

  @p("n", [2.1, "7", 21j, "-8", -7.5, factorial])
  def test_non_integer(self, n):
    with pytest.raises(TypeError):
      factorial(n)

  @p("n", [-1, -2, -3, -4.0, -3.0, -factorial(30)])
  def test_negative(self, n):
    with pytest.raises(ValueError):
      factorial(n)

  @p(("n", "length"), [(2*factorial(7), 35980),
                       (factorial(8), 168187)]
    )
  def test_really_big_number_length(self, n, length):
    assert len(str(factorial(n))) == length


class TestDB10DB20(object):

  @p("func", [dB10, dB20])
  def test_zero(self, func):
    assert func(0) == -inf


class TestAbsolute(object):

  def test_absolute(self):
    assert absolute(25) == 25
    assert absolute(-2) == 2
    assert absolute(-4j) == 4.
    assert almost_eq(absolute(3 + 4j), 5)
    assert absolute([5, -12, 14j, -2j, 0]) == [5, 12, 14., 2., 0]
    assert almost_eq(absolute([1.2, -1.57e-3, -(pi ** 2), -2j,  8 - 4j]),
                     [1.2, 1.57e-3, pi ** 2, 2., 4 * 5 ** .5])

########NEW FILE########
__FILENAME__ = test_midi
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Tue Jul 31 2012
# danilo [dot] bellini [at] gmail [dot] com
"""
Testing module for the lazy_midi module
"""

import pytest
p = pytest.mark.parametrize

from random import random

# Audiolazy internal imports
from ..lazy_midi import (MIDI_A4, FREQ_A4, SEMITONE_RATIO, midi2freq,
                         str2midi, freq2midi, midi2str)
from ..lazy_misc import almost_eq
from ..lazy_compat import xzip
from ..lazy_math import inf, nan, isinf, isnan


class TestMIDI2Freq(object):
  table = [(MIDI_A4, FREQ_A4),
           (MIDI_A4 + 12, FREQ_A4 * 2),
           (MIDI_A4 + 24, FREQ_A4 * 4),
           (MIDI_A4 - 12, FREQ_A4 * .5),
           (MIDI_A4 - 24, FREQ_A4 * .25),
           (MIDI_A4 + 1, FREQ_A4 * SEMITONE_RATIO),
           (MIDI_A4 + 2, FREQ_A4 * SEMITONE_RATIO ** 2),
           (MIDI_A4 - 1, FREQ_A4 / SEMITONE_RATIO),
           (MIDI_A4 - 13, FREQ_A4 * .5 / SEMITONE_RATIO),
           (MIDI_A4 - 3, FREQ_A4 / SEMITONE_RATIO ** 3),
           (MIDI_A4 - 11, FREQ_A4 * SEMITONE_RATIO / 2),
          ]

  @p(("note", "freq"), table)
  def test_single_note(self, note, freq):
    assert almost_eq(midi2freq(note), freq)

  @p("data_type", [tuple, list])
  def test_note_list_tuple(self, data_type):
    notes, freqs = xzip(*self.table)
    assert almost_eq(midi2freq(data_type(notes)), data_type(freqs))

  invalid_table = [
    (inf, lambda x: isinf(x) and x > 0),
    (-inf, lambda x: x == 0),
    (nan, isnan),
  ]
  @p(("note", "func_result"), invalid_table)
  def test_invalid_inputs(self, note, func_result):
    assert func_result(midi2freq(note))


class TestFreq2MIDI(object):
  @p(("note", "freq"), TestMIDI2Freq.table)
  def test_single_note(self, note, freq):
    assert almost_eq(freq2midi(freq), note)

  invalid_table = [
    (inf, lambda x: isinf(x) and x > 0),
    (0, lambda x: isinf(x) and x < 0),
    (-1, isnan),
    (-inf, isnan),
    (nan, isnan),
  ]
  @p(("freq", "func_result"), invalid_table)
  def test_invalid_inputs(self, freq, func_result):
    assert func_result(freq2midi(freq))


class TestStr2MIDI(object):
  table = [("A4", MIDI_A4),
           ("A5", MIDI_A4 + 12),
           ("A3", MIDI_A4 - 12),
           ("Bb4", MIDI_A4 + 1),
           ("B4", MIDI_A4 + 2), # TestMIDI2Str.test_name_with_errors:
           ("C5", MIDI_A4 + 3), # These "go beyond" octave by a small amount
           ("C#5", MIDI_A4 + 4),
           ("Db3", MIDI_A4 - 20),
          ]

  @p(("name", "note"), table)
  def test_single_name(self, name, note):
    assert str2midi(name) == note
    assert str2midi(name.lower()) == note
    assert str2midi(name.upper()) == note
    assert str2midi("  " + name + " ") == note

  @p("data_type", [tuple, list])
  def test_name_list_tuple(self, data_type):
    names, notes = xzip(*self.table)
    assert str2midi(data_type(names)) == data_type(notes)

  def test_interrogation_input(self):
    assert isnan(str2midi("?"))


class TestMIDI2Str(object):
  @p(("name", "note"), TestStr2MIDI.table)
  def test_single_name(self, name, note):
    assert midi2str(note, sharp="#" in name) == name

  @p(("name", "note"), TestStr2MIDI.table)
  def test_name_with_errors(self, name, note):
    error = round(random() / 3 + .1, 3) # Minimum is greater than tolerance

    full_name = name + "+{}%".format("%.1f" % (error * 100))
    assert midi2str(note + error, sharp="#" in name) == full_name

    full_name = name + "-{}%".format("%.1f" % (error * 100))
    assert midi2str(note - error, sharp="#" in name) == full_name

  @p("note", [inf, -inf, nan])
  def test_interrogation_output(self, note):
    assert midi2str(note) == "?"

########NEW FILE########
__FILENAME__ = test_misc
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Tue Jul 31 2012
# danilo [dot] bellini [at] gmail [dot] com
"""
Testing module for the lazy_misc module
"""

import pytest
p = pytest.mark.parametrize

import itertools as it

# Audiolazy internal imports
from ..lazy_misc import rint, elementwise, freq2lag, lag2freq, almost_eq
from ..lazy_compat import INT_TYPES, orange, xrange


class TestRInt(object):
  table = [
    (.499, 0),
    (-.499, 0),
    (.5, 1),
    (-.5, -1),
    (1.00001e3, 1000),
    (-227.0090239, -227),
    (-12.95, -13),
  ]

  @p(("data", "expected"), table)
  def tests_from_table_default_step(self, data, expected):
    result = rint(data)
    assert isinstance(result, INT_TYPES)
    assert result == expected

  @p(("data", "expected"), table)
  @p("n", [2, 3, 10])
  def tests_from_step_n(self, data, expected, n):
    data_n, expected_n = n * data, n * expected # Inputs aren't in step n
    result = rint(data_n, step=n)
    assert isinstance(result, INT_TYPES)
    assert result == expected_n


class TestElementwise(object):
  _data = [1, 7, 9, -11, 0, .3, "ab", True, None, rint]
  @p("data", it.chain(_data, [_data], tuple(_data),
                      it.combinations_with_replacement(_data, 2))
    )
  def test_identity_with_single_and_generic_hybrid_tuple_and_list(self, data):
    f = elementwise()(lambda x: x)
    assert f(data) == data

  def test_generator_and_lazy_range_inputs(self):
    f = elementwise()(lambda x: x*2)
    fx = f(xrange(42))
    gen = (x*4 for x in xrange(42))
    fg = f(x*2 for x in xrange(42))
    assert type(fx) == type(gen)
    assert type(fg) == type(gen)
    assert list(fx) == orange(0,42*2,2)
    assert list(fg) == list(gen)


class TestConverters(object):

  def test_freq_lag_converters_are_inverses(self):
    for v in [37, 12, .5, -2, 1, .18, 4, 1e19, 2.7e-34]:
      assert freq2lag(v) == lag2freq(v)
      values = [lag2freq(freq2lag(v)), freq2lag(lag2freq(v)), v]
      for a, b in it.permutations(values, 2):
        assert almost_eq(a, b)

  def test_freq_lag_converters_with_some_values(self):
    eq = 2.506628274631
    data = {
      2.5: 2.5132741228718345,
       30: 0.20943951023931953,
        2: 3.141592653589793,
       eq: eq,
    } # This doesn't deserve to count as more than one test...
    for k, v in data.items():
      assert almost_eq(freq2lag(k), v)
      assert almost_eq(lag2freq(k), v)
      assert almost_eq(freq2lag(v), k)
      assert almost_eq(lag2freq(v), k)
      assert almost_eq(freq2lag(-k), -v)
      assert almost_eq(lag2freq(-k), -v)
      assert almost_eq(freq2lag(-v), -k)
      assert almost_eq(lag2freq(-v), -k)

########NEW FILE########
__FILENAME__ = test_poly
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Mon Oct 07 2012
# danilo [dot] bellini [at] gmail [dot] com
"""
Testing module for the lazy_poly module
"""

from __future__ import division

import pytest
p = pytest.mark.parametrize

import operator
import types
from itertools import combinations_with_replacement, combinations

# Audiolazy internal imports
from ..lazy_poly import Poly, lagrange, resample, x
from ..lazy_misc import almost_eq, blocks
from ..lazy_compat import orange, xrange
from ..lazy_math import inf
from ..lazy_filters import z
from ..lazy_itertools import count
from ..lazy_core import OpMethod
from ..lazy_stream import Stream

from . import skipper
operator.div = getattr(operator, "div", skipper("There's no operator.div"))


class TestPoly(object):
  example_data = [[1, 2, 3], [-7, 0, 3, 0, 5], [1], orange(-5, 3, -1)]

  instances = [
    Poly([1.7, 2, 3.3]),
    Poly({-2: 1, -1: 5.1, 3: 2}),
    Poly({-1.1: 1, 1.1: .5}),
  ]

  polynomials = [
    12 * x ** 2 + .5 * x + 18,
    .45 * x ** 17 + 2 * x ** 5 - x + 8,
    8 * x ** 5 + .2 * x ** 3 + .1 * x ** 2,
    42.7 * x ** 4,
    8 * x ** 3 + 3 * x ** 2 + 22.2 * x + .17,
  ]

  diff_table = [ # Pairs (polynomial, its derivative)
    (x + 2, 1),
    (Poly({0: 22}), 0),
    (Poly({}), 0),
    (x ** 2 + 2 * x + x ** -7 + x ** -.2 - 4,
     2 * x + 2 - 7 * x ** -8 - .2 * x ** -1.2),
  ]

  to_zero_inputs = [0, 0.0, False, {}, []]

  @p("data", example_data)
  def test_len_iter_from_list(self, data):
    assert len(Poly(data)) == len([k for k in data if k != 0])
    assert len(list(Poly(data).values())) == len(data)
    assert list(Poly(data).values()) == data

  def test_empty(self):
    assert len(Poly()) == 0
    assert not Poly()
    assert len(Poly([])) == 0
    assert not Poly([])

  @p(("key", "value"), [(3, 2), (7, 12), (500, 8), (0, 12), (1, 8)])
  def test_input_dict_one_item(self, key, value):
    data = {key: value}
    assert list(Poly(dict(data)).values()) == [0] * key + [value]

  def test_input_dict_three_items_and_fake_zero(self):
    data = {8: 5, 7: -1, 6: 80, 9: 0}
    polynomial = Poly(dict(data))
    assert len(polynomial) == 3

    assert list(polynomial.values()) == [0] * 6 + [80, -1, 5]
  @p("data", example_data)
  def test_output_dict(self, data):
    assert dict(Poly(data).terms()) == {k: v for k, v in enumerate(data)
                                             if v != 0}

  def test_sum(self):
    assert Poly([2, 3, 4]) + Poly([0, 5, -4, -1]) == Poly([2, 8, 0, -1])

  def test_float_sub(self):
    poly_obj = Poly([.3, 4]) - Poly() - Poly([0, 4, -4]) + Poly([.7, 0, -4])
    assert len(poly_obj) == 1
    assert almost_eq(poly_obj[0], 1)

  @p("val", instances)
  @p("div", [operator.div, operator.truediv])
  @p("den", [.1, -4e-3, 2])
  def test_int_float_div(self, val, div, den):
    assert almost_eq(div(den * val, den).terms(), val.terms())
    assert almost_eq(div(den * val, -den).terms(), (-val).terms())
    assert almost_eq(div(den * -val, den).terms(), (-val).terms())
    assert almost_eq(div(-den * val, den).terms(), (-val).terms())
    expected = Poly({k: operator.truediv(v, den) for k, v in val.terms()})
    assert almost_eq(div(val, den).terms(), expected.terms())
    assert almost_eq(div(val, -den).terms(), (-expected).terms())
    assert almost_eq(div(-val, den).terms(), (-expected).terms())
    assert almost_eq(div(-val, -den).terms(), expected.terms())

  @p("poly", instances + polynomials)
  def test_value_zero(self, poly):
    expected = ([v for k, v in poly.terms() if k == 0] + [0])[0]
    assert expected == poly(0)
    assert expected == poly(0.0)
    assert expected == poly[0]
    assert expected == poly[0.0]

  @p("poly", [Poly(v) for v in [{}, {0: 1}, {0: 0}, {0: -12.3}]])
  def test_constant_and_empty_polynomial_and_laurent(self, poly):
    assert poly.is_polynomial()
    assert poly.is_laurent()

  @p("poly", polynomials)
  def test_is_polynomial(self, poly):
    assert poly.is_polynomial()
    assert (poly + x ** 22.).is_polynomial()
    assert (poly + 8).is_polynomial()
    assert (poly * x).is_polynomial()
    assert (poly(-x) * .5).is_polynomial()
    assert (poly * .5 * x ** 2).is_polynomial()
    assert not (poly * .5 * x ** .2).is_polynomial()
    assert not (poly * x ** .5).is_polynomial()
    assert not (poly * x ** -(max(poly.terms())[0] + 1)).is_polynomial()

  @p("poly", polynomials)
  def test_is_laurent(self, poly):
    plaur = poly(x ** -1)
    assert poly.is_laurent()
    assert plaur.is_laurent()
    assert (plaur + x ** 2.).is_laurent()
    assert (plaur + 22).is_laurent()
    assert (plaur * x ** 2).is_laurent()
    assert (poly * x ** -(max(poly.terms())[0] + 1)).is_laurent()
    assert (plaur * x ** -(max(poly.terms())[0] + 1)).is_laurent()
    assert (plaur * x ** -(max(poly.terms())[0] // 2 + 1)).is_laurent()
    assert not (poly * x ** .5).is_laurent()
    assert not (poly + x ** -.2).is_laurent()

  def test_values_order_empty(self):
    poly = Poly({})
    val = poly.values()
    assert isinstance(val, types.GeneratorType)
    assert list(val) == []
    assert poly.order == 0
    assert poly.is_polynomial()
    assert poly.is_laurent()

  def test_values_order_invalid(self):
    poly = Poly({-1: 3, 1: 2})
    val = poly.values()
    with pytest.raises(AttributeError):
      next(val)
    with pytest.raises(AttributeError):
      poly.order
    assert not poly.is_polynomial()
    assert poly.is_laurent()

  @p("poly", polynomials)
  def test_values_order_valid(self, poly):
    order = max(poly.terms())[0]
    assert poly.order == order
    values = list(poly.values())
    for key, value in poly.terms():
      assert values[key] == value
      values[key] = 0
    assert values == [0] * (order + 1)

  @p("poly", polynomials)
  @p("zero", to_zero_inputs)
  def test_values_order_valid_with_zero(self, poly, zero):
    new_poly = Poly(list(poly.values()), zero=zero)
    order = max(new_poly.terms())[0]
    assert new_poly.order == order == poly.order
    values = list(new_poly.values())
    for key, value in poly.terms():
      assert values[key] == value
      values[key] = zero
    assert values == [zero] * (order + 1)

  @p(("poly", "diff_poly"), diff_table)
  def test_diff(self, poly, diff_poly):
    assert poly.diff() == diff_poly

  @p(("poly", "diff_poly"), diff_table)
  def test_integrate(self, poly, diff_poly):
    if not isinstance(diff_poly, Poly):
      diff_poly = Poly(diff_poly)
    integ = diff_poly.integrate()
    poly = poly - poly[0] # Removes the constant
    assert almost_eq(integ.terms(), poly.terms())

  @p("poly", polynomials + [0])
  def test_integrate_error(self, poly):
    if not isinstance(poly, Poly):
      poly = Poly(poly)
    if poly[-1] == 0: # Ensure polynomial has the problematic term
      poly = poly + x ** -1
    with pytest.raises(ValueError):
      print(poly)
      poly.integrate()
      print(poly.integrate())

  def test_empty_comparison_to_zero(self):
    inputs = [[], {}, [0, 0], [0], {25: 0}, {0: 0}, {-.2: 0}]
    values = [0, 0.] + [Poly(k) for k in inputs]
    for a, b in combinations_with_replacement(values, 2):
      assert a == b

  @p("input_data", [[], {}, [0, 0], [0], {25: 0}, {0: 0}, {-.2: 0}])
  def test_empty_polynomial_evaluation(self, input_data):
    poly = Poly(input_data)
    assert poly(5) == poly(0) == poly(-3) == poly(.2) == poly(None) == 0
    for zero in self.to_zero_inputs:
      poly = Poly(input_data, zero=zero)
      assert poly(5) is zero
      assert poly(0) is zero
      assert poly(-3) is zero
      assert poly(.2) is zero
      assert poly(None) is zero

  def test_not_equal(self):
    for a, b in combinations(self.polynomials, 2):
      assert a != b

  @p("op", OpMethod.get("+ - *"))
  @p("zero", to_zero_inputs)
  def test_operators_with_poly_input_keeping_zero(self, op, zero):
    if op.rev: # Testing binary reversed
      for p0, p1 in combinations_with_replacement(self.polynomials, 2):
        p0 = Poly(p0)
        p1 = Poly(p1, zero)
        result = getattr(p0, op.dname)(p1)
        assert isinstance(result, Poly)
        assert result.zero == 0
        result = getattr(p1, op.dname)(p0)
        assert isinstance(result, Poly)
        assert result.zero is zero
    elif op.arity == 2: # Testing binary
      for p0, p1 in combinations_with_replacement(self.polynomials, 2):
        p0 = Poly(p0)
        p1 = Poly(p1, zero)
        result = op.func(p0, p1)
        assert isinstance(result, Poly)
        assert result.zero == 0
        result = op.func(Poly(p1), p0) # Should keep
        assert isinstance(result, Poly)
        assert result.zero is zero
    else: # Testing unary
      for poly in self.polynomials:
        poly = Poly(poly, zero)
        result = op.func(poly)
        assert isinstance(result, Poly)
        assert result.zero is zero

  @p("op", OpMethod.get("pow truediv"))
  @p("zero", to_zero_inputs)
  def test_pow_truediv_keeping_zero(self, op, zero):
    values = [Poly(2), Poly(1, zero=[]), 3]
    values += [0, Poly()] if op.name == "pow" else [.3, -1.4]
    for value in values:
      for poly in self.polynomials:
        poly = Poly(poly, zero)
        result = op.func(poly, value)
        assert isinstance(result, Poly)
        assert result.zero is zero

  def test_pow_raise(self):
    with pytest.raises(NotImplementedError):
      (x + 2) ** (.5 + x ** -1)
    with pytest.raises(NotImplementedError):
      (x ** -1 + 2) ** (2 * x)
    with pytest.raises(TypeError):
      2 ** (2 * x)

  def test_truediv_raise(self): # In Python 2 div == truediv due to OpMethod
    with pytest.raises(NotImplementedError):
      (x + 2) / (.5 + x ** -1)
    with pytest.raises(NotImplementedError):
      (x ** -1 + 2) / (7 + 2 * x)
    with pytest.raises(TypeError):
      2 / (2 * x) # Would be "__rdiv__" in Python 2, anyway it should raise

  def test_truediv_zero_division_error(self):
    with pytest.raises(ZeroDivisionError):
      x ** 5 / (0 * x)
    with pytest.raises(ZeroDivisionError):
      (2 + x ** 1.1) / (0 * x)
    with pytest.raises(ZeroDivisionError):
      (x ** -31 + 7) / 0.

  @p("zero", to_zero_inputs)
  @p("method", ["diff", "integrate"])
  def test_eq_ne_diff_integrate_keep_zero(self, zero, method):
    if method == "diff":
      expected = Poly([3, 4])
    else:
      expected = Poly([0., 4, 1.5, 2./3])
    result = getattr(Poly([4, 3, 2], zero=zero), method)()
    if zero == 0:
      assert result == expected
    else:
      assert result != expected
    assert almost_eq(result.terms(), expected.terms())
    assert result == Poly(expected, zero=zero)
    assert result.zero is zero

  @p("op", OpMethod.get("pow truediv"))
  @p("zero", to_zero_inputs)
  def test_pow_truediv_from_empty_poly_instance(self, op, zero):
    empty = Poly(zero=zero)
    result = op.func(empty, 2)
    assert result == empty
    assert result != Poly(zero=op)
    assert len(result) == 0
    assert result.zero is zero

  @p("data", example_data)
  @p("poly", polynomials + [x + 5 * x ** 2 + 2])
  def test_stream_evaluation(self, data, poly):
    result = poly(Stream(data))
    assert isinstance(result, Stream)
    result = list(result)
    assert len(result) == len(data)
    assert result == [poly(k) for k in data]

  def test_stream_coeffs_with_integer(self): # Poly before to avoid casting
    poly = x * Stream(0, 2, 3) + x ** 2 * Stream(4, 1) + 8 # Order matters!
    assert str(poly) == "8 + a1 * x + a2 * x^2"
    result = poly(5)
    assert isinstance(result, Stream)
    expected = 5 * Stream(0, 2, 3) + 25 * Stream(4, 1) + 8
    assert all(expected.limit(50) == result.limit(50))

  def test_stream_coeffs_purely_stream(self): # Poly before to avoid casting
    poly = x * Stream(0, 2, 3) + x ** 2 * Stream(4, 1) + Stream(2, 2, 2, 2, 5)
    assert str(poly) == "a0 + a1 * x + a2 * x^2"
    result = poly(count())
    assert isinstance(result, Stream)
    expected = (count() * Stream(0, 2, 3) + count() ** 2 * Stream(4, 1) +
                Stream(2, 2, 2, 2, 5))
    assert all(expected.limit(50) == result.limit(50))

  def test_stream_coeffs_mul(self):
    poly1 = x * Stream(0, 1, 2) + 5 # Order matters
    poly2 = x ** 2 * count() - 2
    poly = poly1 * poly2
    result = poly(Stream(4, 3, 7, 5, 8))
    assert isinstance(result, Stream)
    expected = (Stream(4, 3, 7, 5, 8) ** 3 * Stream(0, 1, 2) * count()
                + Stream(4, 3, 7, 5, 8) ** 2 * 5 * count()
                - Stream(4, 3, 7, 5, 8) * Stream(0, 1, 2) * 2
                - 10
               )
    assert all(expected.limit(50) == result.limit(50))

  @p("zero", to_zero_inputs)
  def test_stream_coeffs_add_copy_with_zero(self, zero):
    poly = x * Stream(0, 4, 2, 3, 1)
    new_poly = 3 * poly.copy(zero=zero)
    new_poly += poly
    assert isinstance(new_poly, Poly)
    assert new_poly.zero is zero
    result = new_poly(Stream(1, 2, 3, 0, 4, 7, -2))
    assert isinstance(result, Stream)
    expected = 4 * Stream(1, 2, 3, 0, 4, 7, -2) * Stream(0, 4, 2, 3, 1)
    assert all(expected.limit(50) == result.limit(50))

  @p("zero", to_zero_inputs)
  def test_stream_coeffs_mul_copy_with_zero(self, zero):
    poly = x ** 2 * Stream(3, 2, 1) + 2 * count() + x ** -3
    new_poly = poly.copy(zero=zero)
    new_poly *= poly + 1
    assert isinstance(new_poly, Poly)
    assert new_poly.zero is zero
    result = new_poly(count(18) ** .5)
    assert isinstance(result, Stream)
    expected = (count(18) * Stream(3, 2, 1)
                + 2 * count() + count(18) ** -1.5
               ) * (count(18) * Stream(3, 2, 1)
                + 2 * count() + count(18) ** -1.5 + 1
               )
    assert almost_eq(expected.limit(50), result.limit(50))

  def test_eq_ne_of_a_stream_copy(self):
    poly = x * Stream(0, 1)
    new_poly = poly.copy()
    assert poly == poly
    assert poly != new_poly
    assert new_poly == new_poly
    other_poly = poly.copy(zero=[])
    assert new_poly != other_poly
    assert new_poly.zero != other_poly.zero

  @p("poly", polynomials)
  def test_pow_basics(self, poly):
    assert poly ** 0 == 1
    assert poly ** Poly() == 1
    assert poly ** 1 == poly
    assert poly ** 2 == poly * poly
    assert poly ** Poly(2) == poly * poly
    assert almost_eq((poly ** 3).terms(), (poly * poly * poly).terms())

  def test_power_one_keep_integer(self):
    for value in [0, -1, .5, 18]:
      poly = Poly(1) ** value
      assert poly.order == 0
      assert poly[0] == 1
      assert isinstance(poly[0], int)

  @p("zero", to_zero_inputs)
  def test_pow_with_stream_coeff(self, zero):
    poly = Poly(x ** -2 * Stream(1, 0) + 2, zero=zero)
    new_poly = poly ** 2
    assert isinstance(new_poly, Poly)
    assert new_poly.zero is zero
    result = new_poly(count(1))
    assert isinstance(result, Stream)
    expected = (count(1) ** -4 * Stream(1, 0)
                + 4 * count(1) ** -2 * Stream(1, 0)
                + 4
               )
    assert almost_eq(expected.limit(50), result.limit(50))

  @p("zero", to_zero_inputs)
  def test_truediv_by_stream(self, zero):
    poly = Poly(x ** .5 * Stream(.2, .4) + 7, zero=zero)
    new_poly = poly / count(2, 4)
    assert isinstance(new_poly, Poly)
    assert new_poly.zero is zero
    result = new_poly(Stream(17, .2, .1, 0, .2, .5, 99))
    assert isinstance(result, Stream)
    expected = (Stream(17, .2, .1, 0, .2, .5, 99) ** .5 * Stream(.2, .4) + 7
               ) / count(2, 4)
    assert almost_eq(expected.limit(50), result.limit(50))

  def test_setitem(self):
    poly = x + 2
    poly[3] = 5
    assert poly == 5 * x ** 3 + x + 2
    poly[.2] = 1
    assert poly == 5 * x ** 3 + x + 2 + x ** .2
    var_coeff = Stream(1, 2, 3)
    poly[0] = var_coeff
    term_iter = poly.terms()
    power, item = next(term_iter)
    assert item is var_coeff
    assert power == 0
    assert Poly(dict(term_iter)) == 5 * x ** 3 + x + x ** .2

  def test_hash(self):
    poly = x + 1
    poly[3] = 1
    my_set = {poly, 27, x}
    with pytest.raises(TypeError):
      poly[3] = 0
    assert poly == x ** 3 + x + 1
    assert poly in my_set


class TestLagrange(object):

  values = [-5, 0, 14, .17]

  @p("v0", values)
  @p("v1", values)
  def test_linear_func(self, v0, v1):
    for k in [0, v0, v1]:
      pairs = [(1 + k, v0), (-1 + k, v1)]
      for interpolator in [lagrange(pairs), lagrange(reversed(pairs))]:
        assert isinstance(interpolator, types.LambdaType)
        assert almost_eq(interpolator(k), v0 * .5 + v1 * .5)
        assert almost_eq(interpolator(3 + k), v0 * 2 - v1)
        assert almost_eq(interpolator(.5 + k), v0 * .75 + v1 * .25)
        assert almost_eq(interpolator(k - .5), v0 * .25 + v1 * .75)

  @p("v0", values)
  @p("v1", values)
  def test_linear_poly(self, v0, v1):
    for k in [0, v0, v1]:
      pairs = [(1 + k, v0), (-1 + k, v1)]
      for interpolator in [lagrange.poly(pairs),
                           lagrange.poly(reversed(pairs))]:
        expected = Poly([v0 - (1 + k) * (v0 - v1) * .5, (v0 - v1) * .5])
        assert almost_eq(interpolator.values(), expected.values())

  @p("v0", values)
  @p("v1", values)
  def test_parabola_poly(self, v0, v1):
    pairs = [(0, v0), (1, v1), (v1 + .2, 0)]
    r = v1 + .2
    a = (v0 + r *(v1 - v0)) / (r * (1 - r))
    b = v1 - v0 - a
    c = v0
    expected = a * x ** 2 + b * x + c
    for interpolator in [lagrange.poly(pairs),
                         lagrange.poly(pairs[1:] + pairs[:1]),
                         lagrange.poly(reversed(pairs))]:
      assert almost_eq(interpolator.values(), expected.values())

  data = [.12, .22, -15, .7, 18, 227, .1, 4, 0, -9e3, 1, 18, 1e-4,
          44, 3, 8.00000004, 27]

  @p("poly", TestPoly.polynomials)
  def test_recover_poly_from_samples(self, poly):
    expected = list(poly.values())
    size = len(expected)
    for seq in blocks(self.data, size=size, hop=1):
      pairs = [(k, poly(k)) for k in seq]
      interpolator = lagrange.poly(pairs)
      assert almost_eq.diff(expected, interpolator.values())


class TestResample(object):

  def test_simple_downsample(self):
    data = [1, 2, 3, 4, 5]
    resampled = resample(data, old=1, new=.5, order=1)
    assert resampled.take(20) == [1, 3, 5]

  def test_simple_upsample_linear(self):
    data = [1, 2, 3, 4, 5]
    resampled = resample(data, old=1, new=2, order=1)
    expected = [1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5]
    assert almost_eq(resampled.take(20), expected)

  def test_simple_upsample_linear_time_varying(self):
    acc = 1 / (1 - z ** -1)
    data = resample(xrange(50), old=1, new=1 + count() / 10, order=1)
    assert data.take() == 0.
    result = data.take(inf)
    expected = acc(1 / (1 + count() / 10))
    assert almost_eq(result, expected.limit(len(result)))

########NEW FILE########
__FILENAME__ = test_stream
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Tue Jul 31 2012
# danilo [dot] bellini [at] gmail [dot] com
"""
Testing module for the lazy_stream module
"""

import pytest
p = pytest.mark.parametrize

import itertools as it
import operator
import warnings
from collections import deque

# Audiolazy internal imports
from ..lazy_stream import Stream, thub, MemoryLeakWarning, StreamTeeHub
from ..lazy_misc import almost_eq
from ..lazy_compat import orange, xrange, xzip, xmap, xfilter, NEXT_NAME
from ..lazy_math import inf, nan, pi

from . import skipper
operator.div = getattr(operator, "div", skipper("There's no operator.div"))


class TestStream(object):

  def test_no_args(self):
    with pytest.raises(TypeError):
      Stream()

  @p("is_iter", [True, False])
  @p("list_", [orange(5), [], [None, Stream, almost_eq, 2.4], [1, "a", 4]])
  def test_from_list(self, list_, is_iter):
    assert list(Stream(iter(list_) if is_iter else list_)) == list_

  @p("tuple_input",[("strange", "tuple with list as fill value".split()),
                    (1,), tuple(), ("abc", [12,15], 8j)]
    )
  def test_from_tuple(self, tuple_input):
    assert tuple(Stream(tuple_input)) == tuple_input

  @p("value", [0, 1, 17, 200])
  def test_lazy_range(self, value):
    assert list(Stream(xrange(value))) == orange(value)

  def test_class_docstring(self):
    x = Stream(it.count())
    y = Stream(3)
    z = 2*x + y
    assert z.take(8) == [3, 5, 7, 9, 11, 13, 15, 17]

  def test_mixed_inputs(self):
    with pytest.raises(TypeError):
      Stream([1, 2, 3], 5)

  @p("d2_type", [list, tuple, Stream])
  @p("d1_iter", [True, False])
  @p("d2_iter", [True, False])
  def test_multiple_inputs_iterable_iterator(self, d2_type, d1_iter, d2_iter):
    data1 = [1, "a", 4]
    data2 = d2_type([7.5, "abc", "abd", 9, it.chain])
    d2copy = data2.copy() if isinstance(data2, Stream) else data2
    data =  [iter(data1) if d1_iter else data1]
    data += [iter(data2) if d2_iter else data2]
    stream_based = Stream(*data)
    it_based = it.chain(data1, d2copy)
    assert list(stream_based) == list(it_based) # No math/casting with float

  def test_non_iterable_input(self):
    data = 25
    for idx, x in xzip(xrange(15), Stream(data)): # Enumerate wouldn't finish
      assert x == data

  def test_multiple_non_iterable_input(self):
    data = [2j+3, 7.5, 75, type(2), Stream]
    for si, di in xzip(Stream(*data), data * 4):
      assert si == di

  def test_init_docstring_finite(self):
    x = Stream([1, 2, 3]) + Stream([8, 5])
    assert list(x) == [9, 7]

  def test_init_docstring_endless(self):
    x = Stream(1,2,3) + Stream(8,5)
    assert x.take(6) == [9, 7, 11, 6, 10, 8]
    assert x.take(6) == [9, 7, 11, 6, 10, 8]
    assert x.take(3) == [9, 7, 11]
    assert x.take(5) == [6, 10, 8, 9, 7]
    assert x.take(15) == [11, 6, 10, 8, 9, 7, 11, 6, 10, 8, 9, 7, 11, 6, 10]

  def test_copy(self):
    a = Stream([1,2,3])
    b = Stream([8,5])
    c = a.copy()
    d = b.copy()
    assert type(a) == type(c)
    assert type(b) == type(d)
    assert id(a) != id(c)
    assert id(b) != id(d)
    assert iter(a) != iter(c)
    assert iter(b) != iter(d)
    assert list(a) == [1,2,3]
    assert list(c) == [1,2,3]
    assert b.take() == 8
    assert d.take() == 8
    assert b.take() == 5
    assert d.take() == 5
    with pytest.raises(StopIteration):
      b.take()
    with pytest.raises(StopIteration):
      d.take()

  @p(("stream_size", "hop", "block_size"), [(48, 11, 15),
                                            (12, 13, 13),
                                            (42, 5, 22),
                                            (72, 14, 3),
                                            (7, 7, 7),
                                            (12, 8, 8),
                                            (12, 1, 5)]
    )
  def test_blocks(self, stream_size, hop, block_size):
    data = Stream(xrange(stream_size))
    data_copy = data.copy()
    myblocks = data.blocks(size=block_size,
                           hop=hop) # Shouldn't use "data" anymore
    myblocks_rev = Stream(reversed(list(data_copy))).blocks(size=block_size,
                                                            hop=hop)
    for idx, (x, y) in enumerate(xzip(myblocks, myblocks_rev)):
      assert len(x) == block_size
      assert len(y) == block_size
      startx = idx * hop
      stopx = startx + block_size
      desiredx = [(k if k < stream_size else 0.)\
                   for k in xrange(startx,stopx)]
      assert list(x) == desiredx
      starty = stream_size - 1 - startx
      stopy = stream_size - 1 - stopx
      desiredy = [max(k,0.) for k in xrange(starty, stopy, -1)]
      assert list(y) == desiredy

  def test_unary_operators_and_binary_pow_xor(self):
    a = +Stream([1, 2, 3])
    b = -Stream([8, 5, 2, 17])
    c = Stream(True) ^ Stream([True, False, None]) # xor
    d = b ** a
    assert d.take(3) == [-8,25,-8]
    with pytest.raises(StopIteration):
      d.take()
    assert c.take(2) == [False, True]
    # TypeError: unsupported operand type(s) for ^: 'bool' and 'NoneType'
    with pytest.raises(TypeError):
      c.take()

  def test_getattr_with_methods_and_equalness_operator(self):
    data = "trying again with strings...a bizarre iterable"
    a = Stream(data)
    b = a.copy()
    c = Stream("trying again ", xrange(5), "string", "."*4)
    d = [True for _ in "trying again "] + \
        [False for _ in xrange(5)] + \
        [True for _ in "string"] + \
        [False, True, True, True]
    assert list(a == c) == d
    assert "".join(list(b.upper())) == data.upper()

  def test_getattr_with_non_callable_attributes(self):
           #[(-2+1j), (40+24j), (3+1j), (-3+5j), (8+16j), (8-2j)]
    data = Stream(1 + 2j, 5 + 3j) * Stream(1j, 8, 1 - 1j)
    real = Stream(-2, 40, 3, -3, 8, 8)
    imag = Stream(1, 24, 1, 5, 16, -2)
    assert data.copy().real.take(6) == real.copy().take(6)
    assert data.copy().imag.take(6) == imag.copy().take(6)
    sum_data = data.copy().real + data.copy().imag
    assert sum_data.take(6) == (real + imag).take(6)

  def test_no_boolean(self):
    with pytest.raises(TypeError):
      bool(Stream(xrange(2)))

  @p("op", [operator.div, operator.truediv])
  def test_div_truediv(self, op):
    input1 = [1, 5, 7., 3.3]
    input2 = [9.2, 10, 11, 4.9]
    data = op(Stream(input1), Stream(input2))
    expected = [operator.truediv(x, y) for x, y in xzip(input1, input2)]
    assert isinstance(data, Stream)
    assert list(data) == expected

  def test_next(self):
    """ Streams should have no "next" method! """
    assert not hasattr(Stream(2), NEXT_NAME)

  def test_peek_take(self):
    data = Stream([1, 4, 3, 2])
    assert data.peek(3) == [1, 4, 3]
    assert data.peek() == 1
    assert data.take() == 1
    assert data.peek() == 4
    assert data.peek(3) == [4, 3, 2]
    assert data.peek() == 4
    assert data.take() == 4
    assert data.peek(3) == [3, 2]
    assert data.peek(3, tuple) == (3, 2)
    assert data.peek(inf, tuple) == (3, 2)
    assert data.take(inf, tuple) == (3, 2)
    assert data.peek(1) == []
    assert data.take(1) == []
    assert data.take(inf) == []
    assert Stream([1, 4, 3, 2]).take(inf) == [1, 4, 3, 2]
    with pytest.raises(StopIteration):
      data.peek()
    with pytest.raises(StopIteration):
      data.take()

  def test_skip_periodic_data(self):
    data = Stream(5, Stream, .2)
    assert data.skip(1).peek(4) == [Stream, .2, 5, Stream]
    assert data.peek(4) == [Stream, .2, 5, Stream]
    assert data.skip(3).peek(4) == [Stream, .2, 5, Stream]
    assert data.peek(4) == [Stream, .2, 5, Stream]
    assert data.skip(2).peek(4) == [5, Stream, .2, 5]
    assert data.peek(4) == [5, Stream, .2, 5]

  def test_skip_finite_data(self):
    data = Stream(xrange(25))
    data2 = data.copy()
    assert data.skip(4).peek(4) == [4, 5, 6, 7]
    assert data2.peek(4) == [0, 1, 2, 3]
    assert data2.skip(30).peek(4) == []

  def test_skip_laziness(self):
    memory = {"last": 0}
    def tg():
      while True:
        memory["last"] += 1
        yield memory["last"]

    data = Stream(tg())
    assert data.take(3) == [1, 2, 3]
    data.skip(7)
    assert memory["last"] == 3
    assert data.take() == 11
    assert memory["last"] == 11

  def test_limit_from_beginning_from_finite_stream(self):
    assert Stream(xrange(25)).limit(10).take(inf) == orange(10)
    assert Stream(xrange(25)).limit(40).take(inf) == orange(25)
    assert Stream(xrange(25)).limit(24).take(inf) == orange(24)
    assert Stream(xrange(25)).limit(25).take(inf) == orange(25)
    assert Stream(xrange(25)).limit(26).take(inf) == orange(25)

  def test_limit_with_skip_from_finite_stream(self):
    assert Stream(xrange(45)).skip(2).limit(13).take(inf) == orange(2, 15)
    assert Stream(xrange(45)).limit(13).skip(3).take(inf) == orange(3, 13)

  @p("noise", [-.3, 0, .1])
  def test_limit_from_periodic_stream(self, noise):
    assert Stream(0, 1, 2).limit(7 + noise).peek(10) == [0, 1, 2, 0, 1, 2, 0]
    data = Stream(-1, .2, it)
    assert data.skip(2).limit(9 + noise).peek(15) == [it, -1, .2] * 3

  @p("noise", [-.3, 0., .1])
  def test_take_peek_skip_with_float(self, noise):
    data = [1.2, 7.7, 1e-3, 1e-17, 2e8, 27.1, 14.003, 1.0001, 7.3e5, 0.]
    ds = Stream(data)
    assert ds.limit(5 + noise).peek(10 - noise) == data[:5]
    assert ds.skip(1 + noise).limit(3 - noise).peek(10 + noise) == data[1:4]
    ds = Stream(data)
    assert ds.skip(2 + noise).peek(20 + noise) == data[2:]
    assert ds.skip(3 - noise).peek(20 - noise) == data[5:]
    assert ds.skip(4 + noise).peek(1 + noise) == [data[9]]
    ds = Stream(data)
    assert ds.skip(4 - noise).peek(2 - noise) == data[4:6]
    assert ds.skip(1 - noise).take(2 + noise) == data[5:7]
    assert ds.peek(inf) == data[7:]
    assert ds.take(inf) == data[7:]

  def test_take_peek_inf(self):
    data = list(xrange(30))
    ds1 = Stream(data)
    ds1.take(3)
    assert ds1.peek(inf) == data[3:]
    assert ds1.take(inf) == data[3:]
    ds2 = Stream(data)
    ds2.take(4)
    assert ds2.peek(inf * 2e-18) == data[4:] # Positive float
    assert ds2.take(inf * 1e-25) == data[4:]
    ds3 = Stream(data)
    ds3.take(1)
    assert ds3.peek(inf * 43) == data[1:] # Positive int
    assert ds3.take(inf * 200) == data[1:]

  def test_take_peek_nan(self):
    for dur in [nan, nan * 23, nan * -5, nan * .3, nan * -.18, nan * 0]:
      assert Stream(29).take(dur) == []
      assert Stream([23]).peek(dur) == []

  def test_take_peek_negative_or_zero(self):
    for dur in [-inf, inf * -1e-16, -1, -2, -.18, 0, 0., -0.]:
      assert Stream(1, 2, 3).take(dur) == []
      assert Stream(-1, -23).peek(dur) == []

  def test_take_peek_not_int_nor_float(self):
    for dur in [Stream, it, [], (2, 3), 3j]:
      with pytest.raises(TypeError):
        Stream([]).take(dur)
      with pytest.raises(TypeError):
        Stream([128]).peek(dur)

  def test_take_peek_none(self):
    data = Stream([Stream, it, [], (2, 3), 3j])
    assert data.peek() is Stream
    assert data.take() is Stream
    assert data.peek() is it
    assert data.take() is it
    assert data.peek() == []
    assert data.take() == []
    assert data.peek() == (2, 3)
    assert data.take() == (2, 3)
    assert data.peek() == 3j
    assert data.take() == 3j
    with pytest.raises(StopIteration):
      data.peek()
    with pytest.raises(StopIteration):
      data.take()

  @p("constructor", [list, tuple, set, deque])
  def test_take_peek_constructor(self, constructor):
    ds = Stream([1, 2, 3] * 12)
    assert ds.peek(constructor=constructor) == 1
    assert ds.take(constructor=constructor) == 1
    assert ds.peek(constructor=constructor) == 2
    assert ds.take(constructor=constructor) == 2
    assert ds.peek(3, constructor=constructor) == constructor([3, 1, 2])
    assert ds.take(4, constructor=constructor) == constructor([3, 1, 2, 3])
    remain = constructor([1, 2, 3] * 10)
    assert ds.peek(inf, constructor=constructor) == remain
    assert ds.take(inf, constructor=constructor) == remain
    assert ds.peek(3, constructor=constructor) == constructor()
    assert ds.take(5, constructor=constructor) == constructor()

  def test_abs_step_by_step(self):
    data = [-1, 5, 2 + 3j, 8, -.7]
    ds = abs(Stream(data))
    assert isinstance(ds, Stream)
    assert ds.take(len(data)) == [abs(el) for el in data]
    assert ds.take(1) == [] # Finished

  def test_abs_take_peek(self):
    assert abs(Stream([])).peek(9) == [] # From empty Stream
    assert abs(Stream([5, -12, 14j, -2j, 0])).take(inf) == [5, 12, 14., 2., 0]
    data = abs(Stream([1.2, -1.57e-3, -(pi ** 2), -2j,  8 - 4j]))
    assert almost_eq(data.peek(inf), [1.2, 1.57e-3, pi ** 2, 2., 4 * 5 ** .5])
    assert data.take() == 1.2
    assert almost_eq(data.take(), 1.57e-3)


class TestEveryMapFilter(object):
  """
  Tests Stream.map, Stream.filter, StreamTeeHub.map, StreamTeeHub.filter,
  lazy_itertools.imap and lazy_itertools.ifilter (map and filter in Python 3)
  """

  map_filter_data = [orange(5), orange(9, 0, -2), [7, 22, -5], [8., 3., 15.],
                     orange(20,40,3)]

  @p("data", map_filter_data)
  @p("func", [lambda x: x ** 2, lambda x: x // 2, lambda x: 18])
  def test_map(self, data, func):
    expected = [func(x) for x in data]
    assert list(Stream(data).map(func)) == expected
    assert list(xmap(func, data)) == expected # Tests the test...
    dt = thub(data, 2)
    assert isinstance(dt, StreamTeeHub)
    dt_data = dt.map(func)
    assert isinstance(dt_data, Stream)
    assert dt_data.take(inf) == expected
    assert list(dt.map(func)) == expected # Second copy
    with pytest.raises(IndexError):
      dt.map(func)

  @p("data", map_filter_data)
  @p("func", [lambda x: x > 0, lambda x: x % 2 == 0, lambda x: False])
  def test_filter(self, data, func):
    expected = [x for x in data if func(x)]
    assert list(Stream(data).filter(func)) == expected
    assert list(xfilter(func, data)) == expected # Tests the test...
    dt = thub(data, 2)
    assert isinstance(dt, StreamTeeHub)
    dt_data = dt.filter(func)
    assert isinstance(dt_data, Stream)
    assert dt_data.take(inf) == expected
    assert list(dt.filter(func)) == expected # Second copy
    with pytest.raises(IndexError):
      dt.filter(func)


class TestThub(object):

  @p("copies", orange(5))
  @p("used_copies", orange(5))
  def test_stream_tee_hub_memory_leak_warning_and_index_error(self, copies,
                                                              used_copies):
    data = Stream(.5, 8, 7 + 2j)
    data = thub(data, copies)
    assert isinstance(data, StreamTeeHub)
    if copies < used_copies:
      with pytest.raises(IndexError):
        [data * n for n in xrange(used_copies)]
    else:
      [data * n for n in xrange(used_copies)]
      warnings.simplefilter("always")
      with warnings.catch_warnings(record=True) as warnings_list:
        data.__del__()
      if copies != used_copies:
        w = warnings_list.pop()
        assert issubclass(w.category, MemoryLeakWarning)
        assert str(copies - used_copies) in str(w.message)
      assert warnings_list == []

  def test_take_peek(self):
    data = Stream(1, 2, 3).limit(50)
    data = thub(data, 2)
    assert data.peek() == 1
    assert data.peek(.2) == []
    assert data.peek(1) == [1]
    with pytest.raises(AttributeError):
      data.take()
    assert data.peek(22) == Stream(1, 2, 3).take(22)
    assert data.peek(42.2) == Stream(1, 2, 3).take(42)
    with pytest.raises(AttributeError):
      data.take(2)
    assert data.peek(57.8) == Stream(1, 2, 3).take(50)
    assert data.peek(inf) == Stream(1, 2, 3).take(50)

  @p("noise", [-.3, 0, .1])
  def test_limit(self, noise):
    source = [.1, -.2, 18, it, Stream]
    length = len(source)
    data = Stream(*source).limit(4 * length)
    data = thub(data, 3)

    # First copy
    first_copy = data.limit(length + noise)
    assert isinstance(first_copy, Stream)
    assert not isinstance(first_copy, StreamTeeHub)
    assert list(first_copy) == source

    # Second copy
    assert data.peek(3 - noise) == source[:3]
    assert Stream(data).take(inf) == 4 * source

    # Third copy
    third_copy = data.limit(5 * length + noise)
    assert isinstance(third_copy, Stream)
    assert not isinstance(third_copy, StreamTeeHub)
    assert third_copy.take(inf) == 4 * source

    # No more copies
    assert isinstance(data, StreamTeeHub)
    with pytest.raises(IndexError):
      data.limit(3)

  @p("noise", [-.3, 0, .1])
  def test_skip_append(self, noise):
    source = [9, 14, -7, noise]
    length = len(source)
    data = Stream(*source).limit(7 * length)
    data = thub(data, 3)

    # First copy
    first_copy = data.skip(length + 1)
    assert isinstance(first_copy, Stream)
    assert not isinstance(first_copy, StreamTeeHub)
    assert first_copy is first_copy.append([8])
    assert list(first_copy) == source[1:] + 5 * source + [8]

    # Second and third copies
    assert data.skip(1 + noise).peek(3 - noise) == source[1:4]
    assert data.append([1]).skip(length - noise).take(inf) == 6 * source + [1]

    # No more copies
    assert isinstance(data, StreamTeeHub)
    with pytest.raises(IndexError):
      data.skip(1)
    with pytest.raises(IndexError):
      data.append(3)

  @p("size", [4, 5, 6])
  @p("hop", [None, 1, 5])
  def test_blocks(self, size, hop):
    copies = 8 - size
    source = Stream(7, 8, 9, -1, -1, -1, -1).take(40)
    data = thub(source, copies)
    expected = list(Stream(source).blocks(size=size, hop=hop).map(list))
    for _ in xrange(copies):
      blks = data.blocks(size=size, hop=hop).map(list)
      assert isinstance(blks, Stream)
      assert not isinstance(blks, StreamTeeHub)
      assert blks.take(inf) == expected
    with pytest.raises(IndexError):
      data.blocks(size=size, hop=hop)

########NEW FILE########
__FILENAME__ = test_synth
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Tue Jul 31 2012
# danilo [dot] bellini [at] gmail [dot] com
"""
Testing module for the lazy_synth module
"""

import pytest
p = pytest.mark.parametrize

import itertools as it

# Audiolazy internal imports
from ..lazy_synth import (modulo_counter, line, impulse, ones, zeros, zeroes,
                          white_noise, gauss_noise, TableLookup, fadein,
                          fadeout, sin_table, saw_table)
from ..lazy_stream import Stream
from ..lazy_misc import almost_eq, sHz, blocks, rint, lag2freq
from ..lazy_compat import orange, xrange, xzip
from ..lazy_itertools import count
from ..lazy_math import pi, inf


class TestLineFadeInFadeOut(object):

  def test_line(self):
    s, Hz = sHz(rate=2)
    L = line(4 * s, .1, .9)
    assert almost_eq(L, (.1 * x for x in xrange(1, 9)))

  def test_line_append(self):
    s, Hz = sHz(rate=3)
    L1 = line(2 * s, 2, 8)
    L1_should = [2, 3, 4, 5, 6, 7]
    L2 = line(1 * s, 8, -1)
    L2_should = [8, 5, 2]
    L3 = line(2 * s, -1, 9, finish=True)
    L3_should = [-1, 1, 3, 5, 7, 9]
    env = L1.append(L2).append(L3)
    env = env.map(int)
    env_should = L1_should + L2_should + L3_should
    assert list(env) == env_should

  def test_fade_in(self):
    s, Hz = sHz(rate=4)
    L = fadein(2.5 * s)
    assert almost_eq(L, (.1 * x for x in xrange(10)))

  def test_fade_out(self):
    s, Hz = sHz(rate=5)
    L = fadeout(2 * s)
    assert almost_eq(L, (.1 * x for x in xrange(10, 0, -1)))


class TestModuloCounter(object):

  def test_ints(self):
    assert modulo_counter(0, 3, 2).take(8) == [0, 2, 1, 0, 2, 1, 0, 2]

  def test_floats(self):
    assert almost_eq(modulo_counter(1., 5., 3.3).take(10),
                     [1., 4.3, 2.6, .9, 4.2, 2.5, .8, 4.1, 2.4, .7])

  def test_ints_modulo_one(self):
    assert modulo_counter(0, 1, 7).take(3) == [0, 0, 0]
    assert modulo_counter(0, 1, -1).take(4) == [0, 0, 0, 0]
    assert modulo_counter(0, 1, 0).take(5) == [0, 0, 0, 0, 0]

  def test_step_zero(self):
    assert modulo_counter(7, 5, 0).take(2) == [2] * 2
    assert modulo_counter(1, -2, 0).take(4) == [-1] * 4
    assert modulo_counter(0, 3.141592653589793, 0).take(7) == [0] * 7

  def test_streamed_step(self):
    mc = modulo_counter(5, 15, modulo_counter(0, 3, 2))
    assert mc.take(18) == [5, 5, 7, 8, 8, 10, 11, 11, 13, 14, 14, 1, 2, 2, 4,
                           5, 5, 7]

  def test_streamed_start(self):
    mc = modulo_counter(modulo_counter(2, 5, 3), 7, 1)
       # start = [2,0,3,1,4,  2,0,3,1,4,  ...]
    should_mc = (Stream(2, 0, 3, 1, 4) + count()) % 7
    assert mc.take(29) == should_mc.take(29)

  @p("step", [0, 17, -17])
  def test_streamed_start_ignorable_step(self, step):
    mc = modulo_counter(it.count(), 17, step)
    assert mc.take(30) == (orange(17) * 2)[:30]

  def test_streamed_start_and_step(self):
    mc = modulo_counter(Stream(3, 3, 2), 17, it.count())
    should_step =  [0, 0, 1, 3, 6, 10, 15-17, 21-17, 28-17, 36-34, 45-34,
                    55-51, 66-68]
    should_start = [3, 3, 2, 3, 3, 2, 3, 3, 2, 3, 3, 2, 3, 3, 2, 3]
    should_mc = [a+b for a,b in xzip(should_start, should_step)]
    assert mc.take(len(should_mc)) == should_mc

  def test_streamed_modulo(self):
    mc = modulo_counter(12, Stream(7, 5), 8)
    assert mc.take(30) == [5, 3, 4, 2, 3, 1, 2, 0, 1, 4] * 3

  def test_streamed_start_and_modulo(self):
    mc = modulo_counter(it.count(), 3 + count(), 1)
    expected = [0, 2, 4, 0, 2, 4, 6, 8, 10, 0, 2, 4, 6, 8, 10, 12,
                14, 16, 18, 20, 22, 0, 2, 4, 6, 8, 10, 12, 14, 16]
    assert mc.take(len(expected)) == expected

  def test_all_inputs_streamed(self):
    mc1 = modulo_counter(it.count(), 3 + count(), Stream(0, 1))
    mc2 = modulo_counter(0, 3 + count(), 1 + Stream(0, 1))
    expected = [0, 1, 3, 4, 6, 7, 0, 1, 3, 4, 6, 7, 9, 10, 12, 13,
                15, 16, 18, 19, 21, 22, 24, 25, 0, 1, 3, 4, 6, 7]
    assert mc1.take(len(expected)) == mc2.take(len(expected)) == expected

  classes = (float, Stream)

  @p("start", [-1e-16, -1e-100])
  @p("cstart", classes)
  @p("cmodulo", classes)
  @p("cstep", classes)
  def test_bizarre_modulo(self, start, cstart, cmodulo, cstep):
    # Not really a modulo counter issue, but used by modulo counter
    for step in xrange(2, 900):
      mc = modulo_counter(cstart(start),
                          cmodulo(step),
                          cstep(step))
      assert all(mc.limit(4) < step)

@p(("func", "data"),
   [(ones, 1.0),
    (zeros, 0.0),
    (zeroes, 0.0)
   ])
class TestOnesZerosZeroes(object):

  def test_no_input(self, func, data):
    my_stream = func()
    assert isinstance(my_stream, Stream)
    assert my_stream.take(25) == [data] * 25

  def test_inf_input(self, func, data):
    my_stream = func(inf)
    assert isinstance(my_stream, Stream)
    assert my_stream.take(30) == [data] * 30

  @p("dur", [-1, 0, .4, .5, 1, 2, 10])
  def test_finite_duration(self, func, data, dur):
    my_stream = func(dur)
    assert isinstance(my_stream, Stream)
    dur_int = max(rint(dur), 0)
    assert list(my_stream) == [data] * dur_int


class TestWhiteNoise(object):

  def test_no_input(self):
    my_stream = white_noise()
    assert isinstance(my_stream, Stream)
    for el in my_stream.take(27):
      assert -1 <= el <= 1

  @p("high", [1, 0, -.042])
  def test_inf_input(self, high):
    my_stream = white_noise(inf, high=high)
    assert isinstance(my_stream, Stream)
    for el in my_stream.take(32):
      assert -1 <= el <= high

  @p("dur", [-1, 0, .4, .5, 1, 2, 10])
  @p("low", [0, .17])
  def test_finite_duration(self, dur, low):
    my_stream = white_noise(dur, low=low)
    assert isinstance(my_stream, Stream)
    dur_int = max(rint(dur), 0)
    my_list = list(my_stream)
    assert len(my_list) == dur_int
    for el in my_list:
      assert low <= el <= 1


class TestGaussNoise(object):

  def test_no_input(self):
    my_stream = gauss_noise()
    assert isinstance(my_stream, Stream)
    assert len(my_stream.take(100)) == 100

  def test_inf_input(self):
    my_stream = gauss_noise(inf)
    assert isinstance(my_stream, Stream)
    assert len(my_stream.take(100)) == 100

  @p("dur", [-1, 0, .4, .5, 1, 2, 10])
  def test_finite_duration(self, dur):
    my_stream = gauss_noise(dur)
    assert isinstance(my_stream, Stream)
    dur_int = max(rint(dur), 0)
    my_list = list(my_stream)
    assert len(my_list) == dur_int


class TestTableLookup(object):

  def test_binary_rbinary_unary(self):
    a = TableLookup([0, 1, 2])
    b = 1 - a
    c = b * 3
    assert b.table == [1, 0, -1]
    assert (-b).table == [-1, 0, 1]
    assert c.table == [3, 0, -3]
    assert (a + b - c).table == [-2, 1, 4]

  def test_sin_basics(self):
    assert sin_table[0] == 0
    assert almost_eq(sin_table(pi, phase=pi/2).take(6), [1, -1] * 3)
    s30 = .5 * 2 ** .5 # sin(30 degrees)
    assert almost_eq(sin_table(pi/2, phase=pi/4).take(12),
                     [s30, s30, -s30, -s30] * 3)
    expected_pi_over_2 = [0., s30, 1., s30, 0., -s30, -1., -s30]
    # Assert with "diff" since it has zeros
    assert almost_eq.diff(sin_table(pi/4).take(32), expected_pi_over_2 * 4)

  def test_saw_basics(self):
    assert saw_table[0] == -1
    assert saw_table[-1] == 1
    assert saw_table[1] - saw_table[0] > 0
    data = saw_table(lag2freq(30)).take(30)
    first_step = data[1] - data[0]
    assert first_step > 0
    for d0, d1 in blocks(data, size=2, hop=1):
      assert d1 - d0 > 0 # Should be monotonically increasing
      assert almost_eq(d1 - d0, first_step) # Should have constant derivative


class TestImpulse(object):

  def test_no_input(self):
    delta = impulse()
    assert isinstance(delta, Stream)
    assert delta.take(25) == [1.] + list(zeros(24))

  def test_inf_input(self):
    delta = impulse(inf)
    assert isinstance(delta, Stream)
    assert delta.take(17) == [1.] + list(zeros(16))

  def test_integer(self):
    delta = impulse(one=1, zero=0)
    assert isinstance(delta, Stream)
    assert delta.take(22) == [1] + [0] * 21

  @p("dur", [-1, 0, .4, .5, 1, 2, 10])
  def test_finite_duration(self, dur):
    delta = impulse(dur)
    assert isinstance(delta, Stream)
    dur_int = max(rint(dur), 0)
    if dur_int == 0:
      assert list(delta) == []
    else:
      assert list(delta) == [1.] + [0.] * (dur_int - 1)

########NEW FILE########
__FILENAME__ = test_synth_numpy
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Tue Oct 16 2012
# danilo [dot] bellini [at] gmail [dot] com
"""
Testing module for the lazy_synth module by using numpy as an oracle
"""

import pytest
p = pytest.mark.parametrize

import numpy as np
from math import pi

# Audiolazy internal imports
from ..lazy_misc import almost_eq, sHz
from ..lazy_synth import adsr, sinusoid


def test_adsr():
  rate = 44100
  dur = 3 * rate
  sustain_level = .8
  attack = np.linspace(0., 1., num=np.round(20e-3 * rate), endpoint=False)
  decay = np.linspace(1., sustain_level, num=np.round(30e-3 * rate),
                      endpoint=False)
  release = np.linspace(sustain_level, 0., num=np.round(50e-3 * rate),
                        endpoint=False)
  sustain_dur = dur - len(attack) - len(decay) - len(release)
  sustain = sustain_level * np.ones(sustain_dur)
  env = np.hstack([attack, decay, sustain, release])

  s, Hz = sHz(rate)
  ms = 1e-3 * s
  assert almost_eq(env, adsr(dur=3*s, a=20*ms, d=30*ms, s=.8, r=50*ms))


def test_sinusoid():
  rate = 44100
  dur = 3 * rate

  freq220 = 220 * (2 * np.pi / rate)
  freq440 = 440 * (2 * np.pi / rate)
  phase220 = np.arange(dur, dtype=np.float64) * freq220
  phase440 = np.arange(dur, dtype=np.float64) * freq440
  sin_data = np.sin(phase440 + np.sin(phase220) * np.pi)

  s, Hz = sHz(rate)
  assert almost_eq.diff(sin_data,
                        sinusoid(freq=440*Hz,
                                 phase=sinusoid(220*Hz) * pi
                                ).take(int(3 * s)),
                        max_diff=1e-8
                       )

########NEW FILE########
__FILENAME__ = test_text
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Tue May 14 2013
# danilo [dot] bellini [at] gmail [dot] com
"""
Testing module for the lazy_text module
"""

import pytest
p = pytest.mark.parametrize

# Audiolazy internal imports
from ..lazy_text import rst_table


class TestRSTTable(object):

  simple_input = [
    [1, 2, 3, "hybrid"],
    [3, "mixed", .5, 123123]
  ]

  def test_simple_input_table(self):
    assert rst_table(
             self.simple_input,
             "this is_ a test".split()
           ) == [
             "==== ===== === ======",
             "this  is_   a   test ",
             "==== ===== === ======",
             "1    2     3   hybrid",
             "3    mixed 0.5 123123",
             "==== ===== === ======",
           ]

########NEW FILE########
__FILENAME__ = _internals
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Sat May 17 22:58:26 2014
# danilo [dot] bellini [at] gmail [dot] com
"""
AudioLazy internals module

The resources found here aren't DSP related nor take part of the main
``audiolazy`` namespace. Unless you're changing or trying to understand
the AudioLazy internals, you probably don't need to know about this.
"""

from functools import wraps, reduce
from warnings import warn
from glob import glob
from operator import concat
import os


def deprecate(func):
  """ A deprecation warning emmiter as a decorator. """
  @wraps(func)
  def wrapper(*args, **kwargs):
    warn("Deprecated, this will be removed in the future", DeprecationWarning)
    return func(*args, **kwargs)
  wrapper.__doc__ = "Deprecated.\n" + wrapper.__doc__
  return wrapper


#
# __init__.py importing resources
#

def get_module_names(package_path, pattern="lazy_*.py*"):
  """
  All names in the package directory that matches the given glob, without
  their extension. Repeated names should appear only once.
  """
  package_contents = glob(os.path.join(package_path[0], pattern))
  relative_path_names = (os.path.split(name)[1] for name in package_contents)
  no_ext_names = (os.path.splitext(name)[0] for name in relative_path_names)
  return sorted(set(no_ext_names))

def get_modules(package_name, module_names):
  """ List of module objects from the package, keeping the name order. """
  def get_module(name):
    return __import__(".".join([package_name, name]), fromlist=[package_name])
  return [get_module(name) for name in module_names]

def dunder_all_concat(modules):
  """ Single list with all ``__all__`` lists from the modules. """
  return reduce(concat, (getattr(m, "__all__", []) for m in modules), [])


#
# Resources for module/package summary tables on doctring
#

def summary_table(pairs, key_header, descr_header="Description", width=78):
  """
  List of one-liner strings containing a reStructuredText summary table
  for the given pairs ``(name, object)``.
  """
  from .lazy_text import rst_table, small_doc
  max_width = width - max(len(k) for k, v in pairs)
  table = [(k, small_doc(v, max_width=max_width)) for k, v in pairs]
  return rst_table(table, (key_header, descr_header))

def docstring_with_summary(docstring, pairs, key_header, summary_type):
  """ Return a string joining the docstring with the pairs summary table. """
  return "\n".join(
    [docstring, "Summary of {}:".format(summary_type), ""] +
    summary_table(pairs, key_header) + [""]
  )

def append_summary_to_module_docstring(module):
  """
  Change the ``module.__doc__`` docstring to include a summary table based
  on its contents as declared on ``module.__all__``.
  """
  pairs = [(name, getattr(module, name)) for name in module.__all__]
  kws = dict(key_header="Name", summary_type="module contents")
  module.__doc__ = docstring_with_summary(module.__doc__, pairs, **kws)


#
# Package initialization, first function to be called internally
#

def init_package(package_path, package_name, docstring):
  """
  Package initialization, to be called only by ``__init__.py``.

  - Find all module names;
  - Import all modules (so they're already cached on sys.modules), in
    the sorting order (this might make difference on cyclic imports);
  - Update all module docstrings (with the summary of its contents);
  - Build a module summary for the package docstring.

  Returns
  -------
  A 4-length tuple ``(modules, __all__, __doc__)``. The first one can be
  used by the package to import every module into the main package namespace.
  """
  module_names = get_module_names(package_path)
  modules = get_modules(package_name, module_names)
  dunder_all = dunder_all_concat(modules)
  for module in modules:
    append_summary_to_module_docstring(module)
  pairs = list(zip(module_names, modules))
  kws = dict(key_header="Module", summary_type="package modules")
  new_docstring = docstring_with_summary(docstring, pairs, **kws)
  return module_names, dunder_all, new_docstring

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Fri Feb 08 2013
# danilo [dot] bellini [at] gmail [dot] com
"""
AudioLazy documentation configuration file for Sphinx

"""

import sys, os
import audiolazy
import shlex
from subprocess import Popen, PIPE
import time
from collections import OrderedDict
import types
from audiolazy import iteritems


def splitter(lines, sep="-=", keep_idx=False):
  """
  Splits underlined blocks without indentation (reStructuredText pattern).

  Parameters
  ----------
  lines :
    A list of strings
  sep :
    Underline symbols. A line with only such symbols will be seen as a
    underlined one.
  keep_idx :
    If False (default), the function returns a collections.OrderedDict. Else,
    returns a
    list of index pairs

  Returns
  -------
  A collections.OrderedDict instance where a block with underlined key like
  ``"Key\\n==="`` and a list of lines following will have the item (key, list
  of lines), in the order that they appeared in the lists input. Empty keys
  gets an order numbering, and might happen for example after a ``"----"``
  separator. The values (lists of lines) don't include the key nor its
  underline, and is also stripped/trimmed as lines (i.e., there's no empty
  line as the first and last list items, but first and last line may start/end
  with whitespaces).

  """
  separators = audiolazy.Stream(
                 idx - 1 for idx, el in enumerate(lines)
                         if all(char in sep for char in el)
                         and len(el) > 0
               ).append([len(lines)])
  first_idx = separators.copy().take()
  blk_data = OrderedDict()

  empty_count = iter(audiolazy.count(1))
  next_empty = lambda: "--Empty--{0}--".format(next(empty_count))

  if first_idx != 0:
    blk_data[next_empty()] = lines[:first_idx]

  for idx1, idx2 in separators.blocks(size=2, hop=1):
    name = lines[idx1].strip() if lines[idx1].strip() != "" else next_empty()
    blk_data[name] = lines[idx1+2 : idx2]

  # Strips the empty lines
  for name in blk_data:
    while blk_data[name][-1].strip() == "":
      blk_data[name].pop()
    while blk_data[name][0].strip() == "":
      blk_data[name] = blk_data[name][1:]

  return blk_data


def audiolazy_namer(name):
  """
  Process a name to get Sphinx reStructuredText internal references like
  ``:obj:`name <audiolazy.lazy_something.name>``` for a given name string,
  specific for AudioLazy.

  """
  sp_name = name.split(".")
  try:

    # Find the audiolazy module name
    data = getattr(audiolazy, sp_name[0])
    if isinstance(data, audiolazy.StrategyDict):
      module_name = data.default.__module__
    else:
      module_name = data.__module__
      if not module_name.startswith("audiolazy"): # Decorated math, cmath, ...
        del module_name
        for mname in audiolazy.__modules__:
          if sp_name[0] in getattr(audiolazy, mname).__all__:
            module_name = "audiolazy." + mname
            break

    # Now gets the referenced item
    location = ".".join([module_name] + sp_name)
    for sub_name in sp_name[1:]:
      data = getattr(data, sub_name)

    # Finds the role to be used for referencing
    type_dict = OrderedDict([
      (audiolazy.StrategyDict, "obj"),
      (Exception, "exc"),
      (types.MethodType, "meth"),
      (types.FunctionType, "func"),
      (types.ModuleType, "mod"),
      (property, "attr"),
      (type, "class"),
    ])
    role = [v for k, v in iteritems(type_dict) if isinstance(data, k)][0]

  # Not found
  except AttributeError:
    return ":obj:`{0}`".format(name)

  # Found!
  else:
    return ":{0}:`{1} <{2}>`".format(role, name, location)


def pre_processor(app, what, name, obj, options, lines,
                  namer=lambda name: ":obj:`{0}`".format(name)):
  """
  Callback preprocessor function for docstrings.
  Converts data from Spyder pattern to Sphinx, using a ``namer`` function
  that defaults to ``lambda name: ":obj:`{0}`".format(name)`` (specific for
  ``.. seealso::``).

  """
  # Duplication removal
  if what == "module": # For some reason, summary appears twice
    idxs = [idx for idx, el in enumerate(lines) if el.startswith("Summary")]
    if len(idxs) >= 2:
      del lines[idxs.pop():] # Remove the last summary
    if len(idxs) >= 1:
      lines.insert(idxs[-1] + 1, "")
      if obj is audiolazy.lazy_math:
        lines.insert(idxs[-1] + 1, ".. tabularcolumns:: cl")
      else:
        lines.insert(idxs[-1] + 1, ".. tabularcolumns:: CJ")
      lines.insert(idxs[-1] + 1, "")

  # Real docstring format pre-processing
  result = []
  for name, blk in iteritems(splitter(lines)):
    nlower =  name.lower()

    if nlower == "parameters":
      starters = audiolazy.Stream(idx for idx, el in enumerate(blk)
                                      if len(el) > 0
                                      and not el.startswith(" ")
                                 ).append([len(blk)])
      for idx1, idx2 in starters.blocks(size=2, hop=1):
        param_data = " ".join(b.strip() for b in blk[idx1:idx2])
        param, expl = param_data.split(":", 1)
        if "," in param:
          param = param.strip()
          if not param[0] in ("(", "[", "<", "{"):
            param = "[{0}]".format(param)
        while "," in param:
          fparam, param = param.split(",", 1)
          result.append(":param {0}: {1}".format(fparam.strip(), "\.\.\."))
        result.append(":param {0}: {1}".format(param.strip(), expl.strip()))

    elif nlower == "returns":
      result.append(":returns: " + " ".join(blk))

    elif nlower in ("note", "warning", "hint"):
      result.append(".. {0}::".format(nlower))
      result.extend("  " + el for el in blk)

    elif nlower == "examples":
      result.append("**Examples**:")
      result.extend("  " + el for el in blk)

    elif nlower == "see also":
      result.append(".. seealso::")
      for el in blk:
        if el.endswith(":"):
          result.append("") # Skip a line
           # Sphinx may need help here to find some object locations
          refs = [namer(f.strip()) for f in el[:-1].split(",")]
          result.append("  " + ", ".join(refs))
        else:
          result.append("  " + el)

    else: # Unkown block name, perhaps the starting one (empty)
      result.extend(blk)

    # Skip a line after each block
    result.append("")

  # Replace lines with the processed data while keeping the actual lines id
  del lines[:]
  lines.extend(result)


def should_skip(app, what, name, obj, skip, options):
  """
  Callback object chooser function for docstring documentation.

  """
  if name in ["__doc__", "__module__", "__dict__", "__weakref__",
               "__abstractmethods__"
              ] or name.startswith("_abc_"):
    return True
  return False


def setup(app):
  """
  Just connects the docstring pre_processor and should_skip functions to be
  applied on all docstrings.

  """
  app.connect('autodoc-process-docstring',
              lambda *args: pre_processor(*args, namer=audiolazy_namer))
  app.connect('autodoc-skip-member', should_skip)


def file_name_generator_recursive(path):
  """
  Generator function for filenames given a directory path name. The resulting
  generator don't yield any [sub]directory name.

  """
  for name in os.listdir(path):
    full_name = os.path.join(path, name)
    if os.path.isdir(full_name):
      for new_name in file_name_generator_recursive(full_name):
        yield new_name
    else:
      yield full_name


def newest_file(file_iterable):
  """
  Returns the name of the newest file given an iterable of file names.

  """
  return max(file_iterable, key=lambda fname: os.path.getmtime(fname))


#
# README.rst file loading
#

# Gets README.rst file location from git (it's on the repository root)
git_command_location = shlex.split("git rev-parse --show-cdup")
git_output = Popen(git_command_location, stdout=PIPE).stdout.read()
file_location = git_output.decode("utf-8").strip()
readme_file_name = os.path.join(file_location, "README.rst")

# Opens the file (this should be importable!)
with open(readme_file_name, "r") as readme_file:
  readme_file_contents = readme_file.read().splitlines()

# Loads the description
description = "\n".join(splitter(readme_file_contents)["AudioLazy"])


#
# General configuration
#
extensions = [
  "sphinx.ext.autodoc",
  "sphinx.ext.doctest",
  "sphinx.ext.coverage",
  "sphinx.ext.mathjax",
  "sphinx.ext.viewcode",
]

templates_path = ["_templates"]
source_suffix = ".rst"
source_encoding = "utf-8"
master_doc = "index"

# General information about the project.
project = "AudioLazy" # Typed just to keep the UpperCamelCase
title = " ".join([project, "documentation"])
year = "2012-2013" # Not used directly by Sphinx
author = audiolazy.__author__ # Not used directly by Sphinx
copyright = ", ".join([year, author])
version = audiolazy.__version__

# If it's a development version, get release date using the last git commit
if version.endswith("dev"):
  git_command_line = "git log --date-order --date=raw --format=%cd -1".split()
  git_time_string = Popen(git_command_line, stdout=PIPE).stdout.read()
  git_raw_time = git_time_string.split()[0]
  iso_release_time = time.strftime("%Y%m%dT%H%M%SZ", # ISO 8601 format, UTF
                                   time.gmtime(int(git_raw_time)))
  release = version + iso_release_time
else:
  release = version

# Get "today" using the last file modification date
# WARNING: Be careful with git clone, clonning date will be "today"
install_path = audiolazy.__path__[0]
installed_nfile = newest_file(file_name_generator_recursive(install_path))
installed_time = os.path.getmtime(installed_nfile)
today = time.strftime("%Y-%m-%d", time.gmtime(installed_time)) # In UTF time

exclude_patterns = []

add_module_names = False
pygments_style = "sphinx"


# HTML output configuration
html_theme = "default"
html_static_path = ["_static"]
htmlhelp_basename = project + "doc"


# LaTeX output configuration
latex_elements = {
  "papersize": "a4paper",
  "pointsize": "10pt", # Font size
  "preamble": r"  \setlength{\tymax}{360pt}",
  "fontpkg": "\\usepackage{cmbright}",
}

latex_documents = [(
  master_doc,
  project + ".tex", # Target
  title,
  author,
  "manual", # The documentclass ("howto"/"manual")
)]

latex_show_pagerefs = True
latex_show_urls = "footnote"
latex_domain_indices = False


# Man (manual page) output configuration
man_pages = [(
  master_doc,
  project.lower(), # Name
  title, # Description
  [author],
  1, # Manual section
)]


# Texinfo output configuration
texinfo_documents = [(
  master_doc,
  project, # Target
  title,
  author,
  project, # Dir menu entry
  description, # From README.rst
  "Miscellanous", # Category
)]


# Epub output configuration
epub_title = project
epub_author = author
epub_publisher = author
epub_copyright = copyright


#
# Item in sys.modules for StrategyDict instances (needed for automodule)
#
for name, sdict in iteritems(audiolazy.__dict__):
  if isinstance(sdict, audiolazy.StrategyDict):
    fname = ".".join([sdict.default.__module__, name])
    sdict.__all__ = tuple(x[0] for x in sdict.keys())
    sys.modules[fname] = sdict

########NEW FILE########
__FILENAME__ = make_all_docs
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Fri Feb 08 2013
# danilo [dot] bellini [at] gmail [dot] com
"""
AudioLazy documentation creator via Sphinx

Note
----
You should call rst_creator first!

"""

import shlex
from subprocess import call
import sphinx

# Call string templates
sphinx_template = "sphinx-build -b {out_type} -d {build_dir}/doctrees "\
                  "-D latex_paper_size=a4 . {build_dir}/{out_type}"
make_template = "make -C {build_dir}/{out_type} {make_param}"

# Make targets given the output type
make_target = {"latex": "all-pdf",
               "texinfo": "info"}

def call_sphinx(out_type, build_dir = "build"):
  """
  Call the ``sphinx-build`` for the given output type and the ``make`` when
  the target has this possibility.

  Parameters
  ----------
  out_type :
    A builder name for ``sphinx-build``. See the full list at
    `<http://sphinx-doc.org/invocation.html>`_.
  build_dir :
    Directory for storing the output. Defaults to "build".

  """
  sphinx_string = sphinx_template.format(build_dir=build_dir,
                                         out_type=out_type)
  if sphinx.main(shlex.split(sphinx_string)) != 0:
    raise RuntimeError("Something went wrong while building '{0}'"
                       .format(out_type))
  if out_type in make_target:
    make_string = make_template.format(build_dir=build_dir,
                                       out_type=out_type,
                                       make_param=make_target[out_type])
    call(shlex.split(make_string)) # Errors here don't need to stop anything

# Calling this as a script builds/makes all targets in the list below
if __name__ == "__main__":
  out_types = ["text", "html", "latex", "man", "texinfo", "epub"]
  for out_type in out_types:
    call_sphinx(out_type)

########NEW FILE########
__FILENAME__ = rst_creator
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Fri Feb 08 2013
# danilo [dot] bellini [at] gmail [dot] com
"""
AudioLazy documentation reStructuredText file creator

Note
----
You should call make_all_docs afterwards!

Warning
-------
Calling this OVERWRITES the RST files in the directory it's in, and don't
ask for confirmation!

"""

import os
import audiolazy
import re
from audiolazy import iteritems

# This file should be at the conf.py directory!
from conf import readme_file_contents, splitter, master_doc


def find_full_name(prefix, suffix="rst"):
  """
  Script path to actual path relative file name converter.

  Parameters
  ----------
  prefix :
    File name prefix (without extension), relative to the script location.
  suffix :
    File name extension (defaults to "rst").

  Returns
  -------
  A file name path relative to the actual location to a file
  inside the script location.

  Warning
  -------
  Calling this OVERWRITES the RST files in the directory it's in, and don't
  ask for confirmation!

  """
  return os.path.join(os.path.split(__file__)[0],
                      os.path.extsep.join([prefix, suffix]))


def save_to_rst(prefix, data):
  """
  Saves a RST file with the given prefix into the script file location.

  """
  with open(find_full_name(prefix), "w") as rst_file:
    rst_file.write(full_gpl_for_rst)
    rst_file.write(data)


#
# First chapter! Splits README.rst data into the gen_blocks iterable
#
readme_data = splitter(readme_file_contents)
rfc_copyright = readme_data.popitem()[1] # Last block is a small license msg
gen_blocks = iteritems(readme_data)

# Process GPL license comment at the beginning to put it in all RST files
gpl_to_add = "  File auto-generated by the rst_creator.py script."
full_gpl_for_rst = next(gen_blocks)[1] # It's before the first readable block
full_gpl_for_rst = "\n".join(full_gpl_for_rst[:-1] + [gpl_to_add] +
                             full_gpl_for_rst[-1:] + ["\n\n"])
gpl_for_rst = "\n  ".join(full_gpl_for_rst.strip()
                                          .strip(".").splitlines()[:-2])

# Process the first readable block (project name and small description)
rfc_name, rfc_description = next(gen_blocks) # Second block
rfc_name = " ".join([rfc_name, "|version|"]) # Puts version in title ...
rfc_name = [rfc_name, "=" * len(rfc_name)] # ... and the syntax of a title

# Process last block to have a nice looking, and insert license file link
license_file_name = "COPYING.txt"
license_full_file_name = "../" + license_file_name
linked_file_name = ":download:`{0} <{1}>`".format(license_file_name,
                                                  license_full_file_name)
rfc_copyright = ("\n  ".join(el.strip() for el in rfc_copyright
                                        if el.strip() != "")
                       .replace(license_file_name,linked_file_name)
                       .replace("- ", "")
                )

#
# Creates a RST for each block in README.rst besides the first (small
# description) and the last (license) ones, which were both already removed
# from "gen_blocks"
#
readme_names = [] # Keep the file names
for name, data in gen_blocks:
  fname = "".join(re.findall("[\w ]", name)).replace(" ", "_").lower()

  # Image location should be corrected before
  img_string = ".. image:: "
  for idx, el in enumerate(data):
    if el.startswith(img_string):
      data[idx]  = el.replace(img_string, img_string + "../")

  save_to_rst(fname, "\n".join([name, "=" * len(name)] + data).strip())
  readme_names.append(fname)


#
# Creates the master document
#

# First block
main_toc = """
.. toctree::
  :maxdepth: 2

  intro
  modules
"""
first_block = rfc_name + [""] + rfc_description + [main_toc]

# Second block
indices_block = """
.. only:: html

  Indices and tables
  ------------------

  * :ref:`genindex`
  * :ref:`modindex`
  * :ref:`search`
"""

# Saves the master document (with the TOC)
index_data = "\n".join(first_block + [indices_block])
save_to_rst(master_doc, index_data.strip())


#
# Creates the intro.rst
#
intro_block = """
Introduction
============

This is the main AudioLazy documentation, whose contents are mainly from the
repository documentation and source code docstrings, tied together with
`Sphinx <http://sphinx.pocoo.org>`_. The sections below can introduce you to
the AudioLazy Python DSP package.

.. toctree::
  :maxdepth: 4
{0}
  license
""".format(("\n" + 2 * " ").join([""] + readme_names))
save_to_rst("intro", intro_block.strip())


#
# Creates the license.rst
#
license_block = """
License and auto-generated reST files
=====================================

All project files, including source and documentation, are free software,
under GPLv3. This is free in the sense that the source code have to be always
available to you if you ask for it, as well as forks or otherwise derivative
new source codes, however stated in a far more precise way by experts in that
kind of law text. That's at the same time far from the technical language from
engineering, maths and computer science, and more details would be beyond the
needs of this document. You should find the following information in all
Python (*\*.py*) source code files and also in all reStructuredText (*\*.rst*)
files:

  ::

    {0}

This is so also for auto-generated reStructuredText documentation files.
However, besides most reStructuredText files being generated by a script,
their contents aren't auto-generated. These are spread in the source code,
both in reStructuredText and Python files, organized in a way that would make
the same manually written documentation be used as:

+ `Spyder <https://code.google.com/p/spyderlib/>`_ (Python IDE made for
  scientific purposes) *Rich Text* auto-documentation at its
  *Object inspector*. Docstrings were written in a reStructuredText syntax
  following its conventions for nice HTML rendering;

+ Python docstrings (besides some docstring creation like what happens in
  StrategyDict instances, that's really the original written data in the
  source);

+ Full documentation, thanks to `Sphinx <sphinx.pocoo.org>`_, that replaces
  the docstring conventions to other ones for creating in the that allows
  automatic conversion to:

  - HTML
  - PDF (LaTeX)
  - ePUB
  - Manual pages (man)
  - Texinfo
  - Pure text files

License is the same in all files that generates those documentations.
Some reStructuredText files, like the README.rst that generated this whole
chapter, were created manually. They're also free software as described in
GPLv3. The main project repository includes a message:

.. parsed-literal::

  {1}

This should be applied to all files that belongs to the AudioLazy project.
Although all the project files were up to now created and modified by a sole
person, this sole person had never wanted to keep such status for so long. If
you found a bug or otherwise have an issue or a patch to send, show the issue
or the pull request at the
`main AudioLazy repository <https://github.com/danilobellini/audiolazy>`_,
so that the bug would be fixed, or the new resource become available, not
only for a few people but for everyone.
""".format(gpl_for_rst, rfc_copyright)
save_to_rst("license", license_block.strip())


#
# Second chapter! Creates the modules.rst
#
modules_block = """
Modules Documentation
=====================

Below is the table of contents, with processed data from docstrings. They were
made and processed in a way that would be helpful as a stand-alone
documentation, but if it's your first time with this package, you should see
at least the :doc:`getting_started` before these, since the
full module documentation isn't written for beginners.

.. toctree::
  :maxdepth: 4
  :glob:

  audiolazy
  lazy_*
"""
save_to_rst("modules", modules_block.strip())


#
# Creates the RST file for the package
#
first_line = ":mod:`audiolazy` Package"
data = [
  first_line,
  "=" * len(first_line),
  ".. automodule:: audiolazy",
]
save_to_rst("audiolazy", "\n".join(data).strip())


#
# Creates the RST file for each module
#
for lzmodule in audiolazy.__modules__:
  first_line = ":mod:`{0}` Module".format(lzmodule)
  data = [
    first_line,
    "=" * len(first_line),
    ".. automodule:: audiolazy.{0}".format(lzmodule),
    "   :members:",
    "   :undoc-members:",
    "   :show-inheritance:",
  ]

  # See if there's any StrategyDict in the module
  module_data = getattr(audiolazy, lzmodule)
  for memb in module_data.__all__:
    memb_data = getattr(module_data, memb)
    if isinstance(memb_data, audiolazy.StrategyDict):
      sline = ":obj:`{0}.{1}` StrategyDict".format(lzmodule, memb)
      data += [
        "", sline,
        "-" * len(sline),
        ".. automodule:: audiolazy.{0}.{1}".format(lzmodule, memb),
        "   :members:",
        "   :undoc-members:",
      ]

  save_to_rst(lzmodule, "\n".join(data).strip())

########NEW FILE########
__FILENAME__ = animated_plot
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Created on Tue May 20 19:41:23 2014
# @author: Danilo de Jesus da Silva Bellini
"""
Matplotlib animated plot with mic input data.

Call with the API name like ...
  ./animated_plot.py jack
... or without nothing for the default PortAudio API.
"""
from __future__ import division
from audiolazy import sHz, chunks, AudioIO, line, pi, window
from matplotlib import pyplot as plt
from matplotlib.animation import FuncAnimation
from numpy.fft import rfft
import numpy as np
import collections, sys, threading

# AudioLazy init
rate = 44100
s, Hz = sHz(rate)
ms = 1e-3 * s

length = 2 ** 12
data = collections.deque([0.] * length, maxlen=length)
wnd = np.array(window.hamming(length)) # For FFT

api = sys.argv[1] if sys.argv[1:] else None # Choose API via command-line
chunks.size = 1 if api == "jack" else 16

# Creates a data updater callback
def update_data():
  with AudioIO(api=api) as rec:
    for el in rec.record(rate=rate):
      data.append(el)
      if update_data.finish:
        break

# Creates the data updater thread
update_data.finish = False
th = threading.Thread(target=update_data)
th.start() # Already start updating data

# Plot setup
fig = plt.figure("AudioLazy in a Matplotlib animation", facecolor='#cccccc')

time_values = np.array(list(line(length, -length / ms, 0)))
time_ax = plt.subplot(2, 1, 1,
                      xlim=(time_values[0], time_values[-1]),
                      ylim=(-1., 1.),
                      axisbg="black")
time_ax.set_xlabel("Time (ms)")
time_plot_line = time_ax.plot([], [], linewidth=2, color="#00aaff")[0]

dft_max_min, dft_max_max = .01, 1.
freq_values = np.array(line(length, 0, 2 * pi / Hz).take(length // 2 + 1))
freq_ax = plt.subplot(2, 1, 2,
                      xlim=(freq_values[0], freq_values[-1]),
                      ylim=(0., .5 * (dft_max_max + dft_max_min)),
                      axisbg="black")
freq_ax.set_xlabel("Frequency (Hz)")
freq_plot_line = freq_ax.plot([], [], linewidth=2, color="#00aaff")[0]

# Functions to setup and update plot
def init(): # Called twice on init, also called on each resize
  time_plot_line.set_data([], []) # Clear
  freq_plot_line.set_data([], [])
  fig.tight_layout()
  return []

def animate(idx):
  array_data = np.array(data)
  spectrum = np.abs(rfft(array_data * wnd)) / length

  time_plot_line.set_data(time_values, array_data)
  freq_plot_line.set_data(freq_values, spectrum)

  # Update y range if needed
  smax = spectrum.max()
  top = freq_ax.get_ylim()[1]
  if top < dft_max_max and abs(smax/top) > 1:
    freq_ax.set_ylim(top=top * 2)
  elif top > dft_max_min and abs(smax/top) < .3:
    freq_ax.set_ylim(top=top / 2)
  else:
    return [time_plot_line, freq_plot_line] # Update only what changed
  return []

# Animate! (assignment to anim is needed to avoid garbage collecting it)
anim = FuncAnimation(fig, animate, init_func=init, interval=10, blit=True)
plt.show() # Blocking

# Stop the recording thread after closing the window
update_data.finish = True
th.join()

########NEW FILE########
__FILENAME__ = butterworth_scipy
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Fri Aug 30 2013
# danilo [dot] bellini [at] gmail [dot] com
"""
Butterworth filter from SciPy as a ZFilter instance, with plots

One resonator (first order filter) is used for comparison with the
butterworth from the example (third order filter). Both has zeros at
1 (DC level) and -1 (Nyquist).

"""

from __future__ import print_function
from audiolazy import sHz, ZFilter, dB10, resonator, pi
from scipy.signal import butter, buttord
import pylab

# Example
rate = 44100
s, Hz = sHz(rate)
wp = pylab.array([100 * Hz, 240 * Hz]) # Bandpass range in rad/sample
ws = pylab.array([80 * Hz, 260 * Hz]) # Bandstop range in rad/sample

# Let's use wp/pi since SciPy defaults freq from 0 to 1 (Nyquist frequency)
order, new_wp_divpi = buttord(wp/pi, ws/pi, gpass=dB10(.6), gstop=dB10(.4))
ssfilt = butter(order, new_wp_divpi, btype="bandpass")
filt_butter = ZFilter(ssfilt[0].tolist(), ssfilt[1].tolist())

# Some debug information
new_wp = new_wp_divpi * pi
print("Butterworth filter order:", order) # Should be 3
print("Bandpass ~3dB range (in Hz):", new_wp / Hz)

# Resonator using only the frequency and bandwidth from the Butterworth filter
freq = new_wp.mean()
bw = new_wp[1] - new_wp[0]
filt_reson = resonator.z_exp(freq, bw)

# Plots with MatPlotLib
kwargs = {
  "min_freq": 10 * Hz,
  "max_freq": 800 * Hz,
  "rate": rate, # Ensure frequency unit in plot is Hz
}
filt_butter.plot(pylab.figure("From scipy.signal.butter"), **kwargs)
filt_reson.plot(pylab.figure("From audiolazy.resonator.z_exp"), **kwargs)
filt_butter.zplot(pylab.figure("Zeros/Poles from scipy.signal.butter"))
filt_reson.zplot(pylab.figure("Zeros/Poles from audiolazy.resonator.z_exp"))
pylab.show()

########NEW FILE########
__FILENAME__ = butterworth_with_noise
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Created on Thu May 22 05:54:30 2014
# @author: Danilo de Jesus da Silva Bellini
"""
Two butterworth filters with Scipy applied to white noise

This example is based on the experiment number 34 from

  Demonstrations to accompany Bregman’s Auditory Scene Analysis

by Albert S. Bregman and Pierre A. Ahad.

This experiment shows the audio is perceived as pitched differently on the
100ms glimpses when the context changes, although they are physically
identical, i.e., the glimpses are indeed perceptually segregated from the
background noise.

Noise ranges are from [0; 2kHz] and [2kHz; 4kHz] and durations are 100ms and
400ms instead of the values declared in the original text. IIR filters are
being used instead of FIR ones to get the noise, and the fact that originally
there's no silence between the higher and lower pitch contexts, but the core
idea of the experiment remains the same.
"""

from audiolazy import (sHz, dB10, ZFilter, pi, ControlStream, white_noise,
                       chunks, AudioIO, xrange, z)
from scipy.signal import butter, buttord
import numpy as np
from time import sleep

rate = 44100
s, Hz = sHz(rate)
kHz = 1e3 * Hz
tol = 100 * Hz
freq = 2 * kHz

wp = freq - tol # Bandpass frequency in rad/sample (from zero)
ws = freq + tol # Bandstop frequency in rad/sample (up to Nyquist frequency)
order, new_wp_divpi = buttord(wp/pi, ws/pi, gpass=dB10(.6), gstop=dB10(.4))
ssfilt = butter(order, new_wp_divpi, btype="lowpass")
filt_low = ZFilter(ssfilt[0].tolist(), ssfilt[1].tolist())

## That can be done without scipy using the equation directly:
#filt_low = ((2.90e-4 + 1.16e-3 * z ** -1 + 1.74e-3 * z ** -2
#                     + 1.16e-3 * z ** -3 + 2.90e-4 * z ** -4) /
#            (1       - 3.26    * z ** -1 + 4.04    * z ** -2
#                     - 2.25    * z ** -3 +  .474   * z ** -4))

wp = np.array([freq + tol, 2 * freq - tol]) # Bandpass range in rad/sample
ws = np.array([freq - tol, 2 * freq + tol]) # Bandstop range in rad/sample
order, new_wp_divpi = buttord(wp/pi, ws/pi, gpass=dB10(.6), gstop=dB10(.4))
ssfilt = butter(order, new_wp_divpi, btype="bandpass")
filt_high = ZFilter(ssfilt[0].tolist(), ssfilt[1].tolist())

## Likewise, using the equation directly this one would be:
#filt_high = ((2.13e-3 * (1 - z ** -6) - 6.39e-3 * (z ** -2 - z ** -4)) /
#             (1 - 4.99173 * z ** -1 + 10.7810 * z ** -2 - 12.8597 * z ** -3
#                + 8.93092 * z ** -4 - 3.42634 * z ** -5 + .569237 * z ** -6))

gain_low = ControlStream(0)
gain_high = ControlStream(0)

low = filt_low(white_noise())
high = filt_high(white_noise())
low /= 2 * max(low.take(2000))
high /= 2 * max(high.take(2000))

chunks.size = 16
with AudioIO() as player:
  player.play(low * gain_low + high * gain_high)
  gain_low.value = 1
  while True:
    gain_high.value = 0
    sleep(1)
    for unused in xrange(5): # Keeps low playing
      sleep(.1)
      gain_high.value = 0
      sleep(.4)
      gain_high.value = 1

    gain_low.value = 0
    sleep(1)
    for unused in xrange(5): # Keeps high playing
      sleep(.1)
      gain_low.value = 0
      sleep(.4)
      gain_low.value = 1

########NEW FILE########
__FILENAME__ = dft_pitch
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Wed May 01 2013
# danilo [dot] bellini [at] gmail [dot] com
"""
Pitch follower via DFT peak with Tkinter GUI
"""

# ------------------------
# AudioLazy pitch follower
# ------------------------
from audiolazy import (tostream, AudioIO, freq2str, sHz,
                       lowpass, envelope, pi, thub, Stream, maverage)
from numpy.fft import rfft

def limiter(sig, threshold=.1, size=256, env=envelope.rms, cutoff=pi/2048):
  sig = thub(sig, 2)
  return sig * Stream( 1. if el <= threshold else threshold / el
                       for el in maverage(size)(env(sig, cutoff=cutoff)) )


@tostream
def dft_pitch(sig, size=2048, hop=None):
  for blk in Stream(sig).blocks(size=size, hop=hop):
    dft_data = rfft(blk)
    idx, vmax = max(enumerate(dft_data),
                    key=lambda el: abs(el[1]) / (2 * el[0] / size + 1)
                   )
    yield 2 * pi * idx / size


def pitch_from_mic(upd_time_in_ms):
  rate = 44100
  s, Hz = sHz(rate)

  with AudioIO() as recorder:
    snd = recorder.record(rate=rate)
    sndlow = lowpass(400 * Hz)(limiter(snd, cutoff=20 * Hz))
    hop = int(upd_time_in_ms * 1e-3 * s)
    for pitch in freq2str(dft_pitch(sndlow, size=2*hop, hop=hop) / Hz):
      yield pitch


# ----------------
# GUI with tkinter
# ----------------
if __name__ == "__main__":
  try:
    import tkinter
  except ImportError:
    import Tkinter as tkinter
  import threading
  import re

  # Window (Tk init), text label and button
  tk = tkinter.Tk()
  tk.title(__doc__.strip().splitlines()[0])
  lbldata = tkinter.StringVar(tk)
  lbltext = tkinter.Label(tk, textvariable=lbldata, font=("Purisa", 72),
                          width=10)
  lbltext.pack(expand=True, fill=tkinter.BOTH)
  btnclose = tkinter.Button(tk, text="Close", command=tk.destroy,
                            default="active")
  btnclose.pack(fill=tkinter.X)

  # Needed data
  regex_note = re.compile(r"^([A-Gb#]*-?[0-9]*)([?+-]?)(.*?%?)$")
  upd_time_in_ms = 200

  # Update functions for each thread
  def upd_value(): # Recording thread
    pitches = iter(pitch_from_mic(upd_time_in_ms))
    while not tk.should_finish:
      tk.value = next(pitches)

  def upd_timer(): # GUI mainloop thread
    lbldata.set("\n".join(regex_note.findall(tk.value)[0]))
    tk.after(upd_time_in_ms, upd_timer)

  # Multi-thread management initialization
  tk.should_finish = False
  tk.value = freq2str(0) # Starting value
  lbldata.set(tk.value)
  tk.upd_thread = threading.Thread(target=upd_value)

  # Go
  tk.upd_thread.start()
  tk.after_idle(upd_timer)
  tk.mainloop()
  tk.should_finish = True
  tk.upd_thread.join()

########NEW FILE########
__FILENAME__ = fmbench
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Tue Oct 16 2012
# danilo [dot] bellini [at] gmail [dot] com
"""
FM synthesis benchmarking
"""

from __future__ import unicode_literals, print_function
from timeit import timeit
import sys


# ===================
# Some initialization
# ===================
num_tests = 30
is_pypy = any(name.startswith("pypy") for name in dir(sys))
if is_pypy:
  print("PyPy detected!")
  print()
  numpy_name = "numpypy"
else:
  numpy_name = "numpy"


# ======================
# AudioLazy benchmarking
# ======================
kws = {}
kws["setup"] = """
from audiolazy import sHz, adsr, sinusoid
from math import pi
"""
kws["number"] = num_tests
kws["stmt"] = """
s, Hz = sHz(44100)
ms = 1e-3 * s
env = adsr(dur=5*s, a=20*ms, d=30*ms, s=.8, r=50*ms)
sin_data = sinusoid(freq=440*Hz,
                    phase=sinusoid(220*Hz) * pi)
result = sum(env * sin_data)
"""

print("=== AudioLazy benchmarking ===")
print("Trials:", kws["number"])
print()
print("Setup code:")
print(kws["setup"])
print()
print("Benchmark code (also executed once as 'setup'/'training'):")
kws["setup"] += kws["stmt"] # Helpful for PyPy
print(kws["stmt"])
print()
print("Mean time (milliseconds):")
print(timeit(**kws) * 1e3 / num_tests)
print("==============================")
print()


# ==================
# Numpy benchmarking
# ==================
kws_np = {}
kws_np["setup"] = "import {0} as np".format(numpy_name)
kws_np["number"] = num_tests
kws_np["stmt"] = """
rate = 44100
dur = 5 * rate
sustain_level = .8
# The np.linspace isn't in numpypy yet; it uses float64
attack = np.linspace(0., 1., num=np.round(20e-3 * rate), endpoint=False)
decay = np.linspace(1., sustain_level, num=np.round(30e-3 * rate),
                    endpoint=False)
release = np.linspace(sustain_level, 0., num=np.round(50e-3 * rate),
                      endpoint=False)
sustain_dur = dur - len(attack) - len(decay) - len(release)
sustain = sustain_level * np.ones(sustain_dur)
env = np.hstack([attack, decay, sustain, release])
freq220 = 220 * 2 * np.pi / rate
freq440 = 440 * 2 * np.pi / rate
phase220 = np.arange(dur, dtype=np.float64) * freq220
phase440 = np.arange(dur, dtype=np.float64) * freq440
sin_data = np.sin(phase440 + np.sin(phase220) * np.pi)
result = np.sum(env * sin_data)
"""

# Alternative for numpypy (since it don't have "linspace" nor "hstack")
stmt_npp = """
rate = 44100
dur = 5 * rate
sustain_level = .8
len_attack = int(round(20e-3 * rate))
attack = np.arange(len_attack, dtype=np.float64) / len_attack
len_decay = int(round(30e-3 * rate))
decay = (np.arange(len_decay - 1, -1, -1, dtype=np.float64
                  ) / len_decay) * (1 - sustain_level) + sustain_level
len_release = int(round(50e-3 * rate))
release = (np.arange(len_release - 1, -1, -1, dtype=np.float64
                    ) / len_release) * sustain_level
env = np.ndarray(dur, dtype=np.float64)
env[:len_attack] = attack
env[len_attack:len_attack+len_decay] = decay
env[len_attack+len_decay:dur-len_release] = sustain_level
env[dur-len_release:dur] = release
freq220 = 220 * 2 * np.pi / rate
freq440 = 440 * 2 * np.pi / rate
phase220 = np.arange(dur, dtype=np.float64) * freq220
phase440 = np.arange(dur, dtype=np.float64) * freq440
sin_data = np.sin(phase440 + np.sin(phase220) * np.pi)
result = np.sum(env * sin_data)
"""

try:
  if is_pypy:
    import numpypy as np
  else:
    import numpy as np
except ImportError:
  print("Numpy not found. Finished benchmarking!")
else:
  if is_pypy:
    kws_np["stmt"] = stmt_npp

  print("Numpy found!")
  print()
  print("=== Numpy benchmarking ===")
  print("Trials:", kws_np["number"])
  print()
  print("Setup code:")
  print(kws_np["setup"])
  print()
  print("Benchmark code (also executed once as 'setup'/'training'):")
  kws_np["setup"] += kws_np["stmt"] # Helpful for PyPy
  print(kws_np["stmt"])
  print()
  print("Mean time (milliseconds):")
  print(timeit(**kws_np) * 1e3 / num_tests)
  print("==========================")

########NEW FILE########
__FILENAME__ = formants
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Tue Sep 10 18:02:32 2013
# danilo [dot] bellini [at] gmail [dot] com
"""
Voiced "ah-eh-ee-oh-oo" based on resonators at formant frequencies
"""

from __future__ import unicode_literals, print_function

from audiolazy import (sHz, maverage, rint, AudioIO, ControlStream,
                       CascadeFilter, resonator, saw_table)
from time import sleep

# Script input, change this with symbols from the table below
vowels = "aɛiɒu"

# Formant table from in http://en.wikipedia.org/wiki/Formant
formants = {
  "i": [240, 2400],
  "y": [235, 2100],
  "e": [390, 2300],
  "ø": [370, 1900],
  "ɛ": [610, 1900],
  "œ": [585, 1710],
  "a": [850, 1610],
  "æ": [820, 1530],
  "ɑ": [750, 940],
  "ɒ": [700, 760],
  "ʌ": [600, 1170],
  "ɔ": [500, 700],
  "ɤ": [460, 1310],
  "o": [360, 640],
  "ɯ": [300, 1390],
  "u": [250, 595],
}


# Initialization
rate = 44100
s, Hz = sHz(rate)
inertia_dur = .5 * s
inertia_filter = maverage(rint(inertia_dur))

with AudioIO() as player:
  first_coeffs = formants[vowels[0]]

  # These are signals to be changed during the synthesis
  f1 = ControlStream(first_coeffs[0] * Hz)
  f2 = ControlStream(first_coeffs[1] * Hz)
  gain = ControlStream(0) # For fading in

  # Creates the playing signal
  filt = CascadeFilter([
    resonator.z_exp(inertia_filter(f1).skip(inertia_dur), 400 * Hz),
    resonator.z_exp(inertia_filter(f2).skip(inertia_dur), 2000 * Hz),
  ])
  sig = filt((saw_table)(100 * Hz)) * inertia_filter(gain)

  th = player.play(sig)
  for vowel in vowels:
    coeffs = formants[vowel]
    print("Now playing: ", vowel)
    f1.value = coeffs[0] * Hz
    f2.value = coeffs[1] * Hz
    gain.value = 1 # Fade in the first vowel, changes nothing afterwards
    sleep(2)

  # Fade out
  gain.value = 0
  sleep(inertia_dur / s + .2) # Divide by s because here it's already
                              # expecting a value in seconds, and we don't
                              # want ot give a value in a time-squaed unit
                              # like s ** 2

########NEW FILE########
__FILENAME__ = gammatone_plots
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Sun Oct 07 2012
# danilo [dot] bellini [at] gmail [dot] com
"""
Gammatone frequency and impulse response plots example
"""

from __future__ import division
from audiolazy import (erb, gammatone, gammatone_erb_constants, sHz, impulse,
                       dB20)
from numpy import linspace, ceil
from matplotlib import pyplot as plt

# Initialization info
rate = 44100
s, Hz = sHz(rate)
ms = 1e-3 * s
plot_freq_time = {80.: 60 * ms,
                  100.: 50 * ms,
                  200.: 40 * ms,
                  500.: 25 * ms,
                  800.: 20 * ms,
                  1000.: 15 * ms}
freq = linspace(0.1, 2 * max(freq for freq in plot_freq_time), 100)

fig1 = plt.figure("Frequency response", figsize=(16, 9), dpi=60)
fig2 = plt.figure("Impulse response", figsize=(16, 9), dpi=60)

# Plotting loop
for idx, (fc, endtime) in enumerate(sorted(plot_freq_time.items()), 1):
  # Configuration for the given frequency
  num_samples = int(round(endtime))
  time_scale = linspace(0, num_samples / ms, num_samples)
  bw = gammatone_erb_constants(4)[0] * erb(fc * Hz, Hz)

  # Subplot configuration
  plt.figure(1)
  plt.subplot(2, ceil(len(plot_freq_time) / 2), idx)
  plt.title("Frequency response - {0} Hz".format(fc))
  plt.xlabel("Frequency (Hz)")
  plt.ylabel("Gain (dB)")

  plt.figure(2)
  plt.subplot(2, ceil(len(plot_freq_time) / 2), idx)
  plt.title("Impulse response - {0} Hz".format(fc))
  plt.xlabel("Time (ms)")
  plt.ylabel("Amplitude")

  # Plots each filter frequency and impulse response
  for gt, config in zip(gammatone, ["b-", "g--", "r-.", "k:"]):
    filt = gt(fc * Hz, bw)

    plt.figure(1)
    plt.plot(freq, dB20(filt.freq_response(freq * Hz)), config,
             label=gt.__name__)

    plt.figure(2)
    plt.plot(time_scale, filt(impulse()).take(num_samples), config,
             label=gt.__name__)

# Finish
for graph in fig1.axes + fig2.axes:
  graph.grid()
  graph.legend(loc="best")

fig1.tight_layout()
fig2.tight_layout()

plt.show()
########NEW FILE########
__FILENAME__ = io_wire
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Wed Nov 07 2012
# danilo [dot] bellini [at] gmail [dot] com
"""
Simple I/O wire example, connecting the input directly to the output

This example uses the default PortAudio API, however you can change it by
using the "api" keyword argument in AudioIO creation, like

  with AudioIO(True, api="jack") as pr:

obviously, you can use another API instead (like "alsa").

Note
----
When using JACK, keep chunks.size = 1
"""

from audiolazy import chunks, AudioIO

chunks.size = 16 # Amount of samples per chunk to be sent to PortAudio
with AudioIO(True) as pr: # A player-recorder
  pr.play(pr.record())

########NEW FILE########
__FILENAME__ = iso226_plot
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Created on Wed May 21 19:57:40 2014
# @author: Danilo de Jesus da Silva Bellini
"""
Plots ISO/FDIS 226:2003 equal loudness contour curves

This is based on figure A.1 of ISO226, and needs Scipy and Matplotlib
"""

from __future__ import division

from audiolazy import exp, line, ln, phon2dB, xrange
import pylab

title = "ISO226 equal loudness curves"
freqs = list(exp(line(2048, ln(20), ln(12500), finish=True)))
pylab.figure(title, figsize=[8, 4.5], dpi=120)

# Plots threshold
freq2dB_threshold = phon2dB.iso226(None) # Threshold
pylab.plot(freqs, freq2dB_threshold(freqs), color="blue", linestyle="--")
pylab.text(300, 5, "Hearing threshold", fontsize=8,
           horizontalalignment="right")

# Plots 20 to 80 phons
for loudness in xrange(20, 81, 10): # in phons
  freq2dB = phon2dB.iso226(loudness)
  pylab.plot(freqs, freq2dB(freqs), color="black")
  pylab.text(850, loudness + 2, "%d phon" % loudness, fontsize=8,
             horizontalalignment="center")

# Plots 90 phons
freq2dB_90phon = phon2dB.iso226(90)
freqs4k1 = list(exp(line(2048, ln(20), ln(4100), finish=True)))
pylab.plot(freqs4k1, freq2dB_90phon(freqs4k1), color="black")
pylab.text(850, 92, "90 phon", fontsize=8, horizontalalignment="center")

# Plots 10 and 100 phons
freq2dB_10phon = phon2dB.iso226(10)
freq2dB_100phon = phon2dB.iso226(100)
freqs1k = list(exp(line(1024, ln(20), ln(1000), finish=True)))
pylab.plot(freqs, freq2dB_10phon(freqs), color="green", linestyle=":")
pylab.plot(freqs1k, freq2dB_100phon(freqs1k), color="green", linestyle=":")
pylab.text(850, 12, "10 phon", fontsize=8, horizontalalignment="center")
pylab.text(850, 102, "100 phon", fontsize=8, horizontalalignment="center")

# Plot axis config
pylab.axis(xmin=16, xmax=16000, ymin=-10, ymax=130)
pylab.xscale("log")
pylab.yticks(list(xrange(-10, 131, 10)))
xticks_values = [16, 31.5, 63, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]
pylab.xticks(xticks_values, xticks_values)
pylab.grid() # The grid follows the ticks

# Plot labels
pylab.title(title)
pylab.xlabel("Frequency (Hz)")
pylab.ylabel("Sound Pressure (dB)")

# Finish
pylab.tight_layout()
pylab.show()

########NEW FILE########
__FILENAME__ = keyboard
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Wed Oct 16 13:44:10 2013
# danilo [dot] bellini [at] gmail [dot] com
"""
Musical keyboard synth example with a QWERTY keyboard
"""

from audiolazy import (str2midi, midi2freq, saw_table, sHz, Streamix, Stream,
                       line, AudioIO, chunks)
import sys
try:
  import tkinter
except ImportError:
  import Tkinter as tkinter

keys = "awsedftgyhujkolp;" # Chromatic scale
first_note = str2midi("C3")

pairs = list(enumerate(keys.upper(), first_note + 12)) + \
        list(enumerate(keys, first_note))
notes = {k: midi2freq(idx) for idx, k in pairs}
synth = saw_table

txt = """
Press keys

W E   T Y U   O P
A S D F G H J K L ;

The above should be
seen as piano keys.

Using lower/upper
letters changes the
octave.
"""

tk = tkinter.Tk()
tk.title("Keyboard Example")
lbl = tkinter.Label(tk, text=txt, font=("Mono", 30))
lbl.pack(expand=True, fill=tkinter.BOTH)

rate = 44100
s, Hz = sHz(rate)
ms = 1e-3 * s
attack = 30 * ms
release = 50 * ms
level = .2 # Highest amplitude value per note

smix = Streamix(True)
cstreams = {}

class ChangeableStream(Stream):
  """
  Stream that can be changed after being used if the limit/append methods are
  called while playing. It uses an iterator that keep taking samples from the
  Stream instead of an iterator to the internal data itself.
  """
  def __iter__(self):
    while True:
      yield next(self._data)

has_after = None

def on_key_down(evt):
  # Ignores key up if it came together with a key down (debounce)
  global has_after
  if has_after:
    tk.after_cancel(has_after)
    has_after = None

  ch = evt.char
  if not ch in cstreams and ch in notes:
    # Prepares the synth
    freq = notes[ch]
    cs = ChangeableStream(level)
    env = line(attack, 0, level).append(cs)
    snd = env * synth(freq * Hz)

    # Mix it, storing the ChangeableStream to be changed afterwards
    cstreams[ch] = cs
    smix.add(0, snd)

def on_key_up(evt):
  global has_after
  has_after = tk.after_idle(on_key_up_process, evt)

def on_key_up_process(evt):
  ch = evt.char
  if ch in cstreams:
    cstreams[ch].limit(0).append(line(release, level, 0))
    del cstreams[ch]

tk.bind("<KeyPress>", on_key_down)
tk.bind("<KeyRelease>", on_key_up)

api = sys.argv[1] if sys.argv[1:] else None # Choose API via command-line
chunks.size = 1 if api == "jack" else 16

with AudioIO(api=api) as player:
  player.play(smix, rate=rate)
  tk.mainloop()

########NEW FILE########
__FILENAME__ = lpc_plot
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Mon Mar 04 2013
# danilo [dot] bellini [at] gmail [dot] com
"""
LPC plot with DFT, showing two formants (magnitude peaks)
"""

from audiolazy import sHz, sin_table, str2freq, lpc
import pylab

rate = 22050
s, Hz = sHz(rate)
size = 512
table = sin_table.harmonize({1: 1, 2: 5, 3: 3, 4: 2, 6: 9, 8: 1}).normalize()

data = table(str2freq("Bb3") * Hz).take(size)
filt = lpc(data, order=14) # Analysis filter
gain = 1e-2 # Gain just for alignment with DFT

# Plots the synthesis filter
# - If blk is given, plots the block DFT together with the filter
# - If rate is given, shows the frequency range in Hz
(gain / filt).plot(blk=data, rate=rate, samples=1024, unwrap=False)
pylab.show()

########NEW FILE########
__FILENAME__ = lptv
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Thu Apr 25 2013
# danilo [dot] bellini [at] gmail [dot] com
"""
LPTV (Linear Periodically Time Variant) filter example (a.k.a. PLTV)
"""

from audiolazy import sHz, sinusoid, Stream, AudioIO, z, pi
import time

# Basic initialization
rate = 44100
s, Hz = sHz(rate)

# Some time-variant coefficients
cycle_a1 = [.1, .2, .1, 0, -.1, -.2, -.1, 0]
cycle_a2 = [.1, 0, -.1, 0, 0]
a1 = Stream(*cycle_a1)
a2 = Stream(*cycle_a2) * 2
b1 = sinusoid(18 * Hz) # Sine phase
b2 = sinusoid(freq=7 * Hz, phase=pi/2) # Cosine phase

# The filter
filt = (1 + b1 * z ** -1 + b2 * z ** -2 + .7 * z ** -5)
filt /= (1 - a1 * z ** -1 - a2 * z ** -2 - .1 * z ** -3)

# A really simple input
input_data = sinusoid(220 * Hz)

# Let's play it!
with AudioIO() as player:
  th = player.play(input_data, rate=rate)
  time.sleep(1) # Wait a sec
  th.stop()
  time.sleep(1) # One sec "paused"
  player.play(filt(input_data), rate=rate) # It's nice with rate/2 here =)
  time.sleep(3) # Play the "filtered" input (3 secs)

# Quiz!
#
# Question 1: What's the filter "cycle" duration?
# Hint: Who cares?
#
# Question 2: Does the filter need to be periodic?
# Hint: Import white_noise and try to put this before defining the filt:
#   a1 *= white_noise()
#   a2 *= white_noise()
#
# Question 3: Does the input need to be periodic?
# Hint: Import comb and white_noise. Now try to use this as the input:
#   .9 * sinusoid(220 * Hz) + .01 * comb(200, .9)(white_noise())

########NEW FILE########
__FILENAME__ = mcfm
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Thu Oct 11 2012
# danilo [dot] bellini [at] gmail [dot] com
"""
Modulo Counter graphics with FM synthesis audio in a wxPython application
"""

# The GUI in this example is based on the dose TDD semaphore source code
# https://github.com/danilobellini/dose

import wx
from math import pi
from audiolazy import (ControlStream, modulo_counter,
                       AudioIO, sHz, sinusoid)

MIN_WIDTH = 15 # pixels
MIN_HEIGHT = 15
FIRST_WIDTH = 200
FIRST_HEIGHT = 200
MOUSE_TIMER_WATCH = 50 # ms
DRAW_TIMER = 50

s, Hz = sHz(44100)

class McFMFrame(wx.Frame):

  def __init__(self, parent):
    frame_style = (wx.FRAME_SHAPED |     # Allows wx.SetShape
                   wx.FRAME_NO_TASKBAR |
                   wx.STAY_ON_TOP |
                   wx.NO_BORDER
                  )
    super(McFMFrame, self).__init__(parent, style=frame_style)
    self.Bind(wx.EVT_ERASE_BACKGROUND, lambda evt: None)
    self._paint_width, self._paint_height = 0, 0 # Ensure update_sizes at
                                                 # first on_paint
    self.ClientSize = (FIRST_WIDTH, FIRST_HEIGHT)
    self.Bind(wx.EVT_PAINT, self.on_paint)
    self._draw_timer = wx.Timer(self)
    self.Bind(wx.EVT_TIMER, self.on_draw_timer, self._draw_timer)
    self.on_draw_timer()
    self.angstep = ControlStream(pi/90)
    self.rotstream = modulo_counter(modulo=2*pi, step=self.angstep)
    self.rotation_data = iter(self.rotstream)

  def on_draw_timer(self, evt=None):
    self.Refresh()
    self._draw_timer.Start(DRAW_TIMER, True)

  def on_paint(self, evt):
    dc = wx.AutoBufferedPaintDCFactory(self)
    gc = wx.GraphicsContext.Create(dc) # Anti-aliasing

    gc.SetPen(wx.Pen("blue", width=4))
    gc.SetBrush(wx.Brush("black"))
    w, h = self.ClientSize
    gc.DrawRectangle(0, 0, w, h)

    gc.SetPen(wx.Pen("gray", width=2))
    w, h = w - 10, h - 10
    gc.Translate(5, 5)
    gc.DrawEllipse(0, 0, w, h)
    gc.SetPen(wx.Pen("red", width=1))
    gc.SetBrush(wx.Brush("yellow"))
    gc.Translate(w * .5, h * .5)
    gc.Scale(w, h)
    rot = next(self.rotation_data)
    gc.Rotate(-rot)
    gc.Translate(.5, 0)
    gc.Rotate(rot)
    gc.Scale(1./w, 1./h)
    gc.DrawEllipse(-5, -5, 10, 10)


class InteractiveFrame(McFMFrame):
  def __init__(self, parent):
    super(InteractiveFrame, self).__init__(parent)
    self._timer = wx.Timer(self)
    self.Bind(wx.EVT_RIGHT_DOWN, self.on_right_down)
    self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
    self.Bind(wx.EVT_TIMER, self.on_timer, self._timer)

  @property
  def player(self):
    return self._player

  @player.setter
  def player(self, value):
    # Also initialize playing thread
    self._player = value
    self.volume_ctrl = ControlStream(.2)
    self.carrier_ctrl = ControlStream(220)
    self.mod_ctrl = ControlStream(440)
    sound = sinusoid(freq=self.carrier_ctrl * Hz,
                     phase=sinusoid(self.mod_ctrl * Hz)
                    ) * self.volume_ctrl
    self.playing_thread = player.play(sound)

  def on_right_down(self, evt):
    self.Close()

  def on_left_down(self, evt):
    self._key_state = None # Ensures initialization
    self.on_timer(evt)

  def on_timer(self, evt):
    """
    Keep watching the mouse displacement via timer
    Needed since EVT_MOVE doesn't happen once the mouse gets outside the
    frame
    """
    ctrl_is_down = wx.GetKeyState(wx.WXK_CONTROL)
    ms = wx.GetMouseState()

    # New initialization when keys pressed change
    if self._key_state != ctrl_is_down:
      self._key_state = ctrl_is_down

      # Keep state at click
      self._click_ms_x, self._click_ms_y = ms.x, ms.y
      self._click_frame_x, self._click_frame_y = self.Position
      self._click_frame_width, self._click_frame_height = self.ClientSize

      # Avoids refresh when there's no move (stores last mouse state)
      self._last_ms = ms.x, ms.y

      # Quadrant at click (need to know how to resize)
      width, height = self.ClientSize
      self._quad_signal_x = 1 if (self._click_ms_x -
                                  self._click_frame_x) / width > .5 else -1
      self._quad_signal_y = 1 if (self._click_ms_y -
                                  self._click_frame_y) / height > .5 else -1

    # "Polling watcher" for mouse left button while it's kept down
    if ms.leftDown:
      if self._last_ms != (ms.x, ms.y): # Moved?
        self._last_ms = (ms.x, ms.y)
        delta_x = ms.x - self._click_ms_x
        delta_y = ms.y - self._click_ms_y

        # Resize
        if ctrl_is_down:
          # New size
          new_w = max(MIN_WIDTH, self._click_frame_width +
                                 2 * delta_x * self._quad_signal_x
                     )
          new_h = max(MIN_HEIGHT, self._click_frame_height +
                                  2 * delta_y * self._quad_signal_y
                     )
          self.ClientSize = new_w, new_h
          self.SendSizeEvent() # Needed for wxGTK

          # Center should be kept
          center_x = self._click_frame_x + self._click_frame_width / 2
          center_y = self._click_frame_y + self._click_frame_height / 2
          self.Position = (center_x - new_w / 2,
                           center_y - new_h / 2)

          self.Refresh()
          self.volume_ctrl.value = (new_h * new_w) / 3e5

        # Move the window
        else:
          self.Position = (self._click_frame_x + delta_x,
                           self._click_frame_y + delta_y)

          # Find the new center position
          x, y = self.Position
          w, h = self.ClientSize
          cx, cy = x + w/2, y + h/2
          self.mod_ctrl.value = 2.5 * cx
          self.carrier_ctrl.value = 2.5 * cy
          self.angstep.value = (cx + cy) * pi * 2e-4

      # Since left button is kept down, there should be another one shot
      # timer event again, without creating many timers like wx.CallLater
      self._timer.Start(MOUSE_TIMER_WATCH, True)


class McFMApp(wx.App):

  def OnInit(self):
    self.SetAppName("mcfm")
    self.wnd = InteractiveFrame(None)
    self.wnd.Show()
    self.SetTopWindow(self.wnd)
    return True # Needed by wxPython


if __name__ == "__main__":
  with AudioIO() as player:
    app = McFMApp(False, player)
    app.wnd.player = player
    app.MainLoop()

########NEW FILE########
__FILENAME__ = pi
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Sun May 05 2013
# danilo [dot] bellini [at] gmail [dot] com
"""
Calculate "pi" using the Madhava-Gregory-Leibniz series and Machin formula
"""

from __future__ import division, print_function
from audiolazy import Stream, thub, count, z, pi # For comparison

def mgl_seq(x):
  """
  Sequence whose sum is the Madhava-Gregory-Leibniz series.

    [x,  -x^3/3, x^5/5, -x^7/7, x^9/9, -x^11/11, ...]

  Returns
  -------
    An endless sequence that has the property
    ``atan(x) = sum(mgl_seq(x))``.
    Usually you would use the ``atan()`` function, not this one.

  """
  odd_numbers = thub(count(start=1, step=2), 2)
  return Stream(1, -1) * x ** odd_numbers / odd_numbers


def atan_mgl(x, n=10):
  """
  Finds the arctan using the Madhava-Gregory-Leibniz series.
  """
  acc = 1 / (1 - z ** -1) # Accumulator filter
  return acc(mgl_seq(x)).skip(n-1).take()


if __name__ == "__main__":
  print("Reference (for comparison):", repr(pi))
  print()

  print("Machin formula (fast)")
  pi_machin = 4 * (4 * atan_mgl(1/5) - atan_mgl(1/239))
  print("Found:", repr(pi_machin))
  print("Error:", repr(abs(pi - pi_machin)))
  print()

  print("Madhava-Gregory-Leibniz series for 45 degrees (slow)")
  pi_mgl_series = 4 * atan_mgl(1, n=1e6) # Sums 1,000,000 items...slow...
  print("Found:", repr(pi_mgl_series))
  print("Error:", repr(abs(pi - pi_mgl_series)))
  print()

########NEW FILE########
__FILENAME__ = play_bach_choral
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Mon Jan 28 2013
# danilo [dot] bellini [at] gmail [dot] com
"""
Random Bach Choral playing example (needs Music21 corpus)
"""

from __future__ import unicode_literals, print_function
from music21 import corpus
from music21.expressions import Fermata
import audiolazy as lz
import random, operator, sys, time
from functools import reduce


def ks_synth(freq):
  """
  Synthesize the given frequency into a Stream by using a model based on
  Karplus-Strong.
  """
  ks_mem = (sum(lz.sinusoid(x * freq) for x in [1, 3, 9]) +
            lz.white_noise() + lz.Stream(-1, 1)) / 5
  return lz.karplus_strong(freq, memory=ks_mem)


def get_random_choral(log=True):
  """ Gets a choral from the J. S. Bach chorals corpus (in Music21). """
  choral_file = corpus.getBachChorales()[random.randint(0, 399)]
  choral = corpus.parse(choral_file)
  if log:
    print("Chosen choral:", choral.metadata.title)
  return choral


def m21_to_stream(score, synth=ks_synth, beat=90, fdur=2., pad_dur=.5,
                  rate=lz.DEFAULT_SAMPLE_RATE):
  """
  Converts Music21 data to a Stream object.

  Parameters
  ----------
  score :
    A Music21 data, usually a music21.stream.Score instance.
  synth :
    A function that receives a frequency as input and should yield a Stream
    instance with the note being played.
  beat :
    The BPM (beats per minute) value to be used in playing.
  fdur :
    Relative duration of a fermata. For example, 1.0 ignores the fermata, and
    2.0 (default) doubles its duration.
  pad_dur :
    Duration in seconds, but not multiplied by ``s``, to be used as a
    zero-padding ending event (avoids clicks at the end when playing).
  rate :
    The sample rate, given in samples per second.

  """
  # Configuration
  s, Hz = lz.sHz(rate)
  step = 60. / beat * s

  # Creates a score from the music21 data
  score = reduce(operator.concat,
                 [[(pitch.frequency * Hz, # Note
                    note.offset * step, # Starting time
                    note.quarterLength * step, # Duration
                    Fermata in note.expressions) for pitch in note.pitches]
                                                 for note in score.flat.notes]
                )

  # Mix all notes into song
  song = lz.Streamix()
  last_start = 0
  for freq, start, dur, has_fermata in score:
    delta = start - last_start
    if has_fermata:
      delta *= 2
    song.add(delta, synth(freq).limit(dur))
    last_start = start

  # Zero-padding and finishing
  song.add(dur + pad_dur * s, lz.Stream([]))
  return song


# Play the song!
if __name__ == "__main__":
  rate = 44100
  while True:
    with lz.AudioIO(True) as player:
      player.play(m21_to_stream(get_random_choral(), rate=rate), rate=rate)
    if not "loop" in sys.argv[1:]:
      break
    time.sleep(3)

########NEW FILE########
__FILENAME__ = save_and_memoize_synth
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Tue Oct 29 04:33:45 2013
# danilo [dot] bellini [at] gmail [dot] com
"""
Random synthesis with saving and memoization
"""

from __future__ import division
from audiolazy import (sHz, octaves, chain, adsr, gauss_noise, sin_table, pi,
                       sinusoid, lag2freq, Streamix, zeros, clip, lowpass,
                       TableLookup, line, inf, xrange, thub, chunks)
from random import choice, uniform, randint
from functools import wraps, reduce
from contextlib import closing
import operator, wave


#
# Helper functions
#
def memoize(func):
  """
  Decorator for unerasable memoization based on function arguments, for
  functions without keyword arguments.
  """
  class Memoizer(dict):
    def __missing__(self, args):
      val = func(*args)
      self[args] = val
      return val
  memory = Memoizer()
  @wraps(func)
  def wrapper(*args):
    return memory[args]
  return wrapper


def save_to_16bit_wave_file(fname, sig, rate):
  """
  Save a given signal ``sig`` to file ``fname`` as a 16-bit one-channel wave
  with the given ``rate`` sample rate.
  """
  with closing(wave.open(fname, "wb")) as wave_file:
    wave_file.setnchannels(1)
    wave_file.setsampwidth(2)
    wave_file.setframerate(rate)
    for chunk in chunks((clip(sig) * 2 ** 15).map(int), dfmt="h", padval=0):
      wave_file.writeframes(chunk)


#
# AudioLazy Initialization
#
rate = 44100
s, Hz = sHz(rate)
ms = 1e-3 * s

# Frequencies (always in Hz here)
freq_base = 440
freq_min = 100
freq_max = 8000
ratios = [1/1, 8/7, 7/6, 3/2, 49/32, 7/4] # 2/1 is the next octave
concat = lambda iterables: reduce(operator.concat, iterables, [])
oct_partial = lambda freq: octaves(freq, fmin = freq_min, fmax = freq_max)
freqs = concat(oct_partial(freq_base * ratio) for ratio in ratios)


#
# Audio synthesis models
#
def freq_gen():
  """
  Endless frequency generator (in rad/sample).
  """
  while True:
    yield choice(freqs) * Hz


def new_note_track(env, synth):
  """
  Audio track with the frequencies.

  Parameters
  ----------
  env:
    Envelope Stream (which imposes the duration).
  synth:
    One-argument function that receives a frequency (in rad/sample) and
    returns a Stream instance (a synthesized note).

  Returns
  -------
  Endless Stream instance that joins synthesized notes.

  """
  list_env = list(env)
  return chain.from_iterable(synth(freq) * list_env for freq in freq_gen())


@memoize
def unpitched_high(dur, idx):
  """
  Non-harmonic treble/higher frequency sound as a list (due to memoization).

  Parameters
  ----------
  dur:
    Duration, in samples.
  idx:
    Zero or one (integer), for a small difference to the sound played.

  Returns
  -------
  A list with the synthesized note.

  """
  first_dur, a, d, r, gain = [
    (30 * ms, 10 * ms, 8 * ms, 10 * ms, .4),
    (60 * ms, 20 * ms, 8 * ms, 20 * ms, .5)
  ][idx]
  env = chain(adsr(first_dur, a=a, d=d, s=.2, r=r),
              adsr(dur - first_dur,
                   a=10 * ms, d=30 * ms, s=.2, r=dur - 50 * ms))
  result = gauss_noise(dur) * env * gain
  return list(result)


# Values used by the unpitched low synth
harmonics = dict(enumerate([3] * 4 + [2] * 4 + [1] * 10))
low_table = sin_table.harmonize(harmonics).normalize()


@memoize
def unpitched_low(dur, idx):
  """
  Non-harmonic bass/lower frequency sound as a list (due to memoization).

  Parameters
  ----------
  dur:
    Duration, in samples.
  idx:
    Zero or one (integer), for a small difference to the sound played.

  Returns
  -------
  A list with the synthesized note.

  """
  env = sinusoid(lag2freq(dur * 2)).limit(dur) ** 2
  freq = 40 + 20 * sinusoid(1000 * Hz, phase=uniform(-pi, pi)) # Hz
  result = (low_table(freq * Hz) + low_table(freq * 1.1 * Hz)) * env * .5
  return list(result)


def geometric_delay(sig, dur, copies, pamp=.5):
  """
  Delay effect by copying data (with Streamix).

  Parameters
  ----------
  sig:
    Input signal (an iterable).
  dur:
    Duration, in samples.
  copies:
    Number of times the signal will be replayed in the given duration. The
    signal is played copies + 1 times.
  pamp:
    The relative remaining amplitude fraction for the next played Stream,
    based on the idea that total amplitude should sum to 1. Defaults to 0.5.

  """
  out = Streamix()
  sig = thub(sig, copies + 1)
  out.add(0, sig * pamp) # Original
  remain = 1 - pamp
  for unused in xrange(copies):
    gain = remain * pamp
    out.add(dur / copies, sig * gain)
    remain -= gain
  return out


#
# Audio mixture
#
tracks = 3 # besides unpitched track
dur_note = 120 * ms
dur_perc = 100 * ms
smix = Streamix()

# Pitched tracks based on a 1:2 triangular wave
table = TableLookup(line(100, -1, 1).append(line(200, 1, -1)).take(inf))
for track in xrange(tracks):
  env = adsr(dur_note, a=20 * ms, d=10 * ms, s=.8, r=30 * ms) / 1.7 / tracks
  smix.add(0, geometric_delay(new_note_track(env, table), 80 * ms, 2))

# Unpitched tracks
pfuncs = [unpitched_low] * 4 + [unpitched_high]
snd = chain.from_iterable(choice(pfuncs)(dur_perc, randint(0, 1))
                          for unused in zeros())
smix.add(0, geometric_delay(snd * (1 - 1/1.7), 20 * ms, 1))


#
# Finishes (save in a wave file)
#
data = lowpass(5000 * Hz)(smix).limit(180 * s)
fname = "audiolazy_save_and_memoize_synth.wav"
save_to_16bit_wave_file(fname, data, rate)

########NEW FILE########
__FILENAME__ = shepard
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Thu Feb 07 2013
# danilo [dot] bellini [at] gmail [dot] com
"""
Example based on the Shepard tone
"""

from __future__ import division
from audiolazy import sHz, Streamix, log2, line, window, sinusoid, AudioIO

# Basic initialization
rate = 44100
s, Hz = sHz(rate)
kHz = 1e3 * Hz

# Some parameters
table_len = 8192
min_freq = 20 * Hz
max_freq = 10 * kHz
duration = 60 * s

# "Track-by-track" partials configuration
noctaves = abs(log2(max_freq/min_freq))
octave_duration = duration / noctaves
smix = Streamix()
data = [] # Global: keeps one parcial "track" for all uses (but the first)

# Inits "data"
def partial():
  smix.add(octave_duration, partial_cached()) # Next track/partial event
  # Octave-based frequency values sequence
  scale = 2 ** line(duration, finish=True)
  partial_freq = (scale - 1) * (max_freq - min_freq) + min_freq
  # Envelope to "hide" the partial beginning/ending
  env = [k ** 2 for k in window.hamming(int(round(duration)))]
  # The generator, properly:
  for el in env * sinusoid(partial_freq) / noctaves:
    data.append(el)
    yield el

# Replicator ("track" data generator)
def partial_cached():
  smix.add(octave_duration, partial_cached()) # Next track/partial event
  for el in data:
    yield el

# Play!
smix.add(0, partial()) # Starts the mixing with the first track/partial
with AudioIO(True) as player:
  player.play(smix, rate=rate)

########NEW FILE########
__FILENAME__ = windows_plot
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Fri Nov 02 2012
# danilo [dot] bellini [at] gmail [dot] com
"""
Window functions plot example
"""

from matplotlib import pyplot as plt
from audiolazy import window

M = 256

for func in window:
  plt.plot(func(M), label=func.__name__)

plt.legend(loc="best")
plt.axis(xmin=-5, xmax=M + 5 - 1, ymin=-.05, ymax=1.05)
plt.title("AudioLazy windows for size of {M} samples".format(M=M))
plt.tight_layout()
plt.show()

########NEW FILE########
__FILENAME__ = zcross_pitch
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This file is part of AudioLazy, the signal processing Python package.
# Copyright (C) 2012-2013 Danilo de Jesus da Silva Bellini
#
# AudioLazy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Created on Tue Mar 05 2013
# danilo [dot] bellini [at] gmail [dot] com
"""
Pitch follower via zero-crossing rate with Tkinter GUI
"""

# ------------------------
# AudioLazy pitch follower
# ------------------------
from audiolazy import (tostream, zcross, lag2freq, AudioIO, freq2str, sHz,
                       lowpass, envelope, pi, maverage, Stream, thub)

def limiter(sig, threshold=.1, size=256, env=envelope.rms, cutoff=pi/2048):
  sig = thub(sig, 2)
  return sig * Stream( 1. if el <= threshold else threshold / el
                       for el in maverage(size)(env(sig, cutoff=cutoff)) )

@tostream
def zcross_pitch(sig, size=2048, hop=None):
  for blk in zcross(sig, hysteresis=.01).blocks(size=size, hop=hop):
    crossings = sum(blk)
    yield 0. if crossings == 0 else lag2freq(2. * size / crossings)


def pitch_from_mic(upd_time_in_ms):
  rate = 44100
  s, Hz = sHz(rate)

  with AudioIO() as recorder:
    snd = recorder.record(rate=rate)
    sndlow = lowpass(400 * Hz)(limiter(snd, cutoff=20 * Hz))
    hop = int(upd_time_in_ms * 1e-3 * s)
    for pitch in freq2str(zcross_pitch(sndlow, size=2*hop, hop=hop) / Hz):
      yield pitch


# ----------------
# GUI with tkinter
# ----------------
if __name__ == "__main__":
  try:
    import tkinter
  except ImportError:
    import Tkinter as tkinter
  import threading
  import re

  # Window (Tk init), text label and button
  tk = tkinter.Tk()
  tk.title(__doc__.strip().splitlines()[0])
  lbldata = tkinter.StringVar(tk)
  lbltext = tkinter.Label(tk, textvariable=lbldata, font=("Purisa", 72),
                          width=10)
  lbltext.pack(expand=True, fill=tkinter.BOTH)
  btnclose = tkinter.Button(tk, text="Close", command=tk.destroy,
                            default="active")
  btnclose.pack(fill=tkinter.X)

  # Needed data
  regex_note = re.compile(r"^([A-Gb#]*-?[0-9]*)([?+-]?)(.*?%?)$")
  upd_time_in_ms = 200

  # Update functions for each thread
  def upd_value(): # Recording thread
    pitches = iter(pitch_from_mic(upd_time_in_ms))
    while not tk.should_finish:
      tk.value = next(pitches)

  def upd_timer(): # GUI mainloop thread
    lbldata.set("\n".join(regex_note.findall(tk.value)[0]))
    tk.after(upd_time_in_ms, upd_timer)

  # Multi-thread management initialization
  tk.should_finish = False
  tk.value = freq2str(0) # Starting value
  lbldata.set(tk.value)
  tk.upd_thread = threading.Thread(target=upd_value)

  # Go
  tk.upd_thread.start()
  tk.after_idle(upd_timer)
  tk.mainloop()
  tk.should_finish = True
  tk.upd_thread.join()

########NEW FILE########
