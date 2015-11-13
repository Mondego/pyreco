__FILENAME__ = dragonplayer

########NEW FILE########
__FILENAME__ = gnome_mplayer

########NEW FILE########
__FILENAME__ = mplayer

########NEW FILE########
__FILENAME__ = vlc
#!/usr/bin/env python

########NEW FILE########
__FILENAME__ = wmp

########NEW FILE########
__FILENAME__ = __main__
#!/usr/bin/env python

def main():
    script_main('you-get', any_download, any_download_playlist)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = ffmpeg

########NEW FILE########
__FILENAME__ = libav

########NEW FILE########
__FILENAME__ = mencoder

########NEW FILE########
__FILENAME__ = common
#!/usr/bin/env python

import getopt
import json
import locale
import os
import re
import sys
from urllib import request, parse
import platform
import threading

from .version import __version__
from .util import log, sogou_proxy_server, get_filename, unescape_html

dry_run = False
force = False
player = None
sogou_proxy = None
sogou_env = None
cookies_txt = None

fake_headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Charset': 'UTF-8,*;q=0.5',
    'Accept-Encoding': 'gzip,deflate,sdch',
    'Accept-Language': 'en-US,en;q=0.8',
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:13.0) Gecko/20100101 Firefox/13.0'
}

if sys.stdout.isatty():
    default_encoding = sys.stdout.encoding.lower()
else:
    default_encoding = locale.getpreferredencoding().lower()

def tr(s):
    try:
        s.encode(default_encoding)
        return s
    except:
        return str(s.encode('utf-8'))[2:-1]

# DEPRECATED in favor of match1()
def r1(pattern, text):
    m = re.search(pattern, text)
    if m:
        return m.group(1)

# DEPRECATED in favor of match1()
def r1_of(patterns, text):
    for p in patterns:
        x = r1(p, text)
        if x:
            return x

def match1(text, *patterns):
    """Scans through a string for substrings matched some patterns (first-subgroups only).

    Args:
        text: A string to be scanned.
        patterns: Arbitrary number of regex patterns.

    Returns:
        When only one pattern is given, returns a string (None if no match found).
        When more than one pattern are given, returns a list of strings ([] if no match found).
    """

    if len(patterns) == 1:
        pattern = patterns[0]
        match = re.search(pattern, text)
        if match:
            return match.group(1)
        else:
            return None
    else:
        ret = []
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                ret.append(match.group(1))
        return ret

def launch_player(player, urls):
    import subprocess
    import shlex
    subprocess.call(shlex.split(player) + list(urls))

def parse_query_param(url, param):
    """Parses the query string of a URL and returns the value of a parameter.

    Args:
        url: A URL.
        param: A string representing the name of the parameter.

    Returns:
        The value of the parameter.
    """

    try:
        return parse.parse_qs(parse.urlparse(url).query)[param][0]
    except:
        return None

def unicodize(text):
    return re.sub(r'\\u([0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f])', lambda x: chr(int(x.group(0)[2:], 16)), text)

# DEPRECATED in favor of util.legitimize()
def escape_file_path(path):
    path = path.replace('/', '-')
    path = path.replace('\\', '-')
    path = path.replace('*', '-')
    path = path.replace('?', '-')
    return path

# DEPRECATED in favor of util.legitimize()
def filenameable(text):
    """Converts a string to a legal filename through various OSes.
    """
    # All POSIX systems
    text = text.translate({
        0: None,
        ord('/'): '-',
    })
    if platform.system() == 'Windows': # For Windows
        text = text.translate({
            ord(':'): '-',
            ord('*'): '-',
            ord('?'): '-',
            ord('\\'): '-',
            ord('\"'): '\'',
            ord('<'): '-',
            ord('>'): '-',
            ord('|'): '-',
            ord('+'): '-',
            ord('['): '(',
            ord(']'): ')',
        })
    else:
        if text.startswith("."):
            text = text[1:]
        if platform.system() == 'Darwin': # For Mac OS
            text = text.translate({
                ord(':'): '-',
            })
    return text

def ungzip(data):
    """Decompresses data for Content-Encoding: gzip.
    """
    from io import BytesIO
    import gzip
    buffer = BytesIO(data)
    f = gzip.GzipFile(fileobj=buffer)
    return f.read()

def undeflate(data):
    """Decompresses data for Content-Encoding: deflate.
    (the zlib compression is used.)
    """
    import zlib
    decompressobj = zlib.decompressobj(-zlib.MAX_WBITS)
    return decompressobj.decompress(data)+decompressobj.flush()

# DEPRECATED in favor of get_content()
def get_response(url, faker = False):
    if faker:
        response = request.urlopen(request.Request(url, headers = fake_headers), None)
    else:
        response = request.urlopen(url)

    data = response.read()
    if response.info().get('Content-Encoding') == 'gzip':
        data = ungzip(data)
    elif response.info().get('Content-Encoding') == 'deflate':
        data = undeflate(data)
    response.data = data
    return response

# DEPRECATED in favor of get_content()
def get_html(url, encoding = None, faker = False):
    content = get_response(url, faker).data
    return str(content, 'utf-8', 'ignore')

# DEPRECATED in favor of get_content()
def get_decoded_html(url, faker = False):
    response = get_response(url, faker)
    data = response.data
    charset = r1(r'charset=([\w-]+)', response.headers['content-type'])
    if charset:
        return data.decode(charset, 'ignore')
    else:
        return data

def get_content(url, headers={}, decoded=True):
    """Gets the content of a URL via sending a HTTP GET request.

    Args:
        url: A URL.
        headers: Request headers used by the client.
        decoded: Whether decode the response body using UTF-8 or the charset specified in Content-Type.

    Returns:
        The content as a string.
    """

    req = request.Request(url, headers=headers)
    if cookies_txt:
        cookies_txt.add_cookie_header(req)
        req.headers.update(req.unredirected_hdrs)
    response = request.urlopen(req)
    data = response.read()

    # Handle HTTP compression for gzip and deflate (zlib)
    content_encoding = response.getheader('Content-Encoding')
    if content_encoding == 'gzip':
        data = ungzip(data)
    elif content_encoding == 'deflate':
        data = undeflate(data)

    # Decode the response body
    if decoded:
        charset = match1(response.getheader('Content-Type'), r'charset=([\w-]+)')
        if charset is not None:
            data = data.decode(charset)
        else:
            data = data.decode('utf-8')

    return data

def url_size(url, faker = False):
    if faker:
        response = request.urlopen(request.Request(url, headers = fake_headers), None)
    else:
        response = request.urlopen(url)

    size = int(response.headers['content-length'])
    return size

def urls_size(urls):
    return sum(map(url_size, urls))

def url_info(url, faker = False):
    if faker:
        response = request.urlopen(request.Request(url, headers = fake_headers), None)
    else:
        response = request.urlopen(request.Request(url))

    headers = response.headers

    type = headers['content-type']
    mapping = {
        'video/3gpp': '3gp',
        'video/f4v': 'flv',
        'video/mp4': 'mp4',
        'video/MP2T': 'ts',
        'video/quicktime': 'mov',
        'video/webm': 'webm',
        'video/x-flv': 'flv',
        'video/x-ms-asf': 'asf',
        'audio/mpeg': 'mp3'
    }
    if type in mapping:
        ext = mapping[type]
    else:
        type = None
        if headers['content-disposition']:
            try:
                filename = parse.unquote(r1(r'filename="?([^"]+)"?', headers['content-disposition']))
                if len(filename.split('.')) > 1:
                    ext = filename.split('.')[-1]
                else:
                    ext = None
            except:
                ext = None
        else:
            ext = None

    if headers['transfer-encoding'] != 'chunked':
        size = int(headers['content-length'])
    else:
        size = None

    return type, ext, size

def url_locations(urls, faker = False):
    locations = []
    for url in urls:
        if faker:
            response = request.urlopen(request.Request(url, headers = fake_headers), None)
        else:
            response = request.urlopen(request.Request(url))

        locations.append(response.url)
    return locations

def url_save(url, filepath, bar, refer = None, is_part = False, faker = False):
    file_size = url_size(url, faker = faker)

    if os.path.exists(filepath):
        if not force and file_size == os.path.getsize(filepath):
            if not is_part:
                if bar:
                    bar.done()
                print('Skipping %s: file already exists' % tr(os.path.basename(filepath)))
            else:
                if bar:
                    bar.update_received(file_size)
            return
        else:
            if not is_part:
                if bar:
                    bar.done()
                print('Overwriting %s' % tr(os.path.basename(filepath)), '...')
    elif not os.path.exists(os.path.dirname(filepath)):
        os.mkdir(os.path.dirname(filepath))

    temp_filepath = filepath + '.download'
    received = 0
    if not force:
        open_mode = 'ab'

        if os.path.exists(temp_filepath):
            received += os.path.getsize(temp_filepath)
            if bar:
                bar.update_received(os.path.getsize(temp_filepath))
    else:
        open_mode = 'wb'

    if received < file_size:
        if faker:
            headers = fake_headers
        else:
            headers = {}
        if received:
            headers['Range'] = 'bytes=' + str(received) + '-'
        if refer:
            headers['Referer'] = refer

        response = request.urlopen(request.Request(url, headers = headers), None)
        try:
            range_start = int(response.headers['content-range'][6:].split('/')[0].split('-')[0])
            end_length = end = int(response.headers['content-range'][6:].split('/')[1])
            range_length = end_length - range_start
        except:
            range_length = int(response.headers['content-length'])

        if file_size != received + range_length:
            received = 0
            if bar:
                bar.received = 0
            open_mode = 'wb'

        with open(temp_filepath, open_mode) as output:
            while True:
                buffer = response.read(1024 * 256)
                if not buffer:
                    if received == file_size: # Download finished
                        break
                    else: # Unexpected termination. Retry request
                        headers['Range'] = 'bytes=' + str(received) + '-'
                        response = request.urlopen(request.Request(url, headers = headers), None)
                output.write(buffer)
                received += len(buffer)
                if bar:
                    bar.update_received(len(buffer))

    assert received == os.path.getsize(temp_filepath), '%s == %s == %s' % (received, os.path.getsize(temp_filepath), temp_filepath)

    if os.access(filepath, os.W_OK):
        os.remove(filepath) # on Windows rename could fail if destination filepath exists
    os.rename(temp_filepath, filepath)

def url_save_chunked(url, filepath, bar, refer = None, is_part = False, faker = False):
    if os.path.exists(filepath):
        if not force:
            if not is_part:
                if bar:
                    bar.done()
                print('Skipping %s: file already exists' % tr(os.path.basename(filepath)))
            else:
                if bar:
                    bar.update_received(os.path.getsize(filepath))
            return
        else:
            if not is_part:
                if bar:
                    bar.done()
                print('Overwriting %s' % tr(os.path.basename(filepath)), '...')
    elif not os.path.exists(os.path.dirname(filepath)):
        os.mkdir(os.path.dirname(filepath))

    temp_filepath = filepath + '.download'
    received = 0
    if not force:
        open_mode = 'ab'

        if os.path.exists(temp_filepath):
            received += os.path.getsize(temp_filepath)
            if bar:
                bar.update_received(os.path.getsize(temp_filepath))
    else:
        open_mode = 'wb'

    if faker:
        headers = fake_headers
    else:
        headers = {}
    if received:
        headers['Range'] = 'bytes=' + str(received) + '-'
    if refer:
        headers['Referer'] = refer

    response = request.urlopen(request.Request(url, headers = headers), None)

    with open(temp_filepath, open_mode) as output:
        while True:
            buffer = response.read(1024 * 256)
            if not buffer:
                break
            output.write(buffer)
            received += len(buffer)
            if bar:
                bar.update_received(len(buffer))

    assert received == os.path.getsize(temp_filepath), '%s == %s == %s' % (received, os.path.getsize(temp_filepath))

    if os.access(filepath, os.W_OK):
        os.remove(filepath) # on Windows rename could fail if destination filepath exists
    os.rename(temp_filepath, filepath)

class SimpleProgressBar:
    def __init__(self, total_size, total_pieces = 1):
        self.displayed = False
        self.total_size = total_size
        self.total_pieces = total_pieces
        self.current_piece = 1
        self.received = 0

    def update(self):
        self.displayed = True
        bar_size = 40
        percent = round(self.received * 100 / self.total_size, 1)
        if percent > 100:
            percent = 100
        dots = bar_size * int(percent) // 100
        plus = int(percent) - dots // bar_size * 100
        if plus > 0.8:
            plus = '='
        elif plus > 0.4:
            plus = '>'
        else:
            plus = ''
        bar = '=' * dots + plus
        bar = '{0:>5}% ({1:>5}/{2:<5}MB) [{3:<40}] {4}/{5}'.format(percent, round(self.received / 1048576, 1), round(self.total_size / 1048576, 1), bar, self.current_piece, self.total_pieces)
        sys.stdout.write('\r' + bar)
        sys.stdout.flush()

    def update_received(self, n):
        self.received += n
        self.update()

    def update_piece(self, n):
        self.current_piece = n

    def done(self):
        if self.displayed:
            print()
            self.displayed = False

class PiecesProgressBar:
    def __init__(self, total_size, total_pieces = 1):
        self.displayed = False
        self.total_size = total_size
        self.total_pieces = total_pieces
        self.current_piece = 1
        self.received = 0

    def update(self):
        self.displayed = True
        bar = '{0:>5}%[{1:<40}] {2}/{3}'.format('?', '?' * 40, self.current_piece, self.total_pieces)
        sys.stdout.write('\r' + bar)
        sys.stdout.flush()

    def update_received(self, n):
        self.received += n
        self.update()

    def update_piece(self, n):
        self.current_piece = n

    def done(self):
        if self.displayed:
            print()
            self.displayed = False

class DummyProgressBar:
    def __init__(self, *args):
        pass
    def update_received(self, n):
        pass
    def update_piece(self, n):
        pass
    def done(self):
        pass

def download_urls(urls, title, ext, total_size, output_dir='.', refer=None, merge=True, faker=False):
    assert urls
    if dry_run:
        print('Real URLs:\n%s\n' % urls)
        return

    if player:
        launch_player(player, urls)
        return

    if not total_size:
        try:
            total_size = urls_size(urls)
        except:
            import traceback
            import sys
            traceback.print_exc(file = sys.stdout)
            pass

    title = get_filename(title)

    filename = '%s.%s' % (title, ext)
    filepath = os.path.join(output_dir, filename)
    if total_size:
        if not force and os.path.exists(filepath) and os.path.getsize(filepath) >= total_size * 0.9:
            print('Skipping %s: file already exists' % tr(filepath))
            print()
            return
        bar = SimpleProgressBar(total_size, len(urls))
    else:
        bar = PiecesProgressBar(total_size, len(urls))

    if len(urls) == 1:
        url = urls[0]
        print('Downloading %s ...' % tr(filename))
        url_save(url, filepath, bar, refer = refer, faker = faker)
        bar.done()
    else:
        parts = []
        print('Downloading %s.%s ...' % (tr(title), ext))
        for i, url in enumerate(urls):
            filename = '%s[%02d].%s' % (title, i, ext)
            filepath = os.path.join(output_dir, filename)
            parts.append(filepath)
            #print 'Downloading %s [%s/%s]...' % (tr(filename), i + 1, len(urls))
            bar.update_piece(i + 1)
            url_save(url, filepath, bar, refer = refer, is_part = True, faker = faker)
        bar.done()

        if not merge:
            print()
            return
        if ext == 'flv':
            try:
                from .processor.ffmpeg import has_ffmpeg_installed
                if has_ffmpeg_installed():
                    from .processor.ffmpeg import ffmpeg_concat_flv_to_mp4
                    ffmpeg_concat_flv_to_mp4(parts, os.path.join(output_dir, title + '.mp4'))
                else:
                    from .processor.join_flv import concat_flv
                    concat_flv(parts, os.path.join(output_dir, title + '.flv'))
            except:
                raise
            else:
                for part in parts:
                    os.remove(part)

        elif ext == 'mp4':
            try:
                from .processor.ffmpeg import has_ffmpeg_installed
                if has_ffmpeg_installed():
                    from .processor.ffmpeg import ffmpeg_concat_mp4_to_mp4
                    ffmpeg_concat_mp4_to_mp4(parts, os.path.join(output_dir, title + '.mp4'))
                else:
                    from .processor.join_mp4 import concat_mp4
                    concat_mp4(parts, os.path.join(output_dir, title + '.mp4'))
            except:
                raise
            else:
                for part in parts:
                    os.remove(part)

        else:
            print("Can't merge %s files" % ext)

    print()

def download_urls_chunked(urls, title, ext, total_size, output_dir='.', refer=None, merge=True, faker=False):
    assert urls
    if dry_run:
        print('Real URLs:\n%s\n' % urls)
        return

    if player:
        launch_player(player, urls)
        return

    assert ext in ('ts')

    title = get_filename(title)

    filename = '%s.%s' % (title, 'ts')
    filepath = os.path.join(output_dir, filename)
    if total_size:
        if not force and os.path.exists(filepath[:-3] + '.mkv'):
            print('Skipping %s: file already exists' % tr(filepath[:-3] + '.mkv'))
            print()
            return
        bar = SimpleProgressBar(total_size, len(urls))
    else:
        bar = PiecesProgressBar(total_size, len(urls))

    if len(urls) == 1:
        parts = []
        url = urls[0]
        print('Downloading %s ...' % tr(filename))
        filepath = os.path.join(output_dir, filename)
        parts.append(filepath)
        url_save_chunked(url, filepath, bar, refer = refer, faker = faker)
        bar.done()

        if not merge:
            print()
            return
        if ext == 'ts':
            from .processor.ffmpeg import has_ffmpeg_installed
            if has_ffmpeg_installed():
                from .processor.ffmpeg import ffmpeg_convert_ts_to_mkv
                if ffmpeg_convert_ts_to_mkv(parts, os.path.join(output_dir, title + '.mkv')):
                    for part in parts:
                        os.remove(part)
                else:
                    os.remove(os.path.join(output_dir, title + '.mkv'))
            else:
                print('No ffmpeg is found. Conversion aborted.')
        else:
            print("Can't convert %s files" % ext)
    else:
        parts = []
        print('Downloading %s.%s ...' % (tr(title), ext))
        for i, url in enumerate(urls):
            filename = '%s[%02d].%s' % (title, i, ext)
            filepath = os.path.join(output_dir, filename)
            parts.append(filepath)
            #print 'Downloading %s [%s/%s]...' % (tr(filename), i + 1, len(urls))
            bar.update_piece(i + 1)
            url_save_chunked(url, filepath, bar, refer = refer, is_part = True, faker = faker)
        bar.done()

        if not merge:
            print()
            return
        if ext == 'ts':
            from .processor.ffmpeg import has_ffmpeg_installed
            if has_ffmpeg_installed():
                from .processor.ffmpeg import ffmpeg_concat_ts_to_mkv
                if ffmpeg_concat_ts_to_mkv(parts, os.path.join(output_dir, title + '.mkv')):
                    for part in parts:
                        os.remove(part)
                else:
                    os.remove(os.path.join(output_dir, title + '.mkv'))
            else:
                print('No ffmpeg is found. Merging aborted.')
        else:
            print("Can't merge %s files" % ext)

    print()

def download_rtmp_url(url, playpath, title, ext, total_size=0, output_dir='.', refer=None, merge=True, faker=False):
    assert url
    if dry_run:
        print('Real URL:\n%s\n' % [url])
        print('Real Playpath:\n%s\n' % [playpath])
        return

    if player:
        from .processor.rtmpdump import play_rtmpdump_stream
        play_rtmpdump_stream(player, url, playpath)
        return

    from .processor.rtmpdump import has_rtmpdump_installed, download_rtmpdump_stream
    assert has_rtmpdump_installed(), "RTMPDump not installed."
    download_rtmpdump_stream(url, playpath, title, ext, output_dir)

def playlist_not_supported(name):
    def f(*args, **kwargs):
        raise NotImplementedError('Playlist is not supported for ' + name)
    return f

def print_info(site_info, title, type, size):
    if type:
        type = type.lower()
    if type in ['3gp']:
        type = 'video/3gpp'
    elif type in ['asf', 'wmv']:
        type = 'video/x-ms-asf'
    elif type in ['flv', 'f4v']:
        type = 'video/x-flv'
    elif type in ['mkv']:
        type = 'video/x-matroska'
    elif type in ['mp3']:
        type = 'audio/mpeg'
    elif type in ['mp4']:
        type = 'video/mp4'
    elif type in ['mov']:
        type = 'video/quicktime'
    elif type in ['ts']:
        type = 'video/MP2T'
    elif type in ['webm']:
        type = 'video/webm'

    if type in ['video/3gpp']:
        type_info = "3GPP multimedia file (%s)" % type
    elif type in ['video/x-flv', 'video/f4v']:
        type_info = "Flash video (%s)" % type
    elif type in ['video/mp4', 'video/x-m4v']:
        type_info = "MPEG-4 video (%s)" % type
    elif type in ['video/MP2T']:
        type_info = "MPEG-2 transport stream (%s)" % type
    elif type in ['video/webm']:
        type_info = "WebM video (%s)" % type
    #elif type in ['video/ogg']:
    #    type_info = "Ogg video (%s)" % type
    elif type in ['video/quicktime']:
        type_info = "QuickTime video (%s)" % type
    elif type in ['video/x-matroska']:
        type_info = "Matroska video (%s)" % type
    #elif type in ['video/x-ms-wmv']:
    #    type_info = "Windows Media video (%s)" % type
    elif type in ['video/x-ms-asf']:
        type_info = "Advanced Systems Format (%s)" % type
    #elif type in ['video/mpeg']:
    #    type_info = "MPEG video (%s)" % type
    elif type in ['audio/mpeg']:
        type_info = "MP3 (%s)" % type
    else:
        type_info = "Unknown type (%s)" % type

    print("Video Site:", site_info)
    print("Title:     ", unescape_html(tr(title)))
    print("Type:      ", type_info)
    print("Size:      ", round(size / 1048576, 2), "MiB (" + str(size) + " Bytes)")
    print()

def parse_host(host):
    """Parses host name and port number from a string.
    """
    if re.match(r'^(\d+)$', host) is not None:
        return ("0.0.0.0", int(host))
    if re.match(r'^(\w+)://', host) is None:
        host = "//" + host
    o = parse.urlparse(host)
    hostname = o.hostname or "0.0.0.0"
    port = o.port or 0
    return (hostname, port)

def get_sogou_proxy():
    return sogou_proxy

def set_proxy(proxy):
    proxy_handler = request.ProxyHandler({
        'http': '%s:%s' % proxy,
        'https': '%s:%s' % proxy,
    })
    opener = request.build_opener(proxy_handler)
    request.install_opener(opener)

def unset_proxy():
    proxy_handler = request.ProxyHandler({})
    opener = request.build_opener(proxy_handler)
    request.install_opener(opener)

# DEPRECATED in favor of set_proxy() and unset_proxy()
def set_http_proxy(proxy):
    if proxy == None: # Use system default setting
        proxy_support = request.ProxyHandler()
    elif proxy == '': # Don't use any proxy
        proxy_support = request.ProxyHandler({})
    else: # Use proxy
        proxy_support = request.ProxyHandler({'http': '%s' % proxy, 'https': '%s' % proxy})
    opener = request.build_opener(proxy_support)
    request.install_opener(opener)

def download_main(download, download_playlist, urls, playlist, output_dir, merge, info_only):
    for url in urls:
        if url.startswith('https://'):
            url = url[8:]
        if not url.startswith('http://'):
            url = 'http://' + url

        if playlist:
            download_playlist(url, output_dir = output_dir, merge = merge, info_only = info_only)
        else:
            download(url, output_dir = output_dir, merge = merge, info_only = info_only)

def get_version():
    try:
        import subprocess
        real_dir = os.path.dirname(os.path.realpath(__file__))
        git_hash = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], cwd=real_dir, stderr=subprocess.DEVNULL).decode('utf-8').strip()
        assert git_hash
        return '%s-%s' % (__version__, git_hash)
    except:
        return __version__

def script_main(script_name, download, download_playlist = None):
    version = 'You-Get %s, a video downloader.' % get_version()
    help = 'Usage: %s [OPTION]... [URL]...\n' % script_name
    help += '''\nStartup options:
    -V | --version                           Display the version and exit.
    -h | --help                              Print this help and exit.
    '''
    help += '''\nDownload options (use with URLs):
    -f | --force                             Force overwriting existed files.
    -i | --info                              Display the information of videos without downloading.
    -u | --url                               Display the real URLs of videos without downloading.
    -c | --cookies                           Load NetScape's cookies.txt file.
    -n | --no-merge                          Don't merge video parts.
    -o | --output-dir <PATH>                 Set the output directory for downloaded videos.
    -p | --player <PLAYER [options]>         Directly play the video with PLAYER like vlc/smplayer.
    -x | --http-proxy <HOST:PORT>            Use specific HTTP proxy for downloading.
         --no-proxy                          Don't use any proxy. (ignore $http_proxy)
    -S | --sogou                             Use a Sogou proxy server for downloading.
         --sogou-proxy <HOST:PORT>           Run a standalone Sogou proxy server.
         --debug                             Show traceback on KeyboardInterrupt.
    '''

    short_opts = 'Vhfiuc:nSo:p:x:'
    opts = ['version', 'help', 'force', 'info', 'url', 'cookies', 'no-merge', 'no-proxy', 'debug', 'sogou', 'output-dir=', 'player=', 'http-proxy=', 'sogou-proxy=', 'sogou-env=']
    if download_playlist:
        short_opts = 'l' + short_opts
        opts = ['playlist'] + opts

    try:
        opts, args = getopt.getopt(sys.argv[1:], short_opts, opts)
    except getopt.GetoptError as err:
        log.e(err)
        log.e("try 'you-get --help' for more options")
        sys.exit(2)

    global force
    global dry_run
    global player
    global sogou_proxy
    global sogou_env
    global cookies_txt
    cookies_txt = None

    info_only = False
    playlist = False
    merge = True
    output_dir = '.'
    proxy = None
    traceback = False
    for o, a in opts:
        if o in ('-V', '--version'):
            print(version)
            sys.exit()
        elif o in ('-h', '--help'):
            print(version)
            print(help)
            sys.exit()
        elif o in ('-f', '--force'):
            force = True
        elif o in ('-i', '--info'):
            info_only = True
        elif o in ('-u', '--url'):
            dry_run = True
        elif o in ('-c', '--cookies'):
            from http import cookiejar
            cookies_txt = cookiejar.MozillaCookieJar(a)
            cookies_txt.load()
        elif o in ('-l', '--playlist'):
            playlist = True
        elif o in ('-n', '--no-merge'):
            merge = False
        elif o in ('--no-proxy',):
            proxy = ''
        elif o in ('--debug',):
            traceback = True
        elif o in ('-o', '--output-dir'):
            output_dir = a
        elif o in ('-p', '--player'):
            player = a
        elif o in ('-x', '--http-proxy'):
            proxy = a
        elif o in ('-S', '--sogou'):
            sogou_proxy = ("0.0.0.0", 0)
        elif o in ('--sogou-proxy',):
            sogou_proxy = parse_host(a)
        elif o in ('--sogou-env',):
            sogou_env = a
        else:
            log.e("try 'you-get --help' for more options")
            sys.exit(2)
    if not args:
        if sogou_proxy is not None:
            try:
                if sogou_env is not None:
                    server = sogou_proxy_server(sogou_proxy, network_env=sogou_env)
                else:
                    server = sogou_proxy_server(sogou_proxy)
                server.serve_forever()
            except KeyboardInterrupt:
                if traceback:
                    raise
                else:
                    sys.exit()
        else:
            print(help)
            sys.exit()

    set_http_proxy(proxy)

    try:
        download_main(download, download_playlist, args, playlist, output_dir, merge, info_only)
    except KeyboardInterrupt:
        if traceback:
            raise
        else:
            sys.exit(1)

########NEW FILE########
__FILENAME__ = acfun
#!/usr/bin/env python

__all__ = ['acfun_download']

from ..common import *

from .qq import qq_download_by_id
from .sina import sina_download_by_vid
from .tudou import tudou_download_by_iid
from .youku import youku_download_by_id

import json, re

def get_srt_json(id):
    url = 'http://comment.acfun.com/%s.json' % id
    return get_html(url)

def get_srt_lock_json(id):
    url = 'http://comment.acfun.com/%s_lock.json' % id
    return get_html(url)

def acfun_download_by_vid(vid, title=None, output_dir='.', merge=True, info_only=False):
    info = json.loads(get_html('http://www.acfun.com/video/getVideo.aspx?id=' + vid))
    sourceType = info['sourceType']
    sourceId = info['sourceId']
    danmakuId = info['danmakuId']
    if sourceType == 'sina':
        sina_download_by_vid(sourceId, title, output_dir=output_dir, merge=merge, info_only=info_only)
    elif sourceType == 'youku':
        youku_download_by_id(sourceId, title, output_dir=output_dir, merge=merge, info_only=info_only)
    elif sourceType == 'tudou':
        tudou_download_by_iid(sourceId, title, output_dir=output_dir, merge=merge, info_only=info_only)
    elif sourceType == 'qq':
        qq_download_by_id(sourceId, title, output_dir=output_dir, merge=merge, info_only=info_only)
    else:
        raise NotImplementedError(sourceType)

    if not info_only:
        title = get_filename(title)
        try:
            print('Downloading %s ...\n' % (title + '.cmt.json'))
            cmt = get_srt_json(danmakuId)
            with open(os.path.join(output_dir, title + '.cmt.json'), 'w') as x:
                x.write(cmt)
            print('Downloading %s ...\n' % (title + '.cmt_lock.json'))
            cmt = get_srt_lock_json(danmakuId)
            with open(os.path.join(output_dir, title + '.cmt_lock.json'), 'w') as x:
                x.write(cmt)
        except:
            pass

def acfun_download(url, output_dir = '.', merge = True, info_only = False):
    assert re.match(r'http://[^\.]+.acfun.[^\.]+/v/ac(\d+)', url)
    html = get_html(url)

    title = r1(r'<h1 id="txt-title-view">([^<>]+)<', html)
    title = unescape_html(title)
    title = escape_file_path(title)
    assert title

    videos = re.findall("data-vid=\"(\d+)\" href=\"[^\"]+\" title=\"([^\"]+)\"", html)
    if videos is not None:
        for video in videos:
            p_vid = video[0]
            p_title = title + " - " + video[1]
            acfun_download_by_vid(p_vid, p_title, output_dir=output_dir, merge=merge, info_only=info_only)
    else:
        # Useless - to be removed?
        id = r1(r"src=\"/newflvplayer/player.*id=(\d+)", html)
        sina_download_by_vid(id, title, output_dir=output_dir, merge=merge, info_only=info_only)

site_info = "AcFun.com"
download = acfun_download
download_playlist = playlist_not_supported('acfun')

########NEW FILE########
__FILENAME__ = alive
#!/usr/bin/env python

__all__ = ['alive_download']

from ..common import *

def alive_download(url, output_dir = '.', merge = True, info_only = False):
    html = get_html(url)
    
    title = r1(r'<meta property="og:title" content="([^"]+)"', html)
    
    url = r1(r'file: "(http://alive[^"]+)"', html)
    type, ext, size = url_info(url)
    
    print_info(site_info, title, type, size)
    if not info_only:
        download_urls([url], title, ext, size, output_dir, merge = merge)

site_info = "Alive.in.th"
download = alive_download
download_playlist = playlist_not_supported('alive')

########NEW FILE########
__FILENAME__ = baidu
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__all__ = ['baidu_download']

from ..common import *
from .. import common

from urllib import parse

def baidu_get_song_data(sid):
    data = json.loads(get_html('http://music.baidu.com/data/music/fmlink?songIds=%s' % sid, faker = True))['data']

    if data['xcode'] != '':
    # inside china mainland
        return data['songList'][0]
    else:
    # outside china mainland
        html = get_html("http://music.baidu.com/song/%s" % sid)

        # baidu pan link
        sourceLink = r1(r'"link-src-info"><a href="([^"]+)"', html)
        if sourceLink != None:
            sourceLink = sourceLink.replace('&amp;', '&')
        sourceHtml = get_html(sourceLink) if sourceLink != None else None

        songLink =  r1(r'\\"dlink\\":\\"([^"]*)\\"', sourceHtml).replace('\\\\/', '/') if sourceHtml != None else r1(r'download_url="([^"]+)"', html)
        songName = parse.unquote(r1(r'songname=([^&]+)&', html))
        artistName = parse.unquote(r1(r'songartistname=([^&]+)&', html))
        albumName = parse.unquote(r1(r'songartistname=([^&]+)&', html))
        lrcLink = r1(r'data-lyricdata=\'{ "href":"([^"]+)"', html)

        return json.loads(json.dumps({'songLink'   : songLink,
                                      'songName'   : songName,
                                      'artistName' : artistName,
                                      'albumName'  : albumName,
                                      'lrcLink'    : lrcLink}, ensure_ascii=False))

def baidu_get_song_url(data):
    return data['songLink']

def baidu_get_song_artist(data):
    return data['artistName']

def baidu_get_song_album(data):
    return data['albumName']

def baidu_get_song_title(data):
    return data['songName']

def baidu_get_song_lyric(data):
    lrc = data['lrcLink']
    return None if lrc is '' else "http://music.baidu.com%s" % lrc

def baidu_download_song(sid, output_dir = '.', merge = True, info_only = False):
    data = baidu_get_song_data(sid)
    url = baidu_get_song_url(data)
    title = baidu_get_song_title(data)
    artist = baidu_get_song_artist(data)
    album = baidu_get_song_album(data)
    lrc = baidu_get_song_lyric(data)

    assert url
    file_name = "%s - %s - %s" % (title, album, artist)

    type, ext, size = url_info(url, faker = True)
    print_info(site_info, title, type, size)
    if not info_only:
        download_urls([url], file_name, ext, size, output_dir, merge = merge, faker = True)

    if lrc:
        type, ext, size = url_info(lrc, faker = True)
        print_info(site_info, title, type, size)
        if not info_only:
            download_urls([lrc], file_name, ext, size, output_dir, faker = True)

def baidu_download_album(aid, output_dir = '.', merge = True, info_only = False):
    html = get_html('http://music.baidu.com/album/%s' % aid, faker = True)
    album_name = r1(r'<h2 class="album-name">(.+?)<\/h2>', html)
    artist = r1(r'<span class="author_list" title="(.+?)">', html)
    output_dir = '%s/%s - %s' % (output_dir, artist, album_name)
    ids = json.loads(r1(r'<span class="album-add" data-adddata=\'(.+?)\'>', html).replace('&quot', '').replace(';', '"'))['ids']
    track_nr = 1
    for id in ids:
        song_data = baidu_get_song_data(id)
        song_url = baidu_get_song_url(song_data)
        song_title = baidu_get_song_title(song_data)
        song_lrc = baidu_get_song_lyric(song_data)
        file_name = '%02d.%s' % (track_nr, song_title)

        type, ext, size = url_info(song_url, faker = True)
        print_info(site_info, song_title, type, size)
        if not info_only:
            download_urls([song_url], file_name, ext, size, output_dir, merge = merge, faker = True)

        if song_lrc:
            type, ext, size = url_info(song_lrc, faker = True)
            print_info(site_info, song_title, type, size)
            if not info_only:
                download_urls([song_lrc], file_name, ext, size, output_dir, faker = True)

        track_nr += 1

def baidu_download(url, output_dir = '.', stream_type = None, merge = True, info_only = False):
    if re.match(r'http://pan.baidu.com', url):
        html = get_html(url)

        title = r1(r'server_filename="([^"]+)"', html)
        if len(title.split('.')) > 1:
            title = ".".join(title.split('.')[:-1])

        real_url = r1(r'\\"dlink\\":\\"([^"]*)\\"', html).replace('\\\\/', '/')
        type, ext, size = url_info(real_url, faker = True)

        print_info(site_info, title, ext, size)
        if not info_only:
            download_urls([real_url], title, ext, size, output_dir, merge = merge)

    elif re.match(r'http://music.baidu.com/album/\d+', url):
        id = r1(r'http://music.baidu.com/album/(\d+)', url)
        baidu_download_album(id, output_dir, merge, info_only)

    elif re.match('http://music.baidu.com/song/\d+', url):
        id = r1(r'http://music.baidu.com/song/(\d+)', url)
        baidu_download_song(id, output_dir, merge, info_only)

site_info = "Baidu.com"
download = baidu_download
download_playlist = playlist_not_supported("baidu")

########NEW FILE########
__FILENAME__ = bilibili
#!/usr/bin/env python

__all__ = ['bilibili_download']

from ..common import *

from .sina import sina_download_by_vid
from .tudou import tudou_download_by_id
from .youku import youku_download_by_id

import re

def get_srt_xml(id):
    url = 'http://comment.bilibili.tv/%s.xml' % id
    return get_html(url)

def parse_srt_p(p):
    fields = p.split(',')
    assert len(fields) == 8, fields
    time, mode, font_size, font_color, pub_time, pool, user_id, history = fields
    time = float(time)

    mode = int(mode)
    assert 1 <= mode <= 8
    # mode 1~3: scrolling
    # mode 4: bottom
    # mode 5: top
    # mode 6: reverse?
    # mode 7: position
    # mode 8: advanced

    pool = int(pool)
    assert 0 <= pool <= 2
    # pool 0: normal
    # pool 1: srt
    # pool 2: special?

    font_size = int(font_size)

    font_color = '#%06x' % int(font_color)

    return pool, mode, font_size, font_color

def parse_srt_xml(xml):
    d = re.findall(r'<d p="([^"]+)">(.*)</d>', xml)
    for x, y in d:
        p = parse_srt_p(x)
    raise NotImplementedError()

def parse_cid_playurl(xml):
    from xml.dom.minidom import parseString
    doc = parseString(xml.encode('utf-8'))
    urls = [durl.getElementsByTagName('url')[0].firstChild.nodeValue for durl in doc.getElementsByTagName('durl')]
    return urls

def bilibili_download_by_cid(id, title, output_dir = '.', merge = True, info_only = False):
    url = 'http://interface.bilibili.tv/playurl?cid=' + id
    urls = [i if not re.match(r'.*\.qqvideo\.tc\.qq\.com', i) else re.sub(r'.*\.qqvideo\.tc\.qq\.com', 'http://vsrc.store.qq.com', i) for i in parse_cid_playurl(get_html(url, 'utf-8'))] # dirty fix for QQ

    if re.search(r'\.(flv|hlv)\b', urls[0]):
        type = 'flv'
    elif re.search(r'/flv/', urls[0]):
        type = 'flv'
    elif re.search(r'/mp4/', urls[0]):
        type = 'mp4'
    else:
        type = 'flv'

    size = 0
    for url in urls:
        _, _, temp = url_info(url)
        size += temp

    print_info(site_info, title, type, size)
    if not info_only:
        download_urls(urls, title, type, total_size = None, output_dir = output_dir, merge = merge)

def bilibili_download(url, output_dir = '.', merge = True, info_only = False):
    assert re.match(r'http://(www.bilibili.tv|bilibili.kankanews.com|bilibili.smgbb.cn)/video/av(\d+)', url)
    html = get_html(url)

    title = r1(r'<h2[^>]*>([^<>]+)</h2>', html)
    title = unescape_html(title)
    title = escape_file_path(title)

    flashvars = r1_of([r'player_params=\'(cid=\d+)', r'flashvars="([^"]+)"', r'"https://[a-z]+\.bilibili\.tv/secure,(cid=\d+)(?:&aid=\d+)?"'], html)
    assert flashvars
    t, id = flashvars.split('=', 1)
    id = id.split('&')[0]
    if t == 'cid':
        bilibili_download_by_cid(id, title, output_dir = output_dir, merge = merge, info_only = info_only)
    elif t == 'vid':
        sina_download_by_id(id, title, output_dir = output_dir, merge = merge, info_only = info_only)
    elif t == 'ykid':
        youku_download_by_id(id, title, output_dir = output_dir, merge = merge, info_only = info_only)
    elif t == 'uid':
        tudou_download_by_id(id, title, output_dir = output_dir, merge = merge, info_only = info_only)
    else:
        raise NotImplementedError(flashvars)

    if not info_only:
        title = get_filename(title)
        print('Downloading %s ...\n' % (title + '.cmt.xml'))
        xml = get_srt_xml(id)
        with open(os.path.join(output_dir, title + '.cmt.xml'), 'w', encoding='utf-8') as x:
            x.write(xml)

site_info = "bilibili.tv"
download = bilibili_download
download_playlist = playlist_not_supported('bilibili')

########NEW FILE########
__FILENAME__ = blip
#!/usr/bin/env python

__all__ = ['blip_download']

from ..common import *

import json

def blip_download(url, output_dir = '.', merge = True, info_only = False):
    p_url = url + "?skin=json&version=2&no_wrap=1"
    html = get_html(p_url)
    metadata = json.loads(html)
    
    title = metadata['Post']['title']
    real_url = metadata['Post']['media']['url']
    type, ext, size = url_info(real_url)
    
    print_info(site_info, title, type, size)
    if not info_only:
        download_urls([real_url], title, ext, size, output_dir, merge = merge)

site_info = "Blip.tv"
download = blip_download
download_playlist = playlist_not_supported('blip')

########NEW FILE########
__FILENAME__ = cbs
#!/usr/bin/env python

__all__ = ['cbs_download']

from ..common import *

from .theplatform import theplatform_download_by_pid

def cbs_download(url, output_dir='.', merge=True, info_only=False):
    """Downloads CBS videos by URL.
    """

    html = get_content(url)
    pid = match1(html, r'video\.settings\.pid\s*=\s*\'([^\']+)\'')
    title = match1(html, r'video\.settings\.title\s*=\s*\"([^\"]+)\"')

    theplatform_download_by_pid(pid, title, output_dir=output_dir, merge=merge, info_only=info_only)

site_info = "CBS.com"
download = cbs_download
download_playlist = playlist_not_supported('cbs')

########NEW FILE########
__FILENAME__ = cntv
#!/usr/bin/env python

__all__ = ['cntv_download', 'cntv_download_by_id']

from ..common import *

import json
import re

def cntv_download_by_id(id, title = None, output_dir = '.', merge = True, info_only = False):
    assert id
    info = json.loads(get_html('http://vdn.apps.cntv.cn/api/getHttpVideoInfo.do?pid=' + id))
    title = title or info['title']
    video = info['video']
    alternatives = [x for x in video.keys() if x.startswith('chapters')]
    #assert alternatives in (['chapters'], ['chapters', 'chapters2']), alternatives
    chapters = video['chapters2'] if 'chapters2' in video else video['chapters']
    urls = [x['url'] for x in chapters]
    ext = r1(r'\.([^.]+)$', urls[0])
    assert ext in ('flv', 'mp4')
    size = 0
    for url in urls:
        _, _, temp = url_info(url)
        size += temp
    
    print_info(site_info, title, ext, size)
    if not info_only:
        download_urls(urls, title, ext, size, output_dir = output_dir, merge = merge)

def cntv_download(url, output_dir = '.', merge = True, info_only = False):
    if re.match(r'http://\w+\.cntv\.cn/(\w+/\w+/(classpage/video/)?)?\d+/\d+\.shtml', url):
        id = r1(r'<!--repaste.video.code.begin-->(\w+)<!--repaste.video.code.end-->', get_html(url))
    elif re.match(r'http://xiyou.cntv.cn/v-[\w-]+\.html', url):
        id = r1(r'http://xiyou.cntv.cn/v-([\w-]+)\.html', url)
    else:
        raise NotImplementedError(url)
    
    cntv_download_by_id(id, output_dir = output_dir, merge = merge, info_only = info_only)

site_info = "CNTV.com"
download = cntv_download
download_playlist = playlist_not_supported('cntv')

########NEW FILE########
__FILENAME__ = coursera
#!/usr/bin/env python

__all__ = ['coursera_download']

from ..common import *

def coursera_login(user, password, csrf_token):
    url = 'https://www.coursera.org/maestro/api/user/login'
    my_headers = {
        'Cookie': ('csrftoken=%s' % csrf_token),
        'Referer': 'https://www.coursera.org',
        'X-CSRFToken': csrf_token,
    }
    
    values = {
        'email_address': user,
        'password': password,
    }
    form_data = parse.urlencode(values).encode('utf-8')
    
    response = request.urlopen(request.Request(url, headers = my_headers, data = form_data))
    
    return response.headers

def coursera_download(url, output_dir = '.', merge = True, info_only = False):
    course_code = r1(r'coursera.org/([^/]+)', url)
    url = "http://class.coursera.org/%s/lecture/index" % course_code
    
    request.install_opener(request.build_opener(request.HTTPCookieProcessor()))
    
    import http.client
    conn = http.client.HTTPConnection('class.coursera.org')
    conn.request('GET', "/%s/lecture/index" % course_code)
    response = conn.getresponse()
    
    csrf_token = r1(r'csrf_token=([^;]+);', response.headers['Set-Cookie'])
    
    import netrc, getpass
    info = netrc.netrc().authenticators('coursera.org')
    if info is None:
        user = input("User:     ")
        password = getpass.getpass("Password: ")
    else:
        user, password = info[0], info[2]
    print("Logging in...")
    
    coursera_login(user, password, csrf_token)
    
    request.urlopen("https://class.coursera.org/%s/auth/auth_redirector?type=login&subtype=normal" % course_code) # necessary!
    
    html = get_html(url)
    
    course_name = "%s (%s)" % (r1(r'course_strings_name = "([^"]+)"', html), course_code)
    output_dir = os.path.join(output_dir, course_name)
    
    materials = re.findall(r'<a target="_new" href="([^"]+)"', html)
    num_of_slides = len(re.findall(r'title="[Ss]lides', html))
    num_of_srts = len(re.findall(r'title="Subtitles \(srt\)"', html))
    num_of_texts = len(re.findall(r'title="Subtitles \(text\)"', html))
    num_of_mp4s = len(re.findall(r'title="Video \(MP4\)"', html))
    num_of_others = len(materials) - num_of_slides - num_of_srts - num_of_texts - num_of_mp4s
    
    print("MOOC Site:               ", site_info)
    print("Course Name:             ", course_name)
    print("Num of Videos (MP4):     ", num_of_mp4s)
    print("Num of Subtitles (srt):  ", num_of_srts)
    print("Num of Subtitles (text): ", num_of_texts)
    print("Num of Slides:           ", num_of_slides)
    print("Num of other resources:  ", num_of_others)
    print()
    
    if info_only:
        return
    
    # Process downloading
    
    names = re.findall(r'<div class="hidden">([^<]+)</div>', html)
    assert len(names) == len(materials)
    
    for i in range(len(materials)):
        title = names[i]
        resource_url = materials[i]
        ext = r1(r'format=(.+)', resource_url) or r1(r'\.(\w\w\w\w|\w\w\w|\w\w|\w)$', resource_url) or r1(r'download.(mp4)', resource_url)
        _, _, size = url_info(resource_url)
        
        try:
            if ext == 'mp4':
                download_urls([resource_url], title, ext, size, output_dir, merge = merge)
            else:
                download_url_chunked(resource_url, title, ext, size, output_dir, merge = merge)
        except Exception as err:
            print('Skipping %s: %s\n' % (resource_url, err))
            continue
    
    return

def download_url_chunked(url, title, ext, size, output_dir = '.', refer = None, merge = True, faker = False):
    if dry_run:
        print('Real URL:\n', [url], '\n')
        return
    
    title = escape_file_path(title)
    if ext:
        filename = '%s.%s' % (title, ext)
    else:
        filename = title
    filepath = os.path.join(output_dir, filename)
    
    if not force and os.path.exists(filepath):
        print('Skipping %s: file already exists' % tr(filepath))
        print()
        return
    
    bar = DummyProgressBar()
    print('Downloading %s ...' % tr(filename))
    url_save_chunked(url, filepath, bar, refer = refer, faker = faker)
    bar.done()
    
    print()
    return

site_info = "Coursera"
download = coursera_download
download_playlist = playlist_not_supported('coursera')

########NEW FILE########
__FILENAME__ = dailymotion
#!/usr/bin/env python

__all__ = ['dailymotion_download']

from ..common import *

def dailymotion_download(url, output_dir = '.', merge = True, info_only = False):
    """Downloads Dailymotion videos by URL.
    """

    id = match1(url, r'/video/([^\?]+)') or match1(url, r'video=([^\?]+)')
    embed_url = 'http://www.dailymotion.com/embed/video/%s' % id
    html = get_content(embed_url)

    info = json.loads(match1(html, r'var\s*info\s*=\s*({.+}),\n'))

    title = info['title']

    for quality in ['stream_h264_hd1080_url', 'stream_h264_hd_url', 'stream_h264_hq_url', 'stream_h264_url', 'stream_h264_ld_url']:
        real_url = info[quality]
        if real_url:
            break

    type, ext, size = url_info(real_url)

    print_info(site_info, title, type, size)
    if not info_only:
        download_urls([real_url], title, ext, size, output_dir, merge = merge)

site_info = "Dailymotion.com"
download = dailymotion_download
download_playlist = playlist_not_supported('dailymotion')

########NEW FILE########
__FILENAME__ = douban
#!/usr/bin/env python

__all__ = ['douban_download']

import urllib.request, urllib.parse
from ..common import *

def douban_download(url, output_dir = '.', merge = True, info_only = False):
    html = get_html(url)
    if 'subject' in url:
        titles = re.findall(r'data-title="([^"]*)">', html)
        song_id = re.findall(r'<li class="song-item" id="([^"]*)"', html)
        song_ssid = re.findall(r'data-ssid="([^"]*)"', html)
        get_song_url = 'http://music.douban.com/j/songlist/get_song_url'
        
        for i in range(len(titles)):
            title = titles[i]
            datas = {
                'sid': song_id[i],
                'ssid': song_ssid[i]
            }
            post_params = urllib.parse.urlencode(datas).encode('utf-8')
            try:
                resp = urllib.request.urlopen(get_song_url, post_params)
                resp_data = json.loads(resp.read().decode('utf-8'))
                real_url = resp_data['r']
                type, ext, size = url_info(real_url)
                print_info(site_info, title, type, size)
            except:
                pass

            if not info_only:
                try:
                    download_urls([real_url], title, ext, size, output_dir, merge = merge)
                except:
                    pass

    else: 
        titles = re.findall(r'"name":"([^"]*)"', html)
        real_urls = [re.sub('\\\\/', '/', i) for i in re.findall(r'"rawUrl":"([^"]*)"', html)]
        
        for i in range(len(titles)):
            title = titles[i]
            real_url = real_urls[i]
            
            type, ext, size = url_info(real_url)
            
            print_info(site_info, title, type, size)
            if not info_only:
                download_urls([real_url], title, ext, size, output_dir, merge = merge)

site_info = "Douban.com"
download = douban_download
download_playlist = playlist_not_supported('douban')

########NEW FILE########
__FILENAME__ = ehow
#!/usr/bin/env python

__all__ = ['ehow_download']

from ..common import *

def ehow_download(url, output_dir = '.', merge = True, info_only = False):
	
	assert re.search(r'http://www.ehow.com/video_', url), "URL you entered is not supported"

	html = get_html(url)
	contentid = r1(r'<meta name="contentid" scheme="DMINSTR2" content="([^"]+)" />', html)
	vid = r1(r'"demand_ehow_videoid":"([^"]+)"', html)
	assert vid

	xml = get_html('http://www.ehow.com/services/video/series.xml?demand_ehow_videoid=%s' % vid)
    
	from xml.dom.minidom import parseString
	doc = parseString(xml)
	tab = doc.getElementsByTagName('related')[0].firstChild

	for video in tab.childNodes:
		if re.search(contentid, video.attributes['link'].value):
			url = video.attributes['flv'].value
			break

	title = video.attributes['title'].value
	assert title 

	type, ext, size = url_info(url)
	print_info(site_info, title, type, size)
	
	if not info_only:
		download_urls([url], title, ext, size, output_dir, merge = merge)

site_info = "ehow.com"
download = ehow_download
download_playlist = playlist_not_supported('ehow')
########NEW FILE########
__FILENAME__ = facebook
#!/usr/bin/env python

__all__ = ['facebook_download']

from ..common import *

def facebook_download(url, output_dir = '.', merge = True, info_only = False):
    html = get_html(url)
    
    title = r1(r'<title id="pageTitle">(.+) \| Facebook</title>', html)
    
    for fmt in ["hd_src", "sd_src"]:
        src= re.sub(r'\\/', r'/', r1(r'"' + fmt + '":"([^"]*)"', parse.unquote(unicodize(r1(r'\["params","([^"]*)"\]', html)))))
        if src:
            break
    
    type, ext, size = url_info(src)
    
    print_info(site_info, title, type, size)
    if not info_only:
        download_urls([src], title, ext, size, output_dir, merge = merge)

site_info = "Facebook.com"
download = facebook_download
download_playlist = playlist_not_supported('facebook')

########NEW FILE########
__FILENAME__ = fivesing
#!/usr/bin/env python

__all__ = ['fivesing_download']

from ..common import *

def fivesing_download(url, output_dir=".", merge=True, info_only=False):
    html = get_html(url)
    title = r1(r'var SongName   = "(.*)";', html)
    url = r1(r'file: "(\S*)"', html)
    songtype, ext, size = url_info(url)
    print_info(site_info, title, songtype, size)
    if not info_only:
        download_urls([url], title, ext, size, output_dir)

site_info = "5sing.com"
download = fivesing_download
download_playlist = playlist_not_supported("5sing")

########NEW FILE########
__FILENAME__ = freesound
#!/usr/bin/env python

__all__ = ['freesound_download']

from ..common import *

def freesound_download(url, output_dir = '.', merge = True, info_only = False):
    page = get_html(url)
    
    title = r1(r'<meta property="og:title" content="([^"]*)"', page)
    preview_url = r1(r'<meta property="og:audio" content="([^"]*)"', page)
    
    type, ext, size = url_info(preview_url)
    
    print_info(site_info, title, type, size)
    if not info_only:
        download_urls([preview_url], title, ext, size, output_dir, merge = merge)

site_info = "Freesound.org"
download = freesound_download
download_playlist = playlist_not_supported('freesound')

########NEW FILE########
__FILENAME__ = google
#!/usr/bin/env python

__all__ = ['google_download']

from ..common import *

import re

# YouTube media encoding options, in descending quality order.
# taken from http://en.wikipedia.org/wiki/YouTube#Quality_and_codecs, 3/22/2013.
youtube_codecs = [
    {'itag': 38, 'container': 'MP4', 'video_resolution': '3072p', 'video_encoding': 'H.264', 'video_profile': 'High', 'video_bitrate': '3.5-5', 'audio_encoding': 'AAC', 'audio_bitrate': '192'},
    {'itag': 46, 'container': 'WebM', 'video_resolution': '1080p', 'video_encoding': 'VP8', 'video_profile': '', 'video_bitrate': '', 'audio_encoding': 'Vorbis', 'audio_bitrate': '192'},
    {'itag': 37, 'container': 'MP4', 'video_resolution': '1080p', 'video_encoding': 'H.264', 'video_profile': 'High', 'video_bitrate': '3-4.3', 'audio_encoding': 'AAC', 'audio_bitrate': '192'},
    {'itag': 102, 'container': '', 'video_resolution': '', 'video_encoding': 'VP8', 'video_profile': '', 'video_bitrate': '2', 'audio_encoding': 'Vorbis', 'audio_bitrate': '192'},
    {'itag': 45, 'container': 'WebM', 'video_resolution': '720p', 'video_encoding': '', 'video_profile': '', 'video_bitrate': '', 'audio_encoding': '', 'audio_bitrate': ''},
    {'itag': 22, 'container': 'MP4', 'video_resolution': '720p', 'video_encoding': 'H.264', 'video_profile': 'High', 'video_bitrate': '2-2.9', 'audio_encoding': 'AAC', 'audio_bitrate': '192'},
    {'itag': 84, 'container': 'MP4', 'video_resolution': '720p', 'video_encoding': 'H.264', 'video_profile': '3D', 'video_bitrate': '2-2.9', 'audio_encoding': 'AAC', 'audio_bitrate': '152'},
    {'itag': 120, 'container': 'FLV', 'video_resolution': '720p', 'video_encoding': 'AVC', 'video_profile': 'Main@L3.1', 'video_bitrate': '2', 'audio_encoding': 'AAC', 'audio_bitrate': '128'},
    {'itag': 85, 'container': 'MP4', 'video_resolution': '520p', 'video_encoding': 'H.264', 'video_profile': '3D', 'video_bitrate': '2-2.9', 'audio_encoding': 'AAC', 'audio_bitrate': '152'},
    {'itag': 44, 'container': 'WebM', 'video_resolution': '480p', 'video_encoding': 'VP8', 'video_profile': '', 'video_bitrate': '1', 'audio_encoding': 'Vorbis', 'audio_bitrate': '128'},
    {'itag': 35, 'container': 'FLV', 'video_resolution': '480p', 'video_encoding': 'H.264', 'video_profile': 'Main', 'video_bitrate': '0.8-1', 'audio_encoding': 'AAC', 'audio_bitrate': '128'},
    {'itag': 101, 'container': 'WebM', 'video_resolution': '360p', 'video_encoding': 'VP8', 'video_profile': '3D', 'video_bitrate': '', 'audio_encoding': 'Vorbis', 'audio_bitrate': '192'},
    {'itag': 100, 'container': 'WebM', 'video_resolution': '360p', 'video_encoding': 'VP8', 'video_profile': '3D', 'video_bitrate': '', 'audio_encoding': 'Vorbis', 'audio_bitrate': '128'},
    {'itag': 43, 'container': 'WebM', 'video_resolution': '360p', 'video_encoding': 'VP8', 'video_profile': '', 'video_bitrate': '0.5', 'audio_encoding': 'Vorbis', 'audio_bitrate': '128'},
    {'itag': 34, 'container': 'FLV', 'video_resolution': '360p', 'video_encoding': 'H.264', 'video_profile': 'Main', 'video_bitrate': '0.5', 'audio_encoding': 'AAC', 'audio_bitrate': '128'},
    {'itag': 82, 'container': 'MP4', 'video_resolution': '360p', 'video_encoding': 'H.264', 'video_profile': '3D', 'video_bitrate': '0.5', 'audio_encoding': 'AAC', 'audio_bitrate': '96'},
    {'itag': 18, 'container': 'MP4', 'video_resolution': '270p/360p', 'video_encoding': 'H.264', 'video_profile': 'Baseline', 'video_bitrate': '0.5', 'audio_encoding': 'AAC', 'audio_bitrate': '96'},
    {'itag': 6, 'container': 'FLV', 'video_resolution': '270p', 'video_encoding': 'Sorenson H.263', 'video_profile': '', 'video_bitrate': '0.8', 'audio_encoding': 'MP3', 'audio_bitrate': '64'},
    {'itag': 83, 'container': 'MP4', 'video_resolution': '240p', 'video_encoding': 'H.264', 'video_profile': '3D', 'video_bitrate': '0.5', 'audio_encoding': 'AAC', 'audio_bitrate': '96'},
    {'itag': 13, 'container': '3GP', 'video_resolution': '', 'video_encoding': 'MPEG-4 Visual', 'video_profile': '', 'video_bitrate': '0.5', 'audio_encoding': 'AAC', 'audio_bitrate': ''},
    {'itag': 5, 'container': 'FLV', 'video_resolution': '240p', 'video_encoding': 'Sorenson H.263', 'video_profile': '', 'video_bitrate': '0.25', 'audio_encoding': 'MP3', 'audio_bitrate': '64'},
    {'itag': 36, 'container': '3GP', 'video_resolution': '240p', 'video_encoding': 'MPEG-4 Visual', 'video_profile': 'Simple', 'video_bitrate': '0.17', 'audio_encoding': 'AAC', 'audio_bitrate': '38'},
    {'itag': 17, 'container': '3GP', 'video_resolution': '144p', 'video_encoding': 'MPEG-4 Visual', 'video_profile': 'Simple', 'video_bitrate': '0.05', 'audio_encoding': 'AAC', 'audio_bitrate': '24'},
]
fmt_level = dict(
    zip(
        [str(codec['itag'])
            for codec in
                youtube_codecs],
        range(len(youtube_codecs))))

def google_download(url, output_dir = '.', merge = True, info_only = False):
    # Percent-encoding Unicode URL
    url = parse.quote(url, safe = ':/+%')

    service = url.split('/')[2].split('.')[0]

    if service == 'plus': # Google Plus

        if not re.search(r'plus.google.com/photos/[^/]*/albums/\d+/\d+', url):
            html = get_html(url)
            url = "https://plus.google.com/" + r1(r'"(photos/\d+/albums/\d+/\d+)', html)
            title = r1(r'<title>([^<\n]+)', html)
        else:
            title = None

        html = get_html(url)
        real_urls = re.findall(r'\[(\d+),\d+,\d+,"([^"]+)"\]', html)
        real_url = unicodize(sorted(real_urls, key = lambda x : fmt_level[x[0]])[0][1])

        if title is None:
            post_url = r1(r'"(https://plus.google.com/\d+/posts/[^"]*)"', html)
            post_html = get_html(post_url)
            title = r1(r'<title[^>]*>([^<\n]+)', post_html)

        if title is None:
            response = request.urlopen(request.Request(real_url))
            if response.headers['content-disposition']:
                filename = parse.unquote(r1(r'filename="?(.+)"?', response.headers['content-disposition'])).split('.')
                title = ''.join(filename[:-1])

        type, ext, size = url_info(real_url)
        if ext is None:
            ext = 'mp4'

    elif service in ['docs', 'drive'] : # Google Docs

        html = get_html(url)

        title = r1(r'"title":"([^"]*)"', html) or r1(r'<meta itemprop="name" content="([^"]*)"', html)
        if len(title.split('.')) > 1:
            title = ".".join(title.split('.')[:-1])

        docid = r1(r'"docid":"([^"]*)"', html)

        request.install_opener(request.build_opener(request.HTTPCookieProcessor()))

        request.urlopen(request.Request("https://docs.google.com/uc?id=%s&export=download" % docid))
        real_url ="https://docs.google.com/uc?export=download&confirm=no_antivirus&id=%s" % docid

        type, ext, size = url_info(real_url)

    print_info(site_info, title, ext, size)
    if not info_only:
        download_urls([real_url], title, ext, size, output_dir, merge = merge)

site_info = "Google.com"
download = google_download
download_playlist = playlist_not_supported('google')

########NEW FILE########
__FILENAME__ = ifeng
#!/usr/bin/env python

__all__ = ['ifeng_download', 'ifeng_download_by_id']

from ..common import *

def ifeng_download_by_id(id, title = None, output_dir = '.', merge = True, info_only = False):
    assert r1(r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', id), id
    url = 'http://v.ifeng.com/video_info_new/%s/%s/%s.xml' % (id[-2], id[-2:], id)
    xml = get_html(url, 'utf-8')
    title = r1(r'Name="([^"]+)"', xml)
    title = unescape_html(title)
    url = r1(r'VideoPlayUrl="([^"]+)"', xml)
    from random import randint
    r = randint(10, 19)
    url = url.replace('http://video.ifeng.com/', 'http://video%s.ifeng.com/' % r)
    type, ext, size = url_info(url)
    
    print_info(site_info, title, ext, size)
    if not info_only:
        download_urls([url], title, ext, size, output_dir, merge = merge)

def ifeng_download(url, output_dir = '.', merge = True, info_only = False):
    id = r1(r'/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\.shtml$', url)
    if id:
        return ifeng_download_by_id(id, None, output_dir = output_dir, merge = merge, info_only = info_only)
    
    html = get_html(url)
    id = r1(r'var vid="([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"', html)
    assert id, "can't find video info"
    return ifeng_download_by_id(id, None, output_dir = output_dir, merge = merge, info_only = info_only)

site_info = "ifeng.com"
download = ifeng_download
download_playlist = playlist_not_supported('ifeng')

########NEW FILE########
__FILENAME__ = instagram
#!/usr/bin/env python

__all__ = ['instagram_download']

from ..common import *

def instagram_download(url, output_dir = '.', merge = True, info_only = False):
    html = get_html(url)
    
    id = r1(r'instagram.com/p/([^/]+)/', html)
    description = r1(r'<meta property="og:description" content="([^"]*)"', html)
    title = description + " [" + id + "]"
    url = r1(r'<meta property="og:video" content="([^"]*)"', html)
    type, ext, size = url_info(url)
    
    print_info(site_info, title, type, size)
    if not info_only:
        download_urls([url], title, ext, size, output_dir, merge = merge)

site_info = "Instagram.com"
download = instagram_download
download_playlist = playlist_not_supported('instagram')

########NEW FILE########
__FILENAME__ = iqiyi
#!/usr/bin/env python

__all__ = ['iqiyi_download']

from ..common import *

def iqiyi_download(url, output_dir = '.', merge = True, info_only = False):
    html = get_html(url)

    tvid = r1(r'data-player-tvid="([^"]+)"', html)
    videoid = r1(r'data-player-videoid="([^"]+)"', html)
    assert tvid
    assert videoid

    info_url = 'http://cache.video.qiyi.com/vj/%s/%s/' % (tvid, videoid)
    info = get_html(info_url)
    raise NotImplementedError('iqiyi')

    from xml.dom.minidom import parseString
    doc = parseString(info_xml)
    title = doc.getElementsByTagName('title')[0].firstChild.nodeValue
    size = int(doc.getElementsByTagName('totalBytes')[0].firstChild.nodeValue)
    urls = [n.firstChild.nodeValue for n in doc.getElementsByTagName('file')]
    assert urls[0].endswith('.f4v'), urls[0]

    for i in range(len(urls)):
        temp_url = "http://data.video.qiyi.com/%s" % urls[i].split("/")[-1].split(".")[0] + ".ts"
        try:
            response = request.urlopen(temp_url)
        except request.HTTPError as e:
            key = r1(r'key=(.*)', e.geturl())
        assert key
        urls[i] += "?key=%s" % key

    print_info(site_info, title, 'flv', size)
    if not info_only:
        download_urls(urls, title, 'flv', size, output_dir = output_dir, merge = merge)

site_info = "iQIYI.com"
download = iqiyi_download
download_playlist = playlist_not_supported('iqiyi')

########NEW FILE########
__FILENAME__ = joy
#!/usr/bin/env python

__all__ = ['joy_download']

from ..common import *

def video_info(channel_id, program_id, volumn_id):
    url = 'http://msx.app.joy.cn/service.php'
    if program_id:
        url += '?action=vodmsxv6'
        url += '&channelid=%s' % channel_id
        url += '&programid=%s' % program_id
        url += '&volumnid=%s' % volumn_id
    else:
        url += '?action=msxv6'
        url += '&videoid=%s' % volumn_id
    
    xml = get_html(url)
    
    name = r1(r'<Title>(?:<!\[CDATA\[)?(.+?)(?:\]\]>)?</Title>', xml)
    urls = re.findall(r'<Url[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</Url>', xml)
    hostpath = r1(r'<HostPath[^>]*>(?:<!\[CDATA\[)?(.+?)(?:\]\]>)?</HostPath>', xml)
    
    return name, urls, hostpath

def joy_download(url, output_dir = '.', merge = True, info_only = False):
    channel_id = r1(r'[^_]channelId\s*:\s*"([^\"]+)"', get_html(url))
    program_id = r1(r'[^_]programId\s*:\s*"([^\"]+)"', get_html(url))
    volumn_id = r1(r'[^_]videoId\s*:\s*"([^\"]+)"', get_html(url))
    
    title, urls, hostpath = video_info(channel_id, program_id, volumn_id)
    urls = [hostpath + url for url in urls]
    
    size = 0
    for url in urls:
        _, ext, temp = url_info(url)
        size += temp
    
    print_info(site_info, title, ext, size)
    if not info_only:
        download_urls(urls, title, ext, size, output_dir = output_dir, merge = merge)

site_info = "Joy.cn"
download = joy_download
download_playlist = playlist_not_supported('joy')

########NEW FILE########
__FILENAME__ = jpopsuki
#!/usr/bin/env python

__all__ = ['jpopsuki_download']

from ..common import *

def jpopsuki_download(url, output_dir='.', merge=True, info_only=False):
    html = get_html(url, faker=True)
    
    title = r1(r'<meta name="title" content="([^"]*)"', html)
    if title.endswith(' - JPopsuki TV'):
        title = title[:-14]
    
    url = "http://jpopsuki.tv%s" % r1(r'<source src="([^"]*)"', html)
    type, ext, size = url_info(url, faker=True)
    
    print_info(site_info, title, type, size)
    if not info_only:
        download_urls([url], title, ext, size, output_dir, merge=merge, faker=True)

site_info = "JPopsuki.tv"
download = jpopsuki_download
download_playlist = playlist_not_supported('jpopsuki')

########NEW FILE########
__FILENAME__ = khan
#!/usr/bin/env python

__all__ = ['khan_download']

from ..common import *
from .youtube import youtube_download_by_id

def khan_download(url, output_dir = '.', merge = True, info_only = False):
    page = get_html(url)
    id = page[page.find('src="https://www.youtube.com/embed/') + len('src="https://www.youtube.com/embed/') :page.find('?enablejsapi=1&wmode=transparent&modestbranding=1&rel=0&fs=1&showinfo=0')]
    youtube_download_by_id(id, output_dir=output_dir, merge=merge, info_only=info_only)

site_info = "khanacademy.org"
download = khan_download
download_playlist = playlist_not_supported('khan')

########NEW FILE########
__FILENAME__ = ku6
#!/usr/bin/env python

__all__ = ['ku6_download', 'ku6_download_by_id']

from ..common import *

import json
import re

def ku6_download_by_id(id, title = None, output_dir = '.', merge = True, info_only = False):
    data = json.loads(get_html('http://v.ku6.com/fetchVideo4Player/%s...html' % id))['data']
    t = data['t']
    f = data['f']
    title = title or t
    assert title
    urls = f.split(',')
    ext = re.sub(r'.*\.', '', urls[0])
    assert ext in ('flv', 'mp4', 'f4v'), ext
    ext = {'f4v': 'flv'}.get(ext, ext)
    size = 0
    for url in urls:
        _, _, temp = url_info(url)
        size += temp
    
    print_info(site_info, title, ext, size)
    if not info_only:
        download_urls(urls, title, ext, size, output_dir, merge = merge)

def ku6_download(url, output_dir = '.', merge = True, info_only = False):
    patterns = [r'http://v.ku6.com/special/show_\d+/(.*)\.\.\.html',
            r'http://v.ku6.com/show/(.*)\.\.\.html',
            r'http://my.ku6.com/watch\?.*v=(.*)\.\..*']
    id = r1_of(patterns, url)

    ku6_download_by_id(id, output_dir = output_dir, merge = merge, info_only = info_only)

site_info = "Ku6.com"
download = ku6_download
download_playlist = playlist_not_supported('ku6')

########NEW FILE########
__FILENAME__ = letv
#!/usr/bin/env python

__all__ = ['letv_download']

import json
import random
import xml.etree.ElementTree as ET
from ..common import *

def get_timestamp():
    tn = random.random()
    url = 'http://api.letv.com/time?tn={}'.format(tn)
    result = get_content(url)
    return json.loads(result)['stime']

def get_key(t):
    for s in range(0, 8):
        e = 1 & t
        t >>= 1
        e <<= 31
        t += e
    return t ^ 185025305

def video_info(vid):
    tn = get_timestamp()
    key = get_key(tn)
    url = 'http://api.letv.com/mms/out/video/play?id={}&platid=1&splatid=101&format=1&tkey={}&domain=http%3A%2F%2Fwww.letv.com'.format(vid, key)
    r = get_content(url, decoded=False)
    xml_obj = ET.fromstring(r)
    info = json.loads(xml_obj.find("playurl").text)
    title = info.get('title')
    urls = info.get('dispatch')
    for k in urls.keys():
        url = urls[k][0]
        break
    url += '&termid=1&format=0&hwtype=un&ostype=Windows7&tag=letv&sign=letv&expect=1&pay=0&rateid={}'.format(k)
    return url, title

def letv_download_by_vid(vid, output_dir='.', merge=True, info_only=False):
    url, title = video_info(vid)
    _, _, size = url_info(url)
    ext = 'flv'
    print_info(site_info, title, ext, size)
    if not info_only:
        download_urls([url], title, ext, size, output_dir=output_dir, merge=merge)

def letv_download(url, output_dir='.', merge=True, info_only=False):
    if re.match(r'http://www.letv.com/ptv/vplay/(\d+).html', url):
        vid = match1(url, r'http://www.letv.com/ptv/vplay/(\d+).html')
    else:
        html = get_content(url)
        vid = match1(html, r'vid="(\d+)"')
    letv_download_by_vid(vid, output_dir=output_dir, merge=merge, info_only=info_only)


site_info = "letv.com"
download = letv_download
download_playlist = playlist_not_supported('letv')

########NEW FILE########
__FILENAME__ = magisto
#!/usr/bin/env python

__all__ = ['magisto_download']

from ..common import *

def magisto_download(url, output_dir='.', merge=True, info_only=False):
    html = get_html(url)

    title1 = r1(r'<meta name="twitter:title" content="([^"]*)"', html)
    title2 = r1(r'<meta name="twitter:description" content="([^"]*)"', html)
    video_hash = r1(r'http://www.magisto.com/video/([^/]+)', url)
    title = "%s %s - %s" % (title1, title2, video_hash)
    url = r1(r'<source type="[^"]+" src="([^"]*)"', html)
    type, ext, size = url_info(url)

    print_info(site_info, title, type, size)
    if not info_only:
        download_urls([url], title, ext, size, output_dir, merge=merge)

site_info = "Magisto.com"
download = magisto_download
download_playlist = playlist_not_supported('magisto')

########NEW FILE########
__FILENAME__ = miomio
#!/usr/bin/env python

__all__ = ['miomio_download']

from ..common import *

from .sina import sina_download_by_vid
from .tudou import tudou_download_by_id
from .youku import youku_download_by_id

def miomio_download(url, output_dir = '.', merge = True, info_only = False):
    html = get_html(url)
    
    title = r1(r'<meta name="description" content="([^"]*)"', html)
    flashvars = r1(r'flashvars="(type=[^"]*)"', html)
    
    t = r1(r'type=(\w+)', flashvars)
    id = r1(r'vid=([^"]+)', flashvars)
    if t == 'youku':
        youku_download_by_id(id, title, output_dir=output_dir, merge=merge, info_only=info_only)
    elif t == 'tudou':
        tudou_download_by_id(id, title, output_dir=output_dir, merge=merge, info_only=info_only)
    elif t == 'sina':
        sina_download_by_vid(id, title, output_dir=output_dir, merge=merge, info_only=info_only)
    else:
        raise NotImplementedError(flashvars)

site_info = "MioMio.tv"
download = miomio_download
download_playlist = playlist_not_supported('miomio')

########NEW FILE########
__FILENAME__ = mixcloud
#!/usr/bin/env python

__all__ = ['mixcloud_download']

from ..common import *

def mixcloud_download(url, output_dir = '.', merge = True, info_only = False):
    html = get_html(url)
    title = r1(r'<meta property="og:title" content="([^"]*)"', html)
    preview_url = r1("m-preview=\"([^\"]+)\"", html)
    
    url = re.sub(r'previews', r'c/originals', preview_url)
    for i in range(10, 30):
        url = re.sub(r'stream[^.]*', r'stream' + str(i), url)
        
        try:
            type, ext, size = url_info(url)
            break
        except:
            continue
    
    try:
        type
    except:
        url = re.sub('c/originals', r'c/m4a/64', url)
        url = re.sub('.mp3', '.m4a', url)
        for i in range(10, 30):
            url = re.sub(r'stream[^.]*', r'stream' + str(i), url)
            
            try:
                type, ext, size = url_info(url)
                break
            except:
                continue
    
    print_info(site_info, title, type, size)
    if not info_only:
        download_urls([url], title, ext, size, output_dir, merge = merge)

site_info = "Mixcloud.com"
download = mixcloud_download
download_playlist = playlist_not_supported('mixcloud')

########NEW FILE########
__FILENAME__ = netease
#!/usr/bin/env python

__all__ = ['netease_download']

from ..common import *

def netease_download(url, output_dir = '.', merge = True, info_only = False):
    html = get_decoded_html(url)

    title = r1('movieDescription=\'([^\']+)\'', html) or r1('<title>(.+)</title>', html)

    if title[0] == ' ':
        title = title[1:]
    
    src = r1(r'<source src="([^"]+)"', html) or r1(r'<source type="[^"]+" src="([^"]+)"', html)
    
    if src:
        sd_url = r1(r'(.+)-mobile.mp4', src) + ".flv"
        _, _, sd_size = url_info(sd_url)
        
        hd_url = re.sub('/SD/', '/HD/', sd_url)
        _, _, hd_size = url_info(hd_url)
        
        if hd_size > sd_size:
            url, size = hd_url, hd_size
        else:
            url, size = sd_url, sd_size
        ext = 'flv'
        
    else:
        url = (r1(r'["\'](.+)-list.m3u8["\']', html) or r1(r'["\'](.+).m3u8["\']', html)) + ".mp4"
        _, _, size = url_info(url)
        ext = 'mp4'
    
    print_info(site_info, title, ext, size)
    if not info_only:
        download_urls([url], title, ext, size, output_dir = output_dir, merge = merge)

site_info = "163.com"
download = netease_download
download_playlist = playlist_not_supported('netease')

########NEW FILE########
__FILENAME__ = nicovideo
#!/usr/bin/env python

__all__ = ['nicovideo_download']

from ..common import *

def nicovideo_login(user, password):
    data = "current_form=login&mail=" + user +"&password=" + password + "&login_submit=Log+In"
    response = request.urlopen(request.Request("https://secure.nicovideo.jp/secure/login?site=niconico", headers=fake_headers, data=data.encode('utf-8')))
    return response.headers

def nicovideo_download(url, output_dir='.', merge=True, info_only=False):
    import ssl
    ssl_context = request.HTTPSHandler(
context=ssl.SSLContext(ssl.PROTOCOL_TLSv1))
    cookie_handler = request.HTTPCookieProcessor()
    opener = request.build_opener(ssl_context, cookie_handler)
    request.install_opener(opener)

    import netrc, getpass
    info = netrc.netrc().authenticators('nicovideo')
    if info is None:
        user = input("User:     ")
        password = getpass.getpass("Password: ")
    else:
        user, password = info[0], info[2]
    print("Logging in...")
    nicovideo_login(user, password)

    html = get_html(url) # necessary!
    title = unicodize(r1(r'<span class="videoHeaderTitle">([^<]+)</span>', html))

    api_html = get_html('http://www.nicovideo.jp/api/getflv?v=%s' % url.split('/')[-1])
    real_url = parse.unquote(r1(r'url=([^&]+)&', api_html))

    type, ext, size = url_info(real_url)

    print_info(site_info, title, type, size)
    if not info_only:
        download_urls([real_url], title, ext, size, output_dir, merge = merge)

site_info = "Nicovideo.jp"
download = nicovideo_download
download_playlist = playlist_not_supported('nicovideo')

########NEW FILE########
__FILENAME__ = pptv
#!/usr/bin/env python

__all__ = ['pptv_download', 'pptv_download_by_id']

from ..common import *

import re
import urllib
import hashlib

def pptv_download_by_id(id, title = None, output_dir = '.', merge = True, info_only = False):
    xml = get_html('http://web-play.pptv.com/webplay3-0-%s.xml?type=web.fpp' % id)
    host = r1(r'<sh>([^<>]+)</sh>', xml)
    key = r1(r'<key expire=[^<>]+>([^<>]+)</key>', xml)
    rid = r1(r'rid="([^"]+)"', xml)
    title = r1(r'nm="([^"]+)"', xml)
    pieces = re.findall('<sgm no="(\d+)"[^<>]+fs="(\d+)"', xml)
    numbers, fs = zip(*pieces)
    urls = ['http://%s/%s/%s?k=%s' % (host, i, rid, key) for i in numbers]
    total_size = sum(map(int, fs))
    assert rid.endswith('.mp4')
    
    print_info(site_info, title, 'mp4', total_size)
    if not info_only:
        download_urls(urls, title, 'mp4', total_size, output_dir = output_dir, merge = merge)

def pptv_download(url, output_dir = '.', merge = True, info_only = False):
    assert re.match(r'http://v.pptv.com/show/(\w+)\.html$', url)
    html = get_html(url)
    id = r1(r'webcfg\s*=\s*{"id":\s*(\d+)', html)
    assert id
    pptv_download_by_id(id, output_dir = output_dir, merge = merge, info_only = info_only)

site_info = "PPTV.com"
download = pptv_download
download_playlist = playlist_not_supported('pptv')

########NEW FILE########
__FILENAME__ = qq
#!/usr/bin/env python

__all__ = ['qq_download']

from ..common import *

def qq_download_by_id(id, title=None, output_dir='.', merge=True, info_only=False):
    xml = get_html('http://www.acfun.com/getinfo?vids=%s' % id)
    from xml.dom.minidom import parseString
    doc = parseString(xml)
    doc_root = doc.getElementsByTagName('root')[0]
    doc_vl = doc_root.getElementsByTagName('vl')[0]
    doc_vi = doc_vl.getElementsByTagName('vi')[0]
    fn = doc_vi.getElementsByTagName('fn')[0].firstChild.data
    fclip = doc_vi.getElementsByTagName('fclip')[0].firstChild.data
    if int(fclip) > 0:
        fn = fn[:-4] + "." + fclip + fn[-4:]
    fvkey = doc_vi.getElementsByTagName('fvkey')[0].firstChild.data
    doc_ul = doc_vi.getElementsByTagName('ul')
    url = doc_ul[0].getElementsByTagName('url')[0].firstChild.data
    url = url + fn + '?vkey=' + fvkey

    _, ext, size = url_info(url)

    print_info(site_info, title, ext, size)
    if not info_only:
        download_urls([url], title, ext, size, output_dir=output_dir, merge=merge)

def qq_download(url, output_dir = '.', merge = True, info_only = False):
    if re.match(r'http://v.qq.com/([^\?]+)\?vid', url):
        aid = r1(r'(.*)\.html', url)
        vid = r1(r'http://v.qq.com/[^\?]+\?vid=(\w+)', url)
        url = 'http://sns.video.qq.com/tvideo/fcgi-bin/video?vid=%s' % vid

    if re.match(r'http://y.qq.com/([^\?]+)\?vid', url):
        vid = r1(r'http://y.qq.com/[^\?]+\?vid=(\w+)', url)

        url = "http://v.qq.com/page/%s.html" % vid

        r_url = r1(r'<meta http-equiv="refresh" content="0;url=([^"]*)', get_html(url))
        if r_url:
            aid = r1(r'(.*)\.html', r_url)
            url = "%s/%s.html" % (aid, vid)

    if re.match(r'http://static.video.qq.com/.*vid=', url):
        vid = r1(r'http://static.video.qq.com/.*vid=(\w+)', url)
        url = "http://v.qq.com/page/%s.html" % vid

    if re.match(r'http://v.qq.com/cover/.*\.html', url):
        html = get_html(url)
        vid = r1(r'vid:"([^"]+)"', html)
        url = 'http://sns.video.qq.com/tvideo/fcgi-bin/video?vid=%s' % vid

    html = get_html(url)

    title = match1(html, r'<title>(.+?)</title>', r'title:"([^"]+)"')[0].strip()
    assert title
    title = unescape_html(title)
    title = escape_file_path(title)

    try:
        id = vid
    except:
        id = r1(r'vid:"([^"]+)"', html)

    qq_download_by_id(id, title, output_dir = output_dir, merge = merge, info_only = info_only)

site_info = "QQ.com"
download = qq_download
download_playlist = playlist_not_supported('qq')

########NEW FILE########
__FILENAME__ = sina
#!/usr/bin/env python

__all__ = ['sina_download', 'sina_download_by_vid', 'sina_download_by_vkey']

from ..common import *

from hashlib import md5
from random import randint
from time import time

def get_k(vid, rand):
    t = str(int('{0:b}'.format(int(time()))[:-6], 2))
    return md5((vid + 'Z6prk18aWxP278cVAH' + t + rand).encode('utf-8')).hexdigest()[:16] + t

def video_info(vid):
    rand = "0.{0}{1}".format(randint(10000, 10000000), randint(10000, 10000000))
    url = 'http://v.iask.com/v_play.php?vid={0}&ran={1}&p=i&k={2}'.format(vid, rand, get_k(vid, rand))
    xml = get_content(url, headers=fake_headers, decoded=True)

    urls = re.findall(r'<url>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</url>', xml)
    name = match1(xml, r'<vname>(?:<!\[CDATA\[)?(.+?)(?:\]\]>)?</vname>')
    vstr = match1(xml, r'<vstr>(?:<!\[CDATA\[)?(.+?)(?:\]\]>)?</vstr>')
    return urls, name, vstr

def sina_download_by_vid(vid, title=None, output_dir='.', merge=True, info_only=False):
    """Downloads a Sina video by its unique vid.
    http://video.sina.com.cn/
    """

    urls, name, vstr = video_info(vid)
    title = title or name
    assert title
    size = 0
    for url in urls:
        _, _, temp = url_info(url)
        size += temp

    print_info(site_info, title, 'flv', size)
    if not info_only:
        download_urls(urls, title, 'flv', size, output_dir = output_dir, merge = merge)

def sina_download_by_vkey(vkey, title=None, output_dir='.', merge=True, info_only=False):
    """Downloads a Sina video by its unique vkey.
    http://video.sina.com/
    """

    url = 'http://video.sina.com/v/flvideo/%s_0.flv' % vkey
    type, ext, size = url_info(url)

    print_info(site_info, title, 'flv', size)
    if not info_only:
        download_urls([url], title, 'flv', size, output_dir = output_dir, merge = merge)

def sina_download(url, output_dir='.', merge=True, info_only=False):
    """Downloads Sina videos by URL.
    """

    vid = match1(url, r'vid=(\d+)')
    if vid is None:
        video_page = get_content(url)
        vid = hd_vid = match1(video_page, r'hd_vid\s*:\s*\'([^\']+)\'')
        if hd_vid == '0':
            vids = match1(video_page, r'[^\w]vid\s*:\s*\'([^\']+)\'').split('|')
            vid = vids[-1]

    if vid:
        title = match1(video_page, r'title\s*:\s*\'([^\']+)\'')
        sina_download_by_vid(vid, title=title, output_dir=output_dir, merge=merge, info_only=info_only)
    else:
        vkey = match1(video_page, r'vkey\s*:\s*"([^"]+)"')
        title = match1(video_page, r'title\s*:\s*"([^"]+)"')
        sina_download_by_vkey(vkey, title=title, output_dir=output_dir, merge=merge, info_only=info_only)

site_info = "Sina.com"
download = sina_download
download_playlist = playlist_not_supported('sina')

########NEW FILE########
__FILENAME__ = sohu
#!/usr/bin/env python

__all__ = ['sohu_download']

from ..common import *

import json

def real_url(host, prot, file, new):
    url = 'http://%s/?prot=%s&file=%s&new=%s' % (host, prot, file, new)
    start, _, host, key = get_html(url).split('|')[:4]
    return '%s%s?key=%s' % (start[:-1], new, key)

def sohu_download(url, output_dir = '.', merge = True, info_only = False):
    if re.match(r'http://share.vrs.sohu.com', url):
        vid = r1('id=(\d+)', url)
    else:
        html = get_html(url)
        vid = r1(r'\Wvid\s*[\:=]\s*[\'"]?(\d+)[\'"]?', html)
    assert vid

    # Open Sogou proxy if required
    if get_sogou_proxy() is not None:
        server = sogou_proxy_server(get_sogou_proxy(), ostream=open(os.devnull, 'w'))
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        set_proxy(server.server_address)

    if re.match(r'http://tv.sohu.com/', url):
        data = json.loads(get_decoded_html('http://hot.vrs.sohu.com/vrs_flash.action?vid=%s' % vid))
        for qtyp in ["oriVid","superVid","highVid" ,"norVid","relativeId"]:
            hqvid = data['data'][qtyp]
            if hqvid != 0 and hqvid != vid :
                data = json.loads(get_decoded_html('http://hot.vrs.sohu.com/vrs_flash.action?vid=%s' % hqvid))
                break
        host = data['allot']
        prot = data['prot']
        urls = []
        data = data['data']
        title = data['tvName']
        size = sum(data['clipsBytes'])
        assert len(data['clipsURL']) == len(data['clipsBytes']) == len(data['su'])
        for file, new in zip(data['clipsURL'], data['su']):
            urls.append(real_url(host, prot, file, new))
        assert data['clipsURL'][0].endswith('.mp4')

    else:
        data = json.loads(get_decoded_html('http://my.tv.sohu.com/play/videonew.do?vid=%s&referer=http://my.tv.sohu.com' % vid))
        host = data['allot']
        prot = data['prot']
        urls = []
        data = data['data']
        title = data['tvName']
        size = sum([int(clipsBytes) for clipsBytes in data['clipsBytes']])
        assert len(data['clipsURL']) == len(data['clipsBytes']) == len(data['su'])
        for file, new in zip(data['clipsURL'], data['su']):
            urls.append(real_url(host, prot, file, new))
        assert data['clipsURL'][0].endswith('.mp4')

    # Close Sogou proxy if required
    if get_sogou_proxy() is not None:
        server.shutdown()
        unset_proxy()

    print_info(site_info, title, 'mp4', size)
    if not info_only:
        download_urls(urls, title, 'mp4', size, output_dir, refer = url, merge = merge)

site_info = "Sohu.com"
download = sohu_download
download_playlist = playlist_not_supported('sohu')

########NEW FILE########
__FILENAME__ = songtaste
#!/usr/bin/env python

__all__ = ['songtaste_download']

from ..common import *
import urllib.error

def songtaste_download(url, output_dir = '.', merge = True, info_only = False):
    if re.match(r'http://www.songtaste.com/song/\d+', url):
        old_fake_headers = fake_headers
        id = r1(r'http://www.songtaste.com/song/(\d+)', url)
        player_url = 'http://www.songtaste.com/playmusic.php?song_id='+str(id)
        fake_headers['Referer'] = player_url
        html = get_response(player_url).data
        r = '''^WrtSongLine\((.*)\)'''
        
        reg = re.compile(r , re.M)
        
        m = reg.findall(html.decode('gbk'))
        l = m[0].replace('"', '').replace(' ', '').split(',')
        
        title = l[2] + '-' + l[1]
        
        for i in range(0, 10):
            real_url = l[5].replace('http://mg', 'http://m%d' % i)
            try:
                type, ext, size = url_info(real_url, True)
            except urllib.error.HTTPError as e:
                if 403 == e.code:
                    continue
                else:
                    raise e
            break
        
        print_info(site_info, title, type, size)
        
        if not info_only:
            download_urls([real_url], title, ext, size, output_dir, refer = url, merge = merge, faker = True)
        fake_hreaders = old_fake_headers

site_info = "SongTaste.com"
download = songtaste_download
download_playlist = playlist_not_supported('songtaste')

########NEW FILE########
__FILENAME__ = soundcloud
#!/usr/bin/env python

__all__ = ['soundcloud_download', 'soundcloud_download_by_id']

from ..common import *

def soundcloud_download_by_id(id, title = None, output_dir = '.', merge = True, info_only = False):
    assert title
    
    #if info["downloadable"]:
    #   url = 'https://api.soundcloud.com/tracks/' + id + '/download?client_id=b45b1aa10f1ac2941910a7f0d10f8e28'
    url = 'https://api.soundcloud.com/tracks/' + id + '/stream?client_id=b45b1aa10f1ac2941910a7f0d10f8e28'
    assert url
    type, ext, size = url_info(url)
    
    print_info(site_info, title, type, size)
    if not info_only:
        download_urls([url], title, ext, size, output_dir, merge = merge)

def soundcloud_download(url, output_dir = '.', merge = True, info_only = False):
    metadata = get_html('https://api.sndcdn.com/resolve.json?url=' + url + '&client_id=b45b1aa10f1ac2941910a7f0d10f8e28')
    import json
    info = json.loads(metadata)
    title = info["title"]
    id = str(info["id"])
    
    soundcloud_download_by_id(id, title, output_dir, merge = merge, info_only = info_only)

site_info = "SoundCloud.com"
download = soundcloud_download
download_playlist = playlist_not_supported('soundcloud')

########NEW FILE########
__FILENAME__ = ted
#!/usr/bin/env python

__all__ = ['ted_download']

from ..common import *

def ted_download(url, output_dir = '.', merge = True, info_only = False):
    page = get_html(url).split("\n")
    for line in page:
        if line.find("<title>") > -1:
            title = line.replace("<title>", "").replace("</title>", "").replace("\t", "")
            title = title[:title.find(' | ')]
        if line.find("no-flash-video-download") > -1:
            url = line.replace('<a id="no-flash-video-download" href="', "").replace(" ", "").replace("\t", "").replace(".mp4", "-480p.mp4")
            url = url[:url.find('"')]
            type, ext, size = url_info(url)
            print_info(site_info, title, type, size)
            if not info_only:
                download_urls([url], title, ext, size, output_dir, merge=merge)
            break

site_info = "TED.com"
download = ted_download
download_playlist = playlist_not_supported('ted')

########NEW FILE########
__FILENAME__ = theplatform
#!/usr/bin/env python

from ..common import *

def theplatform_download_by_pid(pid, title, output_dir='.', merge=True, info_only=False):
    smil_url = "http://link.theplatform.com/s/dJ5BDC/%s/meta.smil?format=smil&mbr=true" % pid
    smil = get_content(smil_url)
    smil_base = unescape_html(match1(smil, r'<meta base="([^"]+)"'))
    smil_videos = {y:x for x,y in dict(re.findall(r'<video src="([^"]+)".+height="([^"]+)"', smil)).items()}
    for height in ['1080', '720', '480', '360', '240', '216']:
        if height in smil_videos:
            smil_video = smil_videos[height]
            break
    assert smil_video

    type, ext, size = 'mp4', 'mp4', 0

    print_info(site_info, title, type, size)
    if not info_only:
        download_rtmp_url(url=smil_base, playpath=ext+':'+smil_video, title=title, ext=ext, output_dir=output_dir)

site_info = "thePlatform.com"
download = theplatform_download_by_pid
download_playlist = playlist_not_supported('theplatform')

########NEW FILE########
__FILENAME__ = tudou
#!/usr/bin/env python

__all__ = ['tudou_download', 'tudou_download_playlist', 'tudou_download_by_id', 'tudou_download_by_iid']

from ..common import *

def tudou_download_by_iid(iid, title, output_dir = '.', merge = True, info_only = False):
    data = json.loads(get_decoded_html('http://www.tudou.com/outplay/goto/getItemSegs.action?iid=%s' % iid))
    vids = []
    for k in data:
        if len(data[k]) > 0:
            vids.append({"k": data[k][0]["k"], "size": data[k][0]["size"]})

    temp = max(vids, key=lambda x:x["size"])
    vid, size = temp["k"], temp["size"]

    xml = get_html('http://ct.v2.tudou.com/f?id=%s' % vid)
    from xml.dom.minidom import parseString
    doc = parseString(xml)
    url = [n.firstChild.nodeValue.strip() for n in doc.getElementsByTagName('f')][0]

    ext = r1(r'http://[\w.]*/(\w+)/[\w.]*', url)

    print_info(site_info, title, ext, size)
    if not info_only:
        download_urls([url], title, ext, size, output_dir = output_dir, merge = merge)

def tudou_download_by_id(id, title, output_dir = '.', merge = True, info_only = False):     
    html = get_html('http://www.tudou.com/programs/view/%s/' % id)
    
    iid = r1(r'iid\s*[:=]\s*(\S+)', html)    
    title = r1(r'kw\s*[:=]\s*[\'\"]([^\']+?)[\'\"]', html)
    tudou_download_by_iid(iid, title, output_dir = output_dir, merge = merge, info_only = info_only)

def tudou_download(url, output_dir = '.', merge = True, info_only = False):
    # Embedded player
    id = r1(r'http://www.tudou.com/v/([^/]+)/', url)
    if id:
        return tudou_download_by_id(id, title="", info_only=info_only)
    
    html = get_decoded_html(url)
    
    title = r1(r'kw\s*[:=]\s*[\'\"]([^\']+?)[\'\"]', html)
    assert title
    title = unescape_html(title)
    
    vcode = r1(r'vcode\s*[:=]\s*\'([^\']+)\'', html)
    if vcode:
        from .youku import youku_download_by_id
        return youku_download_by_id(vcode, title, output_dir = output_dir, merge = merge, info_only = info_only)
    
    iid = r1(r'iid\s*[:=]\s*(\d+)', html)
    if not iid:
        return tudou_download_playlist(url, output_dir, merge, info_only)
    
    tudou_download_by_iid(iid, title, output_dir = output_dir, merge = merge, info_only = info_only)

def parse_playlist(url):
    aid = r1('http://www.tudou.com/playlist/p/a(\d+)(?:i\d+)?\.html', url)
    html = get_decoded_html(url)
    if not aid:
        aid = r1(r"aid\s*[:=]\s*'(\d+)'", html)
    if re.match(r'http://www.tudou.com/albumcover/', url):
        atitle = r1(r"title\s*:\s*'([^']+)'", html)
    elif re.match(r'http://www.tudou.com/playlist/p/', url):
        atitle = r1(r'atitle\s*=\s*"([^"]+)"', html)
    else:
        raise NotImplementedError(url)
    assert aid
    assert atitle
    import json
    #url = 'http://www.tudou.com/playlist/service/getZyAlbumItems.html?aid='+aid
    url = 'http://www.tudou.com/playlist/service/getAlbumItems.html?aid='+aid
    return [(atitle + '-' + x['title'], str(x['itemId'])) for x in json.loads(get_html(url))['message']]

def tudou_download_playlist(url, output_dir = '.', merge = True, info_only = False):
    videos = parse_playlist(url)
    for i, (title, id) in enumerate(videos):
        print('Processing %s of %s videos...' % (i + 1, len(videos)))
        tudou_download_by_iid(id, title, output_dir = output_dir, merge = merge, info_only = info_only)

site_info = "Tudou.com"
download = tudou_download
download_playlist = tudou_download_playlist
########NEW FILE########
__FILENAME__ = tumblr
#!/usr/bin/env python

__all__ = ['tumblr_download']

from ..common import *

import re

def tumblr_download(url, output_dir = '.', merge = True, info_only = False):
    html = get_html(url)
    html = parse.unquote(html).replace('\/', '/')
    
    title = unescape_html(r1(r'<meta property="og:title" content="([^"]*)" />', html) or
        r1(r'<meta property="og:description" content="([^"]*)" />', html) or
        r1(r'<title>([^<\n]*)', html)).replace('\n', '')
    real_url = r1(r'source src=\\x22([^\\]+)\\', html)
    if not real_url:
        real_url = r1(r'audio_file=([^&]+)&', html) + '?plead=please-dont-download-this-or-our-lawyers-wont-let-us-host-audio'
    
    type, ext, size = url_info(real_url)
    
    print_info(site_info, title, type, size)
    if not info_only:
        download_urls([real_url], title, ext, size, output_dir, merge = merge)

site_info = "Tumblr.com"
download = tumblr_download
download_playlist = playlist_not_supported('tumblr')

########NEW FILE########
__FILENAME__ = vid48
#!/usr/bin/env python

__all__ = ['vid48_download']

from ..common import *

def vid48_download(url, output_dir = '.', merge = True, info_only = False):
    vid = r1(r'v=([^&]*)', url)
    p_url = "http://vid48.com/embed_player.php?vid=%s&autoplay=yes" % vid
    
    html = get_html(p_url)
    
    title = r1(r'<title>(.*)</title>', html)
    url = "http://vid48.com%s" % r1(r'file: "([^"]*)"', html)
    type, ext, size = url_info(url)
    
    print_info(site_info, title, type, size)
    if not info_only:
        download_urls([url], title, ext, size, output_dir, merge = merge)

site_info = "VID48"
download = vid48_download
download_playlist = playlist_not_supported('vid48')

########NEW FILE########
__FILENAME__ = vimeo
#!/usr/bin/env python

__all__ = ['vimeo_download', 'vimeo_download_by_id']

from ..common import *

def vimeo_download_by_id(id, title = None, output_dir = '.', merge = True, info_only = False):
    video_page = get_content('http://player.vimeo.com/video/%s' % id, headers=fake_headers)
    title = r1(r'<title>([^<]+)</title>', video_page)
    info = dict(re.findall(r'"([^"]+)":\{[^{]+"url":"([^"]+)"', video_page))
    for quality in ['hd', 'sd', 'mobile']:
        if quality in info:
            url = info[quality]
            break
    assert url
    
    type, ext, size = url_info(url, faker=True)
    
    print_info(site_info, title, type, size)
    if not info_only:
        download_urls([url], title, ext, size, output_dir, merge = merge, faker = True)

def vimeo_download(url, output_dir = '.', merge = True, info_only = False):
    id = r1(r'http://[\w.]*vimeo.com[/\w]*/(\d+)$', url)
    assert id
    
    vimeo_download_by_id(id, None, output_dir = output_dir, merge = merge, info_only = info_only)

site_info = "Vimeo.com"
download = vimeo_download
download_playlist = playlist_not_supported('vimeo')

########NEW FILE########
__FILENAME__ = vine
#!/usr/bin/env python

__all__ = ['vine_download']

from ..common import *

def vine_download(url, output_dir='.', merge=True, info_only=False):
    html = get_html(url)

    title1 = r1(r'<meta property="twitter:title" content="([^"]*)"', html)
    title2 = r1(r'<meta property="og:title" content="([^"]*)"', html)
    title = "%s - %s" % (title1, title2)
    url = r1(r'<source src="([^"]*)"', html) or r1(r'<meta itemprop="contentURL" content="([^"]*)"', html)
    if url[0:2] == "//":
        url = "http:" + url
    type, ext, size = url_info(url)

    print_info(site_info, title, type, size)
    if not info_only:
        download_urls([url], title, ext, size, output_dir, merge = merge)

site_info = "Vine.co"
download = vine_download
download_playlist = playlist_not_supported('vine')

########NEW FILE########
__FILENAME__ = vk
#!/usr/bin/env python

__all__ = ['vk_download']

from ..common import *

def vk_download(url, output_dir='.', merge=True, info_only=False):
    video_page = get_content(url)
    title = unescape_html(r1(r'"title":"([^"]+)"', video_page))
    info = dict(re.findall(r'\\"url(\d+)\\":\\"([^"]+)\\"', video_page))
    for quality in ['1080', '720', '480', '360', '240']:
        if quality in info:
            url = re.sub(r'\\\\\\/', r'/', info[quality])
            break
    assert url

    type, ext, size = url_info(url)

    print_info(site_info, title, type, size)
    if not info_only:
        download_urls([url], title, ext, size, output_dir, merge=merge)

site_info = "VK.com"
download = vk_download
download_playlist = playlist_not_supported('vk')

########NEW FILE########
__FILENAME__ = w56
#!/usr/bin/env python

__all__ = ['w56_download', 'w56_download_by_id']

from ..common import *

import json

def w56_download_by_id(id, title = None, output_dir = '.', merge = True, info_only = False):
    info = json.loads(get_html('http://vxml.56.com/json/%s/?src=site' % id))['info']
    title = title or info['Subject']
    assert title
    hd = info['hd']
    assert hd in (0, 1, 2)
    type = ['normal', 'clear', 'super'][hd]
    files = [x for x in info['rfiles'] if x['type'] == type]
    assert len(files) == 1
    size = int(files[0]['filesize'])
    url = files[0]['url']
    ext = r1(r'\.([^.]+)\?', url)
    assert ext in ('flv', 'mp4')
    
    print_info(site_info, title, ext, size)
    if not info_only:
        download_urls([url], title, ext, size, output_dir = output_dir, merge = merge)

def w56_download(url, output_dir = '.', merge = True, info_only = False):
    id = r1(r'http://www.56.com/u\d+/v_(\w+).html', url)
    w56_download_by_id(id, output_dir = output_dir, merge = merge, info_only = info_only)

site_info = "56.com"
download = w56_download
download_playlist = playlist_not_supported('56')

########NEW FILE########
__FILENAME__ = xiami
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__all__ = ['xiami_download']

from ..common import *

from xml.dom.minidom import parseString
from urllib import parse

def location_dec(str):
    head = int(str[0])
    str = str[1:]
    rows = head
    cols = int(len(str)/rows) + 1
    
    out = ""
    full_row = len(str) % head
    for c in range(cols):
        for r in range(rows):
            if c == (cols - 1) and r >= full_row:
                continue
            if r < full_row:
                char = str[r*cols+c]
            else:
                char = str[cols*full_row+(r-full_row)*(cols-1)+c]
            out += char
    return parse.unquote(out).replace("^", "0")

def xiami_download_lyric(lrc_url, file_name, output_dir):
    lrc = get_html(lrc_url, faker = True)
    filename = get_filename(file_name)
    if len(lrc) > 0:
        with open(output_dir + "/" + filename + '.lrc', 'w', encoding='utf-8') as x:
            x.write(lrc)

def xiami_download_pic(pic_url, file_name, output_dir):
    pic_url = pic_url.replace('_1', '')
    pos = pic_url.rfind('.')
    ext = pic_url[pos:]
    pic = get_response(pic_url, faker = True).data
    if len(pic) > 0:
        with open(output_dir + "/" + file_name.replace('/', '-') + ext, 'wb') as x:
            x.write(pic)

def xiami_download_song(sid, output_dir = '.', merge = True, info_only = False):
    xml = get_html('http://www.xiami.com/song/playlist/id/%s/object_name/default/object_id/0' % sid, faker = True)
    doc = parseString(xml)
    i = doc.getElementsByTagName("track")[0]
    artist = i.getElementsByTagName("artist")[0].firstChild.nodeValue
    album_name = i.getElementsByTagName("album_name")[0].firstChild.nodeValue
    song_title = i.getElementsByTagName("title")[0].firstChild.nodeValue
    url = location_dec(i.getElementsByTagName("location")[0].firstChild.nodeValue)
    try:
        lrc_url = i.getElementsByTagName("lyric")[0].firstChild.nodeValue
    except:
        pass
    type, ext, size = url_info(url, faker = True)
    if not ext:
        ext = 'mp3'
    
    print_info(site_info, song_title, ext, size)
    if not info_only:
        file_name = "%s - %s - %s" % (song_title, album_name, artist)
        download_urls([url], file_name, ext, size, output_dir, merge = merge, faker = True)
        try:
            xiami_download_lyric(lrc_url, file_name, output_dir)
        except:
            pass

def xiami_download_showcollect(cid, output_dir = '.', merge = True, info_only = False):
    html = get_html('http://www.xiami.com/song/showcollect/id/' + cid, faker = True)
    collect_name = r1(r'<title>(.*)</title>', html)

    xml = get_html('http://www.xiami.com/song/playlist/id/%s/type/3' % cid, faker = True)
    doc = parseString(xml)
    output_dir =  output_dir + "/" + "[" + collect_name + "]"
    tracks = doc.getElementsByTagName("track")
    track_nr = 1
    for i in tracks:
        artist = i.getElementsByTagName("artist")[0].firstChild.nodeValue
        album_name = i.getElementsByTagName("album_name")[0].firstChild.nodeValue
        song_title = i.getElementsByTagName("title")[0].firstChild.nodeValue
        url = location_dec(i.getElementsByTagName("location")[0].firstChild.nodeValue)
        try:
            lrc_url = i.getElementsByTagName("lyric")[0].firstChild.nodeValue
        except:
            pass
        type, ext, size = url_info(url, faker = True)
        if not ext:
            ext = 'mp3'
        
        print_info(site_info, song_title, type, size)
        if not info_only:
            file_name = "%02d.%s - %s - %s" % (track_nr, song_title, artist, album_name)
            download_urls([url], file_name, ext, size, output_dir, merge = merge, faker = True)
            try:
                xiami_download_lyric(lrc_url, file_name, output_dir)
            except:
                pass
        
        track_nr += 1

def xiami_download_album(aid, output_dir = '.', merge = True, info_only = False):
    xml = get_html('http://www.xiami.com/song/playlist/id/%s/type/1' % aid, faker = True)
    album_name = r1(r'<album_name><!\[CDATA\[(.*)\]\]>', xml)
    artist = r1(r'<artist><!\[CDATA\[(.*)\]\]>', xml)
    doc = parseString(xml)
    output_dir = output_dir + "/%s - %s" % (artist, album_name)
    tracks = doc.getElementsByTagName("track")
    track_nr = 1
    pic_exist = False
    for i in tracks:
        song_title = i.getElementsByTagName("title")[0].firstChild.nodeValue
        url = location_dec(i.getElementsByTagName("location")[0].firstChild.nodeValue)
        try:
            lrc_url = i.getElementsByTagName("lyric")[0].firstChild.nodeValue
        except:
            pass
        if not pic_exist:
            pic_url = i.getElementsByTagName("pic")[0].firstChild.nodeValue
        type, ext, size = url_info(url, faker = True)
        if not ext:
            ext = 'mp3'

        print_info(site_info, song_title, type, size)
        if not info_only:
            file_name = "%02d.%s" % (track_nr, song_title)
            download_urls([url], file_name, ext, size, output_dir, merge = merge, faker = True)
            try:
                xiami_download_lyric(lrc_url, file_name, output_dir)
            except:
                pass
            if not pic_exist:
                xiami_download_pic(pic_url, 'cover', output_dir)
                pic_exist = True
        
        track_nr += 1

def xiami_download(url, output_dir = '.', stream_type = None, merge = True, info_only = False):
    if re.match(r'http://www.xiami.com/album/\d+', url):
        id = r1(r'http://www.xiami.com/album/(\d+)', url)
        xiami_download_album(id, output_dir, merge, info_only)
    
    if re.match(r'http://www.xiami.com/song/showcollect/id/\d+', url):
        id = r1(r'http://www.xiami.com/song/showcollect/id/(\d+)', url)
        xiami_download_showcollect(id, output_dir, merge, info_only)
    
    if re.match('http://www.xiami.com/song/\d+', url):
        id = r1(r'http://www.xiami.com/song/(\d+)', url)
        xiami_download_song(id, output_dir, merge, info_only)
    
    if re.match('http://www.xiami.com/song/detail/id/\d+', url):
        id = r1(r'http://www.xiami.com/song/detail/id/(\d+)', url)
        xiami_download_song(id, output_dir, merge, info_only)

site_info = "Xiami.com"
download = xiami_download
download_playlist = playlist_not_supported("xiami")

########NEW FILE########
__FILENAME__ = yinyuetai
#!/usr/bin/env python

__all__ = ['yinyuetai_download', 'yinyuetai_download_by_id']

from ..common import *

def yinyuetai_download_by_id(id, title = None, output_dir = '.', merge = True, info_only = False):
    assert title
    html = get_html('http://www.yinyuetai.com/insite/get-video-info?flex=true&videoId=' + id)
    
    for quality in ['he\w*', 'hd\w*', 'hc\w*', '\w+']:
        url = r1(r'(http://' + quality + '\.yinyuetai\.com/uploads/videos/common/\w+\.(?:flv|mp4)\?(?:sc=[a-f0-9]{16}|v=\d{12}))', html)
        if url:
            break
    assert url
    type, ext, size = url_info(url)
    
    print_info(site_info, title, type, size)
    if not info_only:
        download_urls([url], title, ext, size, output_dir, merge = merge)

def yinyuetai_download(url, output_dir = '.', merge = True, info_only = False):
    id = r1(r'http://\w+.yinyuetai.com/video/(\d+)$', url)
    assert id
    html = get_html(url, 'utf-8')
    title = r1(r'<meta property="og:title"\s+content="([^"]+)"/>', html)
    assert title
    title = parse.unquote(title)
    title = escape_file_path(title)
    yinyuetai_download_by_id(id, title, output_dir, merge = merge, info_only = info_only)

site_info = "YinYueTai.com"
download = yinyuetai_download
download_playlist = playlist_not_supported('yinyuetai')

########NEW FILE########
__FILENAME__ = youku
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__all__ = ['youku_download', 'youku_download_playlist', 'youku_download_by_id']

from ..common import *

import json
from random import randint
from time import time
import re
import sys

def trim_title(title):
    title = title.replace(' - 视频 - 优酷视频 - 在线观看', '')
    title = title.replace(' - 专辑 - 优酷视频', '')
    title = re.sub(r'—([^—]+)—优酷网，视频高清在线观看', '', title)
    return title

def find_video_id_from_url(url):
    patterns = [r'^http://v.youku.com/v_show/id_([\w=]+).htm[l]?',
                r'^http://player.youku.com/player.php/sid/([\w=]+)/v.swf',
                r'^loader\.swf\?VideoIDS=([\w=]+)',
                r'^([\w=]+)$']
    return r1_of(patterns, url)

def find_video_id_from_show_page(url):
    return re.search(r'<a class="btnShow btnplay.*href="([^"]+)"', get_html(url)).group(1)

def youku_url(url):
    id = find_video_id_from_url(url)
    if id:
        return 'http://v.youku.com/v_show/id_%s.html' % id
    if re.match(r'http://www.youku.com/show_page/id_\w+.html', url):
        return find_video_id_from_show_page(url)
    if re.match(r'http://v.youku.com/v_playlist/\w+.html', url):
        return url
    return None

def parse_video_title(url, page):
    if re.search(r'v_playlist', url):
        # if we are playing a viedo from play list, the meta title might be incorrect
        title = r1_of([r'<div class="show_title" title="([^"]+)">[^<]', r'<title>([^<>]*)</title>'], page)
    else:
        title = r1_of([r'<div class="show_title" title="([^"]+)">[^<]', r'<title>([^-]+)—在线播放.*</title>', r'<meta name="title" content="([^"]*)"'], page)
    assert title
    title = trim_title(title)
    if re.search(r'v_playlist', url) and re.search(r'-.*\S+', title):
        title = re.sub(r'^[^-]+-\s*', '', title) # remove the special name from title for playlist video
    title = re.sub(r'—专辑：.*', '', title) # remove the special name from title for playlist video
    title = unescape_html(title)
    
    subtitle = re.search(r'<span class="subtitle" id="subtitle">([^<>]*)</span>', page)
    if subtitle:
        subtitle = subtitle.group(1).strip()
    if subtitle == title:
        subtitle = None
    if subtitle:
        title += '-' + subtitle
    return title

def parse_playlist_title(url, page):
    if re.search(r'v_playlist', url):
        # if we are playing a video from play list, the meta title might be incorrect
        title = re.search(r'<title>([^<>]*)</title>', page).group(1)
    else:
        title = re.search(r'<meta name="title" content="([^"]*)"', page).group(1)
    title = trim_title(title)
    if re.search(r'v_playlist', url) and re.search(r'-.*\S+', title):
        title = re.sub(r'^[^-]+-\s*', '', title)
    title = re.sub(r'^.*—专辑：《(.+)》', r'\1', title)
    title = unescape_html(title)
    return title

def parse_page(url):
    url = youku_url(url)
    page = get_html(url)
    id2 = re.search(r"var\s+videoId2\s*=\s*'(\S+)'", page).group(1)
    title = parse_video_title(url, page)
    return id2, title

def get_info(videoId2):
    return json.loads(get_html('http://v.youku.com/player/getPlayList/VideoIDS/' + videoId2 + '/timezone/+08/version/5/source/out/Sc/2'))
    
def find_video(info, stream_type = None):
    #key = '%s%x' % (info['data'][0]['key2'], int(info['data'][0]['key1'], 16) ^ 0xA55AA5A5)
    segs = info['data'][0]['segs']
    types = segs.keys()
    if not stream_type:
        for x in ['hd3', 'hd2', 'mp4', 'flv']:
            if x in types:
                stream_type = x
                break
        else:
            raise NotImplementedError()
    assert stream_type in ('hd3', 'hd2', 'mp4', 'flv')
    file_type = {'hd3': 'flv', 'hd2': 'flv', 'mp4': 'mp4', 'flv': 'flv'}[stream_type]
    
    seed = info['data'][0]['seed']
    source = list("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ/\\:._-1234567890")
    mixed = ''
    while source:
        seed = (seed * 211 + 30031) & 0xFFFF
        index = seed * len(source) >> 16
        c = source.pop(index)
        mixed += c
    
    ids = info['data'][0]['streamfileids'][stream_type].split('*')[:-1]
    vid = ''.join(mixed[int(i)] for i in ids)
    
    sid = '%s%s%s' % (int(time() * 1000), randint(1000, 1999), randint(1000, 9999))
    
    urls = []
    for s in segs[stream_type]:
        no = '%02x' % int(s['no'])
        url = 'http://f.youku.com/player/getFlvPath/sid/%s_%s/st/%s/fileid/%s%s%s?K=%s&ts=%s' % (sid, no, file_type, vid[:8], no.upper(), vid[10:], s['k'], s['seconds'])
        urls.append((url, int(s['size'])))
    return urls

def file_type_of_url(url):
    return str(re.search(r'/st/([^/]+)/', url).group(1))

def youku_download_by_id(id, title, output_dir = '.', stream_type = None, merge = True, info_only = False):
    # Open Sogou proxy if required
    if get_sogou_proxy() is not None:
        server = sogou_proxy_server(get_sogou_proxy(), ostream=open(os.devnull, 'w'))
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        set_proxy(server.server_address)
    
    info = get_info(id)
    
    # Close Sogou proxy if required
    if get_sogou_proxy() is not None:
        server.shutdown()
        unset_proxy()
    
    urls, sizes = zip(*find_video(info, stream_type))
    ext = file_type_of_url(urls[0])
    total_size = sum(sizes)
    
    print_info(site_info, title, ext, total_size)
    if not info_only:
        download_urls(urls, title, ext, total_size, output_dir, merge = merge)

def parse_playlist_videos(html):
    return re.findall(r'id="A_(\w+)"', html)

def parse_playlist_pages(html):
    m = re.search(r'<ul class="pages">.*?</ul>', html, flags = re.S)
    if m:
        urls = re.findall(r'href="([^"]+)"', m.group())
        x1, x2, x3 = re.match(r'^(.*page_)(\d+)(_.*)$', urls[-1]).groups()
        return ['http://v.youku.com%s%s%s?__rt=1&__ro=listShow' % (x1, i, x3) for i in range(2, int(x2) + 1)]
    else:
        return []

def parse_playlist(url):
    html = get_html(url)
    video_id = re.search(r"var\s+videoId\s*=\s*'(\d+)'", html).group(1)
    show_id = re.search(r'var\s+showid\s*=\s*"(\d+)"', html).group(1)
    list_url = 'http://v.youku.com/v_vpofficiallist/page_1_showid_%s_id_%s.html?__rt=1&__ro=listShow' % (show_id, video_id)
    html = get_html(list_url)
    ids = parse_playlist_videos(html)
    for url in parse_playlist_pages(html):
        ids.extend(parse_playlist_videos(get_html(url)))
    return ids

def parse_vplaylist(url):
    id = r1_of([r'^http://www.youku.com/playlist_show/id_(\d+)(?:_ascending_\d_mode_pic(?:_page_\d+)?)?.html',
                r'^http://v.youku.com/v_playlist/f(\d+)o[01]p\d+.html',
                r'^http://u.youku.com/user_playlist/pid_(\d+)_id_[\w=]+(?:_page_\d+)?.html'],
                url)
    assert id, 'not valid vplaylist url: ' + url
    url = 'http://www.youku.com/playlist_show/id_%s.html' % id
    n = int(re.search(r'<span class="num">(\d+)</span>', get_html(url)).group(1))
    return ['http://v.youku.com/v_playlist/f%so0p%s.html' % (id, i) for i in range(n)]

def youku_download_playlist(url, output_dir='.', merge=True, info_only=False):
    """Downloads a Youku playlist.
    """
    
    if re.match(r'http://www.youku.com/playlist_show/id_\d+(?:_ascending_\d_mode_pic(?:_page_\d+)?)?.html', url):
        ids = parse_vplaylist(url)
    elif re.match(r'http://v.youku.com/v_playlist/f\d+o[01]p\d+.html', url):
        ids = parse_vplaylist(url)
    elif re.match(r'http://u.youku.com/user_playlist/pid_(\d+)_id_[\w=]+(?:_page_\d+)?.html', url):
        ids = parse_vplaylist(url)
    elif re.match(r'http://www.youku.com/show_page/id_\w+.html', url):
        url = find_video_id_from_show_page(url)
        assert re.match(r'http://v.youku.com/v_show/id_([\w=]+).html', url), 'URL not supported as playlist'
        ids = parse_playlist(url)
    else:
        ids = []
    assert ids != []
    
    title = parse_playlist_title(url, get_html(url))
    title = filenameable(title)
    output_dir = os.path.join(output_dir, title)
    
    for i, id in enumerate(ids):
        print('Processing %s of %s videos...' % (i + 1, len(ids)))
        try:
            id, title = parse_page(youku_url(id))
            youku_download_by_id(id, title, output_dir=output_dir, merge=merge, info_only=info_only)
        except:
            continue

def youku_download(url, output_dir='.', merge=True, info_only=False):
    """Downloads Youku videos by URL.
    """
    
    try:
        youku_download_playlist(url, output_dir=output_dir, merge=merge, info_only=info_only)
    except:
        id, title = parse_page(url)
        youku_download_by_id(id, title=title, output_dir=output_dir, merge=merge, info_only=info_only)

site_info = "Youku.com"
download = youku_download
download_playlist = youku_download_playlist

########NEW FILE########
__FILENAME__ = youtube
#!/usr/bin/env python

__all__ = ['youtube_download', 'youtube_download_by_id']

from ..common import *

# YouTube media encoding options, in descending quality order.
# taken from http://en.wikipedia.org/wiki/YouTube#Quality_and_codecs, 2/14/2014.
yt_codecs = [
    {'itag': 38, 'container': 'MP4', 'video_resolution': '3072p', 'video_encoding': 'H.264', 'video_profile': 'High', 'video_bitrate': '3.5-5', 'audio_encoding': 'AAC', 'audio_bitrate': '192'},
    #{'itag': 85, 'container': 'MP4', 'video_resolution': '1080p', 'video_encoding': 'H.264', 'video_profile': '3D', 'video_bitrate': '3-4', 'audio_encoding': 'AAC', 'audio_bitrate': '192'},
    {'itag': 46, 'container': 'WebM', 'video_resolution': '1080p', 'video_encoding': 'VP8', 'video_profile': '', 'video_bitrate': '', 'audio_encoding': 'Vorbis', 'audio_bitrate': '192'},
    {'itag': 37, 'container': 'MP4', 'video_resolution': '1080p', 'video_encoding': 'H.264', 'video_profile': 'High', 'video_bitrate': '3-4.3', 'audio_encoding': 'AAC', 'audio_bitrate': '192'},
    #{'itag': 102, 'container': 'WebM', 'video_resolution': '720p', 'video_encoding': 'VP8', 'video_profile': '3D', 'video_bitrate': '', 'audio_encoding': 'Vorbis', 'audio_bitrate': '192'},
    {'itag': 45, 'container': 'WebM', 'video_resolution': '720p', 'video_encoding': 'VP8', 'video_profile': '', 'video_bitrate': '2', 'audio_encoding': 'Vorbis', 'audio_bitrate': '192'},
    #{'itag': 84, 'container': 'MP4', 'video_resolution': '720p', 'video_encoding': 'H.264', 'video_profile': '3D', 'video_bitrate': '2-3', 'audio_encoding': 'AAC', 'audio_bitrate': '192'},
    {'itag': 22, 'container': 'MP4', 'video_resolution': '720p', 'video_encoding': 'H.264', 'video_profile': 'High', 'video_bitrate': '2-3', 'audio_encoding': 'AAC', 'audio_bitrate': '192'},
    {'itag': 120, 'container': 'FLV', 'video_resolution': '720p', 'video_encoding': 'H.264', 'video_profile': 'Main@L3.1', 'video_bitrate': '2', 'audio_encoding': 'AAC', 'audio_bitrate': '128'},
    {'itag': 44, 'container': 'WebM', 'video_resolution': '480p', 'video_encoding': 'VP8', 'video_profile': '', 'video_bitrate': '1', 'audio_encoding': 'Vorbis', 'audio_bitrate': '128'},
    {'itag': 35, 'container': 'FLV', 'video_resolution': '480p', 'video_encoding': 'H.264', 'video_profile': 'Main', 'video_bitrate': '0.8-1', 'audio_encoding': 'AAC', 'audio_bitrate': '128'},
    #{'itag': 101, 'container': 'WebM', 'video_resolution': '360p', 'video_encoding': 'VP8', 'video_profile': '3D', 'video_bitrate': '', 'audio_encoding': 'Vorbis', 'audio_bitrate': '192'},
    #{'itag': 100, 'container': 'WebM', 'video_resolution': '360p', 'video_encoding': 'VP8', 'video_profile': '3D', 'video_bitrate': '', 'audio_encoding': 'Vorbis', 'audio_bitrate': '128'},
    {'itag': 43, 'container': 'WebM', 'video_resolution': '360p', 'video_encoding': 'VP8', 'video_profile': '', 'video_bitrate': '0.5', 'audio_encoding': 'Vorbis', 'audio_bitrate': '128'},
    {'itag': 34, 'container': 'FLV', 'video_resolution': '360p', 'video_encoding': 'H.264', 'video_profile': 'Main', 'video_bitrate': '0.5', 'audio_encoding': 'AAC', 'audio_bitrate': '128'},
    #{'itag': 82, 'container': 'MP4', 'video_resolution': '360p', 'video_encoding': 'H.264', 'video_profile': '3D', 'video_bitrate': '0.5', 'audio_encoding': 'AAC', 'audio_bitrate': '96'},
    {'itag': 18, 'container': 'MP4', 'video_resolution': '270p/360p', 'video_encoding': 'H.264', 'video_profile': 'Baseline', 'video_bitrate': '0.5', 'audio_encoding': 'AAC', 'audio_bitrate': '96'},
    {'itag': 6, 'container': 'FLV', 'video_resolution': '270p', 'video_encoding': 'Sorenson H.263', 'video_profile': '', 'video_bitrate': '0.8', 'audio_encoding': 'MP3', 'audio_bitrate': '64'},
    #{'itag': 83, 'container': 'MP4', 'video_resolution': '240p', 'video_encoding': 'H.264', 'video_profile': '3D', 'video_bitrate': '0.5', 'audio_encoding': 'AAC', 'audio_bitrate': '96'},
    {'itag': 13, 'container': '3GP', 'video_resolution': '', 'video_encoding': 'MPEG-4 Visual', 'video_profile': '', 'video_bitrate': '0.5', 'audio_encoding': 'AAC', 'audio_bitrate': ''},
    {'itag': 5, 'container': 'FLV', 'video_resolution': '240p', 'video_encoding': 'Sorenson H.263', 'video_profile': '', 'video_bitrate': '0.25', 'audio_encoding': 'MP3', 'audio_bitrate': '64'},
    {'itag': 36, 'container': '3GP', 'video_resolution': '240p', 'video_encoding': 'MPEG-4 Visual', 'video_profile': 'Simple', 'video_bitrate': '0.175', 'audio_encoding': 'AAC', 'audio_bitrate': '36'},
    {'itag': 17, 'container': '3GP', 'video_resolution': '144p', 'video_encoding': 'MPEG-4 Visual', 'video_profile': 'Simple', 'video_bitrate': '0.05', 'audio_encoding': 'AAC', 'audio_bitrate': '24'},
]

def decipher(js, s):
    def tr_js(code):
        code = re.sub(r'function', r'def', code)
        code = re.sub(r'\$', '_', code)
        code = re.sub(r'\{', r':\n\t', code)
        code = re.sub(r'\}', r'\n', code)
        code = re.sub(r'var\s+', r'', code)
        code = re.sub(r'(\w+).join\(""\)', r'"".join(\1)', code)
        code = re.sub(r'(\w+).length', r'len(\1)', code)
        code = re.sub(r'(\w+).reverse\(\)', r'\1[::-1]', code)
        code = re.sub(r'(\w+).slice\((\d+)\)', r'\1[\2:]', code)
        code = re.sub(r'(\w+).split\(""\)', r'list(\1)', code)
        return code

    f1 = match1(js, r'\w+\.sig\|\|(\w+)\(\w+\.\w+\)')
    f1def = match1(js, r'(function %s\(\w+\)\{[^\{]+\})' % f1)
    code = tr_js(f1def)
    f2 = match1(f1def, r'([$\w]+)\(\w+,\d+\)')
    if f2 is not None:
        f2e = re.escape(f2)
        f2def = match1(js, r'(function %s\(\w+,\w+\)\{[^\{]+\})' % f2e)
        f2 = re.sub(r'\$', r'_', f2)
        code = code + 'global %s\n' % f2 + tr_js(f2def)

    code = code + 'sig=%s(s)' % f1
    exec(code, globals(), locals())
    return locals()['sig']

def youtube_download_by_id(id, title=None, output_dir='.', merge=True, info_only=False):
    """Downloads a YouTube video by its unique id.
    """

    raw_video_info = get_content('http://www.youtube.com/get_video_info?video_id=%s' % id)
    video_info = parse.parse_qs(raw_video_info)

    if video_info['status'] == ['ok'] and ('use_cipher_signature' not in video_info or video_info['use_cipher_signature'] == ['False']):
        title = parse.unquote_plus(video_info['title'][0])
        stream_list = parse.parse_qs(raw_video_info)['url_encoded_fmt_stream_map'][0].split(',')

    else:
        # Parse video page when video_info is not usable.
        video_page = get_content('http://www.youtube.com/watch?v=%s' % id)
        ytplayer_config = json.loads(match1(video_page, r'ytplayer.config\s*=\s*([^\n]+});'))

        title = ytplayer_config['args']['title']
        stream_list = ytplayer_config['args']['url_encoded_fmt_stream_map'].split(',')

        html5player = ytplayer_config['assets']['js']
        if html5player[0:2] == '//':
            html5player = 'http:' + html5player

    streams = {
        parse.parse_qs(stream)['itag'][0] : parse.parse_qs(stream)
            for stream in stream_list
    }

    for codec in yt_codecs:
        itag = str(codec['itag'])
        if itag in streams:
            download_stream = streams[itag]
            break

    url = download_stream['url'][0]
    if 'sig' in download_stream:
        sig = download_stream['sig'][0]
        url = '%s&signature=%s' % (url, sig)
    elif 's' in download_stream:
        js = get_content(html5player)
        sig = decipher(js, download_stream['s'][0])
        url = '%s&signature=%s' % (url, sig)

    type, ext, size = url_info(url)

    print_info(site_info, title, type, size)
    if not info_only:
        download_urls([url], title, ext, size, output_dir, merge = merge)

def youtube_list_download_by_id(list_id, title=None, output_dir='.', merge=True, info_only=False):
    """Downloads a YouTube video list by its unique id.
    """

    video_page = get_content('http://www.youtube.com/playlist?list=%s' % list_id)
    ids = set(re.findall(r'<a href="\/watch\?v=([\w-]+)', video_page))
    for id in ids:
        youtube_download_by_id(id, title, output_dir, merge, info_only)

def youtube_download(url, output_dir='.', merge=True, info_only=False):
    """Downloads YouTube videos by URL.
    """

    id = match1(url, r'youtu.be/([^/]+)') or \
        match1(url, r'youtube.com/embed/([^/]+)') or \
        parse_query_param(url, 'v') or \
        parse_query_param(parse_query_param(url, 'u'), 'v')
    if id is None:
        list_id = parse_query_param(url, 'list') or \
          parse_query_param(url, 'p')
    assert id or list_id

    if id:
        youtube_download_by_id(id, title=None, output_dir=output_dir, merge=merge, info_only=info_only)
    else:
        youtube_list_download_by_id(list_id, title=None, output_dir=output_dir, merge=merge, info_only=info_only)

site_info = "YouTube.com"
download = youtube_download
download_playlist = playlist_not_supported('youtube')

########NEW FILE########
__FILENAME__ = __main__
#!/usr/bin/env python
__all__ = ['main', 'any_download', 'any_download_playlist']

from ..extractor import *
from ..common import *

def url_to_module(url):
    video_host = r1(r'https?://([^/]+)/', url)
    video_url = r1(r'https?://[^/]+(.*)', url)
    assert video_host and video_url, 'invalid url: ' + url

    if video_host.endswith('.com.cn'):
        video_host = video_host[:-3]
    domain = r1(r'(\.[^.]+\.[^.]+)$', video_host) or video_host
    assert domain, 'unsupported url: ' + url

    k = r1(r'([^.]+)', domain)
    downloads = {
        '163': netease,
        '56': w56,
        '5sing': fivesing,
        'acfun': acfun,
        'baidu': baidu,
        'bilibili': bilibili,
        'blip': blip,
        'cntv': cntv,
        'cbs': cbs,
        'coursera': coursera,
        'dailymotion': dailymotion,
        'douban': douban,
        'ehow': ehow,
        'facebook': facebook,
        'freesound': freesound,
        'google': google,
        'iask': sina,
        'ifeng': ifeng,
        'in': alive,
        'instagram': instagram,
        'iqiyi': iqiyi,
        'joy': joy,
        'jpopsuki': jpopsuki,
        'kankanews': bilibili,
        'ku6': ku6,
        'letv': letv,
        'magisto': magisto,
        'miomio': miomio,
        'mixcloud': mixcloud,
        'nicovideo': nicovideo,
        'pptv': pptv,
        'qq': qq,
        'sina': sina,
        'smgbb': bilibili,
        'sohu': sohu,
        'songtaste':songtaste,
        'soundcloud': soundcloud,
        'ted': ted,
        'theplatform': theplatform,
        'tudou': tudou,
        'tumblr': tumblr,
        'vid48': vid48,
        'vimeo': vimeo,
        'vine': vine,
        'vk': vk,
        'xiami': xiami,
        'yinyuetai': yinyuetai,
        'youku': youku,
        'youtu': youtube,
        'youtube': youtube,
        'khanacademy': khan,
        #TODO
    }
    if k in downloads:
        return downloads[k], url
    else:
        import http.client
        conn = http.client.HTTPConnection(video_host)
        conn.request("HEAD", video_url)
        res = conn.getresponse()
        location = res.getheader('location')
        if location is None:
            raise NotImplementedError(url)
        else:
            return url_to_module(location)

def any_download(url, output_dir='.', merge=True, info_only=False):
    m, url = url_to_module(url)
    m.download(url, output_dir=output_dir, merge=merge, info_only=info_only)

def any_download_playlist(url, output_dir='.', merge=True, info_only=False):
    m, url = url_to_module(url)
    m.download_playlist(url, output_dir=output_dir, merge=merge, info_only=info_only)

def main():
    script_main('you-get', any_download, any_download_playlist)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = ffmpeg
#!/usr/bin/env python

import os.path
import subprocess

def get_usable_ffmpeg(cmd):
    try:
        p = subprocess.Popen([cmd, '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        vers = str(out, 'utf-8').split('\n')[0].split(' ')
        assert (vers[0] == 'ffmpeg' and vers[2][0] > '0') or (vers[0] == 'avconv')
        return cmd
    except:
        return None

FFMPEG = get_usable_ffmpeg('ffmpeg') or get_usable_ffmpeg('avconv')

def has_ffmpeg_installed():
    return FFMPEG is not None

def ffmpeg_convert_ts_to_mkv(files, output = 'output.mkv'):
    for file in files:
        if os.path.isfile(file):
            params = [FFMPEG, '-i']
            params.append(file)
            params.append(output)
            subprocess.call(params)
    
    return

def ffmpeg_concat_mp4_to_mpg(files, output = 'output.mpg'):
    for file in files:
        if os.path.isfile(file):
            params = [FFMPEG, '-i']
            params.append(file)
            params.append(file + '.mpg')
            subprocess.call(params)
    
    inputs = [open(file + '.mpg', 'rb') for file in files]
    with open(output + '.mpg', 'wb') as o:
        for input in inputs:
            o.write(input.read())
    
    params = [FFMPEG, '-i']
    params.append(output + '.mpg')
    params += ['-vcodec', 'copy', '-acodec', 'copy']
    params.append(output)
    subprocess.call(params)
    
    for file in files:
        os.remove(file + '.mpg')
    os.remove(output + '.mpg')
    
    return

def ffmpeg_concat_ts_to_mkv(files, output = 'output.mkv'):
    params = [FFMPEG, '-isync', '-i']
    params.append('concat:')
    for file in files:
        if os.path.isfile(file):
            params[-1] += file + '|'
    params += ['-f', 'matroska', '-c', 'copy', output]
    
    try:
        if subprocess.call(params) == 0:
            return True
        else:
            return False
    except:
        return False

def ffmpeg_concat_flv_to_mp4(files, output = 'output.mp4'):
    for file in files:
        if os.path.isfile(file):
            params = [FFMPEG, '-i']
            params.append(file)
            params += ['-map', '0', '-c', 'copy', '-f', 'mpegts', '-bsf:v', 'h264_mp4toannexb']
            params.append(file + '.ts')
            
            subprocess.call(params)
    
    params = [FFMPEG, '-i']
    params.append('concat:')
    for file in files:
        f = file + '.ts'
        if os.path.isfile(f):
            params[-1] += f + '|'
    if FFMPEG == 'avconv':
        params += ['-c', 'copy', output]
    else:
        params += ['-c', 'copy', '-absf', 'aac_adtstoasc', output]
    
    if subprocess.call(params) == 0:
        for file in files:
            os.remove(file + '.ts')
        return True
    else:
        raise

def ffmpeg_concat_mp4_to_mp4(files, output = 'output.mp4'):
    for file in files:
        if os.path.isfile(file):
            params = [FFMPEG, '-i']
            params.append(file)
            params += ['-c', 'copy', '-f', 'mpegts', '-bsf:v', 'h264_mp4toannexb']
            params.append(file + '.ts')
            
            subprocess.call(params)
    
    params = [FFMPEG, '-i']
    params.append('concat:')
    for file in files:
        f = file + '.ts'
        if os.path.isfile(f):
            params[-1] += f + '|'
    if FFMPEG == 'avconv':
        params += ['-c', 'copy', output]
    else:
        params += ['-c', 'copy', '-absf', 'aac_adtstoasc', output]
    
    if subprocess.call(params) == 0:
        for file in files:
            os.remove(file + '.ts')
        return True
    else:
        raise

########NEW FILE########
__FILENAME__ = join_flv
#!/usr/bin/env python

import struct
from io import BytesIO

TAG_TYPE_METADATA = 18

##################################################
# AMF0
##################################################

AMF_TYPE_NUMBER = 0x00
AMF_TYPE_BOOLEAN = 0x01
AMF_TYPE_STRING = 0x02
AMF_TYPE_OBJECT = 0x03
AMF_TYPE_MOVIECLIP = 0x04
AMF_TYPE_NULL = 0x05
AMF_TYPE_UNDEFINED = 0x06
AMF_TYPE_REFERENCE = 0x07
AMF_TYPE_MIXED_ARRAY = 0x08
AMF_TYPE_END_OF_OBJECT = 0x09
AMF_TYPE_ARRAY = 0x0A
AMF_TYPE_DATE = 0x0B
AMF_TYPE_LONG_STRING = 0x0C
AMF_TYPE_UNSUPPORTED = 0x0D
AMF_TYPE_RECORDSET = 0x0E
AMF_TYPE_XML = 0x0F
AMF_TYPE_CLASS_OBJECT = 0x10
AMF_TYPE_AMF3_OBJECT = 0x11

class ECMAObject:
    def __init__(self, max_number):
        self.max_number = max_number
        self.data = []
        self.map = {}
    def put(self, k, v):
        self.data.append((k, v))
        self.map[k] = v
    def get(self, k):
        return self.map[k]
    def set(self, k, v):
        for i in range(len(self.data)):
            if self.data[i][0] == k:
                self.data[i] = (k, v)
                break
        else:
            raise KeyError(k)
        self.map[k] = v
    def keys(self):
        return self.map.keys()
    def __str__(self):
        return 'ECMAObject<' + repr(self.map) + '>'
    def __eq__(self, other):
        return self.max_number == other.max_number and self.data == other.data

def read_amf_number(stream):
    return struct.unpack('>d', stream.read(8))[0]

def read_amf_boolean(stream):
    b = read_byte(stream)
    assert b in (0, 1)
    return bool(b)

def read_amf_string(stream):
    xx = stream.read(2)
    if xx == b'':
        # dirty fix for the invalid Qiyi flv
        return None
    n = struct.unpack('>H', xx)[0]
    s = stream.read(n)
    assert len(s) == n
    return s.decode('utf-8')

def read_amf_object(stream):
    obj = {}
    while True:
        k = read_amf_string(stream)
        if not k:
            assert read_byte(stream) == AMF_TYPE_END_OF_OBJECT
            break
        v = read_amf(stream)
        obj[k] = v
    return obj

def read_amf_mixed_array(stream):
    max_number = read_uint(stream)
    mixed_results = ECMAObject(max_number)
    while True:
        k = read_amf_string(stream)
        if k is None:
            # dirty fix for the invalid Qiyi flv
            break
        if not k:
            assert read_byte(stream) == AMF_TYPE_END_OF_OBJECT
            break
        v = read_amf(stream)
        mixed_results.put(k, v)
    assert len(mixed_results.data) == max_number
    return mixed_results

def read_amf_array(stream):
    n = read_uint(stream)
    v = []
    for i in range(n):
        v.append(read_amf(stream))
    return v

amf_readers = {
    AMF_TYPE_NUMBER: read_amf_number,
    AMF_TYPE_BOOLEAN: read_amf_boolean,
    AMF_TYPE_STRING: read_amf_string,
    AMF_TYPE_OBJECT: read_amf_object,
    AMF_TYPE_MIXED_ARRAY: read_amf_mixed_array,
    AMF_TYPE_ARRAY: read_amf_array,
}

def read_amf(stream):
    return amf_readers[read_byte(stream)](stream)

def write_amf_number(stream, v):
    stream.write(struct.pack('>d', v))

def write_amf_boolean(stream, v):
    if v:
        stream.write(b'\x01')
    else:
        stream.write(b'\x00')

def write_amf_string(stream, s):
    s = s.encode('utf-8')
    stream.write(struct.pack('>H', len(s)))
    stream.write(s)

def write_amf_object(stream, o):
    for k in o:
        write_amf_string(stream, k)
        write_amf(stream, o[k])
    write_amf_string(stream, '')
    write_byte(stream, AMF_TYPE_END_OF_OBJECT)

def write_amf_mixed_array(stream, o):
    write_uint(stream, o.max_number)
    for k, v in o.data:
        write_amf_string(stream, k)
        write_amf(stream, v)
    write_amf_string(stream, '')
    write_byte(stream, AMF_TYPE_END_OF_OBJECT)

def write_amf_array(stream, o):
    write_uint(stream, len(o))
    for v in o:
        write_amf(stream, v)

amf_writers_tags = {
    float: AMF_TYPE_NUMBER,
    bool: AMF_TYPE_BOOLEAN,
    str: AMF_TYPE_STRING,
    dict: AMF_TYPE_OBJECT,
    ECMAObject: AMF_TYPE_MIXED_ARRAY,
    list: AMF_TYPE_ARRAY,
}

amf_writers = {
    AMF_TYPE_NUMBER: write_amf_number,
    AMF_TYPE_BOOLEAN: write_amf_boolean,
    AMF_TYPE_STRING: write_amf_string,
    AMF_TYPE_OBJECT: write_amf_object,
    AMF_TYPE_MIXED_ARRAY: write_amf_mixed_array,
    AMF_TYPE_ARRAY: write_amf_array,
}

def write_amf(stream, v):
    if isinstance(v, ECMAObject):
        tag = amf_writers_tags[ECMAObject]
    else:
        tag = amf_writers_tags[type(v)]
    write_byte(stream, tag)
    amf_writers[tag](stream, v)

##################################################
# FLV
##################################################

def read_int(stream):
    return struct.unpack('>i', stream.read(4))[0]

def read_uint(stream):
    return struct.unpack('>I', stream.read(4))[0]

def write_uint(stream, n):
    stream.write(struct.pack('>I', n))

def read_byte(stream):
    return ord(stream.read(1))

def write_byte(stream, b):
    stream.write(bytes([b]))

def read_unsigned_medium_int(stream):
    x1, x2, x3 = struct.unpack('BBB', stream.read(3))
    return (x1 << 16) | (x2 << 8) | x3

def read_tag(stream):
    # header size: 15 bytes
    header = stream.read(15)
    if len(header) == 4:
        return
    x = struct.unpack('>IBBBBBBBBBBB', header)
    previous_tag_size = x[0]
    data_type = x[1]
    body_size = (x[2] << 16) | (x[3] << 8) | x[4]
    assert body_size < 1024 * 1024 * 128, 'tag body size too big (> 128MB)'
    timestamp = (x[5] << 16) | (x[6] << 8) | x[7]
    timestamp += x[8] << 24
    assert x[9:] == (0, 0, 0)
    body = stream.read(body_size)
    return (data_type, timestamp, body_size, body, previous_tag_size)
    #previous_tag_size = read_uint(stream)
    #data_type = read_byte(stream)
    #body_size = read_unsigned_medium_int(stream)
    #assert body_size < 1024*1024*128, 'tag body size too big (> 128MB)'
    #timestamp = read_unsigned_medium_int(stream)
    #timestamp += read_byte(stream) << 24
    #assert read_unsigned_medium_int(stream) == 0
    #body = stream.read(body_size)
    #return (data_type, timestamp, body_size, body, previous_tag_size)

def write_tag(stream, tag):
    data_type, timestamp, body_size, body, previous_tag_size = tag
    write_uint(stream, previous_tag_size)
    write_byte(stream, data_type)
    write_byte(stream, body_size>>16 & 0xff)
    write_byte(stream, body_size>>8  & 0xff)
    write_byte(stream, body_size     & 0xff)
    write_byte(stream, timestamp>>16 & 0xff)
    write_byte(stream, timestamp>>8  & 0xff)
    write_byte(stream, timestamp     & 0xff)
    write_byte(stream, timestamp>>24 & 0xff)
    stream.write(b'\0\0\0')
    stream.write(body)

def read_flv_header(stream):
    assert stream.read(3) == b'FLV'
    header_version = read_byte(stream)
    assert header_version == 1
    type_flags = read_byte(stream)
    assert type_flags == 5
    data_offset = read_uint(stream)
    assert data_offset == 9

def write_flv_header(stream):
    stream.write(b'FLV')
    write_byte(stream, 1)
    write_byte(stream, 5)
    write_uint(stream, 9)

def read_meta_data(stream):
    meta_type = read_amf(stream)
    meta = read_amf(stream)
    return meta_type, meta

def read_meta_tag(tag):
    data_type, timestamp, body_size, body, previous_tag_size = tag
    assert data_type == TAG_TYPE_METADATA
    assert timestamp == 0
    assert previous_tag_size == 0
    return read_meta_data(BytesIO(body))

#def write_meta_data(stream, meta_type, meta_data):
#    assert isinstance(meta_type, basesting)
#    write_amf(meta_type)
#    write_amf(meta_data)

def write_meta_tag(stream, meta_type, meta_data):
    buffer = BytesIO()
    write_amf(buffer, meta_type)
    write_amf(buffer, meta_data)
    body = buffer.getvalue()
    write_tag(stream, (TAG_TYPE_METADATA, 0, len(body), body, 0))


##################################################
# main
##################################################

def guess_output(inputs):
    import os.path
    inputs = map(os.path.basename, inputs)
    n = min(map(len, inputs))
    for i in reversed(range(1, n)):
        if len(set(s[:i] for s in inputs)) == 1:
            return inputs[0][:i] + '.flv'
    return 'output.flv'

def concat_flv(flvs, output = None):
    assert flvs, 'no flv file found'
    import os.path
    if not output:
        output = guess_output(flvs)
    elif os.path.isdir(output):
        output = os.path.join(output, guess_output(flvs))
    
    print('Merging video parts...')
    ins = [open(flv, 'rb') for flv in flvs]
    for stream in ins:
        read_flv_header(stream)
    meta_tags = map(read_tag, ins)
    metas = list(map(read_meta_tag, meta_tags))
    meta_types, metas = zip(*metas)
    assert len(set(meta_types)) == 1
    meta_type = meta_types[0]
    
    # must merge fields: duration
    # TODO: check other meta info, update other meta info
    total_duration = sum(meta.get('duration') for meta in metas)
    meta_data = metas[0]
    meta_data.set('duration', total_duration)
    
    out = open(output, 'wb')
    write_flv_header(out)
    write_meta_tag(out, meta_type, meta_data)
    timestamp_start = 0
    for stream in ins:
        while True:
            tag = read_tag(stream)
            if tag:
                data_type, timestamp, body_size, body, previous_tag_size = tag
                timestamp += timestamp_start
                tag = data_type, timestamp, body_size, body, previous_tag_size
                write_tag(out, tag)
            else:
                break
        timestamp_start = timestamp
    write_uint(out, previous_tag_size)
    
    return output

def usage():
    print('Usage: [python3] join_flv.py --output TARGET.flv flv...')

def main():
    import sys, getopt
    try:
        opts, args = getopt.getopt(sys.argv[1:], "ho:", ["help", "output="])
    except getopt.GetoptError as err:
        usage()
        sys.exit(1)
    output = None
    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit()
        elif o in ("-o", "--output"):
            output = a
        else:
            usage()
            sys.exit(1)
    if not args:
        usage()
        sys.exit(1)
    
    concat_flv(args, output)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = join_mp4
#!/usr/bin/env python

# reference: c041828_ISO_IEC_14496-12_2005(E).pdf

##################################################
# reader and writer
##################################################

import struct
from io import BytesIO

def skip(stream, n):
    stream.seek(stream.tell() + n)

def skip_zeros(stream, n):
    assert stream.read(n) == b'\x00' * n

def read_int(stream):
    return struct.unpack('>i', stream.read(4))[0]

def read_uint(stream):
    return struct.unpack('>I', stream.read(4))[0]

def write_uint(stream, n):
    stream.write(struct.pack('>I', n))

def read_ushort(stream):
    return struct.unpack('>H', stream.read(2))[0]

def read_ulong(stream):
    return struct.unpack('>Q', stream.read(8))[0]

def read_byte(stream):
    return ord(stream.read(1))

def copy_stream(source, target, n):
    buffer_size = 1024 * 1024
    while n > 0:
        to_read = min(buffer_size, n)
        s = source.read(to_read)
        assert len(s) == to_read, 'no enough data'
        target.write(s)
        n -= to_read

class Atom:
    def __init__(self, type, size, body):
        assert len(type) == 4
        self.type = type
        self.size = size
        self.body = body
    def __str__(self):
        #return '<Atom(%s):%s>' % (self.type, repr(self.body))
        return '<Atom(%s):%s>' % (self.type, '')
    def __repr__(self):
        return str(self)
    def write1(self, stream):
        write_uint(stream, self.size)
        stream.write(self.type)
    def write(self, stream):
        assert type(self.body) == bytes, '%s: %s' % (self.type, type(self.body))
        assert self.size == 8 + len(self.body)
        self.write1(stream)
        stream.write(self.body)
    def calsize(self):
        return self.size

class CompositeAtom(Atom):
    def __init__(self, type, size, body):
        assert isinstance(body, list)
        Atom.__init__(self, type, size, body)
    def write(self, stream):
        assert type(self.body) == list
        self.write1(stream)
        for atom in self.body:
            atom.write(stream)
    def calsize(self):
        self.size = 8 + sum([atom.calsize() for atom in self.body])
        return self.size
    def get1(self, k):
        for a in self.body:
            if a.type == k:
                return a
        else:
            raise Exception('atom not found: ' + k)
    def get(self, *keys):
        atom = self
        for k in keys:
            atom = atom.get1(k)
        return atom
    def get_all(self, k):
        return list(filter(lambda x: x.type == k, self.body))

class VariableAtom(Atom):
    def __init__(self, type, size, body, variables):
        assert isinstance(body, bytes)
        Atom.__init__(self, type, size, body)
        self.variables = variables
    def write(self, stream):
        self.write1(stream)
        i = 0
        n = 0
        for name, offset, value in self.variables:
            stream.write(self.body[i:offset])
            write_uint(stream, value)
            n += offset - i + 4
            i = offset + 4
        stream.write(self.body[i:])
        n += len(self.body) - i
        assert n == len(self.body)
    def get(self, k):
        for v in self.variables:
            if v[0] == k:
                return v[2]
        else:
            raise Exception('field not found: ' + k)
    def set(self, k, v):
        for i in range(len(self.variables)):
            variable = self.variables[i]
            if variable[0] == k:
                self.variables[i] = (k, variable[1], v)
                break
        else:
            raise Exception('field not found: '+k)

def read_raw(stream, size, left, type):
    assert size == left + 8
    body = stream.read(left)
    return Atom(type, size, body)

def read_body_stream(stream, left):
    body = stream.read(left)
    assert len(body) == left
    return body, BytesIO(body)

def read_full_atom(stream):
    value = read_uint(stream)
    version = value >> 24
    flags = value & 0xffffff
    assert version == 0
    return value

def read_mvhd(stream, size, left, type):
    body, stream = read_body_stream(stream, left)
    value = read_full_atom(stream)
    left -= 4
    
    # new Date(movieTime * 1000 - 2082850791998L); 
    creation_time = read_uint(stream)
    modification_time = read_uint(stream)
    time_scale = read_uint(stream)
    duration = read_uint(stream)
    left -= 16
    
    qt_preferred_fate = read_uint(stream)
    qt_preferred_volume = read_ushort(stream)
    assert stream.read(10) == b'\x00' * 10
    qt_matrixA = read_uint(stream)
    qt_matrixB = read_uint(stream)
    qt_matrixU = read_uint(stream)
    qt_matrixC = read_uint(stream)
    qt_matrixD = read_uint(stream)
    qt_matrixV = read_uint(stream)
    qt_matrixX = read_uint(stream)
    qt_matrixY = read_uint(stream)
    qt_matrixW = read_uint(stream)
    qt_previewTime = read_uint(stream)
    qt_previewDuration = read_uint(stream)
    qt_posterTime = read_uint(stream)
    qt_selectionTime = read_uint(stream)
    qt_selectionDuration = read_uint(stream)
    qt_currentTime = read_uint(stream)
    nextTrackID = read_uint(stream)
    left -= 80
    assert left == 0
    return VariableAtom(b'mvhd', size, body, [('duration', 16, duration)])

def read_tkhd(stream, size, left, type):
    body, stream = read_body_stream(stream, left)
    value = read_full_atom(stream)
    left -= 4
    
    # new Date(movieTime * 1000 - 2082850791998L); 
    creation_time = read_uint(stream)
    modification_time = read_uint(stream)
    track_id = read_uint(stream)
    assert stream.read(4) == b'\x00' * 4
    duration = read_uint(stream)
    left -= 20
    
    assert stream.read(8) == b'\x00' * 8
    qt_layer = read_ushort(stream)
    qt_alternate_group = read_ushort(stream)
    qt_volume = read_ushort(stream)
    assert stream.read(2) == b'\x00\x00'
    qt_matrixA = read_uint(stream)
    qt_matrixB = read_uint(stream)
    qt_matrixU = read_uint(stream)
    qt_matrixC = read_uint(stream)
    qt_matrixD = read_uint(stream)
    qt_matrixV = read_uint(stream)
    qt_matrixX = read_uint(stream)
    qt_matrixY = read_uint(stream)
    qt_matrixW = read_uint(stream)
    qt_track_width = read_uint(stream)
    width = qt_track_width >> 16
    qt_track_height = read_uint(stream)
    height = qt_track_height >> 16
    left -= 60
    assert left == 0
    return VariableAtom(b'tkhd', size, body, [('duration', 20, duration)])

def read_mdhd(stream, size, left, type):
    body, stream = read_body_stream(stream, left)
    value = read_full_atom(stream)
    left -= 4
    
    # new Date(movieTime * 1000 - 2082850791998L); 
    creation_time = read_uint(stream)
    modification_time = read_uint(stream)
    time_scale = read_uint(stream)
    duration = read_uint(stream)
    left -= 16
    
    packed_language = read_ushort(stream)
    qt_quality = read_ushort(stream)
    left -= 4
    
    assert left == 0
    return VariableAtom(b'mdhd', size, body, [('duration', 16, duration)])

def read_hdlr(stream, size, left, type):
    body, stream = read_body_stream(stream, left)
    value = read_full_atom(stream)
    left -= 4
    
    qt_component_type = read_uint(stream)
    handler_type = read_uint(stream)
    qt_component_manufacturer = read_uint(stream)
    qt_component_flags = read_uint(stream)
    qt_component_flags_mask = read_uint(stream)
    left -= 20
    
    track_name = stream.read(left - 1)
    assert stream.read(1) == b'\x00'
    
    return Atom(b'hdlr', size, body)

def read_vmhd(stream, size, left, type):
    body, stream = read_body_stream(stream, left)
    value = read_full_atom(stream)
    left -= 4
    
    assert left == 8
    graphic_mode = read_ushort(stream)
    op_color_read = read_ushort(stream)
    op_color_green = read_ushort(stream)
    op_color_blue = read_ushort(stream)
    
    return Atom(b'vmhd', size, body)

def read_stsd(stream, size, left, type):
    value = read_full_atom(stream)
    left -= 4
    
    entry_count = read_uint(stream)
    left -= 4
    
    children = []
    for i in range(entry_count):
        atom = read_atom(stream)
        children.append(atom)
        left -= atom.size
    
    assert left == 0
    #return Atom('stsd', size, children)
    class stsd_atom(Atom):
        def __init__(self, type, size, body):
            Atom.__init__(self, type, size, body)
        def write(self, stream):
            self.write1(stream)
            write_uint(stream, self.body[0])
            write_uint(stream, len(self.body[1]))
            for atom in self.body[1]:
                atom.write(stream)
        def calsize(self):
            oldsize = self.size # TODO: remove
            self.size = 8 + 4 + 4 + sum([atom.calsize() for atom in self.body[1]])
            assert oldsize == self.size, '%s: %d, %d' % (self.type, oldsize, self.size) # TODO: remove
            return self.size
    return stsd_atom(b'stsd', size, (value, children))

def read_avc1(stream, size, left, type):
    body, stream = read_body_stream(stream, left)
    
    skip_zeros(stream, 6)
    data_reference_index = read_ushort(stream)
    skip_zeros(stream, 2)
    skip_zeros(stream, 2)
    skip_zeros(stream, 12)
    width = read_ushort(stream)
    height = read_ushort(stream)
    horizontal_rez = read_uint(stream) >> 16
    vertical_rez = read_uint(stream) >> 16
    assert stream.read(4) == b'\x00' * 4
    frame_count = read_ushort(stream)
    string_len = read_byte(stream)
    compressor_name = stream.read(31)
    depth = read_ushort(stream)
    assert stream.read(2) == b'\xff\xff'
    left -= 78
    
    child = read_atom(stream)
    assert child.type in (b'avcC', b'pasp'), 'if the sub atom is not avcC or pasp (actual %s), you should not cache raw body' % child.type
    left -= child.size
    stream.read(left) # XXX
    return Atom(b'avc1', size, body)

def read_avcC(stream, size, left, type):
    stream.read(left)
    return Atom(b'avcC', size, None)

def read_stts(stream, size, left, type):
    value = read_full_atom(stream)
    left -= 4
    
    entry_count = read_uint(stream)
    assert entry_count == 1
    left -= 4
    
    samples = []
    for i in range(entry_count):
            sample_count = read_uint(stream)
            sample_duration = read_uint(stream)
            samples.append((sample_count, sample_duration))
            left -= 8
    
    assert left == 0
    #return Atom('stts', size, None)
    class stts_atom(Atom):
        def __init__(self, type, size, body):
            Atom.__init__(self, type, size, body)
        def write(self, stream):
            self.write1(stream)
            write_uint(stream, self.body[0])
            write_uint(stream, len(self.body[1]))
            for sample_count, sample_duration in self.body[1]:
                write_uint(stream, sample_count)
                write_uint(stream, sample_duration)
        def calsize(self):
            oldsize = self.size # TODO: remove
            self.size = 8 + 4 + 4 + len(self.body[1]) * 8
            assert oldsize == self.size, '%s: %d, %d' % (self.type, oldsize, self.size) # TODO: remove
            return self.size
    return stts_atom(b'stts', size, (value, samples))

def read_stss(stream, size, left, type):
    value = read_full_atom(stream)
    left -= 4
    
    entry_count = read_uint(stream)
    left -= 4
    
    samples = []
    for i in range(entry_count):
            sample = read_uint(stream)
            samples.append(sample)
            left -= 4
    
    assert left == 0
    #return Atom('stss', size, None)
    class stss_atom(Atom):
        def __init__(self, type, size, body):
            Atom.__init__(self, type, size, body)
        def write(self, stream):
            self.write1(stream)
            write_uint(stream, self.body[0])
            write_uint(stream, len(self.body[1]))
            for sample in self.body[1]:
                write_uint(stream, sample)
        def calsize(self):
            self.size = 8 + 4 + 4 + len(self.body[1]) * 4
            return self.size
    return stss_atom(b'stss', size, (value, samples))

def read_stsc(stream, size, left, type):
    value = read_full_atom(stream)
    left -= 4
    
    entry_count = read_uint(stream)
    left -= 4
    
    chunks = []
    for i in range(entry_count):
        first_chunk = read_uint(stream)
        samples_per_chunk = read_uint(stream)
        sample_description_index = read_uint(stream)
        assert sample_description_index == 1 # what is it?
        chunks.append((first_chunk, samples_per_chunk, sample_description_index))
        left -= 12
    #chunks, samples = zip(*chunks)
    #total = 0
    #for c, s in zip(chunks[1:], samples):
    #	total += c*s
    #print 'total', total
    
    assert left == 0
    #return Atom('stsc', size, None)
    class stsc_atom(Atom):
        def __init__(self, type, size, body):
            Atom.__init__(self, type, size, body)
        def write(self, stream):
            self.write1(stream)
            write_uint(stream, self.body[0])
            write_uint(stream, len(self.body[1]))
            for first_chunk, samples_per_chunk, sample_description_index in self.body[1]:
                write_uint(stream, first_chunk)
                write_uint(stream, samples_per_chunk)
                write_uint(stream, sample_description_index)
        def calsize(self):
            self.size = 8 + 4 + 4 + len(self.body[1]) * 12
            return self.size
    return stsc_atom(b'stsc', size, (value, chunks))

def read_stsz(stream, size, left, type):
    value = read_full_atom(stream)
    left -= 4
    
    sample_size = read_uint(stream)
    sample_count = read_uint(stream)
    left -= 8
    
    assert sample_size == 0
    total = 0
    sizes = []
    if sample_size == 0:
        for i in range(sample_count):
            entry_size = read_uint(stream)
            sizes.append(entry_size)
            total += entry_size
            left -= 4
    
    assert left == 0
    #return Atom('stsz', size, None)
    class stsz_atom(Atom):
        def __init__(self, type, size, body):
            Atom.__init__(self, type, size, body)
        def write(self, stream):
            self.write1(stream)
            write_uint(stream, self.body[0])
            write_uint(stream, self.body[1])
            write_uint(stream, self.body[2])
            for entry_size in self.body[3]:
                write_uint(stream, entry_size)
        def calsize(self):
            self.size = 8 + 4 + 8 + len(self.body[3]) * 4
            return self.size
    return stsz_atom(b'stsz', size, (value, sample_size, sample_count, sizes))

def read_stco(stream, size, left, type):
    value = read_full_atom(stream)
    left -= 4
    
    entry_count = read_uint(stream)
    left -= 4
    
    offsets = []
    for i in range(entry_count):
        chunk_offset = read_uint(stream)
        offsets.append(chunk_offset)
        left -= 4
    
    assert left == 0
    #return Atom('stco', size, None)
    class stco_atom(Atom):
        def __init__(self, type, size, body):
            Atom.__init__(self, type, size, body)
        def write(self, stream):
            self.write1(stream)
            write_uint(stream, self.body[0])
            write_uint(stream, len(self.body[1]))
            for chunk_offset in self.body[1]:
                write_uint(stream, chunk_offset)
        def calsize(self):
            self.size = 8 + 4 + 4 + len(self.body[1]) * 4
            return self.size
    return stco_atom(b'stco', size, (value, offsets))

def read_ctts(stream, size, left, type):
    value = read_full_atom(stream)
    left -= 4
    
    entry_count = read_uint(stream)
    left -= 4
    
    samples = []
    for i in range(entry_count):
        sample_count = read_uint(stream)
        sample_offset = read_uint(stream)
        samples.append((sample_count, sample_offset))
        left -= 8
    
    assert left == 0
    class ctts_atom(Atom):
        def __init__(self, type, size, body):
            Atom.__init__(self, type, size, body)
        def write(self, stream):
            self.write1(stream)
            write_uint(stream, self.body[0])
            write_uint(stream, len(self.body[1]))
            for sample_count, sample_offset in self.body[1]:
                write_uint(stream, sample_count)
                write_uint(stream, sample_offset)
        def calsize(self):
            self.size = 8 + 4 + 4 + len(self.body[1]) * 8
            return self.size
    return ctts_atom(b'ctts', size, (value, samples))

def read_smhd(stream, size, left, type):
    body, stream = read_body_stream(stream, left)
    value = read_full_atom(stream)
    left -= 4
    
    balance = read_ushort(stream)
    assert stream.read(2) == b'\x00\x00'
    left -= 4
    
    assert left == 0
    return Atom(b'smhd', size, body)

def read_mp4a(stream, size, left, type):
    body, stream = read_body_stream(stream, left)
    
    assert stream.read(6) == b'\x00' * 6
    data_reference_index = read_ushort(stream)
    assert stream.read(8) == b'\x00' * 8
    channel_count = read_ushort(stream)
    sample_size = read_ushort(stream)
    assert stream.read(4) == b'\x00' * 4
    time_scale = read_ushort(stream)
    assert stream.read(2) == b'\x00' * 2
    left -= 28
    
    atom = read_atom(stream)
    assert atom.type == b'esds'
    left -= atom.size
    
    assert left == 0
    return Atom(b'mp4a', size, body)

def read_descriptor(stream):
    tag = read_byte(stream)
    raise NotImplementedError()

def read_esds(stream, size, left, type):
    value = read_uint(stream)
    version = value >> 24
    assert version == 0
    flags = value & 0xffffff
    left -= 4
    
    body = stream.read(left)
    return Atom(b'esds', size, None)

def read_composite_atom(stream, size, left, type):
    children = []
    while left > 0:
        atom = read_atom(stream)
        children.append(atom)
        left -= atom.size
    assert left == 0, left
    return CompositeAtom(type, size, children)

def read_mdat(stream, size, left, type):
    source_start = stream.tell()
    source_size = left
    skip(stream, left)
    #return Atom(type, size, None)
    #raise NotImplementedError()
    class mdat_atom(Atom):
        def __init__(self, type, size, body):
            Atom.__init__(self, type, size, body)
        def write(self, stream):
            self.write1(stream)
            self.write2(stream)
        def write2(self, stream):
            source, source_start, source_size = self.body
            original = source.tell()
            source.seek(source_start)
            copy_stream(source, stream, source_size)
        def calsize(self):
            return self.size
    return mdat_atom(b'mdat', size, (stream, source_start, source_size))

atom_readers = {
    b'mvhd': read_mvhd, # merge duration
    b'tkhd': read_tkhd, # merge duration
    b'mdhd': read_mdhd, # merge duration
    b'hdlr': read_hdlr, # nothing
    b'vmhd': read_vmhd, # nothing
    b'stsd': read_stsd, # nothing
    b'avc1': read_avc1, # nothing
    b'avcC': read_avcC, # nothing
    b'stts': read_stts, # sample_count, sample_duration
    b'stss': read_stss, # join indexes
    b'stsc': read_stsc, # merge # sample numbers
    b'stsz': read_stsz, # merge # samples
    b'stco': read_stco, # merge # chunk offsets
    b'ctts': read_ctts, # merge
    b'smhd': read_smhd, # nothing
    b'mp4a': read_mp4a, # nothing
    b'esds': read_esds, # noting
    
    b'ftyp': read_raw,
    b'yqoo': read_raw,
    b'moov': read_composite_atom,
    b'trak': read_composite_atom,
    b'mdia': read_composite_atom,
    b'minf': read_composite_atom,
    b'dinf': read_composite_atom,
    b'stbl': read_composite_atom,
    b'iods': read_raw,
    b'dref': read_raw,
    b'free': read_raw,
    b'edts': read_raw,
    b'pasp': read_raw,
    
    b'mdat': read_mdat,
}
#stsd sample descriptions (codec types, initialization etc.) 
#stts (decoding) time-to-sample  
#ctts (composition) time to sample 
#stsc sample-to-chunk, partial data-offset information 
#stsz sample sizes (framing) 
#stz2 compact sample sizes (framing) 
#stco chunk offset, partial data-offset information 
#co64 64-bit chunk offset 
#stss sync sample table (random access points) 
#stsh shadow sync sample table 
#padb sample padding bits 
#stdp sample degradation priority 
#sdtp independent and disposable samples 
#sbgp sample-to-group 
#sgpd sample group description 
#subs sub-sample information


def read_atom(stream):
    header = stream.read(8)
    if not header:
        return
    assert len(header) == 8
    n = 0
    size = struct.unpack('>I', header[:4])[0]
    assert size > 0
    n += 4
    type = header[4:8]
    n += 4
    assert type != b'uuid'
    if size == 1:
        size = read_ulong(stream)
        n += 8
    
    left = size - n
    if type in atom_readers:
        return atom_readers[type](stream, size, left, type)
    raise NotImplementedError('%s: %d' % (type, left))

def write_atom(stream, atom):
    atom.write(stream)

def parse_atoms(stream):
    atoms = []
    while True:
        atom = read_atom(stream)
        if atom:
            atoms.append(atom)
        else:
            break
    return atoms

def read_mp4(stream):
    atoms = parse_atoms(stream)
    moov = list(filter(lambda x: x.type == b'moov', atoms))
    mdat = list(filter(lambda x: x.type == b'mdat', atoms))
    assert len(moov) == 1
    assert len(mdat) == 1
    moov = moov[0]
    mdat = mdat[0]
    return atoms, moov, mdat

##################################################
# merge
##################################################

def merge_stts(samples_list):
    sample_list = []
    for samples in samples_list:
        assert len(samples) == 1
        sample_list.append(samples[0])
    counts, durations = zip(*sample_list)
    assert len(set(durations)) == 1, 'not all durations equal'
    return [(sum(counts), durations[0])]

def merge_stss(samples, sample_number_list):
    results = []
    start = 0
    for samples, sample_number_list in zip(samples, sample_number_list):
        results.extend(map(lambda x: start + x, samples))
        start += sample_number_list
    return results

def merge_stsc(chunks_list, total_chunk_number_list):
    results = []
    chunk_index = 1
    for chunks, total in zip(chunks_list, total_chunk_number_list):
        for i in range(len(chunks)):
            if i < len(chunks) - 1:
                chunk_number = chunks[i + 1][0] - chunks[i][0]
            else:
                chunk_number = total + 1 - chunks[i][0]
            sample_number = chunks[i][1]
            description = chunks[i][2]
            results.append((chunk_index, sample_number, description))
            chunk_index += chunk_number
    return results

def merge_stco(offsets_list, mdats):
    offset = 0
    results = []
    for offsets, mdat in zip(offsets_list, mdats):
        results.extend(offset + x - mdat.body[1] for x in offsets)
        offset += mdat.size - 8
    return results

def merge_stsz(sizes_list):
    return sum(sizes_list, [])

def merge_mdats(mdats):
    total_size = sum(x.size - 8 for x in mdats) + 8
    class multi_mdat_atom(Atom):
        def __init__(self, type, size, body):
            Atom.__init__(self, type, size, body)
        def write(self, stream):
            self.write1(stream)
            self.write2(stream)
        def write2(self, stream):
            for mdat in self.body:
                mdat.write2(stream)
        def calsize(self):
            return self.size
    return multi_mdat_atom(b'mdat', total_size, mdats)

def merge_moov(moovs, mdats):
    mvhd_duration = 0
    for x in moovs:
        mvhd_duration += x.get(b'mvhd').get('duration')
    tkhd_durations = [0, 0]
    mdhd_durations = [0, 0]
    for x in moovs:
        traks = x.get_all(b'trak')
        assert len(traks) == 2
        tkhd_durations[0] += traks[0].get(b'tkhd').get('duration')
        tkhd_durations[1] += traks[1].get(b'tkhd').get('duration')
        mdhd_durations[0] += traks[0].get(b'mdia', b'mdhd').get('duration')
        mdhd_durations[1] += traks[1].get(b'mdia', b'mdhd').get('duration')
    #mvhd_duration = min(mvhd_duration, tkhd_durations)
    
    trak0s = [x.get_all(b'trak')[0] for x in moovs]
    trak1s = [x.get_all(b'trak')[1] for x in moovs]
    
    stts0 = merge_stts(x.get(b'mdia', b'minf', b'stbl', b'stts').body[1] for x in trak0s)
    stts1 = merge_stts(x.get(b'mdia', b'minf', b'stbl', b'stts').body[1] for x in trak1s)
    
    stss = merge_stss((x.get(b'mdia', b'minf', b'stbl', b'stss').body[1] for x in trak0s), (len(x.get(b'mdia', b'minf', b'stbl', b'stsz').body[3]) for x in trak0s))
    
    stsc0 = merge_stsc((x.get(b'mdia', b'minf', b'stbl', b'stsc').body[1] for x in trak0s), (len(x.get(b'mdia', b'minf', b'stbl', b'stco').body[1]) for x in trak0s))
    stsc1 = merge_stsc((x.get(b'mdia', b'minf', b'stbl', b'stsc').body[1] for x in trak1s), (len(x.get(b'mdia', b'minf', b'stbl', b'stco').body[1]) for x in trak1s))
    
    stco0 = merge_stco((x.get(b'mdia', b'minf', b'stbl', b'stco').body[1] for x in trak0s), mdats)
    stco1 = merge_stco((x.get(b'mdia', b'minf', b'stbl', b'stco').body[1] for x in trak1s), mdats)
    
    stsz0 = merge_stsz((x.get(b'mdia', b'minf', b'stbl', b'stsz').body[3] for x in trak0s))
    stsz1 = merge_stsz((x.get(b'mdia', b'minf', b'stbl', b'stsz').body[3] for x in trak1s))
    
    ctts = sum((x.get(b'mdia', b'minf', b'stbl', b'ctts').body[1] for x in trak0s), [])
    
    moov = moovs[0]
    
    moov.get(b'mvhd').set('duration', mvhd_duration)
    trak0 = moov.get_all(b'trak')[0]
    trak1 = moov.get_all(b'trak')[1]
    trak0.get(b'tkhd').set('duration', tkhd_durations[0])
    trak1.get(b'tkhd').set('duration', tkhd_durations[1])
    trak0.get(b'mdia', b'mdhd').set('duration', mdhd_durations[0])
    trak1.get(b'mdia', b'mdhd').set('duration', mdhd_durations[1])
    
    stts_atom = trak0.get(b'mdia', b'minf', b'stbl', b'stts')
    stts_atom.body = stts_atom.body[0], stts0
    stts_atom = trak1.get(b'mdia', b'minf', b'stbl', b'stts')
    stts_atom.body = stts_atom.body[0], stts1
    
    stss_atom = trak0.get(b'mdia', b'minf', b'stbl', b'stss')
    stss_atom.body = stss_atom.body[0], stss
    
    stsc_atom = trak0.get(b'mdia', b'minf', b'stbl', b'stsc')
    stsc_atom.body = stsc_atom.body[0], stsc0
    stsc_atom = trak1.get(b'mdia', b'minf', b'stbl', b'stsc')
    stsc_atom.body = stsc_atom.body[0], stsc1
    
    stco_atom = trak0.get(b'mdia', b'minf', b'stbl', b'stco')
    stco_atom.body = stss_atom.body[0], stco0
    stco_atom = trak1.get(b'mdia', b'minf', b'stbl', b'stco')
    stco_atom.body = stss_atom.body[0], stco1
    
    stsz_atom = trak0.get(b'mdia', b'minf', b'stbl', b'stsz')
    stsz_atom.body = stsz_atom.body[0], stsz_atom.body[1], len(stsz0), stsz0
    stsz_atom = trak1.get(b'mdia', b'minf', b'stbl', b'stsz')
    stsz_atom.body = stsz_atom.body[0], stsz_atom.body[1], len(stsz1), stsz1
    
    ctts_atom = trak0.get(b'mdia', b'minf', b'stbl', b'ctts')
    ctts_atom.body = ctts_atom.body[0], ctts
    
    old_moov_size = moov.size
    new_moov_size = moov.calsize()
    new_mdat_start = mdats[0].body[1] + new_moov_size - old_moov_size
    stco0 = list(map(lambda x: x + new_mdat_start, stco0))
    stco1 = list(map(lambda x: x + new_mdat_start, stco1))
    stco_atom = trak0.get(b'mdia', b'minf', b'stbl', b'stco')
    stco_atom.body = stss_atom.body[0], stco0
    stco_atom = trak1.get(b'mdia', b'minf', b'stbl', b'stco')
    stco_atom.body = stss_atom.body[0], stco1
    
    return moov

def merge_mp4s(files, output):
    assert files
    ins = [open(mp4, 'rb') for mp4 in files]
    mp4s = list(map(read_mp4, ins))
    moovs = list(map(lambda x: x[1], mp4s))
    mdats = list(map(lambda x: x[2], mp4s))
    moov = merge_moov(moovs, mdats)
    mdat = merge_mdats(mdats)
    with open(output, 'wb') as output:
        for x in mp4s[0][0]:
            if x.type == b'moov':
                moov.write(output)
            elif x.type == b'mdat':
                mdat.write(output)
            else:
                x.write(output)

##################################################
# main
##################################################

# TODO: FIXME: duplicate of join_flv

def guess_output(inputs):
    import os.path
    inputs = map(os.path.basename, inputs)
    n = min(map(len, inputs))
    for i in reversed(range(1, n)):
        if len(set(s[:i] for s in inputs)) == 1:
            return inputs[0][:i] + '.mp4'
    return 'output.mp4'

def concat_mp4(mp4s, output = None):
    assert mp4s, 'no mp4 file found'
    import os.path
    if not output:
        output = guess_output(mp4s)
    elif os.path.isdir(output):
        output = os.path.join(output, guess_output(mp4s))
    
    print('Merging video parts...')
    merge_mp4s(mp4s, output)
    
    return output

def usage():
    print('Usage: [python3] join_mp4.py --output TARGET.mp4 mp4...')

def main():
    import sys, getopt
    try:
        opts, args = getopt.getopt(sys.argv[1:], "ho:", ["help", "output="])
    except getopt.GetoptError as err:
        usage()
        sys.exit(1)
    output = None
    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit()
        elif o in ("-o", "--output"):
            output = a
        else:
            usage()
            sys.exit(1)
    if not args:
        usage()
        sys.exit(1)
    
    concat_mp4(args, output)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = rtmpdump
#!/usr/bin/env python

import os.path
import subprocess

def get_usable_rtmpdump(cmd):
    try:
        p = subprocess.Popen([cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        return cmd
    except:
        return None

RTMPDUMP = get_usable_rtmpdump('rtmpdump')

def has_rtmpdump_installed():
    return RTMPDUMP is not None

def download_rtmpdump_stream(url, playpath, title, ext, output_dir='.'):
    filename = '%s.%s' % (title, ext)
    filepath = os.path.join(output_dir, filename)

    params = [RTMPDUMP, '-r']
    params.append(url)
    params.append('-y')
    params.append(playpath)
    params.append('-o')
    params.append(filepath)

    subprocess.call(params)
    return

def play_rtmpdump_stream(player, url, playpath):
    os.system("rtmpdump -r '%s' -y '%s' -o - | %s -" % (url, playpath, player))
    return

########NEW FILE########
__FILENAME__ = fs
#!/usr/bin/env python

import platform

def legitimize(text, os=platform.system()):
    """Converts a string to a valid filename.
    """

    # POSIX systems
    text = text.translate({
        0: None,
        ord('/'): '-',
    })

    if os == 'Windows':
        # Windows (non-POSIX namespace)
        text = text.translate({
            # Reserved in Windows VFAT and NTFS
            ord(':'): '-',
            ord('*'): '-',
            ord('?'): '-',
            ord('\\'): '-',
            ord('|'): '-',
            ord('\"'): '\'',
            # Reserved in Windows VFAT
            ord('+'): '-',
            ord('<'): '-',
            ord('>'): '-',
            ord('['): '(',
            ord(']'): ')',
        })
    else:
        # *nix
        if os == 'Darwin':
            # Mac OS HFS+
            text = text.translate({
                ord(':'): '-',
            })

        # Remove leading .
        if text.startswith("."):
            text = text[1:]

    text = text[:82] # Trim to 82 Unicode characters long
    return text

########NEW FILE########
__FILENAME__ = log
#!/usr/bin/env python

from ..version import __name__

import os, sys, subprocess

# Is terminal ANSI/VT100 compatible
if os.getenv('TERM') in (
        'xterm',
        'vt100',
        'linux',
        'eterm-color',
        'screen',
    ):
    has_colors = True
else:
    try:
        # Eshell
        ppid = os.getppid()
        has_colors = (subprocess.getoutput('ps -p %d -ocomm=' % ppid)
                      == 'emacs')
    except:
        has_colors = False

# ANSI/VT100 escape code
# http://en.wikipedia.org/wiki/ANSI_escape_code
colors = {
    'none': '',
    'reset': '\033[0m',

    'black': '\033[30m',
    'bold-black': '\033[30;1m',
    'dark-gray': '\033[90m',
    'bold-dark-gray': '\033[90;1m',

    'red': '\033[31m',
    'bold-red': '\033[31;1m',
    'light-red': '\033[91m',
    'bold-light-red': '\033[91;1m',

    'green': '\033[32m',
    'bold-green': '\033[32;1m',
    'light-green': '\033[92m',
    'bold-light-green': '\033[92;1m',

    'yellow': '\033[33m',
    'bold-yellow': '\033[33;1m',
    'light-yellow': '\033[93m',
    'bold-light-yellow': '\033[93;1m',

    'blue': '\033[34m',
    'bold-blue': '\033[34;1m',
    'light-blue': '\033[94m',
    'bold-light-blue': '\033[94;1m',

    'magenta': '\033[35m',
    'bold-magenta': '\033[35;1m',
    'light-magenta': '\033[95m',
    'bold-light-magenta': '\033[95;1m',

    'cyan': '\033[36m',
    'bold-cyan': '\033[36;1m',
    'light-cyan': '\033[96m',
    'bold-light-cyan': '\033[96;1m',

    'light-gray': '\033[37m',
    'bold-light-gray': '\033[37;1m',
    'white': '\033[97m',
    'bold-white': '\033[97;1m',
}

def underlined(text):
    """Returns an underlined text.
    """
    return "\33[4m%s\33[24m" % text if has_colors else text

def println(text, color=None, ostream=sys.stdout):
    """Prints a text line to stream.
    """
    if has_colors and color in colors:
        ostream.write("{0}{1}{2}\n".format(colors[color], text, colors['reset']))
    else:
        ostream.write("{0}\n".format(text))

def printlog(message, color=None, ostream=sys.stderr):
    """Prints a log message to stream.
    """
    if has_colors and color in colors:
        ostream.write("{0}{1}: {2}{3}\n".format(colors[color], __name__, message, colors['reset']))
    else:
        ostream.write("{0}: {1}\n".format(__name__, message))

def i(message, ostream=sys.stderr):
    """Sends an info log message.
    """
    printlog(message,
             None,
             ostream=ostream)

def d(message, ostream=sys.stderr):
    """Sends a debug log message.
    """
    printlog(message,
             'blue' if has_colors else None,
             ostream=ostream)

def w(message, ostream=sys.stderr):
    """Sends a warning log message.
    """
    printlog(message,
             'yellow' if has_colors else None,
             ostream=ostream)

def e(message, ostream=sys.stderr):
    """Sends an error log message.
    """
    printlog(message,
             'bold-yellow' if has_colors else None,
             ostream=ostream)

def wtf(message, ostream=sys.stderr):
    """What a Terrible Failure.
    """
    printlog(message,
             'bold-red' if has_colors else None,
             ostream=ostream)

########NEW FILE########
__FILENAME__ = sogou_proxy
#!/usr/bin/env python

# Original code from:
# http://xiaoxia.org/2011/03/26/using-python-to-write-a-local-sogou-proxy-server-procedures/

from . import log

from http.client import HTTPResponse
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from threading import Thread
import random, socket, struct, sys, time

def sogou_proxy_server(
    host=("0.0.0.0", 0),
    network_env='CERNET',
    ostream=sys.stderr):
    """Returns a Sogou proxy server object.
    """

    x_sogou_auth = '9CD285F1E7ADB0BD403C22AD1D545F40/30/853edc6d49ba4e27'
    proxy_host = 'h0.cnc.bj.ie.sogou.com'
    proxy_port = 80

    def sogou_hash(t, host):
        s = (t + host + 'SogouExplorerProxy').encode('ascii')
        code = len(s)
        dwords = int(len(s) / 4)
        rest = len(s) % 4
        v = struct.unpack(str(dwords) + 'i' + str(rest) + 's', s)
        for vv in v:
            if type(vv) != bytes:
                a = (vv & 0xFFFF)
                b = (vv >> 16)
                code += a
                code = code ^ (((code << 5) ^ b) << 0xb)
                # To avoid overflows
                code &= 0xffffffff
                code += code >> 0xb
        if rest == 3:
            code += s[len(s) - 2] * 256 + s[len(s) - 3]
            code = code ^ ((code ^ (s[len(s) - 1]) * 4) << 0x10)
            code &= 0xffffffff
            code += code >> 0xb
        elif rest == 2:
            code += (s[len(s) - 1]) * 256 + (s[len(s) - 2])
            code ^= code << 0xb
            code &= 0xffffffff
            code += code >> 0x11
        elif rest == 1:
            code += s[len(s) - 1]
            code ^= code << 0xa
            code &= 0xffffffff
            code += code >> 0x1
        code ^= code * 8
        code &= 0xffffffff
        code += code >> 5
        code ^= code << 4
        code = code & 0xffffffff
        code += code >> 0x11
        code ^= code << 0x19
        code = code & 0xffffffff
        code += code >> 6
        code = code & 0xffffffff
        return hex(code)[2:].rstrip('L').zfill(8)

    class Handler(BaseHTTPRequestHandler):
        _socket = None
        def do_proxy(self):
            try:
                if self._socket is None:
                    self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self._socket.connect((proxy_host, proxy_port))
                self._socket.send(self.requestline.encode('ascii') + b'\r\n')
                log.d(self.requestline, ostream)

                # Add Sogou Verification Tags
                self.headers['X-Sogou-Auth'] = x_sogou_auth
                t = hex(int(time.time()))[2:].rstrip('L').zfill(8)
                self.headers['X-Sogou-Tag'] = sogou_hash(t, self.headers['Host'])
                self.headers['X-Sogou-Timestamp'] = t
                self._socket.send(str(self.headers).encode('ascii') + b'\r\n')

                # Send POST data
                if self.command == 'POST':
                    self._socket.send(self.rfile.read(int(self.headers['Content-Length'])))
                response = HTTPResponse(self._socket, method=self.command)
                response.begin()

                # Response
                status = 'HTTP/1.1 %s %s' % (response.status, response.reason)
                self.wfile.write(status.encode('ascii') + b'\r\n')
                h = ''
                for hh, vv in response.getheaders():
                    if hh.upper() != 'TRANSFER-ENCODING':
                        h += hh + ': ' + vv + '\r\n'
                self.wfile.write(h.encode('ascii') + b'\r\n')
                while True:
                    response_data = response.read(8192)
                    if len(response_data) == 0:
                        break
                    self.wfile.write(response_data)

            except socket.error:
                log.e('Socket error for ' + self.requestline, ostream)

        def do_POST(self):
            self.do_proxy()

        def do_GET(self):
            self.do_proxy()

    class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
        pass

    # Server starts
    log.printlog('Sogou Proxy Mini-Server', color='bold-green', ostream=ostream)

    try:
        server = ThreadingHTTPServer(host, Handler)
    except Exception as ex:
        log.wtf("Socket error: %s" % ex, ostream)
        exit(1)
    host = server.server_address

    if network_env.upper() == 'CERNET':
        proxy_host = 'h%s.edu.bj.ie.sogou.com' % random.randint(0, 10)
    elif network_env.upper() == 'CTCNET':
        proxy_host = 'h%s.ctc.bj.ie.sogou.com' % random.randint(0, 3)
    elif network_env.upper() == 'CNCNET':
        proxy_host = 'h%s.cnc.bj.ie.sogou.com' % random.randint(0, 3)
    elif network_env.upper() == 'DXT':
        proxy_host = 'h%s.dxt.bj.ie.sogou.com' % random.randint(0, 10)
    else:
        proxy_host = 'h%s.edu.bj.ie.sogou.com' % random.randint(0, 10)

    log.i('Remote host: %s' % log.underlined(proxy_host), ostream)
    log.i('Proxy server running on %s' %
        log.underlined("%s:%s" % host), ostream)

    return server

########NEW FILE########
__FILENAME__ = strings
try:
  # py 3.4
  from html import unescape as unescape_html
except ImportError:
  import re
  from html.entities import entitydefs

  def unescape_html(string):
    '''HTML entity decode'''
    string = re.sub(r'&#[^;]+;', _sharp2uni, string)
    string = re.sub(r'&[^;]+;', lambda m: entitydefs[m.group(0)[1:-1]], string)
    return string

  def _sharp2uni(m):
    '''&#...; ==> unicode'''
    s = m.group(0)[2:].rstrip(';；')
    if s.startswith('x'):
      return chr(int('0'+s, 16))
    else:
      return chr(int(s))

from .fs import legitimize

def get_filename(htmlstring):
  return legitimize(unescape_html(htmlstring))

########NEW FILE########
__FILENAME__ = version
#!/usr/bin/env python
__all__ = ['__version__', '__date__']

__name__ = 'you-get'
__version__ = '0.3.29'
__date__ = '2014-05-29'

########NEW FILE########
__FILENAME__ = test
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

from you_get import *
from you_get.extractor.__main__ import url_to_module

def test_urls(urls):
    for url in urls:
        url_to_module(url)[0].download(url, info_only = True)

class YouGetTests(unittest.TestCase):

    def test_freesound(self):
        test_urls([
            "http://www.freesound.org/people/Corsica_S/sounds/184419/",
        ])

    def test_magisto(self):
        test_urls([
            "http://www.magisto.com/album/video/f3x9AAQORAkfDnIFDA",
        ])

    def test_mixcloud(self):
        test_urls([
            "http://www.mixcloud.com/beatbopz/beat-bopz-disco-mix/",
            "http://www.mixcloud.com/DJVadim/north-america-are-you-ready/",
        ])

    def test_ted(self):
        test_urls([
            "http://www.ted.com/talks/jennifer_lin_improvs_piano_magic.html",
            "http://www.ted.com/talks/derek_paravicini_and_adam_ockelford_in_the_key_of_genius.html",
        ])

    def test_vimeo(self):
        test_urls([
            "http://vimeo.com/56810854",
        ])

    def test_youtube(self):
        test_urls([
            "http://www.youtube.com/watch?v=pzKerr0JIPA",
            "http://youtu.be/pzKerr0JIPA",
            "http://www.youtube.com/attribution_link?u=/watch?v%3DldAKIzq7bvs%26feature%3Dshare"
        ])

########NEW FILE########
__FILENAME__ = test_common
#!/usr/bin/env python

import unittest

from you_get import *

class TestCommon(unittest.TestCase):
    
    def test_match1(self):
        self.assertEqual(match1('http://youtu.be/1234567890A', r'youtu.be/([^/]+)'), '1234567890A')
        self.assertEqual(match1('http://youtu.be/1234567890A', r'youtu.be/([^/]+)', r'youtu.(\w+)'), ['1234567890A', 'be'])

########NEW FILE########
__FILENAME__ = test_util
#!/usr/bin/env python

import unittest

from you_get.util import *

class TestUtil(unittest.TestCase):
    def test_legitimize(self):
        self.assertEqual(legitimize("1*2", os="Linux"), "1*2")
        self.assertEqual(legitimize("1*2", os="Darwin"), "1*2")
        self.assertEqual(legitimize("1*2", os="Windows"), "1-2")

########NEW FILE########
