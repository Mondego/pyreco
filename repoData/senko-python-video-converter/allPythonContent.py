__FILENAME__ = avcodecs
#!/usr/bin/env python


class BaseCodec(object):
    """
    Base audio/video codec class.
    """

    encoder_options = {}
    codec_name = None
    ffmpeg_codec_name = None

    def parse_options(self, opt):
        if 'codec' not in opt or opt['codec'] != self.codec_name:
            raise ValueError('invalid codec name')
        return None

    def _codec_specific_parse_options(self, safe):
        return safe

    def _codec_specific_produce_ffmpeg_list(self, safe):
        return []

    def safe_options(self, opts):
        safe = {}

        # Only copy options that are expected and of correct type
        # (and do typecasting on them)
        for k, v in opts.items():
            if k in self.encoder_options:
                typ = self.encoder_options[k]
                try:
                    safe[k] = typ(v)
                except:
                    pass

        return safe


class AudioCodec(BaseCodec):
    """
    Base audio codec class handles general audio options. Possible
    parameters are:
      * codec (string) - audio codec name
      * channels (integer) - number of audio channels
      * bitrate (integer) - stream bitrate
      * samplerate (integer) - sample rate (frequency)

    Supported audio codecs are: null (no audio), copy (copy from
    original), vorbis, aac, mp3, mp2
    """

    encoder_options = {
        'codec': str,
        'channels': int,
        'bitrate': int,
        'samplerate': int
    }

    def parse_options(self, opt):
        super(AudioCodec, self).parse_options(opt)

        safe = self.safe_options(opt)

        if 'channels' in safe:
            c = safe['channels']
            if c < 1 or c > 12:
                del safe['channels']

        if 'bitrate' in safe:
            br = safe['bitrate']
            if br < 8 or br > 512:
                del safe['bitrate']

        if 'samplerate' in safe:
            f = safe['samplerate']
            if f < 1000 or f > 50000:
                del safe['samplerate']

        safe = self._codec_specific_parse_options(safe)

        optlist = ['-acodec', self.ffmpeg_codec_name]
        if 'channels' in safe:
            optlist.extend(['-ac', str(safe['channels'])])
        if 'bitrate' in safe:
            optlist.extend(['-ab', str(safe['bitrate']) + 'k'])
        if 'samplerate' in safe:
            optlist.extend(['-ar', str(safe['samplerate'])])

        optlist.extend(self._codec_specific_produce_ffmpeg_list(safe))
        return optlist


class SubtitleCodec(BaseCodec):
    """
    Base subtitle codec class handles general subtitle options. Possible
    parameters are:
      * codec (string) - subtitle codec name (mov_text, subrib, ssa only supported currently)
      * language (string) - language of subtitle stream (3 char code)
      * forced (int) - force subtitles (1 true, 0 false)
      * default (int) - default subtitles (1 true, 0 false)

    Supported subtitle codecs are: null (no subtitle), mov_text
    """

    encoder_options = {
        'codec': str,
        'language': str,
        'forced': int,
        'default': int
    }

    def parse_options(self, opt):
        super(SubtitleCodec, self).parse_options(opt)
        safe = self.safe_options(opt)

        if 'forced' in safe:
            f = safe['forced']
            if f < 0 or f > 1:
                del safe['forced']

        if 'default' in safe:
            d = safe['default']
            if d < 0 or d > 1:
                del safe['default']

        if 'language' in safe:
            l = safe['language']
            if len(l) > 3:
                del safe['language']

        safe = self._codec_specific_parse_options(safe)

        optlist = ['-scodec', self.ffmpeg_codec_name]

        optlist.extend(self._codec_specific_produce_ffmpeg_list(safe))
        return optlist


class VideoCodec(BaseCodec):
    """
    Base video codec class handles general video options. Possible
    parameters are:
      * codec (string) - video codec name
      * bitrate (string) - stream bitrate
      * fps (integer) - frames per second
      * width (integer) - video width
      * height (integer) - video height
      * mode (string) - aspect preserval mode; one of:
            * stretch (default) - don't preserve aspect
            * crop - crop extra w/h
            * pad - pad with black bars
      * src_width (int) - source width
      * src_height (int) - source height

    Aspect preserval mode is only used if both source
    and both destination sizes are specified. If source
    dimensions are not specified, aspect settings are ignored.

    If source dimensions are specified, and only one
    of the destination dimensions is specified, the other one
    is calculated to preserve the aspect ratio.

    Supported video codecs are: null (no video), copy (copy directly
    from the source), Theora, H.264/AVC, DivX, VP8, H.263, Flv,
    MPEG-1, MPEG-2.
    """

    encoder_options = {
        'codec': str,
        'bitrate': int,
        'fps': int,
        'width': int,
        'height': int,
        'mode': str,
        'src_width': int,
        'src_height': int,
    }

    def _aspect_corrections(self, sw, sh, w, h, mode):
        # If we don't have source info, we don't try to calculate
        # aspect corrections
        if not sw or not sh:
            return w, h, None

        # Original aspect ratio
        aspect = (1.0 * sw) / (1.0 * sh)

        # If we have only one dimension, we can easily calculate
        # the other to match the source aspect ratio
        if not w and not h:
            return w, h, None
        elif w and not h:
            h = int((1.0 * w) / aspect)
            return w, h, None
        elif h and not w:
            w = int(aspect * h)
            return w, h, None

        # If source and target dimensions are actually the same aspect
        # ratio, we've got nothing to do
        if int(aspect * h) == w:
            return w, h, None

        if mode == 'stretch':
            return w, h, None

        target_aspect = (1.0 * w) / (1.0 * h)

        if mode == 'crop':
            # source is taller, need to crop top/bottom
            if target_aspect > aspect:  # target is taller
                h0 = int(w / aspect)
                assert h0 > h, (sw, sh, w, h)
                dh = (h0 - h) / 2
                return w, h0, 'crop=%d:%d:0:%d' % (w, h, dh)
            else:  # source is wider, need to crop left/right
                w0 = int(h * aspect)
                assert w0 > w, (sw, sh, w, h)
                dw = (w0 - w) / 2
                return w0, h, 'crop=%d:%d:%d:0' % (w, h, dw)

        if mode == 'pad':
            # target is taller, need to pad top/bottom
            if target_aspect < aspect:
                h1 = int(w / aspect)
                assert h1 < h, (sw, sh, w, h)
                dh = (h - h1) / 2
                return w, h1, 'pad=%d:%d:0:%d' % (w, h, dh)  # FIXED
            else:  # target is wider, need to pad left/right
                w1 = int(h * aspect)
                assert w1 < w, (sw, sh, w, h)
                dw = (w - w1) / 2
                return w1, h, 'pad=%d:%d:%d:0' % (w, h, dw)  # FIXED

        assert False, mode

    def parse_options(self, opt):
        super(VideoCodec, self).parse_options(opt)

        safe = self.safe_options(opt)

        if 'fps' in safe:
            f = safe['fps']
            if f < 1 or f > 120:
                del safe['fps']

        if 'bitrate' in safe:
            br = safe['bitrate']
            if br < 16 or br > 15000:
                del safe['bitrate']

        w = None
        h = None

        if 'width' in safe:
            w = safe['width']
            if w < 16 or w > 4000:
                w = None

        if 'height' in safe:
            h = safe['height']
            if h < 16 or h > 3000:
                h = None

        sw = None
        sh = None

        if 'src_width' in safe and 'src_height' in safe:
            sw = safe['src_width']
            sh = safe['src_height']
            if not sw or not sh:
                sw = None
                sh = None

        mode = 'stretch'
        if 'mode' in safe:
            if safe['mode'] in ['stretch', 'crop', 'pad']:
                mode = safe['mode']

        ow, oh = w, h  # FIXED
        w, h, filters = self._aspect_corrections(sw, sh, w, h, mode)

        safe['width'] = w
        safe['height'] = h
        safe['aspect_filters'] = filters

        if w and h:
            safe['aspect'] = '%d:%d' % (w, h)

        safe = self._codec_specific_parse_options(safe)

        w = safe['width']
        h = safe['height']
        filters = safe['aspect_filters']

        optlist = ['-vcodec', self.ffmpeg_codec_name]
        if 'fps' in safe:
            optlist.extend(['-r', str(safe['fps'])])
        if 'bitrate' in safe:
            optlist.extend(['-vb', str(safe['bitrate']) + 'k'])  # FIXED
        if w and h:
            optlist.extend(['-s', '%dx%d' % (w, h)])

            if ow and oh:
                optlist.extend(['-aspect', '%d:%d' % (ow, oh)])

        if filters:
            optlist.extend(['-vf', filters])

        optlist.extend(self._codec_specific_produce_ffmpeg_list(safe))
        return optlist


class AudioNullCodec(BaseCodec):
    """
    Null audio codec (no audio).
    """
    codec_name = None

    def parse_options(self, opt):
        return ['-an']


class VideoNullCodec(BaseCodec):
    """
    Null video codec (no video).
    """

    codec_name = None

    def parse_options(self, opt):
        return ['-vn']


class SubtitleNullCodec(BaseCodec):
    """
    Null video codec (no video).
    """

    codec_name = None

    def parse_options(self, opt):
        return ['-sn']


class AudioCopyCodec(BaseCodec):
    """
    Copy audio stream directly from the source.
    """
    codec_name = 'copy'

    def parse_options(self, opt):
        return ['-acodec', 'copy']


class VideoCopyCodec(BaseCodec):
    """
    Copy video stream directly from the source.
    """
    codec_name = 'copy'

    def parse_options(self, opt):
        return ['-vcodec', 'copy']


class SubtitleCopyCodec(BaseCodec):
    """
    Copy subtitle stream directly from the source.
    """
    codec_name = 'copy'

    def parse_options(self, opt):
        return ['-scodec', 'copy']

# Audio Codecs
class VorbisCodec(AudioCodec):
    """
    Vorbis audio codec.
    @see http://ffmpeg.org/trac/ffmpeg/wiki/TheoraVorbisEncodingGuide
    """
    codec_name = 'vorbis'
    ffmpeg_codec_name = 'libvorbis'
    encoder_options = AudioCodec.encoder_options.copy()
    encoder_options.update({
        'quality': int,  # audio quality. Range is 0-10(highest quality)
        # 3-6 is a good range to try. Default is 3
    })

    def _codec_specific_produce_ffmpeg_list(self, safe):
        optlist = []
        if 'quality' in safe:
            optlist.extend(['-qscale:a', safe['quality']])
        return optlist


class AacCodec(AudioCodec):
    """
    AAC audio codec.
    """
    codec_name = 'aac'
    ffmpeg_codec_name = 'aac'
    aac_experimental_enable = ['-strict', 'experimental']

    def _codec_specific_produce_ffmpeg_list(self, safe):
        return self.aac_experimental_enable


class FdkAacCodec(AudioCodec):
    """
    AAC audio codec.
    """
    codec_name = 'libfdk_aac'
    ffmpeg_codec_name = 'libfdk_aac'


class Ac3Codec(AudioCodec):
    """
    AC3 audio codec.
    """
    codec_name = 'ac3'
    ffmpeg_codec_name = 'ac3'


class FlacCodec(AudioCodec):
    """
    FLAC audio codec.
    """
    codec_name = 'flac'
    ffmpeg_codec_name = 'flac'


class DtsCodec(AudioCodec):
    """
    DTS audio codec.
    """
    codec_name = 'dts'
    ffmpeg_codec_name = 'dts'


class Mp3Codec(AudioCodec):
    """
    MP3 (MPEG layer 3) audio codec.
    """
    codec_name = 'mp3'
    ffmpeg_codec_name = 'libmp3lame'


class Mp2Codec(AudioCodec):
    """
    MP2 (MPEG layer 2) audio codec.
    """
    codec_name = 'mp2'
    ffmpeg_codec_name = 'mp2'


# Video Codecs
class TheoraCodec(VideoCodec):
    """
    Theora video codec.
    @see http://ffmpeg.org/trac/ffmpeg/wiki/TheoraVorbisEncodingGuide
    """
    codec_name = 'theora'
    ffmpeg_codec_name = 'libtheora'
    encoder_options = VideoCodec.encoder_options.copy()
    encoder_options.update({
        'quality': int,  # audio quality. Range is 0-10(highest quality)
        # 5-7 is a good range to try (default is 200k bitrate)
    })

    def _codec_specific_produce_ffmpeg_list(self, safe):
        optlist = []
        if 'quality' in safe:
            optlist.extend(['-qscale:v', safe['quality']])
        return optlist


class H264Codec(VideoCodec):
    """
    H.264/AVC video codec.
    @see http://ffmpeg.org/trac/ffmpeg/wiki/x264EncodingGuide
    """
    codec_name = 'h264'
    ffmpeg_codec_name = 'libx264'
    encoder_options = VideoCodec.encoder_options.copy()
    encoder_options.update({
        'preset': str,  # common presets are ultrafast, superfast, veryfast,
        # faster, fast, medium(default), slow, slower, veryslow
        'quality': int,  # constant rate factor, range:0(lossless)-51(worst)
        # default:23, recommended: 18-28
        # http://mewiki.project357.com/wiki/X264_Settings#profile
        'profile': str,  # default: not-set, for valid values see above link
        'tune': str,  # default: not-set, for valid values see above link
    })

    def _codec_specific_produce_ffmpeg_list(self, safe):
        optlist = []
        if 'preset' in safe:
            optlist.extend(['-preset', safe['preset']])
        if 'quality' in safe:
            optlist.extend(['-crf', safe['quality']])
        if 'profile' in safe:
            optlist.extend(['-profile', safe['profile']])
        if 'tune' in safe:
            optlist.extend(['-tune', safe['tune']])
        return optlist


class DivxCodec(VideoCodec):
    """
    DivX video codec.
    """
    codec_name = 'divx'
    ffmpeg_codec_name = 'mpeg4'


class Vp8Codec(VideoCodec):
    """
    Google VP8 video codec.
    """
    codec_name = 'vp8'
    ffmpeg_codec_name = 'libvpx'


class H263Codec(VideoCodec):
    """
    H.263 video codec.
    """
    codec_name = 'h263'
    ffmpeg_codec_name = 'h263'


class FlvCodec(VideoCodec):
    """
    Flash Video codec.
    """
    codec_name = 'flv'
    ffmpeg_codec_name = 'flv'


class MpegCodec(VideoCodec):
    """
    Base MPEG video codec.
    """
    # Workaround for a bug in ffmpeg in which aspect ratio
    # is not correctly preserved, so we have to set it
    # again in vf; take care to put it *before* crop/pad, so
    # it uses the same adjusted dimensions as the codec itself
    # (pad/crop will adjust it further if neccessary)
    def _codec_specific_parse_options(self, safe):
        w = safe['width']
        h = safe['height']

        if w and h:
            filters = safe['aspect_filters']
            tmp = 'aspect=%d:%d' % (w, h)

            if filters is None:
                safe['aspect_filters'] = tmp
            else:
                safe['aspect_filters'] = tmp + ',' + filters

        return safe


class Mpeg1Codec(MpegCodec):
    """
    MPEG-1 video codec.
    """
    codec_name = 'mpeg1'
    ffmpeg_codec_name = 'mpeg1video'


class Mpeg2Codec(MpegCodec):
    """
    MPEG-2 video codec.
    """
    codec_name = 'mpeg2'
    ffmpeg_codec_name = 'mpeg2video'


# Subtitle Codecs
class MOVTextCodec(SubtitleCodec):
    """
    mov_text subtitle codec.
    """
    codec_name = 'mov_text'
    ffmpeg_codec_name = 'mov_text'


class SSA(SubtitleCodec):
    """
    SSA (SubStation Alpha) subtitle.
    """
    codec_name = 'ass'
    ffmpeg_codec_name = 'ass'


class SubRip(SubtitleCodec):
    """
    SubRip subtitle.
    """
    codec_name = 'subrip'
    ffmpeg_codec_name = 'subrip'


class DVBSub(SubtitleCodec):
    """
    DVB subtitles.
    """
    codec_name = 'dvbsub'
    ffmpeg_codec_name = 'dvbsub'


class DVDSub(SubtitleCodec):
    """
    DVD subtitles.
    """
    codec_name = 'dvdsub'
    ffmpeg_codec_name = 'dvdsub'


audio_codec_list = [
    AudioNullCodec, AudioCopyCodec, VorbisCodec, AacCodec, Mp3Codec, Mp2Codec,
    FdkAacCodec, Ac3Codec, DtsCodec, FlacCodec
]

video_codec_list = [
    VideoNullCodec, VideoCopyCodec, TheoraCodec, H264Codec,
    DivxCodec, Vp8Codec, H263Codec, FlvCodec, Mpeg1Codec,
    Mpeg2Codec
]

subtitle_codec_list = [
    SubtitleNullCodec, SubtitleCopyCodec, MOVTextCodec, SSA, SubRip, DVDSub,
    DVBSub
]

########NEW FILE########
__FILENAME__ = ffmpeg
#!/usr/bin/env python

import os.path
import os
import re
import signal
from subprocess import Popen, PIPE
import logging

logger = logging.getLogger(__name__)


class FFMpegError(Exception):
    pass


class FFMpegConvertError(Exception):
    def __init__(self, message, cmd, output, details=None, pid=0):
        """
        @param    message: Error message.
        @type     message: C{str}

        @param    cmd: Full command string used to spawn ffmpeg.
        @type     cmd: C{str}

        @param    output: Full stdout output from the ffmpeg command.
        @type     output: C{str}

        @param    details: Optional error details.
        @type     details: C{str}
        """
        super(FFMpegConvertError, self).__init__(message)

        self.cmd = cmd
        self.output = output
        self.details = details
        self.pid = pid

    def __repr__(self):
        error = self.details if self.details else self.message
        return ('<FFMpegConvertError error="%s", pid=%s, cmd="%s">' %
                (error, self.pid, self.cmd))

    def __str__(self):
        return self.__repr__()


class MediaFormatInfo(object):
    """
    Describes the media container format. The attributes are:
      * format - format (short) name (eg. "ogg")
      * fullname - format full (descriptive) name
      * bitrate - total bitrate (bps)
      * duration - media duration in seconds
      * filesize - file size
    """

    def __init__(self):
        self.format = None
        self.fullname = None
        self.bitrate = None
        self.duration = None
        self.filesize = None

    def parse_ffprobe(self, key, val):
        """
        Parse raw ffprobe output (key=value).
        """
        if key == 'format_name':
            self.format = val
        elif key == 'format_long_name':
            self.fullname = val
        elif key == 'bit_rate':
            self.bitrate = MediaStreamInfo.parse_float(val, None)
        elif key == 'duration':
            self.duration = MediaStreamInfo.parse_float(val, None)
        elif key == 'size':
            self.size = MediaStreamInfo.parse_float(val, None)

    def __repr__(self):
        if self.duration is None:
            return 'MediaFormatInfo(format=%s)' % self.format
        return 'MediaFormatInfo(format=%s, duration=%.2f)' % (self.format,
                                                              self.duration)


class MediaStreamInfo(object):
    """
    Describes one stream inside a media file. The general
    attributes are:
      * index - stream index inside the container (0-based)
      * type - stream type, either 'audio' or 'video'
      * codec - codec (short) name (e.g "vorbis", "theora")
      * codec_desc - codec full (descriptive) name
      * duration - stream duration in seconds
      * metadata - optional metadata associated with a video or audio stream
      * bitrate - stream bitrate in bytes/second
      * attached_pic - (0, 1 or None) is stream a poster image? (e.g. in mp3)
    Video-specific attributes are:
      * video_width - width of video in pixels
      * video_height - height of video in pixels
      * video_fps - average frames per second
    Audio-specific attributes are:
      * audio_channels - the number of channels in the stream
      * audio_samplerate - sample rate (Hz)
    """

    def __init__(self):
        self.index = None
        self.type = None
        self.codec = None
        self.codec_desc = None
        self.duration = None
        self.bitrate = None
        self.video_width = None
        self.video_height = None
        self.video_fps = None
        self.audio_channels = None
        self.audio_samplerate = None
        self.attached_pic = None
        self.sub_forced = None
        self.sub_default = None
        self.metadata = {}

    @staticmethod
    def parse_float(val, default=0.0):
        try:
            return float(val)
        except:
            return default

    @staticmethod
    def parse_int(val, default=0):
        try:
            return int(val)
        except:
            return default

    def parse_ffprobe(self, key, val):
        """
        Parse raw ffprobe output (key=value).
        """

        if key == 'index':
            self.index = self.parse_int(val)
        elif key == 'codec_type':
            self.type = val
        elif key == 'codec_name':
            self.codec = val
        elif key == 'codec_long_name':
            self.codec_desc = val
        elif key == 'duration':
            self.duration = self.parse_float(val)
        elif key == 'bit_rate':
            self.bitrate = self.parse_int(val, None)
        elif key == 'width':
            self.video_width = self.parse_int(val)
        elif key == 'height':
            self.video_height = self.parse_int(val)
        elif key == 'channels':
            self.audio_channels = self.parse_int(val)
        elif key == 'sample_rate':
            self.audio_samplerate = self.parse_float(val)
        elif key == 'DISPOSITION:attached_pic':
            self.attached_pic = self.parse_int(val)

        if key.startswith('TAG:'):
            key = key.split('TAG:')[1]
            value = val
            self.metadata[key] = value

        if self.type == 'audio':
            if key == 'avg_frame_rate':
                if '/' in val:
                    n, d = val.split('/')
                    n = self.parse_float(n)
                    d = self.parse_float(d)
                    if n > 0.0 and d > 0.0:
                        self.video_fps = float(n) / float(d)
                elif '.' in val:
                    self.video_fps = self.parse_float(val)

        if self.type == 'video':
            if key == 'r_frame_rate':
                if '/' in val:
                    n, d = val.split('/')
                    n = self.parse_float(n)
                    d = self.parse_float(d)
                    if n > 0.0 and d > 0.0:
                        self.video_fps = float(n) / float(d)
                elif '.' in val:
                    self.video_fps = self.parse_float(val)

        if self.type == 'subtitle':
            if key == 'disposition:forced':
                self.sub_forced = self.parse_int(val)
            if key == 'disposition:default':
                self.sub_default = self.parse_int(val)


    def __repr__(self):
        d = ''
        metadata_str = ['%s=%s' % (key, value) for key, value
                        in self.metadata.items()]
        metadata_str = ', '.join(metadata_str)

        if self.type == 'audio':
            d = 'type=%s, codec=%s, channels=%d, rate=%.0f' % (self.type,
                self.codec, self.audio_channels, self.audio_samplerate)
        elif self.type == 'video':
            d = 'type=%s, codec=%s, width=%d, height=%d, fps=%.1f' % (
                self.type, self.codec, self.video_width, self.video_height,
                self.video_fps)
        elif self.type == 'subtitle':
            d = 'type=%s, codec=%s' % (self.type, self.codec)
        if self.bitrate is not None:
            d += ', bitrate=%d' % self.bitrate

        if self.metadata:
            value = 'MediaStreamInfo(%s, %s)' % (d, metadata_str)
        else:
            value = 'MediaStreamInfo(%s)' % d

        return value


class MediaInfo(object):
    """
    Information about media object, as parsed by ffprobe.
    The attributes are:
      * format - a MediaFormatInfo object
      * streams - a list of MediaStreamInfo objects
    """

    def __init__(self, posters_as_video=True):
        """
        :param posters_as_video: Take poster images (mainly for audio files) as
            A video stream, defaults to True
        """
        self.format = MediaFormatInfo()
        self.posters_as_video = posters_as_video
        self.streams = []

    def parse_ffprobe(self, raw):
        """
        Parse raw ffprobe output.
        """
        in_format = False
        current_stream = None

        for line in raw.split('\n'):
            line = line.strip()
            if line == '':
                continue
            elif line == '[STREAM]':
                current_stream = MediaStreamInfo()
            elif line == '[/STREAM]':
                if current_stream.type:
                    self.streams.append(current_stream)
                current_stream = None
            elif line == '[FORMAT]':
                in_format = True
            elif line == '[/FORMAT]':
                in_format = False
            elif '=' in line:
                k, v = line.split('=', 1)
                k = k.strip()
                v = v.strip()
                if current_stream:
                    current_stream.parse_ffprobe(k, v)
                elif in_format:
                    self.format.parse_ffprobe(k, v)

    def __repr__(self):
        return 'MediaInfo(format=%s, streams=%s)' % (repr(self.format),
                                                     repr(self.streams))

    @property
    def video(self):
        """
        First video stream, or None if there are no video streams.
        """
        for s in self.streams:
            if s.type == 'video' and (self.posters_as_video
                                      or not s.attached_pic):
                return s
        return None

    @property
    def posters(self):
        return [s for s in self.streams if s.attached_pic]

    @property
    def audio(self):
        """
        First audio stream, or None if there are no audio streams.
        """
        for s in self.streams:
            if s.type == 'audio':
                return s
        return None


class FFMpeg(object):
    """
    FFMPeg wrapper object, takes care of calling the ffmpeg binaries,
    passing options and parsing the output.

    >>> f = FFMpeg()
    """
    DEFAULT_JPEG_QUALITY = 4

    def __init__(self, ffmpeg_path=None, ffprobe_path=None):
        """
        Initialize a new FFMpeg wrapper object. Optional parameters specify
        the paths to ffmpeg and ffprobe utilities.
        """

        def which(name):
            path = os.environ.get('PATH', os.defpath)
            for d in path.split(':'):
                fpath = os.path.join(d, name)
                if os.path.exists(fpath) and os.access(fpath, os.X_OK):
                    return fpath
            return None

        if ffmpeg_path is None:
            ffmpeg_path = 'ffmpeg'

        if ffprobe_path is None:
            ffprobe_path = 'ffprobe'

        if '/' not in ffmpeg_path:
            ffmpeg_path = which(ffmpeg_path) or ffmpeg_path
        if '/' not in ffprobe_path:
            ffprobe_path = which(ffprobe_path) or ffprobe_path

        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path

        if not os.path.exists(self.ffmpeg_path):
            raise FFMpegError("ffmpeg binary not found: " + self.ffmpeg_path)

        if not os.path.exists(self.ffprobe_path):
            raise FFMpegError("ffprobe binary not found: " + self.ffprobe_path)

    @staticmethod
    def _spawn(cmds):
        logger.debug('Spawning ffmpeg with command: ' + ' '.join(cmds))
        return Popen(cmds, shell=False, stdin=PIPE, stdout=PIPE, stderr=PIPE,
                     close_fds=True)

    def probe(self, fname, posters_as_video=True):
        """
        Examine the media file and determine its format and media streams.
        Returns the MediaInfo object, or None if the specified file is
        not a valid media file.

        >>> info = FFMpeg().probe('test1.ogg')
        >>> info.format
        'ogg'
        >>> info.duration
        33.00
        >>> info.video.codec
        'theora'
        >>> info.video.width
        720
        >>> info.video.height
        400
        >>> info.audio.codec
        'vorbis'
        >>> info.audio.channels
        2
        :param posters_as_video: Take poster images (mainly for audio files) as
            A video stream, defaults to True
        """

        if not os.path.exists(fname):
            return None

        info = MediaInfo(posters_as_video)

        p = self._spawn([self.ffprobe_path,
                         '-show_format', '-show_streams', fname])
        stdout_data, _ = p.communicate()

        info.parse_ffprobe(stdout_data)

        if not info.format.format and len(info.streams) == 0:
            return None

        return info

    def convert(self, infile, outfile, opts, timeout=10):
        """
        Convert the source media (infile) according to specified options
        (a list of ffmpeg switches as strings) and save it to outfile.

        Convert returns a generator that needs to be iterated to drive the
        conversion process. The generator will periodically yield timecode
        of currently processed part of the file (ie. at which second in the
        content is the conversion process currently).

        The optional timeout argument specifies how long should the operation
        be blocked in case ffmpeg gets stuck and doesn't report back. See
        the documentation in Converter.convert() for more details about this
        option.

        >>> conv = FFMpeg().convert('test.ogg', '/tmp/output.mp3',
        ...    ['-acodec libmp3lame', '-vn'])
        >>> for timecode in conv:
        ...    pass # can be used to inform the user about conversion progress

        """
        if not os.path.exists(infile):
            raise FFMpegError("Input file doesn't exist: " + infile)

        cmds = [self.ffmpeg_path, '-i', infile]
        cmds.extend(opts)
        cmds.extend(['-y', outfile])

        if timeout:
            def on_sigalrm(*_):
                signal.signal(signal.SIGALRM, signal.SIG_DFL)
                raise Exception('timed out while waiting for ffmpeg')

            signal.signal(signal.SIGALRM, on_sigalrm)

        try:
            p = self._spawn(cmds)
        except OSError:
            raise FFMpegError('Error while calling ffmpeg binary')

        yielded = False
        buf = ''
        total_output = ''
        pat = re.compile(r'time=([0-9.:]+) ')
        while True:
            if timeout:
                signal.alarm(timeout)

            ret = p.stderr.read(10)

            if timeout:
                signal.alarm(0)

            if not ret:
                break

            total_output += ret
            buf += ret
            if '\r' in buf:
                line, buf = buf.split('\r', 1)

                tmp = pat.findall(line)
                if len(tmp) == 1:
                    timespec = tmp[0]
                    if ':' in timespec:
                        timecode = 0
                        for part in timespec.split(':'):
                            timecode = 60 * timecode + float(part)
                    else:
                        timecode = float(tmp[0])
                    yielded = True
                    yield timecode

        if timeout:
            signal.signal(signal.SIGALRM, signal.SIG_DFL)

        p.communicate()  # wait for process to exit

        if total_output == '':
            raise FFMpegError('Error while calling ffmpeg binary')

        cmd = ' '.join(cmds)
        if '\n' in total_output:
            line = total_output.split('\n')[-2]

            if line.startswith('Received signal'):
                # Received signal 15: terminating.
                raise FFMpegConvertError(line.split(':')[0], cmd, total_output, pid=p.pid)
            if line.startswith(infile + ': '):
                err = line[len(infile) + 2:]
                raise FFMpegConvertError('Encoding error', cmd, total_output,
                                         err, pid=p.pid)
            if line.startswith('Error while '):
                raise FFMpegConvertError('Encoding error', cmd, total_output,
                                         line, pid=p.pid)
            if not yielded:
                raise FFMpegConvertError('Unknown ffmpeg error', cmd,
                                         total_output, line, pid=p.pid)
        if p.returncode != 0:
            raise FFMpegConvertError('Exited with code %d' % p.returncode, cmd,
                                     total_output, pid=p.pid)

    def thumbnail(self, fname, time, outfile, size=None, quality=DEFAULT_JPEG_QUALITY):
        """
        Create a thumbnal of media file, and store it to outfile
        @param time: time point (in seconds) (float or int)
        @param size: Size, if specified, is WxH of the desired thumbnail.
            If not specified, the video resolution is used.
        @param quality: quality of jpeg file in range 2(best)-31(worst)
            recommended range: 2-6

        >>> FFMpeg().thumbnail('test1.ogg', 5, '/tmp/shot.png', '320x240')
        """
        return self.thumbnails(fname, [(time, outfile, size, quality)])

    def thumbnails(self, fname, option_list):
        """
        Create one or more thumbnails of video.
        @param option_list: a list of tuples like:
            (time, outfile, size=None, quality=DEFAULT_JPEG_QUALITY)
            see documentation of `converter.FFMpeg.thumbnail()` for details.

        >>> FFMpeg().thumbnails('test1.ogg', [(5, '/tmp/shot.png', '320x240'),
        >>>                                   (10, '/tmp/shot2.png', None, 5)])
        """
        if not os.path.exists(fname):
            raise IOError('No such file: ' + fname)

        cmds = [self.ffmpeg_path, '-i', fname, '-y', '-an']
        for thumb in option_list:
            if len(thumb) > 2 and thumb[2]:
                cmds.extend(['-s', str(thumb[2])])

            cmds.extend([
                '-f', 'image2', '-vframes', '1',
                '-ss', str(thumb[0]), thumb[1],
                '-q:v', str(FFMpeg.DEFAULT_JPEG_QUALITY if len(thumb) < 4 else str(thumb[3])),
            ])

        p = self._spawn(cmds)
        _, stderr_data = p.communicate()
        if stderr_data == '':
            raise FFMpegError('Error while calling ffmpeg binary')

        if any(not os.path.exists(option[1]) for option in option_list):
            raise FFMpegError('Error creating thumbnail: %s' % stderr_data)

########NEW FILE########
__FILENAME__ = formats
#!/usr/bin/env python


class BaseFormat(object):
    """
    Base format class.

    Supported formats are: ogg, avi, mkv, webm, flv, mov, mp4, mpeg
    """

    format_name = None
    ffmpeg_format_name = None

    def parse_options(self, opt):
        if 'format' not in opt or opt.get('format') != self.format_name:
            raise ValueError('invalid Format format')
        return ['-f', self.ffmpeg_format_name]


class OggFormat(BaseFormat):
    """
    Ogg container format, mostly used with Vorbis and Theora.
    """
    format_name = 'ogg'
    ffmpeg_format_name = 'ogg'


class AviFormat(BaseFormat):
    """
    Avi container format, often used vith DivX video.
    """
    format_name = 'avi'
    ffmpeg_format_name = 'avi'


class MkvFormat(BaseFormat):
    """
    Matroska format, often used with H.264 video.
    """
    format_name = 'mkv'
    ffmpeg_format_name = 'matroska'


class WebmFormat(BaseFormat):
    """
    WebM is Google's variant of Matroska containing only
    VP8 for video and Vorbis for audio content.
    """
    format_name = 'webm'
    ffmpeg_format_name = 'webm'


class FlvFormat(BaseFormat):
    """
    Flash Video container format.
    """
    format_name = 'flv'
    ffmpeg_format_name = 'flv'


class MovFormat(BaseFormat):
    """
    Mov container format, used mostly with H.264 video
    content, often for mobile platforms.
    """
    format_name = 'mov'
    ffmpeg_format_name = 'mov'


class Mp4Format(BaseFormat):
    """
    Mp4 container format, the default Format for H.264
    video content.
    """
    format_name = 'mp4'
    ffmpeg_format_name = 'mp4'


class MpegFormat(BaseFormat):
    """
    MPEG(TS) container, used mainly for MPEG 1/2 video codecs.
    """
    format_name = 'mpg'
    ffmpeg_format_name = 'mpegts'


class Mp3Format(BaseFormat):
    """
    Mp3 container, used audio-only mp3 files
    """
    format_name = 'mp3'
    ffmpeg_format_name = 'mp3'


format_list = [
    OggFormat, AviFormat, MkvFormat, WebmFormat, FlvFormat,
    MovFormat, Mp4Format, MpegFormat, Mp3Format
]

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Video Converter documentation build configuration file, created by
# sphinx-quickstart on Thu May  5 23:58:13 2011.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))
sys.path.append(os.pardir)

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.doctest']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Video Converter'
copyright = u'2011-2013, Video Converter contributors'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '1.1.0'
# The full version, including alpha/beta/rc tags.
release = '1.1.0'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'VideoConverterdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'VideoConverter.tex', u'Video Converter Documentation',
   u'Dobar Kod', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'videoconverter', u'Video Converter Documentation',
     [u'Dobar Kod'], 1)
]

########NEW FILE########
__FILENAME__ = test
#!/usr/bin/env python

# modify the path so that parent directory is in it
import sys

sys.path.append('../')

import random
import string
import shutil
import unittest
import os
from os.path import join as pjoin

from converter import ffmpeg, formats, avcodecs, Converter, ConverterError


def verify_progress(p):
    if not p:
        return False

    li = list(p)
    if len(li) < 1:
        return False

    prev = 0
    for i in li:
        if type(i) != int or i < 0 or i > 100:
            return False
        if i < prev:
            return False
        prev = i
    return True


class TestFFMpeg(unittest.TestCase):
    def setUp(self):
        current_dir = os.path.abspath(os.path.dirname(__file__))
        temp_name = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(20))

        self.temp_dir = pjoin(current_dir, temp_name)

        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)

        self.video_file_path = pjoin(self.temp_dir, 'output.ogg')
        self.audio_file_path = pjoin(self.temp_dir, 'output.mp3')
        self.shot_file_path = pjoin(self.temp_dir, 'shot.png')
        self.shot2_file_path = pjoin(self.temp_dir, 'shot2.png')
        self.shot3_file_path = pjoin(self.temp_dir, 'shot3.png')

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def assertRaisesSpecific(self, exception, fn, *args, **kwargs):
        try:
            fn(*args, **kwargs)
            raise Exception('Expected exception %s not raised' % repr(exception))
        except exception, ex:
            return ex

    @staticmethod
    def ensure_notexist(f):
        if os.path.exists(f):
            os.unlink(f)

    def test_ffmpeg_probe(self):
        self.assertRaisesSpecific(ffmpeg.FFMpegError, ffmpeg.FFMpeg,
                                  ffmpeg_path='/foo', ffprobe_path='/bar')

        f = ffmpeg.FFMpeg()

        self.assertEqual(None, f.probe('nonexistent'))
        self.assertEqual(None, f.probe('/dev/null'))

        info = f.probe('test1.ogg')
        self.assertEqual('ogg', info.format.format)
        self.assertAlmostEqual(33.00, info.format.duration, places=2)
        self.assertEqual(2, len(info.streams))

        v = info.streams[0]
        self.assertEqual(v, info.video)
        self.assertEqual('video', v.type)
        self.assertEqual('theora', v.codec)
        self.assertEqual(720, v.video_width)
        self.assertEqual(400, v.video_height)
        self.assertEqual(None, v.bitrate)
        self.assertAlmostEqual(25.00, v.video_fps, places=2)
        self.assertEqual(v.metadata['ENCODER'], 'ffmpeg2theora 0.19')

        a = info.streams[1]
        self.assertEqual(a, info.audio)
        self.assertEqual('audio', a.type)
        self.assertEqual('vorbis', a.codec)
        self.assertEqual(2, a.audio_channels)
        self.assertEqual(80000, a.bitrate)
        self.assertEqual(48000, a.audio_samplerate)
        self.assertEqual(a.metadata['ENCODER'], 'ffmpeg2theora 0.19')

        self.assertEqual(repr(info), 'MediaInfo(format='
                                     'MediaFormatInfo(format=ogg, duration=33.00), streams=['
                                     'MediaStreamInfo(type=video, codec=theora, width=720, '
                                     'height=400, fps=25.0, ENCODER=ffmpeg2theora 0.19), '
                                     'MediaStreamInfo(type=audio, codec=vorbis, channels=2, rate=48000, '
                                     'bitrate=80000, ENCODER=ffmpeg2theora 0.19)])')

    def test_ffmpeg_convert(self):
        f = ffmpeg.FFMpeg()

        def consume(fn, *args, **kwargs):
            return list(fn(*args, **kwargs))

        self.assertRaisesSpecific(ffmpeg.FFMpegError, consume,
                                  f.convert, 'nonexistent', self.video_file_path, [])

        self.assertRaisesSpecific(ffmpeg.FFMpegConvertError, consume,
                                  f.convert, '/etc/passwd', self.video_file_path, [])

        info = f.probe('test1.ogg')

        convert_options = [
            '-acodec', 'libvorbis', '-ab', '16k', '-ac', '1', '-ar', '11025',
            '-vcodec', 'libtheora', '-r', '15', '-s', '360x200', '-b', '128k']
        conv = f.convert('test1.ogg', self.video_file_path, convert_options)

        last_tc = 0.0
        for tc in conv:
            assert (last_tc < tc <= info.format.duration + 0.1), (last_tc, tc, info.format.duration)

        self._assert_converted_video_file()

    def _assert_converted_video_file(self):
        """
            Asserts converted test1.ogg (in path self.video_file_path) is converted correctly
        """
        f = ffmpeg.FFMpeg()
        info = f.probe(self.video_file_path)
        self.assertEqual('ogg', info.format.format)
        self.assertAlmostEqual(33.00, info.format.duration, places=0)
        self.assertEqual(2, len(info.streams))

        self.assertEqual('video', info.video.type)
        self.assertEqual('theora', info.video.codec)
        self.assertEqual(360, info.video.video_width)
        self.assertEqual(200, info.video.video_height)
        self.assertAlmostEqual(15.00, info.video.video_fps, places=2)

        self.assertEqual('audio', info.audio.type)
        self.assertEqual('vorbis', info.audio.codec)
        self.assertEqual(1, info.audio.audio_channels)
        self.assertEqual(11025, info.audio.audio_samplerate)

    def test_ffmpeg_termination(self):
        # test when ffmpeg is killed
        f = ffmpeg.FFMpeg()
        convert_options = [
            '-acodec', 'libvorbis', '-ab', '16k', '-ac', '1', '-ar', '11025',
            '-vcodec', 'libtheora', '-r', '15', '-s', '360x200', '-b', '128k']
        p_list = {}  # modifiable object in closure
        f._spawn = lambda *args: p_list.setdefault('', ffmpeg.FFMpeg._spawn(*args))
        conv = f.convert('test1.ogg', self.video_file_path, convert_options)
        conv.next()  # let ffmpeg to start
        p = p_list['']
        p.terminate()
        self.assertRaisesSpecific(ffmpeg.FFMpegConvertError, list, conv)

    def test_ffmpeg_thumbnail(self):
        f = ffmpeg.FFMpeg()
        thumb = self.shot_file_path
        thumb2 = self.shot2_file_path

        self.assertRaisesSpecific(IOError, f.thumbnail, 'nonexistent', 10, thumb)

        self.ensure_notexist(thumb)
        f.thumbnail('test1.ogg', 10, thumb)
        self.assertTrue(os.path.exists(thumb))

        self.ensure_notexist(thumb)
        self.assertRaisesSpecific(ffmpeg.FFMpegError, f.thumbnail, 'test1.ogg', 34, thumb)
        self.assertFalse(os.path.exists(thumb))

        # test multiple thumbnail
        self.ensure_notexist(thumb)
        self.ensure_notexist(thumb2)
        f.thumbnails('test1.ogg', [
            (5, thumb),
            (10, thumb2, None, 5),  # set quality
            (5, self.shot3_file_path, '320x240'),  # set size
        ])
        self.assertTrue(os.path.exists(thumb))
        self.assertTrue(os.path.exists(thumb2))
        self.assertTrue(os.path.exists(self.shot3_file_path))

    def test_formats(self):
        c = formats.BaseFormat()
        self.assertRaisesSpecific(ValueError, c.parse_options, {})
        self.assertEqual(['-f', 'ogg'], formats.OggFormat().parse_options({'format': 'ogg'}))

    def test_avcodecs(self):
        c = avcodecs.BaseCodec()
        self.assertRaisesSpecific(ValueError, c.parse_options, {})

        c.encoder_options = {'foo': int, 'bar': bool}
        self.assertEqual({}, c.safe_options({'baz': 1, 'quux': 1, 'foo': 'w00t'}))
        self.assertEqual({'foo': 42, 'bar': False}, c.safe_options({'foo': '42', 'bar': 0}))

        c = avcodecs.AudioCodec()
        c.codec_name = 'doctest'
        c.ffmpeg_codec_name = 'doctest'

        self.assertEqual(['-acodec', 'doctest'],
                         c.parse_options({'codec': 'doctest', 'channels': 0, 'bitrate': 0, 'samplerate': 0}))

        self.assertEqual(['-acodec', 'doctest', '-ac', '1', '-ab', '64k', '-ar', '44100'],
                         c.parse_options({'codec': 'doctest', 'channels': '1', 'bitrate': '64', 'samplerate': '44100'}))

        c = avcodecs.VideoCodec()
        c.codec_name = 'doctest'
        c.ffmpeg_codec_name = 'doctest'

        self.assertEqual(['-vcodec', 'doctest'],
                         c.parse_options({'codec': 'doctest', 'fps': 0, 'bitrate': 0, 'width': 0, 'height': '480'}))

        self.assertEqual(['-vcodec', 'doctest', '-r', '25', '-vb', '300k', '-s', '320x240', '-aspect', '320:240'],
                         c.parse_options(
                             {'codec': 'doctest', 'fps': '25', 'bitrate': '300', 'width': 320, 'height': 240}))

        self.assertEqual(['-vcodec', 'doctest', '-s', '384x240', '-aspect', '320:240', '-vf', 'crop=320:240:32:0'],
                         c.parse_options({'codec': 'doctest', 'src_width': 640, 'src_height': 400, 'mode': 'crop',
                                          'width': 320, 'height': 240}))

        self.assertEqual(['-vcodec', 'doctest', '-s', '320x240', '-aspect', '320:200', '-vf', 'crop=320:200:0:20'],
                         c.parse_options({'codec': 'doctest', 'src_width': 640, 'src_height': 480, 'mode': 'crop',
                                          'width': 320, 'height': 200}))

        self.assertEqual(['-vcodec', 'doctest', '-s', '320x200', '-aspect', '320:240', '-vf', 'pad=320:240:0:20'],
                         c.parse_options({'codec': 'doctest', 'src_width': 640, 'src_height': 400, 'mode': 'pad',
                                          'width': 320, 'height': 240}))

        self.assertEqual(['-vcodec', 'doctest', '-s', '266x200', '-aspect', '320:200', '-vf', 'pad=320:200:27:0'],
                         c.parse_options({'codec': 'doctest', 'src_width': 640, 'src_height': 480, 'mode': 'pad',
                                          'width': 320, 'height': 200}))

        self.assertEqual(['-vcodec', 'doctest', '-s', '320x240'],
                         c.parse_options({'codec': 'doctest', 'src_width': 640, 'src_height': 480, 'width': 320}))

        self.assertEqual(['-vcodec', 'doctest', '-s', '320x240'],
                         c.parse_options({'codec': 'doctest', 'src_width': 640, 'src_height': 480, 'height': 240}))

    def test_converter(self):
        c = Converter()

        self.assertRaisesSpecific(ConverterError, c.parse_options, None)
        self.assertRaisesSpecific(ConverterError, c.parse_options, {})
        self.assertRaisesSpecific(ConverterError, c.parse_options, {'format': 'foo'})

        self.assertRaisesSpecific(ConverterError, c.parse_options, {'format': 'ogg'})
        self.assertRaisesSpecific(ConverterError, c.parse_options, {'format': 'ogg', 'video': 'whatever'})
        self.assertRaisesSpecific(ConverterError, c.parse_options, {'format': 'ogg', 'audio': {}})
        self.assertRaisesSpecific(ConverterError, c.parse_options,
                                  {'format': 'ogg', 'audio': {'codec': 'bogus'}})

        self.assertEqual(['-an', '-vcodec', 'libtheora', '-r', '25', '-sn', '-f', 'ogg'],
                         c.parse_options({'format': 'ogg', 'video': {'codec': 'theora', 'fps': 25}}))
        self.assertEqual(['-acodec', 'copy', '-vcodec', 'copy', '-sn', '-f', 'ogg'],
                         c.parse_options({'format': 'ogg', 'audio': {'codec': 'copy'}, 'video': {'codec': 'copy'}, 'subtitle': {'codec': None}}))

        info = c.probe('test1.ogg')
        self.assertEqual('theora', info.video.codec)
        self.assertEqual(720, info.video.video_width)
        self.assertEqual(400, info.video.video_height)

        f = self.shot_file_path

        self.ensure_notexist(f)
        c.thumbnail('test1.ogg', 10, f)
        self.assertTrue(os.path.exists(f))
        os.unlink(f)

        conv = c.convert('test1.ogg', self.video_file_path, {
            'format': 'ogg',
            'video': {
                'codec': 'theora', 'width': 160, 'height': 120, 'fps': 15, 'bitrate': 300},
            'audio': {
                'codec': 'vorbis', 'channels': 1, 'bitrate': 32}
        })

        self.assertTrue(verify_progress(conv))

        conv = c.convert('test.aac', self.audio_file_path, {
            'format': 'mp3',
            'audio': {
                'codec': 'mp3', 'channels': 1, 'bitrate': 32}
        })

        self.assertTrue(verify_progress(conv))

    def test_converter_2pass(self):
        c = Converter()
        self.video_file_path = 'xx.ogg'
        options = {
            'format': 'ogg',
            'audio': {'codec': 'vorbis', 'samplerate': 11025, 'channels': 1, 'bitrate': 16},
            'video': {'codec': 'theora', 'bitrate': 128, 'width': 360, 'height': 200, 'fps': 15}
        }
        options_repr = repr(options)
        conv = c.convert('test1.ogg', self.video_file_path, options, twopass=True)

        verify_progress(conv)

        # Convert should not change options dict
        self.assertEquals(options_repr, repr(options))

        self._assert_converted_video_file()

    def test_converter_vp8_codec(self):
        c = Converter()
        conv = c.convert('test1.ogg', self.video_file_path, {
            'format': 'webm',
            'video': {
                'codec': 'vp8', 'width': 160, 'height': 120, 'fps': 15, 'bitrate': 300},
            'audio': {
                'codec': 'vorbis', 'channels': 1, 'bitrate': 32}
        })

        self.assertTrue(verify_progress(conv))

    def test_probe_audio_poster(self):
        c = Converter()

        info = c.probe('test.mp3', posters_as_video=True)
        self.assertNotEqual(None, info.video)
        self.assertEqual(info.video.attached_pic, 1)

        info = c.probe('test.mp3', posters_as_video=False)
        self.assertEqual(None, info.video)
        self.assertEqual(len(info.posters), 1)
        poster = info.posters[0]
        self.assertEqual(poster.type, 'video')
        self.assertEqual(poster.codec, 'png')
        self.assertEqual(poster.video_width, 32)
        self.assertEqual(poster.video_height, 32)
        self.assertEqual(poster.attached_pic, 1)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
