__FILENAME__ = listen
import Queue
import threading
import time
import pyaudio
import numpy as np
import quietnet
import options
import sys
import psk

FORMAT = pyaudio.paInt16
frame_length = options.frame_length
chunk = options.chunk
search_freq = options.freq
rate = options.rate
sigil = [int(x) for x in options.sigil]
frames_per_buffer = chunk * 10

in_length = 4000
# raw audio frames
in_frames = Queue.Queue(in_length)
# the value of the fft at the frequency we care about
points = Queue.Queue(in_length)
bits = Queue.Queue(in_length / frame_length)

wait_for_sample_timeout = 0.1
wait_for_frames_timeout = 0.1
wait_for_point_timeout = 0.1
wait_for_byte_timeout = 0.1

# yeeeep this is just hard coded
bottom_threshold = 8000

def process_frames():
    while True:
        try:
            frame = in_frames.get(False)
            fft = quietnet.fft(frame)
            point = quietnet.has_freq(fft, search_freq, rate, chunk)
            points.put(point)
        except Queue.Empty:
            time.sleep(wait_for_frames_timeout)

def process_points():
    while True:
        cur_points = []
        while len(cur_points) < frame_length:
            try:
                cur_points.append(points.get(False))
            except Queue.Empty:
                time.sleep(wait_for_point_timeout)

        while True:
            while np.average(cur_points) > bottom_threshold:
                try:
                    cur_points.append(points.get(False))
                    cur_points = cur_points[1:]
                except Queue.Empty:
                    time.sleep(wait_for_point_timeout)
            next_point = None
            while next_point == None:
                try:
                    next_point = points.get(False)
                except Queue.Empty:
                    time.sleep(wait_for_point_timeout)
            if next_point > bottom_threshold:
                bits.put(0)
                bits.put(0)
                cur_points = [cur_points[-1]]
                break
        print("")

        last_bits = []
        while True:
            if len(cur_points) == frame_length:
                bit = int(quietnet.get_bit(cur_points, frame_length) > bottom_threshold)
                cur_points = []
                bits.put(bit)
                last_bits.append(bit)
            # if we've only seen low bits for a while assume the next message might not be on the same bit boundary
            if len(last_bits) > 3:
                if sum(last_bits) == 0:
                    break
                last_bits = last_bits[1:]
            try:
                cur_points.append(points.get(False))
            except Queue.Empty:
                time.sleep(wait_for_point_timeout)

def process_bits():
    while True:
        cur_bits = []
        # while the last two characters are not the sigil
        while len(cur_bits) < 2 or cur_bits[-len(sigil):len(cur_bits)] != sigil:
            try:
                cur_bits.append(bits.get(False))
            except Queue.Empty:
                time.sleep(wait_for_byte_timeout)
        sys.stdout.write(psk.decode(cur_bits[:-len(sigil)]))
        sys.stdout.flush()

# start the queue processing threads
processes = [process_frames, process_points, process_bits]
threads = []

for process in processes:
    thread = threading.Thread(target=process)
    thread.daemon = True
    thread.start()

def callback(in_data, frame_count, time_info, status):
    frames = list(quietnet.chunks(quietnet.unpack(in_data), chunk))
    for frame in frames:
        if not in_frames.full():
            in_frames.put(frame, False)
    return (in_data, pyaudio.paContinue)

def start_analysing_stream():
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=options.channels, rate=options.rate,
        input=True, frames_per_buffer=frames_per_buffer, stream_callback=callback)
    stream.start_stream()
    while stream.is_active():
        time.sleep(wait_for_sample_timeout)

sys.stdout.write("Quietnet listening at %sHz" % search_freq)
sys.stdout.flush()
start_analysing_stream()

########NEW FILE########
__FILENAME__ = capture_audio
import pyaudio

FORMAT = pyaudio.paInt16
CHANNELS = 1

def capture_buffers(num_buffers, chunk, rate, skip=None):
    if skip == None:
        skip = rate / 2

    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=rate, input=True, frames_per_buffer=chunk)
    
    # ignore some data at the beginning as it is usually weird
    if skip > 0:
        data = stream.read(skip)
    
    buffers = [stream.read(chunk) for i in range(0, num_buffers)]  
    
    # close the audio stream
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    return buffers

def capture_seconds(num_seconds, chunksize, rate, width):
    num_buffers = int(float(num_seconds * rate) / chunksize)
    return capture_buffers(num_buffers, chunksize, rate, width)


########NEW FILE########
__FILENAME__ = test
"""
Matplotlib Animation Example

author: Jake Vanderplas
email: vanderplas@astro.washington.edu
website: http://jakevdp.github.com
license: BSD
Please feel free to use and modify this, but keep the above information. Thanks!
"""

import numpy as np
from matplotlib import pyplot as plt
from matplotlib import animation

# First set up the figure, the axis, and the plot element we want to animate
fig = plt.figure()
ax = plt.axes(xlim=(0, 2), ylim=(-2, 2))
line, = ax.plot([], [], lw=2)

# initialization function: plot the background of each frame
def init():
    line.set_data([], [])
    return line,

# animation function.  This is called sequentially
def animate(i):
    x = np.linspace(0, 2, 1000)
    y = np.sin(2 * np.pi * (x - 0.01 * i))
    line.set_data(x, y)
    return line,

# call the animator.  blit=True means only re-draw the parts that have changed.
anim = animation.FuncAnimation(fig, animate, init_func=init,
                               frames=200, interval=20, blit=True)

# save the animation as an mp4.  This requires ffmpeg or mencoder to be
# installed.  The extra_args ensure that the x264 codec is used, so that
# the video can be embedded in html5.  You may need to adjust this for
# your system: for more information, see
# http://matplotlib.sourceforge.net/api/animation_api.html
anim.save('basic_animation.mp4', fps=30, extra_args=['-vcodec', 'libx264'])

plt.show()

########NEW FILE########
__FILENAME__ = options
rate = 44100
freq = 19100# chosen because it is outside most people's hearing and worked for my microphone and speakers
channels = 1
frame_length = 3
chunk = 256
datasize = chunk * frame_length
sigil = "00"

########NEW FILE########
__FILENAME__ = psk
psk = {
" "  :"1",
"!" :"111111111",
'"' :"101011111",
'#'   :"111110101",
'$'   :"111011011",
'%'   :"1011010101",
'&'   :"1010111011",
"'"   :"101111111",
'('   :"11111011",
')'   :"11110111",
'*'   :"101101111",
'+'   :"111011111",
','   :"1110101",
'-'   :"110101",
'.'   :"1010111",
'/'   :"110101111",
'0'   :"10110111",
'1'   :"10111101",
'2'   :"11101101",
'3'   :"11111111",
'4'   :"101110111",
'5'   :"101011011",
'6'   :"101101011",
'7'   :"110101101",
'8'   :"110101011",
'9'   :"110110111",
':'   :"11110101",
';'   :"110111101",
'<'   :"111101101",
'='   :"1010101",
'>'   :"111010111",
'?'   :"1010101111",
'@'   :"1010111101",
'A'   :"1111101",
'B'   :"11101011",
'C'   :"10101101",
'D'   :"10110101",
'E'   :"1110111",
'F'   :"11011011",
'G'   :"11111101",
'H'   :"101010101",
'I'   :"1111111",
'J'   :"111111101",
'K'   :"101111101",
'L'   :"11010111",
'M'   :"10111011",
'N'   :"11011101",
'O'   :"10101011",
'P'   :"11010101",
'Q'   :"111011101",
'R'   :"10101111",
'S'   :"1101111",
'T'   :"1101101",
'U'   :"101010111",
'V'   :"110110101",
'W'   :"101011101",
'X'   :"101110101",
'Y'   :"101111011",
'Z'   :"1010101101",
'['   :"111110111",
'\\'   :"111101111",
']'   :"111111011",
'^'   :"1010111111",
'_'   :"101101101",
'`'   :"1011011111",
'a'   :"1011",
'b'   :"1011111",
'c'   :"101111",
'd'   :"101101",
'e'   :"11",
'f'   :"111101",
'g'   :"1011011",
'h'   :"101011",
'i'   :"1101",
'j'   :"111101011",
'k'   :"10111111",
'l'   :"11011",
'm'   :"111011",
'n'   :"1111",
'o'   :"111",
'p'   :"111111",
'q'   :"110111111",
'r'   :"10101",
's'   :"10111",
't'   :"101",
'u'   :"110111",
'v'   :"1111011",
'w'   :"1101011",
'x'   :"11011111",
'y'   :"1011101",
'z'   :"111010101",
'{'   :"1010110111",
'|'   :"110111011",
'}'   :"1010110101",
'~'   :"1011010111",
}

decode_psk = {}
for k, v in psk.items():
    decode_psk[v] = k

def encode(string):
    result = []
    for c in string:
        result.append(psk[c])
    return '00'.join(result) + '00'

def decode(string):
    try:
        return decode_psk[''.join([str(i) for i in string])]
    except:
        return ''

########NEW FILE########
__FILENAME__ = quietnet
import numpy as np
import struct
import math

# let us use input in python 2.x.
try: input = raw_input
except NameError: pass

# split something into chunks
def chunks(l, n):
    for i in xrange(0, len(l), n):
        yield l[i:i+n]

def unpack(buffer):
    return unpack_buffer(list(chunks(buffer, 2)))

def unpack_buffer(buffer):
    return [struct.unpack('h', frame)[0] for frame in buffer]

def pack_buffer(buffer):
    return [struct.pack('h', frame) for frame in buffer]

def fft(signal):
    return np.abs(np.fft.rfft(signal))

def get_peak(hertz, rate, chunk):
    return int(round((float(hertz) / rate) * chunk))

def weighted_values_around_peak(in_data, peak_index, offset):
    period = math.pi / (offset * 2)

    out_data = []
    for i in range(len(in_data)):
        if i >= peak_index - offset and i <= peak_index + offset:
            out_data.append(in_data[i] * np.abs(math.sin((period * (i - peak_index + offset)) + (math.pi / 2.0))))
        else:
            out_data.append(0)
    return out_data

def has_freq(fft_sample, freq_in_hertz, rate, chunk, offset=3):
    peak_index = get_peak(freq_in_hertz, rate, chunk)
    top = max(fft_sample[peak_index-1:peak_index+2])

    avg_around_peak = np.average(weighted_values_around_peak(fft_sample, peak_index, offset))

    if top > avg_around_peak:
        return fft_sample[peak_index]
    else:
        return 0

def get_signal(buffer):
    unpacked_buffer = unpack_buffer(list(chunks(buffer, 2)))
    return np.array(unpacked_buffer, dtype=float)

def raw_has_freq(buffer, freq_in_hertz, rate, chunk):
    fft_sample = fft(get_signal(buffer))
    return has_freq(fft_sample, freq_in_hertz, rate, chunk)

def get_freq_over_time(ffts, search_freq, chunk=1024, rate=44100):
    return [has_freq(fft, search_freq, rate, chunk) for fft in ffts]

def get_points(freq_samples, frame_length, threshold=None, last_point=0):
    if threshold == None:
        threshold = np.median(freq_samples)
    points = []
    for i in range(len(freq_samples)):
        freq_value = freq_samples[i]
        point = 0
        if freq_value > threshold:
            # ignore big changes in frequency when they aren't near the frame transition
            if last_point == 1 or (i % frame_length) <= 2:
                point = 1
            else:
                point = 0
        points.append(point)
        last_point = point
    return points

def get_bits(points, frame_length):
    return [int(round(sum(c) / float(frame_length))) for c in list(chunks(points, frame_length)) if len(c) == frame_length]

def get_bit(points, frame_length):
    return int(round(sum(points) / float(frame_length)))

def get_bytes(bits, sigil):
    i = 0
    # scan for the first occurance of the sigil
    while i < len(bits) - len(sigil):
        if bits[i:i+len(sigil)] == sigil:
            i += len(sigil)
            break
        i += 1
    return [l for l in list(chunks(bits[i:], 8)) if len(l) == 8]

def decode_byte(l):
    byte_string = ''.join([str(bit) for bit in l])
    return chr(int(byte_string, base=2))

def decode(bytes):
    string = ""
    for byte in bytes:
        byte = ''.join([str(bit) for bit in byte])
        string += chr(int(byte, base=2))
    return string

def tone(freq=400, datasize=4096, rate=44100, amp=12000.0, offset=0):
    sine_list=[]
    for x in range(datasize):
        samp = math.sin(2*math.pi*freq*((x + offset)/float(rate)))
        sine_list.append(int(samp*amp))
    return sine_list

def envelope(in_data, left=True, right=True, rate=44100):
    half = float(len(in_data)) / 2
    freq = math.pi / (len(in_data) / 2)
    out_data = []

    for x in range(len(in_data)):
        samp = in_data[x]
        if (x < half and left) or (right and x >= half):
            samp = samp * (1 + math.sin(freq*x - (math.pi / 2))) / 2
        out_data.append(int(samp))

    return out_data

########NEW FILE########
__FILENAME__ = send
import sys
import pyaudio
import quietnet
import options
import psk

FORMAT = pyaudio.paInt16
CHANNELS = options.channels
RATE = options.rate
FREQ = options.freq
FREQ_OFF = 0
FRAME_LENGTH = options.frame_length
DATASIZE = options.datasize

p = pyaudio.PyAudio()
stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True)

user_input = input if sys.version_info.major >= 3 else raw_input


def make_buffer_from_bit_pattern(pattern, on_freq, off_freq):
    """ Takes a pattern and returns an audio buffer that encodes that pattern """
    # the key's middle value is the bit's value and the left and right bits are the bits before and after
    # the buffers are enveloped to cleanly blend into each other

    last_bit = pattern[-1]
    output_buffer = []
    offset = 0

    for i in range(len(pattern)):
        bit = pattern[i]
        if i < len(pattern) - 1:
            next_bit = pattern[i+1]
        else:
            next_bit = pattern[0]

        freq = on_freq if bit == '1' else off_freq
        tone = quietnet.tone(freq, DATASIZE, offset=offset)
        output_buffer += quietnet.envelope(tone, left=last_bit=='0', right=next_bit=='0')
        offset += DATASIZE
        last_bit = bit

    return quietnet.pack_buffer(output_buffer)

def play_buffer(buffer):
    output = ''.join(buffer)
    stream.write(output)

if __name__ == "__main__":
    print("Welcome to quietnet. Use ctrl-c to exit")

    try:
        # get user input and play message
        while True:
            message = user_input("> ")
            try:
              pattern = psk.encode(message)
              buffer = make_buffer_from_bit_pattern(pattern, FREQ, FREQ_OFF)
              play_buffer(buffer)
            except KeyError:
              print("Messages may only contain printable ASCII characters.")
    except KeyboardInterrupt:
        # clean up our streams and exit
        stream.stop_stream()
        stream.close()
        p.terminate()
        print("exited cleanly")

########NEW FILE########
