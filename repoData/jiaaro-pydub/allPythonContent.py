__FILENAME__ = audio_segment
from __future__ import division

import os
import subprocess
from tempfile import TemporaryFile, NamedTemporaryFile
import wave
import sys

try:
    from StringIO import StringIO
except:
    from io import StringIO, BytesIO

from .utils import (
    _fd_or_path_or_tempfile,
    db_to_float,
    ratio_to_db,
    get_encoder_name,
    audioop,
)
from .exceptions import (
    TooManyMissingFrames,
    InvalidDuration,
    InvalidID3TagVersion,
    InvalidTag,
    CouldntDecodeError,
)

if sys.version_info >= (3, 0):
    basestring = str
    xrange = range
    StringIO = BytesIO

AUDIO_FILE_EXT_ALIASES = {
    "m4a": "mp4",
    "wave": "wav",
}


class AudioSegment(object):
    """
    AudioSegments are *immutable* objects representing segments of audio
    that can be manipulated using python code.

    AudioSegments are slicable using milliseconds.
    for example:
        a = AudioSegment.from_mp3(mp3file)
        first_second = a[:1000] # get the first second of an mp3
        slice = a[5000:10000] # get a slice from 5 to 10 seconds of an mp3
    """
    converter = get_encoder_name()  # either ffmpeg or avconv

    # TODO: remove in 1.0 release
    # maintain backwards compatibility for ffmpeg attr (now called converter)
    ffmpeg = property(lambda s: s.converter,
                      lambda s, v: setattr(s, 'converter', v))

    DEFAULT_CODECS = {
        "ogg": "libvorbis"
    }

    def __init__(self, data=None, *args, **kwargs):
        if kwargs.get('metadata', False):
            # internal use only
            self._data = data
            for attr, val in kwargs.pop('metadata').items():
                setattr(self, attr, val)
        else:
            # normal construction
            data = data if isinstance(data, basestring) else data.read()
            raw = wave.open(StringIO(data), 'rb')

            raw.rewind()
            self.channels = raw.getnchannels()
            self.sample_width = raw.getsampwidth()
            self.frame_rate = raw.getframerate()
            self.frame_width = self.channels * self.sample_width

            raw.rewind()
            self._data = raw.readframes(float('inf'))

        super(AudioSegment, self).__init__(*args, **kwargs)

    def __len__(self):
        """
        returns the length of this audio segment in milliseconds
        """
        return round(1000 * (self.frame_count() / self.frame_rate))

    def __eq__(self, other):
        try:
            return self._data == other._data
        except:
            return False

    def __ne__(self, other):
        return not (self == other)

    def __iter__(self):
        return (self[i] for i in xrange(len(self)))

    def __getitem__(self, millisecond):
        if isinstance(millisecond, slice):
            start = millisecond.start if millisecond.start is not None else 0
            end = millisecond.stop if millisecond.stop is not None \
                else len(self)

            start = min(start, len(self))
            end = min(end, len(self))
        else:
            start = millisecond
            end = millisecond + 1

        start = self._parse_position(start) * self.frame_width
        end = self._parse_position(end) * self.frame_width
        data = self._data[start:end]

        # ensure the output is as long as the requester is expecting
        expected_length = end - start
        missing_frames = (expected_length - len(data)) // self.frame_width
        if missing_frames:
            if missing_frames > self.frame_count(ms=2):
                raise TooManyMissingFrames(
                    "You should never be filling in "
                    "   more than 2 ms with silence here, "
                    "missing frames: %s" % missing_frames)
            silence = audioop.mul(data[:self.frame_width],
                                  self.sample_width, 0)
            data += (silence * missing_frames)

        return self._spawn(data)

    def get_sample_slice(self, start_sample=None, end_sample=None):
        """
        Get a section of the audio segment by sample index.

        NOTE: Negative indices do *not* address samples backword
        from the end of the audio segment like a python list.
        This is intentional.
        """
        max_val = self.frame_count()

        def bounded(val, default):
            if val is None:
                return default
            if val < 0:
                return 0
            if val > max_val:
                return max_val
            return val

        start_i = bounded(start_sample, 0) * self.frame_width
        end_i = bounded(end_sample, max_val) * self.frame_width

        data = self._data[start_i:end_i]
        return self._spawn(data)

    def __add__(self, arg):
        if isinstance(arg, AudioSegment):
            return self.append(arg, crossfade=0)
        else:
            return self.apply_gain(arg)

    def __sub__(self, arg):
        if isinstance(arg, AudioSegment):
            raise TypeError("AudioSegment objects can't be subtracted from "
                            "each other")
        else:
            return self.apply_gain(-arg)

    def __mul__(self, arg):
        """
        If the argument is an AudioSegment, overlay the multiplied audio
        segment.

        If it's a number, just use the string multiply operation to repeat the
        audio.

        The following would return an AudioSegment that contains the
        audio of audio_seg eight times

        `audio_seg * 8`
        """
        if isinstance(arg, AudioSegment):
            return self.overlay(arg, position=0, loop=True)
        else:
            return self._spawn(data=self._data * arg)

    def _spawn(self, data, overrides={}):
        """
        Creates a new audio segment using the metadata from the current one
        and the data passed in. Should be used whenever an AudioSegment is
        being returned by an operation that would alters the current one,
        since AudioSegment objects are immutable.
        """
        # accept lists of data chunks
        if isinstance(data, list):
            data = b''.join(data)

        # accept file-like objects
        if hasattr(data, 'read'):
            if hasattr(data, 'seek'):
                data.seek(0)
            data = data.read()

        metadata = {
            'sample_width': self.sample_width,
            'frame_rate': self.frame_rate,
            'frame_width': self.frame_width,
            'channels': self.channels
        }
        metadata.update(overrides)
        return AudioSegment(data=data, metadata=metadata)

    @classmethod
    def _sync(cls, seg1, seg2):
        s1_len, s2_len = len(seg1), len(seg2)

        channels = max(seg1.channels, seg2.channels)
        seg1 = seg1.set_channels(channels)
        seg2 = seg2.set_channels(channels)

        frame_rate = max(seg1.frame_rate, seg2.frame_rate)
        seg1 = seg1.set_frame_rate(frame_rate)
        seg2 = seg2.set_frame_rate(frame_rate)

        sample_width = max(seg1.sample_width, seg2.sample_width)
        seg1 = seg1.set_sample_width(sample_width)
        seg2 = seg2.set_sample_width(sample_width)

        assert(len(seg1) == s1_len)
        assert(len(seg2) == s2_len)

        return seg1, seg2

    def _parse_position(self, val):
        if val < 0:
            val = len(self) - abs(val)
        val = self.frame_count(ms=len(self)) if val == float("inf") else \
            self.frame_count(ms=val)
        return int(val)

    @classmethod
    def empty(cls):
        return cls(b'', metadata={
            "channels": 1,
            "sample_width": 1,
            "frame_rate": 1,
            "frame_width": 1
        })

    @classmethod
    def silent(cls, duration=1000):
        """
        Generate a silent audio segment.
        duration specified in milliseconds (default: 1000ms).
        """
        # lowest frame rate I've seen in actual use
        frame_rate = 11025
        frames = int(frame_rate * (duration / 1000.0))
        data = b"\0\0" * frames
        return cls(data, metadata={"channels": 1,
                                   "sample_width": 2,
                                   "frame_rate": frame_rate,
                                   "frame_width": 2})

    @classmethod
    def from_file(cls, file, format=None):
        file = _fd_or_path_or_tempfile(file, 'rb', tempfile=False)

        if format:
            format = AUDIO_FILE_EXT_ALIASES.get(format, format)

        if format == "wav":
            try:
                return cls._from_safe_wav(file)
            except:
                pass

        input_file = NamedTemporaryFile(mode='wb', delete=False)
        input_file.write(file.read())
        input_file.flush()

        output = NamedTemporaryFile(mode="rb", delete=False)

        convertion_command = [cls.converter,
                              '-y',  # always overwrite existing files
                              ]

        # If format is not defined
        # ffmpeg/avconv will detect it automatically
        if format:
            convertion_command += ["-f", format]

        convertion_command += [
            "-i", input_file.name,  # input_file options (filename last)
            "-vn",  # Drop any video streams if there are any
            "-f", "wav",  # output options (filename last)
            output.name
        ]

        retcode = subprocess.call(convertion_command, stderr=open(os.devnull))

        if retcode != 0:
            raise CouldntDecodeError("Decoding failed. ffmpeg returned error code: {0}".format(retcode))

        obj = cls._from_safe_wav(output)

        input_file.close()
        output.close()
        os.unlink(input_file.name)
        os.unlink(output.name)

        return obj

    @classmethod
    def from_mp3(cls, file):
        return cls.from_file(file, 'mp3')

    @classmethod
    def from_flv(cls, file):
        return cls.from_file(file, 'flv')

    @classmethod
    def from_ogg(cls, file):
        return cls.from_file(file, 'ogg')

    @classmethod
    def from_wav(cls, file):
        return cls.from_file(file, 'wav')

    @classmethod
    def _from_safe_wav(cls, file):
        file = _fd_or_path_or_tempfile(file, 'rb', tempfile=False)
        file.seek(0)
        return cls(data=file)

    def export(self, out_f=None, format='mp3', codec=None, bitrate=None, parameters=None, tags=None, id3v2_version='4'):
        """
        Export an AudioSegment to a file with given options

        out_f (string):
            Path to destination audio file

        format (string)
            Format for destination audio file.
            ('mp3', 'wav', 'ogg' or other ffmpeg/avconv supported files)

        codec (string)
            Codec used to encoding for the destination.

        bitrate (string)
            Bitrate used when encoding destination file. (128, 256, 312k...)

        parameters (string)
            Aditional ffmpeg/avconv parameters

        tags (dict)
            Set metadata information to destination files
            usually used as tags. ({title='Song Title', artist='Song Artist'})

        id3v2_version (string)
            Set ID3v2 version for tags. (default: '4')
        """
        id3v2_allowed_versions = ['3', '4']

        out_f = _fd_or_path_or_tempfile(out_f, 'wb+')
        out_f.seek(0)

        # for wav output we can just write the data directly to out_f
        if format == "wav":
            data = out_f
        else:
            data = NamedTemporaryFile(mode="wb", delete=False)

        wave_data = wave.open(data, 'wb')
        wave_data.setnchannels(self.channels)
        wave_data.setsampwidth(self.sample_width)
        wave_data.setframerate(self.frame_rate)
        # For some reason packing the wave header struct with
        # a float in python 2 doesn't throw an exception
        wave_data.setnframes(int(self.frame_count()))
        wave_data.writeframesraw(self._data)
        wave_data.close()

        # for wav files, we're done (wav data is written directly to out_f)
        if format == 'wav':
            return out_f

        output = NamedTemporaryFile(mode="w+b", delete=False)

        # build converter command to export
        convertion_command = [
            self.converter,
            '-y',  # always overwrite existing files
            "-f", "wav", "-i", data.name,  # input options (filename last)
        ]

        if codec is None:
            codec = self.DEFAULT_CODECS.get(format, None)

        if codec is not None:
            # force audio encoder
            convertion_command.extend(["-acodec", codec])

        if bitrate is not None:
            convertion_command.extend(["-b:a", bitrate])

        if parameters is not None:
            # extend arguments with arbitrary set
            convertion_command.extend(parameters)

        if tags is not None:
            if not isinstance(tags, dict):
                raise InvalidTag("Tags must be a dictionary.")
            else:
                # Extend converter command with tags
                # print(tags)
                for key, value in tags.items():
                    convertion_command.extend(
                        ['-metadata', '{0}={1}'.format(key, value)])

                if format == 'mp3':
                    # set id3v2 tag version
                    if id3v2_version not in id3v2_allowed_versions:
                        raise InvalidID3TagVersion(
                            "id3v2_version not allowed, allowed versions: %s" % id3v2_allowed_versions)
                    convertion_command.extend([
                        "-id3v2_version",  id3v2_version
                    ])

        convertion_command.extend([
            "-f", format, output.name,  # output options (filename last)
        ])

        # read stdin / write stdout
        subprocess.call(convertion_command,
                        # make converter shut up
                        stderr=open(os.devnull)
                        )

        output.seek(0)
        out_f.write(output.read())

        data.close()
        output.close()

        os.unlink(data.name)
        os.unlink(output.name)

        out_f.seek(0)
        return out_f

    def get_frame(self, index):
        frame_start = index * self.frame_width
        frame_end = frame_start + self.frame_width
        return self._data[frame_start:frame_end]

    def frame_count(self, ms=None):
        """
        returns the number of frames for the given number of milliseconds, or
            if not specified, the number of frames in the whole AudioSegment
        """
        if ms is not None:
            return ms * (self.frame_rate / 1000.0)
        else:
            return float(len(self._data) // self.frame_width)

    def set_sample_width(self, sample_width):
        if sample_width == self.sample_width:
            return self

        data = self._data

        if self.sample_width == 1:
            data = audioop.bias(data, 1, -128)

        if data:
            data = audioop.lin2lin(data, self.sample_width, sample_width)

        if sample_width == 1:
            data = audioop.bias(data, 1, 128)

        frame_width = self.channels * sample_width
        return self._spawn(data, overrides={'sample_width': sample_width,
                                            'frame_width': frame_width})

    def set_frame_rate(self, frame_rate):
        if frame_rate == self.frame_rate:
            return self

        if self._data:
            converted, _ = audioop.ratecv(self._data, self.sample_width,
                                          self.channels, self.frame_rate,
                                          frame_rate, None)
        else:
            converted = self._data

        return self._spawn(data=converted,
                           overrides={'frame_rate': frame_rate})

    def set_channels(self, channels):
        if channels == self.channels:
            return self

        if channels == 2 and self.channels == 1:
            fn = audioop.tostereo
            frame_width = self.frame_width * 2
        elif channels == 1 and self.channels == 2:
            fn = audioop.tomono
            frame_width = self.frame_width // 2

        converted = fn(self._data, self.sample_width, 1, 1)

        return self._spawn(data=converted,
                           overrides={
                               'channels': channels,
                               'frame_width': frame_width})

    @property
    def rms(self):
        if self.sample_width == 1:
            return self.set_sample_width(2).rms
        else:
            return audioop.rms(self._data, self.sample_width)

    @property
    def dBFS(self):
        rms = self.rms
        if not rms:
            return - float("infinity")
        return ratio_to_db(self.rms / self.max_possible_amplitude)

    @property
    def max(self):
        return audioop.max(self._data, self.sample_width)

    @property
    def max_possible_amplitude(self):
        bits = self.sample_width * 8
        max_possible_val = (2 ** bits)

        # since half is above 0 and half is below the max amplitude is divided
        return max_possible_val / 2

    @property
    def duration_seconds(self):
        return self.frame_rate and self.frame_count() / self.frame_rate or 0.0

    def apply_gain(self, volume_change):
        return self._spawn(data=audioop.mul(self._data, self.sample_width,
                                            db_to_float(float(volume_change))))

    def overlay(self, seg, position=0, loop=False):
        output = TemporaryFile()

        seg1, seg2 = AudioSegment._sync(self, seg)
        sample_width = seg1.sample_width
        spawn = seg1._spawn

        output.write(seg1[:position]._data)

        # drop down to the raw data
        seg1 = seg1[position:]._data
        seg2 = seg2._data
        pos = 0
        seg1_len = len(seg1)
        seg2_len = len(seg2)
        while True:
            remaining = max(0, seg1_len - pos)
            if seg2_len >= remaining:
                seg2 = seg2[:remaining]
                seg2_len = remaining
                loop = False

            output.write(audioop.add(seg1[pos:pos + seg2_len], seg2,
                                     sample_width))
            pos += seg2_len

            if not loop:
                break

        output.write(seg1[pos:])

        return spawn(data=output)

    def append(self, seg, crossfade=100):
        output = TemporaryFile()

        seg1, seg2 = AudioSegment._sync(self, seg)

        if not crossfade:
            return seg1._spawn(seg1._data + seg2._data)

        xf = seg1[-crossfade:].fade(to_gain=-120, start=0, end=float('inf'))
        xf *= seg2[:crossfade].fade(from_gain=-120, start=0, end=float('inf'))

        output.write(seg1[:-crossfade]._data)
        output.write(xf._data)
        output.write(seg2[crossfade:]._data)

        output.seek(0)
        return seg1._spawn(data=output)

    def fade(self, to_gain=0, from_gain=0, start=None, end=None,
             duration=None):
        """
        Fade the volume of this audio segment.

        to_gain (float):
            resulting volume_change in db

        start (int):
            default = beginning of the segment
            when in this segment to start fading in milliseconds

        end (int):
            default = end of the segment
            when in this segment to start fading in milliseconds

        duration (int):
            default = until the end of the audio segment
            the duration of the fade
        """
        if None not in [duration, end, start]:
            raise TypeError('Only two of the three arguments, "start", '
                            '"end", and "duration" may be specified')

        # no fade == the same audio
        if to_gain == 0 and from_gain == 0:
            return self

        start = min(len(self), start) if start is not None else None
        end = min(len(self), end) if end is not None else None

        if start is not None and start < 0:
            start += len(self)
        if end is not None and end < 0:
            end += len(self)

        if duration is not None and duration < 0:
            raise InvalidDuration("duration must be a positive integer")

        if duration:
            if start is not None:
                end = start + duration
            elif end is not None:
                start = end - duration
        else:
            duration = end - start

        from_power = db_to_float(from_gain)

        output = []

        # original data - up until the crossfade portion, as is
        before_fade = self[:start]._data
        if from_gain != 0:
            before_fade = audioop.mul(before_fade,
                                      self.sample_width,
                                      from_power)
        output.append(before_fade)

        gain_delta = db_to_float(to_gain) - from_power

        # fades longer than 100ms can use coarse fading (one gain step per ms),
        # shorter fades will have audible clicks so they use precise fading
        #(one gain step per sample)
        if duration > 100:
            scale_step = gain_delta / duration

            for i in range(duration):
                volume_change = from_power + (scale_step * i)
                chunk = self[start + i]
                chunk = audioop.mul(chunk._data,
                                    self.sample_width,
                                    volume_change)

                output.append(chunk)
        else:
            start_frame = self.frame_count(ms=start)
            end_frame = self.frame_count(ms=end)
            fade_frames = end_frame - start_frame
            scale_step = gain_delta / fade_frames

            for i in range(int(fade_frames)):
                volume_change = from_power + (scale_step * i)
                sample = self.get_frame(int(start_frame + i))
                sample = audioop.mul(sample, self.sample_width, volume_change)

                output.append(sample)

        # original data after the crossfade portion, at the new volume
        after_fade = self[end:]._data
        if to_gain != 0:
            after_fade = audioop.mul(after_fade,
                                     self.sample_width,
                                     db_to_float(to_gain))
        output.append(after_fade)

        return self._spawn(data=output)

    def fade_out(self, duration):
        return self.fade(to_gain=-120, duration=duration, end=float('inf'))

    def fade_in(self, duration):
        return self.fade(from_gain=-120, duration=duration, start=0)

    def reverse(self):
        return self._spawn(
            data=audioop.reverse(self._data, self.sample_width)
        )


from . import effects

########NEW FILE########
__FILENAME__ = effects
import sys
from .utils import (
    db_to_float,
    ratio_to_db,
    register_pydub_effect,
    make_chunks,
    audioop,
)
from .exceptions import TooManyMissingFrames, InvalidDuration

if sys.version_info >= (3, 0):
    xrange = range

@register_pydub_effect
def normalize(seg, headroom=0.1):
    """
    headroom is how close to the maximum volume to boost the signal up to (specified in dB)
    """
    peak_sample_val = seg.max
    
    # if the max is 0, this audio segment is silent, and can't be normalized
    if peak_sample_val == 0:
        return seg
    
    target_peak = seg.max_possible_amplitude * db_to_float(-headroom)

    needed_boost = ratio_to_db(target_peak / peak_sample_val)
    return seg.apply_gain(needed_boost)


@register_pydub_effect
def speedup(seg, playback_speed=1.5, chunk_size=150, crossfade=25):
    # we will keep audio in 150ms chunks since one waveform at 20Hz is 50ms long
    # (20 Hz is the lowest frequency audible to humans)

    # portion of AUDIO TO KEEP. if playback speed is 1.25 we keep 80% (0.8) and
    # discard 20% (0.2)
    atk = 1.0 / playback_speed

    if playback_speed < 2.0:
        # throwing out more than half the audio - keep 50ms chunks
        ms_to_remove_per_chunk = int(chunk_size * (1 - atk) / atk)
    else:
        # throwing out less than half the audio - throw out 50ms chunks
        ms_to_remove_per_chunk = int(chunk_size)
        chunk_size = int(atk * chunk_size / (1 - atk))

    # the crossfade cannot be longer than the amount of audio we're removing
    crossfade = min(crossfade, ms_to_remove_per_chunk - 1)

    # DEBUG
    #print("chunk: {0}, rm: {1}".format(chunk_size, ms_to_remove_per_chunk))

    chunks = make_chunks(seg, chunk_size + ms_to_remove_per_chunk)
    if len(chunks) < 2:
        raise Exception("Could not speed up AudioSegment, it was too short {2:0.2f}s for the current settings:\n{0}ms chunks at {1:0.1f}x speedup".format(
            chunk_size, playback_speed, seg.duration_seconds))

    # we'll actually truncate a bit less than we calculated to make up for the
    # crossfade between chunks
    ms_to_remove_per_chunk -= crossfade

    # we don't want to truncate the last chunk since it is not guaranteed to be
    # the full chunk length
    last_chunk = chunks[-1]
    chunks = [chunk[:-ms_to_remove_per_chunk] for chunk in chunks[:-1]]

    out = chunks[0]
    for chunk in chunks[1:]:
        out = out.append(chunk, crossfade=crossfade)

    out += last_chunk
    return out
    
@register_pydub_effect
def strip_silence(seg, silence_len=1000, silence_thresh=-16, padding=100):
    if padding > silence_len:
        raise InvalidDuration("padding cannot be longer than silence_len")

    chunks = split_on_silence(seg, min_silence_len, silence_thresh, padding)
    crossfade = padding / 2

    if not len(chunks):
        return seg[0:0]

    seg = chunks[0]
    for chunk in chunks[1:]:
        seg.append(chunk, crossfade=crossfade)

    return seg

@register_pydub_effect
def compress_dynamic_range(seg, threshold=-20.0, ratio=4.0, attack=5.0, release=50.0):
    """
    Keyword Arguments:
        
        threshold - default: -20.0
            Threshold in dBFS. default of -20.0 means -20dB relative to the
            maximum possible volume. 0dBFS is the maximum possible value so
            all values for this argument sould be negative.

        ratio - default: 4.0
            Compression ratio. Audio louder than the threshold will be 
            reduced to 1/ratio the volume. A ratio of 4.0 is equivalent to
            a setting of 4:1 in a pro-audio compressor like the Waves C1.
        
        attack - default: 5.0
            Attack in milliseconds. How long it should take for the compressor
            to kick in once the audio has exceeded the threshold.

        release - default: 50.0
            Release in milliseconds. How long it should take for the compressor
            to stop compressing after the audio has falled below the threshold.

    
    For an overview of Dynamic Range Compression, and more detailed explanation
    of the related terminology, see: 

        http://en.wikipedia.org/wiki/Dynamic_range_compression
    """

    thresh_rms = seg.max_possible_amplitude * db_to_float(threshold)
    
    look_frames = int(seg.frame_count(ms=attack))
    def rms_at(frame_i):
        return seg.get_sample_slice(frame_i - look_frames, frame_i).rms
    def db_over_threshold(rms):
        if rms == 0: return 0.0
        db = ratio_to_db(rms / thresh_rms)
        return max(db, 0)

    output = []

    # amount to reduce the volume of the audio by (in dB)
    attenuation = 0.0
    
    attack_frames = seg.frame_count(ms=attack)
    release_frames = seg.frame_count(ms=release)
    for i in xrange(int(seg.frame_count())):
        rms_now = rms_at(i)
        
        # with a ratio of 4.0 this means the volume will exceed the threshold by
        # 1/4 the amount (of dB) that it would otherwise
        max_attenuation = (1 - (1.0 / ratio)) * db_over_threshold(rms_now)
        
        attenuation_inc = max_attenuation / attack_frames
        attenuation_dec = max_attenuation / release_frames
        
        if rms_now > thresh_rms and attenuation <= max_attenuation:
            attenuation += attenuation_inc
            attenuation = min(attenuation, max_attenuation)
        else:
            attenuation -= attenuation_dec
            attenuation = max(attenuation, 0)
        
        frame = seg.get_frame(i)
        if attenuation != 0.0:
            frame = audioop.mul(frame,
                                seg.sample_width,
                                db_to_float(-attenuation))
        
        output.append(frame)
    
    return seg._spawn(data=b''.join(output))

########NEW FILE########
__FILENAME__ = exceptions


class TooManyMissingFrames(Exception):
    pass


class InvalidDuration(Exception):
    pass


class InvalidTag(Exception):
    pass


class InvalidID3TagVersion(Exception):
    pass


class CouldntDecodeError(Exception):
	pass
########NEW FILE########
__FILENAME__ = playback
import subprocess
from tempfile import NamedTemporaryFile
from .utils import get_player_name

PLAYER = get_player_name()

def play(audio_segment):
    with NamedTemporaryFile("w+b", suffix=".wav") as f:
        audio_segment.export(f.name, "wav")
        subprocess.call([PLAYER, "-nodisp", "-autoexit", f.name])

########NEW FILE########
__FILENAME__ = pyaudioop
import __builtin__
import math
import struct
from fractions import gcd
from ctypes import create_string_buffer


class error(Exception):
    pass


def _check_size(size):
    if size != 1 and size != 2 and size != 4:
        raise error("Size should be 1, 2 or 4")


def _check_params(length, size):
    _check_size(size)
    if length % size != 0:
        raise error("not a whole number of frames")


def _sample_count(cp, size):
    return len(cp) / size


def _get_samples(cp, size, signed=True):
    for i in range(_sample_count(cp, size)):
        yield _get_sample(cp, size, i, signed)


def _struct_format(size, signed):
    if size == 1:
        return "b" if signed else "B"
    elif size == 2:
        return "h" if signed else "H"
    elif size == 4:
        return "i" if signed else "I"


def _get_sample(cp, size, i, signed=True):
    fmt = _struct_format(size, signed)
    start = i * size
    end = start + size
    return struct.unpack_from(fmt, buffer(cp)[start:end])[0]


def _put_sample(cp, size, i, val, signed=True):
    fmt = _struct_format(size, signed)
    struct.pack_into(fmt, cp, i * size, val)


def _get_maxval(size, signed=True):
    if signed and size == 1:
        return 0x7f
    elif size == 1:
        return 0xff
    elif signed and size == 2:
        return 0x7fff
    elif size == 2:
        return 0xffff
    elif signed and size == 4:
        return 0x7fffffff
    elif size == 4:
        return 0xffffffff


def _get_minval(size, signed=True):
    if not signed:
        return 0
    elif size == 1:
        return -0x80
    elif size == 2:
        return -0x8000
    elif size == 4:
        return -0x80000000


def _get_clipfn(size, signed=True):
    maxval = _get_maxval(size, signed)
    minval = _get_minval(size, signed)
    return lambda val: __builtin__.max(min(val, maxval), minval)


def _overflow(val, size, signed=True):
    minval = _get_minval(size, signed)
    maxval = _get_maxval(size, signed)
    if minval <= val <= maxval:
        return val

    bits = size * 8
    if signed:
        offset = 2**(bits-1)
        return ((val + offset) % (2**bits)) - offset
    else:
        return val % (2**bits)


def getsample(cp, size, i):
    _check_params(len(cp), size)
    if not (0 <= i < len(cp) / size):
        raise error("Index out of range")
    return _get_sample(cp, size, i)


def max(cp, size):
    _check_params(len(cp), size)

    if len(cp) == 0:
        return 0

    return __builtin__.max(abs(sample) for sample in _get_samples(cp, size))


def minmax(cp, size):
    _check_params(len(cp), size)

    max_sample, min_sample = 0, 0
    for sample in _get_samples(cp, size):
        max_sample = __builtin__.max(sample, max_sample)
        min_sample = __builtin__.min(sample, min_sample)

    return min_sample, max_sample


def avg(cp, size):
    _check_params(len(cp), size)
    sample_count = _sample_count(cp, size)
    if sample_count == 0:
        return 0
    return sum(_get_samples(cp, size)) / sample_count


def rms(cp, size):
    _check_params(len(cp), size)

    sample_count = _sample_count(cp, size)
    if sample_count == 0:
        return 0

    sum_squares = sum(sample**2 for sample in _get_samples(cp, size))
    return int(math.sqrt(sum_squares / sample_count))


def _sum2(cp1, cp2, length):
    size = 2
    total = 0
    for i in range(length):
        total += getsample(cp1, size, i) * getsample(cp2, size, i)
    return total


def findfit(cp1, cp2):
    size = 2

    if len(cp1) % 2 != 0 or len(cp2) % 2 != 0:
        raise error("Strings should be even-sized")

    if len(cp1) < len(cp2):
        raise error("First sample should be longer")

    len1 = _sample_count(cp1, size)
    len2 = _sample_count(cp2, size)

    sum_ri_2 = _sum2(cp2, cp2, len2)
    sum_aij_2 = _sum2(cp1, cp1, len2)
    sum_aij_ri = _sum2(cp1, cp2, len2)

    result = (sum_ri_2 * sum_aij_2 - sum_aij_ri * sum_aij_ri) / sum_aij_2

    best_result = result
    best_i = 0

    for i in range(1, len1 - len2 + 1):
        aj_m1 = _get_sample(cp1, size, i - 1)
        aj_lm1 = _get_sample(cp1, size, i + len2 - 1)

        sum_aij_2 += aj_lm1**2 - aj_m1**2
        sum_aij_ri = _sum2(buffer(cp1)[i*size:], cp2, len2)

        result = (sum_ri_2 * sum_aij_2 - sum_aij_ri * sum_aij_ri) / sum_aij_2

        if result < best_result:
            best_result = result
            best_i = i

    factor = _sum2(buffer(cp1)[best_i*size:], cp2, len2) / sum_ri_2

    return best_i, factor


def findfactor(cp1, cp2):
    size = 2

    if len(cp1) % 2 != 0:
        raise error("Strings should be even-sized")

    if len(cp1) != len(cp2):
        raise error("Samples should be same size")

    sample_count = _sample_count(cp1, size)

    sum_ri_2 = _sum2(cp2, cp2, sample_count)
    sum_aij_ri = _sum2(cp1, cp2, sample_count)

    return sum_aij_ri / sum_ri_2


def findmax(cp, len2):
    size = 2
    sample_count = _sample_count(cp, size)

    if len(cp) % 2 != 0:
        raise error("Strings should be even-sized")

    if len2 < 0 or sample_count < len2:
        raise error("Input sample should be longer")

    if sample_count == 0:
        return 0

    result = _sum2(cp, cp, len2)
    best_result = result
    best_i = 0

    for i in range(1, sample_count - len2 + 1):
        sample_leaving_window = getsample(cp, size, i - 1)
        sample_entering_window = getsample(cp, size, i + len2 - 1)

        result -= sample_leaving_window**2
        result += sample_entering_window**2

        if result > best_result:
            best_result = result
            best_i = i

    return best_i


def avgpp(cp, size):
    _check_params(len(cp), size)
    sample_count = _sample_count(cp, size)

    prevextremevalid = False
    prevextreme = None
    avg = 0
    nextreme = 0

    prevval = getsample(cp, size, 0)
    val = getsample(cp, size, 1)

    prevdiff = val - prevval

    for i in range(1, sample_count):
        val = getsample(cp, size, i)
        diff = val - prevval

        if diff * prevdiff < 0:
            if prevextremevalid:
                avg += abs(prevval - prevextreme)
                nextreme += 1

            prevextremevalid = True
            prevextreme = prevval

        prevval = val
        if diff != 0:
            prevdiff = diff

    if nextreme == 0:
        return 0

    return avg / nextreme


def maxpp(cp, size):
    _check_params(len(cp), size)
    sample_count = _sample_count(cp, size)

    prevextremevalid = False
    prevextreme = None
    max = 0

    prevval = getsample(cp, size, 0)
    val = getsample(cp, size, 1)

    prevdiff = val - prevval

    for i in range(1, sample_count):
        val = getsample(cp, size, i)
        diff = val - prevval

        if diff * prevdiff < 0:
            if prevextremevalid:
                extremediff = abs(prevval - prevextreme)
                if extremediff > max:
                    max = extremediff
            prevextremevalid = True
            prevextreme = prevval

        prevval = val
        if diff != 0:
            prevdiff = diff

    return max


def cross(cp, size):
    _check_params(len(cp), size)

    crossings = 0
    last_sample = 0
    for sample in _get_samples(cp, size):
        if sample <= 0 < last_sample or sample >= 0 > last_sample:
            crossings += 1
        last_sample = sample

    return crossings


def mul(cp, size, factor):
    _check_params(len(cp), size)
    clip = _get_clipfn(size)

    result = create_string_buffer(len(cp))

    for i, sample in enumerate(_get_samples(cp, size)):
        sample = clip(int(sample * factor))
        _put_sample(result, size, i, sample)

    return result.raw


def tomono(cp, size, fac1, fac2):
    _check_params(len(cp), size)
    clip = _get_clipfn(size)

    sample_count = _sample_count(cp, size)

    result = create_string_buffer(len(cp) / 2)

    for i in range(0, sample_count, 2):
        l_sample = getsample(cp, size, i)
        r_sample = getsample(cp, size, i + 1)

        sample = (l_sample * fac1) + (r_sample * fac2)
        sample = clip(sample)

        _put_sample(result, size, i / 2, sample)

    return result.raw


def tostereo(cp, size, fac1, fac2):
    _check_params(len(cp), size)

    sample_count = _sample_count(cp, size)

    result = create_string_buffer(len(cp) * 2)
    clip = _get_clipfn(size)

    for i in range(sample_count):
        sample = _get_sample(cp, size, i)

        l_sample = clip(sample * fac1)
        r_sample = clip(sample * fac2)

        _put_sample(result, size, i * 2, l_sample)
        _put_sample(result, size, i * 2 + 1, r_sample)

    return result.raw


def add(cp1, cp2, size):
    _check_params(len(cp1), size)

    if len(cp1) != len(cp2):
        raise error("Lengths should be the same")

    clip = _get_clipfn(size)
    sample_count = _sample_count(cp1, size)
    result = create_string_buffer(len(cp1))

    for i in range(sample_count):
        sample1 = getsample(cp1, size, i)
        sample2 = getsample(cp2, size, i)

        sample = clip(sample1 + sample2)

        _put_sample(result, size, i, sample)

    return result.raw


def bias(cp, size, bias):
    _check_params(len(cp), size)

    result = create_string_buffer(len(cp))

    for i, sample in enumerate(_get_samples(cp, size)):
        sample = _overflow(sample + bias, size)
        _put_sample(result, size, i, sample)

    return result.raw


def reverse(cp, size):
    _check_params(len(cp), size)
    sample_count = _sample_count(cp, size)

    result = create_string_buffer(len(cp))
    for i, sample in enumerate(_get_samples(cp, size)):
        _put_sample(result, size, sample_count - i - 1, sample)

    return result.raw


def lin2lin(cp, size, size2):
    _check_params(len(cp), size)
    _check_size(size2)

    if size == size2:
        return cp

    new_len = (len(cp) / size) * size2

    result = create_string_buffer(new_len)

    for i in range(_sample_count(cp, size)):
        sample = _get_sample(cp, size, i)
        if size < size2:
            sample = sample << (4 * size2 / size)
        elif size > size2:
            sample = sample >> (4 * size / size2)

        sample = _overflow(sample, size2)

        _put_sample(result, size2, i, sample)

    return result.raw


def ratecv(cp, size, nchannels, inrate, outrate, state, weightA=1, weightB=0):
    _check_params(len(cp), size)
    if nchannels < 1:
        raise error("# of channels should be >= 1")

    bytes_per_frame = size * nchannels
    frame_count = len(cp) / bytes_per_frame

    if bytes_per_frame / nchannels != size:
        raise OverflowError("width * nchannels too big for a C int")

    if weightA < 1 or weightB < 0:
        raise error("weightA should be >= 1, weightB should be >= 0")

    if len(cp) % bytes_per_frame != 0:
        raise error("not a whole number of frames")

    if inrate <= 0 or outrate <= 0:
        raise error("sampling rate not > 0")

    d = gcd(inrate, outrate)
    inrate /= d
    outrate /= d

    prev_i = [0] * nchannels
    cur_i = [0] * nchannels

    if state is None:
        d = -outrate
    else:
        d, samps = state

        if len(samps) != nchannels:
            raise error("illegal state argument")

        prev_i, cur_i = zip(*samps)
        prev_i, cur_i = list(prev_i), list(cur_i)

    q = frame_count / inrate
    ceiling = (q + 1) * outrate
    nbytes = ceiling * bytes_per_frame

    result = create_string_buffer(nbytes)

    samples = _get_samples(cp, size)
    out_i = 0
    while True:
        while d < 0:
            if frame_count == 0:
                samps = zip(prev_i, cur_i)
                retval = result.raw

                # slice off extra bytes
                trim_index = (out_i * bytes_per_frame) - len(retval)
                retval = buffer(retval)[:trim_index]

                return (retval, (d, tuple(samps)))

            for chan in range(nchannels):
                prev_i[chan] = cur_i[chan]
                cur_i[chan] = samples.next()

                cur_i[chan] = (
                    (weightA * cur_i[chan] + weightB * prev_i[chan])
                    / (weightA + weightB)
                )

            frame_count -= 1
            d += outrate

        while d >= 0:
            for chan in range(nchannels):
                cur_o = (
                    (prev_i[chan] * d + cur_i[chan] * (outrate - d))
                    / outrate
                )
                _put_sample(result, size, out_i, _overflow(cur_o, size))
                out_i += 1
                d -= inrate


def lin2ulaw(cp, size):
    raise NotImplementedError()


def ulaw2lin(cp, size):
    raise NotImplementedError()


def lin2alaw(cp, size):
    raise NotImplementedError()


def alaw2lin(cp, size):
    raise NotImplementedError()


def lin2adpcm(cp, size, state):
    raise NotImplementedError()


def adpcm2lin(cp, size, state):
    raise NotImplementedError()

########NEW FILE########
__FILENAME__ = silence
from .utils import (
    db_to_float,
)


def detect_silence(audio_segment, min_silence_len=1000, silence_thresh=-16):
    seg_len = len(audio_segment)
    
    # you can't have a silent portion of a sound that is longer than the sound
    if seg_len < min_silence_len:
        return []

    # convert silence threshold to a float value (so we can compare it to rms)
    silence_thresh = db_to_float(silence_thresh) * audio_segment.max_possible_amplitude

    # find silence and add start and end indicies to the to_cut list
    silence_starts = []
    
    # check every (1 sec by default) chunk of sound for silence
    slice_starts = seg_len - min_silence_len
    
    for i in range(slice_starts):
        audio_slice = audio_segment[i:i+min_silence_len]
        if audio_slice.rms < silence_thresh:
            silence_starts.append(i)

    # short circuit when there is no silence
    if not silence_starts:
        return []

    # combine the silence we detected into ranges (start ms - end ms)
    silent_ranges = []

    prev_i = silence_starts.pop(0)
    current_range_start = prev_i

    for silence_start_i in silence_starts:
        if silence_start_i != prev_i + 1:
            silent_ranges.append([current_range_start, 
                                  prev_i + min_silence_len])
            current_range_start = silence_start_i
        prev_i = silence_start_i

    silent_ranges.append([current_range_start, 
                          silence_start_i + min_silence_len])

    return silent_ranges


def detect_nonsilent(audio_segment, min_silence_len=1000, silence_thresh=-16):
    silent_ranges = detect_silence(audio_segment, min_silence_len, silence_thresh)
    len_seg = len(audio_segment)

    # if there is no silence, the whole thing is nonsilent
    if not silent_ranges:
        return [[0, len_seg]]

    # short circuit when the whole audio segment is silent
    if silent_ranges[0][0] == 0 and silent_ranges[0][1] == len_seg:
        return []

    prev_end_i = 0
    nonsilent_ranges = []
    for start_i, end_i in silent_ranges:
        nonsilent_ranges.append([prev_end_i, start_i])
        prev_end_i = end_i

    if end_i != len_seg:
        nonsilent_ranges.append([prev_end_i, len_seg])

    if nonsilent_ranges[0] == [0, 0]:
        nonsilent_ranges.pop(0)

    return nonsilent_ranges



def split_on_silence(audio_segment, min_silence_len=1000, silence_thresh=-16, keep_silence=100):
    """
    audio_segment - original pydub.AudioSegment() object

    min_silence_len - (in ms) minimum length of a silence to be used for 
        a split. default: 1000ms

    silence_thresh - (in dBFS) anything quieter than this will be 
        considered silence. default: -16dBFS

    keep_silence - (in ms) amount of silence to leave at the beginning
        and end of the chunks. Keeps the sound from sounding like it is
        abruptly cut off. (default: 100ms)
    """

    not_silence_ranges = detect_nonsilent(audio_segment, min_silence_len, silence_thresh)
    
    chunks = []
    for start_i, end_i in not_silence_ranges:
        start_i = max(0, start_i - keep_silence)
        end_i += keep_silence

        chunks.append(audio_segment[start_i:end_i])
        
    return chunks
########NEW FILE########
__FILENAME__ = utils
from __future__ import division

from math import log, ceil, floor
import os
import re
from subprocess import Popen, PIPE
import sys
from tempfile import TemporaryFile
from warnings import warn

try:
    import audioop
except ImportError:
    import pyaudioop as audioop


if sys.version_info >= (3, 0):
    basestring = str


def _fd_or_path_or_tempfile(fd, mode='w+b', tempfile=True):
    if fd is None and tempfile:
        fd = TemporaryFile(mode=mode)

    if isinstance(fd, basestring):
        fd = open(fd, mode=mode)

    return fd


def db_to_float(db):
    """
    Converts the input db to a float, which represents the equivalent
    ratio in power.
    """
    db = float(db)
    return 10 ** (db / 10)


def ratio_to_db(ratio, val2=None):
    """
    Converts the input float to db, which represents the equivalent
    to the ratio in power represented by the multiplier passed in.
    """
    ratio = float(ratio)

    # accept 2 values and use the ratio of val1 to val2
    if val2 is not None:
        ratio = ratio / val2

    return 10 * log(ratio, 10)


def register_pydub_effect(fn, name=None):
    """
    decorator for adding pydub effects to the AudioSegment objects.

    example use:

        @register_pydub_effect
        def normalize(audio_segment):
            ...

    or you can specify a name:

        @register_pydub_effect("normalize")
        def normalize_audio_segment(audio_segment):
            ...

    """
    if isinstance(fn, basestring):
        name = fn
        return lambda fn: register_pydub_effect(fn, name)

    if name is None:
        name = fn.__name__

    from .audio_segment import AudioSegment
    setattr(AudioSegment, name, fn)
    return fn


def make_chunks(audio_segment, chunk_length):
    """
    Breaks an AudioSegment into chunks that are <chunk_length> milliseconds
    long.

    if chunk_length is 50 then you'll get a list of 50 millisecond long audio
    segments back (except the last one, which can be shorter)
    """
    number_of_chunks = ceil(len(audio_segment) / float(chunk_length))
    return [audio_segment[i * chunk_length:(i + 1) * chunk_length]
            for i in range(int(number_of_chunks))]


def which(program):
    """
    Mimics behavior of UNIX which command.
    """
    #Add .exe program extension for windows support
    if os.name == "nt" and not program.endswith(".exe"):
        program += ".exe"

    envdir_list = os.environ["PATH"].split(os.pathsep)

    for envdir in envdir_list:
        program_path = os.path.join(envdir, program)
        if os.path.isfile(program_path) and os.access(program_path, os.X_OK):
            return program_path


def get_encoder_name():
    """
    Return enconder default application for system, either avconv or ffmpeg
    """
    if which("avconv"):
        return "avconv"
    elif which("ffmpeg"):
        return "ffmpeg"
    else:
        # should raise exception
        warn("Couldn't find ffmpeg or avconv - defaulting to ffmpeg, but may not work", RuntimeWarning)
        return "ffmpeg"

def get_player_name():
    """
    Return enconder default application for system, either avconv or ffmpeg
    """
    if which("avplay"):
        return "avplay"
    elif which("ffplay"):
        return "ffplay"
    else:
        # should raise exception
        warn("Couldn't find ffplay or avplay - defaulting to ffplay, but may not work", RuntimeWarning)
        return "ffplay"


def get_prober_name():
    """
    Return probe application, either avconv or ffmpeg
    """
    if which("avprobe"):
        return "avprobe"
    elif which("ffprobe"):
        return "ffprobe"
    else:
        # should raise exception
        warn("Couldn't find ffprobe or avprobe - defaulting to ffprobe, but may not work", RuntimeWarning)
        return "ffprobe"


def mediainfo(filepath):
    """Return dictionary with media info(codec, duration, size, bitrate...) from filepath
    """

    from .audio_segment import AudioSegment

    command = "{0} -v quiet -show_format -show_streams {1}".format(
        get_prober_name(),
        filepath
    )
    output = Popen(command.split(), stdout=PIPE).communicate()[0].decode("utf-8")

    rgx = re.compile(r"(?:(?P<inner_dict>.*?):)?(?P<key>.*?)\=(?P<value>.*?)$")
    info = {}
    for line in output.split("\n"):
        # print(line)
        mobj = rgx.match(line)

        if mobj:
            # print(mobj.groups())
            inner_dict, key, value = mobj.groups()

            if inner_dict:
                try:
                    info[inner_dict]
                except KeyError:
                    info[inner_dict] = {}
                info[inner_dict][key] = value
            else:
                info[key] = value

    return info

########NEW FILE########
__FILENAME__ = test
from functools import partial
import mimetypes
import os
import unittest
from tempfile import NamedTemporaryFile

from pydub import AudioSegment
from pydub.utils import (
    db_to_float,
    ratio_to_db,
    make_chunks,
    mediainfo,
)
from pydub.exceptions import (
    InvalidTag,
    InvalidID3TagVersion,
    InvalidDuration,
    CouldntDecodeError,
)
from pydub.silence import (
    detect_silence,
)

data_dir = os.path.join(os.path.dirname(__file__), 'data')


class UtilityTests(unittest.TestCase):

    def test_db_float_conversions(self):
        self.assertEqual(db_to_float(10), 10)
        self.assertEqual(db_to_float(0), 1)
        self.assertEqual(ratio_to_db(1), 0)
        self.assertEqual(ratio_to_db(10), 10)
        self.assertEqual(3, db_to_float(ratio_to_db(3)))
        self.assertEqual(12, ratio_to_db(db_to_float(12)))


class FileAccessTests(unittest.TestCase):

    def setUp(self):
        self.mp3_path = os.path.join(data_dir, 'test1.mp3')

    def test_audio_segment_from_mp3(self):
        seg1 = AudioSegment.from_mp3(os.path.join(data_dir, 'test1.mp3'))

        mp3_file = open(os.path.join(data_dir, 'test1.mp3'), 'rb')
        seg2 = AudioSegment.from_mp3(mp3_file)

        self.assertEqual(len(seg1), len(seg2))
        self.assertTrue(seg1._data == seg2._data)
        self.assertTrue(len(seg1) > 0)


test1wav = test1 = test2 = test3 = testparty = None


class AudioSegmentTests(unittest.TestCase):

    def setUp(self):
        global test1, test2, test3, testparty
        if not test1:
            test1 = AudioSegment.from_mp3(os.path.join(data_dir, 'test1.mp3'))
            test2 = AudioSegment.from_mp3(os.path.join(data_dir, 'test2.mp3'))
            test3 = AudioSegment.from_mp3(os.path.join(data_dir, 'test3.mp3'))
            testparty = AudioSegment.from_mp3(
                os.path.join(data_dir, 'party.mp3'))

        self.seg1 = test1
        self.seg2 = test2
        self.seg3 = test3
        self.mp3_seg_party = testparty

        self.ogg_file_path = os.path.join(data_dir, 'bach.ogg')
        self.mp4_file_path = os.path.join(data_dir, 'creative_common.mp4')
        self.mp3_file_path = os.path.join(data_dir, 'party.mp3')

    def assertWithinRange(self, val, lower_bound, upper_bound):
        self.assertTrue(lower_bound < val < upper_bound,
                        "%s is not in the acceptable range: %s - %s" %
                        (val, lower_bound, upper_bound))

    def assertWithinTolerance(self, val, expected, tolerance=None,
                              percentage=None):
        if percentage is not None:
            tolerance = val * percentage
        lower_bound = val - tolerance
        upper_bound = val + tolerance
        self.assertWithinRange(val, lower_bound, upper_bound)

    def test_concat(self):
        catted_audio = self.seg1 + self.seg2

        expected = len(self.seg1) + len(self.seg2)
        self.assertWithinTolerance(len(catted_audio), expected, 1)

    def test_append(self):
        merged1 = self.seg3.append(self.seg1, crossfade=100)
        merged2 = self.seg3.append(self.seg2, crossfade=100)

        self.assertEqual(len(merged1), len(self.seg1) + len(self.seg3) - 100)
        self.assertEqual(len(merged2), len(self.seg2) + len(self.seg3) - 100)

    def test_volume_with_add_sub(self):
        quieter = self.seg1 - 6
        self.assertAlmostEqual(ratio_to_db(quieter.rms, self.seg1.rms),
                               -6,
                               places=2)

        louder = quieter + 2.5
        self.assertAlmostEqual(ratio_to_db(louder.rms, quieter.rms),
                               2.5,
                               places=2)

    def test_repeat_with_multiply(self):
        seg = self.seg1 * 3
        expected = len(self.seg1) * 3
        expected = (expected - 2, expected + 2)
        self.assertTrue(expected[0] < len(seg) < expected[1])

    def test_overlay(self):
        seg_mult = self.seg1[:5000] * self.seg2[:3000]
        seg_over = self.seg1[:5000].overlay(self.seg2[:3000], loop=True)

        self.assertEqual(len(seg_mult), len(seg_over))
        self.assertTrue(seg_mult._data == seg_over._data)

        self.assertEqual(len(seg_mult), 5000)
        self.assertEqual(len(seg_over), 5000)

    def test_slicing(self):
        empty = self.seg1[:0]
        second_long_slice = self.seg1[:1000]
        remainder = self.seg1[1000:]

        self.assertEqual(len(empty), 0)
        self.assertEqual(len(second_long_slice), 1000)
        self.assertEqual(len(remainder), len(self.seg1) - 1000)

        last_5_seconds = self.seg1[-5000:]
        before = self.seg1[:-5000]

        self.assertEqual(len(last_5_seconds), 5000)
        self.assertEqual(len(before), len(self.seg1) - 5000)

        past_end = second_long_slice[:1500]
        self.assertTrue(second_long_slice._data == past_end._data)

    def test_indexing(self):
        short = self.seg1[:100]

        rebuilt1 = self.seg1[:0]
        for part in short:
            rebuilt1 += part

        rebuilt2 = sum([part for part in short], short[:0])

        self.assertTrue(short._data == rebuilt1._data)
        self.assertTrue(short._data == rebuilt2._data)

    def test_set_channels(self):
        mono = self.seg1.set_channels(1)
        stereo = mono.set_channels(2)

        self.assertEqual(len(self.seg1), len(mono))
        self.assertEqual(len(self.seg1), len(stereo))

        mono = self.seg2.set_channels(1)
        mono = mono.set_frame_rate(22050)

        self.assertEqual(len(mono), len(self.seg2))

        monomp3 = AudioSegment.from_mp3(mono.export())
        self.assertWithinTolerance(len(monomp3), len(self.seg2),
                                   percentage=0.01)

        merged = monomp3.append(stereo, crossfade=100)
        self.assertWithinTolerance(len(merged),
                                   len(self.seg1) + len(self.seg2) - 100,
                                   tolerance=1)

    def test_export_as_mp3(self):
        seg = self.seg1
        exported_mp3 = seg.export()
        seg_exported_mp3 = AudioSegment.from_mp3(exported_mp3)

        self.assertWithinTolerance(len(seg_exported_mp3),
                                   len(seg),
                                   percentage=0.01)

    def test_export_as_wav(self):
        seg = self.seg1
        exported_wav = seg.export(format='wav')
        seg_exported_wav = AudioSegment.from_wav(exported_wav)

        self.assertWithinTolerance(len(seg_exported_wav),
                                   len(seg),
                                   percentage=0.01)

    def test_export_as_ogg(self):
        seg = self.seg1
        exported_ogg = seg.export(format='ogg')
        seg_exported_ogg = AudioSegment.from_ogg(exported_ogg)

        self.assertWithinTolerance(len(seg_exported_ogg),
                                   len(seg),
                                   percentage=0.01)

    def test_export_forced_codec(self):
        seg = self.seg1 + self.seg2

        with NamedTemporaryFile('w+b', suffix='.ogg') as tmp_file:
            seg.export(tmp_file.name, 'ogg', codec='libvorbis')
            exported = AudioSegment.from_ogg(tmp_file.name)
            self.assertWithinTolerance(len(exported),
                                       len(seg),
                                       percentage=0.01)

    def test_fades(self):
        seg = self.seg1[:10000]

        # 1 ms difference in the position of the end of the fade out
        inf_end = seg.fade(start=0, end=float('inf'), to_gain=-120)
        negative_end = seg.fade(start=0, end=-1, to_gain=-120)

        self.assertWithinTolerance(inf_end.rms, negative_end.rms,
                                   percentage=0.001)
        self.assertTrue(negative_end.rms <= inf_end.rms)
        self.assertTrue(inf_end.rms < seg.rms)

        self.assertEqual(len(inf_end), len(seg))

        self.assertTrue(-3 < ratio_to_db(inf_end.rms, seg.rms) < -2)

        # use a slice out of the middle to make sure there is audio
        seg = self.seg2[2000:8000]
        fade_out = seg.fade_out(1000)
        fade_in = seg.fade_in(1000)

        self.assertTrue(0 < fade_out.rms < seg.rms)
        self.assertTrue(0 < fade_in.rms < seg.rms)

        self.assertEqual(len(fade_out), len(seg))
        self.assertEqual(len(fade_in), len(seg))

        db_at_beginning = ratio_to_db(fade_in[:1000].rms, seg[:1000].rms)
        db_at_end = ratio_to_db(fade_in[-1000:].rms, seg[-1000:].rms)
        self.assertTrue(db_at_beginning < db_at_end)

        db_at_beginning = ratio_to_db(fade_out[:1000].rms, seg[:1000].rms)
        db_at_end = ratio_to_db(fade_out[-1000:].rms, seg[-1000:].rms)
        self.assertTrue(db_at_end < db_at_beginning)

    def test_reverse(self):
        seg = self.seg1
        rseg = seg.reverse()

        # the reversed audio should be exactly equal in playback duration
        self.assertEqual(len(seg), len(rseg))

        r2seg = rseg.reverse()

        # if you reverse it twice you should get an identical AudioSegment
        self.assertEqual(seg, r2seg)

    def test_normalize(self):
        seg = self.seg1
        normalized = seg.normalize(0.0)

        self.assertEqual(len(normalized), len(seg))
        self.assertTrue(normalized.rms > seg.rms)
        self.assertWithinTolerance(
            normalized.max,
            normalized.max_possible_amplitude,
            percentage=0.0001
        )

    def test_for_accidental_shortening(self):
        seg = self.mp3_seg_party
        with NamedTemporaryFile('w+b', suffix='.mp3') as tmp_mp3_file:
            seg.export(tmp_mp3_file.name)

            for i in range(3):
                AudioSegment.from_mp3(tmp_mp3_file.name).export(tmp_mp3_file.name, "mp3")

            tmp_seg = AudioSegment.from_mp3(tmp_mp3_file.name)
            self.assertFalse(len(tmp_seg) < len(seg))

    def test_formats(self):
        seg_m4a = AudioSegment.from_file(
            os.path.join(data_dir, 'format_test.m4a'), "m4a")
        self.assertTrue(len(seg_m4a))

    def test_equal_and_not_equal(self):
        wav_file = self.seg1.export(format='wav')
        wav = AudioSegment.from_wav(wav_file)
        self.assertTrue(self.seg1 == wav)
        self.assertFalse(self.seg1 != wav)

    def test_duration(self):
        self.assertEqual(int(self.seg1.duration_seconds), 10)

        wav_file = self.seg1.export(format='wav')
        wav = AudioSegment.from_wav(wav_file)
        self.assertEqual(wav.duration_seconds, self.seg1.duration_seconds)

    def test_autodetect_format(self):
        aac_path = os.path.join(data_dir, 'wrong_extension.aac')
        fn = partial(AudioSegment.from_file, aac_path, "aac")
        self.assertRaises(CouldntDecodeError, fn)

        # Trying to auto detect input file format
        aac_file = AudioSegment.from_file(
            os.path.join(data_dir, 'wrong_extension.aac'))
        self.assertEqual(int(aac_file.duration_seconds), 9)

    def test_export_ogg_as_mp3(self):
        with NamedTemporaryFile('w+b', suffix='.mp3') as tmp_mp3_file:
            AudioSegment.from_file(self.ogg_file_path).export(tmp_mp3_file,
                                                              format="mp3")
            tmp_file_type, _ = mimetypes.guess_type(tmp_mp3_file.name)
            self.assertEqual(tmp_file_type, 'audio/mpeg')

    def test_export_mp3_as_ogg(self):
        with NamedTemporaryFile('w+b', suffix='.ogg') as tmp_ogg_file:
            AudioSegment.from_file(self.mp3_file_path).export(tmp_ogg_file,
                                                              format="ogg")
            tmp_file_type, _ = mimetypes.guess_type(tmp_ogg_file.name)
            self.assertEqual(tmp_file_type, 'audio/ogg')

    def test_export_mp4_as_ogg(self):
        with NamedTemporaryFile('w+b', suffix='.ogg') as tmp_ogg_file:
            AudioSegment.from_file(self.mp4_file_path).export(tmp_ogg_file,
                                                              format="ogg")
            tmp_file_type, _ = mimetypes.guess_type(tmp_ogg_file.name)
            self.assertEqual(tmp_file_type, 'audio/ogg')

    def test_export_mp4_as_mp3(self):
        with NamedTemporaryFile('w+b', suffix='.mp3') as tmp_mp3_file:
            AudioSegment.from_file(self.mp4_file_path).export(tmp_mp3_file,
                                                              format="mp3")
            tmp_file_type, _ = mimetypes.guess_type(tmp_mp3_file.name)
            self.assertEqual(tmp_file_type, 'audio/mpeg')

    def test_export_mp4_as_wav(self):
        with NamedTemporaryFile('w+b', suffix='.wav') as tmp_wav_file:
            AudioSegment.from_file(self.mp4_file_path).export(tmp_wav_file,
                                                              format="mp3")
            tmp_file_type, _ = mimetypes.guess_type(tmp_wav_file.name)
            self.assertEqual(tmp_file_type, 'audio/x-wav')

    def test_export_mp4_as_mp3_with_tags(self):
        with NamedTemporaryFile('w+b', suffix='.mp3') as tmp_mp3_file:
            tags_dict = {
                'title': "The Title You Want",
                'artist': "Artist's name",
                'album': "Name of the Album"
            }
            AudioSegment.from_file(self.mp4_file_path).export(tmp_mp3_file,
                                                              format="mp3",
                                                              tags=tags_dict)
            tmp_file_type, _ = mimetypes.guess_type(tmp_mp3_file.name)
            self.assertEqual(tmp_file_type, 'audio/mpeg')

    def test_export_mp4_as_mp3_with_tags_raises_exception_when_tags_are_not_a_dictionary(self):
        with NamedTemporaryFile('w+b', suffix='.mp3') as tmp_mp3_file:
            json = '{"title": "The Title You Want", "album": "Name of the Album", "artist": "Artist\'s name"}'
            func = partial(
                AudioSegment.from_file(self.mp4_file_path).export, tmp_mp3_file,
                format="mp3", tags=json)
            self.assertRaises(InvalidTag, func)

    def test_export_mp4_as_mp3_with_tags_raises_exception_when_id3version_is_wrong(self):
        tags = {'artist': 'Artist', 'title': 'Title'}
        with NamedTemporaryFile('w+b', suffix='.mp3') as tmp_mp3_file:
            func = partial(
                AudioSegment.from_file(self.mp4_file_path).export,
                tmp_mp3_file,
                format="mp3",
                tags=tags,
                id3v2_version='BAD VERSION'
            )
            self.assertRaises(InvalidID3TagVersion, func)

    def test_export_mp3_with_tags(self):
        tags = {'artist': 'Mozart', 'title': 'The Magic Flute'}

        with NamedTemporaryFile('w+b', suffix='.mp3') as tmp_mp3_file:
            AudioSegment.from_file(self.mp4_file_path).export(tmp_mp3_file, format="mp3", tags=tags)

            info = mediainfo(filepath=tmp_mp3_file.name)
            info_tags = info["TAG"]

            self.assertEqual(info_tags["artist"], "Mozart")
            self.assertEqual(info_tags["title"], "The Magic Flute")

    def test_fade_raises_exception_when_duration_start_end_are_none(self):
        seg = self.seg1
        func = partial(seg.fade, start=1, end=1, duration=1)
        self.assertRaises(TypeError, func)

    def test_silent(self):
        seg = AudioSegment.silent(len(self.seg1))
        self.assertEqual(len(self.seg1), len(seg))
        self.assertEqual(seg.rms, 0)
        self.assertEqual(seg.frame_width, 2)

        seg_8bit = seg.set_sample_width(1)
        self.assertEqual(seg_8bit.sample_width, 1)
        self.assertEqual(seg_8bit.frame_width, 1)
        self.assertEqual(seg_8bit.rms, 0)

        seg *= self.seg1
        self.assertEqual(seg.rms, self.seg1.rms)
        self.assertEqual(len(seg), len(self.seg1))
        self.assertEqual(seg.frame_width, self.seg1.frame_width)
        self.assertEqual(seg.frame_rate, self.seg1.frame_rate)

    def test_fade_raises_exception_when_duration_is_negative(self):
        seg = self.seg1
        func = partial(seg.fade,
                       to_gain=1,
                       from_gain=1,
                       start=None,
                       end=None,
                       duration=-1)
        self.assertRaises(InvalidDuration, func)

    def test_make_chunks(self):
        seg = self.seg1
        chunks = make_chunks(seg, 100)
        seg2 = chunks[0]
        for chunk in chunks[1:]:
            seg2 += chunk
        self.assertEqual(len(seg), len(seg2))

    def test_empty(self):
        self.assertEqual(len(self.seg1), len(self.seg1 + AudioSegment.empty()))
        self.assertEqual(len(self.seg2), len(self.seg2 + AudioSegment.empty()))
        self.assertEqual(len(self.seg3), len(self.seg3 + AudioSegment.empty()))

    def test_speedup(self):
        speedup_seg = self.seg1.speedup(2.0)

        self.assertWithinTolerance(
            len(self.seg1) / 2, len(speedup_seg), percentage=0.01)

    def test_dBFS(self):
        seg_8bit = self.seg1.set_sample_width(1)
        self.assertWithinTolerance(seg_8bit.dBFS, -8.88, tolerance=0.01)
        self.assertWithinTolerance(self.seg1.dBFS, -8.88, tolerance=0.01)
        self.assertWithinTolerance(self.seg2.dBFS, -10.39, tolerance=0.01)
        self.assertWithinTolerance(self.seg3.dBFS, -6.47, tolerance=0.01)

    def test_compress(self):
        compressed = self.seg1.compress_dynamic_range()
        self.assertWithinTolerance(self.seg1.dBFS - compressed.dBFS,
                                   10.0,
                                   tolerance=10.0)

        # Highest peak should be lower
        self.assertTrue(compressed.max < self.seg1.max)

        # average volume should be reduced
        self.assertTrue(compressed.rms < self.seg1.rms)

    def test_exporting_to_ogg_uses_default_codec_when_codec_param_is_none(self):
        with NamedTemporaryFile('w+b', suffix='.ogg') as tmp_ogg_file:
            AudioSegment.from_file(self.mp4_file_path).export(tmp_ogg_file, format="ogg")

            info = mediainfo(filepath=tmp_ogg_file.name)

        self.assertEqual(info["codec_name"], "vorbis")
        self.assertEqual(info["format_name"], "ogg")

    def test_zero_length_segment(self):
        self.assertEqual(0, len(self.seg1[0:0]))


class SilenceTests(unittest.TestCase):
    
    def setUp(self):
        global test1wav
        if not test1wav:
            test1wav = AudioSegment.from_wav(os.path.join(data_dir, 'test1.wav'))

        self.seg1 = test1wav

    def test_detect_completely_silent_segment(self):
        seg = AudioSegment.silent(5000)
        silent_ranges = detect_silence(seg, min_silence_len=1000, silence_thresh=-10)
        self.assertEqual(silent_ranges, [[0, 4999]])

    def test_detect_too_long_silence(self):
        seg = AudioSegment.silent(3000)
        silent_ranges = detect_silence(seg, min_silence_len=5000, silence_thresh=-10)
        self.assertEqual(silent_ranges, [])

    def test_detect_silence_seg1(self):
        silent_ranges = detect_silence(self.seg1, min_silence_len=500, silence_thresh=-10)
        self.assertEqual(silent_ranges, [[0, 775], [3141, 4033], [5516, 6051]])




if __name__ == "__main__":
    import sys

    if sys.version_info >= (3, 1):
        unittest.main(warnings="ignore")
    else:
        unittest.main()

########NEW FILE########
