__FILENAME__ = ARcalibrate
# -*- Mode: Python; test-case-name: morituri.test.test_header -*-
# vi:si:et:sw=4:sts=4:ts=4

# Morituri - for those about to RIP

# Copyright (C) 2009 Thomas Vander Stichele

# This file is part of morituri.
# 
# morituri is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# morituri is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with morituri.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import tempfile
import optparse

import gobject
gobject.threads_init()

from morituri.image import image
from morituri.common import task, checksum
from morituri.program import cdrdao, cdparanoia

"""
Find read offset by ripping a track from an AccurateRip CD.
"""

from morituri.common import log
log.init()

def gtkmain(runner, taskk):
    import gtk
    runner.connect('stop', lambda _: gtk.main_quit())

    window = gtk.Window()
    window.add(runner)
    window.show_all()

    runner.run(taskk)

    gtk.main()

def climain(runner, taskk):
    runner.run(taskk)


def arcs(runner, function, table, track, offset):
    # rips the track with the given offset, return the arcs checksum
    print 'ripping track %r with offset %d' % (track, offset)

    fd, path = tempfile.mkstemp(suffix='.track%02d.offset%d.morituri.wav' % (
        track, offset))
    os.close(fd)

    table.getTrackLength
    t = cdparanoia.ReadTrackTask(path, table, table.getTrackStart(track),
        table.getTrackEnd(track), offset)
    t.description = 'Ripping with offset %d' % offset
    function(runner, t)

    t = checksum.AccurateRipChecksumTask(path, trackNumber=track,
        trackCount=len(table.tracks))
    function(runner, t)
    
    os.unlink(path)
    return "%08x" % t.checksum
 
def main(argv):
    parser = optparse.OptionParser()

    default = 'cli'
    parser.add_option('-r', '--runner',
        action="store", dest="runner",
        help="runner ('cli' or 'gtk', defaults to %s)" % default,
        default=default)

    # see http://www.accuraterip.com/driveoffsets.htm
    default = "0, 6, 12, 48, 91, 97, 102, 108, 120, " + \
        "564, 594, 667, 685, 691, 704, 738, 1194, 1292, 1336, 1776, -582"
    parser.add_option('-o', '--offsets',
        action="store", dest="offsets",
        help="list of offsets, comma-separated, "
            "colon-separated for ranges (defaults to %s)" %
            default,
        default=default)

    options, args = parser.parse_args(argv[1:])

    offsets = []
    blocks = options.offsets.split(',')
    for b in blocks:
        if ':' in b:
            a, b = b.split(':')
            offsets.extend(range(int(a), int(b) + 1))
        else:
            offsets.append(int(b))

    # first get the Table Of Contents of the CD
    t = cdrdao.ReadTOCTask()

    if options.runner == 'cli':
        runner = task.SyncRunner()
        function = climain
    elif options.runner == 'gtk':
        from morituri.common import taskgtk
        runner = taskgtk.GtkProgressRunner()
        function = gtkmain

    function(runner, t)
    table = t.table

    print "CDDB disc id", table.getCDDBDiscId()
    url = table.getAccurateRipURL()
    print "AccurateRip URL", url

    # FIXME: download url as a task too
    responses = []
    import urllib2
    try:
        handle = urllib2.urlopen(url)
        data = handle.read()
        responses = image.getAccurateRipResponses(data)
    except urllib2.HTTPError, e:
        if e.code == 404:
            print 'Album not found in AccurateRip database'
            sys.exit(1)
        else:
            raise

    if responses:
        print '%d AccurateRip responses found' % len(responses)

        if responses[0].cddbDiscId != table.getCDDBDiscId():
            print "AccurateRip response discid different: %s" % \
                responses[0].cddbDiscId

    # now rip the first track at various offsets, calculating AccurateRip
    # CRC, and matching it against the retrieved ones
    
    def match(archecksum, track, responses):
        for i, r in enumerate(responses):
            if archecksum == r.checksums[track - 1]:
                return archecksum, i

        return None, None

    for offset in offsets:
        archecksum = arcs(runner, function, table, 1, offset)

        print 'AR checksum calculated: %s' % archecksum

        c, i = match(archecksum, 1, responses)
        if c:
            count = 1
            print 'MATCHED against response %d' % i
            print 'offset of device is likely', offset
            # now try and rip all other tracks as well
            for track in range(2, len(table.tracks) + 1):
                archecksum = arcs(runner, function, table, track, offset)
                c, i = match(archecksum, track, responses)
                if c:
                    print 'MATCHED track %d against response %d' % (track, i)
                    count += 1

            if count == len(table.tracks):
                print 'OFFSET of device is', offset
                return
            else:
                print 'not all tracks matched, continuing'
                
    print 'no matching offset found.'
                    
                


main(sys.argv)

########NEW FILE########
__FILENAME__ = ARcue
# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# Morituri - for those about to RIP

# Copyright (C) 2009 Thomas Vander Stichele

# This file is part of morituri.
# 
# morituri is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# morituri is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with morituri.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import optparse

import gobject
gobject.threads_init()
import gtk

from morituri.image import image
from morituri.common import task, taskgtk, checksum, log, accurip

def gtkmain(runner, taskk):
    runner.connect('stop', lambda _: gtk.main_quit())

    window = gtk.Window()
    window.add(runner)
    window.show_all()

    runner.run(taskk)

    gtk.main()

def climain(runner, taskk):
    runner.run(taskk)


def main(argv):
    log.init()

    parser = optparse.OptionParser()

    default = 'cli'
    parser.add_option('-r', '--runner',
        action="store", dest="runner",
        help="runner ('cli' or 'gtk', defaults to %s)" % default,
        default=default)

    options, args = parser.parse_args(argv[1:])

    path = 'test.cue'

    try:
        path = sys.argv[1]
    except IndexError:
        pass

    cueImage = image.Image(path)
    verifytask = image.ImageVerifyTask(cueImage)
    cuetask = image.AccurateRipChecksumTask(cueImage)

    if options.runner == 'cli':
        runner = task.SyncRunner()
        function = climain
    elif options.runner == 'gtk':
        runner = taskgtk.GtkProgressRunner()
        function = gtkmain

    cueImage.setup(runner)
    print
    print "CDDB disc id", cueImage.table.getCDDBDiscId()
    url = cueImage.table.getAccurateRipURL()
    print "AccurateRip URL", url

    # FIXME: download url as a task too
    responses = []
    import urllib2
    try:
        handle = urllib2.urlopen(url)
        data = handle.read()
        responses = accurip.getAccurateRipResponses(data)
    except urllib2.HTTPError, e:
        if e.code == 404:
            print 'Album not found in AccurateRip database'
        else:
            raise

    if responses:
        print '%d AccurateRip responses found' % len(responses)

        if responses[0].cddbDiscId != cueImage.table.getCDDBDiscId():
            print "AccurateRip response discid different: %s" % \
                responses[0].cddbDiscId

    function(runner, verifytask)
    function(runner, cuetask)

    response = None # track which response matches, for all tracks

    # loop over tracks
    for i, checksum in enumerate(cuetask.checksums):
        status = 'rip NOT accurate'

        confidence = None
        archecksum = None

        # match against each response's checksum
        for j, r in enumerate(responses):
            if "%08x" % checksum == r.checksums[i]:
                if not response:
                    response = r
                else:
                    assert r == response, \
                        "checksum %s for %d matches wrong response %d, "\
                        "checksum %s" % (
                            checksum, i + 1, j + 1, response.checksums[i])
                status = 'rip accurate    '
                archecksum = checksum
                confidence = response.confidences[i]

        c = "(not found)"
        ar = "(not in database)"
        if responses:
            if not response:
                print 'ERROR: none of the responses matched.'
            else:
                maxConfidence = max(r.confidences[i] for r in responses)
                     
                c = "(confidence %3d)" % maxConfidence
                if confidence is not None:
                    if confidence < maxConfidence:
                        c = "(confidence %3d of %3d)" % (confidence, maxConfidence)

                ar = ", AR [%s]" % response.checksums[i]
        print "Track %2d: %s %s [%08x]%s" % (
            i + 1, status, c, checksum, ar)


main(sys.argv)

########NEW FILE########
__FILENAME__ = encode
# -*- Mode: Python; test-case-name: morituri.test.test_header -*-
# vi:si:et:sw=4:sts=4:ts=4

# Morituri - for those about to RIP

# Copyright (C) 2009 Thomas Vander Stichele

# This file is part of morituri.
# 
# morituri is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# morituri is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with morituri.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import optparse
import tempfile
import pickle
import shutil

import gobject
gobject.threads_init()

import gst

import gtk


from morituri.common import task, taskgtk, common, encode

def gtkmain(runner, taskk):
    runner.connect('stop', lambda _: gtk.main_quit())

    window = gtk.Window()
    window.add(runner)
    window.show_all()

    runner.run(taskk)

    gtk.main()

def climain(runner, taskk):
    runner.run(taskk)

class Listener(object):
    def __init__(self, persister):
        self._persister = persister

    def progressed(self, task, value):
        pass

    def described(self, task, description):
        pass

    def started(self, task):
        pass

    def stopped(self, task):
        self._persister.object[task.path] = task.trm
        print task.path, task.trm
        self._persister.persist()


def main(argv):
    parser = optparse.OptionParser()

    default = 'cli'
    parser.add_option('-r', '--runner',
        action="store", dest="runner",
        help="runner ('cli' or 'gtk', defaults to %s)" % default,
        default=default)

    options, args = parser.parse_args(argv[1:])

    taglist = gst.TagList()
    taglist[gst.TAG_ARTIST] = 'Thomas'
    taglist[gst.TAG_TITLE] = 'Yes'
    taskk = encode.EncodeTask(args[0], args[1], taglist=taglist)

    if options.runner == 'cli':
        runner = task.SyncRunner()
        function = climain
    elif options.runner == 'gtk':
        runner = taskgtk.GtkProgressRunner()
        function = gtkmain

    function(runner, taskk)

main(sys.argv)

########NEW FILE########
__FILENAME__ = gtkchecksum
# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# Morituri - for those about to RIP

# Copyright (C) 2009 Thomas Vander Stichele

# This file is part of morituri.
# 
# morituri is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# morituri is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with morituri.  If not, see <http://www.gnu.org/licenses/>.

import sys

import gobject
gobject.threads_init()

import gtk

from morituri.common import task, checksum, taskgtk

def main(path, start, end):
    progress = taskgtk.GtkProgressRunner()
    progress.connect('stop', lambda _: gtk.main_quit())

    window = gtk.Window()
    window.add(progress)
    window.show_all()

    checksumtask = checksum.CRC32Task(path, start, end)
    progress.run(checksumtask)

    gtk.main()

    print "CRC: %08X" % checksumtask.checksum

path = 'test.flac'

start = 0
end = -1
try:
    path = unicode(sys.argv[1])
    start = int(sys.argv[2])
    end = int(sys.argv[3])
except IndexError:
    pass

main(path, start, end)

########NEW FILE########
__FILENAME__ = movecue
# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# Morituri - for those about to RIP

# Copyright (C) 2009 Thomas Vander Stichele

# This file is part of morituri.
# 
# morituri is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# morituri is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with morituri.  If not, see <http://www.gnu.org/licenses/>.

# EAC by default saves .cue files one directory up from the rip directories,
# and only uses the title for the file name.
# Move the .cue file into the corresponding directory, and rename it

import os
import sys

from morituri.image import cue

def move(path):
    print 'reading', path
    cuefile = cue.CueFile(path)
    cuefile.parse()

    track = cuefile.tracks[0]
    idx, file = track.getIndex(1)
    destdir = os.path.dirname(cuefile.getRealPath(file.path))

    if os.path.exists(destdir):
        dirname = os.path.basename(destdir)
        destination = os.path.join(destdir, dirname + '.cue')
        print 'moving %s to %s' % (path, destination)
        os.rename(path, destination)

for path in sys.argv[1:]:
    move(path)

########NEW FILE########
__FILENAME__ = readcue
# -*- Mode: Python; test-case-name: morituri.test.test_header -*-
# vi:si:et:sw=4:sts=4:ts=4

# Morituri - for those about to RIP

# Copyright (C) 2009 Thomas Vander Stichele

# This file is part of morituri.
# 
# morituri is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# morituri is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with morituri.  If not, see <http://www.gnu.org/licenses/>.

import sys

from morituri.image import cue

def main(path):
    cuefile = cue.CueFile(path)
    cuefile.parse()

    print cuefile.tracks

path = 'test.cue'

try:
    path = sys.argv[1]
except IndexError:
    pass

main(path)

########NEW FILE########
__FILENAME__ = readdisc
# -*- Mode: Python; test-case-name: morituri.test.test_header -*-
# vi:si:et:sw=4:sts=4:ts=4

# Morituri - for those about to RIP

# Copyright (C) 2009 Thomas Vander Stichele

# This file is part of morituri.
# 
# morituri is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# morituri is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with morituri.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import tempfile
import optparse
import pickle
import shutil

import gobject
gobject.threads_init()

from morituri.common import common, task, checksum
from morituri.image import image, cue, table
from morituri.program import cdrdao, cdparanoia

"""
Rip a disc.
"""

from morituri.common import log
log.init()

def gtkmain(runner, taskk):
    import gtk
    runner.connect('stop', lambda _: gtk.main_quit())

    window = gtk.Window()
    window.add(runner)
    window.show_all()

    runner.run(taskk)

    gtk.main()
    window.remove(runner)
    window.hide()

def climain(runner, taskk):
    runner.run(taskk)

class TrackMetadata(object):
    artist = None
    title = None

class DiscMetadata(object):
    artist = None
    title = None
    various = False
    tracks = None

    def __init__(self):
        self.tracks = []

def filterForPath(text):
    return "-".join(text.split("/"))

def musicbrainz(discid):
    metadata = DiscMetadata()

    import musicbrainz2.disc as mbdisc
    import musicbrainz2.webservice as mbws


    # Setup a Query object.
    service = mbws.WebService()
    query = mbws.Query(service)


    # Query for all discs matching the given DiscID.
    try:
        filter = mbws.ReleaseFilter(discId=discid)
        results = query.getReleases(filter)
    except mbws.WebServiceError, e:
        print "Error:", e
        return


    # No disc matching this DiscID has been found.
    if len(results) == 0:
        print "Disc is not yet in the MusicBrainz database."
        print "Consider adding it."
        return


    # Display the returned results to the user.
    print 'Matching releases:'

    for result in results:
        release = result.release
        print 'Artist  :', release.artist.name
        print 'Title   :', release.title
        print


    # Select one of the returned releases. We just pick the first one.
    selectedRelease = results[0].release


    # The returned release object only contains title and artist, but no tracks.
    # Query the web service once again to get all data we need.
    try:
        inc = mbws.ReleaseIncludes(artist=True, tracks=True, releaseEvents=True)
        release = query.getReleaseById(selectedRelease.getId(), inc)
    except mbws.WebServiceError, e:
        print "Error:", e
        sys.exit(2)


    isSingleArtist = release.isSingleArtistRelease()
    metadata.various = not isSingleArtist
    metadata.title = release.title
    metadata.artist = release.artist.getUniqueName()

    print "%s - %s" % (release.artist.getUniqueName(), release.title)

    i = 1
    for t in release.tracks:
        track = TrackMetadata()
        if isSingleArtist:
            track.artist = metadata.artist
            track.title = t.title
        else:
            track.artist = t.artist.name
            track.title = t.title
        metadata.tracks.append(track)

    return metadata

def getPath(template, metadata, i):
    # returns without extension

    v = {}

    v['t'] = '%02d' % (i + 1)

    # default values
    v['A'] = 'Unknown Artist'
    v['d'] = 'Unknown Disc'

    v['a'] = v['A']
    v['n'] = 'Unknown Track'

    if metadata:
        v['A'] = filterForPath(metadata.artist)
        v['d'] = filterForPath(metadata.title)
        if i >= 0:
            v['a'] = filterForPath(metadata.tracks[i].artist)
            v['n'] = filterForPath(metadata.tracks[i].title)
        else:
            # htoa defaults to disc's artist
            v['a'] = filterForPath(metadata.artist)
            v['n'] = filterForPath('Hidden Track One Audio')

    import re
    template = re.sub(r'%(\w)', r'%(\1)s', template)

    return template % v

def main(argv):
    parser = optparse.OptionParser()

    default = 'cli'
    parser.add_option('-r', '--runner',
        action="store", dest="runner",
        help="runner ('cli' or 'gtk', defaults to %s)" % default,
        default=default)
    default = 0
    parser.add_option('-o', '--offset',
        action="store", dest="offset",
        help="sample offset (defaults to %d)" % default,
        default=default)
    parser.add_option('-t', '--table-pickle',
        action="store", dest="table_pickle",
        help="pickle to use for reading and writing the table",
        default=default)
    parser.add_option('-T', '--toc-pickle',
        action="store", dest="toc_pickle",
        help="pickle to use for reading and writing the TOC",
        default=default)
    default = '%A - %d/%t. %a - %n'
    parser.add_option('', '--track-template',
        action="store", dest="track_template",
        help="template for track file naming (default %s)" % default,
        default=default)
    default = '%A - %d/%A - %d'
    parser.add_option('', '--disc-template',
        action="store", dest="disc_template",
        help="template for disc file naming (default %s)" % default,
        default=default)


    options, args = parser.parse_args(argv[1:])

    if options.runner == 'cli':
        runner = task.SyncRunner()
        function = climain
    elif options.runner == 'gtk':
        from morituri.common import taskgtk
        runner = taskgtk.GtkProgressRunner()
        function = gtkmain

    # first, read the normal TOC, which is fast
    ptoc = common.Persister(options.toc_pickle or None)
    if not ptoc.object:
        t = cdrdao.ReadTOCTask()
        function(runner, t)
        ptoc.persist(t.table)
    ittoc = ptoc.object
    assert ittoc.hasTOC()

    # already show us some info based on this
    print "CDDB disc id", ittoc.getCDDBDiscId()
    metadata = musicbrainz(ittoc.getMusicBrainzDiscId())

    # now, read the complete index table, which is slower
    ptable = common.Persister(options.table_pickle or None)
    if not ptable.object:
        t = cdrdao.ReadTableTask()
        function(runner, t)
        ptable.persist(t.table)
    itable = ptable.object

    assert itable.hasTOC()

    assert itable.getCDDBDiscId() == ittoc.getCDDBDiscId(), \
        "full table's id %s differs from toc id %s" % (
            itable.getCDDBDiscId(), ittoc.getCDDBDiscId())
    assert itable.getMusicBrainzDiscId() == ittoc.getMusicBrainzDiscId()

    lastTrackStart = 0

    # check for hidden track one audio
    htoapath = None
    index = None
    track = itable.tracks[0]
    try:
        index = track.getIndex(0)
    except KeyError:
        pass

    if index:
        start = index.absolute
        stop = track.getIndex(1).absolute
        print 'Found Hidden Track One Audio from frame %d to %d' % (start, stop)
            
        # rip it
        htoapath = getPath(options.track_template, metadata, -1) + '.wav'
        htoalength = stop - start
        if not os.path.exists(htoapath):
            print 'Ripping track %d: %s' % (0, os.path.basename(htoapath))
            t = cdparanoia.ReadVerifyTrackTask(htoapath, ittoc,
                start, stop - 1,
                offset=int(options.offset))
            function(runner, t)
            if t.checksum:
                print 'Checksums match for track %d' % 0
            else:
                print 'ERROR: checksums did not match for track %d' % 0
            # overlay this rip onto the Table
        itable.setFile(1, 0, htoapath, htoalength, 0)


    for i, track in enumerate(itable.tracks):
        path = getPath(options.track_template, metadata, i) + '.wav'
        dirname = os.path.dirname(path)
        if not os.path.exists(dirname):
            os.makedirs(dirname)

        # FIXME: optionally allow overriding reripping
        if not os.path.exists(path):
            print 'Ripping track %d: %s' % (i + 1, os.path.basename(path))
            t = cdparanoia.ReadVerifyTrackTask(path, ittoc,
                ittoc.getTrackStart(i + 1),
                ittoc.getTrackEnd(i + 1),
                offset=int(options.offset))
            t.description = 'Reading Track %d' % (i + 1)
            function(runner, t)
            if t.checksum:
                print 'Checksums match for track %d' % (i + 1)
            else:
                print 'ERROR: checksums did not match for track %d' % (i + 1)

        # overlay this rip onto the Table
        itable.setFile(i + 1, 1, path, ittoc.getTrackLength(i + 1), i + 1)


    ### write disc files
    discName = getPath(options.disc_template, metadata, i)
    dirname = os.path.dirname(discName)
    if not os.path.exists(dirname):
        os.makedirs(dirname)

    # write .cue file
    cuePath = '%s.cue' % discName
    handle = open(cuePath, 'w')
    handle.write(itable.cue())
    handle.close()

    # write .m3u file
    m3uPath = '%s.m3u' % discName
    handle = open(m3uPath, 'w')
    handle.write('#EXTM3U\n')
    if htoapath:
        handle.write('#EXTINF:%d,%s\n' % (
            htoalength / common.FRAMES_PER_SECOND,
                os.path.basename(htoapath[:-4])))
        handle.write('%s\n' % os.path.basename(htoapath))

    for i, track in enumerate(itable.tracks):
        path = getPath(options.track_template, metadata, i) + '.wav'
        handle.write('#EXTINF:%d,%s\n' % (
            itable.getTrackLength(i + 1) / common.FRAMES_PER_SECOND,
            os.path.basename(path)))
        handle.write('%s\n' % os.path.basename(path))
    handle.close()

    # verify using accuraterip
    print "CDDB disc id", itable.getCDDBDiscId()
    print "MusicBrainz disc id", itable.getMusicBrainzDiscId()
    url = itable.getAccurateRipURL()
    print "AccurateRip URL", url

    # FIXME: download url as a task too
    responses = []
    import urllib2
    try:
        handle = urllib2.urlopen(url)
        data = handle.read()
        responses = image.getAccurateRipResponses(data)
    except urllib2.HTTPError, e:
        if e.code == 404:
            print 'Album not found in AccurateRip database'
        else:
            raise

    if responses:
        print '%d AccurateRip responses found' % len(responses)

        if responses[0].cddbDiscId != itable.getCDDBDiscId():
            print "AccurateRip response discid different: %s" % \
                responses[0].cddbDiscId

       
    # FIXME: put accuraterip verification into a separate task/function
    # and apply here
    cueImage = image.Image(cuePath)
    verifytask = image.ImageVerifyTask(cueImage)
    cuetask = image.AccurateRipChecksumTask(cueImage)
    function(runner, verifytask)
    function(runner, cuetask)

    response = None # track which response matches, for all tracks

    # loop over tracks
    for i, sum in enumerate(cuetask.checksums):
        status = 'rip NOT accurate'

        confidence = None
        arsum = None

        # match against each response's checksum
        for j, r in enumerate(responses):
            if "%08x" % sum == r.checksums[i]:
                if not response:
                    response = r
                else:
                    assert r == response, \
                        "checksum %s for %d matches wrong response %d, "\
                        "checksum %s" % (
                            sum, i + 1, j + 1, response.checksums[i])
                status = 'rip accurate    '
                arsum = sum
                confidence = response.confidences[i]

        c = "(not found)"
        ar = "(not in database)"
        if responses:
            if not response:
                print 'ERROR: none of the responses matched.'
            else:
                maxConfidence = max(r.confidences[i] for r in responses)
                     
                c = "(max confidence %3d)" % maxConfidence
                if confidence is not None:
                    if confidence < maxConfidence:
                        c = "(confidence %3d of %3d)" % (confidence, maxConfidence)

                ar = ", AR [%s]" % response.checksums[i]
        print "Track %2d: %s %s [%08x]%s" % (
            i + 1, status, c, sum, ar)




main(sys.argv)

########NEW FILE########
__FILENAME__ = readhtoa
# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

import os
import sys
import optparse
import tempfile
import shutil

from morituri.common import task, checksum, log
from morituri.program import cdrdao, cdparanoia

import gobject
gobject.threads_init()

def main():
    log.init()

    parser = optparse.OptionParser()

    default = 0
    parser.add_option('-o', '--offset',
        action="store", dest="offset",
        help="sample offset (defaults to %d)" % default,
        default=default)

    options, args = parser.parse_args(sys.argv[1:])

    runner = task.SyncRunner()

    # first do a simple TOC scan
    t = cdrdao.ReadTOCTask()
    runner.run(t)
    toc = t.table

    offset = t.table.tracks[0].getIndex(1).absolute

    if offset < 150:
        print 'Disc is unlikely to have Hidden Track One Audio.'
    else:
        print 'Disc seems to have a %d frame HTOA.' % offset


    # now do a more extensive scan
    t = cdrdao.ReadTableTask()
    runner.run(t)

    # now check if we have a hidden track one audio
    track = t.table.tracks[0]
    try:
        index = track.getIndex(0)
    except KeyError:
        print 'No Hidden Track One Audio found.'
        return

    start = index.absolute
    stop = track.getIndex(1).absolute
    print 'Found Hidden Track One Audio from frame %d to %d' % (start, stop)
        
    # rip it
    riptask = cdparanoia.ReadVerifyTrackTask('track00.wav', t.table,
        start, stop - 1,
        offset=int(options.offset))
    runner.run(riptask)

    print 'runner done'

    if riptask.checksum is not None:
        print 'Checksums match'
    else:
        print 'Checksums did not match'

main()

########NEW FILE########
__FILENAME__ = readtoc
# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

from morituri.common import task, log
from morituri.program import cdrdao

def main():
    log.init()
    runner = task.SyncRunner()
    t = cdrdao.ReadTableTask()
    runner.run(t)
    print 'runner done', t.toc

    if not t.table:
        print 'Failed to read TOC'
        return

    for track in t.table.tracks:
        print track.getIndex(1).absolute

main()

########NEW FILE########
__FILENAME__ = readtrack
# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

import re
import os
import sys
import stat
import subprocess
import tempfile

from morituri.common import task, checksum, log
from morituri.image import table
from morituri.program import cdparanoia

import gobject
gobject.threads_init()

def main():
    log.init()

    
    runner = task.SyncRunner()

    checksums = []
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        fd, path = tempfile.mkstemp(suffix='.morituri.wav')
        os.close(fd)
        print 'storing track to %s' % path

    fakeTable = table.Table([
        table.Track( 1,      0,  15536),
    ])

    t = cdparanoia.ReadVerifyTrackTask(path, fakeTable, 1000, 3000, offset=0)


    runner.run(t)

    print 'runner done'

    if t.checksum is not None:
        print 'Checksums match'
    else:
        print 'Checksums do not match'


main()

########NEW FILE########
__FILENAME__ = trm
# -*- Mode: Python; test-case-name: morituri.test.test_header -*-
# vi:si:et:sw=4:sts=4:ts=4

# Morituri - for those about to RIP

# Copyright (C) 2009 Thomas Vander Stichele

# This file is part of morituri.
# 
# morituri is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# morituri is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with morituri.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import optparse
import tempfile
import pickle
import shutil

import gobject
gobject.threads_init()
import gtk

from morituri.common import checksum, task, taskgtk, common

def gtkmain(runner, taskk):
    runner.connect('stop', lambda _: gtk.main_quit())

    window = gtk.Window()
    window.add(runner)
    window.show_all()

    runner.run(taskk)

    gtk.main()

def climain(runner, taskk):
    runner.run(taskk)

class Listener(object):
    def __init__(self, persister):
        self._persister = persister

    def progressed(self, task, value):
        pass

    def described(self, task, description):
        pass

    def started(self, task):
        pass

    def stopped(self, task):
        self._persister.object[task.path] = task.trm
        print task.path, task.trm
        self._persister.persist()


def main(argv):
    parser = optparse.OptionParser()

    default = 'cli'
    parser.add_option('-r', '--runner',
        action="store", dest="runner",
        help="runner ('cli' or 'gtk', defaults to %s)" % default,
        default=default)
    parser.add_option('-p', '--playlist',
        action="store", dest="playlist",
        help="playlist to analyze files from")
    parser.add_option('-P', '--pickle',
        action="store", dest="pickle",
        help="pickle to store trms to")


    options, args = parser.parse_args(argv[1:])

    paths = []
    if len(args) > 0:
        paths.extend(args[0:])
    if options.playlist:
        paths.extend(open(options.playlist).readlines())

    mtask = task.MultiCombinedTask()
    listener = None

    ptrms = common.Persister(options.pickle or None, {})
    if options.pickle:
        listener = Listener(ptrms)
        print 'Using pickle %s' % options.pickle
    trms = ptrms.object

    for path in paths:
        path = path.rstrip()
        if path in trms.keys():
            continue
        trmtask = checksum.TRMTask(path)
        if listener:
            trmtask.addListener(listener)
        mtask.addTask(trmtask)
    mtask.description = 'Fingerprinting files'


    if options.runner == 'cli':
        runner = task.SyncRunner()
        function = climain
    elif options.runner == 'gtk':
        runner = taskgtk.GtkProgressRunner()
        function = gtkmain

    function(runner, mtask)

    print
    for trmtask in mtask.tasks:
        print trmtask.trm

main(sys.argv)

########NEW FILE########
__FILENAME__ = header
# -*- Mode: Python; test-case-name: morituri.test.test_header -*-
# vi:si:et:sw=4:sts=4:ts=4

# Morituri - for those about to RIP

# Copyright (C) 2009 Thomas Vander Stichele

# This file is part of morituri.
# 
# morituri is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# morituri is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with morituri.  If not, see <http://www.gnu.org/licenses/>.

########NEW FILE########
__FILENAME__ = offsets
# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# show all possible offsets, in order of popularity, from a download of
# http://www.accuraterip.com/driveoffsets.htm

import sys

import BeautifulSoup

handle = open(sys.argv[1])

doc = handle.read()

soup = BeautifulSoup.BeautifulSoup(doc)

offsets = {} # offset -> total count

rows = soup.findAll('tr')
for row in rows:
    columns = row.findAll('td')
    if len(columns) == 4:
        first, second, third, fourth = columns
        name = first.find(text=True)
        offset = second.find(text=True)
        count = third.find(text=True)

        # only use sensible offsets
        try:
            int(offset)
        except:
            continue

        if offset not in offsets.keys():
            offsets[offset] = 0
        # first line is text, so int will fail with ValueError
        # purged entries will have None as count, so TypeError
        try:
            offsets[offset] += int(count)
        except (ValueError, TypeError):
            pass

# now sort offsets by count
counts = []
for offset, count in offsets.items():
    counts.append((count, offset))

counts.sort()
counts.reverse()

offsets = []
for count, offset in counts:
    offsets.append(offset)

# now format it for code inclusion
lines = []
line = 'OFFSETS = "'

for offset in offsets:
    line += offset + ", "
    if len(line) > 60:
        line += "\" + \\"
        lines.append(line)
        line = '          "'

# get last line too, trimming the comma and adding the quote
if len(line) > 11:
    line = line[:-2] + '"'
    lines.append(line)

print "\n".join(lines)

########NEW FILE########
__FILENAME__ = pep8
#!/usr/bin/python
# pep8.py - Check Python source code formatting, according to PEP 8
# Copyright (C) 2006 Johann C. Rocholl <johann@browsershots.org>
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

"""
Check Python source code formatting, according to PEP 8:
http://www.python.org/dev/peps/pep-0008/

For usage and a list of options, try this:
$ python pep8.py -h

This program and its regression test suite live here:
http://svn.browsershots.org/trunk/devtools/pep8/
http://trac.browsershots.org/browser/trunk/devtools/pep8/

Groups of errors and warnings:
E errors
W warnings
100 indentation
200 whitespace
300 blank lines
400 imports
500 line length
600 deprecation
700 statements

You can add checks to this program by writing plugins. Each plugin is
a simple function that is called for each line of source code, either
physical or logical.

Physical line:
- Raw line of text from the input file.

Logical line:
- Multi-line statements converted to a single line.
- Stripped left and right.
- Contents of strings replaced with 'xxx' of same length.
- Comments removed.

The check function requests physical or logical lines by the name of
the first argument:

def maximum_line_length(physical_line)
def extraneous_whitespace(logical_line)
def blank_lines(logical_line, blank_lines, indent_level, line_number)

The last example above demonstrates how check plugins can request
additional information with extra arguments. All attributes of the
Checker object are available. Some examples:

lines: a list of the raw lines from the input file
tokens: the tokens that contribute to this logical line
line_number: line number in the input file
blank_lines: blank lines before this one
indent_char: first indentation character in this file (' ' or '\t')
indent_level: indentation (with tabs expanded to multiples of 8)
previous_indent_level: indentation on previous line
previous_logical: previous logical line

The docstring of each check function shall be the relevant part of
text from PEP 8. It is printed if the user enables --show-pep8.

"""

import os
import sys
import re
import time
import inspect
import tokenize
from optparse import OptionParser
from keyword import iskeyword
from fnmatch import fnmatch

__version__ = '0.2.0'
__revision__ = '$Rev$'

default_exclude = '.svn,CVS,*.pyc,*.pyo'

indent_match = re.compile(r'([ \t]*)').match
raise_comma_match = re.compile(r'raise\s+\w+\s*(,)').match

operators = """
+  -  *  /  %  ^  &  |  =  <  >  >>  <<
+= -= *= /= %= ^= &= |= == <= >= >>= <<=
!= <> :
in is or not and
""".split()

options = None
args = None


##############################################################################
# Plugins (check functions) for physical lines
##############################################################################


def tabs_or_spaces(physical_line, indent_char):
    """
    Never mix tabs and spaces.

    The most popular way of indenting Python is with spaces only.  The
    second-most popular way is with tabs only.  Code indented with a mixture
    of tabs and spaces should be converted to using spaces exclusively.  When
    invoking the Python command line interpreter with the -t option, it issues
    warnings about code that illegally mixes tabs and spaces.  When using -tt
    these warnings become errors.  These options are highly recommended!
    """
    indent = indent_match(physical_line).group(1)
    for offset, char in enumerate(indent):
        if char != indent_char:
            return offset, "E101 indentation contains mixed spaces and tabs"


def tabs_obsolete(physical_line):
    """
    For new projects, spaces-only are strongly recommended over tabs.  Most
    editors have features that make this easy to do.
    """
    indent = indent_match(physical_line).group(1)
    if indent.count('\t'):
        return indent.index('\t'), "W191 indentation contains tabs"


def trailing_whitespace(physical_line):
    """
    JCR: Trailing whitespace is superfluous.
    """
    physical_line = physical_line.rstrip('\n') # chr(10), newline
    physical_line = physical_line.rstrip('\r') # chr(13), carriage return
    physical_line = physical_line.rstrip('\x0c') # chr(12), form feed, ^L
    stripped = physical_line.rstrip()
    if physical_line != stripped:
        return len(stripped), "W291 trailing whitespace"


def trailing_blank_lines(physical_line, lines, line_number):
    """
    JCR: Trailing blank lines are superfluous.
    """
    if physical_line.strip() == '' and line_number == len(lines):
        return 0, "W391 blank line at end of file"


def missing_newline(physical_line):
    """
    JCR: The last line should have a newline.
    """
    if physical_line.rstrip() == physical_line:
        return len(physical_line), "W292 no newline at end of file"


def maximum_line_length(physical_line):
    """
    Limit all lines to a maximum of 79 characters.

    There are still many devices around that are limited to 80 character
    lines; plus, limiting windows to 80 characters makes it possible to have
    several windows side-by-side.  The default wrapping on such devices looks
    ugly.  Therefore, please limit all lines to a maximum of 79 characters.
    For flowing long blocks of text (docstrings or comments), limiting the
    length to 72 characters is recommended.
    """
    length = len(physical_line.rstrip())
    if length > 79:
        return 79, "E501 line too long (%d characters)" % length


##############################################################################
# Plugins (check functions) for logical lines
##############################################################################


def blank_lines(logical_line, blank_lines, indent_level, line_number,
                previous_logical):
    """
    Separate top-level function and class definitions with two blank lines.

    Method definitions inside a class are separated by a single blank line.

    Extra blank lines may be used (sparingly) to separate groups of related
    functions.  Blank lines may be omitted between a bunch of related
    one-liners (e.g. a set of dummy implementations).

    Use blank lines in functions, sparingly, to indicate logical sections.
    """
    if line_number == 1:
        return # Don't expect blank lines before the first line
    if previous_logical.startswith('@'):
        return # Don't expect blank lines after function decorator
    if (logical_line.startswith('def ') or
        logical_line.startswith('class ') or
        logical_line.startswith('@')):
        if indent_level > 0 and blank_lines != 1:
            return 0, "E301 expected 1 blank line, found %d" % blank_lines
        if indent_level == 0 and blank_lines != 2:
            return 0, "E302 expected 2 blank lines, found %d" % blank_lines
    if blank_lines > 2:
        return 0, "E303 too many blank lines (%d)" % blank_lines


def extraneous_whitespace(logical_line):
    """
    Avoid extraneous whitespace in the following situations:

    - Immediately inside parentheses, brackets or braces.

    - Immediately before a comma, semicolon, or colon.
    """
    line = logical_line
    for char in '([{':
        found = line.find(char + ' ')
        if found > -1:
            return found + 1, "E201 whitespace after '%s'" % char
    for char in '}])':
        found = line.find(' ' + char)
        if found > -1 and line[found - 1] != ',':
            return found, "E202 whitespace before '%s'" % char
    for char in ',;:':
        found = line.find(' ' + char)
        if found > -1:
            return found, "E203 whitespace before '%s'" % char


def missing_whitespace(logical_line):
    """
    JCR: Each comma, semicolon or colon should be followed by whitespace.
    """
    line = logical_line
    for index in range(len(line) - 1):
        char = line[index]
        if char in ',;:' and line[index + 1] != ' ':
            before = line[:index]
            if char == ':' and before.count('[') > before.count(']'):
                continue # Slice syntax, no space required
            return index, "E231 missing whitespace after '%s'" % char


def indentation(logical_line, previous_logical, indent_char,
                indent_level, previous_indent_level):
    """
    Use 4 spaces per indentation level.

    For really old code that you don't want to mess up, you can continue to
    use 8-space tabs.
    """
    if indent_char == ' ' and indent_level % 4:
        return 0, "E111 indentation is not a multiple of four"
    indent_expect = previous_logical.endswith(':')
    if indent_expect and indent_level <= previous_indent_level:
        return 0, "E112 expected an indented block"
    if indent_level > previous_indent_level and not indent_expect:
        return 0, "E113 unexpected indentation"


def whitespace_before_parameters(logical_line, tokens):
    """
    Avoid extraneous whitespace in the following situations:

    - Immediately before the open parenthesis that starts the argument
      list of a function call.

    - Immediately before the open parenthesis that starts an indexing or
      slicing.
    """
    prev_type = tokens[0][0]
    prev_text = tokens[0][1]
    prev_end = tokens[0][3]
    for index in range(1, len(tokens)):
        token_type, text, start, end, line = tokens[index]
        if (token_type == tokenize.OP and
            text in '([' and
            start != prev_end and
            prev_type == tokenize.NAME and
            (index < 2 or tokens[index - 2][1] != 'class') and
            (not iskeyword(prev_text))):
            return prev_end, "E211 whitespace before '%s'" % text
        prev_type = token_type
        prev_text = text
        prev_end = end


def whitespace_around_operator(logical_line):
    """
    Avoid extraneous whitespace in the following situations:

    - More than one space around an assignment (or other) operator to
      align it with another.
    """
    line = logical_line
    for operator in operators:
        found = line.find('  ' + operator)
        if found > -1:
            return found, "E221 multiple spaces before operator"
        found = line.find(operator + '  ')
        if found > -1:
            return found, "E222 multiple spaces after operator"
        found = line.find('\t' + operator)
        if found > -1:
            return found, "E223 tab before operator"
        found = line.find(operator + '\t')
        if found > -1:
            return found, "E224 tab after operator"


def whitespace_around_comma(logical_line):
    """
    Avoid extraneous whitespace in the following situations:

    - More than one space around an assignment (or other) operator to
      align it with another.

    JCR: This should also be applied around comma etc.
    """
    line = logical_line
    for separator in ',;:':
        found = line.find(separator + '  ')
        if found > -1:
            return found + 1, "E241 multiple spaces after '%s'" % separator
        found = line.find(separator + '\t')
        if found > -1:
            return found + 1, "E242 tab after '%s'" % separator


def imports_on_separate_lines(logical_line):
    """
    Imports should usually be on separate lines.
    """
    line = logical_line
    if line.startswith('import '):
        found = line.find(',')
        if found > -1:
            return found, "E401 multiple imports on one line"


def compound_statements(logical_line):
    """
    Compound statements (multiple statements on the same line) are
    generally discouraged.
    """
    line = logical_line
    found = line.find(':')
    if -1 < found < len(line) - 1:
        before = line[:found]
        if (before.count('{') <= before.count('}') and # {'a': 1} (dict)
            before.count('[') <= before.count(']') and # [1:2] (slice)
            not re.search(r'\blambda\b', before)):     # lambda x: x
            return found, "E701 multiple statements on one line (colon)"
    found = line.find(';')
    if -1 < found:
        return found, "E702 multiple statements on one line (semicolon)"


def python_3000_has_key(logical_line):
    """
    The {}.has_key() method will be removed in the future version of
    Python. Use the 'in' operation instead, like:
    d = {"a": 1, "b": 2}
    if "b" in d:
        print d["b"]
    """
    pos = logical_line.find('.has_key(')
    if pos > -1:
        return pos, "W601 .has_key() is deprecated, use 'in'"


def python_3000_raise_comma(logical_line):
    """
    When raising an exception, use "raise ValueError('message')"
    instead of the older form "raise ValueError, 'message'".

    The paren-using form is preferred because when the exception arguments
    are long or include string formatting, you don't need to use line
    continuation characters thanks to the containing parentheses.  The older
    form will be removed in Python 3000.
    """
    match = raise_comma_match(logical_line)
    if match:
        return match.start(1), "W602 deprecated form of raising exception"


##############################################################################
# Helper functions
##############################################################################


def expand_indent(line):
    """
    Return the amount of indentation.
    Tabs are expanded to the next multiple of 8.

    >>> expand_indent('    ')
    4
    >>> expand_indent('\\t')
    8
    >>> expand_indent('    \\t')
    8
    >>> expand_indent('       \\t')
    8
    >>> expand_indent('        \\t')
    16
    """
    result = 0
    for char in line:
        if char == '\t':
            result = result / 8 * 8 + 8
        elif char == ' ':
            result += 1
        else:
            break
    return result


##############################################################################
# Framework to run all checks
##############################################################################


def message(text):
    """Print a message."""
    # print >> sys.stderr, options.prog + ': ' + text
    # print >> sys.stderr, text
    print text


def find_checks(argument_name):
    """
    Find all globally visible functions where the first argument name
    starts with argument_name.
    """
    checks = []
    function_type = type(find_checks)
    for name, function in globals().iteritems():
        if type(function) is function_type:
            args = inspect.getargspec(function)[0]
            if len(args) >= 1 and args[0].startswith(argument_name):
                checks.append((name, function, args))
    checks.sort()
    return checks


def mute_string(text):
    """
    Replace contents with 'xxx' to prevent syntax matching.

    >>> mute_string('"abc"')
    '"xxx"'
    >>> mute_string("'''abc'''")
    "'''xxx'''"
    >>> mute_string("r'abc'")
    "r'xxx'"
    """
    start = 1
    end = len(text) - 1
    # String modifiers (e.g. u or r)
    if text.endswith('"'):
        start += text.index('"')
    elif text.endswith("'"):
        start += text.index("'")
    # Triple quotes
    if text.endswith('"""') or text.endswith("'''"):
        start += 2
        end -= 2
    return text[:start] + 'x' * (end - start) + text[end:]


class Checker:
    """
    Load a Python source file, tokenize it, check coding style.
    """

    def __init__(self, filename):
        self.filename = filename
        self.lines = file(filename).readlines()
        self.physical_checks = find_checks('physical_line')
        self.logical_checks = find_checks('logical_line')
        options.counters['physical lines'] = \
            options.counters.get('physical lines', 0) + len(self.lines)

    def readline(self):
        """
        Get the next line from the input buffer.
        """
        self.line_number += 1
        if self.line_number > len(self.lines):
            return ''
        return self.lines[self.line_number - 1]

    def readline_check_physical(self):
        """
        Check and return the next physical line. This method can be
        used to feed tokenize.generate_tokens.
        """
        line = self.readline()
        if line:
            self.check_physical(line)
        return line

    def run_check(self, check, argument_names):
        """
        Run a check plugin.
        """
        arguments = []
        for name in argument_names:
            arguments.append(getattr(self, name))
        return check(*arguments)

    def check_physical(self, line):
        """
        Run all physical checks on a raw input line.
        """
        self.physical_line = line
        if self.indent_char is None and len(line) and line[0] in ' \t':
            self.indent_char = line[0]
        for name, check, argument_names in self.physical_checks:
            result = self.run_check(check, argument_names)
            if result is not None:
                offset, text = result
                self.report_error(self.line_number, offset, text, check)

    def build_tokens_line(self):
        """
        Build a logical line from tokens.
        """
        self.mapping = []
        logical = []
        length = 0
        previous = None
        for token in self.tokens:
            token_type, text = token[0:2]
            if token_type in (tokenize.COMMENT, tokenize.NL,
                              tokenize.INDENT, tokenize.DEDENT,
                              tokenize.NEWLINE):
                continue
            if token_type == tokenize.STRING:
                text = mute_string(text)
            if previous:
                end_line, end = previous[3]
                start_line, start = token[2]
                if end_line != start_line: # different row
                    if self.lines[end_line - 1][end - 1] not in '{[(':
                        logical.append(' ')
                        length += 1
                elif end != start: # different column
                    fill = self.lines[end_line - 1][end:start]
                    logical.append(fill)
                    length += len(fill)
            self.mapping.append((length, token))
            logical.append(text)
            length += len(text)
            previous = token
        self.logical_line = ''.join(logical)
        assert self.logical_line.lstrip() == self.logical_line
        assert self.logical_line.rstrip() == self.logical_line

    def check_logical(self):
        """
        Build a line from tokens and run all logical checks on it.
        """
        options.counters['logical lines'] = \
            options.counters.get('logical lines', 0) + 1
        self.build_tokens_line()
        first_line = self.lines[self.mapping[0][1][2][0] - 1]
        indent = first_line[:self.mapping[0][1][2][1]]
        self.previous_indent_level = self.indent_level
        self.indent_level = expand_indent(indent)
        if options.verbose >= 2:
            print self.logical_line[:80].rstrip()
        for name, check, argument_names in self.logical_checks:
            if options.verbose >= 3:
                print '   ', name
            result = self.run_check(check, argument_names)
            if result is not None:
                offset, text = result
                if type(offset) is tuple:
                    original_number, original_offset = offset
                else:
                    for token_offset, token in self.mapping:
                        if offset >= token_offset:
                            original_number = token[2][0]
                            original_offset = (token[2][1]
                                               + offset - token_offset)
                self.report_error(original_number, original_offset,
                                  text, check)
        self.previous_logical = self.logical_line

    def check_all(self):
        """
        Run all checks on the input file.
        """
        self.file_errors = 0
        self.line_number = 0
        self.indent_char = None
        self.indent_level = 0
        self.previous_logical = ''
        self.blank_lines = 0
        self.tokens = []
        parens = 0
        for token in tokenize.generate_tokens(self.readline_check_physical):
            # print tokenize.tok_name[token[0]], repr(token)
            self.tokens.append(token)
            token_type, text = token[0:2]
            if token_type == tokenize.OP and text in '([{':
                parens += 1
            if token_type == tokenize.OP and text in '}])':
                parens -= 1
            if token_type == tokenize.NEWLINE and not parens:
                self.check_logical()
                self.blank_lines = 0
                self.tokens = []
            if token_type == tokenize.NL and not parens:
                if len(self.tokens) <= 1:
                    # The physical line contains only this token.
                    self.blank_lines += 1
                self.tokens = []
            if token_type == tokenize.COMMENT:
                source_line = token[4]
                token_start = token[2][1]
                if source_line[:token_start].strip() == '':
                    self.blank_lines = 0
                if text.endswith('\n') and not parens:
                    # The comment also ends a physical line.  This works around
                    # Python < 2.6 behaviour, which does not generate NL after
                    # a comment which is on a line by itself.
                    self.tokens = []
        return self.file_errors

    def report_error(self, line_number, offset, text, check):
        """
        Report an error, according to options.
        """
        if options.quiet == 1 and not self.file_errors:
            message(self.filename)
        self.file_errors += 1
        code = text[:4]
        options.counters[code] = options.counters.get(code, 0) + 1
        options.messages[code] = text[5:]
        if options.quiet:
            return
        if options.testsuite:
            base = os.path.basename(self.filename)[:4]
            if base == code:
                return
            if base[0] == 'E' and code[0] == 'W':
                return
        if ignore_code(code):
            return
        if options.counters[code] == 1 or options.repeat:
            message("%s:%s:%d: %s" %
                    (self.filename, line_number, offset + 1, text))
            if options.show_source:
                line = self.lines[line_number - 1]
                message(line.rstrip())
                message(' ' * offset + '^')
            if options.show_pep8:
                message(check.__doc__.lstrip('\n').rstrip())


def input_file(filename):
    """
    Run all checks on a Python source file.
    """
    if excluded(filename) or not filename_match(filename):
        return {}
    if options.verbose:
        message('checking ' + filename)
    options.counters['files'] = options.counters.get('files', 0) + 1
    errors = Checker(filename).check_all()
    if options.testsuite and not errors:
        message("%s: %s" % (filename, "no errors found"))
    return errors


def input_dir(dirname):
    """
    Check all Python source files in this directory and all subdirectories.
    """
    dirname = dirname.rstrip('/')
    if excluded(dirname):
        return 0
    errors = 0
    for root, dirs, files in os.walk(dirname):
        if options.verbose:
            message('directory ' + root)
        options.counters['directories'] = \
            options.counters.get('directories', 0) + 1
        dirs.sort()
        for subdir in dirs:
            if excluded(subdir):
                dirs.remove(subdir)
        files.sort()
        for filename in files:
            errors += input_file(os.path.join(root, filename))
    return errors


def excluded(filename):
    """
    Check if options.exclude contains a pattern that matches filename.
    """
    basename = os.path.basename(filename)
    for pattern in options.exclude:
        if fnmatch(basename, pattern):
            # print basename, 'excluded because it matches', pattern
            return True


def filename_match(filename):
    """
    Check if options.filename contains a pattern that matches filename.
    If options.filename is unspecified, this always returns True.
    """
    if not options.filename:
        return True
    for pattern in options.filename:
        if fnmatch(filename, pattern):
            return True


def ignore_code(code):
    """
    Check if options.ignore contains a prefix of the error code.
    """
    for ignore in options.ignore:
        if code.startswith(ignore):
            return True


def get_error_statistics():
    """Get error statistics."""
    return get_statistics("E")


def get_warning_statistics():
    """Get warning statistics."""
    return get_statistics("W")


def get_statistics(prefix=''):
    """
    Get statistics for message codes that start with the prefix.

    prefix='' matches all errors and warnings
    prefix='E' matches all errors
    prefix='W' matches all warnings
    prefix='E4' matches all errors that have to do with imports
    """
    stats = []
    keys = options.messages.keys()
    keys.sort()
    for key in keys:
        if key.startswith(prefix):
            stats.append('%-7s %s %s' %
                         (options.counters[key], key, options.messages[key]))
    return stats


def print_statistics(prefix=''):
    """Print overall statistics (number of errors and warnings)."""
    for line in get_statistics(prefix):
        print line


def print_benchmark(elapsed):
    """
    Print benchmark numbers.
    """
    print '%-7.2f %s' % (elapsed, 'seconds elapsed')
    keys = ['directories', 'files',
            'logical lines', 'physical lines']
    for key in keys:
        if key in options.counters:
            print '%-7d %s per second (%d total)' % (
                options.counters[key] / elapsed, key,
                options.counters[key])


def process_options(arglist=None):
    """
    Process options passed either via arglist or via command line args.
    """
    global options, args
    usage = "%prog [options] input ..."
    parser = OptionParser(usage)
    parser.add_option('-v', '--verbose', default=0, action='count',
                      help="print status messages, or debug with -vv")
    parser.add_option('-q', '--quiet', default=0, action='count',
                      help="report only file names, or nothing with -qq")
    parser.add_option('--exclude', metavar='patterns', default=default_exclude,
                      help="skip matches (default %s)" % default_exclude)
    parser.add_option('--filename', metavar='patterns',
                      help="only check matching files (e.g. *.py)")
    parser.add_option('--ignore', metavar='errors', default='',
                      help="skip errors and warnings (e.g. E4,W)")
    parser.add_option('--repeat', action='store_true',
                      help="show all occurrences of the same error")
    parser.add_option('--show-source', action='store_true',
                      help="show source code for each error")
    parser.add_option('--show-pep8', action='store_true',
                      help="show text of PEP 8 for each error")
    parser.add_option('--statistics', action='store_true',
                      help="count errors and warnings")
    parser.add_option('--benchmark', action='store_true',
                      help="measure processing speed")
    parser.add_option('--testsuite', metavar='dir',
                      help="run regression tests from dir")
    parser.add_option('--doctest', action='store_true',
                      help="run doctest on myself")
    options, args = parser.parse_args(arglist)
    if options.testsuite:
        args.append(options.testsuite)
    if len(args) == 0:
        parser.error('input not specified')
    options.prog = os.path.basename(sys.argv[0])
    options.exclude = options.exclude.split(',')
    for index in range(len(options.exclude)):
        options.exclude[index] = options.exclude[index].rstrip('/')
    if options.filename:
        options.filename = options.filename.split(',')
    if options.ignore:
        options.ignore = options.ignore.split(',')
    else:
        options.ignore = []
    options.counters = {}
    options.messages = {}

    return options, args


def _main():
    """
    Parse options and run checks on Python source.
    """
    options, args = process_options()
    if options.doctest:
        import doctest
        return doctest.testmod()
    start_time = time.time()
    errors = 0
    for path in args:
        if os.path.isdir(path):
            errors += input_dir(path)
        else:
            errors += input_file(path)
    elapsed = time.time() - start_time
    if options.statistics:
        print_statistics()
    if options.benchmark:
        print_benchmark(elapsed)
    return errors > 0

if __name__ == '__main__':
    sys.exit(_main())

########NEW FILE########
__FILENAME__ = show-coverage
import os
import sys

class Presentation:
    def __init__(self, name, lines, covered):
        self.name = name
        self.lines = lines
        self.covered = covered

        if self.covered == 0:
            self.percent = 0
        else:
            self.percent = 100 * self.covered / float(self.lines)

    def show(self, maxlen=20):
        format = '%%-%ds  %%3d %%%%   (%%4d / %%4d)' % maxlen
        print format % (self.name, self.percent, self.covered, self.lines)
        

class Coverage:
    def __init__(self):
        self.files = []
        self.total_lines = 0
        self.total_covered = 0
        
    def _strip_filename(self, filename):
        filename = os.path.basename(filename)
        if filename.endswith('.cover'):
            filename = filename[:-6]
        return filename

    def add_file(self, file):
        self.files.append(file)

    def show_results(self):
        if not hasattr(self, 'files'):
            print 'No coverage data'
            return

        self.maxlen = max(map(lambda f: len(self._strip_filename(f)),
                              self.files))
        print 'Coverage report:'
        print '-' * (self.maxlen + 23)
        for file in self.files:
            self.show_one(file)
        print '-' * (self.maxlen + 23)
        
        p = Presentation('Total', self.total_lines, self.total_covered)
        p.show(self.maxlen)
        
    def show_one(self, filename):
        f = open(filename)
        lines = [line for line in f.readlines()
                         if (':' in line or line.startswith('>>>>>>')) and
                           not line.strip().startswith('#') and
                           not line.endswith(':\n')]

        uncovered_lines = [line for line in lines
                                   if line.startswith('>>>>>>')]
        if not lines:
            return

        filename = self._strip_filename(filename)
        
        p = Presentation(filename,
                         len(lines),
                         len(lines) - len(uncovered_lines))
        p.show(self.maxlen)

        self.total_lines += p.lines
        self.total_covered += p.covered
        
def main(args):
    c = Coverage()
    files = args[1:]
    files.sort()
    for file in files:
        if 'flumotion.test' in file:
            continue
        if '__init__' in file:
            continue
        c.add_file(file)

    c.show_results()
    
if __name__ == '__main__':
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = accurip
# -*- Mode: Python; test-case-name: morituri.test.test_common_accurip -*-
# vi:si:et:sw=4:sts=4:ts=4

# Morituri - for those about to RIP

# Copyright (C) 2009 Thomas Vander Stichele

# This file is part of morituri.
#
# morituri is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# morituri is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with morituri.  If not, see <http://www.gnu.org/licenses/>.

import errno
import os
import struct
import urlparse
import urllib2

from morituri.common import log

_CACHE_DIR = os.path.join(os.path.expanduser('~'), '.morituri', 'cache')


class AccuCache(log.Loggable):

    def __init__(self):
        if not os.path.exists(_CACHE_DIR):
            self.debug('Creating cache directory %s', _CACHE_DIR)
            os.makedirs(_CACHE_DIR)

    def _getPath(self, url):
        # split path starts with /
        return os.path.join(_CACHE_DIR, urlparse.urlparse(url)[2][1:])

    def retrieve(self, url, force=False):
        self.debug("Retrieving AccurateRip URL %s", url)
        path = self._getPath(url)
        self.debug("Cached path: %s", path)
        if force:
            self.debug("forced to download")
            self.download(url)
        elif not os.path.exists(path):
            self.debug("%s does not exist, downloading", path)
            self.download(url)

        if not os.path.exists(path):
            self.debug("%s does not exist, not in database", path)
            return None

        data = self._read(url)

        return getAccurateRipResponses(data)

    def download(self, url):
        # FIXME: download url as a task too
        try:
            handle = urllib2.urlopen(url)
            data = handle.read()

        except urllib2.HTTPError, e:
            if e.code == 404:
                return None
            else:
                raise

        self._cache(url, data)
        return data

    def _cache(self, url, data):
        path = self._getPath(url)
        try:
            os.makedirs(os.path.dirname(path))
        except OSError, e:
            self.debug('Could not make dir %s: %r' % (
                path, log.getExceptionMessage(e)))
            if e.errno != errno.EEXIST:
                raise

        handle = open(path, 'wb')
        handle.write(data)
        handle.close()

    def _read(self, url):
        self.debug("Reading %s from cache", url)
        path = self._getPath(url)
        handle = open(path, 'rb')
        data = handle.read()
        handle.close()
        return data


def getAccurateRipResponses(data):
    ret = []

    while data:
        trackCount = struct.unpack("B", data[0])[0]
        nbytes = 1 + 12 + trackCount * (1 + 8)

        ret.append(AccurateRipResponse(data[:nbytes]))
        data = data[nbytes:]

    return ret


class AccurateRipResponse(object):
    """
    I represent the response of the AccurateRip online database.

    @type checksums: list of str
    """

    trackCount = None
    discId1 = ""
    discId2 = ""
    cddbDiscId = ""
    confidences = None
    checksums = None

    def __init__(self, data):
        self.trackCount = struct.unpack("B", data[0])[0]
        self.discId1 = "%08x" % struct.unpack("<L", data[1:5])[0]
        self.discId2 = "%08x" % struct.unpack("<L", data[5:9])[0]
        self.cddbDiscId = "%08x" % struct.unpack("<L", data[9:13])[0]

        self.confidences = []
        self.checksums = []

        pos = 13
        for _ in range(self.trackCount):
            confidence = struct.unpack("B", data[pos])[0]
            checksum = "%08x" % struct.unpack("<L", data[pos + 1:pos + 5])[0]
            pos += 9
            self.confidences.append(confidence)
            self.checksums.append(checksum)

########NEW FILE########
__FILENAME__ = cache
# -*- Mode: Python; test-case-name: morituri.test.test_common_cache -*-
# vi:si:et:sw=4:sts=4:ts=4

# Morituri - for those about to RIP

# Copyright (C) 2009 Thomas Vander Stichele

# This file is part of morituri.
#
# morituri is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# morituri is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with morituri.  If not, see <http://www.gnu.org/licenses/>.

import os
import os.path
import glob
import tempfile
import shutil

from morituri.result import result
from morituri.common import directory

from morituri.extern.log import log


class Persister(log.Loggable):
    """
    I wrap an optional pickle to persist an object to disk.

    Instantiate me with a path to automatically unpickle the object.
    Call persist to store the object to disk; it will get stored if it
    changed from the on-disk object.

    @ivar object: the persistent object
    """

    def __init__(self, path=None, default=None):
        """
        If path is not given, the object will not be persisted.
        This allows code to transparently deal with both persisted and
        non-persisted objects, since the persist method will just end up
        doing nothing.
        """
        self._path = path
        self.object = None

        self._unpickle(default)

    def persist(self, obj=None):
        """
        Persist the given object, if we have a persistence path and the
        object changed.

        If object is not given, re-persist our object, always.
        If object is given, only persist if it was changed.
        """
        # don't pickle if it's already ok
        if obj and obj == self.object:
            return

        # store the object on ourselves if not None
        if obj is not None:
            self.object = obj

        # don't pickle if there is no path
        if not self._path:
            return

        # default to pickling our object again
        if obj is None:
            obj = self.object

        # pickle
        self.object = obj
        (fd, path) = tempfile.mkstemp(suffix='.morituri.pickle')
        handle = os.fdopen(fd, 'wb')
        import pickle
        pickle.dump(obj, handle, 2)
        handle.close()
        # do an atomic move
        shutil.move(path, self._path)
        self.debug('saved persisted object to %r' % self._path)

    def _unpickle(self, default=None):
        self.object = default

        if not self._path:
            return None

        if not os.path.exists(self._path):
            return None

        handle = open(self._path)
        import pickle

        try:
            self.object = pickle.load(handle)
            self.debug('loaded persisted object from %r' % self._path)
        except:
            # can fail for various reasons; in that case, pretend we didn't
            # load it
            pass

    def delete(self):
        self.object = None
        os.unlink(self._path)


class PersistedCache(log.Loggable):
    """
    I wrap a directory of persisted objects.
    """

    path = None

    def __init__(self, path):
        self.path = path
        try:
            os.makedirs(self.path)
        except OSError, e:
            if e.errno != 17: # FIXME
                raise

    def _getPath(self, key):
        return os.path.join(self.path, '%s.pickle' % key)

    def get(self, key):
        """
        Returns the persister for the given key.
        """
        persister = Persister(self._getPath(key))
        if persister.object:
            if hasattr(persister.object, 'instanceVersion'):
                o = persister.object
                if o.instanceVersion < o.__class__.classVersion:
                    self.debug(
                        'key %r persisted object version %d is outdated',
                        key, o.instanceVersion)
                    persister.object = None
        # FIXME: don't delete old objects atm
        #             persister.delete()

        return persister


class ResultCache(log.Loggable):

    def __init__(self, path=None):
        if not path:
            path = self._getResultCachePath()

        self._path = path
        self._pcache = PersistedCache(self._path)

    def _getResultCachePath(self):
        path = os.path.join(os.path.expanduser('~'), '.morituri', 'cache',
            'result')
        return path

    def getRipResult(self, cddbdiscid, create=True):
        """
        Retrieve the persistable RipResult either from our cache (from a
        previous, possibly aborted rip), or return a new one.

        @rtype: L{Persistable} for L{result.RipResult}
        """
        presult = self._pcache.get(cddbdiscid)

        if not presult.object:
            self.debug('result for cddbdiscid %r not in cache', cddbdiscid)
            if not create:
                self.debug('returning None')
                return None

            self.debug('creating result')
            presult.object = result.RipResult()
            presult.persist(presult.object)
        else:
            self.debug('result for cddbdiscid %r found in cache, reusing',
                cddbdiscid)

        return presult

    def getIds(self):
        paths = glob.glob(os.path.join(self._path, '*.pickle'))

        return [os.path.splitext(os.path.basename(path))[0] for path in paths]


class TableCache(log.Loggable):

    """
    I read and write entries to and from the cache of tables.

    If no path is specified, the cache will write to the current cache
    directory and read from all possible cache directories (to allow for
    pre-0.2.1 cddbdiscid-keyed entries).
    """

    def __init__(self, path=None):
        if not path:
            d = directory.Directory()
            self._path = d.getCache('table')
            self._readPaths = d.getReadCaches('table')
        else:
            self._path = path
            self._readPaths = [path, ]

        self._pcache = PersistedCache(self._path)
        self._readPCaches = [PersistedCache(p) for p in self._readPaths]

    def get(self, cddbdiscid, mbdiscid):
        # Before 0.2.1, we only saved by cddbdiscid, and had collisions
        # mbdiscid collisions are a lot less likely
        for pcache in self._readPCaches:
            ptable = pcache.get('mbdiscid.' + mbdiscid)
            if ptable.object:
                break

        if not ptable.object:
            for pcache in self._readPCaches:
                ptable = pcache.get(cddbdiscid)
                if ptable.object:
                    if ptable.object.getMusicBrainzDiscId() != mbdiscid:
                        self.debug('cached table is for different mb id %r' % (
                            ptable.object.getMusicBrainzDiscId()))
                    ptable.object = None
                else:
                    self.debug('no valid cached table found for %r' %
                        cddbdiscid)

        if not ptable.object:
            # get an empty persistable from the writable location
            ptable = self._pcache.get('mbdiscid.' + mbdiscid)

        return ptable

########NEW FILE########
__FILENAME__ = checksum
# -*- Mode: Python; test-case-name: morituri.test.test_common_checksum -*-
# vi:si:et:sw=4:sts=4:ts=4

# Morituri - for those about to RIP

# Copyright (C) 2009 Thomas Vander Stichele

# This file is part of morituri.
#
# morituri is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# morituri is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with morituri.  If not, see <http://www.gnu.org/licenses/>.

import os
import struct
import zlib

import gst

from morituri.common import common
from morituri.common import gstreamer as cgstreamer
from morituri.common import log
from morituri.common import task

from morituri.extern.task import gstreamer

# checksums are not CRC's. a CRC is a specific type of checksum.


class ChecksumTask(log.Loggable, gstreamer.GstPipelineTask):
    """
    I am a task that calculates a checksum of the decoded audio data.

    @ivar checksum: the resulting checksum
    """

    logCategory = 'ChecksumTask'

    # this object needs a main loop to stop
    description = 'Calculating checksum'

    def __init__(self, path, sampleStart=0, sampleLength=-1):
        """
        A sample is considered a set of samples for each channel;
        ie 16 bit stereo is 4 bytes per sample.
        If sampleLength < 0 it is treated as 'unknown' and calculated.

        @type  path:       unicode
        @type  sampleStart: int
        @param sampleStart: the sample to start at
        """

        # sampleLength can be e.g. -588 when it is -1 * SAMPLES_PER_FRAME

        assert type(path) is unicode, "%r is not unicode" % path

        self.logName = "ChecksumTask 0x%x" % id(self)

        # use repr/%r because path can be unicode
        if sampleLength < 0:
            self.debug(
                'Creating checksum task on %r from sample %d until the end',
                path, sampleStart)
        else:
            self.debug(
                'Creating checksum task on %r from sample %d for %d samples',
                path, sampleStart, sampleLength)

        if not os.path.exists(path):
            raise IndexError('%r does not exist' % path)

        self._path = path
        self._sampleStart = sampleStart
        self._sampleLength = sampleLength
        self._sampleEnd = None
        self._checksum = 0
        self._bytes = 0 # number of bytes received
        self._first = None
        self._last = None
        self._adapter = gst.Adapter()

        self.checksum = None # result

        cgstreamer.removeAudioParsers()

    ### gstreamer.GstPipelineTask implementations

    def getPipelineDesc(self):
        return '''
            filesrc location="%s" !
            decodebin name=decode ! audio/x-raw-int !
            appsink name=sink sync=False emit-signals=True
            ''' % gstreamer.quoteParse(self._path).encode('utf-8')

    def _getSampleLength(self):
        # get length in samples of file
        sink = self.pipeline.get_by_name('sink')

        self.debug('query duration')
        try:
            length, qformat = sink.query_duration(gst.FORMAT_DEFAULT)
        except gst.QueryError, e:
            self.setException(e)
            return None

        # wavparse 0.10.14 returns in bytes
        if qformat == gst.FORMAT_BYTES:
            self.debug('query returned in BYTES format')
            length /= 4
        self.debug('total sample length of file: %r', length)

        return length


    def paused(self):
        sink = self.pipeline.get_by_name('sink')

        length = self._getSampleLength()
        if length is None:
            return

        if self._sampleLength < 0:
            self._sampleLength = length - self._sampleStart
            self.debug('sampleLength is queried as %d samples',
                self._sampleLength)
        else:
            self.debug('sampleLength is known, and is %d samples' %
                self._sampleLength)

        self._sampleEnd = self._sampleStart + self._sampleLength - 1
        self.debug('sampleEnd is sample %d' % self._sampleEnd)

        self.debug('event')


        if self._sampleStart == 0 and self._sampleEnd + 1 == length:
            self.debug('No need to seek, crcing full file')
        else:
            # the segment end only is respected since -good 0.10.14.1
            event = gst.event_new_seek(1.0, gst.FORMAT_DEFAULT,
                gst.SEEK_FLAG_FLUSH,
                gst.SEEK_TYPE_SET, self._sampleStart,
                gst.SEEK_TYPE_SET, self._sampleEnd + 1) # half-inclusive
            self.debug('CRCing %r from frame %d to frame %d (excluded)' % (
                self._path,
                self._sampleStart / common.SAMPLES_PER_FRAME,
                (self._sampleEnd + 1) / common.SAMPLES_PER_FRAME))
            # FIXME: sending it with sampleEnd set screws up the seek, we
            # don't get # everything for flac; fixed in recent -good
            result = sink.send_event(event)
            self.debug('event sent, result %r', result)
            if not result:
                self.error('Failed to select samples with GStreamer seek event')
        sink.connect('new-buffer', self._new_buffer_cb)
        sink.connect('eos', self._eos_cb)

        self.debug('scheduling setting to play')
        # since set_state returns non-False, adding it as timeout_add
        # will repeatedly call it, and block the main loop; so
        #   gobject.timeout_add(0L, self.pipeline.set_state, gst.STATE_PLAYING)
        # would not work.

        def play():
            self.pipeline.set_state(gst.STATE_PLAYING)
            return False
        self.schedule(0, play)

        #self.pipeline.set_state(gst.STATE_PLAYING)
        self.debug('scheduled setting to play')

    def stopped(self):
        self.debug('stopped')
        if not self._last:
            # see http://bugzilla.gnome.org/show_bug.cgi?id=578612
            self.debug(
                'not a single buffer gotten, setting exception EmptyError')
            self.setException(common.EmptyError('not a single buffer gotten'))
            return
        else:
            self._checksum = self._checksum % 2 ** 32
            self.debug("last buffer's sample offset %r", self._last.offset)
            self.debug("last buffer's sample size %r", len(self._last) / 4)
            last = self._last.offset + len(self._last) / 4 - 1
            self.debug("last sample offset in buffer: %r", last)
            self.debug("requested sample end: %r", self._sampleEnd)
            self.debug("requested sample length: %r", self._sampleLength)
            self.debug("checksum: %08X", self._checksum)
            self.debug("bytes: %d", self._bytes)
            if self._sampleEnd != last:
                msg = 'did not get all samples, %d of %d missing' % (
                    self._sampleEnd - last, self._sampleEnd)
                self.warning(msg)
                self.setExceptionAndTraceback(common.MissingFrames(msg))
                return

        self.checksum = self._checksum

    ### subclass methods

    def do_checksum_buffer(self, buf, checksum):
        """
        Subclasses should implement this.

        @param buf:      a byte buffer containing two 16-bit samples per
                         channel.
        @type  buf:      C{str}
        @param checksum: the checksum so far, as returned by the
                         previous call.
        @type  checksum: C{int}
        """
        raise NotImplementedError

    ### private methods

    def _new_buffer_cb(self, sink):
        buf = sink.emit('pull-buffer')
        gst.log('received new buffer at offset %r with length %r' % (
            buf.offset, buf.size))
        if self._first is None:
            self._first = buf.offset
            self.debug('first sample is sample offset %r', self._first)
        self._last = buf

        assert len(buf) % 4 == 0, "buffer is not a multiple of 4 bytes"

        # FIXME: gst-python 0.10.14.1 doesn't have adapter_peek/_take wrapped
        # see http://bugzilla.gnome.org/show_bug.cgi?id=576505
        self._adapter.push(buf)

        while self._adapter.available() >= common.BYTES_PER_FRAME:
            # FIXME: in 0.10.14.1, take_buffer leaks a ref
            buf = self._adapter.take_buffer(common.BYTES_PER_FRAME)

            self._checksum = self.do_checksum_buffer(buf, self._checksum)
            self._bytes += len(buf)

            # update progress
            sample = self._first + self._bytes / 4
            samplesDone = sample - self._sampleStart
            progress = float(samplesDone) / float((self._sampleLength))
            # marshal to the main thread
            self.schedule(0, self.setProgress, progress)

    def _eos_cb(self, sink):
        # get the last one; FIXME: why does this not get to us before ?
        #self._new_buffer_cb(sink)
        self.debug('eos, scheduling stop')
        self.schedule(0, self.stop)


class CRC32Task(ChecksumTask):
    """
    I do a simple CRC32 check.
    """

    description = 'Calculating CRC'

    def do_checksum_buffer(self, buf, checksum):
        return zlib.crc32(buf, checksum)


class AccurateRipChecksumTask(ChecksumTask):
    """
    I implement the AccurateRip checksum.

    See http://www.accuraterip.com/
    """

    description = 'Calculating AccurateRip checksum'

    def __init__(self, path, trackNumber, trackCount, sampleStart=0,
            sampleLength=-1):
        ChecksumTask.__init__(self, path, sampleStart, sampleLength)
        self._trackNumber = trackNumber
        self._trackCount = trackCount
        self._discFrameCounter = 0 # 1-based

    def __repr__(self):
        return "<AccurateRipCheckSumTask of track %d in %r>" % (
            self._trackNumber, self._path)

    def do_checksum_buffer(self, buf, checksum):
        self._discFrameCounter += 1

        # on first track ...
        if self._trackNumber == 1:
            # ... skip first 4 CD frames
            if self._discFrameCounter <= 4:
                gst.debug('skipping frame %d' % self._discFrameCounter)
                return checksum
            # ... on 5th frame, only use last value
            elif self._discFrameCounter == 5:
                values = struct.unpack("<I", buf[-4:])
                checksum += common.SAMPLES_PER_FRAME * 5 * values[0]
                checksum &= 0xFFFFFFFF
                return checksum

        # on last track, skip last 5 CD frames
        if self._trackNumber == self._trackCount:
            discFrameLength = self._sampleLength / common.SAMPLES_PER_FRAME
            if self._discFrameCounter > discFrameLength - 5:
                self.debug('skipping frame %d', self._discFrameCounter)
                return checksum

        values = struct.unpack("<%dI" % (len(buf) / 4), buf)
        for i, value in enumerate(values):
            # self._bytes is updated after do_checksum_buffer
            checksum += (self._bytes / 4 + i + 1) * value
            checksum &= 0xFFFFFFFF
            # offset = self._bytes / 4 + i + 1
            # if offset % common.SAMPLES_PER_FRAME == 0:
            #   print 'frame %d, ends before %d, last value %08x, CRC %08x' % (
            #     offset / common.SAMPLES_PER_FRAME, offset, value, sum)

        return checksum


class TRMTask(task.GstPipelineTask):
    """
    I calculate a MusicBrainz TRM fingerprint.

    @ivar trm: the resulting trm
    """

    trm = None
    description = 'Calculating fingerprint'

    def __init__(self, path):
        if not os.path.exists(path):
            raise IndexError('%s does not exist' % path)

        self.path = path
        self._trm = None
        self._bus = None

    def getPipelineDesc(self):
        return '''
            filesrc location="%s" !
            decodebin ! audioconvert ! audio/x-raw-int !
            trm name=trm !
            appsink name=sink sync=False emit-signals=True''' % self.path

    def parsed(self):
        sink = self.pipeline.get_by_name('sink')
        sink.connect('new-buffer', self._new_buffer_cb)

    def paused(self):
        gst.debug('query duration')

        self._length, qformat = self.pipeline.query_duration(gst.FORMAT_TIME)
        gst.debug('total length: %r' % self._length)
        gst.debug('scheduling setting to play')
        # since set_state returns non-False, adding it as timeout_add
        # will repeatedly call it, and block the main loop; so
        #   gobject.timeout_add(0L, self.pipeline.set_state, gst.STATE_PLAYING)
        # would not work.


    # FIXME: can't move this to base class because it triggers too soon
    # in the case of checksum

    def bus_eos_cb(self, bus, message):
        gst.debug('eos, scheduling stop')
        self.schedule(0, self.stop)

    def bus_tag_cb(self, bus, message):
        taglist = message.parse_tag()
        if 'musicbrainz-trmid' in taglist.keys():
            self._trm = taglist['musicbrainz-trmid']

    def _new_buffer_cb(self, sink):
        # this is just for counting progress
        buf = sink.emit('pull-buffer')
        position = buf.timestamp
        if buf.duration != gst.CLOCK_TIME_NONE:
            position += buf.duration
        self.setProgress(float(position) / self._length)

    def stopped(self):
        self.trm = self._trm

class MaxSampleTask(ChecksumTask):
    """
    I check for the biggest sample value.
    """

    description = 'Finding highest sample value'

    def do_checksum_buffer(self, buf, checksum):
        values = struct.unpack("<%dh" % (len(buf) / 2), buf)
        absvalues = [abs(v) for v in values]
        m = max(absvalues)
        if checksum < m:
            checksum = m

        return checksum


########NEW FILE########
__FILENAME__ = common
# -*- Mode: Python; test-case-name: morituri.test.test_common_common -*-
# vi:si:et:sw=4:sts=4:ts=4

# Morituri - for those about to RIP

# Copyright (C) 2009 Thomas Vander Stichele

# This file is part of morituri.
#
# morituri is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# morituri is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with morituri.  If not, see <http://www.gnu.org/licenses/>.


import os
import os.path
import commands
import math
import subprocess

from morituri.extern import asyncsub
from morituri.extern.log import log

FRAMES_PER_SECOND = 75

SAMPLES_PER_FRAME = 588 # a sample is 2 16-bit values, left and right channel
WORDS_PER_FRAME = SAMPLES_PER_FRAME * 2
BYTES_PER_FRAME = SAMPLES_PER_FRAME * 4


def msfToFrames(msf):
    """
    Converts a string value in MM:SS:FF to frames.

    @param msf: the MM:SS:FF value to convert
    @type  msf: str

    @rtype:   int
    @returns: number of frames
    """
    if not ':' in msf:
        return int(msf)

    m, s, f = msf.split(':')

    return 60 * FRAMES_PER_SECOND * int(m) \
        + FRAMES_PER_SECOND * int(s) \
        + int(f)


def framesToMSF(frames, frameDelimiter=':'):
    f = frames % FRAMES_PER_SECOND
    frames -= f
    s = (frames / FRAMES_PER_SECOND) % 60
    frames -= s * 60
    m = frames / FRAMES_PER_SECOND / 60

    return "%02d:%02d%s%02d" % (m, s, frameDelimiter, f)


def framesToHMSF(frames):
    # cdparanoia style
    f = frames % FRAMES_PER_SECOND
    frames -= f
    s = (frames / FRAMES_PER_SECOND) % 60
    frames -= s * FRAMES_PER_SECOND
    m = (frames / FRAMES_PER_SECOND / 60) % 60
    frames -= m * FRAMES_PER_SECOND * 60
    h = frames / FRAMES_PER_SECOND / 60 / 60

    return "%02d:%02d:%02d.%02d" % (h, m, s, f)


def formatTime(seconds, fractional=3):
    """
    Nicely format time in a human-readable format, like
    HH:MM:SS.mmm

    If fractional is zero, no seconds will be shown.
    If it is greater than 0, we will show seconds and fractions of seconds.
    As a side consequence, there is no way to show seconds without fractions.

    @param seconds:    the time in seconds to format.
    @type  seconds:    int or float
    @param fractional: how many digits to show for the fractional part of
                       seconds.
    @type  fractional: int

    @rtype: string
    @returns: a nicely formatted time string.
    """
    chunks = []

    if seconds < 0:
        chunks.append(('-'))
        seconds = -seconds

    hour = 60 * 60
    hours = seconds / hour
    seconds %= hour

    minute = 60
    minutes = seconds / minute
    seconds %= minute

    chunk = '%02d:%02d' % (hours, minutes)
    if fractional > 0:
        chunk += ':%0*.*f' % (fractional + 3, fractional, seconds)

    chunks.append(chunk)

    return " ".join(chunks)


def tagListToDict(tl):
    """
    Converts gst.TagList to dict.
    Also strips it of tags that are not writable.
    """
    import gst

    d = {}
    for key in tl.keys():
        if key == gst.TAG_DATE:
            date = tl[key]
            d[key] = "%4d-%2d-%2d" % (date.year, date.month, date.day)
        elif key in [
            gst.TAG_AUDIO_CODEC,
            gst.TAG_VIDEO_CODEC,
            gst.TAG_MINIMUM_BITRATE,
            gst.TAG_BITRATE,
            gst.TAG_MAXIMUM_BITRATE,
            ]:
            pass
        else:
            d[key] = tl[key]
    return d


def tagListEquals(tl1, tl2):
    d1 = tagListToDict(tl1)
    d2 = tagListToDict(tl2)

    return d1 == d2


def tagListDifference(tl1, tl2):
    d1 = tagListToDict(tl1)
    d2 = tagListToDict(tl2)
    return set(d1.keys()) - set(d2.keys())

    return d1 == d2


class MissingDependencyException(Exception):
    dependency = None

    def __init__(self, *args):
        self.args = args
        self.dependency = args[0]


class EmptyError(Exception):
    pass

class MissingFrames(Exception):
    """
    Less frames decoded than expected.
    """
    pass


def shrinkPath(path):
    """
    Shrink a full path to a shorter version.
    Used to handle ENAMETOOLONG
    """
    parts = list(os.path.split(path))
    length = len(parts[-1])
    target = 127
    if length <= target:
        target = pow(2, int(math.log(length, 2))) - 1

    name, ext = os.path.splitext(parts[-1])
    target -= len(ext) + 1

    # split on space, then reassemble
    words = name.split(' ')
    length = 0
    pieces = []
    for word in words:
        if length + 1 + len(word) <= target:
            pieces.append(word)
            length += 1 + len(word)
        else:
            break

    name = " ".join(pieces)
    # ext includes period
    parts[-1] = u'%s%s' % (name, ext)
    path = os.path.join(*parts)
    return path


def getRealPath(refPath, filePath):
    """
    Translate a .cue or .toc's FILE argument to an existing path.
    Does Windows path translation.
    Will look for the given file name, but with .flac and .wav as extensions.

    @param refPath:  path to the file from which the track is referenced;
                     for example, path to the .cue file in the same directory
    @type  refPath:  unicode

    @type  filePath: unicode
    """
    assert type(filePath) is unicode, "%r is not unicode" % filePath

    if os.path.exists(filePath):
        return filePath

    candidatePaths = []

    # .cue FILE statements can have Windows-style path separators, so convert
    # them as one possible candidate
    # on the other hand, the file may indeed contain a backslash in the name
    # on linux
    # FIXME: I guess we might do all possible combinations of splitting or
    #        keeping the slash, but let's just assume it's either Windows
    #        or linux
    # See https://thomas.apestaart.org/morituri/trac/ticket/107
    parts = filePath.split('\\')
    if parts[0] == '':
        parts[0] = os.path.sep
    tpath = os.path.join(*parts)

    for path in [filePath, tpath]:
        if path == os.path.abspath(path):
            candidatePaths.append(path)
        else:
            # if the path is relative:
            # - check relatively to the cue file
            # - check only the filename part relative to the cue file
            candidatePaths.append(os.path.join(
                os.path.dirname(refPath), path))
            candidatePaths.append(os.path.join(
                os.path.dirname(refPath), os.path.basename(path)))

    # Now look for .wav and .flac files, as .flac files are often named .wav
    for candidate in candidatePaths:
        noext, _ = os.path.splitext(candidate)
        for ext in ['wav', 'flac']:
            cpath = '%s.%s' % (noext, ext)
            if os.path.exists(cpath):
                return cpath

    raise KeyError("Cannot find file for %r" % filePath)


def getRelativePath(targetPath, collectionPath):
    """
    Get a relative path from the directory of collectionPath to
    targetPath.

    Used to determine the path to use in .cue/.m3u files
    """
    log.debug('common', 'getRelativePath: target %r, collection %r' % (
        targetPath, collectionPath))

    targetDir = os.path.dirname(targetPath)
    collectionDir = os.path.dirname(collectionPath)
    if targetDir == collectionDir:
        log.debug('common',
            'getRelativePath: target and collection in same dir')
        return os.path.basename(targetPath)
    else:
        rel = os.path.relpath(
            targetDir + os.path.sep,
            collectionDir + os.path.sep)
        log.debug('common',
            'getRelativePath: target and collection in different dir, %r' %
                rel)
        return os.path.join(rel, os.path.basename(targetPath))


class VersionGetter(object):
    """
    I get the version of a program by looking for it in command output
    according to a regexp.
    """

    def __init__(self, dependency, args, regexp, expander):
        """
        @param dependency: name of the dependency providing the program
        @param args:       the arguments to invoke to show the version
        @type  args:       list of str
        @param regexp:     the regular expression to get the version
        @param expander:   the expansion string for the version using the
                           regexp group dict
        """

        self._dep = dependency
        self._args = args
        self._regexp = regexp
        self._expander = expander

    def get(self):
        version = "(Unknown)"

        try:
            p = asyncsub.Popen(self._args,
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, close_fds=True)
            p.wait()
            output = asyncsub.recv_some(p, e=0, stderr=1)
            vre = self._regexp.search(output)
            if vre:
                version = self._expander % vre.groupdict()
        except OSError, e:
            import errno
            if e.errno == errno.ENOENT:
                raise MissingDependencyException(self._dep)
            raise

        return version


def getRevision():
    """
    Get a revision tag for the current git source tree.

    Appends -modified in case there are local modifications.

    If this is not a git tree, return the top-level REVISION contents instead.

    Finally, return unknown.
    """
    topsrcdir = os.path.join(os.path.dirname(__file__), '..', '..')

    # only use git if our src directory looks like a git checkout
    # if you run git regardless, it recurses up until it finds a .git,
    # which may be higher than your current source tree
    if os.path.exists(os.path.join(topsrcdir, '.git')):

        # always falls back to the current commit hash if no tags are found
        status, describe = commands.getstatusoutput('git describe --all')
        if status == 0:
            if commands.getoutput('git diff-index --name-only HEAD --'):
                describe += '-modified'

            return describe

    # check for a top-level REVISION file
    path = os.path.join(topsrcdir, 'REVISION')
    if os.path.exists(path):
        revision = open(path).read().strip()
        return revision

    return '(unknown)'

########NEW FILE########
__FILENAME__ = config
# -*- Mode: Python; test-case-name: morituri.test.test_common_config -*-
# vi:si:et:sw=4:sts=4:ts=4

# Morituri - for those about to RIP

# Copyright (C) 2009 Thomas Vander Stichele

# This file is part of morituri.
#
# morituri is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# morituri is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with morituri.  If not, see <http://www.gnu.org/licenses/>.

import os.path
import shutil
import urllib
import codecs
import tempfile
import ConfigParser

from morituri.common import directory, log


class Config(log.Loggable):

    def __init__(self, path=None):
        if not path:
            path = self.getDefaultPath()

        self._path = path

        self._parser = ConfigParser.SafeConfigParser()

        self.open()

    def getDefaultPath(self):
        return directory.Directory().getConfig()

    def open(self):
        # Open the file with the correct encoding
        if os.path.exists(self._path):
            with codecs.open(self._path, 'r', encoding='utf-8') as f:
                self._parser.readfp(f)

        self.info('Loaded %d sections from config file' %
            len(self._parser.sections()))

    def write(self):
        fd, path = tempfile.mkstemp(suffix=u'.moriturirc')
        handle = os.fdopen(fd, 'w')
        self._parser.write(handle)
        handle.close()
        shutil.move(path, self._path)


    ### any section

    def _getter(self, suffix, section, option):
        methodName = 'get' + suffix
        method = getattr(self._parser, methodName)
        try:
            return method(section, option)
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            return None

    def get(self, section, option):
        return self._getter('', section, option)

    def getboolean(self, section, option):
        return self._getter('boolean', section, option)

    ### drive sections

    def setReadOffset(self, vendor, model, release, offset):
        """
        Set a read offset for the given drive.

        Strips the given strings of leading and trailing whitespace.
        """
        section = self._findOrCreateDriveSection(vendor, model, release)
        self._parser.set(section, 'read_offset', str(offset))
        self.write()

    def getReadOffset(self, vendor, model, release):
        """
        Get a read offset for the given drive.
        """
        section = self._findDriveSection(vendor, model, release)

        try:
            return int(self._parser.get(section, 'read_offset'))
        except ConfigParser.NoOptionError:
            raise KeyError("Could not find read_offset for %s/%s/%s" % (
                vendor, model, release))


    def setDefeatsCache(self, vendor, model, release, defeat):
        """
        Set whether the drive defeats the cache.

        Strips the given strings of leading and trailing whitespace.
        """
        section = self._findOrCreateDriveSection(vendor, model, release)
        self._parser.set(section, 'defeats_cache', str(defeat))
        self.write()

    def getDefeatsCache(self, vendor, model, release):
        section = self._findDriveSection(vendor, model, release)

        try:
            return bool(self._parser.get(section, 'defeats_cache'))
        except ConfigParser.NoOptionError:
            raise KeyError("Could not find defeats_cache for %s/%s/%s" % (
                vendor, model, release))

    def _findDriveSection(self, vendor, model, release):
        for name in self._parser.sections():
            if not name.startswith('drive:'):
                continue

            self.debug('Looking at section %r' % name)
            conf = {}
            for key in ['vendor', 'model', 'release']:
                locals()[key] = locals()[key].strip()
                conf[key] = self._parser.get(name, key)
                self.debug("%s: '%s' versus '%s'" % (
                    key, locals()[key], conf[key]))
            if vendor.strip() != conf['vendor']:
                continue
            if model.strip() != conf['model']:
                continue
            if release.strip() != conf['release']:
                continue

            return name

        raise KeyError("Could not find configuration section for %s/%s/%s" % (
                vendor, model, release))

    def _findOrCreateDriveSection(self, vendor, model, release):
        try:
            section = self._findDriveSection(vendor, model, release)
        except KeyError:
            section = 'drive:' + urllib.quote('%s:%s:%s' % (
                vendor, model, release))
            self._parser.add_section(section)
            __pychecker__ = 'no-local'
            for key in ['vendor', 'model', 'release']:
                self._parser.set(section, key, locals()[key].strip())

        self.write()

        return self._findDriveSection(vendor, model, release)



########NEW FILE########
__FILENAME__ = deps
# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

import os
import urllib

from morituri.extern.deps import deps


class DepsHandler(deps.DepsHandler):

    def __init__(self, name='morituri'):
        deps.DepsHandler.__init__(self, name)

        self.add(GStPython())
        self.add(CDDB())
        self.add(SetupTools())
        self.add(PyCDIO())

    def report(self, summary):
        reporter = os.environ.get('EMAIL_ADDRESS', None)
        get = "summary=%s" % urllib.quote(summary)
        if reporter:
            get += "&reporter=%s" % urllib.quote(reporter)
        return 'http://thomas.apestaart.org/morituri/trac/newticket?' + get


class GStPython(deps.Dependency):
    module = 'gst'
    name = "GStreamer Python bindings"
    homepage = "http://gstreamer.freedesktop.org"

    def Fedora_install(self, distro):
        return self.Fedora_yum('gstreamer-python')

    #def Ubuntu_install(self, distro):
    #    pass


class CDDB(deps.Dependency):
    module = 'CDDB'
    name = "python-CDDB"
    homepage = "http://cddb-py.sourceforge.net/"

    def Fedora_install(self, distro):
        return self.Fedora_yum('python-CDDB')

    def Ubuntu_install(self, distro):
        return self.Ubuntu_apt('python-cddb')


class SetupTools(deps.Dependency):
    module = 'pkg_resources'
    name = "python-setuptools"
    homepage = "http://pypi.python.org/pypi/setuptools"

    def Fedora_install(self, distro):
        return self.Fedora_yum('python-setuptools')


class PyCDIO(deps.Dependency):

    module = 'pycdio'
    name = "pycdio"
    homepage = "http://www.gnu.org/software/libcdio/"
    egg = 'pycdio'

    def Fedora_install(self, distro):
        return self.Fedora_yum('pycdio')

    def validate(self):
        version = self.version()
        if version == '0.18':
            return '''pycdio 0.18 does not work.
See http://savannah.gnu.org/bugs/?38185'''

########NEW FILE########
__FILENAME__ = directory
# -*- Mode: Python; test-case-name: morituri.test.test_common_directory -*-
# vi:si:et:sw=4:sts=4:ts=4

# Morituri - for those about to RIP

# Copyright (C) 2013 Thomas Vander Stichele

# This file is part of morituri.
#
# morituri is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# morituri is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with morituri.  If not, see <http://www.gnu.org/licenses/>.

import os

from morituri.common import log


class Directory(log.Loggable):

    def getConfig(self):
        try:
            from xdg import BaseDirectory
            directory = BaseDirectory.save_config_path('morituri')
            path = os.path.join(directory, 'morituri.conf')
            self.info('Using XDG, configuration file is %s' % path)
        except ImportError:
            path = os.path.join(os.path.expanduser('~'), '.moriturirc')
            self.info('Not using XDG, configuration file is %s' % path)
        return path


    def getCache(self, name=None):
        try:
            from xdg import BaseDirectory
            path = BaseDirectory.save_cache_path('morituri')
            self.info('Using XDG, cache directory is %s' % path)
        except (ImportError, AttributeError):
            # save_cache_path was added in pyxdg 0.25
            path = os.path.join(os.path.expanduser('~'), '.morituri', 'cache')
            if not os.path.exists(path):
                os.makedirs(path)
            self.info('Not using XDG, cache directory is %s' % path)

        if name:
            path = os.path.join(path, name)
            if not os.path.exists(path):
                os.makedirs(path)

        return path

    def getReadCaches(self, name=None):
        paths = []

        try:
            from xdg import BaseDirectory
            path = BaseDirectory.save_cache_path('morituri')
            self.info('For XDG, read cache directory is %s' % path)
            paths.append(path)
        except (ImportError, AttributeError):
            # save_cache_path was added in pyxdg 0.21
            pass

        path = os.path.join(os.path.expanduser('~'), '.morituri', 'cache')
        if os.path.exists(path):
            self.info('From before XDG, read cache directory is %s' % path)
            paths.append(path)

        if name:
            paths = [os.path.join(p, name) for p in paths]

        return paths



########NEW FILE########
__FILENAME__ = drive
# -*- Mode: Python; test-case-name: morituri.test.test_common_drive -*-
# vi:si:et:sw=4:sts=4:ts=4

# Morituri - for those about to RIP

# Copyright (C) 2009 Thomas Vander Stichele

# This file is part of morituri.
#
# morituri is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# morituri is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with morituri.  If not, see <http://www.gnu.org/licenses/>.

import os

from morituri.common import log


def _listify(listOrString):
    if type(listOrString) == str:
        return [listOrString, ]

    return listOrString


def getAllDevicePaths():
    try:
        # see https://savannah.gnu.org/bugs/index.php?38477
        return [str(dev) for dev in _getAllDevicePathsPyCdio()]
    except ImportError:
        log.info('drive', 'Cannot import pycdio')
        return _getAllDevicePathsStatic()


def _getAllDevicePathsPyCdio():
    import pycdio
    import cdio

    # using FS_AUDIO here only makes it list the drive when an audio cd
    # is inserted
    # ticket 102: this cdio call returns a list of str, or a single str
    return _listify(cdio.get_devices_with_cap(pycdio.FS_MATCH_ALL, False))


def _getAllDevicePathsStatic():
    ret = []

    for c in ['/dev/cdrom', '/dev/cdrecorder']:
        if os.path.exists(c):
            ret.append(c)

    return ret


def getDeviceInfo(path):
    try:
        import cdio
    except ImportError:
        return None

    device = cdio.Device(path)
    ok, vendor, model, release = device.get_hwinfo()

    return (vendor, model, release)

########NEW FILE########
__FILENAME__ = encode
# -*- Mode: Python; test-case-name: morituri.test.test_common_encode -*-
# vi:si:et:sw=4:sts=4:ts=4

# Morituri - for those about to RIP

# Copyright (C) 2009 Thomas Vander Stichele

# This file is part of morituri.
#
# morituri is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# morituri is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with morituri.  If not, see <http://www.gnu.org/licenses/>.

import math
import os
import shutil
import tempfile

from morituri.common import common, log
from morituri.common import gstreamer as cgstreamer
from morituri.common import task as ctask

from morituri.extern.task import task, gstreamer


class Profile(log.Loggable):

    name = None
    extension = None
    pipeline = None
    losless = None

    def test(self):
        """
        Test if this profile will work.
        Can check for elements, ...
        """
        pass


class FlacProfile(Profile):
    name = 'flac'
    extension = 'flac'
    pipeline = 'flacenc name=tagger quality=8'
    lossless = True

    # FIXME: we should do something better than just printing ERRORS

    def test(self):

        # here to avoid import gst eating our options
        import gst

        plugin = gst.registry_get_default().find_plugin('flac')
        if not plugin:
            print 'ERROR: cannot find flac plugin'
            return False

        versionTuple = tuple([int(x) for x in plugin.get_version().split('.')])
        if len(versionTuple) < 4:
            versionTuple = versionTuple + (0, )
        if versionTuple > (0, 10, 9, 0) and versionTuple <= (0, 10, 15, 0):
            print 'ERROR: flacenc between 0.10.9 and 0.10.15 has a bug'
            return False

        return True

# FIXME: ffenc_alac does not have merge_tags


class AlacProfile(Profile):
    name = 'alac'
    extension = 'alac'
    pipeline = 'ffenc_alac'
    lossless = True

# FIXME: wavenc does not have merge_tags


class WavProfile(Profile):
    name = 'wav'
    extension = 'wav'
    pipeline = 'wavenc'
    lossless = True


class WavpackProfile(Profile):
    name = 'wavpack'
    extension = 'wv'
    pipeline = 'wavpackenc bitrate=0 name=tagger'
    lossless = True


class _LameProfile(Profile):
    extension = 'mp3'
    lossless = False

    def test(self):
        version = cgstreamer.elementFactoryVersion('lamemp3enc')
        self.debug('lamemp3enc version: %r', version)
        if version:
            t = tuple([int(s) for s in version.split('.')])
            if t >= (0, 10, 19):
                self.pipeline = self._lamemp3enc_pipeline
                return True

        version = cgstreamer.elementFactoryVersion('lame')
        self.debug('lame version: %r', version)
        if version:
            self.pipeline = self._lame_pipeline
            return True

        return False


class MP3Profile(_LameProfile):
    name = 'mp3'

    _lame_pipeline = 'lame name=tagger quality=0 ! id3v2mux'
    _lamemp3enc_pipeline = \
        'lamemp3enc name=tagger target=bitrate cbr=true bitrate=320 ! ' \
         'xingmux ! id3v2mux'


class MP3VBRProfile(_LameProfile):
    name = 'mp3vbr'

    _lame_pipeline = 'lame name=tagger ' \
        'vbr-quality=0 vbr=new vbr-mean-bitrate=192 ! ' \
        'id3v2mux'
    _lamemp3enc_pipeline = 'lamemp3enc name=tagger quality=0 ' \
        '! xingmux ! id3v2mux'


class VorbisProfile(Profile):
    name = 'vorbis'
    extension = 'oga'
    pipeline = 'audioconvert ! vorbisenc name=tagger ! oggmux'
    lossless = False


PROFILES = {
    'wav': WavProfile,
    'flac': FlacProfile,
    'alac': AlacProfile,
    'wavpack': WavpackProfile,
}

LOSSY_PROFILES = {
    'mp3': MP3Profile,
    'mp3vbr': MP3VBRProfile,
    'vorbis': VorbisProfile,
}

ALL_PROFILES = PROFILES.copy()
ALL_PROFILES.update(LOSSY_PROFILES)


class EncodeTask(ctask.GstPipelineTask):
    """
    I am a task that encodes a .wav file.
    I set tags too.
    I also calculate the peak level of the track.

    @param peak: the peak volume, from 0.0 to 1.0.  This is the sqrt of the
                 peak power.
    @type  peak: float
    """

    logCategory = 'EncodeTask'

    description = 'Encoding'
    peak = None

    def __init__(self, inpath, outpath, profile, taglist=None, what="track"):
        """
        @param profile: encoding profile
        @type  profile: L{Profile}
        """
        assert type(inpath) is unicode, "inpath %r is not unicode" % inpath
        assert type(outpath) is unicode, \
            "outpath %r is not unicode" % outpath

        self._inpath = inpath
        self._outpath = outpath
        self._taglist = taglist
        self._length = 0 # in samples

        self._level = None
        self._peakdB = None
        self._profile = profile

        self.description = "Encoding %s" % what
        self._profile.test()

        cgstreamer.removeAudioParsers()

    def getPipelineDesc(self):
        # start with an emit interval of one frame, because we end up setting
        # the final interval after paused and after processing some samples
        # already, which is too late
        interval = int(self.gst.SECOND / 75.0)
        return '''
            filesrc location="%s" !
            decodebin name=decoder !
            audio/x-raw-int,width=16,depth=16,channels=2 !
            level name=level interval=%d !
            %s ! identity name=identity !
            filesink location="%s" name=sink''' % (
                gstreamer.quoteParse(self._inpath).encode('utf-8'),
                interval,
                self._profile.pipeline,
                gstreamer.quoteParse(self._outpath).encode('utf-8'))

    def parsed(self):
        tagger = self.pipeline.get_by_name('tagger')

        # set tags
        if tagger and self._taglist:
            # FIXME: under which conditions do we not have merge_tags ?
            # See for example comment saying wavenc did not have it.
            try:
                tagger.merge_tags(self._taglist, self.gst.TAG_MERGE_APPEND)
            except AttributeError, e:
                self.warning('Could not merge tags: %r',
                    log.getExceptionMessage(e))

    def paused(self):
        # get length
        identity = self.pipeline.get_by_name('identity')
        self.debug('query duration')
        try:
            length, qformat = identity.query_duration(self.gst.FORMAT_DEFAULT)
        except self.gst.QueryError, e:
            self.setException(e)
            self.stop()
            return


        # wavparse 0.10.14 returns in bytes
        if qformat == self.gst.FORMAT_BYTES:
            self.debug('query returned in BYTES format')
            length /= 4
        self.debug('total length: %r', length)
        self._length = length

        duration = None
        try:
            duration, qformat = identity.query_duration(self.gst.FORMAT_TIME)
        except self.gst.QueryError, e:
            self.debug('Could not query duration')
        self._duration = duration

        # set up level callbacks
        # FIXME: publicize bus and reuse it instead of regetting and adding ?
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()

        bus.connect('message::element', self._message_element_cb)
        self._level = self.pipeline.get_by_name('level')

        # set an interval that is smaller than the duration
        # FIXME: check level and make sure it emits level up to the last
        # sample, even if input is small
        interval = self.gst.SECOND
        if interval > duration:
            interval = duration / 2
        self.debug('Setting level interval to %s, duration %s',
            self.gst.TIME_ARGS(interval), self.gst.TIME_ARGS(duration))
        self._level.set_property('interval', interval)
        # add a probe so we can track progress
        # we connect to level because this gives us offset in samples
        srcpad = self._level.get_static_pad('src')
        self.gst.debug('adding srcpad buffer probe to %r' % srcpad)
        ret = srcpad.add_buffer_probe(self._probe_handler)
        self.gst.debug('added srcpad buffer probe to %r: %r' % (srcpad, ret))

    def _probe_handler(self, pad, buffer):
        # update progress based on buffer offset (expected to be in samples)
        # versus length in samples
        # marshal to main thread
        self.schedule(0, self.setProgress,
            float(buffer.offset) / self._length)

        # don't drop the buffer
        return True

    def bus_eos_cb(self, bus, message):
        self.debug('eos, scheduling stop')
        self.schedule(0, self.stop)

    def _message_element_cb(self, bus, message):
        if message.src != self._level:
            return

        s = message.structure
        if s.get_name() != 'level':
            return


        if self._peakdB is None:
            self._peakdB = s['peak'][0]

        for p in s['peak']:
            if self._peakdB < p:
                self.log('higher peakdB found, now %r', self._peakdB)
                self._peakdB = p

        # FIXME: works around a bug on F-15 where buffer probes don't seem
        # to get triggered to update progress
        if self._duration is not None:
            self.schedule(0, self.setProgress,
                float(s['stream-time'] + s['duration']) / self._duration)

    def stopped(self):
        if self._peakdB is not None:
            self.debug('peakdB %r', self._peakdB)
            self.peak = math.sqrt(math.pow(10, self._peakdB / 10.0))
            return

        self.warning('No peak found.')

        if self._duration:
            self.warning('GStreamer level element did not send messages.')
            # workaround for when the file is too short to have volume ?
            if self._length == common.SAMPLES_PER_FRAME:
                self.warning('only one frame of audio, setting peak to 0.0')
                self.peak = 0.0


class TagReadTask(ctask.GstPipelineTask):
    """
    I am a task that reads tags.

    @ivar  taglist: the tag list read from the file.
    @type  taglist: L{gst.TagList}
    """

    logCategory = 'TagReadTask'

    description = 'Reading tags'

    taglist = None

    def __init__(self, path):
        """
        """
        assert type(path) is unicode, "path %r is not unicode" % path

        self._path = path

    def getPipelineDesc(self):
        return '''
            filesrc location="%s" !
            decodebin name=decoder !
            fakesink''' % (
                gstreamer.quoteParse(self._path).encode('utf-8'))

    def bus_eos_cb(self, bus, message):
        self.debug('eos, scheduling stop')
        self.schedule(0, self.stop)

    def bus_tag_cb(self, bus, message):
        taglist = message.parse_tag()
        self.debug('tag_cb, %d tags' % len(taglist.keys()))
        if not self.taglist:
            self.taglist = taglist
        else:
            import gst
            self.taglist = self.taglist.merge(taglist, gst.TAG_MERGE_REPLACE)


class TagWriteTask(ctask.LoggableTask):
    """
    I am a task that retags an encoded file.
    """

    logCategory = 'TagWriteTask'

    description = 'Writing tags'

    def __init__(self, inpath, outpath, taglist=None):
        """
        """
        assert type(inpath) is unicode, "inpath %r is not unicode" % inpath
        assert type(outpath) is unicode, "outpath %r is not unicode" % outpath

        self._inpath = inpath
        self._outpath = outpath
        self._taglist = taglist

    def start(self, runner):
        task.Task.start(self, runner)

        # here to avoid import gst eating our options
        import gst

        # FIXME: this hardcodes flac; we should be using the correct
        #        tag element instead
        self._pipeline = gst.parse_launch('''
            filesrc location="%s" !
            flactag name=tagger !
            filesink location="%s"''' % (
                gstreamer.quoteParse(self._inpath).encode('utf-8'),
                gstreamer.quoteParse(self._outpath).encode('utf-8')))

        # set tags
        tagger = self._pipeline.get_by_name('tagger')
        if self._taglist:
            tagger.merge_tags(self._taglist, gst.TAG_MERGE_APPEND)

        self.debug('pausing pipeline')
        self._pipeline.set_state(gst.STATE_PAUSED)
        self._pipeline.get_state()
        self.debug('paused pipeline')

        # add eos handling
        bus = self._pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect('message::eos', self._message_eos_cb)

        self.debug('scheduling setting to play')
        # since set_state returns non-False, adding it as timeout_add
        # will repeatedly call it, and block the main loop; so
        #   gobject.timeout_add(0L, self._pipeline.set_state,
        #       gst.STATE_PLAYING)
        # would not work.

        def play():
            self._pipeline.set_state(gst.STATE_PLAYING)
            return False
        self.schedule(0, play)

        #self._pipeline.set_state(gst.STATE_PLAYING)
        self.debug('scheduled setting to play')

    def _message_eos_cb(self, bus, message):
        self.debug('eos, scheduling stop')
        self.schedule(0, self.stop)

    def stop(self):
        # here to avoid import gst eating our options
        import gst

        self.debug('stopping')
        self.debug('setting state to NULL')
        self._pipeline.set_state(gst.STATE_NULL)
        self.debug('set state to NULL')
        task.Task.stop(self)


class SafeRetagTask(ctask.LoggableMultiSeparateTask):
    """
    I am a task that retags an encoded file safely in place.
    First of all, if the new tags are the same as the old ones, it doesn't
    do anything.
    If the tags are not the same, then the file gets retagged, but only
    if the decodes of the original and retagged file checksum the same.

    @ivar changed: True if the tags have changed (and hence an output file is
                   generated)
    """

    logCategory = 'SafeRetagTask'

    description = 'Retagging'

    changed = False

    def __init__(self, path, taglist=None):
        """
        """
        assert type(path) is unicode, "path %r is not unicode" % path

        task.MultiSeparateTask.__init__(self)

        self._path = path
        self._taglist = taglist.copy()

        self.tasks = [TagReadTask(path), ]

    def stopped(self, taskk):
        from morituri.common import checksum

        if not taskk.exception:
            # Check if the tags are different or not
            if taskk == self.tasks[0]:
                taglist = taskk.taglist.copy()
                if common.tagListEquals(taglist, self._taglist):
                    self.debug('tags are already fine: %r',
                        common.tagListToDict(taglist))
                else:
                    # need to retag
                    self.debug('tags need to be rewritten')
                    self.debug('Current tags: %r, new tags: %r',
                        common.tagListToDict(taglist),
                        common.tagListToDict(self._taglist))
                    assert common.tagListToDict(taglist) \
                        != common.tagListToDict(self._taglist)
                    self.tasks.append(checksum.CRC32Task(self._path))
                    self._fd, self._tmppath = tempfile.mkstemp(
                        dir=os.path.dirname(self._path), suffix=u'.morituri')
                    self.tasks.append(TagWriteTask(self._path,
                        self._tmppath, self._taglist))
                    self.tasks.append(checksum.CRC32Task(self._tmppath))
                    self.tasks.append(TagReadTask(self._tmppath))
            elif len(self.tasks) > 1 and taskk == self.tasks[4]:
                if common.tagListEquals(self.tasks[4].taglist, self._taglist):
                    self.debug('tags written successfully')
                    c1 = self.tasks[1].checksum
                    c2 = self.tasks[3].checksum
                    self.debug('comparing checksums %08x and %08x' % (c1, c2))
                    if c1 == c2:
                        # data is fine, so we can now move
                        # but first, copy original mode to our temporary file
                        shutil.copymode(self._path, self._tmppath)
                        self.debug('moving temporary file to %r' % self._path)
                        os.rename(self._tmppath, self._path)
                        self.changed = True
                    else:
                        # FIXME: don't raise TypeError
                        e = TypeError("Checksums failed")
                        self.setAndRaiseException(e)
                else:
                    self.debug('failed to update tags, only have %r',
                        common.tagListToDict(self.tasks[4].taglist))
                    self.debug('difference: %r',
                        common.tagListDifference(self.tasks[4].taglist,
                            self._taglist))
                    os.unlink(self._tmppath)
                    e = TypeError("Tags not written")
                    self.setAndRaiseException(e)

        task.MultiSeparateTask.stopped(self, taskk)

########NEW FILE########
__FILENAME__ = gstreamer
# -*- Mode: Python; test-case-name: morituri.test.test_common_gstreamer -*-
# vi:si:et:sw=4:sts=4:ts=4

# Morituri - for those about to RIP

# Copyright (C) 2009 Thomas Vander Stichele

# This file is part of morituri.
#
# morituri is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# morituri is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with morituri.  If not, see <http://www.gnu.org/licenses/>.

import re
import commands

from morituri.common import log

# workaround for issue #64


def removeAudioParsers():
    log.debug('gstreamer', 'Removing buggy audioparsers plugin if needed')

    import gst
    registry = gst.registry_get_default()

    plugin = registry.find_plugin("audioparsersbad")
    if plugin:
        # always remove from bad
        log.debug('gstreamer', 'removing audioparsersbad plugin from registry')
        registry.remove_plugin(plugin)

    plugin = registry.find_plugin("audioparsers")
    if plugin:
        log.debug('gstreamer', 'removing audioparsers plugin from %s %s',
            plugin.get_source(), plugin.get_version())

        # the query bug was fixed after 0.10.30 and before 0.10.31
        # the seek bug is still there though
        # if plugin.get_source() == 'gst-plugins-good' \
        #   and plugin.get_version() > '0.10.30.1':
        #    return

        registry.remove_plugin(plugin)

def gstreamerVersion():
    import gst
    return _versionify(gst.version())

def gstPythonVersion():
    import gst
    return _versionify(gst.pygst_version)

_VERSION_RE = re.compile(
    "Version:\s*(?P<version>[\d.]+)")

def elementFactoryVersion(name):
    # surprisingly, there is no python way to get from an element factory
    # to its plugin and its version directly; you can only compare
    # with required versions
    # Let's use gst-inspect-0.10 and wave hands and assume it points to the
    # same version that python uses
    output = commands.getoutput('gst-inspect-0.10 %s | grep Version' % name)
    m = _VERSION_RE.search(output)
    if not m:
        return None
    return m.group('version')


def _versionify(tup):
    l = list(tup)
    if len(l) == 4 and l[3] == 0:
        l = l[:3]
    v = [str(n) for n in l]
    return ".".join(v)

########NEW FILE########
__FILENAME__ = log
# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# Morituri - for those about to RIP

# Copyright (C) 2009 Thomas Vander Stichele

# This file is part of morituri.
#
# morituri is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# morituri is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with morituri.  If not, see <http://www.gnu.org/licenses/>.

"""
Logging
"""

from morituri.extern.log import log as externlog
from morituri.extern.log.log import *


def init():
    externlog.init('RIP_DEBUG')
    externlog.setPackageScrubList('morituri')

########NEW FILE########
__FILENAME__ = logcommand
# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# Morituri - for those about to RIP

# Copyright (C) 2009 Thomas Vander Stichele

# This file is part of morituri.
#
# morituri is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# morituri is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with morituri.  If not, see <http://www.gnu.org/licenses/>.

"""
Logging Command.
"""

from morituri.extern.command import command
from morituri.common import log


class LogCommand(command.Command, log.Loggable):

    def __init__(self, parentCommand=None, **kwargs):
        command.Command.__init__(self, parentCommand, **kwargs)
        self.logCategory = self.name

    # command.Command has a fake debug method, so choose the right one

    def debug(self, format, *args):
        kwargs = {}
        log.Loggable.doLog(self, log.DEBUG, -2, format, *args, **kwargs)

########NEW FILE########
__FILENAME__ = mbngs
# -*- Mode: Python; test-case-name: morituri.test.test_common_mbngs -*-
# vi:si:et:sw=4:sts=4:ts=4

# Morituri - for those about to RIP

# Copyright (C) 2009, 2010, 2011 Thomas Vander Stichele

# This file is part of morituri.
#
# morituri is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# morituri is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with morituri.  If not, see <http://www.gnu.org/licenses/>.

"""
Handles communication with the musicbrainz server using NGS.
"""

import urllib2

from morituri.common import log


VA_ID = "89ad4ac3-39f7-470e-963a-56509c546377" # Various Artists


class MusicBrainzException(Exception):

    def __init__(self, exc):
        self.args = (exc, )
        self.exception = exc


class NotFoundException(MusicBrainzException):

    def __str__(self):
        return "Disc not found in MusicBrainz"


class TrackMetadata(object):
    artist = None
    title = None
    duration = None # in ms
    mbid = None
    sortName = None
    mbidArtist = None


class DiscMetadata(object):
    """
    @param artist:       artist(s) name
    @param sortName:     album artist sort name
    @param release:      earliest release date, in YYYY-MM-DD
    @type  release:      unicode
    @param title:        title of the disc (with disambiguation)
    @param releaseTitle: title of the release (without disambiguation)
    @type  tracks:       C{list} of L{TrackMetadata}
    """
    artist = None
    sortName = None
    title = None
    various = False
    tracks = None
    release = None

    releaseTitle = None
    releaseType = None

    mbid = None
    mbidArtist = None
    url = None

    catalogNumber = None
    barcode = None

    def __init__(self):
        self.tracks = []


def _record(record, which, name, what):
    # optionally record to disc as a JSON serialization
    if record:
        import json
        filename = 'morituri.%s.%s.json' % (which, name)
        handle = open(filename, 'w')
        handle.write(json.dumps(what))
        handle.close()
        log.info('mbngs', 'Wrote %s %s to %s', which, name, filename)

# credit is of the form [dict, str, dict, ... ]
# e.g. [
#   {'artist': {
#     'sort-name': 'Sukilove',
#     'id': '5f4af6cf-a1b8-4e51-a811-befed399a1c6',
#     'name': 'Sukilove'
#   }}, ' & ', {
#   'artist': {
#     'sort-name': 'Blackie and the Oohoos',
#     'id': '028a9dc7-f5ef-43c2-866b-08d69ffff363',
#     'name': 'Blackie & the Oohoos'}}]
# or
# [{'artist':
#    {'sort-name': 'Pixies',
#     'id': 'b6b2bb8d-54a9-491f-9607-7b546023b433', 'name': 'Pixies'}}]


class _Credit(list):
    """
    I am a representation of an artist-credit in musicbrainz for a disc
    or track.
    """

    def joiner(self, attributeGetter, joinString=None):
        res = []

        for item in self:
            if isinstance(item, dict):
                res.append(attributeGetter(item))
            else:
                if not joinString:
                    res.append(item)
                else:
                    res.append(joinString)

        return "".join(res)


    def getSortName(self):
        return self.joiner(lambda i: i.get('artist').get('sort-name', None))

    def getName(self):
        return self.joiner(lambda i: i.get('artist').get('name', None))

    def getIds(self):
        return self.joiner(lambda i: i.get('artist').get('id', None),
            joinString=";")


def _getMetadata(releaseShort, release, discid):
    """
    @type  release: C{dict}
    @param release: a release dict as returned in the value for key release
                    from get_release_by_id

    @rtype: L{DiscMetadata} or None
    """
    log.debug('program', 'getMetadata for release id %r',
        release['id'])
    if not release['id']:
        log.warning('program', 'No id for release %r', release)
        return None

    assert release['id'], 'Release does not have an id'

    discMD = DiscMetadata()

    discMD.releaseType = releaseShort.get('release-group', {}).get('type')
    discCredit = _Credit(release['artist-credit'])

    # FIXME: is there a better way to check for VA ?
    discMD.various = False
    if discCredit[0]['artist']['id'] == VA_ID:
        discMD.various = True


    if len(discCredit) > 1:
        log.debug('mbngs', 'artist-credit more than 1: %r', discCredit)

    albumArtistName = discCredit.getName()

    # getUniqueName gets disambiguating names like Muse (UK rock band)
    discMD.artist = albumArtistName
    discMD.sortName = discCredit.getSortName()
    # FIXME: is format str ?
    if not 'date' in release:
        log.warning('mbngs', 'Release %r does not have date', release)
    else:
        discMD.release = release['date']

    discMD.mbid = release['id']
    discMD.mbidArtist = discCredit.getIds()
    discMD.url = 'http://musicbrainz.org/release/' + release['id']

    discMD.barcode = release.get('barcode', None)
    lil = release.get('label-info-list', [{}])
    if lil:
        discMD.catalogNumber = lil[0].get('catalog-number')
    tainted = False
    duration = 0

    # only show discs from medium-list->disc-list with matching discid
    for medium in release['medium-list']:
        for disc in medium['disc-list']:
            if disc['id'] == discid:
                title = release['title']
                discMD.releaseTitle = title
                if 'disambiguation' in release:
                    title += " (%s)" % release['disambiguation']
                count = len(release['medium-list'])
                if count > 1:
                    title += ' (Disc %d of %d)' % (
                        int(medium['position']), count)
                if 'title' in medium:
                    title += ": %s" % medium['title']
                discMD.title = title
                for t in medium['track-list']:
                    track = TrackMetadata()
                    trackCredit = _Credit(t['recording']['artist-credit'])
                    if len(trackCredit) > 1:
                        log.debug('mbngs',
                            'artist-credit more than 1: %r', trackCredit)

                    # FIXME: leftover comment, need an example
                    # various artists discs can have tracks with no artist
                    track.artist = trackCredit.getName()
                    track.sortName = trackCredit.getSortName()
                    track.mbidArtist = trackCredit.getIds()

                    track.title = t['recording']['title']
                    track.mbid = t['recording']['id']

                    # FIXME: unit of duration ?
                    track.duration = int(t['recording'].get('length', 0))
                    if not track.duration:
                        log.warning('getMetadata',
                            'track %r (%r) does not have duration' % (
                                track.title, track.mbid))
                        tainted = True
                    else:
                        duration += track.duration

                    discMD.tracks.append(track)

                if not tainted:
                    discMD.duration = duration
                else:
                    discMD.duration = 0

    return discMD


# see http://bugs.musicbrainz.org/browser/python-musicbrainz2/trunk/examples/
#     ripper.py


def musicbrainz(discid, record=False):
    """
    Based on a MusicBrainz disc id, get a list of DiscMetadata objects
    for the given disc id.

    Example disc id: Mj48G109whzEmAbPBoGvd4KyCS4-

    @type  discid: str

    @rtype: list of L{DiscMetadata}
    """
    log.debug('musicbrainz', 'looking up results for discid %r', discid)
    from morituri.extern.musicbrainzngs import musicbrainz

    ret = []

    try:
        result = musicbrainz.get_releases_by_discid(discid,
            includes=["artists", "recordings", "release-groups"])
    except musicbrainz.ResponseError, e:
        if isinstance(e.cause, urllib2.HTTPError):
            if e.cause.code == 404:
                raise NotFoundException(e)

        raise MusicBrainzException(e)

    # No disc matching this DiscID has been found.
    if len(result) == 0:
        return None

    log.debug('musicbrainzngs', 'found %d releases for discid %r',
        len(result['disc']['release-list']),
        discid)
    _record(record, 'releases', discid, result)

    # Display the returned results to the user.

    import json
    for release in result['disc']['release-list']:
        formatted = json.dumps(release, sort_keys=False, indent=4)
        log.debug('program', 'result %s: artist %r, title %r' % (
            formatted, release['artist-credit-phrase'], release['title']))

        # to get titles of recordings, we need to query the release with
        # artist-credits

        res = musicbrainz.get_release_by_id(release['id'],
            includes=["artists", "artist-credits", "recordings", "discids",
                "labels"])
        _record(record, 'release', release['id'], res)
        releaseDetail = res['release']
        formatted = json.dumps(releaseDetail, sort_keys=False, indent=4)
        log.debug('program', 'release %s' % formatted)

        md = _getMetadata(release, releaseDetail, discid)
        if md:
            log.debug('program', 'duration %r', md.duration)
            ret.append(md)

    return ret

########NEW FILE########
__FILENAME__ = path
# -*- Mode: Python; test-case-name: morituri.test.test_common_path -*-
# vi:si:et:sw=4:sts=4:ts=4

# Morituri - for those about to RIP

# Copyright (C) 2009 Thomas Vander Stichele

# This file is part of morituri.
#
# morituri is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# morituri is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with morituri.  If not, see <http://www.gnu.org/licenses/>.

import re


class PathFilter(object):
    """
    I filter path components for safe storage on file systems.
    """

    def __init__(self, slashes=True, quotes=True, fat=True, special=False):
        """
        @param slashes: whether to convert slashes to dashes
        @param quotes:  whether to normalize quotes
        @param fat:     whether to strip characters illegal on FAT filesystems
        @param special: whether to strip special characters
        """
        self._slashes = slashes
        self._quotes = quotes
        self._fat = fat
        self._special = special

    def filter(self, path):
        if self._slashes:
            path = re.sub(r'[/\\]', '-', path, re.UNICODE)

        def separators(path):
            # replace separators with a space-hyphen or hyphen
            path = re.sub(r'[:]', ' -', path, re.UNICODE)
            path = re.sub(r'[\|]', '-', path, re.UNICODE)
            return path

        # change all fancy single/double quotes to normal quotes
        if self._quotes:
            path = re.sub(ur'[\xc2\xb4\u2018\u2019\u201b]', "'", path,
                re.UNICODE)
            path = re.sub(ur'[\u201c\u201d\u201f]', '"', path, re.UNICODE)

        if self._special:
            path = separators(path)
            path = re.sub(r'[\*\?&!\'\"\$\(\)`{}\[\]<>]', '_', path, re.UNICODE)

        if self._fat:
            path = separators(path)
            # : and | already gone, but leave them here for reference
            path = re.sub(r'[:\*\?"<>|"]', '_', path, re.UNICODE)

        return path

########NEW FILE########
__FILENAME__ = program
# -*- Mode: Python; test-case-name: morituri.test.test_common_program -*-
# vi:si:et:sw=4:sts=4:ts=4

# Morituri - for those about to RIP

# Copyright (C) 2009, 2010, 2011 Thomas Vander Stichele

# This file is part of morituri.
#
# morituri is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# morituri is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with morituri.  If not, see <http://www.gnu.org/licenses/>.

"""
Common functionality and class for all programs using morituri.
"""

import os
import sys
import time

from morituri.common import common, log, mbngs, cache, path
from morituri.program import cdrdao, cdparanoia
from morituri.image import image

from morituri.extern.task import task, gstreamer
from morituri.extern.musicbrainzngs import musicbrainz


# FIXME: should Program have a runner ?


class Program(log.Loggable):
    """
    I maintain program state and functionality.

    @ivar metadata:
    @type metadata: L{mbngs.DiscMetadata}
    @ivar result:   the rip's result
    @type result:   L{result.RipResult}
    @type outdir:   unicode
    @type config:   L{morituri.common.config.Config}
    """

    cuePath = None
    logPath = None
    metadata = None
    outdir = None
    result = None

    _stdout = None

    def __init__(self, config, record=False, stdout=sys.stdout):
        """
        @param record: whether to record results of API calls for playback.
        """
        self._record = record
        self._cache = cache.ResultCache()
        self._stdout = stdout
        self._config = config

        d = {}

        for key, default in {
            'fat': True,
            'special': False
        }.items():
            value = None
            value = self._config.getboolean('main', 'path_filter_'+ key)
            if value is None:
                value = default

            d[key] = value

        self._filter = path.PathFilter(**d)

    def setWorkingDirectory(self, workingDirectory):
        if workingDirectory:
            self.info('Changing to working directory %s' % workingDirectory)
            os.chdir(workingDirectory)

    def loadDevice(self, device):
        """
        Load the given device.
        """
        os.system('eject -t %s' % device)

    def ejectDevice(self, device):
        """
        Eject the given device.
        """
        os.system('eject %s' % device)

    def unmountDevice(self, device):
        """
        Unmount the given device if it is mounted, as happens with automounted
        data tracks.

        If the given device is a symlink, the target will be checked.
        """
        device = os.path.realpath(device)
        self.debug('possibly unmount real path %r' % device)
        proc = open('/proc/mounts').read()
        if device in proc:
            print 'Device %s is mounted, unmounting' % device
            os.system('umount %s' % device)

    def getFastToc(self, runner, toc_pickle, device):
        """
        Retrieve the normal TOC table from a toc pickle or the drive.
        Also retrieves the cdrdao version

        @rtype: tuple of L{table.Table}, str
        """
        def function(r, t):
            r.run(t)

        ptoc = cache.Persister(toc_pickle or None)
        if not ptoc.object:
            tries = 0
            while True:
                tries += 1
                t = cdrdao.ReadTOCTask(device=device)
                try:
                    function(runner, t)
                    break
                except:
                    if tries > 3:
                        raise
                    self.debug('failed to read TOC after %d tries, retrying' % tries)

            version = t.tasks[1].parser.version
            from pkg_resources import parse_version as V
            # we've built a cdrdao 1.2.3rc2 modified package with the patch
            if V(version) < V('1.2.3rc2p1'):
                self.stdout.write('Warning: cdrdao older than 1.2.3 has a '
                    'pre-gap length bug.\n'
                    'See http://sourceforge.net/tracker/?func=detail'
                    '&aid=604751&group_id=2171&atid=102171\n')
            ptoc.persist(t.table)
        toc = ptoc.object
        assert toc.hasTOC()
        return toc

    def getTable(self, runner, cddbdiscid, mbdiscid, device):
        """
        Retrieve the Table either from the cache or the drive.

        @rtype: L{table.Table}
        """
        tcache = cache.TableCache()
        ptable = tcache.get(cddbdiscid, mbdiscid)

        if not ptable.object:
            self.debug('getTable: cddbdiscid %s, mbdiscid %s not in cache, '
                'reading table' % (
                cddbdiscid, mbdiscid))
            t = cdrdao.ReadTableTask(device=device)
            runner.run(t)
            ptable.persist(t.table)
            self.debug('getTable: read table %r' % t.table)
        else:
            self.debug('getTable: cddbdiscid %s, mbdiscid %s in cache' % (
                cddbdiscid, mbdiscid))
            ptable.object.unpickled()
            self.debug('getTable: loaded table %r' % ptable.object)
        itable = ptable.object
        assert itable.hasTOC()

        self.result.table = itable

        self.debug('getTable: returning table with mb id %s' %
            itable.getMusicBrainzDiscId())
        return itable

    # FIXME: the cache should be model/offset specific

    def getRipResult(self, cddbdiscid):
        """
        Retrieve the persistable RipResult either from our cache (from a
        previous, possibly aborted rip), or return a new one.

        @rtype: L{result.RipResult}
        """
        assert self.result is None

        self._presult = self._cache.getRipResult(cddbdiscid)
        self.result = self._presult.object

        return self.result

    def saveRipResult(self):
        self._presult.persist()

    def getPath(self, outdir, template, mbdiscid, i, profile=None,
        disambiguate=False):
        """
        Based on the template, get a complete path for the given track,
        minus extension.
        Also works for the disc name, using disc variables for the template.

        @param outdir:   the directory where to write the files
        @type  outdir:   unicode
        @param template: the template for writing the file
        @type  template: unicode
        @param i:        track number (0 for HTOA, or for disc)
        @type  i:        int
        @type  profile:  L{morituri.common.encode.Profile}

        @rtype: unicode
        """
        assert type(outdir) is unicode, "%r is not unicode" % outdir
        assert type(template) is unicode, "%r is not unicode" % template

        # the template is similar to grip, except for %s/%S/%r/%R
        # see #gripswitches

        # returns without extension

        v = {}

        v['t'] = '%02d' % i

        # default values
        v['A'] = 'Unknown Artist'
        v['d'] = mbdiscid # fallback for title
        v['r'] = 'unknown'
        v['R'] = 'Unknown'
        v['B'] = '' # barcode
        v['C'] = '' # catalog number
        v['x'] = profile and profile.extension or 'unknown'
        v['X'] = v['x'].upper()
        v['y'] = '0000'

        v['a'] = v['A']
        if i == 0:
            v['n'] = 'Hidden Track One Audio'
        else:
            v['n'] = 'Unknown Track %d' % i


        if self.metadata:
            release = self.metadata.release or '0000'
            v['y'] = release[:4]
            v['A'] = self._filter.filter(self.metadata.artist)
            v['S'] = self._filter.filter(self.metadata.sortName)
            v['d'] = self._filter.filter(self.metadata.title)
            v['B'] = self.metadata.barcode
            v['C'] = self.metadata.catalogNumber
            if self.metadata.releaseType:
                v['R'] = self.metadata.releaseType
                v['r'] = self.metadata.releaseType.lower()
            if i > 0:
                try:
                    v['a'] = self._filter.filter(self.metadata.tracks[i - 1].artist)
                    v['s'] = self._filter.filter(
                        self.metadata.tracks[i - 1].sortName)
                    v['n'] = self._filter.filter(self.metadata.tracks[i - 1].title)
                except IndexError, e:
                    print 'ERROR: no track %d found, %r' % (i, e)
                    raise
            else:
                # htoa defaults to disc's artist
                v['a'] = self._filter.filter(self.metadata.artist)

        # when disambiguating, use catalogNumber then barcode
        if disambiguate:
            templateParts = list(os.path.split(template))
            if self.metadata.catalogNumber:
                templateParts[-2] += ' (%s)' % self.metadata.catalogNumber
            elif self.metadata.barcode:
                templateParts[-2] += ' (%s)' % self.metadata.barcode
            template = os.path.join(*templateParts)
            self.debug('Disambiguated template to %r' % template)

        import re
        template = re.sub(r'%(\w)', r'%(\1)s', template)

        ret = os.path.join(outdir, template % v)



        return ret

    def getCDDB(self, cddbdiscid):
        """
        @param cddbdiscid: list of id, tracks, offsets, seconds

        @rtype: str
        """
        # FIXME: convert to nonblocking?
        import CDDB
        try:
            code, md = CDDB.query(cddbdiscid)
            self.debug('CDDB query result: %r, %r', code, md)
            if code == 200:
                return md['title']

        except IOError, e:
            # FIXME: for some reason errno is a str ?
            if e.errno == 'socket error':
                self._stdout.write("Warning: network error: %r\n" % (e, ))
            else:
                raise

        return None

    def getMusicBrainz(self, ittoc, mbdiscid, release=None):
        """
        @type  ittoc: L{morituri.image.table.Table}
        """
        # look up disc on musicbrainz
        self._stdout.write('Disc duration: %s, %d audio tracks\n' % (
            common.formatTime(ittoc.duration() / 1000.0),
            ittoc.getAudioTracks()))
        self.debug('MusicBrainz submit url: %r',
            ittoc.getMusicBrainzSubmitURL())
        ret = None

        metadatas = None
        e = None

        for _ in range(0, 4):
            try:
                metadatas = mbngs.musicbrainz(mbdiscid,
                    record=self._record)
            except mbngs.NotFoundException, e:
                break
            except musicbrainz.NetworkError, e:
                self._stdout.write("Warning: network error: %r\n" % (e, ))
                break
            except mbngs.MusicBrainzException, e:
                self._stdout.write("Warning: %r\n" % (e, ))
                time.sleep(5)
                continue

        if not metadatas:
            if e:
                self._stdout.write("Error: %r\n" % (e, ))
            self._stdout.write('Continuing without metadata\n')

        if metadatas:
            deltas = {}

            self._stdout.write('\nMatching releases:\n')

            for metadata in metadatas:
                self._stdout.write('\n')
                self._stdout.write('Artist  : %s\n' %
                    metadata.artist.encode('utf-8'))
                self._stdout.write('Title   : %s\n' %
                    metadata.title.encode('utf-8'))
                self._stdout.write('Duration: %s\n' %
                    common.formatTime(metadata.duration / 1000.0))
                self._stdout.write('URL     : %s\n' % metadata.url)
                self._stdout.write('Release : %s\n' % metadata.mbid)
                self._stdout.write('Type    : %s\n' % metadata.releaseType)

                delta = abs(metadata.duration - ittoc.duration())
                if not delta in deltas:
                    deltas[delta] = []
                deltas[delta].append(metadata)

            if release:
                metadatas = [m for m in metadatas if m.url.endswith(release)]
                self.debug('Asked for release %r, only kept %r',
                    release, metadatas)
                if len(metadatas) == 1:
                    self._stdout.write('\n')
                    self._stdout.write('Picked requested release id %s\n' %
                        release)
                    self._stdout.write('Artist : %s\n' %
                        metadatas[0].artist.encode('utf-8'))
                    self._stdout.write('Title :  %s\n' %
                        metadatas[0].title.encode('utf-8'))
                elif not metadatas:
                    self._stdout.write(
                        "Requested release id '%s', "
                        "but none of the found releases match\n" % release)
                    return
            else:
                # Select the release that most closely matches the duration.
                lowest = min(deltas.keys())

                # If we have multiple, make sure they match
                metadatas = deltas[lowest]

            if len(metadatas) > 1:
                artist = metadatas[0].artist
                releaseTitle = metadatas[0].releaseTitle
                for i, metadata in enumerate(metadatas):
                    if not artist == metadata.artist:
                        self.warning("artist 0: %r and artist %d: %r "
                            "are not the same" % (
                                artist, i, metadata.artist))
                    if not releaseTitle == metadata.releaseTitle:
                        self.warning("title 0: %r and title %d: %r "
                            "are not the same" % (
                                releaseTitle, i, metadata.releaseTitle))

                if (not release and len(deltas.keys()) > 1):
                    self._stdout.write('\n')
                    self._stdout.write('Picked closest match in duration.\n')
                    self._stdout.write('Others may be wrong in musicbrainz, '
                        'please correct.\n')
                    self._stdout.write('Artist : %s\n' %
                        artist.encode('utf-8'))
                    self._stdout.write('Title :  %s\n' %
                        metadatas[0].title.encode('utf-8'))

            # Select one of the returned releases. We just pick the first one.
            ret = metadatas[0]
        else:
            self._stdout.write(
                'Submit this disc to MusicBrainz at the above URL.\n')
            ret = None

        self._stdout.write('\n')
        return ret

    def getTagList(self, number):
        """
        Based on the metadata, get a gst.TagList for the given track.

        @param number:   track number (0 for HTOA)
        @type  number:   int

        @rtype: L{gst.TagList}
        """
        trackArtist = u'Unknown Artist'
        albumArtist = u'Unknown Artist'
        disc = u'Unknown Disc'
        title = u'Unknown Track'

        if self.metadata:
            trackArtist = self.metadata.artist
            albumArtist = self.metadata.artist
            disc = self.metadata.title
            mbidAlbum = self.metadata.mbid
            mbidTrackAlbum = self.metadata.mbidArtist

            if number > 0:
                try:
                    track = self.metadata.tracks[number - 1]
                    trackArtist = track.artist
                    title = track.title
                    mbidTrack = track.mbid
                    mbidTrackArtist = track.mbidArtist
                except IndexError, e:
                    print 'ERROR: no track %d found, %r' % (number, e)
                    raise
            else:
                # htoa defaults to disc's artist
                title = 'Hidden Track One Audio'

        # here to avoid import gst eating our options
        import gst

        ret = gst.TagList()

        # gst-python 0.10.15.1 does not handle unicode -> utf8 string
        # conversion
        # see http://bugzilla.gnome.org/show_bug.cgi?id=584445
        if self.metadata and self.metadata.various:
            ret["album-artist"] = albumArtist.encode('utf-8')
        ret[gst.TAG_ARTIST] = trackArtist.encode('utf-8')
        ret[gst.TAG_TITLE] = title.encode('utf-8')
        ret[gst.TAG_ALBUM] = disc.encode('utf-8')

        # gst-python 0.10.15.1 does not handle tags that are UINT
        # see gst-python commit 26fa6dd184a8d6d103eaddf5f12bd7e5144413fb
        # FIXME: no way to compare against 'master' version after 0.10.15
        if gst.pygst_version >= (0, 10, 15):
            ret[gst.TAG_TRACK_NUMBER] = number
        if self.metadata:
            # works, but not sure we want this
            # if gst.pygst_version >= (0, 10, 15):
            #     ret[gst.TAG_TRACK_COUNT] = len(self.metadata.tracks)
            # hack to get a GstDate which we cannot instantiate directly in
            # 0.10.15.1
            # FIXME: The dates are strings and must have the format 'YYYY',
            # 'YYYY-MM' or 'YYYY-MM-DD'.
            # GstDate expects a full date, so default to
            # Jan and 1st if MM and DD are missing
            date = self.metadata.release
            if date:
                log.debug('metadata',
                    'Converting release date %r to structure', date)
                if len(date) == 4:
                    date += '-01'
                if len(date) == 7:
                    date += '-01'

                s = gst.structure_from_string('hi,date=(GstDate)%s' %
                    str(date))
                ret[gst.TAG_DATE] = s['date']

            # no musicbrainz info for htoa tracks
            if number > 0:
                ret["musicbrainz-trackid"] = mbidTrack
                ret["musicbrainz-artistid"] = mbidTrackArtist
                ret["musicbrainz-albumid"] = mbidAlbum
                ret["musicbrainz-albumartistid"] = mbidTrackAlbum

        # FIXME: gst.TAG_ISRC

        return ret

    def getHTOA(self):
        """
        Check if we have hidden track one audio.

        @returns: tuple of (start, stop), or None
        """
        track = self.result.table.tracks[0]
        try:
            index = track.getIndex(0)
        except KeyError:
            return None

        start = index.absolute
        stop = track.getIndex(1).absolute - 1
        return (start, stop)

    def verifyTrack(self, runner, trackResult):
        # here to avoid import gst eating our options
        from morituri.common import checksum

        t = checksum.CRC32Task(trackResult.filename)

        try:
            runner.run(t)
        except task.TaskException, e:
            if isinstance(e.exception, common.MissingFrames):
                self.warning('missing frames for %r' % trackResult.filename)
                return False
            elif isinstance(e.exception, gstreamer.GstException):
                self.warning('GstException %r' % (e.exception, ))
                return False
            else:
                raise

        ret = trackResult.testcrc == t.checksum
        log.debug('program',
            'verifyTrack: track result crc %r, file crc %r, result %r',
            trackResult.testcrc, t.checksum, ret)
        return ret

    def ripTrack(self, runner, trackResult, offset, device, profile, taglist,
        what=None):
        """
        Ripping the track may change the track's filename as stored in
        trackResult.

        @param trackResult: the object to store information in.
        @type  trackResult: L{result.TrackResult}
        @param number:      track number (1-based)
        @type  number:      int
        """
        if trackResult.number == 0:
            start, stop = self.getHTOA()
        else:
            start = self.result.table.getTrackStart(trackResult.number)
            stop = self.result.table.getTrackEnd(trackResult.number)

        dirname = os.path.dirname(trackResult.filename)
        if not os.path.exists(dirname):
            os.makedirs(dirname)

        if not what:
            what='track %d' % (trackResult.number, )

        t = cdparanoia.ReadVerifyTrackTask(trackResult.filename,
            self.result.table, start, stop,
            offset=offset,
            device=device,
            profile=profile,
            taglist=taglist,
            what=what)

        runner.run(t)

        self.debug('ripped track')
        self.debug('test speed %.3f/%.3f seconds' % (
            t.testspeed, t.testduration))
        self.debug('copy speed %.3f/%.3f seconds' % (
            t.copyspeed, t.copyduration))
        trackResult.testcrc = t.testchecksum
        trackResult.copycrc = t.copychecksum
        trackResult.peak = t.peak
        trackResult.quality = t.quality
        trackResult.testspeed = t.testspeed
        trackResult.copyspeed = t.copyspeed
        # we want rerips to add cumulatively to the time
        trackResult.testduration += t.testduration
        trackResult.copyduration += t.copyduration

        if trackResult.filename != t.path:
            trackResult.filename = t.path
            self.info('Filename changed to %r', trackResult.filename)

    def retagImage(self, runner, taglists):
        cueImage = image.Image(self.cuePath)
        t = image.ImageRetagTask(cueImage, taglists)
        runner.run(t)

    def verifyImage(self, runner, responses):
        """
        Verify our image against the given AccurateRip responses.

        Needs an initialized self.result.
        Will set accurip and friends on each TrackResult.
        """

        self.debug('verifying Image against %d AccurateRip responses',
            len(responses or []))

        cueImage = image.Image(self.cuePath)
        verifytask = image.ImageVerifyTask(cueImage)
        cuetask = image.AccurateRipChecksumTask(cueImage)
        runner.run(verifytask)
        runner.run(cuetask)

        self._verifyImageWithChecksums(responses, cuetask.checksums)

    def _verifyImageWithChecksums(self, responses, checksums):
        # loop over tracks to set our calculated AccurateRip CRC's
        for i, csum in enumerate(checksums):
            trackResult = self.result.getTrackResult(i + 1)
            trackResult.ARCRC = csum


        if not responses:
            self.warning('No AccurateRip responses, cannot verify.')
            return

        # now loop to match responses
        for i, csum in enumerate(checksums):
            trackResult = self.result.getTrackResult(i + 1)

            confidence = None
            response = None

            # match against each response's checksum for this track
            for j, r in enumerate(responses):
                if "%08x" % csum == r.checksums[i]:
                    response = r
                    self.debug(
                        "Track %02d matched response %d of %d in "
                        "AccurateRip database",
                        i + 1, j + 1, len(responses))
                    trackResult.accurip = True
                    # FIXME: maybe checksums should be ints
                    trackResult.ARDBCRC = int(r.checksums[i], 16)
                    # arsum = csum
                    confidence = r.confidences[i]
                    trackResult.ARDBConfidence = confidence

            if not trackResult.accurip:
                self.warning("Track %02d: not matched in AccurateRip database",
                    i + 1)

            # I have seen AccurateRip responses with 0 as confidence
            # for example, Best of Luke Haines, disc 1, track 1
            maxConfidence = -1
            maxResponse = None
            for r in responses:
                if r.confidences[i] > maxConfidence:
                    maxConfidence = r.confidences[i]
                    maxResponse = r

            self.debug('Track %02d: found max confidence %d' % (
                i + 1, maxConfidence))
            trackResult.ARDBMaxConfidence = maxConfidence
            if not response:
                self.warning('Track %02d: none of the responses matched.',
                    i + 1)
                trackResult.ARDBCRC = int(
                    maxResponse.checksums[i], 16)
            else:
                trackResult.ARDBCRC = int(response.checksums[i], 16)

    def getAccurateRipResults(self):
        """
        @rtype: list of str
        """
        res = []

        # loop over tracks
        for i, trackResult in enumerate(self.result.tracks):
            status = 'rip NOT accurate'

            if trackResult.accurip:
                    status = 'rip accurate    '

            c = "(not found)            "
            ar = ", DB [notfound]"
            if trackResult.ARDBMaxConfidence:
                c = "(max confidence    %3d)" % trackResult.ARDBMaxConfidence
                if trackResult.ARDBConfidence is not None:
                    if trackResult.ARDBConfidence \
                            < trackResult.ARDBMaxConfidence:
                        c = "(confidence %3d of %3d)" % (
                            trackResult.ARDBConfidence,
                            trackResult.ARDBMaxConfidence)

                ar = ", DB [%08x]" % trackResult.ARDBCRC
            # htoa tracks (i == 0) do not have an ARCRC
            if trackResult.ARCRC is None:
                assert trackResult.number == 0, \
                    'no trackResult.ARCRC on non-HTOA track %d' % \
                        trackResult.number
                res.append("Track  0: unknown          (not tracked)")
            else:
                res.append("Track %2d: %s %s [%08x]%s" % (
                    trackResult.number, status, c, trackResult.ARCRC, ar))

        return res

    def writeCue(self, discName):
        assert self.result.table.canCue()
        cuePath = '%s.cue' % discName
        self.debug('write .cue file to %s', cuePath)
        handle = open(cuePath, 'w')
        # FIXME: do we always want utf-8 ?
        handle.write(self.result.table.cue(cuePath).encode('utf-8'))
        handle.close()

        self.cuePath = cuePath

        return cuePath

    def writeLog(self, discName, logger):
        logPath = '%s.log' % discName
        handle = open(logPath, 'w')
        log = logger.log(self.result)
        handle.write(log.encode('utf-8'))
        handle.close()

        self.logPath = logPath

        return logPath

########NEW FILE########
__FILENAME__ = renamer
# -*- Mode: Python; test-case-name: morituri.test.test_common_renamer -*-
# vi:si:et:sw=4:sts=4:ts=4

# Morituri - for those about to RIP

# Copyright (C) 2009 Thomas Vander Stichele

# This file is part of morituri.
#
# morituri is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# morituri is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with morituri.  If not, see <http://www.gnu.org/licenses/>.

import os
import tempfile

"""
Rename files on file system and inside metafiles in a resumable way.
"""


class Operator(object):

    def __init__(self, statePath, key):
        self._todo = []
        self._done = []
        self._statePath = statePath
        self._key = key
        self._resuming = False

    def addOperation(self, operation):
        """
        Add an operation.
        """
        self._todo.append(operation)

    def load(self):
        """
        Load state from the given state path using the given key.
        Verifies the state.
        """
        todo = os.path.join(self._statePath, self._key + '.todo')
        lines = []
        with open(todo, 'r') as handle:
            for line in handle.readlines():
                lines.append(line)
                name, data = line.split(' ', 1)
                cls = globals()[name]
                operation = cls.deserialize(data)
                self._todo.append(operation)


        done = os.path.join(self._statePath, self._key + '.done')
        if os.path.exists(done):
            with open(done, 'r') as handle:
                for i, line in enumerate(handle.readlines()):
                    assert line == lines[i], "line %s is different than %s" % (
                        line, lines[i])
                    self._done.append(self._todo[i])

        # last task done is i; check if the next one might have gotten done.
        self._resuming = True

    def save(self):
        """
        Saves the state to the given state path using the given key.
        """
        # only save todo first time
        todo = os.path.join(self._statePath, self._key + '.todo')
        if not os.path.exists(todo):
            with open(todo, 'w') as handle:
                for o in self._todo:
                    name = o.__class__.__name__
                    data = o.serialize()
                    handle.write('%s %s\n' % (name, data))

        # save done every time
        done = os.path.join(self._statePath, self._key + '.done')
        with open(done, 'w') as handle:
            for o in self._done:
                name = o.__class__.__name__
                data = o.serialize()
                handle.write('%s %s\n' % (name, data))

    def start(self):
        """
        Execute the operations
        """

    def next(self):
        operation = self._todo[len(self._done)]
        if self._resuming:
            operation.redo()
            self._resuming = False
        else:
            operation.do()

        self._done.append(operation)
        self.save()


class FileRenamer(Operator):

    def addRename(self, source, destination):
        """
        Add a rename operation.

        @param source:      source filename
        @type  source:      str
        @param destination: destination filename
        @type  destination: str
        """


class Operation(object):

    def verify(self):
        """
        Check if the operation will succeed in the current conditions.
        Consider this a pre-flight check.

        Does not eliminate the need to handle errors as they happen.
        """

    def do(self):
        """
        Perform the operation.
        """
        pass

    def redo(self):
        """
        Perform the operation, without knowing if it already has been
        (partly) performed.
        """
        self.do()

    def serialize(self):
        """
        Serialize the operation.
        The return value should bu usable with L{deserialize}

        @rtype: str
        """

    def deserialize(cls, data):
        """
        Deserialize the operation with the given operation data.

        @type  data: str
        """
        raise NotImplementedError
    deserialize = classmethod(deserialize)


class RenameFile(Operation):

    def __init__(self, source, destination):
        self._source = source
        self._destination = destination

    def verify(self):
        assert os.path.exists(self._source)
        assert not os.path.exists(self._destination)

    def do(self):
        os.rename(self._source, self._destination)

    def serialize(self):
        return '"%s" "%s"' % (self._source, self._destination)

    def deserialize(cls, data):
        _, source, __, destination, ___ = data.split('"')
        return RenameFile(source, destination)
    deserialize = classmethod(deserialize)

    def __eq__(self, other):
        return self._source == other._source \
            and self._destination == other._destination


class RenameInFile(Operation):

    def __init__(self, path, source, destination):
        self._path = path
        self._source = source
        self._destination = destination

    def verify(self):
        assert os.path.exists(self._path)
        # check if the source exists in the given file

    def do(self):
        with open(self._path) as handle:
            (fd, name) = tempfile.mkstemp(suffix='.morituri')

            for s in handle:
                os.write(fd, s.replace(self._source, self._destination))

            os.close(fd)
            os.rename(name, self._path)

    def serialize(self):
        return '"%s" "%s" "%s"' % (self._path, self._source, self._destination)

    def deserialize(cls, data):
        _, path, __, source, ___, destination, ____ = data.split('"')
        return RenameInFile(path, source, destination)
    deserialize = classmethod(deserialize)

    def __eq__(self, other):
        return self._source == other._source \
            and self._destination == other._destination \
            and self._path == other._path

########NEW FILE########
__FILENAME__ = task
# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

import os
import signal
import subprocess

from morituri.extern import asyncsub
from morituri.extern.log import log
from morituri.extern.task import task, gstreamer

# log.Loggable first to get logging


class SyncRunner(log.Loggable, task.SyncRunner):
    pass


class LoggableTask(log.Loggable, task.Task):
    pass

class LoggableMultiSeparateTask(log.Loggable, task.MultiSeparateTask):
    pass

class GstPipelineTask(log.Loggable, gstreamer.GstPipelineTask):
    pass


class PopenTask(log.Loggable, task.Task):
    """
    I am a task that runs a command using Popen.
    """

    logCategory = 'PopenTask'
    bufsize = 1024
    command = None
    cwd = None

    def start(self, runner):
        task.Task.start(self, runner)

        try:
            self._popen = asyncsub.Popen(self.command,
                bufsize=self.bufsize,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, close_fds=True, cwd=self.cwd)
        except OSError, e:
            import errno
            if e.errno == errno.ENOENT:
                self.commandMissing()

            raise

        self.debug('Started %r with pid %d', self.command,
            self._popen.pid)

        self.schedule(1.0, self._read, runner)

    def _read(self, runner):
        try:
            read = False

            ret = self._popen.recv()

            if ret:
                self.log("read from stdout: %s", ret)
                self.readbytesout(ret)
                read = True

            ret = self._popen.recv_err()

            if ret:
                self.log("read from stderr: %s", ret)
                self.readbyteserr(ret)
                read = True

            # if we read anything, we might have more to read, so
            # reschedule immediately
            if read and self.runner:
                self.schedule(0.0, self._read, runner)
                return

            # if we didn't read anything, give the command more time to
            # produce output
            if self._popen.poll() is None and self.runner:
                # not finished yet
                self.schedule(1.0, self._read, runner)
                return

            self._done()
        except Exception, e:
            self.debug('exception during _read()')
            self.debug(log.getExceptionMessage(e))
            self.setException(e)
            self.stop()

    def _done(self):
            assert self._popen.returncode is not None, "No returncode"

            if self._popen.returncode >= 0:
                self.debug('Return code was %d', self._popen.returncode)
            else:
                self.debug('Terminated with signal %d',
                    -self._popen.returncode)

            self.setProgress(1.0)

            if self._popen.returncode != 0:
                self.failed()
            else:
                self.done()

            self.stop()
            return

    def abort(self):
        self.debug('Aborting, sending SIGTERM to %d', self._popen.pid)
        os.kill(self._popen.pid, signal.SIGTERM)
        # self.stop()

    def readbytesout(self, bytes):
        """
        Called when bytes have been read from stdout.
        """
        pass

    def readbyteserr(self, bytes):
        """
        Called when bytes have been read from stderr.
        """
        pass

    def done(self):
        """
        Called when the command completed successfully.
        """
        pass

    def failed(self):
        """
        Called when the command failed.
        """
        pass


    def commandMissing(self):
        """
        Called when the command is missing.
        """
        pass



########NEW FILE########
__FILENAME__ = configure
# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

'''
configure-time variables for installed or uninstalled operation

Code should run
    >>> from morituri.configure import configure

and then access the variables from the configure module.  For example:
    >>> print configure.version

@var  isinstalled: whether an installed version is being run
@type isinstalled: boolean

@var  version:     morituri version number
@type version:     string
'''

import os

# where am I on the disk ?
__thisdir = os.path.dirname(os.path.abspath(__file__))

if os.path.exists(os.path.join(__thisdir, 'uninstalled.py')):
    from morituri.configure import uninstalled
    config_dict = uninstalled.get()
elif os.path.exists(os.path.join(__thisdir, 'installed.py')):
    from morituri.configure import installed
    config_dict = installed.get()
else:
    # hack on fresh checkout, no make run yet, and configure needs revision
    from morituri.common import common
    config_dict = {
        'revision': common.getRevision(),
    }

for key, value in config_dict.items():
    dictionary = locals()
    dictionary[key] = value

########NEW FILE########
__FILENAME__ = asyncsub
# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# from http://code.activestate.com/recipes/440554/

import os
import subprocess
import errno
import time
import sys

PIPE = subprocess.PIPE

if subprocess.mswindows:
    from win32file import ReadFile, WriteFile
    from win32pipe import PeekNamedPipe
    import msvcrt
else:
    import select
    import fcntl


class Popen(subprocess.Popen):

    def recv(self, maxsize=None):
        return self._recv('stdout', maxsize)

    def recv_err(self, maxsize=None):
        return self._recv('stderr', maxsize)

    def send_recv(self, input='', maxsize=None):
        return self.send(input), self.recv(maxsize), self.recv_err(maxsize)

    def get_conn_maxsize(self, which, maxsize):
        if maxsize is None:
            maxsize = 1024
        elif maxsize < 1:
            maxsize = 1
        return getattr(self, which), maxsize

    def _close(self, which):
        getattr(self, which).close()
        setattr(self, which, None)

    if subprocess.mswindows:

        def send(self, input):
            if not self.stdin:
                return None

            try:
                x = msvcrt.get_osfhandle(self.stdin.fileno())
                (errCode, written) = WriteFile(x, input)
            except ValueError:
                return self._close('stdin')
            except (subprocess.pywintypes.error, Exception), why:
                if why[0] in (109, errno.ESHUTDOWN):
                    return self._close('stdin')
                raise

            return written

        def _recv(self, which, maxsize):
            conn, maxsize = self.get_conn_maxsize(which, maxsize)
            if conn is None:
                return None

            try:
                x = msvcrt.get_osfhandle(conn.fileno())
                (read, nAvail, nMessage) = PeekNamedPipe(x, 0)
                if maxsize < nAvail:
                    nAvail = maxsize
                if nAvail > 0:
                    (errCode, read) = ReadFile(x, nAvail, None)
            except ValueError:
                return self._close(which)
            except (subprocess.pywintypes.error, Exception), why:
                if why[0] in (109, errno.ESHUTDOWN):
                    return self._close(which)
                raise

            if self.universal_newlines:
                read = self._translate_newlines(read)
            return read

    else:

        def send(self, input):
            if not self.stdin:
                return None

            if not select.select([], [self.stdin], [], 0)[1]:
                return 0

            try:
                written = os.write(self.stdin.fileno(), input)
            except OSError, why:
                if why[0] == errno.EPIPE: #broken pipe
                    return self._close('stdin')
                raise

            return written

        def _recv(self, which, maxsize):
            conn, maxsize = self.get_conn_maxsize(which, maxsize)
            if conn is None:
                return None

            flags = fcntl.fcntl(conn, fcntl.F_GETFL)
            if not conn.closed:
                fcntl.fcntl(conn, fcntl.F_SETFL, flags| os.O_NONBLOCK)

            try:
                if not select.select([conn], [], [], 0)[0]:
                    return ''

                r = conn.read(maxsize)
                if not r:
                    return self._close(which)

                if self.universal_newlines:
                    r = self._translate_newlines(r)
                return r
            finally:
                if not conn.closed:
                    fcntl.fcntl(conn, fcntl.F_SETFL, flags)

message = "Other end disconnected!"


def recv_some(p, t=.1, e=1, tr=5, stderr=0):
    if tr < 1:
        tr = 1
    x = time.time()+t
    y = []
    r = ''
    pr = p.recv
    if stderr:
        pr = p.recv_err
    while time.time() < x or r:
        r = pr()
        if r is None:
            if e:
                raise Exception(message)
            else:
                break
        elif r:
            y.append(r)
        else:
            time.sleep(max((x-time.time())/tr, 0))
    return ''.join(y)


def send_all(p, data):
    while len(data):
        sent = p.send(data)
        if sent is None:
            raise Exception(message)
        data = buffer(data, sent)

if __name__ == '__main__':
    if sys.platform == 'win32':
        shell, commands, tail = ('cmd', ('dir /w', 'echo HELLO WORLD'), '\r\n')
    else:
        shell, commands, tail = ('sh', ('ls', 'echo HELLO WORLD'), '\n')

    a = Popen(shell, stdin=PIPE, stdout=PIPE)
    print recv_some(a),
    for cmd in commands:
        send_all(a, cmd + tail)
        print recv_some(a),
    send_all(a, 'exit' + tail)
    print recv_some(a, e=0)
    a.wait()

########NEW FILE########
__FILENAME__ = gstreamer
# -*- Mode: Python; test-case-name: test_gstreamer -*-
# vi:si:et:sw=4:sts=4:ts=4

# Morituri - for those about to RIP

# Copyright (C) 2009 Thomas Vander Stichele

# This file is part of morituri.
#
# morituri is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# morituri is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with morituri.  If not, see <http://www.gnu.org/licenses/>.

import task

def quoteParse(path):
    """
    Quote a path for use in gst.parse_launch.
    """
    # Make sure double quotes and backslashes are escaped.  See
    # morituri.test.test_common_checksum.NormalPathTestCase

    return path.replace('\\', '\\\\').replace('"', '\\"')


class GstException(Exception):
    def __init__(self, gerror, debug):
        self.args = (gerror, debug, )
        self.gerror = gerror
        self.debug = debug

    def __repr__(self):
        return '<GstException: GError %r, debug %r>' % (
            self.gerror.message, self.debug)

class GstPipelineTask(task.Task):
    """
    I am a base class for tasks that use a GStreamer pipeline.

    I handle errors and raise them appropriately.

    @cvar gst:      the GStreamer module, so code does not have to import gst
                    as a module in code everywhere to avoid option stealing.
    @cvar playing:  whether the pipeline should be set to playing after
                    paused.  Some pipelines don't need to play for a task
                    to be done (for example, querying length)
    @type playing:  bool
    @type pipeline: L{gst.Pipeline}
    @type bus:      L{gst.Bus}
    """

    gst = None
    playing = True
    pipeline = None
    bus = None

    ### task.Task implementations
    def start(self, runner):
        import gst
        self.gst = gst

        task.Task.start(self, runner)

        self.getPipeline()

        self.bus = self.pipeline.get_bus()
        # FIXME: remove this
        self._bus = self.bus
        self.gst.debug('got bus %r' % self.bus)

        # a signal watch calls callbacks from an idle loop
        # self.bus.add_signal_watch()

        # sync emission triggers sync-message signals which calls callbacks
        # from the thread that signals, but happens immediately
        self.bus.enable_sync_message_emission()
        self.bus.connect('sync-message::eos', self.bus_eos_cb)
        self.bus.connect('sync-message::tag', self.bus_tag_cb)
        self.bus.connect('sync-message::error', self.bus_error_cb)

        self.parsed()

        self.debug('setting pipeline to PAUSED')
        self.pipeline.set_state(gst.STATE_PAUSED)
        self.debug('set pipeline to PAUSED')
        # FIXME: this can block
        ret = self.pipeline.get_state()
        self.debug('got pipeline to PAUSED: %r', ret)

        # GStreamer tasks could already be done in paused, and not
        # need playing.
        if self.exception:
            raise self.exception

        done = self.paused()

        if done:
            self.debug('paused() is done')
        else:
            self.debug('paused() wants more')
            self.play()

    def play(self):
        # since set_state returns non-False, adding it as timeout_add
        # will repeatedly call it, and block the main loop; so
        #   gobject.timeout_add(0L, self._pipeline.set_state,
        #       gst.STATE_PLAYING)
        # would not work.
        def playLater():
            if self.exception:
                self.debug('playLater: exception was raised, not playing')
                self.stop()
                return False

            self.debug('setting pipeline to PLAYING')
            self.pipeline.set_state(self.gst.STATE_PLAYING)
            self.debug('set pipeline to PLAYING')
            return False

        if self.playing:
            self.debug('schedule playLater()')
            self.schedule(0, playLater)

    def stop(self):
        self.debug('stopping')


        # FIXME: in theory this should help clean up properly,
        # but in practice we can still get
        # python: /builddir/build/BUILD/Python-2.7/Python/pystate.c:595: PyGILState_Ensure: Assertion `autoInterpreterState' failed.

        self.pipeline.set_state(self.gst.STATE_READY)
        self.debug('set pipeline to READY')
        # FIXME: this can block
        ret = self.pipeline.get_state()
        self.debug('got pipeline to READY: %r', ret)

        self.debug('setting state to NULL')
        self.pipeline.set_state(self.gst.STATE_NULL)
        self.debug('set state to NULL')
        self.stopped()
        task.Task.stop(self)

    ### subclass optional implementations
    def getPipeline(self):
        desc = self.getPipelineDesc()

        self.debug('creating pipeline %r', desc)
        self.pipeline = self.gst.parse_launch(desc)

    def getPipelineDesc(self):
        """
        subclasses should implement this to provide a pipeline description.

        @rtype: str
        """
        raise NotImplementedError

    def parsed(self):
        """
        Called after parsing/getting the pipeline but before setting it to
        paused.
        """
        pass

    def paused(self):
        """
        Called after pipeline is paused.

        If this returns True, the task is done and
        should not continue going to PLAYING.
        """
        pass

    def stopped(self):
        """
        Called after pipeline is set back to NULL but before chaining up to
        stop()
        """
        pass

    def bus_eos_cb(self, bus, message):
        """
        Called synchronously (ie from messaging thread) on eos message.

        Override me to handle eos
        """
        pass

    def bus_tag_cb(self, bus, message):
        """
        Called synchronously (ie from messaging thread) on tag message.

        Override me to handle tags.
        """
        pass

    def bus_error_cb(self, bus, message):
        """
        Called synchronously (ie from messaging thread) on error message.
        """
        self.debug('bus_error_cb: bus %r, message %r' % (bus, message))
        if self.exception:
            self.debug('bus_error_cb: already got an exception, ignoring')
            return

        exc = GstException(*message.parse_error())
        self.setAndRaiseException(exc)
        self.debug('error, scheduling stop')
        self.schedule(0, self.stop)

    def query_length(self, element):
        """
        Query the length of the pipeline in samples, for progress updates.
        To be called from paused()
        """
        # get duration
        self.debug('query duration')
        try:
            duration, qformat = element.query_duration(self.gst.FORMAT_DEFAULT)
        except self.gst.QueryError, e:
            # Fall back to time; for example, oggdemux/vorbisdec only supports
            # TIME
            try:
                duration, qformat = element.query_duration(self.gst.FORMAT_TIME)
            except self.gst.QueryError, e:
                self.setException(e)
                # schedule it, otherwise runner can get set to None before
                # we're done starting
                self.schedule(0, self.stop)
                return

        # wavparse 0.10.14 returns in bytes
        if qformat == self.gst.FORMAT_BYTES:
            self.debug('query returned in BYTES format')
            duration /= 4

        if qformat == self.gst.FORMAT_TIME:
            rate = None
            self.debug('query returned in TIME format')
            # we need sample rate
            pads = list(element.pads())
            sink = element.get_by_name('sink')
            pads += list(sink.pads())

            for pad in pads:
                caps = pad.get_negotiated_caps()
                print caps[0].keys()
                if 'rate' in caps[0].keys():
                    rate = caps[0]['rate']
                    self.debug('Sample rate: %d Hz', rate)

            if not rate:
                raise KeyError(
                    'Cannot find sample rate, cannot convert to samples')

            duration = int(float(rate) * (float(duration) / self.gst.SECOND))

        self.debug('total duration: %r', duration)

        return duration



########NEW FILE########
__FILENAME__ = task
# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# Morituri - for those about to RIP

# Copyright (C) 2009 Thomas Vander Stichele

# This file is part of morituri.
#
# morituri is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# morituri is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with morituri.  If not, see <http://www.gnu.org/licenses/>.

import sys

import gobject

class TaskException(Exception):
    """
    I wrap an exception that happened during task execution.
    """

    exception = None # original exception

    def __init__(self, exception, message=None):
        self.exception = exception
        self.exceptionMessage = message
        self.args = (exception, message, )

# lifted from flumotion log module
def _getExceptionMessage(exception, frame=-1, filename=None):
    """
    Return a short message based on an exception, useful for debugging.
    Tries to find where the exception was triggered.
    """
    import traceback

    stack = traceback.extract_tb(sys.exc_info()[2])
    if filename:
        stack = [f for f in stack if f[0].find(filename) > -1]

    # badly raised exceptions can come without a stack
    if stack:
        (filename, line, func, text) = stack[frame]
    else:
        (filename, line, func, text) = ('no stack', 0, 'none', '')

    exc = exception.__class__.__name__
    msg = ""
    # a shortcut to extract a useful message out of most exceptions
    # for now
    if str(exception):
        msg = ": %s" % str(exception)
    return "exception %(exc)s at %(filename)s:%(line)s: %(func)s()%(msg)s" \
        % locals()


class LogStub(object):
    """
    I am a stub for a log interface.
    """

    ### log stubs
    def log(self, message, *args):
        pass

    def debug(self, message, *args):
        pass

    def info(self, message, *args):
        pass

    def warning(self, message, *args):
        pass

    def error(self, message, *args):
        pass


class Task(LogStub):
    """
    I wrap a task in an asynchronous interface.
    I can be listened to for starting, stopping, description changes
    and progress updates.

    I communicate an error by setting self.exception to an exception and
    stopping myself from running.
    The listener can then handle the Task.exception.

    @ivar  description: what am I doing
    @ivar  exception:   set if an exception happened during the task
                        execution.  Will be raised through run() at the end.
    """
    logCategory = 'Task'

    description = 'I am doing something.'

    progress = 0.0
    increment = 0.01
    running = False
    runner = None
    exception = None
    exceptionMessage = None
    exceptionTraceback = None

    _listeners = None


    ### subclass methods
    def start(self, runner):
        """
        Start the task.

        Subclasses should chain up to me at the beginning.

        Subclass implementations should raise exceptions immediately in
        case of failure (using set(AndRaise)Exception) first, or do it later
        using those methods.

        If start doesn't raise an exception, the task should run until
        complete, or setException and stop().
        """
        self.debug('starting')
        self.setProgress(self.progress)
        self.running = True
        self.runner = runner
        self._notifyListeners('started')

    def stop(self):
        """
        Stop the task.
        Also resets the runner on the task.

        Subclasses should chain up to me at the end.
        It is important that they do so in all cases, even when
        they ran into an exception of their own.

        Listeners will get notified that the task is stopped,
        whether successfully or with an exception.
        """
        self.debug('stopping')
        self.running = False
        if not self.runner:
            print 'ERROR: stopping task which is already stopped'
            import traceback; traceback.print_stack()
        self.runner = None
        self.debug('reset runner to None')
        self._notifyListeners('stopped')

    ### base class methods
    def setProgress(self, value):
        """
        Notify about progress changes bigger than the increment.
        Called by subclass implementations as the task progresses.
        """
        if value - self.progress > self.increment or value >= 1.0 or value == 0.0:
            self.progress = value
            self._notifyListeners('progressed', value)
            self.log('notifying progress: %r on %r', value, self.description)

    def setDescription(self, description):
        if description != self.description:
            self._notifyListeners('described', description)
            self.description = description

    # FIXME: unify?
    def setExceptionAndTraceback(self, exception):
        """
        Call this to set a synthetically created exception (and not one
        that was actually raised and caught)
        """
        import traceback

        stack = traceback.extract_stack()[:-1]
        (filename, line, func, text) = stack[-1]
        exc = exception.__class__.__name__
        msg = ""
        # a shortcut to extract a useful message out of most exceptions
        # for now
        if str(exception):
            msg = ": %s" % str(exception)
        line = "exception %(exc)s at %(filename)s:%(line)s: %(func)s()%(msg)s" \
            % locals()

        self.exception = exception
        self.exceptionMessage = line
        self.exceptionTraceback = traceback.format_exc()
        self.debug('set exception, %r' % self.exceptionMessage)
    # FIXME: remove
    setAndRaiseException = setExceptionAndTraceback

    def setException(self, exception):
        """
        Call this to set a caught exception on the task.
        """
        import traceback

        self.exception = exception
        self.exceptionMessage = _getExceptionMessage(exception)
        self.exceptionTraceback = traceback.format_exc()
        self.debug('set exception, %r, %r' % (
            exception, self.exceptionMessage))

    def schedule(self, delta, callable, *args, **kwargs):
        if not self.runner:
            print "ERROR: scheduling on a task that's altready stopped"
            import traceback; traceback.print_stack()
            return
        self.runner.schedule(self, delta, callable, *args, **kwargs)


    def addListener(self, listener):
        """
        Add a listener for task status changes.

        Listeners should implement started, stopped, and progressed.
        """
        self.debug('Adding listener %r', listener)
        if not self._listeners:
            self._listeners = []
        self._listeners.append(listener)

    def _notifyListeners(self, methodName, *args, **kwargs):
        if self._listeners:
            for l in self._listeners:
                method = getattr(l, methodName)
                try:
                    method(self, *args, **kwargs)
                except Exception, e:
                    self.setException(e)

# FIXME: should this become a real interface, like in zope ?
class ITaskListener(object):
    """
    I am an interface for objects listening to tasks.
    """
    ### listener callbacks
    def progressed(self, task, value):
        """
        Implement me to be informed about progress.

        @type  value: float
        @param value: progress, from 0.0 to 1.0
        """

    def described(self, task, description):
        """
        Implement me to be informed about description changes.

        @type  description: str
        @param description: description
        """

    def started(self, task):
        """
        Implement me to be informed about the task starting.
        """

    def stopped(self, task):
        """
        Implement me to be informed about the task stopping.
        If the task had an error, task.exception will be set.
        """



# this is a Dummy task that can be used to test if this works at all
class DummyTask(Task):
    def start(self, runner):
        Task.start(self, runner)
        self.schedule(1.0, self._wind)

    def _wind(self):
        self.setProgress(min(self.progress + 0.1, 1.0))

        if self.progress >= 1.0:
            self.stop()
            return

        self.schedule(1.0, self._wind)

class BaseMultiTask(Task, ITaskListener):
    """
    I perform multiple tasks.

    @ivar tasks: the tasks to run
    @type tasks: list of L{Task}
    """

    description = 'Doing various tasks'
    tasks = None

    def __init__(self):
        self.tasks = []
        self._task = 0

    def addTask(self, task):
        """
        Add a task.

        @type task: L{Task}
        """
        if self.tasks is None:
            self.tasks = []
        self.tasks.append(task)

    def start(self, runner):
        """
        Start tasks.

        Tasks can still be added while running.  For example,
        a first task can determine how many additional tasks to run.
        """
        Task.start(self, runner)

        # initialize task tracking
        if not self.tasks:
            self.warning('no tasks')
        self._generic = self.description

        self.next()

    def next(self):
        """
        Start the next task.
        """
        try:
            # start next task
            task = self.tasks[self._task]
            self._task += 1
            self.debug('BaseMultiTask.next(): starting task %d of %d: %r',
                self._task, len(self.tasks), task)
            self.setDescription("%s (%d of %d) ..." % (
                task.description, self._task, len(self.tasks)))
            task.addListener(self)
            task.start(self.runner)
            self.debug('BaseMultiTask.next(): started task %d of %d: %r',
                self._task, len(self.tasks), task)
        except Exception, e:
            self.setException(e)
            self.debug('Got exception during next: %r', self.exceptionMessage)
            self.stop()
            return

    ### ITaskListener methods
    def started(self, task):
        pass

    def progressed(self, task, value):
        pass

    def stopped(self, task):
        """
        Subclasses should chain up to me at the end of their implementation.
        They should fall through to chaining up if there is an exception.
        """
        self.log('BaseMultiTask.stopped: task %r (%d of %d)',
            task, self.tasks.index(task) + 1, len(self.tasks))
        if task.exception:
            self.log('BaseMultiTask.stopped: exception %r',
                task.exceptionMessage)
            self.exception = task.exception
            self.exceptionMessage = task.exceptionMessage
            self.stop()
            return

        if self._task == len(self.tasks):
            self.log('BaseMultiTask.stopped: all tasks done')
            self.stop()
            return

        # pick another
        self.log('BaseMultiTask.stopped: pick next task')
        self.schedule(0, self.next)


class MultiSeparateTask(BaseMultiTask):
    """
    I perform multiple tasks.
    I track progress of each individual task, going back to 0 for each task.
    """
    description = 'Doing various tasks separately'

    def start(self, runner):
        self.debug('MultiSeparateTask.start()')
        BaseMultiTask.start(self, runner)

    def next(self):
        self.debug('MultiSeparateTask.next()')
        # start next task
        self.progress = 0.0 # reset progress for each task
        BaseMultiTask.next(self)

    ### ITaskListener methods
    def progressed(self, task, value):
        self.setProgress(value)

    def described(self, description):
        self.setDescription("%s (%d of %d) ..." % (
            description, self._task, len(self.tasks)))

class MultiCombinedTask(BaseMultiTask):
    """
    I perform multiple tasks.
    I track progress as a combined progress on all tasks on task granularity.
    """

    description = 'Doing various tasks combined'
    _stopped = 0

    ### ITaskListener methods
    def progressed(self, task, value):
        self.setProgress(float(self._stopped + value) / len(self.tasks))

    def stopped(self, task):
        self._stopped += 1
        self.setProgress(float(self._stopped) / len(self.tasks))
        BaseMultiTask.stopped(self, task)

class TaskRunner(LogStub):
    """
    I am a base class for task runners.
    Task runners should be reusable.
    """
    logCategory = 'TaskRunner'

    def run(self, task):
        """
        Run the given task.

        @type  task: Task
        """
        raise NotImplementedError

    ### methods for tasks to call
    def schedule(self, delta, callable, *args, **kwargs):
        """
        Schedule a single future call.

        Subclasses should implement this.

        @type  delta: float
        @param delta: time in the future to schedule call for, in seconds.
        """
        raise NotImplementedError


class SyncRunner(TaskRunner, ITaskListener):
    """
    I run the task synchronously in a gobject MainLoop.
    """
    def __init__(self, verbose=True):
        self._verbose = verbose
        self._longest = 0 # longest string shown; for clearing

    def run(self, task, verbose=None, skip=False):
        self.debug('run task %r', task)
        self._task = task
        self._verboseRun = self._verbose
        if verbose is not None:
            self._verboseRun = verbose
        self._skip = skip

        self._loop = gobject.MainLoop()
        self._task.addListener(self)
        # only start the task after going into the mainloop,
        # otherwise the task might complete before we are in it
        gobject.timeout_add(0L, self._startWrap, self._task)
        self.debug('run loop')
        self._loop.run()

        self.debug('done running task %r', task)
        if task.exception:
            # catch the exception message
            # FIXME: this gave a traceback in the logging module
            self.debug('raising TaskException for %r, %r' % (
                task.exceptionMessage, task.exceptionTraceback))
            msg = task.exceptionMessage
            if task.exceptionTraceback:
                msg += "\n" + task.exceptionTraceback
            raise TaskException(task.exception, message=msg)

    def _startWrap(self, task):
        # wrap task start such that we can report any exceptions and
        # never hang
        try:
            self.debug('start task %r' % task)
            task.start(self)
        except Exception, e:
            # getExceptionMessage uses global exception state that doesn't
            # hang around, so store the message
            task.setException(e)
            self.debug('exception during start: %r', task.exceptionMessage)
            self.stopped(task)


    def schedule(self, task, delta, callable, *args, **kwargs):
        def c():
            try:
                self.log('schedule: calling %r(*args=%r, **kwargs=%r)',
                    callable, args, kwargs)
                callable(*args, **kwargs)
                return False
            except Exception, e:
                self.debug('exception when calling scheduled callable %r',
                    callable)
                task.setException(e)
                self.stopped(task)
                raise
        self.log('schedule: scheduling %r(*args=%r, **kwargs=%r)',
            callable, args, kwargs)

        gobject.timeout_add(int(delta * 1000L), c)

    ### ITaskListener methods
    def progressed(self, task, value):
        if not self._verboseRun:
            return

        self._report()

        if value >= 1.0:
            if self._skip:
                self._output('%s %3d %%' % (
                    self._task.description, 100.0))
            else:
                # clear with whitespace
                sys.stdout.write("%s\r" % (' ' * self._longest, ))

    def _output(self, what, newline=False, ret=True):
        sys.stdout.write(what)
        sys.stdout.write(' ' * (self._longest - len(what)))
        if ret:
            sys.stdout.write('\r')
        if newline:
            sys.stdout.write('\n')
        sys.stdout.flush()
        if len(what) > self._longest:
            #print; print 'setting longest', self._longest; print
            self._longest = len(what)

    def described(self, task, description):
        if self._verboseRun:
            self._report()

    def stopped(self, task):
        self.debug('stopped task %r', task)
        self.progressed(task, 1.0)
        self._loop.quit()

    def _report(self):
        self._output('%s %3d %%' % (
            self._task.description, self._task.progress * 100.0))

if __name__ == '__main__':
    task = DummyTask()
    runner = SyncRunner()
    runner.run(task)

########NEW FILE########
__FILENAME__ = taskgtk
# -*- Mode: Python; test-case-name: test_taskgtk -*-
# vi:si:et:sw=4:sts=4:ts=4

# Morituri - for those about to RIP

# Copyright (C) 2009 Thomas Vander Stichele

# This file is part of morituri.
# 
# morituri is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# morituri is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with morituri.  If not, see <http://www.gnu.org/licenses/>.

import gobject
import gtk

import task

class GtkProgressRunner(gtk.VBox, task.TaskRunner):
    """
    I am a widget that shows progress on a task.
    """

    __gsignals__ = {
        'stop': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ())
    }

    def __init__(self):
        gtk.VBox.__init__(self)
        self.set_border_width(6)
        self.set_spacing(6)

        self._label = gtk.Label()
        self.add(self._label)

        self._progress = gtk.ProgressBar()
        self.add(self._progress)

    def run(self, task):
        self._task = task
        self._label.set_text(task.description)
        task.addListener(self)
        while gtk.events_pending():
            gtk.main_iteration()
        task.start(self)

    def schedule(self, delta, callable, *args, **kwargs):
        def c():
            callable(*args, **kwargs)
            return False
        gobject.timeout_add(int(delta * 1000L), c)

    def started(self, task):
        pass

    def stopped(self, task):
        self.emit('stop')
        # self._task.removeListener(self)

    def progressed(self, task, value):
        self._progress.set_fraction(value)

    def described(self, task, description):
        self._label.set_text(description)

########NEW FILE########
__FILENAME__ = cue
# -*- Mode: Python; test-case-name: morituri.test.test_image_cue -*-
# vi:si:et:sw=4:sts=4:ts=4

# Morituri - for those about to RIP

# Copyright (C) 2009 Thomas Vander Stichele

# This file is part of morituri.
#
# morituri is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# morituri is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with morituri.  If not, see <http://www.gnu.org/licenses/>.

"""
Reading .cue files

See http://digitalx.org/cuesheetsyntax.php
"""

import re
import codecs

from morituri.common import common, log
from morituri.image import table

_REM_RE = re.compile("^REM\s(\w+)\s(.*)$")
_PERFORMER_RE = re.compile("^PERFORMER\s(.*)$")
_TITLE_RE = re.compile("^TITLE\s(.*)$")

_FILE_RE = re.compile(r"""
    ^FILE                 # FILE
    \s+"(?P<name>.*)"     # 'file name' in quotes
    \s+(?P<format>\w+)$   # format (WAVE/MP3/AIFF/...)
""", re.VERBOSE)

_TRACK_RE = re.compile(r"""
    ^\s+TRACK            # TRACK
    \s+(?P<track>\d\d)   # two-digit track number
    \s+(?P<mode>.+)$    # mode (AUDIO, MODEx/2xxx, ...)
""", re.VERBOSE)

_INDEX_RE = re.compile(r"""
    ^\s+INDEX   # INDEX
    \s+(\d\d)   # two-digit index number
    \s+(\d\d)   # minutes
    :(\d\d)     # seconds
    :(\d\d)$    # frames
""", re.VERBOSE)


class CueFile(object, log.Loggable):
    """
    I represent a .cue file as an object.

    @type table: L{table.Table}
    @ivar table: the index table.
    """
    logCategory = 'CueFile'

    def __init__(self, path):
        """
        @type  path: unicode
        """
        assert type(path) is unicode, "%r is not unicode" % path

        self._path = path
        self._rems = {}
        self._messages = []
        self.leadout = None
        self.table = table.Table()

    def parse(self):
        state = 'HEADER'
        currentFile = None
        currentTrack = None
        counter = 0

        self.info('Parsing .cue file %r', self._path)
        handle = codecs.open(self._path, 'r', 'utf-8')

        for number, line in enumerate(handle.readlines()):
            line = line.rstrip()

            m = _REM_RE.search(line)
            if m:
                tag = m.expand('\\1')
                value = m.expand('\\2')
                if state != 'HEADER':
                    self.message(number, 'REM %s outside of header' % tag)
                else:
                    self._rems[tag] = value
                continue

            # look for FILE lines
            m = _FILE_RE.search(line)
            if m:
                counter += 1
                filePath = m.group('name')
                fileFormat = m.group('format')
                currentFile = File(filePath, fileFormat)

            # look for TRACK lines
            m = _TRACK_RE.search(line)
            if m:
                if not currentFile:
                    self.message(number, 'TRACK without preceding FILE')
                    continue

                state = 'TRACK'

                trackNumber = int(m.group('track'))
                #trackMode = m.group('mode')

                self.debug('found track %d', trackNumber)
                currentTrack = table.Track(trackNumber)
                self.table.tracks.append(currentTrack)
                continue

            # look for INDEX lines
            m = _INDEX_RE.search(line)
            if m:
                if not currentTrack:
                    self.message(number, 'INDEX without preceding TRACK')
                    print 'ouch'
                    continue

                indexNumber = int(m.expand('\\1'))
                minutes = int(m.expand('\\2'))
                seconds = int(m.expand('\\3'))
                frames = int(m.expand('\\4'))
                frameOffset = frames \
                    + seconds * common.FRAMES_PER_SECOND \
                    + minutes * common.FRAMES_PER_SECOND * 60

                self.debug('found index %d of track %r in %r:%d',
                    indexNumber, currentTrack, currentFile.path, frameOffset)
                # FIXME: what do we do about File's FORMAT ?
                currentTrack.index(indexNumber,
                    path=currentFile.path, relative=frameOffset,
                    counter=counter)
                continue

    def message(self, number, message):
        """
        Add a message about a given line in the cue file.

        @param number: line number, counting from 0.
        """
        self._messages.append((number + 1, message))

    def getTrackLength(self, track):
        # returns track length in frames, or -1 if can't be determined and
        # complete file should be assumed
        # FIXME: this assumes a track can only be in one file; is this true ?
        i = self.table.tracks.index(track)
        if i == len(self.table.tracks) - 1:
            # last track, so no length known
            return -1

        thisIndex = track.indexes[1] # FIXME: could be more
        nextIndex = self.table.tracks[i + 1].indexes[1] # FIXME: could be 0

        c = thisIndex.counter
        if c is not None and c == nextIndex.counter:
            # they belong to the same source, so their relative delta is length
            return nextIndex.relative - thisIndex.relative

        # FIXME: more logic
        return -1

    def getRealPath(self, path):
        """
        Translate the .cue's FILE to an existing path.

        @type  path: unicode
        """
        return common.getRealPath(self._path, path)


class File:
    """
    I represent a FILE line in a cue file.
    """

    def __init__(self, path, format):
        """
        @type  path: unicode
        """
        assert type(path) is unicode, "%r is not unicode" % path

        self.path = path
        self.format = format

    def __repr__(self):
        return '<File %r of format %s>' % (self.path, self.format)

########NEW FILE########
__FILENAME__ = image
# -*- Mode: Python; test-case-name: morituri.test.test_image_image -*-
# vi:si:et:sw=4:sts=4:ts=4

# Morituri - for those about to RIP

# Copyright (C) 2009 Thomas Vander Stichele

# This file is part of morituri.
#
# morituri is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# morituri is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with morituri.  If not, see <http://www.gnu.org/licenses/>.

"""
Wrap on-disk CD images based on the .cue file.
"""

import os

from morituri.common import log, common
from morituri.image import cue, table

from morituri.extern.task import task, gstreamer


class Image(object, log.Loggable):
    """
    @ivar table: The Table of Contents for this image.
    @type table: L{table.Table}
    """
    logCategory = 'Image'

    def __init__(self, path):
        """
        @type  path: unicode
        @param path: .cue path
        """
        assert type(path) is unicode, "%r is not unicode" % path

        self._path = path
        self.cue = cue.CueFile(path)
        self.cue.parse()
        self._offsets = [] # 0 .. trackCount - 1
        self._lengths = [] # 0 .. trackCount - 1

        self.table = None

    def getRealPath(self, path):
        """
        Translate the .cue's FILE to an existing path.

        @param path: .cue path
        """
        assert type(path) is unicode, "%r is not unicode" % path

        return self.cue.getRealPath(path)

    def setup(self, runner):
        """
        Do initial setup, like figuring out track lengths, and
        constructing the Table of Contents.
        """
        self.debug('setup image start')
        verify = ImageVerifyTask(self)
        self.debug('verifying image')
        runner.run(verify)
        self.debug('verified image')

        # calculate offset and length for each track

        # CD's have a standard lead-in time of 2 seconds;
        # checksums that use it should add it there
        offset = self.cue.table.tracks[0].getIndex(1).relative

        tracks = []

        for i in range(len(self.cue.table.tracks)):
            length = self.cue.getTrackLength(self.cue.table.tracks[i])
            if length == -1:
                length = verify.lengths[i + 1]
            t = table.Track(i + 1, audio=True)
            tracks.append(t)
            # FIXME: this probably only works for non-compliant .CUE files
            # where pregap is put at end of previous file
            t.index(1, absolute=offset,
                path=self.cue.table.tracks[i].getIndex(1).path,
                relative=0)

            offset += length

        self.table = table.Table(tracks)
        self.table.leadout = offset
        self.debug('setup image done')


class AccurateRipChecksumTask(log.Loggable, task.MultiSeparateTask):
    """
    I calculate the AccurateRip checksums of all tracks.
    """

    description = "Checksumming tracks"

    def __init__(self, image):
        task.MultiSeparateTask.__init__(self)

        self._image = image
        cue = image.cue
        self.checksums = []

        self.debug('Checksumming %d tracks' % len(cue.table.tracks))
        for trackIndex, track in enumerate(cue.table.tracks):
            index = track.indexes[1]
            length = cue.getTrackLength(track)
            if length < 0:
                self.debug('track %d has unknown length' % (trackIndex + 1, ))
            else:
                self.debug('track %d is %d samples long' % (
                    trackIndex + 1, length))

            path = image.getRealPath(index.path)

            # here to avoid import gst eating our options
            from morituri.common import checksum

            checksumTask = checksum.AccurateRipChecksumTask(path,
                trackNumber=trackIndex + 1, trackCount=len(cue.table.tracks),
                sampleStart=index.relative * common.SAMPLES_PER_FRAME,
                sampleLength=length * common.SAMPLES_PER_FRAME)
            self.addTask(checksumTask)

    def stop(self):
        self.checksums = [t.checksum for t in self.tasks]
        task.MultiSeparateTask.stop(self)


class AudioLengthTask(log.Loggable, gstreamer.GstPipelineTask):
    """
    I calculate the length of a track in audio samples.

    @ivar  length: length of the decoded audio file, in audio samples.
    """
    logCategory = 'AudioLengthTask'
    description = 'Getting length of audio track'
    length = None

    playing = False

    def __init__(self, path):
        """
        @type  path: unicode
        """
        assert type(path) is unicode, "%r is not unicode" % path

        self._path = path
        self.logName = os.path.basename(path).encode('utf-8')

    def getPipelineDesc(self):
        return '''
            filesrc location="%s" !
            decodebin ! audio/x-raw-int !
            fakesink name=sink''' % \
                gstreamer.quoteParse(self._path).encode('utf-8')

    def paused(self):
        self.debug('query duration')
        sink = self.pipeline.get_by_name('sink')
        assert sink, 'Error constructing pipeline'

        try:
            length, qformat = sink.query_duration(self.gst.FORMAT_DEFAULT)
        except self.gst.QueryError, e:
            self.info('failed to query duration of %r' % self._path)
            self.setException(e)
            raise

        # wavparse 0.10.14 returns in bytes
        if qformat == self.gst.FORMAT_BYTES:
            self.debug('query returned in BYTES format')
            length /= 4
        self.debug('total length of %r in samples: %d', self._path, length)
        self.length = length

        self.pipeline.set_state(self.gst.STATE_NULL)
        self.stop()


class ImageVerifyTask(log.Loggable, task.MultiSeparateTask):
    """
    I verify a disk image and get the necessary track lengths.
    """

    logCategory = 'ImageVerifyTask'

    description = "Checking tracks"
    lengths = None

    def __init__(self, image):
        task.MultiSeparateTask.__init__(self)

        self._image = image
        cue = image.cue
        self._tasks = []
        self.lengths = {}

        for trackIndex, track in enumerate(cue.table.tracks):
            self.debug('verifying track %d', trackIndex + 1)
            index = track.indexes[1]
            length = cue.getTrackLength(track)

            if length == -1:
                path = image.getRealPath(index.path)
                assert type(path) is unicode, "%r is not unicode" % path
                self.debug('schedule scan of audio length of %r', path)
                taskk = AudioLengthTask(path)
                self.addTask(taskk)
                self._tasks.append((trackIndex + 1, track, taskk))
            else:
                self.debug('track %d has length %d', trackIndex + 1, length)

    def stop(self):
        for trackIndex, track, taskk in self._tasks:
            if taskk.exception:
                self.debug('subtask %r had exception %r, shutting down' % (
                    taskk, taskk.exception))
                self.setException(taskk.exception)
                break

            # print '%d has length %d' % (trackIndex, taskk.length)
            index = track.indexes[1]
            assert taskk.length % common.SAMPLES_PER_FRAME == 0
            end = taskk.length / common.SAMPLES_PER_FRAME
            self.lengths[trackIndex] = end - index.relative

        task.MultiSeparateTask.stop(self)


class ImageEncodeTask(log.Loggable, task.MultiSeparateTask):
    """
    I encode a disk image to a different format.
    """

    description = "Encoding tracks"

    def __init__(self, image, profile, outdir):
        task.MultiSeparateTask.__init__(self)

        self._image = image
        self._profile = profile
        cue = image.cue
        self._tasks = []
        self.lengths = {}

        def add(index):
            # here to avoid import gst eating our options
            from morituri.common import encode

            path = image.getRealPath(index.path)
            assert type(path) is unicode, "%r is not unicode" % path
            self.debug('schedule encode of %r', path)
            root, ext = os.path.splitext(os.path.basename(path))
            outpath = os.path.join(outdir, root + '.' + profile.extension)
            self.debug('schedule encode to %r', outpath)
            taskk = encode.EncodeTask(path, os.path.join(outdir,
                root + '.' + profile.extension), profile)
            self.addTask(taskk)

        try:
            htoa = cue.table.tracks[0].indexes[0]
            self.debug('encoding htoa track')
            add(htoa)
        except (KeyError, IndexError):
            self.debug('no htoa track')
            pass

        for trackIndex, track in enumerate(cue.table.tracks):
            self.debug('encoding track %d', trackIndex + 1)
            index = track.indexes[1]
            add(index)

########NEW FILE########
__FILENAME__ = table
# -*- Mode: Python; test-case-name: morituri.test.test_image_table -*-
# vi:si:et:sw=4:sts=4:ts=4

# Morituri - for those about to RIP

# Copyright (C) 2009 Thomas Vander Stichele

# This file is part of morituri.
#
# morituri is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# morituri is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with morituri.  If not, see <http://www.gnu.org/licenses/>.

"""
Wrap Table of Contents.
"""

import copy
import urllib
import urlparse

from morituri.common import common, log
from morituri.configure import configure

# FIXME: taken from libcdio, but no reference found for these

CDTEXT_FIELDS = [
    'ARRANGER',
    'COMPOSER',
    'DISCID',
    'GENRE',
    'MESSAGE',
    'ISRC',
    'PERFORMER',
    'SIZE_INFO',
    'SONGWRITER',
    'TITLE',
    'TOC_INFO',
    'TOC_INFO2',
    'UPC_EAN',
]


class Track:
    """
    I represent a track entry in an Table.

    @ivar number:  track number (1-based)
    @type number:  int
    @ivar audio:   whether the track is audio
    @type audio:   bool
    @type indexes: dict of number -> L{Index}
    @ivar isrc:    ISRC code (12 alphanumeric characters)
    @type isrc:    str
    @ivar cdtext:  dictionary of CD Text information; see L{CDTEXT_KEYS}.
    @type cdtext:  str -> unicode
    """

    number = None
    audio = None
    indexes = None
    isrc = None
    cdtext = None
    session = None

    def __repr__(self):
        return '<Track %02d>' % self.number

    def __init__(self, number, audio=True, session=None):
        self.number = number
        self.audio = audio
        self.indexes = {}
        self.cdtext = {}

    def index(self, number, absolute=None, path=None, relative=None,
              counter=None):
        """
        @type path:  unicode or None
        """
        if path is not None:
            assert type(path) is unicode, "%r is not unicode" % path

        i = Index(number, absolute, path, relative, counter)
        self.indexes[number] = i

    def getIndex(self, number):
        return self.indexes[number]

    def getFirstIndex(self):
        """
        Get the first chronological index for this track.

        Typically this is INDEX 01; but it could be INDEX 00 if there's
        a pre-gap.
        """
        indexes = self.indexes.keys()
        indexes.sort()
        return self.indexes[indexes[0]]

    def getLastIndex(self):
        indexes = self.indexes.keys()
        indexes.sort()
        return self.indexes[indexes[-1]]

    def getPregap(self):
        """
        Returns the length of the pregap for this track.

        The pregap is 0 if there is no index 0, and the difference between
        index 1 and index 0 if there is.
        """
        if 0 not in self.indexes:
            return 0

        return self.indexes[1].absolute - self.indexes[0].absolute


class Index:
    """
    @ivar counter: counter for the index source; distinguishes between
                   the matching FILE lines in .cue files for example
    @type path:    unicode or None
    """
    number = None
    absolute = None
    path = None
    relative = None
    counter = None

    def __init__(self, number, absolute=None, path=None, relative=None,
                 counter=None):

        if path is not None:
            assert type(path) is unicode, "%r is not unicode" % path

        self.number = number
        self.absolute = absolute
        self.path = path
        self.relative = relative
        self.counter = counter

    def __repr__(self):
        return '<Index %02d absolute %r path %r relative %r counter %r>' % (
            self.number, self.absolute, self.path, self.relative, self.counter)


class Table(object, log.Loggable):
    """
    I represent a table of indexes on a CD.

    @ivar tracks:  tracks on this CD
    @type tracks:  list of L{Track}
    @ivar catalog: catalog number
    @type catalog: str
    @type cdtext:  dict of str -> str
    """

    tracks = None # list of Track
    leadout = None # offset where the leadout starts
    catalog = None # catalog number; FIXME: is this UPC ?
    cdtext = None

    classVersion = 4

    def __init__(self, tracks=None):
        if not tracks:
            tracks = []

        self.tracks = tracks
        self.cdtext = {}
        # done this way because just having a class-defined instance var
        # gets overridden when unpickling
        self.instanceVersion = self.classVersion
        self.unpickled()

    def unpickled(self):
        self.logName = "Table 0x%08x v%d" % (id(self), self.instanceVersion)
        self.debug('set logName')

    def getTrackStart(self, number):
        """
        @param number: the track number, 1-based
        @type  number: int

        @returns: the start of the given track number's index 1, in CD frames
        @rtype:   int
        """
        track = self.tracks[number - 1]
        return track.getIndex(1).absolute

    def getTrackEnd(self, number):
        """
        @param number: the track number, 1-based
        @type  number: int

        @returns: the end of the given track number (ie index 1 of next track)
        @rtype:   int
        """
        # default to end of disc
        end = self.leadout - 1

        # if not last track, calculate it from the next track
        if number < len(self.tracks):
            end = self.tracks[number].getIndex(1).absolute - 1

            # if on a session border, subtract the session leadin
            thisTrack = self.tracks[number - 1]
            nextTrack = self.tracks[number]
            if nextTrack.session > thisTrack.session:
                gap = self._getSessionGap(nextTrack.session)
                end -= gap

        return end

    def getTrackLength(self, number):
        """
        @param number: the track number, 1-based
        @type  number: int

        @returns: the length of the given track number, in CD frames
        @rtype:   int
        """
        return self.getTrackEnd(number) - self.getTrackStart(number) + 1

    def getAudioTracks(self):
        """
        @returns: the number of audio tracks on the CD
        @rtype:   int
        """
        return len([t for t in self.tracks if t.audio])

    def hasDataTracks(self):
        """
        @returns: whether this disc contains data tracks
        """
        return len([t for t in self.tracks if not t.audio]) > 0

    def _cddbSum(self, i):
        ret = 0
        while i > 0:
            ret += (i % 10)
            i /= 10

        return ret

    def getCDDBValues(self):
        """
        Get all CDDB values needed to calculate disc id and lookup URL.

        This includes:
         - CDDB disc id
         - number of audio tracks
         - offset of index 1 of each track
         - length of disc in seconds (including data track)

        @rtype:   list of int
        """
        result = []

        result.append(self.getAudioTracks())

        # cddb disc id takes into account data tracks
        # last byte is the number of tracks on the CD
        n = 0

        # CD's have a standard lead-in time of 2 seconds
        # which gets added for CDDB disc id's
        delta = 2 * common.FRAMES_PER_SECOND
        #if self.getTrackStart(1) > 0:
        #    delta = 0

        debug = [str(len(self.tracks))]
        for track in self.tracks:
            offset = self.getTrackStart(track.number) + delta
            result.append(offset)
            debug.append(str(offset))
            seconds = offset / common.FRAMES_PER_SECOND
            n += self._cddbSum(seconds)

        # the 'real' leadout, not offset by 150 frames
        # print 'THOMAS: disc leadout', self.leadout
        last = self.tracks[-1]
        leadout = self.getTrackEnd(last.number) + 1
        self.debug('leadout LBA: %d', leadout)

        # FIXME: we can't replace these calculations with the getFrameLength
        # call because the start and leadout in the algorithm get rounded
        # before making the difference
        startSeconds = self.getTrackStart(1) / common.FRAMES_PER_SECOND
        leadoutSeconds = leadout / common.FRAMES_PER_SECOND
        t = leadoutSeconds - startSeconds
        # durationFrames = self.getFrameLength(data=True)
        # duration = durationFrames / common.FRAMES_PER_SECOND
        # assert t == duration, "%r != %r" % (t, duration)

        debug.append(str(leadoutSeconds + 2)) # 2 is the 150 frame cddb offset
        result.append(leadoutSeconds)

        value = (n % 0xff) << 24 | t << 8 | len(self.tracks)
        result.insert(0, value)

        # compare this debug line to cd-discid output
        self.debug('cddb values: %r', result)

        self.debug('cddb disc id debug: %s',
            " ".join(["%08x" % value, ] + debug))

        return result

    def getCDDBDiscId(self):
        """
        Calculate the CDDB disc ID.

        @rtype:   str
        @returns: the 8-character hexadecimal disc ID
        """
        values = self.getCDDBValues()
        return "%08x" % values[0]

    def getMusicBrainzDiscId(self):
        """
        Calculate the MusicBrainz disc ID.

        @rtype:   str
        @returns: the 28-character base64-encoded disc ID
        """
        values = self._getMusicBrainzValues()

        # MusicBrainz disc id does not take into account data tracks
        # P2.3
        try:
            import hashlib
            sha1 = hashlib.sha1
        except ImportError:
            from sha import sha as sha1
        import base64

        sha = sha1()

        # number of first track
        sha.update("%02X" % values[0])

        # number of last track
        sha.update("%02X" % values[1])

        sha.update("%08X" % values[2])

        # offsets of tracks
        for i in range(1, 100):
            try:
                offset = values[2 + i]
            except IndexError:
                #print 'track', i - 1, '0 offset'
                offset = 0
            sha.update("%08X" % offset)

        digest = sha.digest()
        assert len(digest) == 20, \
            "digest should be 20 chars, not %d" % len(digest)

        # The RFC822 spec uses +, /, and = characters, all of which are special
        # HTTP/URL characters. To avoid the problems with dealing with that, I
        # (Rob) used ., _, and -

        # base64 altchars specify replacements for + and /
        result = base64.b64encode(digest, '._')

        # now replace =
        result = "-".join(result.split("="))
        assert len(result) == 28, \
            "Result should be 28 characters, not %d" % len(result)

        self.log('getMusicBrainzDiscId: returning %r' % result)
        return result

    def getMusicBrainzSubmitURL(self):
        host = 'mm.musicbrainz.org'

        discid = self.getMusicBrainzDiscId()
        values = self._getMusicBrainzValues()

        query = urllib.urlencode({
            'id': discid,
            'toc': ' '.join([str(v) for v in values]),
            'tracks': self.getAudioTracks(),
        })

        return urlparse.urlunparse((
            'http', host, '/bare/cdlookup.html', '', query, ''))

    def getFrameLength(self, data=False):
        """
        Get the length in frames (excluding HTOA)

        @param data: whether to include the data tracks in the length
        """
        # the 'real' leadout, not offset by 150 frames
        if data:
            last = self.tracks[-1]
        else:
            last = self.tracks[self.getAudioTracks() - 1]

        leadout = self.getTrackEnd(last.number) + 1
        self.debug('leadout LBA: %d', leadout)
        durationFrames = leadout - self.getTrackStart(1)

        return durationFrames

    def duration(self):
        """
        Get the duration in ms for all audio tracks (excluding HTOA).
        """
        return int(self.getFrameLength() * 1000.0 / common.FRAMES_PER_SECOND)

    def _getMusicBrainzValues(self):
        """
        Get all MusicBrainz values needed to calculate disc id and submit URL.

        This includes:
         - track number of first track
         - number of audio tracks
         - leadout of disc
         - offset of index 1 of each track

        @rtype:   list of int
        """
        # MusicBrainz disc id does not take into account data tracks

        result = []

        # number of first track
        result.append(1)

        # number of last audio track
        result.append(self.getAudioTracks())

        leadout = self.leadout
        # if the disc is multi-session, last track is the data track,
        # and we should subtract 11250 + 150 from the last track's offset
        # for the leadout
        if self.hasDataTracks():
            assert not self.tracks[-1].audio
            leadout = self.tracks[-1].getIndex(1).absolute - 11250 - 150

        # treat leadout offset as track 0 offset
        result.append(150 + leadout)

        # offsets of tracks
        for i in range(1, 100):
            try:
                track = self.tracks[i - 1]
                if not track.audio:
                    continue
                offset = track.getIndex(1).absolute + 150
                result.append(offset)
            except IndexError:
                pass


        self.log('Musicbrainz values: %r', result)
        return result

    def getAccurateRipIds(self):
        """
        Calculate the two AccurateRip ID's.

        @returns: the two 8-character hexadecimal disc ID's
        @rtype:   tuple of (str, str)
        """
        # AccurateRip does not take into account data tracks,
        # but does count the data track to determine the leadout offset
        discId1 = 0
        discId2 = 0

        for track in self.tracks:
            if not track.audio:
                continue
            offset = self.getTrackStart(track.number)
            discId1 += offset
            discId2 += (offset or 1) * track.number

        # also add end values, where leadout offset is one past the end
        # of the last track
        last = self.tracks[-1]
        offset = self.getTrackEnd(last.number) + 1
        discId1 += offset
        discId2 += offset * (self.getAudioTracks() + 1)

        discId1 &= 0xffffffff
        discId2 &= 0xffffffff

        return ("%08x" % discId1, "%08x" % discId2)

    def getAccurateRipURL(self):
        """
        Return the full AccurateRip URL.

        @returns: the AccurateRip URL
        @rtype:   str
        """
        discId1, discId2 = self.getAccurateRipIds()

        return "http://www.accuraterip.com/accuraterip/" \
            "%s/%s/%s/dBAR-%.3d-%s-%s-%s.bin" % (
                discId1[-1], discId1[-2], discId1[-3],
                self.getAudioTracks(), discId1, discId2, self.getCDDBDiscId())

    def cue(self, cuePath='', program='Morituri'):
        """
        @param cuePath: path to the cue file to be written. If empty,
                        will treat paths as if in current directory.


        Dump our internal representation to a .cue file content.

        @rtype: C{unicode}
        """
        self.debug('generating .cue for cuePath %r', cuePath)

        lines = []

        def writeFile(path):
            targetPath = common.getRelativePath(path, cuePath)
            line = 'FILE "%s" WAVE' % targetPath
            lines.append(line)
            self.debug('writeFile: %r' % line)

        # header
        main = ['PERFORMER', 'TITLE']

        for key in CDTEXT_FIELDS:
                if key not in main and key in self.cdtext:
                    lines.append("    %s %s" % (key, self.cdtext[key]))

        assert self.hasTOC(), "Table does not represent a full CD TOC"
        lines.append('REM DISCID %s' % self.getCDDBDiscId().upper())
        lines.append('REM COMMENT "%s %s"' % (program, configure.version))

        if self.catalog:
            lines.append("CATALOG %s" % self.catalog)

        for key in main:
            if key in self.cdtext:
                lines.append('%s "%s"' % (key, self.cdtext[key]))

        # FIXME:
        # - the first FILE statement goes before the first TRACK, even if
        #   there is a non-file-using PREGAP
        # - the following FILE statements come after the last INDEX that
        #   use that FILE; so before a next TRACK, PREGAP silence, ...

        # add the first FILE line; EAC always puts the first FILE
        # statement before TRACK 01 and any possible PRE-GAP
        firstTrack = self.tracks[0]
        index = firstTrack.getFirstIndex()
        indexOne = firstTrack.getIndex(1)
        counter = index.counter
        track = firstTrack

        while not index.path:
            t, i = self.getNextTrackIndex(track.number, index.number)
            track = self.tracks[t - 1]
            index = track.getIndex(i)
            counter = index.counter

        if index.path:
            self.debug('counter %d, writeFile' % counter)
            writeFile(index.path)

        for i, track in enumerate(self.tracks):
            self.debug('track i %r, track %r' % (i, track))
            # FIXME: skip data tracks for now
            if not track.audio:
                continue

            indexes = track.indexes.keys()
            indexes.sort()

            wroteTrack = False

            for number in indexes:
                index = track.indexes[number]
                self.debug('index %r, %r' % (number, index))

                # any time the source counter changes to a higher value,
                # write a FILE statement
                # it has to be higher, because we can run into the HTOA
                # at counter 0 here
                if index.counter > counter:
                    if index.path:
                        self.debug('counter %d, writeFile' % counter)
                        writeFile(index.path)
                    self.debug('setting counter to index.counter %r' %
                        index.counter)
                    counter = index.counter

                # any time we hit the first index, write a TRACK statement
                if not wroteTrack:
                    wroteTrack = True
                    line = "  TRACK %02d %s" % (i + 1, 'AUDIO')
                    lines.append(line)
                    self.debug('%r' % line)

                    for key in CDTEXT_FIELDS:
                        if key in track.cdtext:
                            lines.append('    %s "%s"' % (
                                key, track.cdtext[key]))

                    if track.isrc is not None:
                        lines.append("    ISRC %s" % track.isrc)

                    # handle TRACK 01 INDEX 00 specially
                    if 0 in indexes:
                        index00 = track.indexes[0]
                        if i == 0:
                            # if we have a silent pre-gap, output it
                            if not index00.path:
                                length = indexOne.absolute - index00.absolute
                                lines.append("    PREGAP %s" %
                                    common.framesToMSF(length))
                                continue

                        # handle any other INDEX 00 after its TRACK
                        lines.append("    INDEX %02d %s" % (0,
                            common.framesToMSF(index00.relative)))

                if number > 0:
                    # index 00 is output after TRACK up above
                    lines.append("    INDEX %02d %s" % (number,
                        common.framesToMSF(index.relative)))

        lines.append("")

        return "\n".join(lines)

    ### methods that modify the table

    def clearFiles(self):
        """
        Clear all file backings.
        Resets indexes paths and relative offsets.
        """
        # FIXME: do a loop over track indexes better, with a pythonic
        # construct that allows you to do for t, i in ...
        t = self.tracks[0].number
        index = self.tracks[0].getFirstIndex()
        i = index.number

        self.debug('clearing path')
        while True:
            track = self.tracks[t - 1]
            index = track.getIndex(i)
            self.debug('Clearing path on track %d, index %d', t, i)
            index.path = None
            index.relative = None
            try:
                t, i = self.getNextTrackIndex(t, i)
            except IndexError:
                break

    def setFile(self, track, index, path, length, counter=None):
        """
        Sets the given file as the source from the given index on.
        Will loop over all indexes that fall within the given length,
        to adjust the path.

        Assumes all indexes have an absolute offset and will raise if not.

        @type  track: C{int}
        @type  index: C{int}
        """
        self.debug('setFile: track %d, index %d, path %r, '
            'length %r, counter %r', track, index, path, length, counter)

        t = self.tracks[track - 1]
        i = t.indexes[index]
        start = i.absolute
        assert start is not None, "index %r is missing absolute offset" % i
        end = start + length - 1 # last sector that should come from this file

        # FIXME: check border conditions here, esp. wrt. toc's off-by-one bug
        while i.absolute <= end:
            i.path = path
            i.relative = i.absolute - start
            i.counter = counter
            self.debug('Setting path %r, relative %r on '
                'track %d, index %d, counter %r',
                path, i.relative, track, index, counter)
            try:
                track, index = self.getNextTrackIndex(track, index)
                t = self.tracks[track - 1]
                i = t.indexes[index]
            except IndexError:
                break

    def absolutize(self):
        """
        Calculate absolute offsets on indexes as much as possible.
        Only possible for as long as tracks draw from the same file.
        """
        t = self.tracks[0].number
        index = self.tracks[0].getFirstIndex()
        i = index.number
        # the first cut is the deepest
        counter = index.counter

        #for t in self.tracks: print t, t.indexes
        self.debug('absolutizing')
        while True:
            track = self.tracks[t - 1]
            index = track.getIndex(i)
            assert track.number == t
            assert index.number == i
            if index.counter is None:
                self.debug('Track %d, index %d has no counter', t, i)
                break
            if index.counter != counter:
                self.debug('Track %d, index %d has a different counter', t, i)
                break
            self.debug('Setting absolute offset %d on track %d, index %d',
                index.relative, t, i)
            if index.absolute is not None:
                if index.absolute != index.relative:
                    msg = 'Track %d, index %d had absolute %d,' \
                        ' overriding with %d' % (
                            t, i, index.absolute, index.relative)
                    raise ValueError(msg)
            index.absolute = index.relative
            try:
                t, i = self.getNextTrackIndex(t, i)
            except IndexError:
                break

    def merge(self, other, session=2):
        """
        Merges the given table at the end.
        The other table is assumed to be from an additional session,


        @type  other: L{Table}
        """
        gap = self._getSessionGap(session)

        trackCount = len(self.tracks)
        sourceCounter = self.tracks[-1].getLastIndex().counter

        for track in other.tracks:
            t = copy.deepcopy(track)
            t.number = track.number + trackCount
            t.session = session
            for i in t.indexes.values():
                if i.absolute is not None:
                    i.absolute += self.leadout + gap
                    self.debug('Fixing track %02d, index %02d, absolute %d' % (
                        t.number, i.number, i.absolute))
                if i.counter is not None:
                    i.counter += sourceCounter
                    self.debug('Fixing track %02d, index %02d, counter %d' % (
                        t.number, i.number, i.counter))
            self.tracks.append(t)

        self.leadout += other.leadout + gap # FIXME
        self.debug('Fixing leadout, now %d', self.leadout)

    def _getSessionGap(self, session):
        # From cdrecord multi-session info:
        # For the first additional session this is 11250 sectors
        # lead-out/lead-in overhead + 150 sectors for the pre-gap of the first
        # track after the lead-in = 11400 sectos.

        # For all further session this is 6750 sectors lead-out/lead-in
        # overhead + 150 sectors for the pre-gap of the first track after the
        # lead-in = 6900 sectors.

        gap = 11400
        if session > 2:
            gap = 6900
        return gap

    ### lookups

    def getNextTrackIndex(self, track, index):
        """
        Return the next track and index.

        @param track: track number, 1-based

        @raises IndexError: on last index

        @rtype: tuple of (int, int)
        """
        t = self.tracks[track - 1]
        indexes = t.indexes.keys()
        position = indexes.index(index)

        if position + 1 < len(indexes):
            return track, indexes[position + 1]

        track += 1
        if track > len(self.tracks):
            raise IndexError("No index beyond track %d, index %d" % (
                track - 1, index))

        t = self.tracks[track - 1]
        indexes = t.indexes.keys()

        return track, indexes[0]

    # various tests for types of Table

    def hasTOC(self):
        """
        Check if the Table has a complete TOC.
        a TOC is a list of all tracks and their Index 01, with absolute
        offsets, as well as the leadout.
        """
        if not self.leadout:
            self.debug('no leadout, no TOC')
            return False

        for t in self.tracks:
            if 1 not in t.indexes.keys():
                self.debug('no index 1, no TOC')
                return False
            if t.indexes[1].absolute is None:
                self.debug('no absolute index 1, no TOC')
                return False

        return True

    def canCue(self):
        """
        Check if this table can be used to generate a .cue file
        """
        if not self.hasTOC():
            self.debug('No TOC, cannot cue')
            return False

        for t in self.tracks:
            for i in t.indexes.values():
                if i.relative is None:
                    self.debug('Track %02d, Index %02d does not have relative',
                        t.number, i.number)
                    return False

        return True

########NEW FILE########
__FILENAME__ = toc
# -*- Mode: Python; test-case-name: morituri.test.test_image_toc -*-
# vi:si:et:sw=4:sts=4:ts=4

# Morituri - for those about to RIP

# Copyright (C) 2009 Thomas Vander Stichele

# This file is part of morituri.
#
# morituri is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# morituri is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with morituri.  If not, see <http://www.gnu.org/licenses/>.

"""
Reading .toc files

The .toc file format is described in the man page of cdrdao
"""

import re
import codecs

from morituri.common import common, log
from morituri.image import table

# shared
_CDTEXT_CANDIDATE_RE = re.compile(r'(?P<key>\w+) "(?P<value>.+)"')

# header
_CATALOG_RE = re.compile(r'^CATALOG "(?P<catalog>\d+)"$')

# records
_TRACK_RE = re.compile(r"""
    ^TRACK            # TRACK
    \s(?P<mode>.+)$   # mode (AUDIO, MODE2_FORM_MIX, MODEx/2xxx, ...)
""", re.VERBOSE)

_ISRC_RE = re.compile(r'^ISRC "(?P<isrc>\w+)"$')

# a HTOA is marked in the cdrdao's TOC as SILENCE
_SILENCE_RE = re.compile(r"""
    ^SILENCE              # SILENCE
    \s(?P<length>.*)$     # pre-gap length
""", re.VERBOSE)

# ZERO is used as pre-gap source when switching mode
_ZERO_RE = re.compile(r"""
    ^ZERO                 # ZERO
    \s(?P<mode>.+)        # mode (AUDIO, MODEx/2xxx, ...)
    \s(?P<length>.*)$     # zero length
""", re.VERBOSE)


_FILE_RE = re.compile(r"""
    ^FILE                 # FILE
    \s+"(?P<name>.*)"     # 'file name' in quotes
    \s+(?P<start>.+)      # start offset
    \s(?P<length>.+)$     # length in frames of section
""", re.VERBOSE)

_DATAFILE_RE = re.compile(r"""
    ^DATAFILE             # DATA FILE
    \s+"(?P<name>.*)"     # 'file name' in quotes
    \s+(?P<length>\S+)    # start offset
    \s*.*                 # possible // comment
""", re.VERBOSE)


# FIXME: start can be 0
_START_RE = re.compile(r"""
    ^START                # START
    \s(?P<length>.*)$     # pre-gap length
""", re.VERBOSE)


_INDEX_RE = re.compile(r"""
    ^INDEX            # INDEX
    \s(?P<offset>.+)$ # start offset
""", re.VERBOSE)


class Sources(log.Loggable):
    """
    I represent the list of sources used in the .toc file.
    Each SILENCE and each FILE is a source.
    If the filename for FILE doesn't change, the counter is not increased.
    """

    def __init__(self):
        self._sources = []

    def append(self, counter, offset, source):
        """
        @param counter: the source counter; updates for each different
                        data source (silence or different file path)
        @type  counter: int
        @param offset:  the absolute disc offset where this source starts
        """
        self.debug('Appending source, counter %d, abs offset %d, source %r' % (
            counter, offset, source))
        self._sources.append((counter, offset, source))

    def get(self, offset):
        """
        Retrieve the source used at the given offset.
        """
        for i, (c, o, s) in enumerate(self._sources):
            if offset < o:
                return self._sources[i - 1]

        return self._sources[-1]

    def getCounterStart(self, counter):
        """
        Retrieve the absolute offset of the first source for this counter
        """
        for i, (c, o, s) in enumerate(self._sources):
            if c == counter:
                return self._sources[i][1]

        return self._sources[-1][1]


class TocFile(object, log.Loggable):

    def __init__(self, path):
        """
        @type  path: unicode
        """
        assert type(path) is unicode, "%r is not unicode" % path
        self._path = path
        self._messages = []
        self.table = table.Table()
        self.logName = '<TocFile %08x>' % id(self)

        self._sources = Sources()

    def _index(self, currentTrack, i, absoluteOffset, trackOffset):
        absolute = absoluteOffset + trackOffset
        # this may be in a new source, so calculate relative
        c, o, s = self._sources.get(absolute)
        self.debug('at abs offset %d, we are in source %r' % (
            absolute, s))
        counterStart = self._sources.getCounterStart(c)
        relative = absolute - counterStart

        currentTrack.index(i, path=s.path,
            absolute=absolute,
            relative=relative,
            counter=c)
        self.debug(
            '[track %02d index %02d] trackOffset %r, added %r',
                currentTrack.number, i, trackOffset,
                currentTrack.getIndex(i))


    def parse(self):
        # these two objects start as None then get set as real objects,
        # so no need to complain about them here
        __pychecker__ = 'no-objattrs'
        currentFile = None
        currentTrack = None

        state = 'HEADER'
        counter = 0 # counts sources for audio data; SILENCE/ZERO/FILE
        trackNumber = 0
        indexNumber = 0
        absoluteOffset = 0 # running absolute offset of where each track starts
        relativeOffset = 0 # running relative offset, relative to counter src
        currentLength = 0 # accrued during TRACK record parsing;
                          # length of current track as parsed so far;
                          # reset on each TRACK statement
        totalLength = 0 # accrued during TRACK record parsing, total disc
        pregapLength = 0 # length of the pre-gap, current track in for loop

        # the first track's INDEX 1 can only be gotten from the .toc
        # file once the first pregap is calculated; so we add INDEX 1
        # at the end of each parsed  TRACK record
        handle = codecs.open(self._path, "r", "utf-8")

        for number, line in enumerate(handle.readlines()):
            line = line.rstrip()

            # look for CDTEXT stuff in either header or tracks
            m = _CDTEXT_CANDIDATE_RE.search(line)
            if m:
                key = m.group('key')
                value = m.group('value')
                # usually, value is encoded with octal escapes and in latin-1
                # FIXME: other encodings are possible, does cdrdao handle
                # them ?
                value = value.decode('string-escape').decode('latin-1')
                if key in table.CDTEXT_FIELDS:
                    # FIXME: consider ISRC separate for now, but this
                    # is a limitation of our parser approach
                    if state == 'HEADER':
                        self.table.cdtext[key] = value
                        self.debug('Found disc CD-Text %s: %r', key, value)
                    elif state == 'TRACK':
                        if key != 'ISRC' or not currentTrack \
                            or currentTrack.isrc is not None:
                            self.debug('Found track CD-Text %s: %r',
                                key, value)
                            currentTrack.cdtext[key] = value

            # look for header elements
            m = _CATALOG_RE.search(line)
            if m:
                self.table.catalog = m.group('catalog')
                self.debug("Found catalog number %s", self.table.catalog)

            # look for TRACK lines
            m = _TRACK_RE.search(line)
            if m:
                state = 'TRACK'

                # set index 1 of previous track if there was one, using
                # pregapLength if applicable
                if currentTrack:
                    self._index(currentTrack, 1, absoluteOffset, pregapLength)

                # create a new track to be filled by later lines
                trackNumber += 1
                trackMode = m.group('mode')
                audio = trackMode == 'AUDIO'
                currentTrack = table.Track(trackNumber, audio=audio)
                self.table.tracks.append(currentTrack)

                # update running totals
                absoluteOffset += currentLength
                relativeOffset += currentLength
                totalLength += currentLength

                # FIXME: track mode
                self.debug('found track %d, mode %s, at absoluteOffset %d',
                    trackNumber, trackMode, absoluteOffset)

                # reset counters relative to a track
                currentLength = 0
                indexNumber = 1
                pregapLength = 0

                continue

            # look for ISRC lines
            m = _ISRC_RE.search(line)
            if m:
                isrc = m.group('isrc')
                currentTrack.isrc = isrc
                self.debug('Found ISRC code %s', isrc)

            # look for SILENCE lines
            m = _SILENCE_RE.search(line)
            if m:
                length = m.group('length')
                self.debug('SILENCE of %r', length)
                self._sources.append(counter, absoluteOffset, None)
                if currentFile is not None:
                    self.debug('SILENCE after FILE, increasing counter')
                    counter += 1
                    relativeOffset = 0
                    currentFile = None
                currentLength += common.msfToFrames(length)

            # look for ZERO lines
            m = _ZERO_RE.search(line)
            if m:
                if currentFile is not None:
                    self.debug('ZERO after FILE, increasing counter')
                    counter += 1
                    relativeOffset = 0
                    currentFile = None
                length = m.group('length')
                currentLength += common.msfToFrames(length)

            # look for FILE lines
            m = _FILE_RE.search(line)
            if m:
                filePath = m.group('name')
                start = m.group('start')
                length = m.group('length')
                self.debug('FILE %s, start %r, length %r',
                    filePath, common.msfToFrames(start),
                    common.msfToFrames(length))
                if not currentFile or filePath != currentFile.path:
                    counter += 1
                    relativeOffset = 0
                    self.debug('track %d, switched to new FILE, '
                               'increased counter to %d',
                        trackNumber, counter)
                currentFile = File(filePath, common.msfToFrames(start),
                    common.msfToFrames(length))
                self._sources.append(counter, absoluteOffset + currentLength,
                    currentFile)
                #absoluteOffset += common.msfToFrames(start)
                currentLength += common.msfToFrames(length)

            # look for DATAFILE lines
            m = _DATAFILE_RE.search(line)
            if m:
                filePath = m.group('name')
                length = m.group('length')
                # print 'THOMAS', length
                self.debug('FILE %s, length %r',
                    filePath, common.msfToFrames(length))
                if not currentFile or filePath != currentFile.path:
                    counter += 1
                    relativeOffset = 0
                    self.debug('track %d, switched to new FILE, '
                        'increased counter to %d',
                        trackNumber, counter)
                # FIXME: assume that a MODE2_FORM_MIX track always starts at 0
                currentFile = File(filePath, 0, common.msfToFrames(length))
                self._sources.append(counter, absoluteOffset + currentLength,
                    currentFile)
                #absoluteOffset += common.msfToFrames(start)
                currentLength += common.msfToFrames(length)


            # look for START lines
            m = _START_RE.search(line)
            if m:
                if not currentTrack:
                    self.message(number, 'START without preceding TRACK')
                    print 'ouch'
                    continue

                length = common.msfToFrames(m.group('length'))
                c, o, s = self._sources.get(absoluteOffset)
                self.debug('at abs offset %d, we are in source %r' % (
                    absoluteOffset, s))
                counterStart = self._sources.getCounterStart(c)
                relativeOffset = absoluteOffset - counterStart

                currentTrack.index(0, path=s and s.path or None,
                    absolute=absoluteOffset,
                    relative=relativeOffset, counter=c)
                self.debug('[track %02d index 00] added %r',
                    currentTrack.number, currentTrack.getIndex(0))
                # store the pregapLength to add it when we index 1 for this
                # track on the next iteration
                pregapLength = length

            # look for INDEX lines
            m = _INDEX_RE.search(line)
            if m:
                if not currentTrack:
                    self.message(number, 'INDEX without preceding TRACK')
                    print 'ouch'
                    continue

                indexNumber += 1
                offset = common.msfToFrames(m.group('offset'))
                self._index(currentTrack, indexNumber, absoluteOffset, offset)

        # handle index 1 of final track, if any
        if currentTrack:
            self._index(currentTrack, 1, absoluteOffset, pregapLength)

        # totalLength was added up to the penultimate track
        self.table.leadout = totalLength + currentLength
        self.debug('parse: leadout: %r', self.table.leadout)

    def message(self, number, message):
        """
        Add a message about a given line in the cue file.

        @param number: line number, counting from 0.
        """
        self._messages.append((number + 1, message))

    def getTrackLength(self, track):
        """
        Returns the length of the given track, from its INDEX 01 to the next
        track's INDEX 01
        """
        # returns track length in frames, or -1 if can't be determined and
        # complete file should be assumed
        # FIXME: this assumes a track can only be in one file; is this true ?
        i = self.table.tracks.index(track)
        if i == len(self.table.tracks) - 1:
            # last track, so no length known
            return -1

        thisIndex = track.indexes[1] # FIXME: could be more
        nextIndex = self.table.tracks[i + 1].indexes[1] # FIXME: could be 0

        c = thisIndex.counter
        if c is not None and c == nextIndex.counter:
            # they belong to the same source, so their relative delta is length
            return nextIndex.relative - thisIndex.relative

        # FIXME: more logic
        return -1

    def getRealPath(self, path):
        """
        Translate the .toc's FILE to an existing path.

        @type  path: unicode
        """
        return common.getRealPath(self._path, path)


class File:
    """
    I represent a FILE line in a .toc file.
    """

    def __init__(self, path, start, length):
        """
        @type  path:   C{unicode}
        @type  start:  C{int}
        @param start:  starting point for the track in this file, in frames
        @param length: length for the track in this file, in frames
        """
        assert type(path) is unicode, "%r is not unicode" % path

        self.path = path
        self.start = start
        self.length = length

    def __repr__(self):
        return '<File %r>' % (self.path, )

########NEW FILE########
__FILENAME__ = cdparanoia
# -*- Mode: Python; test-case-name: morituri.test.test_program_cdparanoia -*-
# vi:si:et:sw=4:sts=4:ts=4

# Morituri - for those about to RIP

# Copyright (C) 2009 Thomas Vander Stichele

# This file is part of morituri.
#
# morituri is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# morituri is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with morituri.  If not, see <http://www.gnu.org/licenses/>.

import os
import errno
import time
import re
import stat
import shutil
import subprocess
import tempfile

from morituri.common import log, common
from morituri.common import task as ctask

from morituri.extern import asyncsub
from morituri.extern.task import task


class FileSizeError(Exception):

    message = None

    """
    The given path does not have the expected size.
    """

    def __init__(self, path, message):
        self.args = (path, message)
        self.path = path
        self.message = message


class ReturnCodeError(Exception):
    """
    The program had a non-zero return code.
    """

    def __init__(self, returncode):
        self.args = (returncode, )
        self.returncode = returncode


class ChecksumException(Exception):
    pass


# example:
# ##: 0 [read] @ 24696
_PROGRESS_RE = re.compile(r"""
    ^\#\#: (?P<code>.+)\s         # function code
    \[(?P<function>.*)\]\s@\s     # [function name] @
    (?P<offset>\d+)               # offset in words (2-byte one channel value)
""", re.VERBOSE)

_ERROR_RE = re.compile("^scsi_read error:")

# from reading cdparanoia source code, it looks like offset is reported in
# number of single-channel samples, ie. 2 bytes (word) per unit, and absolute


class ProgressParser(log.Loggable):
    read = 0 # last [read] frame
    wrote = 0 # last [wrote] frame
    errors = 0 # count of number of scsi errors
    _nframes = None # number of frames read on each [read]
    _firstFrames = None # number of frames read on first [read]
    reads = 0 # total number of reads

    def __init__(self, start, stop):
        """
        @param start:  first frame to rip
        @type  start:  int
        @param stop:   last frame to rip (inclusive)
        @type  stop:   int
        """
        self.start = start
        self.stop = stop

        # FIXME: privatize
        self.read = start

        self._reads = {} # read count for each sector

    def parse(self, line):
        """
        Parse a line.
        """
        m = _PROGRESS_RE.search(line)
        if m:
            # code = int(m.group('code'))
            function = m.group('function')
            wordOffset = int(m.group('offset'))
            if function == 'read':
                self._parse_read(wordOffset)
            elif function == 'wrote':
                self._parse_wrote(wordOffset)

        m = _ERROR_RE.search(line)
        if m:
            self.errors += 1

    def _parse_read(self, wordOffset):
        if wordOffset % common.WORDS_PER_FRAME != 0:
            print 'THOMAS: not a multiple of %d: %d' % (
                common.WORDS_PER_FRAME, wordOffset)
            return

        frameOffset = wordOffset / common.WORDS_PER_FRAME

        # set nframes if not yet set
        if self._nframes is None and self.read != 0:
            self._nframes = frameOffset - self.read
            self.debug('set nframes to %r', self._nframes)

        # set firstFrames if not yet set
        if self._firstFrames is None:
            self._firstFrames = frameOffset - self.start
            self.debug('set firstFrames to %r', self._firstFrames)

        markStart = None
        markEnd = None # the next unread frame (half-inclusive)

        # verify it either read nframes more or went back for verify
        if frameOffset > self.read:
            delta = frameOffset - self.read
            if self._nframes and delta != self._nframes:
                # print 'THOMAS: Read %d frames more, not %d' % (
                # delta, self._nframes)
                # my drive either reads 7 or 13 frames
                pass

            # update our read sectors hash
            markStart = self.read
            markEnd = frameOffset
        else:
            # went back to verify
            # we could use firstFrames as an estimate on how many frames this
            # read, but this lowers our track quality needlessly where
            # EAC still reports 100% track quality
            markStart = frameOffset # - self._firstFrames
            markEnd = frameOffset

        # FIXME: doing this is way too slow even for a testcase, so disable
        if False:
            for frame in range(markStart, markEnd):
                if not frame in self._reads.keys():
                    self._reads[frame] = 0
                self._reads[frame] += 1

        # cdparanoia reads quite a bit beyond the current track before it
        # goes back to verify; don't count those
        # markStart, markEnd of 0, 21 with stop 0 should give 1 read
        if markEnd > self.stop + 1:
            markEnd = self.stop + 1
        if markStart > self.stop + 1:
            markStart = self.stop + 1

        self.reads += markEnd - markStart

        # update our read pointer
        self.read = frameOffset

    def _parse_wrote(self, wordOffset):
        # cdparanoia outputs most [wrote] calls with one word less than a frame
        frameOffset = (wordOffset + 1) / common.WORDS_PER_FRAME
        self.wrote = frameOffset

    def getTrackQuality(self):
        """
        Each frame gets read twice.
        More than two reads for a frame reduce track quality.
        """
        frames = self.stop - self.start + 1 # + 1 since stop is inclusive
        reads = self.reads
        self.debug('getTrackQuality: frames %d, reads %d' % (frames, reads))

        # don't go over a 100%; we know cdparanoia reads each frame at least
        # twice
        return min(frames * 2.0 / reads, 1.0)


# FIXME: handle errors


class ReadTrackTask(log.Loggable, task.Task):
    """
    I am a task that reads a track using cdparanoia.

    @ivar reads: how many reads were done to rip the track
    """

    description = "Reading track"
    quality = None # set at end of reading
    speed = None
    duration = None # in seconds

    _MAXERROR = 100 # number of errors detected by parser

    def __init__(self, path, table, start, stop, offset=0, device=None,
        action="Reading", what="track"):
        """
        Read the given track.

        @param path:   where to store the ripped track
        @type  path:   unicode
        @param table:  table of contents of CD
        @type  table:  L{table.Table}
        @param start:  first frame to rip
        @type  start:  int
        @param stop:   last frame to rip (inclusive); >= start
        @type  stop:   int
        @param offset: read offset, in samples
        @type  offset: int
        @param device: the device to rip from
        @type  device: str
        @param action: a string representing the action; e.g. Read/Verify
        @type  action: str
        @param what:   a string representing what's being read; e.g. Track
        @type  what:   str
        """
        assert type(path) is unicode, "%r is not unicode" % path

        self.path = path
        self._table = table
        self._start = start
        self._stop = stop
        self._offset = offset
        self._parser = ProgressParser(start, stop)
        self._device = device
        self._start_time = None

        self._buffer = "" # accumulate characters
        self._errors = []
        self.description = "%s %s" % (action, what)

    def start(self, runner):
        task.Task.start(self, runner)

        # find on which track the range starts and stops
        startTrack = 0
        startOffset = 0
        stopTrack = 0
        stopOffset = self._stop

        for i, t in enumerate(self._table.tracks):
            if self._table.getTrackStart(i + 1) <= self._start:
                startTrack = i + 1
                startOffset = self._start - self._table.getTrackStart(i + 1)
            if self._table.getTrackEnd(i + 1) <= self._stop:
                stopTrack = i + 1
                stopOffset = self._stop - self._table.getTrackStart(i + 1)

        self.debug('Ripping from %d to %d (inclusive)',
            self._start, self._stop)
        self.debug('Starting at track %d, offset %d',
            startTrack, startOffset)
        self.debug('Stopping at track %d, offset %d',
            stopTrack, stopOffset)

        bufsize = 1024
        argv = ["cdparanoia", "--stderr-progress",
            "--sample-offset=%d" % self._offset, ]
        if self._device:
            argv.extend(["--force-cdrom-device", self._device, ])
        argv.extend(["%d[%s]-%d[%s]" % (
                startTrack, common.framesToHMSF(startOffset),
                stopTrack, common.framesToHMSF(stopOffset)),
            self.path])
        self.debug('Running %s' % (" ".join(argv), ))
        try:
            self._popen = asyncsub.Popen(argv,
                bufsize=bufsize,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, close_fds=True)
        except OSError, e:
            import errno
            if e.errno == errno.ENOENT:
                raise common.MissingDependencyException('cdparanoia')

            raise

        self._start_time = time.time()
        self.schedule(1.0, self._read, runner)

    def _read(self, runner):
        ret = self._popen.recv_err()
        if not ret:
            if self._popen.poll() is not None:
                self._done()
                return
            self.schedule(0.01, self._read, runner)
            return

        self._buffer += ret

        # parse buffer into lines if possible, and parse them
        if "\n" in self._buffer:
            lines = self._buffer.split('\n')
            if lines[-1] != "\n":
                # last line didn't end yet
                self._buffer = lines[-1]
                del lines[-1]
            else:
                self._buffer = ""

            for line in lines:
                self._parser.parse(line)

            # fail if too many errors
            if self._parser.errors > self._MAXERROR:
                self.debug('%d errors, terminating', self._parser.errors)
                self._popen.terminate()

            num = self._parser.wrote - self._start + 1
            den = self._stop - self._start + 1
            assert den != 0, "stop %d should be >= start %d" % (
                self._stop, self._start)
            progress = float(num) / float(den)
            if progress < 1.0:
                self.setProgress(progress)

        # 0 does not give us output before we complete, 1.0 gives us output
        # too late
        self.schedule(0.01, self._read, runner)

    def _poll(self, runner):
        if self._popen.poll() is None:
            self.schedule(1.0, self._poll, runner)
            return

        self._done()

    def _done(self):
        end_time = time.time()
        self.setProgress(1.0)

        # check if the length matches
        size = os.stat(self.path)[stat.ST_SIZE]
        # wav header is 44 bytes
        offsetLength = self._stop - self._start + 1
        expected = offsetLength * common.BYTES_PER_FRAME + 44
        if size != expected:
            # FIXME: handle errors better
            self.warning('file size %d did not match expected size %d',
                size, expected)
            if (size - expected) % common.BYTES_PER_FRAME == 0:
                self.warning('%d frames difference' % (
                    (size - expected) / common.BYTES_PER_FRAME))
            else:
                self.warning('non-integral amount of frames difference')

            self.setAndRaiseException(FileSizeError(self.path,
                "File size %d did not match expected size %d" % (
                    size, expected)))

        if not self.exception and self._popen.returncode != 0:
            if self._errors:
                print "\n".join(self._errors)
            else:
                self.warning('exit code %r', self._popen.returncode)
                self.exception = ReturnCodeError(self._popen.returncode)

        self.quality = self._parser.getTrackQuality()
        self.duration = end_time - self._start_time
        self.speed = (offsetLength / 75.0) / self.duration

        self.stop()
        return


class ReadVerifyTrackTask(log.Loggable, task.MultiSeparateTask):
    """
    I am a task that reads and verifies a track using cdparanoia.
    I also encode the track.

    The path where the file is stored can be changed if necessary, for
    example if the file name is too long.

    @ivar path:         the path where the file is to be stored.
    @ivar checksum:     the checksum of the track; set if they match.
    @ivar testchecksum: the test checksum of the track.
    @ivar copychecksum: the copy checksum of the track.
    @ivar testspeed:    the test speed of the track, as a multiple of
                        track duration.
    @ivar copyspeed:    the copy speed of the track, as a multiple of
                        track duration.
    @ivar testduration: the test duration of the track, in seconds.
    @ivar copyduration: the copy duration of the track, in seconds.
    @ivar peak:         the peak level of the track
    """

    checksum = None
    testchecksum = None
    copychecksum = None
    peak = None
    quality = None
    testspeed = None
    copyspeed = None
    testduration = None
    copyduration = None

    _tmpwavpath = None
    _tmppath = None

    def __init__(self, path, table, start, stop, offset=0, device=None,
                 profile=None, taglist=None, what="track"):
        """
        @param path:    where to store the ripped track
        @type  path:    str
        @param table:   table of contents of CD
        @type  table:   L{table.Table}
        @param start:   first frame to rip
        @type  start:   int
        @param stop:    last frame to rip (inclusive)
        @type  stop:    int
        @param offset:  read offset, in samples
        @type  offset:  int
        @param device:  the device to rip from
        @type  device:  str
        @param profile: the encoding profile
        @type  profile: L{encode.Profile}
        @param taglist: a list of tags
        @param taglist: L{gst.TagList}
        """
        task.MultiSeparateTask.__init__(self)

        self.debug('Creating read and verify task on %r', path)
        self.path = path

        if taglist:
            self.debug('read and verify with taglist %r', taglist)
        # FIXME: choose a dir on the same disk/dir as the final path
        fd, tmppath = tempfile.mkstemp(suffix='.morituri.wav')
        tmppath = unicode(tmppath)
        os.close(fd)
        self._tmpwavpath = tmppath

        # here to avoid import gst eating our options
        from morituri.common import checksum

        self.tasks = []
        self.tasks.append(
            ReadTrackTask(tmppath, table, start, stop,
                offset=offset, device=device, what=what))
        self.tasks.append(checksum.CRC32Task(tmppath))
        t = ReadTrackTask(tmppath, table, start, stop,
            offset=offset, device=device, action="Verifying", what=what)
        self.tasks.append(t)
        self.tasks.append(checksum.CRC32Task(tmppath))

        fd, tmpoutpath = tempfile.mkstemp(suffix='.morituri.%s' %
            profile.extension)
        tmpoutpath = unicode(tmpoutpath)
        os.close(fd)
        self._tmppath = tmpoutpath

        # here to avoid import gst eating our options
        from morituri.common import encode

        self.tasks.append(encode.EncodeTask(tmppath, tmpoutpath, profile,
            taglist=taglist, what=what))
        # make sure our encoding is accurate
        self.tasks.append(checksum.CRC32Task(tmpoutpath))

        self.checksum = None

        umask = os.umask(0)
        os.umask(umask)
        self.file_mode = 0666 - umask

    def stop(self):
        # FIXME: maybe this kind of try-wrapping to make sure
        # we chain up should be handled by a parent class function ?
        try:
            if not self.exception:
                self.quality = max(self.tasks[0].quality,
                    self.tasks[2].quality)
                self.peak = self.tasks[4].peak
                self.debug('peak: %r', self.peak)
                self.testspeed = self.tasks[0].speed
                self.copyspeed = self.tasks[2].speed
                self.testduration = self.tasks[0].duration
                self.copyduration = self.tasks[2].duration

                self.testchecksum = c1 = self.tasks[1].checksum
                self.copychecksum = c2 = self.tasks[3].checksum
                if c1 == c2:
                    self.info('Checksums match, %08x' % c1)
                    self.checksum = self.testchecksum
                else:
                    # FIXME: detect this before encoding
                    self.info('Checksums do not match, %08x %08x' % (
                        c1, c2))
                    self.exception = ChecksumException(
                        'read and verify failed: test checksum')

                if self.tasks[5].checksum != self.checksum:
                    self.exception = ChecksumException(
                        'Encoding failed, checksum does not match')

                # delete the unencoded file
                os.unlink(self._tmpwavpath)

                os.chmod(self._tmppath, self.file_mode)

                if not self.exception:
                    try:
                        self.debug('Moving to final path %r', self.path)
                        shutil.move(self._tmppath, self.path)
                    except IOError, e:
                        if e.errno == errno.ENAMETOOLONG:
                            self.path = common.shrinkPath(self.path)
                            shutil.move(self._tmppath, self.path)
                    except Exception, e:
                        self.debug('Exception while moving to final path %r: '
                            '%r',
                            self.path, log.getExceptionMessage(e))
                        self.exception = e
                else:
                    os.unlink(self._tmppath)
            else:
                self.debug('stop: exception %r', self.exception)
        except Exception, e:
            print 'WARNING: unhandled exception %r' % (e, )

        task.MultiSeparateTask.stop(self)

_VERSION_RE = re.compile(
    "^cdparanoia (?P<version>.+) release (?P<release>.+) \(.*\)")


def getCdParanoiaVersion():
    getter = common.VersionGetter('cdparanoia',
        ["cdparanoia", "-V"],
        _VERSION_RE,
        "%(version)s %(release)s")

    return getter.get()


_OK_RE = re.compile(r'Drive tests OK with Paranoia.')
_WARNING_RE = re.compile(r'WARNING! PARANOIA MAY NOT BE')


class AnalyzeTask(ctask.PopenTask):

    logCategory = 'AnalyzeTask'
    description = 'Analyzing drive caching behaviour'

    defeatsCache = None

    cwd = None

    _output = []

    def __init__(self, device=None):
        # cdparanoia -A *always* writes cdparanoia.log
        self.cwd = tempfile.mkdtemp(suffix='.morituri.cache')
        self.command = ['cdparanoia', '-A']
        if device:
            self.command += ['-d', device]

    def commandMissing(self):
        raise common.MissingDependencyException('cdparanoia')

    def readbyteserr(self, bytes):
        self._output.append(bytes)

    def done(self):
        if self.cwd:
            shutil.rmtree(self.cwd)
        output = "".join(self._output)
        m = _OK_RE.search(output)
        if m:
            self.defeatsCache = True
        else:
            self.defeatsCache = False

    def failed(self):
        # cdparanoia exits with return code 1 if it can't determine
        # whether it can defeat the audio cache
        output = "".join(self._output)
        m = _WARNING_RE.search(output)
        if m:
            self.defeatsCache = False
        if self.cwd:
            shutil.rmtree(self.cwd)

########NEW FILE########
__FILENAME__ = cdrdao
# -*- Mode: Python; test-case-name:morituri.test.test_program_cdrdao -*-
# vi:si:et:sw=4:sts=4:ts=4

# Morituri - for those about to RIP

# Copyright (C) 2009 Thomas Vander Stichele

# This file is part of morituri.
#
# morituri is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# morituri is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with morituri.  If not, see <http://www.gnu.org/licenses/>.


import re
import os
import tempfile

from morituri.common import log, common
from morituri.image import toc, table
from morituri.common import task as ctask

from morituri.extern.task import task


class ProgramError(Exception):
    """
    The program had a fatal error.
    """

    def __init__(self, errorMessage):
        self.args = (errorMessage, )
        self.errorMessage = errorMessage

states = ['START', 'TRACK', 'LEADOUT', 'DONE']

_VERSION_RE = re.compile(r'^Cdrdao version (?P<version>.*) - \(C\)')

_ANALYZING_RE = re.compile(r'^Analyzing track (?P<track>\d+).*')

_TRACK_RE = re.compile(r"""
    ^(?P<track>[\d\s]{2})\s+ # Track
    (?P<mode>\w+)\s+         # Mode; AUDIO
    \d\s+                    # Flags
    \d\d:\d\d:\d\d           # Start in HH:MM:FF
    \((?P<start>.+)\)\s+     # Start in frames
    \d\d:\d\d:\d\d           # Length in HH:MM:FF
    \((?P<length>.+)\)       # Length in frames
""", re.VERBOSE)

_LEADOUT_RE = re.compile(r"""
    ^Leadout\s
    \w+\s+               # Mode
    \d\s+                # Flags
    \d\d:\d\d:\d\d       # Start in HH:MM:FF
    \((?P<start>.+)\)    # Start in frames
""", re.VERBOSE)

_POSITION_RE = re.compile(r"""
    ^(?P<hh>\d\d):       # HH
    (?P<mm>\d\d):        # MM
    (?P<ss>\d\d)         # SS
""", re.VERBOSE)

_ERROR_RE = re.compile(r"""^ERROR: (?P<error>.*)""")


class LineParser(object, log.Loggable):
    """
    Parse incoming bytes into lines
    Calls 'parse' on owner for each parsed line.
    """

    def __init__(self, owner):
        self._buffer = ""     # accumulate characters
        self._lines = []      # accumulate lines
        self._owner = owner

    def read(self, bytes):
        self.log('received %d bytes', len(bytes))
        self._buffer += bytes

        # parse buffer into lines if possible, and parse them
        if "\n" in self._buffer:
            self.log('buffer has newline, splitting')
            lines = self._buffer.split('\n')
            if lines[-1] != "\n":
                # last line didn't end yet
                self.log('last line still in progress')
                self._buffer = lines[-1]
                del lines[-1]
            else:
                self.log('last line finished, resetting buffer')
                self._buffer = ""

            for line in lines:
                self.log('Parsing %s', line)
                self._owner.parse(line)

            self._lines.extend(lines)


class OutputParser(object, log.Loggable):

    def __init__(self, taskk, session=None):
        self._buffer = ""     # accumulate characters
        self._lines = []      # accumulate lines
        self._state = 'START'
        self._frames = None   # number of frames
        self.track = 0        # which track are we analyzing?
        self._task = taskk
        self.tracks = 0      # count of tracks, relative to session
        self._session = session


        self.table = table.Table() # the index table for the TOC
        self.version = None # cdrdao version

    def read(self, bytes):
        self.log('received %d bytes in state %s', len(bytes), self._state)
        self._buffer += bytes

        # find counter in LEADOUT state; only when we read full toc
        self.log('state: %s, buffer bytes: %d', self._state, len(self._buffer))
        if self._buffer and self._state == 'LEADOUT':
            # split on lines that end in \r, which reset cursor to counter
            # start
            # this misses the first one, but that's ok:
            # length 03:40:71...\n00:01:00
            times = self._buffer.split('\r')
            # counter ends in \r, so the last one would be empty
            if not times[-1]:
                del times[-1]

            position = ""
            m = None
            while times and not m:
                position = times.pop()
                m = _POSITION_RE.search(position)

            # we need both a position reported and an Analyzing line
            # to have been parsed to report progress
            if m and self.track is not None:
                track = self.table.tracks[self.track - 1]
                frame = (track.getIndex(1).absolute or 0) \
                    + int(m.group('hh')) * 60 * common.FRAMES_PER_SECOND \
                    + int(m.group('mm')) * common.FRAMES_PER_SECOND \
                    + int(m.group('ss'))
                self.log('at frame %d of %d', frame, self._frames)
                self._task.setProgress(float(frame) / self._frames)

        # parse buffer into lines if possible, and parse them
        if "\n" in self._buffer:
            self.log('buffer has newline, splitting')
            lines = self._buffer.split('\n')
            if lines[-1] != "\n":
                # last line didn't end yet
                self.log('last line still in progress')
                self._buffer = lines[-1]
                del lines[-1]
            else:
                self.log('last line finished, resetting buffer')
                self._buffer = ""
            for line in lines:
                self.log('Parsing %s', line)
                m = _ERROR_RE.search(line)
                if m:
                    error = m.group('error')
                    self._task.errors.append(error)
                    self.debug('Found ERROR: output: %s', error)
                    self._task.exception = ProgramError(error)
                    self._task.abort()
                    return

            self._parse(lines)
            self._lines.extend(lines)

    def _parse(self, lines):
        for line in lines:
            #print 'parsing', len(line), line
            methodName = "_parse_" + self._state
            getattr(self, methodName)(line)

    def _parse_START(self, line):
        if line.startswith('Cdrdao version'):
            m = _VERSION_RE.search(line)
            self.version = m.group('version')

        if line.startswith('Track'):
            self.debug('Found possible track line')
            if line == "Track   Mode    Flags  Start                Length":
                self.debug('Found track line, moving to TRACK state')
                self._state = 'TRACK'
                return

        m = _ERROR_RE.search(line)
        if m:
            error = m.group('error')
            self._task.errors.append(error)

    def _parse_TRACK(self, line):
        if line.startswith('---'):
            return

        m = _TRACK_RE.search(line)
        if m:
            t = int(m.group('track'))
            self.tracks += 1
            track = table.Track(self.tracks, session=self._session)
            track.index(1, absolute=int(m.group('start')))
            self.table.tracks.append(track)
            self.debug('Found absolute track %d, session-relative %d', t,
                self.tracks)

        m = _LEADOUT_RE.search(line)
        if m:
            self.debug('Found leadout line, moving to LEADOUT state')
            self._state = 'LEADOUT'
            self._frames = int(m.group('start'))
            self.debug('Found absolute leadout at offset %r', self._frames)
            self.info('%d tracks found for this session', self.tracks)
            return

    def _parse_LEADOUT(self, line):
        m = _ANALYZING_RE.search(line)
        if m:
            self.debug('Found analyzing line')
            track = int(m.group('track'))
            self.description = 'Analyzing track %d...' % track
            self.track = track


# FIXME: handle errors


class CDRDAOTask(ctask.PopenTask):
    """
    I am a task base class that runs CDRDAO.
    """

    logCategory = 'CDRDAOTask'
    description = "Reading TOC..."
    options = None

    def __init__(self):
        self.errors = []
        self.debug('creating CDRDAOTask')

    def start(self, runner):
        self.debug('Starting cdrdao with options %r', self.options)
        self.command = ['cdrdao', ] + self.options

        ctask.PopenTask.start(self, runner)

    def commandMissing(self):
        raise common.MissingDependencyException('cdrdao')


    def failed(self):
        if self.errors:
            raise DeviceOpenException("\n".join(self.errors))
        else:
            raise ProgramFailedException(self._popen.returncode)


class DiscInfoTask(CDRDAOTask):
    """
    I am a task that reads information about a disc.

    @ivar sessions: the number of sessions
    @type sessions: int
    """

    logCategory = 'DiscInfoTask'
    description = "Scanning disc..."
    table = None
    sessions = None

    def __init__(self, device=None):
        """
        @param device:  the device to rip from
        @type  device:  str
        """
        self.debug('creating DiscInfoTask for device %r', device)
        CDRDAOTask.__init__(self)

        self.options = ['disk-info', ]
        if device:
            self.options.extend(['--device', device, ])

        self.parser = LineParser(self)

    def readbytesout(self, bytes):
        self.parser.read(bytes)

    def readbyteserr(self, bytes):
        self.parser.read(bytes)

    def parse(self, line):
        # called by parser
        if line.startswith('Sessions'):
            self.sessions = int(line[line.find(':') + 1:])
            self.debug('Found %d sessions', self.sessions)
        m = _ERROR_RE.search(line)
        if m:
            error = m.group('error')
            self.errors.append(error)

    def done(self):
        pass


# Read stuff for one session


class ReadSessionTask(CDRDAOTask):
    """
    I am a task that reads things for one session.

    @ivar table: the index table
    @type table: L{table.Table}
    """

    logCategory = 'ReadSessionTask'
    description = "Reading session"
    table = None
    extraOptions = None

    def __init__(self, session=None, device=None):
        """
        @param session: the session to read
        @type  session: int
        @param device:  the device to rip from
        @type  device:  str
        """
        self.debug('Creating ReadSessionTask for session %d on device %r',
            session, device)
        CDRDAOTask.__init__(self)
        self.parser = OutputParser(self)
        (fd, self._tocfilepath) = tempfile.mkstemp(
            suffix=u'.readtablesession.morituri')
        os.close(fd)
        os.unlink(self._tocfilepath)

        self.options = ['read-toc', ]
        if device:
            self.options.extend(['--device', device, ])
        if session:
            self.options.extend(['--session', str(session)])
            self.description = "%s of session %d..." % (
                self.description, session)
        if self.extraOptions:
            self.options.extend(self.extraOptions)

        self.options.extend([self._tocfilepath, ])

    def readbyteserr(self, bytes):
        self.parser.read(bytes)

        if self.parser.tracks > 0:
            self.setProgress(float(self.parser.track - 1) / self.parser.tracks)

    def done(self):
        # by merging the TOC info.
        self._tocfile = toc.TocFile(self._tocfilepath)
        self._tocfile.parse()
        os.unlink(self._tocfilepath)
        self.table = self._tocfile.table

        # we know the .toc file represents a single wav rip, so all offsets
        # are absolute since beginning of disc
        self.table.absolutize()
        # we unset relative since there is no real file backing this toc
        for t in self.table.tracks:
            for i in t.indexes.values():
                #i.absolute = i.relative
                i.relative = None

        # copy the leadout from the parser's table
        # FIXME: how do we get the length of the last audio track in the case
        # of a data track ?
        # self.table.leadout = self.parser.table.leadout

        # we should have parsed it from the initial output
        assert self.table.leadout is not None


class ReadTableSessionTask(ReadSessionTask):
    """
    I am a task that reads all indexes of a CD for a session.

    @ivar table: the index table
    @type table: L{table.Table}
    """

    logCategory = 'ReadTableSessionTask'
    description = "Scanning indexes"


class ReadTOCSessionTask(ReadSessionTask):
    """
    I am a task that reads the TOC of a CD, without pregaps.

    @ivar table: the index table that matches the TOC.
    @type table: L{table.Table}
    """

    logCategory = 'ReadTOCSessTask'
    description = "Reading TOC"
    extraOptions = ['--fast-toc', ]

    def done(self):
        ReadSessionTask.done(self)

        assert self.table.hasTOC(), "This Table Index should be a TOC"

# read all sessions


class ReadAllSessionsTask(task.MultiSeparateTask):
    """
    I am a base class for tasks that need to read all sessions.

    @ivar table: the index table
    @type table: L{table.Table}
    """

    logCategory = 'ReadAllSessionsTask'
    table = None
    _readClass = None

    def __init__(self, device=None):
        """
        @param device:  the device to rip from
        @type  device:  str
        """
        task.MultiSeparateTask.__init__(self)

        self._device = device

        self.debug('Starting ReadAllSessionsTask')
        self.tasks = [DiscInfoTask(device=device), ]

    def stopped(self, taskk):
        if not taskk.exception:
            # After first task, schedule additional ones
            if taskk == self.tasks[0]:
                for i in range(taskk.sessions):
                    self.tasks.append(self._readClass(session=i + 1,
                        device=self._device))

            if self._task == len(self.tasks):
                self.table = self.tasks[1].table
                if len(self.tasks) > 2:
                    for i, t in enumerate(self.tasks[2:]):
                        self.table.merge(t.table, i + 2)

                assert self.table.leadout is not None

        task.MultiSeparateTask.stopped(self, taskk)


class ReadTableTask(ReadAllSessionsTask):
    """
    I am a task that reads all indexes of a CD for all sessions.

    @ivar table: the index table
    @type table: L{table.Table}
    """

    logCategory = 'ReadTableTask'
    description = "Scanning indexes..."
    _readClass = ReadTableSessionTask


class ReadTOCTask(ReadAllSessionsTask):
    """
    I am a task that reads the TOC of a CD, without pregaps.

    @ivar table: the index table that matches the TOC.
    @type table: L{table.Table}
    """

    logCategory = 'ReadTOCTask'
    description = "Reading TOC..."
    _readClass = ReadTOCSessionTask


class DeviceOpenException(Exception):

    def __init__(self, msg):
        self.msg = msg
        self.args = (msg, )


class ProgramFailedException(Exception):

    def __init__(self, code):
        self.code = code
        self.args = (code, )


_VERSION_RE = re.compile(
    "^Cdrdao version (?P<version>.+) -")


def getCDRDAOVersion():
    getter = common.VersionGetter('cdrdao',
        ["cdrdao"],
        _VERSION_RE,
        "%(version)s")

    return getter.get()

########NEW FILE########
__FILENAME__ = logger
# -*- Mode: Python; test-case-name: morituri.test.test_result_logger -*-
# vi:si:et:sw=4:sts=4:ts=4

# Morituri - for those about to RIP

# Copyright (C) 2009 Thomas Vander Stichele

# This file is part of morituri.
#
# morituri is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# morituri is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with morituri.  If not, see <http://www.gnu.org/licenses/>.

import time

from morituri.common import common
from morituri.configure import configure
from morituri.result import result


class MorituriLogger(result.Logger):

    def log(self, ripResult, epoch=time.time()):
        """
        @type  ripResult: L{morituri.result.result.RipResult}
        """
        lines = self.logRip(ripResult, epoch=epoch)
        return '\n'.join(lines)

    def logRip(self, ripResult, epoch):

        lines = []

        ### global

        lines.append("Logfile created by: morituri %s" % configure.version)
        # FIXME: when we localize this, see #49 to handle unicode properly.
        import locale
        old = locale.getlocale(locale.LC_TIME)
        locale.setlocale(locale.LC_TIME, 'C')
        date = time.strftime("%b %d %H:%M:%S", time.localtime(epoch))
        locale.setlocale(locale.LC_TIME, old)
        lines.append("Logfile created on: %s" % date)
        lines.append("")

        # album
        lines.append("Album: %s - %s" % (ripResult.artist, ripResult.title))
        lines.append("")

        lines.append("CDDB disc id:           %s" % ripResult. table.getCDDBDiscId())
        lines.append("MusicBrainz disc id:    %s" % ripResult. table.getMusicBrainzDiscId())
        lines.append("MusicBrainz lookup URL: %s" % ripResult. table.getMusicBrainzSubmitURL())
        lines.append("")

        # drive
        lines.append(
            "Drive: vendor %s, model %s" % (
                ripResult.vendor, ripResult.model))
        lines.append("")

        lines.append("Read offset correction: %d" %
            ripResult.offset)
        lines.append("")

        # toc
        lines.append("Table of Contents:")
        lines.append("")
        lines.append(
            "     Track |   Start           |  Length")
        lines.append(
            "     ------------------------------------------------")
        table = ripResult.table


        for t in table.tracks:
            start = t.getIndex(1).absolute
            length = table.getTrackLength(t.number)
            lines.append(
            "       %2d  | %6d - %s | %6d - %s" % (
                t.number,
                start, common.framesToMSF(start),
                length, common.framesToMSF(length)))

        lines.append("")
        lines.append("")

        ### per-track
        for t in ripResult.tracks:
            lines.extend(self.trackLog(t))
            lines.append('')

        return lines

    def trackLog(self, trackResult):

        lines = []

        lines.append('Track %2d' % trackResult.number)
        lines.append('')
        lines.append('  Filename %s' % trackResult.filename)
        lines.append('')
        if trackResult.pregap:
            lines.append('  Pre-gap: %s' % common.framesToMSF(
                trackResult.pregap))
            lines.append('')

        lines.append('  Peak level %.1f %%' % (trackResult.peak * 100.0))
        if trackResult.copyspeed:
            lines.append('  Extraction Speed (Copy) %.4f X' % (
                trackResult.copyspeed))
        if trackResult.testspeed:
            lines.append('  Extraction Speed (Test) %.4f X' % (
                trackResult.testspeed))

        if trackResult.copycrc is not None:
            lines.append('  Copy CRC %08X' % trackResult.copycrc)
        if trackResult.testcrc is not None:
            lines.append('  Test CRC %08X' % trackResult.testcrc)
            if trackResult.testcrc == trackResult.copycrc:
                lines.append('  Copy OK')
            else:
                lines.append("  WARNING: CRCs don't match!")
        else:
            lines.append("  WARNING: no CRC check done")


        if trackResult.accurip:
            lines.append('  Accurately ripped (confidence %d) [%08X]' % (
                trackResult.ARDBConfidence, trackResult.ARCRC))
        else:
            if trackResult.ARDBCRC:
                lines.append('  Cannot be verified as accurate '
                    '[%08X], AccurateRip returned [%08X]' % (
                        trackResult.ARCRC, trackResult.ARDBCRC))
            else:
                lines.append('  Track not present in AccurateRip database')

        return lines

########NEW FILE########
__FILENAME__ = result
# -*- Mode: Python; test-case-name: morituri.test.test_result_result -*-
# vi:si:et:sw=4:sts=4:ts=4

# Morituri - for those about to RIP

# Copyright (C) 2009 Thomas Vander Stichele

# This file is part of morituri.
#
# morituri is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# morituri is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with morituri.  If not, see <http://www.gnu.org/licenses/>.

import pkg_resources
import time


class TrackResult:
    """
    @type filename:          unicode
    @ivar testcrc:           4-byte CRC for the test read
    @type testcrc:           int
    @ivar copycrc:           4-byte CRC for the copy read
    @type copycrc:           int

    @var  accurip:           whether this track's AR CRC was found in the
                             database, and thus whether the track is considered
                             accurately ripped.
                             If false, it can be ripped wrong, not exist in
                             the database, ...
    @type accurip:           bool

    @var  ARCRC:             our calculated 4 byte AccurateRip CRC for this
                             track.
    @type ARCRC:             int

    @var  ARDBCRC:           the 4-byte AccurateRip CRC this
                             track did or should have matched in the database.
                             If None, the track is not in the database.
    @type ARDBCRC:           int
    @var  ARDBConfidence:    confidence for the matched AccurateRip CRC for
                             this track in the database.
                             If None, the track is not in the database.
    @var  ARDBMaxConfidence: maximum confidence in the AccurateRip database for
                             this track; can still be 0.
                             If None, the track is not in the database.
    """
    number = None
    filename = None
    pregap = 0 # in frames

    peak = 0.0
    quality = 0.0
    testspeed = 0.0
    copyspeed = 0.0
    testduration = 0.0
    copyduration = 0.0
    testcrc = None
    copycrc = None
    accurip = False # whether it's in the database
    ARCRC = None
    ARDBCRC = None
    ARDBConfidence = None
    ARDBMaxConfidence = None

    classVersion = 3


class RipResult:
    """
    I hold information about the result for rips.
    I can be used to write log files.

    @ivar offset: sample read offset
    @ivar table:  the full index table
    @type table:  L{morituri.image.table.Table}

    @ivar vendor:  vendor of the CD drive
    @ivar model:   model of the CD drive
    @ivar release: release of the CD drive

    @ivar cdrdaoVersion:     version of cdrdao used for the rip
    @ivar cdparanoiaVersion: version of cdparanoia used for the rip
    """

    offset = 0
    table = None
    artist = None
    title = None

    vendor = None
    model = None
    release = None

    cdrdaoVersion = None
    cdparanoiaVersion = None
    cdparanoiaDefeatsCache = None

    gstreamerVersion = None
    gstPythonVersion = None
    encoderVersion = None

    profileName = None
    profilePipeline = None

    classVersion = 3

    def __init__(self):
        self.tracks = []

    def getTrackResult(self, number):
        """
        @param number: the track number (0 for HTOA)

        @type  number: int
        @rtype: L{TrackResult}
        """
        for t in self.tracks:
            if t.number == number:
                return t

        return None


class Logger(object):
    """
    I log the result of a rip.
    """

    def log(self, ripResult, epoch=time.time()):
        """
        Create a log from the given ripresult.

        @param epoch:     when the log file gets generated
        @type  epoch:     float
        @type  ripResult: L{RipResult}

        @rtype: str
        """
        raise NotImplementedError


# A setuptools-like entry point


class EntryPoint(object):
    name = 'morituri'

    def load(self):
        from morituri.result import logger
        return logger.MorituriLogger


def getLoggers():
    """
    Get all logger plugins with entry point 'morituri.logger'.

    @rtype: dict of C{str} -> C{Logger}
    """
    d = {}

    pluggables = list(pkg_resources.iter_entry_points("morituri.logger"))
    for entrypoint in [EntryPoint(), ] + pluggables:
        plugin_class = entrypoint.load()
        d[entrypoint.name] = plugin_class

    return d

########NEW FILE########
__FILENAME__ = accurip
# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# Morituri - for those about to RIP

# Copyright (C) 2009 Thomas Vander Stichele

# This file is part of morituri.
#
# morituri is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# morituri is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with morituri.  If not, see <http://www.gnu.org/licenses/>.

from morituri.common import logcommand, accurip


class Show(logcommand.LogCommand):

    summary = "show accuraterip data"

    def do(self, args):

        try:
            url = args[0]
        except IndexError:
            self.stdout.write('Please specify an accuraterip URL.\n')
            return 3

        cache = accurip.AccuCache()
        responses = cache.retrieve(url)

        count = responses[0].trackCount

        self.stdout.write("Found %d responses for %d tracks\n\n" % (
            len(responses), count))

        for (i, r) in enumerate(responses):
            if r.trackCount != count:
                self.stdout.write(
                    "Warning: response %d has %d tracks instead of %d\n" % (
                        i, r.trackCount, count))


        # checksum and confidence by track
        for track in range(count):
            self.stdout.write("Track %d:\n" % (track + 1))
            checksums = {}

            for (i, r) in enumerate(responses):
                if r.trackCount != count:
                    continue

                assert len(r.checksums) == r.trackCount
                assert len(r.confidences) == r.trackCount

                entry = {}
                entry["confidence"] = r.confidences[track]
                entry["response"] = i + 1
                checksum = r.checksums[track]
                if checksum in checksums:
                    checksums[checksum].append(entry)
                else:
                    checksums[checksum] = [entry, ]

            # now sort track results in checksum by highest confidence
            sortedChecksums = []
            for checksum, entries in checksums.items():
                highest = max(d['confidence'] for d in entries)
                sortedChecksums.append((highest, checksum))

            sortedChecksums.sort()
            sortedChecksums.reverse()

            for highest, checksum in sortedChecksums:
                self.stdout.write("  %d result(s) for checksum %s: %s\n" % (
                    len(checksums[checksum]), checksum,
                    str(checksums[checksum])))


class AccuRip(logcommand.LogCommand):
    description = "Handle AccurateRip information."

    subCommandClasses = [Show, ]

########NEW FILE########
__FILENAME__ = cd
# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# Morituri - for those about to RIP

# Copyright (C) 2009 Thomas Vander Stichele

# This file is part of morituri.
#
# morituri is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# morituri is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with morituri.  If not, see <http://www.gnu.org/licenses/>.

import os
import math
import glob
import urllib2
import socket

import gobject
gobject.threads_init()

from morituri.common import logcommand, common, accurip, gstreamer
from morituri.common import drive, program, task
from morituri.result import result
from morituri.program import cdrdao, cdparanoia
from morituri.rip import common as rcommon

from morituri.extern.command import command


MAX_TRIES = 5


class _CD(logcommand.LogCommand):

    """
    @type program: L{program.Program}
    @ivar eject:   whether to eject the drive after completing
    """

    eject = True

    def addOptions(self):
        # FIXME: have a cache of these pickles somewhere
        self.parser.add_option('-T', '--toc-pickle',
            action="store", dest="toc_pickle",
            help="pickle to use for reading and writing the TOC")
        self.parser.add_option('-R', '--release-id',
            action="store", dest="release_id",
            help="MusicBrainz release id to match to (if there are multiple)")


    def do(self, args):
        self.program = program.Program(self.getRootCommand().config,
            record=self.getRootCommand().record,
            stdout=self.stdout)
        self.runner = task.SyncRunner()

        # if the device is mounted (data session), unmount it
        self.device = self.parentCommand.options.device
        self.stdout.write('Checking device %s\n' % self.device)

        self.program.loadDevice(self.device)
        self.program.unmountDevice(self.device)

        # first, read the normal TOC, which is fast
        self.ittoc = self.program.getFastToc(self.runner,
            self.options.toc_pickle,
            self.device)

        # already show us some info based on this
        self.program.getRipResult(self.ittoc.getCDDBDiscId())
        self.stdout.write("CDDB disc id: %s\n" % self.ittoc.getCDDBDiscId())
        self.mbdiscid = self.ittoc.getMusicBrainzDiscId()
        self.stdout.write("MusicBrainz disc id %s\n" % self.mbdiscid)

        self.stdout.write("MusicBrainz lookup URL %s\n" %
            self.ittoc.getMusicBrainzSubmitURL())

        self.program.metadata = self.program.getMusicBrainz(self.ittoc,
            self.mbdiscid,
            release=self.options.release_id)

        if not self.program.metadata:
            # fall back to FreeDB for lookup
            cddbid = self.ittoc.getCDDBValues()
            cddbmd = self.program.getCDDB(cddbid)
            if cddbmd:
                self.stdout.write('FreeDB identifies disc as %s\n' % cddbmd)

            # also used by rip cd info
            if not getattr(self.options, 'unknown', False):
                if self.eject:
                    self.program.ejectDevice(self.device)
                return -1

        # now, read the complete index table, which is slower

        self.itable = self.program.getTable(self.runner,
            self.ittoc.getCDDBDiscId(),
            self.ittoc.getMusicBrainzDiscId(), self.device)

        assert self.itable.getCDDBDiscId() == self.ittoc.getCDDBDiscId(), \
            "full table's id %s differs from toc id %s" % (
                self.itable.getCDDBDiscId(), self.ittoc.getCDDBDiscId())
        assert self.itable.getMusicBrainzDiscId() == \
            self.ittoc.getMusicBrainzDiscId(), \
            "full table's mb id %s differs from toc id mb %s" % (
            self.itable.getMusicBrainzDiscId(),
            self.ittoc.getMusicBrainzDiscId())
        assert self.itable.getAccurateRipURL() == \
            self.ittoc.getAccurateRipURL(), \
            "full table's AR URL %s differs from toc AR URL %s" % (
            self.itable.getAccurateRipURL(), self.ittoc.getAccurateRipURL())

        # result

        self.program.result.cdrdaoVersion = cdrdao.getCDRDAOVersion()
        self.program.result.cdparanoiaVersion = \
            cdparanoia.getCdParanoiaVersion()
        info = drive.getDeviceInfo(self.parentCommand.options.device)
        if info:
            try:
                self.program.result.cdparanoiaDefeatsCache = \
                    self.getRootCommand().config.getDefeatsCache(*info)
            except KeyError, e:
                self.debug('Got key error: %r' % (e, ))
        self.program.result.artist = self.program.metadata \
            and self.program.metadata.artist \
            or 'Unknown Artist'
        self.program.result.title = self.program.metadata \
            and self.program.metadata.title \
            or 'Unknown Title'
        # cdio is optional for now
        try:
            import cdio
            _, self.program.result.vendor, self.program.result.model, \
                self.program.result.release = \
                cdio.Device(self.device).get_hwinfo()
        except ImportError:
            self.stdout.write(
                'WARNING: pycdio not installed, cannot identify drive\n')
            self.program.result.vendor = 'Unknown'
            self.program.result.model = 'Unknown'
            self.program.result.release = 'Unknown'

        self.doCommand()

        if self.eject:
            self.program.ejectDevice(self.device)

    def doCommand(self):
        pass


class Info(_CD):
    summary = "retrieve information about the currently inserted CD"

    eject = False


class Rip(_CD):
    summary = "rip CD"

    # see morituri.common.program.Program.getPath for expansion
    description = """
Rips a CD.

%s

Paths to track files referenced in .cue and .m3u files will be made
relative to the directory of the disc files.

All files will be created relative to the given output directory.
Log files will log the path to tracks relative to this directory.
""" % rcommon.TEMPLATE_DESCRIPTION

    def addOptions(self):
        _CD.addOptions(self)

        loggers = result.getLoggers().keys()

        self.parser.add_option('-L', '--logger',
            action="store", dest="logger",
            default='morituri',
            help="logger to use "
                "(default '%default', choose from '" +
                    "', '".join(loggers) + "')")
        # FIXME: get from config
        self.parser.add_option('-o', '--offset',
            action="store", dest="offset",
            help="sample read offset (defaults to configured value, or 0)")
        self.parser.add_option('-O', '--output-directory',
            action="store", dest="output_directory",
            help="output directory; will be included in file paths in result "
                "files "
                "(defaults to absolute path to current directory; set to "
                "empty if you want paths to be relative instead) ")
        self.parser.add_option('-W', '--working-directory',
            action="store", dest="working_directory",
            help="working directory; morituri will change to this directory "
                "and files will be created relative to it when not absolute ")

        rcommon.addTemplate(self)

        default = 'flac'

        # here to avoid import gst eating our options
        from morituri.common import encode

        self.parser.add_option('', '--profile',
            action="store", dest="profile",
            help="profile for encoding (default '%s', choices '%s')" % (
                default, "', '".join(encode.PROFILES.keys())),
            default=default)
        self.parser.add_option('-U', '--unknown',
            action="store_true", dest="unknown",
            help="whether to continue ripping if the CD is unknown (%default)",
            default=False)

    def handleOptions(self, options):
        options.track_template = options.track_template.decode('utf-8')
        options.disc_template = options.disc_template.decode('utf-8')

        if options.offset is None:
            info = drive.getDeviceInfo(self.parentCommand.options.device)
            if info:
                try:
                    options.offset = self.getRootCommand(
                        ).config.getReadOffset(*info)
                    self.stdout.write("Using configured read offset %d\n" %
                        options.offset)
                except KeyError:
                    pass

        if options.offset is None:
            options.offset = 0
            self.stdout.write("""WARNING: using default offset %d.
Install pycdio and run 'rip offset find' to detect your drive's offset.
""" %
                        options.offset)
        if self.options.output_directory is None:
            self.options.output_directory = os.getcwd()

        if self.options.logger:
            try:
                klazz = result.getLoggers()[self.options.logger]
            except KeyError:
                self.stderr.write("No logger named %s found!\n" % (
                    self.options.logger))
                raise command.CommandError("No logger named %s" %
                    self.options.logger)

            self.logger = klazz()

    def doCommand(self):
        # here to avoid import gst eating our options
        from morituri.common import encode
        profile = encode.PROFILES[self.options.profile]()
        self.program.result.profileName = profile.name
        self.program.result.profilePipeline = profile.pipeline
        elementFactory = profile.pipeline.split(' ')[0]
        self.program.result.gstreamerVersion = gstreamer.gstreamerVersion()
        self.program.result.gstPythonVersion = gstreamer.gstPythonVersion()
        self.program.result.encoderVersion = gstreamer.elementFactoryVersion(
            elementFactory)

        self.program.setWorkingDirectory(self.options.working_directory)
        self.program.outdir = self.options.output_directory.decode('utf-8')
        self.program.result.offset = int(self.options.offset)

        ### write disc files
        disambiguate = False
        while True:
            discName = self.program.getPath(self.program.outdir,
                self.options.disc_template, self.mbdiscid, 0,
                profile=profile, disambiguate=disambiguate)
            dirname = os.path.dirname(discName)
            if os.path.exists(dirname):
                self.stdout.write("Output directory %s already exists\n" %
                    dirname.encode('utf-8'))
                logs = glob.glob(os.path.join(dirname, '*.log'))
                if logs:
                    self.stdout.write(
                        "Output directory %s is a finished rip\n" %
                        dirname.encode('utf-8'))
                    if not disambiguate:
                        disambiguate = True
                        continue
                    return
                else:
                    break

            else:
                self.stdout.write("Creating output directory %s\n" %
                    dirname.encode('utf-8'))
                os.makedirs(dirname)
                break

        # FIXME: say when we're continuing a rip
        # FIXME: disambiguate if the pre-existing rip is different


        # FIXME: turn this into a method

        def ripIfNotRipped(number):
            self.debug('ripIfNotRipped for track %d' % number)
            # we can have a previous result
            trackResult = self.program.result.getTrackResult(number)
            if not trackResult:
                trackResult = result.TrackResult()
                self.program.result.tracks.append(trackResult)
            else:
                self.debug('ripIfNotRipped have trackresult, path %r' %
                    trackResult.filename)

            path = self.program.getPath(self.program.outdir,
                self.options.track_template,
                self.mbdiscid, number,
                profile=profile, disambiguate=disambiguate) \
                + '.' + profile.extension
            self.debug('ripIfNotRipped: path %r' % path)
            trackResult.number = number

            assert type(path) is unicode, "%r is not unicode" % path
            trackResult.filename = path
            if number > 0:
                trackResult.pregap = self.itable.tracks[number - 1].getPregap()

            # FIXME: optionally allow overriding reripping
            if os.path.exists(path):
                if path != trackResult.filename:
                    # the path is different (different name/template ?)
                    # but we can copy it
                    self.debug('previous result %r, expected %r' % (
                        trackResult.filename, path))

                self.stdout.write('Verifying track %d of %d: %s\n' % (
                    number, len(self.itable.tracks),
                    os.path.basename(path).encode('utf-8')))
                if not self.program.verifyTrack(self.runner, trackResult):
                    self.stdout.write('Verification failed, reripping...\n')
                    os.unlink(path)

            if not os.path.exists(path):
                self.debug('path %r does not exist, ripping...' % path)
                tries = 0
                # we reset durations for test and copy here
                trackResult.testduration = 0.0
                trackResult.copyduration = 0.0
                extra = ""
                while tries < MAX_TRIES:
                    tries += 1
                    if tries > 1:
                        extra = " (try %d)" % tries
                    self.stdout.write('Ripping track %d of %d%s: %s\n' % (
                        number, len(self.itable.tracks), extra,
                        os.path.basename(path).encode('utf-8')))
                    try:
                        self.debug('ripIfNotRipped: track %d, try %d',
                            number, tries)
                        self.program.ripTrack(self.runner, trackResult,
                            offset=int(self.options.offset),
                            device=self.parentCommand.options.device,
                            profile=profile,
                            taglist=self.program.getTagList(number),
                            what='track %d of %d%s' % (
                                number, len(self.itable.tracks), extra))
                        break
                    except Exception, e:
                        self.debug('Got exception %r on try %d',
                            e, tries)


                if tries == MAX_TRIES:
                    self.error('Giving up on track %d after %d times' % (
                        number, tries))
                if trackResult.testcrc == trackResult.copycrc:
                    self.stdout.write('Checksums match for track %d\n' %
                        number)
                else:
                    self.stdout.write(
                        'ERROR: checksums did not match for track %d\n' %
                        number)
                    raise

                self.stdout.write('Peak level: %.2f %%\n' % (
                    math.sqrt(trackResult.peak) * 100.0, ))
                self.stdout.write('Rip quality: %.2f %%\n' % (
                    trackResult.quality * 100.0, ))

            # overlay this rip onto the Table
            if number == 0:
                # HTOA goes on index 0 of track 1
                self.itable.setFile(1, 0, trackResult.filename,
                    self.ittoc.getTrackStart(1), number)
            else:
                self.itable.setFile(number, 1, trackResult.filename,
                    self.ittoc.getTrackLength(number), number)

            self.program.saveRipResult()


        # check for hidden track one audio
        htoapath = None
        htoa = self.program.getHTOA()
        if htoa:
            start, stop = htoa
            self.stdout.write(
                'Found Hidden Track One Audio from frame %d to %d\n' % (
                start, stop))

            # rip it
            ripIfNotRipped(0)
            htoapath = self.program.result.tracks[0].filename

        for i, track in enumerate(self.itable.tracks):
            # FIXME: rip data tracks differently
            if not track.audio:
                self.stdout.write(
                    'WARNING: skipping data track %d, not implemented\n' % (
                    i + 1, ))
                # FIXME: make it work for now
                track.indexes[1].relative = 0
                continue

            ripIfNotRipped(i + 1)

        ### write disc files
        discName = self.program.getPath(self.program.outdir,
            self.options.disc_template, self.mbdiscid, 0,
            profile=profile, disambiguate=disambiguate)
        dirname = os.path.dirname(discName)
        if not os.path.exists(dirname):
            os.makedirs(dirname)

        self.debug('writing cue file for %r', discName)
        self.program.writeCue(discName)

        # write .m3u file
        self.debug('writing m3u file for %r', discName)
        m3uPath = u'%s.m3u' % discName
        handle = open(m3uPath, 'w')
        handle.write(u'#EXTM3U\n')

        def writeFile(handle, path, length):
            targetPath = common.getRelativePath(path, m3uPath)
            u = u'#EXTINF:%d,%s\n' % (length, targetPath)
            handle.write(u.encode('utf-8'))
            u = '%s\n' % targetPath
            handle.write(u.encode('utf-8'))


        if htoapath:
            writeFile(handle, htoapath,
                self.itable.getTrackStart(1) / common.FRAMES_PER_SECOND)

        for i, track in enumerate(self.itable.tracks):
            if not track.audio:
                continue

            path = self.program.getPath(self.program.outdir,
                self.options.track_template, self.mbdiscid, i + 1,
                profile=profile,
                disambiguate=disambiguate) + '.' + profile.extension
            writeFile(handle, path,
                self.itable.getTrackLength(i + 1) / common.FRAMES_PER_SECOND)

        handle.close()

        # verify using accuraterip
        url = self.ittoc.getAccurateRipURL()
        self.stdout.write("AccurateRip URL %s\n" % url)

        accucache = accurip.AccuCache()
        try:
            responses = accucache.retrieve(url)
        except urllib2.URLError, e:
            if isinstance(e.args[0], socket.gaierror):
                if e.args[0].errno == -2:
                    self.stdout.write("Warning: network error: %r\n" % (
                        e.args[0], ))
                    responses = None
                else:
                    raise
            else:
                raise

        if not responses:
            self.stdout.write('Album not found in AccurateRip database\n')

        if responses:
            self.stdout.write('%d AccurateRip reponses found\n' %
                len(responses))

            if responses[0].cddbDiscId != self.itable.getCDDBDiscId():
                self.stdout.write(
                    "AccurateRip response discid different: %s\n" %
                    responses[0].cddbDiscId)


        self.program.verifyImage(self.runner, responses)

        self.stdout.write("\n".join(
            self.program.getAccurateRipResults()) + "\n")

        self.program.saveRipResult()

        # write log file
        self.program.writeLog(discName, self.logger)

        self.program.ejectDevice(self.device)


class CD(logcommand.LogCommand):

    summary = "handle CD's"

    subCommandClasses = [Info, Rip, ]

    def addOptions(self):
        self.parser.add_option('-d', '--device',
            action="store", dest="device",
            help="CD-DA device")

    def handleOptions(self, options):
        if not options.device:
            drives = drive.getAllDevicePaths()
            if not drives:
                self.error('No CD-DA drives found!')
                return 3

            # pick the first
            self.options.device = drives[0]

        # this can be a symlink to another device
        self.options.device = os.path.realpath(self.options.device)

########NEW FILE########
__FILENAME__ = common
# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# options and arguments shared between commands

DEFAULT_TRACK_TEMPLATE = u'%r/%A - %d/%t. %a - %n'
DEFAULT_DISC_TEMPLATE = u'%r/%A - %d/%A - %d'

TEMPLATE_DESCRIPTION = '''
Tracks are named according to the track template, filling in the variables
and adding the file extension.  Variables exclusive to the track template are:
 - %t: track number
 - %a: track artist
 - %n: track title
 - %s: track sort name

Disc files (.cue, .log, .m3u) are named according to the disc template,
filling in the variables and adding the file extension. Variables for both
disc and track template are:
 - %A: album artist
 - %S: album sort name
 - %d: disc title
 - %y: release year
 - %r: release type, lowercase
 - %R: Release type, normal case
 - %x: audio extension, lowercase
 - %X: audio extension, uppercase

'''

def addTemplate(obj):
    # FIXME: get from config
    obj.parser.add_option('', '--track-template',
        action="store", dest="track_template",
        help="template for track file naming (default %default)",
        default=DEFAULT_TRACK_TEMPLATE)
    obj.parser.add_option('', '--disc-template',
        action="store", dest="disc_template",
        help="template for disc file naming (default %default)",
        default=DEFAULT_DISC_TEMPLATE)

########NEW FILE########
__FILENAME__ = debug
# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# Morituri - for those about to RIP

# Copyright (C) 2009 Thomas Vander Stichele

# This file is part of morituri.
#
# morituri is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# morituri is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with morituri.  If not, see <http://www.gnu.org/licenses/>.

from morituri.common import logcommand
from morituri.result import result

from morituri.common import task, cache

class RCCue(logcommand.LogCommand):

    name = "cue"
    summary = "write a cue file for the cached result"

    def do(self, args):
        self._cache = cache.ResultCache()

        persisted = self._cache.getRipResult(args[0], create=False)

        if not persisted:
            self.stderr.write(
                'Could not find a result for cddb disc id %s\n' % args[0])
            return 3

        self.stdout.write(persisted.object.table.cue().encode('utf-8'))


class RCList(logcommand.LogCommand):

    name = "list"
    summary = "list cached results"

    def do(self, args):
        self._cache = cache.ResultCache()
        results = []

        for i in self._cache.getIds():
            r = self._cache.getRipResult(i, create=False)
            results.append((r.object.artist, r.object.title, i))

        results.sort()

        for artist, title, cddbid in results:
            if artist is None:
                artist = '(None)'
            if title is None:
                title = '(None)'

            self.stdout.write('%s: %s - %s\n' % (
                cddbid, artist.encode('utf-8'), title.encode('utf-8')))


class RCLog(logcommand.LogCommand):

    name = "log"
    summary = "write a log file for the cached result"

    def addOptions(self):
        loggers = result.getLoggers().keys()

        self.parser.add_option('-L', '--logger',
            action="store", dest="logger",
            default='morituri',
            help="logger to use "
                "(default '%default', choose from '" +
                    "', '".join(loggers) + "')")

    def do(self, args):
        self._cache = cache.ResultCache()

        persisted = self._cache.getRipResult(args[0], create=False)

        if not persisted:
            self.stderr.write(
                'Could not find a result for cddb disc id %s\n' % args[0])
            return 3

        try:
            klazz = result.getLoggers()[self.options.logger]
        except KeyError:
            self.stderr.write("No logger named %s found!\n" % (
                self.options.logger))
            return 3

        logger = klazz()
        self.stdout.write(logger.log(persisted.object).encode('utf-8'))


class ResultCache(logcommand.LogCommand):

    summary = "debug result cache"
    aliases = ['rc', ]

    subCommandClasses = [RCCue, RCList, RCLog, ]


class Checksum(logcommand.LogCommand):

    summary = "run a checksum task"

    def do(self, args):
        if not args:
            self.stdout.write('Please specify one or more input files.\n')
            return 3

        runner = task.SyncRunner()
        # here to avoid import gst eating our options
        from morituri.common import checksum

        for arg in args:
            fromPath = unicode(arg)

            checksumtask = checksum.CRC32Task(fromPath)

            runner.run(checksumtask)

            self.stdout.write('Checksum: %08x\n' % checksumtask.checksum)


class Encode(logcommand.LogCommand):

    summary = "run an encode task"

    def addOptions(self):
        # here to avoid import gst eating our options
        from morituri.common import encode

        default = 'flac'
        self.parser.add_option('', '--profile',
            action="store", dest="profile",
            help="profile for encoding (default '%s', choices '%s')" % (
                default, "', '".join(encode.ALL_PROFILES.keys())),
            default=default)

    def do(self, args):
        from morituri.common import encode
        profile = encode.ALL_PROFILES[self.options.profile]()

        try:
            fromPath = unicode(args[0])
        except IndexError:
            self.stdout.write('Please specify an input file.\n')
            return 3

        try:
            toPath = unicode(args[1])
        except IndexError:
            toPath = fromPath + '.' + profile.extension

        runner = task.SyncRunner()

        self.debug('Encoding %s to %s',
            fromPath.encode('utf-8'),
            toPath.encode('utf-8'))
        encodetask = encode.EncodeTask(fromPath, toPath, profile)

        runner.run(encodetask)

        self.stdout.write('Peak level: %r\n' % encodetask.peak)
        self.stdout.write('Encoded to %s\n' % toPath.encode('utf-8'))


class MaxSample(logcommand.LogCommand):

    summary = "run a max sample task"

    def do(self, args):
        if not args:
            self.stdout.write('Please specify one or more input files.\n')
            return 3

        runner = task.SyncRunner()
        # here to avoid import gst eating our options
        from morituri.common import checksum

        for arg in args:
            fromPath = unicode(arg.decode('utf-8'))

            checksumtask = checksum.MaxSampleTask(fromPath)

            runner.run(checksumtask)

            self.stdout.write('%s\n' % arg)
            self.stdout.write('Biggest absolute sample: %04x\n' %
                checksumtask.checksum)


class Tag(logcommand.LogCommand):

    summary = "run a tag reading task"

    def do(self, args):
        try:
            path = unicode(args[0])
        except IndexError:
            self.stdout.write('Please specify an input file.\n')
            return 3

        runner = task.SyncRunner()

        from morituri.common import encode
        self.debug('Reading tags from %s' % path.encode('utf-8'))
        tagtask = encode.TagReadTask(path)

        runner.run(tagtask)

        for key in tagtask.taglist.keys():
            self.stdout.write('%s: %r\n' % (key, tagtask.taglist[key]))


class MusicBrainzNGS(logcommand.LogCommand):

    usage = "[MusicBrainz disc id]"
    summary = "examine MusicBrainz NGS info"
    description = """Look up a MusicBrainz disc id and output information.

You can get the MusicBrainz disc id with rip cd info.

Example disc id: KnpGsLhvH.lPrNc1PBL21lb9Bg4-"""

    def do(self, args):
        try:
            discId = unicode(args[0])
        except IndexError:
            self.stdout.write('Please specify a MusicBrainz disc id.\n')
            return 3

        from morituri.common import mbngs
        metadatas = mbngs.musicbrainz(discId,
            record=self.getRootCommand().record)

        self.stdout.write('%d releases\n' % len(metadatas))
        for i, md in enumerate(metadatas):
            self.stdout.write('- Release %d:\n' % (i + 1, ))
            self.stdout.write('    Artist: %s\n' % md.artist.encode('utf-8'))
            self.stdout.write('    Title:  %s\n' % md.title.encode('utf-8'))
            self.stdout.write('    Type:   %s\n' % md.releaseType.encode('utf-8'))
            self.stdout.write('    URL: %s\n' % md.url)
            self.stdout.write('    Tracks: %d\n' % len(md.tracks))
            if md.catalogNumber:
                self.stdout.write('    Cat no: %s\n' % md.catalogNumber)
            if md.barcode:
                self.stdout.write('   Barcode: %s\n' % md.barcode)

            for j, track in enumerate(md.tracks):
                self.stdout.write('      Track %2d: %s - %s\n' % (
                    j + 1, track.artist.encode('utf-8'),
                    track.title.encode('utf-8')))


class CDParanoia(logcommand.LogCommand):

    def do(self, args):
        from morituri.program import cdparanoia
        version = cdparanoia.getCdParanoiaVersion()
        self.stdout.write("cdparanoia version: %s\n" % version)


class CDRDAO(logcommand.LogCommand):

    def do(self, args):
        from morituri.program import cdrdao
        version = cdrdao.getCDRDAOVersion()
        self.stdout.write("cdrdao version: %s\n" % version)


class Version(logcommand.LogCommand):

    summary = "debug version getting"

    subCommandClasses = [CDParanoia, CDRDAO]


class Debug(logcommand.LogCommand):

    summary = "debug internals"

    subCommandClasses = [Checksum, Encode, MaxSample, Tag, MusicBrainzNGS,
                         ResultCache, Version]

########NEW FILE########
__FILENAME__ = drive
# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# Morituri - for those about to RIP

# Copyright (C) 2009 Thomas Vander Stichele

# This file is part of morituri.
#
# morituri is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# morituri is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with morituri.  If not, see <http://www.gnu.org/licenses/>.

import os

from morituri.extern.task import task

from morituri.common import logcommand, drive
from morituri.program import cdparanoia

class Analyze(logcommand.LogCommand):

    summary = "analyze caching behaviour of drive"

    def addOptions(self):
        self.parser.add_option('-d', '--device',
            action="store", dest="device",
            help="CD-DA device")

    def handleOptions(self, options):
        if not options.device:
            drives = drive.getAllDevicePaths()
            if not drives:
                self.error('No CD-DA drives found!')
                return 3

            # pick the first
            self.options.device = drives[0]

        # this can be a symlink to another device
        self.options.device = os.path.realpath(self.options.device)

    def do(self, args):
        runner = task.SyncRunner()
        t = cdparanoia.AnalyzeTask(self.options.device)
        runner.run(t)

        if t.defeatsCache is None:
            self.stdout.write(
                'Cannot analyze the drive.  Is there a CD in it?\n')
            return
        if not t.defeatsCache:
            self.stdout.write(
                'cdparanoia cannot defeat the audio cache on this drive.\n')
        else:
            self.stdout.write(
                'cdparanoia can defeat the audio cache on this drive.\n')

        info = drive.getDeviceInfo(self.options.device)
        if not info:
            return

        self.stdout.write(
            'Adding drive cache behaviour to configuration file.\n')

        self.getRootCommand().config.setDefeatsCache(info[0], info[1], info[2],
            t.defeatsCache)


class List(logcommand.LogCommand):

    summary = "list drives"

    def do(self, args):
        paths = drive.getAllDevicePaths()

        if not paths:
            self.stdout.write('No drives found.\n')
            self.stdout.write('Create /dev/cdrom if you have a CD drive, \n')
            self.stdout.write('or install pycdio for better detection.\n')

            return

        try:
            import cdio as _
        except ImportError:
            self.stdout.write(
                'Install pycdio for vendor/model/release detection.\n')
            return

        for path in paths:
            vendor, model, release = drive.getDeviceInfo(path)
            self.stdout.write(
                "drive: %s, vendor: %s, model: %s, release: %s\n" % (
                path, vendor, model, release))

            try:
                offset = self.getRootCommand().config.getReadOffset(
                    vendor, model, release)
                self.stdout.write(
                    "       Configured read offset: %d\n" % offset)
            except KeyError:
                self.stdout.write(
                    "       No read offset found.  Run 'rip offset find'\n")

            try:
                defeats = self.getRootCommand().config.getDefeatsCache(
                    vendor, model, release)
                self.stdout.write(
                    "       Can defeat audio cache: %s\n" % defeats)
            except KeyError:
                self.stdout.write(
                    "       Unknown whether audio cache can be defeated. "
                    "Run 'rip drive analyze'\n")


        if not paths:
            self.stdout.write('No drives found.\n')


class Drive(logcommand.LogCommand):

    summary = "handle drives"

    subCommandClasses = [Analyze, List, ]

########NEW FILE########
__FILENAME__ = image
# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# Morituri - for those about to RIP

# Copyright (C) 2009 Thomas Vander Stichele

# This file is part of morituri.
#
# morituri is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# morituri is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with morituri.  If not, see <http://www.gnu.org/licenses/>.

import os

from morituri.common import logcommand, accurip, program
from morituri.image import image
from morituri.result import result

from morituri.extern.task import task


class Encode(logcommand.LogCommand):

    summary = "encode image"

    def addOptions(self):
        # FIXME: get from config
        self.parser.add_option('-O', '--output-directory',
            action="store", dest="output_directory",
            help="output directory (defaults to current directory)")

        default = 'vorbis'

        # here to avoid import gst eating our options
        from morituri.common import encode

        self.parser.add_option('', '--profile',
            action="store", dest="profile",
            help="profile for encoding (default '%s', choices '%s')" % (
                default, "', '".join(encode.ALL_PROFILES.keys())),
            default=default)

    def do(self, args):
        prog = program.Program(self.getRootCommand().config)
        prog.outdir = (self.options.output_directory or os.getcwd())
        prog.outdir = prog.outdir.decode('utf-8')

        # here to avoid import gst eating our options
        from morituri.common import encode

        profile = encode.ALL_PROFILES[self.options.profile]()

        runner = task.SyncRunner()

        for arg in args:
            arg = arg.decode('utf-8')
            indir = os.path.dirname(arg)
            cueImage = image.Image(arg)
            cueImage.setup(runner)
            # FIXME: find a decent way to get an album-specific outdir
            root = os.path.basename(indir)
            outdir = os.path.join(prog.outdir, root)
            try:
                os.makedirs(outdir)
            except:
                # FIXME: handle other exceptions than OSError Errno 17
                pass
            # FIXME: handle this nicer
            assert outdir != indir

            taskk = image.ImageEncodeTask(cueImage, profile, outdir)
            runner.run(taskk)

            # FIXME: translate .m3u file if it exists
            root, ext = os.path.splitext(arg)
            m3upath = root + '.m3u'
            if os.path.exists(m3upath):
                self.debug('translating .m3u file')
                inm3u = open(m3upath)
                outm3u = open(os.path.join(outdir, os.path.basename(m3upath)),
                    'w')
                for line in inm3u.readlines():
                    root, ext = os.path.splitext(line)
                    if ext:
                        # newline is swallowed by splitext here
                        outm3u.write('%s.%s\n' % (root, profile.extension))
                    else:
                        outm3u.write('%s' % root)
                outm3u.close()


class Retag(logcommand.LogCommand):

    summary = "retag image files"

    def addOptions(self):
        self.parser.add_option('-R', '--release-id',
            action="store", dest="release_id",
            help="MusicBrainz release id to match to (if there are multiple)")


    def do(self, args):
        # here to avoid import gst eating our options
        from morituri.common import encode

        prog = program.Program(self.getRootCommand().config, stdout=self.stdout)
        runner = task.SyncRunner()

        for arg in args:
            self.stdout.write('Retagging image %r\n' % arg)
            arg = arg.decode('utf-8')
            cueImage = image.Image(arg)
            cueImage.setup(runner)

            mbdiscid = cueImage.table.getMusicBrainzDiscId()
            self.stdout.write('MusicBrainz disc id is %s\n' % mbdiscid)
            prog.metadata = prog.getMusicBrainz(cueImage.table, mbdiscid,
                release=self.options.release_id)

            if not prog.metadata:
                print 'Not in MusicBrainz database, skipping'
                continue

            # FIXME: this feels like we're poking at internals.
            prog.cuePath = arg
            prog.result = result.RipResult()
            for track in cueImage.table.tracks:
                path = cueImage.getRealPath(track.indexes[1].path)

                taglist = prog.getTagList(track.number)
                self.debug(
                    'possibly retagging %r from cue path %r with taglist %r',
                    path, arg, taglist)
                t = encode.SafeRetagTask(path, taglist)
                runner.run(t)
                path = os.path.basename(path)
                if t.changed:
                    print 'Retagged %s' % path
                else:
                    print '%s already tagged correctly' % path
            print


class Verify(logcommand.LogCommand):

    usage = '[CUEFILE]...'
    summary = "verify image"

    description = '''
Verifies the image from the given .cue files against the AccurateRip database.
'''

    def do(self, args):
        prog = program.Program(self.getRootCommand().config)
        runner = task.SyncRunner()
        cache = accurip.AccuCache()

        for arg in args:
            arg = arg.decode('utf-8')
            cueImage = image.Image(arg)
            cueImage.setup(runner)

            url = cueImage.table.getAccurateRipURL()
            responses = cache.retrieve(url)

            # FIXME: this feels like we're poking at internals.
            prog.cuePath = arg
            prog.result = result.RipResult()
            for track in cueImage.table.tracks:
                tr = result.TrackResult()
                tr.number = track.number
                prog.result.tracks.append(tr)

            prog.verifyImage(runner, responses)

            print "\n".join(prog.getAccurateRipResults()) + "\n"


class Image(logcommand.LogCommand):

    summary = "handle images"

    description = """
Handle disc images.  Disc images are described by a .cue file.
Disc images can be encoded to another format (for example, to make a
compressed encoding), retagged and verified.
"""

    subCommandClasses = [Encode, Retag, Verify, ]

########NEW FILE########
__FILENAME__ = main
# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

import os
import sys
import pkg_resources

from morituri.common import log, logcommand, common, config
from morituri.configure import configure

from morituri.rip import cd, offset, drive, image, accurip, debug

from morituri.extern.command import command
from morituri.extern.task import task


def main(argv):
    # load plugins

    from morituri.configure import configure
    pluginsdir = configure.pluginsdir
    homepluginsdir = os.path.join(os.path.expanduser('~'),
        '.morituri', 'plugins')

    distributions, errors = pkg_resources.working_set.find_plugins(
        pkg_resources.Environment([pluginsdir, homepluginsdir]))
    if errors:
        log.warning('errors finding plugins: %r', errors)
    log.debug('mapping distributions %r', distributions)
    map(pkg_resources.working_set.add, distributions)

    # validate dependencies
    from morituri.common import deps
    h = deps.DepsHandler()
    h.validate()

    # set user agent
    from morituri.extern.musicbrainzngs import musicbrainz
    musicbrainz.set_useragent("morituri", configure.version,
        'https://thomas.apestaart.org/morituri/trac')


    c = Rip()
    try:
        ret = c.parse(argv)
    except SystemError, e:
        sys.stderr.write('rip: error: %s\n' % e.args)
        return 255
    except ImportError, e:
        h.handleImportError(e)
        return 255
    except task.TaskException, e:
        if isinstance(e.exception, ImportError):
            h.handleImportError(e.exception)
            return 255
        elif isinstance(e.exception, common.MissingDependencyException):
            sys.stderr.write('rip: error: missing dependency "%s"\n' %
                e.exception.dependency)
            return 255
        # FIXME: move this exception
        from morituri.program import cdrdao
        if isinstance(e.exception, cdrdao.DeviceOpenException):
            sys.stderr.write("""rip: error: cannot read CD from drive.
cdrdao says:
%s
""" % e.exception.msg)
            return 255

        if isinstance(e.exception, common.EmptyError):
            log.debug('main',
                "EmptyError: %r", log.getExceptionMessage(e.exception))
            sys.stderr.write(
                'rip: error: Could not create encoded file.\n')
            return 255

        raise
    except command.CommandError, e:
        sys.stderr.write('rip: error: %s\n' % e.output)
        return e.status

    if ret is None:
        return 0

    return ret


class Rip(logcommand.LogCommand):
    usage = "%prog %command"
    description = """Rip rips CD's.

Rip gives you a tree of subcommands to work with.
You can get help on subcommands by using the -h option to the subcommand.
"""

    subCommandClasses = [accurip.AccuRip,
        cd.CD, debug.Debug, drive.Drive, offset.Offset, image.Image, ]

    def addOptions(self):
        # FIXME: is this the right place ?
        log.init()
        from morituri.configure import configure
        log.debug("morituri", "This is morituri version %s (%s)",
            configure.version, configure.revision)

        self.parser.add_option('-R', '--record',
                          action="store_true", dest="record",
                          help="record API requests for playback")
        self.parser.add_option('-v', '--version',
                          action="store_true", dest="version",
                          help="show version information")

    def handleOptions(self, options):
        if options.version:
            print "rip %s" % configure.version
            sys.exit(0)

        self.record = options.record

        self.config = config.Config()

    def parse(self, argv):
        log.debug("morituri", "rip %s" % " ".join(argv))
        logcommand.LogCommand.parse(self, argv)

########NEW FILE########
__FILENAME__ = offset
# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# Morituri - for those about to RIP

# Copyright (C) 2009 Thomas Vander Stichele

# This file is part of morituri.
#
# morituri is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# morituri is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with morituri.  If not, see <http://www.gnu.org/licenses/>.

import os
import tempfile

import gobject
gobject.threads_init()

from morituri.common import logcommand, accurip, drive, program, common
from morituri.common import task as ctask
from morituri.program import cdrdao, cdparanoia

from morituri.extern.task import task

# see http://www.accuraterip.com/driveoffsets.htm
# and misc/offsets.py
OFFSETS = "+6, +48, +102, +667, +12, +30, +618, +594, +738, -472, " + \
          "+98, +116, +96, +733, +120, +691, +685, +97, +600, " + \
          "+690, +1292, +99, +676, +686, +1182, -24, +704, +572, " + \
          "+688, +91, +696, +103, -491, +689, +145, +708, +697, " + \
          "+564, +86, +679, +355, -496, -1164, +1160, +694, 0, " + \
          "-436, +79, +94, +684, +681, +106, +692, +943, +1194, " + \
          "+92, +117, +680, +682, +1268, +678, -582, +1473, +1279, " + \
          "-54, +1508, +740, +1272, +534, +976, +687, +675, +1303, " + \
          "+674, +1263, +108, +974, +122, +111, -489, +772, +732, " + \
          "-495, -494, +975, +935, +87, +668, +1776, +1364, +1336, " + \
          "+1127"


class Find(logcommand.LogCommand):
    summary = "find drive read offset"
    description = """Find drive's read offset by ripping tracks from a
CD in the AccurateRip database."""

    def addOptions(self):
        default = OFFSETS
        self.parser.add_option('-o', '--offsets',
            action="store", dest="offsets",
            help="list of offsets, comma-separated, "
                "colon-separated for ranges (defaults to %s)" % default,
            default=default)
        self.parser.add_option('-d', '--device',
            action="store", dest="device",
            help="CD-DA device")

    def handleOptions(self, options):
        self.options = options
        self._offsets = []
        blocks = options.offsets.split(',')
        for b in blocks:
            if ':' in b:
                a, b = b.split(':')
                self._offsets.extend(range(int(a), int(b) + 1))
            else:
                self._offsets.append(int(b))

        self.debug('Trying with offsets %r', self._offsets)

        if not options.device:
            drives = drive.getAllDevicePaths()
            if not drives:
                self.error('No CD-DA drives found!')
                return 3

            # pick the first
            self.options.device = drives[0]

        # this can be a symlink to another device

    def do(self, args):
        prog = program.Program(self.getRootCommand().config)
        runner = ctask.SyncRunner()

        device = self.options.device

        # if necessary, load and unmount
        self.stdout.write('Checking device %s\n' % device)

        prog.loadDevice(device)
        prog.unmountDevice(device)

        # first get the Table Of Contents of the CD
        t = cdrdao.ReadTOCTask(device=device)

        try:
            runner.run(t)
        except cdrdao.DeviceOpenException, e:
            self.error(e.msg)
            return 3

        table = t.table

        self.debug("CDDB disc id: %r", table.getCDDBDiscId())
        url = table.getAccurateRipURL()
        self.debug("AccurateRip URL: %s", url)

        # FIXME: download url as a task too
        responses = []
        import urllib2
        try:
            handle = urllib2.urlopen(url)
            data = handle.read()
            responses = accurip.getAccurateRipResponses(data)
        except urllib2.HTTPError, e:
            if e.code == 404:
                self.stdout.write(
                    'Album not found in AccurateRip database.\n')
                return 1
            else:
                raise

        if responses:
            self.debug('%d AccurateRip responses found.' % len(responses))

            if responses[0].cddbDiscId != table.getCDDBDiscId():
                self.warning("AccurateRip response discid different: %s",
                    responses[0].cddbDiscId)

        # now rip the first track at various offsets, calculating AccurateRip
        # CRC, and matching it against the retrieved ones

        def match(archecksum, track, responses):
            for i, r in enumerate(responses):
                if archecksum == r.checksums[track - 1]:
                    return archecksum, i

            return None, None

        for offset in self._offsets:
            self.stdout.write('Trying read offset %d ...\n' % offset)
            try:
                archecksum = self._arcs(runner, table, 1, offset)
            except task.TaskException, e:

                # let MissingDependency fall through
                if isinstance(e.exception,
                    common.MissingDependencyException):
                    raise e

                if isinstance(e.exception, cdparanoia.FileSizeError):
                    self.stdout.write(
                        'WARNING: cannot rip with offset %d...\n' % offset)
                    continue

                self.warning("Unknown task exception for offset %d: %r" % (
                    offset, e))
                self.stdout.write(
                    'WARNING: cannot rip with offset %d...\n' % offset)
                continue

            self.debug('AR checksum calculated: %s' % archecksum)

            c, i = match(archecksum, 1, responses)
            if c:
                count = 1
                self.debug('MATCHED against response %d' % i)
                self.stdout.write(
                    'Offset of device is likely %d, confirming ...\n' %
                        offset)

                # now try and rip all other tracks as well, except for the
                # last one (to avoid readers that can't do overread
                for track in range(2, (len(table.tracks) + 1) - 1):
                    try:
                        archecksum = self._arcs(runner, table, track, offset)
                    except task.TaskException, e:
                        if isinstance(e.exception, cdparanoia.FileSizeError):
                            self.stdout.write(
                                'WARNING: cannot rip with offset %d...\n' %
                                offset)
                            continue

                    c, i = match(archecksum, track, responses)
                    if c:
                        self.debug('MATCHED track %d against response %d' % (
                            track, i))
                        count += 1

                if count == len(table.tracks) - 1:
                    self._foundOffset(device, offset)
                    return 0
                else:
                    self.stdout.write(
                        'Only %d of %d tracks matched, continuing ...\n' % (
                        count, len(table.tracks)))

        self.stdout.write('No matching offset found.\n')
        self.stdout.write('Consider trying again with a different disc.\n')

    def _arcs(self, runner, table, track, offset):
        # rips the track with the given offset, return the arcs checksum
        self.debug('Ripping track %r with offset %d ...', track, offset)

        fd, path = tempfile.mkstemp(
            suffix=u'.track%02d.offset%d.morituri.wav' % (
                track, offset))
        os.close(fd)

        t = cdparanoia.ReadTrackTask(path, table,
            table.getTrackStart(track), table.getTrackEnd(track),
            offset=offset, device=self.options.device)
        t.description = 'Ripping track %d with read offset %d' % (
            track, offset)
        runner.run(t)

        # here to avoid import gst eating our options
        from morituri.common import checksum

        t = checksum.AccurateRipChecksumTask(path, trackNumber=track,
            trackCount=len(table.tracks))
        runner.run(t)

        os.unlink(path)
        return "%08x" % t.checksum

    def _foundOffset(self, device, offset):
        self.stdout.write('\nRead offset of device is: %d.\n' %
            offset)

        info = drive.getDeviceInfo(device)
        if not info:
            return

        self.stdout.write('Adding read offset to configuration file.\n')

        self.getRootCommand().config.setReadOffset(info[0], info[1], info[2],
            offset)


class Offset(logcommand.LogCommand):
    summary = "handle drive offsets"

    subCommandClasses = [Find, ]

########NEW FILE########
__FILENAME__ = common
# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

import re
import os
import sys

# twisted's unittests have skip support, standard unittest don't
from twisted.trial import unittest

from morituri.common import log
from morituri.configure import configure

log.init()

# lifted from flumotion


def _diff(old, new, desc):
    import difflib
    lines = difflib.unified_diff(old, new)
    lines = list(lines)
    if not lines:
        return
    output = ''
    for line in lines:
        output += '%s: %s\n' % (desc, line[:-1])

    raise AssertionError(
        ("\nError while comparing strings:\n"
         "%s") % (output.encode('utf-8'), ))


def diffStrings(orig, new, desc='input'):

    assert type(orig) == type(new), 'type %s and %s are different' % (
        type(orig), type(new))

    def _tolines(s):
        return [line + '\n' for line in s.split('\n')]

    return _diff(_tolines(orig),
                 _tolines(new),
                 desc=desc)


class TestCase(log.Loggable, unittest.TestCase):
    # unittest.TestCase.failUnlessRaises does not return the exception,
    # and we'd like to check for the actual exception under TaskException,
    # so override the way twisted.trial.unittest does, without failure

    def failUnlessRaises(self, exception, f, *args, **kwargs):
        try:
            result = f(*args, **kwargs)
        except exception, inst:
            return inst
        except exception, e:
            raise self.failureException('%s raised instead of %s:\n %s'
                                        % (sys.exc_info()[0],
                                           exception.__name__,
                                           log.getExceptionMessage(e)))
        else:
            raise self.failureException('%s not raised (%r returned)'
                                        % (exception.__name__, result))

    assertRaises = failUnlessRaises

    def readCue(self, name):
        """
        Read a .cue file, and replace the version comment with the current
        version so we can use it in comparisons.
        """
        ret = open(os.path.join(os.path.dirname(__file__), name)).read(
            ).decode('utf-8')
        ret = re.sub(
            'REM COMMENT "Morituri.*',
            'REM COMMENT "Morituri %s"' % (configure.version),
            ret, re.MULTILINE)

        return ret

class UnicodeTestMixin:
    # A helper mixin to skip tests if we're not in a UTF-8 locale

    try:
        os.stat(u'morituri.test.B\xeate Noire.empty')
    except UnicodeEncodeError:
        skip = 'No UTF-8 locale'
    except OSError:
        pass

########NEW FILE########
__FILENAME__ = test_common_accurip
# -*- Mode: Python; test-case-name: morituri.test.test_common_accurip -*-
# vi:si:et:sw=4:sts=4:ts=4

import os

from morituri.common import accurip

from morituri.test import common as tcommon


class AccurateRipResponseTestCase(tcommon.TestCase):

    def testResponse(self):
        path = os.path.join(os.path.dirname(__file__),
            'dBAR-011-0010e284-009228a3-9809ff0b.bin')
        data = open(path, "rb").read()

        responses = accurip.getAccurateRipResponses(data)
        self.assertEquals(len(responses), 3)


        response = responses[0]

        self.assertEquals(response.trackCount, 11)
        self.assertEquals(response.discId1, "0010e284")
        self.assertEquals(response.discId2, "009228a3")
        self.assertEquals(response.cddbDiscId, "9809ff0b")

        for i in range(11):
            self.assertEquals(response.confidences[i], 35)
        self.assertEquals(response.checksums[0], "beea32c8")
        self.assertEquals(response.checksums[10], "acee98ca")

########NEW FILE########
__FILENAME__ = test_common_cache
# -*- Mode: Python; test-case-name: morituri.test.test_common_cache -*-
# vi:si:et:sw=4:sts=4:ts=4

import os

from morituri.common import cache

from morituri.test import common as tcommon


class ResultCacheTestCase(tcommon.TestCase):

    def setUp(self):
        self.cache = cache.ResultCache(
            os.path.join(os.path.dirname(__file__), 'cache', 'result'))

    def testGetResult(self):
        result = self.cache.getRipResult('fe105a11')
        self.assertEquals(result.object.title, "The Writing's on the Wall")

    def testGetIds(self):
        ids = self.cache.getIds()
        self.assertEquals(ids, ['fe105a11'])

########NEW FILE########
__FILENAME__ = test_common_checksum
# -*- Mode: Python; test-case-name: morituri.test.test_common_checksum -*-
# vi:si:et:sw=4:sts=4:ts=4

import os
import tempfile

import gobject
gobject.threads_init()

from morituri.common import checksum, task as ctask

from morituri.extern.task import task, gstreamer

from morituri.test import common as tcommon


def h(i):
    return "0x%08x" % i


class EmptyTestCase(tcommon.TestCase):

    def testEmpty(self):
        # this test makes sure that checksumming empty files doesn't hang
        self.runner = ctask.SyncRunner(verbose=False)
        fd, path = tempfile.mkstemp(suffix=u'morituri.test.empty')
        checksumtask = checksum.ChecksumTask(path)
        # FIXME: do we want a specific error for this ?
        e = self.assertRaises(task.TaskException, self.runner.run,
            checksumtask, verbose=False)
        self.failUnless(isinstance(e.exception, gstreamer.GstException))
        os.unlink(path)


class PathTestCase(tcommon.TestCase):

    def _testSuffix(self, suffix):
        self.runner = ctask.SyncRunner(verbose=False)
        fd, path = tempfile.mkstemp(suffix=suffix)
        checksumtask = checksum.ChecksumTask(path)
        e = self.assertRaises(task.TaskException, self.runner.run,
            checksumtask, verbose=False)
        self.failUnless(isinstance(e.exception, gstreamer.GstException))
        os.unlink(path)


class UnicodePathTestCase(PathTestCase, tcommon.UnicodeTestMixin):

    def testUnicodePath(self):
        # this test makes sure we can checksum a unicode path
        self._testSuffix(u'morituri.test.B\xeate Noire.empty')


class NormalPathTestCase(PathTestCase):

    def testSingleQuote(self):
        self._testSuffix(u"morituri.test.Guns 'N Roses")

    def testDoubleQuote(self):
        # This test makes sure we can checksum files with double quote in
        # their name
        self._testSuffix(u'morituri.test.12" edit')

    def testBackSlash(self):
        # This test makes sure we can checksum files with a backslash in
        # their name
        self._testSuffix(u'morituri.test.40 Years Back\\Come')

########NEW FILE########
__FILENAME__ = test_common_common
# -*- Mode: Python; test-case-name: morituri.test.test_common_common -*-
# vi:si:et:sw=4:sts=4:ts=4

import os
import tempfile

from morituri.common import common

from morituri.test import common as tcommon


class ShrinkTestCase(tcommon.TestCase):

    def testSufjan(self):
        path = (u'morituri/Sufjan Stevens - Illinois/02. Sufjan Stevens - '
                 'The Black Hawk War, or, How to Demolish an Entire '
                 'Civilization and Still Feel Good About Yourself in the '
                 'Morning, or, We Apologize for the Inconvenience but '
                 'You\'re Going to Have to Leave Now, or, "I Have Fought '
                 'the Big Knives and Will Continue to Fight Them Until They '
                 'Are Off Our Lands!".flac')

        shorter = common.shrinkPath(path)
        self.failUnless(os.path.splitext(path)[0].startswith(
            os.path.splitext(shorter)[0]))
        self.failIfEquals(path, shorter)


class FramesTestCase(tcommon.TestCase):

    def testFrames(self):
        self.assertEquals(common.framesToHMSF(123456), '00:27:26.06')


class FormatTimeTestCase(tcommon.TestCase):

    def testFormatTime(self):
        self.assertEquals(common.formatTime(7202), '02:00:02.000')


class GetRelativePathTestCase(tcommon.TestCase):

    def testRelativeOutputDirectory(self):
        directory = '.Placebo - Black Market Music (2000)'
        cue = './' + directory + '/Placebo - Black Market Music (2000)'
        track = './' + directory + '/01. Placebo - Taste in Men.flac'

        self.assertEquals(common.getRelativePath(track, cue),
            '01. Placebo - Taste in Men.flac')


class GetRealPathTestCase(tcommon.TestCase):

    def testRealWithBackslash(self):
        fd, path = tempfile.mkstemp(suffix=u'back\\slash.flac')
        refPath = os.path.join(os.path.dirname(path), 'fake.cue')

        self.assertEquals(common.getRealPath(refPath, path),
            path)

        # same path, but with wav extension, will point to flac file
        wavPath = path[:-4] + 'wav'
        self.assertEquals(common.getRealPath(refPath, wavPath),
            path)

        os.close(fd)
        os.unlink(path)

########NEW FILE########
__FILENAME__ = test_common_config
# -*- Mode: Python; test-case-name: morituri.test.test_common_config -*-
# vi:si:et:sw=4:sts=4:ts=4

import os
import tempfile

from morituri.common import config

from morituri.test import common as tcommon


class OffsetTestCase(tcommon.TestCase):

    def setUp(self):
        fd, self._path = tempfile.mkstemp(suffix=u'.morituri.test.config')
        os.close(fd)
        self._config = config.Config(self._path)

    def tearDown(self):
        os.unlink(self._path)

    def testAddReadOffset(self):
        self.assertRaises(KeyError,
            self._config.getReadOffset, 'PLEXTOR ', 'DVDR   PX-L890SA', '1.05')
        self._config.setReadOffset('PLEXTOR ', 'DVDR   PX-L890SA', '1.05', 6)

        # getting it from memory should work
        offset = self._config.getReadOffset('PLEXTOR ', 'DVDR   PX-L890SA',
            '1.05')
        self.assertEquals(offset, 6)

        # and so should getting it after reading it again
        self._config.open()
        offset = self._config.getReadOffset('PLEXTOR ', 'DVDR   PX-L890SA',
            '1.05')
        self.assertEquals(offset, 6)

    def testAddReadOffsetSpaced(self):
        self.assertRaises(KeyError,
            self._config.getReadOffset, 'Slimtype', 'eSAU208   2     ', 'ML03')
        self._config.setReadOffset('Slimtype', 'eSAU208   2     ', 'ML03', 6)

        # getting it from memory should work
        offset = self._config.getReadOffset(
            'Slimtype', 'eSAU208   2     ', 'ML03')
        self.assertEquals(offset, 6)

        # and so should getting it after reading it again
        self._config.open()
        offset = self._config.getReadOffset(
            'Slimtype', 'eSAU208   2     ', 'ML03')
        self.assertEquals(offset, 6)

########NEW FILE########
__FILENAME__ = test_common_directory
# -*- Mode: Python; test-case-name: morituri.test.test_common_directory -*-
# vi:si:et:sw=4:sts=4:ts=4

from morituri.common import directory

from morituri.test import common


class DirectoryTestCase(common.TestCase):

    def testAll(self):
        d = directory.Directory()

        path = d.getConfig()
        self.failUnless(path.startswith('/home'))

        path = d.getCache()
        self.failUnless(path.startswith('/home'))

        paths = d.getReadCaches()
        self.failUnless(paths[0].startswith('/home'))

########NEW FILE########
__FILENAME__ = test_common_drive
# -*- Mode: Python; test-case-name: morituri.test.test_common_drive -*-
# vi:si:et:sw=4:sts=4:ts=4

from morituri.test import common
from morituri.common import drive


class ListifyTestCase(common.TestCase):

    def testString(self):
        string = '/dev/sr0'
        self.assertEquals(drive._listify(string), [string, ])

    def testList(self):
        lst = ['/dev/scd0', '/dev/sr0']
        self.assertEquals(drive._listify(lst), lst)

########NEW FILE########
__FILENAME__ = test_common_encode
# -*- Mode: Python; test-case-name: morituri.test.test_common_encode -*-
# vi:si:et:sw=4:sts=4:ts=4

import os
import tempfile

import gobject
gobject.threads_init()

import gst

from morituri.common import encode

from morituri.extern.task import task, gstreamer

from morituri.test import common


class PathTestCase(common.TestCase):

    def _testSuffix(self, suffix):
        # because of https://bugzilla.gnome.org/show_bug.cgi?id=688625
        # we first create the file with a 'normal' filename, then rename
        self.runner = task.SyncRunner(verbose=False)
        fd, path = tempfile.mkstemp()

        cmd = "gst-launch " \
            "audiotestsrc num-buffers=100 samplesperbuffer=1024 ! " \
            "audioconvert ! audio/x-raw-int,width=16,depth=16,channels =2 ! " \
            "wavenc ! " \
            "filesink location=\"%s\" > /dev/null 2>&1" % (
            gstreamer.quoteParse(path).encode('utf-8'), )
        self.debug('Running cmd %r' % cmd)
        os.system(cmd)
        self.failUnless(os.path.exists(path))
        os.close(fd)

        fd, newpath = tempfile.mkstemp(suffix=suffix)
        os.rename(path, newpath)

        encodetask = encode.EncodeTask(newpath, newpath + '.out',
            encode.WavProfile())
        self.runner.run(encodetask, verbose=False)
        os.close(fd)
        os.unlink(newpath)
        os.unlink(newpath + '.out')


class UnicodePathTestCase(PathTestCase, common.UnicodeTestMixin):

    def testUnicodePath(self):
        # this test makes sure we can checksum a unicode path
        self._testSuffix(u'.morituri.test_encode.B\xeate Noire')


class NormalPathTestCase(PathTestCase):

    def testSingleQuote(self):
        self._testSuffix(u".morituri.test_encode.Guns 'N Roses")

    def testDoubleQuote(self):
        self._testSuffix(u'.morituri.test_encode.12" edit')


class TagReadTestCase(common.TestCase):

    def testRead(self):
        path = os.path.join(os.path.dirname(__file__), u'track.flac')
        self.runner = task.SyncRunner(verbose=False)
        t = encode.TagReadTask(path)
        self.runner.run(t)
        self.failUnless(t.taglist)
        self.assertEquals(t.taglist['audio-codec'], 'FLAC')
        self.assertEquals(t.taglist['description'], 'audiotest wave')


class TagWriteTestCase(common.TestCase):

    def testWrite(self):
        fd, inpath = tempfile.mkstemp(suffix=u'.morituri.tagwrite.flac')

        # wave is pink-noise because a pure sine is encoded too efficiently
        # by flacenc and triggers not enough frames in parsing
        # FIXME: file a bug for this in GStreamer
        os.system('gst-launch '
            'audiotestsrc '
                'wave=pink-noise num-buffers=10 samplesperbuffer=588 ! '
            'audioconvert ! '
            'audio/x-raw-int,channels=2,width=16,height=16,rate=44100 ! '
            'flacenc ! filesink location=%s > /dev/null 2>&1' % inpath)
        os.close(fd)

        fd, outpath = tempfile.mkstemp(suffix=u'.morituri.tagwrite.flac')
        self.runner = task.SyncRunner(verbose=False)
        taglist = gst.TagList()
        taglist[gst.TAG_ARTIST] = 'Artist'
        taglist[gst.TAG_TITLE] = 'Title'

        t = encode.TagWriteTask(inpath, outpath, taglist)
        self.runner.run(t)

        t = encode.TagReadTask(outpath)
        self.runner.run(t)
        self.failUnless(t.taglist)
        self.assertEquals(t.taglist['audio-codec'], 'FLAC')
        self.assertEquals(t.taglist['description'], 'audiotest wave')
        self.assertEquals(t.taglist[gst.TAG_ARTIST], 'Artist')
        self.assertEquals(t.taglist[gst.TAG_TITLE], 'Title')

        os.unlink(inpath)
        os.unlink(outpath)


class SafeRetagTestCase(common.TestCase):

    def setUp(self):
        self._fd, self._path = tempfile.mkstemp(suffix=u'.morituri.retag.flac')

        os.system('gst-launch '
            'audiotestsrc '
                'num-buffers=40 samplesperbuffer=588 wave=pink-noise ! '
            'audioconvert ! '
            'audio/x-raw-int,channels=2,width=16,height=16,rate=44100 ! '
            'flacenc ! filesink location=%s > /dev/null 2>&1' % self._path)
        os.close(self._fd)
        self.runner = task.SyncRunner(verbose=False)

    def tearDown(self):
        os.unlink(self._path)

    def testNoChange(self):
        taglist = gst.TagList()
        taglist[gst.TAG_DESCRIPTION] = 'audiotest wave'
        taglist[gst.TAG_AUDIO_CODEC] = 'FLAC'

        t = encode.SafeRetagTask(self._path, taglist)
        self.runner.run(t)

    def testChange(self):
        taglist = gst.TagList()
        taglist[gst.TAG_DESCRIPTION] = 'audiotest retagged'
        taglist[gst.TAG_AUDIO_CODEC] = 'FLAC'
        taglist[gst.TAG_ARTIST] = 'Artist'

        t = encode.SafeRetagTask(self._path, taglist)
        self.runner.run(t)

########NEW FILE########
__FILENAME__ = test_common_gstreamer
# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

from morituri.common import gstreamer

from morituri.test import common


class VersionTestCase(common.TestCase):

    def testGStreamer(self):
        version = gstreamer.gstreamerVersion()
        self.failUnless(version.startswith('0.'))

    def testGSTPython(self):
        version = gstreamer.gstPythonVersion()
        self.failUnless(version.startswith('0.'))

    def testFlacEnc(self):
        version = gstreamer.elementFactoryVersion('flacenc')
        self.failUnless(version.startswith('0.'))

########NEW FILE########
__FILENAME__ = test_common_mbngs
# -*- Mode: Python; test-case-name: morituri.test.test_common_mbngs -*-
# vi:si:et:sw=4:sts=4:ts=4

import os
import json

import unittest

from morituri.common import mbngs


class MetadataTestCase(unittest.TestCase):

    # Generated with rip -R cd info
    def testJeffEverybodySingle(self):
        path = os.path.join(os.path.dirname(__file__),
            'morituri.release.3451f29c-9bb8-4cc5-bfcc-bd50104b94f8.json')
        handle = open(path, "rb")
        response = json.loads(handle.read())
        handle.close()
        discid = "wbjbST2jUHRZaB1inCyxxsL7Eqc-"

        metadata = mbngs._getMetadata({}, response['release'], discid)

        self.failIf(metadata.release)

    def test2MeterSessies10(self):
        # various artists, multiple artists per track
        path = os.path.join(os.path.dirname(__file__),
            'morituri.release.a76714e0-32b1-4ed4-b28e-f86d99642193.json')
        handle = open(path, "rb")
        response = json.loads(handle.read())
        handle.close()
        discid = "f7XO36a7n1LCCskkCiulReWbwZA-"

        metadata = mbngs._getMetadata({}, response['release'], discid)

        self.assertEquals(metadata.artist, u'Various Artists')
        self.assertEquals(metadata.release, u'2001-10-15')
        self.assertEquals(metadata.mbidArtist,
            u'89ad4ac3-39f7-470e-963a-56509c546377')

        self.assertEquals(len(metadata.tracks), 18)

        track16 = metadata.tracks[15]

        self.assertEquals(track16.artist, 'Tom Jones & Stereophonics')
        self.assertEquals(track16.mbidArtist,
            u'57c6f649-6cde-48a7-8114-2a200247601a'
            ';0bfba3d3-6a04-4779-bb0a-df07df5b0558'
        )
        self.assertEquals(track16.sortName,
            u'Jones, Tom & Stereophonics')

    def testBalladOfTheBrokenSeas(self):
        # various artists disc
        path = os.path.join(os.path.dirname(__file__),
            'morituri.release.e32ae79a-336e-4d33-945c-8c5e8206dbd3.json')
        handle = open(path, "rb")
        response = json.loads(handle.read())
        handle.close()
        discid = "xAq8L4ELMW14.6wI6tt7QAcxiDI-"

        metadata = mbngs._getMetadata({}, response['release'], discid)

        self.assertEquals(metadata.artist, u'Isobel Campbell & Mark Lanegan')
        self.assertEquals(metadata.sortName,
            u'Campbell, Isobel & Lanegan, Mark')
        self.assertEquals(metadata.release, u'2006-01-30')
        self.assertEquals(metadata.mbidArtist,
            u'd51f3a15-12a2-41a0-acfa-33b5eae71164;'
            'a9126556-f555-4920-9617-6e013f8228a7')

        self.assertEquals(len(metadata.tracks), 12)

        track12 = metadata.tracks[11]

        self.assertEquals(track12.artist, u'Isobel Campbell & Mark Lanegan')
        self.assertEquals(track12.sortName,
            u'Campbell, Isobel'
            ' & Lanegan, Mark'
            )
        self.assertEquals(track12.mbidArtist,
            u'd51f3a15-12a2-41a0-acfa-33b5eae71164;'
            'a9126556-f555-4920-9617-6e013f8228a7')

    def testMalaInCuba(self):
        # single artist disc, but with multiple artists tracks
        # see https://github.com/thomasvs/morituri/issues/19
        path = os.path.join(os.path.dirname(__file__),
            'morituri.release.61c6fd9b-18f8-4a45-963a-ba3c5d990cae.json')
        handle = open(path, "rb")
        response = json.loads(handle.read())
        handle.close()
        discid = "u0aKVpO.59JBy6eQRX2vYcoqQZ0-"

        metadata = mbngs._getMetadata({}, response['release'], discid)

        self.assertEquals(metadata.artist, u'Mala')
        self.assertEquals(metadata.sortName, u'Mala')
        self.assertEquals(metadata.release, u'2012-09-17')
        self.assertEquals(metadata.mbidArtist,
            u'09f221eb-c97e-4da5-ac22-d7ab7c555bbb')

        self.assertEquals(len(metadata.tracks), 14)

        track6 = metadata.tracks[5]

        self.assertEquals(track6.artist, u'Mala feat. Dreiser & Sexto Sentido')
        self.assertEquals(track6.sortName,
            u'Mala feat. Dreiser & Sexto Sentido')
        self.assertEquals(track6.mbidArtist,
            u'09f221eb-c97e-4da5-ac22-d7ab7c555bbb'
            ';ec07a209-55ff-4084-bc41-9d4d1764e075'
            ';f626b92e-07b1-4a19-ad13-c09d690db66c'
        )



########NEW FILE########
__FILENAME__ = test_common_path
# -*- Mode: Python; test-case-name: morituri.test.test_common_path -*-
# vi:si:et:sw=4:sts=4:ts=4

from morituri.common import path

from morituri.test import common


class FilterTestCase(common.TestCase):

    def setUp(self):
        self._filter = path.PathFilter(special=True)

    def testSlash(self):
        part = u'A Charm/A Blade'
        self.assertEquals(self._filter.filter(part), u'A Charm-A Blade')

    def testFat(self):
        part = u'A Word: F**k you?'
        self.assertEquals(self._filter.filter(part), u'A Word - F__k you_')

    def testSpecial(self):
        part = u'<<< $&*!\' "()`{}[]spaceship>>>'
        self.assertEquals(self._filter.filter(part),
               u'___ _____ ________spaceship___')

    def testGreatest(self):
        part = u'Greatest Ever! Soul: The Definitive Collection'
        self.assertEquals(self._filter.filter(part),
               u'Greatest Ever_ Soul - The Definitive Collection')

########NEW FILE########
__FILENAME__ = test_common_program
# -*- Mode: Python; test-case-name: morituri.test.test_common_program -*-
# vi:si:et:sw=4:sts=4:ts=4


import os
import pickle

import unittest

from morituri.result import result
from morituri.common import program, accurip, mbngs, config
from morituri.rip import common as rcommon


class TrackImageVerifyTestCase(unittest.TestCase):
    # example taken from a rip of Luke Haines Is Dead, disc 1
    # AccurateRip database has 0 confidence for 1st track
    # Rip had a wrong result for track 9

    def testVerify(self):
        path = os.path.join(os.path.dirname(__file__),
            'dBAR-020-002e5023-029d8e49-040eaa14.bin')
        data = open(path, "rb").read()
        responses = accurip.getAccurateRipResponses(data)

        # these crc's were calculated from an actual rip
        checksums = [1644890007, 2945205445, 3983436658, 1528082495,
        1203704270, 1163423644, 3649097244, 100524219, 1583356174, 373652058,
        1842579359, 2850056507, 1329730252, 2526965856, 2525886806, 209743350,
        3184062337, 2099956663, 2943874164, 2321637196]

        prog = program.Program(config.Config())
        prog.result = result.RipResult()
        # fill it with empty trackresults
        for i, c in enumerate(checksums):
            r = result.TrackResult()
            r.number = i + 1
            prog.result.tracks.append(r)

        prog._verifyImageWithChecksums(responses, checksums)

        # now check if the results were filled in properly
        tr = prog.result.getTrackResult(1)
        self.assertEquals(tr.accurip, False)
        self.assertEquals(tr.ARDBMaxConfidence, 0)
        self.assertEquals(tr.ARDBCRC, 0)
        self.assertEquals(tr.ARDBCRC, 0)

        tr = prog.result.getTrackResult(2)
        self.assertEquals(tr.accurip, True)
        self.assertEquals(tr.ARDBMaxConfidence, 2)
        self.assertEquals(tr.ARDBCRC, checksums[2 - 1])

        tr = prog.result.getTrackResult(10)
        self.assertEquals(tr.accurip, False)
        self.assertEquals(tr.ARDBMaxConfidence, 2)
        # we know track 10 was ripped wrong
        self.assertNotEquals(tr.ARDBCRC, checksums[10 - 1])

        res = prog.getAccurateRipResults()
        self.assertEquals(res[1 - 1],
            "Track  1: rip NOT accurate (not found)             "
            "[620b0797], DB [notfound]")
        self.assertEquals(res[2 - 1],
            "Track  2: rip accurate     (max confidence      2) "
            "[af8c44c5], DB [af8c44c5]")
        self.assertEquals(res[10 - 1],
            "Track 10: rip NOT accurate (max confidence      2) "
            "[16457a5a], DB [eb6e55b4]")


class HTOATestCase(unittest.TestCase):

    def setUp(self):
        path = os.path.join(os.path.dirname(__file__),
            'silentalarm.result.pickle')
        self._tracks = pickle.load(open(path, 'rb'))

    def testGetAccurateRipResults(self):
        prog = program.Program(config.Config())
        prog.result = result.RipResult()
        prog.result.tracks = self._tracks

        prog.getAccurateRipResults()


class PathTestCase(unittest.TestCase):

    def testStandardTemplateEmpty(self):
        prog = program.Program(config.Config())

        path = prog.getPath(u'/tmp', rcommon.DEFAULT_DISC_TEMPLATE,
            'mbdiscid', 0)
        self.assertEquals(path,
            u'/tmp/unknown/Unknown Artist - mbdiscid/Unknown Artist - mbdiscid')

    def testStandardTemplateFilled(self):
        prog = program.Program(config.Config())
        md = mbngs.DiscMetadata()
        md.artist = md.sortName = 'Jeff Buckley'
        md.title = 'Grace'
        prog.metadata = md

        path = prog.getPath(u'/tmp', rcommon.DEFAULT_DISC_TEMPLATE,
            'mbdiscid', 0)
        self.assertEquals(path,
            u'/tmp/unknown/Jeff Buckley - Grace/Jeff Buckley - Grace')

    def testIssue66TemplateFilled(self):
        prog = program.Program(config.Config())
        md = mbngs.DiscMetadata()
        md.artist = md.sortName = 'Jeff Buckley'
        md.title = 'Grace'
        prog.metadata = md

        path = prog.getPath(u'/tmp', u'%A/%d', 'mbdiscid', 0)
        self.assertEquals(path,
            u'/tmp/Jeff Buckley/Grace')

########NEW FILE########
__FILENAME__ = test_common_renamer
# -*- Mode: Python; test-case-name: morituri.test.test_image_cue -*-
# vi:si:et:sw=4:sts=4:ts=4

import os
import tempfile

import unittest

from morituri.common import renamer


class RenameInFileTestcase(unittest.TestCase):

    def setUp(self):
        (fd, self._path) = tempfile.mkstemp(suffix='.morituri.renamer.infile')
        os.write(fd, 'This is a test\nThis is another\n')
        os.close(fd)

    def testVerify(self):
        o = renamer.RenameInFile(self._path, 'is is a', 'at was some')
        self.assertEquals(o.verify(), None)
        os.unlink(self._path)
        self.assertRaises(AssertionError, o.verify)

    def testDo(self):
        o = renamer.RenameInFile(self._path, 'is is a', 'at was some')
        o.do()
        output = open(self._path).read()
        self.assertEquals(output, 'That was some test\nThat was somenother\n')
        os.unlink(self._path)

    def testSerialize(self):
        o = renamer.RenameInFile(self._path, 'is is a', 'at was some')
        data = o.serialize()
        o2 = renamer.RenameInFile.deserialize(data)
        o2.do()
        output = open(self._path).read()
        self.assertEquals(output, 'That was some test\nThat was somenother\n')
        os.unlink(self._path)


class RenameFileTestcase(unittest.TestCase):

    def setUp(self):
        (fd, self._source) = tempfile.mkstemp(suffix='.morituri.renamer.file')
        os.write(fd, 'This is a test\nThis is another\n')
        os.close(fd)
        (fd, self._destination) = tempfile.mkstemp(
            suffix='.morituri.renamer.file')
        os.close(fd)
        os.unlink(self._destination)
        self._operation = renamer.RenameFile(self._source, self._destination)

    def testVerify(self):
        self.assertEquals(self._operation.verify(), None)

        handle = open(self._destination, 'w')
        handle.close()
        self.assertRaises(AssertionError, self._operation.verify)

        os.unlink(self._destination)
        self.assertEquals(self._operation.verify(), None)

        os.unlink(self._source)
        self.assertRaises(AssertionError, self._operation.verify)

    def testDo(self):
        self._operation.do()
        output = open(self._destination).read()
        self.assertEquals(output, 'This is a test\nThis is another\n')
        os.unlink(self._destination)

    def testSerialize(self):
        data = self._operation.serialize()
        o = renamer.RenameFile.deserialize(data)
        o.do()
        output = open(self._destination).read()
        self.assertEquals(output, 'This is a test\nThis is another\n')
        os.unlink(self._destination)


class OperatorTestCase(unittest.TestCase):

    def setUp(self):
        self._statePath = tempfile.mkdtemp(suffix='.morituri.renamer.operator')
        self._operator = renamer.Operator(self._statePath, 'test')

        (fd, self._source) = tempfile.mkstemp(
            suffix='.morituri.renamer.operator')
        os.write(fd, 'This is a test\nThis is another\n')
        os.close(fd)
        (fd, self._destination) = tempfile.mkstemp(
            suffix='.morituri.renamer.operator')
        os.close(fd)
        os.unlink(self._destination)
        self._operator.addOperation(
            renamer.RenameInFile(self._source, 'is is a', 'at was some'))
        self._operator.addOperation(
            renamer.RenameFile(self._source, self._destination))

    def tearDown(self):
        os.system('rm -rf %s' % self._statePath)

    def testLoadNoneDone(self):
        self._operator.save()

        o = renamer.Operator(self._statePath, 'test')
        o.load()

        self.assertEquals(o._todo, self._operator._todo)
        self.assertEquals(o._done, [])
        os.unlink(self._source)

    def testLoadOneDone(self):
        self.assertEquals(len(self._operator._done), 0)
        self._operator.save()
        self._operator.next()
        self.assertEquals(len(self._operator._done), 1)

        o = renamer.Operator(self._statePath, 'test')
        o.load()

        self.assertEquals(len(o._done), 1)
        self.assertEquals(o._todo, self._operator._todo)
        self.assertEquals(o._done, self._operator._done)

        # now continue
        o.next()
        self.assertEquals(len(o._done), 2)
        os.unlink(self._destination)

    def testLoadOneInterrupted(self):
        self.assertEquals(len(self._operator._done), 0)
        self._operator.save()

        # cheat by doing a task without saving
        self._operator._todo[0].do()

        self.assertEquals(len(self._operator._done), 0)

        o = renamer.Operator(self._statePath, 'test')
        o.load()

        self.assertEquals(len(o._done), 0)
        self.assertEquals(o._todo, self._operator._todo)
        self.assertEquals(o._done, self._operator._done)

        # now continue, resuming
        o.next()
        self.assertEquals(len(o._done), 1)
        o.next()
        self.assertEquals(len(o._done), 2)

        os.unlink(self._destination)

########NEW FILE########
__FILENAME__ = test_image_cue
# -*- Mode: Python; test-case-name: morituri.test.test_image_cue -*-
# vi:si:et:sw=4:sts=4:ts=4

import os
import tempfile
import unittest

from morituri.image import table, cue
from morituri.configure import configure

from morituri.test import common


class KingsSingleTestCase(unittest.TestCase):

    def setUp(self):
        self.cue = cue.CueFile(os.path.join(os.path.dirname(__file__),
            u'kings-single.cue'))
        self.cue.parse()
        self.assertEquals(len(self.cue.table.tracks), 11)

    def testGetTrackLength(self):
        t = self.cue.table.tracks[0]
        self.assertEquals(self.cue.getTrackLength(t), 17811)
        # last track has unknown length
        t = self.cue.table.tracks[-1]
        self.assertEquals(self.cue.getTrackLength(t), -1)


class KingsSeparateTestCase(unittest.TestCase):

    def setUp(self):
        self.cue = cue.CueFile(os.path.join(os.path.dirname(__file__),
            u'kings-separate.cue'))
        self.cue.parse()
        self.assertEquals(len(self.cue.table.tracks), 11)

    def testGetTrackLength(self):
        # all tracks have unknown length
        t = self.cue.table.tracks[0]
        self.assertEquals(self.cue.getTrackLength(t), -1)
        t = self.cue.table.tracks[-1]
        self.assertEquals(self.cue.getTrackLength(t), -1)


class KanyeMixedTestCase(unittest.TestCase):

    def setUp(self):
        self.cue = cue.CueFile(os.path.join(os.path.dirname(__file__),
            u'kanye.cue'))
        self.cue.parse()
        self.assertEquals(len(self.cue.table.tracks), 13)

    def testGetTrackLength(self):
        t = self.cue.table.tracks[0]
        self.assertEquals(self.cue.getTrackLength(t), -1)


class WriteCueFileTestCase(unittest.TestCase):

    def testWrite(self):
        fd, path = tempfile.mkstemp(suffix=u'.morituri.test.cue')
        os.close(fd)

        it = table.Table()

        t = table.Track(1)
        t.index(1, absolute=0, path=u'track01.wav', relative=0, counter=1)
        it.tracks.append(t)

        t = table.Track(2)
        t.index(0, absolute=1000, path=u'track01.wav',
            relative=1000, counter=1)
        t.index(1, absolute=2000, path=u'track02.wav', relative=0, counter=2)
        it.tracks.append(t)
        it.absolutize()
        it.leadout = 3000

        common.diffStrings(u"""REM DISCID 0C002802
REM COMMENT "Morituri %s"
FILE "track01.wav" WAVE
  TRACK 01 AUDIO
    INDEX 01 00:00:00
  TRACK 02 AUDIO
    INDEX 00 00:13:25
FILE "track02.wav" WAVE
    INDEX 01 00:00:00
""" % configure.version, it.cue())
        os.unlink(path)

########NEW FILE########
__FILENAME__ = test_image_image
# -*- Mode: Python; test-case-name: morituri.test.test_image_image -*-
# vi:si:et:sw=4:sts=4:ts=4

import os
import tempfile

import gobject
gobject.threads_init()

import gst

from morituri.image import image
from morituri.common import common, log

from morituri.extern.task import task, gstreamer

from morituri.test import common as tcommon

log.init()


def h(i):
    return "0x%08x" % i


class TrackSingleTestCase(tcommon.TestCase):

    def setUp(self):
        self.image = image.Image(os.path.join(os.path.dirname(__file__),
            u'track-single.cue'))
        self.runner = task.SyncRunner(verbose=False)
        self.image.setup(self.runner)

    def testAccurateRipChecksum(self):
        checksumtask = image.AccurateRipChecksumTask(self.image)
        self.runner.run(checksumtask, verbose=False)

        self.assertEquals(len(checksumtask.checksums), 4)
        self.assertEquals(h(checksumtask.checksums[0]), '0x00000000')
        self.assertEquals(h(checksumtask.checksums[1]), '0x793fa868')
        self.assertEquals(h(checksumtask.checksums[2]), '0x8dd37c26')
        self.assertEquals(h(checksumtask.checksums[3]), '0x00000000')

    def testLength(self):
        self.assertEquals(self.image.table.getTrackLength(1), 2)
        self.assertEquals(self.image.table.getTrackLength(2), 2)
        self.assertEquals(self.image.table.getTrackLength(3), 2)
        self.assertEquals(self.image.table.getTrackLength(4), 4)

    def testCDDB(self):
        self.assertEquals(self.image.table.getCDDBDiscId(), "08000004")

    def testAccurateRip(self):
        self.assertEquals(self.image.table.getAccurateRipIds(), (
            "00000016", "0000005b"))


class TrackSeparateTestCase(tcommon.TestCase):

    def setUp(self):
        self.image = image.Image(os.path.join(os.path.dirname(__file__),
            u'track-separate.cue'))
        self.runner = task.SyncRunner(verbose=False)
        self.image.setup(self.runner)

    def testAccurateRipChecksum(self):
        checksumtask = image.AccurateRipChecksumTask(self.image)
        self.runner.run(checksumtask, verbose=False)

        self.assertEquals(len(checksumtask.checksums), 4)
        self.assertEquals(h(checksumtask.checksums[0]), '0xd60e55e1')
        self.assertEquals(h(checksumtask.checksums[1]), '0xd63dc2d2')
        self.assertEquals(h(checksumtask.checksums[2]), '0xd63dc2d2')
        self.assertEquals(h(checksumtask.checksums[3]), '0x7271db39')

    def testLength(self):
        self.assertEquals(self.image.table.getTrackLength(1), 10)
        self.assertEquals(self.image.table.getTrackLength(2), 10)
        self.assertEquals(self.image.table.getTrackLength(3), 10)
        self.assertEquals(self.image.table.getTrackLength(4), 10)

    def testCDDB(self):
        self.assertEquals(self.image.table.getCDDBDiscId(), "08000004")

    def testAccurateRip(self):
        self.assertEquals(self.image.table.getAccurateRipIds(), (
            "00000064", "00000191"))


class AudioLengthTestCase(tcommon.TestCase):

    def testLength(self):
        path = os.path.join(os.path.dirname(__file__), u'track.flac')
        t = image.AudioLengthTask(path)
        runner = task.SyncRunner()
        runner.run(t, verbose=False)
        self.assertEquals(t.length, 10 * common.SAMPLES_PER_FRAME)


class AudioLengthPathTestCase(tcommon.TestCase):

    def _testSuffix(self, suffix):
        self.runner = task.SyncRunner(verbose=False)
        fd, path = tempfile.mkstemp(suffix=suffix)
        t = image.AudioLengthTask(path)
        e = self.assertRaises(task.TaskException, self.runner.run,
            t, verbose=False)
        self.failUnless(isinstance(e.exception, gstreamer.GstException),
            "%r is not a gstreamer.GstException" % e.exceptionMessage)
        self.assertEquals(e.exception.gerror.domain, gst.STREAM_ERROR)
        # our empty file triggers TYPE_NOT_FOUND
        self.assertEquals(e.exception.gerror.code,
            gst.STREAM_ERROR_TYPE_NOT_FOUND)
        os.unlink(path)


class NormalAudioLengthPathTestCase(AudioLengthPathTestCase):

    def testSingleQuote(self):
        self._testSuffix(u"morituri.test.Guns 'N Roses")

    def testDoubleQuote(self):
        # This test makes sure we can checksum files with double quote in
        # their name
        self._testSuffix(u'morituri.test.12" edit')


class UnicodeAudioLengthPathTestCase(AudioLengthPathTestCase,
        tcommon.UnicodeTestMixin):

    def testUnicodePath(self):
        # this test makes sure we can checksum a unicode path
        self._testSuffix(u'morituri.test.B\xeate Noire.empty')

########NEW FILE########
__FILENAME__ = test_image_table
# -*- Mode: Python; test-case-name: morituri.test.test_image_table -*-
# vi:si:et:sw=4:sts=4:ts=4

from morituri.image import table

from morituri.test import common as tcommon


def h(i):
    return "0x%08x" % i


class TrackTestCase(tcommon.TestCase):

    def testRepr(self):
        track = table.Track(1)
        self.assertEquals(repr(track), "<Track 01>")

        track.index(1, 100)
        self.failUnless(repr(track.indexes[1]).startswith('<Index 01 '))


class LadyhawkeTestCase(tcommon.TestCase):
    # Ladyhawke - Ladyhawke - 0602517818866
    # contains 12 audio tracks and one data track
    # CDDB has been verified against freedb:
    #   http://www.freedb.org/freedb/misc/c60af50d
    #   http://www.freedb.org/freedb/jazz/c60af50d
    # AccurateRip URL has been verified against EAC's, using wireshark

    def setUp(self):
        self.table = table.Table()

        for i in range(12):
            self.table.tracks.append(table.Track(i + 1, audio=True))
        self.table.tracks.append(table.Track(13, audio=False))

        offsets = [0, 15537, 31691, 50866, 66466, 81202, 99409,
            115920, 133093, 149847, 161560, 177682, 207106]
        t = self.table.tracks
        for i, offset in enumerate(offsets):
            t[i].index(1, absolute=offset)

        self.failIf(self.table.hasTOC())

        self.table.leadout = 210385

        self.failUnless(self.table.hasTOC())
        self.assertEquals(self.table.tracks[0].getPregap(), 0)

    def testCDDB(self):
        self.assertEquals(self.table.getCDDBDiscId(), "c60af50d")

    def testMusicBrainz(self):
        # output from mb-submit-disc:
        # http://mm.musicbrainz.org/bare/cdlookup.html?toc=1+12+195856+150+
        # 15687+31841+51016+66616+81352+99559+116070+133243+149997+161710+
        # 177832&tracks=12&id=KnpGsLhvH.lPrNc1PBL21lb9Bg4-
        # however, not (yet) in musicbrainz database

        self.assertEquals(self.table.getMusicBrainzDiscId(),
            "KnpGsLhvH.lPrNc1PBL21lb9Bg4-")

    def testAccurateRip(self):
        self.assertEquals(self.table.getAccurateRipIds(), (
            "0013bd5a", "00b8d489"))
        self.assertEquals(self.table.getAccurateRipURL(),
        "http://www.accuraterip.com/accuraterip/a/5/d/"
        "dBAR-012-0013bd5a-00b8d489-c60af50d.bin")

    def testDuration(self):
        self.assertEquals(self.table.duration(), 2761413)


class MusicBrainzTestCase(tcommon.TestCase):
    # example taken from http://musicbrainz.org/doc/DiscIDCalculation
    # disc is Ettella Diamant

    def setUp(self):
        self.table = table.Table()

        for i in range(6):
            self.table.tracks.append(table.Track(i + 1, audio=True))

        offsets = [0, 15213, 32164, 46442, 63264, 80339]
        t = self.table.tracks
        for i, offset in enumerate(offsets):
            t[i].index(1, absolute=offset)

        self.failIf(self.table.hasTOC())

        self.table.leadout = 95312

        self.failUnless(self.table.hasTOC())

    def testMusicBrainz(self):
        self.assertEquals(self.table.getMusicBrainzDiscId(),
            '49HHV7Eb8UKF3aQiNmu1GR8vKTY-')


class PregapTestCase(tcommon.TestCase):

    def setUp(self):
        self.table = table.Table()

        for i in range(2):
            self.table.tracks.append(table.Track(i + 1, audio=True))

        offsets = [0, 15537]
        t = self.table.tracks
        for i, offset in enumerate(offsets):
            t[i].index(1, absolute=offset)
        t[1].index(0, offsets[1] - 200)

    def testPreGap(self):
        self.assertEquals(self.table.tracks[0].getPregap(), 0)
        self.assertEquals(self.table.tracks[1].getPregap(), 200)

########NEW FILE########
__FILENAME__ = test_image_toc
# -*- Mode: Python; test-case-name: morituri.test.test_image_toc -*-
# vi:si:et:sw=4:sts=4:ts=4

import os
import copy
import shutil
import tempfile

from morituri.image import toc

from morituri.test import common


class CureTestCase(common.TestCase):

    def setUp(self):
        self.path = os.path.join(os.path.dirname(__file__),
            u'cure.toc')
        self.toc = toc.TocFile(self.path)
        self.toc.parse()
        self.assertEquals(len(self.toc.table.tracks), 13)

    def testGetTrackLength(self):
        t = self.toc.table.tracks[0]
        # first track has known length because the .toc is a single file
        # its length is all of track 1 from .toc, plus the INDEX 00 length
        # of track 2
        self.assertEquals(self.toc.getTrackLength(t),
            (((6 * 60) + 16) * 75 + 45) + ((1 * 75) + 4))
        # last track has unknown length
        t = self.toc.table.tracks[-1]
        self.assertEquals(self.toc.getTrackLength(t), -1)

    def testIndexes(self):
        # track 2, index 0 is at 06:16:45 or 28245
        # track 2, index 1 is at 06:17:49 or 28324
        # FIXME: cdrdao seems to get length of FILE 1 frame too many,
        # and START value one frame less
        t = self.toc.table.tracks[1]
        self.assertEquals(t.getIndex(0).relative, 28245)
        self.assertEquals(t.getIndex(1).relative, 28324)

    def _getIndex(self, t, i):
        track = self.toc.table.tracks[t - 1]
        return track.getIndex(i)

    def _assertAbsolute(self, t, i, value):
        index = self._getIndex(t, i)
        self.assertEquals(index.absolute, value)

    def _assertPath(self, t, i, value):
        index = self._getIndex(t, i)
        self.assertEquals(index.path, value)

    def _assertRelative(self, t, i, value):
        index = self._getIndex(t, i)
        self.assertEquals(index.relative, value)

    def testSetFile(self):
        self._assertAbsolute(1, 1, 0)
        self._assertAbsolute(2, 0, 28245)
        self._assertAbsolute(2, 1, 28324)
        self._assertPath(1, 1, "data.wav")

        # self.toc.table.absolutize()
        self.toc.table.clearFiles()

        self._assertAbsolute(1, 1, 0)
        self._assertAbsolute(2, 0, 28245)
        self._assertAbsolute(2, 1, 28324)
        self._assertAbsolute(3, 1, 46110)
        self._assertAbsolute(4, 1, 66767)
        self._assertPath(1, 1, None)
        self._assertRelative(1, 1, None)

        # adding the first track file with length 28324 to the table should
        # relativize from absolute 0 to absolute 28323, right before track 2,
        # index 1
        self.toc.table.setFile(1, 1, 'track01.wav', 28324)
        self._assertPath(1, 1, 'track01.wav')
        self._assertRelative(1, 1, 0)
        self._assertPath(2, 0, 'track01.wav')
        self._assertRelative(2, 0, 28245)

        self._assertPath(2, 1, None)
        self._assertRelative(2, 1, None)

    def testConvertCue(self):
        # self.toc.table.absolutize()
        cue = self.toc.table.cue()
        ref = self.readCue('cure.cue')
        common.diffStrings(ref, cue)

        # we verify it because it has failed in readdisc in the past
        self.assertEquals(self.toc.table.getAccurateRipURL(),
            'http://www.accuraterip.com/accuraterip/'
            '3/c/4/dBAR-013-0019d4c3-00fe8924-b90c650d.bin')

    def testGetRealPath(self):
        self.assertRaises(KeyError, self.toc.getRealPath, u'track01.wav')
        (fd, path) = tempfile.mkstemp(suffix=u'.morituri.test.wav')
        self.assertEquals(self.toc.getRealPath(path), path)

        winpath = path.replace('/', '\\')
        self.assertEquals(self.toc.getRealPath(winpath), path)
        os.close(fd)
        os.unlink(path)

# Bloc Party - Silent Alarm has a Hidden Track One Audio


class BlocTestCase(common.TestCase):

    def setUp(self):
        self.path = os.path.join(os.path.dirname(__file__),
            u'bloc.toc')
        self.toc = toc.TocFile(self.path)
        self.toc.parse()
        self.assertEquals(len(self.toc.table.tracks), 13)

    def testGetTrackLength(self):
        t = self.toc.table.tracks[0]
        # first track has known length because the .toc is a single file
        # the length is from Track 1, Index 1 to Track 2, Index 1, so
        # does not include the htoa
        self.assertEquals(self.toc.getTrackLength(t), 19649)
        # last track has unknown length
        t = self.toc.table.tracks[-1]
        self.assertEquals(self.toc.getTrackLength(t), -1)

    def testIndexes(self):
        track01 = self.toc.table.tracks[0]
        index00 = track01.getIndex(0)
        self.assertEquals(index00.absolute, 0)
        self.assertEquals(index00.relative, 0)
        self.assertEquals(index00.counter, 0)

        index01 = track01.getIndex(1)
        self.assertEquals(index01.absolute, 15220)
        self.assertEquals(index01.relative, 0)
        self.assertEquals(index01.counter, 1)

        track05 = self.toc.table.tracks[4]

        index00 = track05.getIndex(0)
        self.assertEquals(index00.absolute, 84070)
        self.assertEquals(index00.relative, 68850)
        self.assertEquals(index00.counter, 1)

        index01 = track05.getIndex(1)
        self.assertEquals(index01.absolute, 84142)
        self.assertEquals(index01.relative, 68922)
        self.assertEquals(index01.counter, 1)

    # This disc has a pre-gap, so is a good test for .CUE writing

    def testConvertCue(self):
        #self.toc.table.absolutize()
        self.failUnless(self.toc.table.hasTOC())
        cue = self.toc.table.cue()
        ref = self.readCue('bloc.cue')
        common.diffStrings(ref, cue)

    def testCDDBId(self):
        # self.toc.table.absolutize()
        # cd-discid output:
        # ad0be00d 13 15370 35019 51532 69190 84292 96826 112527 132448
        # 148595 168072 185539 203331 222103 3244

        self.assertEquals(self.toc.table.getCDDBDiscId(), 'ad0be00d')

    def testAccurateRip(self):
        # we verify it because it has failed in readdisc in the past
        # self.toc.table.absolutize()
        self.assertEquals(self.toc.table.getAccurateRipURL(),
            'http://www.accuraterip.com/accuraterip/'
            'e/d/2/dBAR-013-001af2de-0105994e-ad0be00d.bin')

# The Breeders - Mountain Battles has CDText


class BreedersTestCase(common.TestCase):

    def setUp(self):
        self.path = os.path.join(os.path.dirname(__file__),
            u'breeders.toc')
        self.toc = toc.TocFile(self.path)
        self.toc.parse()
        self.assertEquals(len(self.toc.table.tracks), 13)

    def testCDText(self):
        cdt = self.toc.table.cdtext
        self.assertEquals(cdt['PERFORMER'], 'THE BREEDERS')
        self.assertEquals(cdt['TITLE'], 'MOUNTAIN BATTLES')

        t = self.toc.table.tracks[0]
        cdt = t.cdtext
        self.assertRaises(AttributeError, getattr, cdt, 'PERFORMER')
        self.assertEquals(cdt['TITLE'], 'OVERGLAZED')

    def testConvertCue(self):
        # self.toc.table.absolutize()
        self.failUnless(self.toc.table.hasTOC())
        cue = self.toc.table.cue()
        ref = self.readCue('breeders.cue')
        self.assertEquals(cue, ref)

# Ladyhawke has a data track


class LadyhawkeTestCase(common.TestCase):

    def setUp(self):
        self.path = os.path.join(os.path.dirname(__file__),
            u'ladyhawke.toc')
        self.toc = toc.TocFile(self.path)
        self.toc.parse()
        self.assertEquals(len(self.toc.table.tracks), 13)
        #import code; code.interact(local=locals())
        self.failIf(self.toc.table.tracks[-1].audio)

    def testCDDBId(self):
        #self.toc.table.absolutize()
        self.assertEquals(self.toc.table.getCDDBDiscId(), 'c60af50d')
        # output from cd-discid:
        # c60af50d 13 150 15687 31841 51016 66616 81352 99559 116070 133243
        # 149997 161710 177832 207256 2807

    def testMusicBrainz(self):
        self.assertEquals(self.toc.table.getMusicBrainzDiscId(),
            "KnpGsLhvH.lPrNc1PBL21lb9Bg4-")
        self.assertEquals(self.toc.table.getMusicBrainzSubmitURL(),
            "http://mm.musicbrainz.org/bare/cdlookup.html?toc="
            "1+12+195856+150+15687+31841+51016+66616+81352+99559+"
            "116070+133243+149997+161710+177832&"
            "tracks=12&id=KnpGsLhvH.lPrNc1PBL21lb9Bg4-")

    # FIXME: I don't trust this toc, but I can't find the CD anymore

    def testDuration(self):
        self.assertEquals(self.toc.table.duration(), 2761413)

    def testGetFrameLength(self):
        self.assertEquals(self.toc.table.getFrameLength(data=True), 210385)

    def testCue(self):
        self.failUnless(self.toc.table.canCue())
        data = self.toc.table.cue()
        lines = data.split("\n")
        self.assertEquals(lines[0], "REM DISCID C60AF50D")


class CapitalMergeTestCase(common.TestCase):

    def setUp(self):
        self.toc1 = toc.TocFile(os.path.join(os.path.dirname(__file__),
            u'capital.1.toc'))
        self.toc1.parse()
        self.assertEquals(len(self.toc1.table.tracks), 11)
        self.failUnless(self.toc1.table.tracks[-1].audio)

        self.toc2 = toc.TocFile(os.path.join(os.path.dirname(__file__),
            u'capital.2.toc'))
        self.toc2.parse()
        self.assertEquals(len(self.toc2.table.tracks), 1)
        self.failIf(self.toc2.table.tracks[-1].audio)

        self.table = copy.deepcopy(self.toc1.table)
        self.table.merge(self.toc2.table)

    def testCDDBId(self):
        #self.table.absolutize()
        self.assertEquals(self.table.getCDDBDiscId(), 'b910140c')
        # output from cd-discid:
        # b910140c 12 24320 44855 64090 77885 88095 104020 118245 129255 141765
        # 164487 181780 209250 4440

    def testMusicBrainz(self):
        # URL to submit: http://mm.musicbrainz.org/bare/cdlookup.html?toc=1+11+
        # 197850+24320+44855+64090+77885+88095+104020+118245+129255+141765+
        # 164487+181780&tracks=11&id=MAj3xXf6QMy7G.BIFOyHyq4MySE-
        self.assertEquals(self.table.getMusicBrainzDiscId(),
            "MAj3xXf6QMy7G.BIFOyHyq4MySE-")

    def testDuration(self):
        # this matches track 11 end sector - track 1 start sector on
        # musicbrainz
        # compare to 3rd and 4th value in URL above
        self.assertEquals(self.table.getFrameLength(), 173530)
        self.assertEquals(self.table.duration(), 2313733)


class UnicodeTestCase(common.TestCase, common.UnicodeTestMixin):

    def setUp(self):
        # we copy the normal non-utf8 filename to a utf-8 filename
        # in this test because builds with LANG=C fail if we include
        # utf-8 filenames in the dist
        path = u'Jos\xe9Gonz\xe1lez.toc'
        self._performer = u'Jos\xe9 Gonz\xe1lez'
        source = os.path.join(os.path.dirname(__file__), 'jose.toc')
        (fd, self.dest) = tempfile.mkstemp(suffix=path)
        os.close(fd)
        shutil.copy(source, self.dest)
        self.toc = toc.TocFile(self.dest)
        self.toc.parse()
        self.assertEquals(len(self.toc.table.tracks), 10)

    def tearDown(self):
        os.unlink(self.dest)

    def testGetTrackLength(self):
        t = self.toc.table.tracks[0]
        # first track has known length because the .toc is a single file
        self.assertEquals(self.toc.getTrackLength(t), 12001)
        # last track has unknown length
        t = self.toc.table.tracks[-1]
        self.assertEquals(self.toc.getTrackLength(t), -1)

    def testGetTrackPerformer(self):
        t = self.toc.table.tracks[0]
        self.assertEquals(t.cdtext['PERFORMER'], self._performer)


# Interpol - Turn of the Bright Lights has same cddb disc id as
# Afghan Whigs - Gentlemen


class TOTBLTestCase(common.TestCase):

    def setUp(self):
        self.path = os.path.join(os.path.dirname(__file__),
            u'totbl.fast.toc')
        self.toc = toc.TocFile(self.path)
        self.toc.parse()
        self.assertEquals(len(self.toc.table.tracks), 11)

    def testCDDBId(self):
        #self.toc.table.absolutize()
        self.assertEquals(self.toc.table.getCDDBDiscId(), '810b7b0b')


# The Strokes - Someday has a 1 frame SILENCE marked as such in toc


class StrokesTestCase(common.TestCase):

    def setUp(self):
        self.path = os.path.join(os.path.dirname(__file__),
            u'strokes-someday.toc')
        self.toc = toc.TocFile(self.path)
        self.toc.parse()
        self.assertEquals(len(self.toc.table.tracks), 1)

    def testIndexes(self):
        t = self.toc.table.tracks[0]
        i0 = t.getIndex(0)
        self.assertEquals(i0.relative, 0)
        self.assertEquals(i0.absolute, 0)
        self.assertEquals(i0.counter, 0)
        self.assertEquals(i0.path, None)

        i1 = t.getIndex(1)
        self.assertEquals(i1.relative, 0)
        self.assertEquals(i1.absolute, 1)
        self.assertEquals(i1.counter, 1)
        self.assertEquals(i1.path, u'data.wav')

        cue = self._filterCue(self.toc.table.cue())
        ref = self._filterCue(open(os.path.join(os.path.dirname(__file__),
            'strokes-someday.eac.cue')).read()).decode('utf-8')
        common.diffStrings(ref, cue)

    def _filterCue(self, output):
        # helper to be able to compare our generated .cue with the
        # EAC-extracted one
        discard = [ 'TITLE', 'PERFORMER', 'FLAGS', 'REM' ]
        lines = output.split('\n')

        res = []

        for line in lines:
            found = False
            for needle in discard:
                if line.find(needle) > -1:
                    found = True

            if line.find('FILE') > -1:
                line = 'FILE "data.wav" WAVE'

            if not found:
                res.append(line)

        return '\n'.join(res)




# Surfer Rosa has
# track 00 consisting of 32 frames of SILENCE
# track 11 Vamos with an INDEX 02
# compared to an EAC single .cue file, all our offsets are 32 frames off
# because the toc uses silence for track 01 index 00 while EAC puts it in
# Range.wav


class SurferRosaTestCase(common.TestCase):

    def setUp(self):
        self.path = os.path.join(os.path.dirname(__file__),
            u'surferrosa.toc')
        self.toc = toc.TocFile(self.path)
        self.toc.parse()
        self.assertEquals(len(self.toc.table.tracks), 21)

    def testIndexes(self):
        # HTOA
        t = self.toc.table.tracks[0]
        self.assertEquals(len(t.indexes), 2)

        i0 = t.getIndex(0)
        self.assertEquals(i0.relative, 0)
        self.assertEquals(i0.absolute, 0)
        self.assertEquals(i0.path, None)
        self.assertEquals(i0.counter, 0)

        i1 = t.getIndex(1)
        self.assertEquals(i1.relative, 0)
        self.assertEquals(i1.absolute, 32)
        self.assertEquals(i1.path, 'data.wav')
        self.assertEquals(i1.counter, 1)

        # track 11, Vamos

        t = self.toc.table.tracks[10]
        self.assertEquals(len(t.indexes), 2)

        # 32 frames of silence, and 1483 seconds of data.wav
        self.assertEquals(t.getIndex(1).relative, 111225)
        self.assertEquals(t.getIndex(1).absolute, 111257)
        self.assertEquals(t.getIndex(2).relative, 111225 + 3370)
        self.assertEquals(t.getIndex(2).absolute, 111257 + 3370)

#        print self.toc.table.cue()


########NEW FILE########
__FILENAME__ = test_program_cdparanoia
# -*- Mode: Python; test-case-name: morituri.test.test_program_cdparanoia -*-
# vi:si:et:sw=4:sts=4:ts=4

import os

from morituri.extern.task import task

from morituri.program import cdparanoia

from morituri.test import common


class ParseTestCase(common.TestCase):

    def setUp(self):
        # report from Afghan Whigs - Sweet Son Of A Bitch
        path = os.path.join(os.path.dirname(__file__),
            'cdparanoia.progress')
        self._parser = cdparanoia.ProgressParser(start=45990, stop=47719)

        self._handle = open(path)

    def testParse(self):
        for line in self._handle.readlines():
            self._parser.parse(line)

        q = '%.01f %%' % (self._parser.getTrackQuality() * 100.0, )
        self.assertEquals(q, '99.6 %')

class Parse1FrameTestCase(common.TestCase):

    def setUp(self):
        path = os.path.join(os.path.dirname(__file__),
            'cdparanoia.progress.strokes')
        self._parser = cdparanoia.ProgressParser(start=0, stop=0)

        self._handle = open(path)

    def testParse(self):
        for line in self._handle.readlines():
            self._parser.parse(line)

        q = '%.01f %%' % (self._parser.getTrackQuality() * 100.0, )
        self.assertEquals(q, '100.0 %')


class ErrorTestCase(common.TestCase):

    def setUp(self):
        # report from a rip with offset -1164 causing scsi errors
        path = os.path.join(os.path.dirname(__file__),
            'cdparanoia.progress.error')
        self._parser = cdparanoia.ProgressParser(start=0, stop=10800)

        self._handle = open(path)

    def testParse(self):
        for line in self._handle.readlines():
            self._parser.parse(line)

        q = '%.01f %%' % (self._parser.getTrackQuality() * 100.0, )
        self.assertEquals(q, '79.6 %')


class VersionTestCase(common.TestCase):

    def testGetVersion(self):
        v = cdparanoia.getCdParanoiaVersion()
        self.failUnless(v)
        # of the form III 10.2
        # make sure it ends with a digit
        self.failUnless(int(v[-1]), v)


class AnalyzeFileTask(cdparanoia.AnalyzeTask):

    def __init__(self, path):
        self.command = ['cat', path]

    def readbytesout(self, bytes):
        self.readbyteserr(bytes)


class CacheTestCase(common.TestCase):

    def testDefeatsCache(self):
        self.runner = task.SyncRunner(verbose=False)

        path = os.path.join(os.path.dirname(__file__),
            'cdparanoia', 'PX-L890SA.cdparanoia-A.stderr')
        t = AnalyzeFileTask(path)
        self.runner.run(t)
        self.failUnless(t.defeatsCache)


########NEW FILE########
__FILENAME__ = test_program_cdrdao
# -*- Mode: Python; test-case-name: morituri.test.test_program_cdparanoia -*-
# vi:si:et:sw=4:sts=4:ts=4

import os

from morituri.program import cdrdao

from morituri.test import common


class FakeTask:

    def setProgress(self, value):
        pass


class ParseTestCase(common.TestCase):

    def setUp(self):
        path = os.path.join(os.path.dirname(__file__),
            'cdrdao.readtoc.progress')
        self._parser = cdrdao.OutputParser(FakeTask())

        self._handle = open(path)

    def testParse(self):
        # FIXME: we should be testing splitting in byte blocks, not lines
        for line in self._handle.readlines():
            self._parser.read(line)

        for i, offset in enumerate(
            [0, 13864, 31921, 48332, 61733, 80961,
             100219, 116291, 136188, 157504, 175275]):
            track = self._parser.table.tracks[i]
            self.assertEquals(track.getIndex(1).absolute, offset)

        self.assertEquals(self._parser.version, '1.2.2')


class VersionTestCase(common.TestCase):

    def testGetVersion(self):
        v = cdrdao.getCDRDAOVersion()
        self.failUnless(v)
        # make sure it starts with a digit
        self.failUnless(int(v[0]))

########NEW FILE########
