__FILENAME__ = tagging
# Metadata tag support for whatbetter.
#
# Copyright (c) 2013 Milky Joe <milkiejoe@gmail.com>
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Simple tagging for whatbetter.
"""

import os.path
import re
import mutagen
import mutagen.flac
import mutagen.mp3
from mutagen.easyid3 import EasyID3

numeric_tags = set([
        'tracknumber',
        'discnumber',
        'tracktotal',
        'totaltracks',
        'disctotal',
        'totaldiscs',
        ])

class TaggingException(Exception):
    pass

def valid_fractional_tag(value):
    # m or m/n
    if re.match(r"""\d+(/(\d+))?$""", value):
        return True
    else:
        return False

def scrub_tag(name, value):
    """Strip whitespace (and other common problems) from tag values.

    May return the empty string ''.
    """
    scrubbed_value = value.strip().strip('\x00')

    # Strip trailing '/' or '/0' from numeric tags.
    if name in numeric_tags:
        scrubbed_value = re.sub(r"""/(0+)?$""", '', scrubbed_value)

    # Remove leading '/' from numeric tags.
    if name in numeric_tags:
        scrubbed_value = scrubbed_value.lstrip('/')

    # Numeric tags should not be '0' (but tracknumber 0 is OK, e.g.,
    # hidden track).
    if name in numeric_tags - set(['tracknumber']):
        if re.match(r"""0+(/.*)?$""", scrubbed_value):
            return ''

    return scrubbed_value

def check_tags(filename, check_tracknumber_format=True):
    """Verify that the file has the required What.CD tags.

    Returns (True, None) if OK, (False, msg) if a tag is missing or
    invalid.

    """
    info = mutagen.File(filename, easy=True)
    for tag in ['artist', 'album', 'title', 'tracknumber']:
        if tag not in info.keys():
            return (False, '"%s" has no %s tag' % (filename, tag))
        elif info[tag] == [u'']:
            return (False, '"%s" has an empty %s tag' % (filename, tag))

    if check_tracknumber_format:
        tracknumber = info['tracknumber'][0]
        if not valid_fractional_tag(tracknumber):
            return (False, '"%s" has a malformed tracknumber tag ("%s")' % (filename, tracknumber))

    return (True, None)

def copy_tags(flac_file, transcode_file):
    flac_info = mutagen.flac.FLAC(flac_file)
    transcode_info = None
    valid_key_fn = None
    transcode_ext = os.path.splitext(transcode_file)[1].lower()

    if transcode_ext == '.flac':
        transcode_info = mutagen.flac.FLAC(transcode_file)
        valid_key_fn = lambda k: True

    elif transcode_ext == '.mp3':
        transcode_info = mutagen.mp3.EasyMP3(transcode_file)
        valid_key_fn = lambda k: k in EasyID3.valid_keys.keys()

    else:
        raise TaggingException('Unsupported tag format "%s"' % transcode_file)

    for tag in filter(valid_key_fn, flac_info):
        # scrub the FLAC tags, just to be on the safe side.
        values = map(lambda v: scrub_tag(tag,v), flac_info[tag])
        if values and values != [u'']:
            transcode_info[tag] = values

    if transcode_ext == '.mp3':
        # Support for TRCK and TPOS x/y notation, which is not
        # supported by EasyID3.
        #
        # These tags don't make sense as lists, so we just use the head
        # element when fixing them up.
        #
        # totaltracks and totaldiscs may also appear in the FLAC file
        # as 'tracktotal' and 'disctotal'. We support either tag, but
        # in files with both we choose only one.

        if 'tracknumber' in transcode_info.keys():
            totaltracks = None
            if 'totaltracks' in flac_info.keys():
                totaltracks = scrub_tag('totaltracks', flac_info['totaltracks'][0])
            elif 'tracktotal' in flac_info.keys():
                totaltracks = scrub_tag('tracktotal', flac_info['tracktotal'][0])

            if totaltracks:
                transcode_info['tracknumber'] = [u'%s/%s' % (transcode_info['tracknumber'][0], totaltracks)]

        if 'discnumber' in transcode_info.keys():
            totaldiscs = None
            if 'totaldiscs' in flac_info.keys():
                totaldiscs = scrub_tag('totaldiscs', flac_info['totaldiscs'][0])
            elif 'disctotal' in flac_info.keys():
                totaldiscs = scrub_tag('disctotal', flac_info['disctotal'][0])

            if totaldiscs:
                transcode_info['discnumber'] = [u'%s/%s' % (transcode_info['discnumber'][0], totaldiscs)]

    transcode_info.save()

# EasyID3 extensions for whatbetter.

for key, frameid in {
    'albumartist': 'TPE2',
    'album artist': 'TPE2',
    'grouping': 'TIT1',
    'content group': 'TIT1',
    }.iteritems():
    EasyID3.RegisterTextKey(key, frameid)

def comment_get(id3, _):
    return [comment.text for comment in id3['COMM'].text]

def comment_set(id3, _, value):
    id3.add(mutagen.id3.COMM(encoding=3, lang='eng', desc='', text=value))

def originaldate_get(id3, _):
    return [stamp.text for stamp in id3['TDOR'].text]

def originaldate_set(id3, _, value):
    id3.add(mutagen.id3.TDOR(encoding=3, text=value))

EasyID3.RegisterKey('comment', comment_get, comment_set)
EasyID3.RegisterKey('description', comment_get, comment_set)
EasyID3.RegisterKey('originaldate', originaldate_get, originaldate_set)
EasyID3.RegisterKey('original release date', originaldate_get, originaldate_set)

########NEW FILE########
__FILENAME__ = transcode
#!/usr/bin/env python
import os
import re
import sys
import errno
import pipes
import shlex
import shutil
import signal
import fnmatch
import tempfile
import subprocess
import multiprocessing
import mutagen.flac
import tagging

encoders = {
    '320':  {'enc': 'lame', 'ext': '.mp3',  'opts': '-h -b 320 --ignore-tag-errors'},
    'V0':   {'enc': 'lame', 'ext': '.mp3',  'opts': '-V 0 --vbr-new --ignore-tag-errors'},
    'V2':   {'enc': 'lame', 'ext': '.mp3',  'opts': '-V 2 --vbr-new --ignore-tag-errors'},
    'FLAC': {'enc': 'flac', 'ext': '.flac', 'opts': '--best'}
}

class TranscodeException(Exception):
    pass

class TranscodeDownmixException(TranscodeException):
    pass

class UnknownSampleRateException(TranscodeException):
    pass
    
# In most Unix shells, pipelines only report the return code of the
# last process. We need to know if any process in the transcode
# pipeline fails, not just the last one.
#
# This function constructs a pipeline of processes from a chain of
# commands just like a shell does, but it returns the status code (and
# stderr) of every process in the pipeline, not just the last one. The
# results are returned as a list of (code, stderr) pairs, one pair per
# process.
def run_pipeline(cmds):
    # The Python executable (and its children) ignore SIGPIPE. (See
    # http://bugs.python.org/issue1652) Our subprocesses need to see
    # it.
    sigpipe_handler = signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    stdin = None
    last_proc = None
    procs = []
    try:
        for cmd in cmds:
            proc = subprocess.Popen(shlex.split(cmd), stdin=stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if last_proc:
                # Ensure last_proc receives SIGPIPE if proc exits first
                last_proc.stdout.close()
            procs.append(proc)
            stdin = proc.stdout
            last_proc = proc
    finally:
        signal.signal(signal.SIGPIPE, sigpipe_handler)

    last_stderr = last_proc.communicate()[1]

    results = []
    for (cmd, proc) in zip(cmds[:-1], procs[:-1]):
        # wait() is OK here, despite use of PIPE above; these procs
        # are finished.
        proc.wait()
        results.append((proc.returncode, proc.stderr.read()))
    results.append((last_proc.returncode, last_stderr))
    return results

def locate(root, match_function, ignore_dotfiles=True):
    '''
    Yields all filenames within the root directory for which match_function returns True.
    '''
    for path, dirs, files in os.walk(root):
        for filename in (os.path.abspath(os.path.join(path, filename)) for filename in files if match_function(filename)):
            if ignore_dotfiles and os.path.basename(filename).startswith('.'):
                pass
            else:
                yield filename

def ext_matcher(*extensions):
    '''
    Returns a function which checks if a filename has one of the specified extensions.
    '''
    return lambda f: os.path.splitext(f)[-1].lower() in extensions

def is_24bit(flac_dir):
    '''
    Returns True if any FLAC within flac_dir is 24 bit.
    '''
    flacs = (mutagen.flac.FLAC(flac_file) for flac_file in locate(flac_dir, ext_matcher('.flac')))
    return any(flac.info.bits_per_sample > 16 for flac in flacs)

def is_multichannel(flac_dir):
    '''
    Returns True if any FLAC within flac_dir is multichannel.
    '''
    flacs = (mutagen.flac.FLAC(flac_file) for flac_file in locate(flac_dir, ext_matcher('.flac')))
    return any(flac.info.channels > 2 for flac in flacs)

def needs_resampling(flac_dir):
    '''
    Returns True if any FLAC within flac_dir needs resampling when
    transcoded.
    '''
    return is_24bit(flac_dir)

def resample_rate(flac_dir):
    '''
    Returns the rate to which the release should be resampled.
    '''
    flacs = (mutagen.flac.FLAC(flac_file) for flac_file in locate(flac_dir, ext_matcher('.flac')))
    original_rate = max(flac.info.sample_rate for flac in flacs)
    if original_rate % 44100 == 0:
        return 44100
    elif original_rate % 48000 == 0:
        return 48000
    else:
        return None

def transcode_commands(output_format, resample, needed_sample_rate, flac_file, transcode_file):
    '''
    Return a list of transcode steps (one command per list element),
    which can be used to create a transcode pipeline for flac_file ->
    transcode_file using the specified output_format, plus any
    resampling, if needed.
    '''
    if resample:
        flac_decoder = 'sox %(FLAC)s -G -b 16 -t wav - rate -v -L %(SAMPLERATE)s dither'
    else:
        flac_decoder = 'flac -dcs -- %(FLAC)s'

    lame_encoder = 'lame -S %(OPTS)s - %(FILE)s'
    flac_encoder = 'flac %(OPTS)s -o %(FILE)s -'

    transcoding_steps = [flac_decoder]

    if encoders[output_format]['enc'] == 'lame':
        transcoding_steps.append(lame_encoder)
    elif encoders[output_format]['enc'] == 'flac':
        transcoding_steps.append(flac_encoder)

    transcode_args = {
        'FLAC' : pipes.quote(flac_file),
        'FILE' : pipes.quote(transcode_file),
        'OPTS' : encoders[output_format]['opts'],
        'SAMPLERATE' : needed_sample_rate,
    }

    if output_format == 'FLAC' and resample:
        commands = ['sox %(FLAC)s -G -b 16 %(FILE)s rate -v -L %(SAMPLERATE)s dither' % transcode_args]
    else:
        commands = map(lambda cmd: cmd % transcode_args, transcoding_steps)
    return commands

# Pool.map() can't pickle lambdas, so we need a helper function.
def pool_transcode((flac_file, output_dir, output_format)):
    return transcode(flac_file, output_dir, output_format)

def transcode(flac_file, output_dir, output_format):
    '''
    Transcodes a FLAC file into another format.
    '''
    # gather metadata from the flac file
    flac_info = mutagen.flac.FLAC(flac_file)
    sample_rate = flac_info.info.sample_rate
    bits_per_sample = flac_info.info.bits_per_sample
    resample = sample_rate > 48000 or bits_per_sample > 16

    # if resampling isn't needed then needed_sample_rate will not be used.
    needed_sample_rate = None

    if resample:
        if sample_rate % 44100 == 0:
            needed_sample_rate = '44100'
        elif sample_rate % 48000 == 0:
            needed_sample_rate = '48000'
        else:
            raise UnknownSampleRateException('FLAC file "{0}" has a sample rate {1}, which is not 88.2 , 176.4 or 96kHz but needs resampling, this is unsupported'.format(flac_file, sample_rate))

    if flac_info.info.channels > 2:
        raise TranscodeDownmixException('FLAC file "%s" has more than 2 channels, unsupported' % flac_file)

    # determine the new filename
    transcode_basename = os.path.splitext(os.path.basename(flac_file))[0]
    transcode_basename = re.sub(r'[\?<>\\*\|"]', '_', transcode_basename)
    transcode_file = os.path.join(output_dir, transcode_basename)
    transcode_file += encoders[output_format]['ext']

    if not os.path.exists(os.path.dirname(transcode_file)):
        try:
            os.makedirs(os.path.dirname(transcode_file))
        except OSError as e:
            if e.errno == errno.EEXIST:
                # Harmless race condition -- another transcode process
                # beat us here.
                pass
            else:
                raise e

    commands = transcode_commands(output_format, resample, needed_sample_rate, flac_file, transcode_file)
    results = run_pipeline(commands)

    # Check for problems. Because it's a pipeline, the earliest one is
    # usually the source. The exception is -SIGPIPE, which is caused
    # by "backpressure" due to a later command failing: ignore those
    # unless no other problem is found.
    last_sigpipe = None
    for (cmd, (code, stderr)) in zip(commands, results):
        if code:
            if code == -signal.SIGPIPE:
                last_sigpipe = (cmd, (code, stderr))
            else:
                raise TranscodeException('Transcode of file "%s" failed: %s' % (flac_file, stderr))
    if last_sigpipe:
        # XXX: this should probably never happen....
        raise TranscodeException('Transcode of file "%s" failed: SIGPIPE' % flac_file)

    tagging.copy_tags(flac_file, transcode_file)
    (ok, msg) = tagging.check_tags(transcode_file)
    if not ok:
        raise TranscodeException('Tag check failed on transcoded file: %s' % msg)

    return transcode_file

def get_transcode_dir(flac_dir, output_dir, output_format, resample):
    transcode_dir = os.path.basename(flac_dir)

    if 'FLAC' in flac_dir.upper():
        transcode_dir = re.sub(re.compile('FLAC', re.I), output_format, transcode_dir)
    else:
        transcode_dir = transcode_dir + " (" + output_format + ")"
        if output_format != 'FLAC':
            transcode_dir = re.sub(re.compile('FLAC', re.I), '', transcode_dir)
    if resample:
        if '24' in flac_dir and '96' in flac_dir:
            # XXX: theoretically, this could replace part of the album title too.
            # e.g. "24 days in 96 castles - [24-96]" would become "16 days in 44 castles - [16-44]"
            transcode_dir = transcode_dir.replace('24', '16')
            transcode_dir = transcode_dir.replace('96', '44')
        else:
            transcode_dir += " [16-44]"

    return os.path.join(output_dir, transcode_dir)

def transcode_release(flac_dir, output_dir, output_format, max_threads=None):
    '''
    Transcode a FLAC release into another format.
    '''
    flac_dir = os.path.abspath(flac_dir)
    output_dir = os.path.abspath(output_dir)
    flac_files = locate(flac_dir, ext_matcher('.flac'))

    # check if we need to resample
    resample = needs_resampling(flac_dir)

    # check if we need to encode
    if output_format == 'FLAC' and not resample:
        # XXX: if output_dir is not the same as flac_dir, this may not
        # do what the user expects.
        if output_dir != os.path.dirname(flac_dir):
            print "Warning: no encode necessary, so files won't be placed in", output_dir
        return flac_dir

    # make a new directory for the transcoded files
    #
    # NB: The cleanup code that follows this block assumes that
    # transcode_dir is a new directory created exclusively for this
    # transcode. Do not change this assumption without considering the
    # consequences!
    transcode_dir = get_transcode_dir(flac_dir, output_dir, output_format, resample)
    if not os.path.exists(transcode_dir):
        os.makedirs(transcode_dir)
    else:
        raise TranscodeException('transcode output directory "%s" already exists' % transcode_dir)

    # To ensure that a terminated pool subprocess terminates its
    # children, we make each pool subprocess a process group leader,
    # and handle SIGTERM by killing the process group. This will
    # ensure there are no lingering processes when a transcode fails
    # or is interrupted.
    def pool_initializer():
        os.setsid()
        def sigterm_handler(signum, frame):
            # We're about to SIGTERM the group, including us; ignore
            # it so we can finish this handler.
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            pgid = os.getpgid(0)
            os.killpg(pgid, signal.SIGTERM)
            sys.exit(-signal.SIGTERM)
        signal.signal(signal.SIGTERM, sigterm_handler)

    try:
        # create transcoding threads
        #
        # Use Pool.map() rather than Pool.apply_async() as it will raise
        # exceptions synchronously. (Don't want to waste any more time
        # when a transcode breaks.)
        #
        # XXX: actually, use Pool.map_async() and then get() the result
        # with a large timeout, as a workaround for a KeyboardInterrupt in
        # Pool.join(). c.f.,
        # http://stackoverflow.com/questions/1408356/keyboard-interrupts-with-pythons-multiprocessing-pool?rq=1
        pool = multiprocessing.Pool(max_threads, initializer=pool_initializer)
        try:
            result = pool.map_async(pool_transcode, [(filename, os.path.dirname(filename).replace(flac_dir, transcode_dir), output_format) for filename in flac_files])
            result.get(60 * 60 * 12)
            pool.close()
        except:
            pool.terminate()
            raise
        finally:
            pool.join()

        # copy other files
        allowed_extensions = ['.cue', '.gif', '.jpeg', '.jpg', '.log', '.md5', '.nfo', '.pdf', '.png', '.sfv', '.txt']
        allowed_files = locate(flac_dir, ext_matcher(*allowed_extensions))
        for filename in allowed_files:
            new_dir = os.path.dirname(filename).replace(flac_dir, transcode_dir)
            if not os.path.exists(new_dir):
                os.makedirs(new_dir)
            shutil.copy(filename, new_dir)

        return transcode_dir

    except:
        # Cleanup.
        #
        # ASSERT: transcode_dir was created by this function and does
        # not contain anything other than the transcoded files!
        shutil.rmtree(transcode_dir)
        raise

def make_torrent(input_dir, output_dir, tracker, passkey):
    torrent = os.path.join(output_dir, os.path.basename(input_dir)) + ".torrent"
    if not os.path.exists(os.path.dirname(torrent)):
        os.path.makedirs(os.path.dirname(torrent))
    tracker_url = '%(tracker)s%(passkey)s/announce' % {
        'tracker' : tracker,
        'passkey' : passkey,
    }
    command = ["mktorrent", "-p", "-a", tracker_url, "-o", torrent, input_dir]
    subprocess.check_output(command, stderr=subprocess.STDOUT)
    return torrent

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('input_dir')
    parser.add_argument('output_dir')
    parser.add_argument('output_format', choices=encoders.keys())
    parser.add_argument('-j', '--threads', default=multiprocessing.cpu_count(), type=int)
    args = parser.parse_args()

    transcode_release(os.path.expanduser(args.input_dir), os.path.expanduser(args.output_dir), args.output_format, args.threads)

if __name__ == "__main__": main()

########NEW FILE########
__FILENAME__ = whatapi
#!/usr/bin/env python
import re
import os
import json
import time
import requests
import mechanize
import HTMLParser
from cStringIO import StringIO

headers = {
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_3)'\
        'AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.79'\
        'Safari/535.11',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9'\
        ',*/*;q=0.8',
    'Accept-Encoding': 'gzip,deflate,sdch',
    'Accept-Language': 'en-US,en;q=0.8',
    'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3'}

# gazelle is picky about case in searches with &media=x
media_search_map = {
    'cd': 'CD',
    'dvd': 'DVD',
    'vinyl': 'Vinyl',
    'soundboard': 'Soundboard',
    'sacd': 'SACD',
    'dat': 'DAT',
    'web': 'WEB',
    'blu-ray': 'Blu-ray'
    }

lossless_media = set(media_search_map.keys())

formats = {
    'FLAC': {
        'format': 'FLAC',
        'encoding': 'Lossless'
    },
    'V0': {
        'format' : 'MP3',
        'encoding' : 'V0 (VBR)'
    },
    '320': {
        'format' : 'MP3',
        'encoding' : '320'
    },
    'V2': {
        'format' : 'MP3', 
        'encoding' : 'V2 (VBR)'
    },
}

def allowed_transcodes(torrent):
    """Some torrent types have transcoding restrictions."""
    preemphasis = re.search(r"""pre[- ]?emphasi(s(ed)?|zed)""", torrent['remasterTitle'], flags=re.IGNORECASE)
    if preemphasis:
        return []
    else:
        return formats.keys()

class LoginException(Exception):
    pass

class RequestException(Exception):
    pass

class WhatAPI:
    def __init__(self, username=None, password=None):
        self.session = requests.Session()
        self.session.headers.update(headers)
        self.username = username
        self.password = password
        self.authkey = None
        self.passkey = None
        self.userid = None
        self.tracker = "http://tracker.what.cd:34000/"
        self.last_request = time.time()
        self.rate_limit = 2.0 # seconds between requests
        self._login()

    def _login(self):
        '''Logs in user and gets authkey from server'''
        loginpage = 'https://what.cd/login.php'
        data = {'username': self.username,
                'password': self.password}
        r = self.session.post(loginpage, data=data)
        if r.status_code != 200:
            raise LoginException
        accountinfo = self.request('index')
        self.authkey = accountinfo['authkey']
        self.passkey = accountinfo['passkey']
        self.userid = accountinfo['id']

    def logout(self):
        self.session.get("https://what.cd/logout.php?auth=%s" % self.authkey)

    def request(self, action, **kwargs):
        '''Makes an AJAX request at a given action page'''
        while time.time() - self.last_request < self.rate_limit:
            time.sleep(0.1)

        ajaxpage = 'https://what.cd/ajax.php'
        params = {'action': action}
        if self.authkey:
            params['auth'] = self.authkey
        params.update(kwargs)
        r = self.session.get(ajaxpage, params=params, allow_redirects=False)
        self.last_request = time.time()
        try:
            parsed = json.loads(r.content)
            if parsed['status'] != 'success':
                raise RequestException
            return parsed['response']
        except ValueError:
            raise RequestException
    
    def get_artist(self, id=None, format='MP3', best_seeded=True):
        res = self.request('artist', id=id)
        torrentgroups = res['torrentgroup']
        keep_releases = []
        for release in torrentgroups:
            torrents = release['torrent']
            best_torrent = torrents[0]
            keeptorrents = []
            for t in torrents:
                if t['format'] == format:
                    if best_seeded:
                        if t['seeders'] > best_torrent['seeders']:
                            keeptorrents = [t]
                            best_torrent = t
                    else:
                        keeptorrents.append(t)
            release['torrent'] = list(keeptorrents)
            if len(release['torrent']):
                keep_releases.append(release)
        res['torrentgroup'] = keep_releases
        return res

    def snatched(self, skip=None, media=lossless_media):
        if not media.issubset(lossless_media):
            raise ValueError('Unsupported media type %s' % (media - lossless_media).pop())

        # gazelle doesn't currently support multiple values per query
        # parameter, so we have to search a media type at a time;
        # unless it's all types, in which case we simply don't specify
        # a 'media' parameter (defaults to all types).

        if media == lossless_media:
            media_params = ['']
        else:
            media_params = ['&media=%s' % media_search_map[m] for m in media]

        url = 'https://what.cd/torrents.php?type=snatched&userid=%s&format=FLAC' % self.userid
        for mp in media_params:
            page = 1
            done = False
            pattern = re.compile('torrents.php\?id=(\d+)&amp;torrentid=(\d+)')
            while not done:
                content = self.session.get(url + mp + "&page=%s" % page).text
                for groupid, torrentid in pattern.findall(content):
                    if skip is None or torrentid not in skip:
                        yield int(groupid), int(torrentid)
                done = 'Next &gt;' not in content
                page += 1

    def upload(self, group, torrent, new_torrent, format, description=[]):
        url = "https://what.cd/upload.php?groupid=%s" % group['group']['id']
        response = self.session.get(url)
        forms = mechanize.ParseFile(StringIO(response.text.encode('utf-8')), url)
        form = forms[-1]
        form.find_control('file_input').add_file(open(new_torrent), 'application/x-bittorrent', os.path.basename(new_torrent))
        if torrent['remastered']:
            form.find_control('remaster').set_single('1')
            form['remaster_year'] = str(torrent['remasterYear'])
            form['remaster_title'] = torrent['remasterTitle']
            form['remaster_record_label'] = torrent['remasterRecordLabel']
            form['remaster_catalogue_number'] = torrent['remasterCatalogueNumber']

        form.find_control('format').set('1', formats[format]['format'])
        form.find_control('bitrate').set('1', formats[format]['encoding'])
        form.find_control('media').set('1', torrent['media'])

        release_desc = '\n'.join(description)
        if release_desc:
            form['release_desc'] = release_desc

        _, data, headers = form.click_request_data()
        return self.session.post(url, data=data, headers=dict(headers))

    def set_24bit(self, torrent):
        url = "https://what.cd/torrents.php?action=edit&id=%s" % torrent['id']
        response = self.session.get(url)
        forms = mechanize.ParseFile(StringIO(response.text.encode('utf-8')), url)
        form = forms[-3]
        form.find_control('bitrate').set('1', '24bit Lossless')
        _, data, headers = form.click_request_data()
        return self.session.post(url, data=data, headers=dict(headers))

    def release_url(self, group, torrent):
        return "https://what.cd/torrents.php?id=%s&torrentid=%s#torrent%s" % (group['group']['id'], torrent['id'], torrent['id'])

    def permalink(self, torrent):
        return "https://what.cd/torrents.php?torrentid=%s" % torrent['id']

def unescape(text):
    return HTMLParser.HTMLParser().unescape(text)

########NEW FILE########
__FILENAME__ = _version
__version__ = "1.2"

########NEW FILE########
