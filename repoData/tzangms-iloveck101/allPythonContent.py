__FILENAME__ = exceptions
class URLParseError(Exception):
    pass

########NEW FILE########
__FILENAME__ = iloveck101
import os
import sys
import re
import platform

import gevent
from gevent import monkey

monkey.patch_all()

import requests
from lxml import etree
from more_itertools import chunked

from .utils import get_image_info, parse_url
from .exceptions import URLParseError


REQUEST_HEADERS = {'User-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/31.0.1650.57 Safari/537.36'}
BASE_URL = 'http://ck101.com/'
CHUNK_SIZE = 3


def iloveck101(url):
    """
    Determine the url is valid. And check if the url contains any thread link or it's a thread.
    """

    if 'ck101.com' in url:
        if 'thread' in url:
            retrieve_thread(url)
        else:
            try:
                for thread in retrieve_thread_list(url):
                    if thread is not None:
                        retrieve_thread(thread)
            except KeyboardInterrupt:
                print 'I love ck101'
    else:
        sys.exit('This is not ck101 url')


def retrieve_thread_list(url):
    """
    The url may contains many thread links. We parse them out.
    """

    resp = requests.get(url, headers=REQUEST_HEADERS)

    # parse html
    html = etree.HTML(resp.content)

    links = html.xpath('//a/@href')
    for link in links:
        yield link


def retrieve_thread(url):
    """
    download images from given ck101 URL
    """

    # check if the url has http prefix
    if not url.startswith('http'):
        url = BASE_URL + url

    # find thread id
    m = re.match('thread-(\d+)-.*', url.rsplit('/', 1)[1])
    if not m:
        return

    print '\nVisit %s' % (url)

    thread_id = m.group(1)


    # create `iloveck101` folder in ~/Pictures
    system = platform.system()
    if system == 'Darwin':
        picfolder = 'Pictures'
    elif system == 'Windows':
        release = platform.release()
        if release in ['Vista', '7', '8']:
            picfolder = 'Pictures'
        elif release is 'XP':
            picfolder = os.path.join('My Documents', 'My Pictures')
        else:
            picfolder = ''
    else:
        picfolder = ''

    home = os.path.expanduser("~")
    base_folder = os.path.join(home, picfolder, 'iloveck101')

    if not os.path.exists(base_folder):
        os.mkdir(base_folder)

    # parse title and images
    try:
        title, image_urls = parse_url(url)
    except URLParseError:
        sys.exit('Oops, can not fetch the page')

    # create target folder for saving images
    folder = os.path.join(base_folder, "%s - %s" % (thread_id, title))
    if not os.path.exists(folder):
        os.mkdir(folder)

    def process_image_worker(image_url):
        filename = image_url.rsplit('/', 1)[1]

        # ignore useless image
        if not image_url.startswith('http'):
            return

        # fetch image
        print 'Fetching %s ...' % image_url
        resp = requests.get(image_url, headers=REQUEST_HEADERS)

        # ignore small images
        content_type, width, height = get_image_info(resp.content)
        if width < 400 or height < 400:
            print "image is too small"
            return

        # save image
        with open(os.path.join(folder, filename), 'wb+') as f:
            f.write(resp.content)

    try:
        for chunked_image_urls in chunked(image_urls, CHUNK_SIZE):
            jobs = [gevent.spawn(process_image_worker, image_url)
                    for image_url in chunked_image_urls]
            gevent.joinall(jobs)
    except KeyboardInterrupt:
        raise KeyboardInterrupt


def main():
    try:
        url = sys.argv[1]
    except IndexError:
        sys.exit('Please provide URL from ck101')

    iloveck101(url)

########NEW FILE########
__FILENAME__ = utils
import struct
from cStringIO import StringIO

import requests
from lxml import etree

from .exceptions import URLParseError


def get_image_info(data):
    """
    read image dimension
    """

    data = str(data)
    size = len(data)
    height = -1
    width = -1
    content_type = ''

    # handle GIFs
    if (size >= 10) and data[:6] in ('GIF87a', 'GIF89a'):
        # Check to see if content_type is correct
        content_type = 'image/gif'
        w, h = struct.unpack("<HH", data[6:10])
        width = int(w)
        height = int(h)

    # See PNG 2. Edition spec (http://www.w3.org/TR/PNG/)
    # Bytes 0-7 are below, 4-byte chunk length, then 'IHDR'
    # and finally the 4-byte width, height
    elif ((size >= 24) and data.startswith('\211PNG\r\n\032\n')
          and (data[12:16] == 'IHDR')):
        content_type = 'image/png'
        w, h = struct.unpack(">LL", data[16:24])
        width = int(w)
        height = int(h)

    # Maybe this is for an older PNG version.
    elif (size >= 16) and data.startswith('\211PNG\r\n\032\n'):
        # Check to see if we have the right content type
        content_type = 'image/png'
        w, h = struct.unpack(">LL", data[8:16])
        width = int(w)
        height = int(h)

    # handle JPEGs
    elif (size >= 2) and data.startswith('\377\330'):
        content_type = 'image/jpeg'
        jpeg = StringIO(data)
        jpeg.read(2)
        b = jpeg.read(1)
        try:
            while (b and ord(b) != 0xDA):
                while (ord(b) != 0xFF): b = jpeg.read(1)
                while (ord(b) == 0xFF): b = jpeg.read(1)
                if (ord(b) >= 0xC0 and ord(b) <= 0xC3):
                    jpeg.read(3)
                    h, w = struct.unpack(">HH", jpeg.read(4))
                    break
                else:
                    jpeg.read(int(struct.unpack(">H", jpeg.read(2))[0])-2)
                b = jpeg.read(1)
            width = int(w)
            height = int(h)
        except struct.error:
            pass
        except ValueError:
            pass

    return content_type, width, height

def parse_url(url):
    """
    parse image_url from given url
    """

    REQUEST_HEADERS = {
        'User-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/31.0.1650.57 Safari/537.36'
    }

    # fetch html and find images
    title = None
    for attemp in range(3):
        resp = requests.get(url, headers=REQUEST_HEADERS)
        if resp.status_code != 200:
            print 'Retrying ...'
            continue

        # parse html
        html = etree.HTML(resp.content)

        # title
        try:
            title = html.find('.//title').text.split(' - ')[0].replace('/', '').strip()
            break
        except AttributeError:
            print 'Retrying ...'
            continue

    if title is None:
        raise URLParseError

    image_urls = html.xpath('//img/@file')
    return title, image_urls

########NEW FILE########
