__FILENAME__ = api
from __future__ import unicode_literals

from .exceptions import *
from .tinyjs import *
from .models import Video
from .utils import safe_filename
try:
    from urllib import urlencode
    from urllib2 import urlopen
    from urlparse import urlparse, parse_qs, unquote
except ImportError:
    from urllib.parse import urlencode, urlparse, parse_qs, unquote
    from urllib.request import urlopen

import re, json

YT_BASE_URL = 'http://www.youtube.com/get_video_info'

#YouTube quality and codecs id map.
#source: http://en.wikipedia.org/wiki/YouTube#Quality_and_codecs
YT_ENCODING = {
    #Flash Video
    5: ["flv", "240p", "Sorenson H.263", "N/A", "0.25", "MP3", "64"],
    6: ["flv", "270p", "Sorenson H.263", "N/A", "0.8", "MP3", "64"],
    34: ["flv", "360p", "H.264", "Main", "0.5", "AAC", "128"],
    35: ["flv", "480p", "H.264", "Main", "0.8-1", "AAC", "128"],

    #3GP
    36: ["3gp", "240p", "MPEG-4 Visual", "Simple", "0.17", "AAC", "38"],
    13: ["3gp", "N/A", "MPEG-4 Visual", "N/A", "0.5", "AAC", "N/A"],
    17: ["3gp", "144p", "MPEG-4 Visual", "Simple", "0.05", "AAC", "24"],

    #MPEG-4
    18: ["mp4", "360p", "H.264", "Baseline", "0.5", "AAC", "96"],
    22: ["mp4", "720p", "H.264", "High", "2-2.9", "AAC", "192"],
    37: ["mp4", "1080p", "H.264", "High", "3-4.3", "AAC", "192"],
    38: ["mp4", "3072p", "H.264", "High", "3.5-5", "AAC", "192"],
    82: ["mp4", "360p", "H.264", "3D", "0.5", "AAC", "96"],
    83: ["mp4", "240p", "H.264", "3D", "0.5", "AAC", "96"],
    84: ["mp4", "720p", "H.264", "3D", "2-2.9", "AAC", "152"],
    85: ["mp4", "520p", "H.264", "3D", "2-2.9", "AAC", "152"],

    #WebM
    43: ["webm", "360p", "VP8", "N/A", "0.5", "Vorbis", "128"],
    44: ["webm", "480p", "VP8", "N/A", "1", "Vorbis", "128"],
    45: ["webm", "720p", "VP8", "N/A", "2", "Vorbis", "192"],
    46: ["webm", "1080p", "VP8", "N/A", "N/A", "Vorbis", "192"],
    100: ["webm", "360p", "VP8", "3D", "N/A", "Vorbis", "128"],
    101: ["webm", "360p", "VP8", "3D", "N/A", "Vorbis", "192"],
    102: ["webm", "720p", "VP8", "3D", "N/A", "Vorbis", "192"]
}

# The keys corresponding to the quality/codec map above.
YT_ENCODING_KEYS = (
    'extension', 'resolution', 'video_codec', 'profile', 'video_bitrate',
    'audio_codec', 'audio_bitrate'
)


class YouTube(object):
    _filename = None
    _fmt_values = []
    _video_url = None
    _js_code = False
    _precompiled = False
    title = None
    videos = []
    # fmt was an undocumented URL parameter that allowed selecting
    # YouTube quality mode without using player user interface.

    @property
    def url(self):
        """Exposes the video url."""
        return self._video_url

    @url.setter
    def url(self, url):
        """ Defines the URL of the YouTube video."""
        self._video_url = url
        #Reset the filename.
        self._filename = None
        #Get the video details.
        self._get_video_info()

    @property
    def filename(self):
        """
        Exposes the title of the video. If this is not set, one is
        generated based on the name of the video.
        """
        if not self._filename:
            self._filename = safe_filename(self.title)
        return self._filename

    @filename.setter
    def filename(self, filename):
        """ Defines the filename."""
        self._filename = filename
        if self.videos:
            for video in self.videos:
                video.filename = filename

    @property
    def video_id(self):
        """Gets the video ID extracted from the URL."""
        parts = urlparse(self._video_url)
        qs = getattr(parts, 'query', None)
        if qs:
            video_id = parse_qs(qs).get('v', None)
            if video_id:
                return video_id.pop()

    def get(self, extension=None, resolution=None):
        """
        Return a single video given an extention and resolution.

        Keyword arguments:
        extention -- The desired file extention (e.g.: mp4).
        resolution -- The desired video broadcasting standard.
        """
        result = []
        for v in self.videos:
            if extension and v.extension != extension:
                continue
            elif resolution and v.resolution != resolution:
                continue
            else:
                result.append(v)
        if not len(result):
            return
        elif len(result) is 1:
            return result[0]
        else:
            d = len(result)
            raise MultipleObjectsReturned("get() returned more than one "
                                          "object -- it returned {}!".format(d))

    def filter(self, extension=None, resolution=None):
        """
        Return a filtered list of videos given an extention and
        resolution criteria.

        Keyword arguments:
        extention -- The desired file extention (e.g.: mp4).
        resolution -- The desired video broadcasting standard.
        """
        results = []
        for v in self.videos:
            if extension and v.extension != extension:
                continue
            elif resolution and v.resolution != resolution:
                continue
            else:
                results.append(v)
        return results

    def _fetch(self, path, data):
        """
        Given a path, traverse the response for the desired data. (A
        modified ver. of my dictionary traverse method:
        https://gist.github.com/2009119)

        Keyword arguments:
        path -- A tuple representing a path to a node within a tree.
        data -- The data containing the tree.
        """
        elem = path[0]
        #Get first element in tuple, and check if it contains a list.
        if type(data) is list:
            # Pop it, and let's continue..
            return self._fetch(path, data.pop())
        #Parse the url encoded data
        data = parse_qs(data)
        #Get the element in our path
        data = data.get(elem, None)
        #Offset the tuple by 1.
        path = path[1::1]
        #Check if the path has reached the end OR the element return
        #nothing.
        if len(path) is 0 or data is None:
            if type(data) is list and len(data) is 1:
                data = data.pop()
            return data
        else:
            # Nope, let's keep diggin'
            return self._fetch(path, data)

    def _parse_stream_map(self, text):
        """
        Python's `parse_qs` can't properly decode the stream map
        containing video data so we use this instead.

        Keyword arguments:
        data -- The parsed response from YouTube.
        """
        videoinfo = {
            "itag": [],
            "url": [],
            "quality": [],
            "fallback_host": [],
            "s": [],
            "type": []
        }

        # Split individual videos
        videos = text.split(",")
        # Unquote the characters and split to parameters
        videos = [video.split("&") for video in videos]

        for video in videos:
            for kv in video:
                key, value = kv.split("=")
                videoinfo.get(key, []).append(unquote(value))

        return videoinfo

    def _findBetween(self, s, first, last):
        try:
            start = s.index(first) + len(first)
            end = s.index( last, start )
            return s[start:end]
        except ValueError:
            return ""

    def _get_video_info(self):
        """
        This is responsable for executing the request, extracting the
        necessary details, and populating the different video
        resolutions and formats into a list.
        """
        self.title = None
        self.videos = []

        response = urlopen(self.url)

        if response:
            content = response.read().decode("utf-8")
            try:
                player_conf = content[18 + content.find("ytplayer.config = "):]
                bracket_count = 0
                for i, char in enumerate(player_conf):
                    if char == "{":
                        bracket_count += 1
                    elif char == "}":
                        bracket_count -= 1
                        if bracket_count == 0:
                            break
                else:
                    raise YouTubeError("Cannot get JSON from HTML")
                
                data = json.loads(player_conf[:i+1])
            except Exception as e:
                raise YouTubeError("Cannot decode JSON: {0}".format(e))

            stream_map = self._parse_stream_map(data["args"]["url_encoded_fmt_stream_map"])

            self.title = data["args"]["title"]
            js_url = "http:" + data["assets"]["js"]
            video_urls = stream_map["url"]

            for i, url in enumerate(video_urls):
                try:
                    fmt, fmt_data = self._extract_fmt(url)
                except (TypeError, KeyError):
                    continue
                
                # If the signature must be ciphered...
                if "signature=" not in url:
                    signature = self._cipher(stream_map["s"][i], js_url)
                    url = "%s&signature=%s" % (url, signature)
                
                self.videos.append(Video(url, self.filename, **fmt_data))
                self._fmt_values.append(fmt)
            self.videos.sort()

    def _cipher(self, s, url):
        """
        Get the signature using the cipher implemented in the JavaScript code

        Keyword arguments:
        s -- Signature
        url -- url of JavaScript file
        """

        # Getting JS code (if hasn't downloaded yet)
        if not self._js_code:
            self._js_code = urlopen(url).read().decode() if not self._js_code else self._js_code

        try:
            code = re.findall(r"function \w{2}\(\w{1}\)\{\w{1}=\w{1}\.split\(\"\"\)\;(.*)\}", self._js_code)[0]
            code = code[:code.index("}")]
            
            signature = "a='" + s + "'"

            # Tiny JavaScript VM
            jsvm = JSVM()

            # Precompiling with the super JavaScript VM (if hasn't compiled yet)
            if not self._precompiled:
                self._precompiled = jsvm.compile(code)
            jsvm.setPreinterpreted(jsvm.compile(signature) + self._precompiled)

            # Executing the JS code
            return jsvm.run()["return"]

        except Exception as e:
            raise CipherError("Couldn't cipher the signature. Maybe YouTube has changed the cipher algorithm. Notify this issue on GitHub: %s" % e)

    def _extract_fmt(self, text):
        """
        YouTube does not pass you a completely valid URLencoded form,
        I suspect this is suppose to act as a deterrent.. Nothing some
        regulular expressions couldn't handle.

        Keyword arguments:
        text -- The malformed data contained within each url node.
        """
        itag = re.findall('itag=(\d+)', text)
        if itag and len(itag) is 1:
            itag = int(itag[0])
            attr = YT_ENCODING.get(itag, None)
            if not attr:
                return itag, None
            return itag, dict(zip(YT_ENCODING_KEYS, attr))

########NEW FILE########
__FILENAME__ = exceptions
class MultipleObjectsReturned(Exception):
    """
    The query returned multiple objects when only one was expected.
    """
    pass


class YouTubeError(Exception):
    """
    The REST interface returned an error.
    """
    pass

class CipherError(Exception):
	"""
	The _cipher method returned an error.
	"""
	pass
########NEW FILE########
__FILENAME__ = models
from __future__ import unicode_literals
from os.path import normpath, isfile
from os import remove
try:
    from urllib2 import urlopen
except ImportError:
    from urllib.request import urlopen
from sys import exit


class Video(object):
    """
    Class representation of a single instance of a YouTube video.

    """
    def __init__(self, url, filename, **attributes):
        """
        Define the variables required to declare a new video.

        Keyword arguments:
        extention -- The file extention the video should be saved as.
        resolution -- The broadcasting standard of the video.
        url -- The url of the video. (e.g.: youtube.com/watch?v=..)
        filename -- The filename (minus the extention) to save the video.
        """

        self.url = url
        self.filename = filename
        self.__dict__.update(**attributes)

    def download(self, path=None, chunk_size=8*1024,
                 on_progress=None, on_finish=None):
        """
        Downloads the file of the URL defined within the class
        instance.

        Keyword arguments:
        path -- Destination directory
        chunk_size -- File size (in bytes) to write to buffer at a time
                      (default: 8 bytes).
        on_progress -- A function to be called every time the buffer was
                       written out. Arguments passed are the current and
                       the full size.
        on_finish -- To be called when the download is finished. The full
                     path to the file is passed as an argument.

        """

        path = (normpath(path) + '/' if path else '')
        fullpath = '{0}{1}.{2}'.format(path, self.filename, self.extension)

        # Check for conflicting filenames
        if isfile(fullpath):
            print("\n\nError: Conflicting filename:'{}'.\n\n".format(
                  self.filename))
            exit(1)

        response = urlopen(self.url)
        meta_data = dict(response.info().items())
        file_size = int(meta_data.get("Content-Length") or
                meta_data.get("content-length"))
        self._bytes_received = 0
        try:
            with open(fullpath, 'wb') as dst_file:
                # Print downloading message
                print("\nDownloading: '{0}.{1}' (Bytes: {2})\n\n".format(
                      self.filename, self.extension, file_size))

                while True:
                    self._buffer = response.read(chunk_size)
                    if not self._buffer:
                        if on_finish:
                            on_finish(fullpath)
                        break

                    self._bytes_received += len(self._buffer)
                    dst_file.write(self._buffer)
                    if on_progress:
                        on_progress(self._bytes_received, file_size)

        # Catch possible exceptions occurring during download
        except IOError:
            print("\n\nError: Failed to open file.\n" \
                  "Check that: ('{0}'), is a valid pathname.\n\n" \
                  "Or that ('{1}.{2}') is a valid filename.\n\n".format(
                        path, self.filename, self.extension))
            exit(2)

        except BufferError:
            print("\n\nError: Failed on writing buffer.\n" \
                  "Failed to write video to file.\n\n")
            exit(1)

        except KeyboardInterrupt:
            print("\n\nInterrupt signal given.\nDeleting incomplete video" \
                  "('{0}.{1}').\n\n".format(self.filename, self.extension))
            remove(fullpath)
            exit(1)


    def __repr__(self):
        """A cleaner representation of the class instance."""
        return "<Video: {0} (.{1}) - {2}>".format(self.video_codec, self.extension,
                                           self.resolution)

    def __lt__(self, other):
        if type(other) == Video:
            v1 = "{0} {1}".format(self.extension, self.resolution)
            v2 = "{0} {1}".format(other.extension, other.resolution)
            return (v1 > v2) - (v1 < v2) < 0

########NEW FILE########
__FILENAME__ = tinyjs
import re

class JSVM(object):

    _memory = {}
    _program = []
    _js_methods = {}

    def __init__(self, code=""):
        # TODO: parse automatically the 'swap' method
        # function Bn(a,b){var c=a[0];a[0]=a[b%a.length];a[b]=c;return a};
        def _swap(args): a = list(args[0]); b = int(args[1]); c = a[0]; a[0] = a[b % len(a)]; a[b] = c; return "".join(a)
        def _split(args): return ""
        def _slice(args): return args[0][int(args[1]):]
        def _reverse(args): return args[0][::-1]
        def _join(args): return "".join(args[0])
        def _assign(args): return args[0]
        def _get(args): return self._memory[args[0]]

        self._js_methods = {
            "split": _split,
            "slice": _slice,
            "reverse": _reverse,
            "join": _join,
            "$swap": _swap,
            "$assign": _assign,
            "$get": _get
        }

        if code != "":
            self.compile(code)

    def compile(self, code):
        self._program = []
        regex = re.compile(r"(\w+\.)?(\w+)\(([^)]*)\)")
        code = code.replace("return ", "return=")
        for instruction in code.split(";"):
            #print instruction
            var, method = instruction.split("=")
            m = regex.match(method)
            if m == None:
                arguments = [method[1:-1]]
                method = "$assign"
            else:
                m = m.groups()
                #print m
                arguments = []
                pre_args = [m[0][:-1]] if m[0] != None else []
                pre_args += m[2].split(",")
                for a in pre_args:
                    if a == None or a == "":
                        continue
                    # Replace variables with his value
                    arguments += [JSMethod(self._js_methods["$get"], a) if not a[0] == '"' and not a[0] == '' and not a.isdigit() else a]
                # Suppose that an undefined method is '$swap' method
                method = "$swap" if m[1] not in self._js_methods.keys() else m[1]
            self._program += [(var, JSMethod(self._js_methods[method], arguments))]
        return self._program

    def setPreinterpreted(self, program):
        self._program = program

    def run(self):
        for ins in self._program:
            #print "%s(%s)" % (ins[1]._m.__name__, ins[1]._a)
            if ins[0] not in self._memory:
                self._memory[ins[0]] = None
            self._memory[ins[0]] = ins[1].run()
        return self._memory

class JSMethod(object):

    def __init__(self, method, args):
        self._m = method
        self._a = args

    def run(self):
        args = [arg.run() if isinstance(arg, JSMethod) else arg for arg in self._a]
        return self._m(args)

    def __repr__(self):
        return "%s(%s)" % (self._m.__name__, self._a)
########NEW FILE########
__FILENAME__ = utils
import re


def safe_filename(text, max_length=200):
    """
    Sanitizes filenames for many operating systems.

    Keyword arguments:
    text -- The unsanitized pending filename.
    """
    #Quickly truncates long filenames.
    truncate = lambda text: text[:max_length].rsplit(' ', 0)[0]

    #Tidy up ugly formatted filenames.
    text = text.replace('_', ' ')
    text = text.replace(':', ' -')

    #NTFS forbids filenames containing characters in range 0-31 (0x00-0x1F)
    ntfs = [chr(i) for i in range(0, 31)]

    #Removing these SHOULD make most filename safe for a wide range
    #of operating systems.
    paranoid = ['\"', '\#', '\$', '\%', '\'', '\*', '\,', '\.', '\/', '\:',
                '\;', '\<', '\>', '\?', '\\', '\^', '\|', '\~', '\\\\']

    blacklist = re.compile('|'.join(ntfs + paranoid), re.UNICODE)
    filename = blacklist.sub('', text)
    return truncate(filename)


def print_status(progress, file_size):
    """
    This function - when passed as `on_progress` to `Video.download` - prints
    out the current download progress.

    Arguments:
    progress -- The lenght of the currently downloaded bytes.
    file_size -- The total size of the video.
    """

    percent = progress * 100. / file_size
    status = r"{0:10d}  [{1:3.2f}%]".format(progress, percent)
    status = status + chr(8) * (len(status) + 1)
    print(status,)

########NEW FILE########
