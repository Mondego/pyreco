__FILENAME__ = normalizer
"""
Thierry Bertin-Mahieux (2011) Columbia University
tb2332@columbia.edu


This code contains functions to normalize an artist name,
and possibly a song title.
This is intended to do metadata matching.
It is mostly an elaborate hack, I never did an extensive search of
all problematic name matches.
Code developed using Python 2.6 on a Ubuntu machine, using UTF-8

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.


Copyright 2011, Thierry Bertin-Mahieux

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import re
import sys
import unicodedata
import itertools
import Levenshtein # http://pypi.python.org/pypi/python-Levenshtein/


# ROTATION SYMBOLS (A and B => B and A)
rotation_symbols = ['\|', '/', '&', ',', '\+', ';', '_']#, '\-']
rotation_words = ['and', 'y', 'et', 'vs', 'vs.', 'v', 'with', 'feat',
                  'feat.', 'featuring', 'presents', 'ft.', 'pres.']

# SYMBOLS TO REMOVE AT THE BEGINNING
stub_to_remove = ['dj', 'dj.', 'mc', 'm.c.', 'mc.', 'the', 'los', 'les']

# SYMBOLS TO REMOVE AT THE END
end_to_remove1 = ['big band', 'trio', 'quartet', 'ensemble', 'orchestra']
end_to_remove2 = ['band']

# COMPILED REGULAR EXPRESSION
# white spaces
re_space = re.compile(r'\s')
# non alphanumeric
re_nonalphanum = re.compile(r'\W')
# rotation symbols
re_rotsymbols = re.compile('\s*?' + '|'.join(rotation_symbols) + '\s*?')
# rotation words
re_rotwords = re.compile(r'\s(' + '|'.join(rotation_words) + ')\s')
# stub to remove
re_remstub = re.compile('(' + '|'.join(stub_to_remove) + ')\s(.*)')
# ending to remove
re_remending1 = re.compile('(.*)\s(' + '|'.join(end_to_remove1) + ')')
re_remending2 = re.compile('(.*)\s(' + '|'.join(end_to_remove2) + ')')
# quotes to remove
re_remquotes = re.compile('(.+)\s(".+?")\s(.+)')
# parenthesis to remove
re_remparenthesis = re.compile('(.+)\s(\(.+?\))\s*(.*)')
# brackets to remove
re_rembrackets = re.compile('(.+)\s(\[.+?\])\s*(.*)')


def char_is_ascii(c):
    """
    Check if a unicode character, e.g. u'A', u'1' or u'\u0301' is ASCII
    """
    #return ord(c) < 128
    # the following should be faster, according to:
    #http://stackoverflow.com/questions/196345/how-to-check-if-a-string-in-python-is-in-ascii
    return c < u"\x7F"


def remove_non_ascii(s):
    """
    Normalize characters in unicode string 's' that are not ASCII,
    try to transform accented characters to non accented version.
    Otherwise, remove non-ascii chars
    """
    decomposition = unicodedata.normalize('NFKD', s)
    return filter(lambda x: char_is_ascii(x), decomposition)


def to_lower_case(s):
    """
    transform a unicode string 's' to lowercase
    ok, this one is trivial, I know
    """
    return s.lower()


def remove_spaces(s):
    """
    Remove all possible spaces in the unicode string s
    """
    return re_space.sub('', s)


def replace_rotation_symbols(s):
    """
    Mostly, replace '&' by 'and'
    """
    return re_rotsymbols.sub(' and ', s)


def remove_stub(s):
    """
    Remove a questionable beginning, e.g. dj
    otherwise return string at is
    """
    m = re_remstub.match(s)
    if not m:
        return s
    return m.groups()[1]


def remove_endings(s):
    """
    Remove questionable endings, e.g. 'band'
    """
    m = re_remending1.match(s)
    if m:
       s = m.groups()[0]
    m = re_remending2.match(s)
    if m:
        s = m.groups()[0]
    return s


def remove_quotes(s):
    """
    Remove the quote, like Thierry "The Awesomest" BM
    """
    m = re_remquotes.match(s)
    if not m:
        return s
    parts = m.groups()
    assert len(parts) == 3
    return parts[0] + ' ' + parts[2]


def remove_parenthesis(s):
    """
    Remove parenthesis, like Thierry (Coolest guy)
    """
    m = re_remparenthesis.match(s)
    if not m:
        return s
    parts = m.groups()
    assert len(parts) >= 2
    if len(parts) == 2:
        return parts[0]
    return parts[0] + ' ' + parts[2]


def remove_brackets(s):
    """
    Remove brackets, like Thierry [Coolest guy]
    """
    m = re_rembrackets.match(s)
    if not m:
        return s
    parts = m.groups()
    assert len(parts) >= 2
    if len(parts) == 2:
        return parts[0]
    return parts[0] + ' ' + parts[2]


def normalize_no_rotation(s):
    """
    We normalize a name that is supposed to contain no
    rotation term ('and', 'y', ...)
    """
    # remove beginning
    s = remove_stub(s)
    # remove ends
    s = remove_endings(s)    
    # remove ()
    s = remove_parenthesis(s)
    # remove ""
    s = remove_quotes(s)
    return s


def split_rotation_words(s):
    """
    Split a name using the rotation words: 'and', 'vs', 'y', 'et', ...
    then create all possible permutations
    """
    parts = re_rotwords.split(s)
    parts = filter(lambda p: not p in rotation_words, parts)[:5]
    results = set()
    # keep only the individual elems (risky?)
    for p in parts:
        results.add(p)
    # create all permutations
    permutations = itertools.permutations(parts)
    #maxperm = 30
    #count_perm = 0
    for perm in permutations:
        #count_perm += 1
        #if count_perm > maxperm:
        #    break
        results.add(' '.join(perm))
    # redo the same but remove the stub first for all parts
    parts = map(lambda p: normalize_no_rotation(p), parts)
    for p in parts:
        results.add(p)
    permutations = itertools.permutations(parts)
    for perm in permutations:
        results.add(' '.join(perm))
    # done
    return results


def remove_nonalphanumeric(s):
    """
    Remove usual punctuation signs:  ! , ? : ; . '   etc
    Also, we transform long spaces into normal ones
    """
    # split around non-alphanum chars
    parts = re_nonalphanum.split(s)
    # remove empty spots
    parts = filter(lambda p: p, parts)
    # rejoin with regular space ' '
    return ' '.join(parts)


def normalize_artist(s):
    """
    Return a set of normalized versions of that artist name
    """
    # normalized versions
    results = set()
    # lower case
    s = to_lower_case(s)
    results.add(s)
    # remove non-ascii chars (try to replace them)
    s = remove_non_ascii(s)
    results.add(s)
    # try removing parenthesis before, in case there's an & in it
    s2 = remove_parenthesis(s)
    results.add(s2)
    # replace rotation symbols
    s = replace_rotation_symbols(s)
    # split and permute according to rotation words
    permutations = split_rotation_words(s)
    results.update(permutations)
    # remove non-alphanumeric and normalize spaces
    results = map(lambda s: remove_nonalphanumeric(s), results)
    # remove all spaces
    results = map(lambda s: remove_spaces(s), results)
    # done (and remove dupes)
    return set(results)


def normalize_title(s):
    """
    Return a set of normalized versions of that title
    """
    # normalized versions
    results = set()
    # lower case
    s = to_lower_case(s)
    results.add(s)
    # remove non-ascii chars (try to replace them)
    s = remove_non_ascii(s)
    results.add(s)
    # try removing parenthesis
    s = remove_parenthesis(s)
    results.add(s)
    # try removing brackets
    s = remove_brackets(s)
    results.add(s)
    # remove non-alphanumeric and normalize spaces
    results = map(lambda s: remove_nonalphanumeric(s), results)
    # remove all spaces
    results = map(lambda s: remove_spaces(s), results)
    # done (and remove dupes)
    return set(results)


def same_artist(name1, name2):
    """
    Compare two artists:
    - edit distance
    - if one name is contained in the other
    - by normalizing the names
    Return True if it's the same artist, False otherwise
    """
    # trivial
    n1 = to_lower_case(name1)
    n2 = to_lower_case(name2)
    if n1 == n2:
        return True
    # edit distance
    if len(n1) >= 10 or len(n2) >= 10:
        if Levenshtein.distance(n1, n2) <= 2:
            return True
    # n1 contains n2? or the other way around
    if len(n1) >= 10 and len(n2) >= 10:
        if len(n1) > len(n2):
            if n1.find(n2) >= 0:
                return True
        else:
            if n2.find(n1) >= 0:
                return True
    # compare by normalizing names
    normalized1 = normalize_artist(n1)
    normalized2 = normalize_artist(n2)
    if len(normalized1.intersection(normalized2)) > 0:
        return True
    return False


def same_title(title1, title2):
    """
    Compare two titles:
    - edit distance
    - if one name is contained in the other
    - by normalizing the title
    Return True if it's the same title, False otherwise
    """
    # trivial
    t1 = to_lower_case(title1)
    t2 = to_lower_case(title2)
    if t1 == t2:
        return True
    # edit distance
    if len(t1) >= 10 or len(t2) >= 10:
        if Levenshtein.distance(t1, t2) <= 2:
            return True
    # n1 contains n2? or the other way around
    if len(t1) >= 10 and len(t2) >= 10:
        if len(t1) > len(t2):
            if t1.find(t2) >= 0:
                return True
        else:
            if t2.find(t1) >= 0:
                return True
    # compare by normalizing names
    normalized1 = normalize_title(t1)
    normalized2 = normalize_title(t2)
    if len(normalized1.intersection(normalized2)) > 0:
        return True
    return False

########NEW FILE########
__FILENAME__ = create_aggregate_file
"""
Thierry Bertin-Mahieux (2011) Columbia University
tb2332@columbia.edu

This code creates an aggregate file, i.e. an HDF5 file that looks like song
files, except that it contains more than one song

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.


Copyright 2011, Thierry Bertin-Mahieux

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import glob
import time
import datetime
import hdf5_utils as HDF5


def get_all_files(basedir,ext='.h5') :
    """
    From a root directory, go through all subdirectories
    and find all files with the given extension.
    Return all absolute paths in a list.
    """
    allfiles = []
    for root, dirs, files in os.walk(basedir):
        files = glob.glob(os.path.join(root,'*'+ext))
        for f in files :
            allfiles.append( os.path.abspath(f) )
    return allfiles


def die_with_usage():
    """ HELP MENU """
    print 'create_aggregate_file.py'
    print '   by T. Bertin-Mahieux (2011) Columbia University'
    print '   tb2332@columbia.edu'
    print ''
    print 'Creates an aggregate file from all song file (h5 files)'
    print 'in a given directory.'
    print 'Aggregate files contains many songs. and none of the arrays,'
    print ''
    print 'usage:'
    print '   python create_aggregate_file.py <H5 DIR> <OUTPUT.h5>'
    print 'PARAMS'
    print '   H5 DIR     - directory contains h5 files (subdirs are checked)'
    print '   OUTPUT.h5  - filename of the aggregate file to create'
    sys.exit(0)


if __name__ == '__main__':

    # help menu
    if len(sys.argv)<3:
        die_with_usage()

    # params
    maindir = sys.argv[1]
    output = sys.argv[2]

    # sanity checks
    if not os.path.isdir(maindir):
        print 'ERROR: directory',maindir,'does not exists.'
        sys.exit(0)
    if os.path.isfile(output):
        print 'ERROR: file',output,'exists, delete or provide a new filename.'
        sys.exit(0)

    # start time
    t1 = time.time()

    # get all h5 files
    allh5 = get_all_files(maindir,ext='.h5')
    print 'found',len(allh5),'H5 files.'

    # create aggregate file
    HDF5.create_aggregate_file(output,expectedrows=len(allh5),
                               summaryfile=False)
    print 'Aggregate file created, we start filling it.'

    # fill it
    h5 = HDF5.open_h5_file_append(output)
    HDF5.fill_hdf5_aggregate_file(h5,allh5,summaryfile=False)
    h5.close()

    # done!
    stimelength = str(datetime.timedelta(seconds=time.time()-t1))
    print 'Aggregated',len(allh5),'files in:',stimelength
    

########NEW FILE########
__FILENAME__ = create_summary_file
"""
Thierry Bertin-Mahieux (2011) Columbia University
tb2332@columbia.edu

This code creates a summary file, i.e. an HDF5 file that looks like song
files, except that it contains more than one song and no arrays
(beats, similar artists, tags, ...)

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.


Copyright 2011, Thierry Bertin-Mahieux

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import glob
import time
import datetime
import hdf5_utils as HDF5


def get_all_files(basedir,ext='.h5') :
    """
    From a root directory, go through all subdirectories
    and find all files with the given extension.
    Return all absolute paths in a list.
    """
    allfiles = []
    for root, dirs, files in os.walk(basedir):
        files = glob.glob(os.path.join(root,'*'+ext))
        for f in files :
            allfiles.append( os.path.abspath(f) )
    return allfiles


def die_with_usage():
    """ HELP MENU """
    print 'create_summary_file.py'
    print '   by T. Bertin-Mahieux (2011) Columbia University'
    print '   tb2332@columbia.edu'
    print ''
    print 'Creates a summary file from all song file (h5 files)'
    print 'in a given directory.'
    print 'Summary files contains many songs and none of the arrays,'
    print 'i.e. no beat/segment data, artist similarity, tags, ...'
    print ''
    print 'usage:'
    print '   python create_summary_file.py <H5 DIR> <OUTPUT.h5>'
    print 'PARAMS'
    print '   H5 DIR     - directory contains h5 files (subdirs are checked)'
    print '   OUTPUT.h5  - filename of the summary file to create'
    sys.exit(0)


if __name__ == '__main__':

    # help menu
    if len(sys.argv)<3:
        die_with_usage()

    # params
    maindir = sys.argv[1]
    output = sys.argv[2]

    # sanity checks
    if not os.path.isdir(maindir):
        print 'ERROR: directory',maindir,'does not exists.'
        sys.exit(0)
    if os.path.isfile(output):
        print 'ERROR: file',output,'exists, delete or provide a new filename.'
        sys.exit(0)

    # start time
    t1 = time.time()

    # get all h5 files
    allh5 = get_all_files(maindir,ext='.h5')
    print 'found',len(allh5),'H5 files.'

    # create summary file
    HDF5.create_aggregate_file(output,expectedrows=len(allh5),
                               summaryfile=True)
    print 'Summary file created, we start filling it.'

    # fill it
    h5 = HDF5.open_h5_file_append(output)
    HDF5.fill_hdf5_aggregate_file(h5,allh5,summaryfile=True)
    h5.close()

    # done!
    stimelength = str(datetime.timedelta(seconds=time.time()-t1))
    print 'Summarized',len(allh5),'files in:',stimelength
    

########NEW FILE########
__FILENAME__ = dataset_creator
"""
Thierry Bertin-Mahieux (2010) Columbia University
tb2332@columbia.edu

This code contains code used when creating the actual MSong dataset,
i.e. functions to create a song HDF5 at the right place, with proper
locks for multithreading.

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.


Copyright 2010, Thierry Bertin-Mahieux

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import glob
import copy
import time
from Queue import Queue   # from 'queue' in python 3.0
import shutil
import urllib2
import multiprocessing
import numpy.random as npr
try:
    import hdf5_utils as HDF5
except ImportError:
    pass # will be imported in command line

# pyechonest objects
import pyechonest
import pyechonest.config
pyechonest.config.CALL_TIMEOUT=30 # instead of 10 seconds
from pyechonest import artist as artistEN
from pyechonest import song as songEN
from pyechonest import track as trackEN
CATALOG='7digital'
try:
    _api_dev_key = os.environ['ECHO_NEST_API_KEY']
except KeyError:
    _api_dev_key = os.environ['ECHONEST_API_KEY']
# posgresql import and info for musicbrainz dataset
MBUSER='gordon'
MBPASSWD='gordon'

# HOW LONG DO WE WAIT WHEN SOMETHING GOES WRONG
SLEEPTIME=15 # in seconds

# total number of files in the dataset, should be 1M
TOTALNFILES=1000000

# CAL 500 artist and song txt file
CAL500='https://github.com/tb2332/MSongsDB/raw/master/PythonSrc/DatasetCreation/cal500_artist_song.txt'

# lock to access the set of tracks being treated
# getting a track on the lock means having put the EN id
# of that track in the set TRACKSET
# use: get_lock_song
#      release_lock_song
TRACKSET_LOCK = multiprocessing.Lock()
TRACKSET_CLOSED = multiprocessing.Value('b')
TRACKSET_CLOSED = False # use to end the process, nothing can get a
                        # track lock if this is turn to True
CREATION_CLOSED = multiprocessing.Value('b')
CREATION_CLOSED = False # use to end all threads at a higher level
                        # than trackset closed, it is more a matter
                        # of printing and returning than the risk of
                        # creating a corrupted file
                        
class my_trackset():
    """
    class works with multiprocessing
    should look like a set from outside
    """
    def __init__(self):
        array_length = 10
        self.ar = multiprocessing.Array('l',array_length) # l for long, i not enough
        for k in range(len(self.ar)):
            self.ar[k] = 0
    def remove(self,obj):
        objh = hash(obj)
        for k in range(len(self.ar)):
            if self.ar[k] == objh:
                self.ar[k] = 0
                return
        print 'ERROR: my_trackset, tried to remove inexisting element, obj=',obj,'and hash=',objh
    def add(self,obj):
        objh = hash(obj)
        for k in range(len(self.ar)):
            if self.ar[k] == 0:
                self.ar[k] = objh
                return
        print 'ERROR: shared memory trackset full!!! fake a keyboardinterrupt to stop'
        raise KeyboardInterrupt
    def __contains__(self,obj):
        return hash(obj) in self.ar
    def __str__(self):
        return str(list(self.ar))
# instanciate object for trackset
TRACKSET=my_trackset()

def close_creation():
    """
    Function to use to help stop all processes in a clean way.
    It is usefull because of multithreading: only one thread
    will get the keyboard interrupt, this function tries to
    propagate the info
    """
    close_trackset()
    global CREATION_CLOSED
    CREATION_CLOSED = True
    

def close_trackset():
    """
    When terminating the thread, nothing can add anything
    to TRACKSET anymore
    """
    global TRACKSET_CLOSED
    TRACKSET_CLOSED = True

def get_lock_track(trackid):
    """
    Get the lock for the creation of one particular file
    Returns True if you got, False otherwise (meaning
    someone else just got it
    This is a blocking call.
    """
    got_lock = TRACKSET_LOCK.acquire() # blocking by default
    if not got_lock:
        print 'ERROR: could not get TRACKSET_LOCK locked?'
        return False
    if TRACKSET_CLOSED:
        TRACKSET_LOCK.release()
        print 'RELEASED LOCK BECAUSE TRACKSET_CLOSED'
        return False
    if trackid in TRACKSET:
        TRACKSET_LOCK.release()
        return False
    TRACKSET.add( trackid )
    TRACKSET_LOCK.release()
    return True

def release_lock_track(trackid):
    """
    Release the lock for the creation of one particular file.
    Should always return True, unless there is a problem
    Releasing a song that you don't have the lock on is dangerous.
    """
    got_lock = TRACKSET_LOCK.acquire() # blocking by default
    if not got_lock:
        print 'ERROR: could not get TRACKSET_LOCK lock?'
        return False
    if TRACKSET_CLOSED:
        TRACKSET_LOCK.release()
        print 'RELEASED LOCK BECAUSE TRACKSET_CLOSED, track=',trackid
        return False
    if not trackid in TRACKSET:
        TRACKSET_LOCK.release()
        print 'WARNING: releasing a song you dont own, trackid=',trackid;sys.stdout.flush()
        return False
    TRACKSET.remove(trackid)
    TRACKSET_LOCK.release()
    return True
        

def path_from_trackid(trackid):
    """
    Returns the typical path, with the letters[2-3-4]
    of the trackid (starting at 0), hence a song with
    trackid: TRABC1839DQL4H... will have path:
    A/B/C/TRABC1839DQL4H....h5
    """
    p = os.path.join(trackid[2],trackid[3])
    p = os.path.join(p,trackid[4])
    p = os.path.join(p,trackid+'.h5')
    return p


def count_h5_files(basedir):
    """
    Return the number of hdf5 files contained in all
    subdirectories of base
    """
    cnt = 0
    try:
        for root, dirs, files in os.walk(basedir):
            files = glob.glob(os.path.join(root,'*.h5'))
            cnt += len(files)
        return cnt
    except (IOError,OSError),e:
        print 'ERROR:',e,'in count_h5_files, return 0'
        return 0

def create_track_file(maindir,trackid,track,song,artist,mbconnect=None):
    """
    Main function to create an HDF5 song file.
    You got to have the track, song and artist already.
    If you pass an open connection to the musicbrainz database, we also use it.
    Returns True if song was created, False otherwise.
    False can mean another thread is already doing that song.
    We also check whether the path exists.
    INPUT
       maindir      - main directory of the Million Song Dataset
       trackid      - Echo Nest track id of the track object
       track        - pyechonest track object
       song         - pyechonest song object
       artist       - pyechonest artist object
       mbconnect    - open musicbrainz pg connection
    RETURN
       True if a track file was created, False otherwise
    """
    hdf5_path = os.path.join(maindir,path_from_trackid(trackid))
    if os.path.exists( hdf5_path ):
        return False # file already exists, no stress
    hdf5_path_tmp = hdf5_path + '_tmp'
    # lock the file
    got_lock = get_lock_track(trackid)
    if not got_lock:
        return False # someone is taking care of that file
    if os.path.exists( hdf5_path ):
        release_lock_track(trackid)
        return False # got the lock too late, file exists
    # count errors (=tries), stop after 100 tries
    try_cnt = 0
    # create file and fill it
    try:
        while True: # try until we make it work!
            try:
                # we try one more time
                try_cnt += 1
                if not os.path.isdir( os.path.split(hdf5_path)[0] ):
                    os.makedirs( os.path.split(hdf5_path)[0] )
                # check / delete tmp file if exist
                if os.path.isfile(hdf5_path_tmp):
                    os.remove(hdf5_path_tmp)
                # create tmp file
                HDF5.create_song_file(hdf5_path_tmp)
                h5 = HDF5.open_h5_file_append(hdf5_path_tmp)
                HDF5.fill_hdf5_from_artist(h5,artist)
                HDF5.fill_hdf5_from_song(h5,song)
                HDF5.fill_hdf5_from_track(h5,track)
                if mbconnect is not None:
                    HDF5.fill_hdf5_from_musicbrainz(h5,mbconnect)
                # TODO billboard? lastfm? ...?
                h5.close()
            except KeyboardInterrupt:
                close_creation()
                raise
            # we dont panic, delete file, wait and retry
            except Exception as e:
                # close hdf5
                try:
                    h5.close()
                except NameError,ValueError:
                    pass
                # delete path
                try:
                    os.remove( hdf5_path_tmp )
                except IOError:
                    pass
                # print and wait
                print 'ERROR creating track:',trackid,'on',time.ctime(),'(pid='+str(os.getpid())+')'
                print e
                if try_cnt < 100:
                    print '(try again in',SLEEPTIME,'seconds)'
                    time.sleep(SLEEPTIME)
                    continue
                # give up
                else:
                    print 'we give up after',try_cnt,'tries'
                    release_lock_track(trackid)
                    return False
            # move tmp file to real file
            shutil.move(hdf5_path_tmp, hdf5_path)
            # release lock
            release_lock_track(trackid)
            break
    # KeyboardInterrupt, we delete file, clean things up
    except KeyboardInterrupt:
        # close hdf5
        try:
            h5.close()
        except NameError,ValueError:
            pass
        # delete path
        try:
            if os.path.isfile( hdf5_path_tmp ):
                os.remove( hdf5_path_tmp )
            if os.path.isfile( hdf5_path ):
                os.remove( hdf5_path )
        except IOError:
            pass
        raise
    except (IOError,OSError),e:
        print 'GOT Error',e,'deep deep in creation process, threading problem?'
        raise
    # IF WE GET HERE WE'RE GOOD
    return True



def create_track_file_from_trackid(maindir,trackid,song,artist,mbconnect=None):
    """
    Get a track from a track id and calls for its creation.
    We assume we already have song and artist.
    We can have a connection to musicbrainz as an option.
    This function should create only one file!
    GOAL: mostly, it checks if we have the track already created before
          calling EchoNest API. It saves some calls/time
          Also, handles some errors.
    INPUT
        maindir    - MillionSongDataset root directory
        trackid    - Echo Nest track ID (string: TRABC.....)
        song       - pyechonest song object for that track
        artist     - pyechonest artist object for that song/track
        mbconnect  - open musicbrainz pg connection
    RETURN
        true if a song file is created, false otherwise
    """
    # CLOSED CREATION?
    if CREATION_CLOSED:
        return False
    # do we already have this track in the dataset?
    track_path = os.path.join(maindir,path_from_trackid(trackid))
    if os.path.exists(track_path):
        return False
    # get that track!
    try_cnt = 0
    while True:
        try:
            try_cnt += 1
            track = trackEN.track_from_id(trackid)
            break
        except KeyboardInterrupt:
            close_creation()
            raise
        except urllib2.HTTPError,e:
            print type(e),':',e
            print 'we dont retry for that error, trackid=',trackid,'(pid='+str(os.getpid())+')'
            return False
        except Exception,e:
            print type(e),':',e
            print 'at time',time.ctime(),'in create_track_file_from_trackid, tid=',trackid,'(we wait',SLEEPTIME,'seconds) (pid='+str(os.getpid())+')'
            if try_cnt < 50:
                time.sleep(SLEEPTIME)
                continue
            else:
                print 'we give up after',try_cnt,'tries.'
                return False
    # we have everything, launch create track file
    res = create_track_file(maindir,trackid,track,song,artist,mbconnect=mbconnect)
    return res



def create_track_file_from_song(maindir,song,artist,mbconnect=None):
    """
    Get tracks from a song, choose the first one and calls for its creation.
    We assume we already have song and artist.
    We can have a connection to musicbrainz as an option.
    This function should create only one file!
    GOAL: handles some errors.
    INPUT
        maindir    - MillionSongDataset root directory
        song       - pyechonest song object for that track
        artist     - pyechonest artist object for that song/track
        mbconnect  - open musicbrainz pg connection
    RETURN
        true if a song file is created, false otherwise
    """
    # CLOSED CREATION?
    if CREATION_CLOSED:
        return False
    # get that track id
    while True:
        try:
            tracks = song.get_tracks(CATALOG)
            trackid = tracks[0]['id']
            break
        except (IndexError, TypeError),e:
            return False # should not happen according to EN guys, but still does...
        except TypeError,e:
            print 'ERROR:',e,' something happened that should not, song.id =',song.id,'(pid='+str(os.getpid())+')'
            return False # should not happen according to EN guys, but still does...
        except KeyboardInterrupt:
            close_creation()
            raise
        except Exception,e:
            print type(e),':',e
            print 'at time',time.ctime(),'in create_track_file_from_song, sid=',song.id,'(we wait',SLEEPTIME,'seconds) (pid='+str(os.getpid())+')'
            time.sleep(SLEEPTIME)
            continue
    # we got the track id, call for its creation
    # if a file for that trackid already exists, it will be caught immediately in the next function
    res = create_track_file_from_trackid(maindir,trackid,song,artist,mbconnect=mbconnect)
    return res


def create_track_file_from_song_noartist(maindir,song,mbconnect=None):
    """
    After getting the artist, get tracks from a song, choose the first one and calls for its creation.
    We assume we already have a song.
    We can have a connection to musicbrainz as an option.
    This function should create only one file!
    GOAL: handles some errors.
    INPUT
        maindir    - MillionSongDataset root directory
        song       - pyechonest song object for that track
        mbconnect  - open musicbrainz pg connection
    RETURN
        true if a song file is created, false otherwise
    """
    # CLOSED CREATION?
    if CREATION_CLOSED:
        return False
    # get that artist
    while True:
        try:
            artist = artistEN.Artist(song.artist_id)
            break
        except KeyboardInterrupt:
            close_creation()
            raise
        except pyechonest.util.EchoNestAPIError,e:
            print 'MAJOR ERROR, wrong artist id?'
            print e # means the ID does not exist
            return False
        except Exception,e:
            print type(e),':',e
            print 'at time',time.ctime(),'in create_track_files_from_song_noartist, sid=',song.id,'(we wait',SLEEPTIME,'seconds) (pid='+str(os.getpid())+')'
            time.sleep(SLEEPTIME)
            continue
    # get his songs, creates his song files, return number of actual files created
    return create_track_file_from_song(maindir,song,artist,mbconnect=mbconnect)


def create_track_files_from_artist(maindir,artist,mbconnect=None,maxsongs=100):
    """
    Get all songs from an artist, for each song call for its creation
    We assume we already have artist.
    We can have a connection to musicbrainz as an option.
    This function should create only one file!
    GOAL: handles some errors.
    INPUT
        maindir    - MillionSongDataset root directory
        artist     - pyechonest artist object for that song/track
        mbconnect  - open musicbrainz pg connection
        maxsongs   - maximum number of files retrieved, default=100, should be 500 or 1k
    RETURN
        number fo files created, 0<=...<=1000?
    """
    assert maxsongs <= 1000,'dont think we can query for more than 1K songs per artist'
    if maxsongs==100:
        #print 'WARNING,create_track_files_from_artist, start param should be implemented'
        pass
    # get all the songs we want
    allsongs = []
    while True:
        try:
            n_missing = maxsongs - len(allsongs)
            n_askfor = min(n_missing,100)
            start = len(allsongs)
            songs = songEN.search(artist_id=artist.id, buckets=['id:'+CATALOG, 'tracks', 'audio_summary',
                                                                'artist_familiarity','artist_hotttnesss',
                                                                'artist_location','song_hotttnesss'],
                                  limit=True, results=n_askfor)
            allsongs.extend(songs)
            if len(allsongs) >= maxsongs or len(songs) < n_askfor:
                break
            print 'WARNING tracks from artists, we cant search for more than 100 songs for the moment (pid='+str(os.getpid())+')'
            break # we have not implemented the start yet
        except KeyboardInterrupt:
            close_creation()
            raise
        except pyechonest.util.EchoNestAPIError,e:
            if str(e)[:21] == 'Echo Nest API Error 5': # big hack, wrong artist ID
                print 'SKIPPING ARTIST',artist.id,'FOR NONEXISTENCE'
                return 0
            else:
                print type(e),':',e
                print 'at time',time.ctime(),'in create_track_file_from_artist, aid=',artist.id,'(we wait',SLEEPTIME,'seconds) (pid='+str(os.getpid())+')'
                time.sleep(SLEEPTIME)
                continue
        except Exception,e:
            print type(e),':',e
            print 'at time',time.ctime(),'in create_track_files_from_artist, aid=',artist.id,'(we wait',SLEEPTIME,'seconds) (pid='+str(os.getpid())+')'
            time.sleep(SLEEPTIME)
            continue
    # shuffle the songs, to help multithreading
    npr.shuffle(allsongs)
    # iterate over the songs, call for their creation, count how many actually created
    cnt_created = 0
    for song in allsongs:
        # CLOSED CREATION?
        if CREATION_CLOSED:
            return cnt_created
        # create
        created = create_track_file_from_song(maindir,song,artist,mbconnect=mbconnect)
        if created:
            cnt_created += 1
    # done
    return cnt_created
    

def create_track_files_from_artistid(maindir,artistid,mbconnect=None,maxsongs=100):
    """
    Get an artist from its ID, get all his songs, for each song call for its creation
    We assume we already have artist ID.
    We can have a connection to musicbrainz as an option.
    This function should create only one file!
    GOAL: handles some errors.
    INPUT
        maindir    - MillionSongDataset root directory
        artistid   - echonest artist id
        mbconnect  - open musicbrainz pg connection
        maxsongs   - maximum number of files retrieved, default=100, should be 500 or 1k
    RETURN
        number fo files created, 0<=...<=1000?
    """
    assert maxsongs <= 1000,'dont think we can query for more than 1K songs per artist'
    # get that artist
    while True:
        try:
            artist = artistEN.artist(artistid)
            break
        except KeyboardInterrupt:
            close_creation()
            raise
        except pyechonest.util.EchoNestAPIError,e:
            print 'MAJOR ERROR, wrong artist id?',artistid
            print e # means the ID does not exist
            return 0
        except Exception,e:
            print type(e),':',e
            print 'at time',time.ctime(),'in create_track_files_from_artistid, aid=',artistid,'(we wait',SLEEPTIME,'seconds) (pid='+str(os.getpid())+')'
            time.sleep(SLEEPTIME)
            continue

    # CLOSED CREATION?
    if CREATION_CLOSED:
        return 0
    # get his songs, creates his song files, return number of actual files created
    return create_track_files_from_artist(maindir,artist,mbconnect=mbconnect,maxsongs=maxsongs)    




def get_top_terms(nresults=1000):
    """
    Get the top terms from the Echo Nest, up to 1000
    """
    assert nresults <= 1000,'cannot ask for more than 1000 top terms'
    url = "http://developer.echonest.com/api/v4/artist/top_terms?api_key="
    url += _api_dev_key + "&format=json&results=" + str(nresults)
    # get terms
    while True:
        try:
            f = urllib2.urlopen(url,timeout=60.)
            response = eval( f.readline() )
            if response['response']['status']['message'] != 'Success':
                print 'EN response failure at time',time.ctime(),'in get_top_terms (we wait',SLEEPTIME,'seconds)'
                time.sleep(SLEEPTIME)
                continue
            break
        except (KeyboardInterrupt,NameError):
            close_creation()
            raise
        except Exception,e:
            print type(e),':',e
            print 'at time',time.ctime(),'in get_top_terms (we wait',SLEEPTIME,'seconds)'
            time.sleep(SLEEPTIME)
            continue
    # parse, return
    term_pairs = response['response']['terms']
    terms = map(lambda x: x['name'],term_pairs)
    if len(terms) != nresults:
        print 'WARNING: asked for',nresults,'top terms from EN, got',len(terms)
    return terms


FAMILIARARTISTS_LOCK = multiprocessing.Lock()
def get_most_familiar_artists(nresults=100):
    """
    Get the most familiar artists according to the Echo Nest
    """
    assert nresults <= 100,'we cant ask for more than 100 artists at the moment'
    locked = FAMILIARARTISTS_LOCK.acquire()
    assert locked,'FAMILIARARTISTS_LOCK could not lock?'
    # get top artists
    while True:
        try:
            artists = artistEN.search(sort='familiarity-desc',results=nresults,
                                      buckets=['familiarity','hotttnesss','terms',
                                               'id:musicbrainz','id:7digital','id:playme'])
            break
        except KeyboardInterrupt:
            close_creation()
            raise
        except Exception,e:
            print type(e),':',e
            print 'at time',time.ctime(),'in get_most_familiar_artists (we wait',SLEEPTIME,'seconds)'
            time.sleep(SLEEPTIME)
            continue
    # done
    FAMILIARARTISTS_LOCK.release()
    return artists


def search_songs(**args):
    """
    Use the Search song API, wrapped in our usual error handling
    try/except. All the args are passed toward songEN.search,
    if there is an error... good luck!
    Note that this implies we only look once, so not good for the step param if
    implemented (or you must call that function again)
    RETURN list of songs, can be empty
    """
    while True:
        try:
            songs = songEN.search(**args)
            break
        except (KeyboardInterrupt,NameError):
            close_creation()
            raise
        except Exception,e:
            print type(e),':',e
            print 'at time',time.ctime(),'in search songs [params='+str(args)+'] (we wait',SLEEPTIME,'seconds)'
            time.sleep(SLEEPTIME)
            continue
    # done
    return songs


def get_artists_from_description(description,nresults=100):
    """
    Return artists given a string description,
    for instance a tag.
    """
    assert nresults <= 100,'we cant do more than 100 artists for the moment...'
    # get the artists for that description
    while True:
        try:
            artists = artistEN.search(description=description,sort='familiarity-desc',results=nresults,
                                      buckets=['familiarity','hotttnesss','terms','id:musicbrainz','id:7digital','id:playme'])
            break
        except (KeyboardInterrupt,NameError):
            close_creation()
            raise
        except Exception,e:
            print type(e),':',e
            print 'at time',time.ctime(),'in get_artistids_from_description (we wait',SLEEPTIME,'seconds)'
            time.sleep(SLEEPTIME)
            continue
    # done
    return artists


def get_similar_artists(artist):
    """
    Get the list of similar artists from a target one, might be empty
    """
    while True:
        try:
            similars = artist.get_similar()
            break
        except (KeyboardInterrupt,NameError):
            close_creation()
            raise
        except pyechonest.util.EchoNestAPIError,e:
            if str(e)[:21] == 'Echo Nest API Error 5': # big hack, wrong artist ID
                print 'SKIPPING ARTIST',artist.id,'FOR NONEXISTENCE'
                return []
            else:
                print type(e),':',e
                print 'at time',time.ctime(),'in get_similar_artists from aid =',artist.id,'(we wait',SLEEPTIME,'seconds)'
                time.sleep(SLEEPTIME)
                continue
        except Exception,e:
            print type(e),':',e
            print 'at time',time.ctime(),'in get_similar_artists from aid =',artist.id,'(we wait',SLEEPTIME,'seconds)'
            time.sleep(SLEEPTIME)
            continue
    # done
    return similars


def get_artist_song_from_names(artistname,songtitle):
    """
    Get an artist and a song from their artist name and title,
    return the two: artist,song or None,None if problem
    """
    while True:
        try:
            songs = songEN.search(artist=artistname,
                                  title=songtitle,results=1,
                                  buckets=['artist_familiarity',
                                           'artist_hotttnesss',
                                           'artist_location',
                                           'tracks',
                                           'id:musicbrainz',
                                           'id:7digital','id:playme'])
            break
        except (KeyboardInterrupt,NameError,TypeError):
            close_creation()
            raise
        except Exception,e:
            print type(e),':',e
            print 'at time',time.ctime(),'in get_artist_song_from_names (we wait',SLEEPTIME,'seconds)'
            time.sleep(SLEEPTIME)
            continue
    # sanity checks
    if len(songs) == 0:
        print 'no song found for:',artistname,'(',songtitle,')'
        return None,None
    if CREATION_CLOSED:
        return None, None
    # get artist
    song = songs[0]
    while True:
        try:
            artist = artistEN.Artist(song.artist_id)
            break
        except KeyboardInterrupt:
            close_creation()
            raise
        except pyechonest.util.EchoNestAPIError,e:
            print 'MAJOR ERROR, wrong artist id?',song.artist_id
            print e # means the ID does not exist
            return None,None
        except Exception,e:
            print type(e),':',e
            print 'at time',time.ctime(),'in get_artist_song_from_names, aid=',song.artist_id,'(we wait',SLEEPTIME,'seconds)'
            time.sleep(SLEEPTIME)
            continue
    # done
    return artist,song
    

def create_step10(maindir,mbconnect=None,maxsongs=500,nfilesbuffer=0,verbose=0):
    """
    Most likely the first step to the databse creation.
    Get artists from the EchoNest based on familiarity
    INPUT
       maindir       - MillionSongDataset main directory
       mbconnect     - open musicbrainz pg connection
       maxsongs      - max number of songs per artist
       nfilesbuffer  - number of files to leave when we reach the M songs,
                       e.g. we stop adding new ones if there are more
                            than 1M-nfilesbuffer already 
    RETURN
       number of songs actually created
    """
    # get all artists ids
    artists = get_most_familiar_artists(nresults=100)
    # shuffle them
    npr.shuffle(artists)
    # for each of them create all songs
    cnt_created = 0
    for artist in artists:
        # CLOSED CREATION?
        if CREATION_CLOSED:
            break
        if verbose>0: print 'doing artist:',artist; sys.stdout.flush()
        cnt_created += create_track_files_from_artist(maindir,artist,
                                                      mbconnect=mbconnect,
                                                      maxsongs=maxsongs)
        t1 = time.time()
        nh5 = count_h5_files(maindir)
        t2 = time.time()
        print 'found',nh5,'h5 song files in',maindir,'in',int(t2-t1),'seconds (pid='+str(os.getpid())+')'; sys.stdout.flush()
        # sanity stop
        if nh5 > TOTALNFILES - nfilesbuffer:
            return cnt_created
    # done
    return cnt_created


def create_step20(maindir,mbconnect=None,maxsongs=500,nfilesbuffer=0,verbose=0):
    """
    Get artists based on most used Echo Nest terms. Encode all their
    songs (up to maxsongs)
    INPUT
       maindir       - MillionSongDataset main directory
       mbconnect     - open musicbrainz pg connection
       maxsongs      - max number of songs per artist
       nfilesbuffer  - number of files to leave when we reach the M songs,
                       e.g. we stop adding new ones if there are more
                            than 1M-nfilesbuffer already
       verbose       - tells which term and artist is being done
    RETURN
       number of songs actually created
    """
    # get all terms
    most_used_terms = get_top_terms(nresults=1000)
    most_used_terms = most_used_terms[:200]
    npr.shuffle(most_used_terms)
    if verbose>0: print 'most used terms retrievend, got',len(most_used_terms)
    # keep in mind artist ids we have done already
    done_artists = set()
    # for each term, find all artists then create all songs
    # keep a list of artist id so we don't do one artist twice
    cnt_created = 0
    for termid,term in enumerate(most_used_terms):
        # CLOSED CREATION?
        if CREATION_CLOSED:
            return cnt_created
        # verbose
        print 'doing term',termid,'out of',len(most_used_terms),'(pid='+str(os.getpid())+')'; sys.stdout.flush()
        # get all artists from that term as a description
        artists = get_artists_from_description(term,nresults=100)
        npr.shuffle(artists)
        for artist in artists:
            # CLOSED CREATION?
            if CREATION_CLOSED:
                return cnt_created
            # check if this artists has been done
            if artist.id in done_artists:
                continue
            done_artists.add(artist.id)
            # create all his tracks
            if verbose>0: print 'doing artist:',artist.name,'(term =',term,')'
            cnt_created += create_track_files_from_artist(maindir,artist,
                                                          mbconnect=mbconnect,
                                                          maxsongs=maxsongs)
            # sanity stop
            nh5 = count_h5_files(maindir)
            print 'found',nh5,'h5 song files in',maindir,'(pid='+str(os.getpid())+')'; sys.stdout.flush()
            if nh5 > TOTALNFILES - nfilesbuffer:
                return cnt_created
    # done
    return cnt_created


def create_step30(maindir,mbconnect=None,maxsongs=500,nfilesbuffer=0):
    """
    Get artists and songs from the CAL500 dataset.
    First search for a particular pair artist/song, then from
    that artist, get all possible songs (up to maxsongs)
    We assume the file 'cal500_artist_song.txt' is in CAL500 param
    which is an online URL (to github probably)
    INPUT
       maindir       - MillionSongDataset main directory
       mbconnect     - open musicbrainz pg connection
       maxsongs      - max number of songs per artist
       nfilesbuffer  - number of files to leave when we reach the M songs,
                       e.g. we stop adding new ones if there are more
                            than 1M-nfilesbuffer already
       verbose       - tells which term and artist is being done
    RETURN
       number of songs actually created
    """
    # get the txt file, get the lines
    while True:
        try:
            f = urllib2.urlopen(CAL500)
            lines = f.readlines()
            f.close()
            lines[499] # sanity check, get IndexError if something's wrong
            break
        except KeyboardInterrupt:
            close_creation()
            raise
        except IndexError, e:
            print type(e),':',e
            print 'at time',time.ctime(),'in step20 retrieving CAL500 - response too short! (we wait',SLEEPTIME,'seconds)'
            time.sleep(SLEEPTIME)
            continue
        except Exception,e:
            print type(e),':',e
            print 'at time',time.ctime(),'in step20 retrieving CAL500 (we wait',SLEEPTIME,'seconds)'
            time.sleep(SLEEPTIME)
            continue
    lines = map(lambda x:x.strip(),lines)
    npr.shuffle(lines)
    # get song specifically, then all songs for the artist
    cnt_created = 0
    for lineid,line in enumerate(lines):
        if CREATION_CLOSED:
            return cnt_created
        # sanity stop
        nh5 = count_h5_files(maindir)
        print 'found',nh5,'h5 song files in',maindir; sys.stdout.flush()
        if nh5 > TOTALNFILES - nfilesbuffer:
            return cnt_created
        # verbose
        print 'doing line',lineid,'out of',len(lines),'(pid='+str(os.getpid())+')'; sys.stdout.flush()
        # parse line
        artiststr = line.split('<SEP>')[0]
        songstr = line.split('<SEP>')[1]
        # artist and song
        artist,song = get_artist_song_from_names(artistname=artiststr,
                                                 songtitle=songstr)
        if artist is None or song is None:
            continue
        # create file for that song
        if CREATION_CLOSED:
            return cnt_created
        created = create_track_file_from_song(maindir,song,artist,
                                              mbconnect=mbconnect)
        if created: cnt_created += 1
        # create files for that artist
        if CREATION_CLOSED:
            return cnt_created
        cnt_created += create_track_files_from_artist(maindir,artist,
                                                      mbconnect=mbconnect)
    # done with step 30
    return cnt_created


def create_step40(maindir,mbconnect=None,maxsongs=100,nfilesbuffer=0):
    """
    Search for songs with different attributes, danceability, energy, ...
    INPUT
       maindir       - root directory of the Million Song dataset
       mbconnect     - open pg connection to Musicbrainz
       maxsongs      - max number of song per search (max=100)
       nfilesbuffer  - number of files we leave unfilled in the dataset
    RETURN
       the number of songs actually created
    """
    assert maxsongs <= 100,'create_step40, cannot search for more than 100 songs'
    # list all the args
    types_of_sorts = ['tempo-asc', 'duration-asc', 'loudness-asc', 'artist_hotttnesss-asc', 'song_hotttnesss-asc',
                      'latitude-asc', 'longitude-asc', 'mode-asc', 'key-asc', 'tempo-desc', 'duration-desc',
                      'loudness-desc', 'artist_hotttnesss-desc', 'song_hotttnesss-desc', 'latitude-desc',
                      'longitude-desc', 'mode-desc', 'key-desc', 'energy-asc', 'energy-desc',
                      'danceability-asc', 'danceability-desc']
    all_args = []
    for tsort in types_of_sorts:
        args = {'sort':tsort, 'results':maxsongs}
        args['buckets'] = ['artist_familiarity','artist_hotttnesss','artist_location',
                           'tracks','id:musicbrainz','id:7digital','id:playme']
        args['limit'] = True
        all_args.append(args)
    npr.shuffle(all_args)
    # iterate over set of args
    cnt_created = 0
    for argsid,args in enumerate(all_args):
        # sanity stops
        if CREATION_CLOSED:
            return cnt_created
        nh5 = count_h5_files(maindir)
        print 'found',nh5,'h5 song files in',maindir; sys.stdout.flush()
        if nh5 > TOTALNFILES - nfilesbuffer:
            return cnt_created
        # verbose
        print 'doing search args',argsid,'out of',len(all_args),'(pid='+str(os.getpid())+')'; sys.stdout.flush()
        # songs
        songs = search_songs(**args)
        if len(songs) == 0:
            continue
        for song in songs:
            cnt_created += create_track_file_from_song_noartist(maindir,
                                                                song,
                                                                mbconnect=mbconnect)
    # done
    return cnt_created


def create_step60(maindir,mbconnect=None,maxsongs=100,nfilesbuffer=0):
    """
    Makes sure we have the similar artists to the top 100 most familiar
    artists, and then go on with more similar artists.
    INPUT
       maindir       - root directory of the Million Song dataset
       mbconnect     - open pg connection to Musicbrainz
       maxsongs      - max number of song per search (max=100)
       nfilesbuffer  - number of files we leave unfilled in the dataset
    RETURN
       the number of songs actually created
    """
    # will contain artists TID that are done or already in the queue
    artists_done = set()
    # get all artists ids
    artist_queue = Queue()
    artists = get_most_familiar_artists(nresults=100)
    n_most_familiars = len(artists)
    npr.shuffle(artists)
    for a in artists:
        artists_done.add( a.id )
        artist_queue.put_nowait( a )
    # for each of them create all songs
    cnt_created = 0
    cnt_artists = 0
    while not artist_queue.empty():
        artist = artist_queue.get_nowait()
        cnt_artists += 1
        # CLOSED CREATION?
        if CREATION_CLOSED:
            break
        if cnt_artists % 10 == 0:
            nh5 = count_h5_files(maindir)
            print 'found',nh5,'h5 song files in',maindir; sys.stdout.flush()
            if nh5 > TOTALNFILES - nfilesbuffer:
                return cnt_created
        # verbose
        print 'doing artist',cnt_artists,'(pid='+str(os.getpid())+')'; sys.stdout.flush()
        # encode that artist unless it was done in step10
        #if cnt_artists > n_most_familiars:
        # we had to relaunch this function, lets not redo all the same artists over and over
        if cnt_artists > 1000:
            cnt_created += create_track_files_from_artist(maindir,artist,
                                                          mbconnect=mbconnect,
                                                          maxsongs=maxsongs)
        # get similar artists, add to queue
        similars = get_similar_artists(artist)
        if len(similars) == 0: continue
        npr.shuffle(similars)
        similars = similars[:10] # we keep 10 at random, the radius of artists grows faster
                                 # the thread dont redo the same artists over and over
                                 # too bad for the artists we miss (if any...)
        for a in similars:
            if a.id in artists_done:
                continue
            artists_done.add(a.id)
            artist_queue.put_nowait(a)
    return cnt_created


# error passing problems
class KeyboardInterruptError(Exception):pass

# for multiprocessing
def run_steps_wrapper(args):
    """ wrapper function for multiprocessor, calls run_steps """
    run_steps(**args)

def run_steps(maindir,nomb=False,nfilesbuffer=0,startstep=0,onlystep=-1,idxthread=0):
    """
    Main function to run the different steps of the dataset creation.
    Each thread should be initialized by calling this function.
    INPUT
       maindir       - main directory of the Million Song Dataset
       nomb          - if True, don't use musicbrainz
       nfilesbuffer  -
    """
    print 'run_steps is launched on dir:',maindir
    # sanity check
    assert os.path.isdir(maindir),'maindir: '+str(maindir)+' does not exist'
    # check onlystep and startstep
    if onlystep > -1:
        startstep = 9999999
    # set a seed for this process
    npr.seed(npr.randint(1000) + idxthread)
    # connect to musicbrainz
    if nomb:
        connect = None
    else:
        import pg
        connect = pg.connect('musicbrainz_db','localhost',-1,None,None,MBUSER,MBPASSWD)

    cnt_created = 0
    try:
        # step 10
        if startstep <= 10 or onlystep==10:
            cnt_created += create_step10(maindir,connect,maxsongs=100,nfilesbuffer=nfilesbuffer)
            if CREATION_CLOSED: startstep = onlystep = 999999
        # step 20
        if startstep <= 20 or onlystep==20:
            cnt_created += create_step20(maindir,connect,maxsongs=100,nfilesbuffer=nfilesbuffer)
            if CREATION_CLOSED: startstep = onlystep = 999999
        # step 30
        if startstep <= 30 or onlystep==30:
            cnt_created += create_step30(maindir,connect,maxsongs=100,nfilesbuffer=nfilesbuffer)
            if CREATION_CLOSED: startstep = onlystep = 999999
        # step 40
        if startstep <= 40 or onlystep==40:
            cnt_created += create_step40(maindir,connect,maxsongs=100,nfilesbuffer=nfilesbuffer)
            if CREATION_CLOSED: startstep = onlystep = 999999
        # step 60
        if startstep <= 60 or onlystep==60:
            cnt_created += create_step60(maindir,connect,maxsongs=50,nfilesbuffer=nfilesbuffer)
            if CREATION_CLOSED: startstep = onlystep = 999999
    except KeyboardInterrupt:
        close_creation()
        time.sleep(5) # give time to other processes to end
        raise KeyboardInterruptError()
    finally:
        # done, close pg connection
        if not connect is None:
            connect.close()
        print 'run_steps terminating, at least',cnt_created,'files created'




def die_with_usage():
    """ HELP MENU """
    print 'dataset_creator.py'
    print '    by T. Bertin-Mahieux (2010) Columbia University'
    print '       tb2332@columbia.edu'
    print 'Download data from the EchoNest to create the MillionSongDataset'
    print 'usage:'
    print '   python dataset_creator.py [FLAGS] <maindir>'
    print 'FLAGS'
    print '  -nthreads n      - number of threads to use'
    print '  -nomb            - do not use musicbrainz'
    print '  -nfilesbuffer n  - each thread stop if there is less than that many files'
    print '                     left to be put in the Million Song dataset'
    print '  -t1nobuffer      - removes the filesbuffer for first thread'
    print '  -startstep n     - start at step >= n'
    print '  -onlystep n      - only do step n'
    print 'INPUT'
    print '   maindir  - main directory of the Million Song Dataset'
    sys.exit(0)


if __name__ == '__main__':

    # help menu
    if len(sys.argv) < 2:
        die_with_usage()

    # local imports
    sys.path.append(os.path.abspath(os.path.join(sys.argv[0],'../..')))
    import hdf5_utils as HDF5

    # flags
    nthreads = 1
    nomb = False
    nfilesbuffer = 1000
    t1nobuffer = False
    onlystep = -1
    startstep = 0
    while True:
        if sys.argv[1] == '-nthreads':
            nthreads = int(sys.argv[2])
            sys.argv.pop(1)
        elif sys.argv[1] == '-nomb':
            nomb = True
        elif sys.argv[1] == '-nfilesbuffer':
            nfilesbuffer = int(sys.argv[2])
            sys.argv.pop(1)
        elif sys.argv[1] == '-t1nobuffer':
            t1nobuffer = True
        elif sys.argv[1] == '-startstep':
            startstep = int(sys.argv[2])
            sys.argv.pop(1)
        elif sys.argv[1] == '-onlystep':
            onlystep = int(sys.argv[2])
            sys.argv.pop(1)
        else:
            break
        sys.argv.pop(1)

    # inputs
    maindir = sys.argv[1]

    # add params to dict
    params = {'maindir':maindir,
              'nomb':nomb,'nfilesbuffer':nfilesbuffer,
              'onlystep':onlystep,'startstep':startstep}


    # verbose
    print 'PARAMS:',params

    # LAUNCH THREADS
    params_list = []
    for k in range(nthreads):
        # params for one specific thread
        p = copy.deepcopy(params)
        # add thread id and deals with t1nobufer option
        p['idxthread'] = k
        if k == 0 and t1nobuffer:
            p['nfilesbuffer'] == 0
        params_list.append(p)
    # create pool, launch using the list of params
    # we underuse multiprocessing, we will have as many processes
    # as jobs needed
    pool = multiprocessing.Pool(processes=nthreads)
    try:
        pool.map(run_steps_wrapper, params_list)
        pool.close()
        pool.join()
    except KeyboardInterrupt:
        print 'MULTIPROCESSING'
        print 'stopping multiprocessing due to a keyboard interrupt'
        pool.terminate()
        pool.join()
    except Exception, e:
        print 'MULTIPROCESSING'
        print 'got exception: %r, terminating the pool' % (e,)
        pool.terminate()
        pool.join()

        
    
    

########NEW FILE########
__FILENAME__ = dataset_filestats
"""
Thierry Bertin-Mahieux (2010) Columbia University
tb2332@columbia.edu

This code is more of a sanitcy checks, it counts how many
leaves there are in the filesystem for the million songs,
thus making sure the track ID's are well-balance.
Also try to find the most recent files, in case we have
to delete some at the end.

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.


Copyright 2010, Thierry Bertin-Mahieux

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""


import os
import sys
import time
import glob
try:
    from Queue import PriorityQueue # from queue for Python 3.0
except ImportError:
    from queue import PriorityQueue # Python 3.0

# put in tuples likes -modifdate, fname
# highest priority = lowest first number
MODIFQUEUE = PriorityQueue()

# list of leaves ordered by number of files
# get filled up when we count leaves (by default)
MAP_NFILES_DIR = {}


def get_all_files(basedir,ext='.h5') :
    """
    From a root directory, go through all subdirectories
    and find all files with the given extension.
    Return all absolute paths in a list.
    """
    allfiles = []
    for root, dirs, files in os.walk(basedir):
        files = glob.glob(os.path.join(root,'*'+ext))
        for f in files :
            allfiles.append( os.path.abspath(f) )
    return allfiles


def count_normal_leaves(basedir,revindex=True):
    """
    Count how many directories are of the form
    basedir/A/B/C
    If revindex, we fill up MAP_NFILES_DIR where
    the keys are number of files, and the value is
    a set of directory filenames
    """
    cnt = 0
    for root, dirs, files in os.walk(basedir):
        level3up = os.path.abspath(os.path.join(root,'../../..'))
        if os.path.exists(level3up) and os.path.samefile(level3up,basedir):
            cnt += 1
            if revindex:
                nfiles = len(glob.glob(os.path.join(root,'*.h5')))
                if not nfiles in MAP_NFILES_DIR.keys():
                    MAP_NFILES_DIR[nfiles] = set()
                MAP_NFILES_DIR[nfiles].add(root)
    return cnt

def get_all_files_modif_date(basedir,ext='.h5'):
    """
    From a root directory, look at all the file,
    get their last modification date, put in in priority
    queue so the most recent file pop up first
    """
    for root, dirs, files in os.walk(basedir):
        files = glob.glob(os.path.join(root,'*'+ext))
        for f in files :
            mdate = file_modif_date(f)
            MODIFQUEUE.put_nowait( (-mdate,f) )


def file_modif_date(f):
    """ return modif date in seconds (as in time.time()) """
    return os.stat(f).st_mtime


def die_with_usage():
    """ HELP MENU """
    print 'dataset_filestats.py'
    print '   by T. Bertin-Mahieux (2010) Columbia University'
    print '      tb2332@columbia.edu'
    print 'Simple util to check the file repartition and the most'
    print 'recent file in the Million Song dataset directory'
    print 'usage:'
    print '   python dataset_filestats.py <maindir>'
    sys.exit(0)


if __name__ == '__main__':

    # help menu
    if len(sys.argv) < 2:
        die_with_usage()

    trimdryrun = False
    trim = False
    while True:
        if sys.argv[1] == '-trimdryrun':
            trimdryrun = True
            trim = False
        elif sys.argv[1] == '-trim':
            if trimdryrun:
                pass
            else:
                trim = True
                print 'WE TRIM FOR REAL!!!!'
        else:
            break
        sys.argv.pop(1)

    maindir = sys.argv[1]

    # number of leaves
    n_leaves = count_normal_leaves(maindir)
    print '******************************************************'
    print 'got',n_leaves,'leaves out of',26*26*26,'possible ones.'

    # empty and full leaves
    print '******************************************************'
    min_nfiles = min(MAP_NFILES_DIR.keys())
    print 'most empty leave(s) have',min_nfiles,'files, they are:'
    print MAP_NFILES_DIR[min_nfiles]
    max_nfiles = max(MAP_NFILES_DIR.keys())
    print 'most full leave(s) have',max_nfiles,'files, they are:'
    print MAP_NFILES_DIR[max_nfiles]
    nfiles = 0
    for k in MAP_NFILES_DIR:
        nfiles += k * len(MAP_NFILES_DIR[k])
    print 'we found',nfiles,'files in total'
    print 'average number of files per leaf:',nfiles * 1. / n_leaves

    # tmp files
    ntmpfiles = len( get_all_files(maindir,ext='.h5_tmp') )
    print 'we found',ntmpfiles,'temp files'
    if ntmpfiles > 0: print 'WATCHOUT FOR TMP FILES!!!!'

    # find modif date for all files, and pop out the most recent ones
    get_all_files_modif_date(maindir)
    print '******************************************************'
    if not trim and not trimdryrun:
        print 'most recent files are:'
        for k in range(5):
            t,f = MODIFQUEUE.get_nowait()
            print f,'(',time.ctime(-t),')'
    elif trim or trimdryrun:
        ntoomany = nfiles - 1000000
        print 'we have',ntoomany,'too many files.'
        for k in range(ntoomany):
            t,f = MODIFQUEUE.get_nowait()
            print f,'(',time.ctime(-t),')'
            if trim:
                os.remove(f)
    # done
    print '******************************************************'

########NEW FILE########
__FILENAME__ = dataset_sanity_check
"""
Thierry Bertin-Mahieux (2010) Columbia University
tb2332@columbia.edu

This code contains code used when creating the actual MSong dataset,
i.e. functions to create a song HDF5 at the right place, with proper
locks for multithreading.

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.


Copyright 2010, Thierry Bertin-Mahieux

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import glob
import copy
import time
import datetime
import multiprocessing
import numpy as np
try:
    import hdf5_utils as HDF5
except ImportError:
    pass # will be imported in command line



def get_all_files(basedir,ext='.h5') :
    """
    From a root directory, go through all subdirectories
    and find all files with the given extension.
    Return all absolute paths in a list.
    """
    allfiles = []
    for root, dirs, files in os.walk(basedir):
        files = glob.glob(os.path.join(root,'*'+ext))
        for f in files :
            allfiles.append( os.path.abspath(f) )
    return allfiles

# error passing problems
class KeyboardInterruptError(Exception):pass

# wrapper
def sanity_check_1thread_wrapper(args):
    """ wrapper for multiprocessing to call the real function """
    sanity_check_1thread(**args)

# actual function
def sanity_check_1thread(maindir=None,threadid=-1,nthreads=-1,allfiles=[]):
    """
    Main function, check a bunch of files by opening every field in
    getter.
    """
    assert not maindir is None,'wrong param maindir'
    assert threadid>-1,'wrong param threadid'
    assert nthreads>0,'wrong param nthreads'
    assert len(allfiles)>0,'wrong param allfiles, or no files'
    # get getters
    getters = filter(lambda x: x[:4] == 'get_', GETTERS.__dict__.keys())
    # get the files to check
    files_per_thread = int(np.ceil(len(allfiles) * 1. / nthreads))
    p1 = files_per_thread * threadid
    p2 = min(len(allfiles),files_per_thread * (threadid+1))
    # iterate over files between p1 and p2
    for f in allfiles[p1:p2]:
        try:
            h5 = GETTERS.open_h5_file_read(f)
            for getter in getters:
                tmp = GETTERS.__getattribute__(getter)(h5)
        except KeyboardInterrupt:
            raise KeyboardInterruptError()
        except Exception,e:
            print 'PROBLEM WITH FILE:',f; sys.stdout.flush()
            raise
        finally:
            h5.close()
    # done, all fine
    return


def die_with_usage():
    """ HELP MENU """
    print 'dataset_sanity_check.py'
    print '  by T. Bertin-Mahieux (2010) Columbia University'
    print '     tb2332@columbia.edu'
    print 'do a simple but full sanity check on the dataset'
    print 'GOAL: read every field of every file to make sure nothing'
    print '      is corrupted'
    print 'usage:'
    print '  python dataset_sanity_check.py -nthreads N <main dir>'
    print 'PARAMS:'
    print '  main dir      - Million Song Dataset root directory'
    print 'FLAGS:'
    print '  -nthreads N   - number of threads, default 1'
    sys.exit(0)


if __name__ == '__main__':

    # help menu
    if len(sys.argv) < 2:
        die_with_usage()

    # local imports
    sys.path.append(os.path.abspath(os.path.join(sys.argv[0],'../..')))
    import hdf5_getters as GETTERS

    # flags
    nthreads = 1
    while True:
        if sys.argv[1] == '-nthreads':
            nthreads = int(sys.argv[2])
            sys.argv.pop(1)
        else:
            break
        sys.argv.pop(1)

    # params
    maindir = sys.argv[1]

    # count files
    allfiles = get_all_files(maindir,ext='.h5')
    nfiles = len(allfiles)
    print 'we found',nfiles,'files.'
    if nfiles != 1000000:
        print 'WATCHOUT! NOT A MILLION FILES'
    allfiles = sorted(allfiles)
    
    # create args for the threads
    params_list = []
    for k in range(nthreads):
        params = {'maindir':maindir,'allfiles':allfiles,
                  'threadid':k,'nthreads':nthreads}
        params_list.append(params)

    # start time
    t1 = time.time()

    # launch the processes
    got_probs = False
    pool = multiprocessing.Pool(processes=nthreads)
    try:
        pool.map(sanity_check_1thread_wrapper, params_list)
        pool.close()
        pool.join()
    except KeyboardInterrupt:
        print 'MULTIPROCESSING'
        print 'stopping multiprocessing due to a keyboard interrupt'
        pool.terminate()
        pool.join()
    except Exception, e:
        print 'MULTIPROCESSING'
        print 'got exception: %r, terminating the pool' % (e,)
        pool.terminate()
        pool.join()
        got_probs = True
    
    # end time
    t2 = time.time()
    stimelength = str(datetime.timedelta(seconds=t2-t1))
    if not got_probs:
        print 'ALL DONE, no apparent problem'
    print 'execution time:', stimelength

########NEW FILE########
__FILENAME__ = display_song
"""
Thierry Bertin-Mahieux (2010) Columbia University
tb2332@columbia.edu

Code to quickly see the content of an HDF5 file.

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.


Copyright 2010, Thierry Bertin-Mahieux

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import hdf5_getters
import numpy as np


def die_with_usage():
    """ HELP MENU """
    print 'display_song.py'
    print 'T. Bertin-Mahieux (2010) tb2332@columbia.edu'
    print 'to quickly display all we know about a song'
    print 'usage:'
    print '   python display_song.py [FLAGS] <HDF5 file> <OPT: song idx> <OPT: getter>'
    print 'example:'
    print '   python display_song.py mysong.h5 0 danceability'
    print 'INPUTS'
    print '   <HDF5 file>  - any song / aggregate /summary file'
    print '   <song idx>   - if file contains many songs, specify one'
    print '                  starting at 0 (OPTIONAL)'
    print '   <getter>     - if you want only one field, you can specify it'
    print '                  e.g. "get_artist_name" or "artist_name" (OPTIONAL)'
    print 'FLAGS'
    print '   -summary     - if you use a file that does not have all fields,'
    print '                  use this flag. If not, you might get an error!'
    print '                  Specifically desgin to display summary files'
    sys.exit(0)


if __name__ == '__main__':
    """ MAIN """

    # help menu
    if len(sys.argv) < 2:
        die_with_usage()

    # flags
    summary = False
    while True:
        if sys.argv[1] == '-summary':
            summary = True
        else:
            break
        sys.argv.pop(1)

    # get params
    hdf5path = sys.argv[1]
    songidx = 0
    if len(sys.argv) > 2:
        songidx = int(sys.argv[2])
    onegetter = ''
    if len(sys.argv) > 3:
        onegetter = sys.argv[3]

    # sanity check
    if not os.path.isfile(hdf5path):
        print 'ERROR: file',hdf5path,'does not exist.'
        sys.exit(0)
    h5 = hdf5_getters.open_h5_file_read(hdf5path)
    numSongs = hdf5_getters.get_num_songs(h5)
    if songidx >= numSongs:
        print 'ERROR: file contains only',numSongs
        h5.close()
        sys.exit(0)

    # get all getters
    getters = filter(lambda x: x[:4] == 'get_', hdf5_getters.__dict__.keys())
    getters.remove("get_num_songs") # special case
    if onegetter == 'num_songs' or onegetter == 'get_num_songs':
        getters = []
    elif onegetter != '':
        if onegetter[:4] != 'get_':
            onegetter = 'get_' + onegetter
        try:
            getters.index(onegetter)
        except ValueError:
            print 'ERROR: getter requested:',onegetter,'does not exist.'
            h5.close()
            sys.exit(0)
        getters = [onegetter]
    getters = np.sort(getters)

    # print them
    for getter in getters:
        try:
            res = hdf5_getters.__getattribute__(getter)(h5,songidx)
        except AttributeError, e:
            if summary:
                continue
            else:
                print e
                print 'forgot -summary flag? specified wrong getter?'
        if res.__class__.__name__ == 'ndarray':
            print getter[4:]+": shape =",res.shape
        else:
            print getter[4:]+":",res

    # done
    print 'DONE, showed song',songidx,'/',numSongs-1,'in file:',hdf5path
    h5.close()
    

########NEW FILE########
__FILENAME__ = enpyapi_to_hdf5
"""
Thierry Bertin-Mahieux (2010) Columbia University
tb2332@columbia.edu


This code contains is a standalone (and debugging tool)
that uploads a song to the Echo Nest API and creates a HDF5 with it.

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.


Copyright 2010, Thierry Bertin-Mahieux

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""


import os
import sys
import time
# postgresql
try:
    import pg
except ImportError:
    print "You don't have the 'pg' module, can't use musicbrainz server"
try:
    import multiprocessing
except ImportError:
    print "You can't use multiprocessing"
# our HDF utils library
import hdf5_utils as HDF5
# Echo Nest python API
from pyechonest import artist as artistEN
from pyechonest import song as songEN
from pyechonest import track as trackEN
from pyechonest import config
try:
    config.ECHO_NEST_API_KEY = os.environ['ECHO_NEST_API_KEY']
except KeyError: # historic reasons
    config.ECHO_NEST_API_KEY = os.environ['ECHONEST_API_KEY']
# musicbrainz
DEF_MB_USER = 'gordon'
DEF_MB_PASSWD = 'gordon'

# for multiprocessing
class KeyboardInterruptError(Exception):pass

def convert_one_song(audiofile,output,mbconnect=None,verbose=0,DESTROYAUDIO=False):
    """
    PRINCIPAL FUNCTION
    Converts one given audio file to hdf5 format (saved in 'output')
    by uploading it to The Echo Nest API
    INPUT
         audiofile   - path to a typical audio file (wav, mp3, ...)
            output   - nonexisting hdf5 path
         mbconnect   - if not None, open connection to musicbrainz server
           verbose   - if >0 display more information
      DESTROYAUDIO   - Careful! deletes audio file if everything went well
    RETURN
       1 if we think a song is created, 0 otherwise
    """
    # inputs + sanity checks
    if not os.path.exists(audiofile):
        print 'ERROR: song file does not exist:',songfile
        return 0
    if os.path.exists(output):
        print 'ERROR: hdf5 output file already exist:',output,', delete or choose new path'
        return 0
    # get EN track / song / artist for that song
    if verbose>0: print 'get analysis for file:',audiofile
    track = trackEN.track_from_filename(audiofile)
    song_id = track.song_id
    song = songEN.Song(song_id)
    if verbose>0: print 'found song:',song.title,'(',song_id,')'
    artist_id = song.artist_id
    artist = artistEN.Artist(artist_id)
    if verbose>0: print 'found artist:',artist.name,'(',artist_id,')'
    # hack to fill missing values
    try:
        track.foreign_id
    except AttributeError:
        track.__setattr__('foreign_id','')
        if verbose>0: print 'no track foreign_id found'
    try:
        track.foreign_release_id
    except AttributeError:
        track.__setattr__('foreign_release_id','')
        if verbose>0: print 'no track foreign_release_id found'
    # create HDF5 file
    if verbose>0: print 'create HDF5 file:',output
    HDF5.create_song_file(output,force=False)
    # fill hdf5 file from track
    if verbose>0:
        if mbconnect is None:
            print 'fill HDF5 file with info from track/song/artist'
        else:
            print 'fill HDF5 file with info from track/song/artist/musicbrainz'
    h5 = HDF5.open_h5_file_append(output)
    HDF5.fill_hdf5_from_artist(h5,artist)
    HDF5.fill_hdf5_from_song(h5,song)
    HDF5.fill_hdf5_from_track(h5,track)
    if not mbconnect is None:
        HDF5.fill_hdf5_from_musicbrainz(h5,mbconnect)
    h5.close()
    # done
    if DESTROYAUDIO:
        if verbose>0: print 'We remove audio file:',audiofile
        os.remove(audiofile)
    return 1


def convert_one_song_wrapper(args):
    """ for multiprocessing """
    mbconnect = None
    if args['usemb']:
        if verbose>0: print 'fill HDF5 file using musicbrainz'
        mbconnect = pg.connect('musicbrainz_db','localhost',-1,None,None,
                               args['mbuser'],args['mbpasswd'])
    try:
        convert_one_song(args['audiofile'],args['output'],
                         mbconnect=mbconnect,verbose=args['verbose'],
                         DESTROYAUDIO=args['DESTROYAUDIO'])
    except KeyboardInterrupt:
        raise KeyboardInterruptError()
    except Exception, e:
        print 'ERROR with file:',args['audiofile']+':',e
    finally:
        if not mbconnect is None:
            mbconnect.close()


def die_with_usage():
    """ HELP MENU """
    print 'enpyapi_to_hdf5.py'
    print 'by T. Bertin-Mahieux (2010) Columbia University'
    print ''
    print 'Upload a song to get its analysis, writes it to a HDF5 file'
    print 'using the Million Song Database format'
    print 'NO GUARANTEE THAT THE FILE IS KNOWN! => no artist or song name'
    print 'Note that we do not catch errors like timeouts, etc.'
    print ''
    print 'To have every fields filled, you need a local copy of the'
    print "musicbrainz server with recent dumps. It concerns fields 'year'"
    print "'mbtags' and 'mbtags_count'"
    print ''
    print 'usage:'
    print '  python enpyapi_to_hdf5.py [FLAGS] <songpath> <new hdf5file>'
    print ' OR'
    print '  python enpyapi_to_hdf5.py [FLAGS] -dir <inputdir>'
    print 'PARAMS'
    print '  songpath      - path a song in a usual format, e.g. MP3'
    print '  new hdf5file  - output, e.g. mysong.h5'
    print '      inputdir  - in that mode, converts every known song (mp3,wav,au,ogg)'
    print '                  in all subdirectories, outputpath is songpath + .h5 extension'
    print 'FLAGS'
    print '  -verbose v    - set it to 0 to remove printouts'
    print '  -usemb        - use musicbrainz, e.g. you have a local copy'
    print '  -mbuser U P   - specify the musicbrainz user and password'
    print "                  (default: user='gordon' passwd='gordon')"
    print '                  (you can also change the default values in the code)'
    print ''
    sys.exit(0)


if __name__ == '__main__':

    # help menu
    if len(sys.argv) < 3:
        die_with_usage()

    # start time
    t1 = time.time()

    # flags
    mbuser = DEF_MB_USER
    mbpasswd = DEF_MB_PASSWD
    usemb = False
    verbose = 1
    inputdir = ''
    nthreads = 1
    DESTROYAUDIO=False # let's not advertise that flag in the help menu
    while True:
        if len(sys.argv) < 2: # happens with -dir option
            break
        if sys.argv[1] == '-verbose':
            verbose = int(sys.argv[2])
            sys.argv.pop(1)
        elif sys.argv[1] == '-usemb':
            usemb = True
        elif sys.argv[1] == '-mbuser':
            mbuser = sys.argv[2]
            mbpasswd = sys.argv[3]
            sys.argv.pop(1)
            sys.argv.pop(1)
        elif sys.argv[1] == '-dir':
            inputdir = sys.argv[2]
            sys.argv.pop(1)
        elif sys.argv[1] == '-nthreads':
            nthreads = int(sys.argv[2])
            sys.argv.pop(1)
        elif sys.argv[1] == '-DESTROYAUDIO':
            DESTROYAUDIO = True
        else:
            break
        sys.argv.pop(1)

    # if we only do one file!
    if inputdir == '':
        songfile = sys.argv[1]
        hdf5file = sys.argv[2]
        if not os.path.exists(songfile):
            print 'ERROR: song file does not exist:',songfile
            print '********************************'
            die_with_usage()
        if os.path.exists(hdf5file):
            print 'ERROR: hdf5 file already exist:',hdf5file,', delete or choose new path'
            print '********************************'
            die_with_usage()
        # musicbrainz
        mbconnect = None
        if usemb:
            if verbose>0: print 'fill HDF5 file using musicbrainz'
            mbconnect = pg.connect('musicbrainz_db','localhost',-1,None,None,mbuser,mbpasswd)
        # transform
        convert_one_song(songfile,hdf5file,mbconnect=mbconnect,verbose=verbose)
        # close connection
        if not mbconnect is None:
            mbconnect.close()
        # verbose
        if verbose > 0:
            t2 = time.time()
            print 'From audio:',songfile,'we created hdf5 file:',hdf5file,'in',str(int(t2-t1)),'seconds.'

    # we have an input dir, one thread
    elif nthreads == 1:
        # sanity check
        if not os.path.isdir(inputdir):
            print 'ERROR: input directory',inputdir,'does not exist.'
            print '********************************'
            die_with_usage()
        # musicbrainz
        mbconnect = None
        if usemb:
            if verbose>0: print 'fill HDF5 file using musicbrainz'
            mbconnect = pg.connect('musicbrainz_db','localhost',-1,None,None,mbuser,mbpasswd)
        # iterate
        cnt_songs = 0
        cnt_done = 0
        for root,dirs,files in os.walk(inputdir):
            files = filter(lambda x: os.path.splitext(x)[1] in ('.wav','.ogg','.au','.mp3'),
                           files)
            files = map(lambda x: os.path.join(root,x), files)
            for f in files:
                cnt_songs += 1
                if cnt_songs % 100 == 0:
                    if verbose>0: print 'DOING FILE #'+str(cnt_songs)
                try:
                    cnt_done += convert_one_song(f,f+'.h5',mbconnect=mbconnect,verbose=verbose,
                                                 DESTROYAUDIO=DESTROYAUDIO)
                except KeyboardInterrupt:
                    raise
                except Exception, e:
                    print 'ERROR with file:',f+':',e
        # iteration done
        if verbose>0:
            print 'Converted',str(cnt_done)+'/'+str(cnt_songs),'in all subdirectories of',inputdir
            t2 = time.time()
            print 'All conversions took:',str(int(t2-t1)),'seconds.'
        # close musicbrainz
        if not mbconnect is None:
            mbconnect.close()


    # input dir, many threads
    # YOU SHOULD NOT USE THIS FUNCTION UNLESS YOU HAVE MORE THAN 1000 FILES
    else:
        assert nthreads > 0,'negative or null number of threads? come one!'
        # get all songs
        allsongs = []
        for root,dirs,files in os.walk(inputdir):
            files = filter(lambda x: os.path.splitext(x)[1] in ('.wav','.ogg','.au','.mp3'),
                           files)
            files = map(lambda x: os.path.join(root,x), files)
            allsongs.extend( files )
        if verbose>0: print 'We found',len(allsongs),'songs.'
        # musicbrainz
        mbconnect = None
        if usemb:
            if verbose>0: print 'fill HDF5 file using musicbrainz'
            mbconnect = pg.connect('musicbrainz_db','localhost',-1,None,None,mbuser,mbpasswd)
        # prepare params
        params_list = map(lambda x: {'verbose':verbose,'DESTROYAUDIO':DESTROYAUDIO,
                                     'audiofile':x,'output':x+'.h5','usemb':usemb,
                                     'mbuser':mbuser,'mbpasswd':mbpasswd},allsongs)
        # launch, run all the jobs
        pool = multiprocessing.Pool(processes=nthreads)
        try:
            pool.map(convert_one_song_wrapper, params_list)
            pool.close()
            pool.join()
        except KeyboardInterruptError:
            print 'MULTIPROCESSING'
            print 'stopping multiprocessing due to a keyboard interrupt'
            pool.terminate()
            pool.join()
        except Exception, e:
            print 'MULTIPROCESSING'
            print 'got exception: %r, terminating the pool' % (e,)
            pool.terminate()
            pool.join()
        # musicbrainz
        if not mbconnect is None:
            mbconnect.close()
        # all done!
        if verbose>0:
            t2 = time.time()
            print 'Program ran for:',str(int(t2-t1)),'seconds with',nthreads,'threads.'

########NEW FILE########
__FILENAME__ = hdf5_descriptors
"""
Thierry Bertin-Mahieux (2010) Columbia University
tb2332@columbia.edu


This code contains descriptors used to create HDF5 files
for the Million Song Database Project.
What information gets in the database should be decided here.

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.


Copyright 2010, Thierry Bertin-Mahieux

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

# code relies on pytables, see http://www.pytables.org
import tables


MAXSTRLEN = 1024

class SongMetaData(tables.IsDescription):
    """
    Class to hold the metadata of one song
    """
    artist_name = tables.StringCol(MAXSTRLEN)
    artist_id = tables.StringCol(32)
    artist_mbid = tables.StringCol(40)
    artist_playmeid = tables.IntCol()
    artist_7digitalid = tables.IntCol()
    analyzer_version = tables.StringCol(32)
    genre = tables.StringCol(MAXSTRLEN)
    release = tables.StringCol(MAXSTRLEN)
    release_7digitalid = tables.IntCol()
    title = tables.StringCol(MAXSTRLEN)
    artist_familiarity = tables.Float64Col()
    artist_hotttnesss = tables.Float64Col()
    song_id = tables.StringCol(32)
    song_hotttnesss = tables.Float64Col()
    artist_latitude = tables.Float64Col()
    artist_longitude = tables.Float64Col()
    artist_location = tables.StringCol(MAXSTRLEN)
    track_7digitalid = tables.IntCol()
    # ARRAY INDICES
    idx_similar_artists = tables.IntCol()
    idx_artist_terms = tables.IntCol()
    # TO ADD
    
    # song mbid
    # album mbid

    # url    
    # preview url, 7digital, release_image


class SongAnalysis(tables.IsDescription):
    """
    Class to hold the analysis of one song
    """
    analysis_sample_rate = tables.IntCol()
    audio_md5 = tables.StringCol(32)
    danceability = tables.Float64Col()
    duration = tables.Float64Col()
    end_of_fade_in = tables.Float64Col()
    energy = tables.Float64Col()
    key = tables.IntCol()
    key_confidence = tables.Float64Col()
    loudness = tables.Float64Col()
    mode = tables.IntCol()
    mode_confidence = tables.Float64Col()
    start_of_fade_out = tables.Float64Col()
    tempo = tables.Float64Col()
    time_signature = tables.IntCol()
    time_signature_confidence = tables.Float64Col()
    track_id = tables.StringCol(32)
    # ARRAY INDICES
    idx_segments_start = tables.IntCol()
    idx_segments_confidence = tables.IntCol()
    idx_segments_pitches = tables.IntCol()
    idx_segments_timbre = tables.IntCol()
    idx_segments_loudness_max = tables.IntCol()
    idx_segments_loudness_max_time = tables.IntCol()
    idx_segments_loudness_start = tables.IntCol()
    idx_sections_start = tables.IntCol()
    idx_sections_confidence = tables.IntCol()
    idx_beats_start = tables.IntCol()
    idx_beats_confidence = tables.IntCol()
    idx_bars_start = tables.IntCol()
    idx_bars_confidence = tables.IntCol()
    idx_tatums_start = tables.IntCol()
    idx_tatums_confidence = tables.IntCol()
    
class SongMusicBrainz(tables.IsDescription):
    """
    Class to hold information coming from
    MusicBrainz for one song
    """
    year = tables.IntCol()
    # ARRAY INDEX
    idx_artist_mbtags = tables.IntCol()

########NEW FILE########
__FILENAME__ = hdf5_getters
"""
Thierry Bertin-Mahieux (2010) Columbia University
tb2332@columbia.edu


This code contains a set of getters functions to access the fields
from an HDF5 song file (regular file with one song or
aggregate / summary file with many songs)

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.


Copyright 2010, Thierry Bertin-Mahieux

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""


import tables


def open_h5_file_read(h5filename):
    """
    Open an existing H5 in read mode.
    Same function as in hdf5_utils, here so we avoid one import
    """
    return tables.openFile(h5filename, mode='r')


def get_num_songs(h5):
    """
    Return the number of songs contained in this h5 file, i.e. the number of rows
    for all basic informations like name, artist, ...
    """
    return h5.root.metadata.songs.nrows

def get_artist_familiarity(h5,songidx=0):
    """
    Get artist familiarity from a HDF5 song file, by default the first song in it
    """
    return h5.root.metadata.songs.cols.artist_familiarity[songidx]

def get_artist_hotttnesss(h5,songidx=0):
    """
    Get artist hotttnesss from a HDF5 song file, by default the first song in it
    """
    return h5.root.metadata.songs.cols.artist_hotttnesss[songidx]

def get_artist_id(h5,songidx=0):
    """
    Get artist id from a HDF5 song file, by default the first song in it
    """
    return h5.root.metadata.songs.cols.artist_id[songidx]

def get_artist_mbid(h5,songidx=0):
    """
    Get artist musibrainz id from a HDF5 song file, by default the first song in it
    """
    return h5.root.metadata.songs.cols.artist_mbid[songidx]

def get_artist_playmeid(h5,songidx=0):
    """
    Get artist playme id from a HDF5 song file, by default the first song in it
    """
    return h5.root.metadata.songs.cols.artist_playmeid[songidx]

def get_artist_7digitalid(h5,songidx=0):
    """
    Get artist 7digital id from a HDF5 song file, by default the first song in it
    """
    return h5.root.metadata.songs.cols.artist_7digitalid[songidx]

def get_artist_latitude(h5,songidx=0):
    """
    Get artist latitude from a HDF5 song file, by default the first song in it
    """
    return h5.root.metadata.songs.cols.artist_latitude[songidx]

def get_artist_longitude(h5,songidx=0):
    """
    Get artist longitude from a HDF5 song file, by default the first song in it
    """
    return h5.root.metadata.songs.cols.artist_longitude[songidx]

def get_artist_location(h5,songidx=0):
    """
    Get artist location from a HDF5 song file, by default the first song in it
    """
    return h5.root.metadata.songs.cols.artist_location[songidx]

def get_artist_name(h5,songidx=0):
    """
    Get artist name from a HDF5 song file, by default the first song in it
    """
    return h5.root.metadata.songs.cols.artist_name[songidx]

def get_release(h5,songidx=0):
    """
    Get release from a HDF5 song file, by default the first song in it
    """
    return h5.root.metadata.songs.cols.release[songidx]

def get_release_7digitalid(h5,songidx=0):
    """
    Get release 7digital id from a HDF5 song file, by default the first song in it
    """
    return h5.root.metadata.songs.cols.release_7digitalid[songidx]

def get_song_id(h5,songidx=0):
    """
    Get song id from a HDF5 song file, by default the first song in it
    """
    return h5.root.metadata.songs.cols.song_id[songidx]

def get_song_hotttnesss(h5,songidx=0):
    """
    Get song hotttnesss from a HDF5 song file, by default the first song in it
    """
    return h5.root.metadata.songs.cols.song_hotttnesss[songidx]

def get_title(h5,songidx=0):
    """
    Get title from a HDF5 song file, by default the first song in it
    """
    return h5.root.metadata.songs.cols.title[songidx]

def get_track_7digitalid(h5,songidx=0):
    """
    Get track 7digital id from a HDF5 song file, by default the first song in it
    """
    return h5.root.metadata.songs.cols.track_7digitalid[songidx]

def get_similar_artists(h5,songidx=0):
    """
    Get similar artists array. Takes care of the proper indexing if we are in aggregate
    file. By default, return the array for the first song in the h5 file.
    To get a regular numpy ndarray, cast the result to: numpy.array( )
    """
    if h5.root.metadata.songs.nrows == songidx + 1:
        return h5.root.metadata.similar_artists[h5.root.metadata.songs.cols.idx_similar_artists[songidx]:]
    return h5.root.metadata.similar_artists[h5.root.metadata.songs.cols.idx_similar_artists[songidx]:
                                            h5.root.metadata.songs.cols.idx_similar_artists[songidx+1]]

def get_artist_terms(h5,songidx=0):
    """
    Get artist terms array. Takes care of the proper indexing if we are in aggregate
    file. By default, return the array for the first song in the h5 file.
    To get a regular numpy ndarray, cast the result to: numpy.array( )
    """
    if h5.root.metadata.songs.nrows == songidx + 1:
        return h5.root.metadata.artist_terms[h5.root.metadata.songs.cols.idx_artist_terms[songidx]:]
    return h5.root.metadata.artist_terms[h5.root.metadata.songs.cols.idx_artist_terms[songidx]:
                                            h5.root.metadata.songs.cols.idx_artist_terms[songidx+1]]

def get_artist_terms_freq(h5,songidx=0):
    """
    Get artist terms array frequencies. Takes care of the proper indexing if we are in aggregate
    file. By default, return the array for the first song in the h5 file.
    To get a regular numpy ndarray, cast the result to: numpy.array( )
    """
    if h5.root.metadata.songs.nrows == songidx + 1:
        return h5.root.metadata.artist_terms_freq[h5.root.metadata.songs.cols.idx_artist_terms[songidx]:]
    return h5.root.metadata.artist_terms_freq[h5.root.metadata.songs.cols.idx_artist_terms[songidx]:
                                              h5.root.metadata.songs.cols.idx_artist_terms[songidx+1]]

def get_artist_terms_weight(h5,songidx=0):
    """
    Get artist terms array frequencies. Takes care of the proper indexing if we are in aggregate
    file. By default, return the array for the first song in the h5 file.
    To get a regular numpy ndarray, cast the result to: numpy.array( )
    """
    if h5.root.metadata.songs.nrows == songidx + 1:
        return h5.root.metadata.artist_terms_weight[h5.root.metadata.songs.cols.idx_artist_terms[songidx]:]
    return h5.root.metadata.artist_terms_weight[h5.root.metadata.songs.cols.idx_artist_terms[songidx]:
                                                h5.root.metadata.songs.cols.idx_artist_terms[songidx+1]]

def get_analysis_sample_rate(h5,songidx=0):
    """
    Get analysis sample rate from a HDF5 song file, by default the first song in it
    """
    return h5.root.analysis.songs.cols.analysis_sample_rate[songidx]

def get_audio_md5(h5,songidx=0):
    """
    Get audio MD5 from a HDF5 song file, by default the first song in it
    """
    return h5.root.analysis.songs.cols.audio_md5[songidx]

def get_danceability(h5,songidx=0):
    """
    Get danceability from a HDF5 song file, by default the first song in it
    """
    return h5.root.analysis.songs.cols.danceability[songidx]

def get_duration(h5,songidx=0):
    """
    Get duration from a HDF5 song file, by default the first song in it
    """
    return h5.root.analysis.songs.cols.duration[songidx]

def get_end_of_fade_in(h5,songidx=0):
    """
    Get end of fade in from a HDF5 song file, by default the first song in it
    """
    return h5.root.analysis.songs.cols.end_of_fade_in[songidx]

def get_energy(h5,songidx=0):
    """
    Get energy from a HDF5 song file, by default the first song in it
    """
    return h5.root.analysis.songs.cols.energy[songidx]

def get_key(h5,songidx=0):
    """
    Get key from a HDF5 song file, by default the first song in it
    """
    return h5.root.analysis.songs.cols.key[songidx]

def get_key_confidence(h5,songidx=0):
    """
    Get key confidence from a HDF5 song file, by default the first song in it
    """
    return h5.root.analysis.songs.cols.key_confidence[songidx]

def get_loudness(h5,songidx=0):
    """
    Get loudness from a HDF5 song file, by default the first song in it
    """
    return h5.root.analysis.songs.cols.loudness[songidx]

def get_mode(h5,songidx=0):
    """
    Get mode from a HDF5 song file, by default the first song in it
    """
    return h5.root.analysis.songs.cols.mode[songidx]

def get_mode_confidence(h5,songidx=0):
    """
    Get mode confidence from a HDF5 song file, by default the first song in it
    """
    return h5.root.analysis.songs.cols.mode_confidence[songidx]

def get_start_of_fade_out(h5,songidx=0):
    """
    Get start of fade out from a HDF5 song file, by default the first song in it
    """
    return h5.root.analysis.songs.cols.start_of_fade_out[songidx]

def get_tempo(h5,songidx=0):
    """
    Get tempo from a HDF5 song file, by default the first song in it
    """
    return h5.root.analysis.songs.cols.tempo[songidx]

def get_time_signature(h5,songidx=0):
    """
    Get signature from a HDF5 song file, by default the first song in it
    """
    return h5.root.analysis.songs.cols.time_signature[songidx]

def get_time_signature_confidence(h5,songidx=0):
    """
    Get signature confidence from a HDF5 song file, by default the first song in it
    """
    return h5.root.analysis.songs.cols.time_signature_confidence[songidx]

def get_track_id(h5,songidx=0):
    """
    Get track id from a HDF5 song file, by default the first song in it
    """
    return h5.root.analysis.songs.cols.track_id[songidx]

def get_segments_start(h5,songidx=0):
    """
    Get segments start array. Takes care of the proper indexing if we are in aggregate
    file. By default, return the array for the first song in the h5 file.
    To get a regular numpy ndarray, cast the result to: numpy.array( )
    """
    if h5.root.analysis.songs.nrows == songidx + 1:
        return h5.root.analysis.segments_start[h5.root.analysis.songs.cols.idx_segments_start[songidx]:]
    return h5.root.analysis.segments_start[h5.root.analysis.songs.cols.idx_segments_start[songidx]:
                                           h5.root.analysis.songs.cols.idx_segments_start[songidx+1]]
    
def get_segments_confidence(h5,songidx=0):
    """
    Get segments confidence array. Takes care of the proper indexing if we are in aggregate
    file. By default, return the array for the first song in the h5 file.
    To get a regular numpy ndarray, cast the result to: numpy.array( )
    """
    if h5.root.analysis.songs.nrows == songidx + 1:
        return h5.root.analysis.segments_confidence[h5.root.analysis.songs.cols.idx_segments_confidence[songidx]:]
    return h5.root.analysis.segments_confidence[h5.root.analysis.songs.cols.idx_segments_confidence[songidx]:
                                                h5.root.analysis.songs.cols.idx_segments_confidence[songidx+1]]

def get_segments_pitches(h5,songidx=0):
    """
    Get segments pitches array. Takes care of the proper indexing if we are in aggregate
    file. By default, return the array for the first song in the h5 file.
    To get a regular numpy ndarray, cast the result to: numpy.array( )
    """
    if h5.root.analysis.songs.nrows == songidx + 1:
        return h5.root.analysis.segments_pitches[h5.root.analysis.songs.cols.idx_segments_pitches[songidx]:,:]
    return h5.root.analysis.segments_pitches[h5.root.analysis.songs.cols.idx_segments_pitches[songidx]:
                                             h5.root.analysis.songs.cols.idx_segments_pitches[songidx+1],:]

def get_segments_timbre(h5,songidx=0):
    """
    Get segments timbre array. Takes care of the proper indexing if we are in aggregate
    file. By default, return the array for the first song in the h5 file.
    To get a regular numpy ndarray, cast the result to: numpy.array( )
    """
    if h5.root.analysis.songs.nrows == songidx + 1:
        return h5.root.analysis.segments_timbre[h5.root.analysis.songs.cols.idx_segments_timbre[songidx]:,:]
    return h5.root.analysis.segments_timbre[h5.root.analysis.songs.cols.idx_segments_timbre[songidx]:
                                            h5.root.analysis.songs.cols.idx_segments_timbre[songidx+1],:]

def get_segments_loudness_max(h5,songidx=0):
    """
    Get segments loudness max array. Takes care of the proper indexing if we are in aggregate
    file. By default, return the array for the first song in the h5 file.
    To get a regular numpy ndarray, cast the result to: numpy.array( )
    """
    if h5.root.analysis.songs.nrows == songidx + 1:
        return h5.root.analysis.segments_loudness_max[h5.root.analysis.songs.cols.idx_segments_loudness_max[songidx]:]
    return h5.root.analysis.segments_loudness_max[h5.root.analysis.songs.cols.idx_segments_loudness_max[songidx]:
                                                  h5.root.analysis.songs.cols.idx_segments_loudness_max[songidx+1]]

def get_segments_loudness_max_time(h5,songidx=0):
    """
    Get segments loudness max time array. Takes care of the proper indexing if we are in aggregate
    file. By default, return the array for the first song in the h5 file.
    To get a regular numpy ndarray, cast the result to: numpy.array( )
    """
    if h5.root.analysis.songs.nrows == songidx + 1:
        return h5.root.analysis.segments_loudness_max_time[h5.root.analysis.songs.cols.idx_segments_loudness_max_time[songidx]:]
    return h5.root.analysis.segments_loudness_max_time[h5.root.analysis.songs.cols.idx_segments_loudness_max_time[songidx]:
                                                       h5.root.analysis.songs.cols.idx_segments_loudness_max_time[songidx+1]]

def get_segments_loudness_start(h5,songidx=0):
    """
    Get segments loudness start array. Takes care of the proper indexing if we are in aggregate
    file. By default, return the array for the first song in the h5 file.
    To get a regular numpy ndarray, cast the result to: numpy.array( )
    """
    if h5.root.analysis.songs.nrows == songidx + 1:
        return h5.root.analysis.segments_loudness_start[h5.root.analysis.songs.cols.idx_segments_loudness_start[songidx]:]
    return h5.root.analysis.segments_loudness_start[h5.root.analysis.songs.cols.idx_segments_loudness_start[songidx]:
                                                    h5.root.analysis.songs.cols.idx_segments_loudness_start[songidx+1]]

def get_sections_start(h5,songidx=0):
    """
    Get sections start array. Takes care of the proper indexing if we are in aggregate
    file. By default, return the array for the first song in the h5 file.
    To get a regular numpy ndarray, cast the result to: numpy.array( )
    """
    if h5.root.analysis.songs.nrows == songidx + 1:
        return h5.root.analysis.sections_start[h5.root.analysis.songs.cols.idx_sections_start[songidx]:]
    return h5.root.analysis.sections_start[h5.root.analysis.songs.cols.idx_sections_start[songidx]:
                                           h5.root.analysis.songs.cols.idx_sections_start[songidx+1]]

def get_sections_confidence(h5,songidx=0):
    """
    Get sections confidence array. Takes care of the proper indexing if we are in aggregate
    file. By default, return the array for the first song in the h5 file.
    To get a regular numpy ndarray, cast the result to: numpy.array( )
    """
    if h5.root.analysis.songs.nrows == songidx + 1:
        return h5.root.analysis.sections_confidence[h5.root.analysis.songs.cols.idx_sections_confidence[songidx]:]
    return h5.root.analysis.sections_confidence[h5.root.analysis.songs.cols.idx_sections_confidence[songidx]:
                                                h5.root.analysis.songs.cols.idx_sections_confidence[songidx+1]]

def get_beats_start(h5,songidx=0):
    """
    Get beats start array. Takes care of the proper indexing if we are in aggregate
    file. By default, return the array for the first song in the h5 file.
    To get a regular numpy ndarray, cast the result to: numpy.array( )
    """
    if h5.root.analysis.songs.nrows == songidx + 1:
        return h5.root.analysis.beats_start[h5.root.analysis.songs.cols.idx_beats_start[songidx]:]
    return h5.root.analysis.beats_start[h5.root.analysis.songs.cols.idx_beats_start[songidx]:
                                        h5.root.analysis.songs.cols.idx_beats_start[songidx+1]]

def get_beats_confidence(h5,songidx=0):
    """
    Get beats confidence array. Takes care of the proper indexing if we are in aggregate
    file. By default, return the array for the first song in the h5 file.
    To get a regular numpy ndarray, cast the result to: numpy.array( )
    """
    if h5.root.analysis.songs.nrows == songidx + 1:
        return h5.root.analysis.beats_confidence[h5.root.analysis.songs.cols.idx_beats_confidence[songidx]:]
    return h5.root.analysis.beats_confidence[h5.root.analysis.songs.cols.idx_beats_confidence[songidx]:
                                             h5.root.analysis.songs.cols.idx_beats_confidence[songidx+1]]

def get_bars_start(h5,songidx=0):
    """
    Get bars start array. Takes care of the proper indexing if we are in aggregate
    file. By default, return the array for the first song in the h5 file.
    To get a regular numpy ndarray, cast the result to: numpy.array( )
    """
    if h5.root.analysis.songs.nrows == songidx + 1:
        return h5.root.analysis.bars_start[h5.root.analysis.songs.cols.idx_bars_start[songidx]:]
    return h5.root.analysis.bars_start[h5.root.analysis.songs.cols.idx_bars_start[songidx]:
                                       h5.root.analysis.songs.cols.idx_bars_start[songidx+1]]

def get_bars_confidence(h5,songidx=0):
    """
    Get bars start array. Takes care of the proper indexing if we are in aggregate
    file. By default, return the array for the first song in the h5 file.
    To get a regular numpy ndarray, cast the result to: numpy.array( )
    """
    if h5.root.analysis.songs.nrows == songidx + 1:
        return h5.root.analysis.bars_confidence[h5.root.analysis.songs.cols.idx_bars_confidence[songidx]:]
    return h5.root.analysis.bars_confidence[h5.root.analysis.songs.cols.idx_bars_confidence[songidx]:
                                            h5.root.analysis.songs.cols.idx_bars_confidence[songidx+1]]

def get_tatums_start(h5,songidx=0):
    """
    Get tatums start array. Takes care of the proper indexing if we are in aggregate
    file. By default, return the array for the first song in the h5 file.
    To get a regular numpy ndarray, cast the result to: numpy.array( )
    """
    if h5.root.analysis.songs.nrows == songidx + 1:
        return h5.root.analysis.tatums_start[h5.root.analysis.songs.cols.idx_tatums_start[songidx]:]
    return h5.root.analysis.tatums_start[h5.root.analysis.songs.cols.idx_tatums_start[songidx]:
                                         h5.root.analysis.songs.cols.idx_tatums_start[songidx+1]]

def get_tatums_confidence(h5,songidx=0):
    """
    Get tatums confidence array. Takes care of the proper indexing if we are in aggregate
    file. By default, return the array for the first song in the h5 file.
    To get a regular numpy ndarray, cast the result to: numpy.array( )
    """
    if h5.root.analysis.songs.nrows == songidx + 1:
        return h5.root.analysis.tatums_confidence[h5.root.analysis.songs.cols.idx_tatums_confidence[songidx]:]
    return h5.root.analysis.tatums_confidence[h5.root.analysis.songs.cols.idx_tatums_confidence[songidx]:
                                              h5.root.analysis.songs.cols.idx_tatums_confidence[songidx+1]]

def get_artist_mbtags(h5,songidx=0):
    """
    Get artist musicbrainz tag array. Takes care of the proper indexing if we are in aggregate
    file. By default, return the array for the first song in the h5 file.
    To get a regular numpy ndarray, cast the result to: numpy.array( )
    """
    if h5.root.musicbrainz.songs.nrows == songidx + 1:
        return h5.root.musicbrainz.artist_mbtags[h5.root.musicbrainz.songs.cols.idx_artist_mbtags[songidx]:]
    return h5.root.musicbrainz.artist_mbtags[h5.root.metadata.songs.cols.idx_artist_mbtags[songidx]:
                                             h5.root.metadata.songs.cols.idx_artist_mbtags[songidx+1]]

def get_artist_mbtags_count(h5,songidx=0):
    """
    Get artist musicbrainz tag count array. Takes care of the proper indexing if we are in aggregate
    file. By default, return the array for the first song in the h5 file.
    To get a regular numpy ndarray, cast the result to: numpy.array( )
    """
    if h5.root.musicbrainz.songs.nrows == songidx + 1:
        return h5.root.musicbrainz.artist_mbtags_count[h5.root.musicbrainz.songs.cols.idx_artist_mbtags[songidx]:]
    return h5.root.musicbrainz.artist_mbtags_count[h5.root.metadata.songs.cols.idx_artist_mbtags[songidx]:
                                                   h5.root.metadata.songs.cols.idx_artist_mbtags[songidx+1]]

def get_year(h5,songidx=0):
    """
    Get release year from a HDF5 song file, by default the first song in it
    """
    return h5.root.musicbrainz.songs.cols.year[songidx]

########NEW FILE########
__FILENAME__ = hdf5_to_matfile
"""
Thierry Bertin-Mahieux (2010) Columbia University
tb2332@columbia.edu


This code transforms a HDF5 file to a matlab file, with
the same information (as much as possible!)

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.


Copyright 2010, Thierry Bertin-Mahieux

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import time
import glob
try:
    import scipy.io as sio
    import numpy as np
except ImportError:
    print 'ERROR: you need scipy and numpy to create matfiles!'
    print 'both freely available at: http://www.scipy.org/'
    raise
# project code
import hdf5_getters



def get_all_files(basedir,ext='.h5') :
    """
    From a root directory, go through all subdirectories
    and find all files with the given extension.
    Return all absolute paths in a list.
    """
    allfiles = []
    for root, dirs, files in os.walk(basedir):
        files = glob.glob(os.path.join(root,'*'+ext))
        for f in files :
            allfiles.append( os.path.abspath(f) )
    return allfiles


def transfer(h5path,matpath=None,force=False):
    """
    Transfer an HDF5 song file (.h5) to a matfile (.mat)
    If there are more than one song in the HDF5 file, each
    field name gets a number happened: 1, 2, 3, ...., numfiles
    PARAM
        h5path  - path to the HDF5 song file
        matpath - path to the new matfile, same as HDF5 path
                  with a different extension by default
        force   - if True and matfile exists, overwrite
    RETURN
        True if the file was transfered, False if there was
        a problem.
        Could also raise an IOException
    NOTE
        All the data has to be loaded in memory! be careful
        if one file contains tons of songs!
    """
    # sanity checks
    if not os.path.isfile(h5path):
        print 'path to HF5 files does not exist:',h5path
        return False
    if not os.path.splitext(h5path)[1] == '.h5':
        print 'expecting a .h5 extension for file:',h5path
        return False
    # check matfile
    if matpath is None:
        matpath = os.path.splitext(h5path)[0] + '.mat'
    if os.path.exists(matpath):
        if force:
            print 'overwriting file:',matpath
        else:
            print 'matfile',matpath,'already exists (delete or force):'
            return False
    # get all getters! we assume that all we need is in hdf5_getters.py
    # further assume that they have the form get_blablabla and that's the
    # only thing that has that form
    getters = filter(lambda x: x[:4] == 'get_', hdf5_getters.__dict__.keys())
    getters.remove("get_num_songs") # special case
    # open h5 file
    h5 = hdf5_getters.open_h5_file_read(h5path)
    # transfer
    nSongs = hdf5_getters.get_num_songs(h5)
    matdata = {'transfer_note':'transferred on '+time.ctime()+' from file: '+h5path}
    try:
        # iterate over songs
        for songidx in xrange(nSongs):
            # iterate over getter
            for getter in getters:
                gettername = getter[4:]
                if nSongs > 1:
                    gettername += str(songidx+1)
                data = hdf5_getters.__getattribute__(getter)(h5,songidx)
                matdata[gettername] = data
    except MemoryError:
        print 'Memory Error with file:',h5path
        print 'All data has to be loaded in memory before being saved as matfile'
        print 'Is this an aggregated / summary file with tons of songs?'
        print 'This code is optimized for files containing one song,'
        print 'but write me an email! (TBM)'
        raise
    finally:
        # close h5
        h5.close()
    # create
    sio.savemat(matpath,matdata)
    # all good
    return True



def die_with_usage():
    """ HELP MENU """
    print 'hdf5_to_matfile.py'
    print 'Transform a song file in HDF5 format to a matfile'
    print 'with the same information.'
    print ' '
    print 'usage:'
    print '   python hdf5_to_matfile.py <DIR/FILE>'
    print 'PARAM'
    print '   <DIR/FILE>   if a file TR123.h5, creates TR123.mat in the same dir'
    print '                if a dir, do it for all .h5 files in every subdirectory'
    print ' '
    print 'REQUIREMENTS'
    print '   as usual: HDF5 C library, numpy/scipy, pytables'
    print ' '
    print 'NOTE: the main function is "transfer", you can use it in your script,'
    print 'for instance if you come up with a subset of all songs that are of'
    print 'interest to you, just pass in each song path.'
    print 'Also, data for each song is loaded in memory, can be heavy if you have'
    print 'an aggregated / summary HDF5 file.'
    print ' '
    print 'copyright: T. Bertin-Mahieux (2010) Columbia University'
    print 'tb2332@columbia.edu'
    print 'Million Song Dataset project with LabROSA and the Echo Nest'
    sys.exit(0)

if __name__ == '__main__':

    # HELP MENU
    if len(sys.argv) < 2:
        die_with_usage()

    # GET DIR/FILE
    if not os.path.exists(sys.argv[1]):
        print 'file or dir:',sys.argv[1],'does not exist.'
        sys.exit(0)
    if os.path.isfile(sys.argv[1]):
        if os.path.splitext(sys.argv[1])[1] != '.h5':
            print 'we expect a .h5 extension for file:',sys.argv[1]
            sys.exit(0)
        allh5files = [ os.path.abspath(sys.argv[1]) ]
    elif not os.path.isdir(sys.argv[1]):
        print sys.argv[1],"is neither a file nor a directory? confused... a link? c'est klug?"
        sys.exit(0)
    else:
        allh5files = get_all_files(sys.argv[1],ext='.h5')
    if len(allh5files) == 0:
        print 'no .h5 file found, sorry, check directory you gave us:',sys.argv[1]

    # final sanity checks
    for f in allh5files:
        assert os.path.splitext(f)[1] == '.h5','file with wrong extension? should have been caught earlier... file='+f
    nFiles = len(allh5files)
    if nFiles > 1000:
        print 'you are creating',nFiles,'new matlab files, hope you have the space and time!'

    # let's go!
    cnt = 0
    for f in allh5files:
        filedone = transfer(f)
        if filedone:
            cnt += 1

    # summary report
    print 'we did',cnt,'files out of',len(allh5files)
    if cnt == len(allh5files):
        print 'congratulations!'
    

    

########NEW FILE########
__FILENAME__ = hdf5_utils
"""
Thierry Bertin-Mahieux (2010) Columbia University
tb2332@columbia.edu


This code contains a set of routines to create HDF5 files containing
features and metadata of a song.

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.


Copyright 2010, Thierry Bertin-Mahieux

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""


import os
import sys
import numpy as np
# code relies on pytables, see http://www.pytables.org
import tables
import hdf5_descriptors as DESC
from hdf5_getters import *
# musicbrainz related stuff
try:
    from MBrainzDB import query as QUERYMB
except ImportError:
    print 'need pg module and MBrainzDB folder of Python source code if you'
    print 'want to use musicbrainz related functions, e.g. fill_hdf5_from_musicbrainz'


# description of the different arrays in the song file
ARRAY_DESC_SIMILAR_ARTISTS = 'array of similar artists Echo Nest id'
ARRAY_DESC_ARTIST_TERMS = 'array of terms (Echo Nest tags) for an artist'
ARRAY_DESC_ARTIST_TERMS_FREQ = 'array of term (Echo Nest tags) frequencies for an artist'
ARRAY_DESC_ARTIST_TERMS_WEIGHT = 'array of term (Echo Nest tags) weights for an artist'
ARRAY_DESC_SEGMENTS_START = 'array of start times of segments'
ARRAY_DESC_SEGMENTS_CONFIDENCE = 'array of confidence of segments'
ARRAY_DESC_SEGMENTS_PITCHES = 'array of pitches of segments (chromas)'
ARRAY_DESC_SEGMENTS_TIMBRE = 'array of timbre of segments (MFCC-like)'
ARRAY_DESC_SEGMENTS_LOUDNESS_MAX = 'array of max loudness of segments'
ARRAY_DESC_SEGMENTS_LOUDNESS_MAX_TIME = 'array of max loudness time of segments'
ARRAY_DESC_SEGMENTS_LOUDNESS_START = 'array of loudness of segments at start time'
ARRAY_DESC_SECTIONS_START = 'array of start times of sections'
ARRAY_DESC_SECTIONS_CONFIDENCE = 'array of confidence of sections'
ARRAY_DESC_BEATS_START = 'array of start times of beats'
ARRAY_DESC_BEATS_CONFIDENCE = 'array of confidence of sections'
ARRAY_DESC_BARS_START = 'array of start times of bars'
ARRAY_DESC_BARS_CONFIDENCE = 'array of confidence of bars'
ARRAY_DESC_TATUMS_START = 'array of start times of tatums'
ARRAY_DESC_TATUMS_CONFIDENCE = 'array of confidence of tatums'
ARRAY_DESC_ARTIST_MBTAGS = 'array of tags from MusicBrainz for an artist'
ARRAY_DESC_ARTIST_MBTAGS_COUNT = 'array of tag counts from MusicBrainz for an artist'


def fill_hdf5_from_artist(h5,artist):
    """
    Fill an open hdf5 using all content in a artist object
    from the Echo Nest python API
    There could be overlap with fill_from_song and fill_from_track,
    we assume the data is consistent!
    """
    # get the metadata table, fill it
    metadata = h5.root.metadata.songs
    metadata.cols.artist_id[0] = artist.id
    idsplitter = lambda x,y: x.split(':')[2] if x else y
    metadata.cols.artist_mbid[0] = idsplitter(artist.get_foreign_id(idspace='musicbrainz'),'')
    metadata.cols.artist_playmeid[0] = int(idsplitter(artist.get_foreign_id(idspace='playme'),-1))
    metadata.cols.artist_7digitalid[0] = int(idsplitter(artist.get_foreign_id(idspace='7digital'),-1))
    # fill the metadata arrays
    group = h5.root.metadata
    metadata.cols.idx_similar_artists[0] = 0
    group.similar_artists.append( np.array(map(lambda x : x.id,artist.get_similar(results=100)),dtype='string') )
    metadata.cols.idx_artist_terms[0] = 0
    group.artist_terms.append( np.array(map(lambda x : x.name,artist.get_terms()),dtype='string') )
    group.artist_terms_freq.append( np.array(map(lambda x : x.frequency,artist.get_terms()),dtype='float64') )
    group.artist_terms_weight.append( np.array(map(lambda x : x.weight,artist.get_terms()),dtype='float64') )
    # done, flush
    metadata.flush()
    

def fill_hdf5_from_song(h5,song):
    """
    Fill an open hdf5 using all the content in a song object
    from the Echo Nest python API.
    Usually, fill_hdf5_from_track() will have been called first.
    """
    # get the metadata table, fill it
    metadata = h5.root.metadata.songs
    metadata.cols.artist_familiarity[0] = song.get_artist_familiarity()
    metadata.cols.artist_hotttnesss[0] = song.get_artist_hotttnesss()
    metadata.cols.artist_id[0] = song.artist_id
    metadata.cols.artist_latitude[0] = song.get_artist_location().latitude
    metadata.cols.artist_location[0] = song.get_artist_location().location.encode('utf-8') if song.get_artist_location().location else ''
    metadata.cols.artist_longitude[0] = song.get_artist_location().longitude
    metadata.cols.artist_name[0] = song.artist_name.encode('utf-8') if song.artist_name else ''
    metadata.cols.song_id[0] = song.id
    metadata.cols.song_hotttnesss[0] = song.get_song_hotttnesss()
    metadata.cols.title[0] = song.title.encode('utf-8') if song.title else ''
    metadata.flush()
    # get the analysis table
    analysis = h5.root.analysis.songs
    analysis.danceability = song.get_audio_summary().danceability
    analysis.energy = song.get_audio_summary().energy
    analysis.flush()


def fill_hdf5_from_track(h5,track):
    """
    Fill an open hdf5 using all the content in a track object
    from the Echo Nest python API
    """
    # get the metadata table, fill it
    metadata = h5.root.metadata.songs
    #metadata.cols.analyzer_version[0] = track.analyzer_version
    metadata.cols.artist_name[0] = getattr(track, 'artist', u'').encode('utf-8')
    metadata.cols.release[0] = getattr(track, 'release', u'').encode('utf-8')
    metadata.cols.title[0] = getattr(track, 'title', u'').encode('utf-8')
    idsplitter_7digital = lambda x: int(x.split(':')[2]) if x and x.split(':')[0]=='7digital' else -1
    metadata.cols.release_7digitalid[0] = idsplitter_7digital(track.foreign_release_id)
    metadata.cols.track_7digitalid[0] = idsplitter_7digital(track.foreign_id)
    metadata.flush()
    # get the analysis table, fill it
    analysis = h5.root.analysis.songs
    analysis.cols.analysis_sample_rate[0] = track.analysis_sample_rate
    analysis.cols.audio_md5[0] = track.audio_md5
    analysis.cols.duration[0] = track.duration
    analysis.cols.end_of_fade_in[0] = track.end_of_fade_in
    analysis.cols.key[0] = track.key
    analysis.cols.key_confidence[0] = track.key_confidence
    analysis.cols.loudness[0] = track.loudness
    analysis.cols.mode[0] = track.mode
    analysis.cols.mode_confidence[0] = track.mode_confidence
    analysis.cols.start_of_fade_out[0] = track.start_of_fade_out
    analysis.cols.tempo[0] = track.tempo
    analysis.cols.time_signature[0] = track.time_signature
    analysis.cols.time_signature_confidence[0] = track.time_signature_confidence
    analysis.cols.track_id[0] = track.id
    analysis.flush()
    group = h5.root.analysis
    # analysis arrays (segments)
    analysis.cols.idx_segments_start[0] = 0
    group.segments_start.append( np.array(map(lambda x : x['start'],track.segments),dtype='float64') )
    analysis.cols.idx_segments_confidence[0] = 0
    group.segments_confidence.append( np.array(map(lambda x : x['confidence'],track.segments),dtype='float64') )
    analysis.cols.idx_segments_pitches[0] = 0
    group.segments_pitches.append( np.array(map(lambda x : x['pitches'],track.segments),dtype='float64') )
    analysis.cols.idx_segments_timbre[0] = 0
    group.segments_timbre.append( np.array(map(lambda x : x['timbre'],track.segments),dtype='float64') )
    analysis.cols.idx_segments_loudness_max[0] = 0
    group.segments_loudness_max.append( np.array(map(lambda x : x['loudness_max'],track.segments),dtype='float64') )
    analysis.cols.idx_segments_loudness_max_time[0] = 0
    group.segments_loudness_max_time.append( np.array(map(lambda x : x['loudness_max_time'],track.segments),dtype='float64') )
    analysis.cols.idx_segments_loudness_start[0] = 0
    group.segments_loudness_start.append( np.array(map(lambda x : x['loudness_start'],track.segments),dtype='float64') )
    # analysis arrays (sections)
    analysis.cols.idx_sections_start[0] = 0
    group.sections_start.append( np.array(map(lambda x : x['start'],track.sections),dtype='float64') )
    analysis.cols.idx_sections_confidence[0] = 0
    group.sections_confidence.append( np.array(map(lambda x : x['confidence'],track.sections),dtype='float64') )
    # analysis arrays (beats
    analysis.cols.idx_beats_start[0] = 0
    group.beats_start.append( np.array(map(lambda x : x['start'],track.beats),dtype='float64') )
    analysis.cols.idx_beats_confidence[0] = 0
    group.beats_confidence.append( np.array(map(lambda x : x['confidence'],track.beats),dtype='float64') )
    # analysis arrays (bars)
    analysis.cols.idx_bars_start[0] = 0
    group.bars_start.append( np.array(map(lambda x : x['start'],track.bars),dtype='float64') )
    analysis.cols.idx_bars_confidence[0] = 0
    group.bars_confidence.append( np.array(map(lambda x : x['confidence'],track.bars),dtype='float64') )
    # analysis arrays (tatums)
    analysis.cols.idx_tatums_start[0] = 0
    group.tatums_start.append( np.array(map(lambda x : x['start'],track.tatums),dtype='float64') )
    analysis.cols.idx_tatums_confidence[0] = 0
    group.tatums_confidence.append( np.array(map(lambda x : x['confidence'],track.tatums),dtype='float64') )
    analysis.flush()
    # DONE


def fill_hdf5_from_musicbrainz(h5,connect):
    """
    Fill an open hdf5 using the musicbrainz server and data.
    We assume this code is run after fill_hdf5_from_artist/song
    because we need artist_mbid, artist_name, release and title
    INPUT
       h5        - open song file (append mode)
       connect   - open pg connection to musicbrainz_db
    """
    # get info from h5 song file
    ambid = h5.root.metadata.songs.cols.artist_mbid[0]
    artist_name = h5.root.metadata.songs.cols.artist_name[0]
    release = h5.root.metadata.songs.cols.release[0]
    title = h5.root.metadata.songs.cols.title[0]
    # get the musicbrainz table, fill it
    musicbrainz = h5.root.musicbrainz.songs
    musicbrainz.cols.year[0] = QUERYMB.find_year_safemode(connect,ambid,title,release,artist_name)
    # fill the musicbrainz arrays
    group = h5.root.musicbrainz
    musicbrainz.cols.idx_artist_mbtags[0] = 0
    tags,tagcount = QUERYMB.get_artist_tags(connect, ambid, maxtags=20)
    group.artist_mbtags.append( np.array(tags,dtype='string') )
    group.artist_mbtags_count.append( np.array(tagcount,dtype='float64') )
    # done, flush
    musicbrainz.flush()


def fill_hdf5_aggregate_file(h5,h5_filenames,summaryfile=False):
    """
    Fill an open hdf5 aggregate file using all the content from all the HDF5 files
    listed as filenames. These HDF5 files are supposed to be filled already.
    Usefull to create one big HDF5 file from many, thus improving IO speed.
    For most of the info, we simply use one row per song.
    For the arrays (e.g. segment_start) we need the indecies (e.g. idx_segment_start)
    to know which part of the array belongs to one particular song.
    If summaryfile=True, we skip arrays (indices all 0)
    """
    # counter
    counter = 0
    # iterate over filenames
    for h5idx,h5filename in enumerate(h5_filenames):
        # open h5 file
        h5tocopy = open_h5_file_read(h5filename)
        # get number of songs in new file
        nSongs = get_num_songs(h5tocopy)
        # iterate over songs in one HDF5 (1 if regular file, more if aggregate file)
        for songidx in xrange(nSongs):
            # METADATA
            row = h5.root.metadata.songs.row
            row["artist_familiarity"] = get_artist_familiarity(h5tocopy,songidx)
            row["artist_hotttnesss"] = get_artist_hotttnesss(h5tocopy,songidx)
            row["artist_id"] = get_artist_id(h5tocopy,songidx)
            row["artist_mbid"] = get_artist_mbid(h5tocopy,songidx)
            row["artist_playmeid"] = get_artist_playmeid(h5tocopy,songidx)
            row["artist_7digitalid"] = get_artist_7digitalid(h5tocopy,songidx)
            row["artist_latitude"] = get_artist_latitude(h5tocopy,songidx)
            row["artist_location"] = get_artist_location(h5tocopy,songidx)
            row["artist_longitude"] = get_artist_longitude(h5tocopy,songidx)
            row["artist_name"] = get_artist_name(h5tocopy,songidx)
            row["release"] = get_release(h5tocopy,songidx)
            row["release_7digitalid"] = get_release_7digitalid(h5tocopy,songidx)
            row["song_id"] = get_song_id(h5tocopy,songidx)
            row["song_hotttnesss"] = get_song_hotttnesss(h5tocopy,songidx)
            row["title"] = get_title(h5tocopy,songidx)
            row["track_7digitalid"] = get_track_7digitalid(h5tocopy,songidx)
            # INDICES
            if not summaryfile:
                if counter == 0 : # we're first row
                    row["idx_similar_artists"] = 0
                    row["idx_artist_terms"] = 0
                else:
                    row["idx_similar_artists"] = h5.root.metadata.similar_artists.shape[0]
                    row["idx_artist_terms"] = h5.root.metadata.artist_terms.shape[0]
            row.append()
            h5.root.metadata.songs.flush()
            # ARRAYS
            if not summaryfile:
                h5.root.metadata.similar_artists.append( get_similar_artists(h5tocopy,songidx) )
                h5.root.metadata.artist_terms.append( get_artist_terms(h5tocopy,songidx) )
                h5.root.metadata.artist_terms_freq.append( get_artist_terms_freq(h5tocopy,songidx) )
                h5.root.metadata.artist_terms_weight.append( get_artist_terms_weight(h5tocopy,songidx) )
            # ANALYSIS
            row = h5.root.analysis.songs.row
            row["analysis_sample_rate"] = get_analysis_sample_rate(h5tocopy,songidx)
            row["audio_md5"] = get_audio_md5(h5tocopy,songidx)
            row["danceability"] = get_danceability(h5tocopy,songidx)
            row["duration"] = get_duration(h5tocopy,songidx)
            row["end_of_fade_in"] = get_end_of_fade_in(h5tocopy,songidx)
            row["energy"] = get_energy(h5tocopy,songidx)
            row["key"] = get_key(h5tocopy,songidx)
            row["key_confidence"] = get_key_confidence(h5tocopy,songidx)
            row["loudness"] = get_loudness(h5tocopy,songidx)
            row["mode"] = get_mode(h5tocopy,songidx)
            row["mode_confidence"] = get_mode_confidence(h5tocopy,songidx)
            row["start_of_fade_out"] = get_start_of_fade_out(h5tocopy,songidx)
            row["tempo"] = get_tempo(h5tocopy,songidx)
            row["time_signature"] = get_time_signature(h5tocopy,songidx)
            row["time_signature_confidence"] = get_time_signature_confidence(h5tocopy,songidx)
            row["track_id"] = get_track_id(h5tocopy,songidx)
            # INDICES
            if not summaryfile:
                if counter == 0 : # we're first row
                    row["idx_segments_start"] = 0
                    row["idx_segments_confidence"] = 0
                    row["idx_segments_pitches"] = 0
                    row["idx_segments_timbre"] = 0
                    row["idx_segments_loudness_max"] = 0
                    row["idx_segments_loudness_max_time"] = 0
                    row["idx_segments_loudness_start"] = 0
                    row["idx_sections_start"] = 0
                    row["idx_sections_confidence"] = 0
                    row["idx_beats_start"] = 0
                    row["idx_beats_confidence"] = 0
                    row["idx_bars_start"] = 0
                    row["idx_bars_confidence"] = 0
                    row["idx_tatums_start"] = 0
                    row["idx_tatums_confidence"] = 0
                else : # check the current shape of the arrays
                    row["idx_segments_start"] = h5.root.analysis.segments_start.shape[0]
                    row["idx_segments_confidence"] = h5.root.analysis.segments_confidence.shape[0]
                    row["idx_segments_pitches"] = h5.root.analysis.segments_pitches.shape[0]
                    row["idx_segments_timbre"] = h5.root.analysis.segments_timbre.shape[0]
                    row["idx_segments_loudness_max"] = h5.root.analysis.segments_loudness_max.shape[0]
                    row["idx_segments_loudness_max_time"] = h5.root.analysis.segments_loudness_max_time.shape[0]
                    row["idx_segments_loudness_start"] = h5.root.analysis.segments_loudness_start.shape[0]
                    row["idx_sections_start"] = h5.root.analysis.sections_start.shape[0]
                    row["idx_sections_confidence"] = h5.root.analysis.sections_confidence.shape[0]
                    row["idx_beats_start"] = h5.root.analysis.beats_start.shape[0]
                    row["idx_beats_confidence"] = h5.root.analysis.beats_confidence.shape[0]
                    row["idx_bars_start"] = h5.root.analysis.bars_start.shape[0]
                    row["idx_bars_confidence"] = h5.root.analysis.bars_confidence.shape[0]
                    row["idx_tatums_start"] = h5.root.analysis.tatums_start.shape[0]
                    row["idx_tatums_confidence"] = h5.root.analysis.tatums_confidence.shape[0]
            row.append()
            h5.root.analysis.songs.flush()
            # ARRAYS
            if not summaryfile:
                h5.root.analysis.segments_start.append( get_segments_start(h5tocopy,songidx) )
                h5.root.analysis.segments_confidence.append( get_segments_confidence(h5tocopy,songidx) )
                h5.root.analysis.segments_pitches.append( get_segments_pitches(h5tocopy,songidx) )
                h5.root.analysis.segments_timbre.append( get_segments_timbre(h5tocopy,songidx) )
                h5.root.analysis.segments_loudness_max.append( get_segments_loudness_max(h5tocopy,songidx) )
                h5.root.analysis.segments_loudness_max_time.append( get_segments_loudness_max_time(h5tocopy,songidx) )
                h5.root.analysis.segments_loudness_start.append( get_segments_loudness_start(h5tocopy,songidx) )
                h5.root.analysis.sections_start.append( get_sections_start(h5tocopy,songidx) )
                h5.root.analysis.sections_confidence.append( get_sections_confidence(h5tocopy,songidx) )
                h5.root.analysis.beats_start.append( get_beats_start(h5tocopy,songidx) )
                h5.root.analysis.beats_confidence.append( get_beats_confidence(h5tocopy,songidx) )
                h5.root.analysis.bars_start.append( get_bars_start(h5tocopy,songidx) )
                h5.root.analysis.bars_confidence.append( get_bars_confidence(h5tocopy,songidx) )
                h5.root.analysis.tatums_start.append( get_tatums_start(h5tocopy,songidx) )
                h5.root.analysis.tatums_confidence.append( get_tatums_confidence(h5tocopy,songidx) )
            # MUSICBRAINZ
            row = h5.root.musicbrainz.songs.row
            row["year"] = get_year(h5tocopy,songidx)
            # INDICES
            if not summaryfile:
                if counter == 0 : # we're first row
                    row["idx_artist_mbtags"] = 0
                else:
                    row["idx_artist_mbtags"] = h5.root.musicbrainz.artist_mbtags.shape[0]
            row.append()
            h5.root.musicbrainz.songs.flush()
            # ARRAYS
            if not summaryfile:
                h5.root.musicbrainz.artist_mbtags.append( get_artist_mbtags(h5tocopy,songidx) )
                h5.root.musicbrainz.artist_mbtags_count.append( get_artist_mbtags_count(h5tocopy,songidx) )
            # counter
            counter += 1
        # close h5 file
        h5tocopy.close()


def create_song_file(h5filename,title='H5 Song File',force=False,complevel=1):
    """
    Create a new HDF5 file for a new song.
    If force=False, refuse to overwrite an existing file
    Raise a ValueError if it's the case.
    Other optional param is the H5 file.
    Setups the groups, each containing a table 'songs' with one row:
    - metadata
    - analysis
    DETAIL
    - we set the compression level to 1 by default, it uses the ZLIB library
      to disable compression, set it to 0
    """
    # check if file exists
    if not force:
        if os.path.exists(h5filename):
            raise ValueError('file exists, can not create HDF5 song file')
    # create the H5 file
    h5 = tables.openFile(h5filename, mode='w', title='H5 Song File')
    # set filter level
    h5.filters = tables.Filters(complevel=complevel,complib='zlib')
    # setup the groups and tables
        # group metadata
    group = h5.createGroup("/",'metadata','metadata about the song')
    table = h5.createTable(group,'songs',DESC.SongMetaData,'table of metadata for one song')
    r = table.row
    r.append() # filled with default values 0 or '' (depending on type)
    table.flush()
        # group analysis
    group = h5.createGroup("/",'analysis','Echo Nest analysis of the song')
    table = h5.createTable(group,'songs',DESC.SongAnalysis,'table of Echo Nest analysis for one song')
    r = table.row
    r.append() # filled with default values 0 or '' (depending on type)
    table.flush()
        # group musicbrainz
    group = h5.createGroup("/",'musicbrainz','data about the song coming from MusicBrainz')
    table = h5.createTable(group,'songs',DESC.SongMusicBrainz,'table of data coming from MusicBrainz')
    r = table.row
    r.append() # filled with default values 0 or '' (depending on type)
    table.flush()
    # create arrays
    create_all_arrays(h5,expectedrows=3)
    # close it, done
    h5.close()


def create_aggregate_file(h5filename,title='H5 Aggregate File',force=False,expectedrows=1000,complevel=1,
                          summaryfile=False):
    """
    Create a new HDF5 file for all songs.
    It will contains everything that are in regular song files.
    Tables created empty.
    If force=False, refuse to overwrite an existing file
    Raise a ValueError if it's the case.
    If summaryfile=True, creates a sumary file, i.e. no arrays
    Other optional param is the H5 file.
    DETAILS
    - if you create a very large file, try to approximate correctly
      the number of data points (songs), it speeds things up with arrays (by
      setting the chunking correctly).
    - we set the compression level to 1 by default, it uses the ZLIB library
      to disable compression, set it to 0

    Setups the groups, each containing a table 'songs' with one row:
    - metadata
    - analysis
    """
    # check if file exists
    if not force:
        if os.path.exists(h5filename):
            raise ValueError('file exists, can not create HDF5 song file')
    # summary file? change title
    if summaryfile:
        title = 'H5 Summary File'
    # create the H5 file
    h5 = tables.openFile(h5filename, mode='w', title='H5 Song File')
    # set filter level
    h5.filters = tables.Filters(complevel=complevel,complib='zlib')
    # setup the groups and tables
        # group metadata
    group = h5.createGroup("/",'metadata','metadata about the song')
    table = h5.createTable(group,'songs',DESC.SongMetaData,'table of metadata for one song',
                           expectedrows=expectedrows)
        # group analysis
    group = h5.createGroup("/",'analysis','Echo Nest analysis of the song')
    table = h5.createTable(group,'songs',DESC.SongAnalysis,'table of Echo Nest analysis for one song',
                           expectedrows=expectedrows)
        # group musicbrainz
    group = h5.createGroup("/",'musicbrainz','data about the song coming from MusicBrainz')
    table = h5.createTable(group,'songs',DESC.SongMusicBrainz,'table of data coming from MusicBrainz',
                           expectedrows=expectedrows)
    # create arrays
    if not summaryfile:
        create_all_arrays(h5,expectedrows=expectedrows)
    # close it, done
    h5.close()


def create_all_arrays(h5,expectedrows=1000):
    """
    Utility functions used by both create_song_file and create_aggregate_files,
    creates all the EArrays (empty).
    INPUT
       h5   - hdf5 file, open with write or append permissions
              metadata and analysis groups already exist!
    """
    # group metadata arrays
    group = h5.root.metadata
    h5.createEArray(where=group,name='similar_artists',atom=tables.StringAtom(20,shape=()),shape=(0,),title=ARRAY_DESC_SIMILAR_ARTISTS)
    h5.createEArray(group,'artist_terms',tables.StringAtom(256,shape=()),(0,),ARRAY_DESC_ARTIST_TERMS,
                    expectedrows=expectedrows*40)
    h5.createEArray(group,'artist_terms_freq',tables.Float64Atom(shape=()),(0,),ARRAY_DESC_ARTIST_TERMS_FREQ,
                    expectedrows=expectedrows*40)
    h5.createEArray(group,'artist_terms_weight',tables.Float64Atom(shape=()),(0,),ARRAY_DESC_ARTIST_TERMS_WEIGHT,
                    expectedrows=expectedrows*40)
    # group analysis arrays
    group = h5.root.analysis
    h5.createEArray(where=group,name='segments_start',atom=tables.Float64Atom(shape=()),shape=(0,),title=ARRAY_DESC_SEGMENTS_START)
    h5.createEArray(group,'segments_confidence',tables.Float64Atom(shape=()),(0,),ARRAY_DESC_SEGMENTS_CONFIDENCE,
                    expectedrows=expectedrows*300)
    h5.createEArray(group,'segments_pitches',tables.Float64Atom(shape=()),(0,12),ARRAY_DESC_SEGMENTS_PITCHES,
                    expectedrows=expectedrows*300)
    h5.createEArray(group,'segments_timbre',tables.Float64Atom(shape=()),(0,12),ARRAY_DESC_SEGMENTS_TIMBRE,
                    expectedrows=expectedrows*300)
    h5.createEArray(group,'segments_loudness_max',tables.Float64Atom(shape=()),(0,),ARRAY_DESC_SEGMENTS_LOUDNESS_MAX,
                    expectedrows=expectedrows*300)
    h5.createEArray(group,'segments_loudness_max_time',tables.Float64Atom(shape=()),(0,),ARRAY_DESC_SEGMENTS_LOUDNESS_MAX_TIME,
                    expectedrows=expectedrows*300)
    h5.createEArray(group,'segments_loudness_start',tables.Float64Atom(shape=()),(0,),ARRAY_DESC_SEGMENTS_LOUDNESS_START,
                    expectedrows=expectedrows*300)
    h5.createEArray(group,'sections_start',tables.Float64Atom(shape=()),(0,),ARRAY_DESC_SECTIONS_START,
                    expectedrows=expectedrows*300)
    h5.createEArray(group,'sections_confidence',tables.Float64Atom(shape=()),(0,),ARRAY_DESC_SECTIONS_CONFIDENCE,
                    expectedrows=expectedrows*300)
    h5.createEArray(group,'beats_start',tables.Float64Atom(shape=()),(0,),ARRAY_DESC_BEATS_START,
                    expectedrows=expectedrows*300)
    h5.createEArray(group,'beats_confidence',tables.Float64Atom(shape=()),(0,),ARRAY_DESC_BEATS_CONFIDENCE,
                    expectedrows=expectedrows*300)
    h5.createEArray(group,'bars_start',tables.Float64Atom(shape=()),(0,),ARRAY_DESC_BARS_START,
                    expectedrows=expectedrows*300)
    h5.createEArray(group,'bars_confidence',tables.Float64Atom(shape=()),(0,),ARRAY_DESC_BARS_CONFIDENCE,
                    expectedrows=expectedrows*300)
    h5.createEArray(group,'tatums_start',tables.Float64Atom(shape=()),(0,),ARRAY_DESC_TATUMS_START,
                    expectedrows=expectedrows*300)
    h5.createEArray(group,'tatums_confidence',tables.Float64Atom(shape=()),(0,),ARRAY_DESC_TATUMS_CONFIDENCE,
                    expectedrows=expectedrows*300)
    # group musicbrainz arrays
    group = h5.root.musicbrainz
    h5.createEArray(where=group,name='artist_mbtags',atom=tables.StringAtom(256,shape=()),shape=(0,),title=ARRAY_DESC_ARTIST_MBTAGS,
                    expectedrows=expectedrows*5)
    h5.createEArray(group,'artist_mbtags_count',tables.IntAtom(shape=()),(0,),ARRAY_DESC_ARTIST_MBTAGS_COUNT,
                    expectedrows=expectedrows*5)


def open_h5_file_read(h5filename):
    """
    Open an existing H5 in read mode.
    """
    return tables.openFile(h5filename, mode='r')

def open_h5_file_append(h5filename):
    """
    Open an existing H5 in append mode.
    """
    return tables.openFile(h5filename, mode='a')


################################################ MAIN #####################################

def die_with_usage():
    """ HELP MENU """
    print 'hdf5_utils.py'
    print 'by T. Bertin-Mahieux (2010) Columbia University'
    print ''
    print 'should be used as a library, contains functions to create'
    print 'HDF5 files for the Million Song Dataset project'
    sys.exit(0)


if __name__ == '__main__':

    # help menu
    die_with_usage()



########NEW FILE########
__FILENAME__ = query
"""
Thierry Bertin-Mahieux (2010) Columbia University
tb2332@columbia.edu

This code query the musicbrainz database to get some information
like musicbrainz id and release years.
The databased in installed locally.

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.


Copyright 2010, Thierry Bertin-Mahieux

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import pg
import glob
import numpy as np

USER='gordon'
PASSWD='gordon'


def encode_string(s):
    """
    Simple utility function to make sure a string is proper
    to be used in a SQL query
    EXAMPLE:
      That's my boy! -> N'That''s my boy!'
    """
    res = "N'"+s.replace("'","''")+"'"
    res = res.replace("\\''","''")
    res = res.replace("\''","''")
    return res


def connect_mbdb():
    """
    Simple connection to the musicbrainz database, returns a pgobject
    Return None if there is a problem
    """
    try:
        connect = pg.connect('musicbrainz_db','localhost',-1,None,None,
                             USER,PASSWD)
    except TypeError, e:
        print 'CONNECT_MBDB: type error, should not happen:',e
        return None
    except SyntaxError, e:
        print 'CONNECT_MBDB: syntax error, should not happen:',e
        return None
    except pg.InternalError, e:
        print 'CONNECT_MBDB, internal error:', e
        return None
    # check for levenshtein function
    #q = "SELECT levenshtein('allo','allo2')"
    #try:
    #    res = connect.query(q)
    #except pg.ProgrammingError:
    #    print 'we need levenshtein (contrib) added to the database:'
    #    print 'psql -d musicbrainz_db -f /usr/share/postgresql/8.4/contrib/fuzzystrmatch.sq'
    #    connect.close()
    #    return None
    # done
    return connect


def find_year_safemode(connect,artist_mbid,title,release,artist):
    """
    This is the main function for the creation of the MillionSongDataset
    We get a year value only if we have a recognized musicbrainz id
    and an exact match on either the title or the release (lowercase).
    Other possibility, exact match on title and artist_name or
    release_and artist_name
    INPUT
        artist_mbid   string or None          artist musicbrainz id
        title         string                  track name
        release       string ('' if unknown)  album name
        artist        string                  artist name
    RETURN 0 or year as a int
    """
    # case where we have no musicbrainz_id for the artist
    if artist_mbid is None or artist_mbid == '':
        return find_year_safemode_nombid(connect,title,release,artist)
    q = "SELECT artist id FROM artist WHERE gid='"+artist_mbid+"'"
    res = connect.query(q)
    if len(res.getresult()) == 0: # mb does not know that ID... yes it happens
        return find_year_safemode_nombid(connect,title,release,artist)
    # find all album release dates from albums from tracks that match artist, title, and release
    # i.e. we take all the tracks found in the previous query, check their album names
    # and if an album name matches 'release', we take its release date
    # if more than one match, take earliest year
    # CHECK commented lines if you also want to return the track.id
    q = "SELECT min(release.releasedate) FROM track INNER JOIN artist"
    #q = "SELECT release.releasedate,track.gid FROM track INNER JOIN artist"
    q += " ON artist.gid='"+artist_mbid+"' AND artist.id=track.artist"
    q += " AND lower(track.name)="+encode_string(title.lower())
    q += " INNER JOIN albumjoin ON albumjoin.track=track.id"
    q += " INNER JOIN album ON album.id=albumjoin.album"
    q += " INNER JOIN release ON release.album=album.id"
    q += " AND release.releasedate!='0000-00-00' LIMIT 1"
    #q += " AND release.releasedate!='0000-00-00' ORDER BY release.releasedate LIMIT 1"
    res = connect.query(q)
    if not res.getresult()[0][0] is None:
        return int(res.getresult()[0][0].split('-')[0])
    # we relax the condition that we have to find an exact string match for the title
    # if we find the good album name (our 'release' param)
    #q = "SELECT min(release.releasedate) FROM artist INNER JOIN album"
    q = "SELECT min(release.releasedate) FROM artist INNER JOIN album"
    q += " ON artist.gid='"+artist_mbid+"' AND artist.id=album.artist"
    q += " AND lower(album.name)="+encode_string(release.lower())
    q += " INNER JOIN release ON release.album=album.id"
    q += " AND release.releasedate!='0000-00-00' LIMIT 1"
    res = connect.query(q)
    if not res.getresult()[0][0] is None:
        return int(res.getresult()[0][0].split('-')[0])
    # not found
    return 0


def find_year_safemode_nombid(connect,title,release,artist):
    """
    We try to get a year for a particular track without musicbrainz id
    for the artist.
    We get only if we have a perfect match either for (artist_name / title)
    or (artist_name / release)
    RETURN 0 if not found, or year as int
    """
    # find all albums based on tracks found by exact track title match
    # return the earliest release year of one of these albums
    q = "SELECT min(release.releasedate) FROM track INNER JOIN artist"
    q += " ON lower(artist.name)="+encode_string(artist.lower())+" AND artist.id=track.artist"
    q += " AND lower(track.name)="+encode_string(title.lower())
    q += " INNER JOIN albumjoin ON albumjoin.track=track.id"
    q += " INNER JOIN album ON album.id=albumjoin.album"
    q += " INNER JOIN release ON release.album=album.id"
    q += " AND release.releasedate!='0000-00-00' LIMIT 1"
    res = connect.query(q)
    if not res.getresult()[0][0] is None:
        return int(res.getresult()[0][0].split('-')[0])    
    # we relax the condition that we have to find an exact string match for the title
    # if we find the good album name (our 'release' param)
    q = "SELECT min(release.releasedate) FROM artist INNER JOIN album"
    q += " ON lower(artist.name)="+encode_string(artist.lower())+" AND artist.id=album.artist"
    q += " AND lower(album.name)="+encode_string(release.lower())
    q += " INNER JOIN release ON release.album=album.id"
    q += " AND release.releasedate!='0000-00-00' LIMIT 1"
    res = connect.query(q)
    if not res.getresult()[0][0] is None:
        return int(res.getresult()[0][0].split('-')[0])
    # not found
    return 0


def get_artist_tags(connect, artist_mbid, maxtags=20):
    """
    Get the musicbrainz tags and tag count given a musicbrainz
    artist. Returns two list of length max 'maxtags'
    Always return two lists, eventually empty
    """
    if artist_mbid is None or artist_mbid == '':
        return [],[]
    # find all tags
    q = "SELECT tag.name,artist_tag.count FROM artist"
    q += " INNER JOIN artist_tag ON artist.id=artist_tag.artist"
    q += " INNER JOIN tag ON tag.id=artist_tag.tag"
    q += " WHERE artist.gid='"+artist_mbid+"'"
    q += " ORDER BY count DESC LIMIT "+str(maxtags)
    res = connect.query(q)
    if len(res.getresult()) == 0:
        return [],[]
    return map(lambda x: x[0],res.getresult()),map(lambda x: x[1],res.getresult())


def debug_from_song_file(connect,h5path,verbose=0):
    """
    Slow debugging function that takes a h5 file, reads the info,
    check the match with musicbrainz db, prints out the result.
    Only prints when we dont get exact match!
    RETURN counts of how many files we filled for years, tags
    """
    import hdf5_utils as HDF5
    import hdf5_getters as GETTERS
    h5 = HDF5.open_h5_file_read(h5path)
    title = GETTERS.get_title(h5)
    release = GETTERS.get_release(h5)
    artist = GETTERS.get_artist_name(h5)
    ambid = GETTERS.get_artist_mbid(h5)
    h5.close()
    # mbid
    gotmbid=1
    if ambid=='':
        gotmbid = 0
        if verbose>0: print 'no mb id for:',artist
    # year
    year = find_year_safemode(connect,ambid,title,release,artist)
    gotyear = 1 if year > 0 else 0
    if verbose>0: print 'no years for:',artist,'|',release,'|',title
    # tags
    tags,counts = get_artist_tags(connect,ambid)
    gottags = 1 if len(tags) > 0 else 0
    if gottags == 0 and verbose>0: print 'no tags for:',artist
    # return indicator for mbid, year, tag
    return gotmbid,gotyear,gottags


def die_with_usage():
    """ HELP MENU """
    print 'This contains library functions to query the musicbrainz database'
    print 'For debugging:'
    print '    python query.py -hdf5 <list of songs>'
    print '    e.g. python query.py -hdf5 MillionSong/A/A/*/*.h5'
    sys.exit(0)


if __name__ == '__main__':

    # help menu
    if len(sys.argv) < 2:
        die_with_usage()

    # DEBUGGING
    verbose=0
    while True:
        if sys.argv[1]=='-verbose':
            verbose=1
        else:
            break
        sys.argv.pop(1)
    
    if sys.argv[1] == '-hdf5':
        import time
        import datetime
        sys.path.append( os.path.abspath('..') )
        connect = connect_mbdb()
        paths = sys.argv[2:]
        t1 = time.time()
        cntmbid = 0
        cntyears = 0
        cnttags = 0
        for p in paths:
            mbid,year,tag = debug_from_song_file(connect,p,verbose=verbose)
            cntmbid += mbid
            cntyears += year
            cnttags += tag
        connect.close()
        t2 = time.time()
        stimelength = str(datetime.timedelta(seconds=t2-t1))
        print 'has musicbrainz id for',cntmbid,'out of',len(paths)
        print 'found years for',cntyears,'out of',len(paths)
        print 'found tags for',cnttags,'out of',len(paths)
        print 'all done in',stimelength
        sys.exit(0)



########NEW FILE########
__FILENAME__ = process_test_set
"""
Thierry Bertin-Mahieux (2011) Columbia University
tb2332@columbia.edu

Code to parse the whole testing set using a trained KNN
and predict an artist.

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.

Copyright (c) 2011, Thierry Bertin-Mahieux, All Rights Reserved

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import time
import glob
import copy
import tables
import sqlite3
import datetime
import multiprocessing
import numpy as np
from operator import itemgetter
import hdf5_getters as GETTERS
import process_train_set as TRAIN # for the features
try:
    import scikits.ann as ANN
except ImportError:
    print 'you need scikits.ann: http://www.scipy.org/scipy/scikits/wiki/AnnWrapper'
    sys.exit(0)
    
# error passing problems, useful for multiprocessing
class KeyboardInterruptError(Exception):pass

def fullpath_from_trackid(maindir,trackid):
    """ Creates proper file paths for song files """
    p = os.path.join(maindir,trackid[2])
    p = os.path.join(p,trackid[3])
    p = os.path.join(p,trackid[4])
    p = os.path.join(p,trackid+'.h5')
    return str(p)

def get_all_files(basedir,ext='.h5'):
    """
    From a root directory, go through all subdirectories
    and find all files with the given extension.
    Return all absolute paths in a list.
    """
    allfiles = []
    apply_to_all_files(basedir,func=lambda x: allfiles.append(x),ext=ext)
    return allfiles


def apply_to_all_files(basedir,func=lambda x: x,ext='.h5'):
    """
    From a root directory, go through all subdirectories
    and find all files with the given extension.
    Apply the given function func
    If no function passed, does nothing and counts file
    Return number of files
    """
    cnt = 0
    for root, dirs, files in os.walk(basedir):
        files = glob.glob(os.path.join(root,'*'+ext))
        for f in files :
            func(f)
            cnt += 1
    return cnt


def compute_features(h5):
    """
    Get the same features than during training
    """
    return TRAIN.compute_features(h5)
    

def do_prediction(processed_feats,kd,h5model,K=1):
    """
    Receive processed features from test set, apply KNN,
    return an actual predicted year (float)
    INPUT
       processed_feats - extracted from a test song
                    kd - ANN kdtree on top of model
               h5model - open h5 file with data.feats and data.year
                     K - K-nn parameter
    """
    res = kd.knn(processed_feats,K)
    if K == 1:
        index = res[0][0]
        pred_artist_id = h5model.root.data.artist_id[index]
    else:
        # find artist with most results
        # if tie, the one that was the highest ranking wins
        indices = res[0].flatten()
        artists = {}
        for pos,i in enumerate(indices):
            artist_id = h5model.root.data.artist_id[i]
            if not artist_id in artists.keys():
                artists[artist_id] = [1,-pos]
            else:
                artists[artist_id][0] += 1
        tuples = zip(artists.keys(),artists.values())
        res = sorted(tuples,key=itemgetter(1),reverse=True)
        pred_artist_id = res[0][0]
    # done
    return pred_artist_id
    

def process_filelist_test(filelist=None,model=None,tmpfilename=None,K=1):
    """
    Main function, process all files in the list (as long as their track_id
    is not in testsongs)
    INPUT
       filelist     - a list of song files
       model        - h5 file containing feats and artist_id for all train songs
       tmpfilename  - where to save our processed features
       K            - K-nn parameter (default=1)
    """
    # sanity check
    for arg in locals().values():
        assert not arg is None,'process_filelist_train, missing an argument, something still None'
    if os.path.isfile(tmpfilename):
        print 'ERROR: file',tmpfilename,'already exists.'
        return
    if not os.path.isfile(model):
        print 'ERROR: model',model,'does not exist.'
        return
    # dimension fixed (12-dimensional timbre vector)
    ndim = 12
    finaldim = 90
    # create kdtree
    h5model = tables.openFile(model, mode='r')
    assert h5model.root.data.feats.shape[1]==finaldim,'inconsistency in final dim'
    kd = ANN.kdtree(h5model.root.data.feats)
    # create outputfile
    output = tables.openFile(tmpfilename, mode='a')
    group = output.createGroup("/",'data','TMP FILE FOR ARTIST RECOGNITION')
    output.createEArray(group,'artist_id_real',tables.StringAtom(18,shape=()),(0,),'',
                        expectedrows=len(filelist))
    output.createEArray(group,'artist_id_pred',tables.StringAtom(18,shape=()),(0,),'',
                        expectedrows=len(filelist))
    # iterate over files
    cnt_f = 0
    for f in filelist:
        cnt_f += 1
        # verbose
        if cnt_f % 50000 == 0:
            print 'training... checking file #',cnt_f
        # check what file/song is this
        h5 = GETTERS.open_h5_file_read(f)
        artist_id = GETTERS.get_artist_id(h5)
        track_id = GETTERS.get_track_id(h5)
        if track_id in testsongs: # just in case, but should not be necessary
            print 'Found test track_id during training? weird.',track_id
            h5.close()
            continue
        # extract features, then close file
        processed_feats = compute_features(h5)
        h5.close()
        if processed_feats is None:
            continue
        # do prediction
        artist_id_pred = do_prediction(processed_feats,kd,h5model,K)
        # save features to tmp file
        output.root.data.artist_id_real.append( np.array( [artist_id] ) )
        output.root.data.artist_id_pred.append( np.array( [artist_id_pred] ) )
    # we're done, close output
    output.close()
    return

            
def process_filelist_test_wrapper(args):
    """ wrapper function for multiprocessor, calls process_filelist_test """
    try:
        process_filelist_test(**args)
    except KeyboardInterrupt:
        raise KeyboardInterruptError()


def process_filelist_test_main_pass(nthreads,model,testsongs,K):
    """
    Do the main walk through the data, deals with the threads,
    creates the tmpfiles.
    INPUT
      - nthreads     - number of threads to use
      - model        - h5 files containing feats and artist_id for all train songs
      - testsongs    - set of songs to ignore
      - K            - K-nn parameter
    RETURN
      - tmpfiles     - list of tmpfiles that were created
                       or None if something went wrong
    """
    # sanity checks
    assert nthreads >= 0,'Come on, give me at least one thread!'
    # prepare params for each thread
    params_list = []
    default_params = {'model':model,'K':K}
    tmpfiles_stub = 'mainpasstest_artistrec_tmp_output_'
    tmpfiles = map(lambda x: os.path.join(os.path.abspath('.'),tmpfiles_stub+str(x)+'.h5'),range(nthreads))
    nfiles_per_thread = int(np.ceil(len(testsongs) * 1. / nthreads))
    for k in range(nthreads):
        # params for one specific thread
        p = copy.deepcopy(default_params)
        p['tmpfilename'] = tmpfiles[k]
        p['filelist'] = testsongs[k*nfiles_per_thread:(k+1)*nfiles_per_thread]
        params_list.append(p)
    # launch, run all the jobs
    pool = multiprocessing.Pool(processes=nthreads)
    try:
        pool.map(process_filelist_test_wrapper, params_list)
        pool.close()
        pool.join()
    except KeyboardInterruptError:
        print 'MULTIPROCESSING'
        print 'stopping multiprocessing due to a keyboard interrupt'
        pool.terminate()
        pool.join()
        return None
    except Exception, e:
        print 'MULTIPROCESSING'
        print 'got exception: %r, terminating the pool' % (e,)
        pool.terminate()
        pool.join()
        return None
    # all done!
    return tmpfiles


def test(nthreads,model,testsongs,K):
    """
    Main function to do the training
    Do the main pass with the number of given threads.
    Then, reads the tmp files, creates the main output, delete the tmpfiles.
    INPUT
      - nthreads     - number of threads to use
      - model        - h5 files containing feats and artist_id for all train songs
      - testsongs    - set of songs to ignore
      - K            - K-nn parameter
    RETURN
       - nothing :)
    """
    # initial time
    t1 = time.time()
    # do main pass
    tmpfiles = process_filelist_test_main_pass(nthreads,model,testsongs,K)
    if tmpfiles is None:
        print 'Something went wrong, tmpfiles are None'
        return
    # intermediate time
    t2 = time.time()
    stimelen = str(datetime.timedelta(seconds=t2-t1))
    print 'Main pass done after',stimelen; sys.stdout.flush()
    # aggregate temp files
    artist_id_found = 0
    total_predictions = 0
    for tmpf in tmpfiles:
        h5 = tables.openFile(tmpf)
        for k in range( h5.root.data.artist_id_real.shape[0] ):
            total_predictions += 1
            if h5.root.data.artist_id_real[k] == h5.root.data.artist_id_pred[k]:
                artist_id_found += 1
        h5.close()
        # delete tmp file
        os.remove(tmpf)
    # final time
    t3 = time.time()
    stimelen = str(datetime.timedelta(seconds=t3-t1))
    print 'Whole testing done after',stimelen
    # results
    print 'We found the right artist_id',artist_id_found,'times out of',total_predictions,'predictions.'
    print 'e.g., accuracy is:',artist_id_found*1./total_predictions
    # done
    return


def die_with_usage():
    """ HELP MENU """
    print 'process_test_set.py'
    print '   by T. Bertin-Mahieux (2011) Columbia University'
    print '      tb2332@columbia.edu'
    print 'Code to perform artist recognition on the Million Song Dataset.'
    print 'This performs the evaluation of a trained KNN model.'
    print 'REQUIRES ANN LIBRARY and its python wrapper.'
    print 'USAGE:'
    print '  python process_test_set.py [FLAGS] <MSD_DIR> <model> <testsongs> <tmdb>'
    print 'PARAMS:'
    print '        MSD_DIR  - main directory of the MSD dataset'
    print '          model  - h5 file where the training is saved'
    print '      testsongs  - file containing test songs (to ignore)'
    print '           tmdb  - path to track_metadata.db'
    print 'FLAGS:'
    print '           -K n  - K-nn parameter (default=1)'
    print '    -nthreads n  - number of threads to use (default: 1)'
    sys.exit(0)


if __name__ == '__main__':

    # help menu
    if len(sys.argv) < 5:
        die_with_usage()

    # flags
    nthreads = 1
    K = 1
    while True:
        if sys.argv[1] == '-nthreads':
            nthreads = int(sys.argv[2])
            sys.argv.pop(1)
        elif sys.argv[1] == '-K':
            K = int(sys.argv[2])
            sys.argv.pop(1)
        else:
            break
        sys.argv.pop(1)

    # params
    msd_dir = sys.argv[1]
    model = sys.argv[2]
    testsongs = sys.argv[3]
    tmdb = sys.argv[4]

    # sanity check
    assert os.path.isdir(msd_dir),'ERROR: dir '+msd_dir+' does not exist.'
    assert os.path.isfile(testsongs),'ERROR: file '+testsongs+' does not exist.'
    assert os.path.isfile(model),'ERROR: file '+model+' does not exist.'
    assert os.path.isfile(tmdb),'ERROR: file '+tmdb+' does not exist.'

    # read test artists
    if not os.path.isfile(testsongs):
        print 'ERROR:',testsongs,'does not exist.'
        sys.exit(0)
    testsongs_set = set()
    f = open(testsongs,'r')
    for line in f.xreadlines():
        if line == '' or line.strip() == '':
            continue
        testsongs_set.add( line.strip().split('<SEP>')[0] )
    f.close()
    testsongs_list = map(lambda x: fullpath_from_trackid(msd_dir,x), testsongs_set)

    # settings
    print 'msd dir:',msd_dir
    print 'testsongs:',testsongs,'('+str(len(testsongs_set))+' songs)'
    print 'tmdb:',tmdb
    print 'nthreads:',nthreads
    print 'K:',K

    # launch testing
    test(nthreads,model,testsongs_list,K)

    # done
    print 'DONE!'

########NEW FILE########
__FILENAME__ = process_train_set
"""
Thierry Bertin-Mahieux (2011) Columbia University
tb2332@columbia.edu

Code to parse the whole training set, get a summary of the features,
and save them in a KNN-ready format.

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.

Copyright (c) 2011, Thierry Bertin-Mahieux, All Rights Reserved

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import time
import glob
import copy
import tables
import sqlite3
import datetime
import multiprocessing
import numpy as np
import hdf5_getters as GETTERS


# error passing problems, useful for multiprocessing
class KeyboardInterruptError(Exception):pass


def fullpath_from_trackid(maindir,trackid):
    """ Creates proper file paths for song files """
    p = os.path.join(maindir,trackid[2])
    p = os.path.join(p,trackid[3])
    p = os.path.join(p,trackid[4])
    p = os.path.join(p,trackid+'.h5')
    return str(p)

def get_all_files(basedir,ext='.h5'):
    """
    From a root directory, go through all subdirectories
    and find all files with the given extension.
    Return all absolute paths in a list.
    """
    allfiles = []
    apply_to_all_files(basedir,func=lambda x: allfiles.append(x),ext=ext)
    return allfiles


def apply_to_all_files(basedir,func=lambda x: x,ext='.h5'):
    """
    From a root directory, go through all subdirectories
    and find all files with the given extension.
    Apply the given function func
    If no function passed, does nothing and counts file
    Return number of files
    """
    cnt = 0
    for root, dirs, files in os.walk(basedir):
        files = glob.glob(os.path.join(root,'*'+ext))
        for f in files :
            func(f)
            cnt += 1
    return cnt


def compute_features(h5):
    """
    From an open HDF5 song file, extract average and covariance of the
    timbre vectors.
    RETURN 1x90 vector or None if there is a problem
    """
    feats = GETTERS.get_segments_timbre(h5).T
    # features length
    ftlen = feats.shape[1]
    ndim = feats.shape[0]
    assert ndim==12,'WRONG DEATURE DIMENSION, transpose issue?'
    finaldim = 90
    # too small case
    if ftlen < 3:
        return None
    # avg
    avg = np.average(feats,1)
    # cov
    cov = np.cov(feats)
    covflat = []
    for k in range(12):
        covflat.extend( np.diag(cov,k) )
    covflat = np.array(covflat)
    # concatenate avg and cov
    feats = np.concatenate([avg,covflat])
    # done, reshape & return
    return feats.reshape(1,finaldim)
    
    

def process_filelist_train(filelist=None,testsongs=None,tmpfilename=None):
    """
    Main function, process all files in the list (as long as their track_id
    is not in testsongs)
    INPUT
       filelist     - a list of song files
       testsongs    - set of track ID that we should not use
       tmpfilename  - where to save our processed features
    """
    # sanity check
    for arg in locals().values():
        assert not arg is None,'process_filelist_train, missing an argument, something still None'
    if os.path.isfile(tmpfilename):
        print 'ERROR: file',tmpfilename,'already exists.'
        return
    # dimension fixed (12-dimensional timbre vector)
    ndim = 12
    finaldim = 90
    # create outputfile
    output = tables.openFile(tmpfilename, mode='a')
    group = output.createGroup("/",'data','TMP FILE FOR ARTIST RECOGNITION')
    output.createEArray(group,'feats',tables.Float64Atom(shape=()),(0,finaldim),'',
                        expectedrows=len(filelist))
    output.createEArray(group,'artist_id',tables.StringAtom(18,shape=()),(0,),'',
                        expectedrows=len(filelist))
    # iterate over files
    cnt_f = 0
    for f in filelist:
        cnt_f += 1
        # verbose
        if cnt_f % 50000 == 0:
            print 'training... checking file #',cnt_f
        # check what file/song is this
        h5 = GETTERS.open_h5_file_read(f)
        artist_id = GETTERS.get_artist_id(h5)
        track_id = GETTERS.get_track_id(h5)
        if track_id in testsongs: # just in case, but should not be necessary
            print 'Found test track_id during training? weird.',track_id
            h5.close()
            continue
        # extract features, then close file
        processed_feats = compute_features(h5)
        h5.close()
        if processed_feats is None:
            continue
        # save features to tmp file
        output.root.data.artist_id.append( np.array( [artist_id] ) )
        output.root.data.feats.append( processed_feats )
    # we're done, close output
    output.close()
    return

            
def process_filelist_train_wrapper(args):
    """ wrapper function for multiprocessor, calls process_filelist_train """
    try:
        process_filelist_train(**args)
    except KeyboardInterrupt:
        raise KeyboardInterruptError()


def process_filelist_train_main_pass(nthreads,maindir,testsongs,trainsongs=None):
    """
    Do the main walk through the data, deals with the threads,
    creates the tmpfiles.
    INPUT
      - nthreads     - number of threads to use
      - maindir      - dir of the MSD, wehre to find song files
      - testsongs    - set of songs to ignore
      - trainsongs   - list of files to use for training (faster!)
    RETURN
      - tmpfiles     - list of tmpfiles that were created
                       or None if something went wrong
    """
    # sanity checks
    assert nthreads >= 0,'Come on, give me at least one thread!'
    if not os.path.isdir(maindir):
        print 'ERROR: directory',maindir,'does not exist.'
        return None
    # get all files
    if trainsongs is None:
        allfiles = get_all_files(maindir)
    else:
        allfiles = trainsongs
    assert len(allfiles)>0,'Come on, give me at least one file in '+maindir+'!'
    if nthreads > len(allfiles):
        nthreads = len(allfiles)
        print 'more threads than files, reducing number of threads to:',nthreads
    print 'WE HAVE',len(allfiles),'POTENTIAL TRAIN FILES'
    # prepare params for each thread
    params_list = []
    default_params = {'testsongs':testsongs}
    tmpfiles_stub = 'mainpass_artistrec_tmp_output_'
    tmpfiles = map(lambda x: os.path.join(os.path.abspath('.'),tmpfiles_stub+str(x)+'.h5'),range(nthreads))
    nfiles_per_thread = int(np.ceil(len(allfiles) * 1. / nthreads))
    for k in range(nthreads):
        # params for one specific thread
        p = copy.deepcopy(default_params)
        p['tmpfilename'] = tmpfiles[k]
        p['filelist'] = allfiles[k*nfiles_per_thread:(k+1)*nfiles_per_thread]
        params_list.append(p)
    # launch, run all the jobs
    pool = multiprocessing.Pool(processes=nthreads)
    try:
        pool.map(process_filelist_train_wrapper, params_list)
        pool.close()
        pool.join()
    except KeyboardInterruptError:
        print 'MULTIPROCESSING'
        print 'stopping multiprocessing due to a keyboard interrupt'
        pool.terminate()
        pool.join()
        return None
    except Exception, e:
        print 'MULTIPROCESSING'
        print 'got exception: %r, terminating the pool' % (e,)
        pool.terminate()
        pool.join()
        return None
    # all done!
    return tmpfiles


def train(nthreads,maindir,output,testsongs,trainsongs=None):
    """
    Main function to do the training
    Do the main pass with the number of given threads.
    Then, reads the tmp files, creates the main output, delete the tmpfiles.
    INPUT
      - nthreads     - number of threads to use
      - maindir      - dir of the MSD, wehre to find song files
      - output       - main model, contains everything to perform KNN
      - testsongs    - set of songs to ignore
      - trainsongs   - list of songs to use for training (FASTER)
    RETURN
       - nothing :)
    """
    # sanity checks
    if os.path.isfile(output):
        print 'ERROR: file',output,'already exists.'
        return
    # initial time
    t1 = time.time()
    # do main pass
    tmpfiles = process_filelist_train_main_pass(nthreads,maindir,testsongs,trainsongs=trainsongs)
    if tmpfiles is None:
        print 'Something went wrong, tmpfiles are None'
        return
    # intermediate time
    t2 = time.time()
    stimelen = str(datetime.timedelta(seconds=t2-t1))
    print 'Main pass done after',stimelen; sys.stdout.flush()
    # find approximate number of rows per tmpfiles
    h5 = tables.openFile(tmpfiles[0],'r')
    nrows = h5.root.data.artist_id.shape[0] * len(tmpfiles)
    h5.close()
    # create output
    output = tables.openFile(output, mode='a')
    group = output.createGroup("/",'data','KNN MODEL FILE FOR ARTIST RECOGNITION')
    output.createEArray(group,'feats',tables.Float64Atom(shape=()),(0,90),'feats',
                        expectedrows=nrows)
    output.createEArray(group,'artist_id',tables.StringAtom(18,shape=()),(0,),'artist_id',
                        expectedrows=nrows)
    # aggregate temp files
    for tmpf in tmpfiles:
        h5 = tables.openFile(tmpf)
        output.root.data.artist_id.append( h5.root.data.artist_id[:] )
        output.root.data.feats.append( h5.root.data.feats[:] )
        h5.close()
        # delete tmp file
        os.remove(tmpf)
    # close output
    output.close()
    # final time
    t3 = time.time()
    stimelen = str(datetime.timedelta(seconds=t3-t1))
    print 'Whole training done after',stimelen
    # done
    return


def die_with_usage():
    """ HELP MENU """
    print 'process_train_set.py'
    print '   by T. Bertin-Mahieux (2011) Columbia University'
    print '      tb2332@columbia.edu'
    print 'Code to perform artist recognition on the Million Song Dataset.'
    print 'This performs the training of the KNN model.'
    print 'USAGE:'
    print '  python process_train_set.py [FLAGS] <MSD_DIR> <testsongs> <tmdb> <output>'
    print 'PARAMS:'
    print '        MSD_DIR  - main directory of the MSD dataset'
    print '      testsongs  - file containing test songs (to ignore)'
    print '           tmdb  - path to track_metadata.db'
    print '         output  - output filename (.h5 file)'
    print 'FLAGS:'
    print '    -nthreads n  - number of threads to use (default: 1)'
    print '     -onlytesta  - only train on test artists (makes problem easier!!!)'
    sys.exit(0)


if __name__ == '__main__':

    # help menu
    if len(sys.argv) < 5:
        die_with_usage()

    # flags
    nthreads = 1
    onlytesta = False
    while True:
        if sys.argv[1] == '-nthreads':
            nthreads = int(sys.argv[2])
            sys.argv.pop(1)
        elif sys.argv[1] == '-onlytesta':
            onlytesta = True
        else:
            break
        sys.argv.pop(1)

    # params
    msd_dir = sys.argv[1]
    testsongs = sys.argv[2]
    tmdb = sys.argv[3]
    output = sys.argv[4]

    # read test artists
    if not os.path.isfile(testsongs):
        print 'ERROR:',testsongs,'does not exist.'
        sys.exit(0)
    testsongs_set = set()
    f = open(testsongs,'r')
    for line in f.xreadlines():
        if line == '' or line.strip() == '':
            continue
        testsongs_set.add( line.strip().split('<SEP>')[0] )
    f.close()

    # get songlist from track_metadata.db
    # some SQL magic required
    trainsongs = None
    assert os.path.isfile(tmdb),'Database: '+tmdb+' does not exist.'
    conn = sqlite3.connect(tmdb)
    q = "CREATE TEMP TABLE testsongs (track_id TEXT)" # we'll put all test track_id here
    res = conn.execute(q)
    conn.commit()
    for tid in testsongs_set:
        q = "INSERT INTO testsongs VALUES ('"+tid+"')"
        conn.execute(q)
    conn.commit()
    q = "CREATE TEMP TABLE trainsongs (track_id TEXT)" # we'll put all train track_id here
    res = conn.execute(q)
    conn.commit()
    if not onlytesta:# every song that is not a test song (harder!)
        q = "INSERT INTO trainsongs SELECT DISTINCT track_id FROM songs"
        q += " EXCEPT SELECT track_id FROM testsongs"
        res = conn.execute(q)
    else: # only songs from artist that we test (easier!)
        q = "CREATE TEMP TABLE testartists (artist_id TEXT)" # we'll put test artists here
        res = conn.execute(q)
        conn.commit()
        q = "INSERT INTO testartists SELECT DISTINCT artist_id FROM songs"
        q += " JOIN testsongs ON testsongs.track_id=songs.track_id"
        conn.execute(q)
        conn.commit()
        # now we have test artists, get songs only from these ones
        q = "INSERT INTO trainsongs SELECT DISTINCT track_id FROM songs"
        q += " JOIN testartists ON songs.artist_id=testartists.artist_id"
        q += " EXCEPT SELECT track_id FROM testsongs"
        conn.execute(q)
    conn.commit()
    q = "SELECT track_id FROM trainsongs"
    res = conn.execute(q)
    data = res.fetchall()
    conn.close()
    print 'Found',len(data),'training files from track_metadata.db'
    trainsongs = map(lambda x: fullpath_from_trackid(msd_dir,x[0]),data)
    assert os.path.isfile(trainsongs[0]),'first training file does not exist? '+trainsongs[0]

    # settings
    print 'msd dir:',msd_dir
    print 'output:',output
    print 'testsongs:',testsongs,'('+str(len(testsongs_set))+' songs)'
    print 'trainsongs: got',len(trainsongs),'songs'
    print 'tmdb:',tmdb
    print 'nthreads:',nthreads
    print 'onlytesta:',onlytesta

    # sanity checks
    if not os.path.isdir(msd_dir):
        print 'ERROR:',msd_dir,'is not a directory.'
        sys.exit(0)
    if os.path.isfile(output):
        print 'ERROR: file',output,'already exists.'
        sys.exit(0)

    # launch training
    train(nthreads,msd_dir,output,testsongs_set,trainsongs)

    # done
    print 'DONE!'

########NEW FILE########
__FILENAME__ = split_train_test
"""
Thierry Bertin-Mahieux (2010) Columbia University
tb2332@columbia.edu

Code to split the list of songs for artist recognition.

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.


Copyright 2010, Thierry Bertin-Mahieux

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import time
import glob
from operator import itemgetter
import numpy as np
import sqlite3

# random seed, note that we actually use hash(RNDSEED) so it can be anything
RNDSEED='caitlin'
# number of songs required to consider an artist
NUMSONGS=20

def die_with_usage():
    """ HELP MENU """
    print 'split_train_test.py'
    print '  by T. Bertin-Mahieux (2010) Columbia University'
    print '     tb2332@columbia.edu'
    print 'GOAL'
    print '  Split the list of songs into train and test for artist recognition.'
    print '  We only consider artists with at least 20 songs.'
    print '  The training set consists of 15 songs from each of these artists.'
    print 'USAGE'
    print '  python split_train_test.py <track_metadata.db> <train.txt> <test.txt>'
    print 'PARAMS'
    print ' track_metadata.db    - SQLite database containing metadata for each track'
    print '         train.txt    - list of Echo Nest artist ID'
    print '          test.txt    - list of Echo Nest artist ID'
    print 'NOTE: this gives a train set of 271,095 songs and a test set of 532,300 songs.'
    print '      See songs_train.txt and songs_test.txt.'
    sys.exit(0)


if __name__ == '__main__':

    # help menu
    if len(sys.argv)<4:
        die_with_usage()

    # params
    dbfile = sys.argv[1]
    output_train = sys.argv[2]
    output_test = sys.argv[3]

    # sanity checks
    if not os.path.isfile(dbfile):
        print 'ERROR: database not found:',dbfile
        sys.exit(0)
    if os.path.exists(output_train):
        print 'ERROR:',output_train,'already exists! delete or provide a new name'
        sys.exit(0)
    if os.path.exists(output_test):
        print 'ERROR:',output_test,'already exists! delete or provide a new name'
        sys.exit(0)

    # open connection
    conn = sqlite3.connect(dbfile)

    # get artists with their number of songs
    q = "SELECT artist_id,Count(track_id) FROM songs GROUP BY artist_id"
    res = conn.execute(q)
    data = res.fetchall()
    sorted_artists = sorted(data,key=itemgetter(1,0),reverse=True)

    # find the last artist with that many songs
    last_pos = np.where(np.array(map(lambda x: x[1],sorted_artists))>=NUMSONGS)[0][-1]
    print 'We have',last_pos+1,'artists with at least',NUMSONGS,'songs.'

    # open output files
    ftrain = open(output_train,'w')
    ftest = open(output_test,'w')

    # random seed
    np.random.seed(hash(RNDSEED))

    # iterate over these artists
    for aid,nsongs in sorted_artists[:last_pos+1]:
        # get songs
        q = "SELECT track_id FROM songs WHERE artist_id='"+aid+"'"
        res = conn.execute(q)
        tracks = map(lambda x: x[0], res.fetchall())
        assert len(tracks)==nsongs,'ERROR: num songs should be '+str(nsongs)+' for '+aid+', got: '+str(len(tracks))
        tracks = sorted(tracks)
        np.random.shuffle(tracks)
        for t in tracks[:15]:
            ftrain.write(t+'<SEP>'+aid+'\n')
        for t in tracks[15:]:
            ftest.write(t+'<SEP>'+aid+'\n')
            
    # close files
    ftrain.close()
    ftest.close()
    
    # close connection
    conn.close()

    # done
    print 'DONE!'

########NEW FILE########
__FILENAME__ = split_train_test_unbalanced
"""
Thierry Bertin-Mahieux (2010) Columbia University
tb2332@columbia.edu

Code to split the list of songs for artist recognition.
This split is unbalanced! e.g. the percentage of songs per artist
in the training set is not the same.
This split should be easier than the regular one:
- larger training set
- non uniform prior on the artists

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.


Copyright 2010, Thierry Bertin-Mahieux

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import time
import glob
from operator import itemgetter
import numpy as np
import sqlite3

# random seed, note that we actually use hash(RNDSEED) so it can be anything
RNDSEED='caitlin'
# number of songs required to consider an artist
NUMSONGS=20

def die_with_usage():
    """ HELP MENU """
    print 'split_train_test_unbalanced.py'
    print '  by T. Bertin-Mahieux (2010) Columbia University'
    print '     tb2332@columbia.edu'
    print 'GOAL'
    print '  Split the list of songs into train and test for artist recognition.'
    print '  We only consider artists with at least 20 songs.'
    print '  The training set consists of 2/3 of all songs from each of these artists.'
    print 'USAGE'
    print '  python split_train_test_unbalanced.py <track_metadata.db> <train.txt> <test.txt>'
    print 'PARAMS'
    print ' track_metadata.db    - SQLite database containing metadata for each track'
    print '         train.txt    - list of Echo Nest artist ID'
    print '          test.txt    - list of Echo Nest artist ID'
    print 'NOTE: this gives a train set of 541,892 songs and a test set of 261,503 songs.'
    print '      See songs_train_unbalanced.txt and songs_test_unbalanced.txt.'
    sys.exit(0)


if __name__ == '__main__':

    # help menu
    if len(sys.argv)<4:
        die_with_usage()

    # params
    dbfile = sys.argv[1]
    output_train = sys.argv[2]
    output_test = sys.argv[3]

    # sanity checks
    if not os.path.isfile(dbfile):
        print 'ERROR: database not found:',dbfile
        sys.exit(0)
    if os.path.exists(output_train):
        print 'ERROR:',output_train,'already exists! delete or provide a new name'
        sys.exit(0)
    if os.path.exists(output_test):
        print 'ERROR:',output_test,'already exists! delete or provide a new name'
        sys.exit(0)

    # open connection
    conn = sqlite3.connect(dbfile)

    # get artists with their number of songs
    q = "SELECT artist_id,Count(track_id) FROM songs GROUP BY artist_id"
    res = conn.execute(q)
    data = res.fetchall()
    sorted_artists = sorted(data,key=itemgetter(1,0),reverse=True)

    # find the last artist with that many songs
    last_pos = np.where(np.array(map(lambda x: x[1],sorted_artists))>=NUMSONGS)[0][-1]
    print 'We have',last_pos+1,'artists with at least',NUMSONGS,'songs.'

    # open output files
    ftrain = open(output_train,'w')
    ftest = open(output_test,'w')

    # random seed
    np.random.seed(hash(RNDSEED))

    # iterate over these artists
    for aid,nsongs in sorted_artists[:last_pos+1]:
        # get songs
        q = "SELECT track_id FROM songs WHERE artist_id='"+aid+"'"
        res = conn.execute(q)
        tracks = map(lambda x: x[0], res.fetchall())
        assert len(tracks)==nsongs,'ERROR: num songs should be '+str(nsongs)+' for '+aid+', got: '+str(len(tracks))
        tracks = sorted(tracks)
        np.random.shuffle(tracks)
        two_thirds = int(np.ceil(len(tracks) * 2./3.))
        for t in tracks[:two_thirds]:
            ftrain.write(t+'<SEP>'+aid+'\n')
        for t in tracks[two_thirds:]:
            ftest.write(t+'<SEP>'+aid+'\n')
            
    # close files
    ftrain.close()
    ftest.close()
    
    # close connection
    conn.close()

    # done
    print 'DONE!'

########NEW FILE########
__FILENAME__ = finding_duplicates
#!/usr/bin/env python
"""
Thierry Bertin-Mahieux (2011) Columbia University
tb2332@columbia.edu

This code identifies duplicate songs in the database that
are 'easy to find', usually same artist and title or song id.

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.

Copyright 2011, Thierry Bertin-Mahieux

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import time
import datetime
import sqlite3
import numpy as np


def create_cliques(data):
    """
    Always receive an array of arrays, each sub array has 3 elements:
        - artist (id or name)
        - song (id or title)
        - track id
    From that, create cluster (or clique) that have the first two
    elements in common. We asusme they are duplicates.
    We rely on the python hash() function, we assume no collisions.
    Returns a dictionary: int -> [tracks], int are arbitrary
    """
    cnt_clique = 0
    clique_tracks = {}
    for d1,d2,tid in data:
        hashval = hash(d1+d2)
        if hashval in clique_tracks.keys():
            clique_tracks[hashval].append(tid)
        else:
            clique_tracks[hashval] = [tid]
    return clique_tracks


def merge_cliques(clique1,clique2):
    """
    Merge two sets of cliques, return a new dictionary
    of clique. As always, dict keys are random.
    """
    # copy clique1 into new one
    new_clique = {}
    new_clique.update( zip( range(1,len(clique1)+1), clique1.values() ) )
    clique_id = len(clique1)
    # reverse index
    tid_clique = {}
    for clique,tids in new_clique.items():
        for tid in tids:
            tid_clique[tid] = clique
    # move on to second one
    for clique,tids in clique2.items():
        clique_ids = []
        for tid in tids:
            if tid in tid_clique.keys():
                c = tid_clique[tid]
                if not c in clique_ids:
                    clique_ids.append( c )
        # new clique
        if len(clique_ids) == 0:
            clique_id += 1
            new_clique[clique_id] = tids
        # easy, add to one clique
        elif len(clique_ids) == 1:
            cid = clique_ids[0]
            for tid in tids:
                if not tid in new_clique[cid]:
                    new_clique[cid].append( tid )
        # merge more than one clique
        else:
            # merge the clique
            cid = min(clique_ids)
            for c in clique_ids:
                if c != cid:
                    tids_to_move = new_clique[c]
                    for t in tids_to_move:
                        tid_clique[t] = cid
                    new_clique[cid].extend(tids_to_move)
                    new_clique.pop(c)
            # add to the clique cid
            for tid in tids:
                if not tid in new_clique[cid]:
                    new_clique[cid].append( tid )
    # done
    return new_clique



def die_with_usage():
    """ HELP MENU """
    print 'finding_duplicates.py'
    print '    by T. Bertin-Mahieux (2011) Columbia University'
    print '       tb2332@columbia.edu'
    print ''
    print 'This code identify a list of duplicate songs in the dataset.'
    print 'These duplicates are easy to find, in the sense that they have'
    print 'the same artist and title. WE DO NOT FIND ALL DUPLICATES!'
    print ''
    print 'USAGE'
    print '   python finding_duplicates.py <tmdb> <output>'
    print 'PARAMS'
    print '     tmdb   - track_metadata.py'
    print '   output   - text file with duplicates'
    sys.exit(0)


if __name__ == '__main__':

    # help menu
    if len(sys.argv) < 3:
        die_with_usage()

    # params
    tmdb = sys.argv[1]
    outputf = sys.argv[2]

    # sanity checks
    if not os.path.isfile(tmdb):
        print 'ERROR:',tmdb,'does not exist.'
        sys.exit(0)
    if os.path.isfile(outputf):
        print 'ERROR:',outputf,'already exists.'
        sys.exit(0)

    # open sqlite connection
    conn = sqlite3.connect(tmdb)
    
    # get same artist_name, same title
    t1 = time.time()
    q = "CREATE TEMP TABLE tmp_aname_title (aname TEXT, title TEXT, ntid INT)"
    conn.execute(q); conn.commit()
    q = "INSERT INTO tmp_aname_title SELECT artist_name, title, COUNT(track_id)"
    q += " FROM songs GROUP BY artist_name, title"
    conn.execute(q); conn.commit()
    q = "CREATE INDEX idx_tmp_aname_title ON tmp_aname_title ('ntid','aname','title')"
    conn.execute(q); conn.commit()
    q = "SELECT artist_name,songs.title,songs.track_id FROM songs"
    q += " JOIN tmp_aname_title ON aname=artist_name AND songs.title=tmp_aname_title.title"
    q += " WHERE tmp_aname_title.ntid>1"
    res = conn.execute(q)
    data = res.fetchall()
    # get cliques
    cliques1 = create_cliques(data)
    t2 = time.time()
    print '********************************************************'
    print 'Found duplicates artist name / title in',str(datetime.timedelta(seconds=t2-t1))
    print 'We got',sum(map(lambda tids: len(tids), cliques1.values())),'tracks in',len(cliques1),'cliques.'

    # get same artist id, same title
    t1 = time.time()
    q = "CREATE TEMP TABLE tmp_aid_title (aid TEXT, title TEXT, ntid INT)"
    conn.execute(q); conn.commit()
    q = "INSERT INTO tmp_aid_title SELECT artist_id, title, COUNT(track_id)"
    q += " FROM songs GROUP BY artist_id, title"
    conn.execute(q); conn.commit()
    q = "CREATE INDEX idx_tmp_aid_title ON tmp_aid_title ('ntid','aid','title')"
    conn.execute(q); conn.commit()
    q = "SELECT artist_id,songs.title,songs.track_id FROM songs"
    q += " JOIN tmp_aid_title ON aid=artist_id AND songs.title=tmp_aid_title.title"
    q += " WHERE tmp_aid_title.ntid>1"
    res = conn.execute(q)
    data = res.fetchall()
    # get cliques
    cliques2 = create_cliques(data)
    t2 = time.time()
    print '********************************************************'
    print 'Found duplicates artist id / title in',str(datetime.timedelta(seconds=t2-t1))
    print 'We got',sum(map(lambda tids: len(tids), cliques2.values())),'tracks in',len(cliques2),'cliques.'
    final_cliques = merge_cliques(cliques1,cliques2)
    print 'After merge, got',sum(map(lambda tids: len(tids), final_cliques.values())),'tracks in',len(final_cliques),'cliques.'

    # get same artist name, same song id
    t1 = time.time()
    q = "CREATE TEMP TABLE tmp_aname_sid (aname TEXT, sid TEXT, ntid INT)"
    conn.execute(q); conn.commit()
    q = "INSERT INTO tmp_aname_sid SELECT artist_name, song_id, COUNT(track_id)"
    q += " FROM songs GROUP BY artist_name, song_id"
    conn.execute(q); conn.commit()
    q = "CREATE INDEX idx_tmp_aname_sid ON tmp_aname_sid ('ntid','aname','sid')"
    conn.execute(q); conn.commit()
    q = "SELECT artist_name,songs.song_id,songs.track_id FROM songs"
    q += " JOIN tmp_aname_sid ON aname=artist_name AND songs.song_id=tmp_aname_sid.sid"
    q += " WHERE tmp_aname_sid.ntid>1"
    res = conn.execute(q)
    data = res.fetchall()
    # get cliques
    cliques3 = create_cliques(data)
    t2 = time.time()
    print '********************************************************'
    print 'Found duplicates artist name / song id in',str(datetime.timedelta(seconds=t2-t1))
    print 'We got',sum(map(lambda tids: len(tids), cliques3.values())),'tracks in',len(cliques3),'cliques.'
    final_cliques = merge_cliques(final_cliques,cliques3)
    print 'After merge, got',sum(map(lambda tids: len(tids), final_cliques.values())),'tracks in',len(final_cliques),'cliques.'

    # get same artist id, same song id
    t1 = time.time()
    q = "CREATE TEMP TABLE tmp_aid_sid (aid TEXT, sid TEXT, ntid INT)"
    conn.execute(q); conn.commit()
    q = "INSERT INTO tmp_aid_sid SELECT artist_id, song_id, COUNT(track_id)"
    q += " FROM songs GROUP BY artist_id, song_id"
    conn.execute(q); conn.commit()
    q = "CREATE INDEX idx_tmp_aid_sid ON tmp_aid_sid ('ntid','aid','sid')"
    conn.execute(q); conn.commit()
    q = "SELECT artist_id,songs.song_id,songs.track_id FROM songs"
    q += " JOIN tmp_aid_sid ON aid=artist_id AND songs.song_id=tmp_aid_sid.sid"
    q += " WHERE tmp_aid_sid.ntid>1"
    res = conn.execute(q)
    data = res.fetchall()
    # get cliques
    cliques4 = create_cliques(data)
    t2 = time.time()
    print '********************************************************'
    print 'Found duplicates artist id / song id in',str(datetime.timedelta(seconds=t2-t1))
    print 'We got',sum(map(lambda tids: len(tids), cliques4.values())),'tracks in',len(cliques4),'cliques.'
    final_cliques = merge_cliques(final_cliques,cliques4)
    print 'After merge, got',sum(map(lambda tids: len(tids), final_cliques.values())),'tracks in',len(final_cliques),'cliques.'


    # write output
    output = open(outputf,'w')
    output.write('# MILLION SONG DATASET - DUPLICATES\n')
    output.write('#    created by T. Bertin-Mahieux, Columbia University\n')
    output.write('#               tb2332@columbia.edu\n')
    output.write('#       on '+time.ctime()+'\n')
    output.write('# List of duplicates from artist names / artist id and\n')
    output.write('# titles / song id.\n')
    for clique,trackids in final_cliques.items():
        q = "SELECT artist_name,title FROM songs WHERE track_id='"+trackids[0]+"' LIMIT 1"
        res = conn.execute(q)
        aname,title = res.fetchone()
        output.write('%'+str(clique)+' '+aname.encode('utf-8')+' - '+title.encode('utf-8')+'\n')
        for tid in trackids:
            output.write(tid + '\n')
    output.close()

    # close connection
    conn.close()


    

########NEW FILE########
__FILENAME__ = beat_aligned_feats
"""
Thierry Bertin-Mahieux (2011) Columbia University
tb2332@columbia.edu

Subset of the code to get beat-aligned features
from the HDF5 song files of the Million Song Dataset.

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.


Copyright 2011, Thierry Bertin-Mahieux
parts of this code from Ron J. Weiss

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import time
import glob
import numpy as np
try:
    import hdf5_getters as GETTERS
except ImportError:
    print 'cannot find file hdf5_getters.py'
    print 'you must put MSongsDB/PythonSrc in your path or import it otherwise'
    raise


def get_btchromas(h5):
    """
    Get beat-aligned chroma from a song file of the Million Song Dataset
    INPUT:
       h5          - filename or open h5 file
    RETURN:
       btchromas   - beat-aligned chromas, one beat per column
                     or None if something went wrong (e.g. no beats)
    """
    # if string, open and get chromas, if h5, get chromas
    if type(h5).__name__ == 'str':
        h5 = GETTERS.open_h5_file_read(h5)
        chromas = GETTERS.get_segments_pitches(h5)
        segstarts = GETTERS.get_segments_start(h5)
        btstarts = GETTERS.get_beats_start(h5)
        duration = GETTERS.get_duration(h5)
        h5.close()
    else:
        chromas = GETTERS.get_segments_pitches(h5)
        segstarts = GETTERS.get_segments_start(h5)
        btstarts = GETTERS.get_beats_start(h5)
        duration = GETTERS.get_duration(h5)
    # get the series of starts for segments and beats
    # NOTE: MAYBE USELESS?
    # result for track: 'TR0002Q11C3FA8332D'
    #    segstarts.shape = (708,)
    #    btstarts.shape = (304,)
    segstarts = np.array(segstarts).flatten()
    btstarts = np.array(btstarts).flatten()
    # aligned features
    btchroma = align_feats(chromas.T, segstarts, btstarts, duration)
    if btchroma is None:
        return None
    # Renormalize. Each column max is 1.
    maxs = btchroma.max(axis=0)
    maxs[np.where(maxs == 0)] = 1.
    btchroma = (btchroma / maxs)
    # done
    return btchroma


def get_btloudnessmax(h5):
    """
    Get beat-aligned loudness max from a song file of the Million Song Dataset
    INPUT:
       h5             - filename or open h5 file
    RETURN:
       btloudnessmax  - beat-aligned loudness max, one beat per column
                        or None if something went wrong (e.g. no beats)
    """
    # if string, open and get max loudness, if h5, get max loudness
    if type(h5).__name__ == 'str':
        h5 = GETTERS.open_h5_file_read(h5)
        loudnessmax = GETTERS.get_segments_loudness_max(h5)
        segstarts = GETTERS.get_segments_start(h5)
        btstarts = GETTERS.get_beats_start(h5)
        duration = GETTERS.get_duration(h5)
        h5.close()
    else:
        loudnessmax = GETTERS.get_segments_loudness_max(h5)
        segstarts = GETTERS.get_segments_start(h5)
        btstarts = GETTERS.get_beats_start(h5)
        duration = GETTERS.get_duration(h5)
    # get the series of starts for segments and beats
    # NOTE: MAYBE USELESS?
    # result for track: 'TR0002Q11C3FA8332D'
    #    segstarts.shape = (708,)
    #    btstarts.shape = (304,)
    segstarts = np.array(segstarts).flatten()
    btstarts = np.array(btstarts).flatten()
    # reverse dB
    loudnessmax = idB(loudnessmax)
    # aligned features
    btloudnessmax = align_feats(loudnessmax.reshape(1,
                                                    loudnessmax.shape[0]),
                                segstarts, btstarts, duration)
    if btloudnessmax is None:
        return None
    # set it back to dB
    btloudnessmax = dB(btloudnessmax + 1e-10)
    # done (no renormalization)
    return btloudnessmax


def align_feats(feats, segstarts, btstarts, duration):
    """
    MAIN FUNCTION: aligned whatever matrix of features is passed,
    one column per segment, and interpolate them to get features
    per beat.
    Note that btstarts could be anything, e.g. bar starts
    INPUT
       feats      - matrix of features, one column per segment
       segstarts  - segments starts in seconds,
                    dim must match feats # cols (flatten ndarray)
       btstarts   - beat starts in seconds (flatten ndarray)
       duration   - overall track duration in seconds
    RETURN
       btfeats    - features, one column per beat
                    None if there is a problem
    """
    # sanity check
    if feats.shape[0] == 0 or feats.shape[1] == 0:
        return None
    if btstarts.shape[0] == 0 or segstarts.shape[0] == 0:
        return None

    # FEAT PER BEAT
    # Move segment feature onto a regular grid
    # result for track: 'TR0002Q11C3FA8332D'
    #    warpmat.shape = (304, 708)
    #    btchroma.shape = (304, 12)
    warpmat = get_time_warp_matrix(segstarts, btstarts, duration)
    featchroma = np.dot(warpmat, feats.T).T
    if featchroma.shape[1] == 0: # sanity check
        return None

    # done
    return featchroma


def get_time_warp_matrix(segstart, btstart, duration):
    """
    Used by create_beat_synchro_chromagram
    Returns a matrix (#beats,#segs)
    #segs should be larger than #beats, i.e. many events or segs
    happen in one beat.
    THIS FUNCTION WAS ORIGINALLY CREATED BY RON J. WEISS (Columbia/NYU/Google)
    """
    # length of beats and segments in seconds
    # result for track: 'TR0002Q11C3FA8332D'
    #    seglen.shape = (708,)
    #    btlen.shape = (304,)
    #    duration = 238.91546    meaning approx. 3min59s
    seglen = np.concatenate((segstart[1:], [duration])) - segstart
    btlen = np.concatenate((btstart[1:], [duration])) - btstart

    warpmat = np.zeros((len(segstart), len(btstart)))
    # iterate over beats (columns of warpmat)
    for n in xrange(len(btstart)):
        # beat start time and end time in seconds
        start = btstart[n]
        end = start + btlen[n]
        # np.nonzero returns index of nonzero elems
        # find first segment that starts after beat starts - 1
        try:
            start_idx = np.nonzero((segstart - start) >= 0)[0][0] - 1
        except IndexError:
            # no segment start after that beats, can happen close
            # to the end, simply ignore, maybe even break?
            # (catching faster than ckecking... it happens rarely?)
            break
        # find first segment that starts after beat ends
        segs_after = np.nonzero((segstart - end) >= 0)[0]
        if segs_after.shape[0] == 0:
            end_idx = start_idx
        else:
            end_idx = segs_after[0]
        # fill col of warpmat with 1 for the elem in between
        # (including start_idx, excluding end_idx)
        warpmat[start_idx:end_idx, n] = 1.
        # if the beat started after the segment, keep the proportion
        # of the segment that is inside the beat
        warpmat[start_idx, n] = 1. - ((start - segstart[start_idx])
                                 / seglen[start_idx])
        # if the segment ended after the beat ended, keep the proportion
        # of the segment that is inside the beat
        if end_idx - 1 > start_idx:
            warpmat[end_idx-1, n] = ((end - segstart[end_idx-1])
                                     / seglen[end_idx-1])
        # normalize so the 'energy' for one beat is one
        warpmat[:, n] /= np.sum(warpmat[:, n])
    # return the transpose, meaning (#beats , #segs)
    return warpmat.T


def idB(loudness_array):
    """
    Reverse the Echo Nest loudness dB features.
    'loudness_array' can be pretty any numpy object:
    one value or an array
    Inspired by D. Ellis MATLAB code
    """
    return np.power(10., loudness_array / 20.)


def dB(inv_loudness_array):
    """
    Put loudness back in dB
    """
    return np.log10(inv_loudness_array) * 20.


def die_with_usage():
    """ HELP MENU """
    print 'beat_aligned_feats.py'
    print '   by T. Bertin-Mahieux (2011) Columbia University'
    print '      tb2332@columbia.edu'
    print ''
    print 'This code is intended to be used as a library.'
    print 'For debugging purposes, you can launch:'
    print '   python beat_aligned_feats.py <SONG FILENAME>'
    sys.exit(0)


if __name__ == '__main__':

    # help menu
    if len(sys.argv) < 2:
        die_with_usage()

    print '*** DEBUGGING ***'

    # params
    h5file = sys.argv[1]
    if not os.path.isfile(h5file):
        print 'ERROR: file %s does not exist.' % h5file
        sys.exit(0)

    # compute beat chromas
    btchromas = get_btchromas(h5file)
    print 'btchromas.shape =', btchromas.shape
    if np.isnan(btchromas).any():
        print 'btchromas have NaN'
    else:
        print 'btchromas have no NaN'
    print 'the max value is:', btchromas.max()


########NEW FILE########
__FILENAME__ = compute_hashcodes_mprocess
"""
Code to compute and aggregate hashcodes over a large collection
of data, e.g. the whole million song dataset, using multiple
processes.

Many parameters are hard-coded!

For the help menu, simply launch the code:
    python compute_hashcodes_mprocess.py

Copyright 2011, Thierry Bertin-Mahieux <tb2332@columbia.edu>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import glob
import time
import copy
import sqlite3
import datetime
import multiprocessing
import numpy as np

# hash codes params
WIN=3
DECAY=.995
NORMALIZE=True
WEIGHT_MARGIN=.60
MAX_PER_FRAME=3
LEVELS = [3]
COMPRESSION=2


def get_all_files(basedir,ext='.h5') :
    """
    From a root directory, go through all subdirectories
    and find all files with the given extension.
    Return all absolute paths in a list.
    """
    allfiles = set()
    for root, dirs, files in os.walk(basedir):
        files = glob.glob(os.path.join(root,'*'+ext))
        for f in files :
            allfiles.add( os.path.abspath(f) )
    return list(allfiles)


def aggregate_dbs(conn, tmpdbpath):
    """
    Aggregate the data from a filled, temporary database,
    to a main one already initialized.
    """
    try:
        CHT.__name__
    except NameError:
        #print 'We import cover hash table'
        import cover_hash_table as CHT
    t1 = time.time()
    conn_tmp = sqlite3.connect(tmpdbpath)
    # get number of hashes tables
    q = "SELECT cnt FROM num_hash_tables LIMIT 1"
    res = conn_tmp.execute(q)
    num_tables = res.fetchone()[0]
    # get all tids
    q = "SELECT ROWID, tid FROM tids"
    res = conn_tmp.execute(q)
    tidid_tid_pairs = res.fetchall()
    # iterate over all these tids
    for tidid, tid in tidid_tid_pairs:
        # iterate over all tables
        for tablecnt in range(1, num_tables + 1):
            table_name = 'hashes' + str(tablecnt)
            q = "SELECT jumpcode, weight FROM " + table_name
            q += " WHERE tidid=" + str(tidid)
            res = conn_tmp.execute(q)
            jcode_weight_pairs = res.fetchall()
            tid_is_in = False
            for jcode, weight in jcode_weight_pairs:
                CHT.add_hash(conn, tid, jcode, weight, tid_is_in=tid_is_in)
                tid_is_in = True
        # commit
        conn.commit()
    # done
    conn_tmp.close()
    # verbose
    timestr = str(datetime.timedelta(seconds=time.time()-t1))
    print 'Aggregated %s in %s.' % (tmpdbpath, timestr)


def my_vacuum(dbpathnew, dbpathold):
    """
    My own vacuum function on cover_hash_table.
    It works by copying and is slow!
    My main use, transform the page size to 4096
    Here because of its use of 'aggregate_dbs'
    """
    if os.path.exists(dbpathnew):
        print 'ERROR: %s already exists.' % dbpathnew
        return
    if not os.path.isfile(dbpathold):
        print 'ERROR: %s is not a file.' % dbpathold
        return
    # create new db
    import cover_hash_table as CHT
    conn = sqlite3.connect(dbpathnew)
    conn.execute('PRAGMA temp_store = MEMORY;')
    conn.execute('PRAGMA synchronous = OFF;')
    conn.execute('PRAGMA journal_mode = OFF;') # no ROLLBACK!
    conn.execute('PRAGMA page_size = 4096;')
    conn.execute('PRAGMA cache_size = 500000;') # page_size=4096, 500000->2GB
    CHT.init_db(conn)
    # copy
    aggregate_dbs(conn, dbpathold)
    # reindex
    CHT.reindex(conn)
    # done
    conn.commit()
    conn.close()
    

def create_fill_one_partial_db(filelist=None, outputdb=None):
    """
    This is the main function called by each process
    """
    # assert we have the params
    assert (not filelist is None) and (not outputdb is None), "internal arg passing error...!"
    # must be imported there... maybe... because of local num_hash_tables count
    import cover_hash_table as CHT
    # other imports
    import quick_query_test as QQT # should be replaced in the future
    import fingerprint_hash as FH
    # create output db, including PRAGMA
    conn = sqlite3.connect(outputdb)
    conn.execute('PRAGMA temp_store = MEMORY;')
    conn.execute('PRAGMA synchronous = OFF;')
    conn.execute('PRAGMA journal_mode = OFF;') # no ROLLBACK!
    conn.execute('PRAGMA cache_size = 1000000;') # default=2000, page_size=1024
    CHT.init_db(conn)
    # iterate over files
    cnt_tid_added = 0
    for filepath in filelist:
        # get bthcroma
        btchroma = QQT.get_cpressed_btchroma(filepath, compression=COMPRESSION)
        if btchroma is None:
            continue
        # get tid from filepath (faster than querying h5 file, less robust)
        tid = os.path.split(os.path.splitext(filepath)[0])[1]
        # get jumps
        landmarks = FH.get_landmarks(btchroma, decay=DECAY, max_per_frame=MAX_PER_FRAME)
        jumps = FH.get_jumps(landmarks, win=WIN)
        cjumps = FH.get_composed_jumps(jumps, levels=LEVELS, win=WIN)
        # add them
        jumpcodes = map(lambda cj: FH.get_jumpcode_from_composed_jump(cj, maxwin=WIN), cjumps)
        CHT.add_jumpcodes(conn, tid, jumpcodes, normalize=NORMALIZE, commit=False)
        cnt_tid_added += 1
        if cnt_tid_added % 1000 == 0:
            conn.commit()
        # debug
        if cnt_tid_added % 500 == 0:
            print 'We added %d tid in the hash table(s) of %s.' % (cnt_tid_added,
                                                                   outputdb)
    # we index
    CHT.reindex(conn)
    # close connection
    conn.close()
    # done
    return

# error passing problems
class KeyboardInterruptError(Exception):
    pass

# for multiprocessing
def create_fill_one_partial_db_wrapper(args):
    """ wrapper function for multiprocessor, calls run_steps """
    try:
        create_fill_one_partial_db(**args)
    except KeyboardInterrupt:
        raise KeyboardInterruptError()
    

def die_with_usage():
    """ HELP MENU """
    print 'compute_hashcodes_mprocess.py'
    print '   by T. Bertin-Mahieux (2011) Columbia University'
    print ''
    print 'Code to extract all hashcodes from a give folder of'
    print 'data, e.g. the whole millin song dataset.'
    print 'Creates as many db as process, then aggregate them into one'
    print 'USAGE'
    print '   python compute_hashcodes_mprocess.py <maindir> <output.db> <nthreads>'
    sys.exit(0)


if __name__ == '__main__':

    # help menu
    if len(sys.argv) < 4:
        die_with_usage()

    # params
    maindir = sys.argv[1]
    outputdb = sys.argv[2]
    nthreads = int(sys.argv[3])

    # sanity checks
    if not os.path.isdir(maindir):
        print 'ERROR: %s is not a directory.' % maindir
        sys.exit(0)
    if os.path.exists(outputdb):
        print 'ERROR: %s already exists.' % outputdb
        sys.exit(0)
    if nthreads < 1 or nthreads > 8:
        print 'REALLY? %d processes?' % nthreads
        sys.exit(0)
    
    # FIRST PASS, ITERATE OVER ALL FILES
    # temp db list
    if nthreads == 1:
        tmpdbs = [outputdb]
    else:
        tmpdbs = map(lambda n: outputdb + '_tmp' + str(n) + '.db', range(nthreads))
        for tdb in tmpdbs:
            if os.path.exists(tdb):
                print 'ERROR: tmp db %s already exists.' % tdb
                sys.exit(0)
    # list all files
    allfiles = get_all_files(maindir)
    print 'We got %d h5 files.' % len(allfiles)
    files_per_thread = int(len(allfiles) * 1. / nthreads + 1.)
    print 'That gives us ~%d files per thread.' % files_per_thread
    # params
    params_list = []
    for k in range(nthreads):
        # params for one specific thread
        p = {'outputdb': copy.deepcopy(tmpdbs[k]),
             'filelist': copy.deepcopy(allfiles[files_per_thread * k:
                                                files_per_thread * (k + 1)])}
        params_list.append(p)
    # create pool, launch using the list of params
    # we underuse multiprocessing, we will have as many processes
    # as jobs needed
    pool = multiprocessing.Pool(processes=nthreads)
    try:
        pool.map(create_fill_one_partial_db_wrapper, params_list)
        pool.close()
        pool.join()
    except KeyboardInterrupt:
        print 'MULTIPROCESSING'
        print 'stopping multiprocessing due to a keyboard interrupt'
        pool.terminate()
        pool.join()
    except Exception, e:
        print 'MULTIPROCESSING'
        print 'got exception: %r, terminating the pool' % (e,)
        pool.terminate()
        pool.join()

    # SECOND PASS, AGGREGATE (ONE THREAD)
    if nthreads == 1:
        print 'We are done (there was one thread, no aggregation!)'
        sys.exit(0)
    # create final output
    import cover_hash_table as CHT
    conn = sqlite3.connect(outputdb)
    conn.execute('PRAGMA temp_store = MEMORY;')
    conn.execute('PRAGMA synchronous = OFF;')
    conn.execute('PRAGMA journal_mode = OFF;') # no ROLLBACK!
    conn.execute('PRAGMA page_size = 4096;')
    conn.execute('PRAGMA cache_size = 500000;') # page_size=4096, 500000->2GB
    CHT.init_db(conn)
    print 'Final db initialized (including PRAGMA settings)'

    # iterate over temporary dbs
    for tdb in tmpdbs:
        aggregate_dbs(conn, tdb)
    # index the final db
    CHT.reindex(conn)
    # all done
    conn.commit()
    conn.close()
    print 'ALL DONE! you should delete the temporary databases...'
    print tmpdbs

########NEW FILE########
__FILENAME__ = cover_hash_table
"""
This code tries to implement an efficient hash table for cover
songs using python.
The goal is to receive hashes (defined elsewhere) and store them
so we can do easy retireval.
It's actually more of a big lookup table or a fast NN than a full
hashing system.

NOT EFFICIENT! Doing it over, we would use a big dictionary or some
keystore, not an SQL database! Especially for the query part.

Copyright 2011, Thierry Bertin-Mahieux <tb2332@columbia.edu>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import time
import datetime
import sqlite3
import itertools
import numpy as np
from operator import itemgetter

INDEX_NAMES = 'idx_jumpcodes_'
NEEDS_REINDEXING = True
MAX_ROWS = 1e7   # max number rows in 'hashes' before using a second table

# FOR DEBUGGING
WIN=3
DECAY=.995
NORMALIZE=True
WEIGHT_MARGIN=.60
MAX_PER_FRAME=3
LEVELS = [3]
COMPRESSION=2

# SLOW (SLIGHTLY BETTER) SET OF HASHES
#WIN=6
#DECAY=.96
#NORMALIZE=True
#WEIGHT_MARGIN=.50
#MAX_PER_FRAME=2
#LEVELS = [1,4]
#COMPRESSION=1


import fingerprint_hash as FH

def get_jump_code(tdiff, pdiff, poffset):
    """
    Encode a jump based on a time difference and a pitch difference.
    The encoding is the following:
      pdiff = (pdiff + 12) % 12
      code = tdiff * 12 + pdiff
    tdiff of zero are accepted!
    """
    return FH.get_jump_code(tdiff, pdiff, poffset)


def rotate_jump_code(jumpcode, rotation):
    """
    From a given jumpcode, and a pitch rotation (0 -> 11)
    return a new jumpcode
    """
    assert rotation >= 0 and rotation < 12
    if rotation == 0:
        return jumpcode
    original_offset = jumpcode % 12
    new_offset = (original_offset + rotation) % 12
    return jumpcode - original_offset + new_offset


def rotate_jump_code_sql(jumpcode, rotation):
    """
    Create a piece of SQL command that rotates the jumpcode
    to the right value
    """
    q = str(jumpcode) + "-" + str(jumpcode) + "%12"
    q += "+(" + str(jumpcode) + "%12+" +str(rotation) + ")%12"
    return q


def init_db(conn_or_path):
    """
    Init the hash table using an open sqlite3 connection.
    If the argument is a string, we create/open the database.
    In both case, we return the connection object.
    """
    # open / get connection
    is_file = type(conn_or_path).__name__ == 'str'
    if is_file:
        conn = sqlite3.connect(conn_or_path)
    else:
        conn = conn_or_path
    # create tables
    q = "CREATE TABLE hashes1 (tidid INT, weight FLOAT, jumpcode INT)"
    conn.execute(q)
    conn.commit()
    q = "CREATE TABLE tids (tid TEXT PRIMARY KEY)"
    conn.execute(q)
    conn.commit()
    q = "CREATE TABLE num_hash_tables (cnt INT PRIMARYKEY)"
    conn.execute(q)
    conn.commit()
    q = "INSERT INTO num_hash_tables VALUES (1)"
    conn.execute(q)
    conn.commit()
    # done, return connection
    return conn

def get_current_hash_table(conn):
    """
    Get the name of the current hash_table
    """
    # get the number
    q = "SELECT cnt FROM num_hash_tables LIMIT 1"
    res = conn.execute(q)
    num_tables = res.fetchone()[0]
    return 'hashes' + str(num_tables + 1)


def add_hash_table(conn, verbose=1):
    """
    Add a new hash table ebcause the previous one is full,
    i.e. passed the number of max rows
    RETURN NEW NAME
    """
    # get actual number of tables
    q = "SELECT cnt FROM num_hash_tables LIMIT 1"
    res = conn.execute(q)
    num_tables = res.fetchone()[0]
    if verbose > 0:
        print 'We currently have %d hash tables, we will add a new one.' % num_tables
    # create new table
    table_name = 'hashes' + str(num_tables + 1)
    q = "CREATE TABLE " + table_name + " (tidid INT, weight FLOAT, jumpcode INT)"
    conn.execute(q)
    conn.commit()
    # update number in appropriate table
    q = "DELETE FROM num_hash_tables"
    conn.execute(q)
    q = "INSERT INTO num_hash_tables VALUES (" + str(num_tables + 1) +  ")"
    conn.execute(q)
    conn.commit()
    if verbose > 0:
        print 'Table %s created.' % table_name
    return table_name


def reindex(conn, verbose=1):
    """
    Reindex all hash tables
    """
    # get number of hash tables
    q = "SELECT cnt FROM num_hash_tables LIMIT 1"
    res = conn.execute(q)
    num_tables = res.fetchone()[0]
    # reindex each table
    for tablecnt in range(1, num_tables+1):
        table_name = 'hashes' + str(tablecnt)
        tableverbose = verbose and (tablecnt == 1 or tablecnt == num_tables)
        reindex_table(conn, table_name, verbose=tableverbose)
    # no needs for further reindexing (do we still use that?)
    NEEDS_REINDEXING = False

def reindex_table(conn, table_name, verbose=0):
    """
    Called by reindex
    Create or recreate the index on hashcodes
    """
    t1 = time.time()
    # check if index exists, delete if needed
    try:
        q = "DROP INDEX " + INDEX_NAMES + table_name + '_1'
        conn.execute(q)
    except sqlite3.OperationalError, e:
        #print 'sqlite error:', e
        pass
    try:
        q = "DROP INDEX " + INDEX_NAMES + table_name + '_2'
        conn.execute(q)
    except sqlite3.OperationalError, e:
        #print 'sqlite error:', e
        pass
    # create index on jump codes
    q = "CREATE INDEX " + INDEX_NAMES + table_name + '_1'
    q += " ON " + table_name + " (jumpcode ASC, weight ASC)"
    conn.execute(q)
    conn.commit()
    if verbose > 0:
        strtime = str(datetime.timedelta(seconds=time.time() - t1))
        print 'REINDEXED THE TABLE %s (jumpcode,weight) IN %s' % (table_name, strtime)
        t2 = time.time()
    # create index on tids
    q = "CREATE INDEX " + INDEX_NAMES + table_name + '_2'
    q += " ON " + table_name + " (tidid ASC)"
    conn.execute(q)
    conn.commit()
    # verbose
    if verbose > 0:
        strtime = str(datetime.timedelta(seconds=time.time() - t2))
        print 'REINDEXED THE TABLE %s (tidid) IN %s' % (table_name, strtime)


# important if we start having many tables
current_hash_table = 'hashes1'

def add_hash(conn, tid, hashcode, weight=1., tid_is_in=False):
    """
    Add a given hashcode (jumpcode) in the hashtable,
    possibly with a given weight (default=1.)
    To makes things faster if we know the tid is already in the tids table,
    set tid_is_in to True
    If tid_is_in is False, we also check for the current hash_table, eventually
    we create a new one
    """
    global current_hash_table
    # we mention we need reindexing
    #NEEDS_REINDEXING = True
    # check for inf
    if np.isinf(weight):
        print 'We got INF weight for tid:', tid
        return []
    # do we know that tid already? insert if not, then get rowid
    if not tid_is_in:
        q = "INSERT OR IGNORE INTO tids VALUES ('" + tid + "')" # the OR IGNORE might be slow....
        conn.execute(q)
        conn.commit()
        # should we still be using the same table?
        q = "SELECT MAX(ROWID) FROM " + current_hash_table
        res = conn.execute(q)
        num_rows = res.fetchone()[0]
        if num_rows > MAX_ROWS:
            current_hash_table = add_hash_table(conn, verbose=1)
    # get tid
    q = "SELECT ROWID FROM tids WHERE tid='" + tid + "'"
    res = conn.execute(q)
    tidid = res.fetchone()[0]
    # add the hashcode / jumpcode
    q = "INSERT INTO " + current_hash_table + " VALUES (" + str(tidid) + ", " + str(weight)
    q += ", " + str(hashcode) + ")"
    conn.execute(q)


def add_jumpcodes(conn, tid, jumpcodes, normalize=False, commit=False):
    """
    From a list of jumps (time diff / pitch diff / pitch offset), add
    them to the hashes table
    PARAMS
        codeoffset    - add some offset to the code,
                        can be useful for different sets of codes
    """
    #weights = np.zeros(MAX_JUMP_CODE + 1, dtype='float')
    weights = {}
    # convert to codes, sum weights
    for code in jumpcodes:
        if code not in weights:
            weights[code] = 1.
        else:
            weights[code] += 1.
    # normalize by... norm?
    if normalize:
        #weights = weights * np.sqrt(np.square(weights).sum())
        wsum = float(np.sum(weights.values()))
        for k in weights.keys():
            #weights[k] /= np.sqrt(wsum) # this works well
            weights[k] /= np.log10(wsum) # this works better
            #weights[k] /= wsum
    # add to table
    for cid, c in enumerate(weights.keys()):
        #if weights[c] > 0.:
        if cid == 0:
            add_hash(conn, tid, c, weights[c])
        else:
            add_hash(conn, tid, c, weights[c], tid_is_in=True)
    # commit
    if commit:
       conn.commit() 
    

def retrieve_hash(conn,hashcode):
    """
    Given a hashcode/jumpcode, returns a list of track_id and weight
    that fit.
    RETURN
       list of (tid, weight)
    """
    # need reindexing?
    #if NEEDS_REINDEXING:
    #    reindex(conn)
    # query
    raise NotImplementedError
    q = "SELECT tid, weight FROM hashes WHERE jumpcode="
    q += str(hashcode)
    res = conn.execute(q)
    # done
    return res.fetchall()



def select_matches(conn, jumps, weights, weight_margin=.1, from_tid=None, verbose=0):
    """
    Select possible cover songs based on a set of jumpcodes and weights.
    PARAMS
       weight_margin    - we look for weights that are within that many
                          percent of the original
       tid_in_db        - if the tid is already in the db, we don't need
                          jumps and weights, we take it from db
    """
    # get number of hash tables
    q = "SELECT cnt FROM num_hash_tables LIMIT 1"
    res = conn.execute(q)
    num_tables = res.fetchone()[0]
    # create temp table (delete previous one if needed)
    if verbose > 0:
        t1 = time.time()
    conn.execute("DROP INDEX IF EXISTS idx_tmp_j_w")
    try:
        conn.execute("DELETE FROM tmpjumpweights")
    except sqlite3.OperationalError, e:
        #print 'sqlite error:', e
        q = "CREATE TEMP TABLE tmpjumpweights (weight weight FLOAT, jumpcode INT, rotation INT)"
        conn.execute(q)
    try:
        conn.execute("DELETE FROM tmpmatches")
    except sqlite3.OperationalError, e:
        if verbose > 0:
            print 'sqlite error:', e
        q = "CREATE TEMP TABLE tmpmatches (tidid INT, rotation INT, cnt INT)"
        conn.execute(q)
    try:
        conn.execute("DELETE FROM tmpmatchesperrot")
    except sqlite3.OperationalError, e:
        if verbose > 0:
            print 'sqlite error:', e
        q = "CREATE TEMP TABLE tmpmatchesperrot (tidid INT, rotation INT, cnt INT)"
        conn.execute(q)
    conn.commit()
    # add jumps and weights
    if from_tid is None:
        for jump, weight in zip(jumps, weights):
            for rotation in range(12):
                q = "INSERT INTO tmpjumpweights VALUES ("
                q += str(weight) + ", " + str(jump) + ", "
                q += rotate_jump_code_sql(jump, rotation) + ")"
                #print q
                conn.execute(q)
    else: # WAY FASTER for one hash table...
        q = "SELECT ROWID FROM tids WHERE tid='" + from_tid + "'"
        res = conn.execute(q)
        tidid = res.fetchone()
        if tidid is None:
            print 'We dont find the tid:', from_tid
            return []
        tidid = tidid[0]
        for tablecnt in range(1, num_tables + 1):
            table_name = 'hashes' + str(tablecnt)
            for rotation in range(12):
                q = "INSERT INTO tmpjumpweights SELECT"
                q += " weight, " + rotate_jump_code_sql("jumpcode", rotation)
                q += ", " + str(rotation) + " FROM " + table_name
                q += " WHERE tidid=" + str(tidid)
                conn.execute(q)
    conn.commit()
    if verbose > 0:
        t1bis = time.time()
        print 'Jumps / weights added in %f seconds.' % (t1bis - t1)
        sys.stdout.flush()
    #q = "CREATE INDEX idx_tmp_j_w ON tmpjumpweights ('jumpcode', 'weight')"
    #conn.execute(q)
    #conn.commit()
    if verbose > 0:
        t2 = time.time()
        print 'Jumps / weights indexed in %f seconds.' % (t2 - t1bis)
        sys.stdout.flush()
    # select proper tids for all rotations
    for tablecnt in range(1, num_tables + 1):
        #if tablecnt>1:
        #    print 'DEBUG WE BREAK AFTER 1 TABLE!!!'
        #    break
        table_name = 'hashes' + str(tablecnt)
        #"""
        #q = "INSERT INTO tmpmatches"
        #q += " SELECT " + table_name + ".tidid, " + table_name + ".weight, "
        #q += table_name + ".jumpcode, tmpjumpweights.rotation"
        #q += " FROM tmpjumpweights JOIN " + table_name + " ON "
        #q += table_name + ".jumpcode=tmpjumpweights.jumpcode"
        #if weight_margin > 0.:
        #    q += " AND ABS(" + table_name + ".weight-tmpjumpweights.weight)<tmpjumpweights.weight*" + str(weight_margin)
        #"""
        q = "INSERT INTO tmpmatches"
        q += " SELECT " + table_name + ".tidid, tmpjumpweights.rotation, COUNT(" + table_name + ".ROWID)"
        q += " FROM tmpjumpweights JOIN " + table_name + " ON "
        q += table_name + ".jumpcode=tmpjumpweights.jumpcode"
        if weight_margin > 0.:
            #q += " WHERE ABS(" + table_name + ".weight-tmpjumpweights.weight)<tmpjumpweights.weight*" + str(weight_margin)
            q += " WHERE " + table_name + ".weight BETWEEN tmpjumpweights.weight*(1.-"+ str(weight_margin)
            q += ") AND tmpjumpweights.weight*(1.+" + str(weight_margin) + ")"
        q += " GROUP BY " + table_name + ".tidid, tmpjumpweights.rotation"
        conn.execute(q)
        conn.commit() # we might have >50K new rows
        if verbose > 0 and tablecnt == 1:
            print 'Jumps / weights with TID from 1st hash table selected in %f seconds.' % (time.time() - t2)
            sys.stdout.flush()
    conn.commit()
    if verbose > 0:
        t3 = time.time()
        print 'Jumps / weights with TID selected in %f seconds.' % (t3 - t2)
        res = conn.execute("SELECT MAX(cnt) FROM tmpmatches")
        print 'Max cnt is: %d' % res.fetchone()[0]
        sys.stdout.flush()
    # count the number of tid per rotation
    #"""
    #q = "INSERT INTO tmpmatchesperrot"
    #q += " SELECT tidid, rotation, COUNT(tidid) FROM tmpmatches GROUP BY tidid, rotation"
    #conn.execute(q)
    #conn.commit()
    #"""
    q = "INSERT INTO tmpmatchesperrot"
    q += " SELECT tidid, rotation, SUM(cnt) FROM tmpmatches GROUP BY tidid, rotation"
    conn.execute(q)
    conn.commit()
    # index on tids, cnt?
    # ...
    # get max over all rotations
    q = "SELECT tids.tid FROM tmpmatchesperrot"
    q += " JOIN tids ON tids.ROWID=tmpmatchesperrot.tidid"
    q += " GROUP BY tmpmatchesperrot.tidid ORDER BY MAX(tmpmatchesperrot.cnt) DESC"
    res = conn.execute(q)
    conn.commit()
    tids = map(lambda x: x[0], res.fetchall())
    # verbose / debug
    if verbose > 0:
        t5 = time.time()
        print 'Selected TID for all rotations; ordered the %d tids in %f seconds.' % (len(tids),(t5 - t3))
        s = 'Selecting matches, best TID scores were: '
        for tid in tids[:3]:
            q = "SELECT ROWID FROM tids WHERE tid='" + tid + "'"
            res = conn.execute(q)
            tidid = res.fetchone()[0]
            q = "SELECT MAX(cnt) FROM tmpmatchesperrot WHERE tidid=" + str(tidid)
            res = conn.execute(q)
            s += str(res.fetchone()[0]) + ', '
        print s
        sys.stdout.flush()
    # done
    return tids


_KNOWN_JCODES = set()
_ALL_TIDS = []

def select_matches2(conn, weight_margin=.1, from_tid=None, verbose=0):
    """
    Select possible cover songs based on a set of jumpcodes and weights.
    ASSUME WE HAVE ONE TABLE PER JUMPCODE
    PARAMS
       weight_margin    - we look for weights that are within that many
                          percent of the original
       tid_in_db        - if the tid is already in the db, we don't need
                          jumps and weights, we take it from db
    """
    global _ALL_TIDS
    # get number of hash tables
    q = "SELECT cnt FROM num_hash_tables LIMIT 1"
    res = conn.execute(q)
    num_tables = res.fetchone()[0]
    # create temp table (delete previous one if needed)
    try:
        conn.execute("DELETE FROM tmpjumpweights")
    except sqlite3.OperationalError, e:
        #print 'sqlite error:', e
        q = "CREATE TEMP TABLE tmpjumpweights (weight FLOAT, jumpcode INT, rotation INT)"
        conn.execute(q)
    conn.commit()
    # known jcodes
    if len(_KNOWN_JCODES) == 0:
        q = "SELECT jcode FROM jcodes"
        res = conn.execute(q)
        for jcode in res.fetchall():
            _KNOWN_JCODES.add(jcode[0])
        print 'We know of %d jcodes' % len(_KNOWN_JCODES)
        # let's also do all tids
        q = "SELECT tid FROM tids ORDER BY ROWID ASC"
        res = conn.execute(q)
        _ALL_TIDS = np.concatenate([['tid_error'], np.array(map(lambda x: str(x[0]), res.fetchall()))])
    # start time
    if verbose > 0:
        t1 = time.time()
    # test mega table
    table_tidid_rot = np.zeros((1000000,12), dtype='int')
    if verbose > 0:
        print 'Mega table created'
    # add jumps and weights
    q = "SELECT ROWID FROM tids WHERE tid='" + from_tid + "'"
    res = conn.execute(q)
    tidid = res.fetchone()
    if tidid is None:
        print 'We dont find the tid:', from_tid
        return []
    tidid = tidid[0]
    if verbose > 0:
        print 'tidid =', tidid
    for tablecnt in range(1, num_tables + 1):
        table_name = 'hashes' + str(tablecnt)
        for rotation in range(12):
            q = "INSERT INTO tmpjumpweights SELECT"
            q += " weight, " + rotate_jump_code_sql("jumpcode", rotation)
            q += ", " + str(rotation) + " FROM " + table_name
            q += " WHERE tidid=" + str(tidid)
            conn.execute(q)
    conn.commit()
    if verbose > 0:
        t2 = time.time()
        if verbose > 0:
            print 'Jumps / weights indexed in %f seconds.' % (t2 - t1)
        sys.stdout.flush()
    # get all jumpcodes
    res = conn.execute("SELECT jumpcode, weight, rotation FROM tmpjumpweights")
    jumpcode_weight_r = res.fetchall()
    if verbose > 0:
        print 'Found %d jumpcodes and weights' % len(jumpcode_weight_r)
        sys.stdout.flush()
    # for each jumpcode, get all tids
    t_core_query = 0
    for jumpcode, weight, rotation in jumpcode_weight_r:
        if not jumpcode in _KNOWN_JCODES:
            continue
        # get matching tidid
        jcode_table = 'hashes_jcode_' + str(jumpcode)
        jcode_idx = "idx_jcode_" + str(jumpcode)
        #q = "INSERT INTO tmpmatches "
        #q += "SELECT tidid, weight, " + str(rotation)
        q = "SELECT tidid"#, weight, " + str(rotation)
        q += " FROM (" + jcode_table + " INDEXED BY '" + jcode_idx + "')"
        if weight_margin > 0.:
            #q += " WHERE ABS(" + jcode_table + ".weight-" + str(weight) + ")<" + str(weight * weight_margin)
            w_up = str(weight * (1. + weight_margin))
            w_down = str(max(0, weight * (1. - weight_margin)))
            q += " WHERE " + jcode_table + ".weight BETWEEN " + w_down
            q += " AND " + w_up
        t_before = time.time()
        res = conn.execute(q)
        #for tidid in res.fetchall():
        #    table_tidid_rot[tidid[0], rotation] += 1
        tidids = map(lambda x: x[0], res.fetchall())
        table_tidid_rot[tidids,[rotation]*len(tidids)] += 1
        conn.commit()
        t_core_query += time.time() - t_before
    if verbose > 0:
        t3 = time.time()
        print 'Jumps / weights with TID selected in %f seconds.' % (t3 - t2)
        if verbose > 0:
            print 'Time spend on core queries: %d seconds.' % t_core_query
        sys.stdout.flush()
    # count the number of tid per rotation
    max_per_tidid = np.max(table_tidid_rot,axis=1)
    if verbose > 0:
        print 'Best tidid has a max cnt of = ', np.max(max_per_tidid)
    tidid_ordered = np.argsort(max_per_tidid)[-1::-1]
    tidid_ordered = tidid_ordered[:np.where(max_per_tidid[tidid_ordered]==0)[0][0]]
    # get back tids
    tids = _ALL_TIDS[tidid_ordered]
    # done
    return tids
    

def die_with_usage():
    """ HELP MENU """
    print 'cover_hash_table.py'
    print '   by T. Bertin-Mahieux (2011) Columbia University'
    print '      tb2332@columbia.edu'
    print ''
    print 'This should be mostly used as a library, but you can'
    print 'launch some debugging code using:'
    print '   python cover_hash_table.py [FLAGS] <datadir> <coverlist> <tmp_db>'
    print 'FLAGS'
    print '  -fulldata    load every file in datadir'
    print ''
    sys.exit(0)


if __name__ == '__main__':

    # help menu
    if len(sys.argv) < 2:
        die_with_usage()

    # debugging
    print 'DEBUGGING!'

    # flags
    fulldata = False
    while True:
        if sys.argv[1] == '-fulldata':
            fulldata = True
        else:
            break
        sys.argv.pop(1)

    # params
    maindir = sys.argv[1]
    coverlistf = sys.argv[2]
    tmp_db = sys.argv[3]

    # sanity checks
    if not os.path.isdir(maindir):
        print 'ERROR: %s is not a directory.' % maindir
        sys.exit(0)
    if not os.path.isfile(coverlistf):
        print 'ERROR: %s does not exist.' % coverlistf
        sys.exit(0)
    use_existing_db = False
    if os.path.isfile(tmp_db):
        print 'CAREFUL: we use existing db: %s' % tmp_db
        time.sleep(5)
        use_existing_db = True

    # import hash code
    try:
        import beat_aligned_feats as BAF
        import cover_hash as CH
        import fingerprint_hash as FH
        import plot_covers as PC
        import quick_query_test as QQT
    except ImportError:
        print 'missing packages for debugging.'
        print 'Should not be needed!'

    # try to get data in as fast as possible
    clique_tid, clique_name = PC.read_cover_list(coverlistf)

    def get_jumps1(btchroma):
        """
        Use fingerprinting hash
        """
        landmarks = FH.get_landmarks(btchroma, decay=DECAY, max_per_frame=MAX_PER_FRAME)
        jumps = FH.get_jumps(landmarks, win=WIN)
        # done
        return jumps

    # load everything!
    if fulldata:
        all_h5_files = CH.get_all_files(maindir)
        all_tids = map(lambda x: os.path.split(os.path.splitext(x)[0])[1], all_h5_files)
    else:
        all_tids = []
        for ts in clique_tid.values():
            all_tids.extend(ts)
    print 'GOAL: add %d tids in the db' % len(all_tids)

    # open connection, init
    conn = sqlite3.connect(tmp_db)
    # pragma magic
    conn.execute('PRAGMA temp_store = MEMORY;')
    conn.execute('PRAGMA synchronous = OFF;')
    conn.execute('PRAGMA page_size = 4096;')
    conn.execute('PRAGMA cache_size = 500000;') # page_size=4096, 500000 -> 2GB
    conn.execute('PRAGMA journal_mode = OFF;') # no ROLLBACK!
    print 'We added PRAGMA magic'
    # initialize tables
    if not use_existing_db:
        print 'initalizing...'
        init_db(conn)
        print 'DB initialized'
        sys.stdout.flush()

    
    # for each clique, add jumps
    cnt_tid_added = 0
    for tid in all_tids:
        # the db is already full?
        if use_existing_db:
            break
        # get paths
        filepath = PC.path_from_tid(maindir,tid)
        # get btchromas
        #btchromas = map(lambda p: BAF.get_btchromas(p), filepaths)
        btchroma = QQT.get_cpressed_btchroma(filepath, compression=COMPRESSION)
        # add jumps
        if btchroma is None:
            continue
        # get jumps
        jumps = get_jumps1(btchroma)
        cjumps = FH.get_composed_jumps(jumps, levels=LEVELS, win=WIN)
        # add them
        jumpcodes = map(lambda cj: FH.get_jumpcode_from_composed_jump(cj, maxwin=WIN), cjumps)
        add_jumpcodes(conn, tid, jumpcodes, normalize=NORMALIZE, commit=False)
        cnt_tid_added += 1
        # commit
        #if cnt_tid_added == 10:
        #    reindex(conn)
        if cnt_tid_added % 1000 == 0:
            conn.commit()
        # debug
        if cnt_tid_added % 500 == 0:
            print 'We added %d tid in the hash table(s).' % cnt_tid_added

        # DEBUG!!!!!!!
        #if cnt_tid_added > 500:
        #    print 'DEBUG!!!! we stop adding'
        #    break

    # commit
    print 'done, added %d tids, we commit...' % cnt_tid_added
    conn.commit()
    print 'done'

    # index
    if not use_existing_db:
        reindex(conn)

    # verbose / debugging
    q = "SELECT cnt FROM num_hash_tables LIMIT 1"
    res = conn.execute(q)
    num_tables = res.fetchone()[0]
    print 'We got %d hash tables' % num_tables
    count_entries = 0
    for tablecnt in range(1, num_tables + 1):
        table_name = 'hashes' + str(tablecnt)
        q = "SELECT Count(tidid) FROM " + table_name
        res = conn.execute(q)
        count_entries += res.fetchone()[0]
    print 'We got a total of %d entries in table: hashes' % count_entries
    q = "SELECT Count(tid) FROM tids"
    res = conn.execute(q)
    print 'We got a total of %d unique tid in table: tids' % res.fetchone()[0]

    # we launch testing!
    total_tids = sum(map(lambda x: len(x), clique_tid.values()))
    res_pos = 0.
    n_queries = 0
    cnt_not_matched = 0
    print 'we got %d total tids from train file.' % total_tids
    for cliqueid, tids in clique_tid.items():
        for tid in tids:
            # get closest match!
            jumps = None; weights = None
            matches = np.array(select_matches(conn, jumps, weights,
                                              weight_margin=WEIGHT_MARGIN, from_tid=tid))
            if len(matches) == 0:
                print 'no matches for tid:',tid
                continue
            # check for known covers
            for tid2 in tids:
                if tid2 == tid:
                    continue
                try:
                    pos = np.where(matches==tid2)[0][0]
                except IndexError:
                    pos = int(len(matches) + (total_tids - len(matches)) * .5)
                    cnt_not_matched += 1
                if pos < 5:
                    print '!!! amazing result for %s and %s! (pos=%d)' % (tid, tid2, pos)
                n_queries += 1
                res_pos += pos
                # verbose
                if n_queries % 500 == 0:
                    print 'After %d queries / %d cliques, we got an average pos of: %f/%d' % (n_queries,
                                                                                              cliqueid,
                                                                                              res_pos * 1. / n_queries,
                                                                                              total_tids)
                    print '(for %d queries the right answer was not a candidate)' % cnt_not_matched
    # close connection
    conn.close()

########NEW FILE########
__FILENAME__ = create_jcode_tables
"""
Creates one table per hashcode, containing track IDs.

SHOULD BE REPLACE BY A PROPER KEYSTORE!!!!
hashcode -> tids
it could fit in memory and be so much faster!

Copyright 2011, Thierry Bertin-Mahieux <tb2332@columbia.edu>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import time
import datetime
import sqlite3
import numpy as np



def die_with_usage():
    """ HELP MENU """
    print 'create one table per code!'
    print 'USAGE:'
    print '   python create_jcode_tables.py <db>'
    sys.exit(0)


if __name__ == '__main__':

    # help menu
    if len(sys.argv) < 2:
        die_with_usage()

    # params
    dbpath = sys.argv[1]
    if not os.path.isfile(dbpath):
        print 'ERROR: %s does not exist.' % dbpath
        sys.exit(0)
    print 'We will add tables to %s' % dbpath

    # connect, pragma
    conn = sqlite3.connect(dbpath)
    conn.execute('PRAGMA temp_store = MEMORY;')
    conn.execute('PRAGMA synchronous = OFF;')
    conn.execute('PRAGMA journal_mode = OFF;') # no ROLLBACK!
    conn.execute('PRAGMA cache_size = 10000000;') # page_size=1024

    # get nuber of tables
    q = "SELECT cnt FROM num_hash_tables LIMIT 1"
    res = conn.execute(q)
    num_tables = res.fetchone()[0]

    # get all jcodes
    t1 = time.time()
    jcodes = []
    for tablecnt in range(1, num_tables + 1):
        table_name = 'hashes' + str(tablecnt)
        q = "SELECT DISTINCT jumpcode FROM " + table_name
        res = conn.execute(q)
        jcodes = np.unique(list(jcodes) + map(lambda x: x[0], res.fetchall()))
        print 'After %d tables, we have %d unique jcodes' % (tablecnt,
                                                             len(jcodes))
    t2 = time.time()
    strtime = str(datetime.timedelta(seconds=t2 - t1))
    print 'Jumpcodes extracted in %s' % strtime

    #add jcodes
    q = "CREATE TABLE jcodes (jcode INT PRIMARY KEY)"
    conn.execute(q)
    for jcode in jcodes:
        q = "INSERT INTO jcodes VALUES (" + str(jcode) + ")"
        conn.execute(q)
    conn.commit()
    print 'All unique jcode added into jcodes table'
    
    # create tables
    print 'We start creating tables'
    for jidx in xrange(len(jcodes)):
        jcode = jcodes[jidx]
        s_jcode = str(jcode)
        # create table
        jtable_name = 'hashes_jcode_' + s_jcode
        q = "CREATE TABLE " + jtable_name + " (tidid INT, weight FLOAT)"
        conn.execute(q)
        # fill it
        for tablecnt in range(1, num_tables + 1):
            table_name = 'hashes' + str(tablecnt)
            q = "INSERT INTO " + jtable_name
            q += " SELECT tidid, weight FROM " + table_name
            q += " WHERE jumpcode=" + s_jcode
            conn.execute(q)
        conn.commit()
        # index
        q = "CREATE INDEX idx_jcode_" + s_jcode + " ON " + jtable_name
        q += " (weight)"
        conn.execute(q)
        conn.commit()
        # verbose
        if (jidx + 1) % 5000 == 0:
            strtime = str(datetime.timedelta(seconds=time.time() - t2))
            print 'We did %d jumpcodes (/%d) tables in %s' % (jidx + 1, len(jcodes), strtime)

    # done!
    conn.close()
    print 'Done!'


########NEW FILE########
__FILENAME__ = fingerprint_hash
"""
Code to create fingerprints out of a chroma matrix.

Code inspired by D. Ellis fingerprinting MATLAB code

For chroma, we probably simply have a decay factor,
and no 'local pitch' decay (unlike a freq band)

Copyright 2011, Thierry Bertin-Mahieux <tb2332@columbia.edu>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import copy
import time
import sqlite3
import numpy as np
import cover_hash_table as CHT



def landmarks_pass(btchroma, decay, max_per_frame):
    """
    Performs a forward pass to find landmarks
    PARAMS
       btchroma       - we know what this is
       decay          - same as get_landmarks
       max_per_frame  - how many landmarks we allow in 1 col
    RETURN
       binary matrix, same size as btchroma, with ones
       for landmarks
    """
    # find number of beats
    nbeats = btchroma.shape[1]
    # return matrix
    landmarks = np.zeros(btchroma.shape, dtype='int')
    # initiate threshold, there's probably better than that
    #sthresh = btchroma[:,:10].max()
    sthresh = btchroma[:,:10].max(axis=1) # one threshold per pitch
    # iterate over beats
    # FORWARD PASS
    for b in range(nbeats):
        s_this = btchroma[:,b]
        sdiff = s_this - sthresh
        sdiff[sdiff<0] = 0.
        # sort
        peak_order = np.argsort(sdiff)[-1::-1][:max_per_frame]
        # iterate over max peaks
        for pidx, p in enumerate(peak_order):
            if s_this[p] > sthresh[p]:
                # debug
                landmarks[p, b] = 1
                # this following part is not understood
                #eww = np.square(np.exp(-0.5 * p / 1.));
                #sthresh = max(sthresh, s_this[p] * eww);
                sthresh[p] = s_this[p]
                if pidx == 0:
                    sthresh[sthresh<s_this[p] * decay] = s_this[p] * decay
        # decay sthresh
        sthresh *= decay
    # done
    return landmarks


def get_landmarks(btchroma, decay, max_per_frame=3, verbose=0):
    """
    Returns a set of landmarks extracted from btchroma.
    """
    if verbose > 0:
        t1 = time.time()
    # forward pass
    landmarks_fwd = landmarks_pass(btchroma, decay=decay, max_per_frame=max_per_frame)
    # backward pass
    landmarks_bwd = landmarks_pass(btchroma[:,-1::-1],
                                   decay=decay, max_per_frame=max_per_frame)[:,-1::-1]
    # merge landmarks
    landmarks_fwd *= landmarks_bwd
    # verbose
    if verbose > 0:
        print 'Landmarks (fwd & bwd) computed in %f seconds.' % (time.time() - t1)
    # done?
    return landmarks_fwd


def get_jumps(landmarks, win=12):
    """
    Receives a binary matrix containing landmarks.
    Computes pairs over a window of size 'win'
    ONLY ONE MAX PER COL IS ALOUD
    ONLY JUMPS BETWEEN TWO POINTS ARE CONSIDERED
    RETURN
       list of [tdiff, pdiff, toffset, poffset]
    """
    assert landmarks.shape[0] == 12, 'What?'
    nbeats = landmarks.shape[1]
    # jumps
    jumps = []
    # get all the positive points in a dict
    # faster if there are few landmarks
    lmks_d = {}
    tmp = np.where(landmarks==1)
    for i in range(len(tmp[0])):
        if tmp[1][i] in lmks_d:
            lmks_d[tmp[1][i]].append(tmp[0][i])
        else:
            lmks_d[tmp[1][i]] = [tmp[0][i]]
    #lmks_d.update(zip(tmp[1],tmp[0]))
    #assert len(lmks_d) == len(tmp[0]),'more than one max per col'
    # iterate over beats (until -win, faster than -1, does not change much)
    for b in range(nbeats-win):
        b_lmks = lmks_d.get(b, [])
        if len(b_lmks) == 0:
            continue
        for w in range(b,b+win):
            w_lmks = lmks_d.get(w, [])
            if len(w_lmks) == 0:
                continue
            for b_lmk in b_lmks:
                for w_lmk in w_lmks:
                    if w == b and b_lmk >= w_lmk:
                        continue
                    # tdiff = w-b
                    # toffset = b
                    # poffset = b_lmks
                    pdiff = (w_lmk - b_lmk + 12) % 12
                    jumps.append([w-b, pdiff, b, b_lmk])
    # done
    return jumps

# COMPOSED JUMPS *********************************************


def get_jumpcode_from_composed_jump(jump, maxwin=15, slowdebug=False):
    """
    Compute a jumpcode from a set of jumps
    The jump here is the output of 'get_composed_jumps(...)'
    It's a list of (t,p,t,p,t,p...), eventually with a -1 value at the end
    """
    nlmks = int(len(jump) / 2)
    assert nlmks > 1
    maxcode = 12 * 12 * (maxwin + 1) # max code for a level 1 jump (2 lmks)
    finalcode = 0
    # add each jump, with a power of maxcode
    for j in range(0, nlmks * 2 - 2, 2):
        tdiff = jump[j+2] - jump[j]
        assert tdiff >= 0
        poffset = jump[j+1]
        pdiff = (jump[j+3] - jump[j+1] + 12) % 12
        jcode = get_jump_code(tdiff, pdiff, poffset)
        jcode_norot = jcode - (jcode % 12)
        if j == 0:
            first_rot = jcode - jcode_norot
        finalcode += jcode_norot * np.power(maxcode, j/2)
    # add first rotation
    finalcode += first_rot
    #***********************************
    # MEGA TEST
    if slowdebug:
        rndoffset = np.random.randint(1,12)
        jump2 = list(copy.deepcopy(jump))
        for j in range(1, len(jump2), 2):
            jump2[j] = (jump2[j] + rndoffset) % 12
        finalcode2 = get_jumpcode_from_composed_jump(jump2, maxwin=maxwin, slowdebug=False)
        #print 'finalcode = %d and finalcode2 = %d' % (finalcode, finalcode2)
        assert finalcode2 - (finalcode2 % 12) == finalcode - (finalcode % 12)
    #***********************************
    # done! we think...
    return finalcode


def get_jump_code(tdiff, pdiff, poffset):
    """
    Encode a jump based on a time difference and a pitch difference.
    The encoding is the following:
      pdiff = (pdiff + 12) % 12
      code = tdiff * 12 + pdiff
    tdiff of zero are accepted!
    """
    pdiff = (pdiff + 12) % 12
    # sanity checks, should be removed for speed
    assert tdiff >= 0
    assert pdiff >= 0 and pdiff < 12
    assert poffset >= 0 and poffset < 12
    # return code
    return (tdiff * 12 * 12) + pdiff * 12 + poffset


def compose_jump_code(code1, code2):
    """
    We want to avoid collision, and rotation must still be done
    by %12 and adding rotation
    """
    code1_rot = code1 % 12
    code1_norot = code1 - code1_rot
    code2_norot = code2 - (code2 % 12)
    # combine code norot
    mult = 12 * np.power(10, max(int(np.log10(code1_norot)), int(np.log10(code2_norot))) + 1)
    code = code1_norot * 12 + code2_norot
    # add back rotation1
    code += code1_rot
    # sanity checks
    assert not np.isinf(code), 'oops, our encoding degenerated'
    assert code < sys.maxint, 'oops, our encoding degenerated'
    assert code > 0, 'oops, our encoding degenerated'
    # done
    return code


def add_nlmk2_jumps_to_db(conn, jumps, nocopy=False):
    """
    Get the output of 'get_jumps' and add it to a proper
    database that can be use to compose_jumps later
    """
    # create table
    q = "CREATE TEMP TABLE jumps_level1 (t0 INT, p0 INT, t1 INT, p1 INT, jumpcode INT)"
    conn.execute(q)
    # add jumps
    for tdiff, pdiff, t0, p0 in jumps:
        t1 = t0 + tdiff
        p1 = (p0 + pdiff) % 12
        q = "INSERT INTO jumps_level1 VALUES (" + str(t0) + ", " + str(p0)
        q += ", " + str(t1) + ", " + str(p1) + ", -1)"
        conn.execute(q)
    conn.commit()
    if nocopy:
        return
    # copy
    q = "CREATE TEMP TABLE jumps_level1_bis (t0 INT, p0 INT, t1 INT, p1 INT, jumpcode INT)"
    conn.execute(q)
    q = "INSERT INTO jumps_level1_bis SELECT * FROM jumps_level1"
    conn.execute(q)
    conn.commit()
    # INDEXING
    # (we only need t0/p0 since we add level1 jumps AFTER current jumps)
    # t1 is useful for checking win size
    q = "CREATE INDEX idx_level1_bis ON jumps_level1_bis ('t0', 'p0', 't1')"
    conn.execute(q)
    conn.commit()
    # DONE
    

def compose_jumps(conn, win, level=2, verbose=0):
    """
    Receives a database of jumps that have been composed up to
    the ('level'-1) level
    level1 means jumps between 2 landmarks, so we do at least level 2 here..
    Composed jumps have to have a maximum lenght of size 'win'
    """
    assert level >= 2
    # name of current (level under) table
    curr_table_name = "jumps_level" + str(level-1)
    # add indexing to the current table (end of jumps)
    q = "CREATE INDEX idx_level" + str(level-1)
    q += " ON " + curr_table_name
    q += "('t" + str(level-1) + "', 'p" + str(level-1) + "', 't0')"
    conn.execute(q)
    conn.commit()
    # create new table
    new_table_name = "jumps_level" + str(level)
    q = "CREATE TEMP TABLE " + new_table_name + " ("
    for n in range(level+1):
        q += "t" + str(n) + " INT, p" + str(n) + " INT,"
    q += " jumpcode INT)"
    if verbose > 0:
        print q
    conn.execute(q)
    # add proper new jumps to it, by adding a first level jump AFTER
    q = "INSERT INTO " + new_table_name + " SELECT "
    for n in range(level):
        q += curr_table_name + ".t" + str(n) + ", "
        q += curr_table_name + ".p" + str(n) + ", "
    q += "jumps_level1_bis.t1, jumps_level1_bis.p1, -1" # -1 is jumpcode for the moment
    q += " FROM " + curr_table_name + " JOIN jumps_level1_bis"
    q += " ON " + curr_table_name + ".t" + str(level-1) + "=jumps_level1_bis.t0"
    q += " AND " + curr_table_name + ".p" + str(level-1) + "=jumps_level1_bis.p0"
    q += " WHERE jumps_level1_bis.t1-" + curr_table_name + ".t0<=" + str(win)
    if verbose > 0 :
        print q
    conn.execute(q)
    conn.commit()
    # NEVER USEFUL TO ADD JUMP BEFORE, AFTER IS ENOUGH
    

def get_composed_jumps(jumps, levels, win, verbose=0):
    """
    Take the output of get_jumps (from landmarks)
    Compose the jumps, return them as an array of array.
    If intermediate=True, we return the jumps for intermediary levels,
    not just the requested one.
    We use a temporary sqlite3 connection to work.
    """
    assert len(levels) > 0
    maxlevel = max(levels)
    assert maxlevel >= 1, 'level 1 min, it means jumps between two landmarks'
    # verbose
    if verbose>0:
        t1 = time.time()
    # open temporary connection
    #      IT IS FAST!
    #      timeit.Timer("import sqlite3; conn = sqlite3.connect(':memory:'); conn.close()").timeit(10000)
    #      Out[35]: 0.49553799629211426
    conn = sqlite3.connect(':memory:')
    # special case: level = 1
    if maxlevel == 1:
        add_nlmk2_jumps_to_db(conn, jumps, nocopy=True)
        q = "SELECT * FROM jumps_level1"
        res = conn.execute(q)
        composed_jumps = res.fetchall()
        conn.close()
        if verbose > 0:
            print 'Composed jumps (max lvl = %d) obtained in %f seconds.' % (maxlevel, time.time() - t1)
        return composed_jumps
    # enters level1 jumps
    add_nlmk2_jumps_to_db(conn, jumps)
    # do upper levels
    for lvl in range(2, maxlevel+1):
        compose_jumps(conn, win, level=lvl)
    # what do we return?
    composed_jumps = []
    for lvl in levels:
        q = "SELECT * FROM jumps_level" + str(lvl)
        res = conn.execute(q)
        composed_jumps.extend(res.fetchall())
    # done
    conn.close()
    # verbose
    if verbose > 0:
        print 'Composed jumps (max lvl = %d) obtained in %f seconds.' % (maxlevel, time.time() - t1)
    return composed_jumps

# ************************************************************




def die_with_usage():
    """ HELP MENU """
    print 'fingerprint_hash.py'
    print '   by T. Bertin-Mahieux (2011) Columbia University'
    print '      tb2332@columbia.edu'
    print ''
    print 'This code should mostly be used as a library'
    print 'Creates landmarks similar to D. Ellis fingerprinting code.'
    print 'USAGE (debugging):'
    print '    python fingerprint_hash.py <hdf5 song file> <decay>'
    print ''
    sys.exit(0)


if __name__ == '__main__':

    # help menu
    if len(sys.argv) < 2:
        die_with_usage()

    # debugging
    print 'DEBUGGING'

    # params
    songfile = sys.argv[1]
    decay = .9
    if len(sys.argv) > 2:
        decay = float(sys.argv[2])

    # sanity checks
    if not os.path.isfile(songfile):
        print 'ERROR: %s does not exist.' % songfile
        sys.exit(0)

    # tbm path, import stuff
    import beat_aligned_feats as BAF
    import pylab as P
    import warnings
    warnings.filterwarnings('ignore', category=DeprecationWarning)

    # get chroma
    btchroma = BAF.get_btchromas_loudness(songfile)
    btchroma_db = np.log10(BAF.get_btchromas_loudness(songfile)) * 20.
    btchroma_normal = BAF.get_btchromas(songfile)

    # get landmarks
    landmarks = get_landmarks(btchroma, decay=decay)
    landmarks_normal = get_landmarks(btchroma_normal, decay=decay)

    # plot
    pargs = {'aspect': 'auto',
             'cmap': P.cm.gray_r,
             'interpolation': 'nearest',
             'origin': 'lower'}
    P.subplot(4, 1, 1)
    P.imshow(btchroma, **pargs)
    P.subplot(4, 1, 2)
    P.imshow(landmarks_normal, **pargs)

    # plot landmarks
    P.subplot(4, 1, 3)
    P.imshow(btchroma, **pargs)
    #landmarksY, landmarksX = np.where(landmarks==1)
    landmarksY, landmarksX = np.where(landmarks_normal==1)
    for k in range(len(landmarksX)):
        x = landmarksX[k]
        y = landmarksY[k]
        P.scatter(x,y,s=12,c='r',marker='o')
    # plot groups
    P.subplot(4, 1, 4)

    # plot groups
    def my_groups(btchroma):
        #landmarks = get_landmarks(btchroma, decay=decay)
        jumps = get_jumps(landmarks_normal, win=12)
        unzip = lambda l:tuple(zip(*l)) # magic function!
        tdiff,pdiff,toff,poff = unzip(jumps)
        groups = [None] * len(tdiff)
        for i in range(len(tdiff)):
            x0 = toff[i]
            x1 = toff[i] + tdiff[i]
            y0 = poff[i]
            y1 = (poff[i] + pdiff[i]) % 12
            groups[i] = [[x0,y0], [x1,y1]]
        return groups

    import plot_covers as PC
    groups = my_groups(btchroma)
    PC.plot_landmarks(landmarks, None, None, groups=groups,
                      noshow=True, xlim=None)

    P.show(True)

    

########NEW FILE########
__FILENAME__ = query_for_covers_mprocess
"""
Code to query a filled hash_cover table
(using compute_hashcodes_mprocess most likely)
from a set of cliques (the SHS train or test set)

For the help menu, simply launch the code:
    python query_for_covers_mprocess.py

Copyright 2011, Thierry Bertin-Mahieux <tb2332@columbia.edu>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import copy
import time
import tables
import sqlite3
import datetime
import numpy as np
import multiprocessing


WEIGHT_MARGIN=.6
CACHE_SIZE=3500000 # per thread, '1000000'-> 1GB
                   # if page_size==4096, we divide by 4


def read_cover_list(filename):
    """
    Read shs_dataset_train.txt or similarly formatted file.
    Return
      * clique -> tids dict
      * clique -> name
    clique are random integer numbers
    """
    clique_tid = {}
    clique_name = {}
    f = open(filename, 'r')
    for line in f.xreadlines():
        if line == '' or line.strip() == '' or line[0] == '#':
            continue
        if line[0] == '%':
            clique_id = len(clique_tid) + 1
            clique_name[clique_id] = line.strip()
            continue
        tid = line.strip().split('<SEP>')[0]
        if clique_id in clique_tid.keys():
            clique_tid[clique_id].append(tid)
        else:
            clique_tid[clique_id] = [tid]
    num_tids = sum(map(lambda a: len(a), clique_tid.values()))
    print 'Found %d cliques for a total of %d tids in %s.' % (len(clique_tid), num_tids,
                                                              filename)
    return clique_tid, clique_name


def init_h5_result_file(h5, expectedrows=50000):
    """
    Receives a h5 file that has just been created,
    creates the proper arrays:
     - query
     - target
     - position
     - n_results
    """
    group = h5.createGroup("/",'results','general, sole group')
    h5.createEArray(group,'query',tables.StringAtom(18,shape=()),(0,),
                    'tid of the query',
                    expectedrows=expectedrows)
    h5.createEArray(group,'target',tables.StringAtom(18,shape=()),(0,),
                    'tid of the target',
                    expectedrows=expectedrows)
    h5.createEArray(group,'pos',tables.IntAtom(shape=()),(0,),
                    'position of the target in the result list',
                    expectedrows=expectedrows)
    h5.createEArray(group,'n_results',tables.IntAtom(shape=()),(0,),
                    'lenght of the result list returned by query',
                    expectedrows=expectedrows)
    # done
    return


def query_one_thread(dbpath=None, clique_tid=None, outputf=None):
    """
    Query the database given a set of queries, put the result
    in a... HDF5 file?
    """
    assert not dbpath is None
    assert not clique_tid is None
    assert not outputf is None
    # verbose
    n_cover_songs = sum(map(lambda l: len(l), clique_tid.values()))    
    print 'For tmp output %s, we got %d cliques (%d cover songs).' % (outputf,
                                                                      len(clique_tid),
                                                                      n_cover_songs)
    print 'dbpath = %s' % dbpath
    # import cover_hash_table with code to query
    import cover_hash_table as CHT
    # create tmp output
    h5 = tables.openFile(outputf, 'a')
    expectedrows = sum(map(lambda l: len(l) * (len(l) - 1),
                           clique_tid.values()))
    init_h5_result_file(h5, expectedrows=expectedrows)
    # get toal_tids
    conn = sqlite3.connect(dbpath)
    q = "SELECT DISTINCT tid FROM tids"
    res = conn.execute(q)
    total_tids = len(res.fetchall())
    conn.close()
    # query every clique
    n_queries = 0
    cnt_not_matched = 0
    cnt_cliques = 0
    # start time
    for cliqueid, tids in clique_tid.items():
        # open connection, add pragma stuff
        conn = sqlite3.connect(dbpath)
        conn.execute('PRAGMA temp_store = MEMORY;') # useless?
        conn.execute('PRAGMA synchronous = OFF;') # useless?
        conn.execute('PRAGMA journal_mode = OFF;') # useless?
        res = conn.execute('PRAGMA page_size;')
        page_size = res.fetchone()[0]
        cache_size = CACHE_SIZE
        if page_size == 4096:
            cache_size /= 4
        conn.execute('PRAGMA cache_size = ' + str(cache_size) +';') # default=2000, page_size=1024
        t1 = time.time()
        cnt_cliques += 1
        for tid in tids:
            # get closest match!
            jumps = None; weights = None
            #matches = np.array(CHT.select_matches(conn, jumps, weights,
            #                                      weight_margin=WEIGHT_MARGIN, from_tid=tid))
            verbose = 1 if tid == tids[0] else 0
            matches = np.array(CHT.select_matches2(conn,
                                                   weight_margin=WEIGHT_MARGIN,
                                                   from_tid=tid,
                                                   verbose=verbose))
            if len(matches) == 0:
                print 'no matches for tid:',tid
                #continue
            # check for known covers
            for tid2 in tids:
                if tid2 == tid:
                    continue
                try:
                    pos = np.where(matches==tid2)[0][0]
                except IndexError:
                    pos = int(len(matches) + (total_tids - len(matches)) * .5)
                    cnt_not_matched += 1
                n_queries += 1
                # add to h5
                h5.root.results.query.append([tid])
                h5.root.results.target.append([tid2])
                h5.root.results.pos.append([pos])
                h5.root.results.n_results.append([len(matches)])
            if tid == tids[0]:
                print '[we finished 1st clique query for ouput %s in %d seconds.]' % (outputf, time.time()-t1)
        conn.close()
        h5.flush()
        # verbose
        if cnt_cliques < 20 or cnt_cliques % 5 == 0:
            print 'we did %d cliques for ouput %s' % (cnt_cliques, outputf)
            sys.stdout.flush()
    # done
    h5.flush()
    h5.close()



# error passing problems
class KeyboardInterruptError(Exception):
    pass


# for multiprocessing
def query_one_thread_wrapper(args):
    """ wrapper function for multiprocessor, calls run_steps """
    try:
        query_one_thread(**args)
    except KeyboardInterrupt:
        raise KeyboardInterruptError()


def die_with_usage():
    """ HELP MENU """
    print 'query_for_covers_mprocess.py'
    print '   by T. Bertin-Mahieux (2011) Columbia University'
    print 'query a filled database with cliques of covers'
    print 'i.e. the SHS train or test set'
    print ''
    print 'USAGE'
    print '   python query_for_covers_mprocess.py <db> <SHS set> <output> <nthreads>'
    sys.exit(0)


if __name__ == '__main__':

    # help menu
    if len(sys.argv) < 5:
        die_with_usage()

    # params
    dbpath = sys.argv[1]
    coverlistf = sys.argv[2]
    outputf = sys.argv[3]
    nthreads = int(sys.argv[4])
    
    # sanity checks
    if not os.path.isfile(dbpath):
        print 'ERROR:  %s does not exist.' % dbpath
        sys.exit(0)
    if not os.path.isfile(coverlistf):
        print 'ERROR: %s does not exist.' % coverlistf
        sys.exit(0)
    if os.path.exists(outputf):
        print 'ERROR: %s already exists.' % outputf
        sys.exit(0)
    if nthreads < 1 or nthreads > 8:
        print 'Really? %d threads? come on.' % nthreads
        sys.exit(0)

    # read the cliques
    clique_tid, clique_name = read_cover_list(coverlistf)
    print 'We got %d cliques' % len(clique_tid)
    n_cover_songs = sum(map(lambda l: len(l), clique_tid.values()))
    print 'We got %d cover songs' % n_cover_songs

    # FIRST PASS, ITERATE OVER ALL CLIQUES
    # number of processes
    NPROC = 20
    # temp h5 list
    tmph5s = map(lambda n: outputf + '_tmp' + str(n) + '.h5', range(NPROC))
    for th5 in tmph5s:
        if os.path.exists(th5):
            print 'ERROR: tmp h5 %s already exists.' % th5
            sys.exit(0)
    # list all cliques
    cliques = clique_tid.keys()
    n_cliques_per_thread = int(len(cliques) * 1. / NPROC + 1.)
    print 'That gives us ~%d cliques per thread.' % n_cliques_per_thread
    # params
    db_paths = [dbpath]
    for k in range(10):
        copied_db = dbpath + '_' + str(k) + '.db'
        if os.path.isfile(copied_db):
            db_paths.append(copied_db)
    print 'We have %d db copies!' % len(db_paths)
    params_list = []
    for k in range(NPROC):
        # cliques specific to that thread
        thread_c_t = {}
        for c in cliques[n_cliques_per_thread * k: n_cliques_per_thread * (k + 1)]:
            thread_c_t[c] = copy.deepcopy(clique_tid[c])
        # params for one specific thread
        p = {'dbpath': db_paths[k % len(db_paths)],
             'outputf': copy.deepcopy(tmph5s[k]),
             'clique_tid': thread_c_t}
        params_list.append(p)
    # create pool, launch using the list of params
    # we underuse multiprocessing, we will have as many processes
    # as jobs needed
    pool = multiprocessing.Pool(processes=nthreads)
    try:
        pool.map(query_one_thread_wrapper, params_list)
        pool.close()
        pool.join()
    except KeyboardInterrupt:
        print 'MULTIPROCESSING'
        print 'stopping multiprocessing due to a keyboard interrupt'
        pool.terminate()
        pool.join()
    except Exception, e:
        print 'MULTIPROCESSING'
        print 'got exception: %r, terminating the pool' % (e,)
        pool.terminate()
        pool.join()

    # SECOND PHASE, AGGREGATE

    # open output
    h5 = tables.openFile(outputf, 'a')
    expectedrows = sum(map(lambda l: len(l) * (len(l) - 1),
                           clique_tid.values()))
    init_h5_result_file(h5, expectedrows=expectedrows)

    # iterate over temp h5
    for th5 in tmph5s:
        h5_tmp = tables.openFile(th5, 'r')
        h5.root.results.query.append(np.array(h5_tmp.root.results.query))
        h5.root.results.target.append(np.array(h5_tmp.root.results.target))
        h5.root.results.pos.append(np.array(h5_tmp.root.results.pos))
        h5.root.results.n_results.append(np.array(h5_tmp.root.results.n_results))
        h5_tmp.close()
    h5.flush()
    h5.close()

    # done
    print 'DONE! you should remove tmp files:'
    print tmph5s
    

########NEW FILE########
__FILENAME__ = quick_query_test
"""
This performs a quick sanity check, e.g. compares covers with randomly
selected songs, and tells which one is closer!

Copyright 2011, Thierry Bertin-Mahieux <tb2332@columbia.edu>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""


import os
import sys
import glob
import time
import sqlite3
import numpy as np

# hack to get btchromas
try:
    import beat_aligned_feats as BAF
    import cover_hash_table as CHT
    import fingerprint_hash as FH
except ImportError:
    print "Missed some import, might cause problems..."
    
RANDOMSEED = hash('caitlin')
# params
NUM_EXPS = 524
DECAY = .995
WIN = 3
NORMALIZE = True
WEIGHT_MARGIN = .60
MAX_PER_FRAME = 3
COMPRESSION = [2] #(1,2,3,4,8)
LEVELS = [3] # composed jumps, 1 means first order jumps

# BEST (SLOW!) 500 -> .798
#DECAY = 0.96
#WIN = 6
#NORMALIZE = 1
#WEIGHT_MARGIN = 0.50
#MAX_PER_FRAME = 2
#COMPRESSION = [1]
#LEVELS = [1, 4]


def get_cpressed_btchroma(path, compression=1):
    """ to easily play with the btchromas we get """
    # MAIN FUNCTION WITH COMPRESSION / STRETCH
    add_loudness = False
    h5 = BAF.GETTERS.open_h5_file_read(path)
    chromas = BAF.GETTERS.get_segments_pitches(h5)
    segstarts = BAF.GETTERS.get_segments_start(h5)
    if compression >= 1:
        btstarts = BAF.GETTERS.get_beats_start(h5)[::compression]
    elif compression == .5:
        btstarts = BAF.GETTERS.get_beats_start(h5)
        interpvals = np.interp(range(1,len(btstarts)*2-1,2),
                               range(0,len(btstarts)*2,2), btstarts)
        btstarts = np.array(zip(btstarts,interpvals)).flatten()
    else:
        print 'COMPRESSION OF %d NOT IMPLEMENTED YET' % compression
        raise NotImplementedError
    if add_loudness: # loudness specific stuff
        btloudmax = BAF.get_btloudnessmax(h5)
        loudnessmax = BAF.GETTERS.get_segments_loudness_max(h5)
    duration = BAF.GETTERS.get_duration(h5)
    h5.close()
    segstarts = np.array(segstarts).flatten()
    btstarts = np.array(btstarts).flatten()
    # add back loudness and aligning
    chromas = chromas.T
    if add_loudness:
        chromas = (chromas) * BAF.idB(loudnessmax)
        #pass
    btchroma = BAF.align_feats(chromas, segstarts, btstarts, duration)
    if btchroma is None:
        return None
    # can we do something with these?
    if add_loudness:
        #btchroma = btchroma * btloudmax
        # normalize
        btchroma = BAF.dB(btchroma+1e-10)
        btchroma -= btchroma.min()
        #assert not np.isnan(btchroma).any()
        btchroma /= btchroma.max()
        #btchroma = renorm_chroma(btchroma) # EXPERIMENTAL
        # still not correct!
    # Renormalize. Each column max is 1.
    if not add_loudness:
        maxs = btchroma.max(axis=0)
        maxs[np.where(maxs == 0)] = 1.
        btchroma = (btchroma / maxs)
    return btchroma
        

def renorm_chroma(chroma):
    """
    Weird method to put all chroma values between 0 and 1 where
    the max of each column gets 1, the second 1-1/11, ... the last 0
    """
    t1 = time.time()
    assert chroma.shape[0] == 12
    s = np.argsort(chroma, axis=0)
    #chroma = 1. - 1./s  # we create inf, we could do something faster
    #chroma[np.isinf(chroma)] = 1.
    chroma = 1. - 1./(s+1.)
    return chroma


def path_from_tid(maindir, tid):
    """
    Returns a full path based on a main directory and a track id
    """
    p = os.path.join(maindir, tid[2])
    p = os.path.join(p, tid[3])
    p = os.path.join(p, tid[4])
    p = os.path.join(p, tid.upper() + '.h5')
    return p


def read_cover_list(filename):
    """
    Read shs_dataset_train.txt or similarly formatted file.
    Return
      * clique -> tids dict
      * clique -> name
    clique are random integer numbers
    """
    clique_tid = {}
    clique_name = {}
    f = open(filename, 'r')
    for line in f.xreadlines():
        if line == '' or line.strip() == '' or line[0] == '#':
            continue
        if line[0] == '%':
            clique_id = len(clique_tid) + 1
            clique_name[clique_id] = line.strip()
            continue
        tid = line.strip().split('<SEP>')[0]
        if clique_id in clique_tid.keys():
            clique_tid[clique_id].append(tid)
        else:
            clique_tid[clique_id] = [tid]
    num_tids = sum(map(lambda a: len(a), clique_tid.values()))
    print 'Found %d cliques for a total of %d tids in %s.' % (len(clique_tid), num_tids,
                                                              filename)
    return clique_tid, clique_name


def get_jumps(btchroma, verbose=0):
    """
    Use fingerprinting hash
    """
    landmarks = FH.get_landmarks(btchroma, decay=DECAY, max_per_frame=MAX_PER_FRAME, verbose=verbose)
    jumps = FH.get_jumps(landmarks, win=WIN)
    return jumps


def one_exp(maindir, clique_tid, verbose=0):
    """
    performs one experiment:
      - select two covers
      - select random song
      - computes hashes / jumps
      - return 1 if we return cover correctly, 0 otherwise
    """
    # select cliques
    cliques = sorted(clique_tid.keys())
    np.random.shuffle(cliques)
    cl = cliques[0]
    other_cl = cliques[1]
    # select tracks
    tids = sorted(clique_tid[cl])
    np.random.shuffle(tids)
    query = tids[0]
    good_ans = tids[1]
    len_other_tids = len(clique_tid[other_cl])
    bad_ans = clique_tid[other_cl][np.random.randint(len_other_tids)]
    # create hash table, init
    conn = sqlite3.connect(':memory:')
    conn.execute('PRAGMA synchronous = OFF;')
    conn.execute('PRAGMA journal_mode = OFF;')
    conn.execute('PRAGMA page_size = 4096;')
    conn.execute('PRAGMA cache_size = 250000;')
    CHT.init_db(conn)
    # verbose
    if verbose>0:
        t1 = time.time()
    # compression (still testing)
    for cid, compression in enumerate(COMPRESSION):
        # get btchromas
        query_path = path_from_tid(maindir, query)
        query_btc = get_cpressed_btchroma(query_path, compression=compression)
        good_ans_path = path_from_tid(maindir, good_ans)
        good_ans_btc = get_cpressed_btchroma(good_ans_path, compression=compression)
        bad_ans_path = path_from_tid(maindir, bad_ans)
        bad_ans_btc = get_cpressed_btchroma(bad_ans_path, compression=compression)
        if query_btc is None or good_ans_btc is None or bad_ans_btc is None:
            conn.close()
            return None
        # get hashes (jumps) for good / bad answer
        jumps = get_jumps(query_btc, verbose=verbose)
        cjumps = FH.get_composed_jumps(jumps, levels=LEVELS, win=WIN)
        jumpcodes = map(lambda cj: FH.get_jumpcode_from_composed_jump(cj, maxwin=WIN), cjumps)
        if len(jumpcodes) == 0:
            print 'query has no jumpcode!'
            conn.close()
            return None
        #assert cid == 0
        CHT.add_jumpcodes(conn, query, jumpcodes, normalize=NORMALIZE, commit=False)
        # debug
        if verbose > 0:
            res = conn.execute("SELECT Count(tidid) FROM hashes1")
            print 'query added %d jumps' % res.fetchone()[0]
        # good ans
        jumps = get_jumps(good_ans_btc)
        cjumps = FH.get_composed_jumps(jumps, levels=LEVELS, win=WIN, verbose=verbose)
        jumpcodes = map(lambda cj: FH.get_jumpcode_from_composed_jump(cj, maxwin=WIN), cjumps)
        CHT.add_jumpcodes(conn, good_ans, jumpcodes, normalize=NORMALIZE, commit=False)
        # bad ans
        jumps = get_jumps(bad_ans_btc)
        cjumps = FH.get_composed_jumps(jumps, levels=LEVELS, win=WIN)
        jumpcodes = map(lambda cj: FH.get_jumpcode_from_composed_jump(cj, maxwin=WIN), cjumps)
        CHT.add_jumpcodes(conn, bad_ans, jumpcodes, normalize=NORMALIZE, commit=False)
    conn.commit()
    # indices
    q = "CREATE INDEX tmp_idx1 ON hashes1 ('jumpcode', 'weight')"
    conn.execute(q)
    q = "CREATE INDEX tmp_idx2 ON hashes1 ('tidid')"
    conn.execute(q)
    conn.commit()
    # verbose
    if verbose > 0:
        print 'Extracted/added jumps and indexed the db in %f seconds.' % (time.time()-t1)
    # get query
    #q = "SELECT jumpcode, weight FROM hashes WHERE tid='" + query + "'"
    #res = conn.execute(q)
    #res = res.fetchall()
    #jumps = map(lambda x: x[0], res)
    #weights = map(lambda x: x[1], res)
    jumps = None; weights = None
    # do the actual query
    tids = CHT.select_matches(conn, jumps, weights,
                              weight_margin=WEIGHT_MARGIN,
                              from_tid=query,
                              verbose=verbose)
    #assert tids[0] == query
    assert len(tids) < 4
    for t in tids:
        assert t in (query, bad_ans, good_ans)
    tids = np.array(tids)
    tids = tids[np.where(tids!=query)]
    # close connection
    conn.close()
    # check result
    if len(tids) == 0:
        print '(no matches)'
        return 0
    if tids[0] == good_ans:
        if verbose > 0:
            print 'We got it right!'
        return 1
    assert tids[0] == bad_ans
    if verbose > 0:
        print 'We got it wrong :('
    # DONE
    return 0 # 0 = error


def die_with_usage():
    """ HELP MENU """
    print 'Performs a few quick experiments to easily compare hashing'
    print 'methods without a full experiment.'
    print 'USAGE:'
    print '     python quick_query_test.py <maindir> <coverlist> <OPT: comment>'
    sys.exit(0)


if __name__ == '__main__':

    # help menu
    if len(sys.argv) < 3:
        die_with_usage()

    # params
    maindir = sys.argv[1]
    coverlistf = sys.argv[2]

    # sanity checks
    if not os.path.isdir(maindir):
        print 'ERROR: %s does not exist.' % maindir
        sys.exit(0)
    if not os.path.isfile(coverlistf):
        print 'ERROR: %s does not exist.' % coverlistf
        sys.exit(0)
    
    # read cliques        
    clique_tid, clique_name = read_cover_list(coverlistf)

    # set random seed
    np.random.seed(RANDOMSEED)

    # params
    print '******************************'
    print 'PARAMS:'
    print 'DECAY = %f' % DECAY
    print 'WIN = %d' % WIN
    print 'NORMALIZE = %d' % NORMALIZE
    print 'WEIGHT_MARGIN = %f' % WEIGHT_MARGIN
    print 'MAX_PER_FRAME = %d' % MAX_PER_FRAME
    print 'COMPRESSION =', COMPRESSION
    print 'LEVELS =', LEVELS
    print '******************************'

    cnt = 0.
    cnt_exps = 0.
    for i_exp in range(NUM_EXPS):
        verbose = 0
        if (cnt_exps + 1) % 25 == 0:
            verbose = 1
        try:
            res = one_exp(maindir, clique_tid, verbose=verbose)
        except KeyboardInterrupt:
            break
        if res is None:
            continue
        assert res >= 0 and res <= 1
        cnt += res
        cnt_exps += 1.
        if (cnt_exps) % 50 == 0:
            print '***** Accuracy after %d tries: %f' % (cnt_exps,
                                                         cnt / cnt_exps)

    # params again
    print '******************************'
    print 'PARAMS:'
    print 'DECAY = %f' % DECAY
    print 'WIN = %d' % WIN
    print 'NORMALIZE = %d' % NORMALIZE
    print 'WEIGHT_MARGIN = %f' % WEIGHT_MARGIN
    print 'MAX_PER_FRAME = %d' % MAX_PER_FRAME
    print 'COMPRESSION =', COMPRESSION
    print 'LEVELS =', LEVELS
    if len(sys.argv) > 3:
        print 'comment:', sys.argv[3]
    print '******************************'

########NEW FILE########
__FILENAME__ = lyrics_to_bow
#!/usr/bin/env python
"""
Thierry Bertin-Mahieux (2011) Columbia University
tb2332@columbia.edu

This code shows how we created bag of words for the musiXmatch
dataset. I has a command line interface, but it is mostly a library
with one main function.

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.
http://labrosa.ee.columbia.edu/millionsong/

Copyright 2011, Thierry Bertin-Mahieux

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
try:
    from stemming.porter2 import stem
except ImportError:
    print 'You need to install the following stemming package:'
    print 'http://pypi.python.org/pypi/stemming/1.0'
    sys.exit(0)


def lyrics_to_bow(lyrics):
    """
    Main function to stem and create bag of words.
    It is what we used for the musiXmatch dataset.
    It is heavily oriented towards English lyrics, we apologize for that.
    INPUT
        lyrics as a string
    RETURN
        dictionary word -> count
        or None if something was wrong (e.g. not enough words)
    """
    # remove end of lines
    lyrics_flat = lyrics.replace('\r', '\n').replace('\n', ' ').lower()
    lyrics_flat = ' ' + lyrics_flat + ' '
    # special cases (English...)
    lyrics_flat = lyrics_flat.replace("'m ", " am ")
    lyrics_flat = lyrics_flat.replace("'re ", " are ")
    lyrics_flat = lyrics_flat.replace("'ve ", " have ")
    lyrics_flat = lyrics_flat.replace("'d ", " would ")
    lyrics_flat = lyrics_flat.replace("'ll ", " will ")
    lyrics_flat = lyrics_flat.replace(" he's ", " he is ")
    lyrics_flat = lyrics_flat.replace(" she's ", " she is ")
    lyrics_flat = lyrics_flat.replace(" it's ", " it is ")
    lyrics_flat = lyrics_flat.replace(" ain't ", " is not ")
    lyrics_flat = lyrics_flat.replace("n't ", " not ")
    lyrics_flat = lyrics_flat.replace("'s ", " ")
    # remove boring punctuation and weird signs
    punctuation = (',', "'", '"', ",", ';', ':', '.', '?', '!', '(', ')',
                   '{', '}', '/', '\\', '_', '|', '-', '@', '#', '*')
    for p in punctuation:
        lyrics_flat = lyrics_flat.replace(p, '')
    words = filter(lambda x: x.strip() != '', lyrics_flat.split(' '))
    # stem words
    words = map(lambda x: stem(x), words)
    bow = {}
    for w in words:
        if not w in bow.keys():
            bow[w] = 1
        else:
            bow[w] += 1
    # remove special words that are wrong
    fake_words = ('>', '<', 'outro~')
    bowwords = bow.keys()
    for bw in bowwords:
        if bw in fake_words:
            bow.pop(bw)
        elif bw.find(']') >= 0:
            bow.pop(bw)
        elif bw.find('[') >= 0:
            bow.pop(bw)
    # not big enough? remove instrumental ones among others
    if len(bow) <= 3:
        return None
    # done
    return bow


def die_with_usage():
    """ HELP MENU """
    print 'lyrics_to_bow.py'
    print '   by T. Bertin-Mahieux (2011) Columbia University'
    print '      tb2332@columbia.edu'
    print 'This code shows how we transformed lyrics into bag-of-words.'
    print 'It is mostly intended to be used as a library, but you can pass'
    print 'in lyrics and we print the resulting dictionary.'
    print ''
    print 'USAGE:'
    print '  ./lyrics_to_bow.py <lyrics>'
    print 'PARAMS:'
    print '    <lyrics>  - lyrics as one string'
    sys.exit(0)


if __name__ == '__main__':

    # help menu
    if len(sys.argv) < 2:
        die_with_usage()

    # params (lyrics)
    lyrics = ''
    for word in sys.argv[2:]:
        lyrics += ' ' + word
    lyrics = lyrics.strip()

    # make bag of words
    bow = lyrics_to_bow(lyrics)
    if bow is None:
        print 'ERROR, maybe there was not enough words to be realistic?'
        sys.exit(0)

    # print result
    try:
        from operator import itemgetter
        print sorted(bow.items(), key=itemgetter(1), reverse=True)
    except ImportError:
        print bow

########NEW FILE########
__FILENAME__ = mxm_dataset_to_db
#!/usr/bin/env python
"""
Thierry Bertin-Mahieux (2011) Columbia University
tb2332@columbia.edu

This code puts the musiXmatch dataset (format: 2 text files)
into a SQLite database for ease of use.

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.
http://labrosa.ee.columbia.edu/millionsong/

Copyright 2011, Thierry Bertin-Mahieux

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import sqlite3


def encode_string(s):
    """
    Simple utility function to make sure a string is proper
    to be used in a SQLite query
    (different than posgtresql, no N to specify unicode)
    EXAMPLE:
      That's my boy! -> 'That''s my boy!'
    """
    return "'" + s.replace("'", "''") + "'"


def die_with_usage():
    """ HELP MENU """
    print 'mxm_dataset_to_db.py'
    print '   by T. Bertin-Mahieux (2011) Columbia University'
    print '      tb2332@columbia.edu'
    print 'This code puts the musiXmatch dataset into an SQLite database.'
    print ''
    print 'USAGE:'
    print '  ./mxm_dataset_to_db.py <train> <test> <output.db>'
    print 'PARAMS:'
    print '      <train>  - mXm dataset text train file'
    print '       <test>  - mXm dataset text test file'
    print '  <output.db>  - SQLite database to create'
    sys.exit(0)


if __name__ == '__main__':

    # help menu
    if len(sys.argv) < 4:
        die_with_usage()

    # params
    trainf = sys.argv[1]
    testf = sys.argv[2]
    outputf = sys.argv[3]

    # sanity checks
    if not os.path.isfile(trainf):
        print 'ERROR: %s does not exist.' % trainf
        sys.exit(0)
    if not os.path.isfile(testf):
        print 'ERROR: %s does not exist.' % testf
        sys.exit(0)
    if os.path.exists(outputf):
        print 'ERROR: %s already exists.' % outputf
        sys.exit(0)

    # open output SQLite file
    conn = sqlite3.connect(outputf)

    # create tables -> words and lyrics
    q = "CREATE TABLE words (word TEXT PRIMARY KEY)"
    conn.execute(q)
    q = "CREATE TABLE lyrics (track_id,"
    q += " mxm_tid INT,"
    q += " word TEXT,"
    q += " count INT,"
    q += " is_test INT,"
    q += " FOREIGN KEY(word) REFERENCES words(word))"
    conn.execute(q)

    # get words, put them in the words table
    f = open(trainf, 'r')
    for line in f.xreadlines():
        if line == '':
            continue
        if line[0] == '%':
            topwords = line.strip()[1:].split(',')
            f.close()
            break
    for w in topwords:
        q = "INSERT INTO words VALUES("
        q += encode_string(w) + ")"
        conn.execute(q)
    conn.commit()
    # sanity check, make sure the words were entered according
    # to popularity, most popular word should have ROWID 1
    q = "SELECT ROWID, word FROM words ORDER BY ROWID"
    res = conn.execute(q)
    tmpwords = res.fetchall()
    assert len(tmpwords) == len(topwords), 'Number of words issue.'
    for k in range(len(tmpwords)):
        assert tmpwords[k][0] == k + 1, 'ROWID issue.'
        assert tmpwords[k][1].encode('utf-8') == topwords[k], 'ROWID issue.'
    print "'words' table filled, checked."

    # we put the train data in the dataset
    f = open(trainf, 'r')
    cnt_lines = 0
    for line in f.xreadlines():
        if line == '' or line.strip() == '':
            continue
        if line[0] in ('#', '%'):
            continue
        lineparts = line.strip().split(',')
        tid = lineparts[0]
        mxm_tid = lineparts[1]
        for wordcnt in lineparts[2:]:
            wordid, cnt = wordcnt.split(':')
            q = "INSERT INTO lyrics"
            q += " SELECT '" + tid + "', " + mxm_tid + ", "
            q += " words.word, " + cnt + ", 0"
            q += " FROM words WHERE words.ROWID=" + wordid
            conn.execute(q)
        # verbose
        cnt_lines += 1
        if cnt_lines % 15000 == 0:
            print 'Done with %d train tracks.' % cnt_lines
            conn.commit()
    f.close()
    conn.commit()
    print 'Train lyrics added.'

    # we put the test data in the dataset
    # only difference from train: is_test is now 1
    f = open(testf, 'r')
    cnt_lines = 0
    for line in f.xreadlines():
        if line == '' or line.strip() == '':
            continue
        if line[0] in ('#', '%'):
            continue
        lineparts = line.strip().split(',')
        tid = lineparts[0]
        mxm_tid = lineparts[1]
        for wordcnt in lineparts[2:]:
            wordid, cnt = wordcnt.split(':')
            q = "INSERT INTO lyrics"
            q += " SELECT '" + tid + "', " + mxm_tid + ", "
            q += " words.word, " + cnt + ", 1"
            q += " FROM words WHERE words.ROWID=" + wordid
            conn.execute(q)
        # verbose
        cnt_lines += 1
        if cnt_lines % 15000 == 0:
            print 'Done with %d test tracks.' % cnt_lines
            conn.commit()
    f.close()
    conn.commit()
    print 'Test lyrics added.'

    # create indices
    q = "CREATE INDEX idx_lyrics1 ON lyrics ('track_id')"
    conn.execute(q)
    q = "CREATE INDEX idx_lyrics2 ON lyrics ('mxm_tid')"
    conn.execute(q)
    q = "CREATE INDEX idx_lyrics3 ON lyrics ('word')"
    conn.execute(q)
    q = "CREATE INDEX idx_lyrics4 ON lyrics ('count')"
    conn.execute(q)
    q = "CREATE INDEX idx_lyrics5 ON lyrics ('is_test')"
    conn.execute(q)
    conn.commit()
    print 'Indices created.'

    # close output SQLite connection
    conn.close()

########NEW FILE########
__FILENAME__ = split_mxm_dataset
#!/usr/bin/env python
"""
Thierry Bertin-Mahieux (2011) Columbia University
tb2332@columbia.edu

This code splits the full musiXmatch dataset into train and
test using the same split as for automatic tagging.

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.
http://labrosa.ee.columbia.edu/millionsong/

Copyright 2011, Thierry Bertin-Mahieux

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import glob
import time
import datetime
import sqlite3


def die_with_usage():
    """ HELP MENU """
    print 'split_mxm_dataset.py'
    print '   by T. Bertin-Mahieux (2011) Columbia University'
    print '      tb2332@columbia.edu'
    print 'This code splits the full musiXmatch dataset based on the'
    print 'artist split used for automatic music tagging.'
    print 'This code is provided more as a demo than anything else,'
    print 'you should have received the musiXmatch dataset alredy split.'
    print ''
    print 'USAGE:'
    print '  ./split_mxm_dataset.py <mxmset> <tmdb> <test_aids> <train> <test>'
    print 'PARAMS:'
    print '     <mxmset>  - full musiXmatch dataset'
    print '       <tmdb>  - SQLite database track_metadata.db'
    print '  <test_aids>  - list of test artist IDs (for automatic tagging)'
    print '      <train>  - output train file'
    print '       <test>  - output test file'
    sys.exit(0)


if __name__ == '__main__':

    # help menu
    if len(sys.argv) < 6:
        die_with_usage()

    # params
    mxm_dataset = sys.argv[1]
    tmdb = sys.argv[2]
    testartistsf = sys.argv[3]
    trainf = sys.argv[4]
    testf = sys.argv[5]

    # sanity checks
    if not os.path.isfile(mxm_dataset):
        print 'ERROR: %s does not exist.' % mxm_dataset
        sys.exit(0)
    if not os.path.isfile(tmdb):
        print 'ERROR: %s does not exist.' % tmdb
        sys.exit(0)
    if not os.path.isfile(testartistsf):
        print 'ERROR: %s does not exist.' % testartistsf
        sys.exit(0)
    if os.path.isfile(trainf):
        print 'ERROR: %s already exists.' % trainf
        sys.exit(0)
    if os.path.isfile(testf):
        print 'ERROR: %s already exists.' % testf
        sys.exit(0)

    # open connection to track_metadata.db
    conn = sqlite3.connect(tmdb)

    # load test artists, put them in the database
    q = "CREATE TEMP TABLE testaids (aid TEXT PRIMARY KEY)"
    conn.execute(q)
    f = open(testartistsf, 'r')
    for line in f.xreadlines():
        if line == '' or line.strip() == '' or line[0] == '#':
            continue
        q = "INSERT INTO testaids VALUES ('" + line.strip() + "')"
        conn.execute(q)
    f.close()
    conn.commit()
    # verbose: check number of artists
    q = "SELECT aid FROM testaids"
    res = conn.execute(q)
    print 'We have %d test artists.' % len(res.fetchall())

    def is_test(tid):
        """
        Create simple function to decide if a song is from a test artist
        based on its track ID
        """
        q = "SELECT testaids.aid FROM testaids JOIN songs"
        q += " ON testaids.aid=songs.artist_id"
        q += " WHERE songs.track_id='" + tid + "'"
        q += " LIMIT 1"
        res = conn.execute(q)
        if len(res.fetchall()) == 0:
            return False
        return True

    # we open dataset and output files and start writing
    fIn = open(mxm_dataset, 'r')
    train = open(trainf, 'w')
    test = open(testf, 'w')

    # write intro to output file
    train.write('# TRAINING SET\n')
    test.write('# TESTING SET\n')

    # stats for verbose / debugging
    cnt_train = 0
    cnt_test = 0

    # iterate over lines in the full musiXmatch dataset
    for line in fIn.xreadlines():
        if line == '' or line.strip() == '':
            continue
        # comment
        if line[0] == '#':
            train.write(line)
            test.write(line)
            continue
        # list of words
        if line[0] == '%':
            train.write(line)
            test.write(line)
            continue
        # normal line (lyrics for one track)
        tid = line.split(',')[0]
        if is_test(tid):
            cnt_test += 1
            test.write(line)
        else:
            cnt_train += 1
            train.write(line)

    # we close the files
    fIn.close()
    train.close()
    test.close()

    # close SQLite connection to track_metadata.db
    conn.close()

    # done
    print 'DONE! We have %d train tracks and %d test tracks' % (cnt_train,
                                                                cnt_test)

########NEW FILE########
__FILENAME__ = list_all_artists
"""
Thierry Bertin-Mahieux (2010) Columbia University
tb2332@columbia.edu

This code contains code to parse the dataset and list
all artists. It can either be used as a library, or
as a standalone if we want the result to be output to a file.

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.


Copyright 2010, Thierry Bertin-Mahieux

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import glob
import time
import datetime


def get_artistid_trackid_artistname(trackfile):
    """
    Utility function, opens a h5 file, gets the 4 following fields:
     - artist Echo Nest ID
     - artist Musicbrainz ID
     - track Echo Nest ID
     - artist name
    It is returns as a triple (,,)
    Assumes one song per file only!
    """
    h5 = hdf5_utils.open_h5_file_read(trackfile)
    assert GETTERS.get_num_songs(h5) == 1,'code must be modified if more than one song per .h5 file'
    aid = GETTERS.get_artist_id(h5)
    ambid = GETTERS.get_artist_mbid(h5)
    tid = GETTERS.get_track_id(h5)
    aname = GETTERS.get_artist_name(h5)
    h5.close()
    return aid,ambid,tid,aname

def list_all(maindir):
    """
    Goes through all subdirectories, open every song file,
    and list all artists it finds.
    It returns a dictionary of string -> tuples:
       artistID -> (musicbrainz ID, trackID, artist_name)
    The track ID is random, i.e. the first one we find for that
    artist. The artist information should be the same in all track
    files from that artist.
    We assume one song per file, if not, must be modified to take
    into account the number of songs in each file.
    INPUT
      maindir  - top directory of the dataset, we will parse all
                 subdirectories for .h5 files
    RETURN
      dictionary that maps artist ID to tuple (MBID, track ID, artist name)
    """
    results = {}
    numfiles = 0
    # iterate over all files in all subdirectories
    for root, dirs, files in os.walk(maindir):
        # keep the .h5 files
        files = glob.glob(os.path.join(root,'*.h5'))
        for f in files :
            numfiles +=1
            # get the info we want
            aid,ambid,tid,aname = get_artistid_trackid_artistname(f)
            assert aid != '','null artist id in track file: '+f
            # check if we know that artist
            if aid in results.keys():
                continue
            # we add to the results dictionary
            results[aid] = (ambid,tid,aname)
    # done
    return results


def die_with_usage():
    """ HELP MENU """
    print 'list_all_artists.py'
    print '   by T. Bertin-Mahieux (2010) Columbia University'
    print ''
    print 'usage:'
    print '  python list_all_artists.py <DATASET DIR> output.txt'
    print ''
    print 'This code lets you list all artists contained in all'
    print 'subdirectories of a given directory.'
    print 'This script puts the result in a text file, but its main'
    print 'function can be used by other codes.'
    print 'The txt file format is: (we use <SEP> as separator symbol):'
    print 'artist Echo Nest ID<SEP>artist Musicbrainz ID<SEP>one track Echo Nest ID<SEP>artist name'
    sys.exit(0)



if __name__ == '__main__':

    # help menu
    if len(sys.argv) < 3:
        die_with_usage()

    # Million Song Dataset imports, works under Linux
    # otherwise, put the PythonSrc directory in the PYTHONPATH!
    pythonsrc = os.path.join(sys.argv[0],'../../../PythonSrc')
    pythonsrc = os.path.abspath( pythonsrc )
    sys.path.append( pythonsrc )
    import hdf5_utils
    import hdf5_getters as GETTERS

    # params
    maindir = sys.argv[1]
    output = sys.argv[2]

    # sanity checks
    if not os.path.isdir(maindir):
        print maindir,'is not a directory'
        sys.exit(0)
    if os.path.isfile(output):
        print 'output file:',output,'exists, please delete or choose new one'
        sys.exit(0)

    # go!
    t1 = time.time()
    dArtists = list_all(maindir)
    t2 = time.time()
    stimelength = str(datetime.timedelta(seconds=t2-t1))
    print 'number of artists found:', len(dArtists),'in',stimelength


    # print to file
    artistids = dArtists.keys()
    try:
        import numpy
        artistids = numpy.sort(artistids)
    except ImportError:
        print 'artists IDs will not be sorted alphabetically (numpy not installed)'
    f = open(output,'w')
    for aid in artistids:
        ambid,tid,aname = dArtists[aid]
        f.write(aid+'<SEP>'+ambid+'<SEP>'+tid+'<SEP>'+aname+'\n')
    f.close()

    # FUN STATS! (require numpy)
    try:
        import numpy as np
    except ImportError:
        print 'no numpy, no fun stats!'
        sys.exit(0)
    import re
    print 'FUN STATS!'
    # name length
    name_lengths = map(lambda x: len(dArtists[x][2]), artistids)
    print 'average artist name length:',np.mean(name_lengths),'(std =',str(np.std(name_lengths))+')'
    # most common word
    dWords = {}
    for ambid,tid,aname in dArtists.values():
        words = re.findall(r'\w+', aname.lower())
        for w in words:
            if w in dWords.keys():
                dWords[w] += 1
            else:
                dWords[w] = 1
    words = dWords.keys()
    wfreqs = map(lambda x: dWords[x], words)
    pos = np.argsort(wfreqs)
    pos = pos[-1::-1]
    print 'number of different words used:',len(words)
    print 'the most used words in artist names are:'
    for p in pos[:5]:
        print '*',words[p],'(freq='+str(wfreqs[p])+')'
    print 'some artists using the 30th most frequent word ('+words[pos[30]]+'):'
    frequentword = words[pos[30]]
    cnt = 0
    for ambid,tid,aname in dArtists.values():
        words = re.findall(r'\w+', aname.lower())
        if frequentword in words:
            print '*',aname
            cnt += 1
        if cnt >= min(5,wfreqs[pos[10]]):
            break

########NEW FILE########
__FILENAME__ = get_preview_url
"""
Thierry Bertin-Mahieux (2010) Columbia University
tb2332@columbia.edu


This code uses 7digital API and info contained in HDF5 song
file to get a preview URL.

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.


Copyright 2010, Thierry Bertin-Mahieux

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import urllib2
try:
    from numpy import argmin
except ImportError:
    from scipy import argmin
except ImportError:
    print 'no argmin function (no numpy or scipy), might cause problems'
from xml.dom import minidom

# Million Song Dataset imports, works under Linux
# otherwise, put the PythonSrc directory in the PYTHONPATH!
pythonsrc = os.path.abspath('__file__')
pythonsrc = os.path.join(pythonsrc,'../../../PythonSrc')
pythonsrc = os.path.abspath( pythonsrc )
sys.path.append( pythonsrc )
import hdf5_utils
import hdf5_getters as GETTERS

# try to get 7digital API key
global DIGITAL7_API_KEY
try:
    DIGITAL7_API_KEY = os.environ['DIGITAL7_API_KEY']
except KeyError:
    DIGITAL7_API_KEY = None



def url_call(url):
    """
    Do a simple request to the 7digital API
    We assume we don't do intense querying, this function is not
    robust
    Return the answer as na xml document
    """
    stream = urllib2.urlopen(url)
    xmldoc = minidom.parse(stream).documentElement
    stream.close()
    return xmldoc


def levenshtein(s1, s2):
    """
    Levenstein distance, or edit distance, taken from Wikibooks:
    http://en.wikibooks.org/wiki/Algorithm_implementation/Strings/Levenshtein_distance#Python
    """
    if len(s1) < len(s2):
        return levenshtein(s2, s1)
    if not s1:
        return len(s2)
 
    previous_row = xrange(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1 # j+1 instead of j since previous_row and current_row are one character longer
            deletions = current_row[j] + 1       # than s2
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
 
    return previous_row[-1]


def get_closest_track(tracklist,target):
    """
    Find the closest track based on edit distance
    Might not be an exact match, you should check!
    """
    dists = map(lambda x: levenshtein(x,target),tracklist)
    best = argmin(dists)
    return tracklist[best]


def get_trackid_from_text_search(title,artistname=''):
    """
    Search for an artist + title using 7digital search API
    Return None if there is a problem, or tuple (title,trackid)
    """
    url = 'http://api.7digital.com/1.2/track/search?'
    url += 'oauth_consumer_key='+DIGITAL7_API_KEY
    query = title
    if artistname != '':
        query = artistname + ' ' + query
    query = urllib2.quote(query)
    url += '&q='+query
    xmldoc = url_call(url)
    status = xmldoc.getAttribute('status')
    if status != 'ok':
        return None
    resultelem = xmldoc.getElementsByTagName('searchResult')
    if len(resultelem) == 0:
        return None
    track = resultelem[0].getElementsByTagName('track')[0]
    tracktitle = track.getElementsByTagName('title')[0].firstChild.data
    trackid = int(track.getAttribute('id'))
    return (tracktitle,trackid)

    
def get_tracks_from_artistid(artistid):
    """
    We get a list of release from artists.
    For each of these, get release.
    After calling the API with a given release ID, we receive a list of tracks.
    We return a map of <track name> -> <track id>
    or None if there is a problem
    """
    url = 'http://api.7digital.com/1.2/artist/releases?'
    url += '&artistid='+str(artistid)
    url += '&oauth_consumer_key='+DIGITAL7_API_KEY
    xmldoc = url_call(url)
    status = xmldoc.getAttribute('status')
    if status != 'ok':
        return None
    releaseselem = xmldoc.getElementsByTagName('releases')[0]
    releases = releaseselem.getElementsByTagName('release')
    if len(releases) == 0:
        return None
    releases_ids = map(lambda x: int(x.getAttribute('id')), releases)
    res = {}
    for rid in releases_ids:
        tmpres = get_tracks_from_releaseid(rid)
        if tmpres is not None:
            res.update(tmpres)
    return res


def get_tracks_from_releaseid(releaseid):
    """
    After calling the API with a given release ID, we receive a list of tracks.
    We return a map of <track name> -> <track id>
    or None if there is a problem
    """
    url = 'http://api.7digital.com/1.2/release/tracks?'
    url += 'releaseid='+str(releaseid)
    url += '&oauth_consumer_key='+DIGITAL7_API_KEY
    xmldoc = url_call(url)
    status = xmldoc.getAttribute('status')
    if status != 'ok':
        return None
    tracks = xmldoc.getElementsByTagName('track')
    if len(tracks)==0:
        return None
    res = {}
    for t in tracks:
        tracktitle = t.getElementsByTagName('title')[0].firstChild.data
        trackid = int(t.getAttribute('id'))
        res[tracktitle] = trackid
    return res
    

def get_preview_from_trackid(trackid):
    """
    Ask for the preview to a particular track, get the XML answer
    After calling the API with a given track id,
    we get an XML response that looks like:
    
    <response status="ok" version="1.2" xsi:noNamespaceSchemaLocation="http://api.7digital.com/1.2/static/7digitalAPI.xsd">
      <url>
        http://previews.7digital.com/clips/34/6804688.clip.mp3
      </url>
    </response>

    We parse it for the URL that we return, or '' if a problem
    """
    url = 'http://api.7digital.com/1.2/track/preview?redirect=false'
    url += '&trackid='+str(trackid)
    url += '&oauth_consumer_key='+DIGITAL7_API_KEY
    xmldoc = url_call(url)
    status = xmldoc.getAttribute('status')
    if status != 'ok':
        return ''
    urlelem = xmldoc.getElementsByTagName('url')[0]
    preview = urlelem.firstChild.nodeValue
    return preview


def die_with_usage():
    """ HELP MENU """
    print 'get_preview_url.py'
    print '    by T. Bertin-Mahieux (2010) Columbia University'
    print 'HELP MENU'
    print 'usage:'
    print '    python get_preview_url.py [FLAG] <SONGFILE>'
    print 'PARAMS:'
    print '  <SONGFILE>  - a Million Song Dataset file TRABC...123.h5'
    print 'FLAGS:'
    print '  -7digitalkey KEY - API key from 7 digital, we recomment you put it'
    print '                     under environment variable: DIGITAL7_API_KEY'
    print 'OUTPUT:'
    print '  url from 7digital that should play a clip of the song.'
    print '  No guarantee that this is the exact audio used for the analysis'
    sys.exit(0)


if __name__ == '__main__':

    # help menu
    if len(sys.argv) < 2:
        die_with_usage()

    # flags
    while True:
        if sys.argv[1] == '-7digitalkey':
            DIGITAL7_API_KEY = sys.argv[2]
            sys.argv.pop(1)
        else:
            break
        sys.argv.pop(1)

    # params
    h5path = sys.argv[1]

    # sanity checks
    if DIGITAL7_API_KEY is None:
        print 'You need to set a 7digital API key!'
        print 'Get one at: http://developer.7digital.net/'
        print 'Pass it as a flag: -7digitalkey KEY'
        print 'or set it under environment variable: DIGITAL7_API_KEY'
        sys.exit(0)
    if not os.path.isfile(h5path):
        print 'invalid path (not a file):',h5path
        sys.exit(0)


    # open h5 song, get all we know about the song
    h5 = hdf5_utils.open_h5_file_read(h5path)
    track_7digitalid = GETTERS.get_track_7digitalid(h5)
    release_7digitalid = GETTERS.get_release_7digitalid(h5)
    artist_7digitalid = GETTERS.get_artist_7digitalid(h5)
    artist_name = GETTERS.get_artist_name(h5)
    release_name = GETTERS.get_release(h5)
    track_name = GETTERS.get_title(h5)
    h5.close()

    # we already have the 7digital track id? way too easy!
    if track_7digitalid >= 0:
        preview = get_preview_from_trackid(track_7digitalid)
        if preview == '':
            print 'something went wrong when looking by track id'
        else:
            print preview
            sys.exit(0)

    # we have the release id? get all tracks, find the closest match
    if release_7digitalid >= 0:
        tracks_name_ids = get_tracks_from_releaseid(release_7digitalid)
        if tracks_name_ids is None:
            print 'something went wrong when looking by album id'
        else:
            closest_track = get_closest_track(tracks_name_ids.keys(),track_name)
            if closest_track != track_name:
                print 'we approximate your song title:',track_name,'by:',closest_track
            preview = get_preview_from_trackid(tracks_name_ids[closest_track])
            if preview == '':
                print 'something went wrong when looking by track id after release id'
            else:
                print preview
                sys.exit(0)
            
    # we have the artist id? get all albums, get all tracks, find the closest match
    if artist_7digitalid >= 0:
        tracks_name_ids = get_tracks_from_artistid(artist_7digitalid)
        if tracks_name_ids is None:
            print 'something went wrong when looking by artist id'
        else:
            closest_track = get_closest_track(tracks_name_ids.keys(),track_name)
            if closest_track != track_name:
                print 'we approximate your song title:',track_name,'by:',closest_track
            preview = get_preview_from_trackid(tracks_name_ids[closest_track])
            if preview == '':
                print 'something went wrong when looking by track id after artist id'
            else:
                print preview
                sys.exit(0)

    # damn it! search by artist name + track title
    else:
        res = get_trackid_from_text_search(track_name,artistname=artist_name)
        if res is None:
            print 'something went wrong when doing text search with artist and track name, no more ideas'
            sys.exit(0)
        closest_track,trackid = res
        if closest_track != track_name:
            print 'we approximate your song title:',track_name,'by:',closest_track
        preview = get_preview_from_trackid(trackid)
        if preview == '':
            print 'something went wrong when looking by track id after text searching by artist and track name'
        else:
            print preview
            sys.exit(0)
        

########NEW FILE########
__FILENAME__ = player_7digital
"""
Thierry Bertin-Mahieux (2010) Columbia University
tb2332@columbia.edu

This code uses 7digital API and info contained in HDF5 song
file to get a preview URL and play it.
It can be used to quickly listen to a song in the dataset.
The goal is to be able to search songs by artist name, title,
or Echo Nest ID.

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.


Copyright 2010, Thierry Bertin-Mahieux

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import time
import glob
import urllib
import urllib2
import sqlite3
import numpy as np
import threading
import get_preview_url as GETURL
try:
    from Tkinter import *
except ImportError:
    print 'you need Tkinter installed!'
    sys.exit(0)
try:
    import ao
except ImportError:
    print 'you need pyao installed!'
    sys.exit(0)
try:
    import mad
except ImportError:
    print 'you need pymad installed!'
    sys.exit(0)

# sampling rate from 7 digital
DIGITAL7SRATE=22500


def encode_string(s):
    """
    Simple utility function to make sure a string is proper
    to be used in a SQLite query
    (different than posgtresql, no N to specify unicode)
    EXAMPLE:
      That's my boy! -> 'That''s my boy!'
    """
    return "'"+s.replace("'","''")+"'"


class PlayerApp(Frame):
    """
    MAIN CLASS, contains the Tkinter app
    """
    def __init__(self, master=None, tmdb=None, url=''):
        """
        Contstructor
        INPUTS
           tmdb  - path to track_metadata.db (containing track_7digitalid)
           url   - more for debugging, starts with a loaded url
        """
        Frame.__init__(self, master)
        # verbose
        self.verbose=1
        # some class variables
        self.curr_track_id = None
        self.is_playing = False
        # db conn
        self.tmdb = tmdb
        self.conn_tmdb = sqlite3.connect(tmdb) if tmdb else None
        # grid and size
        self.grid(sticky=N+S+E+W)
        self.config(height=300,width=500)
        self.columnconfigure(0,minsize=60)
        self.grid_propagate(0)
        # add objects
        self.createButtons()
        self.createSearchFields()
        self.createListBoxes()
        # read url
        self.url = url

    def __del__(self):
        """ DESTRUCTOR """
        if not self.conn_tmdb is None:
            self.conn_tmdb.close()

    def createButtons(self):
        # quit
        self.quitButton = Button(self, text='Quit', command=self.do_quit)
        self.quitButton.grid(row=0,column=0,sticky=N+S+E+W)
        # search EN ID
        self.searchidButton = Button(self, text='Search by EN id', command=self.search_enid)
        self.searchidButton.grid(row=4,column=1,sticky=N+S+E+W)
        # search artist name
        self.searchTitleButton = Button(self, text='Search by Artist/Title', command=self.search_title)
        self.searchTitleButton.grid(row=5,column=3,sticky=N+S+E+W)
        # play
        self.playButton = Button(self,text='play', command=self.play_thread)
        self.playButton.grid(row=7,column=1,sticky=N+S+E+W)
        # stop
        self.stopButton = Button(self,text='stop', command=self.stop)
        self.stopButton.grid(row=7,column=2,sticky=N+S+E+W)

    def createSearchFields(self):
        # search Echo Nest ID
        self.entryENID = Entry(self)
        self.entryENID.grid(row=3,column=1,sticky=N+S+E+W)
        # search artist + title
        self.entryArtist = Entry(self)
        self.entryArtist.grid(row=3,column=3,sticky=N+S+E+W)
        self.entryTitle = Entry(self)
        self.entryTitle.grid(row=4,column=3,sticky=N+S+E+W)

    def createListBoxes(self):
        # vertical scrollbar
        self.yScroll = Scrollbar(self,orient=VERTICAL)
        self.yScroll.grid(row=6,column=5,sticky=N+S)
        # listbox
        self.listboxResult = Listbox(self,yscrollcommand=self.yScroll.set)
        self.listboxResult.grid(row=6,column=1,columnspan=4,
                                sticky=N+S+E+W)
        self.listboxResult.exportselection = 0 # prevent copy past
        self.listboxResult.selectmode = SINGLE # one line at a time

    #************************* COMMANDS FOR BUTTONS *******************#

    def update_display(self):
        """ update the main display (ListBox) from a given track_id """
        if self.curr_track_id is None:
            print "no current track id"
        conn = sqlite3.connect(self.tmdb)
        q = "SELECT artist_name,title FROM songs WHERE track_id='"+self.curr_track_id+"' LIMIT 1"
        res = conn.execute(q)
        data = res.fetchone()
        conn.close()
        self.listboxResult.insert(0,'**************************')
        self.listboxResult.insert(1,data[0])
        self.listboxResult.insert(2,data[1])
        self.listboxResult.insert(3,self.curr_track_id)
        if self.url:
            self.listboxResult.insert(4,self.url)

    def search_title(self):
        """ search using artist name and title """
        aname = self.entryArtist.get().strip()
        title = self.entryTitle.get().strip()
        if aname == '' or title == '':
            print 'Empty artist or title field:',aname,'/',title
            return
        # search
        q = "SELECT track_7digitalid,track_id FROM songs WHERE artist_name="+encode_string(aname)
        q += " AND title="+encode_string(title)+" LIMIT 1"
        res = self.conn_tmdb.execute(q)
        d7id = res.fetchone()
        if len(d7id) == 0 or d7id[0] == 0:
            print 'Sorry, we do not have the 7digital track ID for this one'
            return
        self.url = self.get_url_thread(d7id[0])
        self.curr_track_id = d7id[1]
        
    def search_enid(self):
        """ search for a song by its trackid or songid """
        tid = self.entryENID.get().strip().upper()
        if len(tid) != 18:
            print 'WRONG ECHO NEST ID:',tid,'(length='+str(len(tid))+')'
            return
        if tid[:2] != 'TR' and tid[:2] != 'SO':
            print 'WRONG ECHO NEST ID:',tid,'(should start by TR or SO)'
            return
        # we got an id, lets go
        if tid[:2] == 'TR':
            q = "SELECT track_7digitalid,track_id FROM songs WHERE track_id='"+tid+"' LIMIT 1"
            res = self.conn_tmdb.execute(q)
            d7id = res.fetchone()
        else:
            q = "SELECT track_7digitalid,track_id FROM songs WHERE song_id='"+tid+"' LIMIT 1"
            res = self.conn_tmdb.execute(q)
            d7id = res.fetchone()
        print 'for',tid,'we found 7digital track id:',d7id
        if len(d7id) == 0 or d7id[0] == 0:
            print 'Sorry, we do not have the 7digital track ID for this one'
            return
        self.url = self.get_url_thread(d7id[0])
        self.curr_track_id = d7id[1]

    def get_url_thread(self,d7id):
        """ launch 'get_url' as a thread, button does not stay pressed """
        t = threading.Thread(target=self.get_url,args=(d7id,))
        t.start()
        
    def get_url(self,d7id):
        """ get an url from a 7digital track id """
        url = GETURL.get_preview_from_trackid(d7id)
        print 'Found url:',url
        self.url = url
        self.update_display() # update main display

    def do_quit(self):
        """ quit but close stream before """
        self.stop()
        self.quit()
        
    def stop(self):
        self.do_stop = True

    def play_thread(self):
        """ launch 'play' as a thread, button does not stay pressed """
        t = threading.Thread(target=self.play)
        t.start()
        
    def play(self):
        """
        Main function that plays a 7digital url
        """
        if self.url == '':
            return
        if self.is_playing:
            return
        self.is_playing = True
        self.do_stop = False
        self.printinfo('start playing url:',self.url)
        #urldata = urllib.urlretrieve(self.url)
        urlstream = urllib2.urlopen(self.url)
        mf = mad.MadFile(urlstream)
        # if bits=32, too fast
        self.dev = ao.AudioDevice('alsa', bits=16, rate=mf.samplerate(),channels=2)
        buf = mf.read()
        t1 = time.time()
        while buf != None and not self.do_stop:
            # len(buf) is 4608
            self.dev.play(buf, len(buf))
            buf = mf.read()
        self.do_stop = False
        self.is_playing = False
        tlag = time.time() - t1
        self.printinfo('done playing url after',str(int(tlag)),'seconds')

    def printinfo(self,*msg):
        """ print message if verbose """
        if self.verbose>0:
            s = 'INFO:'
            for k in msg:
                s += ' ' + str(k)
            print s



def launch_applet(tmdb=None,url=''):
    """
    Should be the main function to launch the interface
    """
    app = PlayerApp(tmdb=tmdb,url=url)
    app.master.title("7digital Player for the Million Song Dataset")
    app.mainloop()
    

def die_with_usage():
    """ HELP MENU """
    print 'player_7digital.py'
    print '    by T. Bertin-Mahieux (2011) Columbia University'
    print '       tb2332@columbia.edu'
    print 'Small interface to the 7digital service.'
    print 'INPUT'
    print '   python player_7digital.py track_metadata.db'
    print 'REQUIREMENTS'
    print '  * 7digital key in your environment as: DIGITAL7_API_KEY'
    print '  * pyao'
    print '  * pymad'
    print '  * Tkinter for python'
    print '  * track_metadata.db (new one with 7digital ids, check website)'
    sys.exit(0)



if __name__ == '__main__':

    # help menu
    if len(sys.argv) < 2:
        die_with_usage()

    # check track metadata, makes sure it's the new version
    # with track_7digitalid
    tmdb = sys.argv[1]
    if not os.path.isfile(tmdb):
        print 'ERROR: file',tmdb,'does not exist.'
        sys.exit(0)
    conn = sqlite3.connect(tmdb)
    try:
        res = conn.execute("SELECT track_7digitalid FROM songs LIMIT 1")
        data = res.fetchone()
    except sqlite3.OperationalError:
        print 'ERROR: do you have the old track_metadata.db?'
        print '       get the new one with 7digital ids on the Million Song Dataset website'
        sys.exit(0)
    finally:
        conn.close()

    # launch interface
    url = ''
    launch_applet(tmdb=tmdb,url=url)

########NEW FILE########
__FILENAME__ = create_artist_similarity_db
"""
Thierry Bertin-Mahieux (2010) Columbia University
tb2332@columbia.edu

This code creates an SQLite database with two tables,
one for each unique artist in the Million Song dataset
(based on Echo Nest ID) and one with similarity among
artists according to the Echo Nest:
the first row is 'target', the second row is 'similar',
artists in similar are considered similar to the target.

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.


Copyright 2010, Thierry Bertin-Mahieux

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import glob
import time
import datetime
import numpy as np
try:
    import sqlite3
except ImportError:
    print 'you need sqlite3 installed to use this program'
    sys.exit(0)


def path_from_trackid(trackid):
    """
    Creates the path from a given trackid
    """
    s = os.path.join(trackid[2],trackid[3])
    s = os.path.join(s,trackid[4])
    s = os.path.join(s,trackid)
    s = s.upper() + '.h5'
    return s


def encode_string(s):
    """
    Simple utility function to make sure a string is proper
    to be used in a SQLite query
    (different than posgtresql, no N to specify unicode)
    EXAMPLE:
      That's my boy! -> 'That''s my boy!'
    """
    return "'"+s.replace("'","''")+"'"


def create_db(filename,artistlist):
    """
    Create a SQLite database with 2 tables
    table1: artists
            contains one column, artist_id
    table2: similarity
            contains two columns, target and similar
            both containing Echo Nest artist ID
            it means that 'similars' are similar to the
            target. It is not necessarily symmetric!
            Also, artists in here have at least one song
            in the dataset!
    INPUT
    - artistlist    list of all artist Echo Nest IDs
    """
    # creates file
    conn = sqlite3.connect(filename)
    c = conn.cursor()
    # create table 1 and fill it
    q = "CREATE TABLE artists (artist_id text PRIMARY KEY)"
    c.execute(q)
    conn.commit()
    artistlist = np.sort(artistlist)
    for aid in artistlist:
        q = "INSERT INTO artists VALUES ("
        q += encode_string(aid) + ")"
        c.execute(q)
    conn.commit()
    # create table 2
    q = "CREATE TABLE similarity (target text, similar text, "
    q += "FOREIGN KEY(target) REFERENCES artists(artist_id), "
    q += "FOREIGN KEY(similar) REFERENCES artists(artist_id) )"
    c.execute(q)
    conn.commit()

def fill_from_h5(conn,h5path):
    """
    Fill 'similarity' table from the information regarding the
    artist in that file, i.e. we get his similar artists, check
    if they are in the dataset, add them.
    Doesn't commit, doesn't close conn at the end!
    This h5 file must be for a new artist, we can't have twice the
    same artist entered in the database!

    The info is added to tables: similarity
    as many row as existing similar artists are added
    """
    # get info from h5 file
    h5 = open_h5_file_read(h5path)
    artist_id = get_artist_id(h5)
    sims = get_similar_artists(h5)
    h5.close()
    # add as many rows as terms in artist_term table
    for s in sims:
        q = "SELECT Count(artist_id) FROM artists WHERE"
        q += " artist_id="+encode_string(s)
        res = conn.execute(q)
        found = res.fetchone()[0]
        if found == 1:        
            q = "INSERT INTO similarity VALUES ("
            q += encode_string(artist_id) + "," + encode_string(s)
            q += ")"
            conn.execute(q)
    # done
    return


def add_indices_to_db(conn,verbose=0):
    """
    Since the db is considered final, we can add all sorts of indecies
    to make sure the retrieval time is as fast as possible.
    Indecies take up a little space, but they hurt performance only when
    we modify the data (which should not happen)
    This function commits its changes at the end
    
    Note: tutorial on MySQL (close enough to SQLite):
    http://www.databasejournal.com/features/mysql/article.php/10897_1382791_1/Optimizing-MySQL-Queries-and-Indexes.htm
    """
    c = conn.cursor()
    # index to search by (target) or (target,sims)
    q = "CREATE INDEX idx_target_sim ON similarity ('target','similar')"
    if verbose > 0: print q
    c.execute(q)
    # index to search by (sims) or (sims,target)
    q = "CREATE INDEX idx_sim_target ON similarity ('similar','target')"
    if verbose > 0: print q
    c.execute(q)
    # done (artists table as an implicit index as artist_id is the
    # primary key)
    conn.commit()


def die_with_usage():
    """ HELP MENU """
    print 'Command to create the artist_terms SQLite database'
    print 'to launch (it might take a while!):'
    print '   python create_artist_terms_db.py <MillionSong dir> <artistlist> <artist_similarity.db>'
    print 'PARAMS'
    print '  MillionSong dir        - directory containing .h5 song files in sub dirs'
    print '  artist list            - list in form: artistid<SEP>artist_mbid<SEP>track_id<SEP>...'
    print '  artist_similarity.db   - filename for the database'
    print ''
    print 'for artist list, check:       /Tasks_Demos/NamesAnalysis/list_all_artists.py'
    print '          or (faster!):       /Tasks_Demos/SQLite/list_all_artists_from_db.py'
    sys.exit(0)

    
if __name__ == '__main__':

    # help menu
    if len(sys.argv) < 4:
        die_with_usage()

    # import HDF5 stuff
    # yes, it is worth of a WTF like this last one:
    # http://thedailywtf.com/Articles/CompareObjectAsIAlertDocumentOrNullIfNotCastable-and-More.aspx
    # but I plan to buy some bad code offsets anyway
    # http://codeoffsets.com/
    pythonsrc = os.path.join(sys.argv[0],'../../../PythonSrc')
    pythonsrc = os.path.abspath( pythonsrc )
    sys.path.append( pythonsrc )
    from hdf5_getters import *

    # params
    maindir = sys.argv[1]
    artistfile = sys.argv[2]
    dbfile = os.path.abspath(sys.argv[3])

    # check if file exists!
    if os.path.exists(dbfile):
        print dbfile,'already exists! delete or provide a new name'
        sys.exit(0)

    # start time
    t1 = time.time()

     # get all track ids per artist
    trackids = []
    artistids = []
    f = open(artistfile,'r')
    for line in f.xreadlines():
        if line == '' or line.strip() == '':
            continue
        artistids.append( line.split('<SEP>')[0] )
        trackids.append( line.split('<SEP>')[2] )
    f.close()
    print 'found',len(trackids),'artists in file:',artistfile

    # create database
    create_db(dbfile,artistids)

    # open connection
    conn = sqlite3.connect(dbfile)
    
    # iterate over files
    cnt_files = 0
    for trackid in trackids:
        f = os.path.join(maindir,path_from_trackid(trackid))
        fill_from_h5(conn,f)
        cnt_files += 1
        if cnt_files % 500 == 0:
            conn.commit()
    conn.commit()

    # create indices
    add_indices_to_db(conn,verbose=0)

    # close connection
    conn.close()

    # done
    t2 = time.time()
    stimelength = str(datetime.timedelta(seconds=t2-t1))
    print 'All done (including indices) in',stimelength

########NEW FILE########
__FILENAME__ = create_artist_terms_db
"""
Thierry Bertin-Mahieux (2010) Columbia University
tb2332@columbia.edu

This code creates an SQLite database with 5 tables.
One per unique artist, one per unique Echo Nest term,
one per unique musicbrainz tag, then one table
to link artists and terms, and one table to link
artists and mbtags.

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.


Copyright 2010, Thierry Bertin-Mahieux

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""


import os
import sys
import glob
import time
import datetime
import numpy as np
try:
    import sqlite3
except ImportError:
    print 'you need sqlite3 installed to use this program'
    sys.exit(0)




def path_from_trackid(trackid):
    """
    Creates the path from a given trackid
    """
    s = os.path.join(trackid[2],trackid[3])
    s = os.path.join(s,trackid[4])
    s = os.path.join(s,trackid)
    s = s.upper() + '.h5'
    return s


def encode_string(s):
    """
    Simple utility function to make sure a string is proper
    to be used in a SQLite query
    (different than posgtresql, no N to specify unicode)
    EXAMPLE:
      That's my boy! -> 'That''s my boy!'
    """
    return "'"+s.replace("'","''")+"'"


def create_db(filename,artistlist,termlist,mbtaglist):
    """
    Create a SQLite database with 5 tables
    table1: artists
            contains one column, artist_id
    table2: terms
            contains one column, term (tags)
    table3: artist_term
            contains two columns, artist_id and term
    table4: mbtags
            contains one column, mbtag (musicbrainz tags)
    table5: artist_mbtag
            contains two columns, artist_id and mbtag
    INPUT
    - artistlist    list of all artist Echo Nest IDs
    - term list     list of all terms (Echo Nest tags)
    - mbtag list    list of all music brainz tags
    """
    # creates file
    conn = sqlite3.connect(filename)
    c = conn.cursor()
    # create table 1
    q = "CREATE TABLE artists (artist_id text PRIMARY KEY)"
    c.execute(q)
    conn.commit()
    artistlist = np.sort(artistlist)
    for aid in artistlist:
        q = "INSERT INTO artists VALUES ("
        q += encode_string(aid) + ")"
        c.execute(q)
    conn.commit()
    # create table 2, fill with tags
    q = "CREATE TABLE terms (term text PRIMARY KEY)"
    c.execute(q)
    conn.commit()
    termlist = np.sort(termlist)
    for t in termlist: 
        q = "INSERT INTO terms VALUES ("
        q += encode_string(t) + ")"
        c.execute(q)
    conn.commit()
    # create table 3
    q = "CREATE TABLE artist_term (artist_id text, term text, "
    q += "FOREIGN KEY(artist_id) REFERENCES artists(artist_id), "
    q += "FOREIGN KEY(term) REFERENCES terms(term) )"
    c.execute(q)
    conn.commit()
    # create table 4
    q = "CREATE TABLE mbtags (mbtag text PRIMARY KEY)"
    c.execute(q)
    conn.commit()
    mbtaglist = np.sort(mbtaglist)
    for t in mbtaglist: 
        q = "INSERT INTO mbtags VALUES ("
        q += encode_string(t) + ")"
        c.execute(q)
    conn.commit()
    # create table 5
    q = "CREATE TABLE artist_mbtag (artist_id text, mbtag text, "
    q += "FOREIGN KEY(artist_id) REFERENCES artists(artist_id), "
    q += "FOREIGN KEY(mbtag) REFERENCES mbtags(mbtag) )"
    c.execute(q)
    conn.commit()
    # close
    c.close()
    conn.close()


def fill_from_h5(conn,h5path):
    """
    Add information rgarding the artist in that one h5 song file.
    Doesn't commit, doesn't close conn at the end!
    This h5 file must be for a new artist, we can't have twice the
    same artist entered in the database!

    The info is added to tables: artist_term, artist_mbtag
    as many row as term/mbtag are added
    """
    # get info from h5 file
    h5 = open_h5_file_read(h5path)
    artist_id = get_artist_id(h5)
    terms = get_artist_terms(h5)
    mbtags = get_artist_mbtags(h5)
    h5.close()
    # get cursor
    c = conn.cursor()
    # add as many rows as terms in artist_term table
    for t in terms:
        q = "INSERT INTO artist_term VALUES ("
        q += encode_string(artist_id) + "," + encode_string(t)
        q += ")"
        c.execute(q)
    # add as many rows as mtgs in artist_mbtag table
    for t in mbtags:
        q = "INSERT INTO artist_mbtag VALUES ("
        q += encode_string(artist_id) + "," + encode_string(t)
        q += ")"
        c.execute(q)
    # done
    c.close()

def add_indices_to_db(conn,verbose=0):
    """
    Since the db is considered final, we can add all sorts of indecies
    to make sure the retrieval time is as fast as possible.
    Indecies take up a little space, but they hurt performance only when
    we modify the data (which should not happen)
    This function commits its changes at the end
    
    Note: tutorial on MySQL (close enough to SQLite):
    http://www.databasejournal.com/features/mysql/article.php/10897_1382791_1/Optimizing-MySQL-Queries-and-Indexes.htm
    """
    c = conn.cursor()
    # index to search by (artist_id) or (artist_id,term) on artist_term table
    # samething for      (artist_id)    (artist_id,mbtag)   artist_mbtag
    q = "CREATE INDEX idx_artist_id_term ON artist_term ('artist_id','term')"
    if verbose > 0: print q
    c.execute(q)
    q = "CREATE INDEX idx_artist_id_mbtag ON artist_mbtag ('artist_id','mbtag')"
    if verbose > 0: print q
    c.execute(q)
    # index to search by (term) or (term,artist_id) on artist_terms table
    # might be redundant, we probably just need an index on term since the first
    # one can do the join search
    # samehting for (mbtag,artist_id)
    q = "CREATE INDEX idx_term_artist_id ON artist_term ('term','artist_id')"
    if verbose > 0: print q
    c.execute(q)
    q = "CREATE INDEX idx_mbtag_artist_id ON artist_mbtag ('mbtag','artist_id')"
    if verbose > 0: print q
    c.execute(q)
    # we're done, we don't need to add keys to artists and tersm
    # since they have only one column that is a PRIMARY KEY, they have
    # an implicit index
    conn.commit()
    

def die_with_usage():
    """ HELP MENU """
    print 'Command to create the artist_terms SQLite database'
    print 'to launch (it might take a while!):'
    print '   python create_artist_terms_db.py <MillionSong dir> <termlist> <mbtaglist> <artistlist> <artist_term.db>'
    print 'PARAMS'
    print '  MillionSong dir   - directory containing .h5 song files in sub dirs'
    print '  termlist          - list of all possible terms (Echo Nest tags)'
    print '  mbtaglist         - list of all possible musicbrainz tags'
    print '  artist list       - list in form: artistid<SEP>artist_mbid<SEP>track_id<SEP>...'
    print '  artist_terms.db   - filename for the database'
    print ''
    print 'for artist list, check:       /Tasks_Demos/NamesAnalysis/list_all_artists.py'
    print '          or (faster!):       /Tasks_Demos/SQLite/list_all_artists_from_db.py'
    print 'for termlist and mbtaglist:   /Tasks_Demos/Tagging/get_unique_terms.py'
    sys.exit(0)



if __name__ == '__main__':

    # help menu
    if len(sys.argv) < 6:
        die_with_usage()

    # import HDF5 stuff
    # yes, it is worth of a WTF like this last one:
    # http://thedailywtf.com/Articles/CompareObjectAsIAlertDocumentOrNullIfNotCastable-and-More.aspx
    # but I plan to buy some bad code offsets anyway
    # http://codeoffsets.com/
    pythonsrc = os.path.join(sys.argv[0],'../../../PythonSrc')
    pythonsrc = os.path.abspath( pythonsrc )
    sys.path.append( pythonsrc )
    from hdf5_getters import *

    # params
    maindir = sys.argv[1]
    termfile = sys.argv[2]
    mbtagfile = sys.argv[3]
    artistfile = sys.argv[4]
    dbfile = os.path.abspath(sys.argv[5])

   # check if file exists!
    if os.path.exists(dbfile):
        print dbfile,'already exists! delete or provide a new name'
        sys.exit(0) 

    # start time
    t1 = time.time()

    # get all terms
    allterms = []
    f = open(termfile,'r')
    for line in f.xreadlines():
        if line == '' or line.strip() == '':
            continue
        allterms.append(line.strip())
    f.close()
    print 'found',len(allterms),'terms in file:',termfile

    # get all mbtags
    allmbtags = []
    f = open(mbtagfile,'r')
    for line in f.xreadlines():
        if line == '' or line.strip() == '':
            continue
        allmbtags.append(line.strip())
    f.close()
    print 'found',len(allmbtags),'mbtags in file:',mbtagfile

    # get all track ids per artist
    trackids = []
    artistids = []
    f = open(artistfile,'r')
    for line in f.xreadlines():
        if line == '' or line.strip() == '':
            continue
        artistids.append( line.split('<SEP>')[0] )
        trackids.append( line.split('<SEP>')[2] )
    f.close()
    print 'found',len(trackids),'artists in file:',artistfile

    # create database
    create_db(dbfile,artistids,allterms,allmbtags)
    t2 = time.time()
    stimelength = str(datetime.timedelta(seconds=t2-t1))
    print 'tables created after', stimelength

    # open connection
    conn = sqlite3.connect(dbfile)

    # iterate over files
    cnt_files = 0
    for trackid in trackids:
        f = os.path.join(maindir,path_from_trackid(trackid))
        fill_from_h5(conn,f)
        cnt_files += 1
        if cnt_files % 500 == 0:
            conn.commit()
    conn.commit()

    # time update
    t3 = time.time()
    stimelength = str(datetime.timedelta(seconds=t3-t1))
    print 'Looked at',cnt_files,'files, done in',stimelength

    # creates indices
    add_indices_to_db(conn,verbose=0)

    # close connection
    conn.close()

    # done
    t4 = time.time()
    stimelength = str(datetime.timedelta(seconds=t4-t1))
    print 'All done (including indices) in',stimelength

    

########NEW FILE########
__FILENAME__ = create_track_metadata_db
"""
Thierry Bertin-Mahieux (2010) Columbia University
tb2332@columbia.edu

This code creates an SQLite dataset that contains one row
per track and has all the regular metadata.

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.


Copyright 2010, Thierry Bertin-Mahieux

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import glob
import time
import datetime
import numpy as np
try:
    import sqlite3
except ImportError:
    print 'you need sqlite3 installed to use this program'
    sys.exit(0)


def encode_string(s):
    """
    Simple utility function to make sure a string is proper
    to be used in a SQLite query
    (different than posgtresql, no N to specify unicode)
    EXAMPLE:
      That's my boy! -> 'That''s my boy!'
    """
    return "'" + s.replace("'", "''") + "'"


def create_db(filename):
    """
    Creates the file and an empty table.
    """
    # creates file
    conn = sqlite3.connect(filename)
    # add stuff
    c = conn.cursor()
    q = 'CREATE TABLE songs (track_id text PRIMARY KEY, '
    q += 'title text, song_id text, '
    q += 'release text, artist_id text, artist_mbid text, artist_name text, '
    q += 'duration real, artist_familiarity real, '
    q += 'artist_hotttnesss real, year int, '
    q += 'track_7digitalid int, shs_perf int, shs_work int)'
    c.execute(q)
    # commit and close
    conn.commit()
    c.close()
    conn.close()


def fill_from_h5(conn, h5path, verbose=0):
    """
    Add a row with he information from this .h5 file
    Doesn't commit, doesn't close conn at the end!
    """
    h5 = open_h5_file_read(h5path)
    c = conn.cursor()
    # build query
    q = 'INSERT INTO songs VALUES ('
    track_id = get_track_id(h5)
    q += encode_string(track_id)
    title = get_title(h5)
    q += ', ' + encode_string(title)
    song_id = get_song_id(h5)
    q += ', ' + encode_string(song_id)
    release = get_release(h5)
    q += ', ' + encode_string(release)
    artist_id = get_artist_id(h5)
    q += ', ' + encode_string(artist_id)
    artist_mbid = get_artist_mbid(h5)
    q += ', ' + encode_string(artist_mbid)
    artist_name = get_artist_name(h5)
    q += ', ' + encode_string(artist_name)
    duration = get_duration(h5)
    q += ", " + str(duration) if not np.isnan(duration) else ",-1"
    familiarity = get_artist_familiarity(h5)
    q += ", " + str(familiarity) if not np.isnan(familiarity) else ",-1"
    hotttnesss = get_artist_hotttnesss(h5)
    q += ", " + str(hotttnesss) if not np.isnan(hotttnesss) else ",-1"
    year = get_year(h5)
    q += ", " + str(year)
    track_7digitalid = get_track_7digitalid(h5)
    q += ", " + str(track_7digitalid)
    # add empty fields for shs perf than work
    q += ", -1, 0"
    # query done, close h5, commit
    h5.close()
    q += ')'
    if verbose > 0:
        print q
    c.execute(q)
    #conn.commit() # we don't take care of the commit!
    c.close()


def add_indices_to_db(conn, verbose=0):
    """
    Since the db is considered final, we can add all sorts of indecies
    to make sure the retrieval time is as fast as possible.
    Indecies take up a little space, but they hurt performance only when
    we modify the data (which should not happen)
    This function commits its changes at the end

    You might want to add your own indices if you do weird query, e.g. on title
    and artist musicbrainz ID.
    Indices should be on the columns of the WHERE of your search, the goal
    is to quickly find the few rows that match the query. The index does not
    care of the field (column) you actually want, finding the row is the
    important step.
    track_id is implicitely indexed as it is the PRIMARY KEY of the table.
    Note: tutorial on MySQL (close enough to SQLite):
    http://www.databasejournal.com/features/mysql/article.php/10897_1382791_1/
                                   Optimizing-MySQL-Queries-and-Indexes.htm
    """
    c = conn.cursor()
    # index to search by (artist_id) or by (artist_id,release)
    q = "CREATE INDEX idx_artist_id ON songs ('artist_id','release')"
    if verbose > 0:
        print q
    c.execute(q)
    # index to search by (artist_mbid) or by (artist_mbid,release)
    q = "CREATE INDEX idx_artist_mbid ON songs ('artist_mbid','release')"
    if verbose > 0:
        print q
    c.execute(q)
    # index to search by (artist_familiarity)
    # or by (artist_familiarity,artist_hotttnesss)
    q = "CREATE INDEX idx_familiarity ON songs "
    q += "('artist_familiarity','artist_hotttnesss')"
    if verbose > 0:
        print q
    c.execute(q)
    # index to search by (artist_hotttnesss)
    # or by (artist_hotttnesss,artist_familiarity)
    q = "CREATE INDEX idx_hotttnesss ON songs "
    q += "('artist_hotttnesss','artist_familiarity')"
    if verbose > 0:
        print q
    c.execute(q)
    # index to search by (artist_name)
    # or by (artist_name,title) or by (artist_name,title,release)
    q = "CREATE INDEX idx_artist_name ON songs "
    q += "('artist_name','title','release')"
    if verbose > 0:
        print q
    c.execute(q)
    # index to search by (title)
    # or by (title,artist_name) or by (title,artist_name,release)
    q = "CREATE INDEX idx_title ON songs ('title','artist_name','release')"
    if verbose > 0:
        print q
    c.execute(q)
    # index to search by (release)
    # or by (release,artist_name) or by (release,artist_name,title)
    q = "CREATE INDEX idx_release ON songs ('release','artist_name','title')"
    if verbose > 0:
        print q
    # index to search by (duration)
    # or by (duration,artist_id)
    q = "CREATE INDEX idx_duration ON songs ('duration','artist_id')"
    if verbose > 0:
        print q
    c.execute(q)
    # index to search by (year)
    # or by (year,artist_id) or by (year,artist_id,title)
    q = "CREATE INDEX idx_year ON songs ('year','artist_id','title')"
    if verbose > 0:
        print q
    c.execute(q)
    # index to search by (year) or by (year,artist_name)
    q = "CREATE INDEX idx_year2 ON songs ('year','artist_name')"
    if verbose > 0:
        print q
    c.execute(q)
    # index to search by (shs_work)
    q = "CREATE INDEX idx_shs_work ON songs ('shs_work')"
    if verbose > 0:
        print q
    c.execute(q)
    # index to search by (shs_perf)
    q = "CREATE INDEX idx_shs_perf ON songs ('shs_perf')"
    if verbose > 0:
        print q
    c.execute(q)
    # done, commit
    conn.commit()


def die_with_usage():
    """ HELP MENU """
    print 'Command to create the track_metadata SQLite database'
    print 'to launch (it might take a while!):'
    print '   python create_track_metadata_db.py [FLAGS] <MSD dir> <tmdb>'
    print 'PARAMS'
    print '   MSD dir   - directory containing .h5 song files in sub dirs'
    print '        tmdb - filename for the database (track_metadata.db)'
    print 'FLAGS'
    print '  -shsdata f  - file containing the SHS dataset'
    print '                (you can simply concatenate train and test)'
    print '  -verbose    - print every query'
    sys.exit(0)


if __name__ == '__main__':

    # help menu
    if len(sys.argv) < 3:
        die_with_usage()

    # import HDF5 stuff
    # yes, it is worth of a WTF like this last one:
    # http://thedailywtf.com/
    #   Articles/CompareObjectAsIAlertDocumentOrNullIfNotCastable-and-More.aspx
    # but I plan to buy some bad code offsets anyway
    # http://codeoffsets.com/
    pythonsrc = os.path.join(sys.argv[0], '../../../PythonSrc')
    pythonsrc = os.path.abspath(pythonsrc)
    sys.path.append(pythonsrc)
    from hdf5_getters import *

    verbose = 0
    shsdataset = ''
    while True:
        if sys.argv[1] == '-verbose':
            verbose = 1
        elif sys.argv[1] == '-shsdata':
            shsdataset = sys.argv[2]
            sys.argv.pop(1)
        else:
            break
        sys.argv.pop(1)

    # read params
    maindir = os.path.abspath(sys.argv[1])
    dbfile = os.path.abspath(sys.argv[2])

    # sanity checks
    if not os.path.isdir(maindir):
        print 'ERROR: %s is not a directory.' % maindir
    if os.path.exists(dbfile):
        print 'ERROR: %s already exists! delete or provide a new name' % dbfile
        sys.exit(0)
    if shsdataset != '' and not os.path.isfile(shsdataset):
        print 'ERROR %s does not exist.' % shsdataset
        sys.exit(0)

    # start time
    t1 = time.time()

    # create dataset
    create_db(dbfile)

    # open connection
    conn = sqlite3.connect(dbfile)

    # iterate HDF5 files
    cnt_files = 0
    for root, dirs, files in os.walk(maindir):
        files = glob.glob(os.path.join(root, '*.h5'))
        for f in files:
            fill_from_h5(conn, f, verbose=verbose)
            cnt_files += 1
            if cnt_files % 200 == 0:
                conn.commit() # we commit only every 200 files!
    conn.commit()
    t2 = time.time()
    stimelength = str(datetime.timedelta(seconds=t2 - t1))
    print 'added the content of', cnt_files, 'files to database:', dbfile
    print 'it took:', stimelength

    # add SHS data
    if shsdataset != '':
        print 'We add SHS data from file: %s' % shsdataset
        # iterate over SHS file
        shs = open(shsdataset, 'r')
        for line in shs:
            if line == '' or line.strip() == '':
                continue
            if line[0] == '#':
                continue
            # work
            if line[0] == '%':
                works = map(lambda w: int(w),
                            line[1:].split(' ')[0].split(',')[:-1])
                work = min(works)
                continue
            # regular line
            tid, aid, perf = line.strip().split('<SEP>')
            q = "UPDATE songs SET shs_perf=" + perf + ", shs_work=" + str(work)
            q += " WHERE track_id='" + tid + "'"
            if verbose > 0:
                print q
            conn.execute(q)
        # iteration done
        shs.close()
        conn.commit()

    # add indices
    c = conn.cursor()
    res = c.execute('SELECT Count(*) FROM songs')
    nrows_before = res.fetchall()[0][0]
    add_indices_to_db(conn, verbose=verbose)
    res = c.execute('SELECT Count(*) FROM songs')
    nrows_after = res.fetchall()[0][0]
    c.close()
    # sanity check
    assert nrows_before == nrows_after, 'Lost rows during indexing?'
    if nrows_before != 1000000:
        print '*********************************************************'
        print 'We got', nrows_before, 'rows.'
        print 'This is not the full MillionSongDataset! just checking...'
        print '*********************************************************'

    # close connection
    conn.close()

    # end time
    t3 = time.time()

    # DONE
    print 'done! (indices included) database:', dbfile
    stimelength = str(datetime.timedelta(seconds=t3 - t1))
    print 'execution time:', stimelength

########NEW FILE########
__FILENAME__ = demo_artist_similarity
"""
Thierry Bertin-Mahieux (2011) Columbia University
tb2332@columbia.edu

This code demo the use of the artist_similarity.db
To create the db, see create_artist_similarity_db.py
You should be able to download the db from the Million
Song Dataset website.
To view a more basic demo on SQLite, start with
demo_artist_term.py

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.

Copyright 2011, Thierry Bertin-Mahieux

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import glob
import time
import datetime
import numpy as np
try:
    import sqlite3
except ImportError:
    print 'you need sqlite3 installed to use this program'
    sys.exit(0)


def encode_string(s):
    """
    Simple utility function to make sure a string is proper
    to be used in a SQLite query
    (different than posgtresql, no N to specify unicode)
    EXAMPLE:
      That's my boy! -> 'That''s my boy!'
    """
    return "'"+s.replace("'","''")+"'"


def die_with_usage():
    """ HELP MENU """
    print 'demo_artist_similarity.py'
    print '  by T. Bertin-Mahieux (2011) Columbia University'
    print '     tb2332@columbia.edu'
    print 'This codes gives examples on how to query the database artist_similarity.db'
    print 'To first create this database, see: create_artist_similarity_db.py'
    print 'Note that you should first check: demo_track_metadata.py if you are not'
    print 'familiar with SQLite.'
    print 'usage:'
    print '   python demo_artist_similarity.py <database path>'
    sys.exit(0)


if __name__ == '__main__':

    # help menu
    if len(sys.argv) < 2:
        die_with_usage()

    # params
    dbfile = sys.argv[1]

    # connect to the SQLite database
    conn = sqlite3.connect(dbfile)

    # from that connection, get a cursor to do queries
    # NOTE: we could query directly from the connection object
    c = conn.cursor()

    print '*************** GENERAL SQLITE DEMO ***************************'

    # list all tables in that dataset
    # note that sqlite does the actual job when we call fetchall() or fetchone()
    q = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    res = c.execute(q)
    print "* tables contained in that SQLite file/database (there should be 3):"
    print res.fetchall()

    # list all indices
    q = "SELECT name FROM sqlite_master WHERE type='index' ORDER BY name"
    res = c.execute(q)
    print '* indices in the database to make reads faster:'
    print res.fetchall()

    print '*************** ARTISTS TABLE DEMO ****************************'

    # list all artist ID
    q = "SELECT artist_id FROM artists"
    res = c.execute(q)
    print "* number of artist Echo Nest ID in 'artists' table:"
    print len(res.fetchall())

    print '*************** ARTIST SIMILARITY DEMO ************************'

    # get a random similarity relationship
    q = "SELECT target,similar FROM similarity LIMIT 1"
    res = c.execute(q)
    a,s = res.fetchone()
    print '* one random similarity relationship (A->B means B similar to A):'
    print a,'->',s

    # count number of similar artist to a in previous call
    q = "SELECT Count(similar) FROM similarity WHERE target="+encode_string(a)
    res = c.execute(q)
    print '* artist',a,'has that many similar artists in the dataset:'
    print res.fetchone()[0]

    # count number of artist s (c queries up) is similar to
    q = "SELECT Count(target) FROM similarity WHERE similar="+encode_string(s)
    res = c.execute(q)
    print '* artist',s,'is similar to that many artists in the dataset:'
    print res.fetchone()[0]

    # DONE
    # close cursor and connection
    # (if for some reason you added stuff to the db or alter
    #  a table, you need to also do a conn.commit())
    c.close()
    conn.close()

    








########NEW FILE########
__FILENAME__ = demo_artist_term
"""
Thierry Bertin-Mahieux (2010) Columbia University
tb2332@columbia.edu

This code demo the use of the artist_term.db
To create the db, see create_artist_term_db.py
To view a more basic demo on SQLite, start with
demo_artist_term.py

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.

Copyright 2010, Thierry Bertin-Mahieux

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import glob
import time
import datetime
import numpy as np
try:
    import sqlite3
except ImportError:
    print 'you need sqlite3 installed to use this program'
    sys.exit(0)


def encode_string(s):
    """
    Simple utility function to make sure a string is proper
    to be used in a SQLite query
    (different than posgtresql, no N to specify unicode)
    EXAMPLE:
      That's my boy! -> 'That''s my boy!'
    """
    return "'"+s.replace("'","''")+"'"


def die_with_usage():
    """ HELP MENU """
    print 'demo_artist_term.py'
    print '  by T. Bertin-Mahieux (2010) Columbia University'
    print '     tb2332@columbia.edu'
    print 'This codes gives examples on how to query the database artist_term.db'
    print 'To first create this database, see: create_artist_term_db.py'
    print 'Note that you should first check: demo_track_metadata.py if you are not'
    print 'familiar with SQLite.'
    print 'usage:'
    print '   python demo_artist_term.py <database path>'
    sys.exit(0)


if __name__ == '__main__':

    # help menu
    if len(sys.argv) < 2:
        die_with_usage()

    # params
    dbfile = sys.argv[1]

    # connect to the SQLite database
    conn = sqlite3.connect(dbfile)

    # from that connection, get a cursor to do queries
    c = conn.cursor()

    # SCHEMA OVERVIEW
    # we got 3 tables
    # table1: name=artists      #cols=1   (artist_id text)
    #    One row per artists, no duplicates, usually alphabetical order
    # table2: name=terms        #cols=1   (term text)
    #    One row per term, no duplicates, usually alphabetical order
    # table3: name=artist_term  #cols=2   (artist_id text, term text)
    #    One row per pair artist_id/term, no duplicate pairs
    #    Entries in table3 are constrained by table1 and table2,
    # e.g. an artist_id must exist in table1 before it is used in table3.
    # NOT ALL ARTISTS HAVE TERMS. They will still all be in table1, but
    # some artists are not in table3 at all.

    print '*************** GENERAL SQLITE DEMO ***************************'

    # list all tables in that dataset
    # note that sqlite does the actual job when we call fetchall() or fetchone()
    q = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    res = c.execute(q)
    print "* tables contained in that SQLite file/database (there should be 3):"
    print res.fetchall()

    # list all indices
    q = "SELECT name FROM sqlite_master WHERE type='index' ORDER BY name"
    res = c.execute(q)
    print '* indices in the database to make reads faster:'
    print res.fetchall()


    print '*************** ARTISTS TABLE DEMO ****************************'

    # list all artists
    q = "SELECT * FROM artists"
    res = c.execute(q)
    print '* list all known artists in the database (display first 3):'
    print res.fetchall()[:3]

    # list all artists that id starts with ARB
    q = "SELECT artist_id FROM artists WHERE SUBSTR(artist_id,1,3)='ARB' LIMIT 2"
    res = c.execute(q)
    print '* list artists whose ID starts with ARB (we ask for 2 of them):'
    print res.fetchall()

    # count all artists
    q = "SELECT COUNT(artist_id) FROM artists"
    res = c.execute(q)
    print '* count the number of artists (with or without tags):'
    print res.fetchone()
    

    print '*************** TERMS TABLE DEMO ******************************'

    # list all terms (=tags)
    q = "SELECT * FROM terms"
    res = c.execute(q)
    print '* list all known terms in the database (display first 3):'
    print res.fetchall()[:3]

    # list all terms that start with 'indie'
    q = "SELECT term FROM terms WHERE SUBSTR(term,1,5)='indie' LIMIT 3"
    res = c.execute(q)
    print "* list terms that start with 'indie' (we ask for 3 of them):"
    print res.fetchall()

    # check if a tag is inthe dataset
    q1 = "SELECT term FROM terms WHERE term='rock' LIMIT 1"
    q2 = "SELECT term FROM terms WHERE term='abc123xyz'"
    res = c.execute(q1)
    res1_str = str(res.fetchone())
    res = c.execute(q2)
    res2_str = str(res.fetchone())
    print '* we check if two tags are in the database, (the first one is):'
    print 'rock:',res1_str,', abc123xyz:',res2_str

    # similar for mtags, list all mbtags
    q = "SELECT * FROM mbtags"
    res = c.execute(q)
    print '* btags work the same as terms, e.g. list all known mbtags (display first 3):'
    print res.fetchall()[:3]

    # get one badly encoded, fix it...
    # is it a problem only when we write to file???
    # we want to show the usage of t.encode('utf-8')  with t a term


    print '*************** ARTIST / TERM TABLE DEMO **********************'

    # note that the Beatles artist ID is: AR6XZ861187FB4CECD

    # get all tags from the Beatles
    q = "SELECT term FROM artist_term WHERE artist_id='AR6XZ861187FB4CECD'"
    res = c.execute(q)
    print "* we get all tags applied to the Beatles (we know their artist ID), we show 4:"
    print res.fetchall()[:4]

    # count number of tags applied to The Beatles
    q = "SELECT COUNT(term) FROM artist_term WHERE artist_id='AR6XZ861187FB4CECD'"
    res = c.execute(q)
    print "* we count the number of unique tags applied to The Beatles:"
    print res.fetchone()

    # get artist IDs that ahve been tagged with 'jazz'
    # note the encode_string function, that mostly doubles the ' sign
    q = "SELECT artist_id FROM artist_term WHERE term="+encode_string('jazz')
    q += " ORDER BY RANDOM() LIMIT 2"
    res = c.execute(q)
    print "* we get artists tagged with 'jazz', we display 2 at random:"
    print res.fetchall()

    # count number of artists tagged with 'rock'
    q = "SELECT COUNT(artist_id) FROM artist_term WHERE term="+encode_string('rock')
    res = c.execute(q)
    print "* we count the number of unique artists that got term 'rock':"
    print res.fetchone()

    # count number of artists mb tagged with 'rock'
    q = "SELECT COUNT(artist_id) FROM artist_mbtag WHERE mbtag="+encode_string('rock')
    res = c.execute(q)
    print "* samething with musicbrainz tag 'rock':"
    print res.fetchone()

    # get artists that have term 'rock' but not mbtag 'rock'
    q = "SELECT artist_id FROM artist_term WHERE term="+encode_string('rock')
    q += " EXCEPT SELECT artist_id FROM artist_mbtag WHERE mbtag="+encode_string('rock')
    q += " LIMIT 1"
    res = c.execute(q)
    print "* one artist that has term 'rock' but not mbtag 'rock':"
    print res.fetchone()

    # get artists that have no terms
    # simple with the EXCEPT keyword
    # other cool keywords: UNION, UNION ALL, INTERSECT
    q = "SELECT artist_id FROM artists EXCEPT SELECT artist_id FROM artist_term LIMIT 1"
    res = c.execute(q)
    artist_notag = res.fetchone()
    print '* we show an artist with no terms:'
    if artist_notag is None:
        # debug, make sure all artists have at least one tag, can be slow
        q = "SELECT * FROM artists"
        res = c.execute(q)
        allartists = map(lambda x: x[0], res.fetchall())
        for art in allartists:
            q = "SELECT COUNT(term) FROM artist_term WHERE artist_id='"+art+"'"
            res = c.execute(q)
            assert res.fetchone()[0] > 0
        print '(found no artist with no terms, we double-checked)'
    else:
        print artist_notag
    
    # DONE
    # close the cursor and the connection
    # (if for some reason you added stuff to the db or alter
    #  a table, you need to also do a conn.commit())
    c.close()
    conn.close()

########NEW FILE########
__FILENAME__ = demo_track_metadata
"""
Thierry Bertin-Mahieux (2010) Columbia University
tb2332@columbia.edu

This code demo the use of the track_metadata.db
To create the db, see create_track_metadata_db.py

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.

Copyright 2010, Thierry Bertin-Mahieux

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import glob
import time
import datetime
import numpy as np
try:
    import sqlite3
except ImportError:
    print 'you need sqlite3 installed to use this program'
    sys.exit(0)



def encode_string(s):
    """
    Simple utility function to make sure a string is proper
    to be used in a SQLite query
    (different than posgtresql, no N to specify unicode)
    EXAMPLE:
      That's my boy! -> 'That''s my boy!'
    """
    return "'"+s.replace("'","''")+"'"


def die_with_usage():
    """ HELP MENU """
    print 'demo_track_metadata.py'
    print '  by T. Bertin-Mahieux (2010) Columbia University'
    print '     tb2332@columbia.edu'
    print 'This codes gives examples on how to query the database track_metadata.db'
    print 'To first create this database, see: create_track_metadata_db.py'
    print 'usage:'
    print '   python demo_track_metadata.py <database path>'
    sys.exit(0)


if __name__ == '__main__':

    # help menu
    if len(sys.argv) < 2:
        die_with_usage()

    # params
    dbfile = sys.argv[1]

    # connect to the SQLite database
    conn = sqlite3.connect(dbfile)

    # from that connection, get a cursor to do queries
    c = conn.cursor()

    # so there is no confusion, the table name is 'songs'
    TABLENAME = 'songs'

    print '*************** GENERAL SQLITE DEMO ***************************'

    # list all tables in that dataset
    # note that sqlite does the actual job when we call fetchall() or fetchone()
    q = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    res = c.execute(q)
    print "* tables contained in that SQLite file/database (should be only 'songs'):"
    print res.fetchall()

    # list all columns names from table 'songs'
    q = "SELECT sql FROM sqlite_master WHERE tbl_name = 'songs' AND type = 'table'"
    res = c.execute(q)
    print '* get info on columns names (original table creation command):'
    print res.fetchall()[0][0]

    # list all indices
    q = "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='songs' ORDER BY name"
    res = c.execute(q)
    print '* one of the index we added to the table to make things faster:'
    print res.fetchone()

    # find the PRIMARY KEY of a query
    # by default it's called ROWID, it would have been redefined if our primary key
    # was of type INTEGER
    q = "SELECT ROWID FROM songs WHERE artist_name='The Beatles'"
    res = c.execute(q)
    print '* get the primary key (row id) of one entry where the artist is The Beatles:'
    print res.fetchone()
    
    # find an entry with The Beatles as artist_name
    # returns all info (the full table row)
    q = "SELECT * FROM songs WHERE artist_name='The Beatles' LIMIT 1"
    res = c.execute(q)
    print '* get all we have about one track from The Beatles:'
    print res.fetchone()

    print '*************** DEMOS AROUND ARTIST_ID ************************'

    # query for all the artists Echo Nest ID
    # the column name is 'artist_id'
    # DISTINCT makes sure you get each ID returned only once
    q = "SELECT DISTINCT artist_id FROM " + TABLENAME
    res = c.execute(q)
    artists = res.fetchall() # does the actual job of searching the db
    print '* found',len(artists),'unique artist IDs, response looks like:'
    print artists[:3]

    # more cumbersome, get unique artist ID but with one track ID for each.
    # very usefull, it gives you a HDF5 file to query if you want more
    # information about this artist
    q = "SELECT artist_id,track_id FROM songs GROUP BY artist_id"
    res = c.execute(q)
    artist_track_pair = res.fetchone()
    print '* one unique artist with some track (chosen at random) associated with it:'
    print artist_track_pair

    # get artists having only one track in the database
    q = "SELECT artist_id,track_id FROM songs GROUP BY artist_id HAVING ( COUNT(artist_id) = 1 )"
    q += " ORDER BY RANDOM()"
    res = c.execute(q)
    artist_track_pair = res.fetchone()
    print '* one artist that has only one track in the dataset:'
    print artist_track_pair

    # get artists with no musicbrainz ID
    # of course, we want only once each artist
    # for demo purpose, we ask for only two at RANDOM
    q = "SELECT artist_id,artist_mbid FROM songs WHERE artist_mbid=''"
    q += " GROUP BY artist_id ORDER BY RANDOM() LIMIT 2"
    res = c.execute(q)
    print '* two random unique artists with no musicbrainz ID:'
    print res.fetchall()


    print '*************** DEMOS AROUND NAMES ****************************'

    # get all tracks by artist The Beatles
    # artist name must be exact!
    # the encode_string function simply deals with ' (by doubling them)
    # and add ' after and before the string.
    q = "SELECT track_id FROM songs WHERE artist_name="
    q += encode_string('The Beatles')
    res = c.execute(q)
    print "* two track id from 'The Beatles', found by looking up the artist by name:"
    print res.fetchall()[:2]

    # we find all release starting by letter 'T'
    # T != t, we're just looking at albums starting with capital T
    # here we use DISTINCT instead of GROUP BY artist_id
    # since its fine that we find twice the same artist, as long as it is not
    # the same (artist,release) pair
    q = "SELECT DISTINCT artist_name,release FROM songs WHERE SUBSTR(release,1,1)='T'"
    res = c.execute(q)
    print '* one unique artist/release pair where album starts with capital T:'
    print res.fetchone()


    print '*************** DEMOS AROUND FLOATS ***************************'

    # get all artists whose artist familiarity is > .8
    q = "SELECT DISTINCT artist_name, artist_familiarity FROM songs WHERE artist_familiarity>.8"
    res = c.execute(q)
    print '* one artist having familiaryt >0.8:'
    print res.fetchone()

    # get one artist with the highest artist_familiarity but no artist_hotttnesss
    # notice the alias af and ah, makes things more readable
    q = "SELECT DISTINCT artist_name, artist_familiarity as af, artist_hotttnesss as ah"
    q += " FROM songs WHERE ah<0 ORDER BY af"
    res = c.execute(q)
    print '* get the artist with the highest familiarity that has no computed hotttnesss:'
    print res.fetchone()

    # close the cursor and the connection
    # (if for some reason you added stuff to the db or alter
    #  a table, you need to also do a conn.commit())
    c.close()
    conn.close()


    

########NEW FILE########
__FILENAME__ = list_all_artists_from_db
"""
Thierry Bertin-Mahieux (2010) Columbia University
tb2332@columbia.edu

This code creates a text file with all artist ids,
same as /Tasks_Demos/Name_Analysis
but faster since we use the sqlite database: track_metadata.db
Of course, it takes time to create the dataset ;)

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.

Copyright 2010, Thierry Bertin-Mahieux

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import glob
import string
import time
import datetime
import numpy as np
try:
    import sqlite3
except ImportError:
    print 'you need sqlite3 installed to use this program'
    sys.exit(0)




def die_with_usage():
    """ HELP MENU """
    print 'list_all_artists_from_db.py'
    print '   by T. Bertin-Mahieux (2010) Columbia University'
    print 'mimic the program /Tasks_Demo/NamesAnalysis/list_all_artist.py'
    print 'but assumes the sqlite db track_metadata.py is available'
    print 'i.e. it takes a few second instead of a few hours!'
    print 'to download track_metadata.db, see Million Song website'
    print 'to recreate it, see create_track_metadata.py'
    print ''
    print 'usage:'
    print '   python list_all_artists_from_db.py track_metadata.db output.txt'
    print 'creates a file where each line is: (one line per artist)'
    print 'artist id<SEP>artist mbid<SEP>track id<SEP>artist name'
    sys.exit(0)



if __name__ == '__main__':

    # help menu
    if len(sys.argv) < 3:
        die_with_usage()

    # params
    dbfile = sys.argv[1]
    output = sys.argv[2]

    # sanity check
    if not os.path.isfile(dbfile):
        print 'ERROR: can not find database:',dbfile
        sys.exit(0)
    if os.path.exists(output):
        print 'ERROR: file',output,'exists, delete or provide a new name'
        sys.exit(0)

    # start time
    t1 = time.time()

    # connect to the db
    conn = sqlite3.connect(dbfile)
    c = conn.cursor()
    # get what we want
    q = 'SELECT artist_id,artist_mbid,track_id,artist_name FROM songs'
    q += ' GROUP BY artist_id  ORDER BY artist_id'
    res = c.execute(q)
    alldata = res.fetchall()
    # DEBUGGING
    q = 'SELECT DISTINCT artist_id FROM songs'
    res = c.execute(q)
    artists = res.fetchall()
    print 'found',len(artists),'distinct artists'
    assert len(alldata) == len(artists),'incoherent sizes'
    # close db connection
    c.close()
    conn.close()

    # write to file
    f = open(output,'w')
    for data in alldata:
        f.write(data[0]+'<SEP>'+data[1]+'<SEP>'+data[2]+'<SEP>')
        f.write( data[3].encode('utf-8') + '\n' )
    f.close()

    # done
    t2 = time.time()
    stimelength = str(datetime.timedelta(seconds=t2-t1))
    print 'file',output,'with',len(alldata),'artists created in',stimelength

########NEW FILE########
__FILENAME__ = list_all_tracks_from_db
"""
Thierry Bertin-Mahieux (2010) Columbia University
tb2332@columbia.edu

This code creates a text file with all track ID, song ID, artist name and
song name. Does it from the track_metadata.db
format is:
trackID<SEP>songID<SEP>artist name<SEP>song title

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.

Copyright 2010, Thierry Bertin-Mahieux

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""


import os
import sys
import glob
import string
import time
import datetime
import numpy as np
try:
    import sqlite3
except ImportError:
    print 'you need sqlite3 installed to use this program'
    sys.exit(0)


def die_with_usage():
    """ HELP MENU """
    print 'list_all_tracks_from_db.py'
    print '   by T. Bertin-Mahieux (2010) Columbia University'
    print 'Code to create a list of all tracks in the dataset as'
    print 'a text file. Assumes track_metadata.db already exists.'
    print "Format is (IDs are EchoNest's):"
    print 'trackID<SEP>songID<SEP>artist name<SEP>song title'
    print ' '
    print 'usage:'
    print '   python list_all_tracks_from_db.py <track_metadata.db> <output.txt>'
    print ''
    sys.exit(0)


if __name__ == '__main__':

    # help menu
    if len(sys.argv) < 3:
        die_with_usage()

    # params
    dbfile = sys.argv[1]
    output = sys.argv[2]

    # sanity check
    if not os.path.isfile(dbfile):
        print 'ERROR: can not find database:',dbfile
        sys.exit(0)
    if os.path.exists(output):
        print 'ERROR: file',output,'exists, delete or provide a new name'
        sys.exit(0)

    # start time
    t1 = time.time()

    # connect to the db
    conn = sqlite3.connect(dbfile)

    # get what we want
    q = 'SELECT track_id,song_id,artist_name,title FROM songs'
    res = conn.execute(q)
    alldata = res.fetchall() # takes time and memory!
    
    # close connection to db
    conn.close()

    # sanity check
    if len(alldata) != 1000000:
        print 'NOT A MILLION TRACKS FOUND!'

    # write to file
    f = open(output,'w')
    for data in alldata:
        f.write(data[0]+'<SEP>'+data[1]+'<SEP>')
        f.write( data[2].encode('utf-8') +'<SEP>')
        f.write( data[3].encode('utf-8') + '\n' )
    f.close()

    # done
    t2 = time.time()
    stimelength = str(datetime.timedelta(seconds=t2-t1))
    print 'file',output,'created in',stimelength

########NEW FILE########
__FILENAME__ = analyze_test_set
"""
Thierry Bertin-Mahieux (2010) Columbia University
tb2332@columbia.edu

Code to analyze the test set, and give a benchmark result
for automatic tagging based on no audio analysis.

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.


Copyright 2010, Thierry Bertin-Mahieux

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import glob
import time
import numpy as np
import sqlite3


def encode_string(s):
    """
    Simple utility function to make sure a string is proper
    to be used in a SQLite query
    (different than posgtresql, no N to specify unicode)
    EXAMPLE:
      That's my boy! -> 'That''s my boy!'
    """
    return "'"+s.replace("'","''")+"'"


def die_with_usage():
    """ HELP MENU """
    print 'analyze_test_set.py'
    print '    by T. Bertin-Mahieux (2011) Columbia University'
    print '       tb2332@columbia.edu'
    print ''
    print 'Code to analyze the test set, and give a benchmark result for'
    print 'automatic tagging based on tag stats (no audio analysis)'
    print ''
    print 'USAGE'
    print '   python analyze_test_set.py [FLAGS] <artist_test.txt> <track_metadata.db> <artist_term.db>'
    print 'PARAM'
    print '    artist_test.txt  - list of artists in the test set'
    print '  track_metadata.db  - SQLite database with metadata per track'
    print '     artist_term.db  - SQLite database with Echo Nest terms per artist'
    print 'FLAG'
    print '   -predictionlen n  - number of terms we use to tag every test artist.'
    print '                       interesting to find the best F-1 score'
    print '                       By default, we use the average number of top300 terms'
    print '                       of artists in train se, which is 19.'
    sys.exit(0)


if __name__ == '__main__':

    # help menu
    if len(sys.argv) < 4:
        die_with_usage()

    # flags
    forced_avgnterm = -1
    while True:
        if sys.argv[1] == '-predictionlen':
            forced_avgnterm = int(sys.argv[2])
            sys.argv.pop(1)
        else:
            break
        sys.argv.pop(1)

    # params
    artist_test_file = sys.argv[1]
    track_metadata_db_file = sys.argv[2]
    artist_term_db_file = sys.argv[3]

    # sanity check
    if not os.path.isfile(artist_test_file):
        print 'ERROR: file',artist_test_file,'does not exist.'
        sys.exit(0)
    if not os.path.isfile(track_metadata_db_file):
        print 'ERROR: file',track_metadata_db_file,'does not exist.'
        sys.exit(0)
    if not os.path.isfile(artist_term_db_file):
        print 'ERROR: file',artist_term_db_file,'does not exist.'
        sys.exit(0)

    # load artists
    test_artists = set()
    f = open(artist_test_file,'r')
    for line in f.xreadlines():
        if line == '' or line.strip() == '':
            continue
        test_artists.add(line.strip())
    f.close()
    print 'Found',len(test_artists),'unique test artists.'

    # open connections
    conn_tm = sqlite3.connect(track_metadata_db_file)
    conn_at = sqlite3.connect(artist_term_db_file)

    # get total number of artists
    q = "SELECT Count(artist_id) FROM artists"
    res = conn_at.execute(q)
    n_total_artists = res.fetchone()[0]
    print 'Found',n_total_artists,'artists total.'
    q = "SELECT DISTINCT artist_id FROM artist_term"
    res = conn_at.execute(q)
    n_artists_with_term = len(res.fetchall())
    print 'Found',n_artists_with_term,'artists with at least one term.'

    # count number of files/tracks in the test set
    # create tmp table with test artists in track_metadata connection
    q = "CREATE TEMP TABLE test_artists (artist_id TEXT PRIMARY KEY)"
    conn_tm.execute(q)
    conn_tm.commit()
    for artist in test_artists:
        q = "INSERT INTO test_artists VALUES('%s')" % artist
        conn_tm.execute(q)
    conn_tm.commit()
    q = "SELECT track_id FROM songs INNER JOIN test_artists"
    q += " ON test_artists.artist_id=songs.artist_id"
    res = conn_tm.execute(q)
    test_tracks = res.fetchall()
    print 'Found',len(test_tracks),'from the test artists.'
    
    # get 300 most used tags
    q = "SELECT term,Count(artist_id) FROM artist_term GROUP BY term"
    res = conn_at.execute(q)
    term_freq_list = res.fetchall()
    term_freq = {}
    for k in term_freq_list:
        term_freq[k[0]] = int(k[1])
    ordered_terms = sorted(term_freq, key=term_freq.__getitem__, reverse=True)
    top300 = ordered_terms[:300]
    print 'Top 300 hundred terms are:',top300[:3],'...',top300[298:]

    # create tmp table with top 300 terms
    q = "CREATE TEMP TABLE top300 (term TEXT PRIMARY KEY)"
    conn_at.execute(q)
    for t in top300:
        q = "INSERT INTO top300 VALUES(" + encode_string(t) + ")"
        conn_at.execute(q)
    conn_at.commit()

    # create temp table with test_artists in artist_term conection
    q = "CREATE TEMP TABLE test_artists (artist_id TEXT PRIMARY KEY)"
    conn_at.execute(q)
    conn_at.commit()
    for artist in test_artists:
        q = "INSERT INTO test_artists VALUES('%s')" % artist
        conn_at.execute(q)
    conn_at.commit()

    # in train artists, find avgnterm average number of tags within top 300
    q = "SELECT artist_term.artist_id,Count(artist_term.term) FROM artist_term"
    q += " JOIN top300 ON artist_term.term=top300.term"
    q += " GROUP BY artist_term.artist_id"
    res = conn_at.execute(q)
    artist_count_top300 = filter(lambda x: not x[0] in test_artists, res.fetchall())
    print 'got count for',len(artist_count_top300),'artists'
    assert len(artist_count_top300)+len(test_artists) <= n_artists_with_term,'incoherence'
    print n_artists_with_term-len(test_artists)-len(artist_count_top300),'artists have terms but none in top 300.'
    avgnterm = np.average(map(lambda x: x[1],artist_count_top300))
    print 'In train set, an artist has on average',avgnterm,'terms from top 300 terms.'
    print '************ NOTE **********'
    print 'We ignore artists in train set with no term from top 300.'
    print 'The way the test set was built, test artists are guaranteed'
    print 'to have at least one termfrom top 300.'
    print '****************************'

    # tag test artists with the top avgnterm tags
    avgnterm = int(avgnterm)
    if forced_avgnterm >= 0:
        print 'INSTEAD OF',avgnterm,'TERMS, WE USE PREDICTIONS OF LENGTH',forced_avgnterm
        avgnterm = forced_avgnterm
    tagging_prediction = top300[:avgnterm]
    print 'METHOD: we will tag every test artists with the top',avgnterm,'terms, i.e.:'
    print map(lambda x: x.encode('utf-8'),tagging_prediction)

    # measure precision
    # - For terms in my tagging prediction, I retrieve every test artists, therefore precision
    # is the proportion of artists that were actually tagged with it.
    # - For terms not in my tagging prediction, I retrieve no artists, therefore precision is
    # set to 0
    acc_prop = 0
    for t in tagging_prediction:
        q = "SELECT Count(test_artists.artist_id) FROM test_artists"
        q += " JOIN artist_term ON artist_term.artist_id=test_artists.artist_id"
        q += " WHERE artist_term.term="+encode_string(t)
        res = conn_at.execute(q)
        acc_prop += res.fetchone()[0] * 1. / len(test_artists)
    precision = acc_prop / 300.
    print 'precision is:',precision

    # measure recall
    # - For terms in my tagging prediction, I retrieve every artists, therefore recall is 1.
    # - For terms not in my tagging prediction, I retrieve no artists, therefore recall is 0.
    recall = avgnterm / 300.
    print 'recall is:',recall

    # f-1 score
    print 'F-1 score is:',(precision + recall)/2.
    
    # close connections
    conn_tm.close()
    conn_at.close()
    

########NEW FILE########
__FILENAME__ = get_unique_terms
"""
Thierry Bertin-Mahieux (2010) Columbia University
tb2332@columbia.edu

This code is used to get the list of unique terms as fast
as possible. It dumps it to a file which can be used later.

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.


Copyright 2010, Thierry Bertin-Mahieux

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import glob
import time
import datetime
import numpy as np


NUMBUCKETS=10000 # hashing parameter


def path_from_trackid(trackid):
    """
    Creates the path from a given trackid
    """
    s = os.path.join(trackid[2],trackid[3])
    s = os.path.join(s,trackid[4])
    s = os.path.join(s,trackid)
    s = s.upper() + '.h5'
    return s

def put_term_in_hash_table(hash_table,term):
    """
    Function to get the hash code of a term and put it in the
    given table
    """
    np.random.seed(hash(term))
    bucket_idx = np.random.randint(NUMBUCKETS)
    hash_table[bucket_idx].add(term)


def die_with_usage():
    """ HELP MENU """
    print 'get_unique_terms.py'
    print '  by T. Bertin-Mahieux (2010) Colubia University'
    print 'GOAL'
    print '  creates a list of unique terms and unique musicbrainz tags as fast as possible'
    print 'USAGE'
    print '  python get_unique_terms.py <MillionSong dir> <output_terms.txt> <output_mbtags.txt> (OPTIONAL <artist list>)'
    print 'PARAM'
    print '   MillionSong dir   - MillionSongDataset root directory'
    print '   output_terms.txt  - result text file for the terms, one term per line'
    print '   output_mbtags.txt - results text file for the musicbrainz tags, on tag per line'
    print '   artist list       - text file: artistID<SEP>artistMBID<SEP>track<SEP>...   OPTIONAL BUT FASTER'
    print ''
    print 'for artist list, check: /Tasks_Demos/NamesAnalysis/list_all_artists.py'
    sys.exit(0)


if __name__ == '__main__':

    # WARNING
    print '+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++'
    print 'WARNING: if you have the artist_term.db SQLite database,'
    print 'the unique terms are in it and it takes only seconds to retrieve.'
    print 'see /Tasks_Demos/SQLite to know how'
    print '+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++'

    # help menu
    if len(sys.argv) < 4:
        die_with_usage()

    # import HDF5 stuff
    pythonsrc = os.path.join(sys.argv[0],'../../../PythonSrc')
    pythonsrc = os.path.abspath( pythonsrc )
    sys.path.append( pythonsrc )
    import hdf5_utils
    from hdf5_getters import *

    # read params
    maindir = os.path.abspath(sys.argv[1])
    output_terms = os.path.abspath(sys.argv[2])
    output_mbtags = os.path.abspath(sys.argv[3])
    artistfile = ''
    if len(sys.argv) > 4:
        artistfile = sys.argv[4]

    # check if file exists!
    if output_terms == output_mbtags:
        print 'output files most be different'
        sys.exit(0)
    if os.path.exists(output_terms):
        print output_terms,'already exists! delete or provide a new name'
        sys.exit(0)
    if os.path.exists(output_mbtags):
        print output_mbtags,'already exists! delete or provide a new name'
        sys.exit(0)
    

    # start time
    t1 = time.time()

    # create hash tables
    hash_table_terms = [None] * NUMBUCKETS
    hash_table_mbtags = [None] * NUMBUCKETS
    for k in range(NUMBUCKETS):
        hash_table_terms[k] = set()
        hash_table_mbtags[k] = set()
    
    # iterate HDF5 files
    cnt_files = 0
    if artistfile == '':
        for root, dirs, files in os.walk(maindir):
            files = glob.glob(os.path.join(root,'*.h5'))
            for f in files :
                h5 = hdf5_utils.open_h5_file_read(f)
                terms = get_artist_terms(h5)
                mbtags = get_artist_mbtags(h5)
                h5.close()
                # iterate over terms
                for t in terms:
                    put_term_in_hash_table(hash_table_terms,t)
                for t in mbtags:
                    put_term_in_hash_table(hash_table_mbtags,t)
                cnt_files += 1
    else:
        f = open(artistfile,'r')
        trackids = []
        for line in f.xreadlines():
            if line == '' or line.strip() == '':
                continue
            trackids.append( line.split('<SEP>')[2] )
        f.close()
        print 'found',len(trackids),'artists in file:',artistfile
        for trackid in trackids:
            f = os.path.join(maindir,path_from_trackid(trackid))
            h5 = hdf5_utils.open_h5_file_read(f)
            terms = get_artist_terms(h5)
            mbtags = get_artist_mbtags(h5)
            h5.close()
            # iterate over terms
            for t in terms:
                put_term_in_hash_table(hash_table_terms,t)
            for t in mbtags:
                put_term_in_hash_table(hash_table_mbtags,t)
            cnt_files += 1

    # count all terms and mbtags
    t2 = time.time()
    stimelength = str(datetime.timedelta(seconds=t2-t1))
    print 'all terms/mbtags added from',cnt_files,'files in',stimelength
    nUniqueTerms = 0
    for k in range(NUMBUCKETS):
        nUniqueTerms += len(hash_table_terms[k])
    print 'There are',nUniqueTerms,'unique terms.'
    nUniqueMbtags = 0
    for k in range(NUMBUCKETS):
        nUniqueMbtags += len(hash_table_mbtags[k])
    print 'There are',nUniqueMbtags,'unique mbtags.'

    # list all terms and mbtags
    allterms = [None] * nUniqueTerms
    cnt = 0
    for k in range(NUMBUCKETS):
        for t in hash_table_terms[k]:
            allterms[cnt] = t
            cnt += 1
    allterms = np.sort(allterms)
    allmbtags = [None] * nUniqueMbtags
    cnt = 0
    for k in range(NUMBUCKETS):
        for t in hash_table_mbtags[k]:
            allmbtags[cnt] = t
            cnt += 1
    allmbtags = np.sort(allmbtags)
    

    # write to file (terms)
    f = open(output_terms,'w')
    for t in allterms:
        f.write(t + '\n')
    f.close()
    # write to file (mbtags)
    f = open(output_mbtags,'w')
    for t in allmbtags:
        f.write(t + '\n')
    f.close()

    # end time
    t3 = time.time()
    stimelength = str(datetime.timedelta(seconds=t3-t1))
    print 'all done in',stimelength

########NEW FILE########
__FILENAME__ = get_unique_terms_from_db
"""
Thierry Bertin-Mahieux (2010) Columbia University
tb2332@columbia.edu

This code is used to get the list of unique terms as fast
as possible from an SQLite precomputed database (artist_term.db).
It dumps it to a file which can be used later.
Goal is the same as: get_unique_terms.py   just WAY faster
Twist: you need the list of unique terms to build the database
in the first place. Good news: we did it for you!

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.


Copyright 2010, Thierry Bertin-Mahieux

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""


import os
import sys
import glob
import time
import datetime
import numpy as np
try:
    import sqlite3
except ImportError:
    print 'you need sqlite3 installed to use this program'
    sys.exit(0)


def die_with_usage():
    """ HELP MENU """
    print 'get_unique_terms_from_db.py'
    print '  by T. Bertin-Mahieux (2010) Columbia University'
    print 'GOAL'
    print '  creates a list of unique tags as fast as possible'
    print '  actually, this code just extracts it from a SQLite db'
    print 'USAGE'
    print '  python get_unique_terms_from_db.py <artist_term.db> <unique_terms.txt> <unique_mbtags.txt>'
    print 'PARAM'
    print '   artist_term.db    - SQLite database of artists/terms'
    print '   unique_terms.txt  - result text file, one term per line'
    print '   unique_mbtags.txt - result text file, one mbtag per line'
    print ''
    print 'if you do not have the artist_term.db SQLite, check the slower code:'
    print '                        /Tasks_Demos/NamesAnalysis/get_unique_terms.py'
    print 'for artist list, check: /Tasks_Demos/NamesAnalysis/list_all_artists.py'
    print '             or faster: /Tasks_Demos/SQLite/list_all_artists_from_db.py'
    sys.exit(0)


if __name__ == '__main__':

    # help menu
    if len(sys.argv) < 3:
        die_with_usage()

    # params
    dbfile = os.path.abspath(sys.argv[1])
    output_term = os.path.abspath(sys.argv[2])
    output_mbtag = os.path.abspath(sys.argv[3])

    # sanity checks
    if not os.path.isfile(dbfile):
        print 'ERROR: database not found:',dbfile
        sys.exit(0)
    if os.path.exists(output_term):
        print 'ERROR:',output_term,'already exists! delete or provide a new name'
        sys.exit(0)
    if os.path.exists(output_mbtag):
        print 'ERROR:',output_mbtag,'already exists! delete or provide a new name'
        sys.exit(0)

    # query the database
    q1 = "SELECT DISTINCT term FROM terms ORDER BY term" # DISTINCT useless
    q2 = "SELECT DISTINCT mbtag FROM mbtags ORDER BY mbtag" # DISTINCT useless
    conn = sqlite3.connect(dbfile)
    c = conn.cursor()
    res = c.execute(q1)
    allterms = map(lambda x: x[0],res.fetchall())
    res = c.execute(q2)
    allmbtags = map(lambda x: x[0],res.fetchall())
    c.close()
    conn.close()
    print 'found',len(allterms),'unique terms.'
    print 'found',len(allmbtags),'unique mbtags.'
    
    # write to file terms
    f = open(output_term,'w')
    for t in allterms:
        f.write(t.encode('utf-8') + '\n')
    f.close()

    # write to file mbtags
    f = open(output_mbtag,'w')
    for t in allmbtags:
        f.write(t.encode('utf-8') + '\n')
    f.close()

########NEW FILE########
__FILENAME__ = split_train_test
"""
Thierry Bertin-Mahieux (2010) Columbia University
tb2332@columbia.edu

Code to split the dataset of Echo Nest tags into train and test.
Since these tags are applied to artists, we split artists.
The split is reproducible as long as the seed does not change.
Assumes we have the SQLite database artist_term.db

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.


Copyright 2010, Thierry Bertin-Mahieux

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import time
import glob
import warnings
import numpy as np
import sqlite3

# number of top terms we consider
NTERMS=300
# random seed, note that we actually use hash(RNDSEED) so it can be anything
RNDSEED='caitlin'


def encode_string(s):
    """
    Simple utility function to make sure a string is proper
    to be used in a SQLite query
    (different than posgtresql, no N to specify unicode)
    EXAMPLE:
      That's my boy! -> 'That''s my boy!'
    """
    return "'"+s.replace("'","''")+"'"

def check_constraint(term_freq,top_terms,top_terms_test_freq):
    """
    Check the constraint 12%-30% for the test set
    term_freq is the dictionnary of all term frequencies
    top_terms is the list of terms we care about (first 300?)
    top_terms_freq is an array of frequency of top terms in test set.
    RETURN
      True if constraint satisfied, False otherwise
    """
    return check_constraint_12pc(term_freq,top_terms,top_terms_test_freq) and check_constraint_30pc(term_freq,top_terms,top_terms_test_freq)

def check_constraint_12pc(term_freq,top_terms,top_terms_test_freq):
    """
    Check the constraint >12% for the test set
    term_freq is the dictionnary of all term frequencies
    top_terms is the list of terms we care about (first 300?)
    top_terms_freq is an array of frequency of top terms in test set.
    RETURN
      True if constraint satisfied, False otherwise
    """
    for tidx,t in enumerate(top_terms):
        totalf = term_freq[t]
        testf = top_terms_test_freq[tidx]
        if testf < totalf * .12:
            return False
    return True

def check_constraint_30pc(term_freq,top_terms,top_terms_test_freq):
    """
    Check the constraint <30% for the test set
    term_freq is the dictionnary of all term frequencies
    top_terms is the list of terms we care about (first 300?)
    top_terms_freq is an array of frequency of top terms in test set.
    RETURN
      True if constraint satisfied, False otherwise
    """
    for tidx,t in enumerate(top_terms):
        totalf = term_freq[t]
        testf = top_terms_test_freq[tidx]
        if testf > totalf * .30:
            return False
    return True


def get_terms_for_artist(conn,artistid):
    """
    Returns the list of terms for a given artist ID
    """
    q = "SELECT term FROM artist_term WHERE artist_id='"+artistid+"'"
    res = conn.execute(q)
    return map(lambda x: x[0],res.fetchall())

def get_random_artist_for_term(conn,term,avoid_artists=None):
    """
    Get a random artist that is tagged by a given term.
    If avoid_artists is a list, we exclude these artists.
    """
    q = "SELECT artist_id FROM artist_term WHERE term="+encode_string(term)
    res = conn.execute(q)
    all_artists = sorted( map(lambda x: x[0], res.fetchall()) )
    np.random.shuffle(all_artists)
    if avoid_artists is None:
        return all_artists[0]
    for a in all_artists:
        if not a in subset_artists:
            return a
    raise IndexError('Found no artist for term: '+term+' that is not in the avoid list')


def die_with_usage():
    """ HELP MENU """
    print 'split_train_test.py'
    print '  by T. Bertin-Mahieux (2010) Columbia University'
    print 'GOAL'
    print '  split the list of artists into train and test based on terms (Echo Nest tags).'
    print 'USAGE'
    print '  python split_train_test.py <artist_term.db> <train.txt> <test.txt> <top_terms.txt> <subset_tmdb>'
    print 'PARAMS'
    print '  artist_term.db    - SQLite database containing terms per artist'
    print '       train.txt    - list of Echo Nest artist ID'
    print '        test.txt    - list of Echo Nest artist ID'
    print '   top_terms.txt    - list of top terms (top 300)'
    print '     subset_tmdb    - track_metadata for the subset, to be sure all subset artists are in train'
    print ''
    print 'With the current settings, we get 4643 out of 44745 artists in the test set, corresponding to 122125 test tracks.'
    sys.exit(0)


if __name__ == '__main__':

    # help menu
    if len(sys.argv) < 6:
        die_with_usage()

    # params
    dbfile = sys.argv[1]
    output_train = sys.argv[2]
    output_test = sys.argv[3]
    output_top_terms = sys.argv[4]
    subset_tmdb = sys.argv[5]

    # sanity checks
    if not os.path.isfile(dbfile):
        print 'ERROR: database not found:',dbfile
        sys.exit(0)
    if os.path.exists(output_train):
        print 'ERROR:',output_train,'already exists! delete or provide a new name'
        sys.exit(0)
    if os.path.exists(output_test):
        print 'ERROR:',output_test,'already exists! delete or provide a new name'
        sys.exit(0)
    if os.path.exists(output_top_terms):
        print 'ERROR:',output_top_terms,'already exists! delete or provide a new name'
        sys.exit(0)
    if not os.path.exists(subset_tmdb):
        print 'ERROR:',subset_tmdb,'does not exist.'
        sys.exit(0)

    # open connection
    conn = sqlite3.connect(dbfile)

    # get all artists
    q = "SELECT artist_id FROM artists ORDER BY artist_id"
    res = conn.execute(q)
    allartists = map(lambda x: x[0],res.fetchall())
    print 'found',len(allartists),'distinct artists.'

    # get subset artists
    conn_subtmdb = sqlite3.connect(subset_tmdb)
    res = conn_subtmdb.execute('SELECT DISTINCT artist_id FROM songs')
    subset_artists = map(lambda x: x[0], res.fetchall())
    conn_subtmdb.close()
    print 'found',len(subset_artists),'distinct subset artists.'

    # get all terms
    q = "SELECT DISTINCT term FROM terms ORDER BY term" # DISTINCT useless
    res = conn.execute(q)
    allterms = map(lambda x: x[0],res.fetchall())
    print 'found',len(allterms),'distinct terms.'

    # get frequency
    term_freq = {}
    for t in allterms:
        term_freq[t] = 0
    q = "SELECT term FROM artist_term"
    res = conn.execute(q)
    allterms_nonunique = map(lambda x: x[0],res.fetchall())
    for t in allterms_nonunique:
        term_freq[t] += 1
    ordered_terms = sorted(term_freq, key=term_freq.__getitem__, reverse=True)
    print 'most used terms:',map(lambda x:x.encode('utf-8'), ordered_terms[:5])

    # try plotting
    try:
        warnings.simplefilter("ignore")
        import pylab as P
        P.figure()
        P.plot(map(lambda t: term_freq[t],ordered_terms[:500]))
        P.title('Frequencies of the 500 most used terms')
        P.show(False)
    except ImportError:
        print 'can not plot term frequencies, no pylab?'

    # print basic stats
    print 'term pos\tterm\t\tfrequency'
    print '0\t\t'+ordered_terms[0].encode('utf-8')+'\t\t',term_freq[ordered_terms[0]]
    print '50\t\t'+ordered_terms[50].encode('utf-8')+'\t',term_freq[ordered_terms[50]]
    print '100\t\t'+ordered_terms[100].encode('utf-8')+'\t\t',term_freq[ordered_terms[100]]
    print '200\t\t'+ordered_terms[200].encode('utf-8')+'\t\t',term_freq[ordered_terms[200]]
    print '300\t\t'+ordered_terms[300].encode('utf-8')+'\t\t',term_freq[ordered_terms[300]]
    print '500\t\t'+ordered_terms[500].encode('utf-8')+'\t',term_freq[ordered_terms[500]]

    # give info
    print '*************** METHOD *****************************'
    print 'We cut according to the top 300 terms.'
    print 'We select artists at random, but we make sure that'
    print 'that the test set contains between 12% and 30% of'
    print 'the artists for each of these 300 terms.'
    print 'We stop when that constraint is satisfied.'
    print '****************************************************'

    # top 300 terms
    topterms = np.array( ordered_terms[:NTERMS] )
    test_artists = set()
    test_term_freq = np.zeros(NTERMS)

    # set random seed
    np.random.seed(hash(RNDSEED))

    # heuristic: start filling from 300th and hope it works...
    term_id = NTERMS-1
    while term_id >= 0:
        #print 'term_id =',term_id
        #print '# test artists =',len(test_artists)
        term = topterms[term_id]
        artist = get_random_artist_for_term(conn,term,subset_artists)
        if artist in test_artists:
            continue
        test_artists.add(artist)
        terms = get_terms_for_artist(conn,artist)
        for t in terms:
            pos_t = np.where(topterms==t)[0]
            if len(pos_t)==0: continue
            test_term_freq[pos_t[0]] += 1
        # we check constraint 30%, if False, problem
        res = check_constraint_30pc(term_freq,topterms[term_id:],test_term_freq[term_id:])
        if not res:
            print 'we failed, term_id =',term_id,', term =',term
            break
        # we check constraint 12%, if true, decrement
        res = check_constraint_12pc(term_freq,topterms[term_id:],test_term_freq[term_id:])
        if res:
            term_id -= 1

    # close connection
    conn.close()

    # did we make it?
    good = check_constraint(term_freq,topterms,test_term_freq)
    if not good:
        print 'we did not make it'
        sys.exit(0)
    else:
        print 'IT WORKED, we have',len(test_artists),'/',len(allartists),'in the test set.'

    # we print to test file
    test_artists_list = sorted(list(test_artists))
    f = open(output_test,'w')
    for a in test_artists_list:
        f.write(a+'\n')
    f.close()

    # we print to train file
    train_artists = set()
    for a in allartists:
        if not a in test_artists:
            train_artists.add(a)
    assert len(train_artists) == len(allartists)-len(test_artists),'sanity check failed, check code'
    train_artists_list = sorted(list(train_artists))
    f = open(output_train,'w')
    for a in train_artists_list:
        f.write(a+'\n')
    f.close()

    # we print top terms
    f = open(output_top_terms,'w')
    for t in topterms:
        f.write(t.encode('utf-8')+'\n')
    f.close()

    # keep frequency plot open
    try:
        import pylab as P
        P.show(True)
    except ImportError:
        pass

########NEW FILE########
__FILENAME__ = count_ratings_known_artists
"""
Thierry Bertin-Mahieux (2011) Columbia University
tb2332@columbia.edu

This code takes a list of Yahoo artists matched with
Echo Nest ID, and look at the ratings in the Yahoo Dataset R1
to see how many ratings are covered by these artists.

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.

Copyright 2011, Thierry Bertin-Mahieux

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import time
import datetime
import numpy as np



def die_with_usage():
    """ HELP MENU """
    print 'count_ratings_known_artists.py'
    print '   by T. Bertin-Mahieux (2011) Columbia University'
    print '      tb2332@columbia.edu'
    print ''
    print 'Checks how many ratings from the Yahoo Dataset R1 we cover'
    print 'with known Echo Nest artist IDs'
    print ''
    print 'USAGE:'
    print '   python count_ratings_known_artists.py <y_artist_id> <a_map_file> <y_user_ratings>'
    print 'PARAMS:'
    print '     y_artist_id   - file "ydata-ymusic-artist-names-v1_0.txt" from Yahoo Dataset R1'
    print '      a_map_file   - artist mapping file, format: Yahoo Name<SEP>Echo Nest artist ID<SEP>...'
    print '  y_user_ratings   - file "ydata-ymusic-user-artist-ratings-v1_0.txt" from Yahoo Dataset R1'
    sys.exit(0)



if __name__ == '__main__':

    # help menu
    if len(sys.argv) < 4:
        die_with_usage()

    # params
    y_artist_id = sys.argv[1]
    a_map_file = sys.argv[2]
    y_user_ratings = sys.argv[3]

    # sanity checks
    if not os.path.isfile(y_artist_id):
        print 'ERROR: file',y_artist_id,'does not exist.'
        sys.exit(0)
    if not os.path.isfile(a_map_file):
        print 'ERROR: file',a_map_file,'does not exist.'
        sys.exit(0)
    if not os.path.isfile(y_user_ratings):
        print 'ERROR: file',y_user_ratings,'does not exist.'
        sys.exit(0)

    # initial time
    t1 = time.time()

    # read mapping, keep list of known Yahoo artist ID
    known_y_artist_names = set()
    f = open(a_map_file,'r')
    for line in f.xreadlines():
        if line == '' or line.strip() == '':
            continue
        yname = line.split('<SEP>')[0]
        known_y_artist_names.add(yname)
    f.close()
    print 'Found',len(known_y_artist_names),'Yahoo artist names that we know.'

    # read yahoo artist_id - artist_names to see which ID we know
    known_y_artist_id = set()
    f = open(y_artist_id,'r')
    for line in f.xreadlines():
        if line == '' or line.strip() == '':
            continue
        yid,yname = line.strip().split('\t')
        if yname in known_y_artist_names:
            known_y_artist_id.add(int(yid))
    f.close()
    print 'Found',len(known_y_artist_id),'Yahoo artist id that we know.'

    # count ratings belonging to one of these artists
    cnt_lines = 0
    cnt_ratings = 0
    f = open(y_user_ratings,'r')
    for line in f.xreadlines():
        if line == '' or line.strip() == '':
            continue
        cnt_lines += 1
        y_aid = int(line.strip().split('\t')[1])
        if y_aid in known_y_artist_id:
            cnt_ratings += 1
    f.close()
    print 'Found',cnt_ratings,'ratings for known artists out of',cnt_lines,'ratings.'
    print 'This means we cover',str(int(cnt_ratings * 10000. / cnt_lines)/100.)+'% of the ratings.'
    stimelen = str(datetime.timedelta(seconds=time.time()-t1))
    print 'All done in',stimelen

########NEW FILE########
__FILENAME__ = match_artist_names
"""
Thierry Bertin-Mahieux (2011) Columbia University
tb2332@columbia.edu

This code matches artist names with artists from the million
song dataset.

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.

Copyright 2011, Thierry Bertin-Mahieux

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import glob
import time
import copy
import datetime
import numpy as np
import sqlite3
try:
    import Levenshtein
except ImportError:
    print 'You need the code for Levenshtein edit distance:'
    print 'http://code.google.com/p/pylevenshtein/'
    sys.exit(0)

def encode_string(s):
    """
    Simple utility function to make sure a string is proper
    to be used in a SQLite query
    (different than posgtresql, no N to specify unicode)
    EXAMPLE:
      That's my boy! -> 'That''s my boy!'
    """
    return "'"+s.replace("'","''")+"'"


def purge_yahoo_artists(yartists_dict,done_artists):
    """
    Takes a dictionnary 'modified name' -> 'original Yahoo name'
    and removes the ones that are done
    """
    for k in yartists_dict.keys():
        if yartists_dict[k] in done_artists:
            del yartists_dict[k]

def remove_small_chars(s):
    """
    Remove , . and similar things, includind spaces
    """
    s = s.replace(' ','')
    s = s.replace('.','')
    s = s.replace(',','')
    s = s.replace('"','')
    s = s.replace("'",'')
    s = s.replace('\\','')
    s = s.replace('?','')
    s = s.replace('%','')
    s = s.replace('#','')
    s = s.replace('/','')
    s = s.replace('*','')
    s = s.replace('&','')
    return s


def die_with_usage():
    """ HELP MENU """
    print 'match_artist_names.py'
    print '  by T. Bertin-Mahieux (2011) Columbia University'
    print '     tb2332@columbia.edu'
    print ''
    print 'This code try to find matches between artists in Yahoo Ratings'
    print 'and artists in the Million Song Dataset'
    print ''
    print 'USAGE:'
    print '  python match_artist_names.py <track_metadata.db> <yahoo_artists.txt> <output.txt> (OPT: unmatched.txt)'
    print 'PARAMS:'
    print '  track_metadata.db   - SQLite database with all the Million Song Dataset tracks'
    print "  yahoo_artists.txt   - file 'ydata-ymusic-artist-names-v1_0.txt' in Yahoo dataset R1"
    print '             output   - text file with result: yahoo name, Echo Nest name, Echo Nest ID'
    print '      unmatched.txt   - list artists that were not matched'
    sys.exit(0)


if __name__ == '__main__':

    # help menu
    if len(sys.argv) < 4:
        die_with_usage()

    # flags
    startfile = ''
    startstep = 0
    while True:
        if sys.argv[1] == '-startf':
            startfile = sys.argv[2]
            sys.argv.pop(1)
        elif sys.argv[1] == '-startstep':
            startstep = int(sys.argv[2])
            sys.argv.pop(1)
        else:
            break
        sys.argv.pop(1)

    # params
    dbfile = sys.argv[1]
    yahoofile = sys.argv[2]
    output = sys.argv[3]
    out_unmatched = ''
    if len(sys.argv) >= 5:
        out_unmatched = sys.argv[4]

    # sanity checks
    if not os.path.isfile(dbfile):
        print 'ERROR: file',dbfile,'does not exist.'
        sys.exit(0)
    if not os.path.isfile(yahoofile):
        print 'ERROR: file',yahoofile,'does not exist.'
        sys.exit(0)
    if os.path.isfile(output):
        print 'ERROR: file',output,'exists, delete or provide a new one.'
        sys.exit(0)
    if out_unmatched != '' and os.path.isfile(out_unmatched):
        print 'ERROR: file',out_unmatched,'exists, delete or provide a new one.'
        sys.exit(0)

    # read yahoo data
    f = open(yahoofile,'r')
    lines = f.readlines()
    f.close()
    yartists = map(lambda l: l.strip().split('\t')[1],lines)

    # remove 'Not Applicable' and 'Unknown Artist'
    if yartists[0] == 'Not Applicable' and yartists[1] == 'Unknown Artist':
        yartists = yartists[2:]

    print 'Found',len(yartists),'Yahoo artists:',yartists[:3],'...'
    nya = len(yartists)

    # get artist names from the Million Song Dataset
    t1 = time.time()
    q = "SELECT DISTINCT artist_name,artist_id FROM songs"
    conn = sqlite3.connect(dbfile)
    res = conn.execute(q)
    msd_artists = res.fetchall()
    conn.close()
    stimelength = str(datetime.timedelta(seconds=time.time()-t1))
    print 'Found',len(msd_artists),'artists from the Million Song Dataset in',stimelength

    # dict of name -> Echo Nest ID, names are all lower case
    name_enid = {}
    for p in msd_artists:
        name_enid[p[0].lower().encode('utf-8')] = p[1]

    # set of yahoo artists
    yartists_dict = {}
    for a in yartists:
        yartists_dict[a.lower()] = a

    # dictionary of done artists
    done_artists = {}

    # start file?
    if startfile != '':
        f = open(startfile,'r')
        lines = f.readlines()
        done_data = map(lambda x: x.strip().split('<SEP>'),lines)
        for dd in done_data:
            done_artists[dd[0]] = [dd[1],dd[2]]
        f.close()
        purge_yahoo_artists(yartists_dict, done_artists.keys())
        print 'Found',len(done_data),'done artists from the start file.'

    # exact matches
    print '************* EXACT MATCHES ********************'
    if startstep <= 1:
        cnt_exact = 0
        t1 = time.time()
        ya_set = yartists_dict.keys()
        msda_set = name_enid.keys()
        for ya in ya_set:
            if ya in msda_set:
                done_artists[ yartists_dict[ya] ] = [name_enid[ya],ya]
                cnt_exact += 1
                del yartists_dict[ya]
        stimelength = str(datetime.timedelta(seconds=time.time()-t1))
        print 'found',cnt_exact,'exact matches in',stimelength            

    # remove little characters . ' " % and spaces
    print '************* REMOVE SPACES AND SMALL CHAR *****'
    if startstep <= 2:
        purge_yahoo_artists(yartists_dict, done_artists.keys())
        cnt_smallchar = 0
        lower_ya = copy.deepcopy(yartists_dict.keys())
        for a in lower_ya:
            yartists_dict[ remove_small_chars(a) ] = yartists_dict[a]
        lower_msda = copy.deepcopy(name_enid.keys())
        for a in lower_msda:
            name_enid[ remove_small_chars(a) ] = name_enid[a]
        t1 = time.time()
        for ya in yartists_dict.keys():
            if ya in name_enid.keys():
                done_artists[ yartists_dict[ya] ] = [name_enid[ya],ya]
                cnt_smallchar += 1
                del yartists_dict[ya]
        stimelength = str(datetime.timedelta(seconds=time.time()-t1))
        print 'found',cnt_smallchar,'exact matches in',stimelength            
        

    # write matches
    f = open(output,'a')
    for ya in done_artists.keys():
        f.write(ya+'<SEP>'+done_artists[ya][0]+'<SEP>')
        f.write(done_artists[ya][1]+'\n')
    f.close()

    
    # print unmatched
    if out_unmatched != '':
        purge_yahoo_artists(yartists_dict, done_artists.keys())
        unique_a = set()
        for a in yartists_dict.values():
            unique_a.add( a )
        f = open(out_unmatched,'w')
        for a in unique_a:
            f.write(a+'\n')
        f.close()

########NEW FILE########
__FILENAME__ = beat_aligned_feats
"""
Thierry Bertin-Mahieux (2011) Columbia University
tb2332@columbia.edu

Code to get beat-aligned features (chromas or timbre)
from the HDF5 song files of the Million Song Dataset.

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.


Copyright 2011, Thierry Bertin-Mahieux
parts of this code from Ron J. Weiss

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import time
import glob
import numpy as np
try:
    import hdf5_getters as GETTERS
except ImportError:
    print 'cannot find file hdf5_getters.py'
    print 'you must put MSongsDB/PythonSrc in your path or import it otherwise'
    raise


def get_btchromas(h5):
    """
    Get beat-aligned chroma from a song file of the Million Song Dataset
    INPUT:
       h5          - filename or open h5 file
    RETURN:
       btchromas   - beat-aligned chromas, one beat per column
                     or None if something went wrong (e.g. no beats)
    """
    # if string, open and get chromas, if h5, get chromas
    if type(h5).__name__ == 'str':
        h5 = GETTERS.open_h5_file_read(h5)
        chromas = GETTERS.get_segments_pitches(h5)
        segstarts = GETTERS.get_segments_start(h5)
        btstarts = GETTERS.get_beats_start(h5)
        duration = GETTERS.get_duration(h5)
        h5.close()
    else:
        chromas = GETTERS.get_segments_pitches(h5)
        segstarts = GETTERS.get_segments_start(h5)
        btstarts = GETTERS.get_beats_start(h5)
        duration = GETTERS.get_duration(h5)
    # get the series of starts for segments and beats
    # NOTE: MAYBE USELESS?
    # result for track: 'TR0002Q11C3FA8332D'
    #    segstarts.shape = (708,)
    #    btstarts.shape = (304,)
    segstarts = np.array(segstarts).flatten()
    btstarts = np.array(btstarts).flatten()
    # aligned features
    btchroma = align_feats(chromas.T, segstarts, btstarts, duration)
    if btchroma is None:
        return None
    # Renormalize. Each column max is 1.
    maxs = btchroma.max(axis=0)
    maxs[np.where(maxs == 0)] = 1.
    btchroma = (btchroma / maxs)
    # done
    return btchroma


def get_btchromas_loudness(h5):
    """
    Similar to btchroma, but adds the loudness back.
    We use the segments_loudness_max
    There is no max value constraint, simply no negative values.
    """
    # if string, open and get chromas, if h5, get chromas
    if type(h5).__name__ == 'str':
        h5 = GETTERS.open_h5_file_read(h5)
        chromas = GETTERS.get_segments_pitches(h5)
        segstarts = GETTERS.get_segments_start(h5)
        btstarts = GETTERS.get_beats_start(h5)
        duration = GETTERS.get_duration(h5)
        loudnessmax = GETTERS.get_segments_loudness_max(h5)
        h5.close()
    else:
        chromas = GETTERS.get_segments_pitches(h5)
        segstarts = GETTERS.get_segments_start(h5)
        btstarts = GETTERS.get_beats_start(h5)
        duration = GETTERS.get_duration(h5)
        loudnessmax = GETTERS.get_segments_loudness_max(h5)
    # get the series of starts for segments and beats
    segstarts = np.array(segstarts).flatten()
    btstarts = np.array(btstarts).flatten()
    # add back loudness
    chromas = chromas.T * idB(loudnessmax)
    # aligned features
    btchroma = align_feats(chromas, segstarts, btstarts, duration)
    if btchroma is None:
        return None
    # done (no renormalization)
    return btchroma


def get_bttimbre(h5):
    """
    Get beat-aligned timbre from a song file of the Million Song Dataset
    INPUT:
       h5          - filename or open h5 file
    RETURN:
       bttimbre    - beat-aligned timbre, one beat per column
                     or None if something went wrong (e.g. no beats)
    """
    # if string, open and get timbre, if h5, get timbre
    if type(h5).__name__ == 'str':
        h5 = GETTERS.open_h5_file_read(h5)
        timbre = GETTERS.get_segments_timbre(h5)
        segstarts = GETTERS.get_segments_start(h5)
        btstarts = GETTERS.get_beats_start(h5)
        duration = GETTERS.get_duration(h5)
        h5.close()
    else:
        timbre = GETTERS.get_segments_timbre(h5)
        segstarts = GETTERS.get_segments_start(h5)
        btstarts = GETTERS.get_beats_start(h5)
        duration = GETTERS.get_duration(h5)
    # get the series of starts for segments and beats
    # NOTE: MAYBE USELESS?
    # result for track: 'TR0002Q11C3FA8332D'
    #    segstarts.shape = (708,)
    #    btstarts.shape = (304,)
    segstarts = np.array(segstarts).flatten()
    btstarts = np.array(btstarts).flatten()
    # aligned features
    bttimbre = align_feats(timbre.T, segstarts, btstarts, duration)
    if bttimbre is None:
        return None
    # done (no renormalization)
    return bttimbre


def get_btloudnessmax(h5):
    """
    Get beat-aligned loudness max from a song file of the Million Song Dataset
    INPUT:
       h5             - filename or open h5 file
    RETURN:
       btloudnessmax  - beat-aligned loudness max, one beat per column
                        or None if something went wrong (e.g. no beats)
    """
    # if string, open and get max loudness, if h5, get max loudness
    if type(h5).__name__ == 'str':
        h5 = GETTERS.open_h5_file_read(h5)
        loudnessmax = GETTERS.get_segments_loudness_max(h5)
        segstarts = GETTERS.get_segments_start(h5)
        btstarts = GETTERS.get_beats_start(h5)
        duration = GETTERS.get_duration(h5)
        h5.close()
    else:
        loudnessmax = GETTERS.get_segments_loudness_max(h5)
        segstarts = GETTERS.get_segments_start(h5)
        btstarts = GETTERS.get_beats_start(h5)
        duration = GETTERS.get_duration(h5)
    # get the series of starts for segments and beats
    # NOTE: MAYBE USELESS?
    # result for track: 'TR0002Q11C3FA8332D'
    #    segstarts.shape = (708,)
    #    btstarts.shape = (304,)
    segstarts = np.array(segstarts).flatten()
    btstarts = np.array(btstarts).flatten()
    # reverse dB
    loudnessmax = idB(loudnessmax)
    # aligned features
    btloudnessmax = align_feats(loudnessmax.reshape(1,
                                                    loudnessmax.shape[0]),
                                segstarts, btstarts, duration)
    if btloudnessmax is None:
        return None
    # set it back to dB
    btloudnessmax = dB(btloudnessmax + 1e-10)
    # done (no renormalization)
    return btloudnessmax


def align_feats(feats, segstarts, btstarts, duration):
    """
    MAIN FUNCTION: aligned whatever matrix of features is passed,
    one column per segment, and interpolate them to get features
    per beat.
    Note that btstarts could be anything, e.g. bar starts
    INPUT
       feats      - matrix of features, one column per segment
       segstarts  - segments starts in seconds,
                    dim must match feats # cols (flatten ndarray)
       btstarts   - beat starts in seconds (flatten ndarray)
       duration   - overall track duration in seconds
    RETURN
       btfeats    - features, one column per beat
                    None if there is a problem
    """
    # sanity check
    if feats.shape[0] == 0 or feats.shape[1] == 0:
        return None
    if btstarts.shape[0] == 0 or segstarts.shape[0] == 0:
        return None

    # FEAT PER BEAT
    # Move segment feature onto a regular grid
    # result for track: 'TR0002Q11C3FA8332D'
    #    warpmat.shape = (304, 708)
    #    btchroma.shape = (304, 12)
    warpmat = get_time_warp_matrix(segstarts, btstarts, duration)
    featchroma = np.dot(warpmat, feats.T).T
    if featchroma.shape[1] == 0: # sanity check
        return None

    # done
    return featchroma


def get_time_warp_matrix(segstart, btstart, duration):
    """
    Used by create_beat_synchro_chromagram
    Returns a matrix (#beats,#segs)
    #segs should be larger than #beats, i.e. many events or segs
    happen in one beat.
    THIS FUNCTION WAS ORIGINALLY CREATED BY RON J. WEISS (Columbia/NYU/Google)
    """
    # length of beats and segments in seconds
    # result for track: 'TR0002Q11C3FA8332D'
    #    seglen.shape = (708,)
    #    btlen.shape = (304,)
    #    duration = 238.91546    meaning approx. 3min59s
    seglen = np.concatenate((segstart[1:], [duration])) - segstart
    btlen = np.concatenate((btstart[1:], [duration])) - btstart

    warpmat = np.zeros((len(segstart), len(btstart)))
    # iterate over beats (columns of warpmat)
    for n in xrange(len(btstart)):
        # beat start time and end time in seconds
        start = btstart[n]
        end = start + btlen[n]
        # np.nonzero returns index of nonzero elems
        # find first segment that starts after beat starts - 1
        try:
            start_idx = np.nonzero((segstart - start) >= 0)[0][0] - 1
        except IndexError:
            # no segment start after that beats, can happen close
            # to the end, simply ignore, maybe even break?
            # (catching faster than ckecking... it happens rarely?)
            break
        # find first segment that starts after beat ends
        segs_after = np.nonzero((segstart - end) >= 0)[0]
        if segs_after.shape[0] == 0:
            end_idx = start_idx
        else:
            end_idx = segs_after[0]
        # fill col of warpmat with 1 for the elem in between
        # (including start_idx, excluding end_idx)
        warpmat[start_idx:end_idx, n] = 1.
        # if the beat started after the segment, keep the proportion
        # of the segment that is inside the beat
        warpmat[start_idx, n] = 1. - ((start - segstart[start_idx])
                                 / seglen[start_idx])
        # if the segment ended after the beat ended, keep the proportion
        # of the segment that is inside the beat
        if end_idx - 1 > start_idx:
            warpmat[end_idx-1, n] = ((end - segstart[end_idx-1])
                                     / seglen[end_idx-1])
        # normalize so the 'energy' for one beat is one
        warpmat[:, n] /= np.sum(warpmat[:, n])
    # return the transpose, meaning (#beats , #segs)
    return warpmat.T


def idB(loudness_array):
    """
    Reverse the Echo Nest loudness dB features.
    'loudness_array' can be pretty any numpy object:
    one value or an array
    Inspired by D. Ellis MATLAB code
    """
    return np.power(10., loudness_array / 20.)


def dB(inv_loudness_array):
    """
    Put loudness back in dB
    """
    return np.log10(inv_loudness_array) * 20.


def die_with_usage():
    """ HELP MENU """
    print 'beat_aligned_feats.py'
    print '   by T. Bertin-Mahieux (2011) Columbia University'
    print '      tb2332@columbia.edu'
    print ''
    print 'This code is intended to be used as a library.'
    print 'For debugging purposes, you can launch:'
    print '   python beat_aligned_feats.py <SONG FILENAME>'
    sys.exit(0)


if __name__ == '__main__':

    # help menu
    if len(sys.argv) < 2:
        die_with_usage()

    print '*** DEBUGGING ***'

    # params
    h5file = sys.argv[1]
    if not os.path.isfile(h5file):
        print 'ERROR: file %s does not exist.' % h5file
        sys.exit(0)

    # compute beat chromas
    btchromas = get_btchromas(h5file)
    print 'btchromas.shape =', btchromas.shape
    if np.isnan(btchromas).any():
        print 'btchromas have NaN'
    else:
        print 'btchromas have no NaN'
    print 'the max value is:', btchromas.max()

    # compute beat timbre
    bttimbre = get_bttimbre(h5file)
    print 'bttimbre.shape =', bttimbre.shape
    if np.isnan(bttimbre).any():
        print 'bttimbre have NaN'
    else:
        print 'bttimbre have no NaN'
    print 'the max value is:', bttimbre.max()

########NEW FILE########
__FILENAME__ = auto_vw
#!/usr/bin/env python
"""
Code to test a lot of parameters of vowpal
"""

import os
import sys
import copy
import time
import datetime
import numpy as np
from operator import itemgetter
import measure_vw_res as MEASURE


# FIXED ARGS
PREFIX='/home/bin/?????/vowpal_wabbit/vw'         # path to vw program
CACHE='cache_vw_tmp'                              # path to cache file
#CACHETEST='cache_vw_tmp_test'                    # path to test cache file
TRAIN='vw_train.txt'                              # train file
TEST='vw_test.txt'                                # test file
#TRAIN='vw_subtrain.txt'
#TEST='vw_subvalid.txt'
MODEL='vw_model'                                  # where to save the model
PREDS='vw_preds.txt'                              # where to output predictions
QUIET=True                                        # don't display much

AUTOTRAINOUTPUT='auto_train_results.txt'          # save the summary

# PARAMS TO TRY
PASSES=[10,50,100]                                # number of passes
INITIALT=[1,1000,100000]                          # initial t (see vw doc)
LOSSF=['squared','quantile'] # hinge bad?         # loss functions
LRATE=[.1,1,10,100]                               # learning rate
DLRATE=[1./np.sqrt(2),1.]                         # decay learning rate
CONJGRAD=['',' --conjugate_gradient',' --adaptive']  # gradient?

def build_commands():
    """
    Build commands based on arguments to try
    """
    # fixed info
    cmd = PREFIX + ' -c --cache_file ' + CACHE + ' ' + TRAIN
    cmd += ' -f ' + MODEL
    if QUIET:
        cmd += ' --quiet'
    cmd += ' ' # hack, so we can split and keep the interesting part
    # number of passes
    cmds = map(lambda x: cmd + ' --passes '+str(x),PASSES)
    # loss function
    tmpcmds = copy.deepcopy(cmds)
    cmds = []
    for cmd in tmpcmds:
        c = map(lambda x: cmd + ' --loss_function '+x,LOSSF)
        cmds.extend(c)
    # conjugate gradient
    tmpcmds = copy.deepcopy(cmds)
    cmds = []
    for cmd in tmpcmds:
        c = map(lambda x: cmd + x,CONJGRAD)
        cmds.extend(c)
    # learning rate (unless conjugate gradient)
    tmpcmds = copy.deepcopy(cmds)
    cmds = []
    for cmd in tmpcmds:
        c = map(lambda x: cmd + ' -l '+str(x) if cmd.find('conjugate')<0 else cmd,LRATE)
        cmds.extend(c)
    # initial t
    tmpcmds = copy.deepcopy(cmds)
    cmds = []
    for cmd in tmpcmds:
        c = map(lambda x: cmd + ' --initial_t '+str(x) if cmd.find('conjugate')<0 else cmd,INITIALT)
        cmds.extend(c)
    # decay learning rate
    tmpcmds = copy.deepcopy(cmds)
    cmds = []
    for cmd in tmpcmds:
        c = map(lambda x: cmd + ' --decay_learning_rate '+str(x) if cmd.find('conjugate')<0 else cmd ,DLRATE)
        cmds.extend(c)
    # done
    cmds = list(np.unique(cmds))
    return cmds

def build_test_cmd():
    """ CREATE TEST COMMAND """
    cmd = PREFIX + " " + TEST + ' --quiet'
    cmd += " -i " + MODEL + " -p " + PREDS
    # done
    return cmd

def print_best_results(results,ntoprint=5):
    """ function to print best results so far """
    print '*******************************************'
    print 'BEST RESULTS:'
    results = sorted(results,key=itemgetter(0))
    for res in results[:ntoprint]:
        print '*',res[0],'->',res[1].split('  ')[1],format('(%.3f %.3f %.3f %.3f)' % res[2])
    print '*******************************************'


def results_to_file(results):
    """ output results to file """
    results = sorted(results,key=itemgetter(0))
    f = open(AUTOTRAINOUTPUT,'w')
    for res in results:
        f.write('* ['+str(res[0])+'] '+res[1].split('  ')[1]+' -> '+str(res[2]))
        f.write('\n')
    f.close()


def launch_vw_wrapper(cmd=None,threadid=0,outputf=''):
    """
    Wrapper to use our automatic training with multiple processes
    IN DEVELOPMENT
    """
    try:
        assert not cmd is None
        assert not outputf is ''
        # replace stuff
        model = MODEL + str(int(threadid))
        cmd = cmd.replace(MODEL,model)
        cache = CACHE + str(int(threadid))
        cmd = cmd.replace(CACHE,cache)
        # launch
        raise NotImplementedError
        # get results and write them
        raise NotImplementedError
        # cleanup
        if os.path.isfile(model):
            os.remove(model)
        if os.path.isfile(cache):
            os.remove(cache)
    except KeyboardInterrupt:
        raise KeyboardInterruptError()

def die_with_usage():
    """ HELP MENU """
    print 'auto_vw.py'
    print 'test a ton of vw parameters, shows the results'
    print ''
    sys.exit(0)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        die_with_usage()

    # create commands
    cmds = build_commands()
    np.random.shuffle(cmds)
    print 'Got',len(cmds),'commands, first ones:'
    print cmds[:3]

    # results, contains avg diff, cmd, all results
    results = []

    # start time
    t1 = time.time()

    # launch 
    for idx,cmd in enumerate(cmds):
        # launch command
        res = os.system(cmd)
        if res != 0:
            print '************************************************'
            print 'last cmd =',cmd
            print "Something went wrong, keyboard interrupt?"
            break
        # measure result
        test_cmd = build_test_cmd()
        res = os.system(test_cmd)
        if res != 0:
            print "Something went wrong, keyboard interrupt?"
            break
        meas = MEASURE.measure(TEST,PREDS,verbose=0)
        # results
        results.append( [meas[0], cmd, meas] )
        # meas contains: avg diff, std diff, avg diff sq, std diff sq
        print str(idx)+')',format('%.3f %.3f %.3f %.3f' % meas)
        # display time
        if idx % 5 == 4:
            print 'Time so far:',str(datetime.timedelta(seconds=time.time()-t1))
            print_best_results(results)
            results_to_file(results)

    # print best results
    print_best_results(results)

    # print results to file
    results_to_file(results)

########NEW FILE########
__FILENAME__ = compress_feat
"""
Thierry Bertin-Mahieux (2011) Columbia University
tb2332@columbia.edu

Library to compress beat features, mostly timbre here,
probably using random projections in order to use large KNN later.

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.

Copyright 2011, Thierry Bertin-Mahieux

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""


import os
import sys
import numpy as np
import randproj as RANDPROJ


def corr_and_compress(feats,finaldim,seed=3232343,randproj=None):
    """
    From a features matrix 12x.... (beat-aligned or not)
    Compute the correlation matrix (12x12) and projects it (except diagonal)
    to the given final dim
    RETURN
       vector 1xfinaldim   or 0xfinaldim is problem
    """
    # features length
    ftlen = feats.shape[1]
    ndim = feats.shape[0]
    # too small case
    if ftlen < 3:
        return np.zeros((0,finaldim))
    # random projection
    if randproj is None:
        # 12*12
        randproj = RANDPROJ.proj_point5(144, finaldim, seed=seed)
    # corr
    corrc = np.corrcoef(feats)
    # compress
    return np.dot(corrc.flatten(),randproj).reshape(1,finaldim)


def cov_and_compress(feats,finaldim,seed=3232343,randproj=None):
    """
    From a features matrix 12x.... (beat-aligned or not)
    Compute the correlation matrix (12x12) and projects it (except diagonal)
    to the given final dim
    RETURN
       vector 1xfinaldim   or 0xfinaldim is problem
    """
    # features length
    ftlen = feats.shape[1]
    ndim = feats.shape[0]
    # too small case
    if ftlen < 3:
        return np.zeros((0,finaldim))
    # random projection
    if randproj is None:
        # 12*12
        randproj = RANDPROJ.proj_point5(144, finaldim, seed=seed)
    # corr
    fcov = np.cov(feats)
    # compress
    return np.dot(fcov.flatten(),randproj).reshape(1,finaldim)

def avgcov_and_compress(feats,finaldim,seed=3232343,randproj=None):
    """
    From a features matrix 12x.... (beat-aligned or not)
    Compute the correlation matrix (12x12) and projects it (except diagonal)
    to the given final dim
    RETURN
       vector 1xfinaldim   or 0xfinaldim is problem
    """
    # features length
    ftlen = feats.shape[1]
    ndim = feats.shape[0]
    # too small case
    if ftlen < 3:
        return np.zeros((0,finaldim))
    # random projection
    if randproj is None:
        # 12 + 78, 78=13*12/2
        randproj = RANDPROJ.proj_point5(90, finaldim, seed=seed)
    # corr
    avg = np.average(feats,1)
    cov = np.cov(feats)
    covflat = []
    for k in range(12):
        covflat.extend( np.diag(cov,k) )
    covflat = np.array(covflat)
    feats = np.concatenate([avg,covflat])
    # compress
    return np.dot(feats.flatten(),randproj).reshape(1,finaldim)

def extract_and_compress(btfeat,npicks,winsize,finaldim,seed=3232343,randproj=None):
    """
    From a btfeat matrix, usually 12xLENGTH
    Extracts 'npicks' windows of size 'winsize' equally spaced
    Flatten these picks, pass them through a random projection, final
    size is 'finaldim'
    Returns matrix npicks x finaldim, or 0 x finaldim if problem
    (btfeats not long enough for instance)
    We could return less than npicks if not long enough!
    For speed, we can compute the random projection once and pass it as an
    argument.
    """
    # features length
    ftlen = btfeat.shape[1]
    ndim = btfeat.shape[0]
    # too small case
    if ftlen < winsize:
        return np.zeros((0,finaldim))
    # random projection
    if randproj is None:
        randproj = RANDPROJ.proj_point5(ndim * winsize, finaldim, seed=seed)
    # not big enough for number of picks, last one too large return just 1
    if ftlen < int(ftlen * (npicks *1./(npicks+1))) + winsize:
        pos = int( (ftlen-winsize) /  2.) # middle
        picks = [ btfeat[:,pos:pos+winsize] ]
    # regular case, picks will contain npicks
    else:
        picks = []
        for k in range(1,npicks+1):
            pos = int(ftlen * (k *1./(npicks+1)))
            picks.append( btfeat[:,pos:pos+winsize] )
    # project / compress these
    projections = map(lambda x: np.dot(x.flatten(),randproj).reshape(1,finaldim), picks)
    return np.concatenate(projections)
    


def die_with_usage():
    """ HELP MENU """
    print 'compress_feat.py'
    print '   by T. Bertin-Mahieux (2011) Columbia University'
    print '      tb2332@columbia.edu'
    print ''
    print 'This code extracts and compress samples from beat-aligned features.'
    print 'Should be used as a library, no main'
    sys.exit(0)


if __name__ == '__main__':

    # help menu
    die_with_usage()

########NEW FILE########
__FILENAME__ = create_vw_dataset
"""
Thierry Bertin-Mahieux (2011) Columbia University
tb2332@columbia.edu

Code to create a dataset for the vw machine learning tool on
Year Prediction. Features are mean and covariance of
the timbre features. The task is a regression, year
being the target (brought back to 0-1)

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.


Copyright 2011, Thierry Bertin-Mahieux
parts of this code from Ron J. Weiss

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import time
import glob
import sqlite3
import datetime
import numpy as np
import hdf5_getters as GETTERS


def convert_year(y):
    """
    brings back the year between 0 and 1
    returns a float
    """
    res = (y - 1922.) / (2011.-1922.)
    assert res>=0 and res<=1,'problem in year conversion, '+str(y)+'->'+str(res)
    return res

def fullpath_from_trackid(maindir,trackid):
    """ Creates proper file paths for song files """
    p = os.path.join(maindir,trackid[2])
    p = os.path.join(p,trackid[3])
    p = os.path.join(p,trackid[4])
    p = os.path.join(p,trackid+'.h5')
    return str(p)


def get_train_test_songs(msd_dir,testartists,tmdb):
    """
    Creates two list of songs, one for training and one for testing.
    INPUT
           msd_dir   - main MSD dir, <?>/MillionSong/data
       testartists   - file containing test artist IDs
              tmdb   - SQLite database track_metadata.db
    RETURN
       2 lists: trainsongs, testsongs
    """
    # read test artists
    testartists_set = set()
    if testartists != '':
        f = open(testartists,'r')
        for line in f.xreadlines():
            if line == '' or line.strip() == '':
                continue
            testartists_set.add( line.strip() )
        f.close()
    print 'Found',len(testartists_set),'test artists.'
    # get songlist from track_metadata.db
    conn = sqlite3.connect(tmdb)
    q = "CREATE TEMP TABLE testartists (artist_id TEXT)"
    res = conn.execute(q)
    conn.commit()
    for aid in testartists_set:
        q = "INSERT INTO testartists VALUES ('"+aid+"')"
        conn.execute(q)
    conn.commit()
    q = "CREATE TEMP TABLE trainartists (artist_id TEXT)"
    res = conn.execute(q)
    conn.commit()
    q = "INSERT INTO trainartists SELECT DISTINCT artist_id FROM songs"
    q += " EXCEPT SELECT artist_id FROM testartists"
    res = conn.execute(q)
    conn.commit()
    q = "SELECT track_id FROM songs JOIN trainartists"
    q += " ON trainartists.artist_id=songs.artist_id WHERE year>0"
    res = conn.execute(q)
    data = res.fetchall()
    print 'Found',len(data),'training files from track_metadata.db'
    trainsongs = map(lambda x: fullpath_from_trackid(msd_dir,x[0]),data)
    assert os.path.isfile(trainsongs[0]),'first training file does not exist? '+trainsongs[0]
    q = "SELECT track_id FROM songs JOIN testartists"
    q += " ON testartists.artist_id=songs.artist_id WHERE year>0"
    res = conn.execute(q)
    data = res.fetchall()
    print 'Found',len(data),'testing files from track_metadata.db'
    testsongs = map(lambda x: fullpath_from_trackid(msd_dir,x[0]),data)
    assert os.path.isfile(testsongs[0]),'first testing file does not exist? '+testsongs[0]
    # close db
    conn.close()
    # done
    return trainsongs,testsongs


def extract_features(songlist,outputf):
    """
    Extract features from a list of songs, save them in a give filename
    in MLcomp ready format
    INPUT
        songlist   - arrays of path to HDF5 song files
         outputf   - filename (text file)
    """
    # sanity check
    if os.path.isfile(outputf):
        print 'ERROR:',outputf,'already exists.'
        sys.exit(0)
    # open file
    output = open(outputf,'w')
    # iterate ofer songs
    cnt = 0
    for f in songlist:
        # counter
        cnt += 1
        if cnt % 50000 == 0:
            print 'DOING FILE',cnt,'/',len(songlist)
        # extract info
        h5 = GETTERS.open_h5_file_read(f)
        timbres = GETTERS.get_segments_timbre(h5).T
        year = GETTERS.get_year(h5)
        h5.close()
        # sanity checks
        if year <= 0:
            continue
        if timbres.shape[1] == 0 or timbres.shape[0] == 0:
            continue
        if timbres.shape[1] < 10:
            continue # we can save some space from bad examples?
        # features
        avg = np.average(timbres,1)
        cov = np.cov(timbres)
        covflat = []
        for k in range(12):
            covflat.extend( np.diag(cov,k) )
        covflat = np.array(covflat)
        feats = np.concatenate([avg,covflat])
        # sanity check NaN and INF
        if np.isnan(feats).any() or np.isinf(feats).any():
            continue
        # all good? write to file
        output.write(str(convert_year(year))+' |avgcov')
        for k in range(90):
            output.write(' '+str(k+1)+':%.4f' % feats[k])
        output.write('\n')
    # close file
    output.close()


def die_with_usage():
    """ HELP MENU """
    print 'create_vw_dataset.py'
    print '   by T. Bertin-Mahieux (2011) Columbia University'
    print '      tb2332@columbia.edu'
    print '      copyright (c) TBM, 2011, All Rights Reserved'
    print ''
    print 'Code to create a dataset on year prediction for MLcomp.'
    print 'Features are mean and covariance of timbre features.'
    print 'Target is "year".'
    print ''
    print 'USAGE:'
    print '  python create_vw_dataset.py <MSD_DIR> <testartists> <tmdb> <train> <test>'
    print 'PARAMS'
    print '     MSD_DIR  - main Million Song Dataset dir, <?>/millionsong/data'
    print ' testartists  - file containing test artist IDs, one per line'
    print '        tmdb  - SQLite database track_metadata.db'
    print '       train  - output text file with training data'
    print '        test  - output text file with testing data'
    print ''
    sys.exit(0)



if __name__ == '__main__':

    # help menu
    if len(sys.argv)<6:
        die_with_usage()

    # params
    msd_dir = sys.argv[1]
    testartists = sys.argv[2]
    tmdb = sys.argv[3]
    outtrain = sys.argv[4]
    outtest = sys.argv[5]

    # sanity checks
    if not os.path.isdir(msd_dir):
        print 'ERROR:',msd_dir,'is not a directory.'
        sys.exit(0)
    if not os.path.isfile(testartists):
        print 'ERROR:',testartists,'is not a file.'
        sys.exit(0)
    if not os.path.isfile(tmdb):
        print 'ERROR:',tmdb,'is not a file.'
        sys.exit(0)
    if os.path.isfile(outtrain):
        print 'ERROR:',outtrain,'already exists.'
        sys.exit(0)
    if os.path.isfile(outtest):
        print 'ERROR:',outtest,'already exists.'
        sys.exit(0)

    # start time
    t1 = time.time()

    # get training and testing songs
    trainsongs,testsongs = get_train_test_songs(msd_dir,testartists,tmdb)
    t2 = time.time()
    stimelen = str(datetime.timedelta(seconds=t2-t1))
    print 'Got train and test songs in',stimelen; sys.stdout.flush()

    # process train files
    extract_features(trainsongs,outtrain)
    t3 = time.time()
    stimelen = str(datetime.timedelta(seconds=t3-t1))
    print 'Done with train songs',stimelen; sys.stdout.flush()

    # process test files
    extract_features(testsongs,outtest)
    t4 = time.time()
    stimelen = str(datetime.timedelta(seconds=t4-t1))
    print 'Done with test songs',stimelen; sys.stdout.flush()

    # done
    t5 = time.time()
    stimelen = str(datetime.timedelta(seconds=t5-t1))
    print 'ALL DONE IN',stimelen; sys.stdout.flush()

########NEW FILE########
__FILENAME__ = measure_vw_res
"""
Measure vowpal output
"""

import os
import sys
import numpy as np
sys.path.append( os.path.abspath('..') ) # hack!
import year_pred_benchmark as BENCHMARK


def convert_back_to_year(val):
    """
    get something between 0 and 1, return a year between 1922 and 2011
    """
    assert val >= 0 and val <= 1
    return 1922. + val * ( 2011. - 1922. )



def measure(testf,vwout,verbose=1):
    """
    measure the result from the test file and vw output
    """
    years_real = []
    years_pred = []
    f_real = open(testf,'r')
    f_pred = open(vwout,'r')
    for line_real in f_real.xreadlines():
        line_pred = f_pred.readline().strip()
        years_real.append( convert_back_to_year(float(line_real.split(' ')[0])) )
        years_pred.append( convert_back_to_year(float(line_pred)) )
    # close files
    f_real.close()
    f_pred.close()
    # measure
    return BENCHMARK.evaluate(years_real,years_pred,verbose=verbose)


def die_with_usage():
    """ HELP MENU """
    print 'python measure_vw_res.py testfile vwoutput'
    sys.exit(0)

if __name__ == '__main__':

    if len(sys.argv) < 3:
        die_with_usage()

    testf = sys.argv[1]
    vwout = sys.argv[2]
    measure(testf,vwout)


########NEW FILE########
__FILENAME__ = process_test_set
"""
Thierry Bertin-Mahieux (2011) Columbia University
tb2332@columbia.edu

Code to go through the test set, get a summary of the features
(the same as for train set) and predict year using KNN.

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.

Copyright (c) 2011, Thierry Bertin-Mahieux, All Rights Reserved

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

# path to the YearRecognition folder in the Million Song Dataset
# project, if not in PYTHONPATH
YEAR_REC_FOLDERS=['/home/thierry/Columbia/MSongsDB/Tasks_Demos/YearPrediction','/home/empire6/thierry/MSongsDB/Tasks_Demos/YearPrediction']

import os
import sys
import time
import glob
import copy
import tables
import sqlite3
import datetime
import multiprocessing
import numpy as np
import hdf5_getters as GETTERS
import compress_feat as CBTF
import year_pred_benchmark as BENCHMARK
import randproj as RANDPROJ
for p in YEAR_REC_FOLDERS:
    sys.path.append(p)
from beat_aligned_feats import get_bttimbre
try:
    import scikits.ann as ANN
except ImportError:
    print 'you need scikits.ann: http://www.scipy.org/scipy/scikits/wiki/AnnWrapper'
    sys.exit(0)


class KeyboardInterruptError(Exception):pass


def fullpath_from_trackid(maindir,trackid):
    p = os.path.join(maindir,trackid[2])
    p = os.path.join(p,trackid[3])
    p = os.path.join(p,trackid[4])
    p = os.path.join(p,trackid+'.h5')
    return str(p)


def do_prediction(processed_feats,kd,h5model,K=1):
    """
    Receive processed features from test set, apply KNN,
    return an actual predicted year (float)
    INPUT
       processed_feats - extracted from a test song
                    kd - ANN kdtree on top of model
               h5model - open h5 file with data.feats and data.year
                     K - K-nn parameter
    """
    res = kd.knn(processed_feats,K)
    # we take the average for all K, all picks
    indexes = res[0].flatten()
    years = map(lambda x: h5model.root.data.year[x], indexes)
    pred_year = np.average(years)
    if np.isnan(pred_year):
        print 'PROBLEM! we got NaN from years:',years
        print 'Processed feats had NaN?',np.isnan(processed_feats).any()
        print 'processed_feats.shape=',processed_feats.shape
        print 'feats=',processed_feats
        return None
    # done (maybe we should return more info...?
    return pred_year


def process_filelist_test(filelist=None,model=None,tmpfilename=None,
                           npicks=None,winsize=None,finaldim=None,K=1,
                          typecompress='picks'):
    """
    Main function, process all files in the list (as long as their artist
    is in testartist)
    INPUT
       filelist     - a list of song files
       model        - h5 file containing feats and year for all train songs
       tmpfilename  - where to save our processed features
       npicks       - number of segments to pick per song
       winsize      - size of each segment we pick
       finaldim     - how many values do we keep
       K            - param of KNN (default 1)
       typecompress - feature type, 'picks', 'corrcoeff' or 'cov'
                      must be the same as in training
    """
    # sanity check
    for arg in locals().values():
        assert not arg is None,'process_filelist_test, missing an argument, something still None'
    if os.path.isfile(tmpfilename):
        print 'ERROR: file',tmpfilename,'already exists.'
        return
    if not os.path.isfile(model):
        print 'ERROR: model',model,'does not exist.'
        return
    # create kdtree
    h5model = tables.openFile(model, mode='r')
    assert h5model.root.data.feats.shape[1]==finaldim,'inconsistency in final dim'
    kd = ANN.kdtree(h5model.root.data.feats)
    # create outputfile
    output = tables.openFile(tmpfilename, mode='a')
    group = output.createGroup("/",'data','TMP FILE FOR YEAR RECOGNITION')
    output.createEArray(group,'year_real',tables.IntAtom(shape=()),(0,),'',
                        expectedrows=len(filelist))
    output.createEArray(group,'year_pred',tables.Float64Atom(shape=()),(0,),'',
                        expectedrows=len(filelist))
    # random projection
    ndim = 12 # fixed in this dataset
    if typecompress == 'picks':
        randproj = RANDPROJ.proj_point5(ndim * winsize, finaldim)
    elif typecompress == 'corrcoeff' or typecompress=='cov':
        randproj = RANDPROJ.proj_point5(ndim * ndim, finaldim)
    elif typecompress == 'avgcov':
        randproj = RANDPROJ.proj_point5(90, finaldim)
    else:
        assert False,'Unknown type of compression: '+str(typecompress)
    # go through files
    cnt_f = 0
    for f in filelist:
        cnt_f += 1
        if cnt_f % 5000 == 0:
            print 'TESTING FILE #'+str(cnt_f)
        # check file
        h5 = GETTERS.open_h5_file_read(f)
        artist_id = GETTERS.get_artist_id(h5)
        year = GETTERS.get_year(h5)
        track_id = GETTERS.get_track_id(h5)
        h5.close()
        if year <= 0: # probably useless but...
            continue
        if typecompress == 'picks':
            # we have a train artist with a song year, we're good
            bttimbre = get_bttimbre(f)
            if bttimbre is None:
                continue
            # we even have normal features, awesome!
            processed_feats = CBTF.extract_and_compress(bttimbre,npicks,winsize,finaldim,
                                                        randproj=randproj)
        elif typecompress == 'corrcoeff':
            h5 = GETTERS.open_h5_file_read(f)
            timbres = GETTERS.get_segments_timbre(h5).T
            h5.close()
            processed_feats = CBTF.corr_and_compress(timbres,finaldim,randproj=randproj)
        elif typecompress == 'cov':
            h5 = GETTERS.open_h5_file_read(f)
            timbres = GETTERS.get_segments_timbre(h5).T
            h5.close()
            processed_feats = CBTF.cov_and_compress(timbres,finaldim,randproj=randproj)
        elif typecompress == 'avgcov':
            h5 = GETTERS.open_h5_file_read(f)
            timbres = GETTERS.get_segments_timbre(h5).T
            h5.close()
            processed_feats = CBTF.avgcov_and_compress(timbres,finaldim,randproj=randproj)
        else:
            assert False,'Unknown type of compression: '+str(typecompress)
        if processed_feats is None:
            continue
        if processed_feats.shape[0] == 0:
            continue
        # do prediction
        year_pred = do_prediction(processed_feats,kd,h5model,K)
        # add pred and ground truth to output
        if not year_pred is None:
            output.root.data.year_real.append( [year] )
            output.root.data.year_pred.append( [year_pred] )
    # close output and model
    del kd
    h5model.close()
    output.close()
    # done
    return


def process_filelist_test_wrapper(args):
    """ wrapper function for multiprocessor, calls process_filelist_test """
    try:
        process_filelist_test(**args)
    except KeyboardInterrupt:
        raise KeyboardInterruptError()


def process_filelist_test_main_pass(nthreads,model,testsongs,
                                    npicks,winsize,finaldim,K,typecompress):
    """
    Do the main walk through the data, deals with the threads,
    creates the tmpfiles.
    INPUT
      - nthreads     - number of threads to use
      - model        - h5 files containing feats and year for all train songs
      - testsongs    - list of songs in the test set
      - npicks       - number of samples to pick per song
      - winsize      - window size (in beats) of a sample
      - finaldim     - final dimension of the sample, something like 5?
      - K            - K-nn parameter
      - typecompress - feature type, 'picks', 'corrcoeff', 'cov'
    RETURN
      - tmpfiles     - list of tmpfiles that were created
                       or None if something went wrong
    """
    # sanity checks
    assert nthreads >= 0,'Come on, give me at least one thread!'
    # prepare params for each thread
    params_list = []
    default_params = {'npicks':npicks,'winsize':winsize,'finaldim':finaldim,
                      'model':model,'K':K,'typecompress':typecompress}
    tmpfiles_stub = 'mainpasstest_tmp_output_win'+str(winsize)+'_np'+str(npicks)+'_fd'+str(finaldim)+'_'+typecompress+'_'
    tmpfiles = map(lambda x: os.path.join(os.path.abspath('.'),tmpfiles_stub+str(x)+'.h5'),range(nthreads))
    nfiles_per_thread = int(np.ceil(len(testsongs) * 1. / nthreads))
    for k in range(nthreads):
        # params for one specific thread
        p = copy.deepcopy(default_params)
        p['tmpfilename'] = tmpfiles[k]
        p['filelist'] = testsongs[k*nfiles_per_thread:(k+1)*nfiles_per_thread]
        params_list.append(p)
    # launch, run all the jobs
    pool = multiprocessing.Pool(processes=nthreads)
    try:
        pool.map(process_filelist_test_wrapper, params_list)
        pool.close()
        pool.join()
    except KeyboardInterruptError:
        print 'MULTIPROCESSING'
        print 'stopping multiprocessing due to a keyboard interrupt'
        pool.terminate()
        pool.join()
        return None
    except Exception, e:
        print 'MULTIPROCESSING'
        print 'got exception: %r, terminating the pool' % (e,)
        pool.terminate()
        pool.join()
        return None
    # all done!
    return tmpfiles


def test(nthreads,model,testsongs,npicks,winsize,finaldim,K,typecompress):
    """
    Main function to do the testing
    Do the main pass with the number of given threads.
    Then, reads the tmp files, computes the score, delete the tmpfiles.
    INPUT
      - nthreads     - number of threads to use
      - model        - h5 files containing feats and year for all train songs
      - testsongs    - songs to test on
      - npicks       - number of samples to pick per song
      - winsize      - window size (in beats) of a sample
      - finaldim     - final dimension of the sample, something like 5?
      - K            - K-nn parameter
      - typecompress - feature type, one of: 'picks', 'corrcoeff', 'cov'
    RETURN
       - nothing
    """
    # initial time
    t1 = time.time()
    # do main pass
    tmpfiles = process_filelist_test_main_pass(nthreads,model,testsongs,
                                               npicks,winsize,finaldim,K,
                                               typecompress)
                                               
    if tmpfiles is None:
        print 'Something went wrong, tmpfiles are None'
        return
    # intermediate time
    t2 = time.time()
    stimelen = str(datetime.timedelta(seconds=t2-t1))
    print 'Main pass done after',stimelen; sys.stdout.flush()
    # aggregate temp files
    year_real = []
    year_pred = []
    for tmpf in tmpfiles:
        h5 = tables.openFile(tmpf)
        year_real.extend( h5.root.data.year_real[:] )
        year_pred.extend( h5.root.data.year_pred[:] )
        h5.close()
        # delete tmp file
        os.remove(tmpf)
    # result
    BENCHMARK.evaluate(year_real,year_pred,verbose=1)
    # final time
    t3 = time.time()
    stimelen = str(datetime.timedelta(seconds=t3-t1))
    print 'Whole testing done after',stimelen
    # done
    return


def die_with_usage():
    """ HELP MENU """
    print 'process_test_set.py'
    print '   by T. Bertin-Mahieux (2011) Columbia University'
    print '      tb2332@columbia.edu'
    print 'Code to perform year prediction on the Million Song Dataset.'
    print 'This performs the testing based of a KNN model.'
    print 'USAGE:'
    print '  python process_test_set.py [FLAGS] <MSD_DIR> <model> <testartists> <tmdb>'
    print 'PARAMS:'
    print '        MSD_DIR  - main directory of the MSD dataset'
    print '          model  - h5 file where the training is saved'
    print '    testartists  - file containing test artists'
    print '           tmdb  - path to track_metadata.db'
    print 'FLAGS:'
    print '    -nthreads n  - number of threads to use'
    print '      -npicks n  - number of windows to pick per song (can be != than training)'
    print '     -winsize n  - windows size in beats for each pick'
    print '    -finaldim n  - final dimension after random projection'
    print '-typecompress s  - type of features, "picks", "corrcoeff" or "cov"'
    sys.exit(0)


if __name__ == '__main__':

    # help menu
    if len(sys.argv) < 5:
        die_with_usage()

    # flags
    nthreads = 1
    npicks = 3
    winsize = 12
    finaldim = 5
    K = 1
    typecompress = 'picks'
    while True:
        if sys.argv[1] == '-nthreads':
            nthreads = int(sys.argv[2])
            sys.argv.pop(1)
        elif sys.argv[1] == '-npicks':
            npicks = int(sys.argv[2])
            sys.argv.pop(1)
        elif sys.argv[1] == '-winsize':
            winsize = int(sys.argv[2])
            sys.argv.pop(1)
        elif sys.argv[1] == '-finaldim':
            finaldim = int(sys.argv[2])
            sys.argv.pop(1)
        elif sys.argv[1] == '-K':
            K = int(sys.argv[2])
            sys.argv.pop(1)
        elif sys.argv[1] == '-typecompress':
            typecompress = sys.argv[2]
            sys.argv.pop(1)
        else:
            break
        sys.argv.pop(1)

    # params
    msd_dir = sys.argv[1]
    model = sys.argv[2]
    testartists = sys.argv[3]
    tmdb = sys.argv[4]

    # sanity check
    assert os.path.isdir(msd_dir),'ERROR: dir '+msd_dir+' does not exist.'
    assert os.path.isfile(testartists),'ERROR: file '+testartists+' does not exist.'
    assert os.path.isfile(model),'ERROR: file '+model+' does not exist.'
    assert os.path.isfile(tmdb),'ERROR: file '+tmdb+' does not exist.'

    # verbose
    print '************ PARAMS ***************'
    print 'msd_dir:',msd_dir
    print 'model:',model
    print 'testartists:',testartists
    print 'tmdb:',tmdb
    print 'nthreads:', nthreads
    print 'npicks:',npicks
    print 'winsize:',winsize
    print 'finaldim:',finaldim
    print 'K:',K
    print 'typecompress:',typecompress
    print '***********************************'

    # read test artists
    testartists_set = set()
    f = open(testartists,'r')
    for line in f.xreadlines():
        if line == '' or line.strip() == '':
            continue
        testartists_set.add( line.strip() )
    f.close()
    print 'Found',len(testartists_set),'test artists.'

    # get test songs
    conn = sqlite3.connect(tmdb)
    q = "CREATE TEMP TABLE testartists (artist_id TEXT)"
    res = conn.execute(q)
    conn.commit()
    for aid in testartists_set:
        q = "INSERT INTO testartists VALUES ('"+aid+"')"
        conn.execute(q)
    conn.commit()
    q = "SELECT track_id FROM songs JOIN testartists"
    q += " ON testartists.artist_id=songs.artist_id WHERE year>0"
    res = conn.execute(q)
    data = res.fetchall()
    conn.close()
    print 'Found',len(data),'testing files from track_metadata.db'
    testsongs = map(lambda x: fullpath_from_trackid(msd_dir,x[0]),data)
    assert os.path.isfile(testsongs[0]),'first testing file does not exist? '+testsongs[0]

    # launch testing
    test(nthreads,model,testsongs,npicks,winsize,finaldim,K,typecompress)
    
    # done
    print 'DONE!'
    

########NEW FILE########
__FILENAME__ = process_train_set
"""
Thierry Bertin-Mahieux (2011) Columbia University
tb2332@columbia.edu

Code to parse the whole training set, get a summary of the features,
and save them in a KNN-ready format.

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.

Copyright (c) 2011, Thierry Bertin-Mahieux, All Rights Reserved

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

# path to the YearRecognition folder in the Million Song Dataset
# project, if not in PYTHONPATH
YEAR_REC_FOLDERS=['/home/thierry/Columbia/MSongsDB/Tasks_Demos/YearPrediction','/home/empire6/thierry/MSongsDB/Tasks_Demos/YearPrediction']

import os
import sys
import time
import glob
import copy
import tables
import sqlite3
import datetime
import multiprocessing
import numpy as np
import hdf5_getters as GETTERS
import compress_feat as CBTF
import randproj as RANDPROJ
for p in YEAR_REC_FOLDERS:
    sys.path.append(p)
from beat_aligned_feats import get_bttimbre


# error passing problems, useful for multiprocessing
class KeyboardInterruptError(Exception):pass


def fullpath_from_trackid(maindir,trackid):
    """ Creates proper file paths for song files """
    p = os.path.join(maindir,trackid[2])
    p = os.path.join(p,trackid[3])
    p = os.path.join(p,trackid[4])
    p = os.path.join(p,trackid+'.h5')
    return str(p)

def get_all_files(basedir,ext='.h5'):
    """
    From a root directory, go through all subdirectories
    and find all files with the given extension.
    Return all absolute paths in a list.
    """
    allfiles = []
    apply_to_all_files(basedir,func=lambda x: allfiles.append(x),ext=ext)
    return allfiles


def apply_to_all_files(basedir,func=lambda x: x,ext='.h5'):
    """
    From a root directory, go through all subdirectories
    and find all files with the given extension.
    Apply the given function func
    If no function passed, does nothing and counts file
    Return number of files
    """
    cnt = 0
    for root, dirs, files in os.walk(basedir):
        files = glob.glob(os.path.join(root,'*'+ext))
        for f in files :
            func(f)
            cnt += 1
    return cnt


def process_filelist_train(filelist=None,testartists=None,tmpfilename=None,
                           npicks=None,winsize=None,finaldim=None,typecompress='picks'):
    """
    Main function, process all files in the list (as long as their artist
    is not in testartist)
    INPUT
       filelist     - a list of song files
       testartists  - set of artist ID that we should not use
       tmpfilename  - where to save our processed features
       npicks       - number of segments to pick per song
       winsize      - size of each segment we pick
       finaldim     - how many values do we keep
       typecompress - one of 'picks' (win of btchroma), 'corrcoef' (correlation coefficients),
                      'cov' (covariance)
    """
    # sanity check
    for arg in locals().values():
        assert not arg is None,'process_filelist_train, missing an argument, something still None'
    if os.path.isfile(tmpfilename):
        print 'ERROR: file',tmpfilename,'already exists.'
        return
    # create outputfile
    output = tables.openFile(tmpfilename, mode='a')
    group = output.createGroup("/",'data','TMP FILE FOR YEAR RECOGNITION')
    output.createEArray(group,'feats',tables.Float64Atom(shape=()),(0,finaldim),'',
                        expectedrows=len(filelist))
    output.createEArray(group,'year',tables.IntAtom(shape=()),(0,),'',
                        expectedrows=len(filelist))
    output.createEArray(group,'track_id',tables.StringAtom(18,shape=()),(0,),'',
                        expectedrows=len(filelist))
    # random projection
    ndim = 12 # fixed in this dataset
    if typecompress == 'picks':
        randproj = RANDPROJ.proj_point5(ndim * winsize, finaldim)
    elif typecompress == 'corrcoeff' or typecompress == 'cov':
        randproj = RANDPROJ.proj_point5(ndim * ndim, finaldim)
    elif typecompress == 'avgcov':
        randproj = RANDPROJ.proj_point5(90, finaldim)
    else:
        assert False,'Unknown type of compression: '+str(typecompress)
    # iterate over files
    cnt_f = 0
    for f in filelist:
        cnt_f += 1
        # verbose
        if cnt_f % 50000 == 0:
            print 'training... checking file #',cnt_f
        # check file
        h5 = GETTERS.open_h5_file_read(f)
        artist_id = GETTERS.get_artist_id(h5)
        year = GETTERS.get_year(h5)
        track_id = GETTERS.get_track_id(h5)
        h5.close()
        if year <= 0 or artist_id in testartists:
            continue
        # we have a train artist with a song year, we're good
        bttimbre = get_bttimbre(f)
        if typecompress == 'picks':
            if bttimbre is None:
                continue
            # we even have normal features, awesome!
            processed_feats = CBTF.extract_and_compress(bttimbre,npicks,winsize,finaldim,
                                                        randproj=randproj)
        elif typecompress == 'corrcoeff':
            h5 = GETTERS.open_h5_file_read(f)
            timbres = GETTERS.get_segments_timbre(h5).T
            h5.close()
            processed_feats = CBTF.corr_and_compress(timbres,finaldim,randproj=randproj)
        elif typecompress == 'cov':
            h5 = GETTERS.open_h5_file_read(f)
            timbres = GETTERS.get_segments_timbre(h5).T
            h5.close()
            processed_feats = CBTF.cov_and_compress(timbres,finaldim,randproj=randproj)
        elif typecompress == 'avgcov':
            h5 = GETTERS.open_h5_file_read(f)
            timbres = GETTERS.get_segments_timbre(h5).T
            h5.close()
            processed_feats = CBTF.avgcov_and_compress(timbres,finaldim,randproj=randproj)
        else:
            assert False,'Unknown type of compression: '+str(typecompress)
        # save them to tmp file
        n_p_feats = processed_feats.shape[0]
        output.root.data.year.append( np.array( [year] * n_p_feats ) )
        output.root.data.track_id.append( np.array( [track_id] * n_p_feats ) )
        output.root.data.feats.append( processed_feats )
    # we're done, close output
    output.close()
    return

            
def process_filelist_train_wrapper(args):
    """ wrapper function for multiprocessor, calls process_filelist_train """
    try:
        process_filelist_train(**args)
    except KeyboardInterrupt:
        raise KeyboardInterruptError()


def process_filelist_train_main_pass(nthreads,maindir,testartists,
                                     npicks,winsize,finaldim,trainsongs=None,
                                     typecompress='picks'):
    """
    Do the main walk through the data, deals with the threads,
    creates the tmpfiles.
    INPUT
      - nthreads     - number of threads to use
      - maindir      - dir of the MSD, wehre to find song files
      - testartists  - set of artists to ignore
      - npicks       - number of samples to pick per song
      - winsize      - window size (in beats) of a sample
      - finaldim     - final dimension of the sample, something like 5?
      - trainsongs   - list of files to use for training
      - typecompress - 'picks', 'corrcoeff', 'cov'
    RETURN
      - tmpfiles     - list of tmpfiles that were created
                       or None if something went wrong
    """
    # sanity checks
    assert nthreads >= 0,'Come on, give me at least one thread!'
    if not os.path.isdir(maindir):
        print 'ERROR: directory',maindir,'does not exist.'
        return None
    # get all files
    if trainsongs is None:
        allfiles = get_all_files(maindir)
    else:
        allfiles = trainsongs
    assert len(allfiles)>0,'Come on, give me at least one file in '+maindir+'!'
    if nthreads > len(allfiles):
        nthreads = len(allfiles)
        print 'more threads than files, reducing number of threads to:',nthreads
    print 'WE FOUND',len(allfiles),'POTENTIAL TRAIN FILES'
    # prepare params for each thread
    params_list = []
    default_params = {'npicks':npicks,'winsize':winsize,'finaldim':finaldim,
                      'testartists':testartists,'typecompress':typecompress}
    tmpfiles_stub = 'mainpass_tmp_output_win'+str(winsize)+'_np'+str(npicks)+'_fd'+str(finaldim)+'_'+typecompress+'_'
    tmpfiles = map(lambda x: os.path.join(os.path.abspath('.'),tmpfiles_stub+str(x)+'.h5'),range(nthreads))
    nfiles_per_thread = int(np.ceil(len(allfiles) * 1. / nthreads))
    for k in range(nthreads):
        # params for one specific thread
        p = copy.deepcopy(default_params)
        p['tmpfilename'] = tmpfiles[k]
        p['filelist'] = allfiles[k*nfiles_per_thread:(k+1)*nfiles_per_thread]
        params_list.append(p)
    # launch, run all the jobs
    pool = multiprocessing.Pool(processes=nthreads)
    try:
        pool.map(process_filelist_train_wrapper, params_list)
        pool.close()
        pool.join()
    except KeyboardInterruptError:
        print 'MULTIPROCESSING'
        print 'stopping multiprocessing due to a keyboard interrupt'
        pool.terminate()
        pool.join()
        return None
    except Exception, e:
        print 'MULTIPROCESSING'
        print 'got exception: %r, terminating the pool' % (e,)
        pool.terminate()
        pool.join()
        return None
    # all done!
    return tmpfiles



def train(nthreads,maindir,output,testartists,npicks,winsize,finaldim,trainsongs=None,typecompress='picks'):
    """
    Main function to do the training
    Do the main pass with the number of given threads.
    Then, reads the tmp files, creates the main output, delete the tmpfiles.
    INPUT
      - nthreads     - number of threads to use
      - maindir      - dir of the MSD, wehre to find song files
      - output       - main model, contains everything to perform KNN
      - testartists  - set of artists to ignore
      - npicks       - number of samples to pick per song
      - winsize      - window size (in beats) of a sample
      - finaldim     - final dimension of the sample, something like 5?
      - trainsongs   - list of songs to use for training
      - typecompress - 'picks', 'corrcoeff' or 'cov'
    RETURN
       - nothing
    """
    # sanity checks
    if os.path.isfile(output):
        print 'ERROR: file',output,'already exists.'
        return
    # initial time
    t1 = time.time()
    # do main pass
    tmpfiles = process_filelist_train_main_pass(nthreads,maindir,testartists,
                                                npicks,winsize,finaldim,
                                                trainsongs=trainsongs,typecompress=typecompress)
    if tmpfiles is None:
        print 'Something went wrong, tmpfiles are None'
        return
    # intermediate time
    t2 = time.time()
    stimelen = str(datetime.timedelta(seconds=t2-t1))
    print 'Main pass done after',stimelen; sys.stdout.flush()
    # find approximate number of rows per tmpfiles
    h5 = tables.openFile(tmpfiles[0],'r')
    nrows = h5.root.data.year.shape[0] * len(tmpfiles)
    h5.close()
    # create output
    output = tables.openFile(output, mode='a')
    group = output.createGroup("/",'data','KNN MODEL FILE FOR YEAR RECOGNITION')
    output.createEArray(group,'feats',tables.Float64Atom(shape=()),(0,finaldim),'feats',
                        expectedrows=nrows)
    output.createEArray(group,'year',tables.IntAtom(shape=()),(0,),'year',
                        expectedrows=nrows)
    output.createEArray(group,'track_id',tables.StringAtom(18,shape=()),(0,),'track_id',
                        expectedrows=nrows)
    # aggregate temp files
    for tmpf in tmpfiles:
        h5 = tables.openFile(tmpf)
        output.root.data.year.append( h5.root.data.year[:] )
        output.root.data.track_id.append( h5.root.data.track_id[:] )
        output.root.data.feats.append( h5.root.data.feats[:] )
        h5.close()
        # delete tmp file
        os.remove(tmpf)
    # close output
    output.close()
    # final time
    t3 = time.time()
    stimelen = str(datetime.timedelta(seconds=t3-t1))
    print 'Whole training done after',stimelen
    # done
    return


def die_with_usage():
    """ HELP MENU """
    print 'process_train_set.py'
    print '   by T. Bertin-Mahieux (2011) Columbia University'
    print '      tb2332@columbia.edu'
    print 'Code to perform year prediction on the Million Song Dataset.'
    print 'This performs the training of the KNN model.'
    print 'USAGE:'
    print '  python process_train_set.py [FLAGS] <MSD_DIR> <output>'
    print 'PARAMS:'
    print '        MSD_DIR  - main directory of the MSD dataset'
    print '         output  - output filename (.h5 file)'
    print 'FLAGS:'
    print '    -nthreads n  - number of threads to use'
    print ' -testartists f  - file containing test artists (to ignore)'
    print '      -npicks n  - number of windows to pick per song'
    print '     -winsize n  - windows size in beats for each pick'
    print '    -finaldim n  - final dimension after random projection'
    print '        -tmdb f  - path to track_metadata.db, makes things faster'
    print '-typecompress s  - actual features we use, "picks", "corrcoeff" or "cov"'
    sys.exit(0)


if __name__ == '__main__':

    # help menu
    if len(sys.argv) < 3:
        die_with_usage()

    # flags
    nthreads = 1
    testartists = ''
    npicks = 3
    winsize = 12
    finaldim = 5
    tmdb = ''
    typecompress = 'picks'
    while True:
        if sys.argv[1] == '-nthreads':
            nthreads = int(sys.argv[2])
            sys.argv.pop(1)
        elif sys.argv[1] == '-testartists':
            testartists = sys.argv[2]
            sys.argv.pop(1)
        elif sys.argv[1] == '-npicks':
            npicks = int(sys.argv[2])
            sys.argv.pop(1)
        elif sys.argv[1] == '-winsize':
            winsize = int(sys.argv[2])
            sys.argv.pop(1)
        elif sys.argv[1] == '-finaldim':
            finaldim = int(sys.argv[2])
            sys.argv.pop(1)
        elif sys.argv[1] == '-tmdb':
            tmdb = sys.argv[2]
            sys.argv.pop(1)
        elif sys.argv[1] == '-typecompress':
            typecompress = sys.argv[2]
            sys.argv.pop(1)
        else:
            break
        sys.argv.pop(1)

    # params
    msd_dir = sys.argv[1]
    output = sys.argv[2]

    # read test artists
    testartists_set = set()
    if testartists != '':
        f = open(testartists,'r')
        for line in f.xreadlines():
            if line == '' or line.strip() == '':
                continue
            testartists_set.add( line.strip() )
        f.close()

    # get songlist from track_metadata.db
    trainsongs = None
    if tmdb != '':
        assert os.path.isfile(tmdb),'Database: '+tmdb+' does not exist.'
        conn = sqlite3.connect(tmdb)
        q = "CREATE TEMP TABLE testartists (artist_id TEXT)"
        res = conn.execute(q)
        conn.commit()
        for aid in testartists_set:
            q = "INSERT INTO testartists VALUES ('"+aid+"')"
            conn.execute(q)
        conn.commit()
        q = "CREATE TEMP TABLE trainartists (artist_id TEXT)"
        res = conn.execute(q)
        conn.commit()
        q = "INSERT INTO trainartists SELECT DISTINCT artist_id FROM songs"
        q += " EXCEPT SELECT artist_id FROM testartists"
        res = conn.execute(q)
        conn.commit()
        q = "SELECT track_id FROM songs JOIN trainartists"
        q += " ON trainartists.artist_id=songs.artist_id WHERE year>0"
        res = conn.execute(q)
        data = res.fetchall()
        conn.close()
        print 'Found',len(data),'training files from track_metadata.db'
        trainsongs = map(lambda x: fullpath_from_trackid(msd_dir,x[0]),data)
        assert os.path.isfile(trainsongs[0]),'first training file does not exist? '+trainsongs[0]

    # settings
    print 'msd dir:',msd_dir
    print 'output:',output
    print 'nthreads:',nthreads
    print 'testartists:',testartists,'('+str(len(testartists_set))+' artists)'
    print 'npicks:',npicks
    print 'winsize:',winsize
    print 'finaldim:',finaldim
    print 'tmdb:',tmdb
    print 'typecompress:',typecompress

    # sanity check
    if not os.path.isdir(msd_dir):
        print 'ERROR:',msd_dir,'is not a directory.'
        sys.exit(0)
    if os.path.isfile(output):
        print 'ERROR: file',output,'already exists.'
        sys.exit(0)

    # launch training
    train(nthreads,msd_dir,output,testartists_set,npicks,winsize,finaldim,trainsongs,typecompress)

    # done
    print 'DONE!'

########NEW FILE########
__FILENAME__ = randproj
"""
Thierry Bertin-Mahieux (2011) Columbia University
tb2332@columbia.edu

Library to generate random matrices using different methods

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.

Copyright 2011, Thierry Bertin-Mahieux

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import numpy as np

# square root of 3, which we might comput eoften otherwise
SQRT3=np.sqrt(3.)


def proj_point5(dimFrom,dimTo,seed=3232343):
    """
    Creates a matrix dimFrom x dimTo where each element is
    .5 or -.5 with probability 1/2 each
    For theoretical results using this projection see:
      D. Achlioptas. Database-friendly random projections.
      In Symposium on Principles of Database Systems
      (PODS), pages 274-281, 2001.
      http://portal.acm.org/citation.cfm?doid=375551.375608
    """
    if dimFrom == dimTo:
        return np.eye(dimFrom)
    np.random.seed(seed)
    return np.random.randint(2,size=(dimFrom,dimTo)) - .5


def proj_sqrt3(dimFrom, dimTo,seed=3232343):
    """
    Creates a matrix dimFrom x dimTo where each element is
    sqrt(3) or -sqrt(3) with probability 1/6 each
    or 0 otherwise
    Slower than proj_point5 to create, and lots of zeros.
    For theoretical results using this projection see:
      D. Achlioptas. Database-friendly random projections.
      In Symposium on Principles of Database Systems
      (PODS), pages 274-281, 2001.
      http://portal.acm.org/citation.cfm?doid=375551.375608
    """
    if dimFrom == dimTo:
        return np.eye(dimFrom)
    np.random.seed(seed)
    x = np.random.rand(dimFrom,dimTo)
    res = np.zeros((dimFrom,dimTo))
    res[np.where(x<1./6)] = SQRT3
    res[np.where(x>1.-1./6)] = -SQRT3
    return res


def die_with_usage():
    """ HELP MENU """
    print 'randproj.py'
    print '   by T. Bertin-Mahieux (2011) Columbia University'
    print '      tb2332@columbia.edu'
    print ''
    print 'This code generates matrices for random projections.'
    print 'Should be used as a library, no main'
    sys.exit(0)


if __name__ == '__main__':

    # help menu
    die_with_usage()

########NEW FILE########
__FILENAME__ = year_pred_benchmark
"""
Thierry Bertin-Mahieux (2011) Columbia University
tb2332@columbia.edu

Code to measure a benchmark on year prediction, specifically
what score we get if we apply the average train year to the
whole dataset.

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.

Copyright (c) 2011, Thierry Bertin-Mahieux, All Rights Reserved

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import time
import glob
import copy
import tables
import sqlite3
import datetime
import numpy as np


def evaluate(years_real,years_pred,verbose=0):
    """
    Evaluate the result of a year prediction algorithm
    RETURN
      avg diff
      std diff
      avg square diff
      std square diff
    """
    years_real = np.array(years_real).flatten()
    years_pred = np.array(years_pred).flatten()
    if verbose>0:
        print 'Evaluation based on',years_real.shape[0],'examples.'
    assert years_real.shape[0] == years_pred.shape[0],'wrong years length, they dont fit'
    avg_diff = np.average(np.abs(years_real - years_pred))
    std_diff = np.std(np.abs(years_real - years_pred))
    avg_square_diff = np.average(np.square(years_real - years_pred))
    std_square_diff = np.std(np.square(years_real - years_pred))
    # verbose
    if verbose>0:
        print 'avg diff:',avg_diff
        print 'std diff:',std_diff
        print 'avg square diff:',avg_square_diff
        print 'std square diff:',std_square_diff
    # done, return 
    return avg_diff,std_diff,avg_square_diff,std_square_diff

def die_with_usage():
    """ HELP MENU """
    print 'year_pred_benchmark.py'
    print '   by T. Bertin-Mahieux (2011) Columbia University'
    print '      tb2332@columbia.edu'
    print ''
    print 'Script to get a benchmark on year prediction without'
    print 'using features. Also, contains functions to measure'
    print 'our predictions'
    print ''
    print 'USAGE:'
    print '   python year_pred_benchmark.py <test_artists> <track_metadata.db>'
    print 'PARAM:'
    print '      test_artists   - a list of test artist ID'
    print ' track_metadata.db   - SQLite database, comes with the MSD'
    print ''
    sys.exit(0)


if __name__ == '__main__':

    # help menu
    if len(sys.argv) < 3:
        die_with_usage()

    # params
    testf = sys.argv[1]
    tmdb = sys.argv[2]
    print 'test artists file:',testf
    print 'track_metadata.db:',tmdb

    # sanity checks
    if not os.path.isfile(testf):
        print 'ERROR: file',testf,'does not exist.'
        sys.exit(0)
    if not os.path.isfile(tmdb):
        print 'ERROR: file',tmdb,'does not exist.'
        sys.exit(0)
        
    # get test artists
    testartists_set = set()
    if testf != '':
        f = open(testf,'r')
        for line in f.xreadlines():
            if line == '' or line.strip() == '':
                continue
            testartists_set.add( line.strip() )
        f.close()

    # get train artists in tmp table
    conn = sqlite3.connect(tmdb)
    q = "CREATE TEMP TABLE testartists (artist_id TEXT)"
    res = conn.execute(q)
    conn.commit()
    for aid in testartists_set:
        q = "INSERT INTO testartists VALUES ('"+aid+"')"
        conn.execute(q)
    conn.commit()
    q = "CREATE TEMP TABLE trainartists (artist_id TEXT)"
    res = conn.execute(q)
    conn.commit()
    q = "INSERT INTO trainartists SELECT DISTINCT artist_id FROM songs"
    q += " EXCEPT SELECT artist_id FROM testartists"
    res = conn.execute(q)
    conn.commit()
    q = "SELECT year FROM songs JOIN trainartists"
    q += " ON trainartists.artist_id=songs.artist_id WHERE year>0"
    res = conn.execute(q)
    trainyears = map(lambda x: x[0], res.fetchall())

    # avg train years
    avg_train_years = np.average(trainyears)
    std_train_years = np.std(trainyears)
    print 'avg train year:',avg_train_years
    print 'std train year:',std_train_years

    # test years
    q = "SELECT year FROM songs JOIN testartists"
    q += " ON testartists.artist_id=songs.artist_id WHERE year>0"
    res = conn.execute(q)
    testyears = map(lambda x: x[0], res.fetchall())

    # done with the connection
    conn.close()

    # avg test years
    avg_test_years = np.average(testyears)
    std_test_years = np.std(testyears)
    print 'avg test year:',avg_test_years
    print 'std test year:',std_test_years

    # the real years are test_years
    # the predicted years are avg_train_years
    predyears = [avg_train_years] * len(testyears)

    # evaluation
    evaluate( testyears, predyears, verbose=1)
    

########NEW FILE########
__FILENAME__ = split_train_test
"""
Thierry Bertin-Mahieux (2010) Columbia University
tb2332@columbia.edu

Code to split the list of artists into train and test sets
for year prediction.

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.


Copyright 2010, Thierry Bertin-Mahieux

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import time
import glob
import numpy as np
import sqlite3

# random seed, note that we actually use hash(RNDSEED) so it can be anything
RNDSEED='caitlin'



def die_with_usage():
    """ HELP MENU """
    print 'split_train_test.py'
    print '  by T. Bertin-Mahieux (2010) Columbia University'
    print '     tb2332@columbia.edu'
    print 'GOAL'
    print '  Split the list of artists into train and test based on track years.'
    print '  We do not split individual tracks because of the producer effect,'
    print '  e.g. we want to predict years, not to recognize artists.'
    print 'USAGE'
    print '  python split_train_test.py <track_metadata.db> <train.txt> <test.txt>'
    print 'PARAMS'
    print ' track_metadata.db    - SQLite database containing metadata for each track'
    print '         train.txt    - list of Echo Nest artist ID'
    print '          test.txt    - list of Echo Nest artist ID'
    print '       subset_tmdb    - track_metadata for the subset, to be sure all subset artists are in train'
    print 'NOTE'
    print '  There are 515576 track with year info.'
    print '  There are 25398 artists with at least one song with year.'
    print '  With current seed, we get 2822 test artists, corresponding'
    print '  to 49436 test tracks.'
    sys.exit(0)


if __name__ == '__main__':

    # help menu
    if len(sys.argv) < 5:
        die_with_usage()

    # params
    dbfile = sys.argv[1]
    output_train = sys.argv[2]
    output_test = sys.argv[3]
    subset_tmdb = sys.argv[4]

    # sanity checks
    if not os.path.isfile(dbfile):
        print 'ERROR: database not found:',dbfile
        sys.exit(0)
    if os.path.exists(output_train):
        print 'ERROR:',output_train,'already exists! delete or provide a new name'
        sys.exit(0)
    if os.path.exists(output_test):
        print 'ERROR:',output_test,'already exists! delete or provide a new name'
        sys.exit(0)
    if not os.path.exists(subset_tmdb):
        print 'ERROR:',subset_tmdb,'does not exist.'
        sys.exit(0)

    # open connection
    conn = sqlite3.connect(dbfile)

    # get all tracks with year
    q = "SELECT Count(year) FROM songs WHERE year>0"
    res = conn.execute(q)
    ntracks = res.fetchone()[0]
    print 'Found',ntracks,'tracks for which we have year info.'

    # get all artists with average year
    q = "SELECT artist_id,Avg(year),artist_name FROM songs WHERE year>0 GROUP BY artist_id"
    res = conn.execute(q)
    artists = res.fetchall()
    print 'Found',len(artists),'artists with at least one song for which we have year.'

    # order artist per average year
    ordered_artists = sorted(artists,key=lambda x:x[0]) # so its reporducible, first sort by artist id
    ordered_artists = sorted(artists,key=lambda x:x[1])
    print 'Oldest artist:',ordered_artists[0][2]+'('+str(ordered_artists[0][1])+')'
    print 'Most recent artist:',ordered_artists[-1][2]+'('+str(ordered_artists[-1][1])+')'

    # set random seed
    np.random.seed( hash(RNDSEED) )

    # info about split
    print '*********************************************************'
    print 'We split artists by ordering them according to their'
    print 'average track year. For every 10 artists, we keep one at'
    print 'random for the test set.'
    print '*********************************************************'

    # get subset artists
    conn_subtmdb = sqlite3.connect(subset_tmdb)
    res = conn_subtmdb.execute('SELECT DISTINCT artist_id FROM songs')
    subset_artists = map(lambda x: x[0], res.fetchall())
    conn_subtmdb.close()
    print 'Found',len(subset_artists),'distinct subset artists.'
    
    # split between train and test, every 10 artists, put one at random in test
    train_artists = set()
    test_artists = set()
    artists_per_slice = 10
    nslices = int( len(ordered_artists) / artists_per_slice )
    for k in range(nslices):
        pos1 = k * artists_per_slice
        slice_artists = map(lambda x: x[0], ordered_artists[pos1:pos1+artists_per_slice])
        # get random artists, not in subset
        sanity_cnt = 0
        while True:
            sanity_cnt += 1
            test_pos = np.random.randint(len(slice_artists))
            if not slice_artists[test_pos] in subset_artists:
                break
            assert sanity_cnt < 100,'Cant find artist not in subset'
        for aidx,a in enumerate(slice_artists):
            if aidx == test_pos:
                test_artists.add(a)
            else:
                train_artists.add(a)
    print 'Split done, we have',len(test_artists),'test artists and',len(train_artists),'train artists.'

    # count test tracks
    n_test_tracks = 0
    for a in test_artists:
        q = "SELECT Count(track_id) FROM songs WHERE artist_id='"+a+"' AND year>0"
        res = conn.execute(q)
        n_test_tracks += res.fetchone()[0]
    print 'We have',n_test_tracks,'test tracks out of',str(ntracks)+'.'

    # write train
    train_artists_list = sorted(list(train_artists))
    f = open(output_train,'w')
    for a in train_artists_list:
        f.write(a + '\n')
    f.close()

    # write test
    test_artists_list = sorted(list(test_artists))
    f = open(output_test,'w')
    for a in test_artists_list:
        f.write(a + '\n')
    f.close()

    # close connection
    conn.close()


########NEW FILE########
