__FILENAME__ = test
#!/usr/bin/env python

__license__ = '''
Copyright 2010 Jake Wharton

py-video-downloader is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as
published by the Free Software Foundation, either version 3 of
the License, or (at your option) any later version.

py-video-downloader is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General
Public License along with py-video-downloader.  If not, see
<http://www.gnu.org/licenses/>.
'''

#Ensure we get the repository version and not an installed version
import os
import sys
sys.path.insert(0, os.path.abspath(__file__))

from unittest import defaultTestLoader, TestSuite, TextTestRunner, TestCase
from videodownloader.providers import Vimeo, YouTube


class VimeoTests(TestCase):
    video = Vimeo('5720832')

    def test_best_format(self):
        self.assertEqual(VimeoTests.video._get_best_format(), 'hd')

    def test_comments(self):
        self.assertNotEqual(VimeoTests.video.comments, -1)

    def test_duration(self):
        self.assertNotEqual(VimeoTests.video.duration, -1)
        self.assertEqual(VimeoTests.video.duration, 299)

    def test_formats(self):
        self.assertEqual(VimeoTests.video.formats, set(['sd', 'hd']))

    def test_height(self):
        self.assertNotEqual(VimeoTests.video.height, -1)
        self.assertEqual(VimeoTests.video.height, 720)

    def test_likes(self):
        self.assertNotEqual(VimeoTests.video.likes, -1)

    def test_plays(self):
        self.assertNotEqual(VimeoTests.video.plays, -1)

    def test_request_expiration(self):
        self.assertNotEqual(VimeoTests.video.request_expiration, None)

    def test_request_signature(self):
        self.assertNotEqual(VimeoTests.video.request_signature, None)

    def test_thumbnail(self):
        self.assertNotEqual(VimeoTests.video.thumbnail, None)
        self.assertEqual(VimeoTests.video.thumbnail, 'http://b.vimeocdn.com/ts/209/280/20928062_640.jpg')

    def test_title(self):
        self.assertEqual(VimeoTests.video.title, 'Brand New - Jesus (Daisy sessions)')

    def test_uploader(self):
        self.assertNotEqual(VimeoTests.video.uploader, None)
        self.assertEqual(VimeoTests.video.uploader, 'Wiseguy Pictures')

    def test_width(self):
        self.assertNotEqual(VimeoTests.video.width, -1)
        self.assertEqual(VimeoTests.video.width, 1280)


class YouTubeTests(TestCase):
    video = YouTube('tgbNymZ7vqY')

    def test_author(self):
        self.assertNotEqual(YouTubeTests.video.author, None)
        self.assertEqual(YouTubeTests.video.author, 'MuppetsStudio')

    def test_best_format(self):
        self.assertEqual(YouTubeTests.video._get_best_format(), '37')

    def test_duration(self):
        self.assertNotEqual(YouTubeTests.video.duration, -1)
        self.assertEqual(YouTubeTests.video.duration, 287)

    def test_formats(self):
        self.assertEqual(YouTubeTests.video.formats, set(['5', '18', '37', '35', '22', '34', '43', '44', '45']))

    def test_keywords(self):
        self.assertNotEqual(YouTubeTests.video.keywords, set([]))
        self.assertEqual(YouTubeTests.video.keywords, set(['Swedish', 'Zealand', 'Honeydew', 'Gonzo', 'Chef', 'Singing', 'Statler', 'Scooter', 'Teeth', 'Pepe', 'Frog', 'virmup', 'Brian', 'Camilla', 'Animal', 'Dr.', 'New', 'John', 'Bunny', 'virmupHD', 'Bobo', 'Eagle', 'Rock', 'Mahna', 'Electric', 'May', 'Rowlf', 'Minella', 'Bear', 'Monsters', 'Freddie', 'Opera', 'Floyd', 'Studio', 'Music', 'Lew', 'Strangepork', 'Beauregard', 'Queen', 'Beaker', 'King', 'Muppets', 'Mercury', 'Julius', 'Turkey', 'Chickens', 'Waldorf', 'Penguins', 'Zoot', 'Piggy', 'Harry', 'Newsman', 'Janice', 'Snowths', 'Bunsen', 'Deacon', 'Crazy', 'Taylor', 'Johnny', 'Sam', 'Show', 'Roger', 'Rhapsody', 'Musical', 'Sal', 'Roll', 'Prawn', 'Fozzie', 'Mayhem', 'Bohemian', 'Kermit', 'Fiama', 'Muppet', 'Miss']))

    def test_rating(self):
        self.assertNotEqual(YouTubeTests.video.rating, -1.0)

    def test_thumbnail(self):
        self.assertNotEqual(YouTubeTests.video.thumbnail, None)
        self.assertEqual(YouTubeTests.video.thumbnail, 'http://i1.ytimg.com/vi/tgbNymZ7vqY/default.jpg')

    def test_title(self):
        self.assertEqual(YouTubeTests.video.title, 'The Muppets: Bohemian Rhapsody')

    def test_token(self):
        self.assertNotEqual(YouTubeTests.video.token, None)



def run(verbosity=2):
    suite = [
        defaultTestLoader.loadTestsFromTestCase(VimeoTests),
        defaultTestLoader.loadTestsFromTestCase(YouTubeTests),
    ]
    return TextTestRunner(verbosity=verbosity).run(TestSuite(suite))

if __name__ == '__main__':
    run()

########NEW FILE########
__FILENAME__ = main
#!/usr/bin/env python

__license__ = '''
Copyright 2010 Jake Wharton

py-video-downloader is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as
published by the Free Software Foundation, either version 3 of
the License, or (at your option) any later version.

py-video-downloader is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General
Public License along with py-video-downloader.  If not, see
<http://www.gnu.org/licenses/>.
'''

from optparse import OptionParser, OptionGroup
import sys
import os
import urllib2

from videodownloader import providers

def main():
    DEFAULT_DEBUG = False

    print 'videodownloader-2.0.0 - by Jake Wharton <jakewharton@gmail.com>'
    print

    parser = OptionParser(usage="Usage: %prog -p PROVIDER [-f FMT] [-d DIR] videoID [... videoID]")

    provider_list = ', '.join(["'%s'" % provider for provider in providers.__all__])
    parser.add_option('-e', '--ext', dest='ext', default=providers.Provider.DEFAULT_EXT, help='Manually override video extension.')
    parser.add_option('-f', '--format', dest='format', help='Format of video to download. Run with no video IDs for a provider specific list.')
    parser.add_option('-t', '--title', dest='title', help='Manually override video title.')
    parser.add_option('-p', '--provider', dest='provider', help='Online provider from where to download the video. (Available: %s)'%provider_list)
    parser.add_option('--debug', dest='is_debug', action='store_true', default=DEFAULT_DEBUG, help='Enable debugging output.')

    options, videos = parser.parse_args()

    try:
        provider = getattr(providers, options.provider)
    except Exception:
        print 'ERROR: Could not load provider "%s".' % options.provider
        sys.exit(1)

    if len(videos) == 0:
        #Print out a format list for that provider
        print '%-10s %-40s' % ('Format', 'Description')
        print '-'*10, '-'*40
        for format in provider.FORMATS.iteritems():
            print '%-10s %-40s' % format
    else:
        for video in videos:
            v = provider(video, title=options.title, format=options.format, ext=options.ext, debug=options.is_debug)
            print 'Downloading "%s"...' % v.title
            try:
                v.run()
            except KeyboardInterrupt:
                print "WARNING: Aborting download."

                #Try to delete partially completed file
                try:
                    os.remove(v.full_filename)
                except IOError:
                    print 'WARNING: Could not remove partial file.'
            except (urllib2.HTTPError, IOError) as e:
                if options.is_debug:
                    print e
                print "ERROR: Fatal HTTP error."

        print
        print 'Done.'

########NEW FILE########
__FILENAME__ = vimeo
__license__ = '''
Copyright 2010 Jake Wharton

py-video-downloader is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as
published by the Free Software Foundation, either version 3 of
the License, or (at your option) any later version.

py-video-downloader is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General
Public License along with py-video-downloader.  If not, see
<http://www.gnu.org/licenses/>.
'''

from videodownloader.providers import Provider
from xml.etree import ElementTree
import re

class Vimeo(Provider):
    FORMAT_PRIORITY = ['hd', 'sd']
    FORMATS = {
        'sd': '640x360 H.264/AAC Stereo MP4',
        'hd': '1280x720 H.264/AAC Stereo MP4',
    }

    def __init__(self, id, **kwargs):
        super(Vimeo, self).__init__(id, **kwargs)

        #Load video meta information
        url = 'http://vimeo.com/moogaloop/load/clip:%s' % self.id
        self._debug('Vimeo', '__init__', 'Downloading "%s"...' % url)
        self._xml = ElementTree.fromstring(super(Vimeo, Vimeo)._download(url).read())

        #Get available formats
        self.formats = set(['sd'])
        if self._xml.findtext('video/isHD', '0') == '1':
            self.formats.add('hd')
        self._debug('Vimeo', '__init__', 'formats', ', '.join(self.formats))

        #Get video title if not explicitly set
        if self.title is id:
            self.title = self._xml.findtext('video/caption', self.title)
        self._debug('Vimeo', '__init__', 'title', self.title)

        #Get video filename if not explicity set
        self.filename = self.title if self.filename is None else self.filename
        self._debug('Vimeo', '__init__', 'filename', self.filename)

        #Get magic data needed to download
        self.request_signature  = self._xml.findtext('request_signature', None)
        self._debug('Vimeo', '__init__', 'request_signature', self.request_signature)
        self.request_expiration = self._xml.findtext('request_signature_expires', None)
        self._debug('Vimeo', '__init__', 'request_expiration', self.request_expiration)

        #Video thumbnail
        self.thumbnail = self._xml.findtext('video/thumbnail', None)
        self._debug('Vimeo', '__init__', 'thumbnail', self.thumbnail)

        #Video duration (seconds)
        try:
            self.duration  = int(self._xml.findtext('video/duration', -1))
        except ValueError:
            #TODO: warn
            self.duration = -1
        self._debug('Vimeo', '__init__', 'duration', self.duration)

        #Other Vimeo-specific information:
        self.uploader = self._xml.findtext('video/uploader_display_name', None)
        self._debug('Vimeo', '__init__', 'uploader', self.uploader)

        self.url = self._xml.findtext('video/url_clean', None)
        self._debug('Vimeo', '__init__', 'url', self.url)

        try:
            self.height = int(self._xml.findtext('video/height', -1))
        except ValueError:
            #TODO: warn
            self.height = -1
        self._debug('Vimeo', '__init__', 'height', self.height)

        try:
            self.width  = int(self._xml.findtext('video/width', -1))
        except ValueError:
            #TODO: warn
            self.width = -1
        self._debug('Vimeo', '__init__', 'width', self.width)

        try:
            self.likes = int(self._xml.findtext('video/totalLikes', -1))
        except ValueError:
            #TODO: warn
            self.likes = -1
        self._debug('Vimeo', '__init__', 'likes', self.likes)

        try:
            self.plays = int(self._xml.findtext('video/totalPlays', -1))
        except ValueError:
            #TODO: warn
            self.plays = -1
        self._debug('Vimeo', '__init__', 'plays', self.plays)

        try:
            self.comments = int(self._xml.findtext('video/totalComments', -1))
        except ValueError:
            #TODO: warn
            self.comments = -1
        self._debug('Vimeo', '__init__', 'comments', self.comments)

    def get_download_url(self):
        #Validate format
        if self.format is None:
            self.format = self._get_best_format()
        elif self.format not in self.formats:
            raise ValueError('Invalid format "%s". Valid formats are "%s".' % (self.format, '", "'.join(self.formats)))

        url = 'http://vimeo.com/moogaloop/play/clip:%s/%s/%s/' % (self.id, self.request_signature, self.request_expiration)
        if self.format != 'sd':
            url += '?q=%s' % self.format

        self._debug('Vimeo', 'get_download_url', 'url', url)
        return url

    def _get_best_format(self):
        for format in Vimeo.FORMAT_PRIORITY:
            if format in self.formats:
                self._debug('Vimeo', '_get_best_format', 'format', format)
                return format
        raise ValueError('Could not determine the best available format. Vimeo has likely changed its page layout. Please contact the author of this script.')

    def _in_download(self, url):
        self.fileext = re.search(r'(mp4|flv)', url.geturl()).group(1)
        self._debug('Vimeo', '_in_download', 'fileext', self.fileext)
########NEW FILE########
__FILENAME__ = youtube
__license__ = '''
Copyright 2010 Jake Wharton

py-video-downloader is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as
published by the Free Software Foundation, either version 3 of
the License, or (at your option) any later version.

py-video-downloader is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General
Public License along with py-video-downloader.  If not, see
<http://www.gnu.org/licenses/>.
'''

from videodownloader.providers import Provider
import re
import urllib

class YouTube(Provider):
    FORMAT_PRIORITY = ['37', '22', '45', '44', '35', '43', '18', '34', '5']
    FORMATS = {
        '5' : '320x240 H.263/MP3 Mono FLV',
        '13': '176x144 3GP/AMR Mono 3GP',
        '17': '176x144 3GP/AAC Mono 3GP',
        '18': '480x360/480x270 H.264/AAC Stereo MP4',
        '22': '1280x720 H.264/AAC Stereo MP4',
        '34': '320x240 H.264/AAC Stereo FLV',
        '35': '640x480/640x360 H.264/AAC Stereo FLV',
        '37': '1920x1080 H.264/AAC Stereo MP4',
        '43': '640x360 VP8/Vorbis Stereo MP4',
        '44': '854x480 VP8/Vorbis Stereo MP4',
        '45': '1280x720 VP8/Vorbis Stereo MP4',
    }

    def __init__(self, id, **kwargs):
        super(YouTube, self).__init__(id, **kwargs)

        #Load video meta information
        url  = 'http://www.youtube.com/get_video_info?video_id=%s' % self.id
        self._debug('YouTube', '__init__', 'Downloading "%s"...' % url)
        self._html = super(YouTube, YouTube)._download(url).read()

        #Get available formats
        self.formats = set()
        for match in re.finditer(r'itag%3D(\d+)', self._html):
            if match.group(1) not in YouTube.FORMATS.keys():
                print 'WARNING: Unknown format "%s" found.' % match.group(1)
            self.formats.add(match.group(1))
        self._debug('YouTube', '__init__', 'formats', ', '.join(self.formats))

        #Get video title if not explicitly set
        if self.title is id:
            match = re.search(r'&title=([^&]+)', self._html, re.DOTALL)
            if match:
                self.title = urllib.unquote_plus(match.group(1))
                self._debug('YouTube', '__init__', 'title', self.title)
        self._debug('YouTube', '__init__', 'title', self.title)

        #Get video filename if not explicity set
        self.filename = self.title if self.filename is None else self.filename
        self._debug('YouTube', '__init__', 'filename', self.filename)

        #Get proper file extension if a valid format was supplied
        if self.format is not None and self.format in YouTube.FORMATS.keys():
            self.fileext = YouTube.FORMATS[self.format][-3:].lower()
            self._debug('YouTube', '__init__', 'fileext', self.fileext)

        #Get magic data needed to download
        match = re.search(r'&token=([-_0-9a-zA-Z]+%3D)', self._html)
        self.token = urllib.unquote(match.group(1)) if match else None
        self._debug('YouTube', '__init__', 'token', self.token)

        #Video thumbnail
        match = re.search(r'&thumbnail_url=(.+?)&', self._html)
        self.thumbnail = urllib.unquote(match.group(1)) if match else None
        self._debug('YouTube', '__init__', 'thumbnail', self.thumbnail)

        #Video duration (seconds)
        try:
            match = re.search(r'&length_seconds=(\d+)&', self._html)
            self.duration = int(match.group(1)) if match else -1
        except ValueError:
            #TODO: warn
            self.duration = -1
        self._debug('YouTube', '__init__', 'duration', self.duration)

        #Other YouTube-specific information
        match = re.search(r'&author=(.+?)&', self._html)
        self.author = match.group(1) if match else None
        self._debug('YouTube', '__init__', 'author', self.author)

        match = re.search(r'keywords=(.+?)&', self._html)
        self.keywords = set(urllib.unquote(match.group(1)).split(',')) if match else set([])
        self._debug('YouTube', '__init__', 'keywords', ','.join(self.keywords))

        try:
            match = re.search(r'&avg_rating=(\d\.\d+)&', self._html)
            self.rating = float(match.group(1)) if match else -1.0
        except ValueError:
            #TODO: warn
            self.rating = -1.0
        self._debug('YouTube', '__init__', 'rating', self.rating)


    def get_download_url(self):
        #Validate format
        if self.format is None:
            self.format = self._get_best_format()
        elif self.format not in self.formats:
            raise ValueError('Invalid format "%s". Valid formats are "%s".' % (self.format, '", "'.join(self.formats)))

        #Check extension
        if self.fileext is None or self.fileext == Provider.DEFAULT_EXT:
            self.fileext = YouTube.FORMATS[self.format][-3:].lower()

        url = 'http://youtube.com/get_video?video_id=%s&fmt=%s&t=%s' % (self.id, self.format, self.token)

        self._debug('YouTube', 'get_download_url', 'url', url)
        return url

    def _get_best_format(self):
        for format in YouTube.FORMAT_PRIORITY:
            if format in self.formats:
                self._debug('YouTube', '_get_best_format', 'format', format)
                return format
        raise ValueError('Could not determine the best available format. YouTube has likely changed its page layout. Please contact the author of this script.')
########NEW FILE########
