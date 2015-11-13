__FILENAME__ = ffdec
# This file is part of audioread.
# Copyright 2012, Adrian Sampson.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
# 
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

"""Read audio data using the ffmpeg command line tools via a UNIX
pipe.
"""
import subprocess
import re
import threading
import select
import time
from . import DecodeError

class FFmpegError(DecodeError):
    pass

class CommunicationError(FFmpegError):
    """Raised when the output of FFmpeg is not parseable."""

class UnsupportedError(FFmpegError):
    """The file could not be decoded by FFmpeg."""

class NotInstalledError(FFmpegError):
    """Could not find the ffmpeg binary."""

class ReadTimeoutError(FFmpegError):
    """Reading from the ffmpeg command-line tool timed out."""

class ReaderThread(threading.Thread):
    """A thread that consumes data from a filehandle. This is used to ensure
    that a buffer for an input stream never fills up.
    """
    # It may seem a little hacky, but this is the most straightforward &
    # reliable way I can think of to do this. select() is sort of
    # inefficient because it doesn't indicate how much is available to
    # read -- so I end up reading character by character.
    def __init__(self, fh, blocksize=1024):
        super(ReaderThread, self).__init__()
        self.fh = fh
        self.blocksize = blocksize
        self.daemon = True
        self.data = []

    def run(self):
        while True:
            data = self.fh.read(self.blocksize)
            if not data:
                break
            self.data.append(data)

class FFmpegAudioFile(object):
    """An audio file decoded by the ffmpeg command-line utility."""
    def __init__(self, filename):
        try:
            self.proc = subprocess.Popen(
                ['ffmpeg', '-i', filename, '-f', 's16le', '-'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
        except OSError:
            raise NotInstalledError()

        # Read relevant information from stderr.
        self._get_info()

        # Start a separate thread to read the rest of the data from
        # stderr.
        self.stderr_reader = ReaderThread(self.proc.stderr)
        self.stderr_reader.start()

    def read_data(self, block_size=4096, timeout=10.0):
        """Read blocks of raw PCM data from the file."""
        # Read from stdout on this thread.
        start_time = time.time()
        while True:
            # Wait for data to be available or a timeout.
            rready, _, xready = select.select((self.proc.stdout,),
                                              (), (self.proc.stdout,),
                                              timeout)
            end_time = time.time()
            if not rready and not xready:
                if end_time - start_time >= timeout:
                    # Nothing interesting has happened for a while --
                    # FFmpeg is probably hanging.
                    raise ReadTimeoutError(
                        'ffmpeg output: %s' %
                        ''.join(self.stderr_reader.data)
                    )
                else:
                    # Keep waiting.
                    continue
            start_time = end_time

            data = self.proc.stdout.read(block_size)
            if not data:
                break
            yield data

    def _get_info(self):
        """Reads the tool's output from its stderr stream, extracts the
        relevant information, and parses it.
        """
        out_parts = []
        while True:
            line = self.proc.stderr.readline()
            if not line:
                # EOF and data not found.
                raise CommunicationError("stream info not found")
            
            # In Python 3, result of reading from stderr is bytes.
            if isinstance(line, bytes):
                line = line.decode('utf8', 'ignore')
                
            line = line.strip().lower()

            if 'no such file' in line:
                raise IOError('file not found')
            elif 'invalid data found' in line:
                raise UnsupportedError()
            elif 'duration:' in line:
                out_parts.append(line)
            elif 'audio:' in line:
                out_parts.append(line)
                self._parse_info(''.join(out_parts))
                break

    def _parse_info(self, s):
        """Given relevant data from the ffmpeg output, set audio
        parameter fields on this object.
        """
        # Sample rate.
        match = re.search(r'(\d+) hz', s)
        if match:
            self.samplerate = int(match.group(1))
        else:
            self.samplerate = 0

        # Channel count.
        match = re.search(r'hz, ([^,]+),', s)
        if match:
            mode = match.group(1)
            if mode == 'stereo':
                self.channels = 2
            else:
                match = re.match(r'(\d+) ', mode)
                if match:
                    self.channels = int(match.group(1))
                else:
                    self.channels = 1
        else:
            self.channels = 0

        # Duration.
        match = re.search(
            r'duration: (\d+):(\d+):(\d+).(\d)', s
        )
        if match:
            durparts = list(map(int, match.groups()))
            duration = durparts[0] * 60 * 60 + \
                       durparts[1] * 60 + \
                       durparts[2] + \
                       float(durparts[3]) / 10
            self.duration = duration
        else:
            # No duration found.
            self.duration = 0

    def close(self):
        """Close the ffmpeg process used to perform the decoding."""
        if hasattr(self, 'proc') and self.proc.returncode is None:
            self.proc.kill()
            # Flush the stdout buffer (stderr already flushed).
            stdout_reader = ReaderThread(self.proc.stdout)
            stdout_reader.start()
            self.proc.wait()

    def __del__(self):
        self.close()

    # Iteration.
    def __iter__(self):
        return self.read_data()

    # Context manager.
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


########NEW FILE########
__FILENAME__ = gstdec
# This file is part of audioread.
# Copyright 2011, Adrian Sampson.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
# 
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

"""Use Gstreamer to decode audio files.

To read an audio file, pass it to the constructor for GstAudioFile()
and then iterate over the contents:

    >>> f = GstAudioFile('something.mp3')
    >>> try:
    >>>     for block in f:
    >>>         ...
    >>> finally:
    >>>     f.close()

Note that there are a few complications caused by Gstreamer's
asynchronous architecture. This module spawns its own Gobject main-
loop thread; I'm not sure how that will interact with other main
loops if your program has them. Also, in order to stop the thread
and terminate your program normally, you need to call the close()
method on every GstAudioFile you create. Conveniently, the file can be
used as a context manager to make this simpler:

    >>> with GstAudioFile('something.mp3') as f:
    >>>     for block in f:
    >>>         ...

Iterating a GstAudioFile yields strings containing short integer PCM
data. You can also read the sample rate and channel count from the
file:

    >>> with GstAudioFile('something.mp3') as f:
    >>>     print f.samplerate
    >>>     print f.channels
    >>>     print f.duration
"""
from __future__ import with_statement

import gst
import sys
import gobject
import threading
import os
import urllib
import Queue
from . import DecodeError

QUEUE_SIZE = 10
BUFFER_SIZE = 10
SENTINEL = '__GSTDEC_SENTINEL__'


# Exceptions.

class GStreamerError(DecodeError):
    pass

class UnknownTypeError(GStreamerError):
    """Raised when Gstreamer can't decode the given file type."""
    def __init__(self, streaminfo):
        super(UnknownTypeError, self).__init__(
            "can't decode stream: " + streaminfo
        )
        self.streaminfo = streaminfo

class FileReadError(GStreamerError):
    """Raised when the file can't be read at all."""
    pass

class NoStreamError(GStreamerError):
    """Raised when the file was read successfully but no audio streams
    were found.
    """
    def __init__(self):
        super(NoStreamError, self).__init__('no audio streams found')

class MetadataMissingError(GStreamerError):
    """Raised when GStreamer fails to report stream metadata (duration,
    channels, or sample rate).
    """
    pass

class IncompleteGStreamerError(GStreamerError):
    """Raised when necessary components of GStreamer (namely, the
    principal plugin packages) are missing.
    """
    def __init__(self):
        super(IncompleteGStreamerError, self).__init__(
            'missing GStreamer base plugins'
        )


# Managing the Gobject main loop thread.

_shared_loop_thread = None
_loop_thread_lock = threading.RLock()
gobject.threads_init()
def get_loop_thread():
    """Get the shared main-loop thread.
    """
    global _shared_loop_thread
    with _loop_thread_lock:
        if not _shared_loop_thread:
            # Start a new thread.
            _shared_loop_thread = MainLoopThread()
            _shared_loop_thread.start()
        return _shared_loop_thread
class MainLoopThread(threading.Thread):
    """A daemon thread encapsulating a Gobject main loop.
    """
    def __init__(self):   
        super(MainLoopThread, self).__init__()             
        self.loop = gobject.MainLoop()
        self.daemon = True
        
    def run(self):    
        self.loop.run()


# The decoder.

class GstAudioFile(object):
    """Reads raw audio data from any audio file that Gstreamer
    knows how to decode.
    
        >>> with GstAudioFile('something.mp3') as f:
        >>>     print f.samplerate
        >>>     print f.channels
        >>>     print f.duration
        >>>     for block in f:
        >>>         do_something(block)
    
    Iterating the object yields blocks of 16-bit PCM data. Three
    pieces of stream information are also available: samplerate (in Hz),
    number of channels, and duration (in seconds).
    
    It's very important that the client call close() when it's done
    with the object. Otherwise, the program is likely to hang on exit.
    Alternatively, of course, one can just use the file as a context
    manager, as shown above.
    """
    def __init__(self, path):
        self.running = False
        self.finished = False
        
        # Set up the Gstreamer pipeline.
        self.pipeline = gst.Pipeline()
        try:
            self.dec = gst.element_factory_make("uridecodebin")
            self.conv = gst.element_factory_make("audioconvert")
            self.sink = gst.element_factory_make("appsink")
        except gst.ElementNotFoundError:
            # uridecodebin, audioconvert, or appsink is missing. We need
            # gst-plugins-base.
            raise IncompleteGStreamerError()
        
        # Register for bus signals.
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message::eos", self._message)
        bus.connect("message::error", self._message)
        
        # Configure the input.
        uri = 'file://' + urllib.quote(os.path.abspath(path))
        self.dec.set_property("uri", uri)
        # The callback to connect the input.
        self.dec.connect("pad-added", self._pad_added)
        self.dec.connect("no-more-pads", self._no_more_pads)
        # And a callback if decoding failes.
        self.dec.connect("unknown-type", self._unkown_type)
        
        # Configure the output.
        # We want short integer data.
        self.sink.set_property('caps',
            gst.Caps('audio/x-raw-int, width=16, depth=16, signed=true')
        )
        # TODO set endianness?
        # Set up the characteristics of the output. We don't want to
        # drop any data (nothing is real-time here); we should bound
        # the memory usage of the internal queue; and, most
        # importantly, setting "sync" to False disables the default
        # behavior in which you consume buffers in real time. This way,
        # we get data as soon as it's decoded.
        self.sink.set_property('drop', False)
        self.sink.set_property('max-buffers', BUFFER_SIZE)
        self.sink.set_property('sync', False)
        # The callback to receive decoded data.
        self.sink.set_property('emit-signals', True)
        self.sink.connect("new-buffer", self._new_buffer)
        
        # We'll need to know when the stream becomes ready and we get
        # its attributes. This semaphore will become available when the
        # caps are received. That way, when __init__() returns, the file
        # (and its attributes) will be ready for reading.
        self.ready_sem = threading.Semaphore(0)
        self.caps_handler = self.sink.get_pad("sink").connect(
            "notify::caps", self._notify_caps
        )
        
        # Link up everything but the decoder (which must be linked only
        # when it becomes ready).
        self.pipeline.add(self.dec, self.conv, self.sink)
        self.conv.link(self.sink)
        
        # Set up the queue for data and run the main thread.
        self.queue = Queue.Queue(QUEUE_SIZE)
        self.thread = get_loop_thread()
        
        # This wil get filled with an exception if opening fails.
        self.read_exc = None
        
        # Return as soon as the stream is ready!
        self.running = True
        self.got_caps = False
        self.pipeline.set_state(gst.STATE_PLAYING)
        self.ready_sem.acquire()
        if self.read_exc:
            # An error occurred before the stream became ready.
            self.close(True)
            raise self.read_exc
    
    
    # Gstreamer callbacks.
    
    def _notify_caps(self, pad, args):
        # The sink has started to receive data, so the stream is ready.
        # This also is our opportunity to read information about the
        # stream.
        self.got_caps = True
        info = pad.get_negotiated_caps()[0]
        
        # Stream attributes.
        self.channels = info['channels']
        self.samplerate = info['rate']
        
        # Query duration.
        q = gst.query_new_duration(gst.FORMAT_TIME)
        if pad.get_peer().query(q):
            # Success.
            format, length = q.parse_duration()
            if format == gst.FORMAT_TIME:
                self.duration = float(length) / 1000000000
            else:
                self.read_exc = MetadataMissingError(
                    'duration in unknown format'
                )
        else:
            # Query failed.
            self.read_exc = MetadataMissingError('duration not available')
        
        # Allow constructor to complete.
        self.ready_sem.release()
    
    _got_a_pad = False
    def _pad_added(self, element, pad):
        # Decoded data is ready. Connect up the decoder, finally.
        name = pad.get_caps()[0].get_name()
        if name.startswith('audio/x-raw-'):
            nextpad = self.conv.get_pad('sink')
            if not nextpad.is_linked():
                self._got_a_pad = True
                pad.link(nextpad)
    
    def _no_more_pads(self, element):
        # Sent when the pads are done adding (i.e., there are no more
        # streams in the file). If we haven't gotten at least one
        # decodable stream, raise an exception.
        if not self._got_a_pad:
            self.read_exc = NoStreamError()
            self.ready_sem.release()  # No effect if we've already started.
    
    def _new_buffer(self, sink):
        if self.running:
            # New data is available from the pipeline! Dump it into our
            # queue (or possibly block if we're full).
            buf = sink.emit('pull-buffer')
            self.queue.put(str(buf))
    
    def _unkown_type(self, uridecodebin, decodebin, caps):
        # This is called *before* the stream becomes ready when the
        # file can't be read.
        streaminfo = caps.to_string()
        if not streaminfo.startswith('audio/'):
            # Ignore non-audio (e.g., video) decode errors.
            return
        self.read_exc = UnknownTypeError(streaminfo)
        self.ready_sem.release()
    
    def _message(self, bus, message):
        if not self.finished:
            if message.type == gst.MESSAGE_EOS:
                # The file is done. Tell the consumer thread.
                self.queue.put(SENTINEL)
                if not self.got_caps:
                    # If the stream ends before _notify_caps was called, this
                    # is an invalid file.
                    self.read_exc = NoStreamError()
                    self.ready_sem.release()

            elif message.type == gst.MESSAGE_ERROR:
                gerror, debug = message.parse_error()
                if 'not-linked' in debug:
                    self.read_exc = NoStreamError()
                elif 'No such file' in debug:
                    self.read_exc = IOError('resource not found')
                else:
                    self.read_exc = FileReadError(debug)
                self.ready_sem.release()
    
    # Iteration.
    def next(self):
        # Wait for data from the Gstreamer callbacks.
        val = self.queue.get()
        if val == SENTINEL:
            # End of stream.
            raise StopIteration
        return val
    def __iter__(self):
        return self
    
    # Cleanup.
    def close(self, force=False):
        if self.running or force:
            self.running = False
            self.finished = True

            # Stop reading the file.
            self.dec.set_property("uri", None)
            # Block spurious signals.
            self.sink.get_pad("sink").disconnect(self.caps_handler)

            # Make space in the output queue to let the decoder thread
            # finish. (Otherwise, the thread blocks on its enqueue and
            # the interpreter hangs.)
            try:
                self.queue.get_nowait()
            except Queue.Empty:
                pass

            # Halt the pipeline (closing file).
            self.pipeline.set_state(gst.STATE_NULL)

    def __del__(self):
        self.close()
    
    # Context manager.
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

# Smoke test.
if __name__ == '__main__':
    for path in sys.argv[1:]:
        path = os.path.abspath(os.path.expanduser(path))
        with GstAudioFile(path) as f:
            print(f.channels)
            print(f.samplerate)
            print(f.duration)
            for s in f:
                print(len(s), ord(s[0]))

########NEW FILE########
__FILENAME__ = macca
# This file is part of audioread.
# Copyright 2011, Adrian Sampson.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
# 
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

"""Read audio files using CoreAudio on Mac OS X."""
import os
import sys
import ctypes
import ctypes.util
import copy
from . import DecodeError


# CoreFoundation and CoreAudio libraries along with their function
# prototypes.

def _load_framework(name):
    return ctypes.cdll.LoadLibrary(ctypes.util.find_library(name))
_coreaudio = _load_framework('AudioToolbox')
_corefoundation = _load_framework('CoreFoundation')

# Convert CFStrings to C strings. 
_corefoundation.CFStringGetCStringPtr.restype = ctypes.c_char_p
_corefoundation.CFStringGetCStringPtr.argtypes = [ctypes.c_void_p, ctypes.c_int]

# Free memory.
_corefoundation.CFRelease.argtypes = [ctypes.c_void_p]

# Create a file:// URL.
_corefoundation.CFURLCreateFromFileSystemRepresentation.restype = \
    ctypes.c_void_p
_corefoundation.CFURLCreateFromFileSystemRepresentation.argtypes = \
    [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_bool]

# Get a string representation of a URL.
_corefoundation.CFURLGetString.restype = ctypes.c_void_p
_corefoundation.CFURLGetString.argtypes = [ctypes.c_void_p]

# Open an audio file for reading.
_coreaudio.ExtAudioFileOpenURL.restype = ctypes.c_int
_coreaudio.ExtAudioFileOpenURL.argtypes = [ctypes.c_void_p, ctypes.c_void_p]

# Set audio file property.
_coreaudio.ExtAudioFileSetProperty.restype = ctypes.c_int
_coreaudio.ExtAudioFileSetProperty.argtypes = \
    [ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p]

# Get audio file property.
_coreaudio.ExtAudioFileGetProperty.restype = ctypes.c_int
_coreaudio.ExtAudioFileGetProperty.argtypes = \
    [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]

# Read from an audio file.
_coreaudio.ExtAudioFileRead.restype = ctypes.c_int
_coreaudio.ExtAudioFileRead.argtypes = \
    [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]

# Close/free an audio file.
_coreaudio.ExtAudioFileDispose.restype = ctypes.c_int
_coreaudio.ExtAudioFileDispose.argtypes = [ctypes.c_void_p]


# Constants used in CoreAudio.

def multi_char_literal(chars):
    """Emulates character integer literals in C. Given a string "abc",
    returns the value of the C single-quoted literal 'abc'.
    """
    num = 0
    for index, char in enumerate(chars):
        shift = (len(chars) - index - 1) * 8
        num |= ord(char) << shift
    return num

PROP_FILE_DATA_FORMAT = multi_char_literal('ffmt')
PROP_CLIENT_DATA_FORMAT = multi_char_literal('cfmt')
PROP_LENGTH = multi_char_literal('#frm')
AUDIO_ID_PCM = multi_char_literal('lpcm')
PCM_IS_FLOAT = 1 << 0
PCM_IS_BIG_ENDIAN = 1 << 1
PCM_IS_SIGNED_INT = 1 << 2
PCM_IS_PACKED = 1 << 3
ERROR_TYPE = multi_char_literal('typ?')
ERROR_FORMAT = multi_char_literal('fmt?')
ERROR_NOT_FOUND = -43


# Check for errors in functions that return error codes.

class MacError(DecodeError):
    def __init__(self, code):
        if code == ERROR_TYPE:
            msg = 'unsupported audio type'
        elif code == ERROR_FORMAT:
            msg = 'unsupported format'
        else:
            msg = 'error %i' % code
        super(MacError, self).__init__(msg)

def check(err):
    """If err is nonzero, raise a MacError exception."""
    if err == ERROR_NOT_FOUND:
        raise IOError('file not found')
    elif err != 0:
        raise MacError(err)


# CoreFoundation objects.

class CFObject(object):
    def __init__(self, obj):
        if obj == 0:
            raise ValueError('object is zero')
        self._obj = obj

    def __del__(self):
        if _corefoundation:
            _corefoundation.CFRelease(self._obj)

class CFURL(CFObject):
    def __init__(self, filename):
        if not isinstance(filename, bytes):
            filename = filename.encode(sys.getfilesystemencoding())
        filename = os.path.abspath(os.path.expanduser(filename))
        url = _corefoundation.CFURLCreateFromFileSystemRepresentation(
            0, filename, len(filename), False
        )
        super(CFURL, self).__init__(url)
    
    def __str__(self):
        cfstr = _corefoundation.CFURLGetString(self._obj)
        out = _corefoundation.CFStringGetCStringPtr(cfstr, 0)
        # Resulting CFString does not need to be released according to docs.
        return out


# Structs used in CoreAudio.

class AudioStreamBasicDescription(ctypes.Structure):
    _fields_ = [
        ("mSampleRate",       ctypes.c_double),
        ("mFormatID",         ctypes.c_uint),
        ("mFormatFlags",      ctypes.c_uint),
        ("mBytesPerPacket",   ctypes.c_uint),
        ("mFramesPerPacket",  ctypes.c_uint),
        ("mBytesPerFrame",    ctypes.c_uint),
        ("mChannelsPerFrame", ctypes.c_uint),
        ("mBitsPerChannel",   ctypes.c_uint),
        ("mReserved",         ctypes.c_uint),
    ]

class AudioBuffer(ctypes.Structure):
    _fields_ = [
        ("mNumberChannels", ctypes.c_uint),
        ("mDataByteSize",   ctypes.c_uint),
        ("mData",           ctypes.c_void_p),
    ]

class AudioBufferList(ctypes.Structure):
    _fields_ = [
        ("mNumberBuffers",  ctypes.c_uint),
        ("mBuffers", AudioBuffer * 1),
    ]


# Main functionality.

class ExtAudioFile(object):
    """A CoreAudio "extended audio file". Reads information and raw PCM
    audio data from any file that CoreAudio knows how to decode.

        >>> with ExtAudioFile('something.m4a') as f:
        >>>     print f.samplerate
        >>>     print f.channels
        >>>     print f.duration
        >>>     for block in f:
        >>>         do_something(block)

    """
    def __init__(self, filename):
        url = CFURL(filename)
        try:
            self._obj = self._open_url(url)
        except:
            self.closed = True
            raise
        del url

        self.closed = False
        self._file_fmt = None
        self._client_fmt = None

        self.setup()

    @classmethod
    def _open_url(cls, url):
        """Given a CFURL Python object, return an opened ExtAudioFileRef.
        """
        file_obj = ctypes.c_void_p()
        check(_coreaudio.ExtAudioFileOpenURL(
            url._obj, ctypes.byref(file_obj)
        ))
        return file_obj

    def set_client_format(self, desc):
        """Get the client format description. This describes the
        encoding of the data that the program will read from this
        object.
        """
        assert desc.mFormatID == AUDIO_ID_PCM
        check(_coreaudio.ExtAudioFileSetProperty(
            self._obj, PROP_CLIENT_DATA_FORMAT, ctypes.sizeof(desc),
            ctypes.byref(desc)
        ))
        self._client_fmt = desc

    def get_file_format(self):
        """Get the file format description. This describes the type of
        data stored on disk.
        """
        # Have cached file format?
        if self._file_fmt is not None:
            return self._file_fmt

        # Make the call to retrieve it.
        desc = AudioStreamBasicDescription()
        size = ctypes.c_int(ctypes.sizeof(desc))
        check(_coreaudio.ExtAudioFileGetProperty(
            self._obj, PROP_FILE_DATA_FORMAT, ctypes.byref(size),
            ctypes.byref(desc)
        ))

        # Cache result.
        self._file_fmt = desc
        return desc

    @property
    def channels(self):
        """The number of channels in the audio source."""
        return int(self.get_file_format().mChannelsPerFrame)

    @property
    def samplerate(self):
        """Gets the sample rate of the audio."""
        return int(self.get_file_format().mSampleRate)

    @property
    def duration(self):
        """Gets the length of the file in seconds (a float)."""
        return float(self.nframes) / self.samplerate

    @property
    def nframes(self):
        """Gets the number of frames in the source file."""
        length = ctypes.c_long()
        size = ctypes.c_int(ctypes.sizeof(length))
        check(_coreaudio.ExtAudioFileGetProperty(
            self._obj, PROP_LENGTH, ctypes.byref(size), ctypes.byref(length)
        ))
        return length.value

    def setup(self, bitdepth=16):
        """Set the client format parameters, specifying the desired PCM
        audio data format to be read from the file. Must be called
        before reading from the file.
        """
        fmt = self.get_file_format()
        newfmt = copy.copy(fmt)

        newfmt.mFormatID = AUDIO_ID_PCM
        newfmt.mFormatFlags = \
            PCM_IS_SIGNED_INT | PCM_IS_PACKED
        newfmt.mBitsPerChannel = bitdepth
        newfmt.mBytesPerPacket = \
            (fmt.mChannelsPerFrame * newfmt.mBitsPerChannel // 8)
        newfmt.mFramesPerPacket = 1
        newfmt.mBytesPerFrame = newfmt.mBytesPerPacket
        self.set_client_format(newfmt)

    def read_data(self, blocksize=4096):
        """Generates byte strings reflecting the audio data in the file.
        """
        frames = ctypes.c_uint(blocksize // self._client_fmt.mBytesPerFrame)
        buf = ctypes.create_string_buffer(blocksize)

        buflist = AudioBufferList()
        buflist.mNumberBuffers = 1
        buflist.mBuffers[0].mNumberChannels = self._client_fmt.mChannelsPerFrame
        buflist.mBuffers[0].mDataByteSize = blocksize
        buflist.mBuffers[0].mData = ctypes.cast(buf, ctypes.c_void_p)

        while True:
            check(_coreaudio.ExtAudioFileRead(
                self._obj, ctypes.byref(frames), ctypes.byref(buflist)
            ))
            
            assert buflist.mNumberBuffers == 1
            size = buflist.mBuffers[0].mDataByteSize
            if not size:
                break

            data = ctypes.cast(buflist.mBuffers[0].mData,
                            ctypes.POINTER(ctypes.c_char))
            blob = data[:size]
            yield blob

    def close(self):
        """Close the audio file and free associated memory."""
        if not self.closed:
            check(_coreaudio.ExtAudioFileDispose(self._obj))
            self.closed = True

    def __del__(self):
        if _coreaudio:
            self.close()

    # Context manager.
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    # Iteration.
    def __iter__(self):
        return self.read_data()

########NEW FILE########
__FILENAME__ = maddec
# This file is part of audioread.
# Copyright 2011, Adrian Sampson.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
# 
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

"""Decode MPEG audio files with MAD (via pymad)."""
import mad
from . import DecodeError

class UnsupportedError(DecodeError):
    """The file is not readable by MAD."""

class MadAudioFile(object):
    """MPEG audio file decoder using the MAD library."""
    def __init__(self, filename):
        self.fp = open(filename, 'rb')
        self.mf = mad.MadFile(self.fp)
        if not self.mf.total_time(): # Indicates a failed open.
            raise UnsupportedError()

    def close(self):
        if hasattr(self, 'fp'):
            self.fp.close()
        if hasattr(self, 'mf'):
            del self.mf

    def read_blocks(self, block_size=4096):
        """Generates buffers containing PCM data for the audio file.
        """
        while True:
            out = self.mf.read(block_size)
            if not out:
                break
            yield out

    @property
    def samplerate(self):
        """Sample rate in Hz."""
        return self.mf.samplerate()
    
    @property
    def duration(self):
        """Length of the audio in seconds (a float)."""
        return float(self.mf.total_time()) / 1000

    @property
    def channels(self):
        """The number of channels."""
        if self.mf.mode() == mad.MODE_SINGLE_CHANNEL:
            return 1
        elif self.mf.mode() in (mad.MODE_DUAL_CHANNEL,
                                mad.MODE_JOINT_STEREO,
                                mad.MODE_STEREO):
            return 2
        else:
            # Other mode?
            return 2

    def __del__(self):
        self.close()

    # Iteration.
    def __iter__(self):
        return self.read_blocks()

    # Context manager.
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

########NEW FILE########
__FILENAME__ = rawread
# This file is part of audioread.
# Copyright 2011, Adrian Sampson.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
# 
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

"""Uses standard-library modules to read AIFF, AIFF-C, and WAV files."""
import wave
import aifc
import audioop
import struct
from . import DecodeError

TARGET_WIDTH = 2

class UnsupportedError(DecodeError):
    """File is neither an AIFF nor a WAV file."""

def byteswap(s):
    """Swaps the endianness of the bytesting s, which must be an array
    of shorts (16-bit signed integers). This is probably less efficient
    than it should be.
    """
    assert len(s) % 2 == 0
    parts = []
    for i in xrange(0, len(s), 2):
        chunk = s[i:i+2]
        newchunk =struct.pack('<h', *struct.unpack('>h', chunk))
        parts.append(newchunk)
    return ''.join(parts)

class RawAudioFile(object):
    """An AIFF or WAV file that can be read by the Python standard
    library modules ``wave`` and ``aifc``.
    """
    def __init__(self, filename):
        self._fh = open(filename, 'rb')

        try:
            self._file = aifc.open(self._fh)
        except aifc.Error:
            # Return to the beginning of the file to try the WAV reader.
            self._fh.seek(0)
        else:
            self._is_aif = True
            return

        try:
            self._file = wave.open(self._fh)
        except wave.Error:
            pass
        else:
            self._is_aif = False
            return

        raise UnsupportedError()
    
    def close(self):
        """Close the underlying file."""
        self._file.close()
        self._fh.close()

    @property
    def channels(self):
        """Number of audio channels."""
        return self._file.getnchannels()

    @property
    def samplerate(self):
        """Sample rate in Hz."""
        return self._file.getframerate()

    @property
    def duration(self):
        """Length of the audio in seconds (a float)."""
        return float(self._file.getnframes()) / self.samplerate

    def read_data(self, block_samples=1024):
        """Generates blocks of PCM data found in the file."""
        old_width = self._file.getsampwidth()

        while True:
            data = self._file.readframes(block_samples)
            if not data:
                break

            # Make sure we have the desired bitdepth and endianness.
            data = audioop.lin2lin(data, old_width, TARGET_WIDTH)
            if self._is_aif and self._file.getcomptype() != 'sowt':
                # Big-endian data. Swap endianness.
                data = byteswap(data)
            yield data

    # Context manager.
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    # Iteration.
    def __iter__(self):
        return self.read_data()

########NEW FILE########
__FILENAME__ = decode
# This file is part of audioread.
# Copyright 2011, Adrian Sampson.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
# 
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

"""Command-line tool to decode audio files to WAV files."""
from __future__ import print_function
import audioread
import sys
import os
import wave
import contextlib

def decode(filename):
    filename = os.path.abspath(os.path.expanduser(filename))
    if not os.path.exists(filename):
        print("File not found.", file=sys.stderr)
        sys.exit(1)

    try:
        with audioread.audio_open(filename) as f:
            print('Input file: %i channels at %i Hz; %.1f seconds.' % \
                  (f.channels, f.samplerate, f.duration),
                  file=sys.stderr)
            print('Backend:', str(type(f).__module__).split('.')[1],
                  file=sys.stderr)

            with contextlib.closing(wave.open(filename + '.wav', 'w')) as of:
                of.setnchannels(f.channels)
                of.setframerate(f.samplerate)
                of.setsampwidth(2)

                for buf in f:
                    of.writeframes(buf)

    except audioread.DecodeError:
        print("File could not be decoded.", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    decode(sys.argv[1])

########NEW FILE########
