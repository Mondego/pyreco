__FILENAME__ = test_transcode
#!/usr/bin/python3
#
# CherryMusic - a standalone music server
# Copyright (c) 2012 - 2014 Tom Wallroth & Tilman Boerner
#
# Project page:
#   http://fomori.org/cherrymusic/
# Sources on github:
#   http://github.com/devsnd/cherrymusic/
#
# CherryMusic is based on
#   jPlayer (GPL/MIT license) http://www.jplayer.org/
#   CherryPy (BSD license) http://www.cherrypy.org/
#
# licensed under GNU GPL version 3 (or later)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
#

import os
import tempfile

from nose.tools import *

import audiotranscode as transcode

CAPTURE_OUTPUT = True

# inject unavailable encoder
unavailable_enc = transcode.Encoder('mp3', ['notavailable'])
transcode.AudioTranscode.Encoders.append(unavailable_enc)

# inject unavailable decoder
unavailable_enc = transcode.Decoder('mp3', ['notavailable'])
transcode.AudioTranscode.Decoders.append(unavailable_enc)

transcoder = transcode.AudioTranscode(debug=True)
inputdir = os.path.dirname(__file__)
outputpath = tempfile.mkdtemp(prefix='test.cherrymusic.audiotranscode.')
testfiles = {
    'mp3': os.path.join(inputdir, 'test.mp3'),
    'ogg': os.path.join(inputdir, 'test.ogg'),
    'flac': os.path.join(inputdir, 'test.flac'),
    'wav': os.path.join(inputdir, 'test.wav'),
    'wma': os.path.join(inputdir, 'test.wma'),
}


def setup_module():
    if CAPTURE_OUTPUT:
        print('writing transcoder output to %r' % (outputpath,))


def teardown_module():
    if not CAPTURE_OUTPUT:
        os.rmdir(outputpath)


def generictestfunc(filepath, newformat, encoder, decoder):
    ident = "%s_%s_to_%s_%s" % (
            decoder.command[0],
            os.path.basename(filepath),
            encoder.command[0],
            newformat
    )
    #print(ident)
    outdata = b''
    transcoder_stream = transcoder.transcodeStream(
        filepath, newformat, encoder=encoder, decoder=decoder)
    for data in transcoder_stream:
        outdata += data
    if CAPTURE_OUTPUT:
        outname = os.path.join(outputpath, ident + '.' + newformat)
        with open(outname, 'wb') as outfile:
            outfile.write(outdata)
    ok_(len(outdata) > 0, 'No data received: ' + ident)


def test_generator():
    for enc in transcoder.Encoders:
        if not enc.available():
            print('Encoder %s not installed!' % (str(enc),))
            continue
        for dec in transcoder.Decoders:
            if not dec.available():
                print('Decoder %s not installed!' % (str(dec)))
                continue
            if dec.filetype in testfiles:
                filename = testfiles[dec.filetype]
                yield generictestfunc, filename, enc.filetype, enc, dec

@raises(transcode.DecodeError)
def test_file_not_found():
    try:
        for a in transcoder.transcodeStream('nosuchfile', 'mp3'):
            pass
    except Exception as e:
        #print exception for coverage
        print(e)
        raise

@raises(transcode.DecodeError)
def test_no_decoder_available():
    noaudio = os.path.join(inputdir,'test.noaudio')
    for a in transcoder.transcodeStream(noaudio, 'mp3'):
        pass

@raises(transcode.EncodeError)
def test_no_encoder_available():
    for a in transcoder.transcodeStream(testfiles['wav'], 'foobar'):
        pass

def test_automatically_find_encoder():
    for a in transcoder.transcodeStream(testfiles['wav'], 'wav'):
        pass

def test_transcode_file():
    outfile = os.path.join(outputpath, 'test_file.wav')
    transcoder.transcode(testfiles['wav'], outfile)

def test_mimetype():
    assert transcoder.mimeType('mp3') == 'audio/mpeg'
########NEW FILE########
__FILENAME__ = _backported
#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (c) 2009 Raymond Hettinger
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
#     The above copyright notice and this permission notice shall be
#     included in all copies or substantial portions of the Software.
#
#     THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#     EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
#     OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
#     NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
#     HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
#     WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#     FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
#     OTHER DEALINGS IN THE SOFTWARE.

from UserDict import DictMixin

class OrderedDict(dict, DictMixin):

    def __init__(self, *args, **kwds):
        if len(args) > 1:
            raise TypeError('expected at most 1 arguments, got %d' % len(args))
        try:
            self.__end
        except AttributeError:
            self.clear()
        self.update(*args, **kwds)

    def clear(self):
        self.__end = end = []
        end += [None, end, end]         # sentinel node for doubly linked list
        self.__map = {}                 # key --> [key, prev, next]
        dict.clear(self)

    def __setitem__(self, key, value):
        if key not in self:
            end = self.__end
            curr = end[1]
            curr[2] = end[1] = self.__map[key] = [key, curr, end]
        dict.__setitem__(self, key, value)

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        key, prev, next = self.__map.pop(key)
        prev[2] = next
        next[1] = prev

    def __iter__(self):
        end = self.__end
        curr = end[2]
        while curr is not end:
            yield curr[0]
            curr = curr[2]

    def __reversed__(self):
        end = self.__end
        curr = end[1]
        while curr is not end:
            yield curr[0]
            curr = curr[1]

    def popitem(self, last=True):
        if not self:
            raise KeyError('dictionary is empty')
        if last:
            key = reversed(self).next()
        else:
            key = iter(self).next()
        value = self.pop(key)
        return key, value

    def __reduce__(self):
        items = [[k, self[k]] for k in self]
        tmp = self.__map, self.__end
        del self.__map, self.__end
        inst_dict = vars(self).copy()
        self.__map, self.__end = tmp
        if inst_dict:
            return (self.__class__, (items,), inst_dict)
        return self.__class__, (items,)

    def keys(self):
        return list(self)

    setdefault = DictMixin.setdefault
    update = DictMixin.update
    pop = DictMixin.pop
    values = DictMixin.values
    items = DictMixin.items
    iterkeys = DictMixin.iterkeys
    itervalues = DictMixin.itervalues
    iteritems = DictMixin.iteritems

    def __repr__(self):
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, self.items())

    def copy(self):
        return self.__class__(self)

    @classmethod
    def fromkeys(cls, iterable, value=None):
        d = cls()
        for key in iterable:
            d[key] = value
        return d

    def __eq__(self, other):
        if isinstance(other, OrderedDict):
            if len(self) != len(other):
                return False
            for p, q in  zip(self.items(), other.items()):
                if p != q:
                    return False
            return True
        return dict.__eq__(self, other)

    def __ne__(self, other):
        return not self == other

########NEW FILE########
__FILENAME__ = albumartfetcher
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# CherryMusic - a standalone music server
# Copyright (c) 2012 - 2014 Tom Wallroth & Tilman Boerner
#
# Project page:
#   http://fomori.org/cherrymusic/
# Sources on github:
#   http://github.com/devsnd/cherrymusic/
#
# CherryMusic is based on
#   jPlayer (GPL/MIT license) http://www.jplayer.org/
#   CherryPy (BSD license) http://www.cherrypy.org/
#
# licensed under GNU GPL version 3 (or later)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
#

try:
    import urllib.request
    import urllib.parse
except ImportError:
    import backport.urllib as urllib
import os.path
import codecs
import re
import subprocess
from cherrymusicserver import log

#unidecode is opt-dependency
try:
    from unidecode import unidecode
except ImportError:
    unidecode = lambda x: x


def programAvailable(name):
        """
        check if a program is available in the system PATH
        """
        try:
            with open(os.devnull, 'w') as devnull:
                process = subprocess.Popen([name], stdout=subprocess.PIPE,
                                           stderr=devnull)
                out, err = process.communicate()
                return 'ImageMagick' in codecs.decode(out, 'UTF-8')
        except OSError:
            return False


class AlbumArtFetcher:
    """
    provide the means to fetch images from different web services by
    searching for certain keywords
    """

    imageMagickAvailable = programAvailable('convert')

    methods = {
        'amazon': {
            'url': "http://www.amazon.com/s/ref=sr_nr_i_0?rh=k:",
            'regexes': ['<img  src="([^"]*)"\s+class="productImage',
                        '<img.+?src="([^"]*)"\s+class="productImage'],
        },
        'bestbuy.com': {
            'url': 'http://www.bestbuy.com/site/searchpage.jsp?_dyncharset=ISO-8859-1&_dynSessConf=-1844839118144877442&id=pcat17071&type=page&ks=960&sc=Global&cp=1&sp=&qp=category_facet%3DMovies+%26+Music~abcat0600000^category_facet%3DSAAS~Music~cat02001&list=y&usc=All+Categories&nrp=15&fs=saas&iht=n&seeAll=&st=',
            'regexes': ['<img itemprop="image" class="thumb" src="([^"]*)"']
        },
        # buy.com is now rakuten.com
        # with a new search API that nobody bothered to figure out yet
        # 'buy.com': {
        #     'url': "http://www.buy.com/sr/srajax.aspx?from=2&qu=",
        #     'regexes': [' class="productImageLink"><img src="([^"]*)"']
        # },
        'google': {
            'url': "https://ajax.googleapis.com/ajax/services/search/images?v=1.0&imgsz=medium&rsz=8&q=",
            'regexes': ['"url":"([^"]*)"', '"unescapedUrl":"([^"]*)"']
        },
    }

    def __init__(self, method='amazon', timeout=10):
        """define the urls of the services and a regex to fetch images
        """
        self.MAX_IMAGE_SIZE_BYTES = 100*1024
        self.IMAGE_SIZE = 80
        # the GET parameter value of the searchterm must be appendable
        # to the urls defined in "methods".
        if not method in self.methods:
            log.e(_(('''unknown album art fetch method: '%(method)s', '''
                     '''using default.''')),
                  {'method': method})
            method = 'google'
        self.method = method
        self.timeout = timeout

    def resize(self, imagepath, size):
        """
        resize an image using image magick

        Returns:
            the binary data of the image and a matching http header
        """
        if AlbumArtFetcher.imageMagickAvailable:
            with open(os.devnull, 'w') as devnull:
                cmd = ['convert', imagepath,
                       '-resize', str(size[0])+'x'+str(size[1]),
                       'jpeg:-']
                print(' '.join(cmd))
                im = subprocess.Popen(cmd,
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE)
                data = im.communicate()[0]
                header = {'Content-Type': "image/jpeg",
                          'Content-Length': len(data)}
                return header, data
        return None, ''

    def fetchurls(self, searchterm):
        """fetch image urls based on the provided searchterms

        Returns:
            list of urls
        """
        # choose the webservice to retrieve the images from
        method = self.methods[self.method]
        # use unidecode if it's available
        searchterm = unidecode(searchterm).lower()
        # make sure the searchterms are only letters and spaces
        searchterm = re.sub('[^a-z\s]', ' ', searchterm)
        # the keywords must always be appenable to the method-url
        url = method['url']+urllib.parse.quote(searchterm)
        #download the webpage and decode the data to utf-8
        html = codecs.decode(self.retrieveData(url)[0], 'UTF-8')
        # fetch all urls in the page
        matches = []
        for regex in method['regexes']:
            matches += re.findall(regex, html)
        return matches

    def fetch(self, searchterm):
        """
        fetch an image using the provided search term
        encode the searchterms and retrieve an image from one of the
        image providers

        Returns:
            an http header and binary data
        """
        matches = self.fetchurls(searchterm)
        if matches:
            imgurl = matches[0]
            if 'urltransformer' in self.method:
                imgurl = method['urltransformer'](imgurl)
            if imgurl.startswith('//'):
                imgurl = 'http:'+imgurl
            raw_data, header = self.retrieveData(imgurl)
            return header, raw_data
        else:
            return None, ''

    def retrieveData(self, url):
        """
        use a fake user agent to retrieve data from a webaddress

        Returns:
            the binary data and the http header of the request
        """
        user_agent = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/535.19 '
                      '(KHTML, like Gecko) Ubuntu/12.04 '
                      'Chromium/18.0.1025.168 Chrome/18.0.1025.168 '
                      'Safari/535.19')
        req = urllib.request.Request(url, headers={'User-Agent': user_agent})
        urlhandler = urllib.request.urlopen(req, timeout=self.timeout)
        return urlhandler.read(), urlhandler.info()

    def fetchLocal(self, path):
        """ search a local path for image files.
        @param path: directory path
        @type path: string
        @return header, imagedata, is_resized
        @rtype dict, bytestring"""

        filetypes = (".jpg", ".jpeg", ".png")
        try:
            for file_in_dir in os.listdir(path):
                if not file_in_dir.lower().endswith(filetypes):
                    continue
                try:
                    imgpath = os.path.join(path, file_in_dir)
                    if os.path.getsize(imgpath) > self.MAX_IMAGE_SIZE_BYTES:
                        header, data = self.resize(imgpath,
                                                   (self.IMAGE_SIZE,
                                                    self.IMAGE_SIZE))
                        return header, data, True
                    else:
                        with open(imgpath, "rb") as f:
                            data = f.read()
                            if(imgpath.lower().endswith(".png")):
                                mimetype = "image/png"
                            else:
                                mimetype = "image/jpeg"
                            header = {'Content-Type': mimetype,
                                      'Content-Length': len(data)}
                            return header, data, False
                except IOError:
                    return None, '', False
        except OSError:
            return None, '', False
        return None, '', False

########NEW FILE########
__FILENAME__ = cherrymodel
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# CherryMusic - a standalone music server
# Copyright (c) 2012 - 2014 Tom Wallroth & Tilman Boerner
#
# Project page:
#   http://fomori.org/cherrymusic/
# Sources on github:
#   http://github.com/devsnd/cherrymusic/
#
# CherryMusic is based on
#   jPlayer (GPL/MIT license) http://www.jplayer.org/
#   CherryPy (BSD license) http://www.cherrypy.org/
#
# licensed under GNU GPL version 3 (or later)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
#
"""This class is the heart-piece of the program and
will delegate different calls between other classes.
"""

from __future__ import unicode_literals

import os
from random import choice
import codecs
import json
import cherrypy
import audiotranscode
from imp import reload

try:
    from urllib.parse import quote
except ImportError:
    from backport.urllib.parse import quote
try:
    import urllib.request
except ImportError:
    import backport.urllib as urllib

import cherrymusicserver as cherry
from cherrymusicserver import service
from cherrymusicserver import pathprovider
from cherrymusicserver.util import Performance
from cherrymusicserver import resultorder
from cherrymusicserver import log

# used for sorting
NUMBERS = ('0', '1', '2', '3', '4', '5', '6', '7', '8', '9')

@service.user(cache='filecache')
class CherryModel:
    def __init__(self):
        CherryModel.NATIVE_BROWSER_FORMATS = ['ogg', 'mp3']
        CherryModel.supportedFormats = CherryModel.NATIVE_BROWSER_FORMATS[:]
        if cherry.config['media.transcode']:
            self.transcoder = audiotranscode.AudioTranscode()
            CherryModel.supportedFormats += self.transcoder.availableDecoderFormats()
            CherryModel.supportedFormats = list(set(CherryModel.supportedFormats))

    @classmethod
    def abspath(cls, path):
        return os.path.join(cherry.config['media.basedir'], path)

    @classmethod
    def fileSortFunc(cls, filepath):
        upper = pathprovider.filename(filepath).upper().strip()
        return upper

    @classmethod
    def fileSortFuncNum(cls, filepath):
        upper = CherryModel.fileSortFunc(filepath)
        # check if the filename starts with a number
        if upper.startswith(NUMBERS):
            # find index of the first non numerical character:
            non_number_index = 0
            for idx, char in enumerate(upper):
                if not char in NUMBERS:
                    break
                else:
                    non_number_index += 1
            # make sure that numbers are sorted correctly by evening out
            # the number in the filename 0-padding up to 5 digits.
            return '0'*(5 - non_number_index) + upper
        return upper

    def sortFiles(self, files, fullpath='', number_ordering=False):
        # sort alphabetically (case insensitive)
        if number_ordering:
            # make sure numbers are sorted correctly
            sortedfiles = sorted(files, key=CherryModel.fileSortFuncNum)
        else:
            sortedfiles = sorted(files, key=CherryModel.fileSortFunc)
        if fullpath:
            #sort directories up
            isfile = lambda x: os.path.isfile(os.path.join(fullpath, x))
            sortedfiles = sorted(sortedfiles, key=isfile)
        return sortedfiles

    def listdir(self, dirpath, filterstr=''):
        absdirpath = CherryModel.abspath(dirpath)
        if cherry.config['browser.pure_database_lookup']:
            allfilesindir = self.cache.listdir(dirpath)
        else:
            allfilesindir = os.listdir(absdirpath)

        #remove all files not inside the filter
        if filterstr:
            filterstr = filterstr.lower()
            allfilesindir = [f for f in allfilesindir
                             if f.lower().startswith(filterstr)]
        else:
            allfilesindir = [f for f in allfilesindir if not f.startswith('.')]

        musicentries = []

        maximum_shown_files = cherry.config['browser.maxshowfiles']
        compactlisting = len(allfilesindir) > maximum_shown_files
        if compactlisting:
            upper_case_files = [x.upper() for x in allfilesindir]
            filterstr = os.path.commonprefix(upper_case_files)
            filterlength = len(filterstr)+1
            currentletter = '/'  # impossible first character
            # don't care about natural number order in compact listing
            sortedfiles = self.sortFiles(allfilesindir, number_ordering=False)
            for dir in sortedfiles:
                filter_match = dir.upper().startswith(currentletter.upper())
                if filter_match and not len(currentletter) < filterlength:
                    continue
                else:
                    currentletter = dir[:filterlength]
                    #if the filter equals the foldername
                    if len(currentletter) == len(filterstr):
                        subpath = os.path.join(absdirpath, dir)
                        CherryModel.addMusicEntry(subpath, musicentries)
                    else:
                        musicentries.append(
                            MusicEntry(strippath(absdirpath),
                                       repr=currentletter,
                                       compact=True))
        else:
            # enable natural number ordering for real directories and files
            sortedfiles = self.sortFiles(allfilesindir, absdirpath,
                                         number_ordering=True)
            for dir in sortedfiles:
                subpath = os.path.join(absdirpath, dir)
                CherryModel.addMusicEntry(subpath, musicentries)
        if cherry.config['media.show_subfolder_count']:
            for musicentry in musicentries:
                musicentry.count_subfolders_and_files()
        return musicentries

    @classmethod
    def addMusicEntry(cls, fullpath, list):
        if os.path.isfile(fullpath):
            if CherryModel.isplayable(fullpath):
                list.append(MusicEntry(strippath(fullpath)))
        else:
            list.append(MusicEntry(strippath(fullpath), dir=True))

    def updateLibrary(self):
        self.cache.full_update()
        return True

    def file_size_within_limit(self, filelist, maximum_download_size):
        acc_size = 0
        for f in filelist:
            acc_size += os.path.getsize(CherryModel.abspath(f))
            if acc_size > maximum_download_size:
                return False
        return True

    def search(self, term):
        reload(cherry.tweak)
        tweaks = cherry.tweak.CherryModelTweaks
        user = cherrypy.session.get('username', None)
        if user:
            log.d(_("%(user)s searched for '%(term)s'"), {'user': user, 'term': term})
        max_search_results = cherry.config['search.maxresults']
        results = self.cache.searchfor(term, maxresults=max_search_results)
        with Performance(_('sorting DB results using ResultOrder')) as perf:
            debug = tweaks.result_order_debug
            order_function = resultorder.ResultOrder(term, debug=debug)
            results = sorted(results, key=order_function, reverse=True)
            results = results[:min(len(results), max_search_results)]
            if debug:
                n = tweaks.result_order_debug_files
                for sortedResults in results[:n]:
                    perf.log(sortedResults.debugOutputSort)
                for sortedResults in results:
                    sortedResults.debugOutputSort = None  # free ram

        with Performance(_('checking and classifying results:')):
            results = list(filter(CherryModel.isValidMediaFile, results))
        if cherry.config['media.show_subfolder_count']:
            for result in results:
                result.count_subfolders_and_files()
        return results

    def check_for_updates(self):
        try:
            url = 'http://fomori.org/cherrymusic/update_check.php?version='
            url += cherry.__version__
            urlhandler = urllib.request.urlopen(url, timeout=5)
            jsondata = codecs.decode(urlhandler.read(), 'UTF-8')
            versioninfo = json.loads(jsondata)
            return versioninfo
        except Exception as e:
            log.e(_('Error fetching version info: %s') % str(e))
            return []
    def motd(self):
        artist = ['Hendrix',
                  'Miles Davis',
                  'James Brown',
                  'Nina Simone',
                  'Mozart',
                  'Bach',
                  'John Coltraine',
                  'Jim Morrison',
                  'Frank Sinatra',
                  'Django Reinhardt',
                  'Kurt Cobain',
                  'Thom Yorke',
                  'Vivaldi',
                  'Bob Dylan',
                  'Johnny Cash',
                  'James Brown',
                  'Bob Marley',
                  'Björk']
        liquid = ['2 liters of olive oil',
                  'a glass of crocodile tears',
                  'a bowl of liquid cheese',
                  'some battery acid',
                  'cup of grog',
                  ]
        search = ['{artist} can turn diamonds into jelly-beans.',
                  'The french have some really stinky cheese. It\'s true.',
                  '{artist} used to eat squids for breakfast.',
                  'The GEMA wont let me hear {artist}.',
                  'If {artist} had played with {artist}, they would have made bazillions!',
                  '{artist} actually stole everything from {artist}.',
                  '{artist} really liked to listen to {artist}.',
                  '{artist}\'s music played backwards is actually the same as {artist}. This is how they increased their profit margin!',
                  '{artist} always turned the volume up to 11.',
                  'If {artist} made Reggae it sounded like {artist}.',
                  '{artist} backwards is "{revartist}".',
                  '2 songs of {artist} are only composed of haikus.',
                  '{artist} drank {liquid} each morning, sometimes even twice a day.',
                  'Instead of soap, {artist} used {liquid} to shower.',
                  '{artist} had a dog the size of {artist}.',
                  '{artist} was once sued by {artist} for eating all the cake.',
                  '{artist} named his cat after {artist}. It died two years later by drowning in {liquid}.',
                  '{artist} once founded a gang, but then had to quit becaus of the pirates. All former gang members became squirrels.',
                  '{artist}, a.k.a. "Quadnostril" actually had 2 noses. This meant that it was quite hard to be taken seriously.',
                  'Never put {liquid} and {artist} in the same room. Never ever!',
                  '{artist} lived twice, once as a human, once as a duck.',
                  'Nobody ever thought {artist} would still be famous after the great goat-cheese-fiasco.',
                  'For a long time, nobody knew that {artist} secretly loved wall sockets.',
                  'In the beginning {artist} was very poor and had to auction off a pinky toe. It is still exhibited in the "museum of disgusting stuff" in paris.',
                  '{artist} did never mind if somebody made weird noises. Occasionally this was the inspiration for a new song.',
                  'While creating a huge camp fire {artist} lost all hair. It took years for it to regrow.',
                  'A rooster isn\'t necessarily better than a balloon. However, {artist} found out that balloons are less heavy.',
                  'Instead of cars, snow mobiles are often used to move around in the alps. This information has no relevance whatsoever.',
                  'Creating new life-forms always was a hobby of {artist}. The greatest success was the creation of {artist}.',
                  ]
        oneliner = choice(search)
        while '{artist}' in oneliner:
            a = choice(artist)
            oneliner = oneliner.replace('{artist}', a, 1)
            if '{revartist}' in oneliner:
                oneliner = oneliner.replace('{revartist}', a.lower()[::-1])
        if '{liquid}' in oneliner:
            oneliner = oneliner.replace('{liquid}', choice(liquid))
        return oneliner

    def randomMusicEntries(self, count):
        loadCount = int(count * 1.5) + 1           # expect 70% valid entries
        entries = self.cache.randomFileEntries(loadCount)
        filteredEntries = list(filter(CherryModel.isValidMediaFile, entries))

        return filteredEntries[:count]

    @classmethod
    def isValidMediaFile(cls, file):
        file.path = strippath(file.path)
        #let only playable files appear in the search results
        if file.path.startswith('.'):
            return False
        if not CherryModel.isplayable(file.path) and not file.dir:
            return False
        return True

    @classmethod
    def isplayable(cls, filename):
        '''checks to see if there's no extension or if the extension is in
        the configured 'playable' list'''
        ext = os.path.splitext(filename)[1]
        is_supported_ext = ext and ext[1:].lower() in CherryModel.supportedFormats
        # listed files must not be empty
        is_empty_file = os.path.getsize(CherryModel.abspath(filename)) == 0
        return is_supported_ext and not is_empty_file


def strippath(path):
    if path.startswith(cherry.config['media.basedir']):
        return os.path.relpath(path, cherry.config['media.basedir'])
    return path


class MusicEntry:
    # maximum number of files to be iterated inside of a folder to
    # check if there are playable meadia files or other folders inside
    MAX_SUB_FILES_ITER_COUNT = 100

    def __init__(self, path, compact=False, dir=False, repr=None, subdircount=0, subfilescount=0):
        self.path = path
        self.compact = compact
        self.dir = dir
        self.repr = repr
        # number of directories contained inside
        self.subdircount = subdircount
        # number of files contained inside
        self.subfilescount = subfilescount
        # True when the exact amount of files is too big and is estimated
        self.subfilesestimate = False

    def count_subfolders_and_files(self):
        if self.dir:
            self.subdircount = 0
            self.subfilescount = 0
            fullpath = CherryModel.abspath(self.path)
            diriectory_listing = os.listdir(fullpath)
            for idx, filename in enumerate(diriectory_listing):
                if idx > MusicEntry.MAX_SUB_FILES_ITER_COUNT:
                    # estimate remaining file count
                    self.subfilescount *= len(diriectory_listing)/float(idx+1)
                    self.subfilescount = int(self.subfilescount)
                    self.subdircount *= len(diriectory_listing)/float(idx+1)
                    self.subdircount = int(self.subdircount)
                    self.subfilesestimate = True
                    return
                subfilefullpath = os.path.join(fullpath, filename)
                if os.path.isfile(subfilefullpath):
                    if CherryModel.isplayable(subfilefullpath):
                        self.subfilescount += 1
                else:
                    self.subdircount += 1

    def to_dict(self):
        if self.compact:
            #compact
            return {'type': 'compact',
                    'urlpath': self.path,
                    'label': self.repr}
        elif self.dir:
            #dir
            simplename = pathprovider.filename(self.path)
            return {'type': 'dir',
                    'path': self.path,
                    'label': simplename,
                    'foldercount': self.subdircount,
                    'filescount': self.subfilescount,
                    'filescountestimate': self.subfilesestimate }
        else:
            #file
            simplename = pathprovider.filename(self.path)
            urlpath = quote(self.path.encode('utf8'))
            return {'type': 'file',
                    'urlpath': urlpath,
                    'path': self.path,
                    'label': simplename}

    def __repr__(self):
        return "<MusicEntry path:%s, dir:%s>" % (self.path, self.dir)

########NEW FILE########
__FILENAME__ = configuration
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# CherryMusic - a standalone music server
# Copyright (c) 2012 - 2014 Tom Wallroth & Tilman Boerner
#
# Project page:
#   http://fomori.org/cherrymusic/
# Sources on github:
#   http://github.com/devsnd/cherrymusic/
#
# CherryMusic is based on
#   jPlayer (GPL/MIT license) http://www.jplayer.org/
#   CherryPy (BSD license) http://www.cherrypy.org/
#
# licensed under GNU GPL version 3 (or later)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
#

#python 2.6+ backward compability
from __future__ import unicode_literals
from io import open

import itertools
import os
import re
import weakref

from collections import Mapping, namedtuple
from backport.collections import OrderedDict
from backport import callable

from cherrymusicserver import util
from cherrymusicserver import log as logging


def _validate_basedir(basedir):
    if not basedir:
        raise ValueError('basedir must be set')
    if not os.path.isabs(basedir):
        raise ValueError('basedir must be absolute path: {basedir}'.format(basedir=basedir))
    if not os.path.exists(basedir):
        raise ValueError("basedir must exist: {basedir}".format(basedir=basedir))
    if not os.path.isdir(basedir):
        raise ValueError("basedir must be a directory: {basedir}".format(basedir=basedir))
    return True


def from_defaults():
    '''load default configuration. must work if path to standard config file is unknown.'''

    c = ConfigBuilder()

    with c['media.basedir'] as basedir:
        basedir.value = None
        basedir.valid = _validate_basedir
        # i18n: Don't mind whitespace - string will be re-wrapped automatically. Use blank lines to separate paragraphs.
        basedir.doc = _("""
                    BASEDIR specifies where the media that should be
                    served is located. It must be an absolute path, e.g.
                    BASEDIR=/absolute/path/to/media.

                    Links: If your operating system supports them,
                    you can use symlinks directly in BASEDIR. Links to
                    directories which contain BASEDIR will be ignored,
                    just like all links not directly in, but in sublevels
                    of BASEDIR. This is to guard against the adverse
                    effects of link cycles.
                            """)

    with c['media.transcode'] as transcode:
        transcode.value = False
        # i18n: Don't mind whitespace - string will be re-wrapped automatically. Use blank lines to separate paragraphs.
        transcode.doc = _("""
                    TRANSCODE (experimental!) enables automatic live transcoding
                    of the media to be able to listen to every format on every device.
                    This requires you to have the appropriate codecs installed.
                    Please note that transcoding will significantly increase the stress on the CPU!
                            """)

    with c['media.fetch_album_art'] as fetch:
        fetch.value = False
        # i18n: Don't mind whitespace - string will be re-wrapped automatically. Use blank lines to separate paragraphs.
        fetch.doc = _("""
                    Tries to fetch the album cover from various locations in the web,
                    if no image is found locally. By default it will be fetched from amazon.
                    They will be shown next to folders that qualify as a possible
                    album.
                            """)

    with c['media.show_subfolder_count'] as subfoldercount:
        subfoldercount.value = True
        # i18n: Don't mind whitespace - string will be re-wrapped automatically. Use blank lines to separate paragraphs.
        fetch.doc = _("""
                    Show the number of sub-folders and tracks contained
                    in any folder. This will increase the stress for the
                    server, so if you're running CherryMusic on a 386DX II
                    or similar, it is recommended to deactivate this feature.
                            """)


    with c['media.maximum_download_size'] as maxdl:
        maxdl.value = 1024*1024*250
        # i18n: Don't mind whitespace - string will be re-wrapped automatically. Use blank lines to separate paragraphs.
        maxdl.doc = _("""
                    Maximum size in bytes of all files to be downloaded in one zipfile.
                    Defaults to {default_value} {default_unit}.
                            """.format(default_value='250', default_unit=_('megabytes')))

    with c['search.maxresults'] as maxresults:
        maxresults.value = 20
        # i18n: Don't mind whitespace - string will be re-wrapped automatically. Use blank lines to separate paragraphs.
        maxresults.doc = _("""
                    MAXRESULTS sets the maximum amount of search results
                    to be displayed. If MAXRESULTS is set to a higher value,
                    the search will take longer, but will also be more accurate.
                            """)

    with c['search.load_file_db_into_memory'] as memory:
        memory.value = False
        # i18n: Don't mind whitespace - string will be re-wrapped automatically. Use blank lines to separate paragraphs.
        memory.doc = _("""
                    This will load parts of the database into memory for improved
                    performance. This option should only be used on systems with
                    sufficient memory, because it will hurt the performance otherwise.
                            """)

    with c['browser.maxshowfiles'] as maxshowfiles:
        maxshowfiles.value = 100
        # i18n: Don't mind whitespace - string will be re-wrapped automatically. Use blank lines to separate paragraphs.
        maxshowfiles.doc = _('''
                    MAXSHOWFILES specifies how many files and folders should
                    be shown at the same time. E.g. if you open a folder
                    with more than MAXSHOWFILES, the files will be grouped
                    according to the first letter in their name.
                    100 is a good value, as a CD can have up to 99 tracks.
                            ''')

    with c['browser.pure_database_lookup'] as pure_database_lookup:
        pure_database_lookup.value = False
        # i18n: Don't mind whitespace - string will be re-wrapped automatically. Use blank lines to separate paragraphs.
        pure_database_lookup.doc = _("""
                    Only use the media database, never the filesystem, for content
                    lookups in browser and search. Useful if the media files reside
                    on an external hard drive or behind a slow network connection.
                            """)

    with c['server.port'] as port:
        port.value = 8080
        # i18n: Don't mind whitespace - string will be re-wrapped automatically. Use blank lines to separate paragraphs.
        port.doc = _('The port the server will listen to.')

    with c['server.ipv6_enabled'] as ipv6:
        ipv6.value = False
        # i18n: Don't mind whitespace - string will be re-wrapped automatically. Use blank lines to separate paragraphs.
        ipv6.doc = _("""When set to true, the server will listen on a IPv6
                          socket instead of IPv4""")

    with c['server.localhost_only'] as localhost_only:
        localhost_only.value = False
        # i18n: Don't mind whitespace - string will be re-wrapped automatically. Use blank lines to separate paragraphs.
        localhost_only.doc = _('''
                    when localhost_only is set to true, the server will not
                    be visible in the network and only play music on the
                    same computer it is running on.
                            ''')

    with c['server.rootpath'] as rootpath:
        rootpath.value = '/'
        # i18n: Don't mind whitespace - string will be re-wrapped automatically. Use blank lines to separate paragraphs.
        rootpath.doc = _('''
                    The path cherrymusic will be available on. Normally
                    you'll want to leave it as '/', so that CherryMusic is
                    available under e.g. localhost:8080. You might want to
                    change the path if CherryMusic runs behind a reverse
                    proxy. Changing it to '/cherrymusic' will make it available
                    under e.g. localhost:8080/cherrymusic
                                ''')


    with c['server.localhost_auto_login'] as localhost_auto_login:
        localhost_auto_login.value = False
        # i18n: Don't mind whitespace - string will be re-wrapped automatically. Use blank lines to separate paragraphs.
        localhost_auto_login.doc = _('''
                    When localhost_auto_login is set to "True", the server will
                    not ask for credentials when using it locally. The user will
                    be automatically logged in as admin.
                            ''')

    with c['server.permit_remote_admin_login'] as permit_remote_admin_login:
        permit_remote_admin_login.value = True
        # i18n: Don't mind whitespace - string will be re-wrapped automatically. Use blank lines to separate paragraphs.
        permit_remote_admin_login.doc = _('''
                    When permit_remote_admin_login is set to "False", admin users
                    may only log in from the computer cherrymusic is currently
                    running on. This can improve security.
                            ''')

    with c['server.keep_session_in_ram'] as keep_session_in_ram:
        keep_session_in_ram.value = False
        # i18n: Don't mind whitespace - string will be re-wrapped automatically. Use blank lines to separate paragraphs.
        keep_session_in_ram.doc = _('''
                    Will keep the user sessions in RAM instead of a file in the
                    configuration directory. This means, that any unsaved
                    playlists will be lost when the server is restarted.
                            ''')

    with c['server.ssl_enabled'] as ssl_enabled:
        ssl_enabled.value = False
        # i18n: Don't mind whitespace - string will be re-wrapped automatically. Use blank lines to separate paragraphs.
        ssl_enabled.doc = _('''
                    The following options allow you to use cherrymusic with
                    https encryption. If ssl_enabled is set to "False", all other
                    ssl options will be ommited.
                            ''')

    with c['server.ssl_port'] as ssl_port:
        ssl_port.value = 8443
        # i18n: Don't mind whitespace - string will be re-wrapped automatically. Use blank lines to separate paragraphs.
        ssl_port.doc = _('''
                    The port that will listen to SSL encrypted requests. If
                    ssl_enabled is set to "True", all unencrypted HTTP requests
                    will be redirected to this port.
                            ''')

    with c['server.ssl_certificate'] as ssl_certificate:
        ssl_certificate.value = 'certs/server.crt'
        # i18n: Don't mind whitespace - string will be re-wrapped automatically. Use blank lines to separate paragraphs.
        ssl_certificate.doc = _('''
                    The SSL certiticate sent to the client to verify the
                    server's authenticity. A relative path is relative to the
                    location of the CherryMusic configuration file.
                            ''')

    with c['server.ssl_private_key'] as ssl_private_key:
        ssl_private_key.value = 'certs/server.key'
        # i18n: Don't mind whitespace - string will be re-wrapped automatically. Use blank lines to separate paragraphs.
        ssl_private_key.doc = _('''
                    SSL private key file used by the server to decrypt and sign
                    secure communications. Keep this one secret!  A relative
                    path is relative to the location of the CherryMusic
                    configuration file.
                            ''')

    with c['general.update_notification'] as update_notification:
        update_notification.value = True
        # i18n: Don't mind whitespace - string will be re-wrapped automatically. Use blank lines to separate paragraphs.
        update_notification.doc = _('''
                    Notify admins about available security and feature updates.
                            ''')

    return c.to_configuration()


def from_configparser(filepath):
    """Have an ini file that the python configparser can understand? Pass the filepath
    to this function, and a matching Configuration will magically be returned."""

    if not os.path.exists(filepath):
        logging.error(_('configuration file not found: %(filepath)s'), {'filepath':filepath})
        return None
    if not os.path.isfile(filepath):
        logging.error(_('configuration path is not a file: %(filepath)s'), {'filepath':filepath})
        return None

    try:
        from configparser import ConfigParser
    except ImportError:
        from backport.configparser import ConfigParser
    cfgp = ConfigParser()
    with open(filepath, encoding='utf-8') as fp:
        cfgp.readfp(fp)
    dic = OrderedDict()
    for section_name in cfgp.sections():
        if 'DEFAULT' == section_name:
            section_name = ''
        for name, value in cfgp.items(section_name):
            value += ''   # inner workaround for python 2.6+
                              # transforms ascii str to unicode because
                              # of unicode_literals import
            dic[Key(section_name) + name] = value
    return Configuration.from_mapping(dic)


def write_to_file(cfg, filepath):
    """ Write a configuration to the given file so that it's readable by
        configparser.
    """
    with open(filepath, mode='w', encoding='utf-8') as f:

        def printf(s):
            f.write(s + os.linesep)

        lastsection = None
        for prop in cfg.to_properties():
            if prop.hidden:
                continue
            key, value, doc = (Key(prop.key), prop.value, prop.doc)
            section, subkey = str(key.head), str(key.tail)
            if section != lastsection:
                lastsection = section
                printf('%s[%s]' % (os.linesep, section,))
            if doc:
                printf('')
                lines = util.phrase_to_lines(doc)
                for line in lines:
                    printf('; %s' % (line,))
            printf('%s = %s' % (subkey, value))


def from_dict(mapping):
    '''Alias for :meth:`Configuration.from_mapping`.'''
    return Configuration.from_mapping(mapping)


def from_list(properties):
    '''Alias for :meth:`Configuration.from_properties`.'''
    return Configuration.from_properties(properties)


def to_list(cfg):
    '''Alias for :meth:`Configuration.to_properties`.'''
    return cfg.to_properties()


class ConfigError(Exception):
    """Base class for configuration errors."""
    def __init__(self, key, value=None, msg='', detail=''):
        self.key = key
        self.value = value
        self.msg = msg % {'key': key, 'value': value}
        self.detail = detail % {'key': key, 'value': value}
        Exception.__init__(self, self.key, self.value, self.msg, self.detail)

    def __repr__(self):
        return "{cls}: {msg}, key:{key} value:{val}, {detail}".format(
            cls=self.__class__.__name__,
            key=repr(self.key),
            val=repr(self.value),
            msg=self.msg,
            detail=self.detail,
        )

    def __str__(self):
        detail = self.detail.strip() if hasattr(self, 'detail') else ''
        if detail:
            detail = ' ({0})'.format(detail)
        return '{0}: {1}{2}'.format(self.__class__.__name__, self.msg, detail)


class ConfigNamingError(ConfigError):
    """Something is wrong with the name ('Key') of a config Property."""
    def __init__(self, key, detail=''):
        ConfigError.__init__(self, key, None,
                             'invalid key name: %(key)r', detail)


class ConfigKeyError(ConfigError, KeyError):
    """ A config key does not exist. """
    def __init__(self, key, detail=''):
        ConfigError.__init__(self, key, None,
                             'key does not exist: %(key)r', detail)


class ConfigValueError(ConfigError, ValueError):
    """A configuration property does not accept a value."""
    def __init__(self, key, value, detail=''):
        ConfigError.__init__(self, key, value,
                             'invalid value: %(value)r', detail)


class ConfigWriteError(ConfigError):
    """Error while trying to change an existing configuration property."""
    def __init__(self, key, value, detail=''):
        ConfigError.__init__(self, key, value,
                             "can't write to %(key)s", detail)


def raising_error_handler(e):
    "Simply raise the active exception."
    raise


class error_collector(object):
    """ Callable that can be used to collect errors of Configuration operations
        instead of raising them.
    """
    def __init__(self):
        self.errors = []

    def __call__(self, error):
        self.errors.append(error)

    def __len__(self):
        return len(self.errors)

    def __iter__(self):
        return iter(self.errors)


class Key(object):
    """ A hierarchical property name; alphanumerical and caseless.

        Keys parts can contain ASCII letters, digits and `_`; they must start
        with a letter and be separated by a `.`.
    """
    _sep = '.'
    _re = re.compile(r'^({name}({sep}{name})*)?$'.format(
        name=r'[A-Za-z][A-Za-z0-9_]*',
        sep=_sep,
    ))

    def __init__(self, name=None):
        """ name : Key or str
                `None` means ''
        """
        if None is name:
            name = ''
        elif isinstance(name, Key):
            name = name._str
        elif not isinstance(name, (str, type(''))):
            raise ConfigNamingError(name, 'name must be a Key, str or unicode (is {type!r})'.format(type=type(name)))
        elif not self._re.match(name):
            raise ConfigNamingError(
                name, 'Key parts must only contain the characters [A-Za-z0-9_],'
                            ' start with a letter and be separated by a {seperator}'.format(seperator=self._sep))
        name += ''   # inner workaround for python 2.6+
                    # transforms ascii str to unicode because
                    # of unicode_literals import
        self._str = name.lower()

    def __repr__(self):
        return '{0}({1!r})'.format(self.__class__.__name__, self._str)

    def __str__(self):
        return self._str

    def __iter__(self):
        """Iterate over hierarchical key parts,"""
        return iter(map(Key, self._str.split(self._sep)))

    def __len__(self):
        """The number of non-empty hierarchical parts in this Key."""
        return self._str.count(self._sep) + 1 if self._str else 0

    def __add__(self, other):
        """Append something that can become a Key to a copy of this Key."""
        other = Key(other)
        if self and other:
            return self._sep.join((self._str, other._str))
        return Key(self or other)

    def __radd__(self, other):
        """Make a Key of the left operand and add a copy of this key to it."""
        return Key(other) + self

    def __hash__(self):
        return hash(self.normal)

    def __eq__(self, other):
        return self.normal == Key(other).normal

    def __ne__(self, other):
        return not (self == other)

    @property
    def parent(self):
        """ This Key without its last hierarchical part; evaluates to `False`
            if there are less than two parts in this Key.
        """
        lastsep = self._str.rfind(self._sep)
        if lastsep >= 0:
            return Key(self._str[:lastsep])
        return Key()

    @property
    def head(self):
        """ The first hierarchical part of this Key."""
        firstsep = self._str.find(self._sep)
        if firstsep >= 0:
            return Key(self._str[:firstsep])
        return self

    @property
    def tail(self):
        """ This key without its last hierarchical part; evaluates to `False`
            if there are less than two parts in this Key.
        """
        firstsep = self._str.find(self._sep)
        if firstsep >= 0:
            return Key(self._str[firstsep + 1:])
        return Key()

    @property
    def normal(self):
        """The normal, hashable form of this Key to compare against."""
        return self._str


class _PropertyMap(Mapping):
    """ A map of keys to corresponding Properties; immutable, but can generate
        updated copies of itself. Certain unset property attributes are
        inherited from the property with the closest parent key. These
        inherited attributes are: ``valid``, ``readonly`` and ``hidden``.

        Uses the Property.replace mechanic to update existing properties.
    """
    def __init__(self, properties=()):
        dic = OrderedDict((p.key, p) for p in properties)
        sortedkeys = sorted(dic, key=lambda k: Key(k).normal)
        inherit = _InheritanceViewer(dic)
        for key in sortedkeys:
            dic[key] = inherit.property_with_inherited_attributes(key)
        self._dic = dic

    def __repr__(self):
        return '{%s}' % (', '.join(
            '%r: %r' % (k, v) for k, v in self._dic.items()))

    def __len__(self):
        return len(self._dic)

    def __contains__(self, key):
        return key in self._dic

    def __iter__(self):
        return iter(self._dic)

    def __getitem__(self, key):
        try:
            return self._dic[key]
        except KeyError:
            raise ConfigKeyError(key)

    def replace(self, properties, on_error):
        def getnew(prop):
            return self[prop.key].replace(**prop.to_dict())
        return self._copy_with_new_properties(getnew, properties, on_error)

    def update(self, properties, on_error):
        def getnew(prop):
            try:
                return self[prop.key].replace(**prop.to_dict())
            except KeyError:
                return prop
        return self._copy_with_new_properties(getnew, properties, on_error)

    def _copy_with_new_properties(self, getnew, properties, on_error):
        newdic = OrderedDict(self._dic)
        for prop in properties:
            try:
                newprop = getnew(prop)
            except ConfigError as error:
                on_error(error)
                continue
            newdic[newprop.key] = newprop
        return self.__class__(newdic.values())


class Property(namedtuple('PropertyTuple', 'key value type valid readonly hidden doc')):
    """ A configuration Property with attributes for key (name), value, type,
        validation and doc(umentation); immutable.

        Use :meth:`replace` to return a new Property with changed attributes.

        Attribute values of `None` are considered *not set*, and are the
        default. They also have a special meaning to :meth:`replace`.

        key : str
            A string that acts as this Property's identifier (name).
        value :
            Anything goes that fits possible type or validity constraints,
            except for `dict`s (and mappings in general); use hierarchical
            keys to express those.
        type :
            The desired value type to auto-cast to; factually a constraint to
            possible values. If `None` or an empty string, the property value
            will remain unchanged.
        valid : str or callable
            A validity constraint on the value, applied after `type`. A
            *callable* value will be called and the result evaluated in
            boolean context, to decide if a value is valid. A *str* value will
            be interpreted as a regular expression which the whole
            ``str()`` form of a value will be matched against.
        readonly : bool
            A readonly property will refuse any :meth"`replace` calls with a
            :class:`ConfigWriteError`.
        hidden : bool
            Just a flag; interpretation is up to the user.
        doc : str
            A documentation string.
    """

    def __new__(cls, key=None, value=None, type=None, valid=None, readonly=None,
                hidden=None, doc=None):
        try:
            key = Key(key).normal
            type = cls._get_valid_type(value, type)
            valid = valid
            value = cls._validate(valid, cls._to_type(type, value), type)
            readonly = readonly
            hidden = hidden
            doc = doc
        except ValueError as e:
            raise ConfigValueError(key, value, detail=str(e))
        return super(cls, cls).__new__(
            cls, key, value, type, valid, readonly, hidden, doc)

    @property
    def _args(self):
        """The arguments needed to create this Property: ``(name, value)*``."""
        for name in ('key', 'value', 'type', 'valid', 'readonly', 'hidden', 'doc'):
            attr = getattr(self, name)
            if attr is not None:
                yield name, attr

    def to_dict(self):
        return dict(self._args)

    def replace(self, **kwargs):
        """ Return a new property as a copy of this property, with attributes
            changed according to `kwargs`.

            Generally, all attributes can be overridden if they are currently
            unset (`None`). An exception is `value`, which will be overridden
            by anything but `None`. Restrictions set by `type` and `valid`
            apply.
        """
        dic = self.to_dict()
        dic.update(kwargs)
        other = Property(**dic)
        if self.key and other.key and self.key != other.key:
            raise ConfigWriteError(self.key, other.key,
                'new key must match old ({newkey!r} != {oldkey!r})'.format(
                newkey=other.key, oldkey=self.key))
        if self.readonly:
            raise ConfigWriteError(self.key, other.value,
                'is readonly ({value!r})'.format(value=self.value))
        return Property(
            key=self.key or other.key,
            value=self._override_self('value', other),
            type=self._override_other('type', other),
            valid=self._override_other('valid', other),
            readonly=self._override_other('readonly', other),
            hidden=self._override_other('hidden', other),
            doc=self._override_other('doc', other),
        )

    def _override_self(self, attrname, other):
        """ Select the value of an attribute from self or another instance,
            with preference to other."""
        return self.__select_with_preference(other, self, attrname)

    def _override_other(self, attrname, other):
        """ Select the value of an attribute from self or another instance,
            with preference to self."""
        return self.__select_with_preference(self, other, attrname)

    @staticmethod
    def __select_with_preference(preferred, alt, attrname):
        """ Select one of the values of an attribute to two objects, preferring
            the first unless it holds `None`.
        """
        preference = getattr(preferred, attrname, None)
        alternative = getattr(alt, attrname, None)
        return alternative if preference is None else preference

    @staticmethod
    def _get_valid_type(value, type_):
        """ Turn the type argument into something useful. """
        if type_ in (None, ''):
            if type(value) in (bool, int, float, str, type('')):
                type_ = type(value)
            else:
                return None
        typestr = type_.__name__ if isinstance(type_, type) else str(type_)
        typestr += ''   # inner workaround for python 2.6+
                        # transforms ascii str to unicode because
                        # of unicode_literals import
        if not typestr in Transformers:
            return None
        return typestr

    @staticmethod
    def _to_type(type_, value):
        if value is None:
            return value
        try:
            return Transformers[type_](value)
        except TransformError:
            raise ValueError('cannot transform value to type %s' % (type_,))

    @classmethod
    def _validate(cls, valid, value, type_):
        if value is None:
            return value
        validator = cls._validator(valid)
        return cls._validate_single_value(validator, value)

    @classmethod
    def _validate_single_value(cls, validator, value):
        if not validator(value):
            raise ValueError(validator.__name__)
        return value

    @classmethod
    def _validator(cls, valid):
        if callable(valid):
            return valid
        if not valid:
            return lambda _: True
        return cls._regexvalidator(valid)

    @staticmethod
    def _regexvalidator(valid):
        def regex_validator(value):
            testvalue = '' if value is None else str(value)
            testvalue += ''  # python2.6 compatibility
            exp = valid.strip().lstrip('^').rstrip('$').strip()
            exp = '^' + exp + '$'
            if not re.match(exp, testvalue):
                raise ValueError('value string must match {0!r}, is {1!r}'.format(exp, testvalue))
            return True
        return regex_validator


class _PropertyModel(object):
    """ Objects whose __dict__ can be used to create a Property from;
        calling it with a ``key`` argument will yield a nested model.
    """

    # as class member to keep children out of instance __dict__s
    _children = weakref.WeakKeyDictionary()

    @staticmethod
    def to_property(model):
        return Property(**model.__dict__)

    @classmethod
    def model_family_to_properties(cls, parent_model):
        return (Property(**m.__dict__) for m in cls._family(parent_model))

    @classmethod
    def _makechild(cls, parent, key):
        child = cls(Key(parent.key) + key)
        cls._children[parent].append(child)
        return child

    @classmethod
    def _family(cls, root):
        yield root
        for child in itertools.chain(*[cls._family(c) for c in cls._children[root]]):
            yield child

    def __init__(self, key=None):
        self._children[self] = []
        self.key = Key(key).normal

    def __getitem__(self, key):
        return self._makechild(self, key)

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        pass


class ConfigBuilder(object):

    def __init__(self):
        self.models = OrderedDict()

    def __getitem__(self, key):
        return self.models.setdefault(key, _PropertyModel(key))

    def properties(self):
        return itertools.chain(
            *(_PropertyModel.model_family_to_properties(m) for m in self.models.values()))

    def to_configuration(self):
        return Configuration.from_properties(self.properties())


class Configuration(Mapping):
    """ A mapping of keys to corresponding values, backed by a collection of
        :class:`Property` objects.

        Immutable; call :meth:`update` or :meth:`replace` with a mapping
        argument to modify a copy of a configuration.

        Unset Property attributes of ``valid``, ``readonly`` and ``hidden``
        are overridden by those of a property with a "parent" key.
    """

    @classmethod
    def from_properties(cls, properties):
        cfg = cls()
        cfg.__propertymap = _PropertyMap(properties)
        return cfg

    def to_properties(self):
        return self.__propertymap.values()

    @classmethod
    def from_mapping(cls, mapping):
        properties = (Property(key, value) for key, value in mapping.items())
        return cls.from_properties(properties)

    def to_nested_dict(self):
        d = {}
        for key, value in self.items():
            target = d
            for part in Key(key):
                target = target.setdefault(str(part), {})
            if value is not None:
                target[''] = self[key]
        for key in self:
            parent = None
            target = d
            for part in Key(key):
                parent = target
                target = target[str(part)]
            if [''] == list(target):
                parent[str(part)] = target.pop('')
        return d

    def __init__(self):
        self.__propertymap = _PropertyMap()

    def __repr__(self):
        return '{0}({1})'.format(self.__class__.__name__,
                                 tuple(self.__propertymap.values()))

    def __contains__(self, key):
        return key in self.__propertymap

    def __len__(self):
        return len(self.__propertymap)

    def __iter__(self):
        return iter(self.__propertymap)

    def __getitem__(self, key):
        return self.property(key).value

    def property(self, key):
        """ Return the property corresponding to the key argument or raise a
            ConfigKeyError.
        """
        return self.__propertymap[key]

    def replace(self, mapping, on_error=raising_error_handler):
        """ Return a copy of this configuration with some values replaced by
            the corresponding values in the mapping argument; adding new keys
            is not allowed.

            Resulting ConfigErrors will be raised or passed to a callable
            error handler, if given.
        """
        return self._mutated_by(mapping, self.__propertymap.replace, on_error)

    def update(self, mapping, on_error=raising_error_handler):
        """ Return a copy of this configuration with some values replaced or
            added corresponding to the values in the mapping argument.

            Resulting ConfigErrors will be raised or passed to a callable
            error handler, if given.
        """
        return self._mutated_by(mapping, self.__propertymap.update, on_error)

    def _mutated_by(self, mapping, mutator, on_error):
        mutated = self.__class__()
        properties = []
        for key, value in mapping.items():
            try:
                properties.append(Property(key, value))
            except ConfigError as e:
                on_error(e)
        mutated.__propertymap = mutator(properties, on_error)
        return mutated


class _InheritanceViewer(object):
    def __init__(self, propertymap):
        self.propertymap = propertymap

    def property_with_inherited_attributes(self, key):
        property = self.propertymap[key]
        model = _PropertyModel()
        model.__dict__.update(property.to_dict())
        self._inherit_attribute_if_not_set('valid', model)
        self._inherit_attribute_if_not_set('readonly', model)
        self._inherit_attribute_if_not_set('hidden', model)
        return _PropertyModel.to_property(model)

    def _inherit_attribute_if_not_set(self, attrname, model):
        if getattr(model, attrname, None) is None:
            key = Key(model.key).parent
            value = None
            while value is None and key:
                try:
                    value = getattr(self.propertymap[key.normal], attrname, None)
                except KeyError:
                    pass
                key = key.parent
            setattr(model, attrname, value)


Transformers = {}


def transformer(name, *more):
    global Transformers  # hell yeah!

    def transformer_decorator(func):
        Transformers[name] = func
        for additional in more:
            Transformers[additional] = func
        return func
    return transformer_decorator


class TransformError(Exception):

    def __init__(self, transformername, val):
        msg = ("Error while trying to parse value with transformer "
               "'%s': %s" % (transformername, val))
        super(self.__class__, self).__init__(msg)


@transformer(None)
def _identity(val=None):
    return val


@transformer(name='bool')
def _to_bool_transformer(val=None):
    if isinstance(val, (bool, int, float, complex, list, set, dict, tuple)):
        return bool(val)
    if isinstance(val, (type(''), str)):
        if val.strip().lower() in ('yes', 'true', 'y', '1'):
            return True
        if val.strip().lower() in ('false', 'no', '', 'n', '0'):
            return False
    raise TransformError('bool', val)


@transformer('int')
def _to_int_transformer(val=None):
    try:
        return int(val)
    except (TypeError, ValueError):
        raise TransformError('int', val)


@transformer('float')
def _to_float_transformer(val=None):
    try:
        return float(val)
    except (TypeError, ValueError):
        raise TransformError('float', val)


@transformer('str', 'unicode')
def _to_str_transformer(val=None):
    if val is None:
        return ''
    if isinstance(val, (str, type(''))):
        return val.strip() + ''  # inner workaround for python 2.6+
    return str(val) + ''         # transforms ascii str to unicode because
                                 # of unicode_literals import

########NEW FILE########
__FILENAME__ = connect
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# CherryMusic - a standalone music server
# Copyright (c) 2012 - 2014 Tom Wallroth & Tilman Boerner
#
# Project page:
#   http://fomori.org/cherrymusic/
# Sources on github:
#   http://github.com/devsnd/cherrymusic/
#
# CherryMusic is based on
#   jPlayer (GPL/MIT license) http://www.jplayer.org/
#   CherryPy (BSD license) http://www.cherrypy.org/
#
# licensed under GNU GPL version 3 (or later)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
#
'''
Connect to databases.
'''

# from abc import ABCMeta, abstractmethod   # don't, for py2 compatibility

import cherrymusicserver.service as service


# class AbstractConnector(metaclass=ABCMeta):
class AbstractConnector(object):
    '''Provide database connections by name.

    Override :meth:`connection` and :meth:`dbname` to subclass.
    '''
    def __repr__(self):
        return '{0} [{1}]'.format(self.__class__.__name__, hex(id(self)))

    # @abstractmethod
    def connection(self, dbname):
        '''Return a connection object to talk to a database.'''
        raise NotImplementedError('abstract method')

    # @abstractmethod
    def dblocation(self, basename):
        '''Return the internal handle used for the database with ``basename``.'''
        raise NotImplementedError('abstract method')

    def bound(self, dbname):
        '''Return a :class:`BoundConnector` bound to the database with ``dbname``.'''
        return BoundConnector(dbname, self)


@service.user(baseconnector='dbconnector')
class BoundConnector(object):
    '''Provide connections to a specific database name.'''
    def __init__(self, dbname, overrideconnector=None):
        self.name = dbname
        if overrideconnector is not None:
            self.baseconnector = overrideconnector

    def __repr__(self):
        return '{cls}({0!r}, {1})'.format(
            self.name, repr(self.baseconnector),
            cls=self.__class__.__name__)

    @property
    def dblocation(self):
        '''Return the internal handle used for the bound database.'''
        return self.baseconnector.dblocation(self.name)

    def connection(self):
        '''Return a connection object to talk to the bound database.'''
        return self.baseconnector.connection(self.name)

    def execute(self, query, params=()):
        '''Connect to the bound database and execute a query; then return the
        cursor object used.'''
        cursor = self.connection().cursor()
        cursor.execute(query, params)
        return cursor

########NEW FILE########
__FILENAME__ = sql
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# CherryMusic - a standalone music server
# Copyright (c) 2012 - 2014 Tom Wallroth & Tilman Boerner
#
# Project page:
#   http://fomori.org/cherrymusic/
# Sources on github:
#   http://github.com/devsnd/cherrymusic/
#
# CherryMusic is based on
#   jPlayer (GPL/MIT license) http://www.jplayer.org/
#   CherryPy (BSD license) http://www.cherrypy.org/
#
# licensed under GNU GPL version 3 (or later)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
#
'''SQL Database handling.'''

import os.path
import sqlite3
import tempfile
import threading

from cherrymusicserver import log
from cherrymusicserver.database.connect import AbstractConnector, BoundConnector


class SQLiteConnector(AbstractConnector):
    '''Connector for SQLite3 databases.

    By specification of the python sqlite3 module, sharing connections is to
    be considered NOT THREADSAFE.

    datadir: str
        Base directories of database files.
    extension: str (optional)
        Extension to append to database filenames.
    connargs: dict (optional)
        Dictionary with keyword args to pass on to sqlite3.Connection.
    '''
    def __init__(self, datadir='', extension='', connargs={}):
        self.datadir = datadir
        self.extension = extension
        self.connargs = connargs

    def connection(self, dbname):
        return sqlite3.connect(self.dblocation(dbname), **self.connargs)

    def dblocation(self, basename):
        if self.extension:
            basename = os.path.extsep.join((basename, self.extension))
        return os.path.join(self.datadir, basename)


class Updater(object):
    '''Handle the versioning needs of a single database.

    name : str
        The name of the database to manage.
    dbdef : dict
        The corresponding definition.
    connector : :class:`cherrymusicserver.database.connect.AbstractConnector`
        To connect to the database.
    '''

    _metatable = {
        'create.sql': """CREATE TABLE IF NOT EXISTS _meta_version(
                            version TEXT,
                            _created INTEGER NOT NULL DEFAULT (datetime('now'))
                        );""",
        'drop.sql': """DROP TABLE IF EXISTS _meta_version;"""
    }

    _classlock = threading.RLock()
    _dblockers = {}

    def __init__(self, name, dbdef):
        assert name and dbdef
        self.name = name
        self.desc = dbdef
        self.db = BoundConnector(self.name)
        with self:
            self._init_meta()

    def __del__(self):
        self._unlock()

    def __repr__(self):
        return 'updater({0!r}, {1} -> {2})'.format(
            self.name,
            self._version,
            self._target,
        )

    def __enter__(self):
        self._lock()
        return self

    def __exit__(self, exctype, exception, traceback):
        self._unlock()

    @property
    def _islocked(self):
        name, lockers = self.name, self._dblockers
        with self._classlock:
            return name in lockers and lockers[name] is self

    def _lock(self):
        name, lockers = self.name, self._dblockers
        with self._classlock:
            assert lockers.get(name, self) is self, (
                name + ': is locked by another updater')
            lockers[name] = self

    def _unlock(self):
        with self._classlock:
            if self._islocked:
                del self._dblockers[self.name]

    @property
    def needed(self):
        """ ``True`` if the database is unversioned or if its version is less
            then the maximum defined.
        """
        self._validate_locked()
        version, target = self._version, self._target
        log.d('%s update check: version=[%s] target=[%s]',
              self.name, version, target)
        return version is None or version < target

    @property
    def requires_consent(self):
        """`True` if any missing updates require user consent."""
        self._validate_locked()
        for version in self._updates_due:
            if 'prompt' in self.desc[version]:
                return True
        return False

    @property
    def prompts(self):
        """ Return an iterable of string prompts for updates that require user
            consent.
        """
        self._validate_locked()
        for version in self._updates_due:
            if 'prompt' in self.desc[version]:
                yield self.desc[version]['prompt']

    def run(self):
        """Update database schema to the highest possible version."""
        self._validate_locked()
        log.i('%r: updating database schema', self.name)
        log.d('from version %r to %r', self._version, self._target)
        if None is self._version:
            self._init_with_version(self._target)
        else:
            for version in self._updates_due:
                self._update_to_version(version)

    def reset(self):
        """Delete all content from the database along with supporting structures."""
        self._validate_locked()
        version = self._version
        log.i('%s: resetting database', self.name)
        log.d('version: %s', version)
        if None is version:
            log.d('nothing to reset.')
            return
        with self.db.connection() as cxn:
            cxn.executescript(self.desc[version]['drop.sql'])
            cxn.executescript(self._metatable['drop.sql'])
            cxn.executescript(self._metatable['create.sql'])
            self._setversion(None, cxn)
        cxn.close()

    def _validate_locked(self):
        assert self._islocked, 'must be called in updater context (use "with")'

    @property
    def _version(self):
        try:
            return self.__version
        except AttributeError:
            maxv = self.db.execute('SELECT MAX(version) FROM _meta_version').fetchone()
            maxv = maxv and maxv[0]
            self.__version = maxv if maxv is None else str(maxv)
            return self.__version

    def _setversion(self, value, conn=None):
        del self.__version
        conn = conn or self.db.connection
        log.d('{0}: set version to {1}'.format(self.name, value))
        conn.execute('INSERT INTO _meta_version(version) VALUES (?)', (value,))

    @property
    def _target(self):
        return max(self.desc)

    @property
    def _updates_due(self):
        if None is self._version:
            return ()
        versions = sorted(self.desc)
        start = versions.index(self._version) + 1
        return versions[start:]

    def _init_meta(self):
        content = self.db.execute('SELECT type, name FROM sqlite_master;').fetchall()
        content = [(t, n) for t, n in content if n != '_meta_version' and not n.startswith('sqlite')]
        with self.db.connection() as cxn:
            cxn.isolation_level = "EXCLUSIVE"
            cxn.executescript(self._metatable['create.sql'])
            if content and self._version is None:
                log.d('%s: unversioned content found: %r', self.name, content)
                self._setversion(0, cxn)
        cxn.isolation_level = ''
        cxn.close()

    def _init_with_version(self, vnum):
        log.d('initializing database %r to version %s', self.name, vnum)
        cxn = self.db.connection()
        cxn.isolation_level = None  # autocommit
        self._runscript(vnum, 'create.sql', cxn)
        self._run_afterscript_if_exists(vnum, cxn)
        self._setversion(vnum, cxn)
        cxn.isolation_level = ''
        cxn.close()

    def _update_to_version(self, vnum):
        log.d('updating database %r to version %d', self.name, vnum)
        cxn = self.db.connection()
        cxn.isolation_level = None  # autocommit
        self._runscript(vnum, 'update.sql', cxn)
        self._run_afterscript_if_exists(vnum, cxn)
        self._setversion(vnum, cxn)
        cxn.isolation_level = ''
        cxn.close()

    def _run_afterscript_if_exists(self, vnum, conn):
        try:
            self._runscript(vnum, 'after.sql', conn)
        except KeyError:
            pass

    def _runscript(self, version, name, cxn):
        try:
            cxn.executescript(self.desc[version][name])
        except sqlite3.OperationalError:
            # update scripts are tested, so the problem's seems to be sqlite
            # itself
            log.x(_('Exception while updating database schema.'))
            log.e(_('Database error. This is probably due to your version of'
                    ' sqlite being too old. Try updating sqlite3 and'
                    ' updating python. If the problem persists, you will need'
                    ' to delete the database at ' + self.db.dblocation))
            import sys
            sys.exit(1)

class TmpConnector(AbstractConnector):
    """Special SQLite Connector that uses its own temporary directory.

    As with the sqlite3 module in general, sharing connections is NOT THREADSAFE.
    """
    def __init__(self):
        self.testdirname = tempfile.mkdtemp(suffix=self.__class__.__name__)

    def __del__(self):
        import shutil
        shutil.rmtree(self.testdirname, ignore_errors=True)

    def connection(self, dbname):
        return sqlite3.connect(self.dblocation(dbname))

    def dblocation(self, basename):
        return os.path.join(self.testdirname, basename)


class MemConnector(AbstractConnector):  # NOT threadsafe
    """Special SQLite3 Connector that reuses THE SAME memory connection for
    each dbname. This connection is NOT CLOSABLE by normal means.
    Therefore, this class is NOT THREADSAFE.
    """
    def __init__(self):
        self.connections = {}
        self.Connection = type(
            self.__class__.__name__ + '.Connection',
            (sqlite3.Connection,),
            {'close': self.__disconnect})

    def __del__(self):
        self.__disconnect(seriously=True)

    def __repr__(self):
        return '{name} [{id}]'.format(
            name=self.__class__.__name__,
            id=hex(id(self))
        )

    def connection(self, dbname):
        return self.__connect(dbname)

    def dblocation(self, _):
        return ':memory:'

    def __connect(self, dbname):
        try:
            return self.connections[dbname]
        except KeyError:
            cxn = sqlite3.connect(':memory:', factory=self.Connection)
            return self.connections.setdefault(dbname, cxn)

    def __disconnect(self, seriously=False):
        if seriously:
            connections = dict(self.connections)
            self.connections.clear()
            for cxn in connections.values():
                super(cxn.__class__, cxn).close()

########NEW FILE########
__FILENAME__ = zipstream
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
This library was created by SpiderOak, Inc. and is released under the GPLv3.
https://github.com/gourneau/SpiderOak-zipstream

Iterable ZIP archive genrator.

Derived directly from zipfile.py
"""
import struct, os, time, sys
import binascii
import codecs

try:
    import zlib # We may need its compression method
except ImportError:
    zlib = None

__all__ = ["ZIP_STORED", "ZIP_DEFLATED", "ZipStream"]


ZIP64_LIMIT= (1 << 31) - 1

# constants for Zip file compression methods
ZIP_STORED = 0
ZIP_DEFLATED = 8
# Other ZIP compression methods not supported

# Here are some struct module formats for reading headers
structEndArchive = b"<4s4H2lH"     # 9 items, end of archive, 22 bytes
stringEndArchive = b"PK\005\006"   # magic number for end of archive record
structCentralDir = b"<4s4B4HILL5HLI"# 19 items, central directory, 46 bytes
stringCentralDir = b"PK\001\002"   # magic number for central directory
structFileHeader = b"<4s2B4HlLL2H"  # 12 items, file header record, 30 bytes
stringFileHeader = b"PK\003\004"   # magic number for file header
structEndArchive64Locator = b"<4slql" # 4 items, locate Zip64 header, 20 bytes
stringEndArchive64Locator = b"PK\x06\x07" # magic token for locator header
structEndArchive64 = b"<4sqhhllqqqq" # 10 items, end of archive (Zip64), 56 bytes
stringEndArchive64 = b"PK\x06\x06" # magic token for Zip64 header
stringDataDescriptor = b"PK\x07\x08" # magic number for data descriptor

# indexes of entries in the central directory structure
_CD_SIGNATURE = 0
_CD_CREATE_VERSION = 1
_CD_CREATE_SYSTEM = 2
_CD_EXTRACT_VERSION = 3
_CD_EXTRACT_SYSTEM = 4                  # is this meaningful?
_CD_FLAG_BITS = 5
_CD_COMPRESS_TYPE = 6
_CD_TIME = 7
_CD_DATE = 8
_CD_CRC = 9
_CD_COMPRESSED_SIZE = 10
_CD_UNCOMPRESSED_SIZE = 11
_CD_FILENAME_LENGTH = 12
_CD_EXTRA_FIELD_LENGTH = 13
_CD_COMMENT_LENGTH = 14
_CD_DISK_NUMBER_START = 15
_CD_INTERNAL_FILE_ATTRIBUTES = 16
_CD_EXTERNAL_FILE_ATTRIBUTES = 17
_CD_LOCAL_HEADER_OFFSET = 18

# indexes of entries in the local file header structure
_FH_SIGNATURE = 0
_FH_EXTRACT_VERSION = 1
_FH_EXTRACT_SYSTEM = 2                  # is this meaningful?
_FH_GENERAL_PURPOSE_FLAG_BITS = 3
_FH_COMPRESSION_METHOD = 4
_FH_LAST_MOD_TIME = 5
_FH_LAST_MOD_DATE = 6
_FH_CRC = 7
_FH_COMPRESSED_SIZE = 8
_FH_UNCOMPRESSED_SIZE = 9
_FH_FILENAME_LENGTH = 10
_FH_EXTRA_FIELD_LENGTH = 11


class ZipInfo (object):
    """Class with attributes describing each file in the ZIP archive."""

    __slots__ = (
            'orig_filename',
            'filename',
            'date_time',
            'compress_type',
            'comment',
            'extra',
            'create_system',
            'create_version',
            'extract_version',
            'reserved',
            'flag_bits',
            'volume',
            'internal_attr',
            'external_attr',
            'header_offset',
            'CRC',
            'compress_size',
            'file_size',
        )

    def __init__(self, filename="NoName", date_time=(1980,1,1,0,0,0)):
        self.orig_filename = filename   # Original file name in archive

        # Terminate the file name at the first null byte.  Null bytes in file
        # names are used as tricks by viruses in archives.
        null_byte = filename.find(chr(0))
        if null_byte >= 0:
            filename = filename[0:null_byte]
        # This is used to ensure paths in generated ZIP files always use
        # forward slashes as the directory separator, as required by the
        # ZIP format specification.
        if os.sep != "/" and os.sep in filename:
            filename = filename.replace(os.sep, "/")

        self.filename = codecs.encode(filename, 'UTF-8')        # Normalized file name
        self.date_time = date_time      # year, month, day, hour, min, sec
        # Standard values:
        self.compress_type = ZIP_STORED # Type of compression for the file
        self.comment = b""               # Comment for each file
        self.extra = b""                 # ZIP extra data
        if sys.platform == 'win32':
            self.create_system = 0          # System which created ZIP archive
        else:
            # Assume everything else is unix-y
            self.create_system = 3          # System which created ZIP archive
        self.create_version = 20        # Version which created ZIP archive
        self.extract_version = 20       # Version needed to extract archive
        self.reserved = 0               # Must be zero
        self.flag_bits = 0x08           # ZIP flag bits, bit 3 indicates presence of data descriptor
        self.volume = 0                 # Volume number of file header
        self.internal_attr = 0          # Internal attributes
        self.external_attr = 0          # External file attributes
        # Other attributes are set by class ZipFile:
        # header_offset         Byte offset to the file header
        # CRC                   CRC-32 of the uncompressed file
        # compress_size         Size of the compressed file
        # file_size             Size of the uncompressed file

    def DataDescriptor(self):
        if self.compress_size > ZIP64_LIMIT or self.file_size > ZIP64_LIMIT:
            fmt = "<4sIQQ"
        else:
            fmt = "<4sILL"
        return struct.pack(fmt, stringDataDescriptor, self.CRC, self.compress_size, self.file_size)

    def FileHeader(self):
        """Return the per-file header as a string."""
        dt = self.date_time
        dosdate = (dt[0] - 1980) << 9 | dt[1] << 5 | dt[2]
        dostime = dt[3] << 11 | dt[4] << 5 | (dt[5] // 2)
        if self.flag_bits & 0x08:
            # Set these to zero because we write them after the file data
            CRC = compress_size = file_size = 0
        else:
            CRC = self.CRC
            compress_size = self.compress_size
            file_size = self.file_size

        extra = self.extra

        if file_size > ZIP64_LIMIT or compress_size > ZIP64_LIMIT:
            # File is larger than what fits into a 4 byte integer,
            # fall back to the ZIP64 extension
            fmt = '<hhqq'
            extra = extra + struct.pack(fmt,
                    1, struct.calcsize(fmt)-4, file_size, compress_size)
            file_size = 0xffffffff # -1
            compress_size = 0xffffffff # -1
            self.extract_version = max(45, self.extract_version)
            self.create_version = max(45, self.extract_version)

        header = struct.pack(structFileHeader, stringFileHeader,
                 self.extract_version, self.reserved, self.flag_bits,
                 self.compress_type, dostime, dosdate, CRC,
                 compress_size, file_size,
                 len(self.filename), len(extra))
        return header + self.filename + extra



class ZipStream:
    """
    """

    def __init__(self, paths, arc_path='', compression=ZIP_DEFLATED):
        if compression == ZIP_STORED:
            pass
        elif compression == ZIP_DEFLATED:
            if not zlib:
                raise RuntimeError("Compression requires the (missing) zlib module")
        else:
            raise RuntimeError("That compression method is not supported")

        self.filelist = []              # List of ZipInfo instances for archive
        self.compression = compression  # Method of compression
        self.paths = paths              # source paths
        self.arc_path = arc_path        # top level path in archive
        self.data_ptr = 0               # Keep track of location inside archive

    def __iter__(self):
        for path in self.paths:
            for data in self.zip_path(path, self.arc_path):
                yield data

        yield self.archive_footer()

    def update_data_ptr(self, data):
        """As data is added to the archive, update a pointer so we can determine
        the location of various structures as they are generated.

        data -- data to be added to archive

        Returns data
        """
        self.data_ptr += len(data)
        return data

    def zip_path(self, path, archive_dir_name):
        """Recursively generate data to add directory tree or file pointed to by
        path to the archive. Results in archive containing

        archive_dir_name/basename(path)
        archive_dir_name/basename(path)/*
        archive_dir_name/basename(path)/*/*
        .
        .
        .
        

        path -- path to file or directory
        archive_dir_name -- name of containing directory in archive
        """
        if os.path.isdir(path):
            dir_name = os.path.basename(path)
            for name in os.listdir(path):
                r_path = os.path.join(path, name)
                r_archive_dir_name = os.path.join(archive_dir_name, dir_name)
                for data in self.zip_path(r_path, r_archive_dir_name):
                    yield data
        else:
            archive_path = os.path.join(archive_dir_name, os.path.basename(path))
            for data in self.zip_file(path, archive_path):
                yield data


    def zip_file(self, filename, arcname=None, compress_type=None):
        """Generates data to add file at 'filename' to an archive.

        filename -- path to file to add to arcive
        arcname -- path of file inside the archive
        compress_type -- unused in ZipStream, just use self.compression


        This function generates the data corresponding to the fields:

        [local file header n]
        [file data n]
        [data descriptor n]

        as described in section V. of the PKZIP Application Note:
        http://www.pkware.com/business_and_developers/developer/appnote/
        """
        st = os.stat(filename)
        mtime = time.localtime(st.st_mtime)
        date_time = mtime[0:6]
        # Create ZipInfo instance to store file information
        if arcname is None:
            arcname = filename
        arcname = os.path.normpath(os.path.splitdrive(arcname)[1])
        while arcname[0] in (os.sep, os.altsep):
            arcname = arcname[1:]
        zinfo = ZipInfo(arcname, date_time)
        zinfo.external_attr = (st[0] & 0xFFFF) << 16      # Unix attributes
        if compress_type is None:
            zinfo.compress_type = self.compression
        else:
            zinfo.compress_type = compress_type

        zinfo.file_size = st.st_size
        zinfo.header_offset = self.data_ptr    # Start of header bytes

        fp = open(filename, "rb")
        zinfo.CRC = CRC = 0
        zinfo.compress_size = compress_size = 0
        zinfo.file_size = file_size = 0
        yield self.update_data_ptr(zinfo.FileHeader())
        if zinfo.compress_type == ZIP_DEFLATED:
            cmpr = zlib.compressobj(zlib.Z_DEFAULT_COMPRESSION,
                 zlib.DEFLATED, -15)
        else:
            cmpr = None
        while 1:
            buf = fp.read(1024 * 8)
            if not buf:
                break
            file_size = file_size + len(buf)
            CRC = binascii.crc32(buf, CRC)
            if cmpr:
                buf = cmpr.compress(buf)
                compress_size = compress_size + len(buf)
            yield self.update_data_ptr(buf)
        fp.close()
        if cmpr:
            buf = cmpr.flush()
            compress_size = compress_size + len(buf)
            yield self.update_data_ptr(buf)
            zinfo.compress_size = compress_size
        else:
            zinfo.compress_size = file_size
        zinfo.CRC = abs(CRC)
        zinfo.file_size = file_size
        yield self.update_data_ptr(zinfo.DataDescriptor())
        self.filelist.append(zinfo)


    def archive_footer(self):
        """Returns data to finish off an archive based on the files already
        added via zip_file(...).  The data returned corresponds to the fields:

        [archive decryption header] 
        [archive extra data record] 
        [central directory]
        [zip64 end of central directory record]
        [zip64 end of central directory locator] 
        [end of central directory record]

        as described in section V. of the PKZIP Application Note:
        http://www.pkware.com/business_and_developers/developer/appnote/
        """
        data = []
        count = 0
        pos1 = self.data_ptr
        for zinfo in self.filelist:         # write central directory
            count = count + 1
            dt = zinfo.date_time
            dosdate = (dt[0] - 1980) << 9 | dt[1] << 5 | dt[2]
            dostime = dt[3] << 11 | dt[4] << 5 | (dt[5] // 2)
            extra = []
            if zinfo.file_size > ZIP64_LIMIT or zinfo.compress_size > ZIP64_LIMIT:
                extra.append(zinfo.file_size)
                extra.append(zinfo.compress_size)
                file_size = 0xffffffff #-1
                compress_size = 0xffffffff #-1
            else:
                file_size = zinfo.file_size
                compress_size = zinfo.compress_size

            if zinfo.header_offset > ZIP64_LIMIT:
                extra.append(zinfo.header_offset)
                header_offset = -1  # struct "l" format:  32 one bits
            else:
                header_offset = zinfo.header_offset

            extra_data = zinfo.extra
            if extra:
                # Append a ZIP64 field to the extra's
                extra_data = struct.pack('<hh' + 'q'*len(extra),1, 8*len(extra), *extra) + extra_data
                extract_version = max(45, zinfo.extract_version)
                create_version = max(45, zinfo.create_version)
            else:
                extract_version = zinfo.extract_version
                create_version = zinfo.create_version
            centdir = struct.pack(structCentralDir,
                                  stringCentralDir, create_version,
                                  zinfo.create_system, extract_version, zinfo.reserved,
                                  zinfo.flag_bits, zinfo.compress_type, dostime, dosdate,
                                  zinfo.CRC, compress_size, file_size,
                                  len(zinfo.filename), len(extra_data), len(zinfo.comment),
                                  0, zinfo.internal_attr, zinfo.external_attr,
                                  header_offset)
            
            data.append( self.update_data_ptr(centdir))
            data.append( self.update_data_ptr(zinfo.filename))
            data.append( self.update_data_ptr(extra_data))
            data.append( self.update_data_ptr(zinfo.comment))

        pos2 = self.data_ptr
        # Write end-of-zip-archive record
        if pos1 > ZIP64_LIMIT:
            # Need to write the ZIP64 end-of-archive records
            zip64endrec = struct.pack(structEndArchive64, stringEndArchive64,
                                      44, 45, 45, 0, 0, count, count, pos2 - pos1, pos1)
            data.append( self.update_data_ptr(zip64endrec))

            zip64locrec = struct.pack(structEndArchive64Locator,
                                      stringEndArchive64Locator, 0, pos2, 1)
            data.append( self.update_data_ptr(zip64locrec))

            # XXX Why is `pos3` computed next?  It's never referenced.
            pos3 = self.data_ptr
            endrec = struct.pack(structEndArchive, stringEndArchive,
                                 0, 0, count, count, pos2 - pos1, -1, 0)
            data.append( self.update_data_ptr(endrec))

        else:
            endrec = struct.pack(structEndArchive, stringEndArchive,
                                 0, 0, count, count, pos2 - pos1, pos1, 0)
            data.append( self.update_data_ptr(endrec))

        return b''.join(data)


if __name__ == "__main__":
    zipfile = sys.argv[1]
    path = sys.argv[2]

    zf = open(zipfile, 'wb')

    for data in ZipStream(path):
        zf.write(data)

    zf.close()


########NEW FILE########
__FILENAME__ = httphandler
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# CherryMusic - a standalone music server
# Copyright (c) 2012 - 2014 Tom Wallroth & Tilman Boerner
#
# Project page:
#   http://fomori.org/cherrymusic/
# Sources on github:
#   http://github.com/devsnd/cherrymusic/
#
# CherryMusic is based on
#   jPlayer (GPL/MIT license) http://www.jplayer.org/
#   CherryPy (BSD license) http://www.cherrypy.org/
#
# licensed under GNU GPL version 3 (or later)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
#

"""This class provides the api to talk to the client.
It will then call the cherrymodel, to get the
requested information"""

import os  # shouldn't have to list any folder in the future!
import json
import cherrypy
import codecs
import sys

try:
    from urllib.parse import unquote
except ImportError:
    from backport.urllib.parse import unquote
try:
    from urllib import parse
except ImportError:
    from backport.urllib import parse


import audiotranscode

from cherrymusicserver import userdb
from cherrymusicserver import log
from cherrymusicserver import albumartfetcher
from cherrymusicserver import service
from cherrymusicserver.pathprovider import readRes
from cherrymusicserver.pathprovider import albumArtFilePath
import cherrymusicserver as cherry
import cherrymusicserver.metainfo as metainfo
from cherrymusicserver.util import Performance, MemoryZipFile

from cherrymusicserver.ext import zipstream
import time

debug = True


@service.user(model='cherrymodel', playlistdb='playlist',
              useroptions='useroptions', userdb='users')
class HTTPHandler(object):
    def __init__(self, config):
        self.config = config

        template_main = 'res/dist/main.html'
        template_login = 'res/login.html'
        template_firstrun = 'res/firstrun.html'

        self.mainpage = readRes(template_main)
        self.loginpage = readRes(template_login)
        self.firstrunpage = readRes(template_firstrun)

        self.handlers = {
            'search': self.api_search,
            'rememberplaylist': self.api_rememberplaylist,
            'saveplaylist': self.api_saveplaylist,
            'loadplaylist': self.api_loadplaylist,
            'generaterandomplaylist': self.api_generaterandomplaylist,
            'deleteplaylist': self.api_deleteplaylist,
            'getmotd': self.api_getmotd,
            'restoreplaylist': self.api_restoreplaylist,
            'getplayables': self.api_getplayables,
            'getuserlist': self.api_getuserlist,
            'adduser': self.api_adduser,
            'userdelete': self.api_userdelete,
            'userchangepassword': self.api_userchangepassword,
            'showplaylists': self.api_showplaylists,
            'logout': self.api_logout,
            'downloadpls': self.api_downloadpls,
            'downloadm3u': self.api_downloadm3u,
            'getsonginfo': self.api_getsonginfo,
            'getencoders': self.api_getencoders,
            'getdecoders': self.api_getdecoders,
            'transcodingenabled': self.api_transcodingenabled,
            'updatedb': self.api_updatedb,
            'getconfiguration': self.api_getconfiguration,
            'compactlistdir': self.api_compactlistdir,
            'listdir': self.api_listdir,
            'fetchalbumart': self.api_fetchalbumart,
            'fetchalbumarturls': self.api_fetchalbumarturls,
            'albumart_set': self.api_albumart_set,
            'heartbeat': self.api_heartbeat,
            'getuseroptions': self.api_getuseroptions,
            'setuseroption': self.api_setuseroption,
            'changeplaylist': self.api_changeplaylist,
            'downloadcheck': self.api_downloadcheck,
            'setuseroptionfor': self.api_setuseroptionfor,
        }

    def issecure(self, url):
        return parse.urlparse(url).scheme == 'https'

    def getBaseUrl(self, redirect_unencrypted=False):
        ipAndPort = parse.urlparse(cherrypy.url()).netloc
        is_secure_connection = self.issecure(cherrypy.url())
        ssl_enabled = cherry.config['server.ssl_enabled']
        if ssl_enabled and not is_secure_connection:
            log.d(_('Not secure, redirecting...'))
            ip = ipAndPort[:ipAndPort.rindex(':')]
            url = 'https://' + ip + ':' + str(cherry.config['server.ssl_port'])
            if redirect_unencrypted:
                raise cherrypy.HTTPRedirect(url, 302)
        else:
            url = 'http://' + ipAndPort
        return url

    def index(self, *args, **kwargs):
        self.getBaseUrl(redirect_unencrypted=True)
        firstrun = 0 == self.userdb.getUserCount()
        show_page = self.mainpage #generated main.html from devel.html
        if 'devel' in kwargs:
            #reload pages everytime in devel mode
            show_page = readRes('res/devel.html')
            self.loginpage = readRes('res/login.html')
            self.firstrunpage = readRes('res/firstrun.html')
        if 'login' in kwargs:
            username = kwargs.get('username', '')
            password = kwargs.get('password', '')
            login_action = kwargs.get('login', '')
            if login_action == 'login':
                self.session_auth(username, password)
                if cherrypy.session['username']:
                    username = cherrypy.session['username']
                    log.i(_('user {name} just logged in.').format(name=username))
            elif login_action == 'create admin user':
                if firstrun:
                    if username.strip() and password.strip():
                        self.userdb.addUser(username, password, True)
                        self.session_auth(username, password)
                        return show_page
                else:
                    return "No, you can't."
        if firstrun:
            return self.firstrunpage
        else:
            if self.isAuthorized():
                return show_page
            else:
                return self.loginpage
    index.exposed = True

    def isAuthorized(self):
        try:
            sessionUsername = cherrypy.session.get('username', None)
            sessionUserId = cherrypy.session.get('userid', -1)
            nameById = self.userdb.getNameById(sessionUserId)
        except (UnicodeDecodeError, ValueError) as e:
            # workaround for python2/python3 jump, filed bug in cherrypy
            # https://bitbucket.org/cherrypy/cherrypy/issue/1216/sessions-python2-3-compability-unsupported
            log.w(_('''
            Dropping all sessions! Try not to change between python 2 and 3,
            everybody has to relogin now.'''))
            cherrypy.session.delete()
            sessionUsername = None
        if sessionUsername is None:
            if self.autoLoginActive():
                cherrypy.session['username'] = self.userdb.getNameById(1)
                cherrypy.session['userid'] = 1
                cherrypy.session['admin'] = True
                return True
            else:
                return False
        elif sessionUsername != nameById:
            self.api_logout(value=None)
            return False
        return True

    def autoLoginActive(self):
        is_loopback = cherrypy.request.remote.ip in ('127.0.0.1', '::1')
        if is_loopback and cherry.config['server.localhost_auto_login']:
            return True
        return False

    def session_auth(self, username, password):
        user = self.userdb.auth(username, password)
        allow_remote = cherry.config['server.permit_remote_admin_login']
        is_loopback = cherrypy.request.remote.ip in ('127.0.0.1', '::1')
        if not is_loopback and user.isadmin and not allow_remote:
            log.i(_('Rejected remote admin login from user: {name}').format(name=user.name))
            user = userdb.User.nobody()
        cherrypy.session['username'] = user.name
        cherrypy.session['userid'] = user.uid
        cherrypy.session['admin'] = user.isadmin

    def getUserId(self):
        try:
            return cherrypy.session['userid']
        except KeyError:
            cherrypy.lib.sessions.expire()
            cherrypy.HTTPRedirect(cherrypy.url(), 302)
            return ''

    def trans(self, newformat, *path, **params):
        ''' Transcodes the track given as ``path`` into ``newformat``.

            Streams the response of the corresponding
            ``audiotranscode.AudioTranscode().transcodeStream()`` call.

            params:
                bitrate: int for kbps. None or < 1 for default
        '''
        if not self.isAuthorized():
            raise cherrypy.HTTPRedirect(self.getBaseUrl(), 302)
        cherrypy.session.release_lock()
        if cherry.config['media.transcode'] and path:

            # bitrate
            bitrate = params.pop('bitrate', None) or None  # catch empty strings
            if bitrate:
                try:
                    bitrate = max(0, int(bitrate)) or None  # None if < 1
                except (TypeError, ValueError):
                    raise cherrypy.HTTPError(400, "Bad query: "
                        "bitrate ({0!r}) must be an integer".format(str(bitrate)))

            # path
            path = os.path.sep.join(path)
            if sys.version_info < (3, 0):       # workaround for #327 (cherrypy issue)
                path = path.decode('utf-8')     # make it work with non-ascii
            else:
                path = codecs.decode(codecs.encode(path, 'latin1'), 'utf-8')
            fullpath = os.path.join(cherry.config['media.basedir'], path)

            starttime = int(params.pop('starttime', 0))

            transcoder = audiotranscode.AudioTranscode()
            mimetype = transcoder.mimeType(newformat)
            cherrypy.response.headers["Content-Type"] = mimetype
            try:
                return transcoder.transcodeStream(fullpath, newformat,
                            bitrate=bitrate, starttime=starttime)
            except audiotranscode.TranscodeError as e:
                raise cherrypy.HTTPError(404, e.value)
    trans.exposed = True
    trans._cp_config = {'response.stream': True}


    def api(self, *args, **kwargs):
        """calls the appropriate handler from the handlers
        dict, if available. handlers having noauth set to
        true do not need authentification to work.
        """
        #check action
        action = args[0] if args else ''
        if not action in self.handlers:
            return "Error: no such action. '%s'" % action
        #authorize if not explicitly deactivated
        handler = self.handlers[action]
        needsAuth = not ('noauth' in dir(handler) and handler.noauth)
        if needsAuth and not self.isAuthorized():
            raise cherrypy.HTTPError(401, 'Unauthorized')
        handler_args = {}
        if 'data' in kwargs:
            handler_args = json.loads(kwargs['data'])
        is_binary = ('binary' in dir(handler) and handler.binary)
        if is_binary:
            return handler(**handler_args)
        else:
            return json.dumps({'data': handler(**handler_args)})

    api.exposed = True

    def download_check_files(self, filelist):
        # only admins and allowed users may download
        if not cherrypy.session['admin']:
            uo = self.useroptions.forUser(self.getUserId())
            if not uo.getOptionValue('media.may_download'):
                return 'not_permitted'
        # make sure nobody tries to escape from basedir
        for f in filelist:
            if '/../' in f:
                return 'invalid_file'
        # make sure all files are smaller than maximum download size
        size_limit = cherry.config['media.maximum_download_size']
        try:
            if self.model.file_size_within_limit(filelist, size_limit):
                return 'ok'
            else:
                return 'too_big'
        except OSError as e:        # use OSError for python2 compatibility
            return str(e)

    def api_downloadcheck(self, filelist):
        status = self.download_check_files(filelist)
        if status == 'not_permitted':
            return """You are not allowed to download files."""
        elif status == 'invalid_file':
            return "Error: invalid filename found in {list}".format(list=filelist)
        elif status == 'too_big':
            size_limit = cherry.config['media.maximum_download_size']
            return """Can't download: Playlist is bigger than {maxsize} mB.
                        The server administrator can change this configuration.
                        """.format(maxsize=size_limit/1024/1024)
        elif status == 'ok':
            return status
        else:
            message = "Error status check for download: {status!r}".format(status=status)
            log.e(message)
            return message

    def download(self, value):
        if not self.isAuthorized():
            raise cherrypy.HTTPError(401, 'Unauthorized')
        filelist = [filepath for filepath in json.loads(unquote(value))]
        dlstatus = self.download_check_files(filelist)
        if dlstatus == 'ok':
            cherrypy.session.release_lock()
            zipmime = 'application/x-zip-compressed'
            cherrypy.response.headers["Content-Type"] = zipmime
            zipname = 'attachment; filename="music.zip"'
            cherrypy.response.headers['Content-Disposition'] = zipname
            basedir = cherry.config['media.basedir']
            fullpath_filelist = [os.path.join(basedir, f) for f in filelist]
            return zipstream.ZipStream(fullpath_filelist)
        else:
            return dlstatus
    download.exposed = True
    download._cp_config = {'response.stream': True}

    def api_getuseroptions(self):
        uo = self.useroptions.forUser(self.getUserId())
        uco = uo.getChangableOptions()
        if cherrypy.session['admin']:
            uco['media'].update({'may_download': True})
        else:
            uco['media'].update({'may_download': uo.getOptionValue('media.may_download')})
        return uco

    def api_heartbeat(self):
        uo = self.useroptions.forUser(self.getUserId())
        uo.setOption('last_time_online', int(time.time()))

    def api_setuseroption(self, optionkey, optionval):
        uo = self.useroptions.forUser(self.getUserId())
        uo.setOption(optionkey, optionval)
        return "success"
    def api_setuseroptionfor(self, userid, optionkey, optionval):
        if cherrypy.session['admin']:
            uo = self.useroptions.forUser(userid)
            uo.setOption(optionkey, optionval)
            return "success"
        else:
            return "error: not permitted. Only admins can change other users options"

    def api_fetchalbumarturls(self, searchterm):
        if not cherrypy.session['admin']:
            raise cherrypy.HTTPError(401, 'Unauthorized')
        cherrypy.session.release_lock()
        fetcher = albumartfetcher.AlbumArtFetcher()
        imgurls = fetcher.fetchurls(searchterm)
        # show no more than 10 images
        return imgurls[:min(len(imgurls), 10)]

    def api_albumart_set(self, directory, imageurl):
        if not cherrypy.session['admin']:
            raise cherrypy.HTTPError(401, 'Unauthorized')
        b64imgpath = albumArtFilePath(directory)
        fetcher = albumartfetcher.AlbumArtFetcher()
        data, header = fetcher.retrieveData(imageurl)
        self.albumartcache_save(b64imgpath, data)

    def api_fetchalbumart(self, directory):
        cherrypy.session.release_lock()
        default_folder_image = "/res/img/folder.png"

        #try getting a cached album art image
        b64imgpath = albumArtFilePath(directory)
        img_data = self.albumartcache_load(b64imgpath)
        if img_data:
            cherrypy.response.headers["Content-Length"] = len(img_data)
            return img_data

        #try getting album art inside local folder
        fetcher = albumartfetcher.AlbumArtFetcher()
        localpath = os.path.join(cherry.config['media.basedir'], directory)
        header, data, resized = fetcher.fetchLocal(localpath)

        if header:
            if resized:
                #cache resized image for next time
                self.albumartcache_save(b64imgpath, data)
            cherrypy.response.headers.update(header)
            return data
        elif cherry.config['media.fetch_album_art']:
            #fetch album art from online source
            try:
                foldername = os.path.basename(directory)
                keywords = foldername
                log.i(_("Fetching album art for keywords {keywords!r}").format(keywords=keywords))
                header, data = fetcher.fetch(keywords)
                if header:
                    cherrypy.response.headers.update(header)
                    self.albumartcache_save(b64imgpath, data)
                    return data
                else:
                    # albumart fetcher failed, so we serve a standard image
                    raise cherrypy.HTTPRedirect(default_folder_image, 302)
            except:
                # albumart fetcher threw exception, so we serve a standard image
                raise cherrypy.HTTPRedirect(default_folder_image, 302)
        else:
            # no local album art found, online fetching deactivated, show default
            raise cherrypy.HTTPRedirect(default_folder_image, 302)
    api_fetchalbumart.noauth = True
    api_fetchalbumart.binary = True

    def albumartcache_load(self, imgb64path):
        if os.path.exists(imgb64path):
            with open(imgb64path, 'rb') as f:
                return f.read()

    def albumartcache_save(self, path, data):
        with open(path, 'wb') as f:
            f.write(data)

    def api_compactlistdir(self, directory, filterstr=None):
        files_to_list = self.model.listdir(directory, filterstr)
        return [entry.to_dict() for entry in files_to_list]

    def api_listdir(self, directory=''):
        return [entry.to_dict() for entry in self.model.listdir(directory)]

    def api_search(self, searchstring):
        if not searchstring.strip():
            jsonresults = '[]'
        else:
            with Performance(_('processing whole search request')):
                searchresults = self.model.search(searchstring.strip())
                with Performance(_('rendering search results as json')):
                    jsonresults = [entry.to_dict() for entry in searchresults]
        return jsonresults

    def api_rememberplaylist(self, playlist):
        cherrypy.session['playlist'] = playlist

    def api_saveplaylist(self, playlist, public, playlistname, overwrite=False):
        res = self.playlistdb.savePlaylist(
            userid=self.getUserId(),
            public=1 if public else 0,
            playlist=playlist,
            playlisttitle=playlistname,
            overwrite=overwrite)
        if res == "success":
            return res
        else:
            raise cherrypy.HTTPError(400, res)

    def api_deleteplaylist(self, playlistid):
        res = self.playlistdb.deletePlaylist(playlistid,
                                             self.getUserId(),
                                             override_owner=False)
        if res == "success":
            return res
        else:
            # not the ideal status code but we don't know the actual
            # cause without parsing res
            raise cherrypy.HTTPError(400, res)

    def api_loadplaylist(self, playlistid):
        return [entry.to_dict() for entry in self.playlistdb.loadPlaylist(
                                        playlistid=playlistid,
                                        userid=self.getUserId()
                                        )]

    def api_generaterandomplaylist(self):
        return [entry.to_dict() for entry in self.model.randomMusicEntries(50)]

    def api_changeplaylist(self, plid, attribute, value):
        if attribute == 'public':
            is_valid = type(value) == bool and type(plid) == int
            if is_valid:
                return self.playlistdb.setPublic(userid=self.getUserId(),
                                                 plid=plid,
                                                 public=value)

    def api_getmotd(self):
        if cherrypy.session['admin'] and cherry.config['general.update_notification']:
            cherrypy.session.release_lock()
            new_versions = self.model.check_for_updates()
            if new_versions:
                newest_version = new_versions[0]['version']
                features = []
                fixes = []
                for version in new_versions:
                    for update in version['features']:
                        if update.startswith('FEATURE:'):
                            features.append(update[len('FEATURE:'):])
                        elif update.startswith('FIX:'):
                            fixes.append(update[len('FIX:'):])
                        elif update.startswith('FIXED:'):
                            fixes.append(update[len('FIXED:'):])
                retdata = {'type': 'update', 'data': {}}
                retdata['data']['version'] = newest_version
                retdata['data']['features'] = features
                retdata['data']['fixes'] = fixes
                return retdata
        return {'type': 'wisdom', 'data': self.model.motd()}

    def api_restoreplaylist(self):
        session_playlist = cherrypy.session.get('playlist', [])
        return session_playlist

    def api_getplayables(self):
        """DEPRECATED"""
        return json.dumps(cherry.config['media.playable'])

    def api_getuserlist(self):
        if cherrypy.session['admin']:
            userlist = self.userdb.getUserList()
            for user in userlist:
                if user['id'] == cherrypy.session['userid']:
                    user['deletable'] = False
                user_options = self.useroptions.forUser(user['id'])
                t = user_options.getOptionValue('last_time_online')
                may_download = user_options.getOptionValue('media.may_download')
                user['last_time_online'] = t
                user['may_download'] = may_download
            sortfunc = lambda user: user['last_time_online']
            userlist = sorted(userlist, key=sortfunc, reverse=True)
            return json.dumps({'time': int(time.time()),
                               'userlist': userlist})
        else:
            return json.dumps({'time': 0, 'userlist': []})

    def api_adduser(self, username, password, isadmin):
        if cherrypy.session['admin']:
            if self.userdb.addUser(username, password, isadmin):
                return 'added new user: %s' % username
            else:
                return 'error, cannot add new user!' % username
        else:
            return "You didn't think that would work, did you?"

    def api_userchangepassword(self, oldpassword, newpassword, username=''):
        isself = username == ''
        if isself:
            username = cherrypy.session['username']
            authed_user = self.userdb.auth(username, oldpassword)
            is_authenticated = userdb.User.nobody() != authed_user
            if not is_authenticated:
                raise cherrypy.HTTPError(403, "Forbidden")
        if isself or cherrypy.session['admin']:
            return self.userdb.changePassword(username, newpassword)
        else:
            raise cherrypy.HTTPError(403, "Forbidden")

    def api_userdelete(self, userid):
        is_self = cherrypy.session['userid'] == userid
        if cherrypy.session['admin'] and not is_self:
            deleted = self.userdb.deleteUser(userid)
            return 'success' if deleted else 'failed'
        else:
            return "You didn't think that would work, did you?"

    def api_showplaylists(self, sortby="created", filterby=''):
        playlists = self.playlistdb.showPlaylists(self.getUserId(), filterby)
        curr_time = int(time.time())
        #translate userids to usernames:
        for pl in playlists:
            pl['username'] = self.userdb.getNameById(pl['userid'])
            pl['type'] = 'playlist'
            pl['age'] = curr_time - pl['created']
        if not sortby in ('username', 'age', 'title'):
            sortby = 'created'
        playlists = sorted(playlists, key=lambda x: x[sortby])
        return playlists

    def api_logout(self):
        cherrypy.lib.sessions.expire()
    api_logout.no_auth = True

    def api_downloadpls(self, plid, hostaddr):
        userid = self.getUserId()
        pls = self.playlistdb.createPLS(plid=plid, userid=userid, addrstr=hostaddr)
        name = self.playlistdb.getName(plid, userid)
        if pls and name:
            return self.serve_string_as_file(pls, name+'.pls')
    api_downloadpls.binary = True

    def api_downloadm3u(self, plid, hostaddr):
        userid = self.getUserId()
        pls = self.playlistdb.createM3U(plid=plid, userid=userid, addrstr=hostaddr)
        name = self.playlistdb.getName(plid, userid)
        if pls and name:
            return self.serve_string_as_file(pls, name+'.m3u')
    api_downloadm3u.binary = True

    def export_playlists(self, format, all=False, hostaddr=''):
        userid = self.getUserId()
        if not userid:
            raise cherrypy.HTTPError(401, _("Please log in"))
        hostaddr = (hostaddr.strip().rstrip('/') + cherry.config['server.rootpath']).rstrip('/')

        format = format.lower()
        if format == 'm3u':
            filemaker = self.playlistdb.createM3U
        elif format == 'pls':
            filemaker = self.playlistdb.createPLS
        else:
            raise cherrypy.HTTPError(400,
                _('Unknown playlist format: {format!r}').format(format=format))

        playlists = self.playlistdb.showPlaylists(userid, include_public=all)
        if not playlists:
            raise cherrypy.HTTPError(404, _('No playlists found'))

        with MemoryZipFile() as zip:
            for pl in playlists:
                plid = pl['plid']
                plstr = filemaker(plid=plid, userid=userid, addrstr=hostaddr)
                name = self.playlistdb.getName(plid, userid) + '.' + format
                if not pl['owner']:
                    username = self.userdb.getNameById(pl['userid'])
                    name =  username + '/' + name
                zip.writestr(name, plstr)

        zipmime = 'application/x-zip-compressed'
        zipname = 'attachment; filename="playlists.zip"'
        cherrypy.response.headers["Content-Type"] = zipmime
        cherrypy.response.headers['Content-Disposition'] = zipname
        return zip.getbytes()
    export_playlists.exposed = True

    def api_getsonginfo(self, path):
        basedir = cherry.config['media.basedir']
        abspath = os.path.join(basedir, path)
        return json.dumps(metainfo.getSongInfo(abspath).dict())

    def api_getencoders(self):
        return json.dumps(audiotranscode.getEncoders())

    def api_getdecoders(self):
        return json.dumps(audiotranscode.getDecoders())

    def api_transcodingenabled(self):
        return json.dumps(cherry.config['media.transcode'])

    def api_updatedb(self):
        self.model.updateLibrary()
        return 'success'

    def api_getconfiguration(self):
        clientconfigkeys = {
            'transcodingenabled': cherry.config['media.transcode'],
            'fetchalbumart': cherry.config['media.fetch_album_art'],
            'isadmin': cherrypy.session['admin'],
            'username': cherrypy.session['username'],
            'servepath': 'serve/',
            'transcodepath': 'trans/',
            'auto_login': self.autoLoginActive(),
            'version': cherry.REPO_VERSION or cherry.VERSION,
        }
        if cherry.config['media.transcode']:
            decoders = self.model.transcoder.availableDecoderFormats()
            clientconfigkeys['getdecoders'] = decoders
            encoders = self.model.transcoder.availableEncoderFormats()
            clientconfigkeys['getencoders'] = encoders
        else:
            clientconfigkeys['getdecoders'] = []
            clientconfigkeys['getencoders'] = []
        return clientconfigkeys

    def serve_string_as_file(self, string, filename):
        content_disposition = 'attachment; filename="'+filename+'"'
        cherrypy.response.headers["Content-Type"] = "application/x-download"
        cherrypy.response.headers["Content-Disposition"] = content_disposition
        return codecs.encode(string, "UTF-8")

########NEW FILE########
__FILENAME__ = i18n_client
def get():
    return {
        'track has no path set!': _('track has no path set!'),
        'track has no label set!': _('track has no label set!'),
    }
########NEW FILE########
__FILENAME__ = log
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# CherryMusic - a standalone music server
# Copyright (c) 2012 - 2014 Tom Wallroth & Tilman Boerner
#
# Project page:
#   http://fomori.org/cherrymusic/
# Sources on github:
#   http://github.com/devsnd/cherrymusic/
#
# CherryMusic is based on
#   jPlayer (GPL/MIT license) http://www.jplayer.org/
#   CherryPy (BSD license) http://www.cherrypy.org/
#
# licensed under GNU GPL version 3 (or later)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
#

# pylint: disable=W0611
from backport import logging
import logging.config
import inspect
import os
import sys

from cherrymusicserver import pathprovider

from logging import NOTSET, DEBUG, INFO, WARN, WARNING, ERROR, CRITICAL, FATAL


LOGLEVEL = INFO

class RelocateLoggingCall(logging.Filter):
    '''using this module's logging methods puts some misleading values into
    standard log record attributes, especially pertaining to the origin of
    the logging call. this filter corrects them with the help of
    extended attributes added by _get_logger()'''
    def filter(self, record):
        has_org = lambda seq: False if not seq else True if seq[0].startswith('org_') else has_org(seq[1:])
        if has_org(dir(record)):
            record.lineno = record.org_lineno
            record.funcName = record.org_funcName
            record.pathname = record.org_pathname
        return 1
relocator = RelocateLoggingCall()

class LowPass(logging.Filter):
    def __init__(self, cutoff):
        self.cutoff = cutoff

    def filter(self, record):
        return 1 if record.levelno < self.cutoff else 0


formatter_briefest = logging.Formatter(fmt='[%(asctime)s] %(message)s', datefmt='%y%m%d-%H:%M')
formatter_brief = logging.Formatter(fmt='[%(asctime)s] %(levelname)-8s: %(message)s', datefmt='%y%m%d-%H:%M')
formatter_full = logging.Formatter(fmt=('-'*80)+ '\n%(levelname)-8s [%(asctime)s] : %(name)-20s : from line (%(lineno)d) at\n\t%(pathname)s\n\t--\n\t%(message)s\n')

handler_console = logging.StreamHandler(stream=sys.stdout)

handler_console.formatter = formatter_briefest
handler_console.level = DEBUG
handler_console.addFilter(LowPass(WARNING))
handler_console.addFilter(relocator)

handler_console_priority = logging.StreamHandler(stream=sys.stderr)
handler_console_priority.formatter = formatter_brief
handler_console_priority.level = WARNING
handler_console_priority.addFilter(relocator)

handler_file_error = logging.FileHandler(os.path.join(pathprovider.getUserDataPath(), 'error.log'), mode='a', delay=True)
handler_file_error.formatter = formatter_full
handler_file_error.level = ERROR
handler_file_error.addFilter(relocator)

logging.root.setLevel(LOGLEVEL)
logging.root.addHandler(handler_console)
logging.root.addHandler(handler_console_priority)
logging.root.addHandler(handler_file_error)

testlogger = logging.getLogger('test')
testlogger.setLevel(CRITICAL)
testlogger.addHandler(handler_console)
testlogger.addHandler(handler_console_priority)
testlogger.propagate = False

logging.getLogger('cherrypy.error').setLevel(WARNING)




def debug(msg, *args, **kwargs):
    '''logs a message with severity DEBUG on the caller's module logger.
    uses the root logger if caller has no module.'''
    _get_logger().debug(msg, *args, **kwargs)


def info(msg, *args, **kwargs):
    '''logs a message with severity INFO on the caller's module logger.
    uses the root logger if caller has no module.'''
    _get_logger().info(msg, *args, **kwargs)


def warn(msg, *args, **kwargs):
    '''logs a message with severity WARN on the caller's module logger.
    uses the root logger if caller has no module.'''
    _get_logger().warning(msg, *args, **kwargs)


def error(msg, *args, **kwargs):
    '''logs a message with severity ERROR on the caller's module logger.
    uses the root logger if caller has no module.'''
    _get_logger().error(msg, *args, **kwargs)


def critical(msg, *args, **kwargs):
    '''logs a message with severity CRITICAL on the caller's module logger.
    uses the root logger if caller has no module.'''
    _get_logger().critical(msg, *args, **kwargs)


def exception(msg, *args, **kwargs):
    '''logs a message with severity ERROR on the caller's module logger,
    including exception information. uses the root logger if caller
    has no module.'''
    _get_logger().exception(msg, *args, **kwargs)

def level(lvl):
    '''sets the level for the caller's module logger, or, if there is no
    module, the root logger. `lvl` is an int as defined in logging, or
    a corresponding string respresentation.'''
    _get_logger().setLevel(lvl)


__istest = False
def setTest(state=True):
    global __istest
    __istest = state


d = debug
i = info
w = warn
e = error
c = critical
ex = exception
x = exception

warning = warn


def _get_logger():
    '''find out the caller's module name and get or create a corresponding
    logger. if caller has no module, return root logger.'''
    if __istest:
        return testlogger
    caller_frm = inspect.stack()[2]
    caller_mod = inspect.getmodule(caller_frm[0])
    name = None if caller_mod is None else caller_mod.__name__
    orgpath = caller_frm[1]
    orgfile = os.path.basename(orgpath)
    caller_info = {
                    'org_filename': orgfile,
                    'org_lineno': caller_frm[2],
                    'org_funcName': caller_frm[3],
                    #'org_module': name if name else os.path.splitext(orgfile)[0],
                    'org_pathname': orgpath,
                   }
    logger = logging.LoggerAdapter(logging.getLogger(name), caller_info)
    return logger




########NEW FILE########
__FILENAME__ = metainfo
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# CherryMusic - a standalone music server
# Copyright (c) 2012 - 2014 Tom Wallroth & Tilman Boerner
#
# Project page:
#   http://fomori.org/cherrymusic/
# Sources on github:
#   http://github.com/devsnd/cherrymusic/
#
# CherryMusic is based on
#   jPlayer (GPL/MIT license) http://www.jplayer.org/
#   CherryPy (BSD license) http://www.cherrypy.org/
#
# licensed under GNU GPL version 3 (or later)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
#

from cherrymusicserver import log
import sys

from tinytag import TinyTag

class Metainfo():
    def __init__(self, artist='', album='', title='', track='', length=0):
        self.artist = artist
        self.album = album
        self.title = title
        self.track = track
        self.length = length
    def dict(self):
        return {
        'artist': self.artist,
        'album': self.album,
        'title': self.title,
        'track': self.track,
        'length': self.length
        }

def getSongInfo(filepath):
    try:
        tag = TinyTag.get(filepath)
    except LookupError:
        return Metainfo()
    # make sure everthing returned (except length) is a string
    for attribute in ['artist','album','title','track']:
        if getattr(tag, attribute) is None:
            setattr(tag, attribute, '')
    return Metainfo(tag.artist, tag.album, tag.title, str(tag.track), tag.duration)


########NEW FILE########
__FILENAME__ = pathprovider
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# CherryMusic - a standalone music server
# Copyright (c) 2012 - 2014 Tom Wallroth & Tilman Boerner
#
# Project page:
#   http://fomori.org/cherrymusic/
# Sources on github:
#   http://github.com/devsnd/cherrymusic/
#
# CherryMusic is based on
#   jPlayer (GPL/MIT license) http://www.jplayer.org/
#   CherryPy (BSD license) http://www.cherrypy.org/
#
# licensed under GNU GPL version 3 (or later)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
#

import os
import sys
import base64
import codecs

userDataFolderName = 'cherrymusic'  # $XDG_DATA_HOME/userDataFolderName
pidFileName = 'cherrymusic.pid'     # $XDG_DATA_HOME/userDataFolderName/cherrymusic.pid
configFolderName = 'cherrymusic'    # $XDG_CONFIG_HOME/configFolderName
configFileName = 'cherrymusic.conf' # $XDG_CONFIG_HOME/configFolderName/cherrymusic.conf
sharedFolderName = 'cherrymusic'    # /usr/share/sharedFolderName

def getUserDataPath():
    userdata = ''
    if sys.platform.startswith('linux'):  # linux
        if 'XDG_DATA_HOME' in os.environ:
            userdata = os.path.join(os.environ['XDG_DATA_HOME'],userDataFolderName)
        else:
            userdata = os.path.join(os.path.expanduser('~'), '.local', 'share', userDataFolderName)
    elif sys.platform.startswith('win'): # windows
        userdata = os.path.join(os.environ['APPDATA'],'cherrymusic')
    elif sys.platform.startswith('darwin'): # osx
        userdata = os.path.join(os.path.expanduser('~'),'Application Support',userDataFolderName)

    if not userdata:
        userdata = fallbackPath()
    assureFolderExists(userdata,['db','albumart','sessions'])
    return userdata

def getConfigPath():
    if len(sys.argv) > 2 and (sys.argv[1] == '-c' or sys.argv[1] == '--config-path') and os.path.exists(sys.argv[2]):
        return sys.argv[2]
    else:
        configpath = ''
        if sys.platform.startswith('linux'):  # linux
            if 'XDG_CONFIG_HOME' in os.environ:
                configpath = os.path.join(os.environ['XDG_CONFIG_HOME'], configFolderName)
            else:
                configpath = os.path.join(os.path.expanduser('~'), '.config', configFolderName)
        elif sys.platform.startswith('win'): #windows
            configpath = os.path.join(os.environ['APPDATA'],configFolderName)
        elif sys.platform.startswith('darwin'): #osx
            configpath = os.path.join(os.path.expanduser('~'),'Application Support',configFolderName)

        if not configpath:
            configpath = fallbackPath()
        assureFolderExists(configpath)
        return configpath

def fallbackPath():
    return os.path.join(os.path.expanduser('~'), '.cherrymusic')

def fallbackPathInUse():
    for _, _, files in os.walk(fallbackPath()):
        if files:
            return True
    return False

def pidFile():
    return os.path.join(getUserDataPath(), pidFileName)

def pidFileExists():
    return os.path.exists(pidFile())

def licenseFile():
    owndir = os.path.dirname(__file__)
    basedir = os.path.split(owndir)[0] or '.'
    basedir = os.path.abspath(basedir)
    return os.path.join(basedir, 'COPYING')

def configurationFile():
    return os.path.join(getConfigPath(), configFileName)

def configurationFileExists():
    return os.path.exists(configurationFile())

def absOrConfigPath(filepath):
    if os.path.isabs(filepath):
        path = filepath
    else:
        path = os.path.join(getConfigPath(), filepath)
    return os.path.normpath(path)

def databaseFilePath(filename):
    configdir = os.path.join(getUserDataPath(), 'db')
    if not os.path.exists(configdir):
        os.makedirs(configdir)
    configpath = os.path.join(configdir, filename)
    return configpath

def albumArtFilePath(directorypath):
    albumartcachepath = os.path.join(getUserDataPath(), 'albumart')
    if not os.path.exists(albumartcachepath):
        os.makedirs(albumartcachepath)
    configpath = os.path.join(albumartcachepath, base64encode(directorypath))
    return configpath

def base64encode(s):
    utf8_bytestr = codecs.encode(s, 'UTF-8')
    utf8_altchar = codecs.encode('+-', 'UTF-8')
    return codecs.decode(base64.b64encode(utf8_bytestr, utf8_altchar), 'UTF-8')

def base64decode(s):
    return codecs.decode(base64.b64decode(s),'UTF-8')

def assureFolderExists(folder,subfolders=['']):
    for subfolder in subfolders:
        dirpath = os.path.join(folder, subfolder)
        if not os.path.exists(dirpath):
            os.makedirs(dirpath)

def readRes(path):
    with codecs.open(getResourcePath(path),encoding="utf-8") as f:
        return f.read()

def getResourcePath(path):
    #check share first
    resourceprefix = os.path.join(sys.prefix, 'share', sharedFolderName)
    respath = os.path.join(resourceprefix, path)
    if not os.path.exists(respath):
        #log.w("Couldn't find " + respath + ". Trying local install path.")
        #otherwise check local/share
        resourceprefix = os.path.join(sys.prefix, 'local', 'share', sharedFolderName)
        respath = os.path.join(resourceprefix, path)
    if not os.path.exists(respath):
        #log.w("Couldn't find " + respath + ". Trying local install path.")
        #otherwise check local install
        resourceprefix = os.path.dirname(os.path.dirname(__file__))
        respath = os.path.join(resourceprefix, path)
    if not os.path.exists(respath):
        #log.w("Couldn't find " + respath + ". Trying home dir.")
        #lastly check homedir
        resourceprefix = getUserDataPath()
        respath = os.path.join(resourceprefix, path)
    if not os.path.exists(respath):
        raise ResourceNotFound("Couldn't locate {path!r} in {res!r}!".format(
            path=path, res=resourceprefix))
    return os.path.join(resourceprefix, path)

class ResourceNotFound(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return repr(self.msg)

def filename(path, pathtofile=False):
    if pathtofile:
        return os.path.split(path)[0]
    else:
        return os.path.split(path)[1]

def stripext(filename):
    if '.' in filename:
        return filename[:filename.rindex('.')]
    return filename

########NEW FILE########
__FILENAME__ = playlistdb
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# CherryMusic - a standalone music server
# Copyright (c) 2012 - 2014 Tom Wallroth & Tilman Boerner
#
# Project page:
#   http://fomori.org/cherrymusic/
# Sources on github:
#   http://github.com/devsnd/cherrymusic/
#
# CherryMusic is based on
#   jPlayer (GPL/MIT license) http://www.jplayer.org/
#   CherryPy (BSD license) http://www.cherrypy.org/
#
# licensed under GNU GPL version 3 (or later)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
#

from cherrymusicserver import database
from cherrymusicserver import log
from cherrymusicserver.cherrymodel import MusicEntry
from cherrymusicserver.database.connect import BoundConnector
try:
    from urllib.parse import unquote
except ImportError:
    from backport.urllib.parse import unquote

DBNAME = 'playlist'

class PlaylistDB:
    def __init__(self, connector=None):
        database.require(DBNAME, version='1')
        self.conn = BoundConnector(DBNAME, connector).connection()

    def deletePlaylist(self, plid, userid, override_owner=False):
        cursor = self.conn.cursor()
        ownerid = cursor.execute(
            "SELECT userid FROM playlists WHERE rowid = ?", (plid,)).fetchone()
        if not ownerid:
            return _("This playlist doesn't exist! Nothing deleted!")
        if userid != ownerid[0] and not override_owner:
            return _("This playlist belongs to another user! Nothing deleted.")
        cursor.execute("""DELETE FROM playlists WHERE rowid = ?""", (plid,))
        self.conn.commit()
        return 'success'

    def savePlaylist(self, userid, public, playlist, playlisttitle, overwrite=False):
        if not len(playlist):
            return _('I will not create an empty playlist. sorry.')
        duplicateplaylistid = self.conn.execute("""SELECT rowid FROM playlists
            WHERE userid = ? AND title = ?""",(userid,playlisttitle)).fetchone()
        if duplicateplaylistid and overwrite:
            self.deletePlaylist(duplicateplaylistid[0], userid)
            duplicateplaylistid = False
        if not duplicateplaylistid:
            cursor = self.conn.cursor()
            cursor.execute("""INSERT INTO playlists
                (title, userid, public) VALUES (?,?,?)""",
                (playlisttitle, userid, 1 if public else 0))
            playlistid = cursor.lastrowid;
            #put tracknumber to each track
            numberedplaylist = []
            for track, song in enumerate(playlist):
                numberedplaylist.append((playlistid, track, song['url'], song['title']))
            cursor.executemany("""INSERT INTO tracks (playlistid, track, url, title)
                VALUES (?,?,?,?)""", numberedplaylist)
            self.conn.commit()
            return "success"
        else:
            return _("This playlist name already exists! Nothing saved.")

    def loadPlaylist(self, playlistid, userid):
        cursor = self.conn.cursor()
        cursor.execute("""SELECT rowid FROM playlists WHERE
            rowid = ? AND (public = 1 OR userid = ?) LIMIT 0,1""",
            (playlistid, userid));
        result = cursor.fetchone()
        if result:
            cursor.execute("""SELECT title, url FROM tracks WHERE
                playlistid = ? ORDER BY track ASC""", (playlistid,))
            alltracks = cursor.fetchall()
            apiplaylist = []
            for track in alltracks:
                #TODO ugly hack: playlistdb saves the "serve" dir as well...
                trackurl = unquote(track[1])
                if trackurl.startswith('/serve/'):
                    trackurl = trackurl[7:]
                elif trackurl.startswith('serve/'):
                    trackurl = trackurl[6:]
                apiplaylist.append(MusicEntry(path=trackurl, repr=unquote(track[0])))
            return apiplaylist

    def getName(self, plid, userid ):
        cur = self.conn.cursor()
        cur.execute("""SELECT rowid as id,title FROM playlists WHERE
            (public = 1 OR userid = ?) and rowid=?""", (userid,plid));
        result = cur.fetchall()
        if result:
            return result[0][1]
        return 'playlist'

    def setPublic(self, userid, plid, public):
        ispublic = 1 if public else 0
        cur = self.conn.cursor()
        cur.execute("""UPDATE playlists SET public = ? WHERE rowid = ? AND userid = ?""", (ispublic, plid, userid))
        self.conn.commit()

    def _searchPlaylist(self, searchterm):
        q = '''SELECT DISTINCT playlists.rowid FROM playlists, tracks
               WHERE ( tracks.playlistid = playlists.rowid
                       AND tracks.title LIKE ? )
                     OR
                       playlists.title LIKE ?'''
        cur = self.conn.cursor()
        res = cur.execute(q, ('%'+searchterm+'%', '%'+searchterm+'%'))
        return [row[0] for row in res.fetchall()]

    def showPlaylists(self, userid, filterby='', include_public=True):
        filtered = None
        if filterby != '':
            filtered = self._searchPlaylist(filterby)
        cur = self.conn.cursor()
        select = "SELECT rowid, title, userid, public, _created FROM playlists"
        if include_public:
            where = """ WHERE public=:public OR userid=:userid"""
        else:
            where = """ WHERE userid=:userid"""
        cur.execute(select + where, {'public': True, 'userid': userid});
        results = cur.fetchall()
        playlists = []
        for result in results:
            if not filtered is None and result[0] not in filtered:
                continue
            playlists.append({'plid': result[0],
                              'title': result[1],
                              'userid': result[2],
                              'public': bool(result[3]),
                              'owner': bool(userid==result[2]),
                              'created': result[4]
                              })
        return playlists


    def createPLS(self,userid,plid, addrstr):
        pl = self.loadPlaylist(userid=userid, playlistid=plid)
        if pl:
            plsstr = '''[playlist]
    NumberOfEntries={}
    '''.format(len(pl))
            for i,track in enumerate(pl):
                trinfo = {  'idx':i+1,
                            'url':addrstr+'/serve/'+track.path,
                            'name':track.repr,
                            'length':-1,
                        }
                plsstr += '''
    File{idx}={url}
    Title{idx}={name}
    Length{idx}={length}
    '''.format(**trinfo)
            return plsstr


    def createM3U(self,userid,plid,addrstr):
        pl = self.loadPlaylist(userid=userid, playlistid=plid)
        if pl:
            trackpaths = map(lambda x: addrstr+'/serve/'+x.path,pl)
            return '\n'.join(trackpaths)

########NEW FILE########
__FILENAME__ = progress
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# CherryMusic - a standalone music server
# Copyright (c) 2012 - 2014 Tom Wallroth & Tilman Boerner
#
# Project page:
#   http://fomori.org/cherrymusic/
# Sources on github:
#   http://github.com/devsnd/cherrymusic/
#
# CherryMusic is based on
#   jPlayer (GPL/MIT license) http://www.jplayer.org/
#   CherryPy (BSD license) http://www.cherrypy.org/
#
# licensed under GNU GPL version 3 (or later)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
#

from time import time

from cherrymusicserver import log
from cherrymusicserver import util


class Progress(object):
    """Simple, timed progress tracking.
    Based on the notion the time to complete a task can be broken up into
    evenly spaced ticks, when a good estimate of total ticks
    is known. Estimates time remaining from the time taken for past ticks.
    The timer starts on the first tick."""

    def __init__(self, ticks, name=''):
        assert ticks > 0, "expected ticks must be > 0"
        self._ticks = 0
        self._expected_ticks = ticks
        self._starttime = time()
        self._finished = False
        self._finishtime = 0
        self.name = name

    def _start(self):
        self._starttime = time()

    def tick(self):
        """Register a tick with this object. The first tick starts the timer."""
        if self._ticks == 0:
            self._start()
        self._ticks += 1

    def finish(self):
        """Mark this progress as finished. Setting this is final."""
        self._finished = True
        self._finishtime = time()

    def formatstr(self, fstr, *args):
        add = ''.join(list(args))
        fstr = fstr % {'eta': self.etastr,
                       'percent': self.percentstr,
                       'ticks': self._ticks,
                       'total': self._expected_ticks}
        return fstr + add

    @property
    def percent(self):
        """Number estimate of percent completed. Receiving more ticks than
        initial estimate increases this number beyond 100."""
        if (self._finished):
            return 100
        return self._ticks * 100 / self._expected_ticks

    @property
    def percentstr(self):
        """String version of `percent`. Invalid values outside of (0..100)
        are rendered as unknown value."""
        if (self._finished):
            return '100%'
        p = self.percent
        return '%s%%' % (str(int(p)) if p <= 100 else '??')

    @property
    def starttime(self):
        return self._starttime

    @property
    def runtime(self):
        if (self._ticks == 0):
            return 0
        reftime = self._finishtime if self._finished else time()
        return reftime - self.starttime

    @property
    def eta(self):
        """Estimate of time remaining, in seconds. Ticks beyond initial estimate
        lead to a negative value."""
        if self._finished:
            return 0
        if self._ticks == 0:
            return 0
        return ((self._expected_ticks - self._ticks) * self.runtime / self._ticks) + 1

    @property
    def etastr(self):
        """String version of remaining time estimate. A negative `eta` is marked
        as positive overtime."""
        overtime = ''
        eta = self.eta
        if eta < 0:
            eta = -eta
            overtime = '+'
        hh, mm, ss = util.splittime(eta)
        return '%(ot)s%(hh)02d:%(mm)02d:%(ss)02d' % {
                                                     'hh': hh,
                                                     'mm': mm,
                                                     'ss': ss,
                                                     'ot':overtime,
                                                     }


class ProgressTree(Progress):
    '''
    Extension of the Progress concept that allows spawning 'child progress'
    objects that will contribute a tick to their parent on completion.
    '''

    def __init__(self, name=None, parent=None):
        super(self.__class__, self).__init__(ticks=1, name=name)
        self._parent = parent
        self._active_children = set()
        self.root = self
        self.level = 0
        self.reporter = None

    def __repr__(self):
        return '[%3d:%3d=%.2f] %d %.1f->[%s] %s' % (
                                      self._ticks,
                                      self._expected_ticks,
                                      self.completeness,
                                      len(self._active_children),
                                      self.runtime,
                                      self.etastr,
                                      self.name,
                                      )

    def spawnchild(self, name=None):
        '''Creates a child progress that will tick this progress on finish'''
        if name is None:
            name = self.name
        child = ProgressTree(name, parent=self)
        child.root = self.root
        child.level = self.level + 1
        self.extend()
        return child

    def extend(self, amount=1):
        '''Raises the number of expected ticks by amount'''
        assert amount > 0
        if self._finished:
            self.unfinish()
        self._expected_ticks += amount

    def unfinish(self):
        '''If progress resumes after a finish has been declared, undo the
        effects of finish().'''
        self._finished = False
        if not self._parent is None:
            self._parent.untick()
            self._parent._active_children.add(self)

    def untick(self):
        '''Take back a past tick'''
        if self._ticks > 0:
            if self._ticks == self._expected_ticks:
                self.unfinish()
            self._ticks -= 1

    def _start(self):
        super(self.__class__, self)._start()
        if not self._parent is None:
            self._parent._active_children.add(self)

    def tick(self, report=True):
        super(self.__class__, self).tick()
        if report and self.root.reporter:
            self.root.reporter.tick(self)
        if self._ticks == self._expected_ticks:
            self.finish()

    def finish(self):
        if self._finished:
            return
        super(self.__class__, self).finish()
        if not self._parent is None:
            self._parent.tick(report=False)
            self._parent._active_children.remove(self)

    @property
    def completeness(self):
        '''Ratio of registered ticks to total expected ticks. Can be > 1.'''
        if self._finished:
            return 1.0
        c = self._ticks
        for child in self._active_children:
            c += child.completeness
        c /= self._expected_ticks
        return c

    @property
    def percent(self):
        return self.completeness * 100

    @property
    def eta(self):
        if self._finished:
            return 0
        c = self.completeness
        if c == 0:
            return 0
        return (1 - c) * self.runtime / c


class ProgressReporter(object):
    '''
    Customizable progress reporter. Can report on every object with the
    following attributes or properties:

    name : str
        a descriptive name of this progress

    eta : float
        estimated time to completion in seconds. negative values mean overtime

    level : int >= 0
        for nested progress: the nesting depth, with 0 being top

    root : progress not None
        for nested progress: the origin (super parent) progress; can be == this
    '''

    @classmethod
    def timefmt(cls, eta):
        '''the default time format: [+]hh:mm:ss'''
        overtime = 'ETA '
        if eta < 0:
            eta = -eta
            overtime = '+'
        hh, mm, ss = util.splittime(eta)
        return '%(ot)s%(hh)02d:%(mm)02d:%(ss)02d' % {
                                                     'hh': hh,
                                                     'mm': mm,
                                                     'ss': ss,
                                                     'ot':overtime,
                                                     }

    @classmethod
    def prettytime(cls, eta):
        '''
        time display with variable precision: only show the most interesting
        time unit.
        '''
        def round_to(val, stepsize):
            return (val + stepsize / 2) // stepsize * stepsize

        prefix = 'ETA '
        if eta < 0:
            eta = -eta
            prefix = '+'
        hh, mm, ss = util.splittime(eta)
        if hh > 3:
            timestr = '%2d hrs' % hh
        elif hh > 0.25:
            hh = round_to(hh * 100, 25) / 100
            timestr = '%.2f h' % hh
        elif mm > 0.8:
            timestr = '%2d min' % int(mm + 0.5)
        elif ss > 20:
            timestr = '%2d sec' % round_to(ss, 20)
        elif ss > 5:
            timestr = '%2d sec' % round_to(ss, 5)
        else:
            timestr = '%2d sec' % ss
        return prefix + timestr


    @classmethod
    def prettyqty(cls, amount):
        '''return a quantity as kilos (k) or megas (M) if  justified)'''
        if amount < 10000:
            return '%d' % (amount,)
        if amount < 10e6:
            return '%dk' % (amount // 1000,)
        if amount < 10e7:
            return '%1.1fM' % (amount // 10e6,)
        return '%dM' % (amount // 10e6,)


    def __init__(self, lvl= -1, dly=1, timefmt=None, namefmt=None, repf=None):
        '''
        Creates a progress reporter with the following customization options:

        lvl : int (default -1)
            The maximum level in the progress hierarchy that will trigger a
            report. When a report is triggered, it will contain all progress
            events up to this level that have occurred since the last report. A
            negative value will use the time trigger (see ``dly``) to report the
            newest progress event with the upmost available level.

        dly : float (default 1)
            The target maximum delay between reports, in seconds. Triggers a
            report conforming with ``lvl`` if ``dly`` seconds have passed
            since the last report. Set to 0 to turn off timed reporting;
            set to a value < 0 for a time trigger without delay.

        timefmt : callable(float) -> str (default ProgressReport.timefmt)
            A function that turns the number for the estimated completion time
            into a string. That number is provided by ``progress.root.eta``.
            Per default, it interpreted as seconds until completion, with
            negative values meaning overtime since estimated completion.

        namefmt : callable(str) -> str (default: no conversion)
            A function that converts the name given by ``progress.name`` into
            a more suitable format.

        repf : callable(dict) (default: log '%(eta) %(nam) (%(tix))' as info)
           Function callback to handle the actual reporting. The dict argument
           contains the following items::
               'eta': completion time as str,
               'nam': progress name,
               'tix': str giving total ticks registered with this reporter,
               'progress': progress to report on, containing the raw data
        '''
        self._eta_adjuster = lambda e: e + 1
        self._eta_formatter = self.prettytime if timefmt is None else timefmt
        self._name_formatter = (lambda s: s) if namefmt is None else namefmt
        self._reportfunc = (lambda d: log.i('%(eta)s %(nam)s (%(tix)s)', d)) if repf is None else repf
        self._replevel = lvl
        self._repintvl = dly
        self._maxlevel = 0
        self._levelcache = {}
        self._ticks = 0
        self._lastreport = 0


    def tick(self, progress):
        '''
        Register a progress advance for progress, potentially triggering a
        report. A total of ticks will be kept.
        '''
        self._ticks += 1
        self._maxlevel = max(self._maxlevel, progress.level)
        self._levelcache[progress.level] = progress
        if progress.level <= self._replevel:
            self.report(progress)
            del self._levelcache[progress.level]
        elif self._repintvl and time() - self._lastreport > self._repintvl:
            self.reportlast()

    def reportlast(self):
        '''
        Report progress events since the last report.
        '''
        lvl = 0
        while lvl <= self._maxlevel:
            if lvl in self._levelcache:
                p = self._levelcache.pop(lvl)
                self.report(p)
                if lvl >= self._replevel:
                    break
            lvl += 1

    def report(self, progress):
        '''Trigger a report for ``progress``'''
        self._reportfunc({
              'eta': self._eta_formatter(self._eta_adjuster(progress.root.eta)),
              'nam': self._name_formatter(progress.name),
              'tix': self.prettyqty(self._ticks),
              'progress' : progress,
              })
        self._lastreport = time()

########NEW FILE########
__FILENAME__ = resultorder
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# CherryMusic - a standalone music server
# Copyright (c) 2012 - 2014 Tom Wallroth & Tilman Boerner
#
# Project page:
#   http://fomori.org/cherrymusic/
# Sources on github:
#   http://github.com/devsnd/cherrymusic/
#
# CherryMusic is based on
#   jPlayer (GPL/MIT license) http://www.jplayer.org/
#   CherryPy (BSD license) http://www.cherrypy.org/
#
# licensed under GNU GPL version 3 (or later)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
#

"""This class determines the order of the results
fetched from the database by some mystic-voodoo-
hocuspocus heuristics"""

from cherrymusicserver import pathprovider
from cherrymusicserver import log
import cherrymusicserver.tweak
from imp import reload
from cherrymusicserver.util import Performance

class ResultOrder:
    def __init__(self, searchword, debug=False):
        self.debug = debug
        self.fullsearchterm = searchword.lower()
        self.searchwords = searchword.lower().split(' ')

        reload(cherrymusicserver.tweak)
        self.perfect_match_bonus = cherrymusicserver.tweak.ResultOrderTweaks.perfect_match_bonus
        self.partial_perfect_match_bonus = cherrymusicserver.tweak.ResultOrderTweaks.partial_perfect_match_bonus
        self.starts_with_bonus = cherrymusicserver.tweak.ResultOrderTweaks.starts_with_bonus
        self.folder_bonus = cherrymusicserver.tweak.ResultOrderTweaks.folder_bonus
        self.word_in_file_name_bonus = cherrymusicserver.tweak.ResultOrderTweaks.word_in_file_name_bonus
        self.word_not_in_file_name_penalty = cherrymusicserver.tweak.ResultOrderTweaks.word_not_in_file_name_penalty
        self.word_in_file_path_bonus = cherrymusicserver.tweak.ResultOrderTweaks.word_in_file_path_bonus
        self.word_not_in_file_path_penalty = cherrymusicserver.tweak.ResultOrderTweaks.word_not_in_file_path_penalty
    def __call__(self,element):
        file = element.path
        isdir = element.dir
        fullpath = file.lower()
        filename = pathprovider.filename(file).lower()
        filename_words = filename.split(' ')

        bias = 0
        occurences_bias = 0
        perfect_match_bias = 0
        partial_perfect_match_bias = 0
        folder_bias = 0
        starts_with_bias = 0
        starts_with_no_track_number_bias = 0

        #count occurences of searchwords
        occurences=0
        for searchword in self.searchwords:
            if searchword in fullpath:
                occurences_bias += self.word_in_file_path_bonus
            else:
                occurences_bias += self.word_not_in_file_path_penalty
            if searchword in filename:
                occurences_bias += self.word_in_file_name_bonus
            else:
                occurences_bias += self.word_not_in_file_name_penalty

        #perfect match?
        if filename == self.fullsearchterm or self.noThe(filename) == self.fullsearchterm:
            perfect_match_bias += self.perfect_match_bonus

        filename = pathprovider.stripext(filename)
        #partial perfect match?
        for searchword in self.searchwords:
            if searchword in filename_words:
                partial_perfect_match_bias += self.partial_perfect_match_bonus
        if isdir:
            folder_bias += self.folder_bonus

        #file starts with match?
        for searchword in self.searchwords:
            if filename.startswith(searchword):
                starts_with_bias += self.starts_with_bonus

        #remove possible track number
        while len(filename)>0 and '0' <= filename[0] <= '9':
            filename = filename[1:]
        filename = filename.strip()
        for searchword in self.searchwords:
            if filename == searchword:
                starts_with_no_track_number_bias += self.starts_with_bonus

        bias = occurences_bias + perfect_match_bias + partial_perfect_match_bias + folder_bias + starts_with_bias + starts_with_no_track_number_bias

        if self.debug:
            element.debugOutputSort = '''
fullsearchterm: %s
searchwords: %s
filename: %s
filepath: %s
occurences_bias                  %d
perfect_match_bias               %d
partial_perfect_match_bias       %d
folder_bias                      %d
starts_with_bias                 %d
starts_with_no_track_number_bias %d
------------------------------------
total bias                       %d
            ''' % (
        self.fullsearchterm,
        self.searchwords,
        filename,
        fullpath,
        occurences_bias,
        perfect_match_bias,
        partial_perfect_match_bias,
        folder_bias,
        starts_with_bias,
        starts_with_no_track_number_bias,
        bias)

        return bias

    def noThe(self,a):
        if a.lower().endswith((', the',', die')):
            return a[:-5]
        return a

########NEW FILE########
__FILENAME__ = service
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# CherryMusic - a standalone music server
# Copyright (c) 2012 - 2014 Tom Wallroth & Tilman Boerner
#
# Project page:
#   http://fomori.org/cherrymusic/
# Sources on github:
#   http://github.com/devsnd/cherrymusic/
#
# CherryMusic is based on
#   jPlayer (GPL/MIT license) http://www.jplayer.org/
#   CherryPy (BSD license) http://www.cherrypy.org/
#
# licensed under GNU GPL version 3 (or later)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
#
""" Dependency injection and other facilities to match providers of services
    with their users.

    Nature and interface of a service are left for the concerned parties to
    agree on; all this module knows about the service is its name, or "handle".

    Basic usage::

        >>> pizza = object()
        >>> service.provide('pizzaservice', pizza)
        >>> pizza is service.get('pizzaservice')
        True

    Types as providers and users::

        >>> class PizzaService(object):
        ...     pass
        ...
        >>> @service.user(mypizza='pizzaservice')     # become a user
        ... class PizzaUser(object):
        ...     pass
        ...
        >>> user = PizzaUser()
        >>> service.provide('pizzaservice', PizzaService)
        >>> isinstance(user.mypizza, PizzaService)    # provider as attribute
        True
"""
import threading

from cherrymusicserver import log


class MutualDependencyBreak(Exception):
    """Raised when mutually dependent providers are trying to instantiate
    each other in their constructors.

    This happens while creating a provider that is part of a dependency
    cycle; when it is allowed, in its constructor, to access a dependency
    that's also part of the cycle, a singularity is spawned which implodes the
    universe. This exception is raised to prevent that.

    In general, don't create cyclic dependencies. It's bad for your brain and
    also a sure sign of a problematic program architecture. When confronted
    with a mutual dependency, extract a third class from one of the offenders
    for both to depend on.
    """
    pass


__provider_factories = {}
__providercache = {}


def provide(handle, provider, args=(), kwargs={}):
    """ Activate a provider for the service identified by ``handle``,
        replacing a previous provider for the same service.

        If the provider is a ``type``, an instance will be created as the
        actual provider. Instantiation is lazy, meaning it will be deferred
        until the provider is requested (:func:`get`) by some user.

        To use a type as a provider, you need to wrap it into something that is
        not a type.

        handle : str
            The name of the serivce.
        provider :
            An object that provides the service, or a type that instantiates
            such objects. Instantiation will happen on the first get call.
        args, kwargs :
            Pass on arguments to a type.
    """
    assert isinstance(provider, type) or not (args or kwargs)
    __provider_factories[handle] = _ProviderFactory.get(provider, args, kwargs)
    __providercache.pop(handle, None)
    log.d('service %r: now provided by %r', handle, provider)


def get(handle):
    """Request the provider for the service identified by ``handle``.

    If a type was registered for the handle, the actual provider will be the
    result of instantiating the type when it is first requested.

    Although the goal is to create only one instance, it is possible that
    different threads see different instances.
    """
    try:
        return __providercache[handle]
    except KeyError:
        return _createprovider(handle)


class require(object):
    """Descriptor to make a service provider available as a class attribute.

        >>> import cherrymusicserver.service as service
        >>> class ServiceUser(object):
        ...     mypizzas = service.require('pizzaservice')
    """
    def __init__(self, handle):
        self.handle = handle

    def __repr__(self):
        return '{0}({1!r})'.format(self.__class__.__name__, self.handle)

    def __get__(self, instance, owner):
        return get(self.handle)


def user(**requirements):
    """ Class deocrator to inject service providers as attributes into the
        decorated class.

        requirements : name=handle
            Create :class:`require` descriptor attributes in the class:
            ``name = require(handle)``.

        Returns: Class Decorator
            A function that takes the user class as its sole argument.
    """
    def clsdecorator(cls):
        for attribute, handle in requirements.items():
            setattr(cls, attribute, require(handle))
        return cls
    return clsdecorator


def _createprovider(handle):
    try:
        factory = __provider_factories[handle]
    except KeyError:
        raise LookupError('Service not available: {0!r}'.format(handle))
    return __providercache.setdefault(handle, factory.make())


class _ProviderFactory(object):
    """ High security facility to contain cyclic dependency and multithreading
        issues.

        Factory instances guard against dependency cycles by raising a
        :class:`MutualDependencyBreak` when mutually dependent providers
        try to instantiate each other.
    """

    _master_lock = threading.Lock()

    __factories = {}

    @classmethod
    def get(cls, provider, args=(), kwargs=None):
        if kwargs is None:
            kwargs = {}
        with cls._master_lock:
            try:
                factory = cls.__factories[id(provider)]
                factory.args = args
                factory.kwargs = kwargs
            except KeyError:
                factory = cls(provider, args, kwargs)
                cls.__factories[id(provider)] = factory
            return factory

    def __init__(self, provider, args=(), kwargs={}):
        assert self._master_lock.locked(), 'use .get(...) to obtain instances'
        self.provider = provider
        self.args = args
        self.kwargs = kwargs
        self.__threadlocal = threading.local()

    @property
    def lock(self):
        """Thread-local: dependendy issues will happen inside the same thread,
        so don't compete with other threads."""
        local = self.__threadlocal
        try:
            lock = local.lock
        except AttributeError:
            with self._master_lock:
                lock = local.__dict__.setdefault('lock', threading.Lock())
        return lock

    def make(self):
        """ Return a provider instance.

            Raises : :cls:`MutualDependencyBreak`
                If called recursively within the same thread, which happens
                when mutually dependent providers try to instantiate each other.
        """
        if self.lock.locked():
            raise MutualDependencyBreak(self.provider)
        with self.lock:
            if isinstance(self.provider, (type, type(Python2OldStyleClass))):
                return self.provider(*self.args, **self.kwargs)
            return self.provider


class Python2OldStyleClass:
    """In Python2, I am a ``classobj`` which is not the same as a ``type``."""
    pass

########NEW FILE########
__FILENAME__ = sqlitecache
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# CherryMusic - a standalone music server
# Copyright (c) 2012 - 2014 Tom Wallroth & Tilman Boerner
#
# Project page:
#   http://fomori.org/cherrymusic/
# Sources on github:
#   http://github.com/devsnd/cherrymusic/
#
# CherryMusic is based on
#   jPlayer (GPL/MIT license) http://www.jplayer.org/
#   CherryPy (BSD license) http://www.cherrypy.org/
#
# licensed under GNU GPL version 3 (or later)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
#

#python 2.6+ backward compability
from __future__ import unicode_literals

import os
import re
import sqlite3
import sys
import traceback

from collections import deque
from operator import itemgetter

import cherrymusicserver as cherry
from cherrymusicserver import database
from cherrymusicserver import log
from cherrymusicserver import service
from cherrymusicserver import util
from cherrymusicserver.cherrymodel import MusicEntry
from cherrymusicserver.database.connect import BoundConnector
from cherrymusicserver.util import Performance
from cherrymusicserver.progress import ProgressTree, ProgressReporter
import cherrymusicserver.tweak
from imp import reload
import random

UNIDECODE_AVAILABLE = True
try:
    import unidecode
except ImportError:
    UNIDECODE_AVAILABLE = False

scanreportinterval = 1
AUTOSAVEINTERVAL = 100
debug = False
keepInRam = False

#if debug:
#    log.level(log.DEBUG)

DBNAME = 'cherry.cache'

# unidecode will transform umlauts etc to their ASCII equivalent by
# stripping the accents. This is a simple table for other common
# transformations not performed by unidecode
SPECIAL_LETTER_TRANSFORMS = {
    'ä': 'ae',
    'ö': 'oe',
    'ü': 'ue',
}

class SQLiteCache(object):

    def __init__(self, connector=None):
        database.require(DBNAME, version='1')
        self.normalize_basedir()
        connector = BoundConnector(DBNAME, connector)
        self.DBFILENAME = connector.dblocation
        self.conn = connector.connection()
        self.db = self.conn.cursor()

        #I don't care about journaling!
        self.conn.execute('PRAGMA synchronous = OFF')
        self.conn.execute('PRAGMA journal_mode = MEMORY')
        self.load_db_to_memory()

    def file_db_in_memory(self):
        return not self.DBFILENAME == ':memory:' and cherry.config['search.load_file_db_into_memory']

    def load_db_to_memory(self):
        if self.file_db_in_memory():
            self.file_db_mem = MemoryDB(self.DBFILENAME, 'files')
            self.file_db_mem.db.execute('CREATE INDEX IF NOT EXISTS idx_files_parent'
                          ' ON files(parent)')

    @classmethod
    def searchterms(cls, searchterm):
        words = re.findall('(\w+|[^\s\w]+)',searchterm.replace('_', ' ').replace('%',' '),re.UNICODE)
        words = [word.lower() for word in words]
        if UNIDECODE_AVAILABLE:
            unidecoded = [unidecode.unidecode(word) for word in words]
            words += unidecoded
        special_transforms = []
        for word in words:
            if any(char in word for char in SPECIAL_LETTER_TRANSFORMS.keys()):
                for char, substitute in SPECIAL_LETTER_TRANSFORMS.items():
                    word = word.replace(char, substitute)
                special_transforms.append(word)
        words += special_transforms
        return set(words)

    def fetchFileIds(self, terms, maxFileIdsPerTerm, mode):
        """returns list of ids each packed in a tuple containing the id"""

        assert '' not in terms, _("terms must not contain ''")
        resultlist = []

        for term in terms:
            tprefix, tlast = term[:-1], term[-1]
            query = '''SELECT search.frowid FROM dictionary JOIN search ON search.drowid = dictionary.rowid WHERE '''
            if sys.maxunicode <= ord(tlast):
                where = ''' dictionary.word LIKE ? '''
                params = (term + '%',)
            else:
                where = ''' (dictionary.word >= ? AND dictionary.word < ?) '''
                params = (term, tprefix + chr(1 + ord(tlast)))
            order = ' ORDER BY dictionary.occurrences DESC '
            limit = ' LIMIT 0, ' + str(maxFileIdsPerTerm) #TODO add maximum db results as configuration parameter
            sql = query + where + order +limit
            if debug:
                log.d('Search term: %r', term)
                log.d('Query used: %r, %r', sql, params)
            #print(self.conn.execute('EXPLAIN QUERY PLAN ' + sql, params).fetchall())
            self.db.execute(sql, params)
            resultlist += self.db.fetchall()
        return resultlist

    def searchfor(self, value, maxresults=10):
        mode = 'normal'
        if value.startswith('!f '):
            mode = 'fileonly'
            value = value[3:]
        elif value.endswith(' !f'):
            mode = 'fileonly'
            value = value[:-3]
        elif value.startswith('!d '):
            mode = 'dironly'
            value = value[3:]
        elif value.endswith(' !d'):
            mode = 'dironly'
            value = value[:-3]

        reload(cherrymusicserver.tweak)
        file_search_limit = cherrymusicserver.tweak.SearchTweaks.normal_file_search_limit

        terms = SQLiteCache.searchterms(value)
        with Performance(_('searching for a maximum of %s files') % str(file_search_limit * len(terms))):
            if debug:
                log.d('searchterms')
                log.d(terms)
            results = []

            maxFileIdsPerTerm = file_search_limit
            with Performance(_('file id fetching')):
                #unpack tuples
                fileids = [t[0] for t in self.fetchFileIds(terms, maxFileIdsPerTerm, mode)]

            if len(fileids) > file_search_limit:
                with Performance(_('sorting results by fileid occurrences')):
                    resultfileids = {}
                    for fileid in fileids:
                        if fileid in resultfileids:
                            resultfileids[fileid] += 1
                        else:
                            resultfileids[fileid] = 1
                    # sort items by occurrences and only return maxresults
                    fileids = sorted(resultfileids.items(), key=itemgetter(1), reverse=True)
                    fileids = [t[0] for t in fileids]
                    fileids = fileids[:min(len(fileids), file_search_limit)]

            if mode == 'normal':
                with Performance(_('querying fullpaths for %s fileIds') % len(fileids)):
                    results += self.musicEntryFromFileIds(fileids)
            else:
                with Performance(_('querying fullpaths for %s fileIds, files only') % len(fileids)):
                    results += self.musicEntryFromFileIds(fileids,mode=mode)

            if debug:
                log.d('resulting paths')
                log.d(results)
            return results

    def listdir(self, path):
        basedir = cherry.config['media.basedir']
        targetpath = os.path.join(basedir, path)
        targetdir = self.db_find_file_by_path(targetpath)
        if targetdir is None:
            log.e(_('media cache cannot listdir %r: path not in database'), path)
            return []
        return list(map(lambda f: f.basename, self.fetch_child_files(targetdir)))

    def randomFileEntries(self, count):
        ''' Return a number of random entries from the file cache.

            The actual number returned may be less than ``count`` if the
            database does not contain enough entries or if randomization hits
            directory entries or entries that have been deleted.
        '''
        assert count >= 0
        cursor = self.conn.cursor()
        minId = cursor.execute('''SELECT _id FROM files ORDER BY _id ASC LIMIT 1;''').fetchone()
        if minId is None:
            return ()     # database is empty
        minId = minId[0]
        maxId = cursor.execute('''SELECT _id FROM files ORDER BY _id DESC LIMIT 1;''').fetchone()[0]

        if sys.version_info < (3,):
            genrange = xrange                   # use generator, not a large list
        else:
            genrange = range

        if maxId - minId < count:
            file_ids = genrange(minId, maxId + 1)
        else:
            # range generator pays off:
            file_ids = random.sample(genrange(minId, maxId + 1), count)

        entries = self.musicEntryFromFileIds(file_ids, mode='fileonly')
        random.shuffle(entries)
        return entries


    def musicEntryFromFileIds(self, filerowids, incompleteMusicEntries=None, mode='normal'):
        reload(cherrymusicserver.tweak)
        file_search_limit = cherrymusicserver.tweak.SearchTweaks.normal_file_search_limit

        #incompleteMusicEntries maps db parentid to incomplete musicEntry
        assert mode in ('normal', 'dironly', 'fileonly'), mode
        if incompleteMusicEntries is None:
            incompleteMusicEntries = {}
        musicEntries = [] #result list

        if self.file_db_in_memory():
            db = self.file_db_mem.db
        else:
            db = self.conn

        cursor = db.cursor()
        sqlquery = '''  SELECT rowid, parent, filename, filetype, isdir
                        FROM files WHERE rowid IN ({ids})'''.format(
                            ids=', '.join('?' * len(filerowids)))
        sqlparams = tuple(filerowids)

        if not incompleteMusicEntries:
            #only filter 1st recursion level
            if mode != 'normal':
                sqlquery += ' AND isdir = ?'
                sqlparams += ('dironly' == mode,)
            sqlquery += ' LIMIT 0, ?'
            sqlparams += (file_search_limit,)

        cursor.execute(sqlquery, sqlparams)
        for id, parent_id, filename, fileext, isdir in cursor.fetchall():
            path = filename + fileext
            #check if fetched row is parent of existing entry
            if id in incompleteMusicEntries:
                #remove item and map to new parent id
                entries = incompleteMusicEntries.pop(id)
                for entry in entries:
                    entry.path = os.path.join(path, entry.path)
            else:
                #id is not parent of any entry, so make a new one
                entries = [MusicEntry(path, dir=bool(isdir))]

            if parent_id == -1:
                #put entries in result list if they've reached top level
                musicEntries += entries
            else:
                #otherwise map parent id to dict
                incompleteMusicEntries[parent_id] = incompleteMusicEntries.get(parent_id,[]) + entries

        if incompleteMusicEntries:
            #recurse for all incomplete entries
            musicEntries += self.musicEntryFromFileIds(
                                incompleteMusicEntries.keys(),
                                incompleteMusicEntries = incompleteMusicEntries,
                                mode = mode
                            )
        return musicEntries

    def register_file_with_db(self, fileobj):
        """add data in File object to relevant tables in media database"""
        try:
            self.add_to_file_table(fileobj)
            word_ids = self.add_to_dictionary_table(fileobj.name)
            self.add_to_search_table(fileobj.uid, word_ids)
            return fileobj
        except UnicodeEncodeError as e:
            log.e(_("wrong encoding for filename '%s' (%s)"), fileobj.relpath, e.__class__.__name__)


    def add_to_file_table(self, fileobj):
        cursor = self.conn.execute('INSERT INTO files (parent, filename, filetype, isdir) VALUES (?,?,?,?)', (fileobj.parent.uid if fileobj.parent else -1, fileobj.name, fileobj.ext, 1 if fileobj.isdir else 0))
        rowid = cursor.lastrowid
        fileobj.uid = rowid
        return fileobj


    def add_to_dictionary_table(self, filename):
        word_ids = []
        for word in set(SQLiteCache.searchterms(filename)):
            wordrowid = self.conn.execute('''SELECT rowid FROM dictionary WHERE word = ? LIMIT 0,1''', (word,)).fetchone()
            if wordrowid is None:
                wordrowid = self.conn.execute('''INSERT INTO dictionary (word) VALUES (?)''', (word,)).lastrowid
            else:
                wordrowid = wordrowid[0]
            word_ids.append(wordrowid)
        return word_ids


    def add_to_search_table(self, file_id, word_id_seq):
        self.conn.executemany('INSERT INTO search (drowid, frowid) VALUES (?,?)',
                              ((wid, file_id) for wid in word_id_seq))


    def remove_recursive(self, fileobj, progress=None):
        '''recursively remove fileobj and all its children from the media db.'''


        if progress is None:
            log.i(
                  _('removing dead reference(s): %s "%s"'),
                  'directory' if fileobj.isdir else 'file',
                  fileobj.relpath,
                  )
            factory = None
            remove = lambda item: self.remove_file(item)
        else:
            def factory(new, pnt):
                if pnt is None:
                    return (new, None, progress)
                return (new, pnt, pnt[2].spawnchild('[-] ' + new.relpath))
            remove = lambda item: (self.remove_file(item[0]), item[2].tick())

        deld = 0
        try:
            with self.conn:
                for item in self.db_recursive_filelister(fileobj, factory):
                    remove(item)
                    deld += 1
        except Exception as e:
            log.e(_('error while removing dead reference(s): %s'), e)
            log.e(_('rolled back to safe state.'))
            return 0
        else:
            return deld


    def remove_file(self, fileobj):
        '''removes a file entry from the db, which means removing:
            - all search references,
            - all dictionary words which were orphaned by this,
            - the reference in the files table.'''
        try:
            dead_wordids = self.remove_from_search(fileobj.uid)
            self.remove_all_from_dictionary(dead_wordids)
            self.remove_from_files(fileobj.uid)
        except Exception as exception:
            log.ex(exception)
            log.e(_('error removing entry for %s'), fileobj.relpath)
            raise exception


    def remove_from_search(self, fileid):
        '''remove all references to the given fileid from the search table.
        returns a list of all wordids which had their last search references
        deleted during this operation.'''
        foundlist = self.conn.execute(
                            'SELECT drowid FROM search' \
                            ' WHERE frowid=?', (fileid,)) \
                            .fetchall()
        wordset = set([t[0] for t in foundlist])

        self.conn.execute('DELETE FROM search WHERE frowid=?', (fileid,))

        for wid in set(wordset):
            count = self.conn.execute('SELECT count(*) FROM search'
                                      ' WHERE drowid=?', (wid,)) \
                                      .fetchone()[0]
            if count:
                wordset.remove(wid)
        return wordset


    def remove_all_from_dictionary(self, wordids):
        '''deletes all words with the given ids from the dictionary table'''
        if not wordids:
            return
        args = list(zip(wordids))
        self.conn.executemany('DELETE FROM dictionary WHERE rowid=(?)', args)


    def remove_from_files(self, fileid):
        '''deletes the given file id from the files table'''
        self.conn.execute('DELETE FROM files WHERE rowid=?', (fileid,))


    def db_recursive_filelister(self, fileobj, factory=None):
        """generator: enumerates fileobj and children listed in the db as File
        objects. each item is returned before children are fetched from db.
        this means that fileobj gets bounced back as the first return value."""
        if factory is None:
            queue = deque((fileobj,))
            while queue:
                item = queue.popleft()
                yield item
                queue.extend(self.fetch_child_files(item))
        else:
            queue = deque((factory(fileobj, None),))
            child = lambda parent: lambda item: factory(item, parent)
            while queue:
                item = queue.popleft()
                yield item
                queue.extend(map(child(item), self.fetch_child_files(item[0])))


    def fetch_child_files(self, fileobj, sort=True, reverse=False):
        '''fetches from files table a list of all File objects that have the
        argument fileobj as their parent.'''
        id_tuples = self.conn.execute(
                            'SELECT rowid, filename, filetype, isdir' \
                            ' FROM files where parent=?', (fileobj.uid,)) \
                            .fetchall()
        if sort:
            id_tuples = sorted(id_tuples, key=lambda t: t[1], reverse=reverse)
        return (File(name + ext,
                     parent=fileobj,
                     isdir=False if isdir == 0 else True,
                     uid=uid) for uid, name, ext, isdir in id_tuples)


    def normalize_basedir(self):
        basedir = cherry.config['media.basedir']
        basedir = os.path.normcase(basedir)
        if len(basedir) > 1:
            basedir = basedir.rstrip(os.path.sep)
        cherry.config = cherry.config.replace({'media.basedir': basedir})
        log.d(_('media base directory: %r') % basedir)


    @util.timed
    def full_update(self):
        '''verify complete media database against the filesystem and make
        necesary changes.'''

        log.i(_('running full update...'))
        try:
            self.update_db_recursive(cherry.config['media.basedir'], skipfirst=True)
        except:
            log.e(_('error during media update. database update incomplete.'))
        finally:
            self.update_word_occurrences()
            log.i(_('media database update complete.'))


    def partial_update(self, path, *paths):
        basedir = cherry.config['media.basedir']
        paths = (path,) + paths
        log.i(_('updating paths: %s') % (paths,))
        for path in paths:
            path = os.path.normcase(path)
            abspath = path if os.path.isabs(path) else os.path.join(basedir, path)
            normpath = os.path.normpath(abspath)
            if not normpath.startswith(basedir):
                log.e(_('path is not in basedir. skipping %r') % abspath)
                continue
            log.i(_('updating %r...') % path)
            try:
                self.update_db_recursive(normpath, skipfirst=False)
            except Exception as exception:
                log.e(_('update incomplete: %r'), exception)
        self.update_word_occurrences()
        log.i(_('done updating paths.'))


    def update_db_recursive(self, fullpath, skipfirst=False):
        '''recursively update the media database for a path in basedir'''

        from collections import namedtuple
        Item = namedtuple('Item', 'infs indb parent progress')
        def factory(fs, db, parent):
            fileobj = fs if fs is not None else db
            name = fileobj.relpath or fileobj.fullpath if fileobj else '<path not found in filesystem or database>'
            if parent is None:
                progress = ProgressTree(name=name)
                maxlen = lambda s: util.trim_to_maxlen(50, s)
                progress.reporter = ProgressReporter(lvl=1, namefmt=maxlen)
            else:
                progress = parent.progress.spawnchild(name)
            return Item(fs, db, parent, progress)

        log.d(_('recursive update for %s'), fullpath)
        generator = self.enumerate_fs_with_db(fullpath, itemfactory=factory)
        skipfirst and generator.send(None)
        adds_without_commit = 0
        add = 0
        deld = 0
        try:
            with self.conn:
                for item in generator:
                    infs, indb, progress = (item.infs, item.indb, item.progress)
                    if infs and indb:
                        if infs.isdir != indb.isdir:
                            progress.name = '[±] ' + progress.name
                            deld += self.remove_recursive(indb, progress)
                            self.register_file_with_db(infs)
                            adds_without_commit = 1
                        else:
                            infs.uid = indb.uid
                            progress.name = '[=] ' + progress.name
                    elif indb:
                        progress.name = '[-] ' + progress.name
                        deld += self.remove_recursive(indb, progress)
                        adds_without_commit = 0
                        continue    # progress ticked by remove; don't tick again
                    elif infs:
                        self.register_file_with_db(item.infs)
                        adds_without_commit += 1
                        progress.name = '[+] ' + progress.name
                    else:
                        progress.name = '[?] ' + progress.name
                    if adds_without_commit == AUTOSAVEINTERVAL:
                        self.conn.commit()
                        add += adds_without_commit
                        adds_without_commit = 0
                    progress.tick()
        except Exception as exc:
            log.e(_("error while updating media: %s %s"), exc.__class__.__name__, exc)
            log.e(_("rollback to previous commit."))
            traceback.print_exc()
            raise exc
        finally:
            add += adds_without_commit
            log.i(_('items added %d, removed %d'), add, deld)
            self.load_db_to_memory()

    def update_word_occurrences(self):
        log.i(_('updating word occurrences...'))
        self.conn.execute('''UPDATE dictionary SET occurrences = (
                select count(*) from search WHERE search.drowid = dictionary.rowid
            )''')

    def enumerate_fs_with_db(self, startpath, itemfactory=None):
        '''
        Starting at `startpath`, enumerates path items containing representations
        for each path as it exists in the filesystem and the database,
        respectively.

        `startpath` and `basedir` need to be absolute paths, with `startpath`
        being a subtree of `basedir`. However, no checks are being promised to
        enforce the latter requirement.

        Iteration is depth-first, but each path is returned before its children
        are determined, to enable recursive corrective action like deleting a
        whole directory from the database at once. Accordingly, the first item
        to be returned will represent `startpath`. This item is guaranteed to be
        returned, even if `startpath` does not exist in filesystem and database;
        all other items will have at least one existing representation.

        `basedir`, should it happen to equal `startpath`, will be returned as an
        item. It is up to the caller to properly deal with it.

        Each item has the following attributes: `infs`, a File object
        representing the path in the filesystem; `indb`, a File object
        representing the path in the database; and `parent`, the parent item.
        All three can be None, signifying non-existence.

        It is possible to customize item creation by providing an `itemfactory`.
        The argument must be a callable with the following parameter signature::

            itemfactory(infs, indb, parent [, optional arguments])

        and must return an object satisfying the above requirements for an item.
        '''
        from backport.collections import OrderedDict
        basedir = cherry.config['media.basedir']
        startpath = os.path.normcase(startpath).rstrip(os.path.sep)
        Item = itemfactory
        if Item is None:
            from collections import namedtuple
            Item = namedtuple('Item', 'infs indb parent')
        assert os.path.isabs(startpath), _('argument must be an abolute path: "%s"') % startpath
        assert startpath.startswith(basedir), _('argument must be a path in basedir (%s): "%s"') % (basedir, startpath)

        if not os.path.exists(startpath):
            fsobj = None
        elif startpath == basedir:
            fsobj = File(basedir)
        elif startpath > basedir:
            pathparent, pathbase = os.path.split(startpath)
            fsparent = self.db_find_file_by_path(pathparent, create=True)
            assert fsparent is not None, _('parent path not in database: %r') % pathparent
            fsobj = File(pathbase, fsparent)
            del pathparent, pathbase, fsparent
        else:
            assert False, _("shouldn't get here! (argument path not in basedir)")

        dbobj = self.db_find_file_by_path(startpath)
        stack = deque()
        stack.append(Item(fsobj, dbobj, None))
        while stack:
            item = stack.pop()
            yield item
            dbchildren = {}
            if item.indb:
                dbchildren = OrderedDict((
                                   (f.basename, f)
                                   for f in self.fetch_child_files(item.indb)
                                   ))
            if item.infs and item.infs.isdir:
                for fs_child in File.inputfilter(item.infs.children()):
                    db_child = dbchildren.pop(fs_child.basename, None)
                    stack.append(Item(fs_child, db_child, item))
            for db_child in dbchildren.values():
                stack.append(Item(None, db_child, item))
            del dbchildren


    def db_find_file_by_path(self, fullpath, create=False):
        '''Finds an absolute path in the file database. If found, returns
        a File object matching the database record; otherwise, returns None.
        Paths matching a media basedir are a special case: these will yield a
        File object with an invalid record id matching the one listed by its
        children.
        '''
        basedir = cherry.config['media.basedir']
        fullpath = os.path.normpath(fullpath)
        if os.path.isabs(fullpath):
            if not fullpath.startswith(basedir):
                return None
        else:
            fullpath = os.path.join(basedir, fullpath)

        relpath = fullpath[len(basedir):].strip(os.path.sep)
        root = File(basedir, isdir=True, uid= -1)
        if not relpath:
            return root

        file = root
        for part in relpath.split(os.path.sep):
            found = False
            for child in self.fetch_child_files(file):  # gotta be ugly: don't know if name/ext split in db
                if part == child.basename:
                    found = True
                    file = child
                    break
            if not found:
                if create:
                    file = File(part, parent=file)
                    log.i(_('creating database entry for %r'), file.relpath)
                    self.register_file_with_db(file)
                else:
                    return None
        return file


if sys.version_info < (3,):
    from codecs import decode
    encoding = sys.getfilesystemencoding()
    is_unicode = lambda s: isinstance(s, type(''))  # from unicode_literals import

    def _unicode_listdir(dirname):
        for name in os.listdir(dirname):
            try:
                yield (name if is_unicode(name) else decode(name, encoding))
            except UnicodeError:
                log.e(_('unable to decode filename %r in %r; skipping.'),
                    name, dirname)
else:
    _unicode_listdir = os.listdir


class File():
    def __init__(self, path, parent=None, isdir=None, uid= -1):
        assert isinstance(path, type('')), _('expecting unicode path, got %s') % type(path)

        if len(path) > 1:
            path = path.rstrip(os.path.sep)
        if parent is None:
            self.root = self
            self.basepath = os.path.dirname(path)
            self.basename = os.path.basename(path)
        else:
            if os.path.sep in path:
                raise ValueError(_('non-root filepaths must be direct relative to parent: path: %s, parent: %s') % (path, parent))
            self.root = parent.root
            self.basename = path
        self.uid = uid
        self.parent = parent
        if isdir is None:
            self.isdir = os.path.isdir(os.path.abspath(self.fullpath))
        else:
            self.isdir = isdir

    def __str__(self):
        return self.fullpath

    def __repr__(self):
        return ('%(fp)s%(isdir)s [%(n)s%(x)s] (%(id)s)%(pid)s' %
             {'fp': self.fullpath,
              'isdir': '/' if self.isdir else '',
              'n': self.name,
              'x': self.ext,
              'id': self.uid,
              'pid': ' -> ' + str(self.parent.uid) if self.parent and self.parent.uid > -1 else ''
              })

    @property
    def relpath(self):
        '''this File's path relative to its root'''
        up = self
        components = deque()
        while up != self.root:
            components.appendleft(up.basename)
            up = up.parent
        return os.path.sep.join(components)

    @property
    def fullpath(self):
        '''this file's relpath with leading root path'''
        fp = os.path.join(self.root.basepath, self.root.basename, self.relpath)
        if len(fp) > 1:
            fp = fp.rstrip(os.path.sep)
        return fp

    @property
    def name(self):
        '''if this file.isdir, its complete basename; otherwise its basename
        without extension suffix'''
        if self.isdir:
            name = self.basename
        else:
            name = os.path.splitext(self.basename)[0]
        return name

    @property
    def ext(self):
        '''if this file.isdir, the empty string; otherwise the extension suffix
        of its basename'''
        if self.isdir:
            ext = ''
        else:
            ext = os.path.splitext(self.basename)[1]
        return ext

    @property
    def exists(self):
        '''True if this file's fullpath exists in the filesystem'''
        return os.path.exists(self.fullpath)

    @property
    def islink(self):
        '''True if this file is a symbolic link'''
        return os.path.islink(self.fullpath)

    def children(self, sort=True, reverse=True):
        '''If self.isdir and self.exists, return an iterable of fileobjects
        corresponding to its direct content (non-recursive).
        Otherwise, log an error and return ().
        '''
        try:
            content = _unicode_listdir(self.fullpath)
            if sort:
                content = sorted(content, reverse=reverse)
            return (File(name, parent=self) for name in content)
        except OSError as error:
            log.e(_('cannot list directory: %s'), error)
            return ()


    @classmethod
    def inputfilter(cls, files_iter):
        basedir = cherry.config['media.basedir']
        for f in files_iter:
            if not f.exists:
                log.e(_('file not found: %s. skipping.' % f.fullpath))
                continue
            if not f.fullpath.startswith(basedir):
                log.e(_('file not in basedir: %s. skipping.') % f.fullpath)
                continue
            if f.islink:
                rp = os.path.realpath(f.fullpath)
                if os.path.abspath(basedir).startswith(rp) \
                    or (os.path.islink(basedir)
                        and
                        os.path.realpath(basedir).startswith(rp)):
                    log.e(_(("Cyclic symlink found: %s creates a circle "
                             "if followed. Skipping.")) % f.relpath)
                    continue
                if not (f.parent is None or f.parent.parent is None):
                    log.e(_(("Deeply nested symlink found: %s . All links "
                          "must be directly in your basedir (%s). The "
                          "program cannot safely handle them otherwise."
                          " Skipping.")) % (f.relpath, os.path.abspath(basedir)))
                    continue
            yield f

class MemoryDB:
    def __init__(self, db_file, table_to_dump):
        log.i(_("Loading files database into memory..."))
        self.db = sqlite3.connect(':memory:', check_same_thread=False)
        cu = self.db.cursor()
        cu.execute('attach database "%s" as attached_db' % db_file)
        cu.execute("select sql from attached_db.sqlite_master "
                   "where type='table' and name='" + table_to_dump + "'")
        sql_create_table = cu.fetchone()[0]
        cu.execute(sql_create_table);
        cu.execute("insert into " + table_to_dump +
                   " select * from attached_db." + table_to_dump)
        self.db.commit()
        cu.execute("detach database attached_db")



########NEW FILE########
__FILENAME__ = helpers
#!/usr/bin/env python3
# -*- coding: utf-8 -*- #
#
# CherryMusic - a standalone music server
# Copyright (c) 2012-2014 Tom Wallroth & Tilman Boerner
#
# Project page:
#   http://fomori.org/cherrymusic/
# Sources on github:
#   http://github.com/devsnd/cherrymusic/
#
# CherryMusic is based on
#   jPlayer (GPL/MIT license) http://www.jplayer.org/
#   CherryPy (BSD license) http://www.cherrypy.org/
#
# licensed under GNU GPL version 3 (or later)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
#
""" Things that are helpful when testing the CherryMusic backend """

import shutil
import tempfile

from contextlib import contextmanager

from mock import *
from nose.tools import *

from cherrymusicserver import configuration
from cherrymusicserver import database
from cherrymusicserver import service

_default_config = configuration.from_defaults()     # load only once

@contextmanager
def cherryconfig(override=None):
    """ Context manager providing a CherryMusic default configuration
        that can be overridden.

        :param dict override: The overridden config values
    """
    override = override or {}
    config = _default_config.update(override)
    with patch('cherrymusicserver.config', config):
        yield config

@contextmanager
def tempdir(name_hint, keep=False):
    """ Context manager providing a temp directory to do stuff in.

        Yields the dir name. Deletes the directory on exit by default.

        :param str name_hint:  Part of the temp dir's name
        :param bool keep:   If true, don't delete the directory.
    """
    try:
        tmpdir = tempfile.mkdtemp(prefix=name_hint + '.')
        yield tmpdir
    finally:
        if not keep:
            shutil.rmtree(tmpdir, ignore_errors=False, onerror=None)


@contextmanager
def dbconnector(connector=None):
    """ Context manager providing a 'dbconnector' service

        :param database.AbstractConnector connector: Connector instance. MemConnector by default.
    """
    connector = connector or database.sql.MemConnector()
    real_get = service.get
    fake_get = lambda handle: connector if handle == 'dbconnector' else real_get(handle)
    with patch('cherrymusicserver.service.get', fake_get):
        yield connector
_dbconnector = dbconnector

def cherrytest(config=None, dbconnector=None):
    """ Function decorator that does some standard CherryMusic setup.

        It wraps the function call into a :func:`cherryconfig` and
        :func:`dbconnector` context.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            with cherryconfig(config):
                with _dbconnector(dbconnector):
                    func(*args, **kwargs)
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    return decorator


########NEW FILE########
__FILENAME__ = test_albumartfetcher
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# CherryMusic - a standalone music server
# Copyright (c) 2012 - 2014 Tom Wallroth & Tilman Boerner
#
# Project page:
#   http://fomori.org/cherrymusic/
# Sources on github:
#   http://github.com/devsnd/cherrymusic/
#
# CherryMusic is based on
#   jPlayer (GPL/MIT license) http://www.jplayer.org/
#   CherryPy (BSD license) http://www.cherrypy.org/
#
# licensed under GNU GPL version 3 (or later)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
#

import nose

from mock import *
from nose.tools import *

from cherrymusicserver import log
log.setTest()


from cherrymusicserver import albumartfetcher

def test_methods():
    for method in albumartfetcher.AlbumArtFetcher.methods:
        yield try_method, method

def try_method(method, timeout=5):
    fetcher = albumartfetcher.AlbumArtFetcher(method=method, timeout=timeout)
    results = fetcher.fetchurls('best of')
    ok_(results, "method {0!r} results: {1}".format(method, results))


if __name__ == '__main__':
    nose.runmodule()

########NEW FILE########
__FILENAME__ = test_cherrymodel
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# CherryMusic - a standalone music server
# Copyright (c) 2012 - 2014 Tom Wallroth & Tilman Boerner
#
# Project page:
#   http://fomori.org/cherrymusic/
# Sources on github:
#   http://github.com/devsnd/cherrymusic/
#
# CherryMusic is based on
#   jPlayer (GPL/MIT license) http://www.jplayer.org/
#   CherryPy (BSD license) http://www.cherrypy.org/
#
# licensed under GNU GPL version 3 (or later)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
#

import nose
import os

from mock import *
from nose.tools import *

from collections import defaultdict

from cherrymusicserver import log
log.setTest()

from cherrymusicserver import cherrymodel

def cherryconfig(cfg=None):
    from cherrymusicserver import configuration
    cfg = cfg or {}
    c = configuration.from_defaults()
    c = c.update({'media.basedir': os.path.join(os.path.dirname(__file__), 'data_files')})
    c = c.update(cfg)
    return c

@patch('cherrymusicserver.cherrymodel.cherry.config', cherryconfig())
@patch('cherrymusicserver.cherrymodel.os')
@patch('cherrymusicserver.cherrymodel.CherryModel.cache')
@patch('cherrymusicserver.cherrymodel.isplayable', lambda _: True)
def test_hidden_names_listdir(cache, os):
    model = cherrymodel.CherryModel()
    os.path.join = lambda *a: '/'.join(a)

    content = ['.hidden']
    cache.listdir.return_value = content
    os.listdir.return_value = content
    assert not model.listdir('')

    content = ['not_hidden.mp3']
    cache.listdir.return_value = content
    os.listdir.return_value = content
    assert model.listdir('')


@patch('cherrymusicserver.cherrymodel.cherry.config', cherryconfig({'search.maxresults': 10}))
@patch('cherrymusicserver.cherrymodel.CherryModel.cache')
@patch('cherrymusicserver.cherrymodel.cherrypy')
def test_hidden_names_search(cherrypy, cache):
    model = cherrymodel.CherryModel()

    cache.searchfor.return_value = [cherrymodel.MusicEntry('.hidden.mp3', dir=False)]
    assert not model.search('something')

    cache.searchfor.return_value = [cherrymodel.MusicEntry('not_hidden.mp3', dir=False)]
    assert model.search('something')

@patch('cherrymusicserver.cherrymodel.cherry.config', cherryconfig({'search.maxresults': 10}))
@patch('cherrymusicserver.cherrymodel.CherryModel.cache')
@patch('cherrymusicserver.cherrymodel.cherrypy')
def test_hidden_names_listdir(cherrypy, cache):
    model = cherrymodel.CherryModel()
    dir_listing = model.listdir('')
    assert len(dir_listing) == 1
    assert dir_listing[0].path == 'not_hidden.mp3'


if __name__ == '__main__':
    nose.runmodule()

########NEW FILE########
__FILENAME__ = test_configuration
#!/usr/bin/env python3
#
# CherryMusic - a standalone music server
# Copyright (c) 2012 - 2014 Tom Wallroth & Tilman Boerner
#
# Project page:
#   http://fomori.org/cherrymusic/
# Sources on github:
#   http://github.com/devsnd/cherrymusic/
#
# CherryMusic is based on
#   jPlayer (GPL/MIT license) http://www.jplayer.org/
#   CherryPy (BSD license) http://www.cherrypy.org/
#
# licensed under GNU GPL version 3 (or later)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
#

import unittest
from nose.tools import raises

try:
    from collections import OrderedDict
except ImportError:
    from backport.collections import OrderedDict

import cherrymusicserver.configuration as cfg
from cherrymusicserver.configuration import Key, Property, Configuration

from cherrymusicserver import log
log.setTest()


class TestKey(object):

    def testConstructor(self):
        assert '' == str(Key())
        assert '' == str(Key(None))
        assert '' == str(Key(str()))
        assert 'a.b' == str(Key('a.b'))
        assert 'a.b' == str(Key('A.B'))

    def testValidation(self):
        for name in '. 1 _ $'.split() + [object()]:
            try:
                Key(name)
            except cfg.ConfigError:
                pass
            else:
                assert False, 'must not accept {0} as Key name'.format(name)

    def testEquals(self):
        assert None == Key()
        assert '' == Key()
        assert Key() == Key()
        assert Key('a') == Key('A')
        assert 'a' == Key('a')
        assert Key('a') != Key('b')
        assert not('a' != Key('A'))

    def testAdd(self):
        assert '' == Key() + Key()
        assert '' == Key() + None
        assert 'string' == Key() + 'string'
        assert 'a.b' == Key('a') + 'b'

    def testRightAdd(self):
        assert 'a.b' == 'a' + Key('b')

    def testAssignAdd(self):
        key = Key('a')
        second_key = key

        second_key += 'b'

        assert key is not second_key
        assert 'a.b' == second_key, (second_key)
        assert 'a' == key, (key)


class TestProperty(object):

    attributes = 'key value type valid readonly hidden doc'.split()

    def test_tupleness_attributes_and_defaults(self):
        """A property is a tuple with named values."""
        default = OrderedDict.fromkeys(self.attributes, None)
        default['key'] = ''
        p = Property()

        assert tuple(default.values()) == p, p
        for attrname, value in default.items():
            assert getattr(p, attrname) == value

    def test_key_is_normalized(self):
        assert 'x.y' == Property('X.Y').key

    def test_type_inferrence(self):
        for T in (bool, int, float, str, type(''),):
            assert T.__name__ == Property(value=T()).type, T

        class UnknownType:
            pass

        assert None == Property(value=UnknownType()).type

        assert 'float' == Property('', 4, float).type

    def test_autocast(self):
        assert 13 == Property('', '13', int).value

    @raises(cfg.ConfigValueError)
    def test_bad_value_for_type(self):
        Property('', 'a', int)

    @raises(cfg.ConfigValueError)
    def test_validation_by_regex(self):
        assert 0 == Property('', 0, valid='[0-9]').value
        Property('', ['x'], valid='[0-9]')

    @raises(cfg.ConfigValueError)
    def test_validation_by_callable(self):
        Property('', False, valid=lambda v: v)

    def test_None_value_is_not_cast_or_validated(self):
        assert None == Property(type=bool, valid=lambda v: v is not None).value

    def test_to_dict(self):
        p = Property('bla', 12, int, '\d+', True, True, '')

        assert p == Property(**p.to_dict())

    def test_replace_without_values(self):
        p = Property('a', 5, int, '\d+', False, False, 'doc')

        assert p == p.replace()
        assert p == p.replace(**dict.fromkeys(self.attributes))

    @raises(cfg.ConfigWriteError)
    def test_cannot_replace_if_readonly(self):
        Property(readonly=True).replace()

    @raises(cfg.ConfigWriteError)
    def test_replace_key(self):
        assert 'different.key' == Property().replace(key='different.key').key
        Property('some.key').replace(key='different.key')

    def test_replace_value(self):
        p = Property(value='original')

        assert 'new' == p.replace(value='new').value
        assert 'original' == p.replace(value=None).value

    def test_replace_type(self):
        assert 'int' == Property().replace(type=int).type
        assert 'int' == Property(type=int).replace(type=str).type

    def test_replace_attributes_only_overridden_if_None(self):
        for attrname in self.attributes[3:]:
            good = {attrname: ''}     # a False value != None to make readonly work
            bad = {attrname: 'unwanted'}
            assert '' == getattr(Property().replace(**good), attrname)
            assert '' == getattr(Property(**good).replace(**bad), attrname)

    def test_immutable(self):
        p = Property()
        assert p is not p.replace(**p.to_dict())

        for attrname in self.attributes:
            try:
                setattr(p, attrname, None)
            except AttributeError:
                pass
            else:
                assert False, 'must not be able to change %r ' % (attrname,)


class TestConfiguration:

    def test_constructor(self):
        from collections import Mapping

        assert isinstance(Configuration(), Mapping)
        assert not len(Configuration())

    def test_equals_works_with_dict(self):
        assert {} == Configuration()
        assert {'a': 1} != Configuration()

    def test_from_and_to_properties(self):
        properties = [Property('a'),
                      Property('a.b', 5, int, '\d+', True, True, 'doc'),
                      Property('b', 5, int, '\d+', True, True, 'doc')]

        conf = Configuration.from_properties(properties)
        assert properties == list(conf.to_properties())
        assert 'a' in conf
        assert 'a.b' in conf
        assert 'b' in conf

    def test_from_mapping(self):
        mapping = {'a': None, 'a.b': 5, 'b': 7}
        assert mapping == Configuration.from_mapping(mapping)

    def test_attribute_access(self):
        p = Property('b', 5, int, '\d+', True, True, 'doc')
        conf = Configuration.from_properties([p])

        assert 5 == conf['b']
        assert p == conf.property('b')

    def test_builder(self):
        properties = [Property('a', 5), Property('a.b', 6, int, '6.*', True, True, 'doc')]
        cb = cfg.ConfigBuilder()

        with cb['a'] as a:
            a.value = 5
            with a['b'] as ab:
                ab.value = 6
                ab.valid = '6.*'
                ab.readonly = True
                ab.hidden = True
                ab.doc = 'doc'

        assert properties == list(cb.to_configuration().to_properties())

    def test_inheritance_of_property_attributes(self):
        cb = cfg.ConfigBuilder()
        with cb['parent'] as parent:
            parent.valid = '.*'
            parent.readonly = True
            parent.hidden = True
            with parent['child'] as child:
                child.value = 4

        childprop = cb.to_configuration().property('parent.child')

        assert '.*' == childprop.valid
        assert childprop.readonly
        assert childprop.hidden

    def test_update(self):
        conf = Configuration.from_properties([Property('b', 'old')])
        newvalues = {'b': 'replaced', 'c': 'new'}
        assert newvalues == conf.update(newvalues)

    def test_replace_changes_existing(self):
        conf = Configuration.from_properties([Property('b', 'old')])
        newvalues = {'b': 'replaced'}
        assert newvalues == conf.replace(newvalues)

    @raises(cfg.ConfigKeyError)
    def test_replace_cannot_add_new(self):
        Configuration().replace({'new': None})


class TestTransformers(unittest.TestCase):

    def test_value_conversions(self):

        def assert_value_conversion(kind, testvalue, expected):
            p = Property('test', testvalue, type=kind)
            actual = p.value
            self.assertEqual(
                expected, actual,
                ('Bad %s conversion for value: %r! expect: %r, actual: %r'
                 % (kind, p.value, expected, actual)))

        def assert_value_conversions(kind, val_exp_pairs):
            for testvalue, expected in val_exp_pairs:
                assert_value_conversion(kind, testvalue, expected)

        assert_value_conversions('str', (('  ', ''),
                                         (None, None),
                                         ))

        assert_value_conversions('int', (('99', 99),
                                         ('-1', -1),
                                         (None, None),
                                         ))

        assert_value_conversions('float', (('99', 99),
                                           ('1.2', 1.2),
                                           ('1.2e3', 1200),
                                           (None, None),
                                           ))

        assert_value_conversions('bool', (('1', True),
                                          ('0', False),
                                          ('Yes', True),
                                          ('Y', True),
                                          ('NO', False),
                                          ('N', False),
                                          ('truE', True),
                                          ('False', False),
                                          ('', False),
                                          (None, None),
                                          ))


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_database
#!/usr/bin/env python3
#
# CherryMusic - a standalone music server
# Copyright (c) 2012 - 2014 Tom Wallroth & Tilman Boerner
#
# Project page:
#   http://fomori.org/cherrymusic/
# Sources on github:
#   http://github.com/devsnd/cherrymusic/
#
# CherryMusic is based on
#   jPlayer (GPL/MIT license) http://www.jplayer.org/
#   CherryPy (BSD license) http://www.cherrypy.org/
#
# licensed under GNU GPL version 3 (or later)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
#

import unittest
import sqlite3
import os


from cherrymusicserver import log
log.setTest()

import cherrymusicserver.database.defs as defs
from cherrymusicserver.database.sql import MemConnector


class TestDefs(unittest.TestCase):

    def setUp(self):
        defdir = os.path.dirname(defs.__file__)
        dbnames = tuple(n for n in os.listdir(defdir) if not n.startswith('__'))
        self.defs = dict((name, defs.get(name)) for name in dbnames)

    def test_all_databases_are_defined(self):
        required = ('cherry.cache', 'playlist', 'user', 'useroptions')
        missing = set(required) - set(self.defs)
        assert not missing, "no database definitions must be missing " + str(missing)

    def test_versionnames_are_all_ints(self):
        def check(dbdef):
            "version names must all be integers"
            nonint = [version for version in dbdef if not version.isdigit()]
            if nonint:
                yield nonint
        self.run_forall_defs(check)

    def test_versionnames_are_consecutive_starting_0_or_1(self):
        def check(dbdef):
            "versions must be consecutive and start with 0 or 1"
            versions = sorted(int(v) for v in dbdef)
            min, max = versions[0], versions[-1]
            expected = list(range(1 if min else 0, max + 1))
            if expected != versions:
                yield versions
        self.run_forall_defs(check)

    def test_versionkeys_required_are_present(self):
        required = ('create.sql', 'drop.sql', 'update.sql')
        initially_ok = ('update.sql',)

        def check(dbdef):
            "database version must include required keys"
            for vnum, vdef in dbdef.items():
                missing = set(required) - set(vdef)
                if vnum == min(dbdef):
                    missing -= set(initially_ok)
                if missing:
                    yield vnum, missing
        self.run_forall_defs(check)

    def test_versionpermutations_are_updatable(self):
        def check(dbdef):
            "incremental updates must work for all versions"
            start, stop = int(min(dbdef)), int(max(dbdef)) + 1
            program = ((i, range(i + 1, stop)) for i in range(start, stop))
            for base, updates in program:
                connector = MemConnector().bound(None)  # new MemConnector for fresh db
                try:
                    create(dbdef, base, connector)
                    update(dbdef, updates, connector)
                except AssertionError as e:
                    yield 'base version: {0} {1}'.format(base, e.args[0])
                    break   # don't accumulate errors
        self.run_forall_defs(check)

    def test_versionremoval_drop_clears_db(self):
        def check(dbdef):
            "drop script must clear the database"
            for version in dbdef:
                connector = MemConnector().bound(None)
                create(dbdef, version, connector)
                drop(dbdef, version, connector)
                remaining = connector.execute(
                    "SELECT * FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"
                ).fetchall()
                if remaining:
                    yield '{0}:drop.sql'.format(version), remaining
        self.run_forall_defs(check)

    def run_forall_defs(self, check):
        errors = []
        for dbname, dbdef in self.defs.items():
            for error in check(dbdef):
                errors += ['{0}: {1}: {2}'.format(check.__doc__, dbname, error)]
        assert not errors, os.linesep + os.linesep.join(errors)


def create(dbdef, vnum, connector):
    with connector.connection() as c:
        runscript(dbdef, vnum, 'create.sql', c)
        runscript(dbdef, vnum, 'after.sql', c, missing_ok=True)


def drop(dbdef, vnum, connector):
    with connector.connection() as c:
        runscript(dbdef, vnum, 'drop.sql', c)


def update(dbdef, vnums, connector):
    for vnum in vnums:
        with connector.connection() as c:
            runscript(dbdef, vnum, 'update.sql', c)
            runscript(dbdef, vnum, 'after.sql', c, missing_ok=True)


def runscript(dbdef, vnum, scriptname, conn, missing_ok=False):
    '''Run an SQL script, statement per statement, and give a helpful
    message on error.
    '''
    try:
        script = dbdef[str(vnum)][scriptname]
    except KeyError:
        if missing_ok:
            return
        raise
    lno = 1
    for stmt in split_sqlscript(script):
        linecount = stmt.count('\n')   # yeah, linux linesep.
        try:
            cursor = conn.cursor()
            cursor.execute(stmt.strip())
        except sqlite3.Error as e:
            if stmt.splitlines() and not stmt.splitlines()[0].strip():  # skip 1st line if empty
                lno += 1
                linecount -= 1
            msg = '{br}{script}:{br}{listing}{br}{br}{error}'.format(
                script='{0}:{1}:{2}'.format(vnum, scriptname, lno),
                listing=os.linesep.join(script_lines(script, lno, linecount + 1)),
                error=e,
                br=os.linesep)
            raise AssertionError(msg)
        else:
            lno += linecount
        finally:
            cursor.close()


def split_sqlscript(script):
    import re
    stmts = [x + ';' for x in script.split(';')]
    i = 0
    while i < len(stmts):
        if re.search(r'\bBEGIN\b', stmts[i], re.I):
            while (i + 1) < len(stmts) and not re.search(r'\bEND\b', stmts[i], re.I):
                stmts[i] += stmts[i + 1]
                del stmts[i + 1]
                if re.search(r'\bEND\b', stmts[i], re.I):
                    break
        i += 1
    return stmts


def script_lines(script, start=1, length=0):
    '''A range of lines from a text file, including line number prefix.'''
    stop = start + length
    gutterwidth = len(str(stop)) + 1
    i = 0
    for line in script.splitlines()[start - 1:stop - 1]:
        yield '{n:{w}}| {line}'.format(
            n=start + i,
            w=gutterwidth,
            line=line
        )
        i += 1


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_httphandler
#!/usr/bin/env python3
#
# CherryMusic - a standalone music server
# Copyright (c) 2012 - 2014 Tom Wallroth & Tilman Boerner
#
# Project page:
#   http://fomori.org/cherrymusic/
# Sources on github:
#   http://github.com/devsnd/cherrymusic/
#
# CherryMusic is based on
#   jPlayer (GPL/MIT license) http://www.jplayer.org/
#   CherryPy (BSD license) http://www.cherrypy.org/
#
# licensed under GNU GPL version 3 (or later)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
#

from mock import *
import unittest

import json

from contextlib import contextmanager

import cherrymusicserver as cherry

from cherrymusicserver import configuration
cherry.config = configuration.from_defaults()

from cherrymusicserver import httphandler
from cherrymusicserver import service
from cherrymusicserver.cherrymodel import MusicEntry

from cherrymusicserver import log

class MockAction(Exception):
    pass

class MockModel:
    def __init__(self):
        pass
    def search(self,value,isFastSearch=False):
        if isFastSearch:
            return [MusicEntry('fast mock result','fast mock result')]
        else:
            return [MusicEntry('mock result','mock result')]
    def motd(self):
        return "motd"
    def updateLibrary(self):
        raise MockAction('updateLibrary')
service.provide('cherrymodel', MockModel)


class CherryPyMock:
    def __init__(self):
        self.session = {'admin': False}

from cherrymusicserver.playlistdb import PlaylistDB
MockPlaylistDB = Mock(spec=PlaylistDB)
service.provide('playlist', MockPlaylistDB)


@contextmanager
def mock_auth():
    ''' Context where user 1 is logged in '''
    always_auth = lambda _: True
    root_id = lambda _: 1
    with patch('cherrymusicserver.httphandler.HTTPHandler.isAuthorized', always_auth):
        with patch('cherrymusicserver.httphandler.HTTPHandler.getUserId', root_id):
            yield


class TestHTTPHandler(unittest.TestCase):
    def setUp(self):
        self.http = httphandler.HTTPHandler(cherry.config)
        for apicall, func in self.http.handlers.items():
            try:
                getattr(self,'test_'+func.__name__)
            except AttributeError:
                print('Missing test for api handler %s!' % func.__name__)

    def tearDown(self):
        pass

    def call_api(self, action, **data):
        with mock_auth():
            return self.http.api(action, data=json.dumps(data))



    def test_api_search(self):
        """when attribute error is raised, this means that cherrypy
        session is used to authenticate the http request."""
        self.assertRaises(AttributeError, self.http.api, 'search')

    def test_api_fastsearch(self):
        """when attribute error is raised, this means that cherrypy
        session is used to authenticate the http request."""
        self.assertRaises(AttributeError, self.http.api, 'search')

    def test_api_rememberplaylist(self):
        """when attribute error is raised, this means that cherrypy
        session is used to authenticate the http request."""
        self.assertRaises(AttributeError, self.http.api, 'rememberplaylist')

    def test_api_saveplaylist(self):
        """when attribute error is raised, this means that cherrypy
        session is used to authenticate the http request."""
        self.assertRaises(AttributeError, self.http.api, 'saveplaylist')

    def test_api_deleteplaylist(self):
        try:
            print(self.call_api('deleteplaylist', playlistid=13))
        except httphandler.cherrypy.HTTPError as e:
            print(e)
        MockPlaylistDB.deletePlaylist.assert_called_with(13, ANY, override_owner=False)

    def test_api_loadplaylist(self):
        pass #needs to be tested in playlistdb

    def test_api_getmotd(self):
        """when attribute error is raised, this means that cherrypy
        session is used to authenticate the http request."""
        self.assertRaises(AttributeError, self.http.api, 'getmotd')

    def test_api_restoreplaylist(self):
        """when attribute error is raised, this means that cherrypy
        session is used to authenticate the http request."""
        self.assertRaises(AttributeError, self.http.api, 'restoreplaylist')

    def test_api_getplayables(self):
        """when attribute error is raised, this means that cherrypy
        session is used to authenticate the http request."""
        self.assertRaises(AttributeError, self.http.api, 'getplayables')

    def test_api_getuserlist(self):
        """when attribute error is raised, this means that cherrypy
        session is used to authenticate the http request."""
        self.assertRaises(AttributeError, self.http.api, 'getuserlist')

    def test_api_adduser(self):
        """when attribute error is raised, this means that cherrypy
        session is used to authenticate the http request."""
        self.assertRaises(AttributeError, self.http.api, 'adduser')

    def test_api_showplaylists(self):
        """when attribute error is raised, this means that cherrypy
        session is used to authenticate the http request."""
        self.assertRaises(AttributeError, self.http.api, 'showplaylists')

    def test_api_logout(self):
        """when attribute error is raised, this means that cherrypy
        session is used to authenticate the http request."""
        self.assertRaises(AttributeError, self.http.api, 'logout')

    def test_api_downloadpls(self):
        """when attribute error is raised, this means that cherrypy
        session is used to authenticate the http request."""
        self.assertRaises(AttributeError, self.http.api, 'downloadpls')

    def test_api_downloadm3u(self):
        """when attribute error is raised, this means that cherrypy
        session is used to authenticate the http request."""
        self.assertRaises(AttributeError, self.http.api, 'downloadm3u')

    def test_api_downloadpls_call(self):
        MockPlaylistDB.getName.return_value = 'some_playlist_name'
        MockPlaylistDB.createPLS.return_value = 'some_pls_string'

        self.call_api('downloadpls', plid=13, hostaddr='host')

        MockPlaylistDB.createPLS.assert_called_with(userid=ANY, plid=13, addrstr='host')


    def test_api_downloadm3u_call(self):
        MockPlaylistDB.getName.return_value = 'some_playlist_name'
        MockPlaylistDB.createM3U.return_value = 'some_m3u_string'

        self.call_api('downloadm3u', plid=13, hostaddr='host')

        MockPlaylistDB.createM3U.assert_called_with(userid=ANY, plid=13, addrstr='host')


    def test_api_export_playlists(self):
        from collections import defaultdict
        MockPlaylistDB.showPlaylists.return_value = [defaultdict(MagicMock)]
        MockPlaylistDB.getName.return_value = 'some_playlist_name'
        MockPlaylistDB.createM3U.return_value = 'some_m3u_string'

        with patch('cherrypy.session', {'userid': 1}, create=True):
            bytestr = self.http.export_playlists(hostaddr='hostaddr', format='m3u')

        import io, zipfile
        zip = zipfile.ZipFile(io.BytesIO(bytestr), 'r')
        try:
            badfile = zip.testzip()
            assert badfile is None
            filenames = zip.namelist()
            assert ['some_playlist_name.m3u'] == filenames, filenames
            content = zip.read('some_playlist_name.m3u')
            assert 'some_m3u_string'.encode('ASCII') == content, content
        finally:
            zip.close()

    def test_api_getsonginfo(self):
        """when attribute error is raised, this means that cherrypy
        session is used to authenticate the http request."""
        self.assertRaises(AttributeError, self.http.api, 'getsonginfo')

    def test_api_getencoders(self):
        """when attribute error is raised, this means that cherrypy
        session is used to authenticate the http request."""
        self.assertRaises(AttributeError, self.http.api, 'getencoders')

    def test_api_getdecoders(self):
        """when attribute error is raised, this means that cherrypy
        session is used to authenticate the http request."""
        self.assertRaises(AttributeError, self.http.api, 'getdecoders')

    def test_api_transcodingenabled(self):
        """when attribute error is raised, this means that cherrypy
        session is used to authenticate the http request."""
        self.assertRaises(AttributeError, self.http.api, 'transcodingenabled')

    def test_api_updatedb(self):
        """when attribute error is raised, this means that cherrypy
        session is used to authenticate the http request."""
        self.assertRaises(AttributeError, self.http.api, 'updatedb')

    def test_api_compactlistdir(self):
        """when attribute error is raised, this means that cherrypy
        session is used to authenticate the http request."""
        self.assertRaises(AttributeError, self.http.api, 'compactlistdir')

    def test_api_getconfiguration(self):
        """when attribute error is raised, this means that cherrypy
        session is used to authenticate the http request."""
        self.assertRaises(AttributeError, self.http.api, 'getconfiguration')

    def test_api_getuseroptions(self):
        """when attribute error is raised, this means that cherrypy
        session is used to authenticate the http request."""
        self.assertRaises(AttributeError, self.http.api, 'getuseroptions')

    def test_api_userdelete_needs_auth(self):
        """when attribute error is raised, this means that cherrypy
        session is used to authenticate the http request."""
        self.assertRaises(AttributeError, self.http.api, 'userdelete')

    def test_api_userdelete_call(self):
        session = {'userid': 1, 'admin': True}
        userdb = Mock()
        with patch('cherrypy.session', session, create=True):
            with patch('cherrymusicserver.service.get') as service:
                service.return_value = userdb
                self.call_api('userdelete', userid=13)
        userdb.deleteUser.assert_called_with(13)

    def test_api_heartbeat(self):
        """when attribute error is raised, this means that cherrypy
        session is used to authenticate the http request."""
        self.assertRaises(AttributeError, self.http.api, 'heartbeat')

    def test_api_fetchalbumart(self):
        """when attribute error is raised, this means that cherrypy
        session is used to authenticate the http request."""
        if not self.http.handlers['fetchalbumart'].noauth:
            self.assertRaises(AttributeError, self.http.api, 'fetchalbumart')

    def test_api_setuseroption(self):
        """when attribute error is raised, this means that cherrypy
        session is used to authenticate the http request."""
        self.assertRaises(AttributeError, self.http.api, 'setuseroption')

    def test_api_changeplaylist(self):
        """when attribute error is raised, this means that cherrypy
        session is used to authenticate the http request."""
        if not self.http.handlers['fetchalbumart'].noauth:
            self.assertRaises(AttributeError, self.http.api, 'fetchalbumart')

    def test_api_listdir(self):
        """when attribute error is raised, this means that cherrypy
        session is used to authenticate the http request."""
        self.assertRaises(AttributeError, self.http.api, 'changeplaylist')

    def test_api_userchangepassword(self):
        """when attribute error is raised, this means that cherrypy
        session is used to authenticate the http request."""
        self.assertRaises(AttributeError, self.http.api, 'userchangepassword')

    def test_trans(self):
        import os
        config = {'media.basedir': 'BASEDIR', 'media.transcode': True}
        with mock_auth():
            with patch('cherrymusicserver.httphandler.cherry.config', config):
                with patch('cherrymusicserver.httphandler.cherrypy'):
                    with patch('cherrymusicserver.httphandler.audiotranscode.AudioTranscode') as transcoder:
                        transcoder.return_value = transcoder
                        expectPath = os.path.join(config['media.basedir'], 'path')

                        httphandler.HTTPHandler(config).trans('newformat', 'path', bitrate=111)

                        transcoder.transcodeStream.assert_called_with(expectPath, 'newformat', bitrate=111, starttime=0)


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_pathprovider
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# CherryMusic - a standalone music server
# Copyright (c) 2012 - 2014 Tom Wallroth & Tilman Boerner
#
# Project page:
#   http://fomori.org/cherrymusic/
# Sources on github:
#   http://github.com/devsnd/cherrymusic/
#
# CherryMusic is based on
#   jPlayer (GPL/MIT license) http://www.jplayer.org/
#   CherryPy (BSD license) http://www.cherrypy.org/
#
# licensed under GNU GPL version 3 (or later)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
#

import nose

#from mock import *
from nose.tools import *

import os.path

from cherrymusicserver import log
log.setTest()

from cherrymusicserver import pathprovider

def test_absOrConfigPath():
    relpath = 'relpath'
    abspath = os.path.abspath(relpath)
    ok_(pathprovider.absOrConfigPath(relpath).startswith(pathprovider.getConfigPath()))
    eq_(abspath, pathprovider.absOrConfigPath(abspath))


if __name__ == '__main__':
    nose.runmodule()

########NEW FILE########
__FILENAME__ = test_playlistdb
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# CherryMusic - a standalone music server
# Copyright (c) 2012 - 2014 Tom Wallroth & Tilman Boerner
#
# Project page:
#   http://fomori.org/cherrymusic/
# Sources on github:
#   http://github.com/devsnd/cherrymusic/
#
# CherryMusic is based on
#   jPlayer (GPL/MIT license) http://www.jplayer.org/
#   CherryPy (BSD license) http://www.cherrypy.org/
#
# licensed under GNU GPL version 3 (or later)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
#

import nose

from mock import *
from nose.tools import *

from cherrymusicserver import log
log.setTest()

from cherrymusicserver import database
from cherrymusicserver import service

from cherrymusicserver.playlistdb import *


_DEFAULT_USERID = 1


def setup():
    service.provide('dbconnector', database.sql.TmpConnector)
    database.ensure_current_version(DBNAME)


def teardown():
    service.provide('dbconnector', None)


def create_playlist(name, titles):
    pldb = PlaylistDB()
    public = True
    userid = _DEFAULT_USERID
    songs = [dict(title=t, url="url(" + t + ")") for t in titles]
    pldb.savePlaylist(userid, public, songs, name, overwrite=True)
    playlist = get_playlist(name)
    assert playlist
    return playlist

def test_delete_playlist():
    pldb = PlaylistDB()
    create_playlist('deleteme', ['delete', 'me'])
    pl = get_playlist('deleteme')
    assert pldb.deletePlaylist(pl['plid'], None, override_owner=True) == 'success'
    assert pldb.deletePlaylist(pl['plid'], None, override_owner=True) == "This playlist doesn't exist! Nothing deleted!"

def get_playlist(name):
    pldb = PlaylistDB()
    for p in pldb.showPlaylists(_DEFAULT_USERID):
        if p['title'] == name:
            return p

def test_set_public():
    pl = create_playlist('some_title', list('abc'))
    assert get_playlist('some_title')['public']

    PlaylistDB().setPublic(_DEFAULT_USERID, pl['plid'], False)

    assert not get_playlist('some_title')['public']


if __name__ == '__main__':
    nose.runmodule()

########NEW FILE########
__FILENAME__ = test_service
#!/usr/bin/env python3
#
# CherryMusic - a standalone music server
# Copyright (c) 2012 - 2014 Tom Wallroth & Tilman Boerner
#
# Project page:
#   http://fomori.org/cherrymusic/
# Sources on github:
#   http://github.com/devsnd/cherrymusic/
#
# CherryMusic is based on
#   jPlayer (GPL/MIT license) http://www.jplayer.org/
#   CherryPy (BSD license) http://www.cherrypy.org/
#
# licensed under GNU GPL version 3 (or later)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
#

import unittest

from cherrymusicserver import service


class TestService(unittest.TestCase):

    def test_mutual_dependency(self):

        @service.user(myfoo='fooservice')
        class Reflecto(object):
            def __init__(self):
                service.provide('fooservice', self.__class__)
                assert self.myfoo

        self.assertRaises(service.MutualDependencyBreak, Reflecto)

########NEW FILE########
__FILENAME__ = test_sqlitecache
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# CherryMusic - a standalone music server
# Copyright (c) 2012 - 2014 Tom Wallroth & Tilman Boerner
#
# Project page:
#   http://fomori.org/cherrymusic/
# Sources on github:
#   http://github.com/devsnd/cherrymusic/
#
# CherryMusic is based on
#   jPlayer (GPL/MIT license) http://www.jplayer.org/
#   CherryPy (BSD license) http://www.cherrypy.org/
#
# licensed under GNU GPL version 3 (or later)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
#

#python 2.6+ backward compability
from __future__ import unicode_literals

import nose
import unittest
from nose.tools import *

import os
import re
import shutil
import sys
import tempfile

import cherrymusicserver as cherry
from cherrymusicserver import configuration
from cherrymusicserver import database
from cherrymusicserver import log
from cherrymusicserver import sqlitecache
from cherrymusicserver import service

sqlitecache.debug = True

from cherrymusicserver.database.sql import MemConnector

log.setTest()


class TestFile(object):

    def __init__(self, fullpath, parent=None, isdir=None, uid=None):
        self.uid = uid if uid else -1
        self.fullpath = fullpath if not parent else os.path.join(parent.fullpath, fullpath)
        self.parent = parent
        self.isdir = fullpath.endswith(os.path.sep) if (isdir is None) else isdir
        if self.isdir:
            self.fullpath = fullpath[:-1]
            self.name = os.path.basename(self.fullpath)
            self.ext = ''
        else:
            self.name, self.ext = os.path.splitext(os.path.basename(fullpath))

    def __repr__(self):
        return '[%d] %s%s (-> %d)' % (self.uid,
                                  self.name + self.ext,
                                  '*' if self.isdir else '',
                                  - 1 if self.parent is None
                                    else self.parent.uid)

    @property
    def exists(self):
        return os.path.exists(self.fullpath)


    @classmethod
    def enumerate_files_in(cls, somewhere, sort):
        raise NotImplementedError("%s.%s.enumerate_files_in(cls, paths, sort)"
                                  % (__name__, cls.__name__))

tmpdir = None
def setUpModule():
    global tmpdir
    tmpdir = tempfile.mkdtemp(suffix='-test_sqlitecache', prefix='tmp-cherrymusic-')
if sys.version_info < (2, 7):  # hack to support python 2.6 which doesn't setUpModule()
    setUpModule()

def tearDownModule():
    shutil.rmtree(tmpdir, ignore_errors=False, onerror=None)

def getAbsPath(*relpath):
    'returns the absolute path for a path relative to the global testdir'
    return os.path.join(tmpdir, *relpath)


def setupTestfile(testfile):
    if testfile.isdir:
        setupDir(testfile.fullpath)
        # os.makedirs(testfile.fullpath, exist_ok=True)
    else:
        if not os.path.exists(testfile.fullpath):
            open(testfile.fullpath, 'w').close()
    assert testfile.exists


def setupTestfiles(testdir, testfiles):
    testdir = os.path.join(tmpdir, testdir, '')
    setupTestfile(TestFile(testdir))
    for filename in testfiles:
        filename = os.path.join(testdir, filename)
        setupTestfile(TestFile(filename))


def setupDir(testdir):
    import errno
    try:
        os.makedirs(testdir)  #, exist_ok=True) # py2 compatibility
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(testdir):
            pass
        else:
            raise

def removeTestfile(testfile):
    if testfile.isdir:
        os.rmdir(testfile.fullpath)
    else:
        os.remove(testfile.fullpath)


def removeTestfiles(testdir, testfiles):
    testdir = os.path.join(tmpdir, testdir)
    shutil.rmtree(testdir, ignore_errors=True, onerror=None)


class AddFilesToDatabaseTest(unittest.TestCase):

    testdirname = 'empty'

    def setupConfig(self):
        cherry.config = configuration.from_defaults()
        cherry.config = cherry.config.replace({'media.basedir': self.testdir})


    def setUp(self):
        self.testdir = getAbsPath(self.testdirname)
        setupTestfiles(self.testdir, ())
        self.setupConfig()
        service.provide('dbconnector', MemConnector)
        database.ensure_current_version(sqlitecache.DBNAME, autoconsent=True)
        self.Cache = sqlitecache.SQLiteCache()
        self.Cache.full_update()


    def tearDown(self):
        removeTestfiles(self.testdir, ())
        self.Cache.conn.close()


    def test_add_to_file_table(self):
        parent = TestFile('test/', parent=None, isdir=True)
        parent.uid = 42
        file = TestFile('test/filename.extension', parent=parent, isdir=False)

        # RUN
        self.Cache.add_to_file_table(parent)
        self.Cache.add_to_file_table(file)

        self.assertTrue(file.uid >= 0, "file must have valid rowid")

        colnames = ('parent', 'filename', 'filetype', 'isdir')
        res = self.Cache.conn.execute('SELECT %s from files WHERE rowid=?'%(', '.join(colnames),), (file.uid,)).fetchall()

        self.assertTrue(1 == len(res), "expect exactly one file with that uid")
        self.assertTrue(len(colnames) == len(res[0]), "expect exactly %s colums stored per file, got %s" % (len(colnames),len(res[0])))

        resdict = {}
        i=0
        for k in colnames:
            resdict[k] = res[0][i]
            i+=1
        self.assertTrue(parent.uid == resdict['parent'], "correct parent id must be saved")
        self.assertTrue('filename' == resdict['filename'], "filename must be saved without extension")
        self.assertTrue('.extension' == resdict['filetype'], "extension must be saved with leading .")
        self.assertFalse(resdict['isdir'], 'isdir must not be set in files table')

        isdir = self.Cache.conn.execute('SELECT isdir from files WHERE rowid=?', (parent.uid,)).fetchone()[0]
        self.assertTrue(isdir, "isdir must be saved correctly")


    def test_add_to_dictionary_table(self):
        """searchable parts of a filename must be added to the dictionary as
        words, and a list of unique word ids returned"""

        filename = 'abc ÖÄUßé.wurst_-_blablabla.nochmal.wurst'
        words = sqlitecache.SQLiteCache.searchterms(filename)

        ids = self.Cache.add_to_dictionary_table(filename)

        idset = set(ids)
        self.assertTrue(len(ids) == len(idset), "there must be no duplicate ids")
        for word in words:
            cursor = self.Cache.conn.execute('SELECT rowid FROM dictionary WHERE word=?', (word,))
            res = cursor.fetchall()
            self.assertTrue(len(res) == 1, "there must be exactly one matching row per word")
            self.assertTrue(res[0][0] in idset, "the wordid must be returned by the function")
            idset.remove(res[0][0])   # make sure no other tested word can use that id to pass
        self.assertTrue(len(idset) == 0, "there must not be more ids than unique words")


    def test_add_to_search_table(self):
        fileid = 99
        wordids = (13, 42)

        self.Cache.add_to_search_table(fileid, wordids)

        for wid in wordids:
            found = self.Cache.conn.execute('SELECT frowid FROM search WHERE drowid=?', (wid,)).fetchone()[0]
            self.assertTrue(fileid == found, 'fileid must be associated with wordid')


    def test_register_file_with_db(self):
        testnames = (
                     'SUCHMICH',
                     'findmich suchmich',
                     'suchMICH blablub',
                     'wurst-mit-Suchmich.doch-schinken',
                     )

        for filename in testnames:
            self.Cache.register_file_with_db(TestFile(filename))

        found = self.Cache.searchfor('SUCHMICH', 100)
        #map musicentries to string
        found = list(map(lambda x : x.path, found))
        for filename in testnames:
            self.assertTrue(filename in found, "all added files must be findable by cache search")




class FileTest(unittest.TestCase):

    testdir = 'filetest'

    testfiles = (
                 os.path.join('rootlevelfile'),
                 os.path.join('firstdir', ''),
                 os.path.join('firstdir', 'firstlevelfile'),
                 os.path.join('firstdir', 'seconddir', ''),
                 os.path.join('firstdir', 'seconddir', 'secondlevelfile'),
                 os.path.join('nonASCIItest', ''),
                 os.path.join('nonASCIItest', 'öäßÖÄÉ'),
                 )


    def setUp(self):
        setupTestfiles(self.testdir, self.testfiles)


    def tearDown(self):
        removeTestfiles(self.testdir, self.testfiles)

    def assertFilesEqual(self, expected, actual):
        self.assertTrue(actual.exists)
        self.assertTrue(expected.fullpath == actual.fullpath, "equal fullpath %s vs %s" % (expected.fullpath, actual.fullpath))
        self.assertTrue(expected.name == actual.name, "equal name %s vs %s " % (expected.name, actual.name))
        self.assertTrue(expected.ext == actual.ext, 'equal extension %s vs %s' % (expected.ext, actual.ext))
        self.assertTrue(expected.isdir == actual.isdir, 'equal dir flag %s vs %s (%s)' % (expected.isdir, actual.isdir, expected.fullpath))


    def testFileClass(self):
        for filename in self.testfiles:
            filename = os.path.join(tmpdir, self.testdir, filename)
            expected = TestFile(filename)
            if filename.endswith(os.path.sep):
                filename = filename[:-1]
            actual = sqlitecache.File(filename)
            self.assertFilesEqual(expected, actual)


class RemoveFilesFromDatabaseTest(unittest.TestCase):

    testdirname = 'deltest'

    testfiles = (
                 os.path.join('root_file'),
                 os.path.join('root_dir', ''),
                 os.path.join('root_dir', 'first_file'),
                 os.path.join('root_dir', 'first_dir', ''),
                 os.path.join('root_dir', 'first_dir', 'first_file'),
                 os.path.join('commonName', ''),
                 os.path.join('commonName', 'commonname_uniquename'),
                 )

    fileobjects = {}


    def setupConfig(self):
        cherry.config = configuration.from_defaults()
        cherry.config = cherry.config.replace({
            'media.basedir': self.testdir,
        })


    def setupFileObjects(self):
        testpath = os.path.abspath(self.testdir)
        root = sqlitecache.File(testpath)
        self.fileobjects[''] = root
        for path in self.testfiles:
            self.addPathToFileObjects(path, root)


    def addPathToFileObjects(self, path, root):
        path = path.rstrip(os.path.sep)
        ref, base = os.path.split(path)
        if ref:
            if not ref in self.fileobjects:
                self.addPathToFileObjects(ref, root)
            parent = self.fileobjects[ref]
        else:
            parent = root
        fob = sqlitecache.File(base, parent=parent)
        self.id_fileobj(fob)
        self.fileobjects[path] = fob


    def setUp(self):
        self.testdir = getAbsPath(self.testdirname)
        setupTestfiles(self.testdir, self.testfiles)
        self.setupConfig()
        service.provide('dbconnector', MemConnector)
        database.ensure_current_version(sqlitecache.DBNAME, autoconsent=True)
        self.Cache = sqlitecache.SQLiteCache()
        self.Cache.full_update()
        self.setupFileObjects()
        assert self.fileobjects[''].fullpath == os.path.abspath(self.testdir), \
                'precondition: test rootdir has correct fullpath'

    def tearDown(self):
        removeTestfiles(self.testdir, self.testfiles)
        self.Cache.conn.close()


    def lookup_filename(self, filename, parentid):
        return self.Cache.conn.execute(
                        'SELECT rowid FROM files WHERE parent=? AND filename=?',
                        (parentid, filename,))\
                        .fetchone()

    def fileid_in_db(self, fileid):
        return self.Cache.conn.execute('SELECT COUNT(*) FROM files'\
                                       ' WHERE rowid=?', (fileid,))\
                                       .fetchone()[0]


    def id_fileobj(self, fileobj):
        '''fetches the db id for fileobj and saves it in fileobj.uid'''
        if fileobj.parent is None:
            pid = -1
        else:
            if fileobj.parent.uid == -1:
                self.id_fileobj(fileobj.parent)
            pid = fileobj.parent.uid
        res = self.lookup_filename(fileobj.basename, pid)
        if res is None:
            if fileobj != fileobj.root:     # testdir itself is not in db
                log.w('fileobj not in database: %s', fileobj)
            return
        uid = res[0]
        fileobj.uid = uid


    def db_count(self, tablename):
        query = 'SELECT COUNT(*) FROM ' + tablename
        return self.Cache.conn.execute(query).fetchone()[0]


    def testMissingFileIsRemovedFromDb(self):
        fob = self.fileobjects['root_file']
        removeTestfile(fob)
        assert not fob.exists
        assert self.fileid_in_db(fob.uid)

        self.Cache.full_update()

        self.assertFalse(self.fileid_in_db(fob.uid),
                    'file entry must be removed from db')


    def testFilesWithSameNameAsMissingAreNotRemoved(self):
        fob = self.fileobjects['root_dir/first_dir/first_file']
        removeTestfile(fob)
        beforecount = self.db_count('files')

        self.Cache.full_update()

        self.assertEqual(beforecount - 1, self.db_count('files'),
                         'exactly one file entry must be removed')


    def get_fileobjects_for(self, dirname):
        return [self.fileobjects[key] for key
                in sorted(self.fileobjects.keys())
                if key.startswith(dirname)]


    def testMissingDirIsRemovedRecursively(self):
        removelist = self.get_fileobjects_for('root_dir')
        for fob in reversed(removelist):
            removeTestfile(fob)

        self.Cache.full_update()

        for fob in removelist:
            self.assertFalse(self.fileid_in_db(fob.uid),
                        'all children entries from removed dir must be removed')


    def testRemoveFileAlsoRemovesSearchIndexes(self):
        fob = self.fileobjects['root_file']
        removeTestfile(fob)

        self.Cache.full_update()

        searchids = self.Cache.conn.execute('SELECT count(*) FROM search'
                                            ' WHERE frowid=?', (fob.uid,)) \
                                            .fetchone()[0]
        self.assertEqual(0, searchids,
                         'all search indexes referencing removed file must also be removed')


    def testRemoveAllIndexesForWordRemovesWord(self):
        fob = self.fileobjects[os.path.join('commonName', 'commonname_uniquename')]
        removeTestfile(fob)

        self.Cache.full_update()

        unique = self.Cache.conn.execute('SELECT COUNT(*) FROM dictionary'
                                         ' WHERE word=?', ('uniquename',)) \
                                         .fetchone()[0]
        common = self.Cache.conn.execute('SELECT COUNT(*) FROM dictionary'
                                         ' WHERE word=?', ('commonname',)) \
                                         .fetchone()[0]

        self.assertEqual(0, unique,
                         'orphaned words must be removed')
        self.assertEqual(1, common,
                         'words still referenced elsewhere must not be removed')

    def testRollbackOnException(self):

        class BoobytrappedConnector(MemConnector):
            exceptcount = 0

            def __init__(self):
                super(self.__class__, self).__init__()
                self.Connection = type(
                    str('%s.BoobytrappedConnection' % (self.__class__.__module__)),
                    (self.Connection,),
                    {'execute': self.__execute})

            def __execute(connector, stmt, *parameters):
                '''triggers an Exception when the 'undeletable' item should be
                removed. relies on way too much knowledge of Cache internals. :(
                '''
                if stmt.lower().startswith('delete from files') \
                  and parameters[0][0] == undeletable.uid:
                    connector.exceptcount += 1
                    raise Exception("boom goes the dynamite")
                return super(
                    connector.Connection,
                    connector.connection(sqlitecache.DBNAME)).execute(stmt, *parameters)

        # SPECIAL SETUP
        connector = BoobytrappedConnector()
        service.provide('dbconnector', connector)
        database.ensure_current_version(sqlitecache.DBNAME, autoconsent=True)
        self.Cache = sqlitecache.SQLiteCache()
        self.Cache.full_update()

        removelist = self.get_fileobjects_for('root_dir')
        for fob in removelist:
            self.id_fileobj(fob)
        for fob in reversed(removelist):
            removeTestfile(fob)

        undeletable = self.fileobjects[os.path.join('root_dir',
                                                    'first_dir',
                                                    'first_file')]
        deletable = [self.fileobjects[os.path.join('root_dir',
                                                   'first_file')]]



        # RUN
        self.Cache.full_update()
        removed = [f for f in removelist if not self.fileid_in_db(f.uid)]


        # ASSERT
        self.assertTrue(1 <= connector.exceptcount,
                         'test must have raised at least one exception')

        self.assertEqual(deletable, removed,
        # self.assertListEqual(deletable, removed,
                        'complete rollback must restore all deleted entries.')


class RandomEntriesTest(unittest.TestCase):

    testdirname = 'randomFileEntries'

    def setUp(self):
        self.testdir = getAbsPath(self.testdirname)
        setupTestfiles(self.testdir, ())
        cherry.config = cherry.config.replace({'media.basedir': self.testdir})
        service.provide('dbconnector', MemConnector)
        database.ensure_current_version(sqlitecache.DBNAME, autoconsent=True)
        self.Cache = sqlitecache.SQLiteCache()
        return self

    def register_files(self, *paths):
        ''' paths = ('dir/file', 'dir/subdir/') will register
                - directories:
                    - dir/
                    - dir/subdir/
                - files:
                    - /dir/file '''
        files = {}
        for path in paths:
            previous = ''
            for element in re.findall('\w+/?', path):
                fullpath = previous + element
                if fullpath not in files:
                    parent = files.get(previous, None)
                    fileobj = TestFile(element, parent=parent, isdir=element.endswith('/'))
                    self.Cache.register_file_with_db(fileobj)
                    files[fullpath] = fileobj
                previous = fullpath
        return files

    def test_should_return_empty_sequence_when_no_files(self):
        entries = self.Cache.randomFileEntries(10)

        eq_(0, len(entries), entries)

    def test_should_return_empty_sequence_when_zero_count(self):
        entries = self.Cache.randomFileEntries(0)

        eq_(0, len(entries), entries)

    def test_should_return_all_entries_when_fewer_than_count(self):
        self.register_files('a', 'b')

        entries = self.Cache.randomFileEntries(10)

        eq_(2, len(entries), entries)

    def test_should_not_return_deleted_entries(self):
        files = self.register_files('a', 'b', 'c')
        self.Cache.remove_file(files['b'])

        entries = self.Cache.randomFileEntries(10)

        eq_(2, len(entries), entries)

    def test_should_not_return_more_than_count_entries(self):
        self.register_files('a', 'b', 'c')

        entries = self.Cache.randomFileEntries(2)

        ok_(2 >= len(entries), entries)

    def test_should_not_return_dir_entries(self):
        self.register_files('a_dir/a_subdir/')

        entries = self.Cache.randomFileEntries(10)

        eq_(0, len(entries), entries)

    def test_can_handle_entries_in_subdirs(self):
        self.register_files('dir/subdir/file')

        entries = self.Cache.randomFileEntries(10)

        eq_(1, len(entries), entries)
        eq_('dir/subdir/file', entries[0].path, entries[0])


class SymlinkTest(unittest.TestCase):

    testdirname = 'linktest'

    testfiles = (
                 os.path.join('root_file'),
                 os.path.join('root_dir', ''),
                 )


    def setUp(self):
        self.testdir = getAbsPath(self.testdirname)
        setupTestfiles(self.testdir, self.testfiles)
        cherry.config = cherry.config.replace({'media.basedir': self.testdir})
        service.provide('dbconnector', MemConnector)
        database.ensure_current_version(sqlitecache.DBNAME, autoconsent=True)
        self.Cache = sqlitecache.SQLiteCache()

    def tearDown(self):
        removeTestfiles(self.testdir, self.testfiles)
        self.Cache.conn.close()


    def enumeratedTestdir(self):
        return [os.path.join(self.testdir, i.infs.relpath) for
                i in self.Cache.enumerate_fs_with_db(self.testdir)]


    def testRootLinkOk(self):
        link = os.path.join(self.testdir, 'link')
        target = os.path.join(self.testdir, 'root_file')
        os.symlink(target, link)

        try:
            self.assertTrue(link in self.enumeratedTestdir(),
                            'root level links must be returned')
        finally:
            os.remove(link)


    def testSkipSymlinksBelowBasedirRoot(self):
        link = os.path.join(self.testdir, 'root_dir', 'link')
        target = os.path.join(self.testdir, 'root_file')
        os.symlink(target, link)

        try:
            self.assertFalse(link in self.enumeratedTestdir(),
                            'deeply nested link must not be returned')
        finally:
            os.remove(link)


    def testNoCyclicalSymlinks(self):
        target = os.path.abspath(self.testdir)
        link = os.path.join(self.testdir, 'link')
        os.symlink(target, link)

        try:
            self.assertFalse(link in self.enumeratedTestdir(),
                            'cyclic link must not be returned')
        finally:
            os.remove(link)


class UpdateTest(unittest.TestCase):

    testdirname = 'updatetest'

    testfiles = (
                 os.path.join('root_file'),
                 os.path.join('root_dir', ''),
                 os.path.join('root_dir', 'first_file'),
                 )


    def setupConfig(self):
        cherry.config = configuration.from_defaults()
        cherry.config = cherry.config.replace({
            'media.basedir': self.testdir,
        })

    def setupCache(self):
        service.provide('dbconnector', MemConnector)
        database.ensure_current_version(sqlitecache.DBNAME, autoconsent=True)
        self.Cache = sqlitecache.SQLiteCache()
        self.Cache.full_update()

    def clearCache(self):
        self.Cache.conn.execute('delete from files')
        self.Cache.conn.execute('delete from dictionary')
        self.Cache.conn.execute('delete from search')

    def setUp(self):
        self.testdir = getAbsPath(self.testdirname)
        setupTestfiles(self.testdir, self.testfiles)
        self.setupConfig()
        self.setupCache()

    def tearDown(self):
        removeTestfiles(self.testdir, self.testfiles)
        self.Cache.conn.close()


    def test_enumerate_add(self):
        '''items not in db must be enumerated'''
        self.clearCache()
        lister = self.Cache.enumerate_fs_with_db(self.testdir)
        expected_files = [f.rstrip(os.path.sep) for f in self.testfiles]
        lister.send(None)  # skip first item
        for item in lister:
            self.assertEqual(None, item.indb, 'database part must be empty, found: %s' % item.indb)
            self.assertTrue(item.infs.relpath in expected_files, '%s %s' % (item.infs.relpath, expected_files))
            expected_files.remove(item.infs.relpath)
        self.assertEqual(0, len(expected_files))


    def test_enumerate_delete(self):
        '''items not in fs must be enumerated'''
        removeTestfiles(self.testdir, self.testfiles)
        lister = self.Cache.enumerate_fs_with_db(self.testdir)
        expected_files = [f.rstrip(os.path.sep) for f in self.testfiles]
        lister.send(None)  # skip first item
        for item in lister:
            self.assertEqual(None, item.infs, 'filesystem part must be empty, found: %s' % item.indb)
            self.assertTrue(item.indb.relpath in expected_files, '%s %s' % (item.indb.relpath, expected_files))
            expected_files.remove(item.indb.relpath)
        self.assertEqual(0, len(expected_files))


    def test_enumerate_same(self):
        '''unchanged fs must have equal db'''
        lister = self.Cache.enumerate_fs_with_db(self.testdir)
        expected_files = [f.rstrip(os.path.sep) for f in self.testfiles]
        lister.send(None)  # skip first item
        for item in lister:
            self.assertEqual(item.infs.fullpath, item.indb.fullpath)
            self.assertEqual(item.infs.isdir, item.indb.isdir)
            self.assertTrue(item.indb.relpath in expected_files, '%s %s' % (item.indb.relpath, expected_files))
            expected_files.remove(item.indb.relpath)
        self.assertEqual(0, len(expected_files))

    def test_new_file_in_known_dir(self):
        newfile = os.path.join('root_dir', 'second_file')
        setupTestfiles(self.testdir, (newfile,))

        self.Cache.full_update()

        self.assertNotEqual(None, self.Cache.db_find_file_by_path(getAbsPath(self.testdir, newfile)),
                            'file must have been added correctly to the database')

    def test_partial_update(self):

        newfiles = (
                      os.path.join('root_dir', 'sub_dir', ''),
                      os.path.join('root_dir', 'sub_dir', 'a_file'),
                      os.path.join('root_dir', 'sub_dir', 'another_file'),
                      )
        setupTestfiles(self.testdir, newfiles)
        path_to = lambda x: getAbsPath(self.testdir, x)

        msg = 'after updating newpath, all paths in newpath must be in database'
        self.Cache.partial_update(path_to(newfiles[0]))
        self.assertNotEqual(None, self.Cache.db_find_file_by_path(path_to(newfiles[0])), msg)
        self.assertNotEqual(None, self.Cache.db_find_file_by_path(path_to(newfiles[1])), msg)
        self.assertNotEqual(None, self.Cache.db_find_file_by_path(path_to(newfiles[2])), msg)

        msg = 'after updating samepath, all paths in samepath must be in database'
        self.Cache.partial_update(path_to(newfiles[0]))
        self.assertNotEqual(None, self.Cache.db_find_file_by_path(path_to(newfiles[0])), msg)
        self.assertNotEqual(None, self.Cache.db_find_file_by_path(path_to(newfiles[1])), msg)
        self.assertNotEqual(None, self.Cache.db_find_file_by_path(path_to(newfiles[2])), msg)

        removeTestfiles(self.testdir, newfiles)

        msg = 'after updating removedpath, all paths in reomevpath must be gone from database'
        self.Cache.partial_update(path_to(newfiles[0]))
        self.assertEqual(None, self.Cache.db_find_file_by_path(path_to(newfiles[0])), msg)
        self.assertEqual(None, self.Cache.db_find_file_by_path(path_to(newfiles[1])), msg)
        self.assertEqual(None, self.Cache.db_find_file_by_path(path_to(newfiles[2])), msg)

        setupTestfiles(self.testdir, newfiles)

        msg = 'after updating newpath/subpath, only newpath and subpath must be in database, not othersubpath'
        self.Cache.partial_update(path_to(newfiles[1]))
        self.assertNotEqual(None, self.Cache.db_find_file_by_path(path_to(newfiles[0])), msg)
        self.assertNotEqual(None, self.Cache.db_find_file_by_path(path_to(newfiles[1])), msg)
        self.assertEqual(None, self.Cache.db_find_file_by_path(path_to(newfiles[2])), msg)

        removeTestfiles(self.testdir, newfiles)

        msg = 'after updating removedpath/subpath, subpath most be gone from database, removedpath must still be there'
        self.Cache.partial_update(path_to(newfiles[1]))
        self.assertNotEqual(None, self.Cache.db_find_file_by_path(path_to(newfiles[0])), msg)
        self.assertEqual(None, self.Cache.db_find_file_by_path(path_to(newfiles[1])), msg)
        self.assertEqual(None, self.Cache.db_find_file_by_path(path_to(newfiles[2])), msg)

from cherrymusicserver.test.helpers import cherrytest, tempdir

def setup_cache(testfiles=()):
    """ Sets up a SQLiteCache instance bound to current `media.basedir`.

        The basedir is assumed to exist (as it must) and can be initialized
        with directories and (empty) files.

        :param list testfiles: Strings of filenames. Names ending in '/' are directories.
    """
    database.resetdb(sqlitecache.DBNAME)
    database.ensure_current_version(sqlitecache.DBNAME, autoconsent=True)
    cache = sqlitecache.SQLiteCache()

    basedir = cherry.config['media.basedir']
    assert not os.listdir(basedir)

    for filename in testfiles:
        fullpath = os.path.join(basedir, filename)
        setupTestfile(TestFile(fullpath))

    cache.full_update()
    return cache


def cachetest(func):
    """ Function decorator that provides a basic CherryMusic context, complete
        with a temporary `media.basedir`.
    """
    testname = '{0}.{1}'.format(func.__module__ , func.__name__)
    def wrapper(*args, **kwargs):
        with tempdir(testname) as basedir:
            testfunc = cherrytest({'media.basedir': basedir})(func)
            testfunc(*args, **kwargs)
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper

@cachetest
def test_listdir():
    basedir_contents = ['some_file']
    cache = setup_cache(basedir_contents)

    assert basedir_contents == cache.listdir('')
    assert basedir_contents == cache.listdir('.')
    assert basedir_contents == cache.listdir('./.')

    assert [] == cache.listdir('/.')
    assert [] == cache.listdir('..')
    assert [] == cache.listdir('./..')

if __name__ == "__main__":
    nose.runmodule()

########NEW FILE########
__FILENAME__ = test_userdb
#!/usr/bin/env python3
#
# CherryMusic - a standalone music server
# Copyright (c) 2012 - 2014 Tom Wallroth & Tilman Boerner
#
# Project page:
#   http://fomori.org/cherrymusic/
# Sources on github:
#   http://github.com/devsnd/cherrymusic/
#
# CherryMusic is based on
#   jPlayer (GPL/MIT license) http://www.jplayer.org/
#   CherryPy (BSD license) http://www.cherrypy.org/
#
# licensed under GNU GPL version 3 (or later)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
#
import unittest

from cherrymusicserver import log
log.setTest()

from cherrymusicserver import database
from cherrymusicserver import service
from cherrymusicserver import userdb
from cherrymusicserver.database.sql import MemConnector


class TestAuthenticate(unittest.TestCase):
    '''test authentication functions of userdb'''

    def setUp(self):
        service.provide('dbconnector', MemConnector)
        database.ensure_current_version(userdb.DBNAME)
        self.users = userdb.UserDB()
        self.users.addUser('user', 'password', False)

        #unittest2 compability
        if not hasattr(self,'assertTupleEqual'):
            def assertTupEq(t1,t2,msg):
                if not all(i==j for i,j in zip(t1,t2)):
                    raise AssertionError(msg)
            self.assertTupleEqual = assertTupEq
        #end of workaround


    def tearDown(self):
        pass

    def testRegisteredUserCanLogin(self):
        '''successful authentication must return authenticated user'''

        authuser = self.users.auth('user', 'password')

        self.assertEqual('user', authuser.name,
                         'authentication must return authenticated user')


    def testNoLoginWithWrongPassword(self):
        '''valid username and invalid password = authentication failure'''

        authuser = self.users.auth('user', 'passwordtypo')

        self.assertTupleEqual(userdb.User.nobody(), authuser,
                         'authentication failure must return invalid user')


    def testNoLoginWithInvalidUser(self):
        '''invalid username = authentication failure'''

        authuser = self.users.auth('!@#$%^&*(', ')(*&^%$#')

        self.assertTupleEqual(userdb.User.nobody(), authuser,
                         'authentication failure must return invalid user')

    def testChangePassword(self):
        #create new user
        self.users.addUser('newpwuser', 'password', False)
        msg = self.users.changePassword('newpwuser', 'newpassword')
        self.assertEqual(msg, "success")

        authuser = self.users.auth('newpwuser', 'password')
        self.assertTupleEqual(userdb.User.nobody(), authuser,
                         'authentication with old password after change must fail')

        authuser = self.users.auth('newpwuser', 'newpassword')
        self.assertEqual('newpwuser', authuser.name,
                         'authentication with new passowrd failed')



if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()

########NEW FILE########
__FILENAME__ = test_useroptiondb
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# CherryMusic - a standalone music server
# Copyright (c) 2012 - 2014 Tom Wallroth & Tilman Boerner
#
# Project page:
#   http://fomori.org/cherrymusic/
# Sources on github:
#   http://github.com/devsnd/cherrymusic/
#
# CherryMusic is based on
#   jPlayer (GPL/MIT license) http://www.jplayer.org/
#   CherryPy (BSD license) http://www.cherrypy.org/
#
# licensed under GNU GPL version 3 (or later)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
#

import nose

from nose.tools import *


from cherrymusicserver import service
from cherrymusicserver import database
from cherrymusicserver import log
log.setTest()

from cherrymusicserver import useroptiondb
from cherrymusicserver.useroptiondb import UserOptionDB

def setup_module():
    service.provide('dbconnector', database.sql.MemConnector)
    database.ensure_current_version(useroptiondb.DBNAME, autoconsent=True)

def test_constructor():
    UserOptionDB()

if __name__ == '__main__':
    nose.runmodule()

########NEW FILE########
__FILENAME__ = test_util
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# CherryMusic - a standalone music server
# Copyright (c) 2012 - 2014 Tom Wallroth & Tilman Boerner
#
# Project page:
#   http://fomori.org/cherrymusic/
# Sources on github:
#   http://github.com/devsnd/cherrymusic/
#
# CherryMusic is based on
#   jPlayer (GPL/MIT license) http://www.jplayer.org/
#   CherryPy (BSD license) http://www.cherrypy.org/
#
# licensed under GNU GPL version 3 (or later)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
#

import nose

from nose.tools import *

from cherrymusicserver import util
from cherrymusicserver import log
log.setTest()

def test_maxlen_trim():
    assert util.trim_to_maxlen(7, 'abcdefghi') == 'a ... i'

def test_phrase_to_lines():
    phrase = '''qwertyui9o0 sdfghjk dfghjk dfghj fghjk dfghjk fghj fghj
    ghjfdkj ahg jkdgf sjkdfhg skjfhg sjkfh sjkd fhgsjd hgf sdjhgf skjg
    fg hjkfghjk fghjk gfhjk fghj fghjk ghj fghj gfhjk fghj ghj

    asd'''
    lines = util.phrase_to_lines(phrase, length=80)
    assert 60 < len(lines[0]) < 80
    assert 60 < len(lines[1]) < 80
    assert len(lines[1]) < 80

def test_moving_average():
    mov = util.MovingAverage(size=2)
    assert mov.avg == 0
    assert mov.min == 0
    assert mov.max == 0
    mov.feed(2)
    assert mov.avg == 1
    assert mov.min == 0
    assert mov.max == 2

def test_time2text():
    assert util.time2text(0) == 'just now'
    for mult in [60, 60*60, 60*60*24, 60*60*24*31, 60*60*24*365]:
        for i in [-1, -3, 1, 3]:
            assert util.time2text(i * mult)

def test_performance_logger():
    with util.Performance('potato head') as p:
        p.log('elephant')

if __name__ == '__main__':
    nose.runmodule()

########NEW FILE########
__FILENAME__ = tweak
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# CherryMusic - a standalone music server
# Copyright (c) 2012 - 2014 Tom Wallroth & Tilman Boerner
#
# Project page:
#   http://fomori.org/cherrymusic/
# Sources on github:
#   http://github.com/devsnd/cherrymusic/
#
# CherryMusic is based on
#   jPlayer (GPL/MIT license) http://www.jplayer.org/
#   CherryPy (BSD license) http://www.cherrypy.org/
#
# licensed under GNU GPL version 3 (or later)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
#

"""This file contains all static values that can be used to tweak the
program execution. All classes are static and only contain simple values.
To use this class, please import it using the fully classified module name, e.g

    import cherrymusicserver.tweak

To account for changes while the server is running, reload the module
before using it:

    reload(cherrymusicserver.tweak)

make sure to have reload imported as well:

    from imp import reload
"""

class ResultOrderTweaks:
    perfect_match_bonus = 100
    partial_perfect_match_bonus = 30
    starts_with_bonus = 10
    folder_bonus = 5
    word_in_file_name_bonus = 20
    word_not_in_file_name_penalty = -30
    word_in_file_path_bonus = 3
    word_not_in_file_path_penalty = -10

class CherryModelTweaks:
    result_order_debug = False
    result_order_debug_files = 10

class SearchTweaks:
    normal_file_search_limit = 400


########NEW FILE########
__FILENAME__ = userdb
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# CherryMusic - a standalone music server
# Copyright (c) 2012 - 2014 Tom Wallroth & Tilman Boerner
#
# Project page:
#   http://fomori.org/cherrymusic/
# Sources on github:
#   http://github.com/devsnd/cherrymusic/
#
# CherryMusic is based on
#   jPlayer (GPL/MIT license) http://www.jplayer.org/
#   CherryPy (BSD license) http://www.cherrypy.org/
#
# licensed under GNU GPL version 3 (or later)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
#

import hashlib
import uuid
import sqlite3

from collections import namedtuple

from cherrymusicserver import database
from cherrymusicserver import log
from cherrymusicserver import service
from cherrymusicserver.database.connect import BoundConnector

DBNAME = 'user'


class UserDB:
    def __init__(self, connector=None):
        database.require(DBNAME, version='1')
        self.conn = BoundConnector(DBNAME, connector).connection()

    def addUser(self, username, password, admin):
        if not (username.strip() or password.strip()):
            log.d(_('empty username or password!'))
            return False
        user = User.create(username, password, admin)
        try:
            self.conn.execute('''
            INSERT INTO users
            (username, admin, password, salt)
            VALUES (?,?,?,?)''',
            (user.name, 1 if user.isadmin else 0, user.password, user.salt))
        except sqlite3.IntegrityError:
            log.e('cannot create user "%s", already exists!' % user.name)
            return False
        self.conn.commit()
        log.d('added user: ' + user.name)
        return True

    def isDeletable(self, userid):
        #cant delete 1st admin
        if not userid == 1:
            return True
        return False

    def changePassword(self, username, newpassword):
        if not newpassword.strip():
            return _("not a valid password")
        else:
            newuser = User.create(username, newpassword, False) #dummy user for salt
            self.conn.execute('''
            UPDATE users SET password = ?, salt = ? WHERE username = ?
            ''', (newuser.password, newuser.salt, newuser.name) )
            return "success"

    def deleteUser(self, userid):
        if self.isDeletable(userid):
            self.conn.execute('''DELETE FROM users WHERE rowid = ?''', (userid,))
            self.conn.commit()
            return True
        return False

    def auth(self, username, password):
        '''try to authenticate the given username and password. on success,
        a valid user tuple will be returned; failure will return User.nobody().
        will fail if username or password are empty.'''

        if not (username.strip() and password.strip()):
            return User.nobody()

        rows = self.conn.execute('SELECT rowid, username, admin, password, salt'
                                 ' FROM users WHERE username = ?', (username,))\
                                 .fetchall()
        assert len(rows) <= 1
        if rows:
            user = User(*rows[0])
            if Crypto.scramble(password, user.salt) == user.password:
                return user
        return User.nobody()

    def getUserList(self):
        cur = self.conn.cursor()
        cur.execute('''SELECT rowid, username, admin FROM users''')
        ret = []
        for uid, user, admin in cur.fetchall():
            ret.append({'id':uid, 'username':user, 'admin':admin,'deletable':self.isDeletable(uid)})
        return ret

    def getUserCount(self):
        cur = self.conn.cursor()
        cur.execute('''SELECT COUNT(*) FROM users''')
        return cur.fetchall()[0][0]

    def getNameById(self, userid):
        res = self.conn.execute('''SELECT username FROM users WHERE rowid = ?''',(userid,))
        username = res.fetchone()
        return username[0] if username else 'nobody'

class Crypto(object):

    @classmethod
    def generate_salt(cls):
        '''returns a random hex string'''
        return uuid.uuid4().hex

    @classmethod
    def salted(cls, plain, salt):
        '''interweaves plain and salt'''
        return (plain[1::2] + salt + plain[::2])[::-1]

    @classmethod
    def scramble(cls, plain, salt):
        '''returns a sha512-hash of plain and salt as a hex string'''
        saltedpassword_bytes = cls.salted(plain, salt).encode('UTF-8')
        return hashlib.sha512(saltedpassword_bytes).hexdigest()


class User(namedtuple('User_', 'uid name isadmin password salt')):

    __NOBODY = None

    @classmethod
    def create(cls, name, password, isadmin=False):
        '''create a new user with given name and password.
        will add a random salt.'''

        if not name.strip():
            raise ValueError(_('name must not be empty'))
        if not password.strip():
            raise ValueError(_('password must not be empty'))

        salt = Crypto.generate_salt()
        password = Crypto.scramble(password, salt)
        return User(-1, name, isadmin, password, salt)


    @classmethod
    def nobody(cls):
        '''return a user object representing an unknown user'''
        if User.__NOBODY is None:
            User.__NOBODY = User(-1, None, None, None, None)
        return User.__NOBODY

########NEW FILE########
__FILENAME__ = useroptiondb
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# CherryMusic - a standalone music server
# Copyright (c) 2012 - 2014 Tom Wallroth & Tilman Boerner
#
# Project page:
#   http://fomori.org/cherrymusic/
# Sources on github:
#   http://github.com/devsnd/cherrymusic/
#
# CherryMusic is based on
#   jPlayer (GPL/MIT license) http://www.jplayer.org/
#   CherryPy (BSD license) http://www.cherrypy.org/
#
# licensed under GNU GPL version 3 (or later)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
#

import json

from cherrymusicserver import log
from cherrymusicserver import configuration as cfg
from cherrymusicserver import database as db
from cherrymusicserver.database.connect import BoundConnector

DBNAME = 'useroptions'


class UserOptionDB:

    def __init__(self, connector=None):
        """user configuration:
            hidden values can not be set by the user in the options,
            but might be subject of being set automatically, e.g. the
            heartbeat.
        """
        db.require(DBNAME, '0')
        c = cfg.ConfigBuilder()
        with c['keyboard_shortcuts'] as kbs:
            kbs.valid = '\d\d?\d?'
            kbs['prev'].value = 89
            kbs['play'].value = 88
            kbs['pause'].value = 67
            kbs['stop'].value = 86
            kbs['next'].value = 66
            kbs['search'].value = 83
        with c['misc.show_playlist_download_buttons'] as pl_download_buttons:
            pl_download_buttons.value = False
        with c['misc.autoplay_on_add'] as autoplay_on_add:
            autoplay_on_add.value = False
        with c['custom_theme.primary_color'] as primary_color:
            primary_color.value = '#F02E75'
            primary_color.valid = '#[0-9a-fA-F]{6}'
        with c['custom_theme.white_on_black'] as white_on_black:
            white_on_black.value = False
        with c['media.may_download'] as may_download:
            may_download.value = False
        with c['media.force_transcode_to_bitrate'] as force_transcode:
            force_transcode.value = 0
            force_transcode.valid = '0|96|128'
        with c['ui.confirm_quit_dialog'] as confirm_quit_dialog:
            confirm_quit_dialog.value = True
        with c['last_time_online'] as last_time_online:
            last_time_online.value = 0
            last_time_online.valid = '\\d+'
            last_time_online.hidden = True
            last_time_online.doc = "UNIX TIME (1.1.1970 = never)"

        self.DEFAULTS = c.to_configuration()

        self.conn = BoundConnector(DBNAME, connector).connection()

    def getOptionFromMany(self, key, userids):
        result = {}
        for userid in userids:
            val = self.useroptiondb.conn.execute(
                '''SELECT value FROM option WHERE  userid = ? AND name = ?''',
                (userid, key,)).fetchone()
            if val:
                result[userid] = val
            else:
                result[userid] = self.DEFAULTS[key]
        return result

    def forUser(self, userid):
        return UserOptionDB.UserOptionProxy(self, userid)

    class UserOptionProxy:
        def __init__(self, useroptiondb, userid):
            self.useroptiondb = useroptiondb
            self.userid = userid

        def getChangableOptions(self):
            opts = self.getOptions()
            visible_props = (p for p in opts.to_properties() if not p.hidden)
            return cfg.from_list(visible_props).to_nested_dict()

        def getOptions(self):
            results = self.useroptiondb.conn.execute(
                '''SELECT name, value FROM option WHERE userid = ?''',
                (self.userid,)).fetchall()
            useropts = dict((r[0], json.loads(r[1])) for r in results)
            return self.useroptiondb.DEFAULTS.replace(
                useropts,
                on_error=self.delete_bad_option)

        def getOptionValue(self, key):
            return self.getOptions()[key]

        def setOption(self, key, value):
            opts = self.getOptions().replace({key: value})
            self.setOptions(opts)

        def setOptions(self, c):
            for k in cfg.to_list(c):
                value = json.dumps(k.value)
                key = k.key
                sel = self.useroptiondb.conn.execute(
                    '''SELECT name, value FROM option
                        WHERE userid = ? AND name = ?''',
                    (self.userid, key)).fetchone()
                if sel:
                    self.useroptiondb.conn.execute(
                        '''UPDATE option SET value = ?
                            WHERE userid = ? AND name = ?''',
                        (value, self.userid, key))
                else:
                    self.useroptiondb.conn.execute(
                        '''INSERT INTO option (userid, name, value) VALUES
                            (?,?,?)''', (self.userid, key, value))
            self.useroptiondb.conn.commit()

        def deleteOptionIfExists(self, key):
            stmt = """DELETE FROM option WHERE userid = ? AND name = ?;"""
            with self.useroptiondb.conn as conn:
                conn.execute(stmt, (self.userid, key))

        def delete_bad_option(self, error):
            self.deleteOptionIfExists(error.key)
            log.warning('deleted bad option %r for userid %r (%s)',
                        error.key, self.userid, error.msg)

########NEW FILE########
__FILENAME__ = util
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# CherryMusic - a standalone music server
# Copyright (c) 2012 - 2014 Tom Wallroth & Tilman Boerner
#
# Project page:
#   http://fomori.org/cherrymusic/
# Sources on github:
#   http://github.com/devsnd/cherrymusic/
#
# CherryMusic is based on
#   jPlayer (GPL/MIT license) http://www.jplayer.org/
#   CherryPy (BSD license) http://www.cherrypy.org/
#
# licensed under GNU GPL version 3 (or later)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
#

#python 2.6+ backward compability
from __future__ import unicode_literals

import os
import sys
import base64
import codecs
from cherrymusicserver import log
from time import time

PERFORMANCE_TEST = True


def timed(func):
    """decorator to time function execution and log result on DEBUG"""
    def wrapper(*args, **kwargs):
        starttime = time()
        result = func(*args, **kwargs)
        duration = time() - starttime
        log.d('%s.%s: %.4f s', func.__module__, func.__name__, duration)
        return result
    return wrapper


def trim_to_maxlen(maxlen, s, insert=' ... '):
    '''no sanity check for maxlen and len(insert)'''
    if len(s) > maxlen:
        keep = maxlen - len(insert)
        left = keep // 2
        right = keep - left
        s = s[:left] + insert + s[-right:]
    return s


def phrase_to_lines(phrase, length=80):
    """splits a string along whitespace and distributes the parts into
    lines of the given length.

    each paragraph is followed by a blank line, replacing all blank
    lines separating the paragraphs in the phrase; if paragraphs get
    squashed in your multiline strings, try inserting explicit newlines.

    """

    import re
    parag_ptn = r'''(?x)      # verbose mode
    (?:                       # non-capturing group:
        [ \t\v\f\r]*          #    any non-breaking space
        \n                    #    linebreak
    ){2,}                     # at least two of these
    '''

    paragraphs = re.split(parag_ptn, phrase)
    lines = []
    for paragraph in paragraphs:
        if not paragraph:
            continue
        words = paragraph.split()
        line = ''
        for word in words:
            if len(line) + len(word) > length:
                lines.append(line.rstrip())
                line = ''
            line += word + ' '
        lines += [line.rstrip(), '']
    return lines


def splittime(seconds):
    '''converts time given in seconds into a tuple: (hours, mins, secs)'''
    tmp = seconds
    hh = tmp / 3600
    tmp %= 3600
    mm = tmp / 60
    tmp %= 60
    ss = tmp
    return (hh, mm, ss)


def Property(func):
    """
    decorator that allows defining acessors in place as local functions.
    func must define fget, and may define fset, fdel and doc; `return locals()`
    at the end.
    Seen at http://adam.gomaa.us/blog/2008/aug/11/the-python-property-builtin/
    """
    return property(**func())


from collections import deque
import math


class MovingAverage(object):
    def __init__(self, size=15, fill=0):
        assert size > 0
        self._values = deque((fill for i in range(size)))
        self._avg = fill
        self._size = size

    @property
    def avg(self):
        return self._avg

    @property
    def min(self):
        return min(self._values)

    @property
    def max(self):
        return max(self._values)

    @property
    def median(self):
        sort = sorted(self._values)
        mid = self._size // 2
        median = sort[mid]
        if self._size % 2:
            return median
        return (median + sort[mid - 1]) / 2

    @property
    def variance(self):
        diff = []
        mean = self.avg
        [diff.append((x - mean) * (x - mean)) for x in self._values]
        return sum(diff) / len(diff)

    @property
    def stddev(self):
        return math.sqrt(self.variance)

    def feed(self, val):
        '''insert a new value and get back the new average'''
        old = self._values.popleft()
        try:
            self._avg += (val - old) / self._size
        except TypeError as tpe:
            self._values.appendleft(old)
            raise tpe
        self._values.append(val)
        return self._avg


class Performance:
    indentation = 0

    def __init__(self, text):
        self.text = text

    def __enter__(self):
        global PERFORMANCE_TEST
        if PERFORMANCE_TEST:
            self.time = time()
            Performance.indentation += 1
            log.w('|   ' * (Performance.indentation - 1)
                  + '/ˉˉ' + self.text)
            return self

    def __exit__(self, type, value, traceback):
        global PERFORMANCE_TEST
        if PERFORMANCE_TEST:
            duration = (time() - self.time) * 1000
            log.w('|   ' * (Performance.indentation-1)
                  + '\__ %g ms' % (duration,))
            Performance.indentation -= 1

    def log(self, text):
        global PERFORMANCE_TEST
        if PERFORMANCE_TEST:
            for line in text.split('\n'):
                log.w('|   ' * (Performance.indentation) + line)


def time2text(sec):
    abssec = abs(sec)
    minutes = abssec/60
    hours = minutes/60
    days = hours/24
    weeks = days/7
    months = days/30
    years = months/12
    if abssec > 30:
        if sec > 0:
            if int(years) != 0:
                if years > 1:
                    return _('%d years ago') % years
                else:
                    return _('a year ago')
            elif int(months) != 0:
                if months > 1:
                    return _('%d months ago') % months
                else:
                    return _('a month ago')
            elif int(weeks) != 0:
                if weeks > 1:
                    return _('%d weeks ago') % weeks
                else:
                    return _('a week ago')
            elif int(days) != 0:
                if days > 1:
                    return _('%d days ago') % days
                else:
                    return _('a day ago')
            elif int(hours) != 0:
                if hours > 1:
                    return _('%d hours ago') % hours
                else:
                    return _('an hour ago')
            elif hours > 0.45:
                return _('half an hour ago')
            elif int(minutes) != 0:
                if minutes > 1:
                    return _('%d minutes ago') % hours
                else:
                    return _('a minute ago')
            else:
                return _('a few seconds ago')
        else:
            if int(years) != 0:
                if years > 1:
                    return _('in %d years') % years
                else:
                    return _('in a year')
            elif int(months) != 0:
                if months > 1:
                    return _('in %d months') % months
                else:
                    return _('in a month')
            elif int(weeks) != 0:
                if weeks > 1:
                    return _('in %d weeks') % weeks
                else:
                    return _('in a week')
            elif int(days) != 0:
                if days > 1:
                    return _('in %d days') % days
                else:
                    return _('in a day')
            elif int(hours) != 0:
                if hours > 1:
                    return _('in %d hours') % hours
                else:
                    return _('in an hour')
            elif hours > 0.45:
                return _('in half an hour')
            elif int(minutes) != 0:
                if minutes > 1:
                    return _('in %d minutes') % hours
                else:
                    return _('in a minute')
            else:
                return _('in a few seconds')
    else:
        return _('just now')


class MemoryZipFile(object):

    def __init__(self):
        from io import BytesIO
        from zipfile import ZipFile
        self.buffer = BytesIO()
        self.zip = ZipFile(self.buffer, 'w')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def writestr(self, name, bytes):
        try:
            self.zip.writestr(name, bytes)
        except:
            log.x(_('Error writing file %(name)r to memory zip'), {'name': name})
            raise

    def getbytes(self):
        return self.buffer.getvalue()

    def close(self):
        self.zip.close()

########NEW FILE########
__FILENAME__ = deploy
#!/usr/bin/python3

import subprocess as sp
import re
import os
import hashlib

MAIN_CM_FOLDER = os.path.dirname(os.path.dirname(__file__))

DEVEL_INPUT_HTML = os.path.join(MAIN_CM_FOLDER, 'res/devel.html')
MAIN_OUTPUT_HTML = os.path.join(MAIN_CM_FOLDER, 'res/dist/main.html')

LESSC = 'lessc'
JSMIN = 'jsmin'

def prog_exists(exe):
    try:
        with open(os.devnull,'w') as devnull:
            prog = sp.Popen([exe], stdin=devnull, stdout=devnull)
            stout, sterr = prog.communicate('')
    except IOError:
        return False
    return True
    
if not (prog_exists(LESSC) and prog_exists(JSMIN)):
    print('''=== WARNING: CANNOT DEPLOY ===
For automatic deployment, please install jsmin and the less-css compiler
and make sure they are in your $PATH.''')
    exit(0)

def compile_less(in_less_file, out_css_file):
    LESSC_OPTS = ['--include-path='+os.path.dirname(in_less_file),'-'] #['--yui-compress', '-']
    print(" compiling %s to %s"%(in_less_file, out_css_file))
    with open(in_less_file, 'rb') as fr:
        with open(out_css_file, 'wb') as fw:
            less_file_dir = os.path.dirname(in_less_file)
            compiler = sp.Popen([LESSC]+LESSC_OPTS,
                                stdin=sp.PIPE,
                                stdout=sp.PIPE)
            stout, sterr = compiler.communicate(fr.read())
            fw.write(stout)
            print(" Wrote %s bytes."% fw.tell())

def parse_args(argsstr):
    argpairs = [x.split('=') for x in argsstr.strip().split(' ')]
    return dict(argpairs)

def match_less_compile(match):
    args = parse_args(match.group(1))
    lessfile = re.findall('href="([^"]+)', match.group(2))[0]
    outfile = args['out']
    compile_less(lessfile, outfile)
    return '<link href="%s" media="all" rel="stylesheet" type="text/css" />' % outfile

def compile_jsmin(instr, outfile):
     with open(outfile, 'wb') as fw:
        compiler = sp.Popen([JSMIN], stdin=sp.PIPE, stdout=sp.PIPE)
        stout, sterr = compiler.communicate(instr)
        fw.write(stout)
        print("compressed to %s bytes."% fw.tell())
        print("that's %d%% less" % (100 - fw.tell()/len(instr)*100) )

def match_js_concat_min(match):
    args = parse_args(match.group(1))
    jsstr = b''
    for scriptpath in re.findall('<script.*src="([^"]+)"', match.group(2)):
        with open(scriptpath, 'rb') as script:
            jsstr += script.read()
            jsstr += b';\n'
    jshash = hashlib.md5(jsstr).hexdigest()
    print('calculated hash %s' % jshash)
    print('js scripts uncompressed %d bytes' % len(jsstr))
    outfilename = args['out']
    #dotpos = outfilename.rindex('.')
    #outfilename = outfilename[:dotpos]+jshash+outfilename[dotpos:]
    compile_jsmin(jsstr, outfilename)
    return '<script type="text/javascript" src="%s"></script>' % outfilename

def remove_whitespace(html):
    no_white = re.sub('\s+', ' ', html, flags=re.MULTILINE)
    print('removed whitespace. before %d bytes, after %d bytes.' % (len(html), len(no_white)))
    print("that's %d%% less" % (100 - len(no_white)/len(html)*100) )
    return no_white

html = None
with open(DEVEL_INPUT_HTML, 'r') as develhtml:
    html = develhtml.read()

html = re.sub('<!--LESS-TO-CSS-BEGIN([^>]*)-->(.*)<!--LESS-TO-CSS-END-->',
              match_less_compile,
              html,
              flags=re.MULTILINE | re.DOTALL)
html = re.sub('<!--REMOVE-BEGIN-->(.*)<!--REMOVE-END-->',
              '',
              html,
              flags=re.MULTILINE | re.DOTALL)
html = re.sub('<!--COMPRESS-JS-BEGIN([^>]*)-->(.*)<!--COMPRESS-JS-END-->',
              match_js_concat_min,
              html,
              flags=re.MULTILINE | re.DOTALL)
html = remove_whitespace(html)

with open(MAIN_OUTPUT_HTML, 'w') as mainhtml:
    mainhtml.write(html)
########NEW FILE########
__FILENAME__ = release
#!/usr/bin/python3
import subprocess
import os
import sys
import codecs
import time

usage = """
%s --major
    prepare a major release, e.g. 1.3.5 --> 2.3.5
%s --minor
    prepare a minor release, e.g. 1.3.5 --> 1.4.5
%s --path
    prepare a patch release, e.g. 1.3.5 --> 1.3.6
""" % (__file__,__file__,__file__,)

if (2 > len(sys.argv) == 1) or not sys.argv[1] in ['--major','--minor','--patch']:
    print(usage)
    sys.exit(1)
else:
    release_type = sys.argv[1][2:]  # = 'major' 'minor' or 'patch'

CM_MAIN_FOLDER = os.path.join(os.path.dirname(__file__), '..')
os.chdir(CM_MAIN_FOLDER)

output = subprocess.check_output(['python', '-c', 'import cherrymusicserver; print(cherrymusicserver.__version__)'])
rawcmversion = codecs.decode(output, 'UTF-8')
major, minor, patch = [int(v) for v in rawcmversion.split('.')]
version_now = (major, minor, patch)
if release_type == 'major':
    version_next = (major+1, 0, 0)
elif release_type == 'minor':
    version_next = (major, minor+1, 0)
elif release_type == 'patch':
    version_next = (major, minor, patch+1)

######## CHANGE INIT SCRIPT VERSION NUMBER #####
initscript = None
with open('cherrymusicserver/__init__.py', 'r', encoding='UTF-8') as fh:
    initscript = fh.read()
    version_line_tpl = '''VERSION = "%d.%d.%d"'''
    version_now_line = version_line_tpl % version_now
    version_next_line = version_line_tpl % version_next
    if initscript.find(version_now_line) == -1:
        print('''Cannot find version string in startup script! Looking for:

%s
''' % version_now_line)
        sys.exit(1)
    print('Changing version number in startup script. %s --> %s' %
          (version_now_line, version_next_line))
    initscript = initscript.replace(version_now_line, version_next_line)
with open('cherrymusicserver/__init__.py', 'w', encoding='UTF-8') as fh:
    fh.write(initscript)


######## UPDATE CHANGELOG #####
changelog_lines = None
t = time.gmtime()
with open('CHANGES', 'r', encoding='UTF-8') as fh:
    changelog_lines = fh.readlines()
with open('CHANGES', 'w', encoding='UTF-8') as fh:
    fh.write('Changelog\n---------\n\n')
    fh.write('%d.%d.%d ' % version_next)
    fh.write('(%d-%02d-%02d)\n' % (t.tm_year, t.tm_mon, t.tm_mday))
    fh.write(' - FEATURE: ... new feature here!\n')
    fh.write(' - FIXED:\n')
    fh.write(' - IMPROVEMENT:\n\n')
    fh.write(''.join(changelog_lines[3:]))  # leave out header
subprocess.call(['nano', 'CHANGES'])

####### PREPARE COMMIT AND REVIEW DIFF

subprocess.call(['git', 'add', 'CHANGES'])
subprocess.call(['git', 'add', 'cherrymusicserver/__init__.py'])
subprocess.call(['git', 'diff', '--staged'])
if input('Are you happy now? (y/n)') != 'y':
    print('''user unhappy. revert changes with
git checkout CHANGES
git checkout cherrymusicserver/__init__.py
''')
    sys.exit(1)

print('creating tagged commit...')
version_name = 'release %d.%d.%d' % version_next
tag_name = '%d.%d.%d' % version_next
subprocess.call(['git', 'commit', '-m', '"%s"' % version_name])
subprocess.call(['git', 'tag', '-a', '-m', '"%s"' % version_name, tag_name])
print('''all done, you can push the changes now! e.g.:

git push --tags
''')


########NEW FILE########
__FILENAME__ = conf
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# CherryMusic documentation build configuration file, created by
# sphinx-quickstart on Fri Mar  1 23:32:37 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join('..', '..')))
import cherrymusicserver as cherry
# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'CherryMusic'
copyright = '2012 - 2014, Tom Wallroth, with Tilman Boerner'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = os.path.splitext(cherry.VERSION)[0]
# The full version, including alpha/beta/rc tags.
release = cherry.VERSION

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
html_theme = 'haiku'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}
html_theme_options = {
#        'textcolor': '#333333',
        'headingcolor': '#892601',
        'linkcolor': '#2c5792',
        'visitedlinkcolor': '#0c3762',
#       'hoverlinkcolor': '#0c3762',
}
# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None
html_title = 'CherryMusic %s documentation' % (cherry.VERSION,)

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
# html_static_path = ['_static']

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
htmlhelp_basename = 'cherrymusicdoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',
'papersize': 'a4paper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'CherryMusic.tex', 'CherryMusic Documentation',
   'Author', 'manual'),
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

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'CherryMusic', 'CherryMusic Documentation',
     ['Author'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'CherryMusic', 'CherryMusic Documentation',
   'Author', 'CherryMusic', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'


# -- Options for Epub output ---------------------------------------------------

# Bibliographic Dublin Core info.
epub_title = 'CherryMusic'
epub_author = 'Author'
epub_publisher = 'Author'
epub_copyright = '2012 - 2014, Author'

# The language of the text. It defaults to the language option
# or en if the language is not set.
#epub_language = ''

# The scheme of the identifier. Typical schemes are ISBN or URL.
#epub_scheme = ''

# The unique identifier of the text. This can be a ISBN number
# or the project homepage.
#epub_identifier = ''

# A unique identification for the text.
#epub_uid = ''

# A tuple containing the cover image and cover page html template filenames.
#epub_cover = ()

# HTML files that should be inserted before the pages created by sphinx.
# The format is a list of tuples containing the path and title.
#epub_pre_files = []

# HTML files shat should be inserted after the pages created by sphinx.
# The format is a list of tuples containing the path and title.
#epub_post_files = []

# A list of files that should not be packed into the epub file.
#epub_exclude_files = []

# The depth of the table of contents in toc.ncx.
#epub_tocdepth = 3

# Allow duplicate toc entries.
#epub_tocdup = True

########NEW FILE########
__FILENAME__ = update_translations
#!/usr/bin/python3
import subprocess
import os

currdir = os.path.relpath(os.path.dirname(__file__), start=os.getcwd())
sourcedir = os.path.normpath(os.path.join(currdir, '..', '..', 'cherrymusicserver'))

print('updating pot file')
subprocess.call('xgettext --language=Python --keyword=_ --add-comments=i18n --output='+currdir+'/cherrymusic.pot --from-code=UTF-8 `find '+sourcedir+' -name "*.py"`', shell=True)
print('updating all translations')
for translation in os.listdir(currdir):
    transfile = os.path.join(currdir, translation)
    if os.path.isdir(transfile):
        print('    merging %s' % transfile)
        subprocess.call('msgmerge --update '+transfile+'/LC_MESSAGES/default.po '+currdir+'/cherrymusic.pot', shell=True)
        print('    compiling %s' % transfile)
        subprocess.call('msgfmt -o '+transfile+'/LC_MESSAGES/default.mo -v '+transfile+'/LC_MESSAGES/default.po', shell=True)


########NEW FILE########
__FILENAME__ = tinytag
#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# tinytag - an audio meta info reader
# Copyright (c) 2014 Tom Wallroth
#
# Sources on github:
# http://github.com/devsnd/tinytag/
#
# licensed under GNU GPL version 3 (or later)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>
#

import codecs
import struct
import os


class TinyTag(object):
    """Base class for all tag types"""
    def __init__(self, filehandler, filesize):
        self._filehandler = filehandler
        self.filesize = filesize
        self.track = None
        self.track_total = None
        self.title = None
        self.artist = None
        self.album = None
        self.year = None
        self.duration = 0
        self.audio_offset = 0
        self.bitrate = 0.0  # must be float for later VBR calculations
        self.samplerate = 0

    def has_all_tags(self):
        """check if all tags are already defined. Useful for ID3 tags
        since multiple kinds of tags can be in one audio file
        """
        return all((self.track, self.track_total, self.title,
                    self.artist, self.album, self.year))

    @classmethod
    def get(cls, filename, tags=True, duration=True):
        parser_class = None
        size = os.path.getsize(filename)
        if not size > 0:
            return TinyTag(None, 0)
        if cls == TinyTag:
            """choose which tag reader should be used by file extension"""
            mapping = {
                ('.mp3',): ID3,
                ('.oga', '.ogg'): Ogg,
                ('.wav'): Wave,
                ('.flac'): Flac,
            }
            for fileextension, tagclass in mapping.items():
                if filename.lower().endswith(fileextension):
                    parser_class = tagclass
        else:
            # use class on which the method was invoked as parser
            parser_class = cls
        if parser_class is None:
            raise LookupError('No tag reader found to support filetype! ')
        with open(filename, 'rb') as af:
            tag = parser_class(af, size)
            tag.load(tags=tags, duration=duration)
            return tag

    def __str__(self):
        public_attrs = ((k, v) for k, v in self.__dict__.items() if not k.startswith('_'))
        return str(dict(public_attrs))

    def __repr__(self):
        return str(self)

    def load(self, tags, duration):
        """default behavior of all tags. This method is called in the
        constructors of all tag readers
        """
        if tags:
            self._parse_tag(self._filehandler)
            self._filehandler.seek(0)
        if duration:
            self._determine_duration(self._filehandler)

    def _set_field(self, fieldname, bytestring, transfunc=None):
        """convienience function to set fields of the tinytag by name.
        the payload (bytestring) can be changed using the transfunc"""
        if getattr(self, fieldname):
            return
        if transfunc:
            setattr(self, fieldname, transfunc(bytestring))
        else:
            setattr(self, fieldname, bytestring)

    def _determine_duration(self, fh):
        raise NotImplementedError()

    def _parse_tag(self, fh):
        raise NotImplementedError()

    def update(self, other):
        """update the values of this tag with the values from another tag"""
        for key in ['track', 'track_total', 'title', 'artist',
                    'album', 'year', 'duration']:
            if not getattr(self, key) and getattr(other, key):
                setattr(self, key, getattr(other, key))


class ID3(TinyTag):
    FID_TO_FIELD = {  # Mapping from Frame ID to a field of the TinyTag
        'TRCK': 'track',  'TRK': 'track',
        'TYER': 'year',   'TYE': 'year',
        'TALB': 'album',  'TAL': 'album',
        'TPE1': 'artist', 'TP1': 'artist',
        'TIT2': 'title',  'TT2': 'title',
    }
    _MAX_ESTIMATION_SEC = 30

    def __init__(self, filehandler, filesize):
        TinyTag.__init__(self, filehandler, filesize)
        # save position after the ID3 tag for duration mesurement speedup
        self._bytepos_after_id3v2 = 0

    @classmethod
    def set_estimation_precision(cls, estimation_in_seconds):
        cls._MAX_ESTIMATION_SEC = estimation_in_seconds

    def _determine_duration(self, fh):
        max_estimation_frames = (ID3._MAX_ESTIMATION_SEC*44100) // 1152
        frame_size_mean = 0
        # set sample rate from first found frame later, default to 44khz
        file_sample_rate = 44100
        # see this page for the magic values used in mp3:
        # http://www.mpgedit.org/mpgedit/mpeg_format/mpeghdr.htm
        bitrates = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192,
                    224, 256, 320]
        samplerates = [44100, 48000, 32000]
        header_bytes = 4
        frames = 0  # count frames for determining mp3 duration
        # seek to first position after id3 tag (speedup for large header)
        fh.seek(self._bytepos_after_id3v2)
        while True:
            # reading through garbage until 12 '1' bits are found
            b = fh.read(1)
            if len(b) == 0:
                break
            if b == b'\xff':
                b = fh.read(1)
                if b > b'\xf0':
                    bitrate_freq, rest = struct.unpack('BB', fh.read(2))
                    br_id = (bitrate_freq & 0xf0) >> 4  # biterate id
                    sr_id = (bitrate_freq & 0x03) >> 2  # sample rate id
                    # check if the values aren't just random
                    if br_id == 15 or br_id == 0 or sr_id == 3:
                        # invalid frame! roll back to last position
                        fh.seek(-2, os.SEEK_CUR)
                        continue
                    frames += 1  # it's most probably an mp3 frame
                    bitrate = bitrates[br_id]
                    samplerate = samplerates[sr_id]
                    # running average of bitrate
                    self.bitrate = (self.bitrate*(frames-1) + bitrate)/frames
                    if frames == 1:
                        # we already read the 4 bytes frame header
                        self.audio_offset = fh.tell() - 4
                        self.samplerate = samplerate
                    padding = 1 if bitrate_freq & 0x02 > 0 else 0
                    frame_length = (144000 * bitrate) // samplerate + padding
                    frame_size_mean += frame_length
                    if frames == max_estimation_frames:
                        # try to estimate duration
                        fh.seek(-1, 2)  # jump to last byte
                        estimated_frame_count = fh.tell() / (frame_size_mean / frames)
                        samples = estimated_frame_count * 1152
                        self.duration = samples/float(self.samplerate)
                        return
                    if frame_length > 1:
                        # jump over current frame body
                        fh.seek(frame_length - header_bytes, os.SEEK_CUR)
        samples = frames * 1152  # 1152 is the default frame size for mp3
        if self.samplerate:
            self.duration = samples/float(self.samplerate)

    def _parse_tag(self, fh):
        self._parse_id3v2(fh)
        if not self.has_all_tags():  # try to get more info using id3v1
            fh.seek(-128, 2)  # id3v1 occuppies the last 128 bytes
            self._parse_id3v1(fh)

    def _parse_id3v2(self, fh):
        # for info on the specs, see: http://id3.org/Developer%20Information
        header = struct.unpack('3sBBB4B', fh.read(10))
        tag = codecs.decode(header[0], 'ISO-8859-1')
        # check if there is an ID3v2 tag at the beginning of the file
        if tag == 'ID3':
            major, rev = header[1:3]
            unsync = (header[3] & 0x80) > 0
            extended = (header[3] & 0x40) > 0
            experimental = (header[3] & 0x20) > 0
            footer = (header[3] & 0x10) > 0
            size = self._calc_size_7bit_bytes(header[4:9])
            self._bytepos_after_id3v2 = size
            parsed_size = 0
            if extended:  # just read over the extended header.
                size_bytes = struct.unpack('4B', fh.read(6)[0:4])
                extd_size = self._calc_size_7bit_bytes(size_bytes)
                fh.read(extd_size - 6)
            while parsed_size < size:
                is_id3_v22 = major == 2
                frame_size = self._parse_frame(fh, is_v22=is_id3_v22)
                if frame_size == 0:
                    break
                parsed_size += frame_size

    def _parse_id3v1(self, fh):
        if fh.read(3) == b'TAG':  # check if this is an ID3 v1 tag
            asciidecode = lambda x: self._unpad(codecs.decode(x, 'ASCII'))
            self._set_field('title', fh.read(30), transfunc=asciidecode)
            self._set_field('artist', fh.read(30), transfunc=asciidecode)
            self._set_field('album', fh.read(30), transfunc=asciidecode)
            self._set_field('year', fh.read(4), transfunc=asciidecode)
            comment = fh.read(30)
            if b'\x00\x00' < comment[-2:] < b'\x01\x00':
                self._set_field('track', str(ord(comment[-1:])))

    def _parse_frame(self, fh, is_v22=False):
        encoding = 'ISO-8859-1'  # default encoding used in most mp3 tags
        # ID3v2.2 especially ugly. see: http://id3.org/id3v2-00
        frame_header_size = 6 if is_v22 else 10
        frame_size_bytes = 3 if is_v22 else 4
        binformat = '3s3B' if is_v22 else '4s4B2B'
        frame_header_data = fh.read(frame_header_size)
        if len(frame_header_data) == 0:
            return 0
        frame = struct.unpack(binformat, frame_header_data)
        frame_id = self._decode_string(frame[0])
        frame_size = self._calc_size_7bit_bytes(frame[1:1+frame_size_bytes])
        if frame_size > 0:
            # flags = frame[1+frame_size_bytes:] # dont care about flags.
            content = fh.read(frame_size)
            fieldname = ID3.FID_TO_FIELD.get(frame_id)
            if fieldname:
                if fieldname == 'track':
                    self._parse_track(content)
                else:
                    self._set_field(fieldname, content, self._decode_string)
            return frame_size
        return 0

    def _decode_string(self, b):
        # it's not my fault, this is the spec.
        if b[:1] == b'\x00':
            return self._unpad(codecs.decode(b[1:], 'ISO-8859-1'))
        if b[0:3] == b'\x01\xff\xfe':
            bytestr = b[3:-1] if len(b) % 2 == 0 else b[3:]
            return codecs.decode(bytestr, 'UTF-16')
        return self._unpad(codecs.decode(b, 'ISO-8859-1'))

    def _unpad(self, s):
        # strings in mp3 _can_ be terminated with a zero byte at the end
        return s[:s.index('\x00')] if '\x00' in s else s

    def _parse_track(self, b):
        track = self._decode_string(b)
        track_total = None
        if '/' in track:
            track, track_total = track.split('/')
        self._set_field('track', track)
        self._set_field('track_total', track_total)

    def _calc_size_7bit_bytes(self, bytestr):
        ret = 0             # length of mp3 header fields is described
        for b in bytestr:   # by some "7-bit-bytes". The most significant
            ret <<= 7       # bit is always set to zero, so it has to be
            ret += b & 127  # removed.
        return ret          #


class StringWalker(object):
    """file obj like string. probably there are buildins doing this already"""
    def __init__(self, string):
        self.string = string

    def read(self, nbytes):
        retstring, self.string = self.string[:nbytes], self.string[nbytes:]
        return retstring


class Ogg(TinyTag):
    def __init__(self, filehandler, filesize):
        TinyTag.__init__(self, filehandler, filesize)
        self._tags_parsed = False
        self._max_samplenum = 0  # maximum sample position ever read

    def _determine_duration(self, fh):
        MAX_PAGE_SIZE = 65536  # https://xiph.org/ogg/doc/libogg/ogg_page.html
        if not self._tags_parsed:
            self._parse_tag(fh)  # determine sample rate
            fh.seek(0)           # and rewind to start
        if self.filesize > MAX_PAGE_SIZE:
            fh.seek(-MAX_PAGE_SIZE, 2)  # go to last possible page position
        while True:
            b = fh.read(1)
            if len(b) == 0:
                return  # EOF
            if b == b'O':  # look for an ogg header
                if fh.read(3) == b'ggS':
                    fh.seek(-4, 1)  # parse the page header from start
                    for packet in self._parse_pages(fh):
                        pass  # parse all remaining pages
                    self.duration = self._max_samplenum / float(self.samplerate)
                else:
                    fh.seek(-3, 1)  # oops, no header, rewind selectah!

    def _parse_tag(self, fh):
        page_start_pos = fh.tell()  # set audio_offest later if its audio data
        for packet in self._parse_pages(fh):
            walker = StringWalker(packet)
            header = walker.read(7)
            if header == b"\x01vorbis":
                (channels, self.samplerate, max_bitrate, bitrate,
                 min_bitrate) = struct.unpack("<B4i", packet[11:28])
                if not self.audio_offset:
                    self.bitrate = bitrate / 1024
                    self.audio_offset = page_start_pos
            elif header == b"\x03vorbis":
                self._parse_vorbis_comment(walker)
            else:
                break
            page_start_pos = fh.tell()

    def _parse_vorbis_comment(self, fh):
        # for the spec, see: http://xiph.org/vorbis/doc/v-comment.html
        mapping = {'album': 'album', 'title': 'title', 'artist': 'artist',
                   'date': 'year', 'tracknumber': 'track'}
        vendor_length = struct.unpack('I', fh.read(4))[0]
        vendor = fh.read(vendor_length)
        elements = struct.unpack('I', fh.read(4))[0]
        for i in range(elements):
            length = struct.unpack('I', fh.read(4))[0]
            keyvalpair = codecs.decode(fh.read(length), 'UTF-8')
            if '=' in keyvalpair:
                splitidx = keyvalpair.index('=')
                key, value = keyvalpair[:splitidx], keyvalpair[splitidx+1:]
                fieldname = mapping.get(key.lower())
                if fieldname:
                    self._set_field(fieldname, value)

    def _parse_pages(self, fh):
        # for the spec, see: https://wiki.xiph.org/Ogg
        previous_page = b''  # contains data from previous (continuing) pages
        header_data = fh.read(27)  # read ogg page header
        while len(header_data) != 0:
            header = struct.unpack('<4sBBqIIiB', header_data)
            oggs, version, flags, pos, serial, pageseq, crc, segments = header
            self._max_samplenum = max(self._max_samplenum, pos)
            if oggs != b'OggS' or version != 0:
                break  # not a valid ogg file
            segsizes = struct.unpack('B'*segments, fh.read(segments))
            total = 0
            for segsize in segsizes:  # read all segments
                total += segsize
                if total < 255:  # less than 255 bytes means end of page
                    yield previous_page + fh.read(total)
                    previous_page = b''
                    total = 0
            if total != 0:
                if total % 255 == 0:
                    previous_page += fh.read(total)
                else:
                    yield previous_page + fh.read(total)
                    previous_page = b''
            header_data = fh.read(27)


class Wave(TinyTag):
    def __init__(self, filehandler, filesize):
        TinyTag.__init__(self, filehandler, filesize)
        self._duration_parsed = False

    def _determine_duration(self, fh):
        # see: https://ccrma.stanford.edu/courses/422/projects/WaveFormat/
        # and: https://en.wikipedia.org/wiki/WAV
        riff, size, fformat = struct.unpack('4sI4s', fh.read(12))
        if riff != b'RIFF' or fformat != b'WAVE':
            print('not a wave file!')
        channels, samplerate, bitdepth = 2, 44100, 16  # assume CD quality
        chunk_header = fh.read(8)
        while len(chunk_header) > 0:
            subchunkid, subchunksize = struct.unpack('4sI', chunk_header)
            if subchunkid == b'fmt ':
                _, channels, self.samplerate = struct.unpack('HHI', fh.read(8))
                _, _, bitdepth = struct.unpack('<IHH', fh.read(8))
                self.bitrate = self.samplerate * channels * bitdepth / 1024
            elif subchunkid == b'data':
                self.duration = subchunksize/channels/samplerate/(bitdepth/8)
                self.audio_offest = fh.tell() - 8  # rewind to data header
                fh.seek(subchunksize, 1)
            elif subchunkid == b'id3 ' or subchunkid == b'ID3 ':
                id3 = ID3(fh, 0)
                id3._parse_id3v2(fh)
                self.update(id3)
            else:  # some other chunk, just skip the data
                fh.seek(subchunksize, 1)
            chunk_header = fh.read(8)
        self._duration_parsed = True

    def _parse_tag(self, fh):
        if not self._duration_parsed:
            self._determine_duration(fh)  # parse_whole file to determine tags :(


class Flac(TinyTag):
    def load(self, tags, duration):
        if self._filehandler.read(4) != b'fLaC':
            return  # not a flac file!
        if tags:
            self._parse_tag(self._filehandler)
            self._filehandler.seek(4)
        if duration:
            self._determine_duration(self._filehandler)

    def _determine_duration(self, fh):
        # for spec, see https://xiph.org/flac/ogg_mapping.html
        header_data = fh.read(4)
        while len(header_data):
            meta_header = struct.unpack('B3B', header_data)
            size = self._bytes_to_int(meta_header[1:4])
            # http://xiph.org/flac/format.html#metadata_block_streaminfo
            if meta_header[0] == 0:  # STREAMINFO
                stream_info_header = fh.read(size)
                if len(stream_info_header) < 34:  # invalid streaminfo
                    break
                header = struct.unpack('HH3s3s8B16s', stream_info_header)
                min_blk, max_blk, min_frm, max_frm = header[0:4]
                min_frm = self._bytes_to_int(struct.unpack('3B', min_frm))
                max_frm = self._bytes_to_int(struct.unpack('3B', max_frm))
                self.samplerate = self._bytes_to_int(header[4:7]) >> 4
                channels = ((header[7] >> 1) & 7) + 1
                bit_depth = ((header[7] & 1) << 4) + ((header[8] & 0xF0) >> 4)
                bit_depth = (bit_depth + 1)
                total_sample_bytes = [(header[8] >> 4)] + list(header[9:12])
                total_samples = self._bytes_to_int(total_sample_bytes)
                md5 = header[12:]
                self.duration = float(total_samples) / self.samplerate
                self.bitrate = self.filesize/self.duration*8/1024
                return
            else:
                fh.seek(size, 1)
                header_data = fh.read(4)

    def _bytes_to_int(self, b):
        result = 0
        for byte in b:
            result = (result << 8) + byte
        return result

    def _parse_tag(self, fh):
        # for spec, see https://xiph.org/flac/ogg_mapping.html
        header_data = fh.read(4)
        while len(header_data):
            meta_header = struct.unpack('B3B', header_data)
            size = self._bytes_to_int(meta_header[1:4])
            if meta_header[0] == 4:
                oggtag = Ogg(fh, 0)
                oggtag._parse_vorbis_comment(fh)
                self.update(oggtag)
                return
            else:
                fh.seek(size, 1)
                header_data = fh.read(4)

########NEW FILE########
