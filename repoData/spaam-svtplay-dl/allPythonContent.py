__FILENAME__ = error
# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-

from __future__ import absolute_import

class UIException(Exception):
    pass

########NEW FILE########
__FILENAME__ = hds
# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-
from __future__ import absolute_import
import sys
import base64
import re
import struct
import logging
import binascii

import xml.etree.ElementTree as ET

from svtplay_dl.output import progressbar, progress_stream, ETA
from svtplay_dl.utils import get_http_data, select_quality, is_py2_old, is_py2, is_py3
from svtplay_dl.error import UIException

log = logging.getLogger('svtplay_dl')

if is_py2:
    def bytes(string=None, encoding="ascii"):
        if string is None:
            return ""
        return string

    def _chr(temp):
        return temp

if is_py3:
    def _chr(temp):
        return chr(temp)

class HDSException(UIException):
    def __init__(self, url, message):
        self.url = url
        super(HDSException, self).__init__(message)


class LiveHDSException(HDSException):
    def __init__(self, url):
        super(LiveHDSException, self).__init__(
            url, "This is a live HDS stream, and they are not supported.")


def download_hds(options, url):
    data = get_http_data(url)
    streams = {}
    bootstrap = {}
    xml = ET.XML(data)

    if options.live and not options.force:
        raise LiveHDSException(url)

    if is_py2_old:
        bootstrapIter = xml.getiterator("{http://ns.adobe.com/f4m/1.0}bootstrapInfo")
        mediaIter = xml.getiterator("{http://ns.adobe.com/f4m/1.0}media")
    else:
        bootstrapIter = xml.iter("{http://ns.adobe.com/f4m/1.0}bootstrapInfo")
        mediaIter = xml.iter("{http://ns.adobe.com/f4m/1.0}media")

    for i in bootstrapIter:
        bootstrap[i.attrib["id"]] = i.text

    for i in mediaIter:
        streams[int(i.attrib["bitrate"])] = {"url": i.attrib["url"], "bootstrapInfoId": i.attrib["bootstrapInfoId"], "metadata": i.find("{http://ns.adobe.com/f4m/1.0}metadata").text}

    test = select_quality(options, streams)

    bootstrap = base64.b64decode(bootstrap[test["bootstrapInfoId"]])
    box = readboxtype(bootstrap, 0)
    antal = None
    if box[2] == b"abst":
        antal = readbox(bootstrap, box[0])

    baseurl = url[0:url.rfind("/")]
    i = 1

    if options.output != "-":
        extension = re.search(r"(\.[a-z0-9]+)$", options.output)
        if not extension:
            options.output = "%s.flv" % options.output
        log.info("Outfile: %s", options.output)
        file_d = open(options.output, "wb")
    else:
        file_d = sys.stdout

    metasize = struct.pack(">L", len(base64.b64decode(test["metadata"])))[1:]
    file_d.write(binascii.a2b_hex(b"464c560105000000090000000012"))
    file_d.write(metasize)
    file_d.write(binascii.a2b_hex(b"00000000000000"))
    file_d.write(base64.b64decode(test["metadata"]))
    file_d.write(binascii.a2b_hex(b"00000000"))
    total = antal[1]["total"]
    eta = ETA(total)
    while i <= total:
        url = "%s/%sSeg1-Frag%s" % (baseurl, test["url"], i)
        if not options.silent and options.output != "-":
            eta.update(i)
            progressbar(total, i, ''.join(["ETA: ", str(eta)]))
        data = get_http_data(url)
        number = decode_f4f(i, data)
        file_d.write(data[number:])
        i += 1

    if options.output != "-":
        file_d.close()
        progress_stream.write('\n')

def readbyte(data, pos):
    return struct.unpack("B", bytes(_chr(data[pos]), "ascii"))[0]

def read16(data, pos):
    endpos = pos + 2
    return struct.unpack(">H", data[pos:endpos])[0]

def read24(data, pos):
    end = pos + 3
    return struct.unpack(">L", "\x00" + data[pos:end])[0]

def read32(data, pos):
    end = pos + 4
    return struct.unpack(">i", data[pos:end])[0]

def read64(data, pos):
    end = pos + 8
    return struct.unpack(">Q", data[pos:end])[0]

def readstring(data, pos):
    length = 0
    while bytes(_chr(data[pos + length]), "ascii") != b"\x00":
        length += 1
    endpos = pos + length
    string = data[pos:endpos]
    pos += length + 1
    return pos, string

def readboxtype(data, pos):
    boxsize = read32(data, pos)
    tpos = pos + 4
    endpos = tpos + 4
    boxtype = data[tpos:endpos]
    if boxsize > 1:
        boxsize -= 8
        pos += 8
        return pos, boxsize, boxtype

# Note! A lot of variable assignments are commented out. These are
# accessible values that we currently don't use.
def readbox(data, pos):
    #version = readbyte(data, pos)
    pos += 1
    #flags = read24(data, pos)
    pos += 3
    #bootstrapversion = read32(data, pos)
    pos += 4
    #byte = readbyte(data, pos)
    pos += 1
    #profile = (byte & 0xC0) >> 6
    #live = (byte & 0x20) >> 5
    #update = (byte & 0x10) >> 4
    #timescale = read32(data, pos)
    pos += 4
    #currentmediatime = read64(data, pos)
    pos += 8
    #smptetimecodeoffset = read64(data, pos)
    pos += 8
    temp = readstring(data, pos)
    #movieidentifier = temp[1]
    pos = temp[0]
    serverentrycount = readbyte(data, pos)
    pos += 1
    serverentrytable = []
    i = 0
    while i < serverentrycount:
        temp = readstring(data, pos)
        serverentrytable.append(temp[1])
        pos = temp[0]
        i += 1
    qualityentrycount = readbyte(data, pos)
    pos += 1
    qualityentrytable = []
    i = 0
    while i < qualityentrycount:
        temp = readstring(data, pos)
        qualityentrytable.append(temp[1])
        pos = temp[0]
        i += 1

    tmp = readstring(data, pos)
    #drm = tmp[1]
    pos = tmp[0]
    tmp = readstring(data, pos)
    #metadata = tmp[1]
    pos = tmp[0]
    segmentruntable = readbyte(data, pos)
    pos += 1
    if segmentruntable > 0:
        tmp = readboxtype(data, pos)
        boxtype = tmp[2]
        boxsize = tmp[1]
        pos = tmp[0]
        if boxtype == b"asrt":
            antal = readasrtbox(data, pos)
            pos += boxsize
    fragRunTableCount = readbyte(data, pos)
    pos += 1
    i = 0
    while i < fragRunTableCount:
        tmp = readboxtype(data, pos)
        boxtype = tmp[2]
        boxsize = tmp[1]
        pos = tmp[0]
        if boxtype == b"afrt":
            readafrtbox(data, pos)
            pos += boxsize
        i += 1
    return antal

# Note! A lot of variable assignments are commented out. These are
# accessible values that we currently don't use.
def readafrtbox(data, pos):
    #version = readbyte(data, pos)
    pos += 1
    #flags = read24(data, pos)
    pos += 3
    #timescale = read32(data, pos)
    pos += 4
    qualityentry = readbyte(data, pos)
    pos += 1
    i = 0
    while i < qualityentry:
        temp = readstring(data, pos)
        #qualitysegmulti = temp[1]
        pos = temp[0]
        i += 1
    fragrunentrycount = read32(data, pos)
    pos += 4
    i = 0
    while i < fragrunentrycount:
        #firstfragment = read32(data, pos)
        pos += 4
        #timestamp = read64(data, pos)
        pos += 8
        #duration = read32(data, pos)
        pos += 4
        i += 1

# Note! A lot of variable assignments are commented out. These are
# accessible values that we currently don't use.
def readasrtbox(data, pos):
    #version = readbyte(data, pos)
    pos += 1
    #flags = read24(data, pos)
    pos += 3
    qualityentrycount = readbyte(data, pos)
    pos += 1
    qualitysegmentmodifers = []
    i = 0
    while i < qualityentrycount:
        temp = readstring(data, pos)
        qualitysegmentmodifers.append(temp[1])
        pos = temp[0]
        i += 1

    seqCount = read32(data, pos)
    pos += 4
    ret = {}
    i = 0

    while i < seqCount:
        firstseg = read32(data, pos)
        pos += 4
        fragPerSeg = read32(data, pos)
        pos += 4
        tmp = i + 1
        ret[tmp] = {"first": firstseg, "total": fragPerSeg}
        i += 1
    return ret

def decode_f4f(fragID, fragData):
    start = fragData.find(b"mdat") + 4
    if (fragID > 1):
        tagLen, = struct.unpack_from(">L", fragData, start)
        tagLen &= 0x00ffffff
        start  += tagLen + 11 + 4
    return start


########NEW FILE########
__FILENAME__ = hls
# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-
from __future__ import absolute_import
import sys
import os
import re

from svtplay_dl.utils import get_http_data, select_quality
from svtplay_dl.output import progressbar, progress_stream, ETA
from svtplay_dl.log import log
from svtplay_dl.utils.urllib import urlparse
from svtplay_dl.error import UIException

class HLSException(UIException):
    def __init__(self, url, message):
        self.url = url
        super(HLSException, self).__init__(message)


class LiveHLSException(HLSException):
    def __init__(self, url):
        super(LiveHLSException, self).__init__(
            url, "This is a live HLS stream, and they are not supported.")


def _get_full_url(url, srcurl):
    if url[:4] == 'http':
        return url

    urlp = urlparse(srcurl)

    # remove everything after last / in the path of the URL
    baseurl = re.sub(r'^([^\?]+)/[^/]*(\?.*)?$', r'\1', srcurl)
    returl = "%s/%s" % (baseurl, url)

    # Append optional query parameters
    if urlp.query:
        returl += "?%s" % urlp.query

    return returl

# needparse is a fulhack++ it will be removed.
def download_hls(options, url, needparse=True):
    if options.live and not options.force:
        raise LiveHLSException(url)

    if needparse:
        data = get_http_data(url)
        globaldata, files = parsem3u(data)
        streams = {}

        for i in files:
            streams[int(i[1]["BANDWIDTH"])] = i[0]

        test = select_quality(options, streams)
        url = _get_full_url(test, url)

    m3u8 = get_http_data(url)
    globaldata, files = parsem3u(m3u8)
    encrypted = False
    key = None
    try:
        keydata = globaldata["KEY"]
        encrypted = True
    except KeyError:
        pass

    if encrypted:
        try:
            from Crypto.Cipher import AES
        except ImportError:
            log.error("You need to install pycrypto to download encrypted HLS streams")
            sys.exit(2)

        match = re.search(r'URI="(https?://.*?)"', keydata)
        key = get_http_data(match.group(1))
        rand = os.urandom(16)
        decryptor = AES.new(key, AES.MODE_CBC, rand)
    if options.output != "-":
        extension = re.search(r"(\.[a-z0-9]+)$", options.output)
        if not extension:
            options.output = "%s.ts" % options.output
        log.info("Outfile: %s", options.output)
        file_d = open(options.output, "wb")
    else:
        file_d = sys.stdout

    n = 0
    eta = ETA(len(files))
    for i in files:
        item = _get_full_url(i[0], url)

        if not options.silent and options.output != "-":
            eta.increment()
            progressbar(len(files), n, ''.join(['ETA: ', str(eta)]))
            n += 1

        data = get_http_data(item)
        if encrypted:
            data = decryptor.decrypt(data)
        file_d.write(data)

    if options.output != "-":
        file_d.close()
        progress_stream.write('\n')

def parsem3u(data):
    if not data.startswith("#EXTM3U"):
        raise ValueError("Does not apprear to be a ext m3u file")

    files = []
    streaminfo = {}
    globdata = {}

    data = data.replace("\r", "\n")
    for l in data.split("\n")[1:]:
        if not l:
            continue
        if l.startswith("#EXT-X-STREAM-INF:"):
            #not a proper parser
            info = [x.strip().split("=", 1) for x in l[18:].split(",")]
            for i in range(0, len(info)):
                if info[i][0] == "BANDWIDTH":
                    streaminfo.update({info[i][0]: info[i][1]})
        elif l.startswith("#EXT-X-ENDLIST"):
            break
        elif l.startswith("#EXT-X-"):
            globdata.update(dict([l[7:].strip().split(":", 1)]))
        elif l.startswith("#EXTINF:"):
            dur, title = l[8:].strip().split(",", 1)
            streaminfo['duration'] = dur
            streaminfo['title'] = title
        elif l[0] == '#':
            pass
        else:
            files.append((l, streaminfo))
            streaminfo = {}

    return globdata, files


########NEW FILE########
__FILENAME__ = http
# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-
from __future__ import absolute_import
import sys
import time
import re

from svtplay_dl.output import progress # FIXME use progressbar() instead
from svtplay_dl.log import log
from svtplay_dl.utils.urllib import urlopen, Request, HTTPError

def download_http(options, url):
    """ Get the stream from HTTP """
    log.debug("Fetching %s", url)
    request = Request(url)
    request.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
    try:
        response = urlopen(request)
    except HTTPError as e:
        log.error("Something wrong with that url")
        log.error("Error code: %s", e.code)
        sys.exit(5)
    try:
        total_size = response.info()['Content-Length']
    except KeyError:
        total_size = 0
    total_size = int(total_size)
    bytes_so_far = 0
    if options.output != "-":
        extension = re.search(r"(\.[a-z0-9]+)$", url)
        if extension:
            options.output = options.output + extension.group(1)
        else:
            options.output = "%s.mp4" % options.output
        log.info("Outfile: %s", options.output)
        file_d = open(options.output, "wb")
    else:
        file_d = sys.stdout

    lastprogress = 0
    while 1:
        chunk = response.read(8192)
        bytes_so_far += len(chunk)

        if not chunk:
            break

        file_d.write(chunk)
        if options.output != "-":
            now = time.time()
            if lastprogress + 1 < now:
                lastprogress = now
                progress(bytes_so_far, total_size)

    if options.output != "-":
        file_d.close()


########NEW FILE########
__FILENAME__ = rtmp
# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-
from __future__ import absolute_import
import subprocess
import re
import shlex

from svtplay_dl.log import log
from svtplay_dl.utils import is_py2

def download_rtmp(options, url):
    """ Get the stream from RTMP """
    args = []
    if options.live:
        args.append("-v")

    if options.resume:
        args.append("-e")

    extension = re.search(r"(\.[a-z0-9]+)$", url)
    if options.output != "-":
        if not extension:
            options.output = "%s.flv" % options.output
        else:
            options.output = options.output + extension.group(1)
        log.info("Outfile: %s", options.output)
        args += ["-o", options.output]
    if options.silent or options.output == "-":
        args.append("-q")
    if options.other:
        if is_py2:
            args += shlex.split(options.other.encode("utf-8"))
        else:
            args += shlex.split(options.other)

    if options.verbose:
        args.append("-V")

    command = ["rtmpdump", "-r", url] + args
    log.debug("Running: %s", " ".join(command))
    try:
        subprocess.call(command)
    except OSError as e:
        log.error("Could not execute rtmpdump: " + e.strerror)


########NEW FILE########
__FILENAME__ = log
# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-
from __future__ import absolute_import
import sys
import logging

log = logging.getLogger('svtplay_dl')
progress_stream = sys.stderr

########NEW FILE########
__FILENAME__ = output
# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-
from __future__ import absolute_import
import sys
import time
from datetime import timedelta

progress_stream = sys.stderr

class ETA(object):
    """
    An ETA class, used to calculate how long it takes to process
    an arbitrary set of items. By initiating the object with the
    number of items and continuously updating with current
    progress, the class can calculate an estimation of how long
    time remains.
    """

    def __init__(self, end, start=0):
        """
        Parameters:
        end:   the end (or size, of start is 0)
        start: the starting position, defaults to 0
        """
        self.start = start
        self.end = end
        self.pos = start

        self.now = time.time()
        self.start_time = self.now

    def update(self, pos):
        """
        Set new absolute progress position.

        Parameters:
        pos: new absolute progress
        """
        self.pos = pos
        self.now = time.time()

    def increment(self, skip=1):
        """
        Like update, but set new pos relative to old pos.

        Parameters:
        skip: progress since last update (defaults to 1)
        """
        self.update(self.pos + skip)

    @property
    def left(self):
        """
        returns: How many item remains?
        """
        return self.end - self.pos

    def __str__(self):
        """
        returns: a time string of the format HH:MM:SS.
        """
        duration = self.now - self.start_time

        # Calculate how long it takes to process one item
        try:
            elm_time = duration / (self.end - self.left)
        except ZeroDivisionError:
            return "(unknown)"

        return str(timedelta(seconds=int(elm_time * self.left)))


def progress(byte, total, extra = ""):
    """ Print some info about how much we have downloaded """
    if total == 0:
        progresstr = "Downloaded %dkB bytes" % (byte >> 10)
        progress_stream.write(progresstr + '\r')
        return
    progressbar(total, byte, extra)

def progressbar(total, pos, msg=""):
    """
    Given a total and a progress position, output a progress bar
    to stderr. It is important to not output anything else while
    using this, as it relies soley on the behavior of carriage
    return (\\r).

    Can also take an optioal message to add after the
    progressbar. It must not contain newliens.

    The progress bar will look something like this:

    [099/500][=========...............................] ETA: 13:36:59

    Of course, the ETA part should be supplied be the calling
    function.
    """
    width = 50 # TODO hardcoded progressbar width
    rel_pos = int(float(pos)/total*width)
    bar = ''.join(["=" * rel_pos, "." * (width - rel_pos)])

    # Determine how many digits in total (base 10)
    digits_total = len(str(total))
    fmt_width = "%0" + str(digits_total) + "d"
    fmt = "\r[" + fmt_width + "/" + fmt_width + "][%s] %s"

    progress_stream.write(fmt % (pos, total, bar, msg))


########NEW FILE########
__FILENAME__ = aftonbladet
# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-
from __future__ import absolute_import
import sys
import re
import json

from svtplay_dl.service import Service
from svtplay_dl.utils import get_http_data, select_quality
from svtplay_dl.log import log
from svtplay_dl.fetcher.hls import download_hls

class Aftonbladet(Service):
    supported_domains = ['tv.aftonbladet.se']

    def get(self, options):
        data = self.get_urldata()
        match = re.search('data-aptomaId="([-0-9a-z]+)"', data)
        if not match:
            log.error("Can't find video info")
            sys.exit(2)
        videoId = match.group(1)
        match = re.search(r'data-isLive="(\w+)"', data)
        if not match:
            log.error("Can't find live info")
            sys.exit(2)
        if match.group(1) == "true":
            options.live = True
        if not options.live:
            dataurl = "http://aftonbladet-play-metadata.cdn.drvideo.aptoma.no/video/%s.json" % videoId
            data = get_http_data(dataurl)
            data = json.loads(data)
            videoId = data["videoId"]

        streamsurl = "http://aftonbladet-play-static-ext.cdn.drvideo.aptoma.no/actions/video/?id=%s&formats&callback=" % videoId
        streams = json.loads(get_http_data(streamsurl))
        hls = streams["formats"]["hls"]["level3"]["csmil"][0]
        address = hls["address"]
        path = hls["path"]

        streams = {}
        for i in hls["files"]:
            streams[int(i["bitrate"])] = i["filename"]

        filename = select_quality(options, streams)
        playlist = "http://%s/%s/%s/master.m3u8" % (address, path, filename)
        download_hls(options, playlist, False)

########NEW FILE########
__FILENAME__ = bambuser
# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-
from __future__ import absolute_import
import sys
import re
import json

from svtplay_dl.service import Service, OpenGraphThumbMixin
from svtplay_dl.utils import get_http_data
from svtplay_dl.log import log
from svtplay_dl.fetcher.rtmp import download_rtmp
from svtplay_dl.fetcher.http import download_http

class Bambuser(Service, OpenGraphThumbMixin):
    supported_domains = ["bambuser.com"]

    def get(self, options):
        match = re.search(r"v/(\d+)", self.url)
        if not match:
            log.error("Can't find video id in url")
            sys.exit(2)
        json_url = "http://player-c.api.bambuser.com/getVideo.json?api_key=005f64509e19a868399060af746a00aa&vid=%s" % match.group(1)
        data = get_http_data(json_url)
        info = json.loads(data)["result"]
        video = info["url"]
        if video[:4] == "rtmp":
            playpath = info["id"][len(info["id"])-36:]
            options.other = "-y %s" % playpath
            if info["type"] == "live":
                options.live = True
            download_rtmp(options, video)
        else:
            download_http(options, video)


########NEW FILE########
__FILENAME__ = dr
# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-
from __future__ import absolute_import
import re
import json
import sys

from svtplay_dl.service import Service, OpenGraphThumbMixin
from svtplay_dl.utils import get_http_data, select_quality
from svtplay_dl.fetcher.rtmp import download_rtmp
from svtplay_dl.fetcher.hls import download_hls
from svtplay_dl.log import log

class Dr(Service, OpenGraphThumbMixin):
    supported_domains = ['dr.dk']

    def get(self, options):
        data = self.get_urldata()
        match = re.search(r'resource:[ ]*"([^"]*)",', data)
        if match:
            resource_url = match.group(1)
            resource_data = get_http_data(resource_url)
            resource = json.loads(resource_data)
            tempresource = resource['Data'][0]['Assets']
            # To find the VideoResource, they have Images as well
            for resources in tempresource:
                if resources['Kind'] == 'VideoResource':
                    links = resources['Links']
                    break

            streams = {}
            for i in links:
                if options.hls:
                    if i["Target"] == "Ios":
                        stream = {}
                        stream["uri"] = i["Uri"]
                        streams[int(i["Bitrate"])] = stream
                else:
                    if i["Target"] == "Streaming":
                        stream = {}
                        stream["uri"] = i["Uri"]
                        streams[int(i["Bitrate"])] = stream

            if len(streams) == 1:
                test = streams[list(streams.keys())[0]]
            else:
                test = select_quality(options, streams)

            if options.hls:
                download_hls(options, test["uri"])
            else:
                options.other = "-y '%s'" % test["uri"].replace("rtmp://vod.dr.dk/cms/", "")
                rtmp = "rtmp://vod.dr.dk/cms/"
                download_rtmp(options, rtmp)
        else:
            match = re.search(r'resource="([^"]*)"', data)
            if not match:
                log.error("Cant find resource info for this video")
                sys.exit(2)
            resource_url = "http://www.dr.dk%s" % match.group(1)
            resource_data = get_http_data(resource_url)
            resource = json.loads(resource_data)
            streams = {}
            for stream in resource['links']:
                streams[stream['bitrateKbps']] = stream['uri']
            if len(streams) == 1:
                uri = streams[list(streams.keys())[0]]
            else:
                uri = select_quality(options, streams)

            options.other = "-v -y '" + uri.replace("rtmp://vod.dr.dk/cms/", "") + "'"
            rtmp = "rtmp://vod.dr.dk/cms/"
            download_rtmp(options, rtmp)

########NEW FILE########
__FILENAME__ = expressen
# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-
from __future__ import absolute_import
import re

from svtplay_dl.service import Service
from svtplay_dl.error import UIException
from svtplay_dl.log import log
from svtplay_dl.fetcher.hls import download_hls
from svtplay_dl.fetcher.http import download_http

class ExpressenException(UIException):
    pass

class Expressen(Service):
    supported_domains = ['expressen.se']
    expressen_div_id = 'ctl00_WebTvArticleContent_BaseVideoHolder_VideoPlaceHolder_Satellite_Satellite'

    def _get_video_source(self, vtype):
        match = re.search(
            '<source src="([^"]+)" type="%s" />' % vtype, self.get_urldata()
        )

        if not match:
            raise ExpressenException(
                "Could not find any videos of type %s" % vtype)

        return match.group(1)

    def _get_hls(self):
        return self._get_video_source("application/x-mpegURL")

    def _get_mp4(self):
        return self._get_video_source('video/mp4')

    def get(self, options):
        try:
            try:
                url = self._get_hls()
                download_hls(options, url)
            except ExpressenException as exc:
                # Lower res, but static mp4 file.
                log.debug(exc)
                url = self._get_mp4()
                download_http(options, url)
        except ExpressenException:
            log.error("Could not find any videos in '%s'", self.url)

########NEW FILE########
__FILENAME__ = hbo
# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-
from __future__ import absolute_import
import sys
import re
import xml.etree.ElementTree as ET

from svtplay_dl.utils.urllib import urlparse
from svtplay_dl.service import Service
from svtplay_dl.utils import get_http_data, select_quality, is_py2_old
from svtplay_dl.log import log
from svtplay_dl.fetcher.rtmp import download_rtmp

class Hbo(Service):
    supported_domains = ['hbo.com']

    def get(self, options):
        parse = urlparse(self.url)
        try:
            other = parse[5]
        except KeyError:
            log.error("Something wrong with that url")
            sys.exit(2)
        match = re.search("^/(.*).html", other)
        if not match:
            log.error("Cant find video file")
            sys.exit(2)
        url = "http://www.hbo.com/data/content/%s.xml" % match.group(1)
        data = get_http_data(url)
        xml = ET.XML(data)
        videoid = xml.find("content")[1].find("videoId").text
        url = "http://render.cdn.hbo.com/data/content/global/videos/data/%s.xml" % videoid
        data = get_http_data(url)
        xml = ET.XML(data)
        ss = xml.find("videos")
        if is_py2_old:
            sa = list(ss.getiterator("size"))
        else:
            sa = list(ss.iter("size"))
        streams = {}
        for i in sa:
            stream = {}
            stream["path"] = i.find("tv14").find("path").text
            streams[int(i.attrib["width"])] = stream

        test = select_quality(options, streams)

        download_rtmp(options, test["path"])


########NEW FILE########
__FILENAME__ = justin
# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-

# pylint has issues with urlparse: "some types could not be inferred"
# pylint: disable=E1103

from __future__ import absolute_import
import sys
import re
import json
import xml.etree.ElementTree as ET

from svtplay_dl.utils.urllib import urlparse, quote
from svtplay_dl.service import Service
from svtplay_dl.utils import get_http_data
from svtplay_dl.log import log
from svtplay_dl.fetcher.hls import download_hls
from svtplay_dl.fetcher.http import download_http

class JustinException(Exception):
    pass

class JustinUrlException(JustinException):
    """
    Used to indicate an invalid URL for a given media_type. E.g.:

      JustinUrlException('video', 'http://twitch.tv/example')
    """
    def __init__(self, media_type, url):
        super(JustinUrlException, self).__init__(
            "'%s' is not recognized as a %s URL" % (url, media_type)
        )


class Justin(Service):
    # Justin and Twitch uses language subdomains, e.g. en.www.twitch.tv. They
    # are usually two characters, but may have a country suffix as well (e.g.
    # zh-tw, zh-cn and pt-br.
    supported_domains_re = [
        r'^(?:(?:[a-z]{2}-)?[a-z]{2}\.)?(www\.)?twitch\.tv$',
        r'^(?:(?:[a-z]{2}-)?[a-z]{2}\.)?(www\.)?justin\.tv$']

    # TODO: verify that this will support Justin as well
    api_base_url = 'https://api.twitch.tv'
    hls_base_url = 'http://usher.justin.tv/api/channel/hls'

    def get(self, options):
        urlp = urlparse(self.url)
        success = False

        for jtv_video_type in [self._get_chapter, self._get_archive,
                               self._get_channel]:
            try:
                jtv_video_type(urlp, options)
                success = True
                break
            except JustinUrlException as e:
                log.debug(str(e))

        if not success:
            log.debug(str(e))
            log.error("This twitch/justin video type is unsupported")
            sys.exit(2)


    def _get_static_video(self, vid, options, vidtype):
        url = "http://api.justin.tv/api/broadcast/by_%s/%s.xml?onsite=true" % (
            vidtype, vid)
        data = get_http_data(url)
        if not data:
            return False

        xml = ET.XML(data)
        url = xml.find("archive").find("video_file_url").text

        download_http(options, url)


    def _get_archive(self, urlp, options):
        match = re.match(r'/\w+/b/(\d+)', urlp.path)
        if not match:
            raise JustinUrlException('video', urlp.geturl())

        self._get_static_video(match.group(1), options, 'archive')


    def _get_chapter(self, urlp, options):
        match = re.match(r'/\w+/c/(\d+)', urlp.path)
        if not match:
            raise JustinUrlException('video', urlp.geturl())

        self._get_static_video(match.group(1), options, 'chapter')


    def _get_access_token(self, channel):
        """
        Get a Twitch access token. It's a three element dict:

         * mobile_restricted
         * sig
         * token

        `sig` is a hexadecimal string, and `token` is a JSON blob, with
        information about access expiration. `mobile_restricted` is not
        important, but is a boolean.

        Both `sig` and `token` should be added to the HLS URI, and the
        token should, of course, be URI encoded.
        """
        return self._ajax_get('/api/channels/%s/access_token' % channel)


    def _ajax_get(self, method):
        url = "%s/%s" % (self.api_base_url, method)

        # Logic found in Twitch's global.js. Prepend /kraken/ to url
        # path unless the API method already is absolute.
        if method[0] != '/':
            method = '/kraken/%s' % method

        # There are references to a api_token in global.js; it's used
        # with the "Twitch-Api-Token" HTTP header. But it doesn't seem
        # to be necessary.
        payload = get_http_data(url, header={
            'Accept': 'application/vnd.twitchtv.v2+json'
        })
        return json.loads(payload)


    def _get_hls_url(self, channel):
        access = self._get_access_token(channel)

        query = "token=%s&sig=%s" % (quote(access['token']), access['sig'])
        return "%s/%s.m3u8?%s" % (self.hls_base_url, channel, query)


    def _get_channel(self, urlp, options):
        match = re.match(r'/(\w+)', urlp.path)

        if not match:
            raise JustinUrlException('channel', urlp.geturl())

        channel = match.group(1)
        hls_url = self._get_hls_url(channel)
        urlp = urlparse(hls_url)

        options.live = True
        if not options.output:
            options.output = channel

        download_hls(options, hls_url)

########NEW FILE########
__FILENAME__ = kanal5
# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-
from __future__ import absolute_import
import sys
import re
import json

from svtplay_dl.utils.urllib import CookieJar, Cookie
from svtplay_dl.service import Service
from svtplay_dl.utils import get_http_data, select_quality, subtitle_json
from svtplay_dl.log import log
from svtplay_dl.fetcher.rtmp import download_rtmp
from svtplay_dl.fetcher.hls import download_hls

class Kanal5(Service):
    supported_domains = ['kanal5play.se', 'kanal9play.se']

    def __init__(self, url):
        Service.__init__(self, url)
        self.cj = CookieJar()
        self.subtitle = None

    def get(self, options):
        match = re.search(r".*video/([0-9]+)", self.url)
        if not match:
            log.error("Can't find video file")
            sys.exit(2)

        video_id = match.group(1)
        if options.username and options.password:
            #bogus
            cc = Cookie(None, 'asdf', None, '80', '80', 'www.kanal5play.se', None, None, '/', None, False, False, 'TestCookie', None, None, None)
            self.cj.set_cookie(cc)
            #get session cookie
            data = get_http_data("http://www.kanal5play.se/", cookiejar=self.cj)
            authurl = "https://kanal5swe.appspot.com/api/user/login?callback=jQuery171029989&email=%s&password=%s&_=136250" % (options.username, options.password)
            data = get_http_data(authurl)
            match = re.search(r"({.*})\);", data)
            jsondata = json.loads(match.group(1))
            if jsondata["success"] == False:
                log.error(jsondata["message"])
                sys.exit(2)
            authToken = jsondata["userData"]["auth"]
            cc = Cookie(version=0, name='authToken',
                          value=authToken,
                          port=None, port_specified=False,
                          domain='www.kanal5play.se',
                          domain_specified=True,
                          domain_initial_dot=True, path='/',
                          path_specified=True, secure=False,
                          expires=None, discard=True, comment=None,
                          comment_url=None, rest={'HttpOnly': None})
            self.cj.set_cookie(cc)

        format_ = "FLASH"
        if options.hls:
            format_ = "IPHONE"
        url = "http://www.kanal5play.se/api/getVideo?format=%s&videoId=%s" % (format_, video_id)
        data = json.loads(get_http_data(url, cookiejar=self.cj))
        if not options.live:
            options.live = data["isLive"]
        if data["hasSubtitle"]:
            self.subtitle = "http://www.kanal5play.se/api/subtitles/%s" % video_id

        if options.subtitle and options.force_subtitle:
            return

        if options.hls:
            url = data["streams"][0]["source"]
            if data["streams"][0]["drmProtected"]:
                log.error("We cant download drm files for this site.")
                sys.exit(2)
            download_hls(options, url)
        else:
            streams = {}

            for i in data["streams"]:
                stream = {}
                if i["drmProtected"]:
                    log.error("We cant download drm files for this site.")
                    sys.exit(2)
                stream["source"] = i["source"]
                streams[int(i["bitrate"])] = stream

            steambaseurl = data["streamBaseUrl"]

            test = select_quality(options, streams)

            filename = test["source"]
            match = re.search(r"^(.*):", filename)
            options.other = "-W %s -y %s " % ("http://www.kanal5play.se/flash/K5StandardPlayer.swf", filename)
            download_rtmp(options, steambaseurl)

    def get_subtitle(self, options):
        if self.subtitle:
            data = get_http_data(self.subtitle, cookiejar=self.cj)
            subtitle_json(options, data)

########NEW FILE########
__FILENAME__ = lemonwhale
# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-
from __future__ import absolute_import
import sys
import re
import xml.etree.ElementTree as ET

from svtplay_dl.utils.urllib import unquote_plus
from svtplay_dl.service import Service
from svtplay_dl.utils import get_http_data
from svtplay_dl.log import log
from svtplay_dl.fetcher.http import download_http

class Lemonwhale(Service):
    supported_domains = ['svd.se']

    def get(self, options):
        vid = None
        data = self.get_urldata()
        match = re.search(r'video url-([^"]+)', data)
        if not match:
            match = re.search(r'embed.jsp\?id=([^&]+)&', data)
            if not match:
                log.error("Cant find video id")
                sys.exit(2)
            vid = match.group(1)
        if not vid:
            path = unquote_plus(match.group(1))
            data = get_http_data("http://www.svd.se%s" % path)
            match = re.search(r'embed.jsp\?id=([^&]+)&', data)
            if not match:
                log.error("Cant find video id2")
                sys.exit(2)
            vid = match.group(1)

        url = "http://amz.lwcdn.com/api/cache/VideoCache.jsp?id=%s" % vid
        data = get_http_data(url)
        xml = ET.XML(data)
        videofile = xml.find("{http://www.lemonwhale.com/xml11}VideoFile")
        mediafiles = videofile.find("{http://www.lemonwhale.com/xml11}MediaFiles")
        high = mediafiles.find("{http://www.lemonwhale.com/xml11}VideoURLHigh")
        if high.text:
            download_http(options, high.text)
        else:
            file = mediafiles.find("{http://www.lemonwhale.com/xml11}VideoURL").text
            download_http(options, file)
########NEW FILE########
__FILENAME__ = mtvservices
# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-
from __future__ import absolute_import
import sys
import re
import xml.etree.ElementTree as ET

from svtplay_dl.service import Service
from svtplay_dl.utils import get_http_data, select_quality, is_py2_old
from svtplay_dl.fetcher.http import download_http

from svtplay_dl.log import log

class Mtvservices(Service):
    supported_domains = ['colbertnation.com', 'thedailyshow.com']

    def get(self, options):
        match = re.search(r"mgid=\"(mgid.*[0-9]+)\" data-wi", self.get_urldata())
        if not match:
            log.error("Can't find video file")
            sys.exit(2)
        url = "http://media.mtvnservices.com/player/html5/mediagen/?uri=%s" % match.group(1)
        data = get_http_data(url)
        start = data.index("<?xml version=")
        data = data[start:]
        xml = ET.XML(data)
        ss = xml.find("video").find("item")
        if is_py2_old:
            sa = list(ss.getiterator("rendition"))
        else:
            sa = list(ss.iter("rendition"))
        streams = {}
        for i in sa:
            streams[int(i.attrib["height"])] = i.find("src").text
        if len(streams) == 0:
            log.error("Can't find video file: %s", ss.text)
            sys.exit(2)
        stream = select_quality(options, streams)
        temp = stream.index("gsp.comedystor")
        url = "http://mtvnmobile.vo.llnwd.net/kip0/_pxn=0+_pxK=18639+_pxE=mp4/44620/mtvnorigin/%s" % stream[temp:]
        download_http(options, url)

########NEW FILE########
__FILENAME__ = nrk
# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-
from __future__ import absolute_import
import re
import sys
import json

from svtplay_dl.service import Service, OpenGraphThumbMixin
from svtplay_dl.utils import get_http_data, subtitle_tt
from svtplay_dl.utils.urllib import urlparse
from svtplay_dl.fetcher.hds import download_hds
from svtplay_dl.fetcher.hls import download_hls
from svtplay_dl.log import log

class Nrk(Service, OpenGraphThumbMixin):
    supported_domains = ['nrk.no', 'tv.nrk.no']

    def get(self, options):
        data = self.get_urldata()
        match = re.search(r'data-media="(.*manifest.f4m)"', data)
        if match:
            manifest_url = match.group(1)
        else:
            match = re.search(r'data-video-id="(\d+)"', data)
            if match is None:
                log.error("Can't find video id.")
                sys.exit(2)
            vid = match.group(1)
            match = re.search(r"PS_VIDEO_API_URL : '([^']*)',", data)
            if match is None:
                log.error("Can't find server address with media info")
                sys.exit(2)
            dataurl = "%smediaelement/%s" % (match.group(1), vid)
            data = json.loads(get_http_data(dataurl))
            manifest_url = data["mediaUrl"]
            options.live = data["isLive"]
        if options.hls:
            manifest_url = manifest_url.replace("/z/", "/i/").replace("manifest.f4m", "master.m3u8")
            download_hls(options, manifest_url)
        else:
            manifest_url = "%s?hdcore=2.8.0&g=hejsan" % manifest_url
            download_hds(options, manifest_url)


    def get_subtitle(self, options):
        match = re.search("data-subtitlesurl = \"(/.*)\"", self.get_urldata())
        if match:
            parse = urlparse(self.url)
            subtitle = "%s://%s%s" % (parse.scheme, parse.netloc, match.group(1))
            data = get_http_data(subtitle)
            subtitle_tt(options, data)


########NEW FILE########
__FILENAME__ = oppetarkiv
# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-
from __future__ import absolute_import
import sys
import re

from svtplay_dl.utils import get_http_data
from svtplay_dl.service.svtplay import Svtplay
from svtplay_dl.log import log

class OppetArkiv(Svtplay):
    supported_domains = ['oppetarkiv.se']

    def find_all_episodes(self, options):
        page = 1
        match = re.search(r'"http://www.oppetarkiv.se/etikett/titel/([^"/]+)', self.get_urldata())
        if match is None:
            match = re.search(r'"http://www.oppetarkiv.se/etikett/titel/([^"/]+)', self.url)
            if match is None:
                log.error("Couldn't find title")
                sys.exit(2)
        program = match.group(1)
        more = True
        episodes = []
        while more:
            url = "http://www.oppetarkiv.se/etikett/titel/%s/?sida=%s&sort=tid_stigande&embed=true" % (program, page)
            data = get_http_data(url)
            visa = re.search(r'svtXColorDarkLightGrey', data)
            if not visa:
                more = False
            regex = re.compile(r'(http://www.oppetarkiv.se/video/[^"]+)')
            for match in regex.finditer(data):
                episodes.append(match.group(1))
            page += 1

        return episodes

########NEW FILE########
__FILENAME__ = picsearch
# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-
from __future__ import absolute_import
import re
import json
import sys

from svtplay_dl.service import Service, OpenGraphThumbMixin
from svtplay_dl.utils import get_http_data, select_quality
from svtplay_dl.fetcher.rtmp import download_rtmp
from svtplay_dl.log import log

class Picsearch(Service, OpenGraphThumbMixin):
    supported_domains = ['dn.se']

    def get(self, options):
        data = self.get_urldata()
        ajax_auth = re.search(r"picsearch_ajax_auth = '(\w+)'", data)
        if not ajax_auth:
            log.error("Cant find token for video")
            sys.exit(2)
        mediaid = re.search(r"mediaId = '([^']+)';", data)
        if not mediaid:
            mediaid = re.search(r'media-id="([^"]+)"', data)
            if not mediaid:
                log.error("Cant find media id")
                sys.exit(2)
        jsondata = get_http_data("http://csp.picsearch.com/rest?jsonp=&eventParam=1&auth=%s&method=embed&mediaid=%s" % (ajax_auth.group(1), mediaid.group(1)))
        jsondata = json.loads(jsondata)
        files = jsondata["media"]["playerconfig"]["playlist"][1]["bitrates"]
        server = jsondata["media"]["playerconfig"]["plugins"]["bwcheck"]["netConnectionUrl"]

        streams = {}
        for i in files:
            streams[int(i["height"])] = i["url"]

        path = select_quality(options, streams)

        options.other = "-y '%s'" % path
        download_rtmp(options, server)
########NEW FILE########
__FILENAME__ = qbrick
# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-
from __future__ import absolute_import
import sys
import re
import xml.etree.ElementTree as ET

from svtplay_dl.service import Service, OpenGraphThumbMixin
from svtplay_dl.utils import get_http_data, select_quality, is_py2_old
from svtplay_dl.utils.urllib import unquote_plus
from svtplay_dl.log import log
from svtplay_dl.fetcher.rtmp import download_rtmp

class Qbrick(Service, OpenGraphThumbMixin):
    supported_domains = ['di.se', 'sydsvenskan.se']

    def get(self, options):
        if re.findall(r"sydsvenskan.se", self.url):
            data = self.get_urldata()
            match = re.search(r"data-qbrick-mcid=\"([0-9A-F]+)\"", data)
            if not match:
                log.error("Can't find video file")
                sys.exit(2)
            mcid = match.group(1)
            host = "http://vms.api.qbrick.com/rest/v3/getsingleplayer/%s" % mcid
        elif re.findall(r"di.se", self.url):
            data = self.get_urldata()
            match = re.search("src=\"(http://qstream.*)\"></iframe", data)
            if not match:
                log.error("Can't find video info")
                sys.exit(2)
            data = get_http_data(match.group(1))
            match = re.search(r"data-qbrick-ccid=\"([0-9A-Z]+)\"", data)
            if not match:
                log.error("Can't find video file")
                sys.exit(2)
            host = "http://vms.api.qbrick.com/rest/v3/getplayer/%s" % match.group(1)
        elif re.findall(r"svd.se", self.url):
            match = re.search(r'video url-([^"]*)\"', self.get_urldata())
            if not match:
                log.error("Can't find video file")
                sys.exit(2)
            path = unquote_plus(match.group(1))
            data = get_http_data("http://www.svd.se%s" % path)
            match = re.search(r"mcid=([A-F0-9]+)\&width=", data)
            if not match:
                log.error("Can't find video file")
                sys.exit(2)
            host = "http://vms.api.qbrick.com/rest/v3/getsingleplayer/%s" % match.group(1)
        else:
            log.error("Can't find site")
            sys.exit(2)

        data = get_http_data(host)
        xml = ET.XML(data)
        try:
            url = xml.find("media").find("item").find("playlist").find("stream").find("format").find("substream").text
        except AttributeError:
            log.error("Can't find video file")
            sys.exit(2)
        live = xml.find("media").find("item").find("playlist").find("stream").attrib["isLive"]
        if live == "true":
            options.live = True
        data = get_http_data(url)
        xml = ET.XML(data)
        server = xml.find("head").find("meta").attrib["base"]
        streams = xml.find("body").find("switch")
        if is_py2_old:
            sa = list(streams.getiterator("video"))
        else:
            sa = list(streams.iter("video"))
        streams = {}
        for i in sa:
            streams[int(i.attrib["system-bitrate"])] = i.attrib["src"]

        path = select_quality(options, streams)

        options.other = "-y '%s'" % path
        download_rtmp(options, server)


########NEW FILE########
__FILENAME__ = radioplay
# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-
# pylint has issues with urlparse: "some types could not be inferred"
# pylint: disable=E1103

from __future__ import absolute_import
import sys
import re
import json

from svtplay_dl.utils.urllib import urlparse
from svtplay_dl.service import Service

from svtplay_dl.fetcher.rtmp import download_rtmp
from svtplay_dl.fetcher.hls import download_hls
from svtplay_dl.fetcher.http import download_http

from svtplay_dl.log import log

class Radioplay(Service):
    supported_domains = ['radioplay.se']

    def get(self, options):
        match = re.search(r"liveStationsRedundancy = ({.*});</script>", self.get_urldata())
        parse = urlparse(self.url)
        station = parse.path[1:]
        streams = None
        if match:
            data = json.loads(match.group(1))
            for i in data["stations"]:
                if station == i["name"].lower().replace(" ", ""):
                    streams = i["streams"]
                    break
        else:
            log.error("Can't find any streams.")
            sys.exit(2)
        if streams:
            if options.hls:
                try:
                    m3u8_url = streams["hls"]
                    download_hls(options, m3u8_url)
                except KeyError:
                    log.error("Can't find any streams.")
                    sys.exit(2)
            else:
                try:
                    rtmp = streams["rtmp"]
                    download_rtmp(options, rtmp)
                except KeyError:
                    mp3 = streams["mp3"]
                    download_http(options, mp3)

        else:
            log.error("Can't find any streams.")
            sys.exit(2)

########NEW FILE########
__FILENAME__ = ruv
# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-
from __future__ import absolute_import
import re

from svtplay_dl.service import Service
from svtplay_dl.utils import get_http_data
from svtplay_dl.fetcher.hls import download_hls

class Ruv(Service):
    supported_domains = ['ruv.is']

    def get(self, options):
        data = self.get_urldata()
        match = re.search(r'(http://load.cache.is/vodruv.*)"', data)
        js_url = match.group(1)
        js = get_http_data(js_url)
        tengipunktur = js.split('"')[1]
        match = re.search(r"http.*tengipunktur [+] '([:]1935.*)'", data)
        m3u8_url = "http://" + tengipunktur + match.group(1)
        download_hls(options, m3u8_url)


########NEW FILE########
__FILENAME__ = sr
# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-

# pylint has issues with urlparse: "some types could not be inferred"
# pylint: disable=E1103

from __future__ import absolute_import
import sys
import json
import re

from svtplay_dl.utils.urllib import quote_plus
from svtplay_dl.service import Service, OpenGraphThumbMixin
from svtplay_dl.utils import get_http_data, select_quality
from svtplay_dl.log import log
from svtplay_dl.fetcher.http import download_http

class Sr(Service, OpenGraphThumbMixin):
    supported_domains = ['sverigesradio.se']

    def get(self, options):
        match = re.search(r'href="(/sida/[\.\/=a-z0-9&;\?]+\d+)" aria-label', self.get_urldata())
        if not match:
            log.error("Can't find audio info")
            sys.exit(2)
        path = quote_plus(match.group(1))
        dataurl = "http://sverigesradio.se/sida/ajax/getplayerinfo?url=%s&isios=false&playertype=html5" % path
        data = get_http_data(dataurl)
        playerinfo = json.loads(data)["playerInfo"]
        streams = {}
        for i in playerinfo["AudioSources"]:
            url = i["Url"]
            if not url.startswith('http'):
                i = 'http:%s' % url
            streams[int(i["Quality"])] = url

        test = select_quality(options, streams)
        download_http(options, test)


########NEW FILE########
__FILENAME__ = svtplay
# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-
from __future__ import absolute_import
import sys
import re
import json
import xml.etree.ElementTree as ET

from svtplay_dl.service import Service, OpenGraphThumbMixin
from svtplay_dl.utils import get_http_data, select_quality, subtitle_wsrt
from svtplay_dl.utils.urllib import urlparse
from svtplay_dl.fetcher.hds import download_hds
from svtplay_dl.fetcher.hls import download_hls
from svtplay_dl.fetcher.rtmp import download_rtmp
from svtplay_dl.fetcher.http import download_http

from svtplay_dl.log import log

class Svtplay(Service, OpenGraphThumbMixin):
    supported_domains = ['svtplay.se', 'svt.se', 'beta.svtplay.se', 'svtflow.se']

    def __init__(self, url):
        Service.__init__(self, url)
        self.subtitle = None

    def get(self, options):
        if re.findall("svt.se", self.url):
            match = re.search(r"data-json-href=\"(.*)\"", self.get_urldata())
            if match:
                filename = match.group(1).replace("&amp;", "&").replace("&format=json", "")
                url = "http://www.svt.se%s" % filename
            else:
                log.error("Can't find video file")
                sys.exit(2)
        else:
            url = self.url

        pos = url.find("?")
        if pos < 0:
            dataurl = "%s?&output=json&format=json" % url
        else:
            dataurl = "%s&output=json&format=json" % url
        data = json.loads(get_http_data(dataurl))
        if "live" in data["video"]:
            options.live = data["video"]["live"]
        else:
            options.live = False

        if data["video"]["subtitleReferences"]:
            try:
                self.subtitle = data["video"]["subtitleReferences"][0]["url"]
            except KeyError:
                pass

        streams = {}
        streams2 = {} #hack..
        for i in data["video"]["videoReferences"]:
            parse = urlparse(i["url"])
            if options.hls and parse.path[len(parse.path)-4:] == "m3u8":
                stream = {}
                stream["url"] = i["url"]
                streams[int(i["bitrate"])] = stream
            elif not options.hls and parse.path[len(parse.path)-3:] == "f4m":
                stream = {}
                stream["url"] = i["url"]
                streams[int(i["bitrate"])] = stream
            elif not options.hls and parse.path[len(parse.path)-3:] != "f4m" and parse.path[len(parse.path)-4:] != "m3u8":
                stream = {}
                stream["url"] = i["url"]
                streams[int(i["bitrate"])] = stream
            if options.hls and parse.path[len(parse.path)-3:] == "f4m":
                stream = {}
                stream["url"] = i["url"]
                streams2[int(i["bitrate"])] = stream

        if len(streams) == 0 and options.hls:
            if len(streams) == 0:
                log.error("Can't find any streams.")
                sys.exit(2)
            test = streams2[0]
            test["url"] = test["url"].replace("/z/", "/i/").replace("manifest.f4m", "master.m3u8")
        elif len(streams) == 0:
            log.error("Can't find any streams.")
            sys.exit(2)
        elif len(streams) == 1:
            test = streams[list(streams.keys())[0]]
        else:
            test = select_quality(options, streams)

        if options.subtitle and options.force_subtitle:
            return

        parse = urlparse(test["url"])
        if parse.scheme == "rtmp":
            embedurl = "%s?type=embed" % url
            data = get_http_data(embedurl)
            match = re.search(r"value=\"(/(public)?(statiskt)?/swf(/video)?/svtplayer-[0-9\.a-f]+swf)\"", data)
            swf = "http://www.svtplay.se%s" % match.group(1)
            options.other = "-W %s" % swf
            download_rtmp(options, test["url"])
        elif options.hls:
            download_hls(options, test["url"])
        elif parse.path[len(parse.path)-3:] == "f4m":
            match = re.search(r"\/se\/secure\/", test["url"])
            if match:
                log.error("This stream is encrypted. Use --hls option")
                sys.exit(2)
            manifest = "%s?hdcore=2.8.0&g=hejsan" % test["url"]
            download_hds(options, manifest)
        else:
            download_http(options, test["url"])


    def get_subtitle(self, options):
        if self.subtitle:
            if options.output != "-":
                data = get_http_data(self.subtitle)
                subtitle_wsrt(options, data)


    def find_all_episodes(self, options):
        match = re.search(r'<link rel="alternate" type="application/rss\+xml" [^>]*href="([^"]+)"',
                          self.get_urldata())
        if match is None:
            log.error("Couldn't retrieve episode list")
            sys.exit(2)

        xml = ET.XML(get_http_data(match.group(1)))

        return sorted(x.text for x in xml.findall(".//item/link"))

########NEW FILE########
__FILENAME__ = expressen
#!/usr/bin/python
# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-

# The unittest framwork doesn't play nice with pylint:
#   pylint: disable-msg=C0103

from __future__ import absolute_import
import unittest
from svtplay_dl.service.tests import HandlesURLsTestMixin
from svtplay_dl.service.expressen import Expressen

class handlesTest(unittest.TestCase, HandlesURLsTestMixin):
    service = Expressen
    urls = {
        "ok": [
            "http://www.expressen.se/tv/nyheter/kungligt/se-nar-estelle-stjal-kungens-show/",
        ],
        "bad": [
            "http://www.oppetarkiv.se/video/1129844/jacobs-stege-ep1",
            "http://www.dn.se/nyheter/sverige/det-ar-en-dodsfalla"
        ]
    }

########NEW FILE########
__FILENAME__ = justin
#!/usr/bin/python
# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-

# The unittest framwork doesn't play nice with pylint:
#   pylint: disable-msg=C0103

from __future__ import absolute_import
import unittest
from svtplay_dl.service.tests import HandlesURLsTestMixin
from svtplay_dl.service.justin import Justin

class handlesTest(unittest.TestCase, HandlesURLsTestMixin):
    service = Justin
    urls = {
        'ok': [
            "http://twitch.tv/foo/c/123456",
            "http://www.twitch.tv/foo/c/123456",
            "http://en.www.twitch.tv/foo/c/123456",
            "http://en.twitch.tv/foo/c/123456",
            "http://pt-br.twitch.tv/foo/c/123456",
            "http://pt-br.www.twitch.tv/foo/c/123456"
        ],
        'bad': [
            "http://www.dn.se/nyheter/sverige/det-ar-en-dodsfalla",
            "http://pxt-br.www.twitch.tv/foo/c/123456",
            "http://pxt-bxr.www.twitch.tv/foo/c/123456",
            "http://p-r.www.twitch.tv/foo/c/123456",
            "http://pxx.www.twitch.tv/foo/c/123456",
            "http://en.wwww.twitch.tv/foo/c/123456"
        ]
    }

########NEW FILE########
__FILENAME__ = oppetarkiv
#!/usr/bin/python
# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-

# The unittest framwork doesn't play nice with pylint:
#   pylint: disable-msg=C0103

from __future__ import absolute_import
import unittest
from svtplay_dl.service.tests import HandlesURLsTestMixin
from svtplay_dl.service.oppetarkiv import OppetArkiv

class handlesTest(unittest.TestCase, HandlesURLsTestMixin):
    service = OppetArkiv
    urls = {
        'ok': [
            "http://www.oppetarkiv.se/video/1129844/jacobs-stege-avsnitt-1-av-1"
        ],
        'bad': [
            "http://www.svtplay.se/video/1090393/del-9"
        ]
    }


########NEW FILE########
__FILENAME__ = service
#!/usr/bin/python
# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-

# The unittest framwork doesn't play nice with pylint:
#   pylint: disable-msg=C0103

from __future__ import absolute_import
import unittest
import mock
from svtplay_dl.service import Service

class MockService(Service):
    supported_domains = ['example.com', 'example.net']

class ServiceTest(unittest.TestCase):
    def test_supports(self):
        self.assertTrue(MockService.handles('http://example.com/video.swf?id=1'))
        self.assertTrue(MockService.handles('http://example.net/video.swf?id=1'))
        self.assertTrue(MockService.handles('http://www.example.com/video.swf?id=1'))
        self.assertTrue(MockService.handles('http://www.example.net/video.swf?id=1'))

########NEW FILE########
__FILENAME__ = svtplay
#!/usr/bin/python
# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-

# The unittest framwork doesn't play nice with pylint:
#   pylint: disable-msg=C0103

from __future__ import absolute_import
import unittest
from svtplay_dl.service.tests import HandlesURLsTestMixin
from svtplay_dl.service.svtplay import Svtplay

class handlesTest(unittest.TestCase, HandlesURLsTestMixin):
    service = Svtplay
    urls = {
        'ok': [
            "http://www.svtplay.se/video/1090393/del-9",
            "http://www.svt.se/nyheter/sverige/det-ar-en-dodsfalla"
        ],
        'bad': [
            "http://www.oppetarkiv.se/video/1129844/jacobs-stege-ep1",
            "http://www.dn.se/nyheter/sverige/det-ar-en-dodsfalla"
        ]
    }

########NEW FILE########
__FILENAME__ = tv4play
# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-
from __future__ import absolute_import
import sys
import re
import xml.etree.ElementTree as ET
import json

from svtplay_dl.utils.urllib import urlparse, parse_qs, quote_plus
from svtplay_dl.service import Service, OpenGraphThumbMixin
from svtplay_dl.utils import get_http_data, select_quality, subtitle_smi, is_py2_old
from svtplay_dl.log import log
from svtplay_dl.fetcher.rtmp import download_rtmp
from svtplay_dl.fetcher.hds import download_hds

class Tv4play(Service, OpenGraphThumbMixin):
    supported_domains = ['tv4play.se', 'tv4.se']

    def __init__(self, url):
        Service.__init__(self, url)
        self.subtitle = None

    def get(self, options):
        parse = urlparse(self.url)
        if "tv4play.se" in self.url:
            try:
                vid = parse_qs(parse[4])["video_id"][0]
            except KeyError:
                log.error("Can't find video file")
                sys.exit(2)
        else:
            match = re.search(r"-(\d+)$", self.url)
            if match:
                vid = match.group(1)
            else:
                match = re.search(r"\"vid\":\"(\d+)\",", self.get_urldata())
                if match:
                    vid = match.group(1)
                else:
                    log.error("Can't find video file")
                    sys.exit(2)

        url = "http://premium.tv4play.se/api/web/asset/%s/play" % vid
        data = get_http_data(url)
        xml = ET.XML(data)
        ss = xml.find("items")
        if is_py2_old:
            sa = list(ss.getiterator("item"))
        else:
            sa = list(ss.iter("item"))

        if xml.find("live").text:
            if xml.find("live").text != "false":
                options.live = True

        streams = {}

        for i in sa:
            if i.find("mediaFormat").text == "mp4":
                stream = {}
                stream["uri"] = i.find("base").text
                stream["path"] = i.find("url").text
                streams[int(i.find("bitrate").text)] = stream
            elif i.find("mediaFormat").text == "smi":
                self.subtitle = i.find("url").text

        if len(streams) == 0:
            log.error("Can't find any streams")
            sys.exit(2)
        elif len(streams) == 1:
            test = streams[list(streams.keys())[0]]
        else:
            test = select_quality(options, streams)

        ## This is how we construct an swf uri, if we'll ever need one
        swf = "http://www.tv4play.se/flash/tv4playflashlets.swf"
        options.other = "-W %s -y %s" % (swf, test["path"])

        if options.subtitle and options.force_subtitle:
            return

        if test["uri"][0:4] == "rtmp":
            download_rtmp(options, test["uri"])
        elif test["uri"][len(test["uri"])-3:len(test["uri"])] == "f4m":
            match = re.search(r"\/se\/secure\/", test["uri"])
            if match:
                log.error("This stream is encrypted. Use --hls option")
                sys.exit(2)
            manifest = "%s?hdcore=2.8.0&g=hejsan" % test["path"]
            download_hds(options, manifest)


    def get_subtitle(self, options):
        if self.subtitle:
            data = get_http_data(self.subtitle)
            subtitle_smi(options, data)

    def find_all_episodes(self, options):
        parse =  urlparse(self.url)
        show = quote_plus(parse.path[parse.path.find("/", 1)+1:])
        data = get_http_data("http://webapi.tv4play.se/play/video_assets?type=episode&is_live=false&platform=web&node_nids=%s&per_page=99999" % show)
        jsondata = json.loads(data)
        episodes = []
        for i in jsondata["results"]:
            try:
                days = int(i["availability"]["availability_group_free"])
            except ValueError:
                days = 999
            if  days > 0:
                id = i["id"]
                url = "http://www.tv4play.se/program/%s?video_id=%s" % (show, id)
                episodes.append(url)
        return sorted(episodes)
########NEW FILE########
__FILENAME__ = urplay
# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-
from __future__ import absolute_import
import re
import json
import sys
import xml.etree.ElementTree as ET

from svtplay_dl.service import Service, OpenGraphThumbMixin
from svtplay_dl.utils import get_http_data, subtitle_tt
from svtplay_dl.fetcher.rtmp import download_rtmp
from svtplay_dl.fetcher.hls import download_hls
from svtplay_dl.log import log

class Urplay(Service, OpenGraphThumbMixin):
    supported_domains = ['urplay.se', 'ur.se']

    def __init__(self, url):
        Service.__init__(self, url)
        self.subtitle = None

    def get(self, options):
        match = re.search(r"urPlayer.init\((.*)\);", self.get_urldata())
        if not match:
            log.error("Can't find json info")
            sys.exit(2)
        data = match.group(1)
        jsondata = json.loads(data)
        self.subtitle = jsondata["subtitles"].split(",")[0]
        basedomain = jsondata["streaming_config"]["streamer"]["redirect"]
        http = "http://%s/%s" % (basedomain, jsondata["file_html5"])
        hd = None
        if len(jsondata["file_html5_hd"]) > 0:
            http_hd = "http://%s/%s" % (basedomain, jsondata["file_html5_hd"])
            hls_hd = "%s%s" % (http_hd, jsondata["streaming_config"]["http_streaming"]["hls_file"])
            tmp = jsondata["file_html5_hd"]
            match = re.search(".*(mp[34]:.*$)", tmp)
            path_hd = match.group(1)
            hd = True
        #hds = "%s%s" % (http, jsondata["streaming_config"]["http_streaming"]["hds_file"])
        hls = "%s%s" % (http, jsondata["streaming_config"]["http_streaming"]["hls_file"])
        rtmp = "rtmp://%s/%s" % (basedomain, jsondata["streaming_config"]["rtmp"]["application"])
        path = "mp%s:%s" % (jsondata["file_flash"][-1], jsondata["file_flash"])
        available = {"sd":{"hls":{"http":http, "playlist":hls}, "rtmp":{"server":rtmp, "path":path}}}
        if hd:
            available.update({"hd":{"hls":{"http":http_hd, "playlist":hls_hd}, "rtmp":{"server":rtmp, "path":path_hd}}})

        if options.quality:
            try:
                selected = available[options.quality]
            except KeyError:
                log.error("Can't find that quality. (Try one of: %s)",
                          ", ".join([str(elm) for elm in available]))
                sys.exit(4)
        else:
            try:
                selected = self.select_highest_quality(available)
            except KeyError:
                log.error("Can't find any streams.")
                sys.exit(4)

        options.other = "-v -a %s -y %s" % (jsondata["streaming_config"]["rtmp"]["application"], selected["rtmp"]["path"])

        if options.subtitle and options.force_subtitle:
            return

        if options.hls:
            download_hls(options, selected["hls"]["playlist"])
        else:
            download_rtmp(options, selected["rtmp"]["server"])

    def select_highest_quality(self, available):
        if 'hd' in available:
            return available["hd"]
        elif 'sd' in available:
            return available["sd"]
        else:
            raise KeyError()


    def get_subtitle(self, options):
        if self.subtitle:
            data = get_http_data(self.subtitle)
            subtitle_tt(options, data)

    def find_all_episodes(self, options):
        match = re.search(r'<link rel="alternate" type="application/rss\+xml" [^>]*href="([^"]+)"',
                  self.get_urldata())
        if match is None:
            log.error("Couldn't retrieve episode list")
            sys.exit(2)
        url = "http://urplay.se%s" % match.group(1).replace("&amp;", "&")
        xml = ET.XML(get_http_data(url))

        return sorted(x.text for x in xml.findall(".//item/link"))
########NEW FILE########
__FILENAME__ = viaplay
# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-

# pylint has issues with urlparse: "some types could not be inferred"
# pylint: disable=E1103

from __future__ import absolute_import
import sys
import re
import xml.etree.ElementTree as ET
import json

from svtplay_dl.utils.urllib import urlparse
from svtplay_dl.service import Service, OpenGraphThumbMixin
from svtplay_dl.utils import get_http_data, subtitle_sami
from svtplay_dl.log import log
from svtplay_dl.fetcher.rtmp import download_rtmp
from svtplay_dl.fetcher.hds import download_hds

class Viaplay(Service, OpenGraphThumbMixin):
    supported_domains = [
        'tv3play.se', 'tv6play.se', 'tv8play.se', 'tv10play.se',
        'tv3play.no', 'tv3play.dk', 'tv6play.no', 'viasat4play.no',
        'tv3play.ee', 'tv3play.lv', 'tv3play.lt', 'tvplay.lv']

    def __init__(self, url):
        Service.__init__(self, url)
        self.subtitle = None


    def _get_video_id(self):
        """
        Extract video id. It will try to avoid making an HTTP request
        if it can find the ID in the URL, but otherwise it will try
        to scrape it from the HTML document. Returns None in case it's
        unable to extract the ID at all.
        """
        parse = urlparse(self.url)
        match = re.search(r'\/(\d+)/?', parse.path)
        if match:
            return match.group(1)

        html_data = self.get_urldata()
        match = re.search(r'data-link="[^"]+/([0-9]+)"', html_data)
        if match:
            return match.group(1)

        return None


    def get(self, options):
        vid = self._get_video_id()
        if vid is None:
            log.error("Cant find video file")
            sys.exit(2)

        url = "http://viastream.viasat.tv/PlayProduct/%s" % vid
        options.other = ""
        data = get_http_data(url)
        xml = ET.XML(data)
        live = xml.find("Product").find("LiveInfo")
        if live is not None:
            live = live.find("Live").text
            if live == "true":
                options.live = True
        if xml.find("Product").find("Syndicate").text == "true":
            options.live = True
        filename = xml.find("Product").find("Videos").find("Video").find("Url").text
        self.subtitle = xml.find("Product").find("SamiFile").text

        if options.subtitle and options.force_subtitle:
            return

        if filename[len(filename)-3:] == "f4m":
            #fulhack. RTMP need live to be set
            if xml.find("Product").find("Syndicate").text == "true":
                options.live = False
            manifest = "%s?hdcore=2.8.0&g=hejsan" % filename
            download_hds(options, manifest)
        else:
            if filename[:4] == "http":
                data = get_http_data(filename)
                xml = ET.XML(data)
                filename = xml.find("Url").text
                if xml.find("Msg").text:
                    log.error("Can't download file:")
                    log.error(xml.find("Msg").text)
                    sys.exit(2)

            parse = urlparse(filename)
            match = re.search("^(/[a-z0-9]{0,20})/(.*)", parse.path)
            if not match:
                log.error("Somthing wrong with rtmpparse")
                sys.exit(2)
            filename = "%s://%s:%s%s" % (parse.scheme, parse.hostname, parse.port, match.group(1))
            path = "-y %s" % match.group(2)
            options.other = "-W http://flvplayer.viastream.viasat.tv/flvplayer/play/swf/player.swf %s" % path

            download_rtmp(options, filename)

    def get_subtitle(self, options):
        if self.subtitle:
            data = get_http_data(self.subtitle)
            subtitle_sami(options, data)

    def find_all_episodes(self, options):
        format_id = re.search(r'data-format-id="(\d+)"', self.get_urldata())
        if not format_id:
            log.error("Can't find video info")
            sys.exit(2)
        data = get_http_data("http://playapi.mtgx.tv/v1/sections?sections=videos.one,seasons.videolist&format=%s" % format_id.group(1))
        jsondata = json.loads(data)
        videos = jsondata["_embedded"]["sections"][1]["_embedded"]["seasons"][0]["_embedded"]["episodelist"]["_embedded"]["videos"]

        return sorted(x["sharing"]["url"] for x in videos)

########NEW FILE########
__FILENAME__ = vimeo
# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-
from __future__ import absolute_import
import sys
import json
import re

from svtplay_dl.service import Service, OpenGraphThumbMixin
from svtplay_dl.utils import get_http_data
from svtplay_dl.fetcher.http import download_http
from svtplay_dl.log import log

class Vimeo(Service, OpenGraphThumbMixin):
    supported_domains = ['vimeo.com']

    def get(self, options):
        match = re.search("data-config-url=\"(.*)\" data-fallback-url", self.get_urldata())
        if not match:
            log.error("Can't find data")
            sys.exit(4)
        player_url = match.group(1).replace("&amp;", "&")
        player_data = get_http_data(player_url)

        if player_data:
            jsondata = json.loads(player_data)
            avail_quality = jsondata["request"]["files"]["h264"]
            if options.quality:
                try:
                    selected = avail_quality[options.quality]
                except KeyError:
                    log.error("Can't find that quality. (Try one of: %s)",
                              ", ".join([str(elm) for elm in avail_quality]))
                    sys.exit(4)
            else:
                try:
                    selected = self.select_highest_quality(avail_quality)
                except KeyError:
                    log.error("Can't find any streams.")
                    sys.exit(4)
            url = selected['url']
            download_http(options, url)
        else:
            log.error("Can't find any streams.")
            sys.exit(2)

    def select_highest_quality(self, available):
        if 'hd' in available:
            return available['hd']
        elif 'sd' in available:
            return available['sd']
        else:
            raise KeyError()

########NEW FILE########
__FILENAME__ = hls
#!/usr/bin/python
# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-

# The unittest framwork doesn't play nice with pylint:
#   pylint: disable-msg=C0103

from __future__ import absolute_import
import unittest
import svtplay_dl.fetcher.hls as hls

class HlsTest(unittest.TestCase):
    def test_get_full_url_1(self):
        for test in [
            # full http:// url as media segment in playlist
            {
                'srcurl': 'INVALID',
                'segment': 'http://example.com/',
                'expected': 'http://example.com/'
            },
            # full https:// url as media segment in playlist
            {
                'srcurl': 'INVALID',
                'segment': 'https://example.com/',
                'expected': 'https://example.com/'
            },
            # filename as media segment in playlist (http)
            {
                'srcurl': 'http://example.com/',
                'segment': 'foo.ts',
                'expected': 'http://example.com/foo.ts'
            },
            # filename as media segment in playlist (https)
            {
                'srcurl': 'https://example.com/',
                'segment': 'foo.ts',
                'expected': 'https://example.com/foo.ts'
            },
            # replacing srcurl file
            {
                'srcurl': 'http://example.com/bar',
                'segment': 'foo.ts',
                'expected': 'http://example.com/foo.ts'
            },
            # with query parameters
            {
                'srcurl': 'http://example.com/bar?baz=qux',
                'segment': 'foo.ts',
                'expected': 'http://example.com/foo.ts?baz=qux'
            },
        ]:
            self.assertEqual(
                hls._get_full_url(test['segment'], test['srcurl']),
                test['expected'])

########NEW FILE########
__FILENAME__ = output
#!/usr/bin/python
# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-

# The unittest framwork doesn't play nice with pylint:
#   pylint: disable-msg=C0103

from __future__ import absolute_import
import unittest
import svtplay_dl.output
from mock import patch

# FIXME: use mock framework instead of this hack
class mockfile(object):
    def __init__(self):
        self.content = []

    def write(self, string):
        self.content.append(string)

    def read(self):
        return self.content.pop()

class progressTest(unittest.TestCase):
    def setUp(self):
        self.mockfile = mockfile()
        svtplay_dl.output.progress_stream = self.mockfile

    @patch('svtplay_dl.output.progressbar')
    def test_0_0(self, pbar):
        svtplay_dl.output.progress(0, 0)
        self.assertFalse(pbar.called)

    @patch('svtplay_dl.output.progressbar')
    def test_0_100(self, pbar):
        svtplay_dl.output.progress(0, 100)
        pbar.assert_any_call(100, 0, "")

class progressbarTest(unittest.TestCase):
    def setUp(self):
        self.mockfile = mockfile()
        svtplay_dl.output.progress_stream = self.mockfile

    def test_0_100(self):
        svtplay_dl.output.progressbar(100, 0)
        self.assertEqual(
            self.mockfile.read(),
            "\r[000/100][..................................................] "
        )

    def test_progress_1_100(self):
        svtplay_dl.output.progressbar(100, 1)
        self.assertEqual(
            self.mockfile.read(),
            "\r[001/100][..................................................] "
        )

    def test_progress_2_100(self):
        svtplay_dl.output.progressbar(100, 2)
        self.assertEqual(
            self.mockfile.read(),
            "\r[002/100][=.................................................] "
        )

    def test_progress_50_100(self):
        svtplay_dl.output.progressbar(100, 50)
        self.assertEqual(
            self.mockfile.read(),
            "\r[050/100][=========================.........................] "
        )

    def test_progress_100_100(self):
        svtplay_dl.output.progressbar(100, 100)
        self.assertEqual(
            self.mockfile.read(),
            "\r[100/100][==================================================] "
        )

    def test_progress_20_100_msg(self):
        svtplay_dl.output.progressbar(100, 20, "msg")
        self.assertEqual(
            self.mockfile.read(),
            "\r[020/100][==========........................................] msg"
        )

class EtaTest(unittest.TestCase):
    @patch('time.time')
    def test_eta_0_100(self, mock_time):
        mock_time.return_value = float(0)

        # Let's make this simple; we'll create something that
        # processes one item per second, and make the size be
        # 100.
        eta = svtplay_dl.output.ETA(100)
        self.assertEqual(eta.left, 100) # no progress yet
        self.assertEqual(str(eta), "(unknown)") # no progress yet

        mock_time.return_value = float(10) # sleep(10)
        eta.update(10)
        self.assertEqual(eta.left, 90)
        self.assertEqual(str(eta), "0:01:30") # 90 items left, 90s left

        mock_time.return_value += 1
        eta.increment() # another item completed in one second!
        self.assertEqual(eta.left, 89)
        self.assertEqual(str(eta), "0:01:29")

        mock_time.return_value += 9
        eta.increment(9) # another item completed in one second!
        self.assertEqual(eta.left, 80)
        self.assertEqual(str(eta), "0:01:20")

        mock_time.return_value = float(90) # sleep(79)
        eta.update(90)
        self.assertEqual(eta.left, 10)
        self.assertEqual(str(eta), "0:00:10")

########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/python
# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-

# The unittest framwork doesn't play nice with pylint:
#   pylint: disable-msg=C0103

from __future__ import absolute_import
import unittest
import svtplay_dl.utils

class timestrTest(unittest.TestCase):
    def test_1(self):
        self.assertEqual(svtplay_dl.utils.timestr(1), "00:00:00,00")

    def test_100(self):
        self.assertEqual(svtplay_dl.utils.timestr(100), "00:00:00,10")

    def test_3600(self):
        self.assertEqual(svtplay_dl.utils.timestr(3600), "00:00:03,60")

    def test_3600000(self):
        self.assertEqual(svtplay_dl.utils.timestr(3600000), "01:00:00,00")

########NEW FILE########
__FILENAME__ = io
# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-

# Pylint does not seem to handle conditional imports
# pylint: disable=F0401
# pylint: disable=W0611
# pylint: disable=E0611

from __future__ import absolute_import
from svtplay_dl.utils import is_py3

if is_py3:
    from io import BytesIO as StringIO
else:
    from StringIO import StringIO

########NEW FILE########
__FILENAME__ = urllib
# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-

# Pylint does not seem to handle conditional imports
# pylint: disable=F0401
# pylint: disable=W0611

from __future__ import absolute_import
from svtplay_dl.utils import is_py3
if is_py3:
    # pylint: disable=E0611
    from urllib.parse import quote, unquote_plus, quote_plus, urlparse, parse_qs
    from urllib.request import urlopen, Request, build_opener, \
                               HTTPCookieProcessor, HTTPRedirectHandler
    from urllib.error import HTTPError, URLError
    from urllib.response import addinfourl
    from http.cookiejar import CookieJar, Cookie
else:
    from urllib import addinfourl, quote, unquote_plus, quote_plus
    from urlparse import urlparse, parse_qs
    from urllib2 import urlopen, Request, HTTPError, URLError, build_opener, \
                        HTTPCookieProcessor, HTTPRedirectHandler
    from cookielib import CookieJar, Cookie

########NEW FILE########
__FILENAME__ = __main__
#!/usr/bin/env python
# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-
import sys

if __package__ is None and not hasattr(sys, "frozen"):
    # direct call of __main__.py
    import os.path
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import svtplay_dl
if __name__ == '__main__':
    svtplay_dl.main()
########NEW FILE########
